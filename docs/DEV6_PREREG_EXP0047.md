# DEV6 exp-0047 — FROZEN preregistration (DORMANT / NOT ACTIVATED)

**Status:** FROZEN DESIGN, **NO GAMES AUTHORISED**. This document is a complete
preregistration for the next decisive DEV6 strength experiment. It is deliberately
written *before* any implementation or benchmark game. Its activation condition
(§3) is **not met at HEAD `d07294d7dbd3a88e5b673f048aeb6a7b1acc1dbf`**, so no
experimental change may be implemented, no opening suite may be generated, no
`tier1-dispatch.json` may be edited to `mode=benchmark`, and no strength game may
be played under this prereg. A normal closed/inconclusive/negative result does
not terminate the mission; this prereg does not claim otherwise.

**Frozen at:** branch `arena/3e6dd5b6-stockbear`, source HEAD
`d07294d7dbd3a88e5b673f048aeb6a7b1acc1dbf`, CI `41826927521` SUCCESS.
**Authoritative acceptance criteria:** `docs/DEV6_PREREG.md` §8 (Gates 1–4,
quoted verbatim in `docs/DEV6_EXP0047_INVESTIGATION_REPORT.md` §2). No criterion
from an earlier development version (in particular the `ADVANCE >= +20` /
`CLOSE if UCB < +10` Tier-1 screen rule of exp-0037…0046) is transplanted here.
**This file's own SHA-256 is recorded in the investigation report and the
failure ledger at activation time.** Nothing in it may be changed after the
first benchmark game; changes require a new experiment ID and a new prereg.

---

## 1. Hypothesis and causal mechanism

**H (single, pre-registered):** a candidate built from this source tree, with
**exactly one** frozen experimental configuration enabled, is at least **+75 Elo**
stronger than the exact released v0.1.0-dev5 artifact at fixed time 40+4 ms, with
a two-sided opening-clustered 95 % CI lower bound strictly greater than +50.

**Causal mechanism (must be supplied and independently evidenced at activation,
§3):** the ONLY credible mechanism not already foreclosed at this HEAD is a
*materially stronger evaluator* — i.e. a candidate whose evaluation predicts
bullet-time game outcomes materially better than the champion 38-parameter
classical evaluator at comparable or lower per-node cost. A speed-only change, a
single search switch, a re-tune, or a post-hoc stack of previously measured
switches is **explicitly excluded**: `docs/DEV6_POWER_ANALYSIS.md` §40–41 states
that sample size is not the binding constraint and that the binding constraint is
a candidate with a true gain >= +75; every measured single-switch candidate in
this cycle has point estimate <= +21.52 and 95 % UCB <= +32.81 (exp-0036).

The activation record (§3) must name the exact mechanism, the frozen source
diff, and the pre-result evidence linking the evaluator-accuracy measurement to
an expected fixed-time Elo effect. No post-hoc justification is permitted.

## 2. Exact scope

- ONE candidate, ONE baseline, ONE experimental configuration, ONE decisive
  measurement. No adaptive tuning, no best-of-N selection, no parameter search,
  no bundling of separately measured switches, no sample extension.
- The candidate's experimental functionality MUST be default-OFF. The OFF build
  MUST be bit-identical to the current default on all three frozen bench
  signatures (`243f9a1c1ba5b36f`, `a14ab62224f837e5`, `e45fa2ec2287eb41`) and on
  the full 12-row fixed-node bench CSV (timing columns excluded).
- No unrelated refactor: no changes to the time manager, tournament driver,
  adjudication, clock, statistical code, opening generator protocol, or any
  default-ON behaviour. Driver/plan changes needed solely to identify the two
  engines are in scope and must be recorded byte-for-byte.
- `AdaptiveNullR`, `SkipDeadTTEval`, `BadCaptureOrdering`, `BadCapturePruning`
  and every other existing experimental switch stays default-OFF unless the
  activation record explicitly names it as THE single candidate mechanism (in
  which case its own prior closure must not be contradicted — see §3).

## 3. ACTIVATION CONDITION (frozen, measurable, no games before it is met)

All four must be recorded, with file paths and hashes, in an append-only
*Activation Record* committed in the same commit as the first benchmark plan:

1. **Evaluator-accuracy evidence:** a fresh, bullet-matched (40+4 ms) self-play
   corpus generated on isolated runners with a frozen seed, DISJOINT from all
   prior suites (§8), plus a pre-registered accuracy/calibration comparison
   showing the candidate evaluator predicts outcomes materially better than the
   champion classical evaluator. The accuracy metric and its threshold must be
   frozen BEFORE the corpus is generated.
2. **Cost evidence:** matched-toolchain fixed-depth NPS of the candidate
   evaluator within `[0.97, 1.03]` of the current default (or a pre-registered,
   power-analysis-justified larger allowance), measured with bit-identical node
   counts and >= 3 alternating repetitions. A candidate that is materially slower
   cannot be assumed to convert accuracy into fixed-time Elo.
