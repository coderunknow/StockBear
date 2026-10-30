#include "test.hpp"
#include "search/timeman.hpp"
using namespace stockbear;
TEST(unit, time_budget_limits_and_infinite) {
    TimeManager t; SearchLimits l;
    l.moveTimeMs=100; t.start(l,White); CHECK_EQ(t.hard_budget_ms(),95);
    l.moveTimeMs=0; t.start(l,White); CHECK_EQ(t.hard_budget_ms(),1);
    l.moveTimeMs=-1; l.whiteTimeMs=1000; l.whiteIncMs=100; l.movesToGo=10;
    t.start(l,White); CHECK_EQ(t.hard_budget_ms(),300);
    l.whiteTimeMs=5; t.start(l,White); CHECK_EQ(t.hard_budget_ms(),1);
    l.infinite=true; t.start(l,White); CHECK_EQ(t.hard_budget_ms(),-1);
}
