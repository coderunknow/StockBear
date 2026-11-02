// Development CLI for the neural evaluation.
//
//   stockbear nnue --net FILE --features --input FENS
//       Prints, for every FEN and both perspectives, the sorted feature indices
//       that the incremental accumulator uses. The Python training mirror
//       (scripts/nnue_features.py) must reproduce this exactly; the differential
//       test tests/integration/test_nnue_features.py checks it on a corpus.
//
//   stockbear nnue --net FILE --eval --input FENS
//       Prints the quantified evaluation of every FEN from White's point of
//       view, plus the same value produced by rebuilding the accumulator from
//       scratch. The two columns must agree: that is the incremental-update
//       check, run over a whole corpus rather than one position.
//
//   stockbear nnue --net FILE --info
//       Prints the network identity, size and the selected SIMD kernel.
#include "utilities/nnuecli.hpp"

#include "chess/fen.hpp"
#include "chess/position.hpp"
#include "evaluation/nnue.hpp"
#include "evaluation/nnue_forward.hpp"

#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace stockbear {

int nnue_cli(int argc, char** argv) {
    std::string netPath, inputPath;
    bool wantFeatures = false, wantEval = false, wantInfo = false;
    for (int i = 0; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--net") {
            if (i + 1 >= argc) return 2;
            netPath = argv[++i];
        } else if (arg == "--input") {
            if (i + 1 >= argc) return 2;
            inputPath = argv[++i];
        } else if (arg == "--features") wantFeatures = true;
        else if (arg == "--eval") wantEval = true;
        else if (arg == "--info") wantInfo = true;
        else {
            std::cerr << "Unknown nnue argument: " << arg << '\n';
            return 2;
        }
    }

    if (!netPath.empty()) {
        std::string error;
        const nnue::Network net = nnue::parse_network_file(netPath, &error);
        if (net.l1 == 0) {
            std::cerr << "cannot load network: " << error << '\n';
            return 1;
        }
        if (!nnue::install_network(net, &error)) {
            std::cerr << "cannot install network: " << error << '\n';
            return 1;
        }
    } else if (!nnue::embedded_network_available()) {
        // Feature dumping does not need weights: with one king bucket the
        // feature set is a property of the position alone. Everything else does.
        if (!wantFeatures) {
            std::cerr << "no --net given and this build embeds no network\n";
            return 2;
        }
        if (inputPath.empty()) {
            std::cerr << "--input FILE is required with --features\n";
            return 2;
        }
        std::ifstream in(inputPath);
        if (!in) { std::cerr << "cannot open " << inputPath << '\n'; return 1; }
        std::string line;
        while (std::getline(in, line)) {
            if (line.empty() || line[0] == '#') continue;
            Position pos;
            std::string error;
            if (!pos.set(line, &error)) {
                std::cerr << "bad FEN: " << error << '\n';
                return 1;
            }
            for (int p = 0; p < ColorNB; ++p) {
                std::vector<int> features;
                nnue::feature_list(pos, Color(p), features);
                std::cout << p << ':';
                for (std::size_t i = 0; i < features.size(); ++i)
                    std::cout << (i ? "," : "") << features[i];
                std::cout << '\n';
            }
        }
        return 0;
    } else {
        std::string error;
        if (!nnue::install_embedded_network(&error)) {
            std::cerr << "cannot install embedded network: " << error << '\n';
            return 1;
        }
    }

    const nnue::Network* net = nnue::active_network();
    if (wantInfo || (!wantFeatures && !wantEval)) {
        std::cout << "# StockBear " << kEngineVersion << "\n"
                  << "network " << nnue::network_identity() << "\n"
                  << "buckets " << net->kingBuckets << "\n"
                  << "l1 " << net->l1 << "\n"
                  << "l2 " << net->l2 << "\n"
                  << "inputs " << net->inputCount << "\n"
                  << "parameters " << net->parameter_count() << "\n"
                  << "serialized_bytes "
                  << nnue::serialize_network(*net).size() << "\n"
                  << "act_shift " << net->actShift << "\n"
                  << "h2_shift " << net->h2Shift << "\n"
                  << "out_shift " << net->outShift << "\n"
                  << "kernel " << nnue::forward_kernel_name() << "\n";
        if (!wantFeatures && !wantEval) return 0;
    }

    if (inputPath.empty()) {
        std::cerr << "--input FILE is required with --features or --eval\n";
        return 2;
    }
    std::ifstream in(inputPath);
    if (!in) {
        std::cerr << "cannot open " << inputPath << '\n';
        return 1;
    }
    std::string line;
    std::uint64_t lines = 0;
    while (std::getline(in, line)) {
        if (line.empty() || line[0] == '#') continue;
        Position pos;
        std::string error;
        if (!pos.set(line, &error)) {
            std::cerr << "bad FEN at input line " << (lines + 1) << ": " << error << '\n';
            return 1;
        }
        ++lines;
        if (wantFeatures) {
            for (int p = 0; p < ColorNB; ++p) {
                std::vector<int> features;
                nnue::feature_list(pos, Color(p), features);
                std::cout << p << ':';
                for (std::size_t i = 0; i < features.size(); ++i)
                    std::cout << (i ? "," : "") << features[i];
                std::cout << '\n';
            }
        }
        if (wantEval) {
            const nnue::Accumulator* acc = pos.nnue_accumulator();
            const int incremental = acc != nullptr ? nnue::evaluate(pos, *acc)
                                                  : nnue::evaluate_from_scratch(pos);
            const int scratch = nnue::evaluate_from_scratch(pos);
            // Printed exactly as the engine uses it: centipawns from the side to
            // move's point of view. Converting to White's point of view here
            // would hide the very sign convention the trainer has to match, so
            // it is not done (see the ordering note in nnue_forward.hpp).
            std::cout << incremental << ',' << scratch << '\n';
        }
    }
    return 0;
}

} // namespace stockbear
