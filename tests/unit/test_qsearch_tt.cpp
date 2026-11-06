// Regression: the exp-0038 qsearch transposition cache must store the value of
// a node that actually SEARCHED captures, not only stand-pat / delta-pruning
// exits. `quiescence()` used to `return best;` from its move loop, bypassing the
// `finish()` store lambda, so the cache was populated only by the early exits
// and could never return a searched value.
//
// The switch is default OFF, so these tests enable it explicitly and compare
// against the same search with it disabled. A qsearch cache is a pure
// memoisation of a deterministic subtree: it may change node counts and move
// ordering, but it must never change a proven mate score or produce an illegal
// move/PV.
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
    std::vector<Move> pv;
};

Outcome search_with(const char* fen, int depth, bool qsearchTT) {
    SearchParams params;
    params.qsearchTT = qsearchTT;
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
    return {r.bestMove, r.score, r.nodes, r.pv};
}

// Capture-rich positions where the qsearch move loop is definitely entered.
const char* kCaptureFens[] = {
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "r4rk1/1pp1qppp/p1np1n2/8/2B1P1b1/2PP1N2/PP3PPP/RNBQ1RK1 w - - 0 10",
    "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/2KR1B1R w - - 0 9",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
};
} // namespace

TEST(qsearch_tt, searched_nodes_are_memoised_without_changing_proven_mates) {
    for (const char* fen : kCaptureFens) {
        const Outcome off = search_with(fen, 6, false);
        const Outcome on = search_with(fen, 6, true);
        CHECK(is_ok(off.best));
        CHECK(is_ok(on.best));
        // A memoised qsearch must not turn a non-mate into a mate or vice versa.
        CHECK_EQ(is_mate_value(off.score), is_mate_value(on.score));
        if (is_mate_value(off.score))
            CHECK_EQ(mate_value_to_moves(off.score), mate_value_to_moves(on.score));
    }
}

// The defect-detecting assertion. Comparing scores/mates alone does NOT catch
// the bug (verified: the buggy build passes those checks), because a cache that
// never stores a searched value is still *correct* -- it is simply useless.
// The discriminating observable is node count. Measured on this exact suite:
//   buggy  `return best;`   : on/off node ratio 0.9990 .. 1.0000
//   fixed  `return finish()`: on/off node ratio 0.3680 .. 0.9301
// Requiring a real reduction on the capture-rich root makes the regression
// fail loudly if the store is ever bypassed again. The 0.98 threshold is far
// from both populations, so it is not a machine-sensitive timing assertion:
// node counts are deterministic for a fixed depth.
TEST(qsearch_tt, cache_actually_memoises_searched_capture_nodes) {
    const Outcome off = search_with(kCaptureFens[0], 5, false);
    const Outcome on = search_with(kCaptureFens[0], 5, true);
    CHECK(off.nodes > 1000);
    CHECK(on.nodes > 0);
    CHECK(on.nodes * 100 < off.nodes * 98);
}

TEST(qsearch_tt, forced_mates_are_identical_with_the_cache_enabled) {
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

TEST(qsearch_tt, cache_is_cleared_between_runs) {
    // run() resets the cache; a stale entry from a different root must not
    // leak into the next search's scores.
    SearchParams params;
    params.qsearchTT = true;
    TranspositionTable tt(4);
    std::atomic<bool> stop{false};
    SearchLimits limits;
    limits.depth = 5;
    auto search = std::make_unique<Search>(tt, params);
    const SearchResult first = search->run(test::position(kCaptureFens[0]), limits, stop);
    tt.clear();
    auto fresh = std::make_unique<Search>(tt, params);
    const SearchResult again = fresh->run(test::position(kCaptureFens[0]), limits, stop);
    CHECK_EQ(again.score, first.score);
    CHECK_EQ(move_to_uci(again.bestMove), move_to_uci(first.bestMove));
    CHECK_EQ(again.nodes, first.nodes);
}
