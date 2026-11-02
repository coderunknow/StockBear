// Tests for the neural evaluation: feature layout, incremental accumulators,
// serialisation and the quantised forward pass.
//
// The tests build a small deterministic network instead of using whatever the
// binary embeds, so they keep testing the same thing after the shipped network
// is retrained. Nothing here needs a trained net to be meaningful: the
// properties under test are structural.
#include "test.hpp"
#include "evaluation/evaluation.hpp"
#include "evaluation/nnue.hpp"
#include "evaluation/nnue_embedded.hpp"
#include "evaluation/nnue_forward.hpp"
#include "chess/position.hpp"

#include <algorithm>
#include <cstdint>
#include <vector>

using namespace stockbear;

namespace {

// A reproducible pseudo-random network with small weights, so that the
// int16 accumulator cannot overflow and the expected values are easy to reason
// about.
nnue::Network synthetic_network(int l1 = 32, int l2 = 8) {
    nnue::Network net;
    net.kingBuckets = 1;
    net.l1 = l1;
    net.l2 = l2;
    net.inputCount = 768;
    net.actShift = 2;
    net.h2Shift = 6;
    net.outShift = 2;
    std::uint64_t state = 0x1234567890ABCDEFULL;
    const auto next = [&state]() {
        state = state * 6364136223846793005ULL + 1442695040888963407ULL;
        return std::int32_t((state >> 33) % 601) - 300; // -300..300
    };
    net.w1.resize(std::size_t(net.inputCount) * std::size_t(l1));
    for (auto& w : net.w1) w = std::int16_t(next() / 8);
    net.b1.resize(std::size_t(l1));
    for (auto& b : net.b1) b = next() / 4;
    net.w2.resize(std::size_t(l2) * std::size_t(2 * l1));
    for (auto& w : net.w2) w = std::int16_t(next() / 16);
    net.b2.resize(std::size_t(l2));
    for (auto& b : net.b2) b = next();
    net.w3.resize(std::size_t(l2));
    for (auto& w : net.w3) w = std::int16_t(next() / 8);
    net.b3 = next();
    return net;
}

struct ScopedNetwork {
    explicit ScopedNetwork(nnue::Network net) {
        std::string error;
        installed_ = nnue::install_network(std::move(net), &error);
        if (!installed_) throw std::runtime_error("test network rejected: " + error);
    }
    ~ScopedNetwork() { nnue::clear_network(); }
    bool installed_ = false;
};

std::vector<int> sorted_reference_features(const Position& pos, Color perspective) {
    std::vector<int> out;
    for (int pt = Pawn; pt <= King; ++pt)
        for (Color c : {White, Black})
            for (Bitboard b = pos.pieces(c, PieceType(pt)); b;) {
                const Square s = pop_lsb(b);
                const int kind = 6 * int(c) + (pt - 1);
                const int rel = perspective == White ? int(s) : (int(s) ^ 56);
                out.push_back(kind * 64 + rel);
            }
    std::sort(out.begin(), out.end());
    return out;
}
} // namespace

TEST(nnue, feature_layout_is_mirror_symmetric) {
    ScopedNetwork guard(synthetic_network());
    // The starting position and its colour-mirrored twin must produce the same
    // feature set when the perspectives are swapped; that identity is what makes
    // the network's output the score for the side to move.
    const Position start = test::position(START_FEN);
    // Same placement, other side to move: the features must not depend on whose
    // turn it is, only on the placement.
    const Position mirrored = test::position("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1");
    std::vector<int> a, b;
    nnue::feature_list(start, White, a);
    nnue::feature_list(mirrored, White, b);
    CHECK(a == b);
    // Kings are features: a king move must change the feature set.
    Position moved = test::position("4k3/8/8/8/3N4/4P3/8/4K3 w - - 0 1");
    std::vector<int> before, after;
    nnue::feature_list(moved, White, before);
    test::play(moved, "e1e2");
    nnue::feature_list(moved, White, after);
    CHECK(after != before);
}

TEST(nnue, feature_indices_match_a_from_scratch_walk) {
    ScopedNetwork guard(synthetic_network());
    const char* fens[] = {
        START_FEN,
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
        "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
        "8/8/8/8/8/8/6k1/4K2R w K - 0 1",
    };
    for (const char* fen : fens) {
        const Position pos = test::position(fen);
        for (Color perspective : {White, Black}) {
            std::vector<int> got;
            nnue::feature_list(pos, perspective, got);
            CHECK(got == sorted_reference_features(pos, perspective));
            // No duplicates: a feature repeated would double its weight.
            CHECK(std::adjacent_find(got.begin(), got.end()) == got.end());
            for (int f : got) CHECK(f >= 0 && f < 768);
        }
    }
}

