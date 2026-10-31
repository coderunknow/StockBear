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

// Selectable search features. The defaults are the shipped configuration; the
// benchmark CLI can switch individual techniques off so that every addition can
// be ablated on a fixed suite instead of being accepted on faith.
struct SearchParams {
    bool aspiration = true;
    int aspirationInitial = 16;
    int aspirationWiden = 32;
    bool nullMove = true;
    bool lmr = true;
    bool reverseFutility = true;
    bool futility = true;
    bool seePruning = true;
    bool checkExtension = true;
    bool counterMoves = true;   // reserved: counter-move ordering is not enabled
};

// One instance per search. Search is single-threaded; asynchronous UCI control
// uses a separate controller thread and an atomic stop flag.
class Search {
public:
    explicit Search(TranspositionTable& table, const SearchParams& params = {})
        : tt_(table), params_(params) {}

    SearchResult run(Position root, const SearchLimits& limits,
                     std::atomic<bool>& stop, const SearchInfo& onInfo = {});

    // Static exchange evaluation of a legal move, in centipawns, from the point
    // of view of the side to move. Exposed for tests.
    static int see(const Position& pos, Move move);

private:
    bool visit(int ply);
    int negamax(Position& pos, int depth, int alpha, int beta, int ply,
                bool pvNode, int extensions, bool allowNull);
    int quiescence(Position& pos, int alpha, int beta, int ply);
    int search_root(Position& pos, int depth, int alpha, int beta);
    void score_moves(const Position& pos, MoveList& moves, Move hashMove, int ply);
    int next_move(MoveList& moves, int index);
    void update_pv(int ply, Move move);
    bool quiet(const Position& pos, Move move) const;
    bool gives_check(Position& pos, Move move);
    void update_quiet_stats(const Position& pos, Move move, int depth, int ply);

    TranspositionTable& tt_;
    SearchParams params_;
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
    struct RootMove {
        Move move = MOVE_NONE;
        int score = -VALUE_INFINITE;
    };
    std::vector<RootMove> rootMoves_;
};
}
