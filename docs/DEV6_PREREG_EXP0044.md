# exp-0044 — SEE-losing-capture ordering (FROZEN before ANY evaluation game)

Registered before ANY exp-0044 evaluation game. `docs/DEV6_PREREG.md` §8 is
UNCHANGED: Gate 1 still requires a >= +75 Elo point AND a combined two-sided
opening-clustered 95 % LCB > +50 on two independent preregistered FIXED-TIME
batches (§8 names exp-0028 + exp-0029), both positive, no material
contradictory regression and reasonable consistency; Gate 2 direction-supported
by both independent datasets; Gate 3 nulls compatible with zero; Gate 4 the
exact packaged final-candidate binary/source/CI linkage and no
correctness/illegal-move/protocol/time-forfeit regression or unexplained
benchmarked-vs-packaged-binary difference. No gate, threshold, margin or
tolerance is weakened. This document is experiment-level only.

## 1. Why this direction (post-exp-0043 re-ranking)
exp-0043 (TT-evidence singular extension) CLOSED/ABANDONED at
`−10.3142 [−20.8915,+0.2440]` on 1,994 games, with a mechanism that was
PROVEN LIVE on 23/24 suite positions at 40+4 ms but cost +13.9 % fixed-depth
nodes. Together with exp-0041 (`−5.0635`, −42.1 % nodes) and exp-0042
(`+2.6110` / `−10.8281`, tighter qsearch pruning), THREE consecutive
mechanisms that change WHICH nodes are searched or ADD a ply at non-PV nodes
have lost at fixed time. The only positive fixed-time directions remain
exp-0036 `+21.5238 [10.2819,32.8108]` (prune SEE-losing captures at shallow
main-search depth) and exp-0038 `+7.6755 [−1.0670,+16.4278]` (qsearch
information reuse). Both change decisions WITHOUT buying a new subtree.

`docs/DEV6_RESEARCH_MATRIX.md` therefore re-ranks **move-ordering ACCURACY
with measured ZERO per-node overhead** to NEXT. Reading `Search::score_moves`
reveals a concrete, previously untested deficiency: a capture whose SEE is
negative is scored at `2000000 + 32*gain + seeScore` ≈ 2,000,000, i.e. ABOVE
killers (1,500,000 / 1,490,000), countermoves (1,485,000) and EVERY quiet
history move (|history| <= 60,000). Losing captures are therefore searched
immediately after winning captures at every main-search node, before any
killer or high-history quiet. Strong engines order bad captures LAST. This is
a genuine structural observation about the code, not a parameter tweak.

## 2. Hypothesis
At a ~4 ms increment, spending the first moves of a node on material
concessions wastes the tiny budget. Demoting SEE-losing captures to the tail
lets the TT move, winning captures, killers and high-history quiets raise
alpha earlier, producing more cutoffs and better tactical/PV accuracy. exp-0036
already showed that SEE-losing captures are low-value at shallow fixed-time
depth (+21.5 Elo when they were pruned at depth <= 3); ordering them last is a
strictly milder intervention — NO move is removed — and should capture part of
that benefit without the deep-sacrifice risk that killed exp-0041 (which
extended the PRUNING to all depths). Unlike exp-0043 it adds NO extra ply and
NO per-node work.

## 3. Exact code change (default OFF)
- `SearchParams::badCaptureOrdering = false`; UCI `BadCaptureOrdering`;
  `bench --param badCaptureOrdering=0|1`.
- `Search::score_moves` gains an explicit `bool mainSearch` argument: `false`
  from `quiescence`, `true` from `negamax`. In the capture branch, when the
  switch is ON, `mainSearch` is true, `seeScore < 0` and the move is NOT a
  promotion, the score becomes `BadCaptureOrderScore + 32*gain + seeScore`
  with the FROZEN constant `BadCaptureOrderScore = -2000000`. That is below
  every quiet/killer move and above nothing; the hash move (4,000,000),
  killers, countermoves and good captures are untouched by the first/other
  branches of the scorer.
