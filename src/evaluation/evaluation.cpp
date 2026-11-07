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
#include "evaluation/nnue.hpp"
#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <mutex>
#include <string>

namespace stockbear {
#ifndef SB_INCREMENTAL_EVAL
#define SB_INCREMENTAL_EVAL 0 // 1: evaluate() reads StateInfo feature counts
#endif

int PieceValueMg[PieceTypeNB] = {0, 100, 320, 335, 500, 975, 0};
int PieceValueEg[PieceTypeNB] = {0, 120, 305, 330, 520, 950, 0};
int PieceSquareMg[PieceTypeNB][SQ_NB] = {};
int PieceSquareEg[PieceTypeNB][SQ_NB] = {};

// DEV6 exp-0048: explicit per-square tables loaded from a PST file. Inactive
// by default; when active they override the formulaic tables in
// evaluation_rebuild_tables(). Kept separate so clearing restores the exact
// shipped formulaic values.
namespace {
int gFullPstMg[PieceTypeNB][SQ_NB] = {};
int gFullPstEg[PieceTypeNB][SQ_NB] = {};
bool gPstFileActive = false;
// Bound a single PST entry so a hostile file cannot overflow the accumulator.
constexpr int PstEntryLimit = 2000;
} // namespace

bool pst_file_active() { return gPstFileActive; }

void clear_pst_file() {
    gPstFileActive = false;
    evaluation_rebuild_tables();
}

bool load_pst_file(const std::string& path, std::string* error) {
    auto fail = [&](const std::string& msg) {
        if (error) *error = msg;
        return false;
    };
    std::ifstream in(path);
    if (!in) return fail("cannot open PST file: " + path);
    std::string magic;
    if (!(in >> magic) || magic != "SBPST1") return fail("PST file must start with SBPST1");
    int mg[PieceTypeNB][SQ_NB];
    int eg[PieceTypeNB][SQ_NB];
    // Piece order in the file: Pawn, Knight, Bishop, Rook, Queen, King.
    const PieceType order[6] = {Pawn, Knight, Bishop, Rook, Queen, King};
    for (PieceType pt : order) {
        for (int idx = 0; idx < SQ_NB; ++idx) {
            long long m, e;
            if (!(in >> m >> e)) return fail("PST file truncated for piece " + std::to_string(int(pt)));
            if (m < -PstEntryLimit || m > PstEntryLimit || e < -PstEntryLimit || e > PstEntryLimit)
                return fail("PST entry out of range [-2000,2000]");
            mg[pt][idx] = int(m);
            eg[pt][idx] = int(e);
        }
    }
    std::string trailing;
    if (in >> trailing) return fail("PST file has trailing content after 384 entries");
    for (PieceType pt : order)
        for (int idx = 0; idx < SQ_NB; ++idx) {
            gFullPstMg[pt][idx] = mg[pt][idx];
            gFullPstEg[pt][idx] = eg[pt][idx];
        }
    gPstFileActive = true;
    evaluation_rebuild_tables();
    if (error) error->clear();
    return true;
}

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

// dev6 exp-0026: the six "extended" pawn/coordination features are only paid
// for when at least one of their parameters is non-zero. With the shipped set
// (all six = 0) the default/champion build is bit-exact AND has zero extra
// per-node cost: the search never even calls the extended feature routine.
// The flag is recomputed in evaluation_rebuild_tables(), i.e. whenever a
// parameter set is installed (default set at startup, or an EvalParams file
// loaded through UCI / --params). This keeps evaluate()'s features() path,
// eval_breakdown()'s accumulate_breakdown() path and the (default-off)
// incremental path in agreement for every parameter set.
bool gExtendedEval = false;
bool extended_eval_active() { return gExtendedEval; }

// --- exp-0052: nonlinear king safety (default OFF) --------------------------
// The shipped KingDanger* rows charge a CONSTANT cp per zone hit, so four
// converging attackers cost exactly 4x one attacker. Real king attacks are
// super-linear: a lone attacker is nearly harmless, several together can be
// decisive. No value of the linear coefficients can express that, which makes
// this a REPRESENTATIONAL limit rather than a tuning error.
//
// Weighted hits into the king zone are summed and the total indexes a
// saturating quadratic curve, tapered as a middlegame-only term (the king PST
// already handles endgame king activity, so safety there would double-count).
// The attack-unit idea is the published Rebel/CPW formulation; the weights,
// curve and cap below are StockBear's own. No external engine code is used.
//
// COST: the units are accumulated inside the EXISTING king-danger loop, which
// already computes every enemy piece's attack set. No attack is recomputed;
// the only new work is one multiply-add per piece plus one table-free curve
// evaluation per side. The accumulation is guarded by the hoisted gate flag,
// so the default build does no extra work at all.
bool gKingSafety = false;
bool king_safety_active() { return gKingSafety; }
// exp-0053: cached activation flag for the threat term, same discipline as
// gKingSafety -- with the shipped set (param 0) evaluate() pays nothing.
bool gThreats = false;
// exp-0055: cached activation flag for the passed-pawn race term.
bool gPassedPawnRace = false;
// DEV6 architecture-survey candidate: cached activation flag for slider batteries.
bool gKingSliderBattery = false;

// Attack-unit weights per attacking piece type (index by PieceType). Pawns and
// kings weigh 0: their zone contact is already covered by the linear rows and
// the pawn shield, and counting them here would double-count.
constexpr int KingAttackWeight[PieceTypeNB] = {0, 0, 2, 2, 3, 5, 0};
// Cap at the p99 of the observed per-side attack-unit distribution (33 units on
// a 3,000-position diagnostic corpus), rounded down to 32. This clips only the
// extreme ~1% of sides and bounds one side's danger at 32*32/16 = 64 cp, so the
// term can never dwarf material or swamp the pruning margins.
constexpr int KingDangerIndexMax = 32;

// Saturating quadratic in "danger units"; the parameter scales it to cp.
//
// SCALE IS PART OF THE DESIGN, NOT A FREE KNOB. exp-0051 measured -159.54 Elo
// for a table whose RMS eval perturbation was 111.83 cp: a large perturbation
// distorts the cp-calibrated futility (110), reverse-futility (85) and delta
// (200) margins, so the search prunes on a different scale than the margins
// assume. This curve is therefore scaled so that, at the frozen coefficient,
// the p99 term is about one pawn and the RMS eval delta stays well below the
// smallest pruning margin. Divisor 16 with the 64-unit cap bounds one side's
// danger at 256 "units"; see docs/STOCKBEAR_RECOVERY_RESEARCH.md for the
// pre-declared criterion and the measured distribution.
int king_danger_curve(int units) {
    const int u = units < 0 ? 0 : (units > KingDangerIndexMax ? KingDangerIndexMax : units);
    return (u * u) / 16;
}

// Shared by features(), accumulate_breakdown() and the incremental count path
// so the three can never drift apart. Queen gate: with no enemy queen the
// weighted total stays small and the curve contributes little, so the term is
// skipped in queenless positions (most endgames), keeping endgame cost flat.
int king_safety_danger(const Position& p, Color them, int units) {
    if (!p.pieces(them, Queen)) return 0;
    return king_danger_curve(units);
}

// Raw counts (always from `us`'s point of view) of the six extended features.
// A single shared implementation is used by features(), accumulate_breakdown()
// and cheap_feature_counts() so the live evaluation and the offline breakdown
// can never drift apart. Semantics (documented in docs/DEV6_EVAL_FEATURES.md):
//   RookOn7th       - a rook on the 7th rank (rank index 6 for White, 1 for Black).
//   KnightOutpost    - knight on relative rank 3..5, defended by a friendly
//                      pawn, and not attackable by an enemy pawn.
//   PawnChain        - a pawn defended by at least one friendly pawn.
//   BackwardPawn     - a non-passed pawn whose stop square is attacked by an
//                      enemy pawn, not defended by a friendly pawn, and which
//                      has fallen behind a friendly pawn on an adjacent file.
//   ConnectedPassed  - a passed pawn with a friendly passed pawn on an
//                      adjacent file (connected passers support each other).
//   RookBehindPassed - a friendly rook on the same file as, and behind, a
//                      friendly passed pawn (classic endgame support).
struct ExtCounts {
    int rookOn7th = 0, knightOutpost = 0, backwardPawn = 0,
        pawnChain = 0, connectedPassed = 0, rookBehindPassed = 0;
};

ExtCounts extended_counts(const Position& p, Color us) {
    const Color them = ~us;
    const Bitboard pawns = p.pieces(us, Pawn);
    const Bitboard enemyPawns = p.pieces(them, Pawn);
    const Bitboard rooks = p.pieces(us, Rook);
    const Bitboard knights = p.pieces(us, Knight);
    ExtCounts e;

    // Passed pawns use exactly the same rule as the shipped PassedPawnAdvance
    // term (leading pawn of a file only), so "passed" is consistent everywhere.
    Bitboard passed = 0;
    for (Bitboard b = pawns; b;) {
        const Square s = pop_lsb(b);
        const int f = file_of(s);
        if (!(enemyPawns & PassedPawnMaskBB[us][s]) &&
            !(pawns & FileBB[f] & ForwardRanksBB[us][rank_of(s)]))
            passed |= square_bb(s);
    }

    for (Bitboard b = pawns; b;) {
        const Square s = pop_lsb(b);
        const int f = file_of(s);
        // PawnChain: a friendly pawn on a defending square (the squares from
        // which a `us` pawn attacks `s` are exactly PawnAttacksBB[them][s]).
        if (pawns & PawnAttacksBB[them][s]) ++e.pawnChain;
        // ConnectedPassed: this is a passer with a passer on an adjacent file.
        if ((passed & square_bb(s)) && (passed & AdjacentFilesBB[f])) ++e.connectedPassed;
        // BackwardPawn: stop square = one step in `us`'s forward direction.
        const int stop = int(s) + (us == White ? 8 : -8);
        if (stop >= 0 && stop < 64) {
            const Square stopSq = Square(stop);
            const bool notPassed        = (enemyPawns & PassedPawnMaskBB[us][s]) != 0;
            const bool enemyPawnHitsStop= (enemyPawns & PawnAttacksBB[us][stopSq]) != 0;
            const bool friendlyDefends  = (pawns & PawnAttacksBB[them][stopSq]) != 0;
            const bool behindNeighbour  = (pawns & AdjacentFilesBB[f] &
                                          ForwardRanksBB[us][rank_of(s)]) != 0;
            if (notPassed && enemyPawnHitsStop && !friendlyDefends && behindNeighbour)
                ++e.backwardPawn;
        }
    }

    // RookBehindPassed: ranks behind a White passer are the ranks below it,
    // i.e. ForwardRanksBB[Black]; behind a Black passer are ranks above it.
    for (Bitboard b = passed; b;) {
        const Square s = pop_lsb(b);
        e.rookBehindPassed += popcount(rooks & FileBB[file_of(s)] &
                                       ForwardRanksBB[them][rank_of(s)]);
    }

    for (Bitboard b = knights; b;) {
        const Square s = pop_lsb(b);
        const int rel = us == White ? rank_of(s) : 7 - rank_of(s);
        if (rel >= 3 && rel <= 5 && (pawns & PawnAttacksBB[them][s]) &&
            !(enemyPawns & PawnAttacksBB[us][s]))
            ++e.knightOutpost;
    }
    for (Bitboard b = rooks; b;) {
        const Square s = pop_lsb(b);
        if (rank_of(s) == (us == White ? 6 : 1)) ++e.rookOn7th;
    }
    return e;
}

// exp-0053: material exposure (threats). StockBear had NO threat term at all:
// an undefended enemy piece, or one attacked by a pawn, was invisible to static
// evaluation. At median depth 5 that is a real representational gap.
//
// Cost design (the exp-0052 lesson, plus a measured dead end): a shared per-square
// attack table was tried first and measured ~19.5% SLOWER -- storing/reloading
// 512 bytes cost more than the magic-lookup recomputation it replaced. Instead
// the union masks are accumulated with a few ORs inside the loops that ALREADY
// generate these attacks, and the threat term itself is pure popcount work.
//
// After both features() calls, by[c] covers colour c's P,N,B,R,Q attacks: the
// N/B/R/Q part comes from that side's own mobility loop, and the P/N/B/R/Q part
// from the opponent's king-danger loop. Kings are added explicitly below.
struct ThreatUnions {
    Bitboard by[2];
    Bitboard byPawn[2];
};

// Fixed internal weights + ONE scale parameter, so the experiment has a single
// attributable knob (the exp-0052 discipline). Bounded so the term can never
// dwarf material or swamp the cp-calibrated pruning margins.
constexpr int ThreatWeightHanging = 10;
constexpr int ThreatWeightPawn    = 16;
constexpr int ThreatUnitsMax      = 64;

bool threats_active() { return gThreats; }

int threat_units(const Position& p, Color us, const ThreatUnions& tu) {
    const Color them = ~us;
    const Bitboard occ = p.pieces();
    const Bitboard enemy = p.pieces(them);
    const Bitboard enemyNonPawn = enemy & ~p.pieces(them, Pawn);
    const Bitboard atkUs   = tu.by[us]   | attacks_bb(King, us,   p.king_square(us),   occ);
    const Bitboard defThem = tu.by[them] | attacks_bb(King, them, p.king_square(them), occ);
    // Attacked by us and not defended by them.
    const Bitboard hanging = enemyNonPawn & atkUs & ~defThem;
    // Any enemy piece attacked by one of our pawns (a pawn is always cheaper).
    const Bitboard pawnThreat = enemy & tu.byPawn[us];
    const int units = ThreatWeightHanging * popcount(hanging)
                    + ThreatWeightPawn    * popcount(pawnThreat);
    return std::min(units, ThreatUnitsMax);
}

// Independent union construction for the offline breakdown / count paths. The
// hot evaluate() path does NOT use this -- it reuses its existing loops -- so
// the breakdown invariant genuinely cross-checks the fused accumulation.
ThreatUnions build_threat_unions(const Position& p) {
    ThreatUnions tu{};
    const Bitboard occ = p.pieces();
    for (int c = 0; c < ColorNB; ++c) {
        const Color col = Color(c);
        for (PieceType pt : {Pawn, Knight, Bishop, Rook, Queen}) {
            Bitboard b = p.pieces(col, pt);
            while (b) {
                const Square s = pop_lsb(b);
                const Bitboard at = attacks_bb(pt, col, s, occ);
                tu.by[c] |= at;
                if (pt == Pawn) tu.byPawn[c] |= at;
            }
        }
    }
    return tu;
}

// exp-0055: passed-pawn promotion race. The shipped evaluation scores a passer
// ONLY as advance^2 * PassedPawnAdvance. It has no idea whether its own king is
// escorting it, whether the enemy king is sitting on the promotion path, or
// whether the path is blocked at all -- king-proximity terms are entirely absent
// from the parameter table. In an endgame those facts decide whether a passer is
// a queen or a dead pawn, so this is a large representational gap.
//
// Distinct from the abandoned exp-0026 bundle, which contained only the narrow
// ConnectedPassed / RookBehindPassed counts and no king geometry.
//
// ONE scale parameter with fixed internal weights (the exp-0053 discipline).
// Chebyshev distance is the right metric: it counts king moves.
constexpr int RaceWeightOwnKing  = 2;
constexpr int RaceWeightEnemyKing = 2;
constexpr int RaceWeightBlocked  = 6;
constexpr int RaceUnitsMax       = 64;

inline int chebyshev(Square a, Square b) {
    const int df = std::abs(file_of(a) - file_of(b));
    const int dr = std::abs(rank_of(a) - rank_of(b));
    return std::max(df, dr);
}

// Per-passer contribution. Shared by the standalone reference walker and the
// FUSED live path inside features(), so the formula exists in exactly one place.
inline int race_passer_units(int advance, int ownD, int enemyD, bool blocked) {
    return advance * (RaceWeightOwnKing * (7 - ownD)
                    - RaceWeightEnemyKing * (7 - enemyD)
                    - (blocked ? RaceWeightBlocked : 0));
}

bool passed_pawn_race_active() { return gPassedPawnRace; }

// Shared by features(), accumulate_breakdown() and all_feature_counts() so the
// live evaluation and the offline breakdown can never drift apart. Uses exactly
// the shipped passed-pawn rule (no enemy pawn in the passed mask, and leading
// pawn of its file) so "passed" means the same thing everywhere.
int passed_pawn_race_units(const Position& p, Color us) {
    const Color them = ~us;
    const Bitboard pawns = p.pieces(us, Pawn);
    const Bitboard enemyPawns = p.pieces(them, Pawn);
    const Bitboard enemyAll = p.pieces(them);
    const Square ownK = p.king_square(us);
    const Square enemyK = p.king_square(them);
    const int forward = us == White ? 8 : -8;
    int units = 0;
    for (Bitboard b = pawns; b;) {
        const Square s = pop_lsb(b);
        const int f = file_of(s);
        if (enemyPawns & PassedPawnMaskBB[us][s]) continue;
        if (pawns & FileBB[f] & ForwardRanksBB[us][rank_of(s)]) continue;
        const int advance = us == White ? rank_of(s) : 7 - rank_of(s);
        const int stopIdx = int(s) + forward;
        if (stopIdx < 0 || stopIdx >= 64) continue;
        const Square stop = Square(stopIdx);
        // Own king close to the stop square escorts the passer; the enemy king
        // close to it blockades. Distances are clamped to the board diameter.
        const int ownD = std::min(chebyshev(ownK, stop), 7);
        const int enemyD = std::min(chebyshev(enemyK, stop), 7);
        // Any enemy piece on the file ahead of the pawn blocks the path.
        const bool blocked =
            (enemyAll & FileBB[f] & ForwardRanksBB[us][rank_of(s)]) != 0;
        units += race_passer_units(advance, ownD, enemyD, blocked);
    }
    return std::clamp(units, -RaceUnitsMax, RaceUnitsMax);
}

// DEV6 architecture-survey candidate: king-facing slider battery / x-ray.
// The shipped KingDanger* rows count immediate zone hits; they do not represent
// an enemy slider aligned with our king behind exactly one intervening blocker.
// Fixed internal weights + ONE scale row, default OFF. Only exactly-one-blocker
// alignments are counted: zero-blocker contact is already covered by checks /
// zone attacks, and two blockers are too screened to be a battery.
constexpr int BatteryWeightOrthogonal = 4; // rook/queen on file/rank
constexpr int BatteryWeightDiagonal   = 3; // bishop/queen on diagonal
constexpr int BatteryUnitsMax         = 16;

bool king_slider_battery_active() { return gKingSliderBattery; }

// exp-0063 semantics-preserving cost optimization of the exp-0061 mechanism:
// alignment is tested with hoisted ray masks instead of per-slider abs(df)/abs(dr),
// and BetweenBB is touched only for a slider already on the king's ray. The
// counted set is identical: exactly one intervening blocker, same weights/cap.
inline Bitboard battery_orthogonal_mask(Square k) {
    return FileBB[file_of(k)] | RankBB[rank_of(k)];
}
inline Bitboard battery_diagonal_mask(Square k) {
    return BatteryDiagonalBB[k];
}
inline int slider_battery_between_units(Square s, Square k, Bitboard occ, int weight) {
    return popcount(BetweenBB[s][k] & occ) == 1 ? weight : 0;
}
inline int slider_battery_aligned_raw(const Position& p, Color them, Square k,
                                      Bitboard occ, Bitboard orth, Bitboard diag) {
    int units = 0;
    // Only sliders already on the king's rays are visited; no per-piece branch
    // is added to the existing king-danger attack loop. Rook/queen orthogonal
    // and bishop/queen diagonal sets are disjoint for any enemy square != k.
    for (Bitboard b = (p.pieces(them, Rook) | p.pieces(them, Queen)) & orth; b;) {
        const Square s = pop_lsb(b);
        units += slider_battery_between_units(s, k, occ, BatteryWeightOrthogonal);
    }
    for (Bitboard b = (p.pieces(them, Bishop) | p.pieces(them, Queen)) & diag; b;) {
        const Square s = pop_lsb(b);
        units += slider_battery_between_units(s, k, occ, BatteryWeightDiagonal);
    }
    return units;
}

int king_slider_battery_units(const Position& p, Color us) {
    const Color them = ~us;
    const Square k = p.king_square(us);
    const int raw = slider_battery_aligned_raw(p, them, k, p.pieces(),
                                               battery_orthogonal_mask(k),
                                               battery_diagonal_mask(k));
    return std::min(raw, BatteryUnitsMax);
}

// Dev5 isolated experiment: activity on an enemy-pawn-controlled square is
// often illusory. This mask is deliberately geometric, not a legality test.
Bitboard mobility_area(const Position& p, Color us) {
    Bitboard area = ~p.pieces(us);
#ifdef STOCKBEAR_SAFE_MOBILITY
    Bitboard attacked = 0;
    for (Bitboard pawns = p.pieces(~us, Pawn); pawns;) {
        const Square s = pop_lsb(pawns);
        attacked |= attacks_bb(Pawn, ~us, s, p.pieces());
    }
    area &= ~attacked;
#endif
    return area;
}

// The live evaluation of one side. Mirrors `accumulate_breakdown` below
// term for term; `eval_breakdown_matches_evaluate` in the unit tests is what
// keeps the two from drifting apart.
Score features(const Position& p, Color us, const EvalParams& par, bool lite = false,
               ThreatUnions* tu = nullptr) {
    const Color them = ~us;
    const Bitboard pawns = p.pieces(us, Pawn);
    const Bitboard mobilityArea = mobility_area(p, us);
    const Bitboard enemyPawns = p.pieces(them, Pawn);
    Score out;
    const auto mgp = [&](EvalParamId id) { return par.mg[std::size_t(id)]; };
    const auto egp = [&](EvalParamId id) { return par.eg[std::size_t(id)]; };

    if (p.count(us, Bishop) >= 2) {
        out.mg += mgp(BishopPair);
        out.eg += egp(BishopPair);
    }

    // exp-0055: the race is fused into this existing pawn walk so a position
    // with no passer pays only the gate test, not a second 8-pawn scan.
    const bool raceOn = passed_pawn_race_active();
    int raceRaw = 0;
    const Bitboard raceEnemyAll = raceOn ? p.pieces(them) : Bitboard(0);
    const Square raceOwnK = raceOn ? p.king_square(us) : SQ_NONE;
    const Square raceEnemyK = raceOn ? p.king_square(them) : SQ_NONE;
    const int raceForward = us == White ? 8 : -8;

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
            const Bitboard ahead = FileBB[f] & ForwardRanksBB[us][rank_of(s)];
            if (!(pawns & ahead)) {
                const int advance = us == White ? rank_of(s) : 7 - rank_of(s);
                out.mg += advance * advance * mgp(PassedPawnAdvance);
                out.eg += advance * advance * egp(PassedPawnAdvance);
                if (raceOn) {
                    const int stopIdx = int(s) + raceForward;
                    if (stopIdx >= 0 && stopIdx < 64) {
                        const Square stop = Square(stopIdx);
                        const int ownD = std::min(chebyshev(raceOwnK, stop), 7);
                        const int enemyD = std::min(chebyshev(raceEnemyK, stop), 7);
                        raceRaw += race_passer_units(advance, ownD, enemyD,
                                                     (raceEnemyAll & ahead) != 0);
                    }
                }
            }
        }
    }
    if (raceOn) {
        const int race = std::clamp(raceRaw, -RaceUnitsMax, RaceUnitsMax);
        out.mg += race * mgp(PassedPawnRace);
        out.eg += race * egp(PassedPawnRace);
    }

    // Penalize each extra pawn on a file once, not once per pair.
    for (int f = 0; f < 8; ++f) {
        const int extra = std::max(0, popcount(pawns & FileBB[f]) - 1);
        out.mg += extra * mgp(DoubledPawn);
        out.eg += extra * egp(DoubledPawn);
    }

    // Count geometrically available squares as a cheap activity proxy.
    for (PieceType pt : {Knight, Bishop, Rook, Queen}) {
        if (lite && pt != Rook) continue; // lite: rook loop kept only for open-file terms
        b = p.pieces(us, pt);
        while (b) {
            Square s = pop_lsb(b);
            if (!lite) {
            const Bitboard at = attacks_bb(pt, us, s, p.pieces());
            if (tu) tu->by[us] |= at;
            const int mobility = popcount(at & mobilityArea);
            EvalParamId id = MobilityKnight;
            if (pt == Bishop) id = MobilityBishop;
            else if (pt == Rook) id = MobilityRook;
            else if (pt == Queen) id = MobilityQueen;
            out.mg += mobility * mgp(id);
            out.eg += mobility * egp(id);
            }
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

    // dev6 extended pawn/coordination features (shared with eval_breakdown).
    // Gated: with the shipped set (all six params = 0) this whole block is
    // skipped, so the default/champion build stays bit-exact and full-speed.
    if (extended_eval_active()) {
        const ExtCounts e = extended_counts(p, us);
        out.mg += e.rookOn7th        * mgp(RookOn7th)
                + e.knightOutpost     * mgp(KnightOutpost)
                + e.backwardPawn      * mgp(BackwardPawn)
                + e.pawnChain         * mgp(PawnChain)
                + e.connectedPassed   * mgp(ConnectedPassed)
                + e.rookBehindPassed  * mgp(RookBehindPassed);
        out.eg += e.rookOn7th        * egp(RookOn7th)
                + e.knightOutpost     * egp(KnightOutpost)
                + e.backwardPawn      * egp(BackwardPawn)
                + e.pawnChain         * egp(PawnChain)
                + e.connectedPassed   * egp(ConnectedPassed)
                + e.rookBehindPassed  * egp(RookBehindPassed);
    }

    // Pawn shield and enemy activity around the king. Kept in the middlegame
    // component so its contribution naturally fades as material comes off.
    const Square k = p.king_square(us);
    const int frontRank = rank_of(k) + (us == White ? 1 : -1);
    if (frontRank >= 0 && frontRank < 8) {
        const Bitboard shieldFiles = FileBB[file_of(k)] | AdjacentFilesBB[file_of(k)];
        out.mg += mgp(PawnShield) * popcount(pawns & shieldFiles & RankBB[frontRank]);
    }
    if (!lite) {
        // exp-0052: accumulate attack units in the SAME loop that already
        // computes these attacks. Hoisted flag => no per-piece branch cost
        // when the feature is off, and no recomputed attack sets when it is on.
        const bool ks = king_safety_active();
        const bool batteryOn = king_slider_battery_active();
        int kingUnits = 0;
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
                const Bitboard at = attacks_bb(pt, them, s, p.pieces());
                if (tu) {
                    tu->by[them] |= at;
                    if (pt == Pawn) tu->byPawn[them] |= at;
                }
                const int hits = popcount(at & zone);
                out.mg -= hits * mgp(id);
                if (ks) kingUnits += KingAttackWeight[pt] * hits;
            }
        }
        if (ks) out.mg -= king_safety_danger(p, them, kingUnits) * mgp(KingSafetyQuadratic);
        if (batteryOn) {
            const int raw = slider_battery_aligned_raw(p, them, k, p.pieces(),
                                                       battery_orthogonal_mask(k),
                                                       battery_diagonal_mask(k));
            const int battery = std::min(raw, BatteryUnitsMax);
            out.mg -= battery * mgp(KingSliderBattery);
            out.eg -= battery * egp(KingSliderBattery);
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
    const Bitboard pawns = p.pieces(us, Pawn);
    const Bitboard mobilityArea = mobility_area(p, us);
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
            const int mobility = popcount(attacks_bb(pt, us, s, p.pieces()) & mobilityArea);
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

    // exp-0055: passed-pawn race count (shared helper, identical to features()).
    {
        const int race = passed_pawn_race_units(p, us);
        mg(PassedPawnRace) += sign * race;
        eg(PassedPawnRace) += sign * race;
    }

    // dev6 extended features (identical counts to features(), shared helper).
    if (extended_eval_active()) {
        const ExtCounts e = extended_counts(p, us);
        mg(RookOn7th)        += sign * e.rookOn7th;
        eg(RookOn7th)        += sign * e.rookOn7th;
        mg(KnightOutpost)     += sign * e.knightOutpost;
        eg(KnightOutpost)     += sign * e.knightOutpost;
        mg(BackwardPawn)      += sign * e.backwardPawn;
        eg(BackwardPawn)      += sign * e.backwardPawn;
        mg(PawnChain)         += sign * e.pawnChain;
        eg(PawnChain)         += sign * e.pawnChain;
        mg(ConnectedPassed)   += sign * e.connectedPassed;
        eg(ConnectedPassed)   += sign * e.connectedPassed;
        mg(RookBehindPassed)  += sign * e.rookBehindPassed;
        eg(RookBehindPassed)  += sign * e.rookBehindPassed;
    }

    const Square k = p.king_square(us);
    const int frontRank = rank_of(k) + (us == White ? 1 : -1);
    if (frontRank >= 0 && frontRank < 8) {
        const Bitboard shieldFiles = FileBB[file_of(k)] | AdjacentFilesBB[file_of(k)];
        mg(PawnShield) += sign * popcount(pawns & shieldFiles & RankBB[frontRank]);
    }
    const bool ks = king_safety_active();
    int kingUnits = 0;
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
            if (ks) kingUnits += KingAttackWeight[pt] * hits;
        }
    }
    // The curve is a pure function of the POSITION, so it enters as a COUNT and
    // the parameter stays linear: sum(count*param) == features() exactly.
    if (ks) mg(KingSafetyQuadratic) -= sign * king_safety_danger(p, them, kingUnits);
    // Slider battery is also a pure position count; same sign convention as the
    // linear king-danger rows (enemy batteries hurt `us`).
    const int battery = king_slider_battery_units(p, us);
    mg(KingSliderBattery) -= sign * battery;
    eg(KingSliderBattery) -= sign * battery;
}
} // namespace

