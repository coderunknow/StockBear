// ---------------------------------------------------------------------------
// nnue.hpp - StockBear's own incrementally-updated neural evaluation.
//
// The network is a three-layer quantised forward pass over sparse
// "piece-square relative to the king" input features:
//
//   features  ->  accumulator (int16, updated incrementally on every move)
//             ->  clipped ReLU  (int8, 0..127)
//             ->  layer 2 (int8 weights, int32 accumulation) + clipped ReLU
//             ->  layer 3 (int8 weights, int32 accumulation)
//             ->  centipawns
//
// Feature index
//   kind      = 6 * colour + (pieceType - 1)          (0..11; kings included)
//   relSquare = colour == White ? square : square ^ 56
//   bucket    = king_bucket(relative King square, kingBuckets)
//   feature   = (bucket * 768) + kind * 64 + relSquare
//
// With `kingBuckets == 1` the bucket is always 0, so the feature set is the 768
// "piece on square" inputs and the incremental update is a pure function of
// (piece, square, perspective). With more buckets the perspective's king square
// also selects a feature block, which is what lets a network learn king-relative
// knowledge; a king move then requires a full refresh of both perspectives.
//
// Everything here is implemented for this project. The layout, the quantisation
// scheme, the SIMD kernels and the training pipeline are documented in
// docs/DEV4_TRAINING.md; nothing is imported from another engine.
// ---------------------------------------------------------------------------
#pragma once

#include "utilities/types.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace stockbear {
class Position;
}

namespace stockbear::nnue {

// Upper bounds. A network larger than this is rejected at load time instead of
// overflowing the fixed-size accumulator.
inline constexpr int MaxL1 = 256;
inline constexpr int MaxL2 = 64;
inline constexpr int MaxBuckets = 64;
inline constexpr int MaxFeatures = MaxBuckets * 768;

// The incrementally maintained first-layer pre-activation for both
// perspectives. `v[p][i]` is the sum of the weights of the active features of
// perspective p, plus the bias.
struct Accumulator {
    std::int16_t v[ColorNB][MaxL1];
};

// A loaded network. `w1` is feature-major (each feature owns `l1` contiguous
// int16 weights) so that adding a feature is a contiguous vector add.
struct Network {
    int kingBuckets = 1;
    int l1 = 0;
    int l2 = 0;
    int inputCount = 0;
    int actShift = 0;    // acc >> actShift, then clip to [0, 127]
    int h2Shift = 12;    // layer-2 output >> h2Shift, then clip to [0, 127]
    int outShift = 6;    // final int32 output >> outShift = centipawns
    std::vector<std::int16_t> w1;  // inputCount * l1
    std::vector<std::int32_t> b1;  // l1
    std::vector<std::int16_t> w2;  // l2 * (2 * l1), perspective 0 rows first
    std::vector<std::int32_t> b2;  // l2
    std::vector<std::int16_t> w3;  // l2
    std::int32_t b3 = 0;
    std::uint64_t checksum = 0;

    std::size_t parameter_count() const {
        return w1.size() + b1.size() + w2.size() + b2.size() + w3.size() + 1;
    }
};

// Serialised form (see docs/DEV4_TRAINING.md):
//   magic "SBNN" | u16 version | u16 kingBuckets | u16 l1 | u16 l2
//   u16 actShift | u16 h2Shift | u16 outShift | u16 reserved
//   i16 w1[inputCount * l1] | i32 b1[l1]
//   i16 w2[l2 * 2 * l1]     | i32 b2[l2]
//   i16 w3[l2]              | i32 b3
// All values little-endian. The loader validates every dimension and rejects
// truncated or oversized data instead of reading past the end.
inline constexpr std::size_t SerializedHeaderBytes = 20; // 4 magic + 8 uint16 fields

std::uint64_t features_checksum(const Network& net);
Network parse_network(const void* data, std::size_t size, std::string* error);
Network parse_network_file(const std::string& path, std::string* error);
std::vector<std::uint8_t> serialize_network(const Network& net);

// The process-wide active network, or nullptr when the classical evaluation is
// in charge. `install_network` takes a copy; `clear_network` releases it.
bool install_network(Network net, std::string* error);
void clear_network();
const Network* active_network();
// Loads the network that was compiled into this binary. Returns false (leaving
// the classical evaluation active) when the build has no embedded network.
bool install_embedded_network(std::string* error);
bool embedded_network_available();
// A one-line identity such as "SBNN-1x128x32 12345678" for bench/uci output.
std::string network_identity();

int king_bucket(Square relativeKing, int buckets);

// Full recomputation of both perspectives from the board.
void refresh(const Position& pos, Accumulator& acc);
// Builds the feature list of one perspective (used by tests and the feature
// dump used to validate the Python training mirror).
void feature_list(const Position& pos, Color perspective, std::vector<int>& out);

// Incremental updates, in the same places where the classical accumulators are
// updated. With one king bucket these cannot depend on the king square.
void add_piece(Accumulator& acc, const Position& pos, Piece pc, Square sq);
void subtract_piece(Accumulator& acc, const Position& pos, Piece pc, Square sq);

// Applies the halfmove clock / repetition scaling? No - the raw static score.
// Returns centipawns from the point of view of the side to move, clamped below
// mate values.
int evaluate(const Position& pos, const Accumulator& acc);

// The same evaluation from the raw inputs, without an incremental accumulator.
// Used by tests to prove the incremental path equals a from-scratch build.
int evaluate_from_scratch(const Position& pos);

} // namespace stockbear::nnue
