# exp-0036 — FIXED-TIME confirmation of exp-0035 (preregistered, frozen before results)

**Frozen BEFORE any fixed-time game on this candidate.** Written after the ONE
authorized push of `03868dafc6f644abb5b53caf2ef6ef1dda14e830` (that push contains
NO fixed-time results), before any fixed-time result is collected. Nothing here
weakens `docs/DEV6_PREREG.md` §8; Gates 1–4 are reproduced verbatim in §6.

## 0. Why this experiment exists
exp-0035 established `+27.10 [+15.94,+38.33]` Elo for `BadCapturePruning=true`
at **fixed node** (`go nodes 6000`). That is **NOT fixed-time strength evidence**
and must never be presented as such. Gate 1 is defined at 40+4 ms. A fixed-time
confirmation is required before any strength claim about the switch.

## 1. Runner constraint (recorded, not disguised)
- **Tier 1 (intended, GitHub-hosted isolated VM):** `.github/workflows/dev6-lane.yml`
  runs each job on a dedicated `ubuntu-latest` VM. Verified on the pushed SHA:
  its `on:` is `push` with `paths:` only (NO `workflow_dispatch`), the workflow
  file is absent from `main` (HTTP 404), and
  `scripts/actions_dev6_lane.sh:commit_and_push()` pushes result commits back to
  the branch. Both **triggering a new job set** (committing a new
  `benchmarks/exp-runs/dev6-trigger.json`) and **its result commits** require a
  SECOND remote write. Authorization was for EXACTLY ONE remote write
  (`git push origin arena/3e6dd5b6-stockbear`, 11 commits through `03868da`).
  Therefore **Tier 1 is blocked by the authorization boundary**. It is not
  claimed as run, and no second push is made.
- **Tier 2 (authorized substitute, executed here):** local **dedicated-core**
  fixed-time execution (`taskset -c 1`, no concurrent CPU work) with a
  pre-registered VALIDITY GATE (§3). This is **NOT a GitHub-hosted isolated VM**;
  a Tier-2 result is labelled corroborating/conditional and CANNOT satisfy
  Gate 4's packaged-artifact requirement. Tier 1 remains the required decisive
  measurement and needs one further explicit authorization.

## 2. Identities / control / build provenance
- Pushed source SHA (CI target, exact): `03868dafc6f644abb5b53caf2ef6ef1dda14e830`.
- Candidate binary (Track A local pinned build): `build-exp0034/stockbear`
  SHA `075ec955a65acad4624cc6d3f4998763aaa7b968e4d01a27e73cd9dfd4c77d82`,
  built GCC 12.2.0 with `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`,
  no `-march=native`, Release/Ninja. Both arms use
  `EvalParams=research-data/params_abc.txt` + `TTEval=true`; candidate arm adds
  `BadCapturePruning=true`, control arm `BadCapturePruning=false`.
- Baseline (Track B, immutable, never rebuilt/renamed):
  `benchmarks/binaries/stockbear-dev5-release`
  `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`,
  `params_abc` + `TTEval=true`.
- Track A same-toolchain dev5 rebuild: `build-dev5/stockbear`
  `214cbed002e58fbc94d74a089491bba94634e9e8d06b782992548fdacaa9b501`.
- TC: **FIXED TIME** `--base-ms 40 --inc-ms 4`, Hash 16, Threads 1,
  `--max-plies 240`. NO `--nodes`. All arms paired colour-reversed, fresh
  disjoint opening suites (seed `2026111901`, 1,600 openings, excluding every
  earlier `openings*.txt`).

## 3. Stage 0 — RUNNER VALIDITY PILOT (frozen gate, run first)
200 pairs (400 games) 40+4 ms NULL control with **bit-identical** binaries
(candidate OFF vs candidate OFF, same SHA, same options), pinned to CPU 1, no
other CPU work. **PASS iff ALL:**
1. `0` TIME_FORFEIT events;
2. `0` illegal-move / crash / UCI failures;
3. two-sided opening-clustered 95 % CR1 CI includes 0;
4. fixed-depth NPS ratio (candidate local pinned build vs official dev5, best
   of 3 `bench --depth 12` runs each) inside **[0.97, 1.03]** — the tolerance
   frozen in exp-0030 (which measured B/A1 = 0.9906).

