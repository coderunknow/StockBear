// exp-0053 material-exposure (threat) detection.
//
// StockBear had NO threat term: an undefended enemy piece, or one attacked by a
// pawn, was invisible to static evaluation. At median depth 5 that is a real
// representational gap. This term counts
//     hanging    = enemy non-pawn pieces attacked by us and NOT defended by them
//     pawnThreat = any enemy piece attacked by one of our pawns
//     units      = min(10*|hanging| + 16*|pawnThreat|, 64)
// and enters as ONE parameter (ThreatDetection), mg and eg.
//
// Two DIFFERENT properties are tested, because exp-0038/0050/0052 showed that
// correctness alone cannot detect a dead or mis-shaped mechanism:
//   1. CORRECTNESS - default-off bit-exactness, exact oracle-derived counts,
//      linear-in-parameters breakdown, saturation, no mate-score leakage.
//   2. LIVENESS    - the term must actually change the search tree.
//
// Every pin below was derived from the INDEPENDENT python-chess reference
// (scripts/check_threats.py) by searching random positions for cases that
// discriminate ONE component each. Hand-labelled diagrams were the cause of a
// false test failure in exp-0052, so none are used here.
#include "test.hpp"
#include "evaluation/evaluation.hpp"
#include "evaluation/eval_params.hpp"
#include "search/search.hpp"
#include <atomic>
#include <memory>

using namespace stockbear;

