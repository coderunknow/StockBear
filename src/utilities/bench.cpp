#include "utilities/bench.hpp"
#include "evaluation/eval_params.hpp"
#include "utilities/bench_positions.hpp"
#include "chess/dead_position.hpp"
#include "chess/fen.hpp"
#include "chess/position.hpp"
#include "search/search.hpp"
#include <sstream>
#include <utility>
#include <vector>
#include <atomic>
#include <charconv>
#include <chrono>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <memory>
#include <string>

namespace stockbear {
namespace {
bool parse_unsigned(const std::string& s, std::uint64_t& n, std::uint64_t max) {
    if (s.empty()) return false;
    const auto r = std::from_chars(s.data(), s.data() + s.size(), n);
    return r.ec == std::errc() && r.ptr == s.data() + s.size() && n <= max;
}
using Clock = std::chrono::steady_clock;
std::uint64_t micros(Clock::time_point start) {
    return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::microseconds>(Clock::now() - start).count());
}
std::uint64_t nps(std::uint64_t nodes, std::uint64_t us) {
    if (!us) us = 1;
    return static_cast<std::uint64_t>(static_cast<long double>(nodes) * 1000000.0L / us);
}
int perft_suite() {
    std::cout << "# StockBear " << kEngineVersion << "; perft suite; one thread\n";
    std::cout << "name,depth,expected,actual,time_us,nps,pass,fen\n";
    bool all = true;
    for (const auto& c : PerftCases) {
        Position p; std::string error;
        if (!p.set(c.fen, &error)) {
            std::cerr << "Invalid benchmark position " << c.name << ": " << error << '\n';
            return 1;
        }
        const auto start = Clock::now();
        const std::uint64_t actual = p.perft(c.depth), us = micros(start);
        const bool pass = actual == c.expected;
        all = all && pass;
        std::cout << '"' << c.name << "\"," << c.depth << ',' << c.expected << ',' << actual << ','
                  << us << ',' << nps(actual, us) << ',' << (pass ? "PASS" : "FAIL") << ",\""
                  << c.fen << "\"\n";
    }
    return all ? 0 : 1;
}
}

int perft_cli(int argc, char** argv) {
    if (argc < 1) { std::cerr << "Usage: stockbear perft DEPTH [--fen FEN] [--divide]\n"; return 2; }
    std::uint64_t depth = 0;
    if (!parse_unsigned(argv[0], depth, 20)) { std::cerr << "Invalid perft depth (0..20)\n"; return 2; }
    std::string fen = START_FEN;
    bool divide = false;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--fen" && i + 1 < argc) fen = argv[++i];
        else if (arg == "--divide") divide = true;
        else { std::cerr << "Unknown or incomplete perft option: " << arg << '\n'; return 2; }
    }
    Position p; std::string error;
    if (!p.set(fen, &error)) { std::cerr << "Invalid FEN: " << error << '\n'; return 2; }
    const auto start = Clock::now();
    std::uint64_t nodes = 0;
    if (divide && depth > 0) {
        MoveList moves;
        generate_moves(p, moves);
        for (const ExtMove& em : moves) {
            p.make_move(em.move);
            const std::uint64_t count = p.perft(int(depth) - 1);
            p.unmake_move(em.move);
            nodes += count;
            std::cout << move_to_uci(em.move) << ": " << count << '\n';
        }
    } else nodes = p.perft(int(depth));
    const auto us = micros(start);
    std::cout << "nodes " << nodes << " time_us " << us << " nps " << nps(nodes, us) << '\n';
    return 0;
}

