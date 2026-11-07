# exp-0064 — extension-agnostic main-TT identity: VALID SCREEN / INCONCLUSIVE

**Verdict: VALID MEASUREMENT / INCONCLUSIVE.** The frozen decision rules were
applied mechanically to the fixed 6,000-game primary sample. The mechanism is
**neither advanced nor rejected**. `TTExtensionAgnostic` **stays default OFF**;
eligibility was not established. Gate 1 remains **UNMET** and the mission remains
**ACTIVE**.

## 1. Identity

| item | value |
|---|---|
| source pin / freeze commit | `48a6110104448b3e3197286c2216d21cf047aba0` |
| prereg | `docs/DEV6_PREREG_EXP0064.md`, SHA-256 `0f29d36bb5725df062f293cdfaa6237914ec8b44af7778c622931d26890d0cfc` |
| frozen plan | `benchmarks/exp-runs/tier1-plan-exp0064.json` |
| compute budget | `benchmarks/recovery/exp0064_compute_budget.json` |
| candidate binary (all arms) | `655fbbcc9ec13f0ff437cd844bedb970e32362289399f7c690a2424848380542` |
| EvalParams (all arms) | `research-data/params_exp0055_race.txt`, `82f93ba7a7b7e8e757c245098f5e2c4f42c866aa25124c73d0ad67ad11f89f01` |
| benchmark run | 42379450457 (success, 4/4 jobs) |
| export run | 42381671293 (success) → evidence commit `04a9312` |
| protocol | fixed 40+4 ms, Hash 16, Threads 1, max 240 plies |
| openings | seed 2026110664, 3,900 fresh 8-ply openings, four disjoint slices |

Design: **same-binary ablation** on the best valid integrated threats+race
candidate. A = `TTExtensionAgnostic=true`, B = `false`; every other option
identical. The primary batches never play dev5, so this run **cannot** satisfy
Gate 1 and is not an integral measurement.

## 2. Result (independent recomputation from raw records)

| job | games | scored | complete pairs | W/D/L | Elo | 95 % CI |
|---|---:|---:|---:|---|---:|---|
| batchA | 3,000 | 2,992 | 1,492 | 1043/963/986 | **+6.4045** | [−0.9887, +13.8035] |
| batchB | 3,000 | 2,992 | 1,492 | 1042/943/1007 | **+4.0753** | [−3.2934, +11.4477] |
| **primary combined** | **6,000** | **5,984** | **2,984** | **2085/1906/1993** | **+5.2399** | **[+0.0235, +10.4586]** |
| candidate null | 1,200 | 1,200 | 600 | 420/356/424 | −1.1581 | [−11.2137, +8.8955] |
| stage0 null | 600 | 595 | 295 | 191/213/191 | −0.0000 | [−14.1309, +14.1309] |

Primary estimate uses **5,968 games in 2,984 complete opening clusters** (the
symmetric complete-pair subset); 5,984 games were scored. Independent cluster
bootstrap cross-check: **[+0.0582, +10.3656]**, agreeing with the CR1 Student-t
interval. Nulls are **never pooled**. Batch label overlap: **0**.

## 3. Frozen decision, applied mechanically

Prereg §8, registered before any game:

- **SCREEN ADVANCE** iff point ≥ **+10** AND LCB **> 0** AND both batch points ≥ −5.
  → point **+5.2399 < +10**. **Not met.**
- **CLOSE (rejected)** iff UCB **< +3** OR point **≤ 0**.
  → UCB **+10.4586 ≥ +3** and point **+5.2399 > 0**. **Not met.**
- Otherwise **INCONCLUSIVE**. → **This is the verdict.**

No rescale, no retune, no extra games, no pooling, no favourable-batch selection,
no post-result criterion change. The interval does exclude zero, but the
preregistered advance bar was +10 and it was not reached; a barely-positive LCB is
**not** licence to promote the mechanism. The switch stays default OFF.

