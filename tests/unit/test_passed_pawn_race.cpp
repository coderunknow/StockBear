// exp-0055 passed-pawn promotion race.
//
// The shipped evaluation scores a passer ONLY as advance^2 * PassedPawnAdvance.
// It cannot see whether its own king is escorting it, whether the enemy king is
// blockading the promotion square, or whether the path is blocked. King geometry
// is entirely absent from the parameter table, yet in an endgame it decides
// whether a passer becomes a queen or dies.
//
//   units = sum over passers of advance * (2*(7-ownKingDist)
//                                        - 2*(7-enemyKingDist)
//                                        - (6 if path blocked else 0))
//   clamped to [-64, +64]; ONE scale parameter, frozen mg=0 eg=1.
//
// Every pin below was derived from the INDEPENDENT python-chess reference
// (scripts/check_passed_pawn_race.py) by searching endgame positions for cases
// that discriminate the components. No hand-labelled diagrams (the exp-0052
// lesson). kBlocked alone kills removal of ANY of the three components.
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

EvalParams with_race(int mg, int eg) {
    EvalParams p = default_eval_params();
    p.mg[PassedPawnRace] = mg;
    p.eg[PassedPawnRace] = eg;
    return p;
}

// Oracle decomposition, White-positive expected count:
// kBlocked: White has 2 passers, own=64 enemy=88 blocked=24 -> raw -48.
//   Removing the blocked term gives -24; removing own-king gives -64 (clamped);
//   removing enemy-king gives +40. So this one position pins all three.
const char* kBlocked = "8/2k5/8/P1P5/8/K7/8/8 w - - 3 67";
// kSaturating: Black raw -68 clamps to -64, so the White-positive diff is +64.
//   Without the clamp it would be +68.
const char* kSaturating = "3k4/2p5/5p2/7b/6p1/1P4K1/8/8 w - - 0 33";
// Neither side has a passer -> exactly 0.
const char* kNoPassers = "6k1/8/8/2p4R/4K3/8/2P2N2/8 b - - 0 34";
// Black has the passer (own=16 enemy=12) -> White-positive diff -4.
const char* kMirror = "5k2/R1pn4/7p/8/3K4/8/2P2N2/8 b - - 0 29";
const char* kQuiet = "r1bq1rk1/pppn1ppp/4pn2/3p4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 1";

