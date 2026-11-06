# exp-0050 — pawn-structure correction history — CLOSED / NEGATIVE

**Verdict: CLOSED / NEGATIVE** at the frozen prereg rule. **2,800 games played
on four isolated GitHub-hosted VMs.** No strength claim, no default change.

- Prereg `docs/DEV6_PREREG_EXP0050.md`, SHA
  `e80375135cf991cd8c4fcc1723e5c6c4f2c1dd957e5a6d920be8bfda88f9569a`, frozen
  before any exp-0050 game and **enforced** by the runner.
- Source `96822f65fc173d8348a91c1bf136af87450a0eb5`; Tier-1 run
  **42206510815** (4/4 SUCCESS); export run **42207882294**.
- Evidence `benchmarks/dev6-baseline/exp0050_results/` (checksummed) and raw
  `benchmarks/exp-runs/tier1-export/run-42206510815/` (**36/36 committed blobs
  verified** by SHA-256 via `git show`, not just the working tree).

## 1. Why this experiment existed

Both accuracy audits (`DEV6_ACCURACY_ELO_LINK_AUDIT.md`,
`DEV6_ACCURACY_GATE_VALIDITY.md`) concluded the same thing: the accuracy gate is
passable by a pure rescale and has no licensed Elo conversion, so **select on
fixed-time games**. exp-0050 was the first direction chosen under that rule.

Correction history was verified **genuinely untried**: it appears nowhere in the
failure ledger and `src/search/` had no eval-bias table. It is a **search**
change, so it needs neither the broken gate nor an accuracy→Elo link.

## 2. Mechanism

A decaying running mean of `(search score − raw static eval)`, indexed by a hash
of the two pawn bitboards, added to the eval used for **pruning margins only**.
The **raw** eval is what the TT stores, so the bias cannot compound through TT
reuse. Writes were guarded to completed, non-check, non-mate nodes with a
quiet/absent best move and a consistent bound. Six constants frozen from theory
before any game. Default OFF; all three shipped bench signatures bit-exact.

## 3. Results — FIXED TIME 40+4 ms, never `--nodes`

Both arms `EvalParams=params_abc.txt` + `TTEval=true`; A adds only
`CorrectionHistory=true`. One byte-identical binary
`7b80ce37ee1977e881f7228ae4cb6caf252efa7d2b6c42fdf12af17836303ed8` in all four
jobs.

| job | games | unadj. | CR1/t Elo | 95 % CI |
|---|---|---|---|---|
| stage0 (control/control null) | 400 | 0 | −9.56 | [−27.89, +8.73] |
| batchA | 997 | 3 | −5.24 | [−16.78, +6.28] |
| batchB | 998 | 2 | +2.09 | [−10.54, +14.74] |
| null (candidate options both) | 399 | 1 | +6.11 | [−15.59, +27.86] |

**FROZEN COMBINED = batchA + batchB only** (nulls never pooled):

- W/D/L **649 / 691 / 655**, 1,995 adjudicated games, 995 opening clusters,
  score 0.4984962
- **CR1/t Elo −1.5713, 95 % CI [−10.1225, +6.9780]**
- Independent Elo-from-score −1.0449
- Independent seeded cluster bootstrap [−9.9544, +6.8099] (no shared code path)

## 4. Decision against the frozen rule

Prereg §6, registered before any game:

- ADVANCE needs point ≥ +20 **and** LCB > 0 **and** both batches ≥ −5 →
  **False** (point −1.57, LCB −10.12, batchA −5.24).
- **CLOSE if combined UCB < +10 OR point ≤ 0** → **both triggers fired**
  (UCB +6.98 < +10; point −1.57 ≤ 0).

**CLOSED / NEGATIVE.** No threshold was changed after results, no sample
increase, no retune, no confirmation run.

## 5. Validity — clean, so this is a real rejection

- **0 TIME_FORFEIT, 0 ILLEGAL, 0 ENGINE_FAILURE** across all four jobs.
- Both required nulls include 0 in their CIs.
- Stage-0 **ctest 14/14 on the packaged binary**; default bench signature
  `243f9a1c1ba5b36f` on the runner.
- Prereg SHA verified against the plan **by the runner**; dev5 baseline
  `391cb50e…5bdb918` verified immutable.
- Independent raw-JSONL audit: **44 stored values checked, 0 issues, AUDIT PASS**.
- 6 `UNADJUDICATED_MAX_PLIES` excluded by the standing rule, never counted.

The four `package_sha256` values differ **only** because `BUILD_INFO.json`
embeds `job_id`; `binary_sha256` is identical in all four and equals
`built_binary_sha256`. Checked, not assumed.

## 6. The mechanism was live — this is not a silent no-op

Before any game, at fixed depth 10 on the 12-position bench suite: OFF
**1,418,459** nodes → ON **1,410,036** (**−0.59 %**), live on **7/12** positions,
bench signature changed. Two deliberate mutants (update removed; apply site
disabled) **both FAILED** the liveness assertion while every correctness
assertion still passed — the exp-0038 lesson applied in advance.

So the negative result cannot be explained away as "the switch never did
anything". It did change the tree, and the change was worth **no** fixed-time Elo.

## 7. Interpretation

The learned pawn-structure bias does not improve pruning decisions enough at
40+4 ms to pay for its per-node lookup. The CI rules out anything near the +20
ADVANCE bar, let alone the +75 mission gate.

Unlike exp-0048/0049, this verdict is **instrument-independent**: fixed-time
games charge every per-node cost against the candidate, both nulls are clean,
and no accuracy metric or Elo conversion enters the decision.

## 8. Status

Gates unchanged: **1 UNMET, 2 direction-supported (exp-0036), 3 PASS, 4 UNMET**.
Mission **ACTIVE / NOT COMPLETE**. exp-0047 **DORMANT**, Activation Record empty.
exp-0048/0049 untouched. No PR strength claim, merge, tag, release or deploy.

**Do NOT** retune the frozen constants on these results, re-run exp-0050, pool
its games with any other experiment, or enable `CorrectionHistory` by default.
The direction is abandoned; the switch remains in the tree, default OFF and
bit-exact, so the measurement stays reproducible.
