# exp-0063 — VALID SCREEN / CLOSED (battery mechanism rejected)

**Verdict: VALID MEASUREMENT — CLOSED (mechanism rejected).** The king-slider
battery mechanism, after a semantics-preserving cost optimization, passed the
prospective CI cost gate but produced a **negative** fixed-time screen estimate:
**−6.0300 Elo, two-sided opening-clustered 95% CI [−14.1476, +2.0809]** over
threats+race in the identical binary. The frozen close rule (point ≤ 0 or
UCB < +5, valid) is satisfied. This closes the battery direction; it is not a
Gate-1 measurement and authorizes no release/merge/tag.

## Cost optimization and prospective gate

exp-0061 had failed the cost gate before games (increment 1.17094, combined
1.25063). exp-0063 kept the **same mechanism, weights, cap and frozen scale**
(`KingSliderBattery=(10,0)`, config sha `7e529623…`) but replaced per-slider
`abs(df)/abs(dr)` geometry and the extra branch inside the king-danger loop with
hoisted ray masks (`FileBB|RankBB`, static empty-occupancy diagonal table) and a
separate aligned-slider count path. Oracle/breakdown agreement and 11/11 mutants
verify semantic preservation; default-off bench signatures remain exact.

Prospective CI cost gate **PASS before games** (run 42365991406 prepare):

- A/A spread **0.026314** (<0.10), A/A median **0.998597** ([0.98,1.02]).
- Battery increment median **1.044700** (≤1.05).
- Combined vs champion median **1.088612** (≤1.10).
- Raw cost evidence: `benchmarks/exp-runs/tier1-export/run-42365991406/cost-gate-exp0063-run42365991406/`
  (13/13 SHA256SUMS verified). This is a new prospective pass for exp-0063; it
  does not retroactively validate exp-0061.

## Frozen registration and identities

- Prereg `docs/DEV6_PREREG_EXP0063.md`, SHA-256
  `31c481f3cd14969671bb9cf529015b3fc9ef4d1a8d656b4e7eab02bb8dc5e0a0`, frozen at
  `7d9aa8f03741c97bac8ee134f5cb913ceffbc216` before dispatch `d292c59`.
- Benchmark run **42365991406** SUCCESS; export run **42367464017** SUCCESS;
  raw mirror `benchmarks/exp-runs/tier1-export/run-42365991406` (export commit
  `215829d4667db0529d6ca963165a4fd0fdd8f285`).
- Candidate binary SHA-256 (identical in all arms):
  `5f923f4f2e7ba5050e2ef28c446f3319fbac4f43b3ddfd5dd6a91b5500fed988`.
- Candidate config `research-data/params_exp0061_battery.txt` sha `7e529623…`;
  ablation `research-data/params_exp0055_race.txt` sha `82f93ba7…`; stage0
  champion `research-data/params_abc.txt` sha `8a9dc81f…`.
- Protocol fixed 40+4 ms, Hash 16, Threads 1, max-plies 240, TTEval=true; fresh
  openings seed **2026110663**, 2,900 openings, suite verification PASS.

## Results (independent recomputation)

| arm | games replayed | scored | W/D/L | Elo | 95% CI |
|---|---:|---:|---|---:|---|
| batchA | 2,000 | 1,997 | 653/656/688 | −6.0990 | [−17.8042, +5.5923] |
| batchB | 2,000 | 1,991 | 676/603/712 | −5.9606 | [−17.2366, +5.3027] |
| **primary combined** | **4,000** | **3,988** | **1329/1259/1400** | **−6.0300** | **[−14.1476, +2.0809]** |
| candidate null | 1,200 | 1,196 | 407/385/404 | +0.8744 | [−9.9834, +11.7340] |
| stage0 null | 600 | 598 | 197/195/206 | −5.8300 | [−21.1728, +9.4901] |

Primary exclusions: symmetric `UNADJUDICATED_MAX_PLIES` 3+9=12. Nulls never
pooled. Independent bootstrap primary [−14.0764, +2.0098], consistent with CR1/t.

## Validity and integrity

`scripts/recovery_exp0063_validity.py` → `benchmarks/recovery/exp0063_validity.json`:
**16/16 checks PASS**, verdict `CLOSED`, `gate1_met=false`.

- Independent auditor issues **0**; committed blobs **68/68**; per-job sums
  **44/44**; cost sums **13/13**.
- **5,800/5,800 PGNs replayed**, 0 inconsistent; zero forfeits/illegal/failures.
- Both powered null CIs include zero; identical arm binaries; positive load
  proofs; fresh stage0 ctest **18/18**.
- Pre-game correctness: oracle 800/0 (197 non-zero), evaldata 4000/0, mutation
  matrix **11/11 KILLED**, liveness depth-8 12/12 trees and 2/12 bestmoves,
  bench signatures exact.

## Decision and consequences

Frozen screen rule: ADVANCE iff point ≥ +15, LCB > 0, both batches ≥ −5 and valid;
CLOSE iff UCB < +5 or point ≤ 0, valid. Observed point **−6.0300** (and UCB
**+2.0809**) satisfies CLOSE. The battery mechanism is rejected at the frozen
scale; no rescale, retune, additional games or pooling is permitted.

- Best valid direct integral candidate remains **threats+race**: exp-0062
  **+40.7732 [+36.2091, +45.3513]** vs published dev5 — **Gate 1 UNMET**.
- exp-0061 remains BLOCKED pre-game; exp-0063 is a distinct optimized identity
  with a prospective cost pass and a valid negative screen.
- No merge, tag, release, prerelease, deploy or new PR; PR #2 untouched;
  `origin/main` remains `6e7c2e0`; public release identity remains dev5.

Mission remains **ACTIVE / INCOMPLETE**. The battery representational direction
is now closed by game evidence, not merely cost. Further progress requires a
distinct source-grounded direction with a fresh preregistration and eventual
direct integrated dev5 measurement; component Elo is never summed.
