// exp-0064: extension-agnostic main-TT identity.
//
// The shipped TT identity is (key, rule50, historyContext, extensions), where
// `extensions` is the per-path check-extension BUDGET, not part of the position.
// With TTExtensionAgnostic the probe AND the store use extension argument 0, so
// identical positions reuse each other across budgets. rule50 and
// historyContext MUST stay distinguishing: they are what keep repetition/draw
// scores sound. These tests pin both halves of that contract, the default-OFF
// behaviour, and mate/stalemate soundness with the switch ON.
#include "test.hpp"
#include "chess/zobrist.hpp"
#include "search/search.hpp"
#include "search/transposition_table.hpp"
#include "evaluation/eval_params.hpp"
#include "utilities/types.hpp"
#include "uci/uci.hpp"
#include <sstream>
#include <atomic>
#include <memory>

using namespace stockbear;

namespace {

SearchResult run_with(const std::string& fen, int depth, bool agnostic) {
    Position p = test::position(fen);
    TranspositionTable tt(4);
    SearchParams sp;
    sp.ttEval = true;
    sp.ttExtensionAgnostic = agnostic;
    SearchLimits lim;
    lim.depth = depth;
    std::atomic<bool> stop{false};
    auto s = std::make_unique<Search>(tt, sp);
    return s->run(p, lim, stop);
}

} // namespace

TEST(tt_extension_identity, helper_preserves_budget_when_off) {
    for (int e = 0; e <= 4; ++e) CHECK_EQ(tt_identity_extensions(false, e), e);
}

TEST(tt_extension_identity, helper_zeroes_budget_when_on) {
    for (int e = 0; e <= 4; ++e) CHECK_EQ(tt_identity_extensions(true, e), 0);
}

TEST(tt_extension_identity, shipped_default_is_off) {
    SearchParams sp;
    CHECK_EQ(sp.ttExtensionAgnostic, false);
    // The shipped identity therefore still distinguishes every budget.
    CHECK_EQ(tt_identity_extensions(sp.ttExtensionAgnostic, 2), 2);
}

TEST(tt_extension_identity, agnostic_identity_reuses_across_budgets) {
    TranspositionTable tt(1);
    Position p = test::position(START_FEN);
    const Key key = p.key();
    const Key ctx = p.history_context();
    tt.store(key, p.rule50(), ctx, tt_identity_extensions(true, 3),
             MOVE_NONE, 42, 5, Bound::Exact, 0, 10);
    // Every budget maps to the same slot, so every budget finds the entry.
    for (int e = 0; e <= 3; ++e) {
        const TTEntry* hit = tt.probe(key, p.rule50(), ctx, tt_identity_extensions(true, e));
        CHECK(hit != nullptr);
        CHECK_EQ(hit->value, 42);
    }
    // The SHIPPED identity does not: this is the reuse loss being removed.
    TranspositionTable shipped(1);
    shipped.store(key, p.rule50(), ctx, tt_identity_extensions(false, 3),
                  MOVE_NONE, 42, 5, Bound::Exact, 0, 10);
    CHECK(shipped.probe(key, p.rule50(), ctx, tt_identity_extensions(false, 3)) != nullptr);
    CHECK(shipped.probe(key, p.rule50(), ctx, tt_identity_extensions(false, 0)) == nullptr);
}

TEST(tt_extension_identity, history_context_still_separates_when_agnostic) {
    TranspositionTable tt(1);
    // A real repetition cycle: the same board, different reversible history.
    Position p = test::position(START_FEN);
    test::play(p, "g1f3"); test::play(p, "g8f6");
    test::play(p, "f3g1"); test::play(p, "f6g8");
    const Key key = p.key();
    const Key ctx = p.history_context();
    tt.store(key, p.rule50(), ctx, tt_identity_extensions(true, 1),
             MOVE_NONE, 500, 6, Bound::Lower, 0, 10);
    CHECK(tt.probe(key, p.rule50(), ctx, tt_identity_extensions(true, 0)) != nullptr);
    // A different history context must NEVER be served, even though the board
    // key and the extension argument now match. This is the draw-soundness pin.
    CHECK(tt.probe(key, p.rule50(), ctx ^ Key(0x9E3779B97F4A7C15ULL),
                   tt_identity_extensions(true, 0)) == nullptr);
}

TEST(tt_extension_identity, rule50_still_separates_when_agnostic) {
    TranspositionTable tt(1);
    Position p = test::position(START_FEN);
    tt.store(p.key(), 0, p.history_context(), tt_identity_extensions(true, 2),
             MOVE_NONE, 7, 6, Bound::Exact, 0, 10);
    CHECK(tt.probe(p.key(), 0, p.history_context(), tt_identity_extensions(true, 0)) != nullptr);
    CHECK(tt.probe(p.key(), 4, p.history_context(), tt_identity_extensions(true, 0)) == nullptr);
}

