#include "test.hpp"
#include "chess/dead_position.hpp"
using namespace stockbear;

TEST(unit, movement_reachability_bounded_and_witnessed) {
    Position p = test::position("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1");
    const auto original = p.fen();
    auto unknown = movement_mate_reachability(p, 1);
    CHECK_EQ(unknown.result, MateReachability::Unknown);
    CHECK_EQ(unknown.positions, 1U);
    auto found = movement_mate_reachability(p, 1000);
    CHECK_EQ(found.result, MateReachability::MateFound);
    CHECK_EQ(found.witness.size(), 1U);
    CHECK_EQ(p.fen(), original);
    for (auto move : found.witness) test::play(p, move_to_uci(move));
    CHECK(p.in_check()); CHECK(!p.has_legal_moves());
}

TEST(unit, movement_reachability_exhaustive_forced_capture) {
    // Black is forced to capture the rook. KvK has no reachable checkmate.
    Position p = test::position("8/8/8/8/8/8/3R4/K1k5 b - - 0 1");
    MoveList moves; generate_moves(p, moves); CHECK_EQ(moves.size(), 1);
    auto result = movement_mate_reachability(p, 10000);
    CHECK_EQ(result.result, MateReachability::NoMate);
    CHECK_EQ(result.positions, 7225U); // independently enumerated with python-chess 1.11.2
    CHECK(result.witness.empty());
    test::state_ok(p);
}

TEST(unit, movement_reachability_promotion_trap_and_locked_budget) {
    Position p = test::position("8/5KPk/8/5N2/8/8/8/8 w - - 0 1");
    test::play(p, "g7g8b"); // forced Kh8, then eventual bishop capture or stalemate
    MoveList moves; generate_moves(p, moves); CHECK_EQ(moves.size(), 1);
    auto result = movement_mate_reachability(p, 500000);
    CHECK_EQ(result.result, MateReachability::NoMate);
    CHECK_EQ(result.positions, 436665U); // independently enumerated with python-chess 1.11.2
    Position locked = test::position("2b1k3/8/8/1p1p1p1p/1P1P1P1P/8/8/2B1K3 w - - 0 1");
    // A tiny budget is not evidence for either outcome.
    CHECK_EQ(movement_mate_reachability(locked, 1).result, MateReachability::Unknown);
}
