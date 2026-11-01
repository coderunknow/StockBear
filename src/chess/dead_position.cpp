// ---------------------------------------------------------------------------
// dead_position.cpp - general FIDE Article 5.2.2 decision procedure.
//
// Two cooperating passes:
//
//   1. A depth-limited "short helpmate" search. Both sides cooperate, so a
//      single legal continuation ending in checkmate is a certificate that the
//      position is alive. This pass is cheap and resolves most real positions.
//
//   2. An exhaustive enumeration of the whole reachable state component. It
//      walks every position reachable from the input (including positions with
//      reduced material, promoted pieces, and every castling-rights and
//      en-passant variant) and stops as soon as any of them is checkmate.
//      If the enumeration finishes without reaching a mate, no series of legal
//      moves can end in checkmate: the position is dead.
//
// Both passes only ever report a verdict they can justify. Running out of
// budget or depth yields DeadStatus::Unknown; the code never guesses.
// ---------------------------------------------------------------------------
#include "chess/dead_position.hpp"
#include "chess/bitboard.hpp"
#include "evaluation/evaluation.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdlib>
#include <cstdint>
#include <utility>
#include <vector>

namespace stockbear {
namespace {

// --- 128-bit state identity -------------------------------------------------
// Two independent 64-bit fingerprints are kept for every enumerated position:
// the position's Zobrist key and a mix over the complete placement and the
// irreversible state (side, castling rights, en-passant square). Treating the
// pair as the identity makes a false collision astronomically unlikely
// (~2^-97 for billions of states), which matters because a collision could
// hide a mate and thereby prove a deadness verdict the position does not have.
std::uint64_t placement_mix(const Position& pos) {
    std::uint64_t h = 0xCBF29CE484222325ULL;
    const auto mix = [&h](std::uint64_t v) {
        h ^= v + 0x9E3779B97F4A7C15ULL + (h << 6) + (h >> 2);
        h *= 0x100000001B3ULL;
        h ^= h >> 29;
    };
    for (int pt = 0; pt < PieceTypeNB; ++pt) mix(pos.pieces(PieceType(pt)));
    mix(pos.pieces(White));
    mix(pos.pieces(Black));
    mix(std::uint64_t(pos.side_to_move()));
    mix(std::uint64_t(pos.castling_rights()));
    const Square ep = pos.ep_square();
    mix(ep == SQ_NONE ? std::uint64_t(64) : std::uint64_t(ep));
    return h;
}

// Open-addressing set of 128-bit fingerprints. Load factor stays below 0.7.
class StateSet {
public:
    void reset(std::size_t hint = 1024) {
        std::size_t capacity = 1024;
        while (capacity < hint * 2) capacity <<= 1;
        slots_.assign(capacity, Slot{});
        mask_ = capacity - 1;
        size_ = 0;
    }

    bool empty() const { return size_ == 0; }
    std::size_t size() const { return size_; }

    // Returns true when the fingerprint was not present yet.
    bool insert(std::uint64_t a, std::uint64_t b) {
        if ((size_ + 1) * 10 >= slots_.size() * 7) grow();
        return insert_no_resize(a, b);
    }

private:
    struct Slot {
        std::uint64_t a = 0;
        std::uint64_t b = 0;
        bool used = false;
    };

    static std::size_t home(std::uint64_t a, std::uint64_t b, std::size_t mask) {
        std::uint64_t h = a ^ (b * 0xD6E8FEB86659FD93ULL);
        h ^= h >> 33;
        h *= 0xFF51AFD7ED558CCDULL;
        h ^= h >> 33;
        return std::size_t(h) & mask;
    }

    bool insert_no_resize(std::uint64_t a, std::uint64_t b) {
        std::size_t i = home(a, b, mask_);
        while (slots_[i].used) {
            if (slots_[i].a == a && slots_[i].b == b) return false;
            i = (i + 1) & mask_;
        }
        slots_[i].a = a;
        slots_[i].b = b;
        slots_[i].used = true;
        ++size_;
        return true;
    }

