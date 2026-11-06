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

- **Correction to the entry above about bench signatures.** "With every switch off
  the bench signatures are exactly dev2's" is true, but it is a statement about
  the twelve benchmark positions, not about the whole search. The review fix that
  makes a null move clear the `moveStack_` slot (the child of a null move was
  ordering its quiets against a stale previous move) leaves both signatures
  unchanged and still changes play: the two three-man endgames that had been
  shuffled into a claimable repetition (`kqk-12`, `krk-17`) now mate, and the
  endgame suite went from 22/24 to 24/24 at the same node budget. A deterministic
  fingerprint of a fixed suite is a regression guard, not a proof of behavioural
  identity, and the release documents now say so.
- **Matched configurations must be recorded, not reconstructed.** The first dev3
  search matches recorded only the effective options that the harness had been
  given, and the *defaults* those options were competing against changed during
  the release. Both matches were therefore replayed with every switch set
  explicitly on both sides, and the harness now writes each engine's advertised
  defaults into the record's `configuration` line. A result whose configuration
  cannot be read out of its own evidence file is not a result.

- **The corrected oracle narrowed the tactics suite, and that is the point of
  having one.** With mate distances counted per ply, the oracle no longer accepts
  a mate in five for a position labelled "mate in three". Regenerating the suite
  dropped one position (its own game move turned out to be a slower mate) and
  shrank most accepted-move sets — `mate02-3ply` went from 31 accepted moves to 7.
  The earlier 26/26 was measured against the looser sets, so the release reports
  25/25 on the strict suite and says plainly that the two numbers are not
  comparable. A suite is only as strong as the oracle that certifies it, and this
  is what it looks like when the oracle gets stricter.

## 2026-11-02 — dev4: neural evaluation, measured and not shipped

- **A learned evaluation was built to be measured, not to be assumed.** Every
  piece — feature function, incremental accumulator, quantised format, scalar and
  AVX2 kernels, self-play generator, trainer, quantiser, verifier — is original
  code in this repository; no third-party weights, data or engine code. The
  release still ships the classical evaluation, because the network **lost 708
  Elo** (95 % CI [−1011, −405]) against it at 2,500 nodes per move. Shipping it
  would have been a strength regression dressed as a feature.
- **The input ordering is part of the network's contract, and getting it wrong is
  silent.** With the two perspectives ordered by *colour* instead of
  *side-to-move-first*, the same board maps to the same input with opposite
  targets. The best fit is the constant 0.5, which is exactly what every
  configuration converged to, at every learning rate, while passing every
  structural test. Measured: correlation of colour-ordered material with the
  side-to-move result −0.0003, of side-to-move material with the same target
  +0.572. The ordering is now documented in `nnue_forward.hpp` and pinned by a
  unit test that constructs the expected forward value both ways.
- **Truncating shifts bias the evaluation downward.** `x >> shift` rounds towards
  −∞; summed over a 128-wide layer this shrank the score by ~4 % relative to the
  float network. Both kernels and the reference now round. Separately, calibrating
  the activation range to the maximum leaves the typical activation using ~7 of
  128 integer levels; a 99.9th-percentile range took the integer-vs-float error
  from 16.2 to 11.7 cp rms by letting outliers saturate instead.
- **Fixed-node matches carry no information unless the node budget is jittered.**
  Play at a fixed node budget is deterministic, so both games of a colour-reversed
  pair are identical and every pair scores 1.0: the pentanomial has zero variance
  and the harness correctly refuses to report an interval. A 60-game control match
  of one binary against itself returned `[0, 0, 30, 0, 0]`. The fix is a seeded
  per-move node jitter (±12 % for experiments) plus a 240-opening random suite, so
  the pair scores spread and the clustered interval has 120 clusters.
- **A single fixed-time match can produce a confident false positive.** Two builds
  that play *bit-identically* at a fixed node budget (same signatures, same node
  counts, same per-game records) produced +29.0 [+1.5, +56.9] for one of them at
  40 ms + 4 ms, while the same binary against itself measured −30.5 in that
  control. The scheduler, not the engine, produced the effect. Fixed-time numbers
  in this release are therefore labelled inconclusive unless they are far larger
  than ~65 Elo or also appear at fixed nodes.
- **Every new search feature measured neutral or negative**, and each was measured
  against the same binary with a null control: ModernLMR −29/−31, MoveCountPruning
  −39/−104, IIR −15/+7, Improving −26/−13, TTEval a verified no-op. dev3's search
  is at a local optimum for its evaluation; the next gain has to come from the
  evaluation, not from more pruning heuristics on top.
- **Rejected on verifiability, not on merit:** SMP (one physical core here — a
  `Threads` option could not be validated, so it is not advertised at all),
  tablebases and an opening book (data/provenance burden, and a book hides search
  weakness), singular extensions and ProbCut (no compute left to validate a
  high-regression-risk change honestly).
- **Counts must come from the tree, not from memory.** The dev3 notes said the
  `unit` group had 37 tests; `git grep "TEST(unit," 32e7d9d -- tests` gives 39.
  `docs/TESTING.md` now states the count as a property of the tree, and the dev4
  report records the recount rather than silently editing history.

## 2026-11-02 — dev5 research begins (not a release)

- Reproduced the exact dev4 tag; CTest 11/11, depth-6 signature unchanged.
- Found historical NNUE artifact hash discrepancy. Verified actual committed
  bytes against independent integer evaluation on 75,416 positions. Preserve
  historical reports and record the discrepancy in DEV5_EVALUATION_DIAGNOSIS.
- Isolate pawn-safe mobility behind default-OFF CMake research flag; independent
  feature oracle and focused unit test, no default strength claim.
- Extend batch feature generation for existing king buckets, not an end-to-end
  trained HalfKP implementation. Do not reinterpret old model features.
- Add binary/opening/explicit evaluator-input hashes to future match records.
  Fixed-node screening is exploratory; practical strength requires fixed time.

## 2026-11-03 — dev6 (v0.1.0-dev6) research cycle: baseline = released dev5

Working branch `arena/3e6dd5b6-stockbear` (this session's fixed research branch;
the toolchain fixes the branch name, so it IS the dedicated dev6 branch). Starting
main SHA `6e7c2e02881faf93a84990a8345c41ad28bcae11`. **All older "dev6"/"dev7"
docs and exp-0016/0017 measured against dev4 during the dev5 cycle on a different
branch — they are historical and cannot satisfy the dev6 gate.** The dev6 gate is
+75 Elo with LCB95 > +50 against the EXACT released v0.1.0-dev5 portable artifact.

- **Immutable baseline provenance (exp-0025).** The sandbox cannot reach the
  release-asset CDN; a free GitHub-hosted runner downloaded the official dev5
  archives, verified them against the published SHA256SUMS.txt, and pinned the
  exact Linux executable `benchmarks/binaries/stockbear-dev5-release`
  (SHA-256 `391cb50e…`, bench `243f9a1c1ba5b36f` / d16 `a14ab62224f837e5`,
  UCI `0.1.0-dev5`, flags `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`).
  Shipped `params_abc.txt` SHA equals the repo champion file SHA
  (`8a9dc81f…`), confirming the champion config of the published +64.7 claim.
  Recorded in `benchmarks/dev6-baseline/manifest.json`, `docs/DEV6_PREREG_BASELINE.md`.
- **Eval audit finding (exp-0026).** Of the four shipped "exp-0022" extended ids,
  only `RookOn7th` and `KnightOutpost` were ever computed; `BackwardPawn` and
  `PawnChain` were dead rows (declared but never counted). The default-off
  incremental path maintained none of them.
- **Design decision.** Implement all six extended features (the four existing +
  two new: `ConnectedPassed`, `RookBehindPassed`) in ONE shared helper
  `extended_counts(p, us)` used by `features()`, `accumulate_breakdown()` and the
  incremental path — so live eval and offline breakdown cannot diverge. Append
  the two new ids (append-only table). Ship all six at value 0 so the default
  build stays bit-exact (bench signatures unchanged) AND gate the whole routine
  behind an "any extended param non-zero" flag, so the champion/default config
  pays zero extra per-node cost. This protects the cp-margin/NPS regime the
  Failure Ledger identifies as decisive at 40+4 ms.
- **Correctness.** Shared-helper guarantee + perturbed-parameter mirror test;
  new unit test with hand-verifiable counts and gating; an INDEPENDENT
  python-chess reference (`scripts/check_dev6_eval_features.py`) over a fixed
  600-position corpus (43,200 feature checks, 0 mismatches); `evaldata --check`
  600/600; ctest 11/11; exact portable `-flto=4` build reproduces both bench
  signatures. Cost measured: ~13% of the combined (breakdown+evaluate) loop
  when enabled, zero when gated off.
