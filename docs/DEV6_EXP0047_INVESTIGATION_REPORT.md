# StockBear DEV6 — Evidence-driven research and next experiment (verifiable report)

**Date:** 2026-11-04 (Asia/Bangkok) · **Branch:** `arena/3e6dd5b6-stockbear`
**Starting and ending HEAD:** `d07294d7dbd3a88e5b673f048aeb6a7b1acc1dbf` (no
engine source change made in this turn) · **CI on that SHA:** `41826927521`
SUCCESS · **Mission: ACTIVE / NOT COMPLETE**

**Headline finding:** after the full authoritative read-back, a fresh gprof
profile of the actual source, a matched-toolchain NPS measurement, and a
re-verification of the frozen audits, **no further engine-strength experiment is
scientifically defensible at this HEAD**. The reason is not "a hypothesis
failed"; it is that every measured candidate is already bounded far below the
mission's primary threshold, the mission's own power analysis says sample size
is not the binding constraint, and the only untried route (a materially stronger
evaluator) lacks three specific pieces of pre-result evidence. Accordingly
**zero strength games were played**, no experimental source change was made, and
no existing decision was reopened. A complete, frozen preregistration for the
next decisive experiment (`docs/DEV6_PREREG_EXP0047.md`) was written and is
**DORMANT** pending those measurements. This is the "explain the missing
evidence rather than invent a promising hypothesis" outcome requested in Phase 2.

---

## 1. Verified starting state (commands and evidence)

| check | verified value |
|---|---|
| `git rev-parse HEAD` | `d07294d7dbd3a88e5b673f048aeb6a7b1acc1dbf` |
| branch | `arena/3e6dd5b6-stockbear` (active) |
| `git status --short` | empty before this turn's new documentation |
| `git ls-remote origin arena/...` | `d07294d…` (local == remote) |
| `origin/main` | `6e7c2e02881faf93a84990a8345c41ad28bcae11` (untouched) |
| last CI on exact HEAD | `41826927521`, conclusion SUCCESS |
| dev5 immutable binary | `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`, intact |
| `find . -name AGENTS.md -not -path './.git/*'` | none |
| PR / merge / tag / release / deploy / dev7 | none |
| `benchmarks/exp-runs/tier1-dispatch.json` | left UNCHANGED: `mode=export`, exp0046, `source_run_id=41825055840`, attempt 25 |

Read in full or in relevant sections: `docs/DEV6_PREREG.md` (§8),
`docs/DEV6_PREREG_BASELINE.md`, `docs/DEV6_CONFIRMATION.md`,
`docs/DEV6_CONFIRMATION_REPORT.md`, `docs/DEV7_CONFIRMATION.md`,
`docs/DEV6_3000_ROADMAP.md` (M0–M5), `docs/DEV6_RESEARCH.md`,
`docs/DEV6_TIER1_INFRASTRUCTURE.md`, `docs/DEV6_REPORT.md`,
`docs/DEV6_POWER_ANALYSIS.md`, `docs/DEV6_CURRENT_STATUS.md`,
`docs/DEV6_STATUS_REPORT.md`, `docs/DEV6_POST_AUTHORIZATION_REPORT.md`,
`docs/DEV6_EXP0036_REPORT.md`, `docs/DEV6_EXP0045_REPORT.md`,
`docs/DEV6_EXP0046_REPORT.md`, `docs/DEV6_RESEARCH_MATRIX.md` (all ranked
alternatives sections), `benchmarks/FAILURE_LEDGER.md` (all 60 headings), the
append-only `AGENTS_LOG.md` / `DESIGN_LOG.md` / `CHANGELOG.md`, the Tier-1
workflow and driver, all plan/suite/dispatch JSON, and the search / evaluation
/ TT / UCI / bench implementation files.

## 2. Authoritative Gate 1 and Gate 4 definitions (verbatim, §8)

From `docs/DEV6_PREREG.md` §8 "Success and failure thresholds (frozen; not
weakened after results)":

> **Gate 1 (primary)**: COMBINED (exp-0028 + exp-0029) point estimate >= +75 Elo
> AND combined two-sided opening-clustered 95% CI lower bound **strictly > +50**;
> BOTH batches show a positive point estimate; neither shows a material
> contradictory regression; the two batches are reasonably consistent.
> **Gate 2**: combined result supported by both independent pre-registered datasets.
> **Gate 3**: nulls compatible with zero.
> **Gate 4**: no unresolved correctness/illegal-move/protocol/time-forfeit
> regression; no unexplained difference between benchmarked and packaged binary.
> The exact candidate release artifact must be the tested binary.
> If ANY gate is unmet -> **FAILURE / gate not met**: no strength claim, no PR,
> no merge, no tag, no release. Results still preserved and reported in full.