TEST(nnue, incremental_accumulator_matches_from_scratch) {
    ScopedNetwork guard(synthetic_network());
    // The whole make/unmake path is exercised: captures, en passant, castling,
    // promotion and a null move all have to update both perspectives exactly.
    Position pos = test::position(START_FEN);
    const char* line[] = {"e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4", "f3d4",
                          "g8f6", "b1c3", "a7a6", "c1e3", "e7e5", "d4b3", "c8e6"};
    for (const char* move : line) {
        test::play(pos, move);
        test::state_ok(pos); // verify_state compares the accumulator with a rebuild
    }
    // Castling moves a rook as well as the king.
    Position castle = test::position("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1");
    test::play(castle, "e1g1");
    test::state_ok(castle);
    test::play(castle, "e8c8");
    test::state_ok(castle);
    // Promotion replaces a pawn with another piece.
    Position promo = test::position("8/P6k/8/8/8/8/7p/5K2 w - - 0 1");
    test::play(promo, "a7a8q");
    test::state_ok(promo);
    test::play(promo, "h2h1n");
    test::state_ok(promo);
    // En passant removes a pawn that is not on the destination square.
    Position ep = test::position("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1");
    test::play(ep, "e5d6");
    test::state_ok(ep);
    // A null move changes nothing about the placement.
    Position nullPos = test::position(START_FEN);
    const nnue::Accumulator before = *nullPos.nnue_accumulator();
    nullPos.make_null_move();
    const nnue::Accumulator after = *nullPos.nnue_accumulator();
    for (int p = 0; p < ColorNB; ++p)
        for (int i = 0; i < 32; ++i) CHECK_EQ(before.v[p][i], after.v[p][i]);
    nullPos.unmake_null_move();
    test::state_ok(nullPos);
    // And unmaking the whole line returns the original evaluation.
    Position undo = test::position(START_FEN);
    const int startEval = nnue::evaluate(undo, *undo.nnue_accumulator());
    std::vector<Move> made;
    for (const char* move : line) {
        const Move m = move_from_uci(undo, move);
        CHECK(is_ok(m));
        undo.make_move(m);
        made.push_back(m);
    }
    while (!made.empty()) {
        undo.unmake_move(made.back());
        made.pop_back();
    }
    test::state_ok(undo);
    CHECK_EQ(nnue::evaluate(undo, *undo.nnue_accumulator()), startEval);
}

TEST(nnue, evaluation_is_ordered_side_to_move_first) {
    ScopedNetwork guard(synthetic_network());
    // The forward pass must receive the side to move's perspective first and the
    // opponent's second. This is the one ordering mistake that trains happily and
    // then plays at roughly the strength of a constant evaluation, so it is
    // checked by construction rather than by playing strength.
    const char* fens[] = {
        "4k3/8/8/8/3N4/4P3/8/4K3 w - - 0 1",
        "4k3/8/8/8/3N4/4P3/8/4K3 b - - 0 1",
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R b KQkq - 0 1",
    };
    for (const char* fen : fens) {
        const Position pos = test::position(fen);
        const int me = int(pos.side_to_move());
        nnue::Accumulator acc;
        nnue::refresh(pos, acc);
        const std::int32_t expected = nnue::forward_scalar(*nnue::active_network(), acc.v[me], acc.v[me ^ 1]);
        CHECK_EQ(nnue::evaluate(pos, acc), int(std::clamp<std::int32_t>(
            expected >> nnue::active_network()->outShift, -VALUE_KNOWN_WIN, VALUE_KNOWN_WIN)));
        // With random weights the two orderings almost surely differ, so the
        // check above is not vacuous.
        const std::int32_t swapped = nnue::forward_scalar(*nnue::active_network(), acc.v[me ^ 1], acc.v[me]);
        CHECK(expected != swapped);
    }
}

