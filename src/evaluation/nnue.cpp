#include "evaluation/nnue.hpp"

#include "chess/position.hpp"
#include "evaluation/nnue_embedded.hpp"
#include "evaluation/nnue_forward.hpp"

#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iterator>
#include <memory>
#include <mutex>

namespace stockbear::nnue {
namespace {

constexpr std::uint16_t FormatVersion = 1;
constexpr char Magic[4] = {'S', 'B', 'N', 'N'};

// Column index inside the input block of one perspective: the twelve piece
// kinds times sixty-four relative squares.
inline int feature_of(Piece pc, Square sq, Color perspective, int bucket) {
    const int kind = 6 * int(color_of(pc)) + (int(type_of(pc)) - 1);
    const int relSquare = perspective == White ? int(sq) : (int(sq) ^ 56);
    return bucket * 768 + kind * 64 + relSquare;
}

inline int bucket_for(const Position& pos, Color perspective, int buckets) {
    if (buckets <= 1) return 0;
    const Square king = pos.king_square(perspective);
    const Square relative = perspective == White ? king : flip_square(king);
    return king_bucket(relative, buckets);
}

std::unique_ptr<Network>& network_slot() {
    static std::unique_ptr<Network> slot;
    return slot;
}

// Little-endian scalar readers. The format is byte-oriented, so a network
// produced on one platform loads identically on another.
template <typename T>
bool read_value(const std::uint8_t*& cursor, const std::uint8_t* end, T& out) {
    if (std::size_t(end - cursor) < sizeof(T)) return false;
    using U = std::make_unsigned_t<T>;
    U raw = 0;
    for (std::size_t i = 0; i < sizeof(T); ++i) raw |= U(cursor[i]) << (8 * i);
    std::memcpy(&out, &raw, sizeof(T));
    cursor += sizeof(T);
    return true;
}

template <typename T>
void write_value(std::vector<std::uint8_t>& out, T value) {
    using U = std::make_unsigned_t<T>;
    U raw = 0;
    std::memcpy(&raw, &value, sizeof(T));
    for (std::size_t i = 0; i < sizeof(T); ++i) out.push_back(std::uint8_t((raw >> (8 * i)) & 0xFF));
}

std::uint64_t fnv1a(const void* data, std::size_t size, std::uint64_t seed) {
    const std::uint8_t* bytes = static_cast<const std::uint8_t*>(data);
    std::uint64_t h = seed;
    for (std::size_t i = 0; i < size; ++i) {
        h ^= bytes[i];
        h *= 1099511628211ULL;
    }
    return h;
}
} // namespace

int king_bucket(Square relativeKing, int buckets) {
    if (buckets <= 1) return 0;
    const int file = file_of(relativeKing);
    const int rank = rank_of(relativeKing);
    switch (buckets) {
    case 4:  return rank / 2;                                        // 4 rank bands
    case 16: return (rank / 2) * 4 + file / 2;                       // 4x4 coarse cells
    case 64: return int(relativeKing);                               // exact square
    default: return (rank * buckets) / 8;                            // rank bands
    }
}

std::uint64_t features_checksum(const Network& net) {
    std::uint64_t h = 1469598103934665603ULL;
    h = fnv1a(&net.kingBuckets, sizeof(net.kingBuckets), h);
    h = fnv1a(&net.l1, sizeof(net.l1), h);
    h = fnv1a(&net.l2, sizeof(net.l2), h);
    h = fnv1a(&net.actShift, sizeof(net.actShift), h);
    h = fnv1a(&net.h2Shift, sizeof(net.h2Shift), h);
    h = fnv1a(&net.outShift, sizeof(net.outShift), h);
    h = fnv1a(net.w1.data(), net.w1.size() * sizeof(std::int16_t), h);
    h = fnv1a(net.b1.data(), net.b1.size() * sizeof(std::int32_t), h);
    h = fnv1a(net.w2.data(), net.w2.size() * sizeof(std::int16_t), h);
    h = fnv1a(net.b2.data(), net.b2.size() * sizeof(std::int32_t), h);
    h = fnv1a(net.w3.data(), net.w3.size() * sizeof(std::int16_t), h);
    h = fnv1a(&net.b3, sizeof(net.b3), h);
    return h;
}

Network parse_network(const void* data, std::size_t size, std::string* error) {
    const auto fail = [&](const std::string& message) {
        if (error) *error = message;
        return Network{};
    };
    if (size < SerializedHeaderBytes) return fail("network file truncated (header)");
    const std::uint8_t* cursor = static_cast<const std::uint8_t*>(data);
    const std::uint8_t* end = cursor + size;
    if (std::memcmp(cursor, Magic, 4) != 0) return fail("network file has a bad magic number");
    cursor += 4;

    std::uint16_t version = 0, buckets = 0, l1 = 0, l2 = 0, actShift = 0, h2Shift = 0, outShift = 0, reserved = 0;
    if (!read_value(cursor, end, version) || !read_value(cursor, end, buckets) ||
        !read_value(cursor, end, l1) || !read_value(cursor, end, l2) ||
        !read_value(cursor, end, actShift) || !read_value(cursor, end, h2Shift) ||
        !read_value(cursor, end, outShift) || !read_value(cursor, end, reserved))
        return fail("network file truncated (header fields)");
    if (version != FormatVersion) return fail("unsupported network format version");
    if (buckets < 1 || buckets > MaxBuckets) return fail("network king-bucket count out of range");
    if (l1 < 16 || l1 > MaxL1 || (l1 % 16) != 0) return fail("network L1 size out of range");
    if (l2 < 1 || l2 > MaxL2) return fail("network L2 size out of range");
    if (actShift > 14 || h2Shift > 24 || outShift > 24) return fail("network shift out of range");

    Network net;
    net.kingBuckets = buckets;
    net.l1 = l1;
    net.l2 = l2;
    net.actShift = actShift;
    net.h2Shift = h2Shift;
    net.outShift = outShift;
    net.inputCount = buckets * 768;

    const std::size_t w1Count = std::size_t(net.inputCount) * std::size_t(l1);
    const std::size_t w2Count = std::size_t(l2) * std::size_t(2 * l1);
    const std::size_t expected = std::size_t(SerializedHeaderBytes) + w1Count * 2 +
                                 std::size_t(l1) * 4 + w2Count * 2 + std::size_t(l2) * 4 +
                                 std::size_t(l2) * 2 + 4;
    if (size != expected)
        return fail("network file size mismatch (expected " + std::to_string(expected) + " bytes, got " +
                    std::to_string(size) + ")");

    net.w1.resize(w1Count);
    net.b1.resize(std::size_t(l1));
    net.w2.resize(w2Count);
    net.b2.resize(std::size_t(l2));
    net.w3.resize(std::size_t(l2));
    for (std::size_t i = 0; i < w1Count; ++i)
        if (!read_value(cursor, end, net.w1[i])) return fail("network file truncated (w1)");
    for (std::size_t i = 0; i < net.b1.size(); ++i)
        if (!read_value(cursor, end, net.b1[i])) return fail("network file truncated (b1)");
    for (std::size_t i = 0; i < w2Count; ++i)
        if (!read_value(cursor, end, net.w2[i])) return fail("network file truncated (w2)");
    for (std::size_t i = 0; i < net.b2.size(); ++i)
        if (!read_value(cursor, end, net.b2[i])) return fail("network file truncated (b2)");
    for (std::size_t i = 0; i < net.w3.size(); ++i)
        if (!read_value(cursor, end, net.w3[i])) return fail("network file truncated (w3)");
    if (!read_value(cursor, end, net.b3)) return fail("network file truncated (b3)");

    // The quantised parameters must not be able to overflow the int16
    // accumulator: at most 32 features can be active per perspective, so the
    // worst-case sum is bounded by the largest magnitude times 32 plus the bias.
    std::int32_t maxWeight = 0;
    for (std::int16_t w : net.w1) maxWeight = std::max<std::int32_t>(maxWeight, std::abs(int(w)));
    std::int32_t maxBias = 0;
    for (std::int32_t b : net.b1) maxBias = std::max<std::int32_t>(maxBias, std::abs(int(b)));
    if (std::int64_t(maxWeight) * 32 + maxBias > 32000)
        return fail("network weights could overflow the 16-bit accumulator");

    net.checksum = features_checksum(net);
    return net;
}

Network parse_network_file(const std::string& path, std::string* error) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        if (error) *error = "cannot open " + path;
        return Network{};
    }
    const std::vector<std::uint8_t> bytes((std::istreambuf_iterator<char>(in)),
                                          std::istreambuf_iterator<char>());
    if (!in.good() && !in.eof()) {
        if (error) *error = "cannot read " + path;
        return Network{};
    }
    return parse_network(bytes.data(), bytes.size(), error);
}