int race_count(const char* fen) {
    const EvalBreakdown bd = eval_breakdown(test::position(fen));
    return bd.eg[std::size_t(PassedPawnRace)];
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

TEST(passed_pawn_race, shipped_row_is_zero_and_default_untouched) {
    ParamsGuard guard;
    const EvalParams d = default_eval_params();
    CHECK_EQ(d.mg[PassedPawnRace], 0);
    CHECK_EQ(d.eg[PassedPawnRace], 0);
    apply_eval_params(d);
    const int q = evaluate(test::position(kQuiet));
    const int b = evaluate(test::position(kBlocked));
    apply_eval_params(d);
    CHECK_EQ(evaluate(test::position(kQuiet)), q);
    CHECK_EQ(evaluate(test::position(kBlocked)), b);
}

// Exact oracle pins. These catch a wrong weight, a wrong sign, a missing
// component, or a missing clamp -- none of which sign-only tests would pin.
TEST(passed_pawn_race, counts_match_the_independent_reference_exactly) {
    ParamsGuard guard;
    apply_eval_params(with_race(0, 1));
    CHECK_EQ(race_count(kBlocked), -48);
    CHECK_EQ(race_count(kSaturating), 64);
    CHECK_EQ(race_count(kNoPassers), 0);
    CHECK_EQ(race_count(kMirror), -4);
    // One count feeds both rows.
    const EvalBreakdown bd = eval_breakdown(test::position(kBlocked));
    CHECK_EQ(bd.mg[std::size_t(PassedPawnRace)], bd.eg[std::size_t(PassedPawnRace)]);
}

// Mutation-discriminating: kBlocked's -48 requires ALL THREE components with the
// correct weights. Any single component removed changes this number.
TEST(passed_pawn_race, all_three_components_are_pinned) {
    ParamsGuard guard;
    apply_eval_params(with_race(0, 1));
    CHECK_EQ(race_count(kBlocked), -48);
    // Positive control so the pin above cannot be satisfied by a dead term.
    CHECK_EQ(race_count(kSaturating), 64);
}

TEST(passed_pawn_race, clamps_symmetrically_and_leaks_no_mate_score) {
    ParamsGuard guard;
    apply_eval_params(with_race(0, 1));
    // Black's raw -68 must clamp to -64 (diff +64), not pass through as +68.
    CHECK_EQ(race_count(kSaturating), 64);
    for (int coef : {400, -400}) {
        apply_eval_params(with_race(coef, coef));
        for (const char* fen : {kBlocked, kSaturating, kNoPassers, kMirror, START_FEN}) {
            const int v = evaluate(test::position(fen));
            CHECK(v >= -VALUE_KNOWN_WIN);
            CHECK(v <= VALUE_KNOWN_WIN);
            CHECK(!is_mate_value(v));
        }
    }
}

TEST(passed_pawn_race, breakdown_stays_linear_in_parameters) {
    ParamsGuard guard;
    for (int coef : {1, 3, 17}) {
        const EvalParams p = with_race(0, coef);
        apply_eval_params(p);
        for (const char* fen : {kBlocked, kSaturating, kNoPassers, kMirror, START_FEN}) {
            const Position pos = test::position(fen);
            const EvalBreakdown bd = eval_breakdown(pos);
            const int expected = race_count(fen);
            CHECK_EQ(bd.eg[std::size_t(PassedPawnRace)], expected);
            const int viaBd = eval_from_breakdown(bd, p);
            const int oriented = pos.side_to_move() == White ? viaBd : -viaBd;
            CHECK_EQ(evaluate(pos), oriented);
        }
    }
}

// The term is frozen mg=0 eg=1, so it must act through the ENDGAME row. This
// pins the taper wiring in BOTH directions, which is stronger than simply
// checking that "some row moves the score":
//   * kBlocked is a pure pawn endgame, so phase_of() == 0 and the mg row CANNOT
//     contribute there, while the eg row must.
//   * kMaterial has phase 16 (> 0), so there the mg row MUST contribute too.
// An earlier version of this test wrongly expected mg to act at phase 0; the
// engine was right and the assertion was corrected.
TEST(passed_pawn_race, mg_and_eg_rows_are_wired_through_the_taper) {
    ParamsGuard guard;
    // Oracle: race diff -48, and no minor/major pieces at all -> phase 0.
    apply_eval_params(with_race(0, 0));
    const int off = evaluate(test::position(kBlocked));
    apply_eval_params(with_race(1, 0));
    const int mgOnly = evaluate(test::position(kBlocked));
    apply_eval_params(with_race(0, 1));
    const int egOnly = evaluate(test::position(kBlocked));
    CHECK_EQ(mgOnly, off);   // phase 0 => mg has no weight
    CHECK(egOnly != off);    // eg carries the full weight
    CHECK(egOnly < off);     // count is negative

    // Oracle: race diff +32 with phase 16, so BOTH rows have weight here.
    const char* kMaterial = "r5n1/4N1kr/npp3p1/6pp/pP3p2/3PP3/b4qBP/2K3NR w - - 0 31";
    CHECK_EQ(race_count(kMaterial), 32);
    apply_eval_params(with_race(0, 0));
    const int mOff = evaluate(test::position(kMaterial));
    apply_eval_params(with_race(1, 0));
    const int mMg = evaluate(test::position(kMaterial));
    apply_eval_params(with_race(0, 1));
    const int mEg = evaluate(test::position(kMaterial));
    CHECK(mMg > mOff);       // positive count, mg has weight at phase 16
    CHECK(mEg > mOff);       // and so does eg
}

TEST(passed_pawn_race, mechanism_is_live_and_changes_the_search_tree) {
    ParamsGuard guard;
    const char* fens[] = {
        kBlocked, kSaturating, kMirror,
        "8/2k5/8/P1P5/8/K7/8/8 w - - 3 67",
        "6k1/8/8/2p4R/4K3/8/2P2N2/8 b - - 0 34",
        "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 9",
    };
    int live = 0;
    for (const char* fen : fens) {
        apply_eval_params(default_eval_params());
        const Outcome off = search_at(fen, 8);
        apply_eval_params(with_race(0, 1));
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