- **NO move is skipped.** `futilityCandidate`, `lmrCandidate` and
  `moveCountPruning` all require `isQuiet`, so a demoted capture is still
  searched at full depth; only its ORDER changes. **NO SEE or evaluate() call
  is added**: `seeScore` is already computed by the shipped scorer and cached
  by the frozen `-DSB_SEE_CACHE=1` build flag. **NO stand-pat value, mate
  score, check-evasion logic, pruning/extension decision or TT behaviour is
  changed.** QUIESCENCE is explicitly excluded: it already skips SEE<0
  captures under the shipped `seePruning`, so its behaviour is bit-identical.
- Frozen threshold is SEE < 0 (no tunable margin). `BadCaptureMargin=100`
  (exp-0036's pruning margin) and `deltaMargin=200` stay frozen. The canonical
  "genuine re-search" singular extension remains deferred; the
  `FullSoftBudget` / time-allocation family remains REJECT (exp-0004
  forfeit-driven, exp-0040 inert). exp-0044 is NOT a repeat of exp-0036:
  exp-0036 REMOVED moves at depth <= 3; exp-0044 removes nothing anywhere.
- Default-off build is bit-identical: bench `243f9a1c1ba5b36f`, d16
  `a14ab62224f837e5`, d12 params `e45fa2ec2287eb41`; Release ctest 11/11,
  ASan+UBSan ctest 11/11
  (`benchmarks/dev6-baseline/exp0044_asan_ctest.log`); UCI
  `BadCaptureOrdering` default false. Every dev6 strength switch remains OFF.

## 4. MANDATORY mechanism-live and overhead diagnostic (BEFORE games)
Instrumented `SB_BADCAP_DEBUG` build from the FROZEN source, counting every
demoted capture.

- FIXED DEPTH 10, 16 exp-0044 suite positions (deterministic tree):
  OFF 2,655,145 nodes / 0 demotions; ON 2,961,866 nodes / 424,155 demotions,
  LIVE on 16/16 positions. Fixed-depth nodes RISE **+11.6 %** — the ordering
  change alters alpha-beta cutoffs, so total nodes can move either way. This
  is a TREE change, NOT added per-node work; three prior experiments recorded
  that fixed-depth/node-count proxies DO NOT predict fixed-time strength.
- FIXED TIME `go wtime 40 btime 40 winc 4 binc 4`, 24 exp-0044 suite
  positions x 2 repeats: OFF 228,643 / 236,838 nodes, ON 203,245 / 214,462
  nodes, median completed depth 6 for BOTH, 22,024 / 24,413 demotions,
  LIVE on **24 of 24** positions (~950 demotions per search). No loss of
  completed depth.

Interpretation: the mechanism genuinely changes the search order at the EXACT
Tier-1 control, adds ZERO per-node work and does not reduce completed depth.
The +11.6 % fixed-depth node increase is DISCLOSED as a risk (bad captures
occasionally give check or refute quickly, so demoting them can grow the
tree), never spun as a positive. A real 40+4 ms Tier-1 screen decides.

## 5. Frozen Tier-1 screen design
- `.github/workflows/dev6-tier1.yml`, one dedicated GitHub-hosted
  `ubuntu-latest` VM per matrix job, pinned `source_sha`, EXACT packaged
  candidate binary extracted and tested (Gate 4 identity).
- **FIXED TIME `--base-ms 40 --inc-ms 4`**, Hash 16, Threads 1, max-plies 240,
  **never `--nodes`**. Both arms receive identical 40+4 ms clocks.
- ONE binary, single switch: candidate `BadCaptureOrdering=true` vs control
  `BadCaptureOrdering=false`. Zero toolchain confound. Both arms:
  `EvalParams=research-data/params_abc.txt`, `TTEval=true`.
- Stage-0 validity null: 400-game 40+4 ms self-match with CONTROL options on
  both sides, 0 TIME_FORFEIT / 0 illegal / 0 UCI or engine failure, 95 % CI
  includes 0. A second 400-game null with CANDIDATE options on both sides
  checks the enabled switch itself; its CI must include 0. If ANY of the four
  jobs has > 0 TIME_FORFEIT, illegal move or engine failure, exp-0044 is
  INVALID MEASUREMENT and no strength inference is made.
- batchA 1,000 games and batchB 1,000 games on two independent fresh disjoint
  500-opening suites, generated by `scripts/dev6_exp0044_openings.py` with seed
  `2026120301` (1,400 openings total; 200 stage0 + 200 null + 500 + 500);
  programmatic ZERO exact-final-position overlap with **33,441** earlier
  committed positions across 125 earlier files and ZERO duplicates within the
  1,400. Colour-reversed, one pair per opening. Slice SHA-256 values are in
  `benchmarks/dev6-baseline/exp0044_suites.json`.
- Statistics: W/D/L, paired pentanomial, opening-clustered CR1/t two-sided
  95 % CI per batch AND frozen combined, LLR labelled a normal approximation,
  independent recomputation from raw JSONL. No batch selection, no post-hoc
  combining, no threshold changes after results. Combined = batchA + batchB
  ONLY, frozen before the run; the Stage-0 and null games are NEVER pooled in.
- Raw PGN/JSONL/CSV/summaries/audit/fingerprint/manifest/SHA256SUMS/UCI/run.log
  and the exact packaged `.tar.gz` are uploaded per job and mirrored by a
  deliberate `mode=export` job after results.

## 6. Frozen decision rules (before results)
- **ADVANCE to a preregistered FRESH bundle candidate** (measured against exact
  dev5, NEVER a post-hoc sum) only if combined point >= +20 Elo AND combined
  95 % LCB > 0 AND both batches >= −5 AND both null CIs include 0 AND 0
  forfeits/illegal/UCI/engine failures in ALL four jobs. ADVANCE alone does
  NOT satisfy Gate 1.
- **CLOSE (mechanism rejected / abandon)** if combined 95 % UCB < +10 Elo OR
  combined point <= 0. Then `BadCaptureOrdering` stays default OFF and is not
  retuned; no bundle, no default change.
- **INCONCLUSIVE otherwise** -> exactly ONE bounded confirmation run under a
  fresh frozen addendum and a NEW disjoint 1,400-opening suite, committed
  BEFORE those games, with the SAME 40+4 ms design, the SAME rules and its
  OWN Stage-0/null jobs. Screen and confirmation are separate experiments and
  are **NEVER pooled** (exp-0042 precedent). A confirmation CLOSE ends exp-0044.
- Experiment-level rules only. Gate 1 still requires >= +75 with LCB > +50 on
  two independent preregistered FIXED-TIME batches; Gate 4 still requires the
  exact packaged final candidate artifact and CI on its source HEAD. No
  experiment outcome terminates the mission.

## 7. Expected failure modes
A SEE-losing capture can be a real sacrifice, give check, or refute a threat
quickly; searching it later can grow the tree (measured +11.6 % fixed-depth
nodes) and lose tactics. Demotion also changes `moveCount`, which feeds LMR and
late-move pruning thresholds for the quiets that now come earlier, so the
effect is not a pure local reorder. History/killer statistics are updated from
cutoffs, so the ordering change can destabilise later iterations. At 40+4 ms
an increased node count may reduce completed depth despite the diagnostic
showing depth 6 unchanged on 24 probe positions. A node-count change in
EITHER direction does NOT predict fixed-time strength in this project. None of
these justify changing the frozen design after results.

## 8. Non-claims / integrity
No fixed-depth/node-count proxy is presented as fixed-time strength. No
absolute/CCRL/FIDE Elo, no gap-to-3000. No post-hoc stacking, no pooling of
independent runs, no default change before gate satisfaction, no PR/merge/tag/
release/deploy/dev7, no strength claim. Closed exp-0041/0042/0043 data are
NEVER reused or pooled. The immutable dev5 baseline
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`, `main`,
and all historical evidence remain untouched.
