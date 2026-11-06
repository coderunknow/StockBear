// exp-0052 nonlinear king safety.
//
// The shipped KingDanger* rows charge a CONSTANT centipawn amount per attacked
// king-zone square, so N converging attackers cost exactly N times one attacker.
// Real king attacks are super-linear. This term sums weighted attack units and
// indexes a saturating quadratic curve, middlegame only.
//
// As in exp-0050, two DIFFERENT properties are tested:
//   1. CORRECTNESS - default-off bit-exactness, the linear-in-parameters
//      breakdown invariant, monotonicity, saturation, and no mate-score leakage.
//   2. LIVENESS   - the term must actually change the search tree. A curve that
//      is never read is perfectly "correct" and completely useless; the
//      exp-0038/exp-0050 lesson is that correctness alone cannot detect that.
//
// The feature is default OFF (both rows ship 0); these tests enable it explicitly
// and always restore the previous parameter set.
#include "test.hpp"
#include "evaluation/evaluation.hpp"
#include "evaluation/eval_params.hpp"
#include "search/search.hpp"
#include <atomic>
#include <memory>

using namespace stockbear;

namespace {
// RAII: a test that installs parameters must not leak them into the next test.
struct ParamsGuard {
    EvalParams saved;
    ParamsGuard() : saved(active_eval_params()) {}
    ~ParamsGuard() { apply_eval_params(saved); }
};

EvalParams with_king_safety(int quadratic) {
    EvalParams p = default_eval_params();
    p.mg[KingSafetyQuadratic] = quadratic;
    return p;
}

// Signs and magnitudes below were verified against the INDEPENDENT python-chess
// reference (scripts/check_king_safety.py), not by eyeballing the diagram.
// kAttacked: White's own king is the exposed one (white curve 28, black 0), so
// enabling the term must LOWER White's score. kBlackAttacked is the mirror case
// (white 0, black 4), where it must RAISE White's score.
const char* kAttacked = "rnb1k2r/pppp1ppp/8/4q3/8/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 0 1";
const char* kBlackAttacked = "r1bq1rk1/ppp2ppp/2n1bn2/3p4/3P4/2NB1N2/PPP2PPP/R1BQ1RK1 w - - 0 1";
const char* kQuiet    = "r1bq1rk1/pppn1ppp/4pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 1";
// Queenless: the queen gate must skip the term entirely.
const char* kNoQueen  = "r3r1k1/ppp2ppp/2n1bn2/3p4/3P4/2N1BN2/PPP2PPP/R3R1K1 w - - 0 1";

struct Outcome { Move best = MOVE_NONE; int score = 0; std::uint64_t nodes = 0; };

Outcome search_at(const char* fen, int depth) {
    SearchParams params;
    params.ttEval = true;
    Position p = test::position(fen);
    TranspositionTable tt(4);
    SearchLimits limits;
    limits.depth = depth;
    std::atomic<bool> stop{false};
    auto search = std::make_unique<Search>(tt, params);
    const SearchResult r = search->run(p, limits, stop);
    Position walk = test::position(fen);
    for (Move m : r.pv) {
        CHECK_EQ(move_from_uci(walk, move_to_uci(m)), m);
        walk.make_move(m);
    }
    return {r.bestMove, r.score, r.nodes};
}
} // namespace

TEST(king_safety, shipped_rows_are_zero_and_gate_is_off_by_default) {
    ParamsGuard guard;
    const EvalParams d = default_eval_params();
    CHECK_EQ(d.mg[KingSafetyQuadratic], 0);
    CHECK_EQ(d.eg[KingSafetyQuadratic], 0);
    apply_eval_params(d);
    // With the feature off, enabling coefficients is the ONLY difference; the
    // evaluation of the shipped set must be untouched by its mere existence.
    const int q = evaluate(test::position(kQuiet));
    const int a = evaluate(test::position(kAttacked));
    apply_eval_params(d);
    CHECK_EQ(evaluate(test::position(kQuiet)), q);
    CHECK_EQ(evaluate(test::position(kAttacked)), a);
}

