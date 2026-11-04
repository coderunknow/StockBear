# DEV6 exp-0045 — bit-exact dead `evaluate()` elimination: INVALID run, bounded valid retry, FINAL CLOSE

**Status: CLOSED / ABANDONED. No strength claim, no default change, no retune,
no bundle, no PR/merge/tag/release/deploy/dev7.** Gates 1 and 4 remain UNMET;
Gate 2 is direction-supported, Gate 3 PASS. Mission ACTIVE / NOT COMPLETE.

## 1. Hypothesis and frozen design

exp-0039 profiled a bit-exact dead-code elimination (skip `evaluate(pos)` when
the TT eval is already usable and the value is provably unused), estimated only
a ~2.9 % timing residual — below the ~7 % noise floor — and reverted it without
games. exp-0045 was the **first Elo measurement** of that direction: a single
default-OFF UCI switch `SkipDeadTTEval` that skips `evaluate(pos)` only when the
switch is ON and the TT eval is valid. Values are bit-identical at a fixed node
count. No added per-node work, no search decision changed, no retune.

Frozen **before any game**:

| artifact | SHA-256 / id |
|---|---|
| `docs/DEV6_PREREG_EXP0045.md` | `0abf66836ed0ad6d979a26a3d4ca8616416bfb88b8ca069875f1e7d4e7bb2863` |
| `benchmarks/exp-runs/tier1-plan-exp0045.json` | `ffed7e591c4796e0aeb55c6ca0d9f123715e95764119f84b4025eb016897909f` |
| `docs/DEV6_PREREG_EXP0045_RETRY.md` | `2172063e22554df99064c54e0820b70db854e2339b0d5e87ccc321b6ca0bce60` |
| `benchmarks/exp-runs/tier1-plan-exp0045-retry.json` | `31f5170c51b5854159c5fc0a9758f5e3b29c74448b224aaafb17e1c07f3db9b2` |

Pre-result diagnostics (NOT strength evidence): default-OFF signatures
`243f9a1c1ba5b36f` / `a14ab62224f837e5` / `e45fa2ec2287eb41` unchanged; depth-16
with `ttEval=1` bit-identical OFF/ON; Release and ASan+UBSan ctest 11/11; UCI
defaults false; OFF/ON node counts identical at depths 8/10/12; ON skipped
40,187 of 379,656 `evaluate()` calls (10.6 %); local 12-repeat timing OFF
804.0 ms vs ON 823.5 ms (−2.37 %, noise-dominated → **NO speedup claim**).

Control, identical in both runs: FIXED TIME 40+4 ms (`--base-ms 40
--inc-ms 4`), Hash 16, Threads 1, 240 plies, **never `--nodes`**; champion
`EvalParams=research-data/params_abc.txt` and `TTEval=true` in BOTH arms; A
adds only `SkipDeadTTEval=true`. Four isolated `ubuntu-latest` VMs: 400-game
Stage-0 control/control validity null, 400-game candidate/candidate null, and
two independent 1,000-game batches. Combined = batchA + batchB only, frozen
before the run; nulls never pooled in. ~13 Elo half-width at 2,800 games: cannot
resolve an expected +2–3 Elo, powered for the +20 ADVANCE threshold and for
ruling out a material regression.

Frozen decision rules (identical in both preregs): **ADVANCE** only if combined
point ≥ +20 Elo AND 95 % LCB > 0 AND both batches ≥ −5 AND both null CIs
include 0 AND 0 forfeits/illegal/UCI/engine failures in ALL four jobs;
**CLOSE** if 95 % UCB < +10 Elo OR point ≤ 0; otherwise CLOSED AS
INCONCLUSIVE by the single-run compute bound (no confirmation, no post-hoc
sample increase). ADVANCE alone would NOT satisfy Gate 1 (+75 / LCB > +50 on two
independent preregistered fixed-time batches).

