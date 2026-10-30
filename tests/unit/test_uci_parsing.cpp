#include "test.hpp"
#include "uci/uci.hpp"
#include <sstream>
using namespace stockbear;
TEST(unit, uci_handshake_and_malformed_position) {
    std::istringstream in("uci\nisready\nposition fen bad\nsetoption name Hash value nope\n"
                          "position startpos moves e2e5\ngo nodes 0\nquit\n");
    std::ostringstream out;
    { UciEngine engine(in,out); engine.loop(); }
    const std::string s = out.str();
    CHECK(s.find("id name StockBear " STOCKBEAR_VERSION) != std::string::npos);
    CHECK(s.find("uciok\n") != std::string::npos);
    CHECK(s.find("readyok\n") != std::string::npos);
    CHECK(s.find("info string position:") != std::string::npos);
    CHECK(s.find("info string setoption:") != std::string::npos);
    CHECK(s.find("bestmove ") != std::string::npos);
}
