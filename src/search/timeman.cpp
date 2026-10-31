#include "search/timeman.hpp"
#include <algorithm>

namespace stockbear {
namespace {
// Leave this much time unused so the bestmove line always reaches the GUI
// before the clock is flagged (protocol output, scheduling, process wake-up).
constexpr std::int64_t MoveOverheadMs = 10;
}

void TimeManager::start(const SearchLimits& limits, Color side) {
    start_ = Clock::now();
    hardBudget_ = softBudget_ = -1;
    hasClock_ = false;
    if (limits.infinite) return;

    if (limits.moveTimeMs >= 0) {
        // Honour an explicit movetime as closely as possible while still
        // reserving a little protocol overhead on very short requests.
        hardBudget_ = std::max<std::int64_t>(1, limits.moveTimeMs - std::min<std::int64_t>(5, MoveOverheadMs));
        softBudget_ = hardBudget_;
        return;
    }

    const std::int64_t remaining = side == White ? limits.whiteTimeMs : limits.blackTimeMs;
    if (remaining < 0) return; // no clock for this side: behave as infinite
    hasClock_ = true;

    const std::int64_t increment = std::max<std::int64_t>(0, side == White ? limits.whiteIncMs
                                                                            : limits.blackIncMs);
    // Without an explicit movestogo assume the game will last another 30 moves;
    // that avoids spending the whole clock on one middlegame position.
    const int moves = limits.movesToGo > 0 ? std::min(limits.movesToGo, 50) : 30;
    const std::int64_t usable = std::max<std::int64_t>(1, remaining - MoveOverheadMs);

    // Allocate the remaining time in roughly equal slices, keeping part of the
    // increment for later moves and never planning to use the whole clock.
    const std::int64_t slice = remaining / moves;
    const std::int64_t target = std::max<std::int64_t>(1, slice + increment * 3 / 4);
    softBudget_ = std::min(usable, target);
    hardBudget_ = std::min(usable, std::max<std::int64_t>(1, std::min(remaining / 3, target * 4)));
    // Never let the soft budget exceed the hard budget.
    softBudget_ = std::min(softBudget_, hardBudget_);
}

bool TimeManager::hard_expired() const { return hardBudget_ >= 0 && elapsed_ms() >= hardBudget_; }
bool TimeManager::soft_expired() const { return softBudget_ >= 0 && elapsed_ms() >= softBudget_; }
std::int64_t TimeManager::elapsed_ms() const { return elapsed_us() / 1000; }
std::int64_t TimeManager::elapsed_us() const {
    return std::chrono::duration_cast<std::chrono::microseconds>(Clock::now() - start_).count();
}
int TimeManager::soft_usage_permille() const {
    if (softBudget_ <= 0) return 0;
    return int(std::min<std::int64_t>(1000, elapsed_ms() * 1000 / softBudget_));
}
}
