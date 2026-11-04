# DEV6 exp-0046 — margin-adaptive null-move reduction: CLOSED AS INCONCLUSIVE

**Status: CLOSED AS INCONCLUSIVE / ABANDONED at the frozen single-run compute
bound. No strength claim, no default change, no retune, no bundle, no
confirmation, no post-hoc sample increase, no PR/merge/tag/release/deploy/
dev7.** Gates 1 and 4 remain UNMET; Gate 2 direction-supported, Gate 3 PASS.
Mission ACTIVE / NOT COMPLETE.

## 1. Hypothesis and frozen design

exp-0045 is CLOSED (INVALID original run + one bounded valid retry, FINAL
CLOSE). exp-0041/0042/0043 lost while changing which nodes are searched or
adding a ply; exp-0044 added ZERO per-node work and was the only non-negative
direction in that group, but is CLOSED AS INCONCLUSIVE at its frozen addendum
compute bound. The next ranked direction was a **NEW decision rule with ZERO
added per-node work**: the shipped null-move verification subtree uses a FIXED
`SB_NULLMOVE_R + depth/5`, discarding the SIZE of `staticEval - beta` that the
null-move guard already computes. exp-0046 makes ONLY that existing subtree
shallower when staticEval is far above beta, keeping the shipped depth when the
margin is marginal. It is NOT a constant retune, NOT "delete more nodes", NOT
any closed switch, and it reuses/pools NO earlier experiment's data.

Frozen **before any game**:

| artifact | SHA-256 / id |
|---|---|
| `docs/DEV6_PREREG_EXP0046.md` | `dda54084d2acffddcb7cd5d1134f8734858e9bf0c69d3ab2eb59d3aeab15dd61` |
| `benchmarks/exp-runs/tier1-plan-exp0046.json` | `557d51fc07ad18eb828e94b2cb273e7225956ca4e6cd55b2279216fb8ebaa18a` |
| exact launch source | `0792555ddd155b2426d926cccc5a16975f77682b` (pinned by `source_sha=HEAD`, verified in every `run.log`) |
| dispatch | `mode=benchmark experiment_id=exp0046 attempt=24` |

Mechanism: default-OFF UCI/bench switch `AdaptiveNullR`. At the EXISTING
null-move pruning site only, with all shipped guards unchanged:
`extra = min(2, (staticEval - beta)/200)`, `reduction = SB_NULLMOVE_R +
depth/5 + extra`. Frozen constants `AdaptiveNullMarginDivisor=200`,
`AdaptiveNullExtraCap=2`, chosen BEFORE any game from theory only, NEVER tuned
on Elo. OFF is byte-identical to the shipped default. No added evaluate/SEE/
movegen call, no extra ply, no TT/move/score/stand-pat/ordering/time decision
change beyond the existing null subtree's depth.

Pre-result diagnostics (NOT strength evidence): default-OFF signatures
`243f9a1c1ba5b36f` / `a14ab62224f837e5` (d16 with `ttEval=1`) /
`e45fa2ec2287eb41` (d12 with `params_abc.txt`); Release ctest 11/11;
ASan+UBSan ctest 11/11 (`benchmarks/dev6-baseline/exp0046_asan_ctest.log`);
UCI `AdaptiveNullR type check default false`. Instrumented
`SB_ADAPTIVE_NULL_DEBUG` build over 24 REAL exp-0046 suite positions: FIXED
DEPTH 10 OFF 4,311,394 nodes / ON 4,252,622 (−1.36 % tree change), 44,789
null-move nodes, 4,133 changed, 4,721 extra plies, LIVE 23/24; a 40 ms
fixed-time PROBE OFF 1,006,703 / ON 974,327 (−3.22 %), LIVE 22/24, median
depth 8 both. Diagnostics are liveness/overhead evidence ONLY; NO local
speedup, NPS or Elo claim.

Control: FIXED TIME 40+4 ms (`--base-ms 40 --inc-ms 4`), Hash 16, Threads 1,
240 plies, **never `--nodes`**; ONE packaged binary; BOTH arms champion
`EvalParams=research-data/params_abc.txt` and `TTEval=true`, A adds ONLY
`AdaptiveNullR=true`. Four isolated `ubuntu-latest` VMs: 400-game Stage-0
control/control validity null, 400-game candidate/candidate null, and two
independent 1,000-game batches. **FROZEN COMBINED = batchA + batchB ONLY.**
1,400 FRESH DISJOINT 8-ply openings from
`scripts/dev6_exp0046_openings.py` seed `2026120701`, ZERO exact-final-position
overlap with **39,041** earlier committed positions across **145** files,
ZERO duplicates, four mutually disjoint slices. ~13 Elo half-width at 2,800
games: powered for the +20 ADVANCE threshold and to rule out a material
regression, NOT to resolve a few Elo.

Frozen decision rules: **ADVANCE** only if combined point ≥ +20 AND 95 % LCB >
0 AND both batches ≥ −5 AND both null CIs include 0 AND 0
forfeits/illegal/UCI/engine failures in ALL four jobs; **CLOSE** if 95 % UCB <
+10 OR point ≤ 0; otherwise **CLOSED AS INCONCLUSIVE** by a SINGLE-RUN COMPUTE
BOUND with no confirmation, no post-hoc sample increase and no retune. The
validity gate (§5) enforces 0 TIME_FORFEIT / ILLEGAL / UCI / ENGINE_FAILURE in
ANY job, else INVALID MEASUREMENT with all Elo discarded, and pre-authorises at
most ONE bounded valid retry. ADVANCE alone would NOT satisfy Gate 1.