    void grow() {
        std::vector<Slot> old;
        old.swap(slots_);
        slots_.assign(old.size() * 2, Slot{});
        mask_ = slots_.size() - 1;
        size_ = 0;
        for (const Slot& s : old)
            if (s.used) insert_no_resize(s.a, s.b);
    }

    std::vector<Slot> slots_;
    std::size_t mask_ = 0;
    std::size_t size_ = 0;
};

// Number of squares the given king could move to, approximately: squares not
// occupied by its own pieces and not attacked by the other side with the king
// removed from the occupancy. Used only to steer the heuristic witness search.
int escape_count(const Position& pos, Color defender) {
    const Square k = pos.king_square(defender);
    const Color attacker = ~defender;
    Bitboard targets = KingAttacksBB[k] & ~pos.pieces(defender);
    const Bitboard occWithoutKing = pos.pieces() ^ square_bb(k);
    int count = 0;
    while (targets) {
        const Square t = pop_lsb(targets);
        if (!pos.attacked_by(attacker, t, occWithoutKing)) ++count;
    }
    return count;
}

enum class Mode {
    Witness,   // depth-limited, prefers checking moves: find any helpmate
    Component  // exhaustive: visit every reachable state exactly once
};

// Chebyshev distance between two squares.
int chebyshev(Square a, Square b) {
    return std::max(std::abs(file_of(a) - file_of(b)),
                    std::abs(rank_of(a) - rank_of(b)));
}

// Distance from a square to the nearest corner (Chebyshev). Helpmates need the
// mated king confined, and corners are where that is cheapest.
const std::array<int, SQ_NB>& corner_distance_table() {
    static const auto table = [] {
        std::array<int, SQ_NB> values{};
        for (int s = 0; s < SQ_NB; ++s) {
            const Square sq = Square(s);
            int best = 7;
            for (int c = 0; c < 4; ++c) {
                const Square corner = make_square(c & 1 ? FileH : FileA, c & 2 ? Rank8 : Rank1);
                best = std::min(best, chebyshev(sq, corner));
            }
            values[s] = best;
        }
        return values;
    }();
    return table;
}

class Explorer {
public:
    Explorer(const DeadLimits& limits, Color attacker) : attacker_(attacker) { (void)limits; }

    // Depth-first enumeration of everything reachable from `pos`. Returns true
    // when a checkmate position was reached; witness() then holds the line.
    bool explore(Position& pos, Mode mode, int depthCap, std::uint64_t budget) {
        frames_.clear();
        path_.clear();
        pathKeys_.clear();
        aborted_ = false;
        depthLimited_ = false;
        states_ = 0;
        witness_.clear();
        seen_.reset(1024);

        if (mode == Mode::Component) {
            seen_.insert(pos.key(), placement_mix(pos));
            ++states_;
        }
        frames_.push_back(Frame{order(pos, mode), 0, pos.key()});

        while (!frames_.empty()) {
            Frame& frame = frames_.back();
            if (frame.cursor >= frame.moves.size()) {
                frames_.pop_back();
                if (!path_.empty()) {
                    pos.unmake_move(path_.back());
                    path_.pop_back();
                    pathKeys_.pop_back();
                }
                continue;
            }
            if (states_ >= budget) {
                aborted_ = true;
                return false;
            }

            const Move move = frame.moves[frame.cursor++];
            pos.make_move_without_repetition(move);
            ++states_;

            MoveList childMoves;
            generate_moves(pos, childMoves, GenType::All);
            if (childMoves.empty()) {
                if (pos.in_check()) {
                    // Checkmate reached: the current path plus `move` is the
                    // certificate.
                    path_.push_back(move);
                    witness_.assign(path_.begin(), path_.end());
                    path_.pop_back();
                    pos.unmake_move(move);
                    return true;
                }
                pos.unmake_move(move); // stalemate: this continuation ends
                continue;
            }

            bool fresh = true;
            if (mode == Mode::Component) {
                fresh = seen_.insert(pos.key(), placement_mix(pos));
            } else {
                const Key k = pos.key();
                fresh = std::find(pathKeys_.begin(), pathKeys_.end(), k) == pathKeys_.end();
            }
            if (!fresh) {
                pos.unmake_move(move);
                continue;
            }
            if (int(path_.size()) + 1 >= depthCap) {
                // Refuse to extend past the cap. This can only reduce the
                // enumerated set, so a caller must treat it as "incomplete".
                depthLimited_ = true;
                pos.unmake_move(move);
                continue;
            }

            path_.push_back(move);
            pathKeys_.push_back(pos.key());
            frames_.push_back(Frame{order(pos, mode, childMoves), 0, pos.key()});
        }
        return false;
    }

