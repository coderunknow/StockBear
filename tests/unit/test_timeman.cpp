#include "test.hpp"
#include "search/timeman.hpp"
using namespace stockbear;

TEST(unit, time_budget_limits_and_infinite) {
    TimeManager t;
    SearchLimits l;

    // movetime: a fixed budget minus a small protocol reserve.
    l.moveTimeMs = 100; t.start(l, White); CHECK_EQ(t.hard_budget_ms(), 95);
    CHECK_EQ(t.soft_budget_ms(), 95);
    l.moveTimeMs = 0; t.start(l, White); CHECK_EQ(t.hard_budget_ms(), 1);

    // Clock with an increment and movestogo: the soft budget is one slice plus
    // part of the increment, the hard budget allows at most a third of the
    // remaining clock and four times the slice.
    l.moveTimeMs = -1; l.whiteTimeMs = 1000; l.whiteIncMs = 100; l.movesToGo = 10;
    t.start(l, White);
    CHECK_EQ(t.soft_budget_ms(), 175);
    CHECK_EQ(t.hard_budget_ms(), 333);
    CHECK(t.soft_budget_ms() <= t.hard_budget_ms());
    CHECK(t.hard_budget_ms() < l.whiteTimeMs);
    CHECK(t.has_clock());

    // Black's clock is used when Black is to move.
    l.blackTimeMs = 1000; l.blackIncMs = 0; l.movesToGo = 0;
    TimeManager black;
    black.start(l, Black);
    // Without movestogo the manager assumes 30 more moves, so the slice is
    // 1000/30 = 33 ms and the hard ceiling is four slices.
    CHECK_EQ(black.soft_budget_ms(), 33);
    CHECK_EQ(black.hard_budget_ms(), 132);

    // Tiny remaining clocks still leave a usable, positive budget.
    l.whiteTimeMs = 5; l.movesToGo = 10;
    t.start(l, White);
    CHECK_EQ(t.hard_budget_ms(), 1);
    CHECK_EQ(t.soft_budget_ms(), 1);

    // No clock for the side to move and no movetime: behave as infinite.
    SearchLimits none;
    TimeManager idle;
    idle.start(none, White);
    CHECK_EQ(idle.hard_budget_ms(), -1);
    CHECK(!idle.has_clock());
    CHECK(!idle.hard_expired());
    CHECK(!idle.soft_expired());

    SearchLimits inf;
    inf.infinite = true;
    t.start(inf, White);
    CHECK_EQ(t.hard_budget_ms(), -1);
    CHECK_EQ(t.soft_usage_permille(), 0);
}
