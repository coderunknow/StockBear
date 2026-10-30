// StockBear's own lightweight evaluation. The table formulae and weights are
// intentionally simple and hand chosen; this is not a trained neural network.
#include "evaluation/evaluation.hpp"
#include "chess/position.hpp"
#include <algorithm>
#include <cstdlib>
#include <mutex>

namespace stockbear {

const int PieceValueMg[PieceTypeNB] = {0, 100, 320, 335, 500, 975, 0};
const int PieceValueEg[PieceTypeNB] = {0, 120, 305, 330, 520, 950, 0};
int PieceSquareMg[PieceTypeNB][SQ_NB] = {};
int PieceSquareEg[PieceTypeNB][SQ_NB] = {};

void init_evaluation() {
    static std::once_flag once;
    std::call_once(once, [] {
        for (int idx = 0; idx < 64; ++idx) {
            const int f = idx % 8;
            const int rank = 7 - idx / 8; // table is rank 8 first, white view
            const int fileCenter = std::min(f, 7 - f);
            const int rankCenter = std::min(rank, 7 - rank);
            const int center = fileCenter + rankCenter;
            PieceSquareMg[Pawn][idx]   = rank * 5 + fileCenter * 3;
            PieceSquareEg[Pawn][idx]   = rank * 9 + fileCenter * 2;
            PieceSquareMg[Knight][idx] = center * 9 - 24;
            PieceSquareEg[Knight][idx] = center * 6 - 18;
            PieceSquareMg[Bishop][idx] = center * 5 - 12;
            PieceSquareEg[Bishop][idx] = center * 4 - 10;
            PieceSquareMg[Rook][idx]   = rank * 2 + fileCenter;
            PieceSquareEg[Rook][idx]   = center * 2;
            PieceSquareMg[Queen][idx]  = center * 2 - 6;
            PieceSquareEg[Queen][idx]  = center * 4 - 12;
            // Middlegame kings prefer their back rank and the wings; in the
            // endgame they seek centralization and become an active piece.
            PieceSquareMg[King][idx]   = -rank * 8 - fileCenter * 5;
            PieceSquareEg[King][idx]   = center * 10 - 30;
        }
    });
}

namespace {
struct Score { int mg = 0; int eg = 0; };

Score features(const Position& p, Color us) {
    const Color them = ~us;
    const Bitboard ours = p.pieces(us), pawns = p.pieces(us, Pawn);
    const Bitboard enemyPawns = p.pieces(them, Pawn);
    Score out;
    if (p.count(us, Bishop) >= 2) { out.mg += 28; out.eg += 38; }

    Bitboard b = pawns;
    while (b) {
        const Square s = pop_lsb(b);
        const int f = file_of(s);
        if (!(pawns & AdjacentFilesBB[f])) { out.mg -= 11; out.eg -= 9; }
        if (!(enemyPawns & PassedPawnMaskBB[us][s])) {
            // A doubled pawn behind another is not an independently useful
            // passed pawn; award only the leading pawn.
            if (!(pawns & FileBB[f] & ForwardRanksBB[us][rank_of(s)])) {
                const int advance = us == White ? rank_of(s) : 7 - rank_of(s);
                out.mg += advance * advance * 2;
                out.eg += advance * advance * 5;
            }
        }
    }

    // Penalize each extra pawn on a file once, not once per pair.
    for (int f = 0; f < 8; ++f) {
        const int extra = std::max(0, popcount(pawns & FileBB[f]) - 1);
        out.mg -= 8 * extra;
        out.eg -= 12 * extra;
    }

    // Count geometrically available squares as a cheap activity proxy.
    for (PieceType pt : {Knight, Bishop, Rook, Queen}) {
        b = p.pieces(us, pt);
        while (b) {
            Square s = pop_lsb(b);
            const int mobility = popcount(attacks_bb(pt, us, s, p.pieces()) & ~ours);
            static constexpr int mgWeight[] = {0, 0, 4, 4, 2, 1, 0};
            static constexpr int egWeight[] = {0, 0, 3, 4, 3, 2, 0};
            out.mg += mobility * mgWeight[pt];
            out.eg += mobility * egWeight[pt];
            if (pt == Rook) {
                const Bitboard file = FileBB[file_of(s)];
                if (!(pawns & file)) {
                    if (!(enemyPawns & file)) { out.mg += 20; out.eg += 12; }
                    else                     { out.mg += 10; out.eg += 6; }
                }
            }
        }
    }

    // Pawn shield and enemy activity around the king. Kept in the middlegame
    // component so its contribution naturally fades as material comes off.
    const Square k = p.king_square(us);
    const int frontRank = rank_of(k) + (us == White ? 1 : -1);
    if (frontRank >= 0 && frontRank < 8) {
        const Bitboard shieldFiles = FileBB[file_of(k)] | AdjacentFilesBB[file_of(k)];
        out.mg += 8 * popcount(pawns & shieldFiles & RankBB[frontRank]);
    }
    const Bitboard zone = KingZoneBB[us][k];
    for (PieceType pt : {Pawn, Knight, Bishop, Rook, Queen}) {
        b = p.pieces(them, pt);
        while (b) {
            Square s = pop_lsb(b);
            int hits = popcount(attacks_bb(pt, them, s, p.pieces()) & zone);
            static constexpr int weight[] = {0, 2, 3, 3, 3, 5, 0};
            out.mg -= hits * weight[pt];
        }
    }
    return out;
}
}

int evaluate(const Position& p) {
    const Score w = features(p, White), b = features(p, Black);
    const int mg = p.acc_mg(White) - p.acc_mg(Black) + w.mg - b.mg;
    const int eg = p.acc_eg(White) - p.acc_eg(Black) + w.eg - b.eg;
    int phase = 0;
    for (Color c : {White, Black}) {
        phase += p.count(c, Knight) + p.count(c, Bishop);
        phase += 2 * p.count(c, Rook) + 4 * p.count(c, Queen);
    }
    phase = std::min(24, phase);
    const int score = std::clamp((mg * phase + eg * (24 - phase)) / 24,
                                 -VALUE_KNOWN_WIN, VALUE_KNOWN_WIN);
    return p.side_to_move() == White ? score : -score;
}
}