## 4. Validity — 22/22 conditions PASS

`benchmarks/recovery/exp0064_validity.json`, from
`scripts/recovery_exp0064_validity.py` (does not trust the audit banner):

- Frozen search-cost guard PASS and its digest pinned in the plan; prereg has
  exactly one commit and matches the pinned digest; freeze is an ancestor of HEAD.
- Source/prereg/protocol identical in all four fingerprints (40+4, Hash 16,
  Threads 1, max 240).
- **Same binary** in every arm: built == packaged == A == B, one digest overall.
- Explicit `EvalParams` and `TTEval` on every arm; **explicit per-arm switch
  values** recorded (`batchA/B` true/false, `null` true/true, `stage0`
  false/false); primary arms differ **only** by the switch; recorded shipped
  default is `false`; `engine_a_defaults == engine_b_defaults` in every job.
- Both powered nulls' intervals **include zero**.
- Auditor issues **0**; committed blobs **54/54**; per-job SHA256SUMS **44/44**;
  positive per-arm `EvalParams` load proofs in all four jobs.
- **7,800/7,800 PGNs replayed**, every move legal, **0** inconsistencies.
- **0** time forfeits, **0** illegal moves, **0** engine failures in every job.
- Openings independently re-derived and verified disjoint
  (`exp0064_suite_verification.json`, verdict PASS, issues []).
- Fresh **ctest 19/19** on the packaged candidate in stage0.

## 5. Pre-game engineering evidence (all completed before the first game)

- All three shipped bench signatures exact: d4 `243f9a1c1ba5b36f`,
  d6 `e06c4352681ae8eb`, d7 `5bceff035f2a4ae4` → default path bit-identical.
- Independent model oracle: **720,000** randomized checks, **0** mismatches;
  cross-budget reuse recovered while `rule50`/`historyContext` isolation held.
- Independent python-chess soundness oracle: 155 positions, **2,453** PV moves
  verified legal, **10** mate claims per arm all replayed to real checkmate with
  exact distances, **0** problems.
- Mutation matrix: **13/13** semantics-changing mutants **KILLED**; the
  semantics-preserving control **SURVIVED** as required.
- Switch liveness: **242/250 (96.8 %)** positions change tree; fixed-depth-7 total
  nodes **8,871,876 → 8,090,236 (0.9119×)**.
- Frozen search-cost guard: wall-time ratio **0.9593** (d5) / **0.8679** (d7),
  both ≤ 1.10; A/A spread 0.0373 / 0.0896, both < 0.10.

## 6. Interpretation

The diagnostic predicted +9.6…+20.0 % relative TT-hit gain; the measured
fixed-depth node reduction was 8.8 %, and exp-0015's scaling law (~2× nodes
≈ +90 Elo) would map that to roughly +11 Elo. The observed **+5.24** is below that
but inside the interval's upper half — consistent with a **real but small**
efficiency lever, not with a large one. Additional cutoffs also return shallower
stored values, which plausibly eats part of the theoretical gain.

The honest conclusion is that the mechanism is **directionally supported but
under-powered against the preregistered +10 bar**, and the preregistration
explicitly forbids buying more games to resolve it. It is recorded as
INCONCLUSIVE and left default OFF.

Even a favourable reading cannot reach the gate: the best valid integrated
candidate is **+40.7732 [+36.2091, +45.3513]** directly vs published dev5, and
component estimates are **never summed**. A new direct integrated measurement
against the exact dev5 executable would still be required for any gate claim.

## 7. Disposition

- exp-0064: **INCONCLUSIVE**, closed for this hypothesis and this sample.
- `TTExtensionAgnostic`: implemented, tested, **default OFF**, not promoted.
- No historical verdict reopened; no prereg, plan or raw measurement edited.
- No merge, tag, release, prerelease, deploy or completion push.
- **Gate 1 UNMET. Mission ACTIVE.** The next hypothesis is selected immediately
  from a fresh source-grounded investigation.
