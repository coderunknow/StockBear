#include "test.hpp"
#include "evaluation/evaluation.hpp"
using namespace stockbear;
TEST(unit, evaluation_color_symmetry_and_material) {
    Position w = test::position("4k3/8/8/8/3N4/4P3/8/4K3 w - - 0 1");
    Position b = test::position("4k3/8/4p3/3n4/8/8/8/4K3 b - - 0 1");
    Position opposite = test::position("4k3/8/8/8/3N4/4P3/8/4K3 b - - 0 1");
    CHECK_EQ(evaluate(w),evaluate(b));
    CHECK_EQ(evaluate(w),-evaluate(opposite));
    CHECK(evaluate(w) > 300);
    Position bare = test::position("4k3/8/8/8/8/8/8/4K3 w - - 0 1");
    CHECK_EQ(evaluate(bare),0);
}
TEST(unit, evaluation_tracks_promotions_and_undo) {
    Position p = test::position("7k/P7/8/8/8/4K3/8/8 w - - 0 1");
    const int before = evaluate(p);
    Move m = move_from_uci(p,"a7a8q"); CHECK(is_ok(m));
    p.make_move(m); CHECK(-evaluate(p) > before + 500); test::state_ok(p);
    p.unmake_move(m); CHECK_EQ(evaluate(p),before); test::state_ok(p);
}
