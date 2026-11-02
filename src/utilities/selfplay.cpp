// ---------------------------------------------------------------------------
// selfplay.cpp - deterministic self-play data generation for the neural
// evaluation pipeline (docs/DEV4_TRAINING.md).
//
// Every game starts from a short pseudo-random opening prefix so that the
// corpus is not a thousand copies of one line, is played by the engine itself
// with a jittered node budget, and is written only if it ended by the rules
// (checkmate, stalemate, an automatic draw, or a claimable repetition /
// fifty-move draw). A game that hits the ply cap is discarded rather than
// recorded as a draw: a capped game is not evidence.
//
// Output is line oriented:
//
//   <result> <game-id> <fen>
//
// where <result> is 1, 0.5 or 0 from the point of view of the side to move in
// that FEN. The engine's own evaluation is not stored, so the corpus stays
// usable after the evaluation changes.
// ---------------------------------------------------------------------------
#include "utilities/selfplay.hpp"

#include "chess/fen.hpp"
#include "chess/position.hpp"
#include "search/search.hpp"

#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace stockbear {
namespace {

// SplitMix64, the generator the repository already uses for deterministic
// constants, so one seed reproduces exactly one corpus.
struct Rng {
    std::uint64_t state;
    explicit Rng(std::uint64_t seed) : state(seed) {}
    std::uint64_t next() {
        std::uint64_t z = (state += 0x9E3779B97F4A7C15ULL);
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
        return z ^ (z >> 31);
    }
    std::uint64_t below(std::uint64_t bound) { return bound == 0 ? 0 : next() % bound; }
};

bool parse_u64(const std::string& text, std::uint64_t& out) {
    if (text.empty()) return false;
    std::uint64_t value = 0;
    for (char c : text) {
        if (c < '0' || c > '9') return false;
        value = value * 10 + std::uint64_t(c - '0');
    }
    out = value;
    return true;
}

struct Record {
    std::string fen;
    Color side = White;
};

// Game-level adjudication without the exact dead-position analysis. The
// generator must not pay `analyze_dead_position` on every ply (it is a bounded
// proof search); the rules that actually end a game in practice are the
// material, halfmove-clock and repetition rules, and they are all cheap.
// Nothing here is used by the engine's search or by the UCI layer.
bool game_over(const Position& pos) {
    if (pos.has_legal_moves()) {
        if (pos.insufficient_material()) return true;
        if (pos.rule50() >= 100) return true;          // claimable fifty-move
        if (pos.repetition_count() >= 3) return true;  // claimable threefold
        return false;
    }
    return true; // checkmate or stalemate
}

} // namespace

int selfplay_cli(int argc, char** argv) {
    std::uint64_t games = 0, nodes = 4000, seed = 1, maxPlies = 400, hashMb = 8;
    std::string outPath;
    for (int i = 0; i < argc; ++i) {
        const std::string arg = argv[i];
        const auto value = [&](std::uint64_t& slot) {
            return i + 1 < argc && parse_u64(argv[i + 1], slot);
        };
        if (arg == "--games") { if (!value(games)) return 2; ++i; }
        else if (arg == "--nodes") { if (!value(nodes)) return 2; ++i; }
        else if (arg == "--seed") { if (!value(seed)) return 2; ++i; }
        else if (arg == "--maxplies") { if (!value(maxPlies)) return 2; ++i; }
        else if (arg == "--hash") { if (!value(hashMb)) return 2; ++i; }
        else if (arg == "--out") { if (i + 1 >= argc) return 2; outPath = argv[++i]; }
        else {
            std::cerr << "Unknown selfplay argument: " << arg << '\n';
            return 2;
        }
    }
    if (games == 0 || nodes == 0 || outPath.empty()) {
        std::cerr << "StockBear selfplay needs --games N --out FILE [--nodes N] [--seed N] "
                     "[--maxplies N] [--hash MB]\n";
        return 2;
    }
    maxPlies = std::clamp<std::uint64_t>(maxPlies, 20, 1000);
    if (hashMb < 1 || hashMb > 512) {
        std::cerr << "--hash must be 1..512\n";
        return 2;
    }
    std::ofstream out(outPath, std::ios::binary | std::ios::trunc);
    if (!out) {
        std::cerr << "cannot open " << outPath << '\n';
        return 1;
    }

    TranspositionTable table(static_cast<std::size_t>(hashMb));
    SearchParams params;
    Search search(table, params);
    Rng rng(seed);
    std::atomic<bool> stop(false);
    std::uint64_t written = 0, discarded = 0, totalPlies = 0, mates = 0, draws = 0;

    for (std::uint64_t game = 0; game < games; ++game) {
        Position pos;
        std::string error;
        if (!pos.set(START_FEN, &error)) throw std::runtime_error("start position: " + error);
        table.clear();
        table.new_search();

        // Random opening prefix: 0..8 plies. Short enough that the engine still
        // decides the game, long enough that the corpus covers many systems.
        const int openingPlies = int(rng.below(9));
        bool playable = true;
        for (int ply = 0; ply < openingPlies; ++ply) {
            MoveList legal;
            generate_moves(pos, legal, GenType::All);
            if (legal.empty()) { playable = false; break; }
            pos.make_move(legal[rng.below(std::uint64_t(legal.size()))].move);
        }
        if (!playable) { ++discarded; continue; }

        std::vector<Record> records;
        records.reserve(220);
        bool finished = false;
        // Result from the point of view of the side to move in the *final*
        // position. A draw is 0.5 for either side, so only the mate case needs
        // to know whose turn it is.
        double finalResult = 0.5;
        for (std::uint64_t ply = 0; ply < maxPlies; ++ply) {
            MoveList legal;
            generate_moves(pos, legal, GenType::All);
            if (legal.empty()) {
                finished = true;
                finalResult = pos.in_check() ? 0.0 : 0.5; // mated here, or stalemate
                break;
            }
            if (game_over(pos)) {
                finished = true;
                finalResult = 0.5;
                break;
            }

            records.push_back(Record{pos.fen(), pos.side_to_move()});

            SearchLimits limits;
            // Jitter the node budget so the corpus is not one fixed depth.
            limits.nodes = nodes * (80 + rng.below(40)) / 100;
            limits.hasNodes = true;
            const SearchResult result = search.run(pos, limits, stop);
            Move chosen = result.bestMove;
            if (!is_ok(chosen) || !legal.contains(chosen))
                chosen = legal[rng.below(std::uint64_t(legal.size()))].move;
            pos.make_move(chosen);
            ++totalPlies;
        }
        if (!finished) { ++discarded; continue; }

        const Color finalStm = pos.side_to_move();
        const double resultWhite = finalStm == White ? finalResult : 1.0 - finalResult;
        for (const Record& record : records) {
            const double value = record.side == White ? resultWhite : 1.0 - resultWhite;
            out << value << ' ' << game << ' ' << record.fen << '\n';
            ++written;
        }
        out.flush();
        if (pos.in_check() && !pos.has_legal_moves()) ++mates; else ++draws;
    }
    std::cerr << "selfplay: " << games << " games, " << written << " positions, " << discarded
              << " discarded (ply cap), " << totalPlies << " searched plies, " << mates
              << " decisive mates, " << draws << " non-mate finishes\n";
    return 0;
}

} // namespace stockbear
