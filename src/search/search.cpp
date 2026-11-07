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
#include <iostream>

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
// exp-0033: fixed, pre-registered razoring margins by remaining depth.
// Deliberately NOT a tunable search parameter: the schedule is frozen in
// docs/DEV6_PREREG_EXP0033.md before any measurement, so it cannot be
// optimised on the test openings.
constexpr int RazorMargin[4] = {0, 125, 175, 300};
// exp-0034: frozen SEE margin for bad-capture pruning (NOT tuned).
constexpr int BadCaptureMargin = 100;
// exp-0043 FROZEN constants (BEFORE any result). Chosen ONLY from the pre-result mechanism-live /
// overhead diagnostic (never from Elo); see docs/DEV6_PREREG_EXP0043.md §3.
constexpr int SingularMinDepth = 3;        // live at the 40+4 ms depth 5-6 tree
constexpr int SingularDepthSlack = 3;      // TT evidence up to 3 plies shallower
constexpr int SingularMargin = 50;         // cp above beta required
constexpr int MaxSingularExtensions = 2;   // hard per-path cap
// exp-0044 FROZEN ordering constant (chosen BEFORE any result, never tuned):
// demoted SEE-losing captures are placed below every quiet/killer move.
constexpr int BadCaptureOrderScore = -2000000;
// exp-0046 FROZEN constants (chosen BEFORE any game, from theory only; NEVER
// tuned on a test suite or Elo result). See docs/DEV6_PREREG_EXP0046.md §3.
constexpr int AdaptiveNullMarginDivisor = 200; // cp per extra reduction ply
constexpr int AdaptiveNullExtraCap = 2;        // hard cap on extra plies
// exp-0050 correction history. ALL constants frozen from theory BEFORE any
// game (docs/DEV6_PREREG_EXP0050.md); none is tuned on a suite or an Elo result.
// The table stores scaled centipawns so the decaying update stays integral.
constexpr int CorrectionScale = 256;            // fixed-point per cp
constexpr int CorrectionLimit = 32 * CorrectionScale;  // clamp at +/-32 cp
constexpr int CorrectionUpdateCap = 8 * CorrectionScale;  // one-step cap
constexpr int CorrectionDepthDivisor = 8;      // weight -> depth/8 of the error
#ifdef SB_CORRECTION_DEBUG
static std::uint64_t correction_updates = 0, correction_applied = 0,
                     correction_nonzero = 0, correction_clamped = 0;
#endif
#ifdef SB_ADAPTIVE_NULL_DEBUG
static std::uint64_t adaptive_null_nodes = 0, adaptive_null_extra = 0,
                     adaptive_null_changed = 0;
#endif
#ifdef SB_DEADEVAL_DEBUG
static std::uint64_t deadeval_skipped = 0, deadeval_evaluated = 0;
#endif
#ifdef SB_BADCAP_DEBUG
static std::uint64_t badcap_demotions = 0, badcap_nodes_with_demotion = 0;
#endif
#ifdef SB_SINGULAR_DEBUG
static std::uint64_t singular_triggers = 0, singular_extensions = 0;
#endif
// exp-0037: frozen ProbCut margin and reduced depth (NOT tuned on any suite).
constexpr int ProbCutMargin = 200;
constexpr int ProbCutReducedDepth = 4;

// Integer-only reduction schedule; keeps results bit-identical across
// platforms and compilers (a floating-point logarithm does not guarantee that).
#include "search/lmr_table.inc"

