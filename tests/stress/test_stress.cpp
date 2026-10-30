#include "test.hpp"
#include "chess/fen.hpp"
#include <random>
#include <vector>
using namespace stockbear;
TEST(stress, deterministic_random_games_roundtrip_and_unwind) {
    std::mt19937_64 rng(0x20261030ULL);
    for (int game=0; game<80; ++game) {
        Position p=test::position(START_FEN);
        struct Snapshot { Move move; std::string fen; Key key, context; };
        std::vector<Snapshot> stack;
        for (int ply=0; ply<180; ++ply) {
            test::state_ok(p);
            Position round = test::position(p.fen());
            CHECK_EQ(round.fen(),p.fen()); CHECK_EQ(round.key(),p.key());
            MoveList ml; generate_moves(p,ml);
            if (ml.empty()) break;
            Move m=ml[int(rng()%std::uint64_t(ml.size()))].move;
            stack.push_back({m,p.fen(),p.key(),p.history_context()});
            p.make_move(m);
            test::state_ok(p);
            if (ply%11 == 0) {
                p.unmake_move(m); CHECK_EQ(p.fen(),stack.back().fen); CHECK_EQ(p.key(),stack.back().key);
                p.make_move(m); test::state_ok(p);
            }
        }
        while (!stack.empty()) {
            const auto snapshot=stack.back(); stack.pop_back(); p.unmake_move(snapshot.move);
            CHECK_EQ(p.fen(),snapshot.fen); CHECK_EQ(p.key(),snapshot.key);
            CHECK_EQ(p.history_context(),snapshot.context); test::state_ok(p);
        }
        CHECK_EQ(p.fen(),std::string(START_FEN)); CHECK_EQ(p.history_size(),std::size_t(1));
    }
}
