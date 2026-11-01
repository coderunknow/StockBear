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

## 2026-11-01 — static exchange values and the king

- **A king cannot recapture into an attacked square, but SEE thought it could.**
  `SeeValue[King]` was 0. In `4k3/3p4/8/8/8/8/3R4/3R2K1 w - - 0 1`, `d2d7` is a
  won pawn because the king may not take back while the second rook x-rays d7, yet
  SEE scored it −400 (king "recaptures" for 0, then the rook falls). A zero value
  for the king also made it the least valuable attacker, so it was picked first.
  The king now carries a dominant value (20,000), which keeps it last in the
  least-valuable-attacker order and makes any line in which it captures look
  catastrophic, so SEE never reads an illegal king recapture as a gain. Covered by
  a known-value test.
- **Consequence for measurement.** SEE feeds both move ordering and the SEE
  pruning rule, so this is a real playing-strength change, not a cosmetic one. The
  dev2 benchmarks and both matches were re-run after the fix and the earlier
  numbers are superseded (the report keeps them, labelled, as discarded
  measurements). Node counts move slightly (106,558 → 108,910 at depth 6); the
  match result moves from +250 =103 −47 to +277 =82 −41, which is the same
  conclusion with a different magnitude.

## 2026-11-01 — dev3: search switches, real MultiPV, and a tuning result that did not ship

- **Search rewrite with per-feature switches.** All pruning and ordering
  decisions moved into `SearchParams`, so a feature can be ablated by
  `bench --param name=0` or by a UCI option. With every dev3 switch off the
  bench signatures are exactly dev2's (`e06c4352681ae8eb` at depth 6,
  `5bceff035f2a4ae4` at depth 7), which is the evidence that the rewrite is
  behaviour-preserving for single-PV search rather than "close enough".
- **Root search and MultiPV.** `search_root` now takes a PV slot index and
  re-runs the root with the already reported moves excluded. Within a pass the
  root list is selection-sorted, and the move that improved alpha is swapped into
  the slot it is reported from; without that swap the reported move could be one
  that did not produce the reported score, which is exactly the inconsistency that
  made an earlier version of this rewrite disagree with dev2 in the bench.
  MultiPV deliberately disables aspiration windows: a band tuned around the first
  line would bias the exact scores the ranking depends on.
- **Ordering features are neutral here, and are documented that way.** Counter
  moves, continuation history, capture history, history maluses and a
  history-adjusted LMR were implemented, unit-tested and matched. At depth 7 they
  cost about 2 % more nodes (255,021 versus 250,053) and 8 % more time. Two
  paired matches measured them: all five on scored +1.3 Elo [−17.9, +20.5] over
  571 decided games against the rebuilt dev2 binary, and the
  history-malus/LMR/continuation subset scored −16.2 Elo [−33.0, +0.5] over 600
  decided games against the same binary with those switches off. Neither is an
  improvement, so they default **off** and the shipped search is behaviourally
  dev2's. They ship as switches rather than being deleted, because deleting them
  would also delete the evidence and make a future re-measurement impossible.
- **Evaluation parameters became data, then stayed the same.** The evaluation is
  linear in a 32-entry parameter table, so `stockbear evaldata` can hand the
  offline tuner an exact design matrix. Three candidate sets were fitted to 2,000
  self-play games (75,416 positions, split by game) and measured with one binary
  on both sides, so the search was identical and only the evaluation differed:
  −119.1 [−140.8, −98.2], −51.3 [−72.1, −30.8] and +12.0 [−10.3, +34.4] Elo
  against the shipped evaluation. The candidate with the best holdout loss was
  the worst in play. The release keeps the dev2 values; `docs/TUNING.md` records
  the pipeline, the dataset hashes, the three sets and the matches, and explains
  what a future attempt should do differently (engine-independent labels, a
  pruning scale separated from the evaluation scale, validation at a time control).
- **A won endgame can still be shuffled into a draw.** At 400 k nodes the engine
  converts 22 of 24 constructed KQK/KRK positions and mates with a proved mate in
  every tactical position, but two conversions reached a repetition claim: the
  winning side allowed the second repetition, which lets the defender claim the
  third. The search scores a repetition as a draw only once it is claimable, and
  from a distance the winning side has no way to see that the shuffle is losing.
  This is a known limitation of a tablebase-free engine, recorded in the report
  instead of being papered over; the fix is a fifty-move/progress term, which is
  deliberately *not* in this release because it was not validated.

- **Advertised defaults come from the configuration, not from a literal.** The
  `uci` handshake used to print `default true` for every check option. Once a
  default changed, that string was a lie that no test could catch, because it was
  a constant next to a different constant. The handshake now formats the live
  `SearchParams` value, so the advertisement cannot drift from the behaviour; the
  integration test still only checks the shape of the line, because what matters
  is that the engine does what it prints.
- **A rejected `position` command leaves the previous position searchable.** An
  invalid FEN (for example one where the side not to move is in check) is
  reported and ignored rather than half-applied, so a GUI that sends a bad
  position does not silently get a search of a board it did not ask for. Testing
  this needed the *previous* position's legal move list to compare against, which
  is also how the earlier `7k/8/8/8/8/8/8/K6Q w - - 0 1` FEN was found to be
  illegal (the queen on h1 checks the king on h8 with White to move) instead of
  an engine bug.

- **A Windows-only segfault in the new tests was a stack-size bug, not a
  MultiPV bug.** `Search` held its triangular PV buffer and continuation-history
  table inline, which made one instance about 0.9 MB. Linux hands a thread 8 MiB
  of stack, Windows 1 MiB, and the MultiPV equivalence test holds two searches at
  once, so it died on Windows in both Debug and Release while passing under ASan
  on Linux. The tables now live on the heap, a `Search` is 50 KB, and a
  `static_assert` caps it at 64 KB. This is the kind of bug that only a
  cross-platform CI run finds; it is recorded here because "it passes locally"
  was true and misleading.
- **The tuning pipeline found no improvement, in three different directions.**
  Aggressive (A), moderate (B) and conservative (C) fits all failed their
  matches, and a fourth fit bounded to a 20 % movement from the shipped values
  changed nothing at all. The useful conclusion is not "tuning does not work" but
  "this objective on this data cannot distinguish these sets", which is why the
  release states the negative result and keeps the coefficients it inherited
  rather than shipping a set on the strength of its holdout loss.
