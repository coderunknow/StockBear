#pragma once
#include "chess/move.hpp"
#include <cstddef>
#include <cstdint>
#include <vector>

namespace stockbear {
enum class Bound : std::uint8_t { None, Exact, Lower, Upper };

// One table slot. The engine is single-threaded, so no atomic access is needed;
// the UCI controller joins the search worker before any resize or clear.
struct TTEntry {
    // Packed to 32 bytes so a two-entry bucket occupies exactly one 64-byte
    // cache line (was 40 bytes / 80-byte bucket). rule50 is clamped to 16 bits:
    // it counts halfmoves since the last pawn move or capture and cannot
    // exceed the game length in any real search (max-plies 240).
    Key key = 0;
    Key historyContext = 0;
    std::uint16_t rule50 = 0;
    Move move = MOVE_NONE;
    std::int16_t value = 0;   // mate values normalized to the stored position
    std::int16_t eval = 0;    // static evaluation, when the search stored one
    std::int16_t depth = -1;
    Bound bound = Bound::None;
    std::uint8_t extensions = 0;
    std::uint8_t generation = 0;
};
static_assert(sizeof(TTEntry) == 32, "TTEntry must fit one cache line per bucket");

// Two-way bucketed transposition table.
//
// Entries are only reusable when the stored position matches exactly: the full
// Zobrist key, plus the draw and extension context that the search score
// depends on. That conservative policy keeps draw scores and mate distances
// sound at the price of a lower hit rate than a plain depth-preferred table.
class TranspositionTable {
public:
    explicit TranspositionTable(std::size_t megabytes = 16) { resize(megabytes); }
    void resize(std::size_t megabytes);
    void clear();
    void new_search();
    const TTEntry* probe(Key key, std::uint64_t rule50, Key context, int extensions) const;
    void store(Key key, std::uint64_t rule50, Key context, int extensions,
               Move move, int value, int depth, Bound bound, int ply,
               int eval = VALUE_NONE);
    int hashfull() const; // per mille over the whole table
    std::size_t allocated_bytes() const { return buckets_.size() * sizeof(Bucket); }
    static int value_from_table(int value, int ply);
    static int value_to_table(int value, int ply);

private:
    static constexpr int BucketSize = 2;
    struct Bucket {
        TTEntry entry[BucketSize];
    };
    Bucket& bucket_for(Key key, Key context, int extensions);
    const Bucket& bucket_for(Key key, Key context, int extensions) const;

    std::vector<Bucket> buckets_;
    std::uint8_t generation_ = 1;
};
}
