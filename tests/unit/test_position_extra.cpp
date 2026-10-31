// Additional position/state-integrity tests that did not fit the older suites:
// null-move make/unmake symmetry and the counters that a null move must and
// must not touch.
#include "test.hpp"
using namespace stockbear;

namespace {
const char* kFens[] = {
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 3 12",
    "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2",
    "8/3k4/p1p2p1p/PpPp1PpP/1P1P2P1/4K3/8/8 w - - 6 49",
    "8/8/8/8/4k3/8/8/1N2K1N1 b - - 0 40",
};
}

TEST(position_extra, null_move_roundtrip_restores_the_exact_position) {
    for (const char* fen : kFens) {
        Position p = test::position(fen);
        const std::string before = p.fen();
        const Key key = p.key();
        p.make_null_move();
        CHECK(p.side_to_move() != (before.find(" w ") != std::string::npos ? White : Black));
        CHECK_EQ(int(p.ep_square()), int(SQ_NONE));
        p.unmake_null_move();
        CHECK_EQ(p.fen(), before);
        CHECK_EQ(p.key(), key);
        test::state_ok(p);
    }
}

TEST(position_extra, repeated_null_moves_do_not_drift_counters) {
    for (const char* fen : kFens) {
        Position p = test::position(fen);
        const std::string before = p.fen();
        for (int i = 0; i < 5; ++i) {
            p.make_null_move();
            p.unmake_null_move();
            test::state_ok(p);
        }
        CHECK_EQ(p.fen(), before);
    }
}

TEST(position_extra, null_move_inside_a_move_sequence_unwinds_exactly) {
    const char* fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1";
    Position p = test::position(fen);
    const std::string before = p.fen();
    // Keep the Move objects: unmaking requires the encoded move (in particular
    // the castling flag), not one re-parsed from the resulting position.
    const Move white = move_from_uci(p, "e1g1");  // castle, so rights change too
    p.make_move(white);
    const Move black = move_from_uci(p, "e8g8");
    p.make_move(black);
    p.make_null_move();
    p.unmake_null_move();
    p.unmake_move(black);
    p.unmake_move(white);
    CHECK_EQ(p.fen(), before);
    test::state_ok(p);
}

TEST(position_extra, null_move_key_clears_the_en_passant_right) {
    // The en-passant square is part of the Zobrist key; a null move discards the
    // right, so the resulting key must equal the key of a freshly parsed
    // position with the same placement, the other side to move and no ep square.
    Position p = test::position("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2");
    p.make_null_move();
    Position expected = test::position("4k3/8/8/3pP3/8/8/8/4K3 b - - 0 2");
    CHECK_EQ(p.key(), expected.key());
    CHECK_EQ(p.fen(), expected.fen());
    p.unmake_null_move();
    test::state_ok(p);
}
