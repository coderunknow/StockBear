#pragma once
#include "utilities/types.hpp"
#include <chrono>
#include <cstdint>

namespace stockbear {
struct SearchLimits {
    int depth = 0;                   // 0 = no explicit depth limit
    bool hasNodes = false;
    std::uint64_t nodes = 0;
    std::int64_t moveTimeMs = -1;   // -1 = unspecified
    std::int64_t whiteTimeMs = -1, blackTimeMs = -1;
    std::int64_t whiteIncMs = 0, blackIncMs = 0;
    int movesToGo = 0;
    bool infinite = false;
};

// Time budgets are conservative on small clocks, with a modest overhead
// allowance for communication. Explicit node/depth limits remain active too.
class TimeManager {
public:
    void start(const SearchLimits& limits, Color side);
    bool hard_expired() const;
    bool soft_expired() const;
    std::int64_t elapsed_ms() const;
    std::int64_t elapsed_us() const;
    std::int64_t hard_budget_ms() const { return hardBudget_; }
private:
    using Clock = std::chrono::steady_clock;
    Clock::time_point start_;
    std::int64_t hardBudget_ = -1;
    std::int64_t softBudget_ = -1;
};
}
