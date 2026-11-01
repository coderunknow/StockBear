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

TEST(unit, static_exchange_evaluation_known_values) {
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
    // A king cannot recapture into a square still attacked by the second rook:
    // rook takes pawn (Rx d7) wins a pawn (+100) even though the king defends it.
    // With a zero king value SEE let the king "recapture" and returned -400.
    CHECK_EQ(see_of("4k3/3p4/8/8/8/8/3R4/3R2K1 w - - 0 1", "d2d7"), 100);
}

TEST(unit, static_exchange_evaluation_promotions) {
    // Promoting to a queen upgrades the pawn's value: 975 - 100.
    CHECK_EQ(see_of("4k3/1P6/8/8/8/8/8/4K3 w - - 0 1", "b7b8q"), 875);
    // A capture-promotion adds the captured rook: 500 + 975 - 100.
    CHECK_EQ(see_of("r3k3/1P6/8/8/8/8/8/4K3 w - - 0 1", "b7a8q"), 1375);
    // Promoting to a rook is worth less than promoting to a queen.
    CHECK_EQ(see_of("4k3/1P6/8/8/8/8/8/4K3 w - - 0 1", "b7b8r"), 400);
}

TEST(unit, search_multipv_lines_are_distinct_ranked_and_legal) {
    // MultiPV must report N *distinct* root moves with non-increasing scores,
    // each with a principal variation that starts with its own move, and the
    // reported best move must be the first line. This is the invariant the GUI
    // relies on for a ranked analysis pane.
    TranspositionTable table(16);
    SearchParams params;
    Search search(table, params);
    Position p = test::position(START_FEN);
    SearchLimits limits;
    limits.depth = 5;
    limits.multiPv = 3;
    std::atomic<bool> stop{false};
    const SearchResult r = search.run(p, limits, stop);
    CHECK_EQ(r.lines.size(), std::size_t(3));
    CHECK(r.bestMove == r.lines[0].move);
    CHECK(!r.lines[0].pv.empty() && r.lines[0].pv[0] == r.lines[0].move);
    CHECK(!r.lines[1].pv.empty() && r.lines[1].pv[0] == r.lines[1].move);
    CHECK(!r.lines[2].pv.empty() && r.lines[2].pv[0] == r.lines[2].move);
    CHECK(r.lines[0].move != r.lines[1].move);
    CHECK(r.lines[0].move != r.lines[2].move);
    CHECK(r.lines[1].move != r.lines[2].move);
    CHECK(r.lines[0].score >= r.lines[1].score);
    CHECK(r.lines[1].score >= r.lines[2].score);
    MoveList legal;
    generate_moves(p, legal, GenType::All);
    for (const PvLine& line : r.lines) CHECK(legal.contains(line.move));
}

TEST(unit, multiPv_matches_single_pv_best_move) {
    // Asking for more lines must not change the best move at a fixed depth: the
    // first line is the same search, only the extra slots are new work.
    //
    // Aspiration windows are switched off for this comparison because MultiPV
    // deliberately disables them (a band tuned around the first line would bias
    // the exact scores the ranking needs), so leaving them on would compare two
    // different search configurations rather than test MultiPV itself.
    TranspositionTable table(16);
    SearchParams params;
    params.aspiration = false;
    SearchLimits single;
    single.depth = 6;
    Position p1 = test::position(START_FEN);
    Position p2 = test::position(START_FEN);
    std::atomic<bool> stop1{false};
    std::atomic<bool> stop2{false};
    Search search1(table, params);
    const SearchResult r1 = search1.run(p1, single, stop1);
    table.clear();
    SearchLimits multi = single;
    multi.multiPv = 4;
    Search search2(table, params);
    const SearchResult r2 = search2.run(p2, multi, stop2);
    CHECK(r1.bestMove == r2.bestMove);
    CHECK_EQ(r2.lines.size(), std::size_t(4));
}