Two clarifications that matter for this report:

- The baseline is the **exact released v0.1.0-dev5 portable artifact** with
  champion runtime `params_abc.txt` + `TTEval=true`, Hash 16, Threads 1
  (`docs/DEV6_PREREG_BASELINE.md`). The historical +50-vs-dev4 criteria in
  `docs/DEV6_CONFIRMATION.md` / `DEV7_CONFIRMATION.md` are explicitly superseded
  and are NOT the current mission. Likewise, the Tier-1 `ADVANCE >= +20` /
  `CLOSE if UCB < +10` screen rule (exp-0037…0046) is an experiment-level
  futility screen and is NOT a Gate-1 acceptance criterion.
- **Documentation drift noted, not silently used:** `docs/DEV6_CURRENT_STATUS.md`
  and `docs/DEV6_POST_AUTHORIZATION_REPORT.md` describe Gate 2 as "direction
  supported by both independent preregistered datasets", while
  `docs/DEV6_CONFIRMATION_REPORT.md` evaluated `gate2_both_batches_positive` as
  FAIL for the decisive six-feature candidate. Since Phase 1 asks for the exact
  definitions of Gates **1 and 4**, both of which are quoted verbatim above and
  are unaffected by this ambiguity, no gate verdict is inferred from the
  secondary wording. Gate 3 is independently PASS from nulls that include zero.

**Current gate status (unchanged by this turn):** Gate 1 UNMET/FAIL for every
candidate measured; Gate 2 direction-supported for exp-0036 only (not a gate
pass); Gate 3 PASS; Gate 4 UNMET (no final candidate release artifact exists,
and "the exact candidate release artifact must be the tested binary" is
unsatisfied). No absolute/CCRL/FIDE Elo and no gap-to-3000 claim exists.

## 3. Complete hypothesis / experiment inventory (append-only, nothing reopened)

All entries below are preserved from `benchmarks/FAILURE_LEDGER.md`,
`docs/DEV6_RESEARCH_MATRIX.md`, `docs/DEV6_REPORT.md` and the experiment
reports. "Invalid" means discarded measurement, "Closed" means a frozen
decision that is not reopened here.

**dev5 development cycle (baseline = dev4; NOT the dev6 mission):** exp-0001
small CPU NNUE (−650…−760 Elo, 4× slower) REJECTED; exp-0002 cp distillation
REJECTED; exp-0003 search ablations REGRESSION; exp-0004 FullSoftBudget
forfeit-driven REJECT; exp-0005/0012 outcome/bullet tuning plateau ≈ +40…+48
ECHEV vs dev4, needed ≈ +54; exp-0006 compile-time search knobs; exp-0007
qsearch-lite REGRESSION (eval quality in qsearch dominates); exp-0008 PGO /
mtune NEUTRAL; exp-0009 TT packing / pow2 / THP NEUTRAL; exp-0010 ISA flags
+12–20 % NPS but only ≈ +3.6 Elo at 40+4 (KEPT but insufficient); exp-0011
option flips (disabling any default-ON pruning/extension/ordering regressed
2–83 Elo); exp-0013 incremental eval −27 % NPS REJECTED; exp-0014 dev6 switch
ablations; exp-0015 half-clock/2×-clock diagnostics (lever identification only,
later INVALID as a strength measurement); exp-0016/0017 historical "dev6/dev7"
confirmations vs dev4 — INVALID MEASUREMENT for the current mission (wrong
baseline/gate/cycle); exp-0018 sandbox wipe (infrastructure); exp-0019 margin /
aspiration-window UCI options + screens; exp-0020 larger tuning corpus
(incomplete after wipe); exp-0021 `-march=native -flto` POSITIVE but
toolchain-induced, later INVALID as strength; exp-0022 zero-default eval
features; exp-0023/0024 dev5-cycle "GATE PASSED" vs dev4 (superseded).

