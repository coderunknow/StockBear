#include "test.hpp"
#include "chess/dead_position.hpp"
using namespace stockbear;

namespace {
DeadResult analyze(const char* fen, DeadLimits limits = DeadLimits{}) {
    Position p = test::position(fen);
    return analyze_dead_position(p, limits);
}
DeadStatus status_of(const char* fen, DeadLimits limits = DeadLimits{}) {
    return analyze(fen, limits).status;
}
// A witness must be a legal move sequence ending in checkmate.
void check_witness(const Position& start, const DeadResult& result) {
    CHECK_EQ(result.status, DeadStatus::Alive);
    CHECK(!result.witness.empty());
    Position p = start;
    for (Move m : result.witness) {
        CHECK(is_ok(m));
        CHECK_EQ(move_from_uci(p, move_to_uci(m)), m);
        p.make_move(m);
    }
    CHECK(p.in_check());
    CHECK(!p.has_legal_moves());
}
void check_witness(const char* fen) {
    Position p = test::position(fen);
    check_witness(p, analyze_dead_position(p));
}
DeadLimits small_budget() {
    DeadLimits limits;
    limits.componentStates = 200000;
    limits.witnessNodes = 20000;
    return limits;
}
}

TEST(deadpos, insufficient_material_is_dead) {
    CHECK_EQ(status_of("8/8/8/4k3/8/8/8/4K3 w - - 0 1"), DeadStatus::Dead);
    CHECK_EQ(status_of("8/8/8/8/4k3/8/8/2B1K3 b - - 0 1"), DeadStatus::Dead);
    CHECK_EQ(status_of("8/8/8/8/4k3/8/8/2N1K3 w - - 0 1"), DeadStatus::Dead);
    // Two same-coloured bishops (c1 and e3 are both dark squares).
    CHECK_EQ(status_of("4k3/8/8/8/8/4B3/8/2B1K3 w - - 0 1"), DeadStatus::Dead);
    // One bishop each, both on dark squares.
    CHECK_EQ(status_of("4k3/8/8/8/8/4b3/8/2B1K3 w - - 0 1"), DeadStatus::Dead);
    Position p = test::position("4k3/8/8/8/8/4b3/8/2B1K3 w - - 0 1");
    CHECK(is_dead_position(p));
}

TEST(deadpos, minor_versus_minor_is_alive) {
    // One knight each and two knights against a bare king admit cooperating
    // mates, so neither may be reported dead.
    check_witness("8/8/8/8/4k3/8/8/1N2K1N1 w - - 0 1");
    // The knight-against-knight mate exists but is longer than the default
    // search depth and its component is large, so only the soundness property
    // is asserted here: the verdict is never Dead without a completed proof.
    CHECK(status_of("4k1n1/8/8/8/8/8/8/4K1N1 w - - 0 1") != DeadStatus::Dead);
}

TEST(deadpos, opposite_coloured_bishops_are_alive) {
    // A bishop each on opposite colours has a cooperating mate; the shortest
    // one is deeper than the witness search reaches, so the complete component
    // enumeration finds it (about 4 million states).
    DeadLimits limits;
    limits.componentStates = 6000000;
    const char* fen = "4k3/8/8/8/8/4b3/8/3B1K2 w - - 0 1";
    Position p = test::position(fen);
    check_witness(p, analyze_dead_position(p, limits));
}

TEST(deadpos, queen_and_rook_endings_are_alive) {
    check_witness("8/8/8/8/8/2k5/8/1Q2K3 w - - 0 1");
    check_witness("4k3/8/8/8/8/8/8/4K2R w - - 0 1");
    check_witness("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"); // mate in one
}

