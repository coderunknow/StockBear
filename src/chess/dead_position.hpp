// ---------------------------------------------------------------------------
// dead_position.hpp - FIDE Laws of Chess Article 5.2.2 ("dead position").
//
// Article 5.2.2: "The game is drawn when a position has arisen in which
// neither player can checkmate the opponent's king with any series of legal
// moves. The game is said to end in a 'dead position'."
//
// Formalisation used here (and by the published helpmate literature):
//
//   mate_reachable(P)  <=>  there exists a finite sequence of legal moves
//                           starting at P that ends in a position where the
//                           side to move is checkmated
//   dead(P)            <=>  mate_reachable(P) is false
//
// Consequences that the implementation relies on:
//   * The property is a property of the *position* (placement, side to move,
//     castling rights, en-passant right), not of the game history. Halfmove
//     and fullmove counters cannot influence it: Article 5.2.2 quantifies over
//     series of legal moves without a move-count limit, so the fifty-move and
//     seventy-five-move rules are not part of the definition.
//   * Legal moves are not reversible (captures, pawn pushes and castling cannot
//     be undone), but they still give a closure property: any legal continuation
//     from a successor B of A can be prefixed with the move A -> B, so
//     mate_reachable(B) implies mate_reachable(A), and therefore dead(A) implies
//     dead(B). Dead positions are a "closed" set under legal moves.
//   * Deciding mate_reachable is PSPACE-complete (arXiv:2010.09271), so no
//     polynomial-time complete procedure exists. The procedure implemented
//     here is exact: it either finds a helpmate witness (=> Alive), or proves
//     that the complete reachable state component contains no checkmate
//     (=> Dead). Because the component can be astronomically large, the search
//     is bounded; hitting a bound yields Unknown, never Dead.
// ---------------------------------------------------------------------------
#pragma once

#include "chess/position.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace stockbear {

enum class DeadStatus {
    Alive,   // a legal continuation reaching checkmate was found (witness)
    Dead,    // the complete reachable component was enumerated: no mate exists
    Unknown  // resource limits were reached before either could be concluded
};

const char* to_string(DeadStatus status);

struct DeadLimits {
    // Work allowed for the fast "short helpmate" witness pass, in visited
    // positions (each visited position costs one legal move generation).
    std::uint64_t witnessNodes = 150000;
    // Work allowed for the exhaustive reachable-component enumeration.
    std::uint64_t componentStates = 3000000;
    // Maximum witness length (plies) attempted by the fast pass.
    int witnessMaxDepth = 12;
    // Hard cap on the enumeration path depth. 0 selects an automatic cap
    // derived from componentStates (a simple path never repeats a state).
    int componentMaxDepth = 0;
    // Set to false to skip the exhaustive pass (used for low-latency callers
    // that must never block, e.g. the UCI root check).
    bool allowExhaustive = true;
};

struct DeadResult {
    DeadStatus status = DeadStatus::Unknown;
    // A legal move sequence from the analysed position ending in checkmate,
    // present whenever status == Alive and a witness was constructed.
    std::vector<Move> witness;
    std::uint64_t visited = 0;    // positions expanded by the witness pass
    // Distinct states enumerated by the component pass (each state is inserted
    // into the visited set once, so this is the size of the reachable
    // component). Zero for the static-proof and terminal verdicts.
    std::uint64_t states = 0;
    // Positions expanded by the component pass, i.e. legal moves applied plus
    // the root. This is what the componentStates budget limits, so it is larger
    // than `states` whenever a reachable state is entered by several moves.
    std::uint64_t expanded = 0;
    bool exhaustiveComplete = false;
    bool depthLimited = false;    // the enumeration hit componentMaxDepth
    std::string reason;           // human readable explanation for the verdict
};

// Decides Article 5.2.2 for the given position.
//
// Preconditions: the position must be legal in the sense of FEN validation.
// If the side to move has no legal move (checkmate or stalemate) the position
// is already terminal under Articles 5.1.1 / 5.2.1 and the result is Alive
// with reason "terminal"; callers must apply those articles first.
DeadResult analyze_dead_position(const Position& pos, const DeadLimits& limits = {});

// True only when Article 5.2.2 is proved for this position.
bool is_dead_position(const Position& pos, const DeadLimits& limits = {});

// Budgets for latency-sensitive callers such as Position::draw_status() and
// the UCI root announcement. Small enough to stay in the sub-100 ms range on
// ordinary hardware, still proves the overwhelmingly common dead positions
// (bare kings, single minor, locked pawn structures with few mobile pieces).
DeadLimits fast_dead_limits();

} // namespace stockbear
