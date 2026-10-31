#pragma once
#include "chess/position.hpp"
#include <cstddef>
#include <vector>

namespace stockbear {
// Research tool, NOT FIDE adjudication: checks reachability under movement
// rules only, ignoring all clocks, repetition and draw termination. A completed
// no-mate traversal proves a dead position under those stronger assumptions;
// a mate witness may not be playable under actual automatic-draw rules.
enum class MateReachability { NoMate, MateFound, Unknown };
struct ReachabilityResult {
    MateReachability result = MateReachability::Unknown;
    std::size_t positions = 0;
    std::vector<Move> witness;
};
// Explore at most maxPositions distinct exact position identities. The memory
// and work budget is explicit; exhaustion returns Unknown, never NoMate.
ReachabilityResult movement_mate_reachability(const Position& root, std::size_t maxPositions);
}
