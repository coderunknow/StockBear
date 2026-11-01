// Iterative-deepening negamax with alpha-beta/PVS, quiescence search,
// aspiration windows, null-move pruning, late move reductions, reverse
// futility pruning, static exchange evaluation, history/counter-move/continuation
// ordering and a context-checked transposition table.
//
// Every pruning decision is guarded so that it cannot change the value of a
// proven mate, and every aborted node propagates a zero that the caller
// discards: only fully completed iterations are reported to the GUI.
#include "search/search.hpp"
#include "evaluation/evaluation.hpp"

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <thread>

namespace stockbear {
namespace {

constexpr int MaxCheckExtensions = 3;
// Hard-timer polling interval. dev1 polled every 64 nodes; dev2 briefly widened
// it to 1024, which lets a `go movetime 1` search overrun its hard budget by up
// to a thousand nodes and risk a clock forfeit. The check is an atomic load plus
// a cached deadline comparison, so 64 is affordable.
constexpr int NodeCheckInterval = 64;
// Static exchange values. The king is deliberately enormous: a king may not
// legally recapture into a still-attacked square, and giving it 0 made SEE think
// it could, so a rook capture of a pawn defended only by the king (with an
// x-raying rook behind) came out as a loss of a rook instead of a won pawn.
constexpr int SeeValue[PieceTypeNB + 1] = {0, 100, 320, 335, 500, 975, 20000, 0};
// History values saturate here; ordering scores are far below the hash-move
// bucket, so saturation can never reorder a capture above a hash move.
constexpr int HistoryLimit = 60000;
// Most quiet moves remembered per node for the penalty pass. A node with more
// quiets than this still gets its cutoff rewarded; only the penalties are
// truncated, which is a quality trade-off, not a correctness one.
constexpr int MaxPenalisedQuiets = 24;

// Integer-only reduction schedule; keeps results bit-identical across
// platforms and compilers (a floating-point logarithm does not guarantee that).
inline int reduction_for(int depth, int moveCount) {
    int r = 1;
    if (depth >= 6) r += 1;
    if (moveCount >= 8) r += 1;
    if (moveCount >= 24) r += 1;
    if (depth >= 14) r += 1;
    return r;
}

inline bool has_non_pawn_material(const Position& pos) {
    const Color us = pos.side_to_move();
    return pos.pieces(us, Knight) || pos.pieces(us, Bishop) ||
           pos.pieces(us, Rook) || pos.pieces(us, Queen);
}

inline int gain_of(const Position& pos, Move move) {
    if (move_type(move) == EnPassantMove) return SeeValue[Pawn];
    const Piece victim = pos.piece_on(move_to(move));
    return victim == NoPiece ? 0 : SeeValue[type_of(victim)];
}

inline int clamp_history(int value) {
    return std::max(-HistoryLimit, std::min(HistoryLimit, value));
}
} // namespace

int static_exchange_evaluation(const Position& pos, Move move) {
    const Square from = move_from(move);
    const Square to = move_to(move);
    // gain[i] is the material balance for the side that makes the i-th capture
    // on `to`, counting from the side to move. gain[0] is the initial capture.
    int gain[32] = {};
    int d = 0;
    gain[0] = gain_of(pos, move);
    if (move_type(move) == PromotionMove)
        gain[0] += SeeValue[promotion_type(move)] - SeeValue[Pawn];

    Bitboard occ = pos.pieces() ^ square_bb(from);
    if (move_type(move) == EnPassantMove) occ ^= square_bb(Square(int(to) ^ 8));

    PieceType attacker = type_of(pos.piece_on(from));
    Color side = ~pos.side_to_move();
    while (d < 31) {
        const Bitboard attackers = pos.attackers_to(to, occ) & occ & pos.pieces(side);
        if (!attackers) break;
        // Least valuable attacker first.
        PieceType chosen = NoPieceType;
        Bitboard chosenBB = 0;
        for (PieceType pt : {Pawn, Knight, Bishop, Rook, Queen, King}) {
            const Bitboard candidates = attackers & pos.pieces(side, pt);
            if (candidates) { chosen = pt; chosenBB = candidates; break; }
        }
        if (chosen == NoPieceType) break;
        occ ^= square_bb(lsb_square(chosenBB));
        ++d;
        gain[d] = SeeValue[attacker] - gain[d - 1];
        attacker = chosen;
        side = ~side;
        // If neither side can profit, the exchange is settled; the last
        // computed value is still folded in below.
        if (std::max(-gain[d - 1], gain[d]) < 0) break;
    }
    // Negamax fold. It must start from the last filled entry (d), otherwise the
    // final recapture is ignored and a losing capture looks winning: a knight
    // taking a pawn defended by a pawn must return 100 - 320 = -220, not +100.
    for (; d > 0; --d) gain[d - 1] = -std::max(gain[d], -gain[d - 1]);
    return gain[0];
}

bool Search::quiet(const Position& pos, Move move) const {
    return move_type(move) != PromotionMove && move_type(move) != EnPassantMove &&
           pos.empty(move_to(move));
}

bool Search::gives_check(Position& pos, Move move) {
    pos.make_move(move);
    const bool check = pos.in_check();
    pos.unmake_move(move);
    return check;
}

bool Search::visit(int ply) {
    if (stop_->load(std::memory_order_relaxed) ||
        (limits_.hasNodes && nodes_ >= limits_.nodes) ||
        ((nodes_ & (NodeCheckInterval - 1)) == 0 && timer_.hard_expired())) {
        aborted_ = true;
        return false;
    }
    ++nodes_;
    selDepth_ = std::max(selDepth_, ply);
    return true;
}

void Search::score_moves(const Position& pos, MoveList& moves, Move hashMove, int ply) {
    const Color us = pos.side_to_move();
    const Move previous = previous_move(ply);
    // The piece that played the previous move is standing on its destination.
    const Piece previousPiece = is_ok(previous) ? pos.piece_on(move_to(previous)) : NoPiece;
    const PieceType previousType = previousPiece == NoPiece ? NoPieceType : type_of(previousPiece);
    for (int i = 0; i < moves.size(); ++i) {
        const Move m = moves[i].move;
        int score;
        if (m == hashMove) {
            score = 4000000;
        } else if (!quiet(pos, m)) {
            const int gain = gain_of(pos, m);
            const Piece attacker = pos.piece_on(move_from(m));
            // Ordering uses the exchange values, not the (now tunable) material
            // weights: a tuned pawn value must not silently change which
            // captures get a full SEE, and a capture ordering that depends on
            // the evaluation parameters would make ablations incomparable.
            const int attackerValue = attacker == NoPiece ? 0 : SeeValue[type_of(attacker)];
            // Static exchange evaluation is only needed where it can change the
            // verdict; a capture of a piece at least as valuable as the
            // capturing one is winning anyway.
            const int seeScore = (params_.seePruning && gain < attackerValue) ? see(pos, m) : gain;
            // Winning and equal captures first, losing captures after quiets.
            score = 2000000 + (seeScore >= 0 ? 1000000 : 0) + 32 * gain + seeScore;
            if (move_type(m) == PromotionMove)
                score += 900000 + SeeValue[promotion_type(m)];
            if (params_.captureHistory) {
                // A small, bounded tie-break between otherwise equal captures.
                const Piece victim = pos.piece_on(move_to(m));
                const int stat = captureHistory_[attacker == NoPiece ? NoPieceType : type_of(attacker)]
                                                 [move_to(m)]
                                                 [victim == NoPiece ? NoPieceType : type_of(victim)];
                score += std::max(-1024, std::min(1024, stat));
            }
        } else if (m == killers_[ply][0]) {
            score = 1500000;
        } else if (m == killers_[ply][1]) {
            score = 1490000;
        } else if (params_.counterMoves && previousPiece != NoPiece &&
                   m == counterMoves_[previousPiece][move_to(previous)]) {
            score = 1485000;
        } else {
            score = history_[us][move_from(m)][move_to(m)];
            if (params_.continuationHistory && previousType != NoPieceType) {
                const int cont = continuation_[previousType][move_to(previous)]
                                              [type_of(pos.piece_on(move_from(m)))]
                                              [move_to(m)];
                // Bounded and secondary: continuation history refines the
                // ordering among quiet moves without overriding the main table.
                score += std::max(-8000, std::min(8000, cont / 4));
            }
        }
        moves[i].score = score;
    }
}

int Search::next_move(MoveList& moves, int index) {
    int best = index;
    for (int i = index + 1; i < moves.size(); ++i)
        if (moves[i].score > moves[best].score) best = i;
    if (best != index) std::swap(moves[best], moves[index]);
    return index;
}

void Search::update_pv(int ply, Move move) {
    pv_[ply][0] = move;
    const int childLength = ply + 1 < MAX_PLY ? pvLength_[ply + 1] : 0;
    const int count = std::min(childLength, MAX_PLY - ply - 1);
    for (int i = 0; i < count; ++i) pv_[ply][i + 1] = pv_[ply + 1][i];
    pvLength_[ply] = count + 1;
}

void Search::update_quiet_stats(const Position& pos, Move move, int depth, int ply, int bonus) {
    const Color us = pos.side_to_move();
    const Move previous = previous_move(ply);
    const Piece previousPiece = is_ok(previous) ? pos.piece_on(move_to(previous)) : NoPiece;
    (void)depth;
    if (bonus > 0) {
        // Killer moves: two quiet moves per ply that recently caused a cutoff.
        if (killers_[ply][0] != move) {
            killers_[ply][1] = killers_[ply][0];
            killers_[ply][0] = move;
        }
        // Counter-move table: remember what refuted the move that led here.
        if (params_.counterMoves && previousPiece != NoPiece)
            counterMoves_[previousPiece][move_to(previous)] = move;
    }
    int& entry = history_[us][move_from(move)][move_to(move)];
    entry = clamp_history(entry + bonus);
    // Keep the table from saturating at the bound: halve everything when a
    // positive update reaches the limit, as dev2 did.
    if (entry >= HistoryLimit) {
        for (auto& color : history_)
            for (auto& from : color)
                for (int& value : from) value /= 2;
    }
    if (params_.continuationHistory && previousPiece != NoPiece) {
        int& cont = continuation_[type_of(previousPiece)][move_to(previous)]
                                  [type_of(pos.piece_on(move_from(move)))]
                                  [move_to(move)];
        cont = clamp_history(cont + bonus);
    }
}

void Search::update_capture_stats(const Position& pos, Move move, int depth) {
    if (!params_.captureHistory) return;
    const Piece attacker = pos.piece_on(move_from(move));
    const Piece victim = pos.piece_on(move_to(move));
    const PieceType at = attacker == NoPiece ? NoPieceType : type_of(attacker);
    const PieceType vt = victim == NoPiece ? NoPieceType : type_of(victim);
    int& entry = captureHistory_[at][move_to(move)][vt];
    entry = std::max(-HistoryLimit, std::min(HistoryLimit, entry + depth * depth));
}

void Search::penalise_quiets(const Position& pos, const Move* moves, int count, int depth, int ply) {
    for (int i = 0; i < count; ++i) update_quiet_stats(pos, moves[i], depth, ply, -depth * depth);
}

int Search::quiescence(Position& pos, int alpha, int beta, int ply) {
    if (!visit(ply)) return 0;
    pvLength_[ply] = 0;
    if (ply >= MAX_PLY - 2) return evaluate(pos);
    if (pos.is_search_draw(ply)) return VALUE_DRAW;

    const bool inCheck = pos.in_check();
    MoveList moves;
    int best;
    if (inCheck) {
        generate_moves(pos, moves, GenType::All);
        if (moves.empty()) return -VALUE_MATE + ply;
        best = -VALUE_INFINITE;
    } else {
        best = evaluate(pos);
        if (best >= beta) return best;
        alpha = std::max(alpha, best);
        // Delta pruning: if no single capture can lift the score to alpha, the
        // static evaluation is already the best this node can offer.
        if (best + SeeValue[Queen] + 200 <= alpha) return best;
        generate_moves(pos, moves, GenType::QSearch);
        if (moves.empty()) {
            // No capture and no promotion: only stalemate can change the score.
            if (!pos.has_legal_moves()) return VALUE_DRAW;
            return best;
        }
    }

    score_moves(pos, moves, MOVE_NONE, ply);
    for (int i = 0; i < moves.size(); ++i) {
        next_move(moves, i);
        const Move m = moves[i].move;
        if (!inCheck && params_.seePruning && see(pos, m) < 0) continue;
        pos.make_move(m);
        moveStack_[ply] = m;
        const int value = -quiescence(pos, -beta, -alpha, ply + 1);
        pos.unmake_move(m);
        if (aborted_) return 0;
        if (value > best) {
            best = value;
            if (value > alpha) {
                alpha = value;
                update_pv(ply, m);
                if (alpha >= beta) {
                    if (!inCheck) update_capture_stats(pos, m, 1);
                    break;
                }
            }
        }
    }
    return best;
}

int Search::negamax(Position& pos, int depth, int alpha, int beta, int ply,
                    bool pvNode, int extensions, bool allowNull) {
    if (depth <= 0) return quiescence(pos, alpha, beta, ply);
    if (!visit(ply)) return 0;
    pvLength_[ply] = 0;
    if (ply >= MAX_PLY - 2) return evaluate(pos);
    if (pos.is_search_draw(ply)) return VALUE_DRAW;

    // Mate distance pruning: a mate found closer to the root dominates.
    alpha = std::max(alpha, -VALUE_MATE + ply);
    beta = std::min(beta, VALUE_MATE - ply - 1);
    if (alpha >= beta) return alpha;

    const bool inCheck = pos.in_check();
    if (params_.checkExtension && inCheck && depth <= 3 && extensions < MaxCheckExtensions) {
        ++depth;
        ++extensions;
    }

    const Key context = pos.history_context() ^ rootContextSalt_;
    const TTEntry* entry = tt_.probe(pos.key(), pos.rule50(), context, extensions);
    const Move hashMove = entry != nullptr ? entry->move : MOVE_NONE;
    if (entry != nullptr && !pvNode && entry->depth >= depth) {
        const int value = TranspositionTable::value_from_table(entry->value, ply);
        if (entry->bound == Bound::Exact ||
            (entry->bound == Bound::Lower && value >= beta) ||
            (entry->bound == Bound::Upper && value <= alpha))
            return value;
    }

    const int staticEval = evaluate(pos);
    const bool mateWindow = std::abs(beta) >= MATE_BOUND || std::abs(alpha) >= MATE_BOUND;

    // Reverse futility pruning: at shallow depth a large static margin over beta
    // is good enough, provided no mate score can be involved.
    if (params_.reverseFutility && !pvNode && !inCheck && !mateWindow && depth <= 6 &&
        staticEval - 85 * depth >= beta)
        return staticEval;

    // Null-move pruning. Disabled when the side to move has no non-pawn
    // material (zugzwang risk) and directly after another null move.
    if (params_.nullMove && allowNull && !pvNode && !inCheck && !mateWindow && depth >= 3 &&
        staticEval >= beta && has_non_pawn_material(pos)) {
        const int reduction = 3 + depth / 5;
        pos.make_null_move();
        const int value = -negamax(pos, depth - 1 - reduction, -beta, -beta + 1, ply + 1,
                                   false, extensions, false);
        pos.unmake_null_move();
        if (aborted_) return 0;
        if (value >= beta) return value >= MATE_BOUND ? beta : value;
    }

    MoveList moves;
    generate_moves(pos, moves, GenType::All);
    if (moves.empty()) return inCheck ? -VALUE_MATE + ply : VALUE_DRAW;

    score_moves(pos, moves, hashMove, ply);
    const int futilityBase = staticEval + 110 * depth;
    const int originalAlpha = alpha;
    int best = -VALUE_INFINITE;
    Move bestMove = MOVE_NONE;
    int moveCount = 0;
    // Quiet moves already searched at this node, for the history penalty when a
    // later move cuts off: the earlier quiets failed to produce the cutoff.
    Move triedQuiets[MaxPenalisedQuiets];
    int triedCount = 0;

    for (int i = 0; i < moves.size(); ++i) {
        next_move(moves, i);
        const Move m = moves[i].move;
        const bool isQuiet = quiet(pos, m);
        const bool isHash = (m == hashMove);

        // The checking test makes and unmakes the move, so it is only run when
        // a pruning or reduction decision actually depends on it.
        const bool futilityCandidate = isQuiet && !pvNode && !inCheck && !mateWindow &&
                                       moveCount > 0 && params_.futility && depth <= 3 &&
                                       futilityBase <= alpha;
        const bool lmrCandidate = isQuiet && !inCheck && !mateWindow && params_.lmr &&
                                  depth >= 3 && moveCount >= 3 && !isHash &&
                                  m != killers_[ply][0] && m != killers_[ply][1];
        bool check = inCheck;
        if (futilityCandidate || lmrCandidate) check = gives_check(pos, m);
        if (futilityCandidate && !check) continue;

        // Read the history value before making the move: the table is indexed
        // by the moving side, which `make_move` flips.
        const int quietHistory = isQuiet ? history_[pos.side_to_move()][move_from(m)][move_to(m)]
                                         : 0;
        pos.make_move(m);
        moveStack_[ply] = m;
        int value;
        if (moveCount == 0) {
            value = -negamax(pos, depth - 1, -beta, -alpha, ply + 1, pvNode, extensions, true);
        } else {
            int reduction = 0;
            if (lmrCandidate && !check) {
                reduction = std::min(reduction_for(depth, moveCount), depth - 2);
                if (params_.lmrHistory) {
                    // Good quiet moves are less reduced; poor ones more. The
                    // bound keeps the reduction inside [0, depth - 2] so the
                    // re-search below always has something to verify.
                    if (quietHistory > 800) reduction = std::max(0, reduction - 1);
                    else if (quietHistory < 0) reduction = std::min(reduction + 1, depth - 2);
                }
            }

            value = -negamax(pos, depth - 1 - reduction, -alpha - 1, -alpha, ply + 1,
                             false, extensions, true);
            if (!aborted_ && reduction > 0 && value > alpha)
                value = -negamax(pos, depth - 1, -alpha - 1, -alpha, ply + 1, false,
                                 extensions, true);
            if (!aborted_ && value > alpha && value < beta)
                value = -negamax(pos, depth - 1, -beta, -alpha, ply + 1, pvNode, extensions,
                                 true);
        }
        pos.unmake_move(m);
        if (aborted_) return 0;
        ++moveCount;

        if (value > best) {
            best = value;
            bestMove = m;
            if (value > alpha) {
                alpha = value;
                update_pv(ply, m);
            }
        }
        if (alpha >= beta) {
            if (isQuiet) {
                update_quiet_stats(pos, m, depth, ply, depth * depth);
                if (params_.historyMaluses && triedCount > 0)
                    penalise_quiets(pos, triedQuiets, triedCount, depth, ply);
            } else {
                update_capture_stats(pos, m, depth);
            }
            if (isQuiet) moves[i].score = -VALUE_INFINITE; // never reorder below killers
            break;
        }
        if (isQuiet && triedCount < MaxPenalisedQuiets) triedQuiets[triedCount++] = m;
    }

    const Bound stored = best >= beta ? Bound::Lower
                        : best <= originalAlpha ? Bound::Upper
                        : Bound::Exact;
    tt_.store(pos.key(), pos.rule50(), context, extensions, bestMove, best, depth, stored, ply);
    return best;
}

int Search::search_root(Position& pos, int depth, int alpha, int beta, int pvIndex) {
    int best = -VALUE_INFINITE;
    // The move that improved alpha in this pass, so the slot is reported with a
    // move that actually produced its score and PV.
    Move alphaMove = rootMoves_[std::size_t(pvIndex)].move;
    int alphaValue = -VALUE_INFINITE;
    for (std::size_t i = std::size_t(pvIndex); i < rootMoves_.size(); ++i) {
        // Selection sort over the root list so the previous best move is tried
        // first on the next iteration and the highest-scoring move of this
        // multi-PV slot heads the list.
        std::size_t pick = i;
        for (std::size_t j = i + 1; j < rootMoves_.size(); ++j)
            if (rootMoves_[j].score > rootMoves_[pick].score) pick = j;
        if (pick != i) std::swap(rootMoves_[i], rootMoves_[pick]);

        const Move m = rootMoves_[i].move;
        moveStack_[0] = m;
        pos.make_move(m);
        int value;
        if (i == std::size_t(pvIndex)) {
            value = -negamax(pos, depth - 1, -beta, -alpha, 1, true, 0, true);
        } else {
            // Only the move occupying this PV slot is searched with a full
            // window from the start; the rest are ranked with a null window and
            // re-searched only if they improve alpha.
            value = -negamax(pos, depth - 1, -alpha - 1, -alpha, 1, false, 0, true);
            if (!aborted_ && value > alpha && value < beta)
                value = -negamax(pos, depth - 1, -beta, -alpha, 1, true, 0, true);
        }
        pos.unmake_move(m);
        if (aborted_) return 0;

        rootMoves_[i].score = value;
        if (value > best) best = value;
        if (value > alpha) {
            alpha = value;
            alphaMove = m;
            alphaValue = value;
            update_pv(0, m);
        }
        if (alpha >= beta) break;
    }
    // Move the alpha-improving move into this slot so that the reported line
    // (move, score, PV) is internally consistent even when a later move beat
    // the one that started the pass.
    if (alphaValue != -VALUE_INFINITE) {
        for (std::size_t i = std::size_t(pvIndex); i < rootMoves_.size(); ++i) {
            if (rootMoves_[i].move == alphaMove) {
                std::swap(rootMoves_[i], rootMoves_[std::size_t(pvIndex)]);
                rootMoves_[std::size_t(pvIndex)].score = alphaValue;
                break;
            }
        }
    }
    return best;
}

void Search::build_lines(SearchResult& result, int requested) const {
    result.lines.clear();
    const int count = std::min<int>(std::max(1, requested), int(rootMoves_.size()));
    for (int i = 0; i < count; ++i) {
        PvLine line;
        line.move = rootMoves_[std::size_t(i)].move;
        line.score = rootMoves_[std::size_t(i)].score;
        if (std::size_t(i) < pvLines_.size() && !pvLines_[std::size_t(i)].empty())
            line.pv = pvLines_[std::size_t(i)];
        else
            line.pv = {line.move};
        result.lines.push_back(std::move(line));
    }
}

SearchResult Search::run(Position root, const SearchLimits& limits,
                         std::atomic<bool>& stop, const SearchInfo& onInfo) {
    limits_ = limits;
    stop_ = &stop;
    aborted_ = false;
    nodes_ = 0;
    selDepth_ = 0;
    std::fill(std::begin(pvLength_), std::end(pvLength_), 0);
    for (auto& row : killers_) std::fill(std::begin(row), std::end(row), MOVE_NONE);
    for (auto& color : history_)
        for (auto& row : color) std::fill(std::begin(row), std::end(row), 0);
    for (auto& row : counterMoves_) std::fill(std::begin(row), std::end(row), MOVE_NONE);
    for (auto& a : continuation_)
        for (auto& b : a)
            for (auto& c : b) std::fill(std::begin(c), std::end(c), 0);
    for (auto& a : captureHistory_)
        for (auto& b : a) std::fill(std::begin(b), std::end(b), 0);
    std::fill(std::begin(moveStack_), std::end(moveStack_), MOVE_NONE);
    pvLines_.clear();
    tt_.new_search();
    // The table context separates this search's root history from anything
    // stored by an earlier search, so a twofold cycle inside this search can
    // never be confused with prior game history.
    rootContextSalt_ = Zobrist::context_seed(root.history_context() ^ root.key() ^
                                             (root.rule50() * 0x9E3779B97F4A7C15ULL));
    timer_.start(limits, root.side_to_move());

    SearchResult result;
    MoveList legal;
    generate_moves(root, legal, GenType::All);
    if (legal.empty()) {
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

    rootMoves_.clear();
    rootMoves_.reserve(std::size_t(legal.size()));
    for (const ExtMove& em : legal) {
        if (!limits.searchMoves.empty() &&
            std::find(limits.searchMoves.begin(), limits.searchMoves.end(), em.move) ==
                limits.searchMoves.end())
            continue;
        rootMoves_.push_back(RootMove{em.move, 0});
    }
    // A searchmoves list that contains no legal move would leave nothing to
    // search. The UCI layer already validates the list against this position;
    // this fallback keeps the invariant that a search always has a move to
    // return instead of silently answering "0000".
    if (rootMoves_.empty())
        for (const ExtMove& em : legal) rootMoves_.push_back(RootMove{em.move, 0});
    result.bestMove = rootMoves_.front().move; // legal even if stopped at once
    result.pv = {result.bestMove};
    result.lines = {PvLine{result.bestMove, 0, {result.bestMove}}};

    // A recognised draw needs no game tree; report depth 0 instead of
    // pretending to have completed arbitrarily deep iterations.
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

    const int multiPv = std::min<int>(std::max(1, limits.multiPv), int(rootMoves_.size()));
    pvLines_.assign(std::size_t(multiPv), {});
    const int maxDepth = limits.depth > 0 ? std::min(limits.depth, MAX_PLY - 3) : MAX_PLY - 3;
    int previousScore = VALUE_ZERO;
    bool havePreviousScore = false;
    Move previousBest = MOVE_NONE;
    int stableIterations = 0;

    for (int depth = 1; depth <= maxDepth; ++depth) {
        int alpha = -VALUE_INFINITE;
        int beta = VALUE_INFINITE;
        int window = params_.aspirationInitial;
        if (params_.aspiration && havePreviousScore && depth >= 4 && multiPv == 1) {
            alpha = std::max(-VALUE_INFINITE, previousScore - window);
            beta = std::min(VALUE_INFINITE, previousScore + window);
        }
        for (int pvIndex = 0; pvIndex < multiPv; ++pvIndex) {
            // Every slot after the first is searched with a fresh full window:
            // its score must be exact for the ranking to be honest, and an
            // aspiration band tuned for the first line would bias it.
            if (pvIndex > 0) { alpha = -VALUE_INFINITE; beta = VALUE_INFINITE; }
            int passValue = -VALUE_INFINITE;
            while (true) {
                const int value = search_root(root, depth, alpha, beta, pvIndex);
                passValue = value;
                if (aborted_) break;
                if (pvIndex > 0) break;
                if (value <= alpha) {
                    beta = alpha;
                    alpha = std::max(-VALUE_INFINITE, value - window);
                    window = std::min(window * 2, 1200);
                    continue;
                }
                if (value >= beta) {
                    beta = std::min(VALUE_INFINITE, value + window);
                    window = std::min(window * 2, 1200);
                    continue;
                }
                break;
            }
            if (aborted_) break;
            (void)passValue;
            pvLines_[std::size_t(pvIndex)].clear();
            for (int i = 0; i < pvLength_[0]; ++i)
                pvLines_[std::size_t(pvIndex)].push_back(pv_[0][i]);
            if (pvLines_[std::size_t(pvIndex)].empty())
                pvLines_[std::size_t(pvIndex)].push_back(rootMoves_[std::size_t(pvIndex)].move);
        }
        if (aborted_) break;

        previousScore = rootMoves_[0].score;
        havePreviousScore = true;
        result.score = rootMoves_[0].score;
        result.depth = depth;
        result.selectiveDepth = selDepth_;
        result.nodes = nodes_;
        result.timeUs = timer_.elapsed_us();
        result.timeMs = result.timeUs / 1000;
        result.hashfull = tt_.hashfull();
        build_lines(result, multiPv);
        result.bestMove = result.lines.front().move;
        result.pv = result.lines.front().pv;
        if (onInfo) onInfo(result);

        stableIterations = (result.bestMove == previousBest) ? stableIterations + 1 : 0;
        previousBest = result.bestMove;

        if (limits.infinite) continue;
        if (timer_.soft_expired()) break;
        // A stable best move plus a well-used soft budget is a good moment to
        // stop; otherwise the next iteration is still affordable.
        if (stableIterations >= 6 && timer_.soft_usage_permille() > 550) break;
        if (timer_.has_clock() && timer_.soft_usage_permille() > 700) break;
        if (stop.load(std::memory_order_relaxed)) { aborted_ = true; break; }
    }

    // `go infinite` must not return spontaneously after reaching the maximum
    // representable depth; wait for the controller.
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
