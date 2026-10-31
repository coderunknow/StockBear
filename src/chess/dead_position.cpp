#include "chess/dead_position.hpp"
#include <algorithm>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace stockbear {
namespace {
// Full identity, rather than a Zobrist key: collisions cannot merge vertices.
// Counters/history do not affect the movement-only graph. Retaining the raw EP
// target is conservative and preserves the exact legal transition relation.
std::string identity(const Position& p) {
    const std::string fen = p.fen();
    auto end = fen.find(' ', fen.find(' ', fen.find(' ', fen.find(' ') + 1) + 1) + 1);
    return fen.substr(0, end);
}
struct Vertex {
    std::string id;
    std::size_t parent;
    Move move;
};
}
ReachabilityResult movement_mate_reachability(const Position& root, std::size_t maxPositions) {
    ReachabilityResult result;
    if (!maxPositions) return result;
    std::vector<Vertex> vertices;
    std::unordered_map<std::string, std::size_t> seen;
    vertices.push_back({identity(root), 0, MOVE_NONE});
    seen.emplace(vertices[0].id, 0);
    for (std::size_t i = 0; i < vertices.size(); ++i) {
        // Fresh FEN avoids path-history storage, counter overflow, and any
        // influence of prior game history on movement-only exploration.
        Position pos;
        std::string error;
        if (!pos.set(vertices[i].id + " 0 1", &error))
            throw std::logic_error("reachability position: " + error);
        MoveList moves;
        generate_moves(pos, moves);
        if (moves.empty() && pos.in_check()) {
            result.result = MateReachability::MateFound;
            for (std::size_t j = i; j != 0; j = vertices[j].parent)
                result.witness.push_back(vertices[j].move);
            std::reverse(result.witness.begin(), result.witness.end());
            result.positions = vertices.size();
            return result;
        }
        for (const ExtMove& em : moves) {
            pos.make_move(em.move);
            std::string next = identity(pos);
            pos.unmake_move(em.move);
            if (seen.find(next) != seen.end()) continue;
            if (vertices.size() == maxPositions) {
                result.positions = vertices.size();
                return result;
            }
            const std::size_t n = vertices.size();
            seen.emplace(next, n);
            vertices.push_back({std::move(next), i, em.move});
        }
    }
    result.positions = vertices.size();
    result.result = MateReachability::NoMate;
    return result;
}
}
