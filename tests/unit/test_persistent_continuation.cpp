// exp-0066: persistent continuation history (single-factor lifetime ablation).
//
// continuation_ is a graded statistic that run() zeroes on every root search.
// With PersistentContinuation it is carried across searches and halved instead.
// The FEATURE switch ContinuationHistory must also be on, because the update
// sites are gated on it; the frozen experiment enables it in both arms.
//
// Lessons from earlier cycles are encoded here deliberately:
//  * the TT is cleared before EVERY probe search, so these tests measure table
//    lifetime and not transposition-table reuse (a prior test got this wrong);
//  * mate fixtures are genuine checkmates, verified by delivering mate, not
//    stalemates (a prior fixture got this wrong);
//  * object-lifetime behaviour that this in-process suite cannot observe is
//    covered by scripts/check_persistent_continuation_uci.py, because two
//    mutants previously survived an in-process-only suite.
#include "test.hpp"
#include "chess/zobrist.hpp"
#include "evaluation/eval_params.hpp"
#include "search/search.hpp"
#include "search/transposition_table.hpp"
#include "uci/uci.hpp"
#include "utilities/types.hpp"
#include <atomic>
#include <memory>
#include <sstream>

using namespace stockbear;

namespace {

const char* kFenA = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 4";
const char* kFenB = "r2q1rk1/pp2ppbp/2np1np1/8/2BNP3/2N1BP2/PPPQ2PP/2KR3R w - - 5 11";

// Genuine checkmate: Qg7 is adjacent to Kh8 and defended by Kg6.
const char* kMated = "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1";
// Same king/queen placement but Qf7 does NOT check h8 -> STALEMATE, not mate.
const char* kStalemate = "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1";
const char* kMateInOne = "7k/5Q2/6K1/8/8/8/8/8 w - - 0 1";

SearchParams params_with(bool persistent, bool feature = true, bool improving = false) {
    SearchParams sp;
    sp.ttEval = true;
    sp.continuationHistory = feature;
    sp.persistentContinuation = persistent;
    sp.improving = improving;
    return sp;
}

// Clearing the TT first is essential: otherwise a second search differs merely
// because of hash hits and the test would not be about history lifetime at all.
SearchResult run_on(Search& s, TranspositionTable& tt, const char* fen, int depth) {
    tt.clear();
    Position p = test::position(fen);
    SearchLimits lim;
    lim.depth = depth;
    std::atomic<bool> stop{false};
    return s.run(p, lim, stop);
}

} // namespace

TEST(persistent_continuation, shipped_defaults_are_off) {
    SearchParams sp;
    CHECK_EQ(sp.persistentContinuation, false);
    CHECK_EQ(sp.persistentHistory, false);
    CHECK_EQ(sp.continuationHistory, false);
}

TEST(persistent_continuation, off_makes_reused_object_identical_to_fresh) {
    // `improving` is enabled so evalStack_ is actually read at low plies.
    TranspositionTable ttA(4), ttB(4);
    auto sp = params_with(false, true, true);
    Search reused(ttA, sp);
    const SearchResult r1 = run_on(reused, ttA, kFenA, 6);
    const SearchResult r2 = run_on(reused, ttA, kFenB, 6);
    const SearchResult r3 = run_on(reused, ttA, kFenA, 6);
    Search freshB(ttB, sp);
    const SearchResult f2 = run_on(freshB, ttB, kFenB, 6);
    Search freshC(ttB, sp);
    const SearchResult f3 = run_on(freshC, ttB, kFenA, 6);
    CHECK(r1.nodes > 0);
    CHECK_EQ(r2.nodes, f2.nodes);
    CHECK_EQ(r2.score, f2.score);
    CHECK_EQ(r3.nodes, f3.nodes);
    CHECK_EQ(r3.score, f3.score);
    CHECK_EQ(r1.nodes, r3.nodes);
}

TEST(persistent_continuation, on_carries_state_and_changes_the_tree) {
    TranspositionTable tt(4);
    Search s(tt, params_with(true));
    const SearchResult first = run_on(s, tt, kFenA, 7);
    const SearchResult second = run_on(s, tt, kFenA, 7);
    CHECK(first.nodes > 0);
    CHECK(second.nodes > 0);
    // Identical position, TT cleared both times: only carried continuation
    // state can explain a different tree.
    CHECK(first.nodes != second.nodes);
}

TEST(persistent_continuation, persistence_is_inert_when_the_feature_is_off) {
    // Source-derived property: both the read and the update of continuation_
    // are gated on params_.continuationHistory, so with the feature OFF nothing
    // is ever written and persisting the table must be an exact no-op.
    TranspositionTable ttOff(4), ttOn(4);
    Search off(ttOff, params_with(false, false));
    Search on(ttOn, params_with(true, false));
    const char* seq[] = {kFenA, kFenB, kFenA, kFenB};
    for (const char* fen : seq) {
        const SearchResult a = run_on(off, ttOff, fen, 7);
        const SearchResult b = run_on(on, ttOn, fen, 7);
        CHECK_EQ(a.nodes, b.nodes);
        CHECK_EQ(a.score, b.score);
    }
}