3. **Expected-effect evidence:** a pre-result argument, from (1) and (2) and the
   historical NPS→Elo and accuracy→Elo evidence in `benchmarks/FAILURE_LEDGER.md`,
   that the candidate's true fixed-time effect is compatible with >= +75 Elo.
   "Plausible direction", "profiling shows a hotspot", or "the CI might include
   +75" do NOT satisfy this condition.
4. **Non-repetition check:** the activation record must state that the mechanism
   is not one of the directions explicitly closed in
   `benchmarks/FAILURE_LEDGER.md` (exp-0001 small CPU NNUE, exp-0013 incremental
   eval, exp-0026 six extended features, exp-0033 razoring, exp-0036 whole-screen
   re-run / stacking / tuning, exp-0038 qsearch TT, exp-0039/0040 profiling
   eliminations, exp-0041…0046) and not a repeat of the exp-0030 +33 control on
   mismatched toolchains.

If any condition is unmet, this prereg stays DORMANT: **zero games**, no invalid
measurement, no data to discard. Activation is a scientific precondition, not a
formality, and may NOT be satisfied by lowering the +75 / +50 thresholds.

## 4. Baseline / candidate identity

| role | identity |
|---|---|
| Baseline B | exact immutable released dev5 artifact `benchmarks/binaries/stockbear-dev5-release`, SHA-256 `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918` (NEVER rebuilt, renamed or described as a rebuild) |
| Candidate A | single binary built from the exact activation commit with `-DCMAKE_BUILD_TYPE=Release -G Ninja -DCMAKE_CXX_FLAGS="-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4"`, no `-march=native` |
| Champion runtime (BOTH sides) | `EvalParams=research-data/params_abc.txt` (SHA `8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be`), `TTEval=true`, Hash 16 MB, Threads 1 |
| A-only options | the single frozen experimental configuration named in the Activation Record; nothing else |
| Binary identity | built SHA-256 == packaged SHA-256 == SHA-256 recorded in every job's `fingerprint.json`; UCI option defaults dumped for both engines |

Track-B caveat, carried unchanged from exp-0030: B was built in the
ubuntu-22.04 release image while A is built on the runner image. Track A
(both source trees rebuilt in ONE pinned toolchain) is the controlled
source-level comparison; Track B is measured SEPARATELY. Any A-vs-B Elo is
therefore a *packaged-artifact* comparison and must never be silently
reinterpreted as a pure source-level gain. The `+33.0 [+13.7,+52.5]`
mismatched-toolchain control remains an INVALID MEASUREMENT for that purpose
and is NOT pooled or re-run here.

## 5. Benchmark protocol (unchanged from the mission's fixed-time conditions)

- FIXED TIME `--base-ms 40 --inc-ms 4`; `--nodes` NEVER used; `--max-plies 240`.
- Hash 16, Threads 1; paired colour-reversed openings, one opening = one cluster.
- GitHub-hosted isolated `ubuntu-latest` VMs, ONE job per VM, no shared local
  sandbox for decisive games; `mode=benchmark` launched only by a deliberate
  `benchmarks/exp-runs/tier1-dispatch.json` push with plan + prereg + code +
  suites frozen in the SAME commit.
- Stage 0 validity job (A options vs A options on the SAME binary) and candidate
  null (identical configuration both sides) are mandatory and are NOT pooled
  into the primary estimate.