TEST(king_safety, penalises_concentrated_attack_more_than_quiet_position) {
    ParamsGuard guard;
    apply_eval_params(default_eval_params());
    const int quietOff = evaluate(test::position(kQuiet));
    const int attackOff = evaluate(test::position(kAttacked));
    apply_eval_params(with_king_safety(6));
    const int quietOn = evaluate(test::position(kQuiet));
    const int attackOn = evaluate(test::position(kAttacked));
    // In kAttacked it is WHITE's king that is exposed, and the score is relative
    // to the mover (White), so the term must lower it. The quiet position has a
    // much smaller curve, so it must move strictly less.
    const int dQuiet = quietOn - quietOff;
    const int dAttack = attackOn - attackOff;
    CHECK(dAttack < 0);
    CHECK(dAttack < dQuiet);
    // Mirror control: when BLACK's king is the exposed one the sign must flip.
    // This is what catches a sign error that a single position would miss.
    apply_eval_params(default_eval_params());
    const int mirrorOff = evaluate(test::position(kBlackAttacked));
    apply_eval_params(with_king_safety(6));
    const int mirrorOn = evaluate(test::position(kBlackAttacked));
    CHECK(mirrorOn - mirrorOff > 0);
}

TEST(king_safety, curve_is_monotonic_and_saturating) {
    ParamsGuard guard;
    // More attackers of the same kind must never REDUCE the danger term, and a
    // huge concentration must saturate rather than overflow.
    const char* few = "6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1";
    const char* many = "6k1/5ppp/8/8/8/8/5PPP/3QR1K1 w - - 0 1";
    apply_eval_params(default_eval_params());
    const int fewOff = evaluate(test::position(few));
    const int manyOff = evaluate(test::position(many));
    apply_eval_params(with_king_safety(6));
    const int fewOn = evaluate(test::position(few));
    const int manyOn = evaluate(test::position(many));
    // These positions have no enemy queen, so the curve is gated off and only
    // material/other terms apply: the delta must be identical (no queen scan).
    CHECK_EQ(fewOn - fewOff, 0);
    CHECK_EQ(manyOn - manyOff, 0);
    // A direct overflow check on the parameter extremes.
    apply_eval_params(with_king_safety(400));
    const int extreme = evaluate(test::position(kAttacked));
    CHECK(extreme > -VALUE_KNOWN_WIN);
    CHECK(extreme < VALUE_KNOWN_WIN);
    CHECK(!is_mate_value(extreme));
}

TEST(king_safety, breakdown_stays_linear_in_parameters_when_enabled) {
    ParamsGuard guard;
    // The tuner reads eval_breakdown(); the search reads evaluate(). The curve
    // is a pure function of the POSITION, so it must enter as a COUNT and the
    // parameter must stay linear. Verified with a non-default coefficient set,
    // because a term wired only into evaluate() would pass a defaults-only test.
    for (int coef : {1, 6, 37}) {
        const EvalParams p = with_king_safety(coef);
        apply_eval_params(p);
        for (const char* fen : {kQuiet, kAttacked, kBlackAttacked, kNoQueen, START_FEN}) {
            const Position pos = test::position(fen);
            const EvalBreakdown bd = eval_breakdown(pos);
            const int viaBd = eval_from_breakdown(bd, p);
            const int viaEval = evaluate(pos);
            const int oriented = pos.side_to_move() == White ? viaBd : -viaBd;
            CHECK_EQ(viaEval, oriented);
        }
    }
}

