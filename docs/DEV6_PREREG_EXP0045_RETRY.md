# exp-0045 RETRY — valid-new-run preregistration (FROZEN before ANY retry game)

## Status that triggers this document: TECHNICAL FAILURE / INVALID MEASUREMENT
exp-0045 run `41817228668` (source `e41a0b18b4e522f57196e2834c8937f8c55019e8`,
frozen prereg `0abf66836ed0ad6d979a26a3d4ca8616416bfb88b8ca069875f1e7d4e7bb2863`)
completed all four isolated-VM jobs SUCCESS and CI `41817228408` SUCCESS, with
9/9 SHA256SUMS.txt OK in each of 4 bundles and a 44/0 independent AUDIT PASS.
BUT batchB `summary.json` records **1 TIME_FORFEIT**: game 272, a 14.1 ms move
at ply 118, `remaining_white_ms=-5.01`, in a long game whose clock was nearly
exhausted. Stage-0 validity null (0 forfeits, CI includes 0), candidate-options
null (0 forfeits, CI includes 0), batchA (0 forfeits) and batchB illegal /
engine_failure counts are all 0.

`docs/DEV6_PREREG_EXP0045.md` §5 FROZEN rule: "0 TIME_FORFEIT / illegal / UCI
/ engine failure in ANY of the four jobs, else INVALID MEASUREMENT." It is
therefore VIOLATED. **exp-0045 run `41817228668` is INVALID MEASUREMENT. ALL
Elo, CIs, W/D/L, LLR and the generic audit's "CLOSE" label from that run are
DISCARDED and may NEVER be used for a strength inference, a decision, a claim
or a pooled estimate.** The audit's `clean=False` is the correct signal. No
threshold is weakened: the frozen zero-forfeit rule is being ENFORCED, not
relaxed.

## Diagnosis and repair scope
The forfeit is a rare long-game clock exhaustion on one isolated VM (1 of 998
batchB games; exp-0043 and exp-0044 recorded 0 forfeits across ~4,000 games
each at the same control). It is a scheduling/timing outlier, not a systematic
mechanism effect, and it benefited the CANDIDATE arm (the control side ran out
of time) so it did not manufacture a positive result. No repair to the FROZEN
40+4 ms control, the clocks, the binary, the switch, the engine time manager or
the tournament driver is authorised: changing any of those would alter the
experiment rather than retrying it. The only in-scope repair is a **valid new
run** of the identical frozen design, which is what this document registers.
This follows the mission rule TECHNICAL FAILURE -> diagnose, repair within
scope, validate, retry using a valid new run.

## Frozen retry design (identical science, entirely fresh data)
- SAME mechanism `SkipDeadTTEval` (default OFF), SAME source-level switch and
  build flags, SAME single-switch A/B, SAME champion options
  (`EvalParams=research-data/params_abc.txt`, `TTEval=true`) in BOTH arms,
  SAME FIXED TIME `--base-ms 40 --inc-ms 4`, Hash 16, Threads 1, max-plies 240,
  **never `--nodes`**, SAME four isolated-VM jobs, SAME statistics and SAME
  independent raw-JSONL audit. No control change, no clock margin, no retune.
- NEW `experiment_id=exp0045_retry`, NEW dispatch attempt 22, NEW frozen plan
  `benchmarks/exp-runs/tier1-plan-exp0045-retry.json`, NEW seeds, and **1,400
  FRESH DISJOINT openings** from `scripts/dev6_exp0045_retry_openings.py`
  seed `2026120601`: ZERO exact-final-position overlap with **37,641** earlier
  committed positions across 140 files and ZERO duplicates within the 1,400,
  four mutually disjoint slices (stage0 200 / null 200 / batchA 500 / batchB
  500). Slice hashes in `benchmarks/dev6-baseline/exp0045_retry_suites.json`.
- **The invalid run `41817228668` is NEVER pooled, NEVER reused, and NEVER
  cited as strength evidence.** Its raw evidence stays in the repository as an
  audited technical-failure record only.
- One 400-game Stage-0 validity null (control options both sides) with a fresh
  ctest on the packaged binary, one 400-game candidate-options null, and two
  independent 1,000-game batches. Combined = batchA + batchB ONLY, frozen
  before the run; nulls are never pooled in.

## Frozen decision rules (copied verbatim from exp-0045 §6)
- **ADVANCE to a preregistered FRESH bundle candidate** (measured against exact
  dev5, never a post-hoc sum) only if combined point >= +20 Elo AND combined
  95 % LCB > 0 AND both batches >= −5 AND both null CIs include 0 AND 0
  forfeits/illegal/UCI/engine failures in ALL four jobs.
- **CLOSE (mechanism rejected / abandon)** if combined 95 % UCB < +10 Elo OR
  combined point <= 0.
- **If neither condition is met, exp-0045 is CLOSED AS INCONCLUSIVE** with no
  strength claim, no default change, no bundle, no retune, and the bit-exact
  dead-eval direction ABANDONED (the original single-run COMPUTE BOUND).
- **BOUNDED RETRY BUDGET:** exactly ONE valid retry is authorised. If this
  retry ALSO has any TIME_FORFEIT / illegal / UCI / engine failure in ANY job,
  exp-0045 is **CLOSED AS TECHNICALLY UNRESOLVABLE** at the frozen 40+4 ms
  control, with no strength inference and no further retries. This is a
  conservative compute/safety bound, not a threshold change; it can only
  prevent a claim, never create one.
- Gates 1-4 and `docs/DEV6_PREREG.md` §8 are untouched. Gate 1 (+75 / LCB > +50
  on two independent preregistered FIXED-TIME batches) and Gate 4 (exact
  packaged final-candidate binary/source/CI linkage) remain UNMET. No
  experiment outcome terminates the mission.

## Power / integrity (unchanged from exp-0045 §4)
A 2,800-game screen has ~13 Elo half-width and CANNOT resolve a +2-3 Elo
bit-exact NPS effect; it is powered for the +20 ADVANCE threshold and to rule
out a material regression only. Full-sized confirmation remains reserved by
the preregistered scheduler for a screen point >= +55. No local speedup, Elo,
absolute/CCRL/FIDE Elo or gap-to-3000 claim; no post-hoc stacking, no pooling,
no default change before gate satisfaction, no PR/merge/tag/release/deploy/
dev7, no strength claim. No exp-0041..0045 data are reused. Immutable dev5
baseline `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`,
`main` and all historical evidence remain untouched.