// dev6 experiment knobs: compile-time overridable so parameter variants can be
// screened without editing source back and forth. Every default below is the
// value dev4 shipped, so a default build stays bit-identical (bench signature
// 243f9a1c1ba5b36f at depth 4).
#ifndef SB_NULLMOVE_R
#define SB_NULLMOVE_R 3          // null-move base reduction
#endif
#ifndef SB_FUTILITY_MARGIN
#define SB_FUTILITY_MARGIN 110   // futility margin per remaining depth
#endif
#ifndef SB_REV_FUTILITY_MARGIN
#define SB_REV_FUTILITY_MARGIN 85 // reverse-futility margin per remaining depth
#endif
#ifndef SB_LMR_BASE
#define SB_LMR_BASE 1            // base LMR reduction
#endif
#ifndef SB_DELTA_MARGIN
#define SB_DELTA_MARGIN 200      // qsearch delta-pruning safety margin
#endif
#ifndef SB_EARLY_STABLE
#define SB_EARLY_STABLE 6        // stable iterations before the early soft stop
#endif
#ifndef SB_EARLY_PERMILLE
#define SB_EARLY_PERMILLE 550    // soft-budget fraction for the stable early stop
#endif
#ifndef SB_CLOCK_PERMILLE
#define SB_CLOCK_PERMILLE 700    // soft-budget fraction for the clock early stop
#endif
#ifndef SB_QEVAL_LITE
#define SB_QEVAL_LITE 0          // 1: qsearch stand-pat uses evaluate_lite()
#endif
#ifndef SB_SEE_CACHE
#define SB_SEE_CACHE 0           // 1: reuse score_moves' SEE result in the qsearch loop
#endif
#if SB_QEVAL_LITE
#define QSEARCH_EVAL(pos) evaluate_lite(pos)
#else
#define QSEARCH_EVAL(pos) evaluate(pos)
#endif

inline int reduction_for(int depth, int moveCount) {
    int r = SB_LMR_BASE;
    if (depth >= 6) r += 1;
    if (moveCount >= 8) r += 1;
    if (moveCount >= 24) r += 1;
    if (depth >= 14) r += 1;
    return r;
}

