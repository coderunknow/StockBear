// Diagnostic only: ns per full evaluate() under a given EvalParams file.
// Prints "full <ns>" so recovery_eval_cost.py can alternate A/B in-process pairs.
#include "chess/position.hpp"
#include "chess/zobrist.hpp"
#include "evaluation/evaluation.hpp"
#include "evaluation/eval_params.hpp"
#include <chrono>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>
using namespace stockbear;

int main(int argc, char** argv) {
    if (argc < 2) { std::fprintf(stderr, "usage: evalprof PARAMS [EPD]\n"); return 2; }
    Zobrist::init();
    EvalParams par;
    std::string perr;
    if (!load_eval_params_file(argv[1], &par, &perr)) {
        std::fprintf(stderr, "load failed: %s\n", perr.c_str()); return 2;
    }
    apply_eval_params(par);
    const char* epd = argc > 2 ? argv[2] : "/tmp/race_fens.epd";
    std::ifstream in(epd);
    std::string line;
    std::vector<Position> positions;
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        std::string err;
        Position p;
        if (!parse_fen(line, p, &err)) continue;
        positions.push_back(p);
    }
    if (positions.empty()) { std::fprintf(stderr, "no positions\n"); return 2; }
    volatile int sink = 0;
    for (const auto& p : positions) sink += evaluate(p);   // warm
    const int reps = 12;
    auto t0 = std::chrono::steady_clock::now();
    for (int r = 0; r < reps; ++r)
        for (const auto& p : positions) sink += evaluate(p);
    auto t1 = std::chrono::steady_clock::now();
    const double ns = std::chrono::duration<double, std::nano>(t1 - t0).count()
                    / (double(reps) * double(positions.size()));
    std::printf("full %.4f\n", ns);
    return sink == 0x7fffffff ? 1 : 0;
}
