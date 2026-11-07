#include "search/transposition_table.hpp"
#ifdef __linux__
#include <cstdint>
#include <sys/mman.h>
#endif
#include "utilities/types.hpp"
#include <algorithm>
#include <stdexcept>

namespace stockbear {
#ifdef SB_TT_IDENTITY_DEBUG
TTIdentityStats ttIdentityStats;
#endif
namespace {
// Mix the position key with the search context so that contexts which produce
// incompatible scores are physically separated in the table.
inline Key index_of(Key key, Key context, int extensions) {
    Key h = key ^ context ^ (Key(std::uint64_t(extensions) * 0x9E3779B97F4A7C15ULL));
    h ^= h >> 33;
    h *= 0xFF51AFD7ED558CCDULL;
    h ^= h >> 29;
    return h;
}
}

void TranspositionTable::resize(std::size_t megabytes) {
    if (megabytes < 1 || megabytes > 512) throw std::invalid_argument("Hash must be 1..512 MB");
    const std::size_t wanted = megabytes * std::size_t(1024 * 1024) / sizeof(Bucket);
    // Allocate before replacing the old table so that a failed allocation
    // leaves the engine with a working table.
    std::vector<Bucket> replacement(std::max<std::size_t>(1, wanted));
    buckets_.swap(replacement);
    generation_ = 1;
#if defined(__linux__) && defined(MADV_HUGEPAGE)
    // Ask for transparent huge pages on the aligned 2 MiB subrange of the
    // table: random TT probes otherwise thrash the TLB with 4 KiB pages.
    // Purely an allocation hint; the table contents and behaviour are
    // unchanged (bench signature stays bit-identical).
    if (buckets_.size() * sizeof(Bucket) >= 2 * 1024 * 1024) {
        const std::uintptr_t base = reinterpret_cast<std::uintptr_t>(buckets_.data());
        const std::size_t bytes = buckets_.size() * sizeof(Bucket);
        const std::uintptr_t aligned =
            (base + 2 * 1024 * 1024 - 1) & ~static_cast<std::uintptr_t>(2 * 1024 * 1024 - 1);
        const std::size_t offset = static_cast<std::size_t>(aligned - base);
        if (offset < bytes)
            (void)madvise(reinterpret_cast<void*>(aligned), bytes - offset, MADV_HUGEPAGE);
    }
#endif
}

void TranspositionTable::clear() {
    std::fill(buckets_.begin(), buckets_.end(), Bucket{});
    generation_ = 1;
}

void TranspositionTable::new_search() {
    if (++generation_ == 0) { clear(); generation_ = 1; }
}

TranspositionTable::Bucket& TranspositionTable::bucket_for(Key key, Key context, int extensions) {
    return buckets_[std::size_t(index_of(key, context, extensions)) % buckets_.size()];
}

const TranspositionTable::Bucket& TranspositionTable::bucket_for(Key key, Key context,
                                                                int extensions) const {
    return buckets_[std::size_t(index_of(key, context, extensions)) % buckets_.size()];
}

const TTEntry* TranspositionTable::probe(Key key, std::uint64_t rule50, Key context,
                                         int extensions) const {
    const Bucket& bucket = bucket_for(key, context, extensions);
    for (const TTEntry& entry : bucket.entry)
        if (entry.bound != Bound::None && entry.key == key && entry.rule50 == rule50 &&
            entry.historyContext == context && entry.extensions == extensions) {
#ifdef SB_TT_IDENTITY_DEBUG
            ++ttIdentityStats.probes;
            ++ttIdentityStats.hits;
#endif
            return &entry;
        }
#ifdef SB_TT_IDENTITY_DEBUG
    // No behaviour change: the probe still returns nullptr. This only records
    // WHICH identity field prevented a match, so the value of each field can be
    // judged from measurement instead of assumption.
    ++ttIdentityStats.probes;
    diag_scan_extension_buckets(key, rule50, context, extensions, diagDepth_);
    for (const TTEntry& entry : bucket.entry) {
        if (entry.bound == Bound::None || entry.key != key) continue;
        if (entry.rule50 == rule50 && entry.historyContext == context &&
            entry.extensions != extensions)
            ++ttIdentityStats.missExtOnly;
        else if (entry.rule50 != rule50 && entry.historyContext == context &&
                 entry.extensions == extensions)
            ++ttIdentityStats.missRule50Only;
        else if (entry.rule50 == rule50 && entry.historyContext != context &&
                 entry.extensions == extensions)
            ++ttIdentityStats.missContextOnly;
    }
#endif
    return nullptr;
}

int TranspositionTable::value_from_table(int value, int ply) {
    if (value >= MATE_BOUND) return value - ply;
    if (value <= -MATE_BOUND) return value + ply;
    return value;
}

int TranspositionTable::value_to_table(int value, int ply) {
    if (value >= MATE_BOUND) return value + ply;
    if (value <= -MATE_BOUND) return value - ply;
    return value;
}

void TranspositionTable::store(Key key, std::uint64_t rule50, Key context, int extensions,
                               Move move, int value, int depth, Bound bound, int ply, int eval) {
    Bucket& bucket = bucket_for(key, context, extensions);
    TTEntry* replace = nullptr;
    // Prefer an exact match (more information about this very position), then
    // an empty or stale slot, then the shallowest entry of the oldest
    // generation.
    for (TTEntry& entry : bucket.entry) {
        if (entry.bound != Bound::None && entry.key == key && entry.rule50 == rule50 &&
            entry.historyContext == context && entry.extensions == extensions) {
            replace = &entry;
            break;
        }
        if (replace == nullptr || entry.generation < replace->generation ||
            (entry.generation == replace->generation && entry.depth < replace->depth))
            replace = &entry;
    }
    if (replace->bound != Bound::None && replace->generation == generation_ &&
        replace->depth > depth + 3 && replace->key != key)
        return; // keep a much deeper result from the current search

    if (move == MOVE_NONE && replace->key == key && replace->historyContext == context &&
        replace->extensions == extensions)
        move = replace->move; // never lose a usable hash move

    replace->key = key;
    replace->rule50 = rule50;
    replace->historyContext = context;
    replace->extensions = static_cast<std::uint8_t>(extensions);
    replace->move = move;
    replace->value = static_cast<std::int16_t>(value_to_table(value, ply));
    replace->depth = static_cast<std::int16_t>(std::min(depth, 1000));
    replace->bound = bound;
    // A bound-only store keeps any static evaluation that is already known for
    // this slot, so an eval-less store cannot erase a usable one.
    if (eval != VALUE_NONE)
        replace->eval = static_cast<std::int16_t>(std::max(-VALUE_KNOWN_WIN, std::min(VALUE_KNOWN_WIN, eval)));
    else if (!(replace->key == key && replace->rule50 == rule50 &&
               replace->historyContext == context && replace->extensions == extensions))
        replace->eval = static_cast<std::int16_t>(VALUE_NONE);
    replace->generation = generation_;
}

#ifdef SB_TT_IDENTITY_DEBUG
void TranspositionTable::diag_scan_extension_buckets(Key key, std::uint64_t rule50,
                                                     Key context, int extensions,
                                                     int depth) const {
    for (int e = 0; e <= 8; ++e) {
        if (e == extensions) continue;
        const Bucket& b = bucket_for(key, context, e);
        for (const TTEntry& entry : b.entry) {
            if (entry.bound == Bound::None || entry.key != key) continue;
            if (entry.rule50 != rule50 || entry.historyContext != context) continue;
            ++ttIdentityStats.missExtOtherBucket;
            if (entry.depth >= depth) ++ttIdentityStats.missExtOtherBucketDeep;
            return; // count once per probe, not once per sibling slot
        }
    }
}
#endif

int TranspositionTable::hashfull() const {
    const std::size_t sample = std::min<std::size_t>(1000, buckets_.size());
    int used = 0;
    for (std::size_t i = 0; i < sample; ++i)
        for (const TTEntry& entry : buckets_[i].entry)
            if (entry.bound != Bound::None && entry.generation == generation_) ++used;
    const int slots = int(sample) * BucketSize;
    return slots == 0 ? 0 : int(std::int64_t(used) * 1000 / slots);
}
}