**If ANY fails → exp-0036 is classified INVALID MEASUREMENT** (clock-noise
confound, consistent with exp-0030 E4), Stage 1 is NOT run, no strength claim
is made, and the fixed-time confirmation is conclusively BLOCKED pending Tier 1.
This is a pre-registered validity rule, not a post-hoc tolerance.

## 4. Stage 1 — only if Stage 0 passes
| arm | A | B | pairs | games |
|---|---|---|---|---|
| batch A | candidate ON | official dev5 | 500 | 1,000 |
| batch B | candidate ON | official dev5 | 500 | 1,000 |
| null | candidate OFF | candidate OFF (identical) | 200 | 400 |
| Track A context | candidate ON | same-toolchain dev5 rebuild | 200 | 400 |

Fresh disjoint suites; colour-reversed pairs; 1 pair per distinct opening.
Power (from exp-0024 raw 3,284 pairs, `s2_eff=0.3623`): 500 pairs -> ±18.94
Elo half-width per batch, 1,000 combined -> ±13.38; 3,300 pairs -> ±7.36;
6,600 pairs -> ±5.21. The historical decisive design used 3,300 pairs/batch.

**Frozen futility boundary (efficiency, NOT a gate weakening):** if the Stage-1
combined two-sided 95 % **upper** bound is < +50 Elo, Gate 1 is conclusively
unmet and the full 3,300-pairs/batch Stage 2 is unnecessary. If point >= +75
AND upper bound >= +50, Stage 2 on Tier-1 isolated runners is REQUIRED before
any conclusion (and needs a further authorization).

## 5. Statistics / integrity
W/D/L, paired pentanomial, opening-clustered CR1/t two-sided 95 % CI, cluster
bootstrap (>=1,000 replicates), LLR labelled a normal approximation; both
batches reported separately AND combined; independent re-audit by
`scripts/dev6_audit.py`. No subset selection, no hidden negative batch, no
excluded games except the documented `UNADJUDICATED_MAX_PLIES` rule; point
estimates always accompanied by uncertainty. No test-set reuse as independent
validation.

## 6. Gates — verbatim from `docs/DEV6_PREREG.md` §8, UNCHANGED
- **Gate 1 (primary)**: COMBINED point estimate >= +75 Elo AND combined
  two-sided opening-clustered 95 % CI lower bound **strictly > +50**; BOTH
  batches show a positive point estimate; neither shows a material
  contradictory regression; the two batches are reasonably consistent.
- **Gate 2**: combined result supported by both independent pre-registered
  datasets.
- **Gate 3**: nulls compatible with zero.
- **Gate 4**: no unresolved correctness/illegal-move/protocol/time-forfeit
  regression; no unexplained difference between benchmarked and packaged
  binary. The exact candidate release artifact must be the tested binary.
- If ANY gate is unmet -> **FAILURE / gate not met**: no strength claim, no PR,
  no merge, no tag, no release. Results still preserved and reported in full.

Additional permanent blockers (not created by this experiment): there is NO
packaged candidate release artifact, and CI-built artifacts use a different
build image (no portable flags) from the pinned Track A binaries, so Gate 4
cannot pass from Tier 2 regardless of the match result.

## 7. Explicit non-claims
Fixed-node `+27.10 [+15.94,+38.33]` is NEVER reported as fixed-time strength.
No absolute/CCRL/FIDE Elo, no gap-to-3000 estimate. A Tier-2 PASS (if any) is
corroborating evidence only, NOT a gate pass. No PR/merge/tag/release/dev7.
Raw: `benchmarks/exp-runs/exp0036-*/`,
`benchmarks/dev6-baseline/exp0036_results.json`.