std::vector<std::uint8_t> serialize_network(const Network& net) {
    std::vector<std::uint8_t> out;
    out.reserve(SerializedHeaderBytes + net.w1.size() * 2 + net.b1.size() * 4 + net.w2.size() * 2 +
                net.b2.size() * 4 + net.w3.size() * 2 + 4);
    for (char c : Magic) out.push_back(std::uint8_t(c));
    write_value<std::uint16_t>(out, FormatVersion);
    write_value<std::uint16_t>(out, std::uint16_t(net.kingBuckets));
    write_value<std::uint16_t>(out, std::uint16_t(net.l1));
    write_value<std::uint16_t>(out, std::uint16_t(net.l2));
    write_value<std::uint16_t>(out, std::uint16_t(net.actShift));
    write_value<std::uint16_t>(out, std::uint16_t(net.h2Shift));
    write_value<std::uint16_t>(out, std::uint16_t(net.outShift));
    write_value<std::uint16_t>(out, std::uint16_t(0));
    for (std::int16_t w : net.w1) write_value<std::int16_t>(out, w);
    for (std::int32_t b : net.b1) write_value<std::int32_t>(out, b);
    for (std::int16_t w : net.w2) write_value<std::int16_t>(out, w);
    for (std::int32_t b : net.b2) write_value<std::int32_t>(out, b);
    for (std::int16_t w : net.w3) write_value<std::int16_t>(out, w);
    write_value<std::int32_t>(out, net.b3);
    return out;
}

