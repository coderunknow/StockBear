// DEV6 architecture-survey candidate: king-facing slider battery / x-ray.
//
// Counts enemy sliders aligned with our king behind EXACTLY ONE intervening
// blocker. Orthogonal rook/queen weight 4, diagonal bishop/queen weight 3,
// per-side cap 16. Default OFF (shipped row 0). Pins below are derived from the
// written geometry and cross-checked by scripts/check_king_slider_battery.py.
#include "test.hpp"
#include "evaluation/evaluation.hpp"
#include "evaluation/eval_params.hpp"

using namespace stockbear;

namespace {
struct ParamsGuard {
    EvalParams saved;
    ParamsGuard() : saved(active_eval_params()) {}
    ~ParamsGuard() { apply_eval_params(saved); }
};

EvalParams with_battery(int mg, int eg) {
    EvalParams p = default_eval_params();
    p.mg[KingSliderBattery] = mg;
    p.eg[KingSliderBattery] = eg;
    return p;
}

// White king e1; black rook e8 behind one white pawn e5 -> danger to White 4.
const char* kOrthRook = "4r2k/8/8/4P3/8/8/8/4K3 w - - 0 1";
// White king e1; black bishop h4 behind one white pawn f2 -> danger 3.
const char* kDiagBishop = "7k/8/8/8/7b/8/5P2/4K3 w - - 0 1";
// Two blockers screen the rook completely -> 0.
const char* kTwoBlockers = "4r2k/8/8/4P3/4P3/8/8/4K3 w - - 0 1";
// Zero blockers is direct contact, not a battery -> 0.
const char* kZeroBlockers = "4r2k/8/8/8/8/8/8/4K3 w - - 0 1";
// Queen uses the same geometry: orthogonal 4, diagonal 3.
const char* kQueenOrth = "4q2k/8/8/4P3/8/8/8/4K3 w - - 0 1";
const char* kQueenDiag = "7k/8/8/8/7q/8/5P2/4K3 w - - 0 1";
// Mirror: black king e8, white rook e1, one black pawn e5 -> White-positive +4.
const char* kMirror = "4k3/8/8/4p3/8/8/8/4R2K w - - 0 1";
// Five screened sliders: raw 4+4+4+3+3=18, cap 16 -> White-positive -16.
const char* kCap = "4r2k/8/8/b3P3/7b/2P5/5P2/rN2K1Br w - - 0 1";
// A knight is not a slider even if aligned -> 0.
const char* kKnight = "7k/8/8/8/8/4n3/5P2/4K3 w - - 0 1";

int battery_count(const char* fen) {
    const EvalBreakdown bd = eval_breakdown(test::position(fen));
    return bd.mg[std::size_t(KingSliderBattery)];
}
} // namespace

TEST(king_slider_battery, shipped_row_is_zero_and_default_untouched) {
    ParamsGuard guard;
    const EvalParams d = default_eval_params();
    CHECK_EQ(d.mg[KingSliderBattery], 0);
    CHECK_EQ(d.eg[KingSliderBattery], 0);
    apply_eval_params(d);
    const int q = evaluate(test::position(kOrthRook));
    const int c = evaluate(test::position(kCap));
    apply_eval_params(d);
    CHECK_EQ(evaluate(test::position(kOrthRook)), q);
    CHECK_EQ(evaluate(test::position(kCap)), c);
}

TEST(king_slider_battery, counts_match_geometry_exactly) {
    ParamsGuard guard;
    apply_eval_params(with_battery(1, 1));
    CHECK_EQ(battery_count(kOrthRook), -4);
    CHECK_EQ(battery_count(kDiagBishop), -3);
    CHECK_EQ(battery_count(kTwoBlockers), 0);
    CHECK_EQ(battery_count(kZeroBlockers), 0);
    CHECK_EQ(battery_count(kQueenOrth), -4);
    CHECK_EQ(battery_count(kQueenDiag), -3);
    CHECK_EQ(battery_count(kMirror), 4);
    CHECK_EQ(battery_count(kKnight), 0);
    const EvalBreakdown bd = eval_breakdown(test::position(kOrthRook));
    CHECK_EQ(bd.mg[std::size_t(KingSliderBattery)], bd.eg[std::size_t(KingSliderBattery)]);
}

TEST(king_slider_battery, cap_is_live_and_symmetric) {
    ParamsGuard guard;
    apply_eval_params(with_battery(1, 1));
    // Without the cap this position would be -18; the frozen cap clips to -16.
    CHECK_EQ(battery_count(kCap), -16);
    CHECK_EQ(battery_count(kMirror), 4);
}

TEST(king_slider_battery, live_evaluate_path_applies_the_count) {
    ParamsGuard guard;
    const EvalParams d = default_eval_params();
    apply_eval_params(d);
    const int baseOrth = evaluate(test::position(kOrthRook));
    const int baseMirror = evaluate(test::position(kMirror));
    const int baseCap = evaluate(test::position(kCap));
    const int baseTwo = evaluate(test::position(kTwoBlockers));
    apply_eval_params(with_battery(1, 1));
    // mg=eg=1 makes the tapered delta exactly the White-positive count for a
    // White-to-move position, independent of phase.
    CHECK_EQ(evaluate(test::position(kOrthRook)), baseOrth - 4);
    CHECK_EQ(evaluate(test::position(kMirror)), baseMirror + 4);
    CHECK_EQ(evaluate(test::position(kCap)), baseCap - 16);
    CHECK_EQ(evaluate(test::position(kTwoBlockers)), baseTwo);
}
