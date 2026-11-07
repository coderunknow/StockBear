// exp-0065: persistent cross-move quiet history.
//
// Shipped behaviour zeroes history_ in run() AND builds a fresh Search per go,
// so quiet-ordering learning never survives a move. With PersistentHistory the
// table is carried over and halved instead, and UciEngine keeps one Search alive
// until ucinewgame. These tests pin: the default is OFF; a REUSED object with the
// switch OFF is indistinguishable from a FRESH one (no state leaks, including
// evalStack_ when `improving` reads it); with ON the carried table observably
// changes the tree; and terminal scores are unaffected.
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

SearchParams params_with(bool persistent, bool improving = false) {
    SearchParams sp;
    sp.ttEval = true;
    sp.improving = improving;
    sp.persistentHistory = persistent;
    return sp;
}

// The TT is cleared before EVERY search so the only state that can differ
// between two runs is the Search object's own tables. Without this the test
// would measure transposition-table reuse, not history lifetime.
SearchResult run_on(Search& s, TranspositionTable& tt, const char* fen, int depth) {
    tt.clear();
    Position p = test::position(fen);
    SearchLimits lim;
    lim.depth = depth;
    std::atomic<bool> stop{false};
    return s.run(p, lim, stop);
}

} // namespace

TEST(persistent_history, shipped_default_is_off) {
    SearchParams sp;
    CHECK_EQ(sp.persistentHistory, false);
}

TEST(persistent_history, off_makes_reused_object_identical_to_fresh) {
    // The load-bearing safety property: with the switch OFF, reusing the object
    // must be indistinguishable from constructing a new one. `improving` is
    // enabled deliberately so evalStack_ is actually READ at low plies.
    TranspositionTable ttA(4), ttB(4);
    auto sp = params_with(false, true);
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
    // A cleared table also makes the repeated search deterministic.
    CHECK_EQ(r1.nodes, r3.nodes);
}

TEST(persistent_history, on_carries_history_and_changes_the_tree) {
    TranspositionTable tt(4);
    Search s(tt, params_with(true));
    const SearchResult first = run_on(s, tt, kFenA, 7);
    const SearchResult second = run_on(s, tt, kFenA, 7);
    CHECK(first.nodes > 0);
    CHECK(second.nodes > 0);
    // Carried (halved) history changes quiet ordering, so the identical position
    // searched twice on the same object must NOT give the shipped repeated tree.
    CHECK(first.nodes != second.nodes);
}

TEST(persistent_history, on_differs_from_off_over_a_move_sequence) {
    TranspositionTable ttOff(4), ttOn(4);
    Search off(ttOff, params_with(false));
    Search on(ttOn, params_with(true));
    const char* seq[] = {kFenA, kFenB, kFenA, kFenB};
    unsigned long long noOff = 0, noOn = 0;
    for (const char* fen : seq) {
        noOff += run_on(off, ttOff, fen, 7).nodes;
        noOn += run_on(on, ttOn, fen, 7).nodes;
    }
    CHECK(noOff > 0);
    CHECK(noOn > 0);
    CHECK(noOff != noOn);
}

TEST(persistent_history, terminal_scores_unaffected) {
    TranspositionTable ttOff(4), ttOn(4);
    Search off(ttOff, params_with(false));
    Search on(ttOn, params_with(true));
    // Checkmated side: Qg7 adjacent to Kh8, defended by Kg6.
    CHECK_EQ(run_on(on, ttOn, "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", 3).score, -VALUE_MATE);
    CHECK_EQ(run_on(off, ttOff, "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", 3).score, -VALUE_MATE);
    // Stalemate and bare kings stay draws in both arms.
    CHECK_EQ(run_on(on, ttOn, "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", 3).score, 0);
    CHECK_EQ(run_on(on, ttOn, "4k3/8/8/8/8/8/8/4K3 w - - 0 1", 4).score, 0);
    // A forced mate keeps its exact distance with the switch ON.
    const SearchResult m1 = run_on(on, ttOn, "7k/5Q2/6K1/8/8/8/8/8 w - - 0 1", 3);
    CHECK(is_mate_value(m1.score));
    CHECK_EQ(mate_value_to_moves(m1.score), 1);
}

TEST(persistent_history, uci_option_is_advertised_and_accepted) {
    std::istringstream in("uci\nsetoption name PersistentHistory value true\n"
                          "setoption name PersistentHistory value false\nquit\n");
    std::ostringstream out;
    { UciEngine engine(in, out); engine.loop(); }
    const std::string s = out.str();
    CHECK(s.find("option name PersistentHistory type check default false") != std::string::npos);
    CHECK(s.find("info string setoption:") == std::string::npos);
}

TEST(persistent_history, wiring_characterization_pins) {
    // Locks the wiring AND the halving decay to the audited behaviour, so a
    // decay-removed / decay-doubled / clearing-kept edit cannot pass unnoticed.
    // NOTE: over only four alternating positions with a cleared TT the carried
    // table is still stale and costs nodes; the mechanism's benefit appears over
    // a real game sequence, which is what the frozen sequential-replay gate
    // measures (20 real games, 2,525 positions, ratio 0.9654).
    const EvalParams saved = active_eval_params();
    apply_eval_params(default_eval_params());
    const char* seq[] = {kFenA, kFenB, kFenA, kFenB};
    const unsigned long long offPins[] = {29340ULL, 37914ULL, 29340ULL, 37914ULL};
    const unsigned long long onPins[] = {29340ULL, 54084ULL, 29027ULL, 45665ULL};
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
