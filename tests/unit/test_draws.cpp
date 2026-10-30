#include "test.hpp"
using namespace stockbear;
TEST(unit, repetition_claim_and_automatic_thresholds) {
    Position p = test::position(START_FEN);
    auto cycle = [&] { for (const char* m : {"g1f3","g8f6","f3g1","f6g8"}) test::play(p,m); };
    cycle(); CHECK_EQ(p.repetition_count(),2); CHECK_EQ(p.draw_status(),DrawStatus::None);
    for (const char* m : {"g1f3","g8f6","f3g1"}) test::play(p,m);
    CHECK(p.can_claim_threefold()); // f6g8 would create the third occurrence
    test::play(p,"f6g8"); CHECK_EQ(p.repetition_count(),3);
    CHECK_EQ(p.draw_status(),DrawStatus::ClaimableThreefold);
    cycle(); cycle(); CHECK_EQ(p.repetition_count(),5); CHECK_EQ(p.draw_status(),DrawStatus::AutomaticFivefold);
    test::state_ok(p);
}
TEST(unit, fifty_and_seventy_five_moves_with_mate_priority) {
    Position p98 = test::position("7k/8/8/8/8/8/8/KR6 w - - 98 1");
    Position p99 = test::position("7k/8/8/8/8/8/8/KR6 w - - 99 1");
    Position p100 = test::position("7k/8/8/8/8/8/8/KR6 w - - 100 1");
    Position p150 = test::position("7k/8/8/8/8/8/8/KR6 w - - 150 1");
    CHECK_EQ(p98.draw_status(),DrawStatus::None);
    CHECK(p99.can_claim_fifty_moves());
    CHECK_EQ(p99.draw_status(),DrawStatus::ClaimableFiftyMove);
    CHECK_EQ(p100.draw_status(),DrawStatus::ClaimableFiftyMove);
    CHECK_EQ(p150.draw_status(),DrawStatus::AutomaticSeventyFiveMove);
    Position mate = test::position("7k/6Q1/5K2/8/8/8/8/8 b - - 150 1");
    CHECK(mate.in_check()); CHECK(!mate.has_legal_moves());
    CHECK_EQ(mate.draw_status(),DrawStatus::None); CHECK(!mate.is_search_draw(0));
    Position stale = test::position("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1");
    CHECK(!stale.in_check()); CHECK_EQ(stale.draw_status(),DrawStatus::AutomaticStalemate);
}
TEST(unit, dead_material_not_just_each_sides_minor_count) {
    CHECK(test::position("4k3/8/8/8/8/8/8/4K3 w - - 0 1").insufficient_material());
    CHECK(test::position("4k3/8/8/8/8/8/8/2B1K3 w - - 0 1").insufficient_material());
    CHECK(test::position("4k3/b7/8/8/8/8/8/2B1K3 w - - 0 1").insufficient_material());
    CHECK(!test::position("4k3/1b6/8/8/8/8/8/2B1K3 w - - 0 1").insufficient_material());
    CHECK(!test::position("4k1n1/8/8/8/8/8/8/4K1N1 w - - 0 1").insufficient_material());
}
TEST(unit, repetition_ignores_uncapturable_raw_ep_square) {
    Position p = test::position("4k1n1/8/8/3p4/8/8/8/4K1N1 w - d6 0 2");
    Position q = test::position("4k1n1/8/8/3p4/8/8/8/4K1N1 w - - 0 2");
    CHECK_EQ(p.key(),q.key());
    for (int n=0; n<2; ++n) for (const char* m : {"g1f3","g8f6","f3g1","f6g8"}) test::play(p,m);
    CHECK_EQ(p.repetition_count(),3); CHECK_EQ(p.draw_status(),DrawStatus::ClaimableThreefold);
}
