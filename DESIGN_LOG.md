# Design log (append-only)

## 2026-10-30 — independent engine baseline

- The repository initially contained only the Apache-2.0 license. Keep that license; implement the engine rather than importing an existing engine.
- Use a mailbox plus per-type/per-color bitboards, generated magic slider tables, owned per-ply state and reversible incremental updates. Detect legality by checks/pins and post-en-passant king safety. Preserve raw FEN EP separately from legally relevant EP in repetition keys.
- Use single-threaded iterative-deepening alpha-beta/PVS and quiescence before considering speculative pruning. Check extensions are capped. Context-sensitive TT tags include the known reversible path, rule-50 count, root boundary and extension budget; this is conservative for draw correctness and intentionally sacrifices some cross-path TT hits.
- Choose independently derived, tapered handcrafted features rather than a fake or untrained neural-network claim. Do not add NNUE/MCTS/training scaffolding without implementation and evidence.
- Keep UCI input on the main thread and one search on a joinable worker. Stop is atomic; every state-changing command joins first. Bound time/node/hash usage and preserve a legal root fallback.
- Distinguish claimable versus automatic draw status, including intended-move claims. Search deliberately assumes claims and treats internal cycles as draws; the GUI/referee owns actual game adjudication. Recognize common dead-material signatures but document that arbitrary blocked dead positions are not fully solved.
- Make the C++ executable self-contained apart from OS runtime libraries; Python and python-chess are optional development tools. Keep external opponents outside the repository and do not use them for engine search.
- Record perft/search/match methodology and actual results under the versioned benchmark directory. Perft uses leaf bulk counting, so its NPS must not be compared to search NPS.

## 2026-10-31 — dev2: general dead positions, stronger search, honest statistics

- **Dead positions must be decided, not guessed.** Article 5.2.2 quantifies over
  *all* legal move series, so material signatures are only a subset and the
  "obvious" generalisations are wrong in both directions (`KNN` v `K` and
  `KB` v `KN` are alive; 14 blocked pawns and locked pawn chains with bishops are
  dead). Deciding `mate_reachable` is PSPACE-complete, so the only honest design
  is an exact procedure with an explicit resource bound: prove `Dead` by
  enumerating the complete reachable state component, prove `Alive` with a legal
  checkmate witness, and answer `Unknown` when either budget runs out. This is
  the architecture used by published helpmate analysers, and it satisfies the
  requirement without pretending to a polynomial algorithm.
- **128-bit state identity.** A single Zobrist key is not enough: the en-passant
  square and castling rights must be part of identity, and a collision could hide
  a mate and thereby *prove* a false deadness. Every enumerated state therefore
  carries the Zobrist key plus an independent mix of placement, side, castling
  rights and en-passant square. Collisions can then only cost a missed analysis,
  never correctness.
- **Adjudication and search stay separate.** The search keeps the cheap, sound,
  incomplete `insufficient_material()` predicate; only `draw_status()` and the
  `deadpos` CLI call the exact analysis, and only a proved verdict can produce
  `AutomaticDeadPosition`. This keeps search strength independent of an
  exponential analysis.
- **Search features are switches, not lore.** Every pruning/reduction feature is
  a `SearchParams` flag, exposed through `bench --param` and through UCI check
  options, so a decision can be re-measured by nodes *and* by matches. Node
  ablations are explicitly treated as insufficient evidence where disabling a
  feature shrinks the tree for ordering reasons (null move, reverse futility,
  check extension); those features are justified only by the aggregate match.
- **Statistics must show dependence.** Two games of one opening are correlated,
  so the paired pentanomial estimate (pair score in {0, 0.5, 1, 1.5, 2}) is the
  headline number, the naive Wilson interval is kept only for reference, SPRT is
  labelled an approximation, and every Elo figure carries an interval and a
  sample size. Capped games remain `unadjudicated` and are excluded from scores;
  time forfeits and illegal moves are losses for the offender.
- **No invented external opponent.** Stockfish 19 cannot be built without NNUE
  network files that this environment cannot fetch, so the release records that
  fact and uses a pinned, checksummed Stockfish 11 built from source instead of
  claiming a Stockfish 19 result. The 0–20 outcome is reported as a loss.
- **Trust no match without a provenance check.** The first dev2-vs-dev1 run was
  discarded because it overlapped compilation and produced mass clock forfeits;
  the recorded run was made on an idle machine with a verified engine identity
  line and a clean termination distribution.

## 2026-10-31 — corrections after review of the dev2 head

- **Static exchange evaluation had a fold bug.** The negamax fold stopped one
  recapture too early (`while (--d > 0)` instead of `while (d-- > 0)`), so a knight
  capturing a pawn defended by a pawn returned +100 instead of −220. That both
  mis-ordered losing captures and fed the SEE pruning rule a false "win", so part
  of the earlier dev2 gain was an artefact of a broken SEE. It is now a free
  function `static_exchange_evaluation()` with hand-checked unit tests
  (knight × defended pawn = −220, pawn × defended pawn = −100, equal trade = 0,
  losing capture ≤ −depth). Every number in this release was measured after the
  fix: the sign of the result did not change, the size did.
- **Correcting the collision claim above.** The dev2 entry says a transposition
  collision "can then only cost a missed analysis, never correctness". That is too
  strong: within the dead-position enumeration a collision can *skip* a state and
  thereby hide a mate, which would turn `Alive` into a wrong `Dead`. What the 128-bit
  mixed key buys is a negligible probability — the birthday bound over a full
  enumeration is about 2^-77 at the 50,000,000-state hard maximum (2^-65 at 2^32
  states) — not immunity. `docs/DEAD_POSITIONS.md` states the bound and the
  residual risk explicitly.
- **Dead-position cost reporting.** `DeadResult` now separates `states` (distinct
  states reached) from `expanded` (move applications charged against the budget),
  because the two differ by up to 6.6× on the locked-pawn-with-bishops component
  and only the second one bounds runtime. `bench`/`deadpos` print both.
