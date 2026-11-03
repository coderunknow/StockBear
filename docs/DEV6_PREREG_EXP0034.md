# exp-0034 — SEE-based bad-capture pruning in the main search (PILOT SCREEN)

**Frozen BEFORE implementation and BEFORE any result.** Registered because
exp-0033's frozen P3 screen is negative: batch A `-16.54 [-31.06,-2.09]` Elo
for razoring ON vs OFF. Per the persistent-continuation protocol, a rejection
closes only that individual experiment; the dev6 mission continues with a
**materially different mechanism**. `docs/DEV6_PREREG.md` §8 is unchanged.

## 1. Evidence / weakness / mechanism (NOT a repeat)
`score_moves()` already computes a static exchange evaluation for every capture
and `quiescence()` skips `SEE < 0` captures (`SB_SEE_CACHE` stores the result in
`ExtMove::seeScore`). But the **main** `negamax` move loop never skips a losing
capture: at shallow depth it spends a full recursive search on a capture that
loses material. exp-0033 pruned *whole nodes* via a qsearch verification;
exp-0034 prunes *individual losing captures*, a different mechanism with a
different failure mode. It is not any recorded dead end (six extended eval
features, small CPU NNUE, cp distillation, FullSoftBudget, qsearch-lite,
PGO/TT packing/THP, incremental eval, disabling dev4 switches, best-of-N
parameter selection, razoring).

Mechanism: at `depth <= 3`, non-PV, not in check, no mate window, for a
non-hash capture whose `SEE < -BadCaptureMargin` with the **fixed, frozen**
margin `100` cp (NOT tuned on any test set), skip the move. Guarded away from
PV nodes, mate scores, checks and the hash move. `BadCapturePruning` becomes a
UCI `check` option, default `false`, so a default build stays bit-identical and
the ablation uses ONE binary with ONE switch — zero toolchain confound.

## 2. Predictions (falsifiable)
- **P1 (efficiency):** `bench --depth 12 --param badCapturePruning=1` visits
  fewer nodes than `=0`; default-off signatures remain `243f9a1c1ba5b36f`
  (d4) and `a14ab62224f837e5` (d16).
- **P2 (correctness):** CTest 11/11 (Release and ASan+UBSan), python-chess
  oracle 600/43,200/0, 3x bench determinism; zero illegal moves / UCI
  failures / TIME_FORFEIT under the fixed-node control.
- **P3 (strength pilot):** fixed-node score of ON vs OFF with a two-sided
  opening-clustered 95% CI; decision rule in §5.
- **P4:** NO fixed-time Elo claim locally (exp-0030: shared 2-vCPU clock
  noise, 5 TIME_FORFEIT events in 400 games). Decisive fixed-time work needs
  isolated runners.

## 3. Control / baseline / identities
- Candidate + control = **the same `build-exp0034/stockbear` binary** (SHA
  pinned), built with the exp-0030 pinned toolchain (GCC 12.2.0, `-mpopcnt
  -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`, no `-march=native`, Release,
  CMake 4.4.4/Ninja). Only `BadCapturePruning` differs; both use
  `EvalParams=research-data/params_abc.txt`, `TTEval=true`, Hash 16, Threads 1.
- Context baseline: immutable official dev5 `391cb50e…` (Track B), measured
  separately only if the pilot advances.
- TC: fixed-node `--nodes 6000 --nodes-jitter 0.15`, `--max-plies 240`.

## 4. Suite / sample size / statistics (PILOT, not confirmation)
- FRESH openings via `scripts/exp_confirmation_openings.py`, new seed, excluding
  every earlier `openings*.txt`; 800 openings split into **two disjoint
  400-opening batches**, colour-reversed, 400 games per batch = **800 paired
  games**. This sample is deliberately a pilot: its CI half-width is ~20 Elo,
  so it can only reject a clearly harmful direction or motivate a larger
  pre-registered confirmation. It is NOT a gate test.
- Statistics: W/D/L, paired pentanomial, opening-clustered CR1/t two-sided 95%
  CI, cluster bootstrap, both batches reported separately and combined; no
  subset selection; only the documented `UNADJUDICATED_MAX_PLIES` exclusion.

## 5. Decision criteria (frozen)
- **ADVANCE** to a new, larger pre-registered confirmation (2 x 1200 games,
  shared paired openings, isolated runners for fixed-time) ONLY IF: combined
  point >= +10 Elo AND combined 95% LCB > -10 Elo, BOTH batches >= -5 Elo,
  P1 and P2 pass.
- **REJECT / CLOSE exp-0034** otherwise; append to the Failure Ledger with root
  cause and a materially different ranked next direction. A rejection closes an
  individual experiment only; the dev6 mission stays ACTIVE.
- No gate pass, no PR/merge/tag/release follows from exp-0034. No absolute Elo
  or gap-to-3000 claim.

## 6. Integrity / isolation
Built in `build-exp0034/`, **separate from `build-exp0033/`**, so exp-0033's
in-flight matches keep their exact immutable binary. Raw PGN/JSONL/CSV under
`benchmarks/exp-runs/exp0034-*`; machine-readable
`benchmarks/dev6-baseline/exp0034_results.json`. No test-set reuse, no gate
weakened, no negative batch hidden, no post-hoc tolerance.