// Late move pruning limits: how many quiet moves are worth searching before
// the rest are skipped, by remaining depth. `improving` halves them, because a
// position that is getting better deserves the extra effort.
inline int late_move_limit(int depth, bool improving) {
    const int limit = 3 + depth * depth;
    return improving ? limit : limit / 2;
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

void Search::score_moves(const Position& pos, MoveList& moves, Move hashMove, int ply,
                          bool mainSearch) {
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
#if SB_SEE_CACHE
            moves[i].seeScore = seeScore;
#endif
            // Winning and equal captures first, losing captures after quiets.
            score = 2000000 + (seeScore >= 0 ? 1000000 : 0) + 32 * gain + seeScore;
            // exp-0044 (frozen before results): a capture whose SEE is
            // negative is a material concession. In the MAIN search it is
            // currently ranked at ~2,000,000, i.e. ABOVE killers (1,500,000)
            // and above every quiet/history move. Demote it to the very tail
            // so good moves raise alpha first. Promotions and the TT hash move
            // are never demoted (they are handled by earlier branches). This
            // changes ONLY the ordering: no move is skipped, no SEE or eval
            // call is added, and no stand-pat value is rewritten. Qsearch is
            // explicitly excluded because it already skips SEE<0 captures.
            if (params_.badCaptureOrdering && mainSearch && seeScore < 0 &&
                move_type(m) != PromotionMove) {
                score = BadCaptureOrderScore + 32 * gain + seeScore;
#ifdef SB_BADCAP_DEBUG
                ++badcap_demotions;
#endif
            }
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
                const int cont = continuation(previousType, move_to(previous),
                                              type_of(pos.piece_on(move_from(m))), move_to(m));
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
    Move* row = pv_row(ply);
    row[0] = move;
    const int childLength = ply + 1 < MAX_PLY ? pvLength_[ply + 1] : 0;
    const int count = std::min(childLength, MAX_PLY - ply - 1);
    const Move* child = ply + 1 < MAX_PLY ? pv_row(ply + 1) : nullptr;
    for (int i = 0; i < count; ++i) row[i + 1] = child[i];
    pvLength_[ply] = count + 1;
}

// exp-0050: index the correction table by PAWN STRUCTURE only. Two 64-bit pawn
// bitboards are mixed with odd multipliers and folded; no allocation, no loop,
// no evaluation call. Pieces are deliberately excluded so the learned bias
// generalises across piece placements sharing the same pawn skeleton.
std::size_t Search::correction_index(const Position& pos, Color us) const {
    const Bitboard wp = pos.pieces(White, Pawn);
    const Bitboard bp = pos.pieces(Black, Pawn);
    std::uint64_t h = wp * 0x9E3779B97F4A7C15ULL;
    h ^= (bp * 0xC2B2AE3D27D4EB4FULL) + 0x165667B19E3779F9ULL + (h << 6) + (h >> 2);
    h ^= h >> 29;
    h *= 0xBF58476D1CE4E5B9ULL;
    h ^= h >> 32;
    return (std::size_t(h) & (CorrectionSlots - 1)) + std::size_t(us) * CorrectionSlots;
}

// exp-0050: fold the observed (search - raw static eval) error into the table
// with a decaying update, so the entry tracks a running mean rather than the
// last node. Called ONLY on a completed, non-mate, non-check node whose best
// move was quiet (a capture's score reflects the capture, not the eval bias).
void Search::update_correction(const Position& pos, Color us, int staticEval,
                              int best, int depth) {
    const int error = (best - staticEval) * CorrectionScale;
    const int weight = std::min(depth, CorrectionDepthDivisor);
    int delta = error * weight / CorrectionDepthDivisor;
    delta = std::clamp(delta, -CorrectionUpdateCap, CorrectionUpdateCap);
    int& entry = correction_[correction_index(pos, us)];
    // Exponential decay towards the new observation: entry += (delta-entry)/8.
    entry += (delta - entry) / 8;
    const int clamped = std::clamp(entry, -CorrectionLimit, CorrectionLimit);
#ifdef SB_CORRECTION_DEBUG
    ++correction_updates;
    if (clamped != entry) ++correction_clamped;
#endif
    entry = clamped;
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
        int& cont = continuation(type_of(previousPiece), move_to(previous),
                                 type_of(pos.piece_on(move_from(move))), move_to(move));
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
    if (ply >= MAX_PLY - 2) return QSEARCH_EVAL(pos);
    if (pos.is_search_draw(ply)) return VALUE_DRAW;

    // exp-0038 (frozen before results): dedicated qsearch transposition table.
    const int originalAlpha = alpha;
    const Key qContext = pos.history_context() ^ rootContextSalt_;
    QCacheEntry* qEntry = params_.qsearchTT
        ? qslot(pos.key(), pos.rule50(), qContext) : nullptr;
    if (qEntry != nullptr && qEntry->bound != 0 &&
        qEntry->key == pos.key() && qEntry->rule50 == pos.rule50() &&
        qEntry->context == qContext) {
        const int value = TranspositionTable::value_from_table(qEntry->value, ply);
        if (qEntry->bound == 1 ||
            (qEntry->bound == 2 && value >= beta) ||
            (qEntry->bound == 3 && value <= alpha))
            return value;
    }
    // Store the completed qsearch value under its ORIGINAL window. Mate scores
    // are excluded: their ply normalisation is exact here but a reused bound
    // could still mask a shorter mate found at a different ply.
    auto finish = [&](int value) {
        if (qEntry != nullptr && !aborted_ && std::abs(value) < MATE_BOUND) {
            qEntry->key = pos.key();
            qEntry->rule50 = pos.rule50();
            qEntry->context = qContext;
            qEntry->value = std::int16_t(TranspositionTable::value_to_table(value, ply));
            qEntry->bound = value >= beta ? 2 : (value <= originalAlpha ? 3 : 1);
        }
        return value;
    };

    const bool inCheck = pos.in_check();
    MoveList moves;
    int best;
    if (inCheck) {
        generate_moves(pos, moves, GenType::All);
        if (moves.empty()) return finish(-VALUE_MATE + ply);
        best = -VALUE_INFINITE;
    } else {
        best = QSEARCH_EVAL(pos);
        if (best >= beta) return finish(best);
        alpha = std::max(alpha, best);
        // Delta pruning: if no single capture can lift the score to alpha, the
        // static evaluation is already the best this node can offer.
        if (best + SeeValue[Queen] + params_.deltaMargin <= alpha) return finish(best);
        generate_moves(pos, moves, GenType::QSearch);
        if (moves.empty()) {
            // No capture and no promotion: only stalemate can change the score.
            if (!pos.has_legal_moves()) return finish(VALUE_DRAW);
            return finish(best);
        }
        // exp-0042 (frozen before results): the shipped delta check above has
        // to assume the best possible capture is a queen (975 cp) because the
        // move list does not exist yet. Now that the legal captures ARE known,
        // use their ACTUAL largest material gain plus the SAME frozen margin.
        // gain_of() plus the SEE-form promotion bonus is exactly SEE's gain[0],
        // so a capture-promotion can never be under-counted. This is a more
        // ACCURATE decision at the same node, not a new lossy pruning rule:
        // the original conservative check still runs first and unchanged, and
        // this extra check can only prune nodes where no available move can
        // plausibly lift the score to alpha. Guarded away from check evasions.
        if (params_.maxGainDelta) {
            int maxGain = 0;
            for (int i = 0; i < moves.size(); ++i) {
                const Move m = moves[i].move;
                int g = gain_of(pos, m);
                if (move_type(m) == PromotionMove)
                    g += SeeValue[promotion_type(m)] - SeeValue[Pawn];
                if (g > maxGain) maxGain = g;
            }
            if (best + maxGain + params_.deltaMargin <= alpha) return finish(best);
        }
    }

    score_moves(pos, moves, MOVE_NONE, ply, false);
    for (int i = 0; i < moves.size(); ++i) {
        next_move(moves, i);
        const Move m = moves[i].move;
#if SB_SEE_CACHE
        if (!inCheck && params_.seePruning && moves[i].seeScore < 0) continue;
#else
        if (!inCheck && params_.seePruning && see(pos, m) < 0) continue;
#endif
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
    // Must go through finish() like every other completed exit. Returning
    // `best` directly bypassed the store, so the qsearch cache only ever held
    // stand-pat / delta-pruning values and NEVER the result of a node that
    // actually searched a capture -- which is the dominant case and the whole
    // point of the cache. Default OFF (params_.qsearchTT), so the shipped
    // search is untouched; see tests/unit/test_search.cpp qsearch_tt group.
    return finish(best);
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
#ifdef SB_TT_IDENTITY_DEBUG
    tt_.diag_set_depth(depth);
#endif
    const int ttExtensions = tt_identity_extensions(params_.ttExtensionAgnostic, extensions);
    const TTEntry* entry = tt_.probe(pos.key(), pos.rule50(), context, ttExtensions);
    const Move hashMove = entry != nullptr ? entry->move : MOVE_NONE;
    if (entry != nullptr && !pvNode && entry->depth >= depth) {
        const int value = TranspositionTable::value_from_table(entry->value, ply);
        if (entry->bound == Bound::Exact ||
            (entry->bound == Bound::Lower && value >= beta) ||
            (entry->bound == Bound::Upper && value <= alpha))
            return value;
    }

    // Internal iterative reduction: with no hash move the node is likely to be
    // refuted by a shallower search, so one ply is borrowed and the result is
    // still stored under the reduced depth.
    if (params_.iir && hashMove == MOVE_NONE && depth >= 4) --depth;

    // exp-0043 (frozen before results): TT-informed singular extension. A TT
    // lower bound found at nearly the same depth and well above beta means all
    // alternatives failed to reach that value in the previous iteration: the
    // hash move is singular. Because the TT cutoff above has already handled
    // proven cutoffs, any surviving lower bound here is shallower than `depth`.
    // Unlike ProbCut (exp-0037) this spends NO verification subtree; the only
    // cost is the extra ply of the hash move itself. Guarded away from PV
    // nodes, checks, mate windows and paths that already used the extension
    // budget, and never applied to mate scores.
    int singularExt = 0;
    if (params_.ttSingularExtension && !pvNode && !inCheck &&
        depth >= SingularMinDepth && hashMove != MOVE_NONE &&
        entry != nullptr && entry->bound == Bound::Lower &&
        entry->depth >= depth - SingularDepthSlack &&
        singularExtensions_ < MaxSingularExtensions) {
        const int ttValue = TranspositionTable::value_from_table(entry->value, ply);
        if (std::abs(ttValue) < MATE_BOUND && ttValue >= beta + SingularMargin) {
            singularExt = 1;
#ifdef SB_SINGULAR_DEBUG
            ++singular_triggers;
#endif
        }
    }
    const bool mateWindow = std::abs(beta) >= MATE_BOUND || std::abs(alpha) >= MATE_BOUND;
    if (mateWindow) singularExt = 0;

    // exp-0045 (frozen before results): with ttEval a TT hit can supply the
    // static evaluation directly. The shipped code nevertheless calls
    // evaluate(pos) first and then overwrites it -- a full tapered evaluation
    // (25-30 % of node time) thrown away. When the switch is ON, skip that
    // dead call. The returned VALUE is bit-identical; only time changes.
    // No TT entry, move, bound, stand-pat value or search decision changes.
    const bool ttEvalUsable = params_.ttEval && entry != nullptr && !inCheck &&
                              entry->eval != VALUE_NONE;
    int staticEval;
    if (ttEvalUsable && params_.skipDeadTTEval) {
        staticEval = int(entry->eval);
#ifdef SB_DEADEVAL_DEBUG
        ++deadeval_skipped;
#endif
    } else {
        staticEval = evaluate(pos);
#ifdef SB_DEADEVAL_DEBUG
        ++deadeval_evaluated;
#endif
        if (ttEvalUsable) staticEval = int(entry->eval);
    }
    // exp-0050 (frozen before results): the RAW evaluation is what the TT stores
    // and what the update below learns against. Only the copy used for the
    // heuristic pruning margins is corrected, so the learned bias can never
    // compound through TT reuse. With the switch OFF this block is unreachable
    // and every value below is bit-identical to the shipped search.
    const int rawStaticEval = staticEval;
    const Color us = pos.side_to_move();
    if (params_.correctionHistory && !inCheck && std::abs(rawStaticEval) < MATE_BOUND) {
        const int scaled = correction_[correction_index(pos, us)];
        const int adjusted = rawStaticEval + scaled / CorrectionScale;
        // Never let a heuristic correction reach a mate score.
        staticEval = std::clamp(adjusted, -MATE_BOUND + 1, MATE_BOUND - 1);
#ifdef SB_CORRECTION_DEBUG
        ++correction_applied;
        if (scaled != 0) ++correction_nonzero;
#endif
    }
    evalStack_[ply] = staticEval;
    // "Improving": is the side to move better off than it was two plies ago?
    // Used only to widen or narrow heuristic margins, never to bound a proven
    // value, so a wrong guess costs strength at worst and never correctness.
    const bool improving = !params_.improving ? true
                        : inCheck ? false
                        : ply >= 2 ? staticEval > evalStack_[ply - 2] - 10
                        : true;

    // exp-0037 ProbCut (frozen in docs/DEV6_PREREG_EXP0037.md BEFORE results):
    // at non-PV nodes with remaining depth >= 5, run a reduced-depth
    // null-window search at a raised beta (beta + frozen 200 cp margin). A
    // fail-high there predicts a full-depth fail-high, so the whole move loop
    // can be skipped. Guarded away from PV nodes and mate windows so a proven
    // mate value can never be replaced. Default off => bit-identical shipped
    // search (bench 243f9a1c1ba5b36f). No tuning on any test suite.
    if (params_.probCut && !pvNode && !mateWindow && depth >= 5) {
        const int raisedBeta = std::min(beta + ProbCutMargin, VALUE_INFINITE - 1);
        const int probValue = negamax(pos, depth - ProbCutReducedDepth,
                                      raisedBeta - 1, raisedBeta, ply,
                                      false, extensions, false);
        if (aborted_) return 0;
        if (probValue >= raisedBeta) return probValue;
    }

    // exp-0033 razoring: at shallow depth a node whose static evaluation is far
    // below alpha almost certainly fails low. Confirm with a cheap null-window
    // quiescence before spending a full move loop. Default off, so the shipped
    // search stays bit-identical. Guarded away from mate windows and PV nodes so
    // it can never change a proven mate value.
    if (params_.razoring && !pvNode && !inCheck && !mateWindow && depth <= 3 &&
        staticEval + RazorMargin[depth] < alpha) {
        const int razorValue = quiescence(pos, alpha - 1, alpha, ply);
        if (aborted_) return 0;
        if (razorValue < alpha) return razorValue;
    }

    // Reverse futility pruning: at shallow depth a large static margin over beta
    // is good enough, provided no mate score can be involved.
    if (params_.reverseFutility && !pvNode && !inCheck && !mateWindow &&
        depth <= (params_.improving ? 8 : 6) &&
        staticEval - (params_.improving ? (improving ? 70 : 105) : SB_REV_FUTILITY_MARGIN) * depth >= beta)
        return staticEval;

    // Null-move pruning. Disabled when the side to move has no non-pawn
    // material (zugzwang risk) and directly after another null move.
    if (params_.nullMove && allowNull && !pvNode && !inCheck && !mateWindow && depth >= 3 &&
        staticEval >= beta && has_non_pawn_material(pos)) {
        int reduction = SB_NULLMOVE_R + depth / 5;
        // exp-0046 (frozen before results): adapt the null-move verification
        // depth to how far staticEval exceeds beta. With the switch OFF this
        // line is unreachable and the shipped formula above is unchanged, so
        // the default build is BIT-IDENTICAL. No new search work is added: the
        // margin uses values already computed for the null-move guard.
        if (params_.adaptiveNullR) {
            const int margin = staticEval - beta;
            const int extra = std::min(AdaptiveNullExtraCap,
                                       margin / AdaptiveNullMarginDivisor);
            reduction += extra;
#ifdef SB_ADAPTIVE_NULL_DEBUG
            ++adaptive_null_nodes;
            adaptive_null_extra += extra;
            if (extra > 0) ++adaptive_null_changed;
#endif
        }
        // A null move is not a move: clear the slot so the child does not read
        // a stale previous move from a sibling branch or an earlier iteration.
        const Move savedPrevious = moveStack_[ply];
        moveStack_[ply] = MOVE_NONE;
        pos.make_null_move();
        const int value = -negamax(pos, depth - 1 - reduction, -beta, -beta + 1, ply + 1,
                                   false, extensions, false);
        pos.unmake_null_move();
        moveStack_[ply] = savedPrevious;
        if (aborted_) return 0;
        if (value >= beta) return value >= MATE_BOUND ? beta : value;
    }

    MoveList moves;
    generate_moves(pos, moves, GenType::All);
    if (moves.empty()) return inCheck ? -VALUE_MATE + ply : VALUE_DRAW;

    score_moves(pos, moves, hashMove, ply, true);
    const int futilityBase = staticEval + SB_FUTILITY_MARGIN * depth;
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

        // exp-0034: skip clearly losing captures in the main search at
        // shallow depth. SEE was computed by score_moves(); the fallback
        // keeps correctness in builds without SB_SEE_CACHE. Guarded away
        // from PV nodes, mate windows, checks and the hash move.
        // exp-0041: with the switch off the guard is bit-identical to the
        // validated exp-0034/0035/0036 implementation (depth <= 3). With it
        // on, the SAME frozen SEE < -100 test also applies higher in the tree.
        if (params_.badCapturePruning && !isQuiet && !isHash && !pvNode &&
            !inCheck && !mateWindow &&
            (depth <= 3 || params_.badCaptureAllDepths)) {
#if SB_SEE_CACHE
            const int capSee = moves[i].seeScore;
#else
            const int capSee = see(pos, m);
#endif
            if (capSee < -BadCaptureMargin) continue;
        }

        // The checking test makes and unmakes the move, so it is only run when
        // a pruning or reduction decision actually depends on it.
        // Late move pruning: at low depth the tail of the quiet move list is
        // not worth searching at all. Skipped when a mate score is already in
        // hand, which is the only way the skipped moves could still matter.
        if (params_.moveCountPruning && !pvNode && !inCheck && !mateWindow && isQuiet &&
            !isHash && best > -MATE_BOUND && depth <= 8 &&
            moveCount >= late_move_limit(depth, improving))
            continue;

        const bool futilityCandidate = isQuiet && !pvNode && !inCheck && !mateWindow &&
                                       moveCount > 0 && params_.futility && depth <= 3 &&
                                       futilityBase <= alpha;
        const bool lmrCandidate = isQuiet && !inCheck && !mateWindow && params_.lmr && !isHash &&
                                  (params_.modernLmr
                                       ? (depth >= 3 && moveCount >= 2)
                                       : (depth >= 3 && moveCount >= 3 &&
                                          m != killers_[ply][0] && m != killers_[ply][1]));
        bool check = inCheck;
        if (futilityCandidate || lmrCandidate) check = gives_check(pos, m);
        if (futilityCandidate && !check) continue;

        // Read the history value before making the move: the table is indexed
        // by the moving side, which `make_move` flips.
        const int quietHistory = isQuiet ? history_[pos.side_to_move()][move_from(m)][move_to(m)]
                                         : 0;
        pos.make_move(m);
        moveStack_[ply] = m;
        // exp-0043: the hash move is always ordered first. Extend it by exactly
        // one ply when the TT evidence above says it is singular. The counter
        // is restored immediately so the cap is per-path, not global.
        const int hashExt = (singularExt != 0 && isHash && moveCount == 0) ? 1 : 0;
        if (hashExt) {
            ++singularExtensions_;
#ifdef SB_SINGULAR_DEBUG
            ++singular_extensions;
#endif
        }
        int value;
        if (moveCount == 0) {
            value = -negamax(pos, depth - 1 + hashExt, -beta, -alpha, ply + 1, pvNode,
                             extensions, true);
        } else {
            int reduction = 0;
            if (lmrCandidate && !check && params_.modernLmr) {
                int r = int(LmrTable[std::min(depth, 63)][std::min(moveCount, 63)]);
                r -= pvNode ? 1 : 0;
                r += improving ? 0 : 1;
                r += quietHistory < 0 ? 1 : 0;
                r += m == killers_[ply][0] || m == killers_[ply][1] ? -1 : 0;
                reduction = std::max(0, std::min(r, depth - 2));
            } else if (lmrCandidate && !check) {
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
        if (hashExt) --singularExtensions_;
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
    // exp-0050: learn from this node's own verdict. Only when the node completed,
    // is not a mate/check node, and the best move was quiet -- a capture's score
    // reflects the material change, not a bias in the static evaluation.
    if (params_.correctionHistory && !aborted_ && !inCheck &&
        std::abs(best) < MATE_BOUND && std::abs(rawStaticEval) < MATE_BOUND &&
        (bestMove == MOVE_NONE || quiet(pos, bestMove)) &&
        !(stored == Bound::Lower && best <= rawStaticEval) &&
        !(stored == Bound::Upper && best > rawStaticEval))
        update_correction(pos, us, rawStaticEval, best, depth);
    // The RAW eval is stored, never the corrected one (see exp-0050 above).
    tt_.store(pos.key(), pos.rule50(), context, ttExtensions, bestMove, best, depth, stored, ply,
              params_.ttEval ? rawStaticEval : VALUE_NONE);
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
    std::fill_n(continuation_.get(), ContinuationSlots, 0);
    std::fill_n(correction_.get(), CorrectionSlots * ColorNB, 0);
    for (auto& a : captureHistory_)
        for (auto& b : a) std::fill(std::begin(b), std::end(b), 0);
    std::fill(std::begin(moveStack_), std::end(moveStack_), MOVE_NONE);
    std::fill_n(qcache_.get(), QCacheSlots, QCacheEntry{});
    singularExtensions_ = 0;
#ifdef SB_BADCAP_DEBUG
    badcap_demotions = 0;
    badcap_nodes_with_demotion = 0;
#endif
#ifdef SB_ADAPTIVE_NULL_DEBUG
    adaptive_null_nodes = adaptive_null_extra = adaptive_null_changed = 0;
#endif
#ifdef SB_CORRECTION_DEBUG
    correction_updates = correction_applied = correction_nonzero = correction_clamped = 0;
#endif
#ifdef SB_DEADEVAL_DEBUG
    deadeval_skipped = deadeval_evaluated = 0;
#endif
#ifdef SB_SINGULAR_DEBUG
    singular_triggers = singular_extensions = 0;
#endif
    pvLines_.clear();
    tt_.new_search();
    // The table context separates this search's root history from anything
    // stored by an earlier search, so a twofold cycle inside this search can
    // never be confused with prior game history.
    rootContextSalt_ = Zobrist::context_seed(root.history_context() ^ root.key() ^
                                             (root.rule50() * 0x9E3779B97F4A7C15ULL));
    timer_.start(limits, root.side_to_move(), params_.bankedTime);

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
            const Move* line = pv_row(0);
            for (int i = 0; i < pvLength_[0]; ++i)
                pvLines_[std::size_t(pvIndex)].push_back(line[i]);
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
        // stop; otherwise the next iteration is still affordable. dev5's
        // FullSoftBudget candidate skips both early stops and always searches
        // until the soft budget is exhausted (the hard budget still guards the
        // clock), trading later-move time for more nodes now.
        if (!params_.fullSoftBudget) {
            if (stableIterations >= SB_EARLY_STABLE && timer_.soft_usage_permille() > SB_EARLY_PERMILLE) break;
            if (timer_.has_clock() && timer_.soft_usage_permille() > SB_CLOCK_PERMILLE) break;
        }
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
#ifdef SB_ADAPTIVE_NULL_DEBUG
    std::cerr << "ADAPTIVENULLDEBUG switches=" << int(params_.adaptiveNullR)
              << " null_nodes=" << adaptive_null_nodes
              << " changed=" << adaptive_null_changed
              << " extra_plies=" << adaptive_null_extra
              << " nodes=" << nodes_ << std::endl;
#endif
#ifdef SB_DEADEVAL_DEBUG
    std::cerr << "DEADEVALDEBUG switches=" << int(params_.skipDeadTTEval)
              << " skipped=" << deadeval_skipped
              << " evaluated=" << deadeval_evaluated
              << " nodes=" << nodes_ << std::endl;
#endif
#ifdef SB_BADCAP_DEBUG
    std::cerr << "BADCAPDEBUG switches=" << int(params_.badCaptureOrdering)
              << " demotions=" << badcap_demotions
              << " nodes=" << nodes_ << std::endl;
#endif
#ifdef SB_SINGULAR_DEBUG
    std::cerr << "SINGULARDEBUG switches=" << int(params_.ttSingularExtension)
              << " triggers=" << singular_triggers
              << " extensions=" << singular_extensions
              << " nodes=" << nodes_ << std::endl;
#endif
    return result;
}
}
