// exp-0067 JOINT sequential-replay efficacy diagnostic (NOT a strength measurement).
// The mechanism only exists ACROSS moves, so an independent-position corpus
// cannot see it. This replays real games in move order: OFF builds a fresh
// Search per position (exactly the shipped UCI behaviour), ON reuses one Search
// for the whole game (exactly the candidate behaviour), both at fixed depth.
// usage: joint_lifetime PARAMS GAMESFILE DEPTH [HASH_MB]
// GAMESFILE: lines "# game N" start a game; other non-empty lines are FENs.
#include "chess/position.hpp"
#include "chess/zobrist.hpp"
#include "evaluation/eval_params.hpp"
#include "search/search.hpp"
#include "utilities/types.hpp"
#include <atomic>
#include <cstdio>
#include <fstream>
#include <memory>
#include <string>
#include <vector>
using namespace stockbear;

int main(int argc, char** argv) {
    if (argc < 4) { std::fprintf(stderr, "usage: joint_lifetime PARAMS GAMESFILE DEPTH [HASH_MB]\n"); return 2; }
    Zobrist::init();
    EvalParams par; std::string err;
    if (!load_eval_params_file(argv[1], &par, &err)) {
        std::fprintf(stderr, "LOAD FAILED %s: %s\n", argv[1], err.c_str()); return 2;
    }
    std::fprintf(stderr, "EvalParams loaded: %s\n", argv[1]);
    apply_eval_params(par);
    const int depth = std::atoi(argv[3]);
    const int hashMb = argc > 4 ? std::atoi(argv[4]) : 16;
    std::ifstream in(argv[2]); std::string line;
    std::vector<std::vector<std::string>> games;
    while (std::getline(in, line)) {
        if (line.rfind("# game", 0) == 0) { games.emplace_back(); continue; }
        if (line.empty() || line[0] == '#') continue;
        if (games.empty()) games.emplace_back();
        games.back().push_back(line);
    }
    std::printf("# game positions nodes_off nodes_on ratio\n");
    unsigned long long totOff = 0, totOn = 0;
    for (std::size_t g = 0; g < games.size(); ++g) {
        if (games[g].empty()) continue;
        unsigned long long off = 0, on = 0;
        {   // OFF: fresh object per position, tables zeroed in run().
            TranspositionTable tt(hashMb);
            SearchParams sp; sp.ttEval = true;
            sp.continuationHistory = true;
            sp.persistentHistory = false; sp.persistentContinuation = false;
            for (const std::string& fen : games[g]) {
                Position p;
                if (!parse_fen(fen, p, &err)) { std::fprintf(stderr, "bad fen\n"); return 2; }
                SearchLimits lim; lim.depth = depth; std::atomic<bool> stop{false};
                auto s = std::make_unique<Search>(tt, sp);
                off += s->run(p, lim, stop).nodes;
            }
        }
        {   // ON: one object for the whole game, history carried and halved.
            TranspositionTable tt(hashMb);
            SearchParams sp; sp.ttEval = true;
            sp.continuationHistory = true;
            sp.persistentHistory = true; sp.persistentContinuation = true;
            auto s = std::make_unique<Search>(tt, sp);
            for (const std::string& fen : games[g]) {
                Position p;
                if (!parse_fen(fen, p, &err)) { std::fprintf(stderr, "bad fen\n"); return 2; }
                SearchLimits lim; lim.depth = depth; std::atomic<bool> stop{false};
                on += s->run(p, lim, stop).nodes;
            }
        }
        totOff += off; totOn += on;
        std::printf("%zu %zu %llu %llu %.6f\n", g, games[g].size(), off, on,
                    double(on) / double(off));
        std::fflush(stdout);
    }
    std::printf("# TOTAL %llu %llu %.6f\n", totOff, totOn, double(totOn) / double(totOff));
    return 0;
}
