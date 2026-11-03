# v0.1.0-dev6 — confirmation report (independently recomputed from raw records)

**Verdict: FAIL / GATE NOT MET.** Recomputed by `scripts/dev6_confirmation_report.py` from the raw per-game JSONL committed by the free dev6 lane. Primary estimator: opening-clustered CR1 variance with a two-sided 95% Student-t interval (G-1 df) on the logistic Elo scale. Pre-registered in `docs/DEV6_PREREG.md` before any result.

Baseline for every strength claim: the **exact released v0.1.0-dev5** portable binary `391cb50e…` at champion options (`params_abc.txt` + `TTEval=true`). Conditions: 40+4 ms, hash 16 MB, 1 thread, paired colour-reversed openings, dedicated isolated GitHub-hosted runners. dev6 candidate built with the exact portable release flags `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`.

## Results

| scope | games | W/D/L | score % | clustered Elo | 95% CI | clusters (df) | paired Elo [CI] |
|---|---|---|---|---|---|---|---|
| Screen: primary (params_dev6_a) | 2000 | +586 =679 -730 | 46.39 | -25.0 | [-42.9, -7.3] | 240 (239) | -25.0 [-36.1, -14.0] |
| Screen: integrity control (params_abc) | 1100 | +409 =378 -307 | 54.66 | +33.0 | [+13.7, +52.5] | 240 (239) | +33.0 [+18.0, +48.1] |
| Screen: historical params_exp0020 | 1100 | +356 =346 -395 | 48.22 | -12.1 | [-33.7, +9.4] | 240 (239) | -12.1 [-27.9, +3.7] |
| Decisive batch A (exp-0028) | 6600 | +2090 =2071 -2418 | 47.51 | -17.8 | [-24.1, -11.5] | 3279 (3278) | -17.8 [-24.1, -11.6] |
| Decisive batch B (exp-0029) | 6600 | +2049 =2185 -2356 | 47.67 | -16.2 | [-22.4, -10.0] | 3290 (3289) | -16.2 [-22.3, -10.0] |
| **COMBINED decisive (Gate 1)** | 13200 | +4139 =4256 -4774 | 47.59 | -17.0 | [-21.4, -12.6] | 6569 (6568) | -17.0 [-21.4, -12.6] |
| Null A (candidate vs identical) | 1100 | +390 =322 -387 | 50.14 | +0.6 | [-9.5, +10.7] | 549 (548) | +0.6 [-9.4, +10.6] |
| Null B (candidate vs identical) | 1100 | +365 =362 -373 | 49.64 | -2.5 | [-12.8, +7.7] | 550 (549) | -2.5 [-12.7, +7.6] |
| Null combined | 2200 | +755 =684 -760 | 49.89 | -0.9 | [-8.1, +6.2] | 1099 (1098) | -0.9 [-8.1, +6.2] |

Combined decisive point estimate **-17.0 Elo**, 95% CI **[-21.4, -12.6]**, t=1.980 on 6568 df, 13200 games over 6569 distinct opening clusters. Naive Wilson is NOT used as the primary estimator; the two games of an opening are never treated as independent.

## Pentanomial, SPRT, terminations, adversarial events

