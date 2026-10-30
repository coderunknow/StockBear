#include "test.hpp"
using namespace stockbear;
TEST(unit, fen_start_and_transactional_errors) {
    Position p = test::position(START_FEN);
    CHECK_EQ(p.fen(), std::string(START_FEN));
    const Key key = p.key();
    const char* invalid[] = {
        "", "8/8/8/8/8/8/8/8 w - - 0 1", // missing kings
        "4k3/8/8/8/8/8/8/4K3 w - - 0", // missing field
        "4k3/8/8/8/8/8/8/4K3 w - - 0 1 extra",
        "4k3/8/8/8/8/8/8/4K3 x - - 0 1",
        "4k3/8/8/8/8/8/8/4K3 w K - 0 1", // no rook
        "4k3/8/8/8/8/8/8/4K3 w - d6 0 1", // no pawn to capture
        "4k3/8/8/8/8/8/8/4K3 w - - -1 1",
        "4k3/8/8/8/8/8/8/4K3 w - - 0 0",
        "4k3/8/8/8/8/8/4k3/4K3 w - - 0 1",
        "8/8/8/8/8/8/4k3/4K3 w - - 0 1", // adjacent kings
        "4k3/8/8/8/8/8/8/P3K3 w - - 0 1", // pawn on first rank
        "4k3/8/8/8/8/8/8/44K w - - 0 1" // consecutive digits
    };
    for (const char* fen : invalid) {
        std::string error;
        CHECK(!p.set(fen, &error)); CHECK(!error.empty());
        CHECK_EQ(p.fen(), std::string(START_FEN)); CHECK_EQ(p.key(), key);
    }
}
TEST(unit, fen_fullmove_and_raw_ep_roundtrip) {
    Position p = test::position(START_FEN);
    test::play(p, "a2a4");
    CHECK_EQ(p.fen(), std::string("rnbqkbnr/pppppppp/8/8/P7/8/1PPPPPPP/RNBQKBNR b KQkq a3 0 1"));
    test::play(p, "h7h5");
    CHECK_EQ(p.fen(), std::string("rnbqkbnr/ppppppp1/8/7p/P7/8/1PPPPPPP/RNBQKBNR w KQkq h6 0 2"));
    Position q = test::position(p.fen());
    CHECK_EQ(p.key(), q.key());
    test::state_ok(p);
}