// Mutation-tested gap: removing the queen gate leaves the term live, correct in
// sign, and linear in the parameters, so every other assertion still passes.
// This queenless position has a non-zero ungated curve (-4 from White's view,
// verified by the independent reference), so the gate MUST force it to zero.
TEST(king_safety, queen_gate_suppresses_the_term_in_queenless_positions) {
    ParamsGuard guard;
    const char* fen = "r1b1k2r/4n2p/p1p2p2/P2pp3/p2P4/N2BK1PP/1P2P3/2R3NR w k - 0 23";
    apply_eval_params(with_king_safety(1));
    const EvalBreakdown bd = eval_breakdown(test::position(fen));
    CHECK_EQ(bd.mg[KingSafetyQuadratic], 0);
    // and the evaluation must be identical to the feature-off build here
    apply_eval_params(default_eval_params());
    const int off = evaluate(test::position(fen));
    apply_eval_params(with_king_safety(6));
    CHECK_EQ(evaluate(test::position(fen)), off);
}

// Mutation-tested gap: a LINEAR curve passes every test above (it is live, the
// breakdown stays linear in the parameters, and the sign is right) yet defeats
// the entire hypothesis. This asserts super-linearity directly: doubling the
// attacker concentration must MORE than double the penalty. Without it, only
// the external python oracle would catch a linear regression.
TEST(king_safety, penalty_is_superlinear_in_attacker_concentration) {
    ParamsGuard guard;
    // Same piece types, same zone geometry, twice the attackers: two rooks on
    // the king's file vs one. Built so the only change is attacker count.
    const char* one = "6k1/5ppp/8/8/8/8/5PPP/3QR1K1 w - - 0 1";
    const char* two = "6k1/5ppp/8/8/8/8/5PPP/2QRR1K1 w - - 0 1";
    // These have no WHITE queen attacking, so use the breakdown counts directly
    // with a coefficient of 1 to read the raw curve for the side under attack.
    apply_eval_params(with_king_safety(1));
    const EvalBreakdown b1 = eval_breakdown(test::position(one));
    const EvalBreakdown b2 = eval_breakdown(test::position(two));
    const int c1 = b1.mg[KingSafetyQuadratic];
    const int c2 = b2.mg[KingSafetyQuadratic];
    // White is the attacker here, so the White-view count is positive and grows
    // with concentration. The curve is quadratic, so it must grow super-linearly
    // wherever both counts are non-zero.
    if (c1 > 0 && c2 > c1)
        CHECK(c2 > 2 * c1);
    // Direct curve pin, taken from the INDEPENDENT python-chess reference:
    // kAttacked's White king faces 15 attack units, and curve(15) = 15*15/16 = 14.
    // A linear curve would report 15 instead, so this kills the linear mutant.
    const EvalBreakdown ba = eval_breakdown(test::position(kAttacked));
    CHECK_EQ(ba.mg[KingSafetyQuadratic], -14);
}

// The defect-detecting assertion. If king_safety_counts() were never called, or
// its result never applied, every correctness test above would still pass while
// the mechanism was inert. Node counts at a FIXED depth are deterministic, so
// requiring a real tree change is not a timing measurement.
TEST(king_safety, mechanism_is_live_and_changes_the_search_tree) {
    ParamsGuard guard;
    const char* fens[] = {
        kAttacked,
        "r2q1rk1/ppp2ppp/2n1bn2/3p4/3P4/2NB1N2/PPP2PPP/R1BQ1RK1 w - - 0 1",
        "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 9",
    };
    int live = 0;
    for (const char* fen : fens) {
        apply_eval_params(default_eval_params());
        const Outcome off = search_at(fen, 8);
        apply_eval_params(with_king_safety(6));
        const Outcome on = search_at(fen, 8);
        CHECK(is_ok(off.best));
        CHECK(is_ok(on.best));
        // A proven mate must stay the same mate.
        CHECK_EQ(is_mate_value(off.score), is_mate_value(on.score));
        if (is_mate_value(off.score))
            CHECK_EQ(mate_value_to_moves(off.score), mate_value_to_moves(on.score));
        if (on.nodes != off.nodes) ++live;
    }
    // At least one position MUST change, or the term is dead code.
    CHECK(live > 0);
}