// --- Raw feature counts (incremental evaluator) -------------------------------
// These mirror features() term for term but produce raw counts instead of
// weighted sums, so the active EvalParams can be applied (or reloaded) at
// evaluate() time. test_eval_baseline keeps evaluate() == dev2 oracle, which
// transitively verifies these counts against features().
EvalParamId mobility_param_id(PieceType pt) {
    switch (pt) {
    case Knight: return MobilityKnight;
    case Bishop: return MobilityBishop;
    case Rook:   return MobilityRook;
    default:     return MobilityQueen;
    }
}

EvalParamId king_danger_param_id(PieceType pt) {
    switch (pt) {
    case Pawn:   return KingDangerPawn;
    case Knight: return KingDangerKnight;
    case Bishop: return KingDangerBishop;
    case Rook:   return KingDangerRook;
    default:     return KingDangerQueen;
    }
}

// Terms that depend only on pawn/rook/king placement and bishop count — cheap
// enough to recompute from scratch on every make_move.
void cheap_feature_counts(const Position& p, Color us, std::int16_t* out) {
    const Color them = ~us;
    const Bitboard pawns = p.pieces(us, Pawn);
    const Bitboard enemyPawns = p.pieces(them, Pawn);
    // Only the genuinely cheap terms; mobility (20-23) and king danger (27-29)
    // live outside this range and are maintained incrementally. The six dev6
    // extended ids are now maintained here too (they are pawn/rook based and
    // cheap), closing the exp-0022 caveat for the default-off incremental path.
    for (int id : {int(BishopPair), int(IsolatedPawn), int(DoubledPawn), int(PassedPawnAdvance),
                   int(RookOpenFile), int(RookSemiOpenFile), int(PawnShield),
                   int(RookOn7th), int(KnightOutpost), int(BackwardPawn), int(PawnChain),
                   int(ConnectedPassed), int(RookBehindPassed),
                   int(KingSafetyQuadratic)})
        out[id] = 0;
    if (extended_eval_active()) {
        const ExtCounts e = extended_counts(p, us);
        out[RookOn7th]       = std::int16_t(e.rookOn7th);
        out[KnightOutpost]    = std::int16_t(e.knightOutpost);
        out[BackwardPawn]     = std::int16_t(e.backwardPawn);
        out[PawnChain]        = std::int16_t(e.pawnChain);
        out[ConnectedPassed]  = std::int16_t(e.connectedPassed);
        out[RookBehindPassed] = std::int16_t(e.rookBehindPassed);
    }
    if (p.count(us, Bishop) >= 2) out[BishopPair] = 1;
    Bitboard b = pawns;
    while (b) {
        const Square s = pop_lsb(b);
        const int f = file_of(s);
        if (!(pawns & AdjacentFilesBB[f])) out[IsolatedPawn] += 1;
        if (!(enemyPawns & PassedPawnMaskBB[us][s])) {
            if (!(pawns & FileBB[f] & ForwardRanksBB[us][rank_of(s)])) {
                const int advance = us == White ? rank_of(s) : 7 - rank_of(s);
                out[PassedPawnAdvance] += std::int16_t(advance * advance);
            }
        }
    }
    for (int f = 0; f < 8; ++f) {
        const int extra = std::max(0, popcount(pawns & FileBB[f]) - 1);
        out[DoubledPawn] += std::int16_t(extra);
    }
    b = p.pieces(us, Rook);
    while (b) {
        const Square s = pop_lsb(b);
        const Bitboard file = FileBB[file_of(s)];
        if (!(pawns & file)) {
            if (!(enemyPawns & file)) out[RookOpenFile] += 1;
            else out[RookSemiOpenFile] += 1;
        }
    }
    const Square k = p.king_square(us);
    const int frontRank = rank_of(k) + (us == White ? 1 : -1);
    if (frontRank >= 0 && frontRank < 8) {
        const Bitboard shieldFiles = FileBB[file_of(k)] | AdjacentFilesBB[file_of(k)];
        out[PawnShield] += std::int16_t(popcount(pawns & shieldFiles & RankBB[frontRank]));
    }
}

