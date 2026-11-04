> **SUPERSEDED by the 2026-11-04 continuation cycle** — see
> `docs/DEV6_RESEARCH_MATRIX.md`, `docs/DEV6_TIER1_INFRASTRUCTURE.md` and
> `docs/DEV6_PREREG_EXP0037_ADDENDUM.md`. This report remains the record
> of the one-push authorization cycle (CI `41770918367`, exp-0036).

# StockBear dev6 — post-authorization status (AUTHORITATIVE, 2026-11-04)

**Status: BLOCKED — NOT COMPLETE. Mission ACTIVE. All authorized work is
exhausted; Gates 1 and 4 are conclusively unmet/blocked. No strength claim,
no PR, no merge, no tag, no release, no deploy, no dev7.** This is a terminal
report for the one-push authorization, not a declaration that the dev6
acceptance criteria have been satisfied.

## 1. Authorization accounting (exactly ONE remote write)
| item | value |
|---|---|
| granted operation | `git push origin arena/3e6dd5b6-stockbear`, ONLY the existing 11 commits through `03868dafc6f644abb5b53caf2ef6ef1dda14e830` |
| executed | `797f5cb..03868da`; `git ls-remote` = `git rev-parse HEAD` = `03868da` |
| grant state | **CONSUMED** |
| other remote writes | NONE — no second push, no other ref/commit, no PR/merge/tag/release/deploy, no workflow dispatch, no dev5 artifact change, no dev7 |
| post-push local commits | documentation/results/raw evidence ONLY; `src/` unchanged, so `03868da` remains the exact CI-tested source SHA |

## 2. Purpose 1 — final-source CI on the exact pushed SHA: **PASS**
Run `41770918367`, `push`, head `03868dafc6f644abb5b53caf2ef6ef1dda14e830`,
conclusion **success**, **9/9 jobs success**: Linux Clang Release, Linux
ASan+UBSan, Linux ThreadSanitizer, Minimum CMake 3.16, Independent
reference/statistics/dead positions, ubuntu-22.04 Debug/Release,
windows-2022 Debug/Release. Evidence
`benchmarks/dev6-baseline/final_source_ci.json`. Artifact IDs pinned; artifact
download blocked by `productionresultssa6.blob.core.windows.net` EOF (host
outside the sandbox allow-list), not retried unchanged. CI builds use a plain
CMake Release image WITHOUT the pinned portable flags, so CI artifacts are NOT
the pinned Track A match binaries.

## 3. Purpose 2 — preregistered FIXED-TIME confirmation of exp-0035

### Tier 1 (GitHub-hosted isolated VM): BLOCKED, recorded as NOT RUN
`.github/workflows/dev6-lane.yml` at `03868da` has **no `workflow_dispatch`**
(only `on: push: paths:`), is absent on `main` (HTTP 404), its trigger file is
still the historical exp0027/28/29 cycle, and
`scripts/actions_dev6_lane.sh:commit_and_push()` pushes result commits back.
A new exp-0036 job set therefore requires a new prereg + trigger commit AND
generates further result pushes — a **SECOND remote write**, not authorized.
No second push was made; no dispatch was attempted; no claim that Tier 1 ran.

### Tier 2 (LOCAL dedicated core, executed): frozen validity gate PASSED
`scripts/dev6_exp0036.py --all`, `taskset -c 1`, no concurrent CPU work,
`--base-ms 40 --inc-ms 4` (NO `--nodes`), hash 16, threads 1, max-plies 240,
fresh disjoint suites. Prereg `docs/DEV6_PREREG_EXP0036.md` SHA
`430fe96e...` frozen before any fixed-time game, Gates 1–4 reproduced verbatim.
Stage 0: 400-game null `-10.43 [-31.86,+10.93]`, **0 TIME_FORFEIT**, 0
illegal/UCI failures, NPS 1.0059 in `[0.97,1.03]` -> **validity PASS**.

| arm | games | Elo (two-sided 95 % CR1) | forfeits |
|---|---|---|---|
| batch A (cand ON vs official dev5) | 1,000 | +17.14 [+1.24,+33.12] | 0 |
| batch B (cand ON vs official dev5) | 997 | +25.91 [+10.03,+41.91] | 0 |
| **combined** | **1,994** | **+21.52 [+10.28,+32.81]** | **0** |
| null (OFF vs OFF, identical) | 400 | -1.75 [-22.39,+18.87] | 0 |
| Track A context (ON vs same-toolchain dev5) | 400 | +26.24 [+0.99,+51.77] | 0 |

