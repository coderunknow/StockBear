#include "search/timeman.hpp"
#include <algorithm>

namespace stockbear {
void TimeManager::start(const SearchLimits& limits, Color side) {
    start_ = Clock::now();
    hardBudget_ = softBudget_ = -1;
    if (limits.infinite) return;
    if (limits.moveTimeMs >= 0) {
        // Reserve at most 5 ms, including for tiny requested times.
        hardBudget_ = std::max<std::int64_t>(1, limits.moveTimeMs - 5);
        softBudget_ = hardBudget_;
        return;
    }
    const std::int64_t remaining = side == White ? limits.whiteTimeMs : limits.blackTimeMs;
    if (remaining < 0) return;
    const std::int64_t increment = side == White ? limits.whiteIncMs : limits.blackIncMs;
    const int moves = limits.movesToGo > 0 ? limits.movesToGo : 30;
    const std::int64_t usable = std::max<std::int64_t>(1, remaining - 10);
    // Guard against integer overflow on pathological input. UCI parser bounds
    // all time fields to 1e12 ms; these operations stay well within int64_t.
    const std::int64_t target = std::max<std::int64_t>(1, remaining / moves + increment / 2);
    hardBudget_ = std::min(usable, std::max<std::int64_t>(1, target * 2));
    softBudget_ = std::min(hardBudget_, target);
}
bool TimeManager::hard_expired() const { return hardBudget_ >= 0 && elapsed_ms() >= hardBudget_; }
bool TimeManager::soft_expired() const { return softBudget_ >= 0 && elapsed_ms() >= softBudget_; }
std::int64_t TimeManager::elapsed_ms() const { return elapsed_us() / 1000; }
std::int64_t TimeManager::elapsed_us() const {
    return std::chrono::duration_cast<std::chrono::microseconds>(Clock::now() - start_).count();
}
}
