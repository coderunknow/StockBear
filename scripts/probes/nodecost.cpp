// exp-0065 per-node cost probe (NOT a strength measurement).
// Fixed NODE budget per position isolates per-node overhead, which is the real
// risk at fixed time; fixed-depth timing would confound it with tree size.
// usage: nodecost PARAMS EPD NODES on|off SWITCH [HASH_MB]
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
    if (argc < 6) { std::fprintf(stderr, "usage: nodecost PARAMS EPD NODES on|off SWITCH [HASH_MB]\n"); return 2; }
    Zobrist::init();
    EvalParams par; std::string err;
    if (!load_eval_params_file(argv[1], &par, &err)) {
        std::fprintf(stderr, "LOAD FAILED %s: %s\n", argv[1], err.c_str()); return 2;
    }
    std::fprintf(stderr, "EvalParams loaded: %s\n", argv[1]);
    apply_eval_params(par);
    const long long nodes = std::atoll(argv[3]);
    const bool on = std::string(argv[4]) == "on";
    const std::string which = argv[5];
    const int hashMb = argc > 6 ? std::atoi(argv[6]) : 16;
    std::vector<std::string> fens;
    std::ifstream in(argv[2]); std::string line;
    while (std::getline(in, line)) if (!line.empty() && line[0] != '#') fens.push_back(line);
    if (fens.empty()) { std::fprintf(stderr, "empty corpus\n"); return 2; }
    std::uint64_t total = 0;
    const auto t0 = std::chrono::steady_clock::now();
    // One Search for the whole corpus when the switch persists state, matching
    // how it behaves across moves in a game.
    TranspositionTable tt(hashMb);
    SearchParams sp; sp.ttEval = true;
    if (which == "persistenthistory") sp.persistentHistory = on;
    else if (which == "ttextensionagnostic") sp.ttExtensionAgnostic = on;
    else if (which == "persistentcontinuation") {
        // exp-0066: the feature is ON in BOTH arms; only lifetime varies.
        sp.continuationHistory = true;
        sp.persistentContinuation = on;
    }
    else { std::fprintf(stderr, "unknown switch %s\n", which.c_str()); return 2; }
    auto s = std::make_unique<Search>(tt, sp);
    for (const std::string& fen : fens) {
        Position p;
        if (!parse_fen(fen, p, &err)) { std::fprintf(stderr, "bad fen\n"); return 2; }
        tt.clear();
        SearchLimits lim; lim.hasNodes = true; lim.nodes = nodes;
        std::atomic<bool> stop{false};
        total += s->run(p, lim, stop).nodes;
    }
    const auto t1 = std::chrono::steady_clock::now();
    const double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    std::printf("switch %s arm %s nodes_budget %lld positions %zu nodes %llu ms %.3f\n",
                which.c_str(), on ? "on" : "off", nodes, fens.size(),
                (unsigned long long)total, ms);
    return 0;
}
