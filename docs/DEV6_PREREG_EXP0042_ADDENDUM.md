# exp-0042 ADDENDUM — bounded additional-sample confirmation (FROZEN before any additional game)

## Status that triggers this addendum
The exp-0042 Tier-1 screen (run `41802986830`, source `efd2f22…`) produced,
under the unchanged frozen §5 rules:

| arm | games | W/D/L | Elo | 95 % CI |
|---|---|---|---|---|
| Stage-0 validity null | 400 | 137/123/140 | −2.6058 | [−21.9076, +16.6798] |
| batchA | 1,000 | 357/300/343 | +4.8644 | [−10.1879, +19.9350] |
| batchB | 998 | 336/328/334 | +0.3488 | [−14.5041, +15.2030] |
| null (candidate vs candidate) | 399 | 144/131/124 | +17.4738 | [−1.9909, +37.0488] |
| **frozen combined A+B** | **1,998** | **693/628/677** | **+2.6110** | **[−7.9556, +13.1825]** |

Stage-0 validity PASS (0 forfeits/illegal/UCI failures, CI includes 0), both
required nulls include zero in their CIs, 998 clusters, independent Elo-from-
score +2.7823, seeded cluster bootstrap `[−8.0085, +12.8868]`, independent
raw-JSONL audit 44/44 values AUDIT PASS. ADVANCE condition (point >= +20 AND
LCB > 0) is FALSE; CLOSE condition (UCB < +10 OR point <= 0) is FALSE because
UCB = +13.1825. The original prereg §5 therefore mandates **"Inconclusive
otherwise -> more samples under the same frozen conditions"**. This addendum
fixes the previously-unspecified SIZE, the pooling policy and a compute bound.
It is written AFTER the screen result and BEFORE any additional game; every
threshold is copied verbatim from the frozen prereg and NO Gate is changed.
The unusually large null-arm point estimate (+17.47, CI includes zero) is
disclosed as a noise observation; it is why a second null is required below.

## Frozen additional-sample design (no post-hoc combining)
- A SEPARATE Tier-1 run, source `HEAD` of this commit, one dedicated
  `ubuntu-latest` VM per matrix job, exact packaged binary extracted/tested.
- **FIXED TIME `--base-ms 40 --inc-ms 4`**, Hash 16, Threads 1, max-plies 240,
  **never `--nodes`**. Identical clocks, identical options, SAME single switch
  `MaxGainDelta=true` vs `false`, same binary, same build flags.
- Two INDEPENDENT 1,000-game batches on 2 × 500 fresh disjoint openings
  (seed `2026113001`, 1,400 openings, ZERO overlap with all earlier suites
  verified programmatically), colour-reversed, one pair per opening.
- One 400-game null (candidate vs candidate) and one 400-game Stage-0 validity
  null (control vs control) with a fresh ctest run on the packaged binary.
- **The screen batches are NOT pooled with these confirmation batches.** The
  screen remains exploratory evidence only. This explicitly avoids any
  post-hoc combining to manufacture significance. The decision below uses
  ONLY the two NEW confirmation batches.

## Frozen decision (thresholds copied verbatim from §5)
- **ADVANCE to a preregistered FRESH bundle candidate** (measured against exact
  dev5, never a post-hoc sum) only if confirmation combined point >= +20 Elo
  AND combined 95 % LCB > 0 AND both confirmation batches >= −5 AND the new
  null CI includes 0 AND 0 forfeits/illegal/UCI failures.
- **CLOSE (max-gain delta rejected / abandon)** if confirmation combined 95 %
  UCB < +10 Elo OR combined point <= 0.
- **If neither condition is met, exp-0042 is CLOSED AS INCONCLUSIVE** with no
  strength claim, no default change, no bundle, no retune, and the direction
  ABANDONED as low expected value. This is an experiment-level COMPUTE BOUND,
  not a threshold change: it is justified by the project's already-preregistered
  scheduler (full-sized fixed-time tournaments are reserved for candidates
  whose screen point >= +55, and exp-0036 proved that spending 13,200 games on
  a +20 candidate is wasteful). It makes the experiment strictly MORE
  conservative: it can only prevent a claim, never create one. Gates 1-4 and
  every statistic in `docs/DEV6_PREREG.md` §3/§8 are untouched.

## Statistics / integrity
W/D/L, paired pentanomial, opening-clustered CR1/t two-sided 95 % CI, LLR
labelled a normal approximation, independent recomputation from raw JSONL by
`scripts/dev6_exp0038_audit.py <run> exp0042_confirm 20 10` (thresholds passed
explicitly, never inferred from results), plus its seeded opening-cluster
bootstrap. No batch selection, no post-hoc combining, no threshold changes.
`MaxGainDelta` stays default OFF until and unless every Gate passes. Raw
evidence is uploaded as Actions artifacts and mirrored by a deliberate
`mode=export` job. No absolute/CCRL/FIDE Elo or gap-to-3000 claim; no
PR/merge/tag/release/deploy/dev7.
