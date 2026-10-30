// ---------------------------------------------------------------------------
// gen_magics.cpp - development tool that generates the magic multipliers used
// by StockBear's magic-bitboard slider attack tables.
//
// The generated constants are checked into src/chess/magic_numbers.inc so the
// engine itself never has to search for them at start-up. This tool exists so
// the constants are reproducible: run it again and compare the output.
//
// Build:  cmake --build build --target stockbear_genmagics
// Run:    ./build/stockbear_genmagics
//
// The search is the classic trial-multiply approach: for every square we try
// sparse random multipliers until (occupancy * magic) >> (64 - bits) maps all
// occupancy subsets of the square's relevant mask to unique indices.
// ---------------------------------------------------------------------------

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <vector>

using Bitboard = uint64_t;

namespace {

constexpr int SQ_NB = 64;

int popcount(Bitboard b) {
    int count = 0;
    while (b) { b &= b - 1; ++count; }
    return count;
}

inline int file_of(int sq) { return sq & 7; }
inline int rank_of(int sq) { return sq >> 3; }
inline int make_sq(int f, int r) { return r * 8 + f; }

// Reference (slow) slider attacks by ray-scanning; used to build tables and to
// validate the magics we find.
Bitboard ray_attacks(int sq, Bitboard blockers, bool diagonal) {
    Bitboard result = 0;
    const int dirs[8][2] = {
        { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 },   // rook directions
        { 1, 1 }, { 1, -1 }, { -1, 1 }, { -1, -1 }, // bishop directions
    };
    const int start = diagonal ? 4 : 0;
    const int end   = diagonal ? 8 : 4;
    for (int d = start; d < end; ++d) {
        int f = file_of(sq) + dirs[d][0];
        int r = rank_of(sq) + dirs[d][1];
        while (f >= 0 && f < 8 && r >= 0 && r < 8) {
            int to = make_sq(f, r);
            result |= Bitboard(1) << to;
            if (blockers & (Bitboard(1) << to)) break;
            f += dirs[d][0];
            r += dirs[d][1];
        }
    }
    return result;
}

Bitboard rook_attacks_ref(int sq, Bitboard blockers)   { return ray_attacks(sq, blockers, false); }
Bitboard bishop_attacks_ref(int sq, Bitboard blockers) { return ray_attacks(sq, blockers, true); }

// Relevant occupancy mask: ray squares excluding the outermost square of each
// ray (a blocker on the board edge never changes the attack set). The edge
// masks are only applied when the slider does not sit on that edge itself -
// otherwise e.g. a rook on a4 would lose its whole a-file mask.
Bitboard slider_mask(int sq, bool diagonal) {
    const Bitboard notA = ~Bitboard(0x0101010101010101ULL);
    const Bitboard notH = ~Bitboard(0x8080808080808080ULL);
    const Bitboard not1 = ~Bitboard(0x00000000000000FFULL);
    const Bitboard not8 = ~Bitboard(0xFF00000000000000ULL);
    Bitboard mask = ray_attacks(sq, 0, diagonal);
    if (diagonal) {
        mask &= notA & notH & not1 & not8;
    } else {
        if (file_of(sq) != 0) mask &= notA;
        if (file_of(sq) != 7) mask &= notH;
        if (rank_of(sq) != 0) mask &= not1;
        if (rank_of(sq) != 7) mask &= not8;
    }
    return mask;
}

// Deterministic PRNG (splitmix64) so runs are reproducible.
struct Rng {
    uint64_t s;
    explicit Rng(uint64_t seed) : s(seed) {}
    uint64_t next() {
        s += 0x9E3779B97F4A7C15ULL;
        uint64_t z = s;
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
        return z ^ (z >> 31);
    }
    // Sparse random number (~10% bit density), the classic candidate shape.
    uint64_t sparse() { return next() & next() & next(); }
};

// Enumerate all subsets of `mask` (Carry-Rippler trick).
std::vector<Bitboard> subsets_of(Bitboard mask) {
    std::vector<Bitboard> out;
    Bitboard occ = 0;
    do {
        out.push_back(occ);
        occ = (occ - mask) & mask;
    } while (occ);
    return out;
}

// Find a magic multiplier for one square. Returns 0 on failure (should not
// happen with enough trials).
Bitboard find_magic(int sq, bool diagonal, Rng& rng, int max_trials = 100000000) {
    const Bitboard mask = slider_mask(sq, diagonal);
    const int bits = popcount(mask);
    const int shift = 64 - bits;
    const std::vector<Bitboard> occ = subsets_of(mask);

    std::vector<Bitboard> used(size_t(1) << bits, 0);
    std::vector<char> occupied(size_t(1) << bits, 0);

    for (int trial = 0; trial < max_trials; ++trial) {
        Bitboard magic = rng.sparse();
        // Fast rejection: the candidate must spread the top bits of the mask.
        if (popcount((mask * magic) & 0xFF00000000000000ULL) < 6) continue;

        bool fail = false;
        std::fill(occupied.begin(), occupied.end(), char(0));
        for (size_t i = 0; i < occ.size() && !fail; ++i) {
            size_t idx = size_t((occ[i] * magic) >> shift);
            Bitboard attack = diagonal ? bishop_attacks_ref(sq, occ[i])
                                       : rook_attacks_ref(sq, occ[i]);
            if (!occupied[idx]) {
                occupied[idx] = 1;
                used[idx] = attack;
            } else if (used[idx] != attack) {
                fail = true; // destructive collision
            }
        }
        if (!fail) return magic;
    }
    return 0;
}

void print_array(const char* name, const Bitboard v[SQ_NB]) {
    std::printf("%s\n", name);
    for (int i = 0; i < SQ_NB; ++i) {
        if (i % 2 == 0) std::printf("   ");
        std::printf("0x%016llXULL,", static_cast<unsigned long long>(v[i]));
        if (i % 2 == 1) std::printf("\n"); else std::printf(" ");
    }
    std::printf("\n");
}

} // namespace

int main() {
    Rng rng(0x5EED1234ULL); // fixed seed -> reproducible constants

    Bitboard rookMagics[SQ_NB];
    Bitboard bishopMagics[SQ_NB];

    for (int sq = 0; sq < SQ_NB; ++sq) {
        rookMagics[sq] = find_magic(sq, false, rng);
        bishopMagics[sq] = find_magic(sq, true, rng);
        if (rookMagics[sq] == 0 || bishopMagics[sq] == 0) {
            std::fprintf(stderr, "FAILED to find magic for square %d\n", sq);
            return 1;
        }
    }

    std::printf("// Generated by tools/gen_magics.cpp (seed 0x5EED1234, splitmix64).\n");
    std::printf("// Do not edit by hand; regenerate instead.\n\n");
    print_array("constexpr Bitboard RookMagicNumbers[64] = {", rookMagics);
    std::printf("};\n\n");
    print_array("constexpr Bitboard BishopMagicNumbers[64] = {", bishopMagics);
    std::printf("};\n");
    return 0;
}
