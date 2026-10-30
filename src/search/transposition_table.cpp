#include "search/transposition_table.hpp"
#include <algorithm>
#include <limits>
#include <stdexcept>

namespace stockbear {
void TranspositionTable::resize(std::size_t megabytes) {
    if (megabytes < 1 || megabytes > 512) throw std::invalid_argument("Hash must be 1..512 MB");
    const std::size_t maxEntries = megabytes * std::size_t(1024 * 1024) / sizeof(TTEntry);
    // Use nearly the full requested budget instead of rounding down to a
    // power of two. Allocation remains within the advertised MB limit.
    // Allocate before replacing the old table, so failure preserves it.
    std::vector<TTEntry> replacement(maxEntries);
    entries_.swap(replacement);
    generation_ = 0;
}
void TranspositionTable::clear() {
    std::fill(entries_.begin(), entries_.end(), TTEntry{});
    generation_ = 0;
}
void TranspositionTable::new_search() {
    if (++generation_ == 0) { clear(); generation_ = 1; }
}
const TTEntry* TranspositionTable::probe(Key key, std::uint64_t rule50, Key context, int extensions) const {
    const Key index = key ^ context ^ (Key(extensions) * 0x9E3779B97F4A7C15ULL);
    const TTEntry& e = entries_[std::size_t(index % entries_.size())];
    return e.bound != Bound::None && e.key == key && e.rule50 == rule50 &&
           e.historyContext == context && e.extensions == extensions ? &e : nullptr;
}
int TranspositionTable::value_from_table(int value, int ply) {
    if (value >= MATE_BOUND) return value - ply;
    if (value <= -MATE_BOUND) return value + ply;
    return value;
}
void TranspositionTable::store(Key key, std::uint64_t rule50, Key context, int extensions,
                               Move move, int value, int depth, Bound bound, int ply) {
    const Key index = key ^ context ^ (Key(extensions) * 0x9E3779B97F4A7C15ULL);
    TTEntry& old = entries_[std::size_t(index % entries_.size())];
    // Prefer deeper current-generation entries, except always replace a match
    // (a new bound/move for this exact position is more useful).
    if (old.bound != Bound::None && (old.key != key || old.historyContext != context || old.extensions != extensions) && old.generation == generation_
        && old.depth > depth + 2) return;
    if (value >= MATE_BOUND) value += ply;
    else if (value <= -MATE_BOUND) value -= ply;
    old.key = key;
    old.rule50 = rule50;
    old.historyContext = context;
    old.extensions = static_cast<std::uint8_t>(extensions);
    old.move = move;
    old.value = static_cast<std::int16_t>(value);
    old.depth = static_cast<std::int16_t>(depth);
    old.bound = bound;
    old.generation = generation_;
}
int TranspositionTable::hashfull() const {
    const std::size_t sample = std::min<std::size_t>(1000, entries_.size());
    int used = 0;
    for (std::size_t i = 0; i < sample; ++i)
        if (entries_[i].bound != Bound::None && entries_[i].generation == generation_) ++used;
    return int(used * 1000 / sample);
}
}
