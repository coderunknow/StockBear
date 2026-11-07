// Fixed-depth liveness probe: same binary, term OFF vs ON, reports the search
// tree size and bestmove for each position. Tree-change proxy ONLY -- not a
// strength or speed measurement.
//
// Prints one line per position:
//   <nodes_off> <nodes_on> <best_off> <best_on>
// Both parameter files are loaded through the real loader and a failed load is
// a hard error, so a silently-ignored path cannot fake a result.
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
bool load(const char* path, EvalParams* out) {
    std::string err;
    if (!load_eval_params_file(path, out, &err)) {
        std::fprintf(stderr, "LOAD FAILED %s: %s\n", path, err.c_str());
        return false;
    }
    std::fprintf(stderr, "EvalParams loaded: %s\n", path);
    return true;
}

struct Res { std::uint64_t nodes; std::string best; };

Res run_one(const std::string& fen, int depth) {
    Position p;
    std::string err;
    if (!parse_fen(fen, p, &err)) { std::fprintf(stderr, "bad fen\n"); std::exit(2); }
    SearchParams sp;
    sp.ttEval = true;
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
        std::fprintf(stderr, "usage: liveness OFF_PARAMS ON_PARAMS EPD DEPTH\n");
        return 2;
    }
    Zobrist::init();
    EvalParams off, on;
    if (!load(argv[1], &off) || !load(argv[2], &on)) return 2;
    const int depth = std::atoi(argv[4]);
    std::ifstream in(argv[3]);
    std::string line;
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        apply_eval_params(off);
        const Res a = run_one(line, depth);
        apply_eval_params(on);
        const Res b = run_one(line, depth);
        std::printf("%llu %llu %s %s\n", (unsigned long long)a.nodes,
                    (unsigned long long)b.nodes, a.best.c_str(), b.best.c_str());
        std::fflush(stdout);
    }
    return 0;
}