- Driver: `scripts/dev6_tier1_job.py` with `engine_a=candidate`,
  `engine_b=baseline`; Stage-0 A control options must be set explicitly (the
  driver's `null=true` copies A options to both sides).

## 6. Primary / secondary metrics

- **Primary:** two-sided opening-clustered CR1/t 95 % CI and point Elo for the
  combined batchA+batchB candidate-vs-baseline games, computed from raw
  `match.jsonl` W/D/L and score; Elo-from-score cross-check; bootstrap CI
  cross-check. Clustered by opening pair (paired colour reversal).
- **Secondary:** per-batch point/CI/W-D-L; Stage-0 and candidate null CIs;
  terminations (illegal moves, crashes, UCI failures, TIME_FORFEIT,
  UNADJUDICATED_MAX_PLIES); node/NPS diagnostics; binary and suite hashes;
  audits. Secondary metrics are diagnostic only and never substitute for the
  primary.

## 7. Fresh disjoint suites

A generator with a NEW frozen seed creates two disjoint batch suites plus
Stage-0/null suites. It MUST assert: zero overlap with all earlier opening files
(`benchmarks/positions/*.txt`, all `benchmarks/dev6-baseline/*suites*.json`),
zero duplicates within the new suites, and exact slice hashes recorded in a
committed suites JSON. Suites may never be reused between experiments; no
pooling with exp-0028/0029 or exp-0030…0046 data under any circumstances.

## 8. Sample size and compute budget (single-run bound)

- **6,600 games per independent batch, 13,200 combined** (plus Stage-0 and
  candidate null), i.e. the mission's decisive design. From
  `docs/DEV6_POWER_ANALYSIS.md`: 13,200 games give a conservative half-width of
  ~5.2 Elo (carrying exp-0024's cluster effect), sufficient to distinguish a
  true +75 with LCB > +50 from a null effect. ~576 games would suffice to reject
  +75, so this budget is deliberately conservative, NOT a binding constraint.
- Compute bound: ONE benchmark run on the frozen activation commit. Shard into
  isolated jobs as needed; the number of shards, seeds and suite slices are
  frozen in the plan BEFORE launch. **NO sample extension, NO second run, NO
  post-hoc increase, NO confirmation batch beyond the two frozen batches.**

## 9. Validity criteria (all required; any failure invalidates the measurement)

1. ZERO TIME_FORFEIT, illegal move, crash, UCI failure in **ANY** job (the
   exp-0045 rule, unchanged and NOT weakened).
2. All `SHA256SUMS.txt` entries OK in every exported bundle; built == packaged
   binary; dev5 SHA-256 matches §4.
3. Frozen default bench signatures identical for the candidate; default-OFF
   verified by UCI option dump.
4. Stage-0 and candidate null two-sided 95 % CIs both include 0.
5. Matched-toolchain fixed-depth NPS ratio inside `[0.97,1.03]`.
6. Suite disjointness proof with exact hashes; exact game counts recorded.
7. Independent raw-game audit (>= 44 stored values) with ZERO issues; driver's
   independent W/D/L/score/Elo/CI recomputation agrees with stored values.

## 10. Invalid-run handling and retry

Any violation of §9 makes the ENTIRE run an **INVALID MEASUREMENT**: all its
Elo, CIs, W/D/L, LLR, scores and cluster statistics are DISCARDED, never
quoted, never pooled. The generic `scripts/dev6_exp0038_audit.py` "INCONCLUSIVE
(more samples)" default is NOT a decision rule here.

**RETRY: NOT AUTHORISED by this prereg.** A bounded retry requires a separate
addendum frozen and committed BEFORE the first game, with its own fresh disjoint
suite, own frozen rules, own attempt number, and an explicit statement of the
maximum number of valid runs. No retry may be invented after seeing a result.

## 11. FROZEN decision thresholds (from `docs/DEV6_PREREG.md` §8, NOT the +20 screen)

Let `p` = combined point Elo, `[L,U]` = combined two-sided opening-clustered
95 % CI, and `clean` = all §9 criteria pass.

- **ADVANCE** iff `clean` AND `p >= +75` AND `L > +50` (strictly) AND both batch
  point estimates are positive AND neither batch shows a material contradictory
  regression AND the batches are reasonably consistent (overlapping CIs) AND
  Gate 3 nulls compatible with zero AND Gate 4 has no unresolved
  correctness/illegal-move/protocol/time-forfeit regression or unexplained
  benchmarked-vs-packaged difference.
- **CLOSE** iff `clean` AND `U < +50` (futility), OR any frozen correctness
  regression is demonstrated. A CLOSE result is a genuine negative result, not a
  reason to retune, restack or relaunch.
- **CLOSED AS INCONCLUSIVE** iff `clean` AND neither ADVANCE nor CLOSE holds at
  the §8 single-run compute bound. **NO further samples.**
- If `clean` is false, the run is INVALID (§10), not INCONCLUSIVE.
- ADVANCE alone does NOT declare the mission COMPLETE: every one of Gates 1–4
  must be independently verified, including the exact candidate release
  artifact being the tested binary, before any strength claim, PR, merge, tag,
  release, deploy or dev7.

## 12. Independent audit and reproducibility

- All four (or N) job bundles exported via `actions/download-artifact(run-id)`
  into `benchmarks/exp-runs/tier1-export/run-<run-id>/`, with
  `export_manifest.json`, `fingerprint.json`, raw `match.jsonl`, PGN, CSV,
  `uci.txt`, `run.log`, `SHA256SUMS.txt`.
- An experiment-specific decision script reads ONLY the raw `match.jsonl`
  files, independently recomputes W/D/L, score, clustered CR1/t Elo/CI,
  terminations and the §11 rule, and prints ADVANCE / CLOSE / INCONCLUSIVE /
  INVALID. It must reproduce the report's verdict exactly and expose
  `clean`, `nulls_ok`, `batches_ok`.
- Exact commit SHA, binary SHA-256s, prereg/plan/suite SHA-256s, benchmark run
  ID, export run ID and CI run IDs recorded in the report, matrix, ledger and
  append-only logs. No pooling unless explicitly preregistered (here: NONE).
- Nothing in §§1–12 may be silently changed. Any change requires a new
  experiment ID and a new frozen prereg before any game.

## 13. Activation Record (TO BE FILLED; currently EMPTY — experiment DORMANT)

| field | value |
|---|---|
| activation commit SHA | *(empty — not activated)* |
| activation date | *(empty)* |
| mechanism / source diff hash | *(empty)* |
| evaluator-accuracy evidence path + hash | *(empty)* |
| cost evidence path + hash | *(empty)* |
| expected-effect argument | *(empty)* |
| non-repetition statement | *(empty)* |
| prereg SHA-256 at activation | *(empty)* |
| plan SHA-256 / suite seed / dispatch attempt | *(empty)* |
| first benchmark game timestamp | *(empty — no games)* |