int mobility_count_at(const Position& p, Color us, PieceType pt, Square sq,
                      Bitboard occ, Bitboard own) {
    (void)p;
    return popcount(attacks_bb(pt, us, sq, occ) & ~own);
}

int king_danger_count_at(const Position& p, Color them, PieceType pt, Square sq,
                         Bitboard occ, Bitboard zone) {
    (void)p;
    return popcount(attacks_bb(pt, them, sq, occ) & zone);
}

// Full raw counts for one side (cheap terms + mobility + king danger).
void all_feature_counts(const Position& p, Color us, std::int16_t* out) {
    for (int id = 0; id < int(EvalParamNB); ++id) out[id] = 0;
    cheap_feature_counts(p, us, out);
    // exp-0053: per-side threat count, from the independent union builder.
    out[std::size_t(ThreatDetection)] =
        std::int16_t(threat_units(p, us, build_threat_unions(p)));
    // exp-0055: per-side passed-pawn race count.
    out[std::size_t(PassedPawnRace)] = std::int16_t(passed_pawn_race_units(p, us));
    const Bitboard occ = p.pieces();
    const Bitboard own = p.pieces(us);
    const Color them = ~us;
    for (PieceType pt : {Knight, Bishop, Rook, Queen}) {
        Bitboard b = p.pieces(us, pt);
        while (b) {
            const Square s = pop_lsb(b);
            out[mobility_param_id(pt)] += std::int16_t(mobility_count_at(p, us, pt, s, occ, own));
        }
    }
    const Bitboard zone = KingZoneBB[us][p.king_square(us)];
    const bool ks = king_safety_active();
    int kingUnits = 0;
    for (PieceType pt : {Pawn, Knight, Bishop, Rook, Queen}) {
        Bitboard b = p.pieces(them, pt);
        while (b) {
            const Square s = pop_lsb(b);
            const int hits = king_danger_count_at(p, them, pt, s, occ, zone);
            out[king_danger_param_id(pt)] -= std::int16_t(hits);
            if (ks) kingUnits += KingAttackWeight[pt] * hits;
        }
    }
    if (ks) out[KingSafetyQuadratic] -= std::int16_t(king_safety_danger(p, them, kingUnits));
}