- **Noise-minimised decisive design (exp-0027/0028/0029, pre-registered).**
  Primary estimator opening-clustered CR1 / Student-t; 40+4 ms, hash 16, 1
  thread; exact dev5 binary at champion options; two FRESH disjoint suites of
  3300 distinct paired openings each (verified disjoint from each other and all
  historical suites), split into 6 immutable slices of 550 so a 1100-game shard
  uses every opening exactly once (no repeats within a batch); 13200 decisive
  games + 2200 null games + screens; distinct seeds; symmetric pre-declared
  forfeit/crash/illegal/max-ply handling. Power analysis from exp-0024 raw
  records (`docs/DEV6_POWER_ANALYSIS.md`): combined half-width ~5 Elo at +75.
- **Version discipline.** VERSION -> `0.1.0-dev6` on the research branch; no
  dev5 tag/release touched; no dev7; no merge/tag/release/PR while the gate is
  unmet (explicit user approval required for those).

### dev6 decisive results (2026-11-03, appended)

exp-0028/0029 ran 2 x 6600 games on two verified-disjoint 3300-opening suites;
combined **−17.0 [−21.4, −12.6] Elo** vs exact released dev5 — a clear
REGRESSION, gate decisively unmet. Nulls clean. The integrity control
(`params_abc`, +33.0 [+13.7,+52.5]) exposed a toolchain confound: dev5 was
built on ubuntu-22.04, the candidate on ubuntu-latest/GCC 13; local same-machine
bench shows my source changes are ~1.015x NPS (negligible), so the +33 is a
build-image effect and/or screen noise, NOT a strength gain and NOT caused by my
code. Confound-free ablation (same suite/binary/baseline, params_abc ->
params_dev6_a) = ≈ −58 Elo: the features themselves are harmful. Design lesson
to carry forward: pin BOTH sides to ONE reproducible build toolchain and verify
binary-level NPS equivalence before any fixed-time comparison; do not treat a
different-image rebuild as a neutral candidate. Direction ABANDONED per the
Failure Ledger; next work must start from M0 (measured external rating) then a
materially different, correctness-verified evaluator. See docs/DEV6_REPORT.md.

## M0 measurement foundation + first post-M0 isolated direction (superseding status note)

The six-feature direction remains ABANDONED (documented above). Subsequent work:

1. **Toolchain control (exp-0030).** Rebuilt dev5 and candidate in ONE pinned
   GCC 12.2.0 / `-flto=4` environment, kept the official artifact immutable.
   Bit-exact fixed-node behaviour and NPS within 3 % prove Track A is valid;
   the +33 Elo control was an ubuntu-22.04-vs-24.04 build-image artifact. Any
   future fixed-time comparison must use identical toolchains AND isolated
   runners (local 2-vCPU clock noise: 5 forfeits in 400 games).
2. **External ladder (exp-0031/0032).** Built SF8-SF11 + Weiss 2.0 from official
   source archives (no blocked CDN, no NNUE weights), SHA-pinned everything,
   used fixed-node `go nodes 6000` to remove clock noise, and fitted a
   draw-aware BTD model. Design lesson learned the hard way: assigning a
   **different opening slice to each cell** confounds all cross-cell ratings.
   exp-0032b (one shared opening set for all subjects) reversed the star
   ladder's subject ordering — so the star ladder's subject ordering must NOT
   be used. Next ladder MUST use a shared paired opening set and >= ~1,000
   games/pairing. Rating is pool-specific INTERNAL; never equate fixed-node
   with fixed-time Elo (dev5 vs dev4: +12.2 fixed-node vs +64.7 fixed-time).
3. **exp-0033 razoring.** `SearchParams::razoring` was declared but
   unimplemented/unexposed — a genuinely unmeasured direction, not a repeat.
   Implemented as a default-off UCI switch on ONE binary so the ablation has
   zero toolchain confound. Prereg `docs/DEV6_PREREG_EXP0033.md`. Efficiency
   result is mixed and reported honestly. No gate weakened.

## exp-0033 rejected, exp-0034 pilot advance (design lessons)

Razoring at depth <= 3 with qsearch verification is harmful (-25.88 Elo): the
qsearch probe is pure overhead whenever a capture rescues the stand-pat, and
returning a qsearch bound perturbs TT/PV at the shallow depths that dominate a
6,000-node search. Do NOT re-tune its margin. The productive successor prunes
INDIVIDUAL losing captures using SEE already computed in `score_moves()` —
-11.29 % fixed-depth nodes, +20.49 [+2.12,+38.97] in an 800-game fixed-node
pilot with all correctness checks passing. Both new switches are default-OFF
UCI checks on ONE binary, giving a zero-toolchain-confound ablation; default
builds remain bit-identical to dev5. Two harness defects (missing
`pair_openings`, unadjudicated `None` pairs) were found, disclosed and fixed —
a reminder that result-processing code needs the same prereg-level care as
search code. No gate is weakened; a pilot advance is not a strength claim.

## exp-0035 confirmed (fixed-node) — what is and is not established

A ~+27 Elo fixed-node improvement from SEE-based bad-capture pruning is now
reproducible across two disjoint 1,000-game batches with a same-binary,
single-switch control, plus a ~+19 Elo (CI includes 0) check against an
identical-toolchain dev5 rebuild. That is a real, isolated, audited effect at
`go nodes 6000` on this hardware. It is NOT transferable to a fixed-time Elo
claim: exp-0030 documented 5 TIME_FORFEIT events and +/-25 Elo of shared-clock
noise on this 2-vCPU sandbox, and the historical +33 Elo "gain" was a build
image artifact. Keep the switch default OFF until isolated-runner fixed-time
confirmation; changing the default would alter the shipped bench signature and
require a fresh artifact/CI cycle. No gate weakened.

### exp-0036 / post-authorization (2026-11-04)
- Kept `docs/DEV6_PREREG.md` §8 unchanged. Added a pre-registered RUNNER
  VALIDITY GATE (0 forfeits + null includes 0 + NPS ratio in [0.97,1.03])
  before any fixed-time match, so a shared-clock environment cannot silently
  produce a fabricated strength result.
- Added a frozen futility boundary (combined 95 % UCB < +50) to stop a
  confirmation cheaply. It is an experiment-level stopping rule, NOT a gate
  weakening:Gate 1 still requires point >= +75 AND LCB > +50.
- Fixed-time confirmation used `--base-ms 40 --inc-ms 4` with NO `--nodes`;
  fixed-node exp-0035 (+27.10) and fixed-time exp-0036 (+21.52) are recorded
  as different quantities. Neither is a gate pass or an absolute Elo.
- Recorded the lane's `commit_and_push` as a hard authorization boundary:
  no `workflow_dispatch`, no `main` copy, results pushed back -> a second push
  would be required. No second push was made.
- Next isolated direction ranked: ProbCut > quiescence TT probe > endgame eval
  knowledge > NNUE-with-accuracy-link > stacking (separate prereg only).

### Tier-1 lane redesign (2026-11-04)
Root cause of the previous blocker: `dev6-lane.yml` was push-triggered via a
`dev6-trigger.json` path filter, had no `workflow_dispatch`, and its shell
script called `commit_and_push()` — so every experiment required an extra
remote write AND produced further automatic remote writes, while the results
channel was git because the artifact blob CDN is unreachable from the sandbox.
Redesign: a separate `workflow_dispatch`-only workflow with a pinned
`source_sha` input, one isolated `ubuntu-latest` VM per matrix job, zero
benchmark-time pushes, complete artifact bundles with SHA-256 manifests, and
a DELIBERATE opt-in `mode=export` job that mirrors the artifacts into one git
commit. The latter is the artifact-access contingency: both the job-logs and
artifact-zip API endpoints 302 to the blocked blob host, but `git` and the
`api.github.com` Contents endpoint are reachable, so exporting artifacts to
the branch makes them independently downloadable and verifiable. Retries are
safe because every condition derives from the pinned source SHA and the frozen
plan inside that commit; a fingerprint hash is written per job.

### exp-0037 ProbCut (design, before results)
Implemented exactly to the frozen prereg: single default-off UCI switch,
raised-beta (`beta + 200 cp`) null-window search at `depth - 4` for non-PV
nodes with `depth >= 5`, no mate window; on a fail-high the whole move loop is
skipped. Kept the TT replacement policy unchanged (it is depth-preferred, so
shallower ProbCut stores cannot evict much deeper current-search entries), and
guarded PV/mate so proven values are untouched. Pre-result diagnostics are
deliberately ambiguous and recorded: startpos depth 12 `ProbCut=true` used
888,947 nodes vs 543,800 OFF (+63 %, overhead dominates shallow), while the
12-position depth-16 bench used 156,640,123 vs 170,160,152 (-7.96 %, cutoffs
pay off deeper). That conflict is exactly why the preregistered screen is run
instead of assuming the direction works. No margin/depth tuning on results.