TEST(tt_extension_identity, mate_distances_preserved_with_switch_on) {
    // Mate in 1: score AND the delivered checkmate must survive the change.
    const char* m1 = "7k/5Q2/6K1/8/8/8/8/8 w - - 0 1";
    SearchResult one = run_with(m1, 3, true);
    CHECK(is_mate_value(one.score));
    CHECK_EQ(mate_value_to_moves(one.score), 1);
    Position p = test::position(m1);
    p.make_move(one.bestMove);
    CHECK(p.in_check());
    CHECK(!p.has_legal_moves());
    // Mate in 2: exact distance, not merely "some mate".
    SearchResult two = run_with("8/8/8/5Q2/k7/8/1K6/8 w - - 0 1", 4, true);
    CHECK(is_mate_value(two.score));
    CHECK_EQ(mate_value_to_moves(two.score), 2);
    // Being CHECKMATED is still reported as a lost score with no move. Qg7 is
    // adjacent to Kh8 and defended by Kg6, so this is mate, not stalemate.
    SearchResult lost = run_with("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", 3, true);
    CHECK_EQ(lost.bestMove, MOVE_NONE);
    CHECK_EQ(lost.score, -VALUE_MATE);
    // The neighbouring stalemate position must stay a draw, not become a mate.
    SearchResult stale = run_with("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", 3, true);
    CHECK_EQ(stale.bestMove, MOVE_NONE);
    CHECK_EQ(stale.score, 0);
}

TEST(tt_extension_identity, drawn_positions_stay_drawn_with_switch_on) {
    CHECK_EQ(run_with("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", 3, false).score,
             run_with("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", 3, true).score);
    CHECK_EQ(run_with("4k3/8/8/8/8/8/8/4K3 w - - 0 1", 4, true).score, 0);
    CHECK_EQ(run_with("7k/8/8/8/8/8/8/K7 w - - 0 1", 4, true).score, 0);
}

TEST(tt_extension_identity, switch_is_live_not_a_no_op) {
    // A tactical middlegame where check extensions actually fire: the two
    // identities must produce different trees. If this ever becomes equal the
    // mechanism has silently died and the strength screen would be meaningless.
    const char* fen = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 4";
    const SearchResult off = run_with(fen, 6, false);
    const SearchResult on = run_with(fen, 6, true);
    CHECK(off.nodes > 0);
    CHECK(on.nodes > 0);
    CHECK(off.nodes != on.nodes);
}

TEST(tt_extension_identity, search_wiring_characterization_pins) {
    // Semantic justification: the model oracle
    // (scripts/probes/tt_identity_oracle.cpp) proves the identity contract is
    // (key, rule50, historyContext) when ON and the full tuple when OFF. These
    // node-count pins lock the SEARCH WIRING to that verified contract, so a
    // probe-only / store-only / context-dropping / rule50-dropping edit cannot
    // pass unnoticed. They are characterization pins of the audited behaviour,
    // not a strength claim.
    const EvalParams saved = active_eval_params();
    apply_eval_params(default_eval_params());
    struct Pin { const char* fen; int depth; bool on; unsigned long long nodes; };
    const char* f1 = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 4";
    const char* f2 = "r2q1rk1/pp2ppbp/2np1np1/8/2BNP3/2N1BP2/PPPQ2PP/2KR3R w - - 5 11";
    const Pin pins[] = {
        {f1, 6, false, 14395ULL}, {f1, 6, true, 14307ULL},
        {f1, 7, false, 29340ULL}, {f1, 7, true, 28708ULL},
        {f2, 6, false, 15387ULL}, {f2, 6, true, 15335ULL},
        {f2, 7, false, 37914ULL}, {f2, 7, true, 37212ULL},
    };
    for (const Pin& pin : pins) {
        const SearchResult r = run_with(pin.fen, pin.depth, pin.on);
        CHECK_EQ(r.nodes, pin.nodes);
    }
    apply_eval_params(saved);
}

TEST(tt_extension_identity, uci_option_is_advertised_and_accepted) {
    // The UCI surface must advertise the option default-false and accept it
    // without an error. End-to-end proof that the parsed value reaches the
    // search is done interactively by scripts/check_tt_extension_identity.py
    // --liveness (a piped std::istringstream hits EOF and aborts the worker, so
    // node counts cannot be asserted from this in-process harness).
    std::istringstream in("uci\nsetoption name TTExtensionAgnostic value true\n"
                          "setoption name TTExtensionAgnostic value false\nquit\n");
    std::ostringstream out;
    { UciEngine engine(in, out); engine.loop(); }
    const std::string s = out.str();
    CHECK(s.find("option name TTExtensionAgnostic type check default false") != std::string::npos);
    CHECK(s.find("info string setoption:") == std::string::npos);
}
