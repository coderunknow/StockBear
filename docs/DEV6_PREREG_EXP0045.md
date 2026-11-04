# exp-0045 — bit-exact dead `evaluate()` elimination on TT hits (FROZEN before ANY game)

Registered before ANY exp-0045 evaluation game. `docs/DEV6_PREREG.md` §8 is
UNCHANGED: Gate 1 still requires >= +75 Elo point AND combined two-sided
opening-clustered 95 % LCB > +50 on two independent preregistered FIXED-TIME
batches (§8 names exp-0028 + exp-0029); Gate 2 direction-supported by both
independent datasets; Gate 3 nulls compatible with zero; Gate 4 exact packaged
final-candidate binary/source/CI linkage and no correctness/illegal/protocol/
time-forfeit regression or unexplained benchmarked-vs-packaged difference. No
gate, threshold, margin or tolerance is weakened. This is experiment-level.

## 1. Why this direction (post-exp-0044 re-ranking)
exp-0044 (SEE-losing-capture ordering) is CLOSED AS INCONCLUSIVE / ABANDONED
at its frozen addendum compute bound: screen `+3.3140 [−7.2389,+13.8730]`,
bounded confirmation `+13.5977 [+2.1746,+25.0503]`, NEVER pooled. It was the
first direction since exp-0038 with two non-negative frozen combined points,
and it added ZERO per-node work. exp-0044's specific mechanism and any retune
are abandoned; no exp-0044 data may be reused.

The ranked matrix's next unexecuted direction that does NOT change any search
decision is **bit-exact `evaluate()` throughput**, explicitly requested as a
NEW properly powered frozen prereg rather than a silent reuse of the abandoned
exp-0038 cache. exp-0039 built exactly this fix (dead static evaluation on TT
hits), verified it bit-exact, measured ~2.9 % locally against a ~7 % shared-vCPU
noise floor, REVERTED it and spent NO games and made NO Elo or speedup claim.
That was a PRECISION/COST decision, not a negative strength result. The
unresolved question is therefore genuinely open: does a bit-exact NPS gain
convert to fixed-time Elo on isolated VMs? exp-0045 is the FIRST Elo
measurement of that hypothesis, with a different (isolated-VM, 40+4 ms,
2,800-game) design — not a repeat of exp-0039's profiling and not a parameter
change of any failed idea.

## 2. Hypothesis and exact code change (default OFF)
`SearchParams::skipDeadTTEval = false`; UCI `SkipDeadTTEval`;
`bench --param skipDeadTTEval=0|1`. In `Search::negamax` the shipped code is:

```
int staticEval = evaluate(pos);
if (ttEval && entry && !inCheck && entry->eval != VALUE_NONE)
    staticEval = int(entry->eval);   // overwrites the evaluation just computed
```

`evaluate()` is the full tapered evaluation (25-30 % of node time) and its
result is dead whenever a main-TT hit supplies a valid static eval. With the
switch ON that call is skipped and the value read directly from the TT. NO TT
entry, move, bound, score, mate value, stand-pat value, quiescence value,
pruning/extension/ordering decision or search depth changes: the OUTPUT IS
BIT-IDENTICAL at any fixed node count. The ONLY possible effect is time per
node, which at fixed 40+4 ms lets the candidate search more nodes. There is NO
added per-node work and no new time-forfeit mechanism (the fix can only make
the engine faster). `TTEval=true` and champion `EvalParams` are used in BOTH
arms, so TT evals are available to both; only the candidate skips the dead call.

Default-off build is bit-identical: bench `243f9a1c1ba5b36f`, d16
`a14ab62224f837e5`, d12 params `e45fa2ec2287eb41`; d16 with `ttEval=1` gives
`a14ab62224f837e5` both OFF and ON (explicit bit-exactness check); Release
ctest 11/11, ASan+UBSan ctest 11/11
(`benchmarks/dev6-baseline/exp0045_asan_ctest.log`); UCI `SkipDeadTTEval`
default false. Every dev6 strength switch remains default OFF.

## 3. MANDATORY mechanism-live and overhead diagnostic (BEFORE games)
Instrumented `SB_DEADEVAL_DEBUG` build from the FROZEN source, on 8 exp-0044
confirmation suite positions with `TTEval=true` and champion `EvalParams`:

- **Bit-exactness:** fixed-depth node counts OFF/ON are IDENTICAL position by
  position at depths 8, 10 and 12 (e.g. depth 12 `[72604, 497628, 311669,
  559024]` for both). No tree change at fixed nodes.
- **Mechanism live:** ON skipped `40,187` of `379,656` static-evaluation calls
  (10.6 %) in the first depth-12 repeat. The dead work is real and is actually
  removed. Hence the theoretical upper bound on the speedup is modest: only
  ~10.6 % of evaluations can be saved, i.e. roughly 2-3 % of total node time.
- **Timing (shared sandbox vCPU, 12 alternating repeats, depth 12, 4 positions):**
  OFF median total 804.0 ms, ON median 823.5 ms, i.e. a measured −2.37 %
  "speedup" (ON slower). This is NOISE-DOMINATED and is reported VERBATIM, not
  spun as a gain or a loss; it reproduces exp-0039's stated problem that a
  ~2-3 % effect cannot be resolved locally against build/CPU noise. No local
  speedup claim is made. The isolated-VM 40+4 ms Elo screen below is the
  measurement that can resolve the fixed-time consequence.