void init_evaluation() {
    // Idempotent: parse_fen calls this on every FEN, and an experiment that
    // installed its own parameter set must not be silently reset by the next
    // position it loads.
    static std::once_flag once;
    std::call_once(once, [] {
        if (!eval_params_installed()) apply_eval_params(default_eval_params());
    });
}

void evaluation_rebuild_tables() {
    build_tables(active_eval_params());
    // exp-0048: a loaded PST file replaces only the piece-square term. The
    // material values and every non-PST feature stay exactly as the active
    // parameter set defines them. Inactive (the default) leaves the formulaic
    // tables untouched, so the shipped search remains bit-identical.
    if (gPstFileActive) {
        for (int pt = 0; pt < PieceTypeNB; ++pt)
            for (int idx = 0; idx < SQ_NB; ++idx) {
                PieceSquareMg[pt][idx] = gFullPstMg[pt][idx];
                PieceSquareEg[pt][idx] = gFullPstEg[pt][idx];
            }
    }
    const EvalParams& p = active_eval_params();
    // The extended features are computed only when at least one of their
    // parameters is non-zero. With the shipped def6 default set and with the
    // dev5 champion set (params_abc.txt) this is false, so the search pays no
    // extra per-node cost and remains bit-exact (bench 243f9a1c1ba5b36f).
    gExtendedEval = p.mg[RookOn7th] || p.eg[RookOn7th]
                 || p.mg[KnightOutpost] || p.eg[KnightOutpost]
                 || p.mg[BackwardPawn] || p.eg[BackwardPawn]
                 || p.mg[PawnChain] || p.eg[PawnChain]
                 || p.mg[ConnectedPassed] || p.eg[ConnectedPassed]
                 || p.mg[RookBehindPassed] || p.eg[RookBehindPassed];
    // exp-0052: pay for the nonlinear king-safety term only when it is enabled.
    gKingSafety = p.mg[KingSafetyQuadratic] || p.eg[KingSafetyQuadratic];
    // exp-0053: pay for the threat term only when it is enabled.
    gThreats = p.mg[ThreatDetection] || p.eg[ThreatDetection];
    // exp-0055: pay for the passed-pawn race term only when it is enabled.
    gPassedPawnRace = p.mg[PassedPawnRace] || p.eg[PassedPawnRace];
    // DEV6 architecture-survey candidate: pay for slider batteries only when enabled.
    gKingSliderBattery = p.mg[KingSliderBattery] || p.eg[KingSliderBattery];
}