**Current dev6 cycle:** exp-0025 baseline provenance (verification);
exp-0026 six extended pawn/coordination features — decisive **−17.0
[−21.4,−12.6]** over 13,200 games vs exact dev5 (batch A −17.8, B −16.2),
left zero-gated; exp-0027 `openings_dev4` screens (diagnostic only);
exp-0028/0029 decisive confirmation (the −17.0 result above); exp-0030
reproducible build/Track A/B integrity — E1 signature PASS, E2 12/12 bit-exact
CSV, E3 A2/A1 NPS 0.9765, B/A1 0.9906, E4 local control −22.6 with 5
TIME_FORFEIT (shared-clock noise), E5 PASS: **the +33 Elo control is confirmed
toolchain-induced; do NOT repeat it on mismatched toolchains**; exp-0031/0032/
0032b external ladder (M0.2, subject ordering INCONCLUSIVE); exp-0033 razoring
−25.88 REJECTED; exp-0034/0035 SEE bad-capture pruning pilot/confirmation
(+20.49 / +27.10, FIXED NODE only); exp-0036 FIXED-TIME Tier-2 dedicated **core**
+21.52 [+10.28,+32.81] vs exact dev5, both batches positive, 0 forfeits, 201/0
audit, **CLOSED at frozen futility UCB < +50** with explicit "do NOT re-run the
whole-screen 40+4 ms confirmation this cycle; do NOT stack with another switch
post hoc; do NOT tune `BadCaptureMargin`; do NOT enable by default before
isolated-runner confirmation"; exp-0037 ProbCut +3.78 CLOSED; exp-0038 qsearch
TT +7.68 CLOSED; exp-0039 dead static eval on TT hits ELIMINATED AT PROFILING
(bit-exact ≤2.9 % residual, reverted); exp-0040 banked-time allocation
ELIMINATED AT PROFILING, no games; exp-0041 `BadCaptureAllDepths` −5.06 CLOSED;
exp-0042 `MaxGainDelta` screen +2.61 / confirmation −10.83, NEVER pooled,
FINAL CLOSED; exp-0043 `TTSingularExtension` −10.31 CLOSED; exp-0044
`BadCaptureOrdering` screen +3.31 / confirmation +13.60, NEVER pooled, CLOSED
AS INCONCLUSIVE; exp-0045 `SkipDeadTTEval` — original `41817228668`
**INVALID MEASUREMENT** (batchB game 272 TIME_FORFEIT, all Elo DISCARDED), one
preregistered bounded valid retry `41818958001` **−8.9240 [−18.2792,+0.4182]**,
CLOSE / ABANDONED, 44/0 audit; exp-0046 `AdaptiveNullR` — single frozen run
`41825055840`, **+3.5096 [−5.1015,+12.1250]** on 1,990 games, 0
forfeits/illegal/failures, 44/0 audit, CLOSED AS INCONCLUSIVE at its frozen
single-run compute bound, NO further samples, switch stays default-OFF.

**Explicitly excluded dead ends (no genuinely new evidence exists for any):**
TT replacement/depth policy is already shipped generation/depth-preferred;
canonical singular re-search with verification subtree is unaffordable at 40+4
(exp-0043 overhead); time allocation REJECT; "delete more nodes", "change which
qsearch nodes are searched", adding work/one extra ply at non-PV nodes,
superficial parameter changes, best-of-N param selection on small screens,
retuning closed switches, rebuilding from Stockfish source, and re-testing
`SkipDeadTTEval` or `AdaptiveNullR` at this control.

## 4. Phase 2 — bounded technical investigation (fresh evidence this turn)

### 4.1 Real profiling of the current source (new, reproducible)

A diagnostic `gprof` build of the exact HEAD was configured with
`-DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_CXX_FLAGS="-mpopcnt -mbmi2 -mlzcnt
-DSB_SEE_CACHE=1 -pg -fno-omit-frame-pointer" -DCMAKE_EXE_LINKER_FLAGS="-pg"`
(no LTO). Its default `bench` signature remained `243f9a1c1ba5b36f`, i.e. no
search semantics changed. Workload: **24 real FENs** derived from
`benchmarks/positions/openings_exp0046_stage0.txt`, `go depth 12` each, one UCI
process, champion runtime. **12,161,395 nodes, 15.17 s wall**, `gmon.out`
written at process exit. Full output:
`benchmarks/dev6-baseline/exp0047_gprof_flat.txt` and
`exp0047_gprof_callgraph.txt`.