## 2. Original run `41817228668` — INVALID MEASUREMENT (all Elo DISCARDED)

Source `e41a0b18b4e522f57196e2834c8937f8c55019e8`, dispatch attempt 20,
benchmark `41817228668` SUCCESS, CI `41817228408` SUCCESS, deliberate export
`41818409701` SUCCESS. All four jobs SUCCESS, **9/9 `SHA256SUMS.txt` OK in each
of 4 bundles**, independent audit 44 stored values / 0 issues AUDIT PASS.

BUT `batchB/summary.json` has `time_forfeit=1`: game 272, a 14.1 ms move at ply
118, `remaining_white_ms=-5.01`, in a long game whose clock was nearly
exhausted. Stage-0 validity null, candidate-options null, batchA, and all
illegal / engine-failure counts were clean. The frozen prereg §5 requires **0
TIME_FORFEIT in ANY of the four jobs, else INVALID MEASUREMENT**. Diagnosis: a
rare isolated-VM long-game clock outlier (1/998 games; exp-0043 and exp-0044
recorded 0 forfeits across ~4,000 games each at the same control), not a
systematic mechanism effect; it favoured the candidate arm (the control side
ran out of time) so it could not manufacture a positive result. **No threshold
was weakened: the zero-forfeit rule was ENFORCED.**

Therefore **ALL Elo, CIs, W/D/L, LLR and the generic audit's "CLOSE" label from
this run are DISCARDED**, with NO strength inference, NO decision and NO pooling.
The audit's `clean=False` is the correct signal. Raw evidence is retained in
`benchmarks/exp-runs/tier1-export/run-41817228668/` as an audited technical-
failure record only. For completeness of the failure record (NOT results):
Stage-0 400 `136/138/126`; candidate null 398 `145/104/149`; batchA 997
`322/335/340`; batchB 998 `339/307/352`; a discarded naive combination would
have been `−5.4128 [−14.4266,+3.5938]`. These numbers are **not** used anywhere
in the verdict.

No repair to the frozen 40+4 ms control, the clocks, the binary, the switch,
the engine time manager or the tournament driver was authorised: changing any
of them would alter the experiment rather than retry it. Per the mission rule
TECHNICAL FAILURE → diagnose, repair within scope, validate, retry using a
valid new run, only a valid new run of the identical frozen design was
permitted.

## 3. Bounded valid retry `41818958001` — VALID, FINAL CLOSE

`docs/DEV6_PREREG_EXP0045_RETRY.md` was frozen BEFORE any retry game:
identical mechanism / switch / build flags / options / FIXED TIME control /
four isolated VMs / statistics / decision thresholds; NEW
`experiment_id=exp0045_retry`, dispatch attempt 22, NEW plan, NEW seeds, and
1,400 FRESH DISJOINT openings from `scripts/dev6_exp0045_retry_openings.py`
(seed `2026120601`, ZERO exact-final-position overlap with **37,641** earlier
committed positions across **140** files, ZERO duplicates; slice SHA-256s
stage0 `5e36e2f56a1269b7…`, null `da13cc7794d80f84…`, batchA
`3aaa333caf5dd809…`, batchB `fe6f7e3a85c223e4…`). Invalid run `41817228668`
NEVER pooled or reused. A BOUNDED RETRY BUDGET (exactly one retry) would have
closed exp-0045 AS TECHNICALLY UNRESOLVABLE had the retry also had a forfeit.

Provenance, from `fingerprint.json` / `run.log` (batchA bundle): pinned
`source_sha=9fb2a58e20b8aab131a56ddb3d749e60fce5278b` (verified equal to the
actual commit), prereg `0abf66836ed0ad6d…`, dev5 baseline
`391cb50e…` VERIFIED, build flags `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1
-flto=4`, **built binary SHA == packaged binary SHA**
`b839fae82b54ff8341abf350e07a6994f2cf1637dfbd4039373d95e2f37a8151`, default
bench `243f9a1c1ba5b36f`, UCI `SkipDeadTTEval type check default false`,
`TTEval type check default false`, A/B options exactly as frozen.

