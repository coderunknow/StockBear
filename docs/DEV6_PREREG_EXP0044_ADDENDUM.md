# exp-0044 ADDENDUM — bounded additional-sample confirmation (FROZEN before any additional game)

## Status that triggers this addendum
The exp-0044 Tier-1 screen (run `41812595433`, source
`2ae4e68fc882991c3484eede22a4622f713da5e2`) produced, under the unchanged
frozen `docs/DEV6_PREREG_EXP0044.md` §6 rules:

| arm | games | W/D/L | Elo | 95 % CI |
|---|---|---|---|---|
| Stage-0 validity null | 400 | 133/145/122 | +9.5569 | [−6.6563, +25.8118] |
| candidate-options null | 400 | 138/124/138 | 0.0000 | [−17.9335, +17.9335] |
| batchA | 1,000 | 341/336/320 | +6.6419 | [−8.1259, +21.4338] |
| batchB | 996 | 335/328/336 | 0.0000 | [−15.0949, +15.0949] |
| **frozen combined A+B** | **1,996** | **676/664/656** | **+3.3140** | **[−7.2389, +13.8730]** |

Stage-0 validity PASS (0 forfeits/illegal/UCI/engine failures, CI includes 0),
both required nulls include zero, 996 clusters, independent Elo-from-score
+3.4814, seeded cluster bootstrap `[−7.1520, +13.7861]`, independent raw-JSONL
audit 44/44 values AUDIT PASS, 9/9 SHA256SUMS OK in each of 4 bundles, CI on
exact source `41812595476` SUCCESS. ADVANCE (point >= +20 AND LCB > 0) is
FALSE; CLOSE (UCB < +10 OR point <= 0) is FALSE because UCB = +13.8730 and
point = +3.3140. The frozen prereg §6 therefore mandates **exactly ONE bounded
confirmation run** with a fresh frozen addendum, a NEW disjoint suite and its
OWN Stage-0/null jobs. The screen and confirmation are separate experiments
and are **NEVER pooled**. This addendum is written AFTER the screen result and
BEFORE any additional game; every threshold is copied verbatim from the frozen
prereg and NO Gate is changed.

## Frozen additional-sample design (no post-hoc combining)
- A SEPARATE Tier-1 run, source `HEAD` of this commit, one dedicated
  `ubuntu-latest` VM per matrix job, exact packaged binary extracted/tested.
- **FIXED TIME `--base-ms 40 --inc-ms 4`**, Hash 16, Threads 1, max-plies 240,
  **never `--nodes`**. Identical clocks, identical options, SAME single switch
  `BadCaptureOrdering=true` vs `false`, same binary, same build flags
  (`-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`).
- Two INDEPENDENT 1,000-game batches on 2 × 500 fresh disjoint openings
  (seed `2026120401`, 1,400 openings, ZERO overlap with 34,841 earlier
  positions in 130 files verified programmatically, four mutually disjoint
  slices), colour-reversed, one pair per opening. Generator
  `scripts/dev6_exp0044_confirm_openings.py`.
- One 400-game Stage-0 validity null (control vs control) with a fresh ctest
  run on the packaged binary, and one 400-game candidate-options null.
- **The screen batches are NOT pooled with these confirmation batches.** The
  screen remains exploratory evidence only. This explicitly avoids any
  post-hoc combining to manufacture significance. The decision below uses
  ONLY the two NEW confirmation batches. ANY time forfeit, illegal move or
  engine failure in ANY of the four confirmation jobs => INVALID MEASUREMENT,
  exactly as in the frozen prereg §5.

## Frozen decision (thresholds copied verbatim from §6)
- **ADVANCE to a preregistered FRESH bundle candidate** (measured against exact
  dev5, never a post-hoc sum) only if confirmation combined point >= +20 Elo
  AND combined 95 % LCB > 0 AND both confirmation batches >= −5 AND both new
  null CIs include 0 AND 0 forfeits/illegal/UCI/engine failures in ALL jobs.
- **CLOSE (mechanism rejected / abandon)** if confirmation combined 95 % UCB
  < +10 Elo OR combined point <= 0.
- **If neither condition is met, exp-0044 is CLOSED AS INCONCLUSIVE** with no
  strength claim, no default change, no bundle, no retune, and the direction
  ABANDONED as low expected value. This is an experiment-level COMPUTE BOUND,
  not a threshold change: the project's preregistered scheduler reserves
  full-sized fixed-time tournaments for candidates whose screen point >= +55,
  and exp-0036 proved that spending 13,200 games on a +20 candidate is
  wasteful. It makes the experiment strictly MORE conservative: it can only
  prevent a claim, never create one. Gates 1-4 and every statistic in
  `docs/DEV6_PREREG.md` §8 are untouched.
- ADVANCE alone does NOT satisfy Gate 1, which still needs >= +75 with LCB > +50
  on two independent preregistered FIXED-TIME batches and the exact packaged
  final-candidate artifact for Gate 4.

## Statistics / integrity
W/D/L, paired pentanomial, opening-clustered CR1/t two-sided 95 % CI, LLR
labelled a normal approximation, independent recomputation from raw JSONL by
`scripts/dev6_exp0038_audit.py <run> exp0044_confirm 20 10` (thresholds passed
explicitly, never inferred from results), plus its seeded opening-cluster
bootstrap. No batch selection, no post-hoc combining, no threshold changes.
`BadCaptureOrdering` stays default OFF until and unless every Gate passes.
Raw evidence is uploaded as Actions artifacts and mirrored by a deliberate
`mode=export` job. No absolute/CCRL/FIDE Elo or gap-to-3000 claim; no
PR/merge/tag/release/deploy/dev7; no reuse of closed exp-0041/0042/0043 data.