### exp-0037 closed — diagnosis that informs exp-0038
The decisive variable at 40+4 ms is nodes-per-move, not nominal depth. Any
mechanism that must spend a subtree-sized verification search before it can
save a subtree is net-negative when the whole move budget is ~4 ms. That
generalises: NPS / per-node cost reductions and pruning that fires on CHEAP
information (SEE already computed, TT already probed) are the viable family;
expensive predictive probes are not. This is why exp-0038 targets qsearch TT
integration (reuse of information already resident in the table) rather than
another predictive search. Also confirmed: a frozen futility/advance rule
closed a weak-positive direction cheaply without weakening any gate.

### exp-0038 design decision (registered before results)

exp-0037's root cause was that a verification subtree must be SPENT before
any saving can be realised, which is fatal at a 4 ms increment. The next
direction therefore reuses already-computed information instead: a qsearch
transposition table. To avoid the known TT-eval sentinel hazard (`VALUE_NONE`
cast into `int16_t`, and `store`'s stale-eval branch) the qsearch cache is a
separate structure, never the main TT. Bounds are stored against the original
window; only lower>=beta and upper<=alpha cuts are allowed; mate values are
excluded. The 2 MB direct-mapped cache is cleared once per `go`, not per
iteration, so hits can accumulate across iterative deepening.

Instrumented profiling found the surprising failure mode: the cache hits a
lot, but almost exclusively at nodes that would already have returned at
stand-pat or delta pruning, so it buys almost no nodes and costs a probe plus
a store at every qsearch node. Fixed-node proxies are explicitly recorded as
misleading in this project's ledger; therefore exp-0038 is decided by a real
Tier-1 fixed-time screen, not by the proxy. If it closes as inert, do NOT
retune the cache size or hash; record the mechanism diagnosis and move to a
direction that changes which NODES are searched rather than how cheaply
already-cheap nodes are revisited.

### exp-0039 (eliminated at profiling, never benchmarked)

Inspection of `negamax` found a genuine dead-computation defect: with the
champion `TTEval=true`, `int staticEval = evaluate(pos);` runs at every node
and is then unconditionally overwritten by `int(entry->eval)` on a TT hit
(the `int16_t` sentinel comparison `entry->eval != VALUE_NONE` is always
true). Selecting the source first is bit-exact by construction: the default
`ttEval=false` path still calls `evaluate()`, the `ttEval=true` hit path still
returns `int(entry->eval)`, and `bench` d16/d12 signatures and node counts
stayed identical.

It was NOT promoted to a strength experiment. Five-repeat `bench --depth 12`
timings were dominated by build/code-layout and shared 2-vCPU variance: on the
SAME old binary `ttEval=0` measured 2.6273 s and `ttEval=1` 2.4443 s with
identical node counts, while the two builds differed by ~7 % on the identical
`ttEval=0` path. The candidate fix measured only 2.3739 s vs 2.4443 s
(~2.9 %), i.e. below the noise floor. A 40+4 ms Tier-1 screen for an effect
that cannot be resolved above measurement noise is not a good use of the
budget, so the source was reverted to the exp-0038 pinned SHA. No Elo, no
strength claim, no result JSON. This is a profiled elimination, not a failed
experiment, and does not close the mission.

### exp-0038 closure: what the profiling actually taught us

The instrumented counter result (millions of hits, ~0 node savings) is the
important architectural lesson, not just a failure report: a transposition
cache is only worth its probe/store overhead when the cached node would
otherwise search a SUBTREE. In this engine qsearch already returns at stand-pat,
delta pruning, or SEE<0 capture pruning for most nodes, so the expensive nodes
are rare and their windows rarely repeat across iterative deepening. A qsearch
TT is therefore structurally weak here. Future directions should either (a)
change WHICH nodes are searched (extensions / pruning decisions), or (b) make
the expensive `evaluate()` call itself cheaper in a bit-exact way. exp-0039
showed option (b) at the negamax layer is below the noise floor; the qsearch
layer remains unmeasured but must not be reached by silently retuning the
abandoned exp-0038 cache — it requires its own frozen preregistration.

### exp-0040 elimination and the "mechanism-live" precondition

exp-0040 is the second profiling-only elimination this cycle (after exp-0039).
It produced a reusable design rule: a candidate must be shown to CHANGE THE
SEARCH TREE at the actual 40+4 ms control before a fixed-time tournament is
spent on it. Merely changing a budget, a cache size, or a formula is not
enough when another gate (here the 55 %/70 % early stops) absorbs the change.
The instrumented `TMDEBUG` check was important: it proved the switch reached
`TimeManager` (soft 4 -> 6 ms, hard 13 ms) so the identical depth/nodes/time
was a genuine interaction, not a wiring bug. exp-0041 deliberately applies
this rule: its fixed-depth 12 diagnostic shows 757,239 -> 438,131 nodes
(−42.1 %), so the mechanism is live before any evaluation game. Fixed-depth
node counts are still NOT strength evidence; the Tier-1 40+4 ms screen is.

### exp-0041 closure: node savings are not strength

exp-0041 satisfied the new "mechanism-live" precondition (−42.1 % fixed-depth-
12 nodes) and still produced `−5.06 [−15.18,+5.05]` Elo at 40+4 ms. This is
the third independent confirmation in this project that throughput proxies
(portable flags, qlite, exp-0041) do not predict fixed-time strength. The
architectural lesson is that extending a validated shallow pruning decision
higher in the tree is qualitatively different from applying it shallowly:
at depth <= 3 a SEE<−100 capture is nearly always refuted, but near the root
it can be a sound sacrifice or a necessary interposition, and removing it also
changes move ordering for the whole subtree. Future search work should prefer
mechanisms that IMPROVE the accuracy of a decision at the same node count
(e.g. better move ordering, singular verification with a genuine re-search)
over mechanisms that simply delete more nodes. Do not tune the frozen
`BadCaptureMargin=100` on these results.

### exp-0042 design: improve decision accuracy, not node deletion

exp-0041 closed with `−5.06 [−15.18,+5.05]` Elo despite a 42 % fixed-depth
node saving. The next mechanism therefore does NOT try to delete more nodes:
it makes an EXISTING pruning decision more accurate. The shipped qsearch delta
check must assume a queen capture (975 cp) because it runs before movegen; once
the legal captures exist, their real maximum gain (SEE gain[0], promotion-safe)
is known and usually much smaller. The original conservative check is kept
first and unchanged, and `deltaMargin=200` stays frozen, so the new check can
only prune nodes whose actual available material cannot reach alpha plus the
same safety margin.

Profiling showed total fixed-depth nodes INCREASE 13.8 % with the switch on.
That is not a contradiction: pruning returns stand-pat values instead of
searched capture values, which changes upstream alpha-beta decisions and
history/ordering. It is recorded as proof the mechanism is LIVE, and as one
more example of why fixed-depth node counts are not strength evidence. If
exp-0042 closes negative, do NOT retune `deltaMargin` or the gain formula; the
conclusion would be that this engine's quiescence stand-pat decisions are
load-bearing, consistent with the earlier qlite rejection.

### exp-0042 screen: an INCONCLUSIVE result is not a failure and not a success

The frozen §5 rules deliberately left a third state. `+2.6110 [−7.9556,
+13.1825]` misses ADVANCE (needs +20 and LCB > 0) but also misses CLOSE
(needs UCB < +10 or point <= 0). Recording it as "no improvement" would be a
post-hoc reinterpretation; recording it as "promising" would be batch
selection. The prereg therefore routes it to more samples. The addendum fixes
the previously-unspecified sample size and, importantly, forbids pooling the
screen with the confirmation: combining an already-observed +2.61 screen with
new data would be exactly the post-hoc combining the mission forbids. The
screen stays exploratory; only the fresh confirmation decides. A terminal
compute bound is added for the residual-inconclusive case; it can only PREVENT
a claim, never create one, and changes no Gate and no threshold. The
confirmation null is required partly because the screen null arm showed a
noisy +17.47 point estimate (CI still includes zero).

### exp-0042 closure: accurate pruning is still a search decision

exp-0042 deliberately avoided exp-0041's failure mode (deleting more nodes):
it made an EXISTING delta decision more accurate using the real legal capture
gains, with the original conservative check and frozen margin untouched. It
still closed at `−10.8281 [−21.8567,+0.1787]` Elo. The mechanism increases
fixed-depth nodes by 13.8 %, so the loss is not from raw throughput but from
changed stand-pat values propagating into upstream alpha-beta decisions and
ordering. Conclusion for future search work: in this engine the quiescence
stand-pat value is load-bearing (also shown by the qlite rejection). Neither
"delete nodes" nor "tighten a qsearch pruning decision" has converted to
fixed-time strength. The next credible family is one that improves MOVE
ORDERING or adds accurate tactical verification without rewriting stand-pat
values — singular/tactical extensions — but exp-0037's warning about
verification-subtree overhead at 4 ms must be profiled first. Do not retune
`deltaMargin=200` on these results.

## exp-0043 launched — TT-evidence singular extension (2026-11-04)
After exp-0042 CLOSED/ABANDONED (screen `+2.6110 [−7.9556,+13.1825]`
INCONCLUSIVE, bounded confirmation `−10.8281 [−21.8567,+0.1787]` CLOSE, NEVER
pooled), the mission remains ACTIVE/NOT COMPLETE. The post-exp-0042 rank-1
direction is now executing WITHOUT re-running or modifying exp0042, reusing
confirmation data, bypassing preregistration or weakening gates.

Mechanism: `SearchParams::ttSingularExtension=false`; in `negamax` a
slightly-shallower TT LOWER bound >= beta + 50 cp at depth >= 3 marks the
always-first hash move singular, and that ONE move is searched a ply deeper.
`MaxSingularExtensions=2` is path-scoped via a counter restored on every
return; `SingularDepthSlack=3`. NO verification subtree (exp-0037 CLOSED at
`+3.7766 [−9.3368,+16.9008]`), NO stand-pat rewrite, NO new qsearch pruning
rule, NO default-ON feature disabled. The canonical genuine re-search variant
is DEFERRED and the deviation is DECLARED IN ADVANCE in the prereg.

Frozen before any evaluation game: `docs/DEV6_PREREG_EXP0043.md` (SHA
`e9fe40f053c9f479835c05efc3bf592547024090c1a315281ec727f0096f31dc`),
`tier1-plan-exp0043.json` (4 jobs), `scripts/dev6_exp0043_openings.py` and
1,400 fresh disjoint openings (seed `2026120201`, ZERO overlap with 32,041
earlier positions in 120 files, four disjoint slices), and dispatch
`mode=benchmark experiment_id=exp0043 attempt=13`. All committed in the SAME
commit as the dispatch. Default-off bit-exact signatures
`243f9a1c1ba5b36f` / `a14ab62224f837e5` / `e45fa2ec2287eb41`, Release ctest
11/11, ASan+UBSan ctest 11/11 (`exp0043_asan_ctest.log`), UCI default false.

MANDATORY pre-result mechanism-live/overhead diagnostic from the FROZEN
source (instrumented `SB_SINGULAR_DEBUG` build, real suite positions):
fixed depth 10 over 16 positions OFF 2,655,145 nodes ON 3,024,895 nodes
(+13.9 % overhead), 15,000 triggers / 8,072 extensions; FIXED TIME 40+4 ms
over 24 positions x 2 repeats OFF 222,636/217,259 nodes ON 218,959/225,368
nodes, median depth 6 both, 1,093/1,092 triggers and 548/516 extensions,
LIVE on 23/24 positions. A startpos `go depth 12` probe found 0 triggers;
suite positions are the preregistered probe. These are VALIDITY/overhead
checks, NOT strength evidence.

Design: FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, never `--nodes`;
Stage-0 validity null 400 games (0 forfeits required), candidate-options null
400 games, batchA/batchB 1,000 games each on independent fresh suites;
combined frozen before the run, independent raw-JSONL audit, 4 isolated VMs,
exact packaged tested binary. Frozen ADVANCE >= +20 point AND LCB > 0 AND
both batches >= −5 AND both null CIs include 0 AND 0 failures; CLOSE if
UCB < +10 OR point <= 0; INCONCLUSIVE -> ONE bounded fresh confirmation,
NEVER pooled. Gates 1 (+75/LCB>+50) and 4 remain UNMET; no strength claim,
no bundle, no default change, no PR/merge/tag/release/deploy/dev7.

## exp-0043 CLOSED / ABANDONED (2026-11-04)
Tier-1 run `41809643084` (4 isolated VMs SUCCESS), export `41810711486`
SUCCESS, CI `41809642415` SUCCESS on exact source
`5ea5ad21348f39dabad1da3e8cb098f798087295`. Frozen prereg
`e9fe40f053c9f479835c05efc3bf592547024090c1a315281ec727f0096f31dc`, plan
`3141fb1f487184459b52d644d3187f201dbd70216455469768613e0aebff2e70`,
packaged=tested binary
`c2ef506c5c6ebf9c3197c52903f61ccbf5326f16221c3c96a5bb3a8dc4420409`,
1,400 fresh disjoint openings seed `2026120201` (0 overlap / 32,041 earlier).
FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, no `--nodes`; one binary,
single switch `TTSingularExtension=true` vs `false`. All 4 bundles 9/9
SHA256SUMS OK, 0 failures.

Mandatory mechanism-live diagnostic: LIVE on 23/24 suite positions at the
exact 40+4 ms control (548/516 extensions across 24 positions x 2 repeats),
median depth 6 unchanged, +13.9 % fixed-depth-10 node overhead. VALID
negative, not an inert experiment.

Stage-0 validity null 399 games 128/129/142 `−13.1005 [−29.9568,+3.6943]`,
0 forfeits/illegal/UCI failures, CI includes 0 -> PASS. Candidate-options
null 400 games 145/123/132 `+11.2956 [−7.4505,+30.1078]`, includes 0.
batchA 997 games 333/302/362 `−9.7895 [−25.2667,+5.6489]`; batchB 997 games
321/325/351 `−10.8390 [−25.2969,+3.5814]`. FROZEN combined 1,994 games
654/627/713, score 0.4852056, `−10.3142 [−20.8915,+0.2440]`, 994 clusters,
independent Elo-from-score −10.2832, seeded cluster bootstrap
`[−20.6467,+0.1748]`. `dev6_exp0038_audit.py 41809643084 exp0043 20 10`
-> 44 stored values, 0 issues, AUDIT PASS.

FROZEN RULE: ADVANCE false (point < +20, LCB < 0, both batches < −5);
CLOSE true (UCB +0.2440 < +10 AND point <= 0). => CLOSE / ABANDONED. Not
INCONCLUSIVE, so no confirmation run and no fresh suites spent.
`TTSingularExtension` stays OFF; frozen constants NOT retuned; no bundle, no
strength claim, no default change, no PR/merge/tag/release/deploy/dev7.
Full report `docs/DEV6_EXP0043_REPORT.md`. Gates 1 and 4 remain UNMET;
mission ACTIVE / NOT COMPLETE; next hypothesis is being selected and launched.

## exp-0044 launched — SEE-losing-capture ordering (2026-11-04)
Post-exp-0043 re-ranking: exp-0041, exp-0042 and exp-0043 are three
consecutive fixed-time losses for mechanisms that change WHICH nodes are
searched or ADD a ply at non-PV nodes; exp-0036 (+21.52, shallow SEE-losing
capture PRUNING) and exp-0038 (+7.68, qsearch information reuse) remain the
only positive directions. Rank 1 is now move-ordering ACCURACY with ZERO added
per-node work.

Code inspection found a concrete deficiency: in `Search::score_moves` a
capture with SEE < 0 scores ~2,000,000, ABOVE killers (1,500,000),
countermoves (1,485,000) and every quiet history move (|h| <= 60,000), so
losing captures are searched immediately after winning captures at EVERY
main-search node. exp-0044 demotes them to the tail in the MAIN search ONLY.
NO move is removed (unlike exp-0036/0041), NO SEE/eval call is added, NO
stand-pat value or pruning/extension decision changes, quiescence excluded.
Frozen `BadCaptureOrderScore=-2000000`, threshold SEE<0, no tunable margin —
NOT best-of-N parameter selection, NOT a repeat of exp-0036/0041.

Frozen before any evaluation game: `docs/DEV6_PREREG_EXP0044.md` (SHA
`73ae460981a09bbf5d605205f8b77bf799b6d92a0fed4dc4abaa3a4ebc3820a5`),
`tier1-plan-exp0044.json` (4 jobs), `scripts/dev6_exp0044_openings.py` and
1,400 fresh disjoint openings (seed `2026120301`, ZERO overlap with 33,441
earlier positions in 125 files, four disjoint slices), dispatch
`mode=benchmark experiment_id=exp0044 attempt=15`. All in the SAME commit as
the dispatch. Default-off bit-exact signatures `243f9a1c1ba5b36f` /
`a14ab62224f837e5` / `e45fa2ec2287eb41`, Release ctest 11/11, ASan+UBSan
ctest 11/11 (`exp0044_asan_ctest.log`), UCI default false.

MANDATORY pre-result mechanism-live/overhead diagnostic from the FROZEN source
(`SB_BADCAP_DEBUG`): fixed depth 10 over 16 suite positions OFF 2,655,145
nodes, ON 2,961,866 nodes (+11.6 % TREE change, ZERO added per-node work),
424,155 demotions, live 16/16; FIXED TIME 40+4 ms over 24 positions x 2
repeats OFF 228,643/236,838 nodes, ON 203,245/214,462 nodes, median depth 6
for both, 22,024/24,413 demotions, LIVE 24/24. The node INCREASE is disclosed
as a risk and is NOT strength evidence.

Design: FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, never `--nodes`;
Stage-0 validity null 400 games, candidate-options null 400 games,
batchA/batchB 1,000 games each on independent fresh suites; ANY time
forfeit/illegal/engine failure in ANY job => INVALID MEASUREMENT. Frozen
ADVANCE >= +20 AND LCB > 0 AND both batches >= −5 AND both null CIs include 0
AND clean; CLOSE if UCB < +10 OR point <= 0; INCONCLUSIVE -> ONE bounded fresh
confirmation, NEVER pooled. Gates 1 (+75/LCB>+50) and 4 remain UNMET; no
strength claim, no bundle, no default change, no PR/merge/tag/release/deploy/
dev7, no reuse of closed exp0041/0042/0043 data.

## exp-0044 screen INCONCLUSIVE; bounded confirmation launched (2026-11-04)
Tier-1 run `41812595433` / export `41813751266` / CI `41812595476` SUCCESS on
exact source `2ae4e68fc882991c3484eede22a4622f713da5e2`; frozen prereg
`73ae460981a09bbf5d605205f8b77bf799b6d92a0fed4dc4abaa3a4ebc3820a5`; 4
isolated VMs, 9/9 SHA256SUMS OK in each of 4 bundles, 0
forfeits/illegal/engine failures. Stage-0 validity null 400 games 133/145/122
`+9.5569 [−6.6563,+25.8118]`; candidate-options null 400 games 138/124/138
`0.0000 [−17.9335,+17.9335]`; batchA 1,000 games 341/336/320
`+6.6419 [−8.1259,+21.4338]`; batchB 996 games 335/328/336
`0.0000 [−15.0949,+15.0949]`; FROZEN combined 1,996 games 676/664/656,
score 0.5050100, 996 clusters, `+3.3140 [−7.2389,+13.8730]`, independent
Elo-from-score +3.4814, seeded bootstrap `[−7.1520,+13.7861]`, 44/0 AUDIT
PASS. ADVANCE false (point<+20, LCB<0); CLOSE false (UCB +13.8730 >= +10,
point>0) => INCONCLUSIVE. Frozen §6 mandates exactly ONE bounded fresh
confirmation, NEVER pooled with the screen.

`docs/DEV6_PREREG_EXP0044_ADDENDUM.md` (SHA
`17d90a790697bb05de108d4b5fb5f7cf745fdb611899c5237c7ccce2b73af835`) freezes
the confirmation BEFORE any confirmation game: separate Tier-1 run, dispatch
`mode=benchmark experiment_id=exp0044_confirm attempt=17`, FIXED TIME 40+4 ms,
SAME single switch `BadCaptureOrdering=true` vs false, 1,400 fresh disjoint
openings seed `2026120401` (ZERO overlap with 34,841 earlier positions in 130
files), generator `scripts/dev6_exp0044_confirm_openings.py`, its own Stage-0
and candidate-options nulls, two independent 1,000-game batches. Decision uses
ONLY new batches: ADVANCE >= +20 AND LCB>0 AND clean; CLOSE if UCB<+10 OR
point<=0; otherwise CLOSED AS INCONCLUSIVE and direction abandoned
(conservative compute bound, NOT a threshold change). No strength claim, no
default change, no bundle, no retune, no pooling. Gates 1 and 4 remain UNMET;
mission ACTIVE / NOT COMPLETE.

## exp-0044 CLOSED AS INCONCLUSIVE / ABANDONED (2026-11-04)
Confirmation run `41814069967`, export attempt 18 `41815187170` FAILED only at
a transient GitHub Internal Server Error evidence push (download + checksums
succeeded; nothing reached remote). TECHNICAL FAILURE diagnosed and repaired
within scope: workflow export step gained a bounded 4-attempt push retry, and
the export was re-dispatched as NEW valid run `41815428066` SUCCESS. 9/9
SHA256SUMS OK in each of 4 bundles, 0 failures. No scientific change.

Confirmation source `0691b9affd36006425ac23605f4a0cc8922a55bb`, addendum
`17d90a790697bb05de108d4b5fb5f7cf745fdb611899c5237c7ccce2b73af835`, CI
`41814069925` SUCCESS. Stage-0 400 games 123/143/134
`−9.5569 [−32.6787,+13.4804]`; candidate null 398 games 142/123/133
`+6.1422 [−14.8210,+27.1502]`; batchA 999 games 360/328/311
`+17.0722 [+0.6984,+33.5222]`; batchB 998 games 339/348/311
`+10.1190 [−5.8209,+26.1015]`; FROZEN combined 1,997 games 699/676/622,
score 0.5192789, 997 clusters, `+13.5977 [+2.1746,+25.0503]`, independent
Elo-from-score +13.4030, seeded bootstrap `[+2.4394,+24.9592]`, 44/0 AUDIT
PASS, 0 forfeits/illegal/failures.

ADVANCE false (point < +20); CLOSE false (UCB >= +10, point > 0). The FROZEN
ADDENDUM explicitly overrides the prereg §6 "more samples" default with an
experiment-level COMPUTE BOUND => **CLOSED AS INCONCLUSIVE / ABANDONED**.
`scripts/dev6_exp0044_confirm_decision.py` reproduces the override from raw
games. Screen `+3.3140 [−7.2389,+13.8730]` and confirmation CIs overlap and
were **NEVER pooled**. No strength claim, no third run, no retune, no bundle,
no default change, no PR/merge/tag/release/deploy/dev7. Full report
`docs/DEV6_EXP0044_REPORT.md`. Gates 1 and 4 remain UNMET; mission ACTIVE /
NOT COMPLETE; the next hypothesis must have its OWN frozen prereg, fresh
disjoint suites and dispatch, and may not reuse exp-0044 data.

## exp-0045 launched — bit-exact dead evaluate() elimination (2026-11-04)
Post-exp-0044 rank change: exp-0044 CLOSED AS INCONCLUSIVE / ABANDONED at its
frozen addendum compute bound; the next ranked direction that changes NO
search decision is bit-exact evaluate() throughput. exp-0039 built this exact
fix, verified it bit-exact, measured ~2.9 % against a ~7 % local noise floor,
REVERTED it and spent NO games. exp-0045 is the FIRST Elo measurement of that
hypothesis on isolated VMs at FIXED TIME 40+4 ms — not a repeat of exp-0039's
profiling, not a parameter change, no exp-0041..0044 data reused.

Frozen before any evaluation game: `docs/DEV6_PREREG_EXP0045.md` (SHA
`0abf66836ed0ad6d979a26a3d4ca8616416bfb88b8ca069875f1e7d4e7bb2863`),
`tier1-plan-exp0045.json` (4 jobs), `scripts/dev6_exp0045_openings.py` and
1,400 fresh disjoint openings (seed `2026120501`, ZERO overlap with 36,241
earlier positions in 135 files, four disjoint slices), dispatch
`mode=benchmark experiment_id=exp0045 attempt=20`. All in the SAME commit as
the dispatch. Default-off bit-exact signatures `243f9a1c1ba5b36f` /
`a14ab62224f837e5` / `e45fa2ec2287eb41`, d16 with `ttEval=1` identical
OFF/ON, Release ctest 11/11, ASan+UBSan ctest 11/11
(`exp0045_asan_ctest.log`), UCI default false.

MANDATORY pre-result diagnostics from the FROZEN source (`SB_DEADEVAL_DEBUG`):
node counts OFF/ON IDENTICAL at depths 8/10/12 (depth 12 `[72604, 497628,
311669, 559024]` for both); ON skipped 40,187 of 379,656 evaluate() calls
(10.6 %) => mechanism LIVE; local 12 alternating repeats at depth 12 OFF
median 804.0 ms / ON 823.5 ms (−2.37 % "speedup", noise-dominated, reported
VERBATIM, NO local speedup claim). Theoretical speedup ~2-3 % because only
10.6 % of evaluations can be saved. Honest power statement: a 2,800-game
screen has ~13 Elo half-width and CANNOT resolve a +2-3 Elo effect; it is
powered for the +20 ADVANCE threshold and to rule out a material regression.
SINGLE-RUN compute bound closes exp-0045 AS INCONCLUSIVE if neither frozen
condition holds; no post-hoc sample increase, no confirmation.

Design: FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, never `--nodes`;
Stage-0 validity null 400 games, candidate-options null 400 games,
batchA/batchB 1,000 games each on independent fresh suites; ANY time
forfeit/illegal/engine failure => INVALID MEASUREMENT. Frozen ADVANCE >= +20
AND LCB>0 AND both batches >= −5 AND both null CIs include 0 AND clean; CLOSE
if UCB<+10 OR point<=0; otherwise CLOSED AS INCONCLUSIVE / ABANDONED. Gates 1
and 4 remain UNMET; no strength claim, no bundle, no default change, no
PR/merge/tag/release/deploy/dev7.

## exp-0045 original run INVALID MEASUREMENT; bounded valid retry launched (2026-11-04)
Run `41817228668` / export `41818409701` / CI `41817228408` SUCCESS on source
`e41a0b18b4e522f57196e2834c8937f8c55019e8`, frozen prereg `0abf66836ed0ad6d…`;
4 isolated VMs, 9/9 SHA256SUMS OK in each of 4 bundles, 44 stored values / 0
issues AUDIT PASS. But batchB `summary.json` has `time_forfeit=1`: game 272,
14.1 ms move at ply 118, `remaining_white_ms=-5.01`, long game, clock nearly
exhausted. FROZEN prereg §5 requires 0 forfeits in ANY job => **INVALID
MEASUREMENT**. ALL Elo/CIs/W-D-L/LLR and the generic audit's "CLOSE" label are
DISCARDED; `clean=False` is the correct signal; NO strength inference. Stage-0
validity null, candidate-options null, batchA and all illegal/engine_failure
counts were clean. Diagnosis: rare isolated-VM long-game clock outlier (1/998;
exp-0043/0044 had 0 forfeits at the same control), not a systematic mechanism
effect; it favoured the candidate and could not manufacture a positive. NO
repair to the frozen 40+4 ms control, clocks, binary, switch, time manager or
driver is authorised.

`docs/DEV6_PREREG_EXP0045_RETRY.md` (SHA
`2172063e22554df99064c54e0820b70db854e2339b0d5e87ccc321b6ca0bce60`) frozen
BEFORE any retry game: identical frozen science, NEW `exp0045_retry`, dispatch
`mode=benchmark attempt=22`, `tier1-plan-exp0045-retry.json`, NEW seeds, 1,400
fresh disjoint openings seed `2026120601` (ZERO overlap with 37,641 earlier
positions in 140 files, generator `scripts/dev6_exp0045_retry_openings.py`).
Invalid run `41817228668` NEVER pooled or reused. Frozen ADVANCE >= +20 AND
LCB>0 AND clean; CLOSE if UCB<+10 OR point<=0; otherwise CLOSED AS
INCONCLUSIVE. BOUNDED RETRY BUDGET: exactly one retry; a second forfeit closes
exp-0045 AS TECHNICALLY UNRESOLVABLE with no strength inference. No threshold
weakened (the zero-forfeit rule was ENFORCED). Gates 1 and 4 remain UNMET; no
strength claim, no default change, no bundle, no PR/merge/tag/release/deploy/
dev7. Mission ACTIVE / NOT COMPLETE.

## exp-0045 FINAL CLOSE / ABANDONED (2026-11-04)
Original run `41817228668` / export `41818409701` / CI `41817228408` SUCCESS but
INVALID MEASUREMENT (1 TIME_FORFEIT in batchB game 272, 14.1 ms move, ply 118,
`remaining_white_ms=-5.01`). Frozen prereg §5 zero-forfeit rule ENFORCED; ALL
Elo/CIs/W-D-L/LLR and the generic audit's "CLOSE" label DISCARDED, no strength
inference, `clean=False`. Diagnosed as a rare isolated-VM long-game clock
outlier; no repair to the frozen 40+4 ms control authorised.

One bounded valid retry (frozen `DEV6_PREREG_EXP0045_RETRY.md` SHA
`2172063e22554df9…`, attempt 22, 1,400 fresh disjoint openings seed
`2026120601`, ZERO overlap / 37,641 earlier positions in 140 files): run
`41818958001` / export `41821624068` / CI `41818958003` SUCCESS. Pinned source
`9fb2a58…`, dev5 baseline VERIFIED, built==packaged binary `b839fae82b54…`,
UCI `SkipDeadTTEval default false`. 9/9 SHA256SUMS OK in each of 4 bundles,
0 forfeits/illegal/failures in ALL four jobs, 44/0 AUDIT PASS `clean=True`.
Stage0 399 `118/155/126` −6.1113 [−23.3656,+11.1129]; candidate null 400
`152/111/137` +13.0349 [−6.3155,+32.4666]; batchA 994 `327/320/347`
−6.6823 [−19.7471,+6.3636]; batchB 999 `324/320/355`
−11.1440 [−24.5596,+2.2383]. FROZEN COMBINED batchA+batchB ONLY 1,993 games
`651/640/702`, score 0.4872052, 993 clusters,
−8.9240 [−18.2792,+0.4182], Elo-from-score −8.8927, bootstrap
[−18.2107,+0.1749]; both null CIs include 0, both batches < −5.
ADVANCE False; CLOSE True (UCB<+10 AND point<=0). Reproduced by
`scripts/dev6_exp0038_audit.py 41818958001 exp0045_retry 20 10` and
`scripts/dev6_exp0045_retry_decision.py`: VERDICT CLOSE (mechanism rejected /
abandoned; NO strength claim). No confirmation / third run / post-hoc sample
increase / pooling / retune / default change / bundle. Switch stays OFF. This
is NOT a proven strength regression (~13 Elo half-width). Gates 1 and 4 UNMET,
2 direction-supported, 3 PASS; mission ACTIVE / NOT COMPLETE; no strength
claim, no PR/merge/tag/release/deploy/dev7. Full report
`docs/DEV6_EXP0045_REPORT.md`; evidence
`benchmarks/exp-runs/tier1-export/run-41818958001/`.


## exp-0046 LAUNCHED — margin-adaptive null-move reduction (2026-11-04)
exp-0045 is CLOSED / ABANDONED (INVALID original run, ONE bounded valid retry
`41818958001` frozen combined `-8.9240 [-18.2792,+0.4182]` => CLOSE). New
ranked direction: shipped null-move verification uses a FIXED
`SB_NULLMOVE_R + depth/5` and discards the SIZE of `staticEval - beta` already
computed for the guard. exp-0046 makes ONLY that existing subtree shallower
when staticEval is far above beta, with ZERO added per-node work, no extra
ply, no constant retune of a closed switch and no earlier data reused.

Default-OFF switch `AdaptiveNullR` in `src/search/search.hpp/cpp`,
`src/uci/uci.cpp`, `src/utilities/bench.cpp`; frozen constants
`AdaptiveNullMarginDivisor=200`, `AdaptiveNullExtraCap=2` chosen BEFORE any
game from theory only. OFF bit-identical: default bench
`243f9a1c1ba5b36f`, d16 ttEval=1 `a14ab62224f837e5`, d12 params
`e45fa2ec2287eb41`; Release ctest 11/11, ASan+UBSan ctest 11/11
(`benchmarks/dev6-baseline/exp0046_asan_ctest.log`), UCI default false.

PRE-RESULT diagnostics (`scripts/dev6_exp0046_diag.py`, instrumented
`SB_ADAPTIVE_NULL_DEBUG` build, 24 REAL exp-0046 suite positions): FIXED DEPTH
10 OFF 4,311,394 nodes / ON 4,252,622 (−1.36 % tree change), 44,789 null
nodes, 4,133 changed, 4,721 extra plies, LIVE 23/24; 40 ms fixed-time PROBE
OFF 1,006,703 / ON 974,327 (−3.22 %), LIVE 22/24, median depth 8 both.
Diagnostics are liveness/overhead evidence ONLY, NOT strength; no local
speedup claim.

FROZEN BEFORE ANY exp-0046 GAME: `docs/DEV6_PREREG_EXP0046.md` SHA
`dda54084d2acffddcb7cd5d1134f8734858e9bf0c69d3ab2eb59d3aeab15dd61`, `benchmarks/exp-runs/tier1-plan-exp0046.json` SHA
`557d51fc07ad18eb828e94b2cb273e7225956ca4e6cd55b2279216fb8ebaa18a` (4 jobs), `scripts/dev6_exp0046_openings.py`, 1,400 fresh disjoint
openings seed `2026120701` (ZERO overlap with 39,041 earlier positions in
145 files, ZERO duplicates, four disjoint slices; SHAs in
`benchmarks/dev6-baseline/exp0046_suites.json`). Dispatch
`mode=benchmark experiment_id=exp0046 attempt=24`, `source_sha=HEAD`, all in
the SAME commit. FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, never
`--nodes`; champion options BOTH arms, A adds ONLY `AdaptiveNullR=true`;
Stage-0 control/control validity null, candidate-options null, batchA/batchB
1,000 games each; frozen combined = batchA+batchB ONLY; independent raw-JSONL
audit. ADVANCE >= +20 AND LCB>0 AND both batches >= −5 AND both null CIs
include 0 AND clean; CLOSE if UCB<+10 OR point<=0; otherwise CLOSED AS
INCONCLUSIVE (single-run compute bound). Validity gate enforces 0 forfeits /
illegal / UCI / engine failures in ANY job (exp-0045 lesson, NOT weakened);
at most ONE bounded valid retry. Gates 1 and 4 UNMET; no strength claim, no
default change, no retune, no bundle, no PR/merge/tag/release/deploy/dev7.
Mission ACTIVE / NOT COMPLETE; no result may terminate it.

## exp-0046 CLOSED AS INCONCLUSIVE / ABANDONED (2026-11-04)
Run `41825055840` / export `41826460428` / CI `41825055708` SUCCESS, exact
source `0792555ddd155b2426d926cccc5a16975f77682b`, prereg SHA
`dda54084d2acffdd…`, plan SHA `557d51fc07ad18eb…`, dispatch attempt 24.
4 isolated VMs, 9/9 SHA256SUMS OK in each of 4 bundles, 0 TIME_FORFEIT /
ILLEGAL / ENGINE_FAILURE in ALL four jobs, 44 stored values / 0 issues AUDIT
PASS `clean=True`. Provenance: dev5 baseline VERIFIED, built==packaged binary
`18b9366edcaf…`, default bench `243f9a1c1ba5b36f`, UCI
`AdaptiveNullR default false`. 1,400 fresh disjoint openings seed
`2026120701` (ZERO overlap / 39,041 earlier positions in 145 files), FIXED
TIME 40+4 ms, Hash16/Threads1/240 plies, never `--nodes`.

Stage0 399 `149/113/137` +11.3524 [−5.1046,+27.8606]; candidate null 399
`122/146/131` −8.7314 [−28.0469,+10.5303]; batchA 995 `333/337/325`
+3.1586 [−8.7463,+15.0709]; batchB 995 `350/305/340`
+3.8606 [−8.5988,+16.3299]; both null CIs include 0, both batches >= −5.
FROZEN COMBINED batchA+batchB ONLY 1,990 games `683/642/665`, score
0.5045226, 990 clusters, +3.5096 [−5.1015,+12.1250], Elo-from-score
+3.1427, bootstrap [−4.9136,+12.1125]. ADVANCE False; CLOSE False
(UCB>=+10, point>0). Generic audit's "more samples" is its §6 DEFAULT,
OVERRIDDEN by the frozen SINGLE-RUN COMPUTE BOUND;
`scripts/dev6_exp0046_decision.py` independently reproduces VERDICT
CLOSED_AS_INCONCLUSIVE (frozen single-run compute bound; NO further samples).
No strength claim (CI includes 0), no default change, no retune, no bundle,
no confirmation, no post-hoc sample increase, no pooling with exp-0045 or any
earlier experiment. `AdaptiveNullR` stays OFF. Gates 1 and 4 UNMET,
2 direction-supported, 3 PASS; mission ACTIVE / NOT COMPLETE; no strength
claim / PR / merge / tag / release / deploy / dev7. Full report
`docs/DEV6_EXP0046_REPORT.md`; evidence
`benchmarks/exp-runs/tier1-export/run-41825055840/`.

---

## 2026-11-04 — DEV6 exp-0047 evidence-driven investigation (NO GAMES)

Exact HEAD `d07294d7dbd3a88e5b673f048aeb6a7b1acc1dbf`; CI `41826927521`
SUCCESS; mission ACTIVE / NOT COMPLETE. Added
`docs/DEV6_EXP0047_INVESTIGATION_REPORT.md` (verifiable Phase-1/2 report),
`docs/DEV6_PREREG_EXP0047.md` (complete FROZEN preregistration, DORMANT /
NOT ACTIVATED), and raw gprof evidence
`benchmarks/dev6-baseline/exp0047_gprof_{flat,callgraph}.txt` +
`exp0047_asan_ctest.txt`. Updated current status and research matrix. NO engine
source change, NO implementation, NO opening suite, NO `tier1-dispatch.json`
edit, NO benchmark run, NO new PGN/JSONL, NO invalid measurement, NO pooling,
NO reopened decision.

Verified: authoritative §8 Gate 1 (>= +75 Elo AND 95 % LCB > +50) and Gate 4
(exact candidate release artifact must be the tested binary); full exp-0001…
0046 hypothesis inventory; fresh gprof profile (24 FENs, 12,161,395 nodes:
features 17.77 %, next_move 10.40 %, attacks_bb 9.45 %, TT probe 8.51 %);
fresh matched-toolchain NPS ratio 1.0289 (inside noise, 3 alternating reps,
24,211,820 identical nodes); Release 11/11 and ASan+UBSan 11/11 ctest; three
frozen bench signatures; all 17 experimental UCI switches default false;
reproduced exp-0045 CLOSE and exp-0046 CLOSED_AS_INCONCLUSIVE decisions;
44/0 audits ×2 and 36/36 checksums ×2 exports.

DECISION: no scientifically defensible strength experiment exists at this HEAD
(power analysis says the candidate, not sample size, is binding; every measured
candidate has UCB < +50). Ranked hypotheses: bit-exact attack-set dedup
(~+3–8 Elo, NOT JUSTIFIED), exp-0036 replication (forbidden by frozen
non-repeat), stronger evaluator with accuracy→strength link (highest relevance,
NOT YET TESTABLE). Missing evidence: fresh bullet-matched corpus + frozen
accuracy metric, matched-toolchain inference cost, pre-result >= +75 argument.
The one selected experiment is preregistered with §8 thresholds, 2 x 6,600
games, fresh disjoint suites, 0-forfeit validity, NO authorised retry, a
single-run compute bound and an independent raw-JSONL decision script; it stays
DORMANT until its Activation Record is committed. Gates 1/4 UNMET, 2
direction-supported, 3 PASS; no strength claim, default change, PR, merge, tag,
release, deploy or dev7.

## 2026-11-06 — benchmark integrity: engine-failure classification

- The tournament harness classified a move by checking the clock before the
  engine error. A crash (`RuntimeError`/`OSError`) or illegal move that happened
  on the same move the clock expired was recorded as `TIME_FORFEIT`, hiding a
  correctness defect inside a timing record. Because the DEV6 validity rule
  counts `FAILURE` and `FORFEIT` substrings separately, this also mis-counted the
  failure category and would misdirect root-cause analysis. The error is now
  classified first: any non-`TimeoutError` engine error is `ENGINE_FAILURE` even
  when the flag also fell; a `TimeoutError` (the forfeit deadline itself) remains
  a time forfeit. Each game record carries `engine_failure`, and the summary
  carries `engine_failures`/`time_forfeits`. The ply limit (`max_plies`) is now
  recorded in the configuration line so censored matches are distinguishable.
  Regression: `tests/integration/test_tournament_integrity.py` (fake engines,
  deterministic flag fall via base_ms=0). No game semantics or adjudication
  changed; only the failure category and provenance fields.

## 2026-11-06 — exp-0048: why a full per-square PST is the next hypothesis

Append-only design note. No result is claimed here.

The DEV6 failure ledger has now closed: small CPU NNUE (exp-0001, -652/-720 Elo,
~4x slower), cp distillation, incremental eval (bit-exact but -27% NPS), six
extended pawn/coordination features (exp-0026, -17), every search-switch
ablation (exp-0033..0046, all within noise or negative), and repeated scalar
retunes of the existing feature weights (exp-0005/0012, plateau). Profiling
attributed 17.8% to feature computation and showed a dedup ceiling of only
+3..8 Elo with an NPS ratio of 1.0289 (noise), which eliminated the
"make the same evaluation faster" family.

What has never been tried is increasing the *expressiveness* of a term whose
per-node cost is already paid. The champion's piece-square term is formulaic:
`rank`, `fileCenter = min(f, 7-f)` and `center`, combined by ~15 scalar
coefficients. That basis cannot represent a knight being bad on a specific
rim square versus a good rim square, a rook on a specific 7th-rank file, or
square-specific king shelter. A full 6x64x2 table can, and the engine already
indexes `PieceSquareMg[pt][idx]` inside its material accumulator, so the
candidate changes only the numbers in that lookup — no new per-node work.

This is a different feature family from exp-0026 (which added pawn-structure
and coordination *counts*) and from exp-0005/0012 (which re-fitted the existing
scalars, including the formulaic PST coefficients). It is not a neural network,
not incremental-eval bookkeeping, and not a search change.

The risk is honest and pre-registered: 768 free parameters fitted to ~6,000
bullet self-play games can overfit, and a better outcome predictor is not
automatically a stronger fixed-time player. Hence a by-game holdout, a frozen
3% relative log-loss threshold plus a non-worsening Brier requirement, a frozen
NPS band, one fit with no sweep, and one 2,000-game diagnostic screen that is
explicitly NOT the decisive gate. If the accuracy or cost evidence fails, the
candidate is recorded as a negative candidate-development outcome and exp-0047
stays dormant.

## 2026-11-06 — Strength-recovery mission, Phases I–V: exp-0052 king-danger concentration

**Phase I (independent audit).** exp-0051 was re-audited from raw per-game JSONL
with a NEW auditor (`scripts/recovery_independent_audit.py`), not by re-running
the summary script that produced the reported numbers. Verdict **VALID**:
combined 373/389/1230 over 992 opening clusters, CR1 **−159.54
[−173.45, −146.10]**, design effect 1.0, 2,800/2,800 PGN moves replayed, 0
forfeits, all 50 blob digests and 40 sums verified, 6 suite intersections 0.
**CLOSED / NEGATIVE stands.** Two initial auditor findings were diagnosed as
auditor false positives (the repo's `_t95` is conservative for df>120; the
tournament shuffles openings with the job seed) and fixed, not used to overturn
a negative result. Report: `docs/STOCKBEAR_RECOVERY_AUDIT.md`.

**Phase II (bottleneck).** `evaluate()` 166.5 ns/call ≈ 33% of node time;
**median depth 5 at 40+4 ms**. A free evaluation would buy ~1.37x nodes ≈ +41
Elo, while +75 needs 1.78x — so speed alone cannot reach Gate 1. Core diagnosis:
king danger is `KingDanger<pt> x popcount(attacks & KingZone)`, **linear in each
attacker count**, giving ceilings 6/21/69/103 cp with a CONSTANT marginal cp per
attacker. Concentration can never be punished super-linearly at any parameter
value. That is a representational limit, not a mis-tune.

**Phase III (directions).** Three conceptually distinct directions ranked by
expected research value in `docs/STOCKBEAR_RECOVERY_RESEARCH.md`: (1) non-linear
king-danger concentration, (2) threat/hanging-piece awareness (no threat term
exists at all), (3) attack-set dedup as runtime *funding*, explicitly not a gate
strategy. Learned evaluation stays ruled out by measurement (NNUE −652/−720,
distillation −30.6, learned PST −159.5), not by fashion. External anchors:
MadChess 2.0 **+27**, MadChess 3.0 **+63** but confounded (2min+1s, bundled with
an aspiration-window change); SF's +2 Elo deltas are NOT transferable because SF
already has non-linear danger. **No single eval term credibly reaches +75.**

**Phase IV (implementation).** ONE appended param `KingSafetyQuadratic`, shipped
0, default-OFF bit-exact (all three signatures unchanged, and the dev5 artifact
re-run reproduces all three). Weights {N2,B2,R3,Q5}, curve `min(u,32)^2/16`,
middlegame-only, per-side queen gate. Units accumulate inside the EXISTING
king-danger loop: the first prototype recomputed attacks and cost ~20% of eval;
fusing cut it to a paired, A/A-calibrated **+0.65%**. A second bundled knob
(`KingSemiOpenFile`) was REMOVED because two knobs repeat exp-0026's attribution
failure.

**Scale is the exp-0049 lesson, applied pre-game.** A criterion was declared
before any game (p99 |delta| <= 120 cp AND RMS < 40 cp, against the smallest
pruning margin of 85 cp). Divisor-8/coef-6 measured RMS **187.85 cp** — worse
than exp-0049's 111.83 that lost 160 Elo — and was REJECTED. Divisor-16/coef-1
still failed p99 (138). The criterion was **not relaxed**; the cap was tightened
to 32 units (the p99 of the observed per-side distribution), giving RMS **13.87**,
p99 **56**, max **64 cp**, sd ratio 1.0072. This deliberately lowers the expected
effect size in exchange for an attributable result.

**Verification.** ctest 15/15; ASan+UBSan 15/15; independent python-chess oracle
1,000 positions 0 mismatches; breakdown invariant 3,997 positions 0 mismatches;
liveness 10/11 trees change. Three mutants physically applied and all KILLED
(never-applied, linear curve, queen-gate removed) — the last two initially
SURVIVED, so shape and gate assertions were added with oracle-derived pins.

**Two instrument defects found and fixed at zero games.** (a) The `king_safety`
group had no `add_test()` entry, so **ctest reported 14/14 PASS while the test
binary reported a failure**. (b) `EvalParams` has the SAME silent-fallback hole
`PstFile` had: a missing file emits "could not load" and returns, playing on with
the previous table — which would fake a result. The runner's load assertion now
covers every file-valued option, per arm, with positive `LOAD VERIFIED` proof.

**Phase V (frozen screen).** `docs/DEV6_PREREG_EXP0052.md`, SHA
`c3a022d5686d4d5485f890ea23884dcc10e36e209e5a9902626c2a505f74d578`. Arm B is the
**exact released dev5 artifact**, not a local ablation. 1,600 fresh openings,
seed 2026110652, independently re-verified (0 overlap vs 51,241 earlier positions
in 182 files, all 10 slice pairs disjoint). A dedicated 400-game
**baseline-equivalence** job makes attribution honest: if candidate-default is
not play-equivalent to dev5, the batch effect may not be claimed as this knob's.
SCREEN rules: ADVANCE >= +20 with LCB > 0; CLOSE if UCB < +10; else INCONCLUSIVE.
**This is not a Gate-1 run and cannot satisfy Gate 1.** Gates: 1 UNMET,
2 direction-supported, 3 PASS, 4 UNMET. Mission ACTIVE; exp-0047 DORMANT.

## 2026-11-06 — exp-0053: threat / material-exposure detection (Direction 2)

**Gate clarified.** The user withdrew the interim dev4 wording as carry-over
context and reconfirmed the dev6 gate: combined point >= +75 AND two-sided
opening-clustered 95% LCB strictly > +50 vs the exact released dev5 champion.
Recorded in `STOCKBEAR_COMPLETION_CHECKLIST.md` §0.1. The in-repo dev4 binary is a
verified rebuild from tag `v0.1.0-dev4`, not a downloaded release asset; the user
asked for the published asset to be fetched and checksum-verified, which is
tracked as an open checklist item (§0.2).

**A measured dead end, recorded because it changed the design.** Direction 3
(shared attack infrastructure) was implemented first as a per-square attack table
built once per evaluate() and shared by both features() calls. It was BIT-EXACT
(all three signatures, ctest 15/15) but measured **~19.5% SLOWER** over 90 paired
blocks in two independent runs: writing and reloading 512 bytes per call costs
more than the magic-lookup recomputation it removes. Removing the 544-byte
zero-initialisation did not rescue it. **Reverted.** The lesson is that attack
generation is not the bottleneck it appears to be in a profile; memory traffic
is. The first A/A control for this measurement was too wide (0.1214) and was
NOT used to claim a number; the conclusion rests on two consistent runs whose
effect (~+19.5%) exceeded the noise.

**exp-0053 mechanism.** StockBear had NO threat term. Added ONE appended param
`ThreatDetection` (shipped 0): units = min(10*|hanging| + 16*|pawnThreat|, 64),
where hanging = enemy non-pawn pieces attacked by us and NOT defended by them,
and pawnThreat = any enemy piece attacked by our pawn. Applied to mg AND eg.
Cost design carries the dead end forward: the union masks are accumulated with a
few ORs INSIDE the existing mobility and king-danger loops, and the term itself
is pure popcount work. Measured cost **+1.97%** (A/A control 0.0598).

**Verification.** All three signatures bit-exact; ctest **16/16** with `threats`
confirmed registered as test #8 and the binary run directly (exit 0, 8 tests, 0
failures); ASan+UBSan **16/16**; independent python-chess oracle **800 positions,
0 mismatches**; breakdown invariant **3,997 positions, 0 mismatches** with the
term ON and OFF (the breakdown path uses an INDEPENDENT union builder, so this
really cross-checks the fusion); liveness **11/11** trees change.