bool install_network(Network net, std::string* error) {
    if (net.l1 < 16 || net.l1 > MaxL1 || net.l2 < 1 || net.l2 > MaxL2 || net.kingBuckets < 1 ||
        net.kingBuckets > MaxBuckets) {
        if (error) *error = "network dimensions out of range";
        return false;
    }
    if (net.inputCount != net.kingBuckets * 768 ||
        net.w1.size() != std::size_t(net.inputCount) * std::size_t(net.l1) ||
        net.b1.size() != std::size_t(net.l1) ||
        net.w2.size() != std::size_t(net.l2) * std::size_t(2 * net.l1) ||
        net.b2.size() != std::size_t(net.l2) || net.w3.size() != std::size_t(net.l2)) {
        if (error) *error = "network weight arrays do not match the declared dimensions";
        return false;
    }
    net.checksum = features_checksum(net);
    network_slot() = std::make_unique<Network>(std::move(net));
    return true;
}

bool embedded_network_available() { return kEmbeddedNetSize != 0; }

bool install_embedded_network(std::string* error) {
    if (kEmbeddedNetSize == 0) {
        if (error) *error = "this build embeds no neural network";
        return false;
    }
    Network net = parse_network(kEmbeddedNetData, kEmbeddedNetSize, error);
    if (net.l1 == 0) return false;
    return install_network(std::move(net), error);
}