| self % | calls | hot function |
|---:|---:|---|
| 17.77 | 22,582,458 | `features(Position,Color,EvalParams,bool)` |
| 10.40 | 21,134,089 | `Search::next_move` (selection scan) |
| 9.45 | 460,060,962 | `attacks_bb` |
| 8.51 | 3,596,175 | `TranspositionTable::probe` |
| 7.37 | 19,644,970 | `Position::make_move_impl` |
| 7.37 | 7,138,444 | `generate_moves` |
| 5.86 | 5,892,376 | `Search::score_moves` |
| 5.48 | 9,488,197 | `static_exchange_evaluation` |
| 5.29 | 32,734,980 | `slider_attacks_bb` (nested in `attacks_bb`) |
| 3.97 / 3.78 | 10,440 / 4,859,552 | `negamax` / `quiescence` |
| 0.76 | 11,291,229 | `evaluate` (self only; its callees dominate) |

Interpretation (not a strength result): evaluation feature counting and attack
generation account for roughly a third of node-level self time; move ordering
and move making/legality another ~30 %; TT probe 8.5 %; SEE 5.5 %.

### 4.2 Source-level findings (no assumed superiority)

- `src/evaluation/evaluation.cpp`: `evaluate()` calls `features(p, White, par)`
  and `features(p, Black, par)`. Each `features()` computes the mobility of its
  own non-pawn pieces AND the king-danger attack sets of the opponent's pieces —
  i.e. **every non-pawn piece's `attacks_bb` is computed twice per `evaluate()`**
  with identical `(pt, square, occupancy)` (`attackerColor` is used only for
  pawns, `src/chess/bitboard.cpp:125–135`). Pawn attacks are computed once. This
  is a genuine, bit-exact redundancy, distinct from the failed exp-0013
  *incremental* eval (which added per-move delta work and lost 27 % NPS) and from
  exp-0039/0045 (which eliminated whole `evaluate()` calls).
- `src/search/search.cpp:296–300`: `next_move()` is a lazy selection scan,
  O(n²) worst case but O(k·n) when a cutoff occurs after k moves; replacing it
  with an eager sort would be bit-exact only with a stable descending sort and
  could be *slower* at the many early-cut nodes. This is an unmeasured trade-off,
  not a free win.
- `src/search/transposition_table.cpp`: replacement already prefers exact match,
  then empty/stale, then shallowest/oldest generation; with a 16 MB table and
  ~10k–30k nodes/move it is far from full. TT replacement/depth policy is
  therefore not a credible untried lever. `probe()` scans a bucket linearly
  (8.51 % self) but changing it would alter search semantics.
- Default qsearch has no dedicated main TT and calls the full `evaluate()` for
  stand-pat; exp-0007 (qsearch-lite) regressed, confirming eval quality there is
  load-bearing. `evaluate_lite()` exists but is not on the default path.
- `SB_SEE_CACHE=1` is already on in the portable build; `SEE` still costs 5.48 %.
- All 17 experimental UCI switches were verified `default false` on a fresh
  Release build of this HEAD (§8), including `AdaptiveNullR`.

### 4.3 Matched-toolchain NPS measurement (new, reproducible)

Fresh `build-verify` from exact HEAD with the frozen portable Release flags
(`-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`, Ninja, GCC 12.2.0),
versus the immutable dev5 binary, `bench --depth 16`, 3 alternating repetitions,
**identical node count 24,211,820** in every run:

| rep | candidate NPS | dev5 NPS |
|---|---:|---:|
| 0 | 0.4654 M | 0.4366 M |
| 1 | 0.4289 M | 0.4450 M |
| 2 | 0.4540 M | 0.4412 M |
| median | **0.4540 M** | **0.4412 M** |

Median ratio **1.0289**, with candidate spread ±4.1 % and dev5 spread ±1.0 % —
the difference is inside local measurement noise. This agrees with exp-0030 E3
(A2/A1 0.9765, B/A1 0.9906) and exp-0010/0013: there is **no unmeasured
bit-exact NPS step-change** in the current source. Historical slope: +12–20 % NPS
produced only ≈ +3.6 Elo at 40+4; `docs/DEV6_RESEARCH.md` estimates ≈ +90 Elo
for 2× nodes, so even a hypothetical 20 % NPS gain maps to ≈ +10–18 Elo, not
+75.