TEST(deadpos, locked_pawn_structure_is_dead) {
    // Every pawn is blocked by an opposing pawn and no capture is available, so
    // no pawn can ever move or promote and only the kings can move. A
    // material-only detector cannot see this.
    const char* fen = "8/3k4/p1p2p1p/PpPp1PpP/1P1P2P1/4K3/8/8 w - - 6 49";
    Position p = test::position(fen);
    const DeadResult result = analyze_dead_position(p);
    CHECK_EQ(result.status, DeadStatus::Dead);
    CHECK(result.exhaustiveComplete);
    CHECK(result.states > 100);
    CHECK_EQ(p.draw_status(), DrawStatus::AutomaticDeadPosition);

    // Deadness is closed under legal moves: every successor is dead too.
    MoveList moves;
    generate_moves(p, moves);
    CHECK(!moves.empty());
    for (const ExtMove& em : moves) {
        Position next = p;
        next.make_move(em.move);
        CHECK_EQ(analyze_dead_position(next, small_budget()).status, DeadStatus::Dead);
    }
}

TEST(deadpos, locked_pawns_with_bishops_is_dead) {
    // Locked pawn chains plus a bishop each: the whole reachable component
    // (about 1.2 million states) contains no checkmate.
    DeadLimits limits;
    limits.componentStates = 2000000;
    CHECK_EQ(status_of("2b1k3/8/8/1p1p1p1p/1P1P1P1P/8/8/2B1K3 w - - 0 1", limits),
             DeadStatus::Dead);
    CHECK_EQ(status_of("2b1k3/8/8/1p1p1p1p/1P1P1P1P/8/8/2B1K3 b - - 0 1", limits),
             DeadStatus::Dead);
}