void clear_network() { network_slot().reset(); }

const Network* active_network() { return network_slot().get(); }

std::string network_identity() {
    const Network* net = active_network();
    if (net == nullptr) return "none";
    return "SBNN-" + std::to_string(net->kingBuckets) + "x" + std::to_string(net->l1) + "x" +
           std::to_string(net->l2) + " " + [](std::uint64_t v) {
               static const char* hex = "0123456789abcdef";
               std::string s(16, '0');
               for (int i = 15; i >= 0; --i) {
                   s[std::size_t(i)] = hex[v & 0xF];
                   v >>= 4;
               }
               return s;
           }(net->checksum);
}

void feature_list(const Position& pos, Color perspective, std::vector<int>& out) {
    out.clear();
    const int buckets = active_network() ? active_network()->kingBuckets : 1;
    const int bucket = bucket_for(pos, perspective, buckets);
    for (int pt = Pawn; pt <= King; ++pt)
        for (Color c : {White, Black})
            for (Bitboard b = pos.pieces(c, PieceType(pt)); b;) {
                const Square s = pop_lsb(b);
                out.push_back(feature_of(make_piece(c, PieceType(pt)), s, perspective, bucket));
            }
    std::sort(out.begin(), out.end());
}

void refresh(const Position& pos, Accumulator& acc) {
    const Network* net = active_network();
    if (net == nullptr) return;
    const int l1 = net->l1;
    for (int p = 0; p < ColorNB; ++p)
        for (int i = 0; i < l1; ++i) acc.v[p][i] = std::int16_t(net->b1[std::size_t(i)]);
    for (int pt = Pawn; pt <= King; ++pt)
        for (Color c : {White, Black})
            for (Bitboard b = pos.pieces(c, PieceType(pt)); b;) {
                const Square s = pop_lsb(b);
                add_piece(acc, pos, make_piece(c, PieceType(pt)), s);
            }
}

void add_piece(Accumulator& acc, const Position& pos, Piece pc, Square sq) {
    const Network* net = active_network();
    if (net == nullptr) return;
    const int l1 = net->l1;
    const int buckets = net->kingBuckets;
    for (int p = 0; p < ColorNB; ++p) {
        const Color perspective = Color(p);
        const int feature = feature_of(pc, sq, perspective, bucket_for(pos, perspective, buckets));
        const std::int16_t* row = net->w1.data() + std::size_t(feature) * std::size_t(l1);
        for (int i = 0; i < l1; ++i) acc.v[p][i] = std::int16_t(acc.v[p][i] + row[i]);
    }
}

void subtract_piece(Accumulator& acc, const Position& pos, Piece pc, Square sq) {
    const Network* net = active_network();
    if (net == nullptr) return;
    const int l1 = net->l1;
    const int buckets = net->kingBuckets;
    for (int p = 0; p < ColorNB; ++p) {
        const Color perspective = Color(p);
        const int feature = feature_of(pc, sq, perspective, bucket_for(pos, perspective, buckets));
        const std::int16_t* row = net->w1.data() + std::size_t(feature) * std::size_t(l1);
        for (int i = 0; i < l1; ++i) acc.v[p][i] = std::int16_t(acc.v[p][i] - row[i]);
    }
}

int evaluate(const Position& pos, const Accumulator& acc) {
    const Network* net = active_network();
    if (net == nullptr) return 0;
    // Side-to-move perspective first; see the note in nnue_forward.hpp.
    const int me = int(pos.side_to_move());
    const std::int32_t raw = forward()(*net, acc.v[me], acc.v[me ^ 1]);
    const std::int32_t cp = raw >> net->outShift;
    return std::clamp<int>(int(cp), -VALUE_KNOWN_WIN, VALUE_KNOWN_WIN);
}

int evaluate_from_scratch(const Position& pos) {
    Accumulator acc;
    refresh(pos, acc);
    return evaluate(pos, acc);
}

} // namespace stockbear::nnue
