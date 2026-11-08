// exp-0067: JOINT persistence of the graded ordering state.
//
// One intervention (age-instead-of-erase) applied to BOTH graded tables at the
// same reset site in Search::run(): quiet history_ and continuation_. This suite
// proves the COMPOSITION, which is what exp-0067 actually tests. Per-table
// behaviour is already covered by test_persistent_history / _continuation.
//
// Composition hazards this suite is designed to catch:
//  * only one of the two tables actually persisting (half the intervention lost);
//  * a table halved twice, or not halved at all (wrong aging schedule);
//  * the shipped SATURATION halving in update_quiet_stats being confused with
//    the persistence halving in run() -- there are two distinct `value /= 2`
//    sites in search.cpp and only the run() one is the intervention;
//  * a reused Search leaking state across games or across configuration changes;
//  * tables that must STAY erased (correction_, captureHistory_, counterMoves_)
//    accidentally becoming persistent.
//
// Carried-forward lessons, encoded deliberately:
//  * the TT is cleared before EVERY probe search, so these tests measure table
//    lifetime and not transposition-table reuse;
//  * object-lifetime behaviour this in-process suite cannot observe is covered
//    by scripts/check_joint_persistence_uci.py, because mutants previously
//    survived an in-process-only suite.
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

// Both graded tables persist; ContinuationHistory must be ON or the continuation
// table is never written and half the intervention would be a no-op.
SearchParams joint(bool on, bool feature = true) {
    SearchParams sp;
    sp.ttEval = true;
    sp.continuationHistory = feature;
    sp.persistentHistory = on;
    sp.persistentContinuation = on;
    return sp;
}

SearchParams only_history(bool on) {
    SearchParams sp = joint(false);
    sp.persistentHistory = on;
    return sp;
}

SearchParams only_continuation(bool on) {
    SearchParams sp = joint(false);
    sp.persistentContinuation = on;
    return sp;
}

// Clearing the TT first is essential: otherwise a second search differs merely
// because of hash hits and the test would not be about table lifetime at all.
SearchResult run_on(Search& s, TranspositionTable& tt, const char* fen, int depth) {
    tt.clear();
    Position p = test::position(fen);
    SearchLimits lim;
    lim.depth = depth;
    std::atomic<bool> stop{false};
    return s.run(p, lim, stop);
}

std::uint64_t nodes_seq(const SearchParams& sp, bool fresh_each_time,
                        const char* f1, const char* f2, int depth) {
    TranspositionTable tt(4);
    Search s(tt, sp);
    (void)run_on(s, tt, f1, depth);
    if (fresh_each_time) {
        Search s2(tt, sp);
        return run_on(s2, tt, f2, depth).nodes;
    }
    return run_on(s, tt, f2, depth).nodes;
}

} // namespace

TEST(joint_persistence, shipped_defaults_are_all_off) {
    SearchParams sp;
    CHECK_EQ(sp.persistentHistory, false);
    CHECK_EQ(sp.persistentContinuation, false);
    CHECK_EQ(sp.continuationHistory, false);
}

TEST(joint_persistence, off_reused_object_equals_fresh_objects) {
    // With the intervention OFF, reusing the Search must be indistinguishable
    // from a fresh one: this is the shipped-behaviour equivalence pin.
    const SearchParams sp = joint(false);
    const std::uint64_t reused = nodes_seq(sp, false, kFenA, kFenB, 7);
    const std::uint64_t fresh = nodes_seq(sp, true, kFenA, kFenB, 7);
    CHECK_EQ(reused, fresh);
}

TEST(joint_persistence, joint_on_changes_the_search) {
    // Liveness: the joint intervention must not be a no-op.
    const std::uint64_t off = nodes_seq(joint(false), false, kFenA, kFenB, 7);
    const std::uint64_t on = nodes_seq(joint(true), false, kFenA, kFenB, 7);
    CHECK(off != on);
}

