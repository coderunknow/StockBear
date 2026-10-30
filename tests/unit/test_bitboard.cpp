#include "test.hpp"
#include "chess/bitboard.hpp"
#include <random>
using namespace stockbear;
namespace {
Bitboard ray(Square s, Bitboard occ, bool bishop) {
    const int dirs[8][2] = {{1,0},{-1,0},{0,1},{0,-1},{1,1},{1,-1},{-1,1},{-1,-1}};
    Bitboard out = 0;
    for (int i = bishop ? 4 : 0; i < (bishop ? 8 : 4); ++i) {
        int f = file_of(s) + dirs[i][0], r = rank_of(s) + dirs[i][1];
        while (f >= 0 && f < 8 && r >= 0 && r < 8) {
            const Bitboard b = square_bb(make_square(f,r)); out |= b;
            if (occ & b) break;
            f += dirs[i][0]; r += dirs[i][1];
        }
    }
    return out;
}
}
TEST(unit, magic_attacks_against_independent_rays) {
    init_bitboards();
    std::mt19937_64 rng(0x4512);
    for (int s = 0; s < 64; ++s) for (int i = 0; i < 500; ++i) {
        const Bitboard occ = rng();
        CHECK_EQ(rook_attacks_bb(Square(s),occ), ray(Square(s),occ,false));
        CHECK_EQ(bishop_attacks_bb(Square(s),occ), ray(Square(s),occ,true));
    }
}
TEST(unit, geometry_and_leapers) {
    init_bitboards();
    CHECK_EQ(popcount(KnightAttacksBB[SQ_A1]), 2);
    CHECK_EQ(popcount(KingAttacksBB[SQ_E4]), 8);
    CHECK_EQ(PawnAttacksBB[White][SQ_A2], square_bb(SQ_B3));
    CHECK_EQ(PawnAttacksBB[Black][SQ_H7], square_bb(SQ_G6));
    CHECK_EQ(popcount(BetweenBB[SQ_A1][SQ_A8]), 6);
    CHECK_EQ(BetweenBB[SQ_A1][SQ_B3], Bitboard(0));
    CHECK(aligned(SQ_A1, SQ_H8, SQ_C3));
    CHECK(!aligned(SQ_A1, SQ_H8, SQ_C4));
}
