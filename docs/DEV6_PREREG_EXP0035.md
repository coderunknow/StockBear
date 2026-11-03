# exp-0035 — larger confirmation of SEE bad-capture pruning (fixed-node)

**Frozen BEFORE results.** Triggered by exp-0034's frozen ADVANCE rule:
combined `+20.49 [+2.12,+38.97]` Elo over 800 games, both batches >= -5,
P1 (-11.29 % nodes) and P2 (correctness) PASS. exp-0034's CI is wide
(+/-18 Elo), so this confirmation is required BEFORE any strength claim.
`docs/DEV6_PREREG.md` §8 is unchanged; this is NOT a dev6 gate test.

## 1. Hypothesis / prediction
`BadCapturePruning=true` is stronger than `false` at fixed nodes with a tighter
CI, and the candidate with the switch ON is not worse than an
identical-toolchain dev5 rebuild. Falsifiable by the decision rule in §5.
Mechanism unchanged from exp-0034: skip non-hash captures with SEE < -100 cp
at depth <= 3 in non-PV, non-check, non-mate-window nodes. Default OFF.

## 2. Control / identities
- Primary: ONE binary `build-exp0034/stockbear`
  (`075ec955a65acad4624cc6d3f4998763aaa7b968e4d01a27e73cd9dfd4c77d82`),
  `BadCapturePruning=true` vs `false`. Zero toolchain confound.
- Track A context: same candidate (switch ON) vs `build-dev5/stockbear`
  (`214cbed0…`, `git archive v0.1.0-dev5` rebuilt in the SAME pinned toolchain),
  both `params_abc.txt` + `TTEval=true`. This is the gate-relevant direction
  check, never relabelled as the official artifact.
- Track B official dev5 `391cb50e…` remains immutable and is NOT used here.
- Build: GCC 12.2.0, `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`,
  no `-march=native`, Release/Ninja/CMake 4.4.4. Fixed-node `6000` +/-15 %,
  hash 16, threads 1, max 240 plies. NO fixed-time claim locally.

## 3. Suite / sample size / statistics
- FRESH openings (`scripts/exp_confirmation_openings.py`, new seed, excluding
  every earlier `openings*.txt`), 2,000 openings split into **two disjoint
  1,000-opening batches**, colour-reversed, 1,000 games per batch =
  **2,000 primary games**; plus **600 Track A context games** on a third fresh
  300-opening slice. Total 2,600 games.
- W/D/L, paired pentanomial, opening-clustered CR1/t two-sided 95 % CI, cluster
  bootstrap, both batches separately and combined; independent re-audit by
  `scripts/dev6_audit.py`. Only the documented `UNADJUDICATED_MAX_PLIES`
  exclusion; no subset selection, no hidden negative batch.

## 4. Correctness / integrity
Default-off bench signatures `243f9a1c1ba5b36f` / `a14ab62224f837e5` remain
exact; CTest 11/11 Release and ASan+UBSan; python-chess oracle 600/43,200/0;
zero illegal / UCI / TIME_FORFEIT events. All raw PGN/JSONL/CSV under
`benchmarks/exp-runs/exp0035-*`; machine-readable
`benchmarks/dev6-baseline/exp0035_results.json`.

## 5. Decision criteria (frozen)
- **CONFIRMED (fixed-node only)** iff combined primary point >= +10 Elo AND
  combined 95 % LCB > 0 AND both batches >= -5 Elo AND Track A context 95 %
  CI is not materially below -10 Elo AND all correctness checks pass.
- **NOT CONFIRMED** otherwise; append to Failure Ledger with root cause,
  close exp-0035, continue with a materially different direction.
- Even CONFIRMED is **NOT a dev6 gate pass**: Gate 1 needs >= +75 with LCB >
  +50 on two independent fixed-time datasets against the exact dev5 artifact;
  Gate 4 needs final-source CI and the exact packaged binary. Decisive
  fixed-time matches require isolated CI runners (authorization ASK).
- No absolute Elo, no CCRL equivalence, no gap-to-3000 claim.
