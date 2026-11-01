// The dev2 evaluation, re-implemented here from its published constants, is the
// fixed baseline that the parameterised dev3 evaluation must reproduce exactly
// when it runs with default parameters. Written out in full (rather than
// calling into the engine's own feature code) so that a refactoring mistake
// cannot hide by changing both sides at once.
#include <algorithm>
#include <string>
#include <vector>

#include "evaluation/evaluation.hpp"
#include "test.hpp"
#include "utilities/bench_positions.hpp"

using namespace stockbear;

namespace {

const int kDev2ValueMg[PieceTypeNB] = {0, 100, 320, 335, 500, 975, 0};
const int kDev2ValueEg[PieceTypeNB] = {0, 120, 305, 330, 520, 950, 0};

int dev2_psq(int idx, int pt, bool eg) {
    const int f = idx % 8;
    const int rank = 7 - idx / 8;
    const int fileCenter = std::min(f, 7 - f);
    const int rankCenter = std::min(rank, 7 - rank);
    const int center = fileCenter + rankCenter;
    switch (pt) {
    case Pawn:   return eg ? rank * 9 + fileCenter * 2 : rank * 5 + fileCenter * 3;
    case Knight: return center * (eg ? 6 : 9) + (eg ? -18 : -24);
    case Bishop: return center * (eg ? 4 : 5) + (eg ? -10 : -12);
    case Rook:   return eg ? center * 2 : rank * 2 + fileCenter;
    case Queen:  return center * (eg ? 4 : 2) + (eg ? -12 : -6);
    case King:   return eg ? center * 10 - 30 : -rank * 8 - fileCenter * 5;
    default:     return 0;
    }
}

struct Dev2Score { int mg = 0; int eg = 0; };

Dev2Score dev2_features(const Position& p, Color us) {
    const Color them = ~us;
    const Bitboard ours = p.pieces(us), pawns = p.pieces(us, Pawn);
    const Bitboard enemyPawns = p.pieces(them, Pawn);
    Dev2Score out;
    if (p.count(us, Bishop) >= 2) { out.mg += 28; out.eg += 38; }

    Bitboard b = pawns;
    while (b) {
        const Square s = pop_lsb(b);
        const int f = file_of(s);
        if (!(pawns & AdjacentFilesBB[f])) { out.mg -= 11; out.eg -= 9; }
        if (!(enemyPawns & PassedPawnMaskBB[us][s])) {
            if (!(pawns & FileBB[f] & ForwardRanksBB[us][rank_of(s)])) {
                const int advance = us == White ? rank_of(s) : 7 - rank_of(s);
                out.mg += advance * advance * 2;
                out.eg += advance * advance * 5;
            }
        }
    }
    for (int f = 0; f < 8; ++f) {
        const int extra = std::max(0, popcount(pawns & FileBB[f]) - 1);
        out.mg -= 8 * extra;
        out.eg -= 12 * extra;
    }
    static constexpr int mgWeight[] = {0, 0, 4, 4, 2, 1, 0};
    static constexpr int egWeight[] = {0, 0, 3, 4, 3, 2, 0};
    for (PieceType pt : {Knight, Bishop, Rook, Queen}) {
        b = p.pieces(us, pt);
        while (b) {
            const Square s = pop_lsb(b);
            const int mobility = popcount(attacks_bb(pt, us, s, p.pieces()) & ~ours);
            out.mg += mobility * mgWeight[pt];
            out.eg += mobility * egWeight[pt];
            if (pt == Rook) {
                const Bitboard file = FileBB[file_of(s)];
                if (!(pawns & file)) {
                    if (!(enemyPawns & file)) { out.mg += 20; out.eg += 12; }
                    else { out.mg += 10; out.eg += 6; }
                }
            }
        }
    }
    const Square k = p.king_square(us);
    const int frontRank = rank_of(k) + (us == White ? 1 : -1);
    if (frontRank >= 0 && frontRank < 8) {
        const Bitboard shieldFiles = FileBB[file_of(k)] | AdjacentFilesBB[file_of(k)];
        out.mg += 8 * popcount(pawns & shieldFiles & RankBB[frontRank]);
    }
    const Bitboard zone = KingZoneBB[us][k];
    static constexpr int weight[] = {0, 2, 3, 3, 3, 5, 0};
    for (PieceType pt : {Pawn, Knight, Bishop, Rook, Queen}) {
        b = p.pieces(them, pt);
        while (b) {
            const Square s = pop_lsb(b);
            const int hits = popcount(attacks_bb(pt, them, s, p.pieces()) & zone);
            out.mg -= hits * weight[pt];
        }
    }
    return out;
}

int dev2_evaluate(const Position& p) {
    int accMg[ColorNB] = {}, accEg[ColorNB] = {};
    for (int pt = Pawn; pt <= King; ++pt) {
        Bitboard b = p.pieces(PieceType(pt));
        while (b) {
            const Square s = pop_lsb(b);
            const Color c = color_of(p.piece_on(s));
            const int idx = pst_index(c, s);
            accMg[c] += kDev2ValueMg[pt] + dev2_psq(idx, pt, false);
            accEg[c] += kDev2ValueEg[pt] + dev2_psq(idx, pt, true);
        }
    }
    const Dev2Score w = dev2_features(p, White), b = dev2_features(p, Black);
    const int mg = accMg[White] - accMg[Black] + w.mg - b.mg;
    const int eg = accEg[White] - accEg[Black] + w.eg - b.eg;
    int phase = 0;
    for (Color c : {White, Black}) {
        phase += p.count(c, Knight) + p.count(c, Bishop);
        phase += 2 * p.count(c, Rook) + 4 * p.count(c, Queen);
    }
    phase = std::min(24, phase);
    const int score = std::clamp((mg * phase + eg * (24 - phase)) / 24,
                                 -VALUE_KNOWN_WIN, VALUE_KNOWN_WIN);
    return p.side_to_move() == White ? score : -score;
}

// Deterministic xorshift so the walk is reproducible without engine internals.
std::uint64_t gState = 0x9E3779B97F4A7C15ULL;
std::uint64_t next_random() {
    gState ^= gState << 13; gState ^= gState >> 7; gState ^= gState << 17;
    return gState;
}
} // namespace

