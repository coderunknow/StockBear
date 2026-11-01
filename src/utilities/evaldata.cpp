// `stockbear eval` and `stockbear evaldata`: the evaluation as data.
//
//   eval --fen FEN [--params FILE] [--top N]
//       Print the score and the largest per-parameter contributions. Used to
//       explain a tuned parameter set and to debug the breakdown/evaluate
//       agreement.
//
//   evaldata --input FILE [--output FILE] [--params FILE] [--check]
//       Emit the tuner's design matrix: for every FEN, the phase and the
//       per-parameter counts (White minus Black) that multiply the parameter
//       values. `--check` instead verifies that the counts reproduce
//       evaluate() exactly, including with perturbed parameters.
#include "evaluation/evaluation.hpp"
#include "chess/fen.hpp"
#include "chess/position.hpp"
#include "utilities/bench.hpp"

#include <algorithm>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace stockbear {
namespace {

bool parse_params(int argc, char** argv, int* next, EvalParams* params) {
    if (*next + 1 >= argc) return false;
    std::string error;
    if (!load_eval_params_file(argv[*next + 1], params, &error)) {
        std::cerr << "Invalid parameter file: " << error << '\n';
        return false;
    }
    if (!error.empty()) std::cerr << "note: " << error << '\n';
    ++*next;
    return true;
}

bool read_lines(const std::string& path, std::vector<std::string>* lines) {
    std::ifstream in(path);
    if (!in) {
        std::cerr << "Cannot open " << path << '\n';
        return false;
    }
    std::string line;
    while (std::getline(in, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty() || line[0] == '#') continue;
        lines->push_back(line);
    }
    return !lines->empty();
}
} // namespace

int eval_cli(int argc, char** argv) {
    std::string fen;
    std::size_t top = 12;
    EvalParams params = default_eval_params();
    bool applyLater = false;
    for (int i = 0; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--fen" && i + 1 < argc) fen = argv[++i];
        else if (arg == "--params" && i + 1 < argc) {
            // Parameters must be installed before a Position is created,
            // because Position keeps material/piece-square accumulators.
            if (!parse_params(argc, argv, &i, &params)) return 2;
            applyLater = true;
        } else if (arg == "--top" && i + 1 < argc) {
            top = std::size_t(std::max(0, std::atoi(argv[++i])));
        } else {
            std::cerr << "Unknown or incomplete eval option: " << arg << '\n';
            return 2;
        }
    }
    if (fen.empty()) {
        std::cerr << "Usage: stockbear eval --fen FEN [--params FILE] [--top N]\n";
        return 2;
    }
    std::string error;
    if (applyLater && !apply_eval_params(params, &error)) {
        std::cerr << "Invalid parameter set: " << error << '\n';
        return 2;
    }
    Position p;
    if (!p.set(fen, &error)) {
        std::cerr << "Invalid FEN: " << error << '\n';
        return 2;
    }
    const EvalBreakdown bd = eval_breakdown(p);
    const EvalParams& active = active_eval_params();
    const int whiteScore = eval_from_breakdown(bd, active);
    std::cout << "fen " << p.fen() << '\n'
              << "side_to_move " << (p.side_to_move() == White ? "white" : "black") << '\n'
              << "phase " << bd.phase << '\n'
              << "acc_mg " << p.acc_mg(White) << ' ' << p.acc_mg(Black) << '\n'
              << "acc_eg " << p.acc_eg(White) << ' ' << p.acc_eg(Black) << '\n'
              << "score " << evaluate(p) << '\n'
              << "score_from_breakdown " << (p.side_to_move() == White ? whiteScore : -whiteScore)
              << " (" << whiteScore << " from White's side)\n"
              << "params_checksum " << std::hex << eval_params_checksum(active) << std::dec << '\n';
    struct Row { std::string name; long long mg, eg, total; };
    std::vector<Row> rows;
    for (int i = 0; i < EvalParamNB; ++i) {
        const long long cm = static_cast<long long>(active.mg[std::size_t(i)]) * bd.mg[std::size_t(i)];
        const long long ce = static_cast<long long>(active.eg[std::size_t(i)]) * bd.eg[std::size_t(i)];
        const long long total = (cm * bd.phase + ce * (24 - bd.phase)) / 24;
        if (bd.mg[std::size_t(i)] == 0 && bd.eg[std::size_t(i)] == 0) continue;
        rows.push_back({eval_param_table()[std::size_t(i)].name,
                        static_cast<long long>(bd.mg[std::size_t(i)]),
                        static_cast<long long>(bd.eg[std::size_t(i)]), total});
    }
    std::sort(rows.begin(), rows.end(), [](const Row& a, const Row& b) {
        return std::llabs(a.total) > std::llabs(b.total);
    });
    std::cout << "contributions (white minus black, centipawns):\n";
    for (std::size_t i = 0; i < std::min(top, rows.size()); ++i)
        std::cout << "  " << rows[i].name << " count_mg=" << rows[i].mg
                  << " count_eg=" << rows[i].eg << " value=" << rows[i].total << '\n';
    return 0;
}

