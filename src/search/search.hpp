#pragma once
#include "chess/position.hpp"
#include "search/timeman.hpp"
#include "search/transposition_table.hpp"
#include <array>
#include <atomic>
#include <cstddef>
#include <memory>
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
    // cp-denominated search margins (exp-0019: exposed as UCI options because
    // the tuned eval scales changed; defaults are the dev4 values, so a
    // default build stays bit-identical, bench 243f9a1c1ba5b36f).
    int futilityMargin = 110;      // per remaining depth
    int revFutilityMargin = 85;    // per remaining depth
    int deltaMargin = 200;         // qsearch delta-pruning safety margin
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

    // --- dev4 search features -------------------------------------------------
    // Each is separately switchable so it can be ablated by a match instead of
    // being accepted because it "should" help. Defaults are set to the
    // configuration that the recorded dev4 experiments measured as strongest;
    // see benchmarks/results/0.1.0-dev4/experiments/.
    bool modernLmr = false;         // logarithmic reduction table + rich adjustment
    bool moveCountPruning = false;  // skip late quiet moves at low depth
    bool iir = false;               // reduce one ply when there is no hash move
    bool improving = false;         // static-eval trend feeds pruning margins
    bool ttEval = false;            // reuse the static evaluation stored in the TT
    bool razoring = false;          // drop into quiescence near the alpha bound
    // --- dev5 experiments -----------------------------------------------------
    // Use the whole soft time slice instead of stopping at 55-70% of it.
    // dev4 left the early stops in; dev5 measures them at a fixed time control.
    bool fullSoftBudget = false;
    // --- dev6 exp-0034 (default off; isolated same-binary ablation) ---------
    // Skip losing captures in the main search at shallow depth using the SEE
    // already computed by score_moves(). See docs/DEV6_PREREG_EXP0034.md.
    bool badCapturePruning = false;
    // --- dev6 exp-0037 (default off; isolated same-binary ablation) ---------
    // ProbCut: a raised-beta reduced-depth null-window search predicts a
    // full-depth fail-high. Frozen margin/depth in docs/DEV6_PREREG_EXP0037.md.
    bool probCut = false;
    // --- dev6 exp-0038 (default off; isolated same-binary ablation) ---------
    // Dedicated qsearch transposition table: cache qsearch bounds by
    // (key, rule50, history context) so repeated quiescence positions can cut
    // without re-searching. Never touches the main TT. Frozen design in
    // docs/DEV6_PREREG_EXP0038.md.
    bool qsearchTT = false;
    // --- dev6 exp-0040 (default off; isolated same-binary ablation) ---------
    // Banked-time allocation: spend part of the initial clock early and
    // converge back to the increment. Frozen in docs/DEV6_PREREG_EXP0040.md.
    bool bankedTime = false;
    // --- dev6 exp-0041 (default off; isolated same-binary ablation) ---------
    // Extend the validated shallow losing-capture pruning to ALL remaining
    // depths with the frozen BadCaptureMargin=100. Frozen design in
    // docs/DEV6_PREREG_EXP0041.md.
    bool badCaptureAllDepths = false;
    // --- dev6 exp-0042 (default off; isolated same-binary ablation) ---------
    // Max-gain delta pruning in quiescence: after generating legal captures,
    // use the ACTUAL largest available gain (including promotion bonus) rather
    // than the fixed "assume a queen" bound. Frozen deltaMargin=200 unchanged,
    // original conservative check retained. See docs/DEV6_PREREG_EXP0042.md.
    bool maxGainDelta = false;
    // --- dev6 exp-0043 (default off; isolated same-binary ablation) ---------
    // TT-informed singular extension: a slightly-shallower TT lower bound far
    // above beta is evidence that the hash move alone beat beta in the previous
    // iteration, so search that move one ply deeper. NO verification subtree
    // (exp-0037 measured verification overhead is fatal at 40+4 ms).
    // Frozen in docs/DEV6_PREREG_EXP0043.md.
    bool ttSingularExtension = false;
    // --- dev6 exp-0044 (default off; isolated same-binary ablation) ---------
    // Pure move-ordering accuracy: in the MAIN search only, order SEE-losing
    // captures BELOW killers/history quiets instead of immediately after
    // winning captures. No move is removed, no per-node work is added, no
    // stand-pat value or pruning/extension decision is changed.
    // Frozen in docs/DEV6_PREREG_EXP0044.md.
    bool badCaptureOrdering = false;
    // --- dev6 exp-0045 (default off; isolated same-binary ablation) ---------
    // Bit-exact throughput: when a main-TT hit already supplies the static
    // evaluation (ttEval=true), the unconditional evaluate(pos) below is dead
    // work whose result is immediately overwritten. Skip it. Values are
    // IDENTICAL; only time per node changes. Frozen in
    // docs/DEV6_PREREG_EXP0045.md.
    bool skipDeadTTEval = false;
    // --- dev6 exp-0046 (default off; isolated same-binary ablation) ---------
    // Margin-adaptive null-move reduction: the shipped null-move reduction is
    // a fixed SB_NULLMOVE_R + depth/5. When staticEval is far above beta the
    // null-move verification subtree can be shallower; when the margin is
    // small it must stay at the shipped depth. This is a NEW decision RULE,
    // not a constant retune: it uses only the already-computed staticEval and
    // beta, adds NO evaluate/SEE/movegen call, NO extra ply and NO per-node
    // work. Frozen in docs/DEV6_PREREG_EXP0046.md.
    bool adaptiveNullR = false;
    // --- dev6 exp-0050 (default off; isolated same-binary ablation) ---------
    // Correction history: the static evaluation is systematically biased in a
    // way that depends on the PAWN STRUCTURE (the tapered handcrafted eval
    // cannot see passed-pawn races, blocked chains or colour-complex holes).
    // Keep a decaying running average of (search score - raw static eval)
    // indexed by a pawn-structure hash, and add it to the eval used for
    // PRUNING decisions. The RAW eval is still what goes into the TT, so the
    // correction can never compound through TT reuse. This is a NEW signal
    // derived from the search's own verdicts, not a constant retune, not an
    // eval-parameter refit and not an accuracy-gated change: it is judged by
    // FIXED-TIME games only. Frozen in docs/DEV6_PREREG_EXP0050.md.
    bool correctionHistory = false;
    // --- dev6 exp-0064 (default off; isolated same-binary ablation) ---------
    // Extension-agnostic main-TT identity. The shipped TT keys entries on
    // (key, rule50, historyContext, extensions), where `extensions` is the
    // per-path check-extension BUDGET counter, not part of the position, the
    // draw rules or mate normalisation. Because it is mixed into the bucket
    // index, an identical position reached with a different remaining budget is
    // unreachable: measured 2.7-4.6% of all probes at depths 5-9 (see
    // benchmarks/recovery/exp0064_tt_identity_diagnostic.json). With this switch
    // ON the main TT is probed AND stored with extension argument 0, so the
    // identity is (key, rule50, historyContext). rule50 and historyContext stay
    // in the key, so repetition/draw soundness is unchanged. No new evaluate,
    // SEE, movegen or verification work. Frozen in docs/DEV6_PREREG_EXP0064.md.
    bool ttExtensionAgnostic = false;
    // --- dev6 exp-0065 (default off; isolated same-binary ablation) ---------
    // Persistent cross-move quiet history. Shipped behaviour zeroes history_ at
    // the start of EVERY root search (search.cpp run()) AND builds a fresh
    // Search per `go` (uci.cpp), so the primary quiet-ordering table never
    // learns anything across moves: at 40+4 ms that is only ~10-30k nodes of
    // training per move, discarded each time. With this switch ON the table is
    // carried over and HALVED (bounded forgetting) instead of zeroed, and the
    // UCI engine keeps one Search alive until `ucinewgame`. Killers stay cleared
    // (ply/position-local); counter-move, continuation, capture, correction and
    // qsearch tables are untouched, so an effect is attributable to ONE table.
    // Frozen in docs/DEV6_PREREG_EXP0065.md.
    bool persistentHistory = false;
    // --- dev6 exp-0066 (default off; single-factor lifetime ablation) -------
    // continuation_ is a GRADED statistic accumulated by +-depth^2, yet run()
    // zeroes it on EVERY root search (search.cpp) and UCI destroys the Search
    // after every `go`. At 40+4 ms it is trained on one move of data and then
    // thrown away. With this switch ON the table is carried across searches and
    // HALVED (bounded forgetting) instead of zeroed, and UCI keeps one Search
    // alive until ucinewgame or a configuration change. The feature switch
    // ContinuationHistory must ALSO be on for anything to be written; the
    // frozen experiment enables it in BOTH arms so lifetime is the only factor.
    // counterMoves_ is deliberately NOT persisted: it is a categorical
    // single-move reply table that saturates after one write.
    // Frozen in docs/DEV6_PREREG_EXP0066.md.
    bool persistentContinuation = false;
};