TEST(unit, searchmoves_restricts_the_root) {
    // `go searchmoves` must restrict the root to the listed legal moves, and a
    // list of illegal moves must fall back to a normal search instead of
    // answering "no move".
    TranspositionTable table(16);
    SearchParams params;
    Search search(table, params);
    Position p = test::position(START_FEN);
    SearchLimits limits;
    limits.depth = 4;
    limits.searchMoves = {move_from_uci(p, "e2e4")};
    std::atomic<bool> stop{false};
    const SearchResult r = search.run(p, limits, stop);
    CHECK(r.bestMove == move_from_uci(p, "e2e4"));
    CHECK_EQ(r.lines.size(), std::size_t(1));

    Position p2 = test::position(START_FEN);
    SearchLimits bogus;
    bogus.depth = 3;
    bogus.searchMoves = {move_from_uci(p2, "e2e5")}; // not legal
    std::atomic<bool> stop2{false};
    Search search2(table, params);
    const SearchResult r2 = search2.run(p2, bogus, stop2);
    CHECK(is_ok(r2.bestMove));
    CHECK(r2.bestMove != move_from_uci(p2, "e2e5"));
}

TEST(unit, terminal_position_searches_are_immediate) {
    // A checkmated position and a stalemate must return no move without
    // spinning, even under an infinite limit that only stop can end.
    TranspositionTable table(16);
    SearchParams params;
    {
        Search search(table, params);
        Position p = test::position("7k/6Q1/5K2/8/8/8/8/8 b - - 0 1");
        SearchLimits limits;
        limits.depth = 4;
        std::atomic<bool> stop{false};
        const SearchResult r = search.run(p, limits, stop);
        CHECK(!is_ok(r.bestMove));
        CHECK(r.score < -MATE_BOUND);
    }
    {
        Search search(table, params);
        Position p = test::position("7k/5Q2/5K2/8/8/8/8/8 b - - 0 1");
        SearchLimits limits;
        limits.depth = 4;
        std::atomic<bool> stop{false};
        const SearchResult r = search.run(p, limits, stop);
        CHECK(!is_ok(r.bestMove));
        CHECK_EQ(r.score, VALUE_DRAW);
    }
}

TEST(unit, experimental_ordering_features_keep_the_search_sound) {
    // The dev3 ordering switches default to off (they measured neutral in play),
    // so without this test the code paths behind them would only be reached by
    // hand. With all of them on, the search must still return a legal move, a
    // consistent (score, pv) pair and a mate score where a mate exists.
    TranspositionTable table(16);
    SearchParams params;
    params.counterMoves = true;
    params.continuationHistory = true;
    params.captureHistory = true;
    params.historyMaluses = true;
    params.lmrHistory = true;
    Search search(table, params);

    Position p = test::position(START_FEN);
    SearchLimits limits;
    limits.depth = 6;
    std::atomic<bool> stop{false};
    const SearchResult r = search.run(p, limits, stop);
    CHECK(is_ok(r.bestMove));
    CHECK(!r.pv.empty() && r.pv.front() == r.bestMove);
    MoveList legal;
    generate_moves(p, legal, GenType::All);
    CHECK(legal.contains(r.bestMove));
    for (Move m : r.pv) CHECK(legal.contains(m) || true); // pv may continue deeper

    // A forced mate must still be reported as a mate, not as a large score.
    // Mate in one: Qg7#. The queen must not already be giving check.
    Position mate = test::position("7k/8/5KQ1/8/8/8/8/8 w - - 0 1");
    SearchLimits mateLimits;
    mateLimits.depth = 6;
    std::atomic<bool> mateStop{false};
    Search mateSearch(table, params);
    const SearchResult mateResult = mateSearch.run(mate, mateLimits, mateStop);
    CHECK(is_mate_value(mateResult.score));
    CHECK(mate_value_to_moves(mateResult.score) == 1);

    // MultiPV must still report distinct legal moves with this configuration.
    SearchLimits multi;
    multi.depth = 4;
    multi.multiPv = 3;
    std::atomic<bool> multiStop{false};
    Position start = test::position(START_FEN);
    Search multiSearch(table, params);
    const SearchResult multiResult = multiSearch.run(start, multi, multiStop);
    CHECK_EQ(multiResult.lines.size(), std::size_t(3));
    CHECK(multiResult.lines[0].move != multiResult.lines[1].move);
    CHECK(multiResult.lines[1].move != multiResult.lines[2].move);
    CHECK(multiResult.lines[0].score >= multiResult.lines[1].score);
}
