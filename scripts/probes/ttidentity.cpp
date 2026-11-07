// DIAGNOSTIC PROBE (exp-0064 investigation): why do main-TT probes miss?
// Links the real engine core and runs real fixed-depth searches. Requires
// -DSB_TT_IDENTITY_DEBUG=1 in the core build; makes NO strength claim.
#include "chess/position.hpp"
#include "chess/zobrist.hpp"
#include "evaluation/eval_params.hpp"
#include "search/search.hpp"
#include <atomic>
#include <cstdio>
#include <fstream>
#include <string>
using namespace stockbear;

int main(int argc, char** argv) {
    if (argc < 4) {
        std::fprintf(stderr, "usage: ttidentity PARAMS EPD DEPTH [TTEVAL 0|1]\n");
        return 2;
    }
    Zobrist::init();
    EvalParams par;
    std::string err;
    if (!load_eval_params_file(argv[1], &par, &err)) {
        std::fprintf(stderr, "load failed: %s\n", err.c_str()); return 2;
    }
    apply_eval_params(par);
    const int depth = std::atoi(argv[3]);
    SearchParams sp;
    sp.ttEval = argc > 4 ? std::atoi(argv[4]) != 0 : true;
    std::ifstream in(argv[2]);
    std::string line;
    std::uint64_t positions = 0, nodes = 0;
    TranspositionTable tt(16);
    std::atomic<bool> stop{false};
#ifdef SB_TT_IDENTITY_DEBUG
    ttIdentityStats = TTIdentityStats{};
#endif
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        Position p;
        if (!parse_fen(line, p, &err)) {
            std::fprintf(stderr, "bad fen: %s\n", err.c_str()); return 2;
        }
        tt.clear();
        Search s(tt, sp);
        SearchLimits lim;
        lim.depth = depth;
        const SearchResult r = s.run(p, lim, stop);
        nodes += r.nodes;
        ++positions;
    }
#ifdef SB_TT_IDENTITY_DEBUG
    const auto& st = ttIdentityStats;
    std::printf("positions %llu depth %d nodes %llu\n",
                (unsigned long long)positions, depth, (unsigned long long)nodes);
    std::printf("probes %llu hits %llu hit_rate %.6f\n",
                (unsigned long long)st.probes, (unsigned long long)st.hits,
                st.probes ? double(st.hits) / double(st.probes) : 0.0);
    std::printf("miss_ext_only %llu (%.4f%% of probes)\n",
                (unsigned long long)st.missExtOnly,
                st.probes ? 100.0 * double(st.missExtOnly) / double(st.probes) : 0.0);
    std::printf("miss_rule50_only %llu (%.4f%%)\n",
                (unsigned long long)st.missRule50Only,
                st.probes ? 100.0 * double(st.missRule50Only) / double(st.probes) : 0.0);
    std::printf("miss_ext_other_bucket %llu (%.4f%% of probes)\n",
                (unsigned long long)st.missExtOtherBucket,
                st.probes ? 100.0 * double(st.missExtOtherBucket) / double(st.probes) : 0.0);
    std::printf("miss_ext_other_bucket_deep %llu (%.4f%% of probes)\n",
                (unsigned long long)st.missExtOtherBucketDeep,
                st.probes ? 100.0 * double(st.missExtOtherBucketDeep) / double(st.probes) : 0.0);
    std::printf("miss_context_only %llu (%.4f%%)\n",
                (unsigned long long)st.missContextOnly,
                st.probes ? 100.0 * double(st.missContextOnly) / double(st.probes) : 0.0);
#else
    std::printf("built without SB_TT_IDENTITY_DEBUG; positions %llu nodes %llu\n",
                (unsigned long long)positions, (unsigned long long)nodes);
#endif
    return 0;
}