namespace {
struct ParamsGuard {
    EvalParams saved;
    ParamsGuard() : saved(active_eval_params()) {}
    ~ParamsGuard() { apply_eval_params(saved); }
};

EvalParams with_threats(int mg, int eg) {
    EvalParams p = default_eval_params();
    p.mg[ThreatDetection] = mg;
    p.eg[ThreatDetection] = eg;
    return p;
}

// Oracle-verified positions. The comment on each is the reference's own
// decomposition, and the expected White-positive breakdown count.
//
// White has exactly one hanging enemy piece and no pawn threat -> +10.
const char* kHanging = "r1bqkb2/pp3ppr/3pp2p/8/PPpnPPn1/6PN/R1PPQ1BP/1NB1K1R1 w - - 0 15";
// Mirror: Black has one hanging piece and one pawn threat -> -26.
const char* kMirror = "1r2qbkr/2pppn1p/pp1B1pp1/3N4/1P5P/P5R1/2RPPPB1/3QK1N1 w - - 3 23";
// White attacks TWO enemy non-pawn pieces but BOTH are defended, and there is no
// pawn threat -> 0. Dropping the ~defThem mask would yield +20 here.
const char* kDefended = "1r3kr1/3bqp1p/p1p3p1/1pn1p1P1/4n3/2PQ3P/PB2KP1R/2R2BN1 b - - 0 21";
// White has one pawn threat and NO hanging piece -> +16. Removing the pawn
// component would yield 0 here.
const char* kPawnOnly = "r1b3nr/ppppkp2/n4qpp/1B2p3/1b2P3/PP3N2/1NPP1PPP/1RBQK2R b K - 9 9";
// Both sides exceed the cap (White raw 74, Black raw 84) so both clamp to 64 and
// the difference is 0. Without the cap this would be -10.
const char* kSaturating = "rn1k1b2/1qp1p3/1P1p4/p1p1npp1/P1bPP1P1/3B1p1r/N7/R1B1K1NR b - - 0 24";
const char* kQuiet = "r1bq1rk1/pppn1ppp/4pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 1";

int threat_count(const char* fen) {
    const EvalBreakdown bd = eval_breakdown(test::position(fen));
    return bd.mg[std::size_t(ThreatDetection)];
}

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

TEST(threats, shipped_row_is_zero_and_default_evaluation_is_untouched) {
    ParamsGuard guard;
    const EvalParams d = default_eval_params();
    CHECK_EQ(d.mg[ThreatDetection], 0);
    CHECK_EQ(d.eg[ThreatDetection], 0);
    apply_eval_params(d);
    const int q = evaluate(test::position(kQuiet));
    const int h = evaluate(test::position(kHanging));
    apply_eval_params(d);
    CHECK_EQ(evaluate(test::position(kQuiet)), q);
    CHECK_EQ(evaluate(test::position(kHanging)), h);
}

// Exact pins. These are what catch a wrong weight, a wrong sign, or a missing
// component -- properties that sign-only or monotonicity tests do not pin.
TEST(threats, counts_match_the_independent_reference_exactly) {
    ParamsGuard guard;
    apply_eval_params(with_threats(1, 1));
    CHECK_EQ(threat_count(kHanging), 10);
    CHECK_EQ(threat_count(kMirror), -26);
    CHECK_EQ(threat_count(kDefended), 0);
    CHECK_EQ(threat_count(kPawnOnly), 16);
    CHECK_EQ(threat_count(kSaturating), 0);
    // The eg row carries the same count as mg (one count, two coefficients).
    const EvalBreakdown bd = eval_breakdown(test::position(kHanging));
    CHECK_EQ(bd.eg[std::size_t(ThreatDetection)], bd.mg[std::size_t(ThreatDetection)]);
}

// Mutation-discriminating: an attacked piece that is DEFENDED is not hanging.
// Without the ~defThem mask kDefended would score +20 while every sign and
// linearity assertion elsewhere still passed.
TEST(threats, defended_pieces_are_not_hanging) {
    ParamsGuard guard;
    apply_eval_params(with_threats(1, 1));
    CHECK_EQ(threat_count(kDefended), 0);
    // Positive control: a genuinely undefended piece IS counted, so the zero
    // above cannot be produced by the whole term being dead.
    CHECK_EQ(threat_count(kHanging), 10);
}

// Mutation-discriminating: the pawn-threat component must exist independently of
// the hanging component (kPawnOnly has zero hanging pieces).
TEST(threats, pawn_threats_are_counted_independently) {
    ParamsGuard guard;
    apply_eval_params(with_threats(1, 1));
    CHECK_EQ(threat_count(kPawnOnly), 16);
}

// Mutation-discriminating: the cap must clamp BOTH sides before subtraction.
TEST(threats, units_saturate_at_the_cap_on_both_sides) {
    ParamsGuard guard;
    apply_eval_params(with_threats(1, 1));
    CHECK_EQ(threat_count(kSaturating), 0);
    // No mate-score leakage at the parameter extremes.
    // taper() clamps INCLUSIVELY to +/-VALUE_KNOWN_WIN (10000), which is a
    // heuristic "clearly winning" bound far below MATE_BOUND (~29900). Reaching
    // exactly 10000 at an absurd coefficient is the pre-existing clamp working,
    // not mate-score leakage. The meaningful invariant is therefore the
    // inclusive bound PLUS no mate encoding, asserted at both sign extremes.
    for (int coef : {400, -400}) {
        apply_eval_params(with_threats(coef, coef));
        for (const char* fen : {kSaturating, kHanging, kMirror, START_FEN}) {
            const int v = evaluate(test::position(fen));
            CHECK(v >= -VALUE_KNOWN_WIN);
            CHECK(v <= VALUE_KNOWN_WIN);
            CHECK(!is_mate_value(v));
        }
    }
    // At the FROZEN coefficient the term is bounded by the 64-unit cap, i.e.
    // at most 64 cp per side -- it must not come close to the clamp.
    apply_eval_params(with_threats(1, 1));
    for (const char* fen : {kSaturating, kHanging, kMirror, START_FEN}) {
        const int v = evaluate(test::position(fen));
        CHECK(v > -VALUE_KNOWN_WIN / 2);
        CHECK(v < VALUE_KNOWN_WIN / 2);
    }
}

// The tuner reads eval_breakdown(); the search reads evaluate(). The count is a
// pure function of the POSITION, so the parameter must stay linear. Checked at
// non-default coefficients, because a term wired only into evaluate() would pass
// a defaults-only test.
TEST(threats, breakdown_stays_linear_in_parameters_when_enabled) {
    ParamsGuard guard;
    for (int coef : {1, 3, 17}) {
        const EvalParams p = with_threats(coef, coef);
        apply_eval_params(p);
        for (const char* fen : {kHanging, kMirror, kDefended, kPawnOnly, kSaturating, START_FEN}) {
            const Position pos = test::position(fen);
            const EvalBreakdown bd = eval_breakdown(pos);
            // The count itself must not depend on the coefficient.
            const int expected = threat_count(fen);
            CHECK_EQ(bd.mg[std::size_t(ThreatDetection)], expected);
            const int viaBd = eval_from_breakdown(bd, p);
            const int viaEval = evaluate(pos);
            const int oriented = pos.side_to_move() == White ? viaBd : -viaBd;
            CHECK_EQ(viaEval, oriented);
        }
    }
}

// Sign/orientation control: kMirror is the Black-favouring case, so enabling the
// term must move White's relativised score the opposite way from kHanging.
TEST(threats, sign_is_correct_and_mirrors) {
    ParamsGuard guard;
    apply_eval_params(default_eval_params());
    const int hOff = evaluate(test::position(kHanging));
    const int mOff = evaluate(test::position(kMirror));
    apply_eval_params(with_threats(1, 1));
    const int hOn = evaluate(test::position(kHanging));
    const int mOn = evaluate(test::position(kMirror));
    // Both FENs have White to move, so White-positive counts raise the score.
    CHECK(hOn - hOff > 0);
    CHECK(mOn - mOff < 0);
}

// LIVENESS: a term that is computed but never applied is perfectly "correct"
// and completely useless. This is the exp-0050 lesson.
TEST(threats, mechanism_is_live_and_changes_the_search_tree) {
    ParamsGuard guard;
    const char* fens[] = {
        kHanging,
        kMirror,
        kPawnOnly,
        "r2q1rk1/ppp2ppp/2n1bn2/3p4/3P4/2NB1N2/PPP2PPP/R1BQ1RK1 w - - 0 1",
        "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 9",
    };
    int live = 0;
    for (const char* fen : fens) {
        apply_eval_params(default_eval_params());
        const Outcome off = search_at(fen, 8);
        apply_eval_params(with_threats(1, 1));
        const Outcome on = search_at(fen, 8);
        CHECK(is_ok(off.best));
        CHECK(is_ok(on.best));
        CHECK_EQ(is_mate_value(off.score), is_mate_value(on.score));
        if (is_mate_value(off.score))
            CHECK_EQ(mate_value_to_moves(off.score), mate_value_to_moves(on.score));
        if (on.nodes != off.nodes) ++live;
    }
    CHECK(live > 0);
}