TEST(deadpos, alive_in_ordinary_positions) {
    check_witness("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
    check_witness("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1");
    check_witness("8/8/8/4k3/8/4P3/8/4K3 w - - 0 1");
}

TEST(deadpos, terminal_positions_are_not_dead_positions) {
    // Checkmate is decided by Article 5.1.1 and stalemate by 5.2.1; neither is
    // reported as an Article 5.2.2 dead position.
    DeadResult mate = analyze("7k/6Q1/5K2/8/8/8/8/8 b - - 0 1");
    CHECK_EQ(mate.status, DeadStatus::Alive);
    CHECK(mate.reason.find("terminal") != std::string::npos);
    DeadResult stale = analyze("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1");
    CHECK_EQ(stale.status, DeadStatus::Alive);
    CHECK(stale.reason.find("terminal") != std::string::npos);
    Position matePos = test::position("7k/6Q1/5K2/8/8/8/8/8 b - - 0 1");
    CHECK_EQ(matePos.draw_status(), DrawStatus::None);
    Position stalePos = test::position("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1");
    CHECK_EQ(stalePos.draw_status(), DrawStatus::AutomaticStalemate);
}

TEST(deadpos, budget_exhaustion_is_unknown_never_dead) {
    // With an unusable budget the analysis must not guess. Positions whose
    // component is far too large to enumerate stay Unknown.
    DeadLimits limits;
    limits.componentStates = 1000;
    limits.witnessMaxDepth = 2;
    limits.witnessNodes = 500;
    CHECK_EQ(status_of("4k1n1/8/8/8/8/8/8/4K1N1 w - - 0 1", limits), DeadStatus::Unknown);
    CHECK_EQ(status_of("4k1n1/8/8/8/8/8/8/4K1N1 w - - 0 1", limits) == DeadStatus::Dead,
             false);
    // A tiny component still concludes with the same small budget.
    CHECK_EQ(status_of("8/8/8/4k3/8/8/8/4K3 w - - 0 1", limits), DeadStatus::Dead);
}

TEST(deadpos, ephemeral_en_passant_and_castling_states_are_explored) {
    // Castling rights and the en-passant right are part of the state; the
    // analysis must still terminate and answer for positions that have them.
    DeadResult withRights = analyze("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1");
    CHECK_EQ(withRights.status, DeadStatus::Alive);
    DeadResult ep = analyze("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2");
    CHECK_EQ(ep.status, DeadStatus::Alive);
}

TEST(deadpos, quick_draw_status_budget_is_bounded) {
    // Position::draw_status() uses fast limits; the answer for an ordinary
    // middlegame must still be "not dead" and must not block for long.
    Position p = test::position("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4");
    CHECK(p.draw_status() != DrawStatus::AutomaticDeadPosition);
    CHECK_EQ(p.draw_status(), DrawStatus::None);
}

namespace {
// Builds a board-only FEN ("<placement> <side> - - 0 1") from one or two kings
// plus an optional extra piece. Returns an empty string for illegal boards.
std::string board_fen(Square wk, Square bk, Square extra = SQ_NONE, char piece = 0) {
    char board[64];
    for (int i = 0; i < 64; ++i) board[i] = 0;
    auto put = [&board](Square s, char c) {
        if (board[s]) return false;
        board[s] = c;
        return true;
    };
    if (!put(wk, 'K') || !put(bk, 'k')) return std::string();
    if (extra != SQ_NONE && !put(extra, piece)) return std::string();
    std::string out;
    for (int r = 7; r >= 0; --r) {
        int run = 0;
        for (int f = 0; f < 8; ++f) {
            const char c = board[r * 8 + f];
            if (!c) { ++run; continue; }
            if (run) { out += char('0' + run); run = 0; }
            out += c;
        }
        if (run) out += char('0' + run);
        if (r) out += '/';
    }
    return out;
}
}

TEST(deadpos, exhaustive_two_king_space_is_dead) {
    // Every legal placement of the two kings, with either side to move, has no
    // legal continuation to a checkmate: kings alone can never mate. This
    // exhausts the complete two-piece state space (4032 placements x 2 sides).
    int legal = 0;
    int dead = 0;
    for (int w = 0; w < 64; ++w) {
        for (int b = 0; b < 64; ++b) {
            const Square wk = Square(w);
            const Square bk = Square(b);
            if (wk == bk) continue;
            const std::string placement = board_fen(wk, bk);
            if (placement.empty()) continue;
            for (const char* side : {"w", "b"}) {
                Position p;
                std::string error;
                if (!p.set(placement + " " + side + " - - 0 1", &error)) continue;
                ++legal;
                if (analyze_dead_position(p).status == DeadStatus::Dead) ++dead;
            }
        }
    }
    CHECK(legal > 3000);
    CHECK_EQ(dead, legal);
}

TEST(deadpos, exhaustive_three_piece_minor_space_is_dead) {
    // Every legal placement of both kings plus a single bishop or knight, with
    // either side to move: a lone minor piece can never mate. Exhausts the
    // complete 3-piece space for those minor types (~250k placements per side).
    struct Extra { char piece; };
    for (const Extra extra : {Extra{'B'}, Extra{'N'}}) {
        int legal = 0;
        int dead = 0;
        int terminal = 0;
        for (int w = 0; w < 64; ++w) {
            for (int b = 0; b < 64; ++b) {
                for (int x = 0; x < 64; ++x) {
                    const Square wk = Square(w);
                    const Square bk = Square(b);
                    const Square px = Square(x);
                    if (wk == bk || wk == px || bk == px) continue;
                    const std::string placement = board_fen(wk, bk, px, extra.piece);
                    if (placement.empty()) continue;
                    for (const char* side : {"w", "b"}) {
                        Position p;
                        std::string error;
                        if (!p.set(placement + " " + side + " - - 0 1", &error)) continue;
                        ++legal;
                        if (!p.has_legal_moves()) {
                            // A stalemate is decided by Article 5.2.1 before
                            // Article 5.2.2 applies; the analyzer must say so
                            // and must never call the position a dead position.
                            ++terminal;
                            const DeadResult result = analyze_dead_position(p);
                            CHECK_EQ(result.status, DeadStatus::Alive);
                            CHECK(result.reason.find("terminal") != std::string::npos);
                            CHECK(!p.in_check());
                        } else if (analyze_dead_position(p).status == DeadStatus::Dead) {
                            ++dead;
                        }
                    }
                }
            }
        }
        CHECK(legal > 200000);
        CHECK_EQ(dead + terminal, legal);
        CHECK(dead > 200000);
    }
}