## 2. Run `41825055840` — valid, all evidence exported

Benchmark `41825055840` SUCCESS: prepare + all four isolated VMs SUCCESS,
`Export evidence` correctly skipped; CI `41825055708` SUCCESS; deliberate
export `41826460428` SUCCESS. Evidence in
`benchmarks/exp-runs/tier1-export/run-41825055840/`, four bundles, **9/9
`SHA256SUMS.txt` OK in EACH bundle**, independent raw-JSONL audit 44 stored
values / 0 issues AUDIT PASS with `clean=True`. **0 TIME_FORFEIT / 0 ILLEGAL /
0 ENGINE_FAILURE in ALL four jobs** (unadjudicated max-plies: stage0 1,
batchA 5, batchB 5, null 1 — recorded games, not failures).

Provenance from `fingerprint.json` / `run.log`: pinned source
`0792555ddd155b2426d926cccc5a16975f77682b` == actual, prereg
`dda54084d2acffdd…`, immutable dev5 baseline
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918` VERIFIED,
build flags `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`,
**built binary SHA == packaged binary SHA**
`18b9366edcaf5831ce7e2e28b38aa8a2a14dc2f28c2812da736c4b2cb211417e`,
default bench `243f9a1c1ba5b36f`, A/B options exactly as frozen, UCI
`AdaptiveNullR type check default false`.

| job | games | W/D/L | CR1/t Elo | 95 % CI |
|---|---|---|---|---|
| Stage-0 validity null (control/control) | 399 | 149/113/137 | +11.3524 | [−5.1046, +27.8606] |
| candidate-options null | 399 | 122/146/131 | −8.7314 | [−28.0469, +10.5303] |
| batchA | 995 | 333/337/325 | +3.1586 | [−8.7463, +15.0709] |
| batchB | 995 | 350/305/340 | +3.8606 | [−8.5988, +16.3299] |

Both null CIs include 0; both batches ≥ −5; no contradictions, no terminations
failures.

**FROZEN COMBINED batchA+batchB ONLY:** 1,990 games, W/D/L `683/642/665`,
score `0.5045226`, 990 clusters, **CR1/t Elo `+3.5096`, 95 % CI
`[−5.1015, +12.1250]`**, independent Elo-from-score `+3.1427`, independent
opening-clustered bootstrap 95 % `[−4.9136, +12.1125]`.

`.venv/bin/python scripts/dev6_exp0038_audit.py 41825055840 exp0046 20 10`
printed `INCONCLUSIVE (more samples, same frozen conditions)` — that is the
generic prereg §6 DEFAULT, **explicitly overridden** by exp-0046 §6's frozen
experiment-level SINGLE-RUN COMPUTE BOUND. Applying the frozen rules:
`point >= +20` False, `LCB > 0` False, `batches_ok` True, `nulls_ok` True,
`clean` True → **ADVANCE False**; `UCB (+12.1250) < +10` False OR
`point (+3.5096) <= 0` False → **CLOSE False**. Therefore:

```
VERDICT: CLOSED_AS_INCONCLUSIVE (frozen single-run compute bound; NO further samples)
```

`scripts/dev6_exp0046_decision.py` reproduces this independently from raw
`match.jsonl`, enforces the zero-forfeit validity gate from both stored
summaries and a raw-JSONL termination scan, and asserts the combined point/CI.
No threshold was weakened; the compute bound was ENFORCED, not relaxed.

## 3. Consequences

- exp-0046 is **CLOSED AS INCONCLUSIVE / ABANDONED**. The margin-adaptive
  null-move reduction direction is abandoned for this code base. `+3.5096`
  is **NOT** a strength claim: the 95 % CI includes zero and the screen cannot
  resolve a few Elo. No confirmation, no third run, no post-hoc sample
  increase, no pooling with exp-0045 or any earlier experiment, no retune of
  closed switches, no default change, no bundle. `AdaptiveNullR` stays OFF.
- Gates: **1 UNMET** (no +75 / LCB > +50 combined result on two independent
  preregistered fixed-time batches), **2 direction-supported**, **3 PASS**,
  **4 UNMET** (no final-candidate artifact; the exact packaged binary was
  verified for this experiment but no release candidate exists). No strength
  claim, no local speedup claim, no absolute/CCRL/FIDE Elo or gap-to-3000
  claim, no PR/merge/tag/release/deploy/dev7.
- Mission ACTIVE / NOT COMPLETE. A normal technical failure, invalid
  measurement, CI failure, inconclusive result or closed result cannot
  terminate it. The next hypothesis must have its OWN frozen prereg, fresh
  disjoint suites, Stage-0 validity null, candidate null, isolated VMs and
  independent raw-game audit; do not repeat exp-0046 or any recorded
  negative/neutral direction without genuinely new evidence. Immutable dev5
  baseline, `origin/main`, all historical evidence and `docs/DEV6_PREREG.md`
  §8 remain untouched.
