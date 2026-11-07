# exp-0055 report — passed-pawn promotion race
## VALID MEASUREMENT / SCREEN ADVANCE (2026-11-07)

**This is a screen of an INCREMENT, not a Gate-1 result.** Gate 1 remains
**UNMET** and the mission remains **INCOMPLETE**.

- Prereg: `docs/DEV6_PREREG_EXP0055.md`, sha256
  `1fe7fd18f6df871d65fadfaf7d9b9dda94553cee3c231a0d84988b43502c24ea`,
  committed at `2594479` **before any exp-0055 game**.
- Plan: `benchmarks/exp-runs/tier1-plan-exp0055.json` (4 jobs, 3,800 games).
- Benchmark run **42336347904** — all 4 jobs SUCCESS.
- Evidence export run **42337431542**, mirrored at
  `benchmarks/exp-runs/tier1-export/run-42336347904/`.
- Independent audit: `benchmarks/recovery/exp0055_independent_raw_audit.json`
  (+ full stdout in `exp0055_independent_audit_stdout.txt`).

## 1. What was measured

A **same-binary ablation**. Both arms ran the *identical* candidate binary
(`9da443d13fcb5941c16b5742988e5de53f2edc92b24e2d7e69c684a58b0bf6b4`); only the
parameter file differed:

| arm | EvalParams | meaning |
|---|---|---|
| A | `params_exp0055_race.txt` (`82f93ba7…`) | threats ON + **race ON** (mg 0, eg 2) |
| B | `params_exp0053_threats.txt` (`7266eb4c…`) | threats ON + **race OFF** |

So the number below is the **increment contributed by the promotion-race term on
top of the already-confirmed threat term**. It is **not** a measurement against
dev5 and must **never** be added to exp-0054's +23.5374.

## 2. Result — independently recomputed from raw per-game JSONL

| scope | W/D/L | clusters | CR1 Elo | 95% CI |
|---|---|---|---|---|
| batchA | 598 / 421 / 477 | 746 | **+28.0044** | [+16.2507, +39.8223] |
| batchB | 590 / 423 / 486 | 749 | **+23.9268** | [+11.9705, +35.9401] |
| **FROZEN COMBINED** | **1188 / 844 / 963** | **1495** | **+25.9606** | **[+17.5818, +34.3697]** |
| stage0 null | 142 / 110 / 148 | 200 | −5.2119 | [−22.5700, +12.1201] |
| candidate null | 141 / 122 / 137 | 200 | +3.4745 | [−12.6319, +19.5958] |

Cluster bootstrap for the combined estimate: **[+17.5610, +34.3906]** — agrees
with the CR1/t interval. Design effect **1.0**; batch label overlap **0**.
2,995 games scored, 2,990 in the primary complete-pair estimate.

## 3. Frozen decision rules applied mechanically

All eleven conditions from prereg §6–§7, evaluated from the audit record:

| condition | result |
|---|---|
| auditor total issues = 0 | **PASS** (0) |
| 0 forfeits / illegal / engine failures | **PASS** (0 / 0 / 0) |
| full PGN replay consistent | **PASS** (3,800 replayed, 0 inconsistent) |
| both null CIs include 0 | **PASS** |
| committed blobs verify | **PASS** (54/54) |
| per-job SHA256SUMS verify | **PASS** (44/44) |
| batch opening overlap = 0 | **PASS** |
| stage0 fresh ctest on packaged binary | **PASS** (17/17, `ctest PASS`) |
| combined point ≥ +20 | **PASS** (+25.9606) |
| combined LCB > 0 | **PASS** (+17.5818) |
| both batches ≥ −5 | **PASS** (+28.00, +23.93) |

**Verdict: SCREEN ADVANCE.** Per-arm `EvalParams LOAD VERIFIED` was cross-checked
against the frozen plan read at its pinned SHA, with the **per-role** expected
digest (A = race config, B = threats config), and the auditor confirmed the
declared same-binary ablation really had equal arm digests.

### The five unscored games

`scored=2995` of 3,000. All five are `UNADJUDICATED_MAX_PLIES`: result `*`,
exactly 240 plies, `engine_failure=false`. This is the **pre-declared symmetric
policy** recorded in every match header — *"claimable draws automatically
claimed; capped games unadjudicated"* — not a forfeit, crash or measurement
defect. They fall out of complete pairs and are excluded from the clustered
estimate by the established methodology.

## 4. Pre-game gates (all executed before the first game)

| gate | result |
|---|---|
| independent python-chess oracle | 800 positions, **0 mismatches**, 352 non-zero |
| breakdown vs live invariant, race ON | **4,000 / 0** |
| breakdown vs live invariant, race OFF | **4,000 / 0** |
| registered suite | `passed_pawn_race` 7 tests; ctest **17/17** |
| every group run individually | **110** C++ assertions + 3 integration, all exit 0 |
| mutation matrix | **10/10 KILLED**, 0 survivors |
| liveness (depth 10) | **11/11** positions change the tree |
| cost, A/A control first | spread **0.0380** (< 0.10) ⇒ interpretable |
| cost, A/B increment | **+1.97 %** on `evaluate()` |
| ASan + UBSan | **17/17**, exit 0 |
| CI (incl. ThreadSanitizer) | run **42336347927**, **9/9 SUCCESS** |
| shipped bit-exactness | depth-4/6/7 signatures **all unchanged** |
| openings | seed 2026110655, 1,900 positions, **0 overlap** vs 56,841 |

The mutation set includes **`live_path_disabled`** and **both** clamp paths
(live and breakdown), so the suite demonstrably detects a dead mechanism rather
than merely checking arithmetic.

## 5. Two engineering findings worth keeping

**A measured cost dead end, fixed.** As a standalone second scan over all pawns
the term cost **+12.36 %** on `evaluate()`. Fusing it into the pawn walk that
already exists in `features()` — which already identifies passers by the identical
rule — cut the cost to **+1.97 %**. The fusion was proven **value-identical on all
4,000 positions** against the pre-fusion binary (Δ vectors equal element-wise;
race-OFF baseline unchanged). The evaluator already knew what was being recomputed.

**Scale chosen a priori, criterion never relaxed.** The magnitude envelope
(p99 ≤ 120, RMS < 40) was written before measurement. eg=1 gave overall RMS 7.14 —
*half* of exp-0052's 13.87, which was INCONCLUSIVE at 3,200 games. With **zero
exp-0055 games played**, eg=2 was frozen instead: overall RMS **14.28** / p99 58,
endgame RMS **35.66** / p99 106, both inside the unchanged envelope and close to
the confirmed threat term's 16.88. The original pre-declared record is preserved
verbatim with an appended amendment (`thresholds_changed: false`).

## 6. What this does and does not license

- **Does:** justify a separately preregistered **confirmation** of the *integral*
  candidate (threats + race) measured **directly** against the exact released
  dev5 artifact.
- **Does not:** satisfy Gate 1, change any shipped default, support a PR strength
  claim, or authorize a merge, tag, release or deploy. `PassedPawnRace` stays
  shipped **0**.
- **Never:** sum +25.9606 with exp-0054's +23.5374. Term interactions are real;
  only a direct measurement of the integral is admissible. The two screens and
  the confirmation are on disjoint openings and are never pooled.

**Gate status: 1 UNMET, 2 SUPPORTED, 3 PASS, 4 UNMET. Mission ACTIVE / INCOMPLETE.**
