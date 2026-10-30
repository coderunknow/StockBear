#pragma once
#include "chess/position.hpp"
#include "search/timeman.hpp"
#include "search/transposition_table.hpp"
#include <atomic>
#include <cstdint>
#include <functional>
#include <vector>

namespace stockbear {
struct SearchResult {
    Move bestMove = MOVE_NONE;
    int score = 0;
    int depth = 0;
    int selectiveDepth = 0;
    std::uint64_t nodes = 0;
    std::int64_t timeMs = 0;
    std::int64_t timeUs = 0;
    int hashfull = 0;
    bool interrupted = false;
    std::vector<Move> pv;
};
using SearchInfo = std::function<void(const SearchResult&)>;

// One instance per search. Search is single-threaded; asynchronous UCI control
// uses a separate controller thread and an atomic stop flag.
class Search {
public:
    explicit Search(TranspositionTable& table) : tt_(table) {}
    SearchResult run(Position root, const SearchLimits& limits,
                     std::atomic<bool>& stop, const SearchInfo& onInfo = {});
private:
    bool visit(int ply);
    int negamax(Position& pos, int depth, int alpha, int beta, int ply,
                bool pvNode, int extensions);
    int quiescence(Position& pos, int alpha, int beta, int ply);
    void order_moves(const Position& pos, MoveList& moves, Move hashMove, int ply);
    void update_pv(int ply, Move move);
    bool quiet(const Position& pos, Move move) const;

    TranspositionTable& tt_;
    SearchLimits limits_{};
    TimeManager timer_;
    std::atomic<bool>* stop_ = nullptr;
    bool aborted_ = false;
    std::uint64_t nodes_ = 0;
    int selDepth_ = 0;
    Key rootContextSalt_ = 0;
    Move pv_[MAX_PLY][MAX_PLY] = {};
    int pvLength_[MAX_PLY] = {};
    Move killers_[MAX_PLY][2] = {};
    int history_[ColorNB][SQ_NB][SQ_NB] = {};
};
}