- **Screen: primary (params_dev6_a)**: pair-score counts (2/1.5/1/0.5/0) = [56, 188, 409, 241, 101]; SPRT (normal approximation) LLR = -4.342236669003666; term-inations {'THREEFOLD_REPETITION': 634, 'CHECKMATE': 1316, 'INSUFFICIENT_MATERIAL': 38, 'STALEMATE': 1, 'UNADJUDICATED_MAX_PLIES': 5, 'FIFTY_MOVES': 6}; unadjudicated 5; adversarial events {'time_forfeit': 0, 'illegal_move': 0, 'crash_or_engine_failure': 0, 'uci_failure': 0, 'max_ply_unadjudicated': 5}.
- **Screen: integrity control (params_abc)**: pair-score counts (2/1.5/1/0.5/0) = [59, 138, 225, 91, 31]; SPRT (normal approximation) LLR = 2.611627810899074; term-inations {'THREEFOLD_REPETITION': 353, 'CHECKMATE': 716, 'UNADJUDICATED_MAX_PLIES': 6, 'INSUFFICIENT_MATERIAL': 23, 'FIFTY_MOVES': 2}; unadjudicated 6; adversarial events {'time_forfeit': 0, 'illegal_move': 0, 'crash_or_engine_failure': 0, 'uci_failure': 0, 'max_ply_unadjudicated': 6}.
- **Screen: historical params_exp0020**: pair-score counts (2/1.5/1/0.5/0) = [51, 94, 225, 120, 57]; SPRT (normal approximation) LLR = -1.1204084831660968; term-inations {'CHECKMATE': 751, 'THREEFOLD_REPETITION': 316, 'INSUFFICIENT_MATERIAL': 28, 'FIFTY_MOVES': 2, 'UNADJUDICATED_MAX_PLIES': 3}; unadjudicated 3; adversarial events {'time_forfeit': 0, 'illegal_move': 0, 'crash_or_engine_failure': 0, 'uci_failure': 0, 'max_ply_unadjudicated': 3}.
- **Decisive batch A (exp-0028)**: pair-score counts (2/1.5/1/0.5/0) = [234, 610, 1358, 740, 337]; SPRT (normal approximation) LLR = -10.04298792016941; term-inations {'CHECKMATE': 4508, 'THREEFOLD_REPETITION': 1956, 'INSUFFICIENT_MATERIAL': 108, 'FIFTY_MOVES': 5, 'UNADJUDICATED_MAX_PLIES': 21, 'STALEMATE': 2}; unadjudicated 21; adversarial events {'time_forfeit': 0, 'illegal_move': 0, 'crash_or_engine_failure': 0, 'uci_failure': 0, 'max_ply_unadjudicated': 21}.
- **Decisive batch B (exp-0029)**: pair-score counts (2/1.5/1/0.5/0) = [222, 630, 1373, 750, 315]; SPRT (normal approximation) LLR = -9.557537418575917; term-inations {'CHECKMATE': 4405, 'THREEFOLD_REPETITION': 2054, 'INSUFFICIENT_MATERIAL': 122, 'FIFTY_MOVES': 6, 'UNADJUDICATED_MAX_PLIES': 10, 'STALEMATE': 3}; unadjudicated 10; adversarial events {'time_forfeit': 0, 'illegal_move': 0, 'crash_or_engine_failure': 0, 'uci_failure': 0, 'max_ply_unadjudicated': 10}.
- ****COMBINED decisive (Gate 1)****: pair-score counts (2/1.5/1/0.5/0) = [456, 1240, 2731, 1490, 652]; SPRT (normal approximation) LLR = -19.611276267953606; term-inations {'CHECKMATE': 8913, 'THREEFOLD_REPETITION': 4010, 'INSUFFICIENT_MATERIAL': 230, 'FIFTY_MOVES': 11, 'UNADJUDICATED_MAX_PLIES': 31, 'STALEMATE': 5}; unadjudicated 31; adversarial events {'time_forfeit': 0, 'illegal_move': 0, 'crash_or_engine_failure': 0, 'uci_failure': 0, 'max_ply_unadjudicated': 31}.
- **Null A (candidate vs identical)**: pair-score counts (2/1.5/1/0.5/0) = [17, 66, 382, 70, 14]; SPRT (normal approximation) LLR = -0.3579165782732944; term-inations {'CHECKMATE': 777, 'THREEFOLD_REPETITION': 298, 'UNADJUDICATED_MAX_PLIES': 1, 'INSUFFICIENT_MATERIAL': 23, 'FIFTY_MOVES': 1}; unadjudicated 1; adversarial events {'time_forfeit': 0, 'illegal_move': 0, 'crash_or_engine_failure': 0, 'uci_failure': 0, 'max_ply_unadjudicated': 1}.
- **Null B (candidate vs identical)**: pair-score counts (2/1.5/1/0.5/0) = [10, 82, 366, 74, 18]; SPRT (normal approximation) LLR = -0.9386794965541655; term-inations {'CHECKMATE': 738, 'THREEFOLD_REPETITION': 340, 'INSUFFICIENT_MATERIAL': 22}; unadjudicated 0; adversarial events {'time_forfeit': 0, 'illegal_move': 0, 'crash_or_engine_failure': 0, 'uci_failure': 0, 'max_ply_unadjudicated': 0}.
- **Null combined**: pair-score counts (2/1.5/1/0.5/0) = [27, 148, 748, 144, 32]; SPRT (normal approximation) LLR = -1.30569611572286; term-inations {'CHECKMATE': 1515, 'THREEFOLD_REPETITION': 638, 'UNADJUDICATED_MAX_PLIES': 1, 'INSUFFICIENT_MATERIAL': 45, 'FIFTY_MOVES': 1}; unadjudicated 1; adversarial events {'time_forfeit': 0, 'illegal_move': 0, 'crash_or_engine_failure': 0, 'uci_failure': 0, 'max_ply_unadjudicated': 1}.

Pre-declared handling (`docs/DEV6_PREREG.md` §4): TIME_FORFEIT, ILLEGAL_MOVE, CRASH/ENGINE_FAILURE, UCI failure, MAX_PLY/unadjudicated are recorded individually, never hidden; engine-caused illegal moves/crashes/protocol failures are losses for the offending engine; unadjudicated games are excluded from the score and counted. No outcome was silently changed or removed; the counts above are the sensitivity check.

## Sensitivity

- Combined paired/cluster bootstrap (2000 replicates): [-21.4, -12.6] Elo (paired (cluster) bootstrap of colour-reversed pairs).
- batch_A leave-one-shard-out point estimates: −shard01: -16.4, −shard02: -18.0, −shard03: -21.2, −shard04: -14.1, −shard05: -19.9, −shard06: -17.3.
- batch_B leave-one-shard-out point estimates: −shard01: -19.3, −shard02: -15.2, −shard03: -15.7, −shard04: -15.9, −shard05: -15.5, −shard06: -15.5.

