// Iterative-deepening negamax with alpha-beta, PVS, quiescence, a transposition
// table and conservative check extensions. No null-move or speculative pruning.
#include "search/search.hpp"
#include "evaluation/evaluation.hpp"
#include <algorithm>
#include <chrono>
#include <thread>

namespace stockbear {
namespace {
constexpr int MaxCheckExtensions = 2;
constexpr int CheckInterval = 64;
}

bool Search::visit(int ply) {
    if (stop_->load(std::memory_order_relaxed) ||
        (limits_.hasNodes && nodes_ >= limits_.nodes) ||
        ((nodes_ % CheckInterval) == 0 && timer_.hard_expired())) {
        aborted_ = true;
        return false;
    }
    ++nodes_;
    selDepth_ = std::max(selDepth_, ply);
    return true;
}

bool Search::quiet(const Position& pos, Move move) const {
    return move_type(move) != PromotionMove && move_type(move) != EnPassantMove &&
           pos.empty(move_to(move));
}

void Search::order_moves(const Position& pos, MoveList& moves, Move hashMove, int ply) {
    for (int i = 0; i < moves.size(); ++i) {
        const Move m = moves[i].move;
        int score = 0;
        if (m == hashMove) score = 2000000;
        else if (!quiet(pos, m)) {
            Piece victim = move_type(m) == EnPassantMove ? make_piece(~pos.side_to_move(), Pawn)
                                                        : pos.piece_on(move_to(m));
            Piece attacker = pos.piece_on(move_from(m));
            const int victimValue = victim == NoPiece ? 0 : PieceValueMg[type_of(victim)];
            const int attackerValue = PieceValueMg[type_of(attacker)];
            score = 1000000 + 16 * victimValue - attackerValue;
            if (move_type(m) == PromotionMove) score += PieceValueMg[promotion_type(m)];
        } else if (m == killers_[ply][0]) score = 900000;
        else if (m == killers_[ply][1]) score = 899000;
        else score = history_[pos.side_to_move()][move_from(m)][move_to(m)];
        moves[i].score = score;
    }
    // Stable ties preserve generator order and reproducibility.
    for (int i = 1; i < moves.size(); ++i) {
        ExtMove item = moves[i];
        int j = i;
        while (j > 0 && moves[j - 1].score < item.score) {
            moves[j] = moves[j - 1]; --j;
        }
        moves[j] = item;
    }
}

void Search::update_pv(int ply, Move move) {
    pv_[ply][0] = move;
    const int childLength = ply + 1 < MAX_PLY ? pvLength_[ply + 1] : 0;
    const int count = std::min(childLength, MAX_PLY - ply - 1);
    for (int i = 0; i < count; ++i) pv_[ply][i + 1] = pv_[ply + 1][i];
    pvLength_[ply] = count + 1;
}

int Search::quiescence(Position& pos, int alpha, int beta, int ply) {
    if (!visit(ply)) return 0;
    pvLength_[ply] = 0;
    if (ply >= MAX_PLY - 1) return evaluate(pos);
    if (pos.is_search_draw(ply)) return VALUE_DRAW;

    const bool check = pos.in_check();
    MoveList moves;
    generate_moves(pos, moves, check ? GenType::All : GenType::QSearch);
    if (moves.empty()) {
        if (check) return -VALUE_MATE + ply;
        // In a quiet position without captures there may be no legal moves at
        // all. Detect stalemate before returning the static evaluation.
        if (!pos.has_legal_moves()) return VALUE_DRAW;
        return evaluate(pos);
    }

    int best = -VALUE_INFINITE;
    if (!check) {
        best = evaluate(pos);
        if (best >= beta) return best;
        alpha = std::max(alpha, best);
    }
    order_moves(pos, moves, MOVE_NONE, ply);
    for (const ExtMove& em : moves) {
        pos.make_move(em.move);
        const int value = -quiescence(pos, -beta, -alpha, ply + 1);
        pos.unmake_move(em.move);
        if (aborted_) return 0;
        if (value > best) best = value;
        if (value > alpha) {
            alpha = value;
            update_pv(ply, em.move);
            if (alpha >= beta) break;
        }
    }
    return best;
}

int Search::negamax(Position& pos, int depth, int alpha, int beta, int ply,
                    bool pvNode, int extensions) {
    if (depth <= 0) return quiescence(pos, alpha, beta, ply);
    if (!visit(ply)) return 0;
    pvLength_[ply] = 0;
    if (ply >= MAX_PLY - 1) return evaluate(pos);
    if (pos.is_search_draw(ply)) return VALUE_DRAW;

    const bool check = pos.in_check();
    if (check && depth <= 2 && extensions < MaxCheckExtensions) {
        ++depth;
        ++extensions;
    }
    const int originalAlpha = alpha;
    const TTEntry* entry = tt_.probe(pos.key(), pos.rule50(), pos.history_context() ^ rootContextSalt_, extensions);
    const Move hashMove = entry ? entry->move : MOVE_NONE;
    if (entry && !pvNode && entry->depth >= depth) {
        const int value = TranspositionTable::value_from_table(entry->value, ply);
        if (entry->bound == Bound::Exact ||
            (entry->bound == Bound::Lower && value >= beta) ||
            (entry->bound == Bound::Upper && value <= alpha)) return value;
    }

    MoveList moves;
    generate_moves(pos, moves, GenType::All);
    if (moves.empty()) return check ? -VALUE_MATE + ply : VALUE_DRAW;
    order_moves(pos, moves, hashMove, ply);
    int best = -VALUE_INFINITE;
    Move bestMove = MOVE_NONE;
    int moveIndex = 0;
    for (const ExtMove& em : moves) {
        const Move m = em.move;
        const bool isQuiet = quiet(pos, m);
        pos.make_move(m);
        int value;
        if (moveIndex == 0) {
            value = -negamax(pos, depth - 1, -beta, -alpha, ply + 1, pvNode, extensions);
        } else {
            // Principal variation search: first try a zero window, then
            // re-search any improving candidate inside the full window.
            value = -negamax(pos, depth - 1, -alpha - 1, -alpha, ply + 1, false, extensions);
            if (!aborted_ && value > alpha && value < beta)
                value = -negamax(pos, depth - 1, -beta, -alpha, ply + 1, pvNode, extensions);
        }
        pos.unmake_move(m);
        if (aborted_) return 0;
        ++moveIndex;
        if (value > best) { best = value; bestMove = m; }
        if (value > alpha) {
            alpha = value;
            update_pv(ply, m);
        }
        if (alpha >= beta) {
            if (isQuiet) {
                if (killers_[ply][0] != m) {
                    killers_[ply][1] = killers_[ply][0];
                    killers_[ply][0] = m;
                }
                int& h = history_[pos.side_to_move()][move_from(m)][move_to(m)];
                h = std::min(100000, h + depth * depth);
            }
            break;
        }
    }
    const Bound bound = best >= beta ? Bound::Lower
                      : best <= originalAlpha ? Bound::Upper : Bound::Exact;
    tt_.store(pos.key(), pos.rule50(), pos.history_context() ^ rootContextSalt_, extensions,
              bestMove, best, depth, bound, ply);
    return best;
}

SearchResult Search::run(Position root, const SearchLimits& limits,
                         std::atomic<bool>& stop, const SearchInfo& onInfo) {
    limits_ = limits;
    stop_ = &stop;
    aborted_ = false;
    nodes_ = 0;
    selDepth_ = 0;
    std::fill(std::begin(pvLength_), std::end(pvLength_), 0);
    // A Search object may be reused by benchmark code.
    for (auto& row : killers_) std::fill(std::begin(row), std::end(row), MOVE_NONE);
    for (auto& color : history_) for (auto& row : color) std::fill(std::begin(row), std::end(row), 0);
    tt_.new_search();
    // A twofold cycle inside this search is different from an occurrence in
    // prior game history. Isolate table bounds by root/history boundary as
    // well as the per-node reversible-history signature.
    rootContextSalt_ = Zobrist::context_seed(root.history_context() ^ root.key() ^
                                              (root.rule50() * 0x9E3779B97F4A7C15ULL));
    timer_.start(limits, root.side_to_move());
    SearchResult result;
    MoveList rootMoves;
    generate_moves(root, rootMoves, GenType::All);
    if (rootMoves.empty()) {
        result.score = root.in_check() ? -VALUE_MATE : VALUE_DRAW;
        if (limits.infinite && !limits.hasNodes && limits.depth == 0) {
            while (!stop.load(std::memory_order_relaxed))
                std::this_thread::sleep_for(std::chrono::milliseconds(2));
            result.interrupted = true;
        }
        result.timeUs = timer_.elapsed_us();
        result.timeMs = result.timeUs / 1000;
        return result; // UCI emits bestmove 0000 for a terminal position
    }
    result.bestMove = rootMoves[0].move; // valid even if stopped before depth 1
    result.pv = {result.bestMove};
    // A recognized draw has no game tree to search. Report depth 0 rather
    // than claiming arbitrarily deep completed iterations.
    if (root.is_search_draw(0)) {
        result.score = VALUE_DRAW;
        result.timeUs = timer_.elapsed_us();
        result.timeMs = result.timeUs / 1000;
        if (onInfo) onInfo(result);
        if (limits.infinite && !limits.hasNodes && limits.depth == 0) {
            while (!stop.load(std::memory_order_relaxed))
                std::this_thread::sleep_for(std::chrono::milliseconds(2));
            result.interrupted = true;
            result.timeUs = timer_.elapsed_us();
            result.timeMs = result.timeUs / 1000;
        }
        return result;
    }

    const int maxDepth = limits.depth > 0 ? std::min(limits.depth, MAX_PLY - 2) : MAX_PLY - 2;
    for (int depth = 1; depth <= maxDepth; ++depth) {
        const int value = negamax(root, depth, -VALUE_INFINITE, VALUE_INFINITE, 0, true, 0);
        if (aborted_) break;
        result.score = value;
        result.depth = depth;
        result.selectiveDepth = selDepth_;
        result.nodes = nodes_;
        result.timeUs = timer_.elapsed_us();
        result.timeMs = result.timeUs / 1000;
        result.hashfull = tt_.hashfull();
        result.pv.clear();
        for (int i = 0; i < pvLength_[0]; ++i) result.pv.push_back(pv_[0][i]);
        if (!result.pv.empty()) result.bestMove = result.pv.front();
        else result.pv.push_back(result.bestMove); // e.g. a draw at root
        if (onInfo) onInfo(result);
        if (timer_.soft_expired() && !limits.infinite) break;
        if (stop.load(std::memory_order_relaxed)) { aborted_ = true; break; }
    }
    // `go infinite` must not spontaneously return after a trivially drawn
    // position reaches the maximum representable depth. Wait for stop.
    if (limits.infinite && !limits.hasNodes && limits.depth == 0 && !aborted_) {
        while (!stop.load(std::memory_order_relaxed))
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
        aborted_ = true;
    }
    result.nodes = nodes_;
    result.timeUs = timer_.elapsed_us();
    result.timeMs = result.timeUs / 1000;
    result.hashfull = tt_.hashfull();
    result.interrupted = aborted_;
    return result;
}
}
