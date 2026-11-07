// Fixed-depth node-count probe for a SEARCH switch (not an EvalParams term).
// Same binary, switch OFF vs ON, identical EvalParams on both arms.
// Prints: <nodes_off> <nodes_on> <best_off> <best_on>
// Tree-change proxy ONLY -- not a strength or speed measurement.
#include "chess/position.hpp"
#include "chess/zobrist.hpp"
#include "evaluation/evaluation.hpp"
#include "evaluation/eval_params.hpp"
#include "search/search.hpp"
#include "utilities/types.hpp"
#include <atomic>
#include <cstdio>
#include <fstream>
#include <memory>
#include <string>
using namespace stockbear;

namespace {
struct Res { std::uint64_t nodes; std::string best; };

Res run_one(const std::string& fen, int depth, bool on, const std::string& which) {
    Position p;
    std::string err;
    if (!parse_fen(fen, p, &err)) { std::fprintf(stderr, "bad fen\n"); std::exit(2); }
    SearchParams sp;
    sp.ttEval = true;
    if (which == "countermoves") sp.counterMoves = on;
    else if (which == "continuationhistory") sp.continuationHistory = on;
    else if (which == "capturehistory") sp.captureHistory = on;
    else if (which == "badcapturepruning") sp.badCapturePruning = on;
    else { std::fprintf(stderr, "unknown switch %s\n", which.c_str()); std::exit(2); }
    TranspositionTable tt(16);
    SearchLimits lim;
    lim.depth = depth;
    std::atomic<bool> stop{false};
    auto s = std::make_unique<Search>(tt, sp);
    const SearchResult r = s->run(p, lim, stop);
    return {r.nodes, move_to_uci(r.bestMove)};
}
} // namespace

int main(int argc, char** argv) {
    if (argc < 5) {
        std::fprintf(stderr, "usage: switch_liveness PARAMS EPD DEPTH SWITCH\n");
        return 2;
    }
    Zobrist::init();
    EvalParams par;
    std::string err;
    if (!load_eval_params_file(argv[1], &par, &err)) {
        std::fprintf(stderr, "LOAD FAILED %s: %s\n", argv[1], err.c_str());
        return 2;
    }
    std::fprintf(stderr, "EvalParams loaded: %s\n", argv[1]);
    apply_eval_params(par);
    const int depth = std::atoi(argv[3]);
    const std::string which = argv[4];
    std::ifstream in(argv[2]);
    std::string line;
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        const Res a = run_one(line, depth, false, which);
        const Res b = run_one(line, depth, true, which);
        std::printf("%llu %llu %s %s\n", (unsigned long long)a.nodes,
                    (unsigned long long)b.nodes, a.best.c_str(), b.best.c_str());
        std::fflush(stdout);
    }
    return 0;
}
