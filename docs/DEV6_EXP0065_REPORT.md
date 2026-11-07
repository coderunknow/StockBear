# exp-0065 — persistent cross-move quiet history: VALID SCREEN / INCONCLUSIVE

**Verdict: VALID MEASUREMENT / INCONCLUSIVE.** Combined point **+9.7673** against a
preregistered ADVANCE bar of **+10**. The bar was missed by **0.23 Elo**. The rule
is applied as written: **no rounding, no extra games, no re-reading of the
criterion.** `PersistentHistory` **stays default OFF**. Gate 1 remains **UNMET**
and the mission remains **ACTIVE**.

## 1. Identity

| item | value |
|---|---|
| source pin / freeze commit | `6658abb20ebe0b1d1902a31e777d6f66574992dc` |
| prereg | `docs/DEV6_PREREG_EXP0065.md`, SHA-256 `4f3e0a018240ffbd862cca9b7129c964cd74cea7a607a99c77b08a06f69ea3ae` |
| frozen plan | `benchmarks/exp-runs/tier1-plan-exp0065.json` |
| candidate binary (all arms) | `e02573561d12017e616f2c86d29618b843e8509928ae022a6a939a3bd92b24f7` |
| EvalParams (all arms) | `research-data/params_exp0055_race.txt`, `82f93ba7…` |
| benchmark run | 42383867075 (success, 4/4 jobs) |
| export run | 42386174113 (success) → evidence commit `cbd200e` |
| protocol | fixed 40+4 ms, Hash 16, Threads 1, max 240 plies |
| openings | seed 2026110665, 3,900 fresh 8-ply openings, four disjoint slices |

Same-binary ablation on threats+race: A = `PersistentHistory=true`, B = `false`,
every other option identical. Primary batches never play dev5.

## 2. Result (independent recomputation from raw records)

| job | games | scored | complete pairs | W/D/L | Elo | 95 % CI |
|---|---:|---:|---:|---|---:|---|
| batchA | 3,000 | 2,984 | 1,484 | 1041/959/984 | **+6.7904** | [−2.3747, +15.9649] |
| batchB | 3,000 | 2,987 | 1,487 | 1063/967/957 | **+12.7396** | [+3.8232, +21.6727] |
| **primary combined** | **6,000** | **5,971** | **2,971** | **2104/1926/1941** | **+9.7673** | **[+3.3767, +16.1645]** |
| candidate null | 1,200 | 1,194 | 595 | 433/346/415 | +5.2557 | [−6.7760, +17.3001] |
| stage0 null | 600 | 596 | 296 | 207/171/218 | −6.4565 | [−21.6834, +8.7457] |

Primary estimate uses **5,942 games in 2,971 complete opening clusters**.
Independent cluster bootstrap: **[+3.3914, +16.2083]**, agreeing with the CR1
Student-t interval. Nulls never pooled. Batch label overlap **0**.

## 3. Frozen decision, applied mechanically

Prereg §8, registered before any game:

- **SCREEN ADVANCE** iff point ≥ **+10** AND LCB **> 0** AND both batch points ≥ −5.
  → LCB **+3.3767 > 0** ✔, both batches positive ✔, but point **+9.7673 < +10** ✘.
  **Not met.**
- **CLOSE (rejected)** iff UCB **< +3** OR point **≤ 0**.
  → UCB **+16.1645**, point **+9.7673 > 0**. **Not met.**
- Otherwise **INCONCLUSIVE** → **this is the verdict.**

The result is statistically distinguishable from zero and both batches are
positive. That makes the miss genuinely unfortunate, and it is exactly the
situation a preregistration exists for. The bar was +10, chosen before the games;
+9.7673 does not satisfy it. **No extra games were bought, no rounding was
applied, no batch was selected, and the criterion was not re-read.** The switch
remains default OFF and the mechanism is not promoted.

## 4. Validity — 25/25 conditions PASS

`benchmarks/recovery/exp0065_validity.json`:

- Frozen per-node cost guard and sequential efficacy gate both PASS, with both
  digests pinned in the plan; mutation matrix 9/9 killed with controls surviving;
  interactive UCI lifetime oracle PASS.
- Prereg has exactly one commit, matches the pinned digest, and the freeze is an
  ancestor of HEAD.
- Source/prereg/protocol identical in all four fingerprints (40+4, Hash 16,
  Threads 1, max 240). **Same binary** in every arm (built == packaged == A == B).
- Explicit `EvalParams`/`TTEval` on every arm; **explicit per-arm switch values**;
  primary arms differ **only** by the switch; recorded shipped default `false`;
  `engine_a_defaults == engine_b_defaults` everywhere.
- Both powered nulls **include zero**.
- Auditor issues **0**; committed blobs **54/54**; per-job SHA256SUMS **44/44**;
  positive per-arm load proofs in all four jobs.
- **7,800/7,800 PGNs replayed**, 0 inconsistencies; **0** forfeits, illegal moves
  or engine failures.
- Openings independently re-derived and disjoint; fresh **ctest 20/20** in stage0.

## 5. Pre-game evidence and the honest caveat

- Bench d4/d6/d7 all exact → default path bit-identical.
- **Sequential-replay efficacy gate:** 20 real games / 2,525 positions at depth 7
  → node ratio **0.9654**, **19/20** games individually improving (gate ≤0.98 plus
  majority).
- **Fixed-node cost guard:** **1.0776** ≤ 1.10, A/A spread 0.0859 < 0.10.
- Mutation matrix **9/9** killable killed; **2** equivalence controls survived.
- The plan recorded, *before the games*, that `0.9654 × 1.0776 ≈ 1.04`
  time-to-depth suggested the fixed-time effect might be neutral or negative.
  The games came back **positive** (+9.77), so that pessimistic reading was wrong
  — most plausibly because the per-node overhead estimate was noisy (A/A spread
  0.0859) and the sequential diagnostic understates the benefit at the shallower
  depths real 40+4 ms play actually reaches.

## 6. Interpretation and what it licenses

The structural finding stands and is now supported by game evidence pointing the
right way: **ordering learning that is erased every move is worth something when
it is allowed to persist.** But "pointing the right way" is not the preregistered
advance condition, and this cycle does not bank the mechanism.

What this **does** license is a *new, distinct* hypothesis with its own
preregistration — for example a different aging schedule, or extending
persistence to the continuation/counter-move tables that are currently still
erased. Those are different mechanisms and would need their own frozen bars; they
are **not** a retry of this sample, and this result may not be pooled with them.

Nothing here changes the integral picture: the best valid direct measurement
against published dev5 remains **+40.7732 [+36.2091, +45.3513]**, component
estimates are **never summed**, and Gate 1 requires a fresh direct integrated
measurement.

## 7. Disposition

- exp-0065: **INCONCLUSIVE**, closed for this hypothesis and this sample.
- `PersistentHistory`: implemented, tested, **default OFF**, not promoted.
- No historical verdict reopened; no prereg, plan or raw measurement edited.
- No merge, tag, release, prerelease, deploy or completion push.
- **Gate 1 UNMET. Mission ACTIVE.**
