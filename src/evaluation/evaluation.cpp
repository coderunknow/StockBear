// StockBear's own lightweight evaluation. Every number it uses lives in the
// parameter table (evaluation/eval_params.hpp); the values shipped in the
// default table are the hand-selected dev2 set, and dev3 replaces them with a
// tuned set produced by `scripts/tune_eval.py` from recorded games.
//
// The evaluation is deliberately linear in its parameters, which is what makes
// offline tuning possible: `eval_breakdown()` returns the per-parameter counts
// that `evaluate()` multiplies by the active values, and a test asserts the two
// agree on every recorded position.
#include "evaluation/evaluation.hpp"
#include "chess/position.hpp"
#include <algorithm>
#include <cstdlib>
#include <mutex>

namespace stockbear {

int PieceValueMg[PieceTypeNB] = {0, 100, 320, 335, 500, 975, 0};
int PieceValueEg[PieceTypeNB] = {0, 120, 305, 330, 520, 950, 0};
int PieceSquareMg[PieceTypeNB][SQ_NB] = {};
int PieceSquareEg[PieceTypeNB][SQ_NB] = {};

namespace {

void build_tables(const EvalParams& params) {
    const auto value = [&](EvalParamId id, bool eg) {
        return eg ? params.eg[std::size_t(id)] : params.mg[std::size_t(id)];
    };
    PieceValueMg[Pawn]   = value(MatPawn, false);
    PieceValueEg[Pawn]   = value(MatPawn, true);
    PieceValueMg[Knight] = value(MatKnight, false);
    PieceValueEg[Knight] = value(MatKnight, true);
    PieceValueMg[Bishop] = value(MatBishop, false);
    PieceValueEg[Bishop] = value(MatBishop, true);
    PieceValueMg[Rook]   = value(MatRook, false);
    PieceValueEg[Rook]   = value(MatRook, true);
    PieceValueMg[Queen]  = value(MatQueen, false);
    PieceValueEg[Queen]  = value(MatQueen, true);
    PieceValueMg[King] = PieceValueEg[King] = 0;

    for (int idx = 0; idx < 64; ++idx) {
        const int f = idx % 8;
        const int rank = 7 - idx / 8; // table is rank 8 first, white view
        const int fileCenter = std::min(f, 7 - f);
        const int rankCenter = std::min(rank, 7 - rank);
        const int center = fileCenter + rankCenter;
        PieceSquareMg[Pawn][idx]   = rank * value(PstPawnRank, false) + fileCenter * value(PstPawnFile, false);
        PieceSquareEg[Pawn][idx]   = rank * value(PstPawnRank, true) + fileCenter * value(PstPawnFile, true);
        PieceSquareMg[Knight][idx] = center * value(PstKnightCenter, false);
        PieceSquareEg[Knight][idx] = center * value(PstKnightCenter, true);
        PieceSquareMg[Bishop][idx] = center * value(PstBishopCenter, false);
        PieceSquareEg[Bishop][idx] = center * value(PstBishopCenter, true);
        PieceSquareMg[Rook][idx]   = rank * value(PstRookRank, false) + fileCenter * value(PstRookFile, false);
        PieceSquareEg[Rook][idx]   = center * value(PstRookCenter, true);
        PieceSquareMg[Queen][idx]  = center * value(PstQueenCenter, false);
        PieceSquareEg[Queen][idx]  = center * value(PstQueenCenter, true);
        // Middlegame kings prefer their back rank and the wings; in the endgame
        // they seek centralisation and become an active piece.
        PieceSquareMg[King][idx]   = rank * value(PstKingRank, false) + fileCenter * value(PstKingFile, false);
        PieceSquareEg[King][idx]   = center * value(PstKingCenter, true);
    }
}

int phase_of(const Position& p) {
    int phase = 0;
    for (Color c : {White, Black}) {
        phase += p.count(c, Knight) + p.count(c, Bishop);
        phase += 2 * p.count(c, Rook) + 4 * p.count(c, Queen);
    }
    return std::min(24, phase);
}

int taper(int mg, int eg, int phase) {
    return std::clamp((mg * phase + eg * (24 - phase)) / 24, -VALUE_KNOWN_WIN, VALUE_KNOWN_WIN);
}

struct Score { int mg = 0; int eg = 0; };

// The live evaluation of one side. Mirrors `accumulate_breakdown` below
// term for term; `eval_breakdown_matches_evaluate` in the unit tests is what
// keeps the two from drifting apart.
Score features(const Position& p, Color us, const EvalParams& par) {
    const Color them = ~us;
    const Bitboard ours = p.pieces(us), pawns = p.pieces(us, Pawn);
    const Bitboard enemyPawns = p.pieces(them, Pawn);
    Score out;
    const auto mgp = [&](EvalParamId id) { return par.mg[std::size_t(id)]; };
    const auto egp = [&](EvalParamId id) { return par.eg[std::size_t(id)]; };

    if (p.count(us, Bishop) >= 2) {
        out.mg += mgp(BishopPair);
        out.eg += egp(BishopPair);
    }

    Bitboard b = pawns;
    while (b) {
        const Square s = pop_lsb(b);
        const int f = file_of(s);
        if (!(pawns & AdjacentFilesBB[f])) {
            out.mg += mgp(IsolatedPawn);
            out.eg += egp(IsolatedPawn);
        }
        if (!(enemyPawns & PassedPawnMaskBB[us][s])) {
            // A doubled pawn behind another is not an independently useful
            // passed pawn; award only the leading pawn.
            if (!(pawns & FileBB[f] & ForwardRanksBB[us][rank_of(s)])) {
                const int advance = us == White ? rank_of(s) : 7 - rank_of(s);
                out.mg += advance * advance * mgp(PassedPawnAdvance);
                out.eg += advance * advance * egp(PassedPawnAdvance);
            }
        }
    }

    // Penalize each extra pawn on a file once, not once per pair.
    for (int f = 0; f < 8; ++f) {
        const int extra = std::max(0, popcount(pawns & FileBB[f]) - 1);
        out.mg += extra * mgp(DoubledPawn);
        out.eg += extra * egp(DoubledPawn);
    }

    // Count geometrically available squares as a cheap activity proxy.
    for (PieceType pt : {Knight, Bishop, Rook, Queen}) {
        b = p.pieces(us, pt);
        while (b) {
            Square s = pop_lsb(b);
            const int mobility = popcount(attacks_bb(pt, us, s, p.pieces()) & ~ours);
            EvalParamId id = MobilityKnight;
            if (pt == Bishop) id = MobilityBishop;
            else if (pt == Rook) id = MobilityRook;
            else if (pt == Queen) id = MobilityQueen;
            out.mg += mobility * mgp(id);
            out.eg += mobility * egp(id);
            if (pt == Rook) {
                const Bitboard file = FileBB[file_of(s)];
                if (!(pawns & file)) {
                    if (!(enemyPawns & file)) {
                        out.mg += mgp(RookOpenFile); out.eg += egp(RookOpenFile);
                    } else {
                        out.mg += mgp(RookSemiOpenFile); out.eg += egp(RookSemiOpenFile);
                    }
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
        out.mg += mgp(PawnShield) * popcount(pawns & shieldFiles & RankBB[frontRank]);
    }
    const Bitboard zone = KingZoneBB[us][k];
    for (PieceType pt : {Pawn, Knight, Bishop, Rook, Queen}) {
        EvalParamId id = KingDangerPawn;
        if (pt == Knight) id = KingDangerKnight;
        else if (pt == Bishop) id = KingDangerBishop;
        else if (pt == Rook) id = KingDangerRook;
        else if (pt == Queen) id = KingDangerQueen;
        b = p.pieces(them, pt);
        while (b) {
            Square s = pop_lsb(b);
            const int hits = popcount(attacks_bb(pt, them, s, p.pieces()) & zone);
            out.mg -= hits * mgp(id);
        }
    }
    return out;
}

void add_pst_counts(EvalBreakdown& bd, PieceType pt, int idx, int sign) {
    const int f = idx % 8;
    const int rank = 7 - idx / 8;
    const int fileCenter = std::min(f, 7 - f);
    const int center = fileCenter + std::min(rank, 7 - rank);
    const auto add = [&](EvalParamId id, int count) {
        bd.mg[std::size_t(id)] += sign * count;
        bd.eg[std::size_t(id)] += sign * count;
    };
    switch (pt) {
    case Pawn:
        add(MatPawn, 1);
        add(PstPawnRank, rank);
        add(PstPawnFile, fileCenter);
        break;
    case Knight:
        add(MatKnight, 1);
        add(PstKnightCenter, center);
        break;
    case Bishop:
        add(MatBishop, 1);
        add(PstBishopCenter, center);
        break;
    case Rook:
        add(MatRook, 1);
        // The shipped middlegame rook table is rank/file based and the endgame
        // one is centrality based, so those counts belong to one row each.
        bd.mg[std::size_t(PstRookRank)] += sign * rank;
        bd.mg[std::size_t(PstRookFile)] += sign * fileCenter;
        bd.eg[std::size_t(PstRookCenter)] += sign * center;
        break;
    case Queen:
        add(MatQueen, 1);
        add(PstQueenCenter, center);
        break;
    case King:
        // The shipped king middlegame weights are negative (advancing costs),
        // so the counts are plain rank/file distances.
        bd.mg[std::size_t(PstKingRank)] += sign * rank;
        bd.mg[std::size_t(PstKingFile)] += sign * fileCenter;
        bd.eg[std::size_t(PstKingCenter)] += sign * center;
        break;
    default:
        break;
    }
}

void accumulate_breakdown(const Position& p, Color us, EvalBreakdown& bd) {
    const Color them = ~us;
    const int sign = us == White ? 1 : -1;
    const Bitboard ours = p.pieces(us), pawns = p.pieces(us, Pawn);
    const Bitboard enemyPawns = p.pieces(them, Pawn);
    const auto mg = [&](EvalParamId id) -> int& { return bd.mg[std::size_t(id)]; };
    const auto eg = [&](EvalParamId id) -> int& { return bd.eg[std::size_t(id)]; };

    for (int i = 1; i <= King; ++i)
        for (Bitboard b = p.pieces(us, PieceType(i)); b;)
            add_pst_counts(bd, PieceType(i), pst_index(us, pop_lsb(b)), sign);

    if (p.count(us, Bishop) >= 2) { mg(BishopPair) += sign; eg(BishopPair) += sign; }

    Bitboard b = pawns;
    while (b) {
        const Square s = pop_lsb(b);
        const int f = file_of(s);
        if (!(pawns & AdjacentFilesBB[f])) { mg(IsolatedPawn) += sign; eg(IsolatedPawn) += sign; }
        if (!(enemyPawns & PassedPawnMaskBB[us][s]) &&
            !(pawns & FileBB[f] & ForwardRanksBB[us][rank_of(s)])) {
            const int advance = us == White ? rank_of(s) : 7 - rank_of(s);
            mg(PassedPawnAdvance) += sign * advance * advance;
            eg(PassedPawnAdvance) += sign * advance * advance;
        }
    }
    for (int f = 0; f < 8; ++f) {
        const int extra = std::max(0, popcount(pawns & FileBB[f]) - 1);
        mg(DoubledPawn) += sign * extra;
        eg(DoubledPawn) += sign * extra;
    }

    for (PieceType pt : {Knight, Bishop, Rook, Queen}) {
        EvalParamId id = MobilityKnight;
        if (pt == Bishop) id = MobilityBishop;
        else if (pt == Rook) id = MobilityRook;
        else if (pt == Queen) id = MobilityQueen;
        for (Bitboard bb = p.pieces(us, pt); bb;) {
            const Square s = pop_lsb(bb);
            const int mobility = popcount(attacks_bb(pt, us, s, p.pieces()) & ~ours);
            mg(id) += sign * mobility;
            eg(id) += sign * mobility;
            if (pt == Rook) {
                const Bitboard file = FileBB[file_of(s)];
                if (!(pawns & file)) {
                    if (!(enemyPawns & file)) { mg(RookOpenFile) += sign; eg(RookOpenFile) += sign; }
                    else { mg(RookSemiOpenFile) += sign; eg(RookSemiOpenFile) += sign; }
                }
            }
        }
    }

    const Square k = p.king_square(us);
    const int frontRank = rank_of(k) + (us == White ? 1 : -1);
    if (frontRank >= 0 && frontRank < 8) {
        const Bitboard shieldFiles = FileBB[file_of(k)] | AdjacentFilesBB[file_of(k)];
        mg(PawnShield) += sign * popcount(pawns & shieldFiles & RankBB[frontRank]);
    }
    const Bitboard zone = KingZoneBB[us][k];
    for (PieceType pt : {Pawn, Knight, Bishop, Rook, Queen}) {
        EvalParamId id = KingDangerPawn;
        if (pt == Knight) id = KingDangerKnight;
        else if (pt == Bishop) id = KingDangerBishop;
        else if (pt == Rook) id = KingDangerRook;
        else if (pt == Queen) id = KingDangerQueen;
        for (Bitboard bb = p.pieces(them, pt); bb;) {
            const Square s = pop_lsb(bb);
            const int hits = popcount(attacks_bb(pt, them, s, p.pieces()) & zone);
            // The feature value is negative (enemy attacks hurt us) while the
            // parameter is positive, so the count enters with the opposite sign.
            mg(id) -= sign * hits;
        }
    }
}
} // namespace

void init_evaluation() {
    // Idempotent: parse_fen calls this on every FEN, and an experiment that
    // installed its own parameter set must not be silently reset by the next
    // position it loads.
    static std::once_flag once;
    std::call_once(once, [] {
        if (!eval_params_installed()) apply_eval_params(default_eval_params());
    });
}

void evaluation_rebuild_tables() { build_tables(active_eval_params()); }

EvalBreakdown eval_breakdown(const Position& p) {
    EvalBreakdown bd;
    accumulate_breakdown(p, White, bd);
    accumulate_breakdown(p, Black, bd);
    bd.phase = phase_of(p);
    return bd;
}

int eval_from_breakdown(const EvalBreakdown& bd, const EvalParams& params) {
    long long mg = 0, eg = 0;
    for (int i = 0; i < EvalParamNB; ++i) {
        mg += static_cast<long long>(params.mg[std::size_t(i)]) * bd.mg[std::size_t(i)];
        eg += static_cast<long long>(params.eg[std::size_t(i)]) * bd.eg[std::size_t(i)];
    }
    const long long phase = bd.phase;
    const long long tapered = (mg * phase + eg * (24 - phase)) / 24;
    return int(std::clamp<long long>(tapered, -VALUE_KNOWN_WIN, VALUE_KNOWN_WIN));
}

int evaluate(const Position& p) {
    const EvalParams& par = active_eval_params();
    const Score w = features(p, White, par), b = features(p, Black, par);
    const int mg = p.acc_mg(White) - p.acc_mg(Black) + w.mg - b.mg;
    const int eg = p.acc_eg(White) - p.acc_eg(Black) + w.eg - b.eg;
    const int score = taper(mg, eg, phase_of(p));
    return p.side_to_move() == White ? score : -score;
}
} // namespace stockbear