    std::uint64_t states() const { return states_; }
    std::uint64_t distinct() const { return seen_.size(); }
    bool aborted() const { return aborted_; }
    bool depth_limited() const { return depthLimited_; }
    const std::vector<Move>& witness() const { return witness_; }

private:
    struct Frame {
        std::vector<Move> moves;
        std::size_t cursor = 0;
        Key key = 0;
    };

    // Orders the child's moves. In witness mode checking moves come first
    // (they are what a helpmate needs); in component mode a cheap static order
    // is used because every move is eventually expanded anyway.
    std::vector<Move> order(const Position& pos, Mode mode) const {
        MoveList ml;
        generate_moves(pos, ml, GenType::All);
        return order(pos, mode, ml);
    }

    std::vector<Move> order(const Position& pos, Mode mode, const MoveList& ml) const {
        struct Scored { Move move = MOVE_NONE; int score = 0; };
        std::vector<Scored> scored;
        scored.reserve(std::size_t(ml.size()));
        const Color us = pos.side_to_move();
        const Color defender = ~attacker_;
        const Square defenderKing = pos.king_square(defender);
        const int defenderCorner = corner_distance_table()[defenderKing];
        const int escapesBefore = mode == Mode::Witness ? escape_count(pos, defender) : 0;
        for (const ExtMove& em : ml) {
            const Move m = em.move;
            int score = 0;
            if (move_type(m) == PromotionMove) score += 4000 + PieceValueMg[promotion_type(m)];
            if (move_type(m) == EnPassantMove || !pos.empty(move_to(m))) {
                const Piece victim = move_type(m) == EnPassantMove
                    ? make_piece(~us, Pawn) : pos.piece_on(move_to(m));
                score += 1000 + 10 * PieceValueMg[type_of(victim)]
                       - PieceValueMg[type_of(pos.piece_on(move_from(m)))];
            }
            if (mode == Mode::Witness) {
                if (pos.in_check()) {
                    score += 200000; // evasions are forced; examine them first
                } else {
                    const Square from = move_from(m);
                    const Square to = move_to(m);
                    // Move the defender's king toward a corner: that is where a
                    // cooperative mate is cheapest, whoever is moving.
                    const Square kingTo = (type_of(pos.piece_on(from)) == King &&
                                           color_of(pos.piece_on(from)) == defender) ? to : defenderKing;
                    score += 300 * (defenderCorner - corner_distance_table()[kingTo]);
                    // Bring own king and pieces closer to the defender's king.
                    score += 8 * (chebyshev(from, defenderKing) - chebyshev(to, defenderKing));
                    if (color_of(pos.piece_on(from)) == attacker_)
                        score += 40 * (chebyshev(from, defenderKing) - chebyshev(to, defenderKing));
                    // The goal of a helpmate is a position where the mated
                    // king has no escape at all, so moves that shrink the
                    // escape count are explored first. This steers both sides:
                    // the attacker confines, the defender confines itself.
                    Position& mutablePos = const_cast<Position&>(pos);
                    mutablePos.make_move_without_repetition(m);
                    const int escapesAfter = escape_count(mutablePos, defender);
                    const bool givesCheck = mutablePos.in_check();
                    mutablePos.unmake_move(m);
                    score += 3000 * (escapesBefore - escapesAfter) - 300 * escapesAfter;
                    if (givesCheck) score += (us == attacker_) ? 5000 : -1000;
                }
            }
            scored.push_back(Scored{m, score});
        }
        // Stable insertion sort: deterministic order, no allocation churn.
        for (std::size_t i = 1; i < scored.size(); ++i) {
            const Scored item = scored[i];
            std::size_t j = i;
            while (j > 0 && scored[j - 1].score < item.score) {
                scored[j] = scored[j - 1];
                --j;
            }
            scored[j] = item;
        }
        std::vector<Move> moves;
        moves.reserve(scored.size());
        for (const Scored& s : scored) moves.push_back(s.move);
        return moves;
    }