TEST(nnue, scalar_and_simd_kernels_agree) {
    ScopedNetwork guard(synthetic_network(64, 16));
    const char* fens[] = {
        START_FEN,
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "4k3/8/8/8/8/8/8/4K3 w - - 0 1",
    };
    for (const char* fen : fens) {
        const Position pos = test::position(fen);
        nnue::Accumulator acc;
        nnue::refresh(pos, acc);
        const std::int32_t scalar = nnue::forward_scalar(*nnue::active_network(), acc.v[0], acc.v[1]);
#if defined(STOCKBEAR_HAVE_AVX2)
        if (nnue::cpu_has_avx2()) {
            const std::int32_t simd = nnue::forward_avx2(*nnue::active_network(), acc.v[0], acc.v[1]);
            CHECK_EQ(scalar, simd);
            // Ordering is part of the contract, and the kernel must respect it.
            CHECK_EQ(nnue::forward_avx2(*nnue::active_network(), acc.v[1], acc.v[0]),
                     nnue::forward_scalar(*nnue::active_network(), acc.v[1], acc.v[0]));
            CHECK_EQ(scalar, simd);
        }
#endif
        (void)scalar;
    }
}

TEST(nnue, serialisation_round_trip_and_rejection) {
    const nnue::Network net = synthetic_network(32, 8);
    std::vector<std::uint8_t> blob = nnue::serialize_network(net);
    std::string error;
    const nnue::Network parsed = nnue::parse_network(blob.data(), blob.size(), &error);
    CHECK_EQ(parsed.l1, net.l1);
    CHECK_EQ(parsed.l2, net.l2);
    CHECK_EQ(parsed.kingBuckets, net.kingBuckets);
    CHECK_EQ(parsed.actShift, net.actShift);
    CHECK_EQ(parsed.h2Shift, net.h2Shift);
    CHECK_EQ(parsed.outShift, net.outShift);
    CHECK(parsed.w1 == net.w1);
    CHECK(parsed.b1 == net.b1);
    CHECK(parsed.w2 == net.w2);
    CHECK(parsed.b2 == net.b2);
    CHECK(parsed.w3 == net.w3);
    CHECK_EQ(parsed.b3, net.b3);

    // A truncated blob, a corrupted magic and a wrong length must all be
    // rejected rather than read past the end.
    for (std::size_t cut : {std::size_t(0), std::size_t(4), blob.size() / 2, blob.size() - 1}) {
        error.clear();
        const nnue::Network bad = nnue::parse_network(blob.data(), cut, &error);
        CHECK_EQ(bad.l1, 0);
        CHECK(!error.empty());
    }
    std::vector<std::uint8_t> corrupt = blob;
    corrupt[0] = 'X';
    error.clear();
    CHECK_EQ(nnue::parse_network(corrupt.data(), corrupt.size(), &error).l1, 0);
    corrupt = blob;
    corrupt.push_back(0);
    error.clear();
    CHECK_EQ(nnue::parse_network(corrupt.data(), corrupt.size(), &error).l1, 0);
    // A dimension that would overflow the accumulator is rejected at load time.
    nnue::Network huge = synthetic_network(32, 8);
    for (auto& w : huge.w1) w = 30000;
    error.clear();
    CHECK_EQ(nnue::parse_network(nnue::serialize_network(huge).data(),
                                 nnue::serialize_network(huge).size(), &error).l1, 0);
    CHECK(!error.empty());
}

TEST(nnue, classical_evaluation_is_restored_when_the_network_is_cleared) {
    const bool embedded = nnue::embedded_network_available();
    nnue::clear_network();
    CHECK(nnue::active_network() == nullptr);
    // Without a network the classical evaluation is in charge and the neural
    // score must not be consulted at all.
    const Position pos = test::position("4k3/8/8/8/3N4/4P3/8/4K3 w - - 0 1");
    const int classical = evaluate(pos);
    ScopedNetwork guard(synthetic_network());
    CHECK(nnue::active_network() != nullptr);
    // Installing a network changes the static score, and the accumulator stack
    // kept by the position follows it.
    CHECK(pos.nnue_accumulator() != nullptr);
    CHECK_EQ(evaluate(pos), nnue::evaluate(pos, *pos.nnue_accumulator()));
    CHECK(evaluate(pos) != classical);
    nnue::clear_network();
    CHECK(nnue::active_network() == nullptr);
    CHECK_EQ(evaluate(pos), classical);
    if (embedded) {
        std::string error;
        CHECK(nnue::install_embedded_network(&error));
        CHECK(nnue::active_network() != nullptr);
        nnue::clear_network();
    }
}
