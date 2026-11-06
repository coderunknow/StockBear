# exp-0051 — RESULT: the frozen exp-0049 PST is decisively WORSE at fixed time

**Verdict: CLOSED / NEGATIVE.** Both frozen CLOSE triggers fired.
Combined **−159.5439 Elo, 95 % CI [−173.5745, −145.9839]** over 1,992 adjudicated
games in 992 opening clusters. No default change. The table is rejected on
measured strength.

- Prereg: `docs/DEV6_PREREG_EXP0051.md`, SHA-256
  `94673e910b0dd8f1676ee90db1784524244f08a9df7fec399fb2038485318ae3`,
  frozen before any game and **enforced by the runner** in all four jobs.
- Source: `0dec094f43f6aea17ce7aaf46d62cf4d2033a45d`.
- Tier-1 run **42217333693** (4/4 SUCCESS); evidence export **42218620021**.
- Control: **fixed time 40+4 ms**, Hash 16, Threads 1, max 240 plies, four
  isolated VMs. Never a node budget.
- Artefact under test: `benchmarks/dev6-baseline/exp0049_results/exp0049.sbpst`,
  SHA-256 `6e31a01a6988fd2192259a101a1e089320e9ddeb8d414acf4ed3d05740d6c733`,
  **read-only and byte-identical** to the exp-0049 commit.

## 1. What was tested, and what was not

Both arms ran the **same packaged binary**
(`7b80ce37ee1977e881f7228ae4cb6caf252efa7d2b6c42fdf12af17836303ed8`) with
`EvalParams=research-data/params_abc.txt` and `TTEval=true`. Arm A added exactly
one option: `PstFile=…/exp0049.sbpst`. The single manipulated variable is the
piece-square table.

This was **not** a refit, rescore, or reopening of exp-0049. No entry was edited,
no cap changed, no corpus read. **exp-0049's CLOSED / NEGATIVE verdict stands and
its corpus stays BURNED.** The justification for spending games on an artefact
from a closed experiment was that exp-0049 §7 gated its fixed-time screen on §5
(accuracy) **and** §6 (NPS cost) — both subsequently proven invalid instruments —
so a genuinely fitted 768-parameter table had been discarded with **zero strength
games**. That gap is now closed with a direct measurement.

## 2. Results

FROZEN COMBINED = batchA + batchB only, fixed in the prereg. Nulls never pooled.

| slice | W/D/L | adjudicated | clusters | CR1/t Elo | 95 % CI |
|---|---|---|---|---|---|
| **combined** | **373/389/1230** | **1,992** | **992** | **−159.5439** | **[−173.5745, −145.9839]** |
| batchA | 199/194/604 | 997 | 497 | −149.8621 | [−170.0498, −130.5858] |
| batchB | 174/195/626 | 995 | 495 | −169.5038 | [−189.2736, −150.7033] |
| stage0 null | 132/127/139 | 398 | 198 | −5.2646 | [−21.6120, +11.0596] |
| candidate null | 134/136/128 | 398 | 198 | +4.3870 | [−14.2867, +23.0862] |

Combined score 0.2848896. Independent Elo-from-score **−159.8786**; independent
cluster bootstrap **[−173.5307, −146.2328]**. Both replications agree with the
primary clustered statistic.

**Frozen rule applied as written:** ADVANCE required point ≥ +20 **and** LCB > 0
**and** both batches ≥ −5 — all false. CLOSE required UCB < +10 **or** point ≤ 0 —
**both true**. 12 `UNADJUDICATED_MAX_PLIES` games excluded as preregistered.

The effect is roughly **12× the width of the confidence interval** away from zero
and consistent across two independently seeded 500-opening slices. This is not a
slice artefact and not noise.

## 3. Validity — including the failure mode that would have faked a null

| check | result |
|---|---|
| time forfeits / illegal moves / engine failures | **0 / 0 / 0** in all four jobs |
| stage0 null CI includes 0 | yes |
| candidate null CI includes 0 | yes |
| ctest on the packaged binary (stage0) | **14/14** |
| committed export blobs re-hashed vs working tree | **50/50** |
| per-job `SHA256SUMS.txt` | **40/40** |
| independent audit | **44 stored values, 0 issues, AUDIT PASS** |
| arm A PST load | **LOAD VERIFIED** in batchA, batchB, null (arm B too in null) |

The load check is not ceremonial. `setoption name PstFile value <missing>` is
**not fatal**: the engine prints `info string … could not load` and **plays on
with the formulaic tables**. In a same-binary ablation that makes arm A
bit-identical to arm B, producing a clean, plausible **fake null** — zero
forfeits, nulls containing zero, everything green. The runner therefore now
requires the PST to be a **declared packaged asset** *and* the probe to print
`PstFile loaded:`; both negative branches were exercised locally before dispatch.
A load probe alone was insufficient because it runs with `cwd=ROOT`, where an
undeclared repo-relative path still resolves from the checkout.

Confirmed from committed bytes, not job status: each `pst_probe_A.txt` contains
`info string PstFile loaded: benchmarks/dev6-baseline/exp0049_results/exp0049.sbpst`,
each `BUILD_INFO.assets_sha256` pins the frozen digest, and the PST **extracted
from every tar.gz re-hashes to `6e31a01a…6c733`**.

Pre-game liveness (tree-change proxy, **not** a strength or speed claim): depth 10,
1,418,459 → 1,621,265 nodes (**+14.30 %**), live on **11/12** positions, 2/12
bestmoves changed. The option demonstrably changes play, so this rejection cannot
be attributed to an inert switch.

## 4. Interpretation

The fitted table **improved its corpus objective by 2.4712 % and lost ~160 Elo**.
That is the central finding: a better fit to the log-loss objective is not better
play. The accuracy gate would have been misleading in **both** directions — it
failed an artefact that is genuinely bad, but it had no way to know that, and the
same gate is passable by a ×0.80 rescale that is not a strength no-op.

So exp-0049's gate failure **protected the engine for the wrong reason**. The
outcome was right; the instrument was not. This strengthens, rather than weakens,
the earlier conclusion that selection must be on fixed-time games.

The magnitude is consistent with the fitting pathology already diagnosed:
**291/768 entries pinned at the ±150 cap** and **RMS δ 111.83 cp**. Tables that
large and that saturated distort the cp-calibrated futility, reverse-futility and
delta margins that assume eval is roughly on a centipawn scale. The loss is far
too big to be explained by the table's per-node lookup cost alone.

## 5. Not claimed

No strength gain; no default change; no refit or rescore of exp-0049; no reopening
of exp-0049; **no validation of accuracy gating**; no NPS or speedup claim; no
absolute, CCRL or FIDE Elo; no gap-to-3000; no Gate 1 or Gate 4 pass. This result
does **not** show that a larger cap or a different corpus would also fail — that
question is untested and would need its own preregistration.

## 6. Disposition

Gates: **1 UNMET**, 2 direction-supported (exp-0036, unchanged), **3 PASS**,
**4 UNMET**. Mission **ACTIVE / NOT COMPLETE**. exp-0047 **DORMANT**, Activation
Record empty. exp-0036 remains the best measured direction at
`+21.5238 [+10.2819, +32.8108]`.

Do **not** refit this table, relax the ±150 cap, re-run exp-0051, or pool its
games. This artefact is rejected on measured strength. No PR strength claim,
merge, tag, release or deploy.

Evidence: `benchmarks/dev6-baseline/exp0051_results/{RESULTS.json,AUDIT.txt,SHA256SUMS.txt}`
and raw games in `benchmarks/exp-runs/tier1-export/run-42217333693/`.