    std::vector<Frame> frames_;
    std::vector<Move> path_;
    std::vector<Key> pathKeys_;
    std::vector<Move> witness_;
    Color attacker_ = White;
    StateSet seen_;
    std::uint64_t states_ = 0;
    bool aborted_ = false;
    bool depthLimited_ = false;
};

} // namespace

const char* to_string(DeadStatus status) {
    switch (status) {
    case DeadStatus::Alive: return "alive";
    case DeadStatus::Dead: return "dead";
    case DeadStatus::Unknown: return "unknown";
    }
    return "unknown";
}

DeadResult analyze_dead_position(const Position& pos, const DeadLimits& limits) {
    DeadResult result;

    // A depth-first path never visits the same state twice, so the path length
    // is bounded by the number of states the caller is willing to enumerate.
    DeadLimits budget = limits;
    if (budget.componentMaxDepth <= 0) {
        budget.componentMaxDepth = int(std::min<std::uint64_t>(limits.componentStates, 400000));
    }

    MoveList rootMoves;
    generate_moves(pos, rootMoves, GenType::All);
    if (rootMoves.empty()) {
        // Articles 5.1.1 and 5.2.1 decide these positions before 5.2.2 can
        // apply; report them explicitly instead of pretending to adjudicate.
        result.status = DeadStatus::Alive;
        result.reason = pos.in_check() ? "terminal: checkmate (Article 5.1.1)"
                                      : "terminal: stalemate (Article 5.2.1)";
        return result;
    }

    // Sound static proof: material that cannot produce a mate at all.
    if (pos.insufficient_material()) {
        result.status = DeadStatus::Dead;
        result.exhaustiveComplete = true;
        result.reason = "proved dead: insufficient mating material";
        return result;
    }

    // Strategy: a very short witness pass catches the common "obvious mate"
    // case, then a bounded enumeration settles every position whose component
    // is small (locked structures, low material). Only positions that survive
    // both get the expensive passes.
    {
        // The quick pass must respect the caller's witness budget as well: a
        // fast_dead_limits() caller asks for 20,000 nodes and depth 6, and
        // ignoring that made draw_status() spend more than it reserved.
        const DeadLimits quick{
            std::min<std::uint64_t>(limits.witnessNodes, 30000), 1,
            std::min(limits.witnessMaxDepth, 8), budget.componentMaxDepth, false};
        for (int depth = 1; depth <= quick.witnessMaxDepth; ++depth) {
            bool concluded = false;
            for (Color attacker : {White, Black}) {
                Explorer explorer(quick, attacker);
                Position work = pos;
                if (explorer.explore(work, Mode::Witness, depth, quick.witnessNodes / 2)) {
                    result.status = DeadStatus::Alive;
                    result.witness = explorer.witness();
                    result.visited = explorer.states();
                    result.reason = "helpmate witness found (quick pass)";
                    return result;
                }
                result.visited = explorer.states();
                if (explorer.aborted()) { concluded = true; break; }
            }
            if (concluded) break;
        }
    }

    const std::uint64_t firstBudget = std::min<std::uint64_t>(budget.componentStates, 300000);
    if (budget.allowExhaustive) {
        Explorer explorer(limits, White);
        Position work = pos;
        const bool found = explorer.explore(work, Mode::Component,
                                            budget.componentMaxDepth, firstBudget);
        result.expanded = explorer.states();
        result.states = explorer.distinct();
        if (found) {
            result.status = DeadStatus::Alive;
            result.witness = explorer.witness();
            result.reason = "checkmate reached within the reachable component";
            return result;
        }
        if (!explorer.aborted() && !explorer.depth_limited()) {
            result.status = DeadStatus::Dead;
            result.exhaustiveComplete = true;
            result.reason = "proved dead: complete reachable component contains no checkmate";
            return result;
        }
        result.exhaustiveComplete = false;
    }

    // Cheap helpmate witness search for positions whose component is large:
    // alive positions almost always admit a short cooperative mate. Both
    // candidate mating sides are tried, since only one of them can mate.
    //
    // The quick pass at the top of this function already ran this search with
    // min(witnessNodes, 30000) / min(witnessMaxDepth, 8). If that is exactly the
    // budget this pass would use, the search is deterministic and would repeat
    // the same work, so it is skipped. The complete enumeration below is never
    // skipped: it is the only pass that can prove `dead`.
    const bool witnessRepeatsEarlierPass =
        std::min<std::uint64_t>(limits.witnessNodes, 30000) == limits.witnessNodes &&
        std::min(limits.witnessMaxDepth, 8) == limits.witnessMaxDepth;
    if (!witnessRepeatsEarlierPass) {
        for (int depth = 1; depth <= budget.witnessMaxDepth; ++depth) {
            for (Color attacker : {White, Black}) {
                Explorer explorer(limits, attacker);
                Position work = pos;
                if (explorer.explore(work, Mode::Witness, depth, budget.witnessNodes / 2)) {
                    result.status = DeadStatus::Alive;
                    result.witness = explorer.witness();
                    result.visited = explorer.states();
                    result.reason = "helpmate witness found (depth-limited search)";
                    return result;
                }
                result.visited = explorer.states();
                if (explorer.aborted()) break;
            }
        }
    }

    if (!budget.allowExhaustive) {
        result.status = DeadStatus::Unknown;
        result.reason = "exhaustive analysis disabled and no witness found";
        return result;
    }

    // Full reachable-component enumeration with the caller's budget.
    {
        Explorer explorer(limits, White);
        Position work = pos;
        const bool found = explorer.explore(work, Mode::Component,
                                            budget.componentMaxDepth,
                                            budget.componentStates);
        result.expanded = explorer.states();
        result.states = explorer.distinct();
        if (found) {
            result.status = DeadStatus::Alive;
            result.witness = explorer.witness();
            result.reason = "checkmate reached within the reachable component";
            return result;
        }
        if (explorer.aborted()) {
            result.status = DeadStatus::Unknown;
            result.reason = "component enumeration exceeded the state budget";
            return result;
        }
        if (explorer.depth_limited()) {
            result.status = DeadStatus::Unknown;
            result.reason = "component enumeration exceeded the path-depth limit";
            return result;
        }
        result.status = DeadStatus::Dead;
        result.exhaustiveComplete = true;
        result.reason = "proved dead: complete reachable component contains no checkmate";
        return result;
    }
}

bool is_dead_position(const Position& pos, const DeadLimits& limits) {
    return analyze_dead_position(pos, limits).status == DeadStatus::Dead;
}

DeadLimits fast_dead_limits() {
    DeadLimits limits;
    limits.witnessNodes = 20000;
    limits.componentStates = 120000;
    limits.witnessMaxDepth = 6;
    return limits;
}

} // namespace stockbear