**Mutation testing was decisive again.** Seven mutants physically applied and
**all seven KILLED**, zero survivors: never-applied, defended-mask removed, pawn
component removed, hanging component removed, cap removed, pawns counted as
hanging targets, sign flipped. Test FENs were derived from the oracle by searching
for positions that discriminate ONE component each (e.g. two attacked but
DEFENDED enemy pieces must score 0; a both-sides-over-cap position must score 0
where uncapped would give -10). No hand-labelled diagrams.

**One test assertion was wrong and was corrected on the merits, not to pass.**
An invented strict bound `v < VALUE_KNOWN_WIN` failed at coefficient 400.
Inspection showed `taper()` clamps INCLUSIVELY to +/-10000, a heuristic bound far
below MATE_BOUND (~29900), so reaching exactly 10000 is the pre-existing clamp
working. The assertion was replaced with the true invariant (inclusive bound
plus no mate encoding, at both sign extremes) and an added check that the frozen
coefficient stays far from the clamp.

**Scale.** Criterion pre-declared before measurement (p99 <= 120 cp, RMS < 40 cp).
Measured RMS **16.88**, p99 **46**, max **64**, sd ratio 0.9981 -> PASS on the
first attempt, so no rescaling and no post-hoc criterion adjustment.

**Frozen screen.** Prereg `docs/DEV6_PREREG_EXP0053.md` SHA
`6049ef7fd044fad15418e453e7ec6cbc51022dd9954835869cdbe49c44e66722`. Arm B is the
exact released dev5 artifact. `KingSafetyQuadratic` is absent from the candidate
file and therefore 0, so exp-0052's feature is OFF and attribution is to threats
alone. 1,600 fresh openings seed 2026110653, independently verified 0 overlap
against 52,841 earlier positions in 188 files, all 10 slice pairs disjoint.
SCREEN rules: ADVANCE >= +20 with LCB > 0; CLOSE if UCB < +10; else INCONCLUSIVE.
**Not a Gate-1 run.** Mission remains ACTIVE and is governed solely by
`STOCKBEAR_COMPLETION_CHECKLIST.md`.