TEST(unit, evaluation_reproduces_dev2_baseline) {
    // The default parameter set must evaluate exactly as dev2 did, on the
    // benchmark positions and on positions reached by random legal play.
    std::vector<Position> positions;
    for (const auto& c : SearchCases) positions.push_back(test::position(c.fen));
    for (const auto& c : PerftCases) positions.push_back(test::position(c.fen));
    for (int game = 0; game < 12; ++game) {
        Position p = test::position(START_FEN);
        for (int ply = 0; ply < 40; ++ply) {
            positions.push_back(p);
            MoveList moves;
            generate_moves(p, moves);
            if (moves.empty()) break;
            p.make_move(moves[int(next_random() % std::uint64_t(moves.size()))].move);
        }
    }
    int checked = 0;
    for (const Position& p : positions) {
        if (evaluate(p) != dev2_evaluate(p)) {
            throw std::runtime_error("dev2 baseline mismatch at " + p.fen() + ": parameterised " +
                                     std::to_string(evaluate(p)) + " vs dev2 " +
                                     std::to_string(dev2_evaluate(p)));
        }
        ++checked;
    }
    CHECK(checked > 200);
}

TEST(unit, evaluation_breakdown_matches_evaluate) {
    // The tuner reads the breakdown, the search reads evaluate(); they must be
    // the same function. Checked with the default set and with a perturbed one,
    // because a coefficient that is only correct at its default value would
    // slip through a defaults-only check.
    //
    // Parameters must be installed before a Position exists (Position caches
    // material and piece-square sums), so the second round rebuilds every
    // Position from its FEN instead of reusing the first round's objects.
    EvalParams perturbed = default_eval_params();
    for (int i = 0; i < EvalParamNB; ++i) {
        const auto& def = eval_param_table()[std::size_t(i)];
        perturbed.mg[std::size_t(i)] = std::min(def.max, def.mg + 3);
        perturbed.eg[std::size_t(i)] = std::max(def.min, def.eg - 2);
    }
    std::vector<std::string> fens;
    for (const auto& c : SearchCases) fens.push_back(c.fen);
    for (int game = 0; game < 8; ++game) {
        Position p = test::position(START_FEN);
        for (int ply = 0; ply < 30; ++ply) {
            fens.push_back(p.fen());
            MoveList moves;
            generate_moves(p, moves);
            if (moves.empty()) break;
            p.make_move(moves[int(next_random() % std::uint64_t(moves.size()))].move);
        }
    }
    const EvalParams original = active_eval_params();
    struct Restore {
        EvalParams saved;
        ~Restore() { std::string ignore; apply_eval_params(saved, &ignore); }
    } restore{original};
    for (int round = 0; round < 2; ++round) {
        if (round == 1) {
            std::string error;
            CHECK(apply_eval_params(perturbed, &error));
        }
        for (const std::string& fen : fens) {
            const Position p = test::position(fen);
            const EvalBreakdown bd = eval_breakdown(p);
            const int whiteScore = eval_from_breakdown(bd, active_eval_params());
            const int expected = p.side_to_move() == White ? whiteScore : -whiteScore;
            if (evaluate(p) != expected) {
                throw std::runtime_error("breakdown mismatch at " + fen + ": evaluate " +
                                         std::to_string(evaluate(p)) + " vs breakdown " +
                                         std::to_string(expected));
            }
        }
    }
}

TEST(unit, evaluation_parameters_are_validated) {
    // A typo or an out-of-range value must be refused, not silently clamped:
    // a tuning run that wrote a broken file would otherwise ship nonsense.
    EvalParams p = default_eval_params();
    const auto& def = eval_param_table()[std::size_t(MatPawn)];
    p.mg[std::size_t(MatPawn)] = def.max + 1;
    std::string error;
    CHECK(!apply_eval_params(p, &error));
    CHECK(!error.empty());
    // The active set is unchanged after a rejected update.
    CHECK_EQ(active_eval_params().mg[std::size_t(MatPawn)], default_eval_params().mg[std::size_t(MatPawn)]);
    // The checksum distinguishes parameter sets and is stable for one set.
    CHECK_EQ(eval_params_checksum(default_eval_params()), eval_params_checksum(default_eval_params()));
    EvalParams other = default_eval_params();
    other.eg[std::size_t(MatRook)] += 1;
    CHECK(eval_params_checksum(other) != eval_params_checksum(default_eval_params()));
}