// exp-0064: the single source of truth for the main-TT identity's extension
// argument, shared by the probe and the store so the two can never drift apart.
// A free function so the correctness tests can exercise it directly.
inline int tt_identity_extensions(bool agnostic, int extensions) {
    return agnostic ? 0 : extensions;
}

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
    void score_moves(const Position& pos, MoveList& moves, Move hashMove, int ply,
                   bool mainSearch);
    int next_move(MoveList& moves, int index);
    void update_pv(int ply, Move move);
    bool quiet(const Position& pos, Move move) const;
    bool gives_check(Position& pos, Move move);
    Move previous_move(int ply) const { return ply > 0 ? moveStack_[ply - 1] : MOVE_NONE; }
    // Row `ply` of the triangular principal-variation buffer.
    Move* pv_row(int ply) { return pv_.get() + std::size_t(ply) * MAX_PLY; }
    const Move* pv_row(int ply) const { return pv_.get() + std::size_t(ply) * MAX_PLY; }
    // Continuation history: how good `move` has been after a given previous
    // move. Kept for one ply of context, which is the variant that pays for
    // itself without a large table.
    int& continuation(PieceType previousType, Square previousTo, PieceType type, Square to) {
        return continuation_[(((std::size_t(previousType) * SQ_NB + std::size_t(previousTo)) *
                              PieceTypeNB + std::size_t(type)) * SQ_NB) + std::size_t(to)];
    }
    // exp-0050 correction history. `correction_index` hashes ONLY the pawn
    // structure (both colours' pawn bitboards) so the learned bias generalises
    // across piece placements. `correction_of` is the current scaled estimate.
    std::size_t correction_index(const Position& pos, Color us) const;
    void update_correction(const Position& pos, Color us, int staticEval,
                           int best, int depth);
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
    // exp-0043: number of singular extensions active on the CURRENT path.
    // Incremented around the extended child and decremented on return, so the
    // cap is path-scoped without changing negamax's signature or TT context.
    int singularExtensions_ = 0;
    std::uint64_t nodes_ = 0;
    int selDepth_ = 0;
    Key rootContextSalt_ = 0;
    // The two largest tables are heap-allocated. Inline, they make a Search
    // object about a megabyte, which overflows the 1 MiB default stack on
    // Windows as soon as two searches exist at once; they are also far too big
    // to copy around, and the search never copies them.
    static constexpr std::size_t PvSlots = std::size_t(MAX_PLY) * MAX_PLY;
    static constexpr std::size_t ContinuationSlots =
        std::size_t(PieceTypeNB) * SQ_NB * PieceTypeNB * SQ_NB;
    // exp-0050: pawn-structure correction table, power of two so the index is a
    // mask. One entry per (colour, pawn hash); scaled centipawns.
    static constexpr std::size_t CorrectionSlots = 16384;
    // Static evaluation of the position at each ply of the current line, so the
    // "improving" heuristic can compare against two plies ago without threading
    // another parameter through every call.
    int evalStack_[MAX_PLY + 2] = {};
    std::unique_ptr<Move[]> pv_{new Move[PvSlots]()};
    std::unique_ptr<int[]> continuation_{new int[ContinuationSlots]()};
    std::unique_ptr<int[]> correction_{new int[CorrectionSlots * ColorNB]()};
    int pvLength_[MAX_PLY] = {};
    Move killers_[MAX_PLY][2] = {};
    int history_[ColorNB][SQ_NB][SQ_NB] = {};
    // Reply table: the move that most often refuted `previous`. Indexed by the
    // previous move's piece and destination square.
    Move counterMoves_[PieceNB][SQ_NB] = {};
    int captureHistory_[PieceTypeNB][SQ_NB][PieceTypeNB] = {};
    // The moves played along the current line, so ordering can see the previous
    // move without threading an extra parameter through every call.
    Move moveStack_[MAX_PLY + 2] = {};
    std::vector<std::vector<Move>> pvLines_;

    // exp-0038: a small dedicated direct-mapped qsearch transposition table.
    // Kept separate from the main TT so shallow qsearch entries can never
    // evict deep main-search entries or leak a VALUE_NONE static eval into
    // `ttEval` reuse. Mate scores are normalised by ply and never stored.
    struct QCacheEntry {
        Key key = 0;
        std::uint64_t rule50 = 0;
        Key context = 0;
        std::int16_t value = 0;
        std::int8_t bound = 0;  // 0 none, 1 exact, 2 lower, 3 upper
    };
    static constexpr std::size_t QCacheSlots = std::size_t(1) << 16;
    std::unique_ptr<QCacheEntry[]> qcache_{new QCacheEntry[QCacheSlots]()};
    QCacheEntry* qslot(Key key, std::uint64_t rule50, Key context) {
        Key h = key ^ context ^ (Key(rule50) * 0x9E3779B97F4A7C15ULL);
        h ^= h >> 33;
        h *= 0xFF51AFD7ED558CCDULL;
        h ^= h >> 29;
        return &qcache_[std::size_t(h) & (QCacheSlots - 1)];
    }

    struct RootMove {
        Move move = MOVE_NONE;
        int score = -VALUE_INFINITE;
    };
    std::vector<RootMove> rootMoves_;
};

// A Search instance sits on the caller's stack in the tests and in the CLI, and
// two of them must fit inside the 1 MiB default thread stack that Windows uses
// (Linux gives 8 MiB, which is why an inline 0.9 MB object went unnoticed until
// a Windows CI run segfaulted). Keep this bound honest when adding tables.
static_assert(sizeof(Search) <= 64 * 1024, "Search must stay small enough for a 1 MiB stack");
}
