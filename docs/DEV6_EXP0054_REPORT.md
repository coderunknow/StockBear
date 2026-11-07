# exp-0054 report — CONFIRMATION of threat / material-exposure detection
## VALID MEASUREMENT · **CONFIRMED IMPROVEMENT** · Gate 1 still UNMET

**Date:** 2026-11-06 · **Branch:** `arena/6a6a2ba3-stockbear`
**Prereg:** `docs/DEV6_PREREG_EXP0054.md`, SHA-256
`48e800e804dbaa27b32d369c368b3c7baed42c931a6d6236bc1166a4d5b993ea` (frozen before
any game, digest enforced by the runner in every job)
**Pinned source:** `dfb4838912aec3e6426c55b7728d6fefe77aca82`
**Tier-1 run:** 42244166583 (SUCCESS, 4 isolated VMs) · **Export run:** 42334347915
**Raw evidence:** `benchmarks/exp-runs/tier1-export/run-42244166583/`
**Independent audit:** `benchmarks/recovery/exp0054_independent_raw_audit.json`

---

## 1. Result

Fixed time **40+4 ms**, Hash 16, Threads 1, max-plies 240. Arm A = candidate with
`ThreatDetection 1 1` (configuration **unchanged** from the exp-0053 screen);
arm B = the **exact released `v0.1.0-dev5` artifact**
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`.
All figures independently recomputed from raw per-game JSONL.

| Scope | W/D/L | Clusters | CR1 Elo | 95% CI (opening-clustered, two-sided) |
|---|---|---|---|---|
| batchA | 729/651/610 | 990 | **+20.3781** | [+9.0853, +31.7141] |
| batchB | 762/622/607 | 991 | **+26.6973** | [+15.8012, +37.6461] |
| **FROZEN COMBINED (A+B)** | **1491/1273/1217** | **1981** | **+23.5374** | **[+15.6937, +31.4052]** |
| stage0 null | 131/131/135 | 197 | −3.5274 | [−21.4982, +14.4245] |
| candidate null | 142/112/146 | 200 | −3.4745 | [−20.8345, +13.8682] |

Independent cluster bootstrap: **[+15.6197, +31.3912]**, agreeing with CR1.
Batch label overlap **0**. Design effect 1.0. 3,981 scored games; 3,962 enter the
primary paired estimate.

## 2. Frozen decision rules applied verbatim

| Condition (prereg §6) | Test | Outcome |
|---|---|---|
| point ≥ +10 | +23.5374 | **PASS** |
| combined LCB > 0 | +15.6937 | **PASS** |
| batchA ≥ −5 | +20.3781 | **PASS** |
| batchB ≥ −5 | +26.6973 | **PASS** |
| stage0 null CI includes 0 | [−21.50, +14.42] | **PASS** |
| candidate null CI includes 0 | [−20.83, +13.87] | **PASS** |
| audit issues == 0 | 0 | **PASS** |

### → **CONFIRMED IMPROVEMENT**

This is the **first independently confirmed strength gain** of the recovery
mission. `ThreatDetection` is now a **banked** improvement, eligible for
inclusion in an integrated final candidate.

## 3. Screen vs confirmation — replication, not pooling

| Instrument | Games | Point | 95% CI |
|---|---|---|---|
| exp-0053 SCREEN | 2,000 | +24.6338 | [+13.1027, +36.2193] |
| exp-0054 CONFIRMATION | 4,000 | **+23.5374** | **[+15.6937, +31.4052]** |

The two estimates differ by **1.10 Elo** on **entirely disjoint openings**
(seed 2026110653 vs 2026110654; the confirmation suite was independently verified
to have **0** overlap with all 54,441 earlier committed positions). The
confirmation's half-width narrowed from ~±11.6 to ~±7.9 as designed.

**The estimates are NOT pooled and NOT averaged.** The confirmation stands alone
as the banked evidence; the screen was the selection instrument. Both batches in
the confirmation are independently positive with LCB > 0, unlike the screen where
batchB's CI straddled zero.

## 4. Validity — PASS, independently established

- **0 TIME_FORFEIT, 0 ILLEGAL, 0 ENGINE_FAILURE in all four jobs.**
- Both validity nulls include 0.
- **PGN replay: 4,800/4,800 games**, every move legal, every outcome consistent,
  **0 inconsistent**.
- **54/54** committed blobs and **44/44** per-job `SHA256SUMS` verified.
- **Per-arm `EvalParams LOAD VERIFIED`** in every job, cross-checked against raw
  probe output *and* the frozen plan re-read from the pinned source commit.
- Arm digests verified against the declared design: arm A = packaged candidate,
  arm B = exact dev5 `391cb50e…5bdb918`.
- No negative clocks; minimum remaining 13.66 ms.
- **TOTAL ISSUES: 0 — INDEPENDENT AUDIT PASS.**

Attribution was already established by exp-0053's baseline-equivalence diagnostic
(+1.7459 [−20.6462, +24.1526], CI includes 0), and the configuration is unchanged,
so the effect is attributable to `ThreatDetection` rather than to unrelated
dev6-lineage differences.

## 5. What is and is not established

**Established:** a real, replicated, independently audited **+23.5 Elo** gain at
40+4 ms from one default-off evaluation term costing **+1.97%** of evaluation
time, correct against an independent oracle (800 positions, 0 mismatches),
consistent across the breakdown invariant (3,997 positions), and covered by a
mutation matrix in which **7 of 7** applied mutants were killed.

**NOT established:** Gate 1. The gate requires combined point ≥ **+75** AND
two-sided opening-clustered 95% **LCB strictly > +50**. At +23.54 [+15.69, +31.41]
this candidate meets **neither**. Roughly three further gains of this size would
be needed, and even then the total may **not** be inferred by addition — the
integrated candidate must be measured directly against the released baseline.

## 6. Disposition

- `ThreatDetection` remains **shipped 0 (default-OFF)**. Banking a confirmed
  improvement does not authorize a default change; only an integrated candidate
  that passes Gate 1 could do that, and that requires explicit user authorization.
- exp-0054 is **CLOSED / CONFIRMED**. It may not be re-run or pooled. Its 2,400
  openings and 4,800 games are burned for selection purposes.
- Public identity stays **`v0.1.0-dev5`**. No version bump, tag, release, deploy
  or merge. `origin/main` untouched.

## 7. Next action

The mission continues. The strongest remaining identified gap is **passed-pawn
evaluation**: StockBear scores a passer only as `advance² × PassedPawnAdvance`
(mg 1, eg 6), with **no** consideration of blockers, defending/attacking king
proximity, or whether the advance square is safe. King-proximity terms are
entirely absent from the parameter table. This is distinct from the abandoned
exp-0026 bundle, which contained only the narrow `ConnectedPassed` and
`RookBehindPassed` counts, and it carries the largest external anchor found
(MadChess passed-pawn rework, +119 Elo at bullet). It will enter under its own
preregistration with the same pre-game scale/cost/liveness/mutation discipline.

Mission status is governed solely by `STOCKBEAR_COMPLETION_CHECKLIST.md`, which
remains **incomplete**.
