#include "test.hpp"
#include <vector>
using namespace stockbear;
TEST(unit, make_unmake_every_legal_move_in_special_positions) {
    const char* fens[] = {
        START_FEN,
        "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
        "7k/8/8/3pP3/4K3/8/8/8 w - d6 0 2",
        "n1n1n1nk/1P1P1P1P/8/8/8/8/p1p1p1p1/K1N1N1N1 w - - 0 1",
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
    };
    for (const char* f : fens) {
        Position p = test::position(f);
        const std::string original = p.fen(); const Key key = p.key(), ctx = p.history_context();
        MoveList moves; generate_moves(p, moves);
        for (const ExtMove& m : moves) {
            p.make_move(m.move); test::state_ok(p);
            p.unmake_move(m.move); test::state_ok(p);
            CHECK_EQ(p.fen(), original); CHECK_EQ(p.key(), key); CHECK_EQ(p.history_context(),ctx);
            CHECK_EQ(p.history_size(), std::size_t(1));
        }
    }
}
TEST(unit, pins_and_castling_through_check) {
    Position p = test::position("k3r3/8/8/8/8/8/4R3/4K3 w - - 0 1");
    CHECK(p.pinned() & square_bb(SQ_E2));
    CHECK_EQ(move_from_uci(p,"e2d2"), MOVE_NONE);
    CHECK(is_ok(move_from_uci(p,"e2e8")));
    Position c = test::position("r3k2r/8/8/8/2b5/8/8/R3K2R w KQkq - 0 1");
    CHECK_EQ(move_from_uci(c,"e1g1"), MOVE_NONE);
    CHECK(is_ok(move_from_uci(c,"e1c1")));
}
TEST(unit, castling_rights_and_undo) {
    Position p = test::position("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1");
    const auto start = p.fen(); const auto key = p.key();
    Move capture = move_from_uci(p,"h1h8"); CHECK(is_ok(capture));
    p.make_move(capture);
    CHECK(!p.can_castle(WhiteOO)); CHECK(!p.can_castle(BlackOO));
    CHECK(p.can_castle(WhiteOOO)); CHECK(p.can_castle(BlackOOO));
    test::state_ok(p); p.unmake_move(capture);
    CHECK_EQ(p.fen(),start); CHECK_EQ(p.key(),key); test::state_ok(p);
    Move castle = move_from_uci(p,"e1c1"); p.make_move(castle);
    CHECK_EQ(p.piece_on(SQ_C1), WhiteKing); CHECK_EQ(p.piece_on(SQ_D1), WhiteRook);
    p.unmake_move(castle); CHECK_EQ(p.fen(),start); test::state_ok(p);
}
TEST(unit, en_passant_legality_and_check_evasion) {
    Position pinned = test::position("k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 2");
    CHECK_EQ(move_from_uci(pinned,"e5d6"), MOVE_NONE);
    Position check = test::position("7k/8/8/3pP3/4K3/8/8/8 w - d6 0 2");
    CHECK(check.in_check());
    Move ep = move_from_uci(check,"e5d6"); CHECK_EQ(move_type(ep),EnPassantMove);
    const auto before = check.fen();
    check.make_move(ep); CHECK_EQ(check.piece_on(SQ_D5), NoPiece);
    test::state_ok(check); check.unmake_move(ep); CHECK_EQ(check.fen(),before); test::state_ok(check);
}
