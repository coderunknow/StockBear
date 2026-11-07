// exp-0064 search-cost regression probe (NOT a strength measurement).
// Fixed-depth, same binary, one arm per process invocation. The candidate adds
// no evaluation work, so the policy's evaluate()-cost instrument cannot exercise
// it; this is the frozen substitute: wall time for a fixed amount of search.
// usage: searchcost PARAMS EPD DEPTH on|off [HASH_MB]
#include "chess/position.hpp"
#include "chess/zobrist.hpp"
#include "evaluation/eval_params.hpp"
#include "search/search.hpp"
#include "utilities/types.hpp"
#include <atomic>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <memory>
#include <string>
#include <vector>
using namespace stockbear;

int main(int argc, char** argv) {
    if (argc < 5) { std::fprintf(stderr, "usage: searchcost PARAMS EPD DEPTH on|off [HASH_MB]\n"); return 2; }
    Zobrist::init();
    EvalParams par; std::string err;
    if (!load_eval_params_file(argv[1], &par, &err)) {
        std::fprintf(stderr, "LOAD FAILED %s: %s\n", argv[1], err.c_str()); return 2;
    }
    std::fprintf(stderr, "EvalParams loaded: %s\n", argv[1]);
    apply_eval_params(par);
    const int depth = std::atoi(argv[3]);
    const bool on = std::string(argv[4]) == "on";
    const int hashMb = argc > 5 ? std::atoi(argv[5]) : 16;
    std::vector<std::string> fens;
    std::ifstream in(argv[2]); std::string line;
    while (std::getline(in, line)) if (!line.empty()) fens.push_back(line);
    if (fens.empty()) { std::fprintf(stderr, "empty corpus\n"); return 2; }
    std::uint64_t totalNodes = 0;
    const auto t0 = std::chrono::steady_clock::now();
    for (const std::string& fen : fens) {
        Position p;
        if (!parse_fen(fen, p, &err)) { std::fprintf(stderr, "bad fen\n"); return 2; }
        TranspositionTable tt(hashMb);
        SearchParams sp; sp.ttEval = true; sp.ttExtensionAgnostic = on;
        SearchLimits lim; lim.depth = depth;
        std::atomic<bool> stop{false};
        auto s = std::make_unique<Search>(tt, sp);
        totalNodes += s->run(p, lim, stop).nodes;
    }
    const auto t1 = std::chrono::steady_clock::now();
    const double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    std::printf("arm %s depth %d positions %zu nodes %llu ms %.3f\n",
                on ? "on" : "off", depth, fens.size(), (unsigned long long)totalNodes, ms);
    return 0;
}