### 4.4 Separation of the four kinds of "improvement"

| category | verified evidence | may it support a strength claim? |
|---|---|---|
| Performance / throughput | gprof hotspot table; 1.0289 NPS ratio inside noise; exp-0010 +12–20 % NPS ≈ +3.6 Elo; exp-0013 −27 % NPS; exp-0039/0040 eliminated at profiling | NO — fixed-depth/NPS/depth numbers are not fixed-time Elo |
| Search quality | exp-0036 +21.52 fixed-time (Tier-2 core, UCB +32.81, closed at futility); exp-0038 +7.68; exp-0046 +3.51 (CI includes 0); all other switches negative or inconclusive | NO — best measured single-switch effect is ~1/4 of Gate 1 |
| Evaluation accuracy | 38-parameter linear classical eval; six extra features −17.0 decisive; outcome-tuning plateau +40…+48 vs dev4; small CPU NNUE −650…−760 Elo / 4× slower | NO — no measured accuracy→strength link at this HEAD |
| Statistically demonstrated strength | Gate 1 requires ≥ +75 / LCB > +50 on two 6,600-game batches; no candidate has ever met it; `docs/DEV6_POWER_ANALYSIS.md`: "~576 games suffice to reject +75; **the binding constraint is a candidate whose true strength gain is >= +75**" | NO — decisive candidate is the blocker, not sample size |

## 5. Ranked candidate hypotheses (at most three, as required)

| # | hypothesis | evidence | expected impact | implementation risk | Gate 1 relevance | verdict |
|---|---|---|---|---|---|---|
| **1** | **Bit-exact evaluation attack-set deduplication** (and/or stable-sort move ordering) — cache each `(piece, square, occupancy)` attack bitboard once per `evaluate()`; no search decision changes | NEW gprof evidence (§4.1/4.2): 17.77 % + 9.45 % + 5.29 % + 10.40 % self time, provable duplicate computation. Exp-0013/0039/0040 show caching/skipping is not automatically a win | Upper bound ≈ 7 % node time → ≈ +3–8 Elo at 40+4 by the historical NPS→Elo slope (matrix explicitly notes "+3–8 Elo is NOT detectable with 2,000 games"). Far below +75 | Low semantic risk (bit-exact provable), but cache lookup may cost as much as a magic-bitboard lookup; would need a pre-result NPS gate like exp-0039 | **None for Gate 1**: a properly powered 13,200-game measurement would almost certainly CLOSE at UCB < +50. It cannot produce a ≥ +75 candidate | **NOT JUSTIFIED as a strength experiment.** Evidence supports a *profiling* investigation only; launching games for it would manufacture activity |
| **2** | **Decisive Tier-1 isolated-VM replication of `BadCapturePruning=true` vs exact dev5** (best positive result of the cycle) | exp-0036 +21.52 [+10.28,+32.81], 1,994 games, both batches positive, 0 forfeits, 201/0 audit; Tier-2 dedicated **core**, not VM | ≈ +21 Elo; 95 % UCB +32.81 < +50 ⇒ Gate 1 is already conclusively unmet (and ≈ 53 Elo short in point) | Very low (switch exists, default-OFF), but ledger explicitly forbids: "do NOT re-run the whole-screen 40+4 ms confirmation this cycle (UCB already < +50)", "do NOT stack … post hoc", "do NOT tune", "do NOT enable by default before isolated-runner confirmation" | A full-power replication could at best refine the Tier-2 estimate and exercise Tier-1/packaged-binary plumbing (Gate 4 sub-criterion), but **cannot** change the Gate-1 verdict | **NOT JUSTIFIED / forbidden by a frozen decision.** Reopening exp-0036 would violate "preserve previous decisions" and "no repeatedly extending" |
| **3** | **A materially stronger evaluator** — a large bullet-matched, quantised fast NNUE or a genuinely new classical feature family, with a measured accuracy→outcome link and measured inference cost | `docs/DEV6_3000_ROADMAP.md` M1/M2 names this the only credible route; status doc: "a FRESH-measured bundle of independently validated mechanisms, never a post-hoc sum, is the only credible route"; research matrix lists "a larger bullet-matched eval corpus with an explicit accuracy-to-strength link" as a remaining ranked direction | Potentially ≥ +75 (the only hypothesis not already bounded below +50), but **unquantified** | Very high: needs a new corpus, training/fitting, fast inference, bit-exact OFF proof, full re-validation, and a fresh decisive measurement | **Highest**, but currently untestable | **NOT YET TESTABLE.** Three missing evidence items are listed in §6. It is the selected direction for the dormant prereg, NOT a claim that it will work |

