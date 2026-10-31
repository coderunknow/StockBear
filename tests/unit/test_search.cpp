#include "test.hpp"
#include "search/search.hpp"
#include <atomic>
#include <chrono>
#include <memory>
#include <thread>
using namespace stockbear;
namespace {
SearchResult run(const char* fen, int depth) {
    Position p = test::position(fen); TranspositionTable tt(1);
    SearchLimits l; l.depth = depth; std::atomic<bool> stop{false};
    auto search = std::make_unique<Search>(tt);
    auto result = search->run(p,l,stop);
    Position pvPosition = p;
    for (Move m : result.pv) {
        CHECK_EQ(move_from_uci(pvPosition,move_to_uci(m)), m);
        pvPosition.make_move(m);
    }
    return result;
}
}
TEST(unit, search_mate_in_one_and_mate_in_two) {
    SearchResult one = run("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1",3);
    CHECK(is_mate_value(one.score)); CHECK_EQ(mate_value_to_moves(one.score),1);
    Position p = test::position("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1");
    p.make_move(one.bestMove); CHECK(p.in_check()); CHECK(!p.has_legal_moves());
    SearchResult two = run("8/8/8/5Q2/k7/8/1K6/8 w - - 0 1",4);
    CHECK_EQ(move_to_uci(two.bestMove),std::string("b2c3"));
    CHECK_EQ(mate_value_to_moves(two.score),2);
}
TEST(unit, search_tactical_defensive_and_endgame_positions) {
    CHECK_EQ(move_to_uci(run("4k3/8/8/3q4/4P3/8/8/4K3 w - - 0 1",3).bestMove),std::string("e4d5"));
    CHECK_EQ(move_to_uci(run("7k/8/8/8/8/8/5rr1/6K1 w - - 0 1",3).bestMove),std::string("g1h1"));
    CHECK_EQ(move_to_uci(run("8/8/7q/8/8/1k6/8/RK6 w - - 0 1",3).bestMove),std::string("a1a3"));
    CHECK_EQ(move_to_uci(run("7k/P7/8/8/8/4K3/8/8 w - - 0 1",3).bestMove),std::string("a7a8q"));
    SearchResult avoid = run("8/1P6/8/8/8/8/8/5K1k w - - 0 1",4);
    Position p = test::position("8/1P6/8/8/8/8/8/5K1k w - - 0 1");
    p.make_move(avoid.bestMove);
    CHECK(p.draw_status() != DrawStatus::AutomaticStalemate);
    CHECK(avoid.score > 0);
}
TEST(unit, search_terminal_and_node_limit) {
    SearchResult mate = run("7k/6Q1/5K2/8/8/8/8/8 b - - 0 1",3);
    CHECK_EQ(mate.bestMove,MOVE_NONE); CHECK_EQ(mate.score,-VALUE_MATE);
    SearchResult draw = run("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",3);
    CHECK_EQ(draw.bestMove,MOVE_NONE); CHECK_EQ(draw.score,0);
    SearchResult bare = run("4k3/8/8/8/8/8/8/4K3 w - - 0 1",4);
    CHECK(is_ok(bare.bestMove)); CHECK_EQ(bare.score,0); CHECK_EQ(bare.depth,0);

    Position p = test::position(START_FEN); TranspositionTable tt(1);
    SearchLimits l; l.hasNodes=true; l.nodes=100;
    std::atomic<bool> stop{false}; auto s = std::make_unique<Search>(tt);
    SearchResult limited = s->run(p,l,stop); CHECK_EQ(limited.nodes,100ULL);
    CHECK(is_ok(move_from_uci(p,move_to_uci(limited.bestMove))));
    stop.store(true); auto s2 = std::make_unique<Search>(tt);
    SearchResult immediate = s2->run(p,l,stop); CHECK_EQ(immediate.nodes,0ULL);
    CHECK(is_ok(move_from_uci(p,move_to_uci(immediate.bestMove))));
}
TEST(unit, search_infinite_cancellation) {
    Position p = test::position(START_FEN); TranspositionTable tt(1);
    SearchLimits l; l.infinite=true; std::atomic<bool> stop{false};
    SearchResult result;
    auto search = std::make_unique<Search>(tt);
    std::thread t([&]{ result = search->run(p,l,stop); });
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
    stop.store(true); t.join();
    CHECK(result.interrupted); CHECK(is_ok(move_from_uci(p,move_to_uci(result.bestMove))));
}

TEST(unit, retained_table_does_not_change_new_root_result) {
    Position p = test::position(START_FEN);
    TranspositionTable retained(1), fresh(1);
    SearchLimits l; l.depth = 4; std::atomic<bool> stop{false};
    auto first = std::make_unique<Search>(retained);
    first->run(p,l,stop);
    test::play(p,"b1c3");
    auto withHistory = std::make_unique<Search>(retained);
    auto withoutHistory = std::make_unique<Search>(fresh);
    SearchResult a = withHistory->run(p,l,stop);
    SearchResult b = withoutHistory->run(p,l,stop);
    CHECK_EQ(a.score,b.score); CHECK_EQ(a.bestMove,b.bestMove);
}

namespace {
int see_of(const char* fen, const char* uci) {
    Position p = test::position(fen);
    const Move m = move_from_uci(p, uci);
    CHECK(is_ok(m));
    return static_exchange_evaluation(p, m);
}
}

TEST(search, static_exchange_evaluation_known_values) {
    // Pawn takes an undefended pawn: +100.
    CHECK_EQ(see_of("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1", "e4d5"), 100);
    // Knight takes a pawn defended by a pawn: 100 - 320 = -220. The final
    // recapture must be folded in, otherwise this losing capture looks winning.
    CHECK_EQ(see_of("4k3/8/2p5/3p4/8/2N5/8/4K3 w - - 0 1", "c3d5"), -220);
    // Queen takes the same defended pawn: 100 - 975 = -875.
    CHECK_EQ(see_of("4k3/8/2p5/3p4/8/8/8/3QK3 w - - 0 1", "d1d5"), -875);
    // Pawn takes a pawn defended by a pawn, with nothing left to recapture:
    // an equal trade, so exactly zero.
    CHECK_EQ(see_of("4k3/8/2p5/3p4/2P5/8/8/4K3 w - - 0 1", "c4d5"), 0);
    // Rook takes a defended rook that a pawn of ours recaptures: 500 - 500 + 100.
    CHECK_EQ(see_of("4k3/8/2p5/3r4/2PR4/8/8/4K3 w - - 0 1", "d4d5"), 100);
    // A quiet move wins nothing and loses nothing.
    CHECK_EQ(see_of("4k3/8/8/8/8/8/8/4K3 w - - 0 1", "e1e2"), 0);
    // En passant removes the captured pawn from the exchange square.
    CHECK_EQ(see_of("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2", "e5d6"), 100);
}

TEST(search, static_exchange_evaluation_promotions) {
    // Promoting to a queen upgrades the pawn's value: 975 - 100.
    CHECK_EQ(see_of("4k3/1P6/8/8/8/8/8/4K3 w - - 0 1", "b7b8q"), 875);
    // A capture-promotion adds the captured rook: 500 + 975 - 100.
    CHECK_EQ(see_of("r3k3/1P6/8/8/8/8/8/4K3 w - - 0 1", "b7a8q"), 1375);
    // Promoting to a rook is worth less than promoting to a queen.
    CHECK_EQ(see_of("4k3/1P6/8/8/8/8/8/4K3 w - - 0 1", "b7b8r"), 400);
}
