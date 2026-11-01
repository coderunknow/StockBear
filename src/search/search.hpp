#pragma once
#include "chess/position.hpp"
#include "search/timeman.hpp"
#include "search/transposition_table.hpp"
#include <array>
#include <atomic>
#include <cstdint>
#include <functional>
#include <vector>

namespace stockbear {

// Static exchange evaluation of `move` on `pos`, in centipawns from the moving
// side's point of view (positive means the exchange wins material). Considers
// every recapture on the target square with least-valuable-attacker-first
// ordering and folds the sequence negamax-style.
int static_exchange_evaluation(const Position& pos, Move move);

// One principal variation of a search. `multiPv == 1` produces exactly one.
struct PvLine {
    Move move = MOVE_NONE;
    int score = 0;
    std::vector<Move> pv;
};

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
    std::vector<Move> pv;           // best line (same as lines.front().pv)
    std::vector<PvLine> lines;      // up to limits.multiPv entries, best first
};
using SearchInfo = std::function<void(const SearchResult&)>;

// Selectable search features. The defaults are the shipped configuration; the
// benchmark CLI and the UCI options can switch individual techniques off so
// that every addition can be ablated on a fixed suite instead of being
// accepted on faith.
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
    // dev3 ordering features. All default off: measured against the dev2 search
    // they are neutral to slightly negative in playing strength (+1.3 Elo
    // [-17.9, +20.5] with everything on, -16.2 [-33.0, +0.5] for the
    // history-malus/LMR subset, 571-600 decided paired games each) and they cost
    // about 2 % more nodes and 8 % more time at a fixed depth. They ship as
    // switches so the measurements can be repeated, not as a claimed gain; the
    // shipped search is therefore bit-identical to dev2's (bench signature
    // e06c4352681ae8eb at depth 6).
    bool counterMoves = false;         // reply table keyed by the previous move
    bool continuationHistory = false;  // history keyed by (prev piece/square, move)
    bool captureHistory = false;       // per-victim capture statistics
    bool historyMaluses = false;       // penalise quiets that did not cut off
    bool lmrHistory = false;           // history-dependent reduction adjustment
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
    static int see(const Position& pos, Move move) {
        return static_exchange_evaluation(pos, move);
    }

private:
    bool visit(int ply);
    int negamax(Position& pos, int depth, int alpha, int beta, int ply,
                bool pvNode, int extensions, bool allowNull);
    int quiescence(Position& pos, int alpha, int beta, int ply);
    int search_root(Position& pos, int depth, int alpha, int beta, int pvIndex);
    void score_moves(const Position& pos, MoveList& moves, Move hashMove, int ply);
    int next_move(MoveList& moves, int index);
    void update_pv(int ply, Move move);
    bool quiet(const Position& pos, Move move) const;
    bool gives_check(Position& pos, Move move);
    Move previous_move(int ply) const { return ply > 0 ? moveStack_[ply - 1] : MOVE_NONE; }
    void update_quiet_stats(const Position& pos, Move move, int depth, int ply, int bonus);
    void update_capture_stats(const Position& pos, Move move, int depth);
    void penalise_quiets(const Position& pos, const Move* moves, int count, int depth, int ply);
    void build_lines(SearchResult& result, int requested) const;

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
    // Reply table: the move that most often refuted `previous`. Indexed by the
    // previous move's piece and destination square.
    Move counterMoves_[PieceNB][SQ_NB] = {};
    // Continuation history: how good `move` has been after a given previous
    // move. Kept for one ply of context, which is the variant that pays for
    // itself without a large table.
    int continuation_[PieceTypeNB][SQ_NB][PieceTypeNB][SQ_NB] = {};
    int captureHistory_[PieceTypeNB][SQ_NB][PieceTypeNB] = {};
    // The moves played along the current line, so ordering can see the previous
    // move without threading an extra parameter through every call.
    Move moveStack_[MAX_PLY + 2] = {};
    std::vector<std::vector<Move>> pvLines_;

    struct RootMove {
        Move move = MOVE_NONE;
        int score = -VALUE_INFINITE;
    };
    std::vector<RootMove> rootMoves_;
};
}
