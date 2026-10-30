#pragma once
#include "chess/move.hpp"
#include <cstddef>
#include <cstdint>
#include <vector>

namespace stockbear {
enum class Bound : std::uint8_t { None, Exact, Lower, Upper };

struct TTEntry {
    Key key = 0;
    std::uint64_t rule50 = 0;
    Key historyContext = 0;
    Move move = MOVE_NONE;
    std::int16_t value = 0;  // mate values normalized to the stored position
    std::int16_t depth = -1;
    Bound bound = Bound::None;
    std::uint8_t extensions = 0;
    std::uint16_t generation = 0;
};

// Single-search-thread table. The UCI controller joins the search before any
// resize or clear, so it needs no atomics or platform-specific operations.
class TranspositionTable {
public:
    explicit TranspositionTable(std::size_t megabytes = 16) { resize(megabytes); }
    void resize(std::size_t megabytes);
    void clear();
    void new_search();
    const TTEntry* probe(Key key, std::uint64_t rule50, Key context, int extensions) const;
    void store(Key key, std::uint64_t rule50, Key context, int extensions,
               Move move, int value, int depth, Bound bound, int ply);
    int hashfull() const; // per mille, sampled from this search generation
    std::size_t allocated_bytes() const { return entries_.size() * sizeof(TTEntry); }
    static int value_from_table(int value, int ply);
private:
    std::vector<TTEntry> entries_;
    std::uint16_t generation_ = 0;
};
}