Combined `+735=645-614`, score 0.5303, 994 clusters, 6 documented
`UNADJUDICATED_MAX_PLIES` exclusions, 0 illegal/crash/UCI/TIME_FORFEIT events.
Independent re-audit: **201 stored values re-verified from raw JSONL, AUDIT
PASS**; Elo-from-score +21.11 agrees with stored CR1 +21.52.

Tier 2 is a dedicated **core**, NOT a dedicated VM. Its results are
corroborating/conditional fixed-time evidence and cannot satisfy Gate 4.

## 4. Gate verdict — `docs/DEV6_PREREG.md` §8 UNCHANGED, no weakening
| Gate | verdict | decisive evidence |
|---|---|---|
| **1** | **FAIL** | combined point +21.52 < +75; 95 % LCB +10.28 NOT strictly > +50. Both batches positive (+17.14, +25.91) and consistent, but the thresholds are not met. |
| 2 | direction supported by both independent preregistered datasets | both batches positive with overlapping CIs; does not rescue Gate 1 |
| **3** | **PASS** | null -1.75 [-22.39,+18.87] and Stage-0 null -10.43 [-31.86,+10.93] both include 0 |
| **4** | **UNMET** | local correctness sub-criteria pass, but there is NO packaged candidate release artifact; CI artifacts are a different build image and undownloadable; Tier 1 isolated runners not run. "The exact candidate release artifact must be the tested binary" is unsatisfied. |

**Frozen futility boundary triggered:** combined 95 % upper bound +32.81 <
+50 -> Gate 1 conclusively unmet; the 3,300-pairs/batch Stage 2 is
unnecessary. exp-0036 closed at its pre-registered futility boundary. Gate 1
remains ~53 Elo short of the required point estimate.

**ANY unmet gate -> FAILURE / gate not met.** No PR/merge/tag/release.

## 5. What is and is not established
- **Established:** a modest, reproducible **fixed-time** gain of about +21 Elo
  for `BadCapturePruning=true` on a validity-gated local dedicated core, with
  clean nulls, both independent batches positive, zero forfeits, and an
  independent raw-data audit. Also: exact-source CI is green on 9/9 jobs.
- **NOT established:** any Gate 1 pass, any Gate 4 pass, any release-worthy
  strength claim, any Tier-1 isolated-runner confirmation, any packaged
  candidate artifact, any absolute/CCRL/FIDE Elo, any gap-to-3000.
- **Kept strictly separate:** exp-0035 `+27.10 [+15.94,+38.33]` is FIXED NODE;
  exp-0036 `+21.52 [+10.28,+32.81]` is FIXED TIME Tier 2. Neither is the
  other; neither is a gate pass. `BadCapturePruning` remains default OFF and
  default builds remain bit-identical to dev5.
- 3,000 Elo remains a long-term strategic target only.

## 6. Evidence map
`docs/DEV6_EXP0036_REPORT.md` (full result), `docs/DEV6_PREREG_EXP0036.md`
(frozen prereg), `docs/DEV6_PREREG_EXP0037.md` (next isolated direction,
NOT run), `benchmarks/dev6-baseline/{exp0036_results.json,final_source_ci.json}`,
`benchmarks/exp-runs/exp0036-*/` (PGN/JSONL/CSV),
`benchmarks/exp-runs/exp0036-run.log`, `scripts/dev6_exp0036.py`,
`scripts/dev6_audit.py` (201 values), `benchmarks/FAILURE_LEDGER.md`
(exp-0036 + CI entries), `CHANGELOG.md`, `DESIGN_LOG.md`, `AGENTS_LOG.md`.

## 7. Exact next action (requires NEW explicit authorization)
Re-run decisive fixed-time confirmation on **Tier-1 GitHub-hosted isolated
VMs** with an exp-0036-style prereg (two independent batches, clean nulls,
Gate 1–4 unchanged), produce the **packaged candidate release artifact** and
test that exact binary, then run final-source CI on the exact head. This needs
a new prereg/trigger commit plus result pushes — i.e. **one further authorized
remote write** — and must not be performed under the consumed grant. In
parallel, `docs/DEV6_PREREG_EXP0037.md` freezes ProbCut as the next isolated
research direction; it is preregistered but NOT executed.
