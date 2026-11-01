#pragma once
#include "chess/position.hpp"
#include "search/search.hpp"
#include <atomic>
#include <iosfwd>
#include <mutex>
#include <string>
#include <thread>

namespace stockbear {
class UciEngine {
public:
    UciEngine(std::istream& input, std::ostream& output);
    ~UciEngine();
    void loop();
private:
    void emit(const std::string& line);
    void stop_and_join();
    void handle_position(const std::string& arguments);
    void handle_go(const std::string& arguments);
    void handle_setoption(const std::string& arguments);
    std::istream& input_;
    std::ostream& output_;
    std::mutex outputMutex_;
    Position position_;
    TranspositionTable table_{16};
    std::atomic<bool> stop_{false};
    std::thread worker_;
    bool debug_ = false;
    // Number of principal variations to report (UCI MultiPV). 1 is the
    // default single-PV behaviour.
    int multiPv_ = 1;
    // Search-feature switches. They exist so ablations can be measured by
    // matches, not only by node counts, and every one defaults to the value
    // used by the engine (true) or by the released build.
    SearchParams params_{};
};
}