int deadpos_cli(int argc, char** argv) {
    std::string fen;
    DeadLimits limits;
    bool quiet = false;
    for (int i = 0; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--fen" && i + 1 < argc) fen = argv[++i];
        else if (arg == "--quiet") quiet = true;
        else if (arg == "--no-exhaustive") limits.allowExhaustive = false;
        else if (arg == "--witness-depth" && i + 1 < argc) {
            std::uint64_t n = 0;
            if (!parse_unsigned(argv[++i], n, 64) || n == 0) { std::cerr << "Invalid --witness-depth\n"; return 2; }
            limits.witnessMaxDepth = int(n);
        } else if (arg == "--witness-nodes" && i + 1 < argc) {
            if (!parse_unsigned(argv[++i], limits.witnessNodes, 1000000000ULL)) { std::cerr << "Invalid --witness-nodes\n"; return 2; }
        } else if (arg == "--states" && i + 1 < argc) {
            if (!parse_unsigned(argv[++i], limits.componentStates, 50000000ULL)) { std::cerr << "Invalid --states\n"; return 2; }
        } else if (arg == "--depth" && i + 1 < argc) {
            std::uint64_t n = 0;
            if (!parse_unsigned(argv[++i], n, 1000000) || n == 0) { std::cerr << "Invalid --depth\n"; return 2; }
            limits.componentMaxDepth = int(n);
        } else { std::cerr << "Unknown or incomplete deadpos option: " << arg << '\n'; return 2; }
    }
    if (fen.empty()) { std::cerr << "Usage: stockbear deadpos --fen FEN [--states N] [--witness-depth N] [--no-exhaustive]\n"; return 2; }
    Position p;
    std::string error;
    if (!p.set(fen, &error)) { std::cerr << "Invalid FEN: " << error << '\n'; return 2; }

    const auto start = Clock::now();
    const DeadResult result = analyze_dead_position(p, limits);
    const std::uint64_t us = micros(start);

    std::cout << "fen " << p.fen() << '\n'
              << "status " << to_string(result.status) << '\n'
              << "exhaustive_complete " << (result.exhaustiveComplete ? "yes" : "no") << '\n'
              << "witness_visited " << result.visited << '\n'
              << "component_states " << result.states << '\n'
              << "component_expanded " << result.expanded << '\n'
              << "time_us " << us << '\n'
              << "reason " << result.reason << '\n';
    if (!result.witness.empty()) {
        std::cout << "witness";
        Position walk = p;
        for (Move m : result.witness) {
            std::cout << ' ' << move_to_uci(m);
            walk.make_move(m);
        }
        std::cout << '\n';
        std::cout << "witness_ends_in_mate " << (walk.in_check() && !walk.has_legal_moves() ? "yes" : "NO") << '\n';
    }
    if (!quiet) std::cout << std::flush;
    return result.status == DeadStatus::Unknown ? 1 : 0;
}

namespace {
// Applies a single "name=0|1" ablation switch. Returns false for unknown names.
bool apply_param(SearchParams& params, const std::string& key, const std::string& value) {
    if (value != "0" && value != "1") return false;
    const bool on = value == "1";
    if (key == "aspiration") params.aspiration = on;
    else if (key == "nullMove") params.nullMove = on;
    else if (key == "lmr") params.lmr = on;
    else if (key == "reverseFutility") params.reverseFutility = on;
    else if (key == "futility") params.futility = on;
    else if (key == "seePruning") params.seePruning = on;
    else if (key == "checkExtension") params.checkExtension = on;
    else if (key == "counterMoves") params.counterMoves = on;
    else if (key == "continuationHistory") params.continuationHistory = on;
    else if (key == "captureHistory") params.captureHistory = on;
    else if (key == "historyMaluses") params.historyMaluses = on;
    else if (key == "lmrHistory") params.lmrHistory = on;
    else return false;
    return true;
}

std::string params_text(const SearchParams& params) {
    std::ostringstream out;
    out << "aspiration=" << int(params.aspiration)
        << ",nullMove=" << int(params.nullMove)
        << ",lmr=" << int(params.lmr)
        << ",reverseFutility=" << int(params.reverseFutility)
        << ",futility=" << int(params.futility)
        << ",seePruning=" << int(params.seePruning)
        << ",checkExtension=" << int(params.checkExtension)
        << ",counterMoves=" << int(params.counterMoves)
        << ",continuationHistory=" << int(params.continuationHistory)
        << ",captureHistory=" << int(params.captureHistory)
        << ",historyMaluses=" << int(params.historyMaluses)
        << ",lmrHistory=" << int(params.lmrHistory);
    return out.str();
}
}

