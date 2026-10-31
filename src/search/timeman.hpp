#pragma once
#include "utilities/types.hpp"
#include <chrono>
#include <cstdint>

namespace stockbear {
struct SearchLimits {
    int depth = 0;                   // 0 = no explicit depth limit
    bool hasNodes = false;
    std::uint64_t nodes = 0;
    std::int64_t moveTimeMs = -1;    // -1 = unspecified
    std::int64_t whiteTimeMs = -1, blackTimeMs = -1;
    std::int64_t whiteIncMs = 0, blackIncMs = 0;
    int movesToGo = 0;
    bool infinite = false;
};

// Two budgets are derived from the clock:
//   * `soft` ends the current iteration boundary early (start no new iteration),
//   * `hard` aborts the running iteration before the clock is lost.
// An explicit movetime maps both budgets, and a fixed node/depth limit always
// stays in force on top of them. The manager also keeps a small reserve for
// process scheduling, protocol output and the opponent's reply.
class TimeManager {
public:
    void start(const SearchLimits& limits, Color side);
    bool hard_expired() const;
    bool soft_expired() const;
    std::int64_t elapsed_ms() const;
    std::int64_t elapsed_us() const;
    std::int64_t hard_budget_ms() const { return hardBudget_; }
    std::int64_t soft_budget_ms() const { return softBudget_; }
    // True when the engine is running on an increment-based clock, which allows
    // slightly deeper iterations to be started once the previous one was quick.
    bool has_clock() const { return hasClock_; }
    // Fraction of the soft budget already used, in per mille.
    int soft_usage_permille() const;

private:
    using Clock = std::chrono::steady_clock;
    Clock::time_point start_;
    std::int64_t hardBudget_ = -1;
    std::int64_t softBudget_ = -1;
    bool hasClock_ = false;
};
}
