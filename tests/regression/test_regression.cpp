#include "test.hpp"
using namespace stockbear;
TEST(regression, capture_unmake_restores_captured_piece) {
    Position p = test::position("4k3/8/8/3q4/4P3/8/8/4K3 w - - 0 1");
    const auto fen=p.fen(); const Key key=p.key();
    Move m=move_from_uci(p,"e4d5"); p.make_move(m); p.unmake_move(m);
    CHECK_EQ(p.fen(),fen); CHECK_EQ(p.piece_on(SQ_D5),BlackQueen); CHECK_EQ(p.key(),key);
    test::state_ok(p);
}
TEST(regression, ep_capture_removes_checker_from_attackers) {
    Position p=test::position("7k/8/8/3pP3/4K3/8/8/8 w - d6 0 2");
    CHECK(p.in_check()); CHECK(is_ok(move_from_uci(p,"e5d6")));
}
TEST(regression, synthetic_ep_block_of_slider_check) {
    // This deliberately synthetic FEN has an impossible immediate history:
    // it exercises the generator's complete post-EP king-safety logic anyway.
    Position p=test::position("5b1k/8/8/3pP3/1K6/8/8/8 w - d6 0 2");
    CHECK(p.in_check()); CHECK(is_ok(move_from_uci(p,"e5d6")));
}
TEST(regression, rook_edge_magic_retains_edge_file) {
    Position p=test::position(START_FEN);
    CHECK_EQ(popcount(rook_attacks_bb(SQ_A4,0)),14);
    CHECK_EQ(p.perft(4),197281ULL);
}
TEST(regression, serialization_uses_correct_piece_symbols) {
    const std::string fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    CHECK_EQ(test::position(fen).fen(),fen);
}

TEST(regression, public_make_move_never_captures_a_king) {
    Position p=test::position("k7/8/8/8/8/8/4R3/4K3 w - - 0 1");
    const auto before=p.fen(); const auto key=p.key();
    bool rejected=false;
    try { p.make_move(stockbear::make_move(SQ_E2,SQ_A8)); }
    catch (const std::invalid_argument&) { rejected=true; }
    CHECK(rejected); CHECK_EQ(p.fen(),before); CHECK_EQ(p.key(),key); test::state_ok(p);
}