TEST(joint_persistence, both_tables_contribute_independently) {
    // Each table alone must differ from OFF, and JOINT must differ from BOTH
    // single-table arms. If one branch were dead, joint would equal the other
    // single arm and this check would fail.
    const std::uint64_t off = nodes_seq(joint(false), false, kFenA, kFenB, 7);
    const std::uint64_t h = nodes_seq(only_history(true), false, kFenA, kFenB, 7);
    const std::uint64_t c = nodes_seq(only_continuation(true), false, kFenA, kFenB, 7);
    const std::uint64_t j = nodes_seq(joint(true), false, kFenA, kFenB, 7);
    CHECK(h != off);
    CHECK(c != off);
    CHECK(j != h);
    CHECK(j != c);
}

TEST(joint_persistence, feature_off_makes_continuation_half_a_noop) {
    // Documents WHY both arms of the experiment set ContinuationHistory=true:
    // with the feature off the continuation table is never written, so turning
    // on its persistence alone changes nothing.
    const SearchParams fo = joint(false, false);
    SearchParams fn = joint(false, false);
    fn.persistentContinuation = true;
    const std::uint64_t a = nodes_seq(fo, false, kFenA, kFenB, 7);
    const std::uint64_t b = nodes_seq(fn, false, kFenA, kFenB, 7);
    CHECK_EQ(a, b);
}

TEST(joint_persistence, third_search_still_carries_state) {
    // Aging must keep acting across a longer sequence, not just once.
    TranspositionTable tt(4);
    Search on(tt, joint(true));
    Search off(tt, joint(false));
    run_on(on, tt, kFenA, 7);
    run_on(off, tt, kFenA, 7);
    run_on(on, tt, kFenB, 7);
    run_on(off, tt, kFenB, 7);
    const std::uint64_t a = run_on(on, tt, kFenA, 7).nodes;
    const std::uint64_t b = run_on(off, tt, kFenA, 7).nodes;
    CHECK(a != b);
}

TEST(joint_persistence, fresh_object_forgets_everything) {
    // A brand-new Search must reproduce the OFF first-search count exactly:
    // no static/global leakage between objects.
    TranspositionTable tt(4);
    Search warm(tt, joint(true));
    run_on(warm, tt, kFenA, 7);
    run_on(warm, tt, kFenB, 7);
    Search cold(tt, joint(true));
    const std::uint64_t c = run_on(cold, tt, kFenA, 7).nodes;
    Search ref(tt, joint(false));
    const std::uint64_t r = run_on(ref, tt, kFenA, 7).nodes;
    CHECK_EQ(c, r);
}

TEST(joint_persistence, joint_wiring_characterization_pins) {
    // EXACT node pins for ALL FOUR configurations, TT cleared per run, depth 7,
    // sequence A,B,A,B. Characterization pins for THIS build.
    //
    // Why exact and not merely "differs from OFF": an inequality assertion is
    // blind to the aging RATE. Five rate mutants (halving removed, halving
    // applied twice, only the first slot decayed -- for either table) initially
    // SURVIVED this group because persistence still changed the node counts.
    // Exact pins kill every one of them. This is the same lesson exp-0066
    // learned; it is encoded here so the composition cannot regress silently.
    TranspositionTable tt(4);
    const char* seq[] = {kFenA, kFenB, kFenA, kFenB};
    const std::uint64_t expected_off[] = {29153ULL, 37911ULL, 29153ULL, 37911ULL};
    const std::uint64_t expected_h[]   = {29153ULL, 58093ULL, 28620ULL, 49940ULL};
    const std::uint64_t expected_c[]   = {29153ULL, 37916ULL, 25730ULL, 36912ULL};
    const std::uint64_t expected_j[]   = {29153ULL, 57921ULL, 28610ULL, 47611ULL};
    struct Arm { SearchParams sp; const std::uint64_t* want; };
    const Arm arms[] = {{joint(false), expected_off}, {only_history(true), expected_h},
                        {only_continuation(true), expected_c}, {joint(true), expected_j}};
    for (const Arm& arm : arms) {
        Search s(tt, arm.sp);
        for (int i = 0; i < 4; ++i)
            CHECK_EQ(run_on(s, tt, seq[i], 7).nodes, arm.want[i]);
    }
}