Ranking is by *relevance to the unmet gates*, not by expected Elo: H3 is the
only hypothesis with any path to Gate 1; H1 and H2 are bounded below the gate
before a single game. No technique was assumed inherently superior.

## 6. Decision: no strength experiment is justified at this HEAD

**Selection outcome:** the ONE selected experiment is the decisive Gate-1
measurement of a genuinely stronger evaluator, fully preregistered in
`docs/DEV6_PREREG_EXP0047.md`, and it is **DORMANT / NOT ACTIVATED**.

Why no games were played (each reason is independently sufficient):

1. `docs/DEV6_POWER_ANALYSIS.md` proves sample size is not the binding
   constraint: ~576 games reject +75, and 13,200 games give ±5.2 Elo. The
   binding constraint is a candidate with a true gain ≥ +75.
2. Every candidate that exists has a 95 % upper bound below +50 (best:
   exp-0036 +32.81) or a closed/inconclusive decision. There is no candidate
   whose prior is compatible with +75.
3. The only untried direction (H3) lacks three specific pre-result measurements:
   **(a)** a fresh bullet-matched self-play corpus with a frozen accuracy/
   calibration comparison against the champion classical evaluator (the prior
   479k/885k corpora were lost in the documented sandbox wipe); **(b)** a
   matched-toolchain inference-cost measurement of the candidate evaluator
   (exp-0001's small CPU NNUE was 4× slower and −650…−760 Elo); **(c)** a
   pre-result argument linking (a)+(b) to an expected ≥ +75 Elo effect. Without
   these, selecting a network architecture or feature set would be a speculative
   heuristic.
4. H2's replication and stacking are explicitly prohibited by the frozen
   exp-0036 closure; exp-0045's invalid run and exp-0046's inconclusive run are
   frozen and must not be pooled, retuned or extended.
5. Launching a 2,800-game screen with the old `+20` acceptance rule would
   directly contradict "Use the authoritative DEV6 mission requirements. Do not
   automatically transplant acceptance criteria from an older development
   version" and "Do not manufacture progress".

Therefore **Phase 4 implementation and Phase 5 games were deliberately NOT
executed**. No source file was modified, no `tier1-dispatch.json` edit was made,
no opening suite was generated, no benchmark run was launched, no measurement
was invalidated, and no frozen result was reinterpreted. This is not a
termination: the mission stays ACTIVE and §11 gives the concrete next action.

## 7. The frozen preregistration (Phase 3 deliverable)

`docs/DEV6_PREREG_EXP0047.md` is a **complete** preregistration — it contains
all fields requested before implementation/games:

- hypothesis and causal mechanism (§1); exact scope and default-OFF/bit-exact
  requirement (§2); a measurable four-part **activation condition** (§3);
- baseline/candidate identity including the immutable dev5 SHA-256, champion
  runtime, portable build flags and the Track-A/Track-B caveat (§4);
- benchmark protocol 40+4 ms, Hash 16, Threads 1, 240 plies, isolated
  `ubuntu-latest` VMs, Stage-0 and candidate nulls, driver `null=true` caveat
  (§5);
- primary/secondary metrics with opening-clustered CR1/t two-sided 95 % CI,
  Elo-from-score and bootstrap cross-checks (§6);
- fresh disjoint suites with zero-overlap/duplicate assertions and recorded
  slice hashes (§7);
- **6,600 games per batch / 13,200 combined**, ±5.2 Elo half-width from the
  power analysis, single-run compute bound with NO extension (§8);
- validity criteria including ZERO TIME_FORFEIT/illegal/crash/UCI failure in
  ANY job, checksums, default signatures, nulls including 0, NPS `[0.97,1.03]`,
  suite disjointness and a ≥ 44-value audit (§9);
- invalid-run handling (discard ALL Elo/CI/WDL) and **NO authorised retry**
  unless a separate addendum precedes the first game (§10);
- frozen ADVANCE (`p >= +75` AND `LCB > +50` AND both batches positive AND
  consistent AND all Gates clean), CLOSE (`U < +50` futility), CLOSED AS
  INCONCLUSIVE at the compute bound with NO further samples (§11) — §8
  thresholds, not the `+20` screen;
- independent raw-JSONL decision script, exact SHAs/run IDs, no pooling,
  append-only records (§12); an empty Activation Record table (§13).

It is frozen **before** any game. It does not weaken, transplant or silently
change any existing condition, statistical method or threshold.

## 8. Validation / audit evidence actually executed this turn (Phases 4–5 surrogates)

Because no experiment was activated, these are integrity re-verifications of the
existing baseline and of the two most recent frozen decisions — NOT new strength
evidence:

| check | result |
|---|---|
| Fresh Release build from exact HEAD, portable flags | `bench` `243f9a1c1ba5b36f`; `bench --depth 16` `a14ab62224f837e5`; `bench --depth 12 --params params_abc` `e45fa2ec2287eb41` (all three frozen signatures) |
| `ctest --test-dir build-verify` | **11/11 PASS** (perft_quick, perft_full, stress, deadpos, uci_integration, uci_fuzz, nnue_features, etc.) |
| Fresh ASan+UBSan build `ctest` | **11/11 PASS**; log `benchmarks/dev6-baseline/exp0047_asan_ctest.txt` (39.36 s) |
| UCI default-option dump | all 17 experimental switches `default false`, including `AdaptiveNullR` and `SkipDeadTTEval` |
| `scripts/dev6_exp0045_retry_decision.py` re-run | `−8.9240 [−18.2792,+0.4182]`, games 1,993, `ADVANCE=False CLOSE=True clean=True`, VERDICT CLOSE; invalid run `41817228668` never pooled |
| `scripts/dev6_exp0046_decision.py` re-run | `+3.5096 [−5.1015,+12.1250]`, games 1,990, `ADVANCE=False CLOSE=False clean=True`, VERDICT CLOSED_AS_INCONCLUSIVE (NO further samples) |
| `scripts/dev6_exp0038_audit.py` `41818958001 exp0045_retry 20 10` | **44 stored values / 0 issues — AUDIT PASS** |
| `scripts/dev6_exp0038_audit.py` `41825055840 exp0046 20 10` | **44 stored values / 0 issues — AUDIT PASS** |
| SHA256SUMS verification of both exports | run-`41818958001` 36 OK / 0 BAD over 4 bundles; run-`41825055840` 36 OK / 0 BAD over 4 bundles |
| `git status` before documentation | clean; dispatch file untouched |

Raw new evidence committed: `benchmarks/dev6-baseline/exp0047_gprof_flat.txt`,
`exp0047_gprof_callgraph.txt`, `exp0047_asan_ctest.txt`. No PGN/JSONL strength
data was produced because no game was played; no decision script was written
for a non-existent run, and none claims to have audited one.

## 9. Gate status after this turn (no claim of a gate pass)

| Gate | status | direct evidence |
|---|---|---|
| 1 | **UNMET / FAIL for every measured candidate** | §8 requires ≥ +75 and LCB > +50; best decisive result is −17.0 (six features), best single-switch +21.52 with UCB +32.81 (exp-0036, closed at futility); no new candidate measurement exists |
| 2 | direction-supported for exp-0036 only; secondary wording drift noted in §2 | two positive batches +17.14/+25.91; not a gate pass |
| 3 | **PASS** | all frozen nulls include 0, including exp-0046 Stage-0 +11.35 [−5.10,+27.86] and candidate null −8.73 [−28.05,+10.53] |
| 4 | **UNMET** | no final candidate release artifact; "the exact candidate release artifact must be the tested binary" unsatisfied. Local correctness re-verified this turn (11/11 Release, 11/11 ASan, signatures, audits) but that does not create a packaged candidate |
| Mission | **ACTIVE / NOT COMPLETE** | no strength claim, no default change, no PR/merge/tag/release/deploy/dev7, no absolute Elo or gap-to-3000 claim |

## 10. Verified facts / interpretations / unresolved questions

**Verified facts:** the §1 state table; §8 gate text; the §3 inventory; the gprof
counts and NPS ratios; 11/11 Release and 11/11 ASan; the three frozen bench
signatures; the re-run audits (44/0 ×2), checksums (36/36 ×2) and decision
scripts; the unchanged dispatch file; no games played this turn.

**Interpretations (clearly labelled):** the ~7 % upper bound on a bit-exact
attack-cache NPS gain and its ≈ +3–8 Elo translation; that a stable descending
sort would be bit-exact but possibly slower at cut nodes; that Gate 2's
"direction-supported" wording is a secondary summary rather than a §8 definition;
that `docs/DEV6_CURRENT_STATUS.md`'s "exact current source SHA 0792555…" refers
to the exp-0046 launch commit while `d07294d…` is a later docs/report closure
with no engine source change (the three signatures above are consistent with
this, but it is an interpretation, not a new measurement).

**Unresolved questions:** whether any evaluator can deliver ≥ +75 Elo at 40+4 ms
within the sandbox's compute budget; the size/quality of a regenerated
bullet-matched corpus; the inference cost of a quantised CPU NNUE on the pinned
portable toolchain; the exact Track-B toolchain offset on isolated runners
(exp-0030 resolved it as toolchain-induced locally but did not measure an
isolated-runner Elo offset); the subject-ordering limitation of the M0.2 ladder;
the historical +33 control remains an INVALID MEASUREMENT for source-strength
purposes (it is not erased and is not pooled).

## 11. Next concrete, evidence-backed action

Bounded work that can be done **without any strength game** and that is required
to activate `docs/DEV6_PREREG_EXP0047.md`:

1. Regenerate a fresh bullet-matched (40+4 ms) self-play corpus on isolated
   runners with a frozen seed; record exact FEN/position counts, hashes and
   disjointness from all prior suites. Freeze the evaluation accuracy/calibration
   metric and its threshold **before** generating the corpus.
2. Measure the champion classical evaluator's outcome-prediction accuracy on
   that corpus, then measure a candidate evaluator's accuracy and its
   matched-toolchain inference cost (NPS, `>= 3` alternating repeats, bit-exact
   node counts, `[0.97,1.03]` target or a power-analysis-justified allowance).
3. Only if (1)+(2) support an expected ≥ +75 Elo fixed-time effect, commit an
   Activation Record with all hashes, implement ONE default-OFF candidate,
   prove OFF bit-identical, re-run the full test matrix, freeze the plan/suites/
   dispatch in ONE commit, and execute the single 13,200-game decisive run
   exactly as preregistered — then audit, run the independent decision script,
   and update this report, matrix, ledger and append-only logs.
4. In parallel, Gate 4 still requires an exact final-candidate release artifact
   that IS the tested binary, with final-source CI on that exact SHA.

No merge, tag, release, deploy or dev7 may substitute for these gates.

## 12. Reproducibility

```
cd /home/user/StockBear
export PATH=/home/user/StockBear/.venv/bin:$PATH
git rev-parse HEAD; git status --short; git ls-remote origin arena/3e6dd5b6-stockbear
cmake -S . -B build-verify -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS="-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4"
ctest --test-dir build-verify --output-on-failure
./build-verify/stockbear bench --depth 16
.venv/bin/python scripts/dev6_exp0045_retry_decision.py
.venv/bin/python scripts/dev6_exp0046_decision.py
.venv/bin/python scripts/dev6_exp0038_audit.py 41825055840 exp0046 20 10
```
The `gprof` profile is reproducible with the flags in §4.1 and the 24 FENs from
`benchmarks/positions/openings_exp0046_stage0.txt` at `go depth 12`. Exact
CI/run IDs, prereg/plan SHA-256s and evidence paths are recorded in
`docs/DEV6_CURRENT_STATUS.md`, `docs/DEV6_RESEARCH_MATRIX.md`,
`benchmarks/FAILURE_LEDGER.md` and the append-only logs.

**Frozen artefact SHA-256 (this turn):**

| file | SHA-256 |
|---|---|
| `docs/DEV6_PREREG_EXP0047.md` | `285b3f3491f57a9a9aa7d20794fdad7624408cb5cd961e6a57f0aa9a1a74ef43` |
| `benchmarks/dev6-baseline/exp0047_gprof_flat.txt` | `bdeb24f3c96396e38262eab3c6e5657c96e28c59f1da318d5b1ba70ae8909063` |
| this report | recorded in the commit message and the ledger entry; a document cannot contain its own hash |

The `docs/DEV6_PREREG_EXP0047.md` hash above is the hash of the DORMANT
preregistration. At activation, the Activation Record (its §13) must re-record
this hash together with the activation commit SHA and the plan/suite hashes;
any byte change to the prereg after the first benchmark game requires a new
experiment ID.