int benchmark_cli(int argc, char** argv) {
    SearchLimits limits;
    limits.depth = 4;
    std::size_t hash = 16;
    SearchParams params;
    std::vector<std::pair<std::string, std::string>> overrides;
    std::string evalParamsPath;
    bool perft = false, gotDepth = false, gotNodes = false, gotMoveTime = false;
    for (int i = 0; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--perft") { perft = true; continue; }
        if (arg == "--param" && i + 1 < argc) {
            const std::string text = argv[++i];
            const std::size_t eq = text.find('=');
            if (eq == std::string::npos || !apply_param(params, text.substr(0, eq), text.substr(eq + 1))) {
                std::cerr << "Invalid --param (expected feature=0|1): " << text << '\n';
                return 2;
            }
            overrides.emplace_back(text.substr(0, eq), text.substr(eq + 1));
            continue;
        }
        if (arg == "--params") {
            // Same parameter file format as `eval`/`evaldata`: bench a candidate
            // evaluation without rebuilding the engine. An empty path is an
            // error, not a silent fallback to the default evaluation.
            if (i + 1 >= argc || std::string(argv[i + 1]).empty()) {
                std::cerr << "--params needs a file path\n";
                return 2;
            }
            evalParamsPath = argv[++i];
            continue;
        }
        if ((arg == "--depth" || arg == "--nodes" || arg == "--hash" || arg == "--movetime") && i + 1 < argc) {
            std::uint64_t n = 0;
            const std::string text = argv[++i];
            if (!parse_unsigned(text, n, 1000000000000ULL) || n == 0) {
                std::cerr << "Invalid value for " << arg << '\n'; return 2;
            }
            if (arg == "--depth") {
                if (n > MAX_PLY - 2) { std::cerr << "Depth too large\n"; return 2; }
                limits.depth = int(n); gotDepth = true;
            } else if (arg == "--nodes") {
                limits.hasNodes = true; limits.nodes = n; limits.depth = 0; gotNodes = true;
            } else if (arg == "--movetime") {
                limits.moveTimeMs = std::int64_t(n); limits.depth = 0; gotMoveTime = true;
            } else {
                if (n > 512) { std::cerr << "Hash must be 1..512 MB\n"; return 2; }
                hash = static_cast<std::size_t>(n);
            }
        } else { std::cerr << "Unknown or incomplete bench option: " << arg << '\n'; return 2; }
    }
    const int modes = int(gotDepth) + int(gotNodes) + int(gotMoveTime);
    if (modes > 1 || (perft && modes > 0)) {
        std::cerr << "Choose one of --depth, --nodes, --movetime or --perft\n"; return 2;
    }
    if (perft) return perft_suite();

    if (!evalParamsPath.empty()) {
        // Install the candidate evaluation before any Position exists.
        EvalParams loaded = default_eval_params();
        std::string evalError;
        if (!load_eval_params_file(evalParamsPath, &loaded, &evalError) ||
            !apply_eval_params(loaded, &evalError)) {
            std::cerr << "Invalid parameter file " << evalParamsPath << ": " << evalError << '\n';
            return 2;
        }
    }

    TranspositionTable table(hash);
    std::cout << "# StockBear " << kEngineVersion << "; threads=1; hash_requested_mb=" << hash
              << "; hash_allocated_bytes=" << table.allocated_bytes() << "; mode="
              << (gotNodes ? "nodes" : gotMoveTime ? "movetime" : "depth") << ';'
              << (gotNodes ? limits.nodes : gotMoveTime ? std::uint64_t(limits.moveTimeMs) : std::uint64_t(limits.depth))
              << "; params=" << params_text(params) << '\n';
    std::cout << "name,bestmove,depth,score_type,score,nodes,time_us,nps,hashfull,pv,fen\n";
    // Deterministic fingerprint of move/score/node/PV data, so a CI run can
    // detect an unintended search behaviour change without comparing timings.
    std::uint64_t signature = 0xCBF29CE484222325ULL;
    auto absorb = [&signature](const std::string& text) {
        for (unsigned char c : text) {
            signature ^= c;
            signature *= 0x100000001B3ULL;
        }
    };
    for (const auto& c : SearchCases) {
        Position p; std::string error;
        if (!p.set(c.fen, &error)) {
            std::cerr << "Invalid benchmark position " << c.name << ": " << error << '\n'; return 1;
        }
        table.clear();
        auto search = std::make_unique<Search>(table, params);
        std::atomic<bool> stop{false};
        const SearchResult result = search->run(p, limits, stop);
        const int score = is_mate_value(result.score) ? mate_value_to_moves(result.score) : result.score;
        std::cout << '"' << c.name << "\"," << (is_ok(result.bestMove) ? move_to_uci(result.bestMove) : "0000")
                  << ',' << result.depth << ',' << (is_mate_value(result.score) ? "mate" : "cp") << ',' << score
                  << ',' << result.nodes << ',' << result.timeUs << ','
                  << nps(result.nodes, std::uint64_t(result.timeUs)) << ',' << result.hashfull << ",\"";
        for (std::size_t i = 0; i < result.pv.size(); ++i) {
            if (i) std::cout << ' ';
            std::cout << move_to_uci(result.pv[i]);
        }
        std::cout << "\",\"" << c.fen << "\"\n";
        absorb(std::string(c.name) + "|" + (is_ok(result.bestMove) ? move_to_uci(result.bestMove) : "0000"));
        absorb(std::to_string(result.depth) + "|" + std::to_string(result.score) + "|" +
               std::to_string(result.nodes));
        for (Move m : result.pv) absorb(move_to_uci(m));
    }
    if (gotMoveTime) {
        // Depth and node count depend on wall-clock time here, and the signature
        // absorbs both, so it is not reproducible between runs of the same build.
        std::cout << "# signature unavailable (movetime mode is not deterministic)\n";
    } else {
        std::cout << "# signature " << std::hex << signature << std::dec << '\n';
    }
    return 0;
}
}