## Gate evaluation (thresholds frozen in the pre-registration)

| gate | requirement | result |
|---|---|---|
| gate1_point_ge_75 | combined point estimate >= +75 Elo | FAIL |
| gate1_lcb_gt_50 | combined 95% CI lower bound strictly > +50 Elo | FAIL |
| gate2_both_batches_positive | both decisive batches show a positive point estimate | FAIL |
| gate2_reasonably_consistent | the two batches are reasonably consistent | PASS |
| gate3_nulls_include_zero | both nulls' 95% intervals include zero | PASS |
| gate4_no_unresolved_engine_failure | no unresolved illegal-move/crash/UCI-failure regression | PASS |
| all_pass | ALL gates pass | FAIL |

## Integrity investigation: the control's unexplained +33 Elo

The pre-registered integrity control was meant to confirm that the dev6 binary with `params_abc` (extended features gated off) is behaviourally identical to the released dev5 champion. It did **not**: the control measured +33.0 [+13.7, +52.5] Elo. Verified from the raw `match.jsonl` configuration that this is NOT a config error: engine A is the runner-built dev6 binary (SHA `4b06b117…`), engine B the released dev5 binary (SHA `391cb50e…`), and BOTH were sent the identical `params_abc.txt` (SHA `8a9dc81f…`) + `TTEval=true`, 40+4 ms, hash 16, 1 thread.

Leading hypotheses, and what was checked:

- **Toolchain difference (most plausible).** The dev5 release artifact was built by `release.yml` on `ubuntu-22.04`; the dev6 candidate was rebuilt by the free lane on `ubuntu-latest` (manifest: `glibc2.39`, AMD EPYC 7763 => Ubuntu 24.04 / GCC 13). Different compiler/image can change NPS at equal 40+4 ms and therefore strength, even with identical source semantics and identical bench signatures (both `243f9a1c1ba5b36f`). The runner candidate binary is not available inside the sandbox for a direct NPS comparison, so this cannot be pinned down here.
- **Screen sampling variation.** The control is a 1100-game screen on `openings_dev4.txt` with only ~240 distinct clusters (half-width ~19 Elo); +33 is statistically positive but modest. Nulls cannot detect a *between-binary* NPS difference because both null sides use the same binary (they correctly show ~0 and rule out harness/order/colour bias).
- **My source changes are ruled out as the cause.** On one machine, at identical `bench --depth 16` node counts, the locally-built dev6 binary (same portable `-flto=4` flags, GCC 12) is only 1.015x the released dev5 binary's NPS (170,160,152 nodes in 52.3 s vs 53.1 s) — negligible; with the shipped set the extended routine is not called at all. A ~+33 Elo advantage cannot come from this.

**Isolated feature ablation (confound-free within-suite contrast).** On the SAME opening suite (`openings_dev4.txt`), SAME dev6 binary and SAME dev5 baseline, only `EvalParams` differs: control `params_abc` = +33.0 Elo, primary `params_dev6_a` = -25.0 Elo. Enabling the six extended features therefore costs ≈ **-58.0 Elo** (wide screen CIs). This is independent of any toolchain confound (it cancels), matches the decisive −17 Elo result (the candidate starts from a possible ~+33 build advantage and the features cost more), and is the primary algorithmic conclusion: **the features are harmful**, not merely neutral.

Consequence: this control is classified **INCONCLUSIVE / confounded** (an unexplained difference between the benchmarked and packaged binary). Per the mission it must be investigated and resolved before ANY approval decision; here the verdict is negative regardless, so no approval is sought. Required fix for a future cycle: build the candidate with the SAME release toolchain/image (or re-pin BOTH sides to one reproducible build environment), verify binary-level NPS equivalence, and re-run the integrity control before any strength comparison. This confound does NOT weaken the primary conclusion: the candidate LOST by -17.0 Elo in two independent 6600-game batches with clean nulls.

## Infrastructure note (not a strength result)

Seventeen lane jobs pushed results concurrently; the push-retry loop produced some duplicate empty `[skip ci]` commits. All 17 result directories were verified present on the branch with their PGN/JSONL/CSV/manifest; no data was lost. Classified INFRASTRUCTURE FAILURE (cosmetic), recurrence condition = many concurrent result-pushing jobs; fix = a single aggregation job or a non-empty-commit guard. History was not rewritten (no destructive remote ops).

## Verdict and consequences

**The mandatory strength gate is NOT met.** Per the mission: no strength claim, no release PR, no merge, no tag, no release, no `0.1.0-dev7` auto-increment. All raw results are preserved; the direction is diagnosed and logged in the Failure Ledger; research continues on materially different hypotheses. The external rating ladder status is documented separately (`docs/DEV6_EXTERNAL_LADDER.md`).

Raw data: `benchmarks/exp-runs/exp0027-*`, `exp0028-*`, `exp0029-*` (PGN + JSONL + CSV + manifest + logs). Machine-readable recomputation: `benchmarks/dev6-baseline/confirmation_results.json`.
