#include "test.hpp"
using namespace stockbear;
TEST(unit, move_encoding_and_parsing) {
    CHECK_EQ(move_to_uci(make_move(SQ_E2,SQ_E4)), std::string("e2e4"));
    for (PieceType pt : {Knight,Bishop,Rook,Queen}) {
        Move m = make_promotion(SQ_A7,SQ_A8,pt);
        CHECK_EQ(promotion_type(m), pt);
        CHECK_EQ(move_from_uci(move_to_uci(m)), m);
    }
    for (const char* s : {"", "a9a1", "a1a9", "e2e4x", "e2e4qq", "E2e4"})
        CHECK_EQ(move_from_uci(s), MOVE_NONE);
    Position p = test::position(START_FEN);
    CHECK(is_ok(move_from_uci(p, "e2e4")));
    CHECK_EQ(move_from_uci(p, "e2e5"), MOVE_NONE);
    CHECK_EQ(move_from_uci(p, "e2e4q"), MOVE_NONE);
}
TEST(unit, all_promotions_and_castling_are_resolved) {
    Position p = test::position("7k/P7/8/8/8/4K3/8/8 w - - 0 1");
    for (const char* m : {"a7a8q", "a7a8r", "a7a8b", "a7a8n"})
        CHECK_EQ(move_type(move_from_uci(p,m)), PromotionMove);
    CHECK_EQ(move_from_uci(p, "a7a8"), MOVE_NONE);
    Position c = test::position("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1");
    CHECK_EQ(move_type(move_from_uci(c,"e1g1")), CastlingMove);
    CHECK_EQ(move_type(move_from_uci(c,"e1c1")), CastlingMove);
}