TEST(persistent_continuation, counter_move_table_is_not_persisted) {
    // The prereg deliberately excludes counter-move persistence. With the
    // continuation feature OFF and counter-moves ON, turning the new switch on
    // must change nothing: only continuation_ has a lifetime branch.
    TranspositionTable ttOff(4), ttOn(4);
    auto spOff = params_with(false, false);
    auto spOn = params_with(true, false);
    spOff.counterMoves = true;
    spOn.counterMoves = true;
    Search off(ttOff, spOff), on(ttOn, spOn);
    const char* seq[] = {kFenA, kFenB, kFenA, kFenB};
    for (const char* fen : seq) {
        const SearchResult a = run_on(off, ttOff, fen, 7);
        const SearchResult b = run_on(on, ttOn, fen, 7);
        CHECK_EQ(a.nodes, b.nodes);
        CHECK_EQ(a.score, b.score);
    }
}

TEST(persistent_continuation, mate_and_draw_scores_are_not_corrupted) {
    TranspositionTable ttOff(4), ttOn(4);
    Search off(ttOff, params_with(false));
    Search on(ttOn, params_with(true));
    // Warm the persisted table first so the checks run with non-empty state.
    run_on(on, ttOn, kFenA, 6);
    run_on(on, ttOn, kFenB, 6);
    CHECK_EQ(run_on(on, ttOn, kMated, 3).score, -VALUE_MATE);
    CHECK_EQ(run_on(off, ttOff, kMated, 3).score, -VALUE_MATE);
    CHECK_EQ(run_on(on, ttOn, kStalemate, 3).score, 0);
    CHECK_EQ(run_on(on, ttOn, "4k3/8/8/8/8/8/8/4K3 w - - 0 1", 4).score, 0);
    // A real mate must keep its exact distance AND deliver checkmate.
    const SearchResult m1 = run_on(on, ttOn, kMateInOne, 3);
    CHECK(is_mate_value(m1.score));
    CHECK_EQ(mate_value_to_moves(m1.score), 1);
    Position p = test::position(kMateInOne);
    p.make_move(m1.bestMove);
    CHECK(p.in_check());
    CHECK(!p.has_legal_moves());
}

TEST(persistent_continuation, node_limited_and_infinite_modes_are_safe) {
    // All relevant search modes must tolerate a reused, non-empty table.
    TranspositionTable tt(4);
    Search s(tt, params_with(true));
    run_on(s, tt, kFenA, 6);
    Position p = test::position(kFenB);
    SearchLimits lim;
    lim.hasNodes = true;
    lim.nodes = 5000;
    std::atomic<bool> stop{false};
    const SearchResult limited = s.run(p, lim, stop);
    CHECK_EQ(limited.nodes, 5000ULL);
    CHECK(is_ok(move_from_uci(p, move_to_uci(limited.bestMove))));
    SearchLimits inf;
    inf.infinite = true;
    stop.store(true);
    const SearchResult immediate = s.run(p, inf, stop);
    CHECK_EQ(immediate.nodes, 0ULL);
    CHECK(is_ok(move_from_uci(p, move_to_uci(immediate.bestMove))));
}

TEST(persistent_continuation, uci_option_is_advertised_and_accepted) {
    std::istringstream in("uci\nsetoption name PersistentContinuation value true\n"
                          "setoption name PersistentContinuation value false\nquit\n");
    std::ostringstream out;
    { UciEngine engine(in, out); engine.loop(); }
    const std::string s = out.str();
    CHECK(s.find("option name PersistentContinuation type check default false") != std::string::npos);
    CHECK(s.find("info string setoption:") == std::string::npos);
}

TEST(persistent_continuation, wiring_characterization_pins) {
    // Locks the wiring AND the halving decay to the audited behaviour so a
    // decay-removed / decay-doubled / clearing-kept / wrong-table edit cannot
    // pass unnoticed. Over four alternating positions with a cleared TT the
    // carried table is still partly stale; the mechanism's benefit is measured
    // over real game sequences by the frozen sequential-replay gate.
    const EvalParams saved = active_eval_params();
    apply_eval_params(default_eval_params());
    const char* seq[] = {kFenA, kFenB, kFenA, kFenB};
    const unsigned long long offPins[] = {29153ULL, 37911ULL, 29153ULL, 37911ULL};
    const unsigned long long onPins[] = {29153ULL, 37916ULL, 25730ULL, 36912ULL};
    for (int on = 0; on < 2; ++on) {
        TranspositionTable tt(4);
        Search s(tt, params_with(on == 1));
        for (int i = 0; i < 4; ++i) {
            const SearchResult r = run_on(s, tt, seq[i], 7);
            CHECK_EQ(r.nodes, on ? onPins[i] : offPins[i]);
        }
    }
    apply_eval_params(saved);
}