EvalBreakdown eval_breakdown(const Position& p) {
    EvalBreakdown bd;
    accumulate_breakdown(p, White, bd);
    accumulate_breakdown(p, Black, bd);
    // exp-0053: threats need BOTH sides' attack unions, so they are added here
    // rather than per-side. build_threat_unions() is an INDEPENDENT computation
    // (evaluate() reuses its own existing loops), so the breakdown-vs-evaluate
    // invariant genuinely cross-checks the fused accumulation.
    const ThreatUnions tu = build_threat_unions(p);
    const int diff = threat_units(p, White, tu) - threat_units(p, Black, tu);
    bd.mg[std::size_t(ThreatDetection)] += diff;
    bd.eg[std::size_t(ThreatDetection)] += diff;
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
    // A loaded neural network replaces the classical terms completely; the
    // classical evaluation stays available as the portable fallback and as the
    // control arm of every experiment that measured the network.
    if (nnue::active_network() != nullptr) {
        if (const nnue::Accumulator* acc = p.nnue_accumulator())
            return nnue::evaluate(p, *acc);
        return nnue::evaluate_from_scratch(p);
    }
    const EvalParams& par = active_eval_params();
#if defined(STOCKBEAR_SAFE_MOBILITY) || !SB_INCREMENTAL_EVAL
    // Default (and safe-mobility) path: compute features() directly.
    // exp-0053: the union masks are filled by the loops inside features() at no
    // extra attack-generation cost. They are only complete after BOTH calls,
    // which is why the threat term is applied here rather than inside features().
    ThreatUnions tu{};
    const bool th = threats_active();
    ThreatUnions* tup = th ? &tu : nullptr;
    const Score w = features(p, White, par, false, tup), b = features(p, Black, par, false, tup);
    int threatMg = 0, threatEg = 0;
    if (th) {
        const int diff = threat_units(p, White, tu) - threat_units(p, Black, tu);
        threatMg = diff * par.mg[std::size_t(ThreatDetection)];
        threatEg = diff * par.eg[std::size_t(ThreatDetection)];
    }
    const int mg = p.acc_mg(White) - p.acc_mg(Black) + w.mg - b.mg + threatMg;
    const int eg = p.acc_eg(White) - p.acc_eg(Black) + w.eg - b.eg + threatEg;
#else
    // Incremental path: raw per-side counts live in the Position's StateInfo
    // (maintained by make_move) and the active parameters are applied here.
    const std::int16_t* fw = p.feat_counts(White);
    const std::int16_t* fb = p.feat_counts(Black);
    int wmg = 0, weg = 0, bmg = 0, beg = 0;
    for (int id = int(BishopPair); id < int(EvalParamNB); ++id) {
        wmg += fw[id] * par.mg[std::size_t(id)];
        weg += fw[id] * par.eg[std::size_t(id)];
        bmg += fb[id] * par.mg[std::size_t(id)];
        beg += fb[id] * par.eg[std::size_t(id)];
    }
    const int mg = p.acc_mg(White) - p.acc_mg(Black) + (wmg - bmg);
    const int eg = p.acc_eg(White) - p.acc_eg(Black) + (weg - beg);
#endif
    const int score = taper(mg, eg, phase_of(p));
    return p.side_to_move() == White ? score : -score;
}

int evaluate_lite(const Position& p) {
    if (nnue::active_network() != nullptr) return evaluate(p);
    const EvalParams& par = active_eval_params();
    const Score w = features(p, White, par, true), b = features(p, Black, par, true);
    const int mg = p.acc_mg(White) - p.acc_mg(Black) + w.mg - b.mg;
    const int eg = p.acc_eg(White) - p.acc_eg(Black) + w.eg - b.eg;
    const int score = taper(mg, eg, phase_of(p));
    return p.side_to_move() == White ? score : -score;
}
} // namespace stockbear
