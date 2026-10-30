#include "test.hpp"
#include "utilities/bench_positions.hpp"
#include <utility>
using namespace stockbear;
TEST(perft_quick, initial_counts) {
    Position p = test::position(START_FEN);
    for (const auto& item : {std::pair<int,std::uint64_t>{0,1}, {1,20}, {2,400}, {3,8902}, {4,197281}})
        CHECK_EQ(p.perft(item.first),item.second);
}
TEST(perft_quick, tactical_special_positions) {
    struct Entry { const char* fen; int depth; std::uint64_t nodes; };
    const Entry cases[] = {
        {PerftCases[1].fen,3,97862}, {PerftCases[2].fen,4,43238},
        {PerftCases[3].fen,3,9467}, {PerftCases[4].fen,3,62379},
        {PerftCases[5].fen,3,530}, {PerftCases[6].fen,3,215},
        {PerftCases[7].fen,3,29531}
    };
    for (const auto& c : cases) { Position p = test::position(c.fen); CHECK_EQ(p.perft(c.depth),c.nodes); }
}
TEST(perft_full, independently_verified_suite) {
    for (const auto& c : PerftCases) {
        Position p = test::position(c.fen);
        const std::uint64_t nodes = p.perft(c.depth);
        if (nodes != c.expected) throw std::runtime_error(std::string(c.name) + " expected " +
            std::to_string(c.expected) + " got " + std::to_string(nodes));
        test::state_ok(p);
    }
}
