# exp-0036 — FIXED-TIME confirmation of exp-0035 (result report, authoritative)

**Prereg:** `docs/DEV6_PREREG_EXP0036.md`, SHA
`430fe96ebd4095e7a4df84716f0b909f175f04cd95cfd4e55c303346f03e610d`, frozen
BEFORE any fixed-time game. **Control: FIXED TIME `--base-ms 40 --inc-ms 4`,
hash 16, threads 1, max-plies 240; `--nodes` NEVER used.** This is genuinely
fixed-time evidence and is kept strictly separate from exp-0035's fixed-node
`+27.10 [+15.94,+38.33]`.

## Runner tier — disclosed, not disguised
- **Tier 1 (intended GitHub-hosted isolated VM): BLOCKED by the authorization
  boundary.** `.github/workflows/dev6-lane.yml` at the pushed SHA has no
  `workflow_dispatch` (only `on: push: paths:`), is absent from `main`
  (HTTP 404), and `scripts/actions_dev6_lane.sh:commit_and_push()` pushes
  result commits. Triggering a NEW exp-0036 job set would require committing a
  new `dev6-trigger.json` AND would generate further remote writes. Exactly ONE
  remote write was authorized (11 commits through `03868da`). No second push
  was made; Tier 1 is recorded as NOT RUN.
- **Tier 2 (executed): LOCAL dedicated core** (`taskset -c 1`, no concurrent
  CPU work), with a pre-registered validity gate. This is **NOT a GitHub-hosted
  isolated VM**. Tier-2 results are corroborating/conditional and cannot
  satisfy Gate 4's packaged-artifact requirement.

## Stage 0 — frozen runner VALIDITY GATE: **PASS**
400-game 40+4 ms null control, bit-identical binaries (candidate OFF vs OFF),
dedicated core: `+129=130-141`, Elo `-10.43 [-31.86,+10.93]`, **0
TIME_FORFEIT**, 0 illegal/UCI failures, CI includes 0. Fixed-depth NPS ratio
candidate/official-dev5 = **1.0059**, inside frozen `[0.97,1.03]`. All four
pre-registered criteria passed, so Stage 1 was permitted to run.

## Stage 1 results (two-sided opening-clustered CR1 95 % CI)

| arm | control | games | Elo | 95 % CI | forfeits |
|---|---|---|---|---|---|
| batch A | candidate ON vs official dev5 | 1,000 | +17.14 | [+1.24, +33.12] | 0 |
| batch B | candidate ON vs official dev5 | 997 | +25.91 | [+10.03, +41.91] | 0 |
| **combined** | candidate ON vs official dev5 | **1,994** | **+21.52** | **[+10.28, +32.81]** | **0** |
| null | candidate OFF vs OFF (identical) | 400 | -1.75 | [-22.39, +18.87] | 0 |
| Track A context | candidate ON vs same-toolchain dev5 rebuild | 400 | +26.24 | [+0.99, +51.77] | 0 |

Combined `+735=645-614`, score 0.5303, 994 clusters; 6
`UNADJUDICATED_MAX_PLIES` exclusions (documented rule). 0 illegal moves,
crashes, UCI failures or TIME_FORFEIT events across every arm.

Independent re-audit (`scripts/dev6_audit.py`): **201 stored values re-verified
from raw JSONL, AUDIT PASS**; independent Elo-from-score +21.11 agrees with
stored CR1 +21.52.

## Gate evaluation — `docs/DEV6_PREREG.md` §8 UNCHANGED, no weakening

| Gate | verdict | evidence |
|---|---|---|
| **Gate 1** | **FAIL** | combined point +21.52 < +75; 95 % LCB +10.28 is NOT strictly > +50. Sub-clauses "both batches positive" (+17.14, +25.91) and "reasonably consistent" are satisfied, but the primary thresholds are not. |
| Gate 2 | direction supported by both independent datasets | both batches positive with overlapping CIs; Gate 1 still fails |
| Gate 3 | **PASS** | null -1.75 [-22.39,+18.87] includes 0; Stage-0 null -10.43 [-31.86,+10.93] includes 0 |
| **Gate 4** | **UNMET** | local correctness sub-criteria pass (0 forfeits/illegal/UCI), but there is NO packaged candidate release artifact, the CI-built artifacts use a different build image (no portable flags) and could not be downloaded (blob CDN EOF), and Tier 2 is not an isolated VM. "The exact candidate release artifact must be the tested binary" is unsatisfied. |

**Frozen futility boundary triggered:** combined 95 % **upper** bound
+32.81 < +50, so Gate 1 is conclusively unmet and the full 3,300-pairs/batch
Stage 2 is unnecessary. This closes exp-0036 at its pre-registered futility
boundary; it does NOT weaken any gate.

**Overall: FAILURE / GATE NOT MET.** No strength claim for release, no PR, no
merge, no tag, no release, no dev7. An approximately +21 Elo fixed-time effect
on a validity-gated local dedicated core is a real, reproducible measurement —
but it is roughly a quarter of the required +75, and it is not Tier-1 evidence.

## Final-source CI (purpose 1 of the authorization) — PASS
Run `41770918367`, event `push`, head SHA
`03868dafc6f644abb5b53caf2ef6ef1dda14e830`, conclusion **success**, **9/9 jobs
success** (Linux Clang Release, ASan+UBSan, Min CMake 3.16, Independent
reference, ThreadSanitizer, ubuntu-22.04 Debug/Release, windows-2022
Debug/Release). Artifact IDs pinned in
`benchmarks/dev6-baseline/final_source_ci.json`; artifact download blocked by
`productionresultssa6.blob.core.windows.net` (EOF, outside sandbox allow-list),
not retried unchanged. No `src/` changes were made after the push, so
`03868da` remains the exact CI-tested source SHA.

## Honest limitations
1. Tier 1 (isolated GitHub VMs) NOT RUN — needs one further authorization; this
   is the only decisive fixed-time confirmation that could address Gate 4.
2. Tier-2 local dedicated core passed its validity gate but is not equivalent
   to a dedicated VM; local clock-noise history (exp-0030 E4: 5 TIME_FORFEITs
   in 400 games) means local fixed-time remains conditional evidence.
3. Gate 1 is ~53 Elo short; Gate 4 has no packaged candidate artifact.
4. Fixed-node (exp-0035) and fixed-time (exp-0036) numbers are different
   quantities; neither is a gate pass, and neither is an absolute Elo.
5. No absolute/CCRL/FIDE rating, no gap-to-3000 claim.

Raw: `benchmarks/exp-runs/exp0036-*/` (PGN/JSONL/CSV),
`benchmarks/dev6-baseline/exp0036_results.json`,
`benchmarks/exp-runs/exp0036-run.log`.