Interpretation: the mechanism is demonstrably live and bit-exact and adds NO
work; the size of its time effect is unresolved locally. That uncertainty is
the reason for the experiment, not a reason to skip it.

## 4. Power, explicitly (no hidden threshold change)
A 2,000-game paired screen has a combined 95 % half-width of ~13 Elo. A
+2-3 Elo bit-exact NPS effect is **NOT resolvable** by this screen; exp-0039's
power analysis already says a +3-8 Elo effect needs far more games, and the
project's preregistered scheduler reserves 3,300 pairs/batch (13,200 games)
ONLY for a candidate whose screen point >= +55. Therefore exp-0045 is powered
to (a) detect a >= +20 Elo ADVANCE, (b) detect a material regression, and
(c) decide whether the direction is worth ANY further compute. It is NOT
presented as "properly powered" for a +3 Elo effect. No post-hoc sample
increase is authorised: a single-run COMPUTE BOUND (§6) closes the experiment
if neither frozen condition is met. Gates 1-4 are untouched, and Gate 1
(+75 / LCB > +50) is far away regardless of outcome.

## 5. Frozen Tier-1 screen design
- `.github/workflows/dev6-tier1.yml`, one dedicated GitHub-hosted
  `ubuntu-latest` VM per matrix job, pinned `source_sha`, EXACT packaged
  candidate binary extracted and tested (Gate 4 identity). Export push has a
  bounded retry after the exp-0044 technical repair.
- **FIXED TIME `--base-ms 40 --inc-ms 4`**, Hash 16, Threads 1, max-plies 240,
  **never `--nodes`**. Both arms receive identical 40+4 ms clocks.
- ONE binary, single switch: candidate `SkipDeadTTEval=true` vs control
  `SkipDeadTTEval=false`. Zero toolchain confound. Both arms:
  `EvalParams=research-data/params_abc.txt`, `TTEval=true`.
- Stage-0 validity null 400 games with CONTROL options on both sides; a second
  400-game null with CANDIDATE options on both sides. Both CIs must include 0;
  0 TIME_FORFEIT / illegal / UCI / engine failure in ANY of the four jobs, else
  INVALID MEASUREMENT.
- batchA 1,000 games and batchB 1,000 games on two independent fresh disjoint
  500-opening suites, generated by `scripts/dev6_exp0045_openings.py` seed
  `2026120501` (1,400 openings total; 200 stage0 + 200 null + 500 + 500);
  programmatic ZERO exact-final-position overlap with **36,241** earlier
  committed positions across 135 files and ZERO duplicates within the 1,400.
  Colour-reversed, one pair per opening. Slice hashes in
  `benchmarks/dev6-baseline/exp0045_suites.json`.
- Statistics: W/D/L, paired pentanomial, opening-clustered CR1/t two-sided
  95 % CI per batch AND frozen combined, LLR labelled a normal approximation,
  independent recomputation from raw JSONL. Combined = batchA + batchB ONLY,
  frozen before the run; Stage-0 and null games are NEVER pooled in. Raw
  PGN/JSONL/CSV/summaries/audit/fingerprint/manifest/SHA256SUMS/UCI/run.log
  and the exact packaged `.tar.gz` uploaded per job and mirrored by a
  deliberate `mode=export` job.

## 6. Frozen decision rules (before results)
- **ADVANCE to a preregistered FRESH bundle candidate** (measured against exact
  dev5, NEVER a post-hoc sum) only if combined point >= +20 Elo AND combined
  95 % LCB > 0 AND both batches >= −5 AND both null CIs include 0 AND 0
  forfeits/illegal/UCI/engine failures in ALL four jobs. ADVANCE alone does
  NOT satisfy Gate 1.
- **CLOSE (mechanism rejected / abandon)** if combined 95 % UCB < +10 Elo OR
  combined point <= 0. Then `SkipDeadTTEval` stays default OFF, no retune, no
  bundle.
- **If neither condition is met, exp-0045 is CLOSED AS INCONCLUSIVE** with no
  strength claim, no default change, no bundle, no retune, and the bit-exact
  dead-eval direction ABANDONED. This is a SINGLE-RUN experiment-level COMPUTE
  BOUND, not a threshold change: it is justified by §4 (a +2-3 Elo effect
  cannot be resolved by a 2,800-game screen, and full-sized confirmation is
  reserved for screen point >= +55). It can only PREVENT a claim, never create
  one. Gates 1-4 and `docs/DEV6_PREREG.md` §8 are untouched. No experiment
  outcome terminates the mission.

## 7. Expected failure modes
Only ~10.6 % of `evaluate()` calls are skippable, so the maximum speedup is
small; the local timing measurement even came out slightly negative (noise).
At 40+4 ms the engine stops at 55-70 % of a ~4 ms soft budget, so a few extra
nodes may not change completed depth at all. A faster search can also change
WHICH iteration completes within the clock, which is a real (not bit-exact-at-
fixed-time) behavioural difference and could be slightly negative. Fixed-depth
node counts are identical by construction; that is NOT strength evidence.
No fixed-depth/node/timing proxy may be presented as fixed-time strength.

## 8. Non-claims / integrity
No local speedup, Elo, absolute/CCRL/FIDE Elo or gap-to-3000 claim. No
post-hoc stacking, no pooling, no default change before gate satisfaction, no
PR/merge/tag/release/deploy/dev7, no strength claim. No exp-0041/0042/0043/
0044 data are reused or pooled. Immutable dev5 baseline
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`, `main`
and all historical evidence remain untouched.
