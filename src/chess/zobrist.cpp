// ---------------------------------------------------------------------------
// zobrist.cpp - Zobrist key initialization.
// ---------------------------------------------------------------------------
#include "chess/zobrist.hpp"
#include <mutex>

namespace stockbear {

namespace {

// splitmix64: high quality, tiny, deterministic. The seed is a fixed constant
// so that hash keys never change between runs or platforms.
struct SplitMix64 {
    std::uint64_t state;
    explicit SplitMix64(std::uint64_t seed) : state(seed) {}
    std::uint64_t next() {
        state += 0x9E3779B97F4A7C15ULL;
        std::uint64_t z = state;
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
        return z ^ (z >> 31);
    }
};

} // namespace

namespace Zobrist {

Key psq[PieceNB][SQ_NB];
Key side;
Key castling[16];
Key epFile[FileNB];

Key context_seed(Key key) {
    key += 0x9E3779B97F4A7C15ULL;
    key = (key ^ (key >> 30)) * 0xBF58476D1CE4E5B9ULL;
    key = (key ^ (key >> 27)) * 0x94D049BB133111EBULL;
    return key ^ (key >> 31);
}
Key context_next(Key previous, Key key) {
    return ((previous << 7) | (previous >> 57)) ^ context_seed(key);
}

void init() {
    static std::once_flag once;
    std::call_once(once, [] {

    SplitMix64 rng(0x570C8BEA7A9E3D1FULL); // "StockBear" seed, arbitrary constant

    for (int p = 0; p < PieceNB; ++p)
        for (int s = 0; s < SQ_NB; ++s)
            psq[p][s] = rng.next();

    side = rng.next();
    for (int i = 0; i < 16; ++i)
        castling[i] = rng.next();
    for (int f = 0; f < FileNB; ++f)
        epFile[f] = rng.next();
    });
}

} // namespace Zobrist

} // namespace stockbear