int evaldata_cli(int argc, char** argv) {
    std::string input, output;
    EvalParams params = default_eval_params();
    bool applyLater = false, check = false;
    for (int i = 0; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--input" && i + 1 < argc) input = argv[++i];
        else if (arg == "--output" && i + 1 < argc) output = argv[++i];
        else if (arg == "--check") check = true;
        else if (arg == "--params" && i + 1 < argc) {
            if (!parse_params(argc, argv, &i, &params)) return 2;
            applyLater = true;
        } else {
            std::cerr << "Unknown or incomplete evaldata option: " << arg << '\n';
            return 2;
        }
    }
    if (input.empty()) {
        std::cerr << "Usage: stockbear evaldata --input FILE [--output FILE] [--params FILE] [--check]\n";
        return 2;
    }
    std::string error;
    if (applyLater && !apply_eval_params(params, &error)) {
        std::cerr << "Invalid parameter set: " << error << '\n';
        return 2;
    }
    std::vector<std::string> lines;
    if (!read_lines(input, &lines)) return 2;

    std::ostream* out = &std::cout;
    std::ofstream file;
    if (!output.empty()) {
        file.open(output);
        if (!file) { std::cerr << "Cannot write " << output << '\n'; return 2; }
        out = &file;
    }
    const EvalParams& active = active_eval_params();
    std::size_t mismatches = 0, positions = 0;
    if (check) {
        for (const std::string& line : lines) {
            Position p;
            if (!p.set(line, &error)) {
                std::cerr << "Invalid FEN in " << input << ": " << line << " (" << error << ")\n";
                return 2;
            }
            ++positions;
            const EvalBreakdown bd = eval_breakdown(p);
            const int white = eval_from_breakdown(bd, active);
            const int expected = p.side_to_move() == White ? white : -white;
            if (evaluate(p) != expected) {
                ++mismatches;
                std::cout << "MISMATCH " << p.fen() << " evaluate=" << evaluate(p)
                          << " breakdown=" << expected << '\n';
            }
        }
        std::cout << "positions " << positions << " mismatches " << mismatches << '\n';
        return mismatches == 0 ? 0 : 1;
    }

    *out << "# stockbear evaldata; params_checksum " << std::hex << eval_params_checksum(active)
         << std::dec << "; entries " << EvalParamNB << '\n';
    *out << "fen,phase";
    for (int i = 0; i < EvalParamNB; ++i) *out << ",mg_" << eval_param_table()[std::size_t(i)].name;
    for (int i = 0; i < EvalParamNB; ++i) *out << ",eg_" << eval_param_table()[std::size_t(i)].name;
    *out << ",score\n";
    for (const std::string& line : lines) {
        Position p;
        if (!p.set(line, &error)) {
            std::cerr << "Invalid FEN in " << input << ": " << line << " (" << error << ")\n";
            return 2;
        }
        const EvalBreakdown bd = eval_breakdown(p);
        *out << line << ',' << bd.phase;
        for (int i = 0; i < EvalParamNB; ++i) *out << ',' << bd.mg[std::size_t(i)];
        for (int i = 0; i < EvalParamNB; ++i) *out << ',' << bd.eg[std::size_t(i)];
        *out << ',' << evaluate(p) << '\n';
        ++positions;
    }
    std::cerr << "wrote " << positions << " rows\n";
    return 0;
}
} // namespace stockbear
