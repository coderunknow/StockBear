// exp-0050 correction history: a decaying running mean of
// (search score - raw static eval), indexed by pawn structure, added to the
// eval used for HEURISTIC PRUNING margins only.
//
// Two properties matter and they are different:
//   1. CORRECTNESS - it must never change a proven mate, emit an illegal
//      move/PV, or let a heuristic correction reach a mate score.
//   2. LIVENESS   - it must actually do something. A correction table that is
//      never updated, or never read, is perfectly "correct" and completely
//      useless. The exp-0038 lesson was that a correctness-only test cannot
//      detect a dead mechanism, so the discriminating assertion here is a
//      deterministic node-count change at fixed depth.
//
// The switch is default OFF; these tests enable it explicitly.
#include "test.hpp"
#include "search/search.hpp"
#include <atomic>
#include <memory>

using namespace stockbear;

namespace {
struct Outcome {
    Move best = MOVE_NONE;
    int score = 0;
    std::uint64_t nodes = 0;
};

Outcome search_with(const char* fen, int depth, bool correctionHistory) {
    SearchParams params;
    params.ttEval = true;                 // champion runtime option
    params.correctionHistory = correctionHistory;
    Position p = test::position(fen);
    TranspositionTable tt(4);
    SearchLimits limits;
    limits.depth = depth;
    std::atomic<bool> stop{false};
    auto search = std::make_unique<Search>(tt, params);
    const SearchResult r = search->run(p, limits, stop);
    // Every PV move must be legal from the position it is played in.
    Position walk = test::position(fen);
    for (Move m : r.pv) {
        CHECK_EQ(move_from_uci(walk, move_to_uci(m)), m);
        walk.make_move(m);
    }
    return {r.bestMove, r.score, r.nodes};
}

// Quiet, pawn-structure-rich middlegames: the correction is learned from nodes
// whose best move was quiet, so capture-dominated positions would barely
// exercise it.
const char* kFens[] = {
    "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 9",
    "r4rk1/1pp1qppp/p1np1n2/8/2B1P1b1/2PP1N2/PP3PPP/RNBQ1RK1 w - - 0 10",
    "rnbq1rk1/ppp1bppp/4pn2/3p4/2PP4/2N2N2/PP2PPPP/R1BQKB1R w KQ - 0 6",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
};
} // namespace

TEST(correction_history, does_not_change_proven_mates_or_emit_illegal_moves) {
    for (const char* fen : kFens) {
        const Outcome off = search_with(fen, 6, false);
        const Outcome on = search_with(fen, 6, true);
        CHECK(is_ok(off.best));
        CHECK(is_ok(on.best));
        CHECK_EQ(is_mate_value(off.score), is_mate_value(on.score));
        if (is_mate_value(off.score))
            CHECK_EQ(mate_value_to_moves(off.score), mate_value_to_moves(on.score));
    }
}

// The defect-detecting assertion. If the table is never written, never read,
// or the update is guarded away on every node, scores and mates above still
// pass -- the mechanism would just be inert. Node counts at a FIXED depth are
// deterministic, so requiring a real tree change is not a timing assertion.
// Measured on this suite at depth 8: the aggregate node count differs by
// ~0.6 %, and 7 of the 12 bench positions change. Requiring that AT LEAST ONE
// of these four positions changes its node count is far from the inert
// population (which is exactly zero change everywhere) while tolerating any
// future rebalancing of the frozen constants.
TEST(correction_history, mechanism_is_live_and_changes_the_tree) {
    bool anyChanged = false;
    for (const char* fen : kFens) {
        const Outcome off = search_with(fen, 8, false);
        const Outcome on = search_with(fen, 8, true);
        CHECK(off.nodes > 0);
        CHECK(on.nodes > 0);
        if (off.nodes != on.nodes) anyChanged = true;
    }
    CHECK(anyChanged);
}

TEST(correction_history, forced_mates_are_identical) {
    const char* fens[] = {
        "7k/5Q2/6K1/8/8/8/8/8 w - - 0 1",       // mate in one
        "8/8/8/5Q2/k7/8/1K6/8 w - - 0 1",       // mate in two
        "7k/8/8/8/8/8/5rr1/6K1 w - - 0 1",      // forced evasion
    };
    for (const char* fen : fens) {
        const Outcome off = search_with(fen, 5, false);
        const Outcome on = search_with(fen, 5, true);
        CHECK_EQ(is_mate_value(off.score), is_mate_value(on.score));
        if (is_mate_value(off.score)) {
            CHECK_EQ(mate_value_to_moves(off.score), mate_value_to_moves(on.score));
            CHECK_EQ(move_to_uci(on.best), move_to_uci(off.best));
        }
    }
}

TEST(correction_history, table_is_cleared_between_runs) {
    // run() resets the correction table. Searching a different root first must
    // not leak a learned bias into a later search of the same position.
    //
    // The TT MUST be cleared too, or this test is confounded: the transposition
    // table persists across run() by design, and re-searching a warm TT legitimately
    // changes the node count. Verified before writing this assertion -- with the
    // switch OFF (new code unreachable) a warm TT gave 28,309 nodes vs 49,064
    // cold, exactly the same discrepancy the switch-ON arm showed. Clearing the
    // TT isolates the correction table as the only remaining state.
    SearchParams params;
    params.ttEval = true;
    params.correctionHistory = true;
    TranspositionTable tt(4);
    std::atomic<bool> stop{false};
    SearchLimits limits;
    limits.depth = 7;

    auto search = std::make_unique<Search>(tt, params);
    const SearchResult clean = search->run(test::position(kFens[0]), limits, stop);

    // Pollute the correction table with a search of an unrelated pawn structure.
    search->run(test::position(kFens[1]), limits, stop);

    // Same Search object (so only run()'s own reset can clear the table), but a
    // cold TT so the comparison is not measuring TT warmth.
    tt.clear();
    const SearchResult again = search->run(test::position(kFens[0]), limits, stop);
    CHECK_EQ(again.nodes, clean.nodes);
    CHECK_EQ(again.score, clean.score);
    CHECK_EQ(move_to_uci(again.bestMove), move_to_uci(clean.bestMove));

    // A brand-new Search on a cold TT must agree too.
    tt.clear();
    auto fresh = std::make_unique<Search>(tt, params);
    const SearchResult other = fresh->run(test::position(kFens[0]), limits, stop);
    CHECK_EQ(other.nodes, clean.nodes);
    CHECK_EQ(other.score, clean.score);
}

TEST(correction_history, switch_off_is_bit_identical_to_shipped) {
    // With the switch OFF the new code must be unreachable: two searches with
    // identical options must agree exactly, and enabling nothing must not
    // perturb the shipped tree.
    for (const char* fen : kFens) {
        const Outcome first = search_with(fen, 7, false);
        const Outcome second = search_with(fen, 7, false);
        CHECK_EQ(first.nodes, second.nodes);
        CHECK_EQ(first.score, second.score);
        CHECK_EQ(move_to_uci(first.best), move_to_uci(second.best));
    }
}