Benchmark `41818958001` SUCCESS (prepare + all four jobs SUCCESS; export
correctly skipped), CI `41818958003` SUCCESS, deliberate export
`41821624068` SUCCESS. Evidence:
`benchmarks/exp-runs/tier1-export/run-41818958001/`, four bundles, **9/9
`SHA256SUMS.txt` OK in each**, 44 stored values / 0 issues independent AUDIT
PASS with `clean=True`, **0 TIME_FORFEIT / 0 ILLEGAL / 0 ENGINE_FAILURE in
ALL four jobs** (unadjudicated max-plies: stage0 1, batchA 6, batchB 1, null
0 — counted as recorded games, not failures).

| job | games | W/D/L | CR1/t Elo | 95 % CI |
|---|---|---|---|---|
| Stage-0 validity null (control/control) | 399 | 118/155/126 | −6.1113 | [−23.3656, +11.1129] |
| candidate-options null | 400 | 152/111/137 | +13.0349 | [−6.3155, +32.4666] |
| batchA | 994 | 327/320/347 | −6.6823 | [−19.7471, +6.3636] |
| batchB | 999 | 324/320/355 | −11.1440 | [−24.5596, +2.2383] |

**FROZEN COMBINED batchA+batchB ONLY:** 1,993 games, W/D/L `651/640/702`,
score `0.4872052`, 993 clusters, **CR1/t Elo `−8.9240`, 95 % CI
`[−18.2792, +0.4182]`**, independent Elo-from-score `−8.8927`, independent
opening-clustered bootstrap 95 % `[−18.2107, +0.1749]`. Both null CIs include
0. Both batches are below −5 (`batches_ok=False`).

Frozen rule evaluation: `point >= +20` False, `LCB > 0` False,
`batches_ok` False, `clean` True, `nulls_ok` True → **ADVANCE False**;
`UCB (+0.4182) < +10` True **OR** `point (−8.9240) <= 0` True → **CLOSE True**.
`scripts/dev6_exp0038_audit.py 41818958001 exp0045_retry 20 10` and the
independent `scripts/dev6_exp0045_retry_decision.py` (recomputed from raw
`match.jsonl`, also enforcing the zero-forfeit validity gate) both reproduce:

```
VERDICT: CLOSE (mechanism rejected / abandoned; NO strength claim)
```

## 4. Consequences

- exp-0045 is **CLOSED / ABANDONED**. The bit-exact dead-`evaluate()`
  elimination direction is rejected for this code base at this control; it is
  **not** a proven engine-strength regression (a ~13 Elo half-width cannot
  resolve a few Elo), and no Elo may be quoted from the invalid run. No
  confirmation, no third run, no post-hoc sample increase, no pooling of the
  invalid run with the retry, no pooling of exp-0045 with exp-0039 / exp-0044
  or any earlier experiment, no retune of closed switches, no default change,
  no bundle.
- The single default-OFF switch stays OFF; `SkipDeadTTEval` is not promoted.
  No strength claim, no local speedup claim, no absolute/CCRL/FIDE Elo or
  gap-to-3000 claim.
- Gates: **1 UNMET** (no +75 / LCB > +50 combined result on two independent
  preregistered fixed-time batches), **2 direction-supported**, **3 PASS**,
  **4 UNMET** (no final-candidate artifact; the exact packaged binary was
  verified for these experiments but no release candidate exists). No
  PR/merge/tag/release/deploy/dev7.
- Mission remains ACTIVE / NOT COMPLETE. Immutable dev5 baseline
  `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`,
  `origin/main`, all historical evidence and `docs/DEV6_PREREG.md` §8 are
  untouched. A normal technical failure, invalid measurement, CI failure,
  inconclusive result or closed result cannot terminate the mission.
