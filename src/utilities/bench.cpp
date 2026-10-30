#include "utilities/bench.hpp"
#include "utilities/bench_positions.hpp"
#include "chess/fen.hpp"
#include "chess/position.hpp"
#include "search/search.hpp"
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

int benchmark_cli(int argc, char** argv) {
    SearchLimits limits;
    limits.depth = 4;
    std::size_t hash = 16;
    bool perft = false, gotDepth = false, gotNodes = false;
    for (int i = 0; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--perft") { perft = true; continue; }
        if ((arg == "--depth" || arg == "--nodes" || arg == "--hash") && i + 1 < argc) {
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
            } else {
                if (n > 512) { std::cerr << "Hash must be 1..512 MB\n"; return 2; }
                hash = static_cast<std::size_t>(n);
            }
        } else { std::cerr << "Unknown or incomplete bench option: " << arg << '\n'; return 2; }
    }
    if ((gotDepth && gotNodes) || (perft && (gotDepth || gotNodes))) {
        std::cerr << "Choose one of --depth, --nodes or --perft\n"; return 2;
    }
    if (perft) return perft_suite();

    TranspositionTable table(hash);
    std::cout << "# StockBear " << kEngineVersion << "; threads=1; hash_requested_mb=" << hash
              << "; hash_allocated_bytes=" << table.allocated_bytes() << "; mode="
              << (gotNodes ? "nodes" : "depth") << ';' << (gotNodes ? limits.nodes : limits.depth) << '\n';
    std::cout << "name,bestmove,depth,score_type,score,nodes,time_us,nps,hashfull,pv,fen\n";
    for (const auto& c : SearchCases) {
        Position p; std::string error;
        if (!p.set(c.fen, &error)) {
            std::cerr << "Invalid benchmark position " << c.name << ": " << error << '\n'; return 1;
        }
        table.clear();
        auto search = std::make_unique<Search>(table);
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
    }
    return 0;
}
}
