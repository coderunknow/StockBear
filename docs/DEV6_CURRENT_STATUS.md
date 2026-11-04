# StockBear v0.1.0-dev6 — CURRENT AUTHORITATIVE STATUS (2026-11-04)

Older reports `docs/DEV6_STATUS_REPORT.md` and
`docs/DEV6_POST_AUTHORIZATION_REPORT.md` are superseded for this cycle; they
remain historical records. This document is the current gate verdict.
**LATEST (post-exp-0046): see the "LATEST (2026-11-04, post-exp-0046
investigation)" section at the end and
`docs/DEV6_EXP0047_INVESTIGATION_REPORT.md`; no new strength games were played
and `docs/DEV6_PREREG_EXP0047.md` is a DORMANT frozen preregistration.**

## Verdict: MISSION ACTIVE — NOT COMPLETE
`docs/DEV6_PREREG.md` §8 gates are **unchanged and unweakened**.

| gate | verdict | basis |
|---|---|---|
| 1 | **UNMET** | No fixed-time 40+4 ms candidate with point >= +75 AND combined two-sided opening-clustered 95 % LCB > +50 on two independent preregistered positive batches. Best preregistered fixed-time evidence remains exp-0036 `+21.5238 [10.2819, 32.8108]` (Tier-2 dedicated core), closed at its frozen futility boundary; exp-0038 `+7.6755 [−1.0670, +16.4278]` (Tier-1 isolated VMs), closed inert/overhead. |
| 2 | **direction-supported** | exp-0036 on both independent datasets under the existing spec. |
| 3 | **PASS** | Both required null experiments include zero in their CIs; exp-0038, exp-0041, exp-0042 and exp-0043 nulls additionally pass. |
| 4 | **UNMET for a final candidate** | Tier-1 infrastructure is verified end-to-end (packaged identity, SHA-256, git + Contents API retrieval, 0/9 and 0/4 checksum failures, CI on exact source), but no exact final candidate release artifact has been tested. |

No strength claim. No PR, approval, merge, tag, release or deploy while any
gate is unmet. 3,000 Elo is a long-term strategic target only; no absolute,
universal, CCRL/FIDE or numeric gap-to-3000 claim. No dev7.

## Experiment status vs mission status
- **Experiment status: exp-0046 CLOSED AS INCONCLUSIVE / ABANDONED** at its
  frozen single-run compute bound. exp-0045 is CLOSED / ABANDONED (original
  run INVALID MEASUREMENT, ONE bounded valid retry, FINAL CLOSE). exp-0044 is
  CLOSED AS INCONCLUSIVE / ABANDONED (screen + bounded confirmation);
  exp-0043, exp-0042,
  exp-0041, exp-0038, exp-0037 and exp-0036 are CLOSED; exp-0039 and exp-0040
  were eliminated at profiling.
- **Mission status: ACTIVE, NOT COMPLETE.** Gates 1 and 4 remain UNMET. No
  experiment terminal state is a mission terminal state. No genuine blocker:
  the supported dispatch mechanism works; the earlier export-only dispatch and
  two transient GitHub `Internal Server Error` push rejections were ordinary
  transient research states, both resolved by a plain retry.
- **Exact current source SHA:** `0792555ddd155b2426d926cccc5a16975f77682b` (the exp-0046 launch dispatch
  commit, pinned by `source_sha=HEAD`). Earlier exact sources: exp-0045 retry
  `9fb2a58e20b8aab131a56ddb3d749e60fce5278b`, exp-0045 original
  `e41a0b18b4e522f57196e2834c8937f8c55019e8`.
- **Exact source SHAs:** exp-0044 screen `2ae4e68fc882991c3484eede22a4622f713da5e2`,
  bounded confirmation `0691b9affd36006425ac23605f4a0cc8922a55bb`, exp-0043
  `5ea5ad21348f39dabad1da3e8cb098f798087295`. Current branch HEAD is recorded
  in `AGENTS_LOG.md`; all were pinned by `source_sha=HEAD` in their dispatch. Local HEAD and remote head are recorded
  in `AGENTS_LOG.md`; working tree is clean.
- **Reproducible benchmark evidence:** exp-0045 original run `41817228668` /
  export `41818409701` / CI `41817228408` SUCCESS but **INVALID MEASUREMENT**
  (1 TIME_FORFEIT in batchB game 272; frozen zero-forfeit rule ENFORCED, ALL
  its Elo DISCARDED, audit `clean=False`, 44 stored values / 0 issues). One
  bounded valid retry `41818958001` / export `41821624068` / CI
  `41818958003` SUCCESS: 4 isolated VMs, 9/9 SHA256SUMS OK per bundle, 0
  forfeits/illegal/failures, 44/0 AUDIT PASS, frozen combined
  `−8.9240 [−18.2792,+0.4182]` on 1,993 games => **CLOSE / ABANDONED**
  (reproduced by `scripts/dev6_exp0045_retry_decision.py`). Invalid run NEVER
  pooled. Full report `docs/DEV6_EXP0045_REPORT.md`. exp-0046 run
  `41825055840` / export `41826460428` / CI `41825055708` SUCCESS: 4 isolated
  VMs, 9/9 SHA256SUMS OK per bundle, 0 forfeits/illegal/failures, 44/0 AUDIT
  PASS, frozen combined `+3.5096 [−5.1015,+12.1250]` on 1,990 games =>
  **CLOSED AS INCONCLUSIVE / ABANDONED** at the frozen single-run compute
  bound (NO strength claim, NO further samples). Reproduced by
  `scripts/dev6_exp0046_decision.py`. Full report
  `docs/DEV6_EXP0046_REPORT.md`. exp-0044 screen `41812595433` /
  export `41813751266` / CI `41812595476` SUCCESS, `+3.3140 [−7.2389,+13.8730]`
  INCONCLUSIVE; bounded confirmation `41814069967` / export (retry)
  `41815428066` / CI `41814069925` SUCCESS, `+13.5977 [+2.1746,+25.0503]`,
  FROZEN ADDENDUM compute bound => CLOSED AS INCONCLUSIVE / ABANDONED,
  NEVER pooled. Both 4 isolated VMs, 9/9 SHA256SUMS OK per bundle, 44/0
  audits PASS, 0 forfeits/illegal/failures. Full report
  `docs/DEV6_EXP0044_REPORT.md`. exp-0043 `41809643084` / export
  `41810711486` / CI `41809642415` SUCCESS, combined
  `−10.3142 [−20.8915,+0.2440]` CLOSE. exp-0042 screen `41802986830` /
  export `41804342869` / CI `41802986854` and confirmation `41804818965` /
  export `41806227744` / CI `41804818984`; both four isolated-VM jobs SUCCESS,
  4/4 SHA256SUMS with 0 failures, 44/0 audits PASS. Screen
  `+2.6110 [−7.9556,+13.1825]` INCONCLUSIVE; confirmation
  `−10.8281 [−21.8567,+0.1787]` CLOSE, **NEVER pooled**. exp-0041
  `41782954038` / export `41784088471` `−5.0635 [−15.1810,+5.0454]`;
  exp-0038 `41780333569` / export `41781546677`
  `+7.6755 [−1.0670,+16.4278]`. Full provenance in
  `docs/DEV6_EXP0046_REPORT.md`, `docs/DEV6_EXP0045_REPORT.md`,
  `docs/DEV6_EXP0043_REPORT.md`,
  `docs/DEV6_EXP0042_REPORT.md`,
  `docs/DEV6_EXP0041_REPORT.md`, `docs/DEV6_EXP0038_REPORT.md` and
  `benchmarks/exp-runs/tier1-export/`.

## What is operational now
- `.github/workflows/dev6-tier1.yml`: `workflow_dispatch` + deliberate
  `benchmarks/exp-runs/tier1-dispatch.json` push trigger (paths-filtered, so a
  docs-only push does NOT launch another benchmark); `prepare`, one isolated
  `ubuntu-latest` VM per matrix benchmark job, artifact upload, and a
  deliberate `mode=export` job using `actions/download-artifact(run-id)` with
  checksum verification and ONE `[skip ci]` evidence commit. Benchmarks never
  push results. `workflow_dispatch` is unusable with the current token (HTTP
  403); the push trigger is the supported path and was used for attempt 15.
- Verified evidence runs: smoke `41778365897` (40-game null self-match,
  **DISCARDED**), exp-0038 `41780333569`, exp-0041 `41782954038`,
  exp-0042 `41802986830` and `41804818965`, exp-0043 `41809643084` — all
  exported and checksum-reverified locally. CI on every relevant source HEAD
  is SUCCESS.
- Independent audits: `scripts/dev6_audit.py` (215 stored values across
  exp-0031..0037) and `scripts/dev6_exp0038_audit.py` (44 stored values plus a
  seeded opening-cluster bootstrap) — both AUDIT PASS.

## Closed experiments this cycle
- **exp-0036** BadCapturePruning: Tier-2 fixed-time `+21.5238 [10.2819,
  32.8108]`, closed at preregistered futility UCB < +50. Not Tier-1.
- **exp-0037** ProbCut: fixed-node Stage-1 `+3.7766 [−9.3368, +16.9008]`,
  closed at frozen Stage-1 rule. Default OFF.
- **exp-0038** dedicated qsearch TT: Tier-1 `+7.6755 [−1.0670, +16.4278]`,
  closed at frozen UCB < +20. Default OFF.
- **exp-0039** dead static evaluation on TT hits: eliminated at profiling
  (<= 2.9 % against a ~7 % noise floor), source reverted, no games.
- **exp-0040** banked-time allocation: eliminated at profiling; the live soft
  budget increase (4 -> 6 ms) left the tree bit-identical. No games.
- **exp-0041** losing-capture pruning at ALL remaining depths: frozen combined
  `−5.0635 [−15.1810, +5.0454]` on 1,995 games, 44/44 audit PASS, CLOSED /
  ABANDONED. The −42.1 % node saving was profiling, NOT strength evidence.
- **exp-0042** max-gain delta pruning: screen `+2.6110 [−7.9556,+13.1825]`
  INCONCLUSIVE, bounded confirmation `−10.8281 [−21.8567,+0.1787]` CLOSE /
  ABANDONED; two Tier-1 runs, 44/0 audits PASS, **NEVER pooled**.
  `MaxGainDelta` OFF, `deltaMargin=200` frozen.
- **exp-0043** TT-evidence singular extension: run `41809643084`, source
  `5ea5ad21348f39dabad1da3e8cb098f798087295`, prereg
  `e9fe40f053c9f4798…`, packaged=tested binary `c2ef506c5c6e…`; Stage-0 and
  candidate-options nulls both include 0, 0 forfeits/illegal/failures;
  batchA `−9.7895 [−25.2667,+5.6489]`, batchB
  `−10.8390 [−25.2969,+3.5814]`, FROZEN combined
  `−10.3142 [−20.8915,+0.2440]` on 1,994 games / 994 clusters, independent
  bootstrap `[−20.6467,+0.1748]`, 44/0 AUDIT PASS. CLOSE/ABANDONED at frozen
  `UCB < +10 OR point <= 0`; switch OFF, no retune, no bundle. The mandatory
  mechanism-live diagnostic proved LIVE on 23/24 suite positions at 40+4 ms
  (a real negative, not inert); +13.9 % fixed-depth node overhead is recorded
  but is NOT strength evidence. Full report `docs/DEV6_EXP0043_REPORT.md`.
- **exp-0044** SEE<0 capture demotion in MAIN search only: screen
  `+3.3140 [−7.2389,+13.8730]` INCONCLUSIVE, bounded confirmation
  `+13.5977 [+2.1746,+25.0503]`; frozen addendum COMPUTE BOUND => CLOSED AS
  INCONCLUSIVE / ABANDONED, **NEVER pooled**, no third run. Default OFF.
  Full report `docs/DEV6_EXP0044_REPORT.md`.
- **exp-0045** bit-exact dead `evaluate()` elimination (`SkipDeadTTEval`,
  default OFF): original run `41817228668` INVALID MEASUREMENT (1 forfeit),
  ALL Elo DISCARDED; ONE bounded valid retry `41818958001` frozen combined
  `−8.9240 [−18.2792,+0.4182]` on 1,993 games => CLOSE / ABANDONED, 0
  forfeits/illegal/failures, 44/0 AUDIT PASS, NEVER pooled with the invalid
  run. No strength claim. Full report `docs/DEV6_EXP0045_REPORT.md`.
- **exp-0046** margin-adaptive null-move reduction (default OFF): valid run
  `41825055840`, frozen combined `+3.5096 [−5.1015,+12.1250]` on 1,990
  games => CLOSED AS INCONCLUSIVE / ABANDONED at the frozen single-run
  compute bound; 0 forfeits/illegal/failures, 44/0 AUDIT PASS. NOT a
  strength claim. Full report `docs/DEV6_EXP0046_REPORT.md`.

## exp-0046 CLOSED AS INCONCLUSIVE / ABANDONED (frozen single-run compute bound)

Run `41825055840` / export `41826460428` / CI `41825055708` SUCCESS on exact
source `0792555ddd155b2426d926cccc5a16975f77682b` (prereg SHA
`dda54084d2acffdd…`, plan `557d51fc07ad18eb…`). Four isolated VMs, 9/9
SHA256SUMS OK in each of 4 bundles, **0 TIME_FORFEIT / ILLEGAL /
ENGINE_FAILURE in ALL four jobs**, 44/0 AUDIT PASS with `clean=True`.
Provenance: dev5 baseline VERIFIED, built binary SHA == packaged binary SHA
`18b9366edcaf…`, default bench `243f9a1c1ba5b36f`, UCI
`AdaptiveNullR default false`, A/B options exactly as frozen. 1,400 fresh
disjoint openings seed `2026120701` (ZERO overlap / 39,041 earlier positions
in 145 files), FIXED TIME 40+4 ms, never `--nodes`, no pooling.

Stage-0 validity null 399 `149/113/137` `+11.3524 [−5.1046,+27.8606]`;
candidate-options null 399 `122/146/131` `−8.7314 [−28.0469,+10.5303]`;
batchA 995 `333/337/325` `+3.1586 [−8.7463,+15.0709]`; batchB 995
`350/305/340` `+3.8606 [−8.5988,+16.3299]`; both null CIs include 0, both
batches >= −5. FROZEN COMBINED batchA+batchB ONLY 1,990 games `683/642/665`,
score `0.5045226`, 990 clusters, **`+3.5096 [−5.1015,+12.1250]`**,
Elo-from-score `+3.1427`, bootstrap `[−4.9136,+12.1125]`. ADVANCE False
(point<+20, LCB<0); CLOSE False (UCB>=+10, point>0). The generic audit's
"INCONCLUSIVE (more samples)" is its prereg §6 DEFAULT, explicitly OVERRIDDEN
by exp-0046 §6's frozen SINGLE-RUN COMPUTE BOUND:
`scripts/dev6_exp0046_decision.py` independently reproduces
**VERDICT: CLOSED_AS_INCONCLUSIVE (frozen single-run compute bound; NO further
samples)**. No strength claim (the CI includes zero), no default change,
no retune, no bundle, no confirmation, no post-hoc sample increase, no
pooling. `AdaptiveNullR` stays OFF. Gates 1 and 4 UNMET. Full report
`docs/DEV6_EXP0046_REPORT.md`; evidence
`benchmarks/exp-runs/tier1-export/run-41825055840/`.

## exp-0045 CLOSED / ABANDONED (INVALID run + ONE bounded valid retry)

The original exp-0045 run (`41817228668`, source
`e41a0b18b4e522f57196e2834c8937f8c55019e8`, prereg `0abf66836ed0ad6d…`, export
`41818409701`, CI `41817228408`) completed all four isolated VMs SUCCESS,
9/9 SHA256SUMS OK in each of 4 bundles and 44/0 AUDIT PASS, but batchB had ONE
`TIME_FORFEIT` (game 272, 14.1 ms move at ply 118, `remaining_white_ms=-5.01`
in a long game). The FROZEN prereg §5 requires 0 forfeits in ANY job, so the
run is **INVALID MEASUREMENT**: all Elo/CIs/W-D-L/LLR and the generic audit's
"CLOSE" label are DISCARDED, with NO strength inference. `clean=False` is the
correct audit signal. Diagnosis: a rare long-game clock exhaustion on one
isolated VM (1/998; exp-0043/0044 had 0 forfeits at the same control), not a
systematic mechanism effect; it benefited the candidate arm and could not
manufacture a positive result. NO repair to the frozen 40+4 ms control, clocks,
binary, switch, time manager or driver was authorised; the zero-forfeit rule
was ENFORCED, not weakened.

`docs/DEV6_PREREG_EXP0045_RETRY.md` (SHA
`2172063e22554df99064c54e0820b70db854e2339b0d5e87ccc321b6ca0bce60`) was frozen
BEFORE any retry game: a valid NEW run with IDENTICAL mechanism, switch, build
flags, options, FIXED TIME 40+4 ms control, four isolated-VM jobs, statistics
and decision thresholds; NEW `exp0045_retry`, dispatch attempt 22, NEW seeds,
1,400 FRESH DISJOINT openings (seed `2026120601`, ZERO overlap with 37,641
earlier positions / 140 files). Invalid run `41817228668` NEVER pooled or
reused. Bounded retry budget: exactly one retry; a second forfeit would have
closed exp-0045 AS TECHNICALLY UNRESOLVABLE.

Retry `41818958001` / export `41821624068` / CI `41818958003` all SUCCESS:
provenance pinned `source_sha=9fb2a58…` verified, dev5 baseline VERIFIED,
built binary SHA == packaged binary SHA `b839fae82b54…`, UCI
`SkipDeadTTEval default false`. 9/9 SHA256SUMS OK in each of 4 bundles,
**0 TIME_FORFEIT / 0 ILLEGAL / 0 ENGINE_FAILURE in ALL four jobs**, 44/0
AUDIT PASS with `clean=True`. Stage-0 validity null 399 `118/155/126`
`−6.1113 [−23.3656,+11.1129]`; candidate null 400 `152/111/137`
`+13.0349 [−6.3155,+32.4666]`; batchA 994 `327/320/347`
`−6.6823 [−19.7471,+6.3636]`; batchB 999 `324/320/355`
`−11.1440 [−24.5596,+2.2383]`; both null CIs include 0. FROZEN COMBINED
batchA+batchB ONLY 1,993 games `651/640/702`, score `0.4872052`, 993 clusters,
**`−8.9240 [−18.2792,+0.4182]`**, independent Elo-from-score `−8.8927`,
bootstrap `[−18.2107,+0.1749]`. ADVANCE False (point<+20, LCB<0, both batches
<−5); CLOSE True (UCB<+10 AND point<=0). `scripts/dev6_exp0038_audit.py
41818958001 exp0045_retry 20 10` and `scripts/dev6_exp0045_retry_decision.py`
independently reproduce **VERDICT: CLOSE (mechanism rejected / abandoned; NO
strength claim)**. No confirmation, no third run, no post-hoc sample increase,
no pooling, no retune, no default change, no bundle. The switch stays OFF;
this is NOT a proven strength regression (a ~13 Elo half-width cannot resolve
a few Elo). Gates 1 and 4 remain UNMET. Full report `docs/DEV6_EXP0045_REPORT.md`,
evidence `benchmarks/exp-runs/tier1-export/run-41818958001/`.

## exp-0044 CLOSED AS INCONCLUSIVE (screen + bounded confirmation)
The exp-0044 screen ran on source `2ae4e68fc882991c3484eede22a4622f713da5e2`,
prereg `73ae460981a09bbf5…`, run `41812595433`, export `41813751266`, CI
`41812595476` SUCCESS; 4 isolated VMs, 9/9 SHA256SUMS OK in each of 4
bundles, 0 forfeits/illegal/engine failures. Stage-0 validity null 400 games
133/145/122 `+9.5569 [−6.6563,+25.8118]`, candidate-options null 400 games
138/124/138 `0.0000 [−17.9335,+17.9335]`, batchA 1,000 games 341/336/320
`+6.6419 [−8.1259,+21.4338]`, batchB 996 games 335/328/336
`0.0000 [−15.0949,+15.0949]`; FROZEN combined 1,996 games 676/664/656,
score 0.5050100, `+3.3140 [−7.2389,+13.8730]`, 996 clusters, independent
Elo-from-score +3.4814, seeded bootstrap `[−7.1520,+13.7861]`, 44/0 AUDIT
PASS. ADVANCE false (point < +20, LCB < 0); CLOSE false (UCB +13.8730 >= +10,
point > 0) => **INCONCLUSIVE**, which the frozen prereg maps to exactly ONE
bounded fresh confirmation.

`docs/DEV6_PREREG_EXP0044_ADDENDUM.md` (SHA
`17d90a790697bb05…`) was frozen BEFORE any confirmation game. Confirmation
source `0691b9affd36006425ac23605f4a0cc8922a55bb`, run `41814069967`, export
attempt 18 `41815187170` FAILED only at a transient evidence push (download +
checksums succeeded, nothing reached the remote); the workflow export push was
repaired with a bounded retry and re-dispatched as NEW valid run
`41815428066` SUCCESS. Confirmation Stage-0 `−9.5569 [−32.6787,+13.4804]`,
candidate null `+6.1422 [−14.8210,+27.1502]`, batchA
`+17.0722 [+0.6984,+33.5222]`, batchB `+10.1190 [−5.8209,+26.1015]`;
FROZEN combined 1,997 games 699/676/622, `+13.5977 [+2.1746,+25.0503]`, 997
clusters, 44/0 AUDIT PASS, 0 forfeits/illegal/failures. ADVANCE false
(point < +20), CLOSE false (UCB >= +10, point > 0) => the frozen addendum's
COMPUTE BOUND applies: **CLOSED AS INCONCLUSIVE**, `BadCaptureOrdering`
abandoned, no retune, no bundle, no third run. The generic audit CLI's
"more samples" default is the prereg §6 branch that the addendum explicitly
overrides; `scripts/dev6_exp0044_confirm_decision.py` reproduces the override
from raw games. Screen and confirmation are NEVER pooled; no strength claim.

## exp-0044 screen design (archived)

- **Why this experiment and why selected:** after three consecutive losses for
  mechanisms that change which nodes are searched or add a ply at non-PV
  nodes, the matrix re-ranks **move-ordering ACCURACY with ZERO added per-node
  work** to NEXT. Code inspection found SEE-losing captures scored ABOVE
  killers and every quiet move in the main search; exp-0036 (+21.5 Elo from
  PRUNING them at shallow depth) shows they are low-value at 40+4 ms.
- **Mechanism:** `badCaptureOrdering` (default OFF) demotes SEE<0
  non-promotion captures to the tail in the MAIN search ONLY. NO move removed
  (unlike exp-0036/0041), NO SEE/eval call added, NO stand-pat rewrite, NO
  pruning/extension decision change, quiescence excluded. Frozen
  `BadCaptureOrderScore=-2000000`, frozen threshold SEE<0, no tunable margin.
- **Frozen before games:** `docs/DEV6_PREREG_EXP0044.md` (SHA
  `73ae460981a09bbf5d605205f8b77bf799b6d92a0fed4dc4abaa3a4ebc3820a5`),
  `tier1-plan-exp0044.json` (4 jobs), the dispatch (`mode=benchmark`,
  attempt 15), source (default OFF, bit-exact signatures
  `243f9a1c1ba5b36f` / `a14ab62224f837e5` / `e45fa2ec2287eb41`, Release 11/11,
  ASan+UBSan 11/11, UCI default false), and 1,400 fresh disjoint openings
  (seed `2026120301`, ZERO overlap with 33,441 earlier positions / 125 files,
  generator `scripts/dev6_exp0044_openings.py`).
- **Mandatory diagnostics (pre-result, NOT strength):** fixed depth 10 =>
  +11.6 % nodes (2,655,145 -> 2,961,866) with ZERO added per-node work,
  424,155 demotions, live 16/16; at the EXACT 40+4 ms control LIVE on 24/24
  suite positions (22,024 / 24,413 demotions), median completed depth 6
  unchanged. The node increase is DISCLOSED as a risk, never spun positive.
- **Design:** FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, never `--nodes`;
  ONE binary, single switch `BadCaptureOrdering=true` vs `false`; Stage-0
  validity null (0 forfeits required), candidate-options null, batchA 1,000
  and batchB 1,000 games on independent fresh suites, combined frozen before
  the run, independent raw-JSONL audit. ANY time forfeit / illegal / engine
  failure in ANY job => INVALID MEASUREMENT. Frozen ADVANCE >= +20 point AND
  LCB > 0 AND both batches >= −5 AND both null CIs include 0 AND clean;
  CLOSE if UCB < +10 OR point <= 0; INCONCLUSIVE -> exactly ONE bounded fresh
  confirmation, NEVER pooled. ADVANCE alone does NOT satisfy Gate 1.

## Remaining work / gates
Gates 1 (+75 / LCB > +50 on two independent preregistered FIXED-TIME batches)
and 4 (exact packaged final-candidate binary/source/CI linkage with no
correctness, illegal-move, protocol or time-forfeit regression and no
unexplained benchmarked-vs-packaged difference) are UNMET. A FRESH-measured
bundle of independently validated mechanisms, never a post-hoc sum, is the
only credible route and is authorised only by a frozen ADVANCE rule. No final
candidate artifact exists. Remaining ranked directions are in
`docs/DEV6_RESEARCH_MATRIX.md`; note that TT replacement/depth policy is
ALREADY SHIPPED (generation- and depth-preferred) and must be profiled before
any games. After exp-0046: ADVANCE -> continue validation/subsequent gates; CLOSE or
CLOSED-AS-INCONCLUSIVE -> document, update matrix and launch the next
hypothesis with its OWN frozen prereg, fresh disjoint suites, Stage-0 validity,
null, isolated VMs and independent raw-game audit; TECHNICAL FAILURE ->
diagnose, repair within scope, validate and retry with a valid new run. No
experiment outcome terminates the mission.

## Workspace reconciliation (earlier this cycle)
A fresh sandbox presented a clone at the original base commit with a stale
turn-end patchset overlay and no `.venv`. The overlay was preserved in a git
stash (`stash@{0}`, stale exp0037-era patchset; do not pop or drop without
need); `git fetch` + `git reset --hard FETCH_HEAD` aligned the local branch to
remote. All documents, plans, raw evidence and scripts were verified present;
`.venv` rebuilt with cmake 4.4.4 / ninja 1.13.2 / numpy 2.4.6 / chess 1.11.2 /
PyYAML 6.0.3. No force push, no shared-history rewrite, no scientific
conclusion changed.

---

## LATEST (2026-11-04, post-exp-0046 investigation) — NO NEW STRENGTH GAMES

Authoritative continuation report: `docs/DEV6_EXP0047_INVESTIGATION_REPORT.md`;
complete frozen preregistration: `docs/DEV6_PREREG_EXP0047.md`
(**DORMANT / NOT ACTIVATED**). Exact HEAD remains
`d07294d7dbd3a88e5b673f048aeb6a7b1acc1dbf`; CI `41826927521` SUCCESS;
`benchmarks/exp-runs/tier1-dispatch.json` unchanged (`mode=export`, exp0046,
attempt 25); no engine source change, no plan, no suite, no benchmark run, no
new PGN/JSONL, no invalid measurement, no pooling, no reopened decision.

Phase 1 re-verified the authoritative `docs/DEV6_PREREG.md` §8 gates verbatim
(Gate 1: combined point >= +75 Elo AND two-sided opening-clustered 95 % LCB
strictly > +50, both batches positive, no material contradictory regression,
reasonably consistent; Gate 4: no unresolved correctness/illegal-move/protocol/
time-forfeit regression, no unexplained benchmarked-vs-packaged difference, and
**the exact candidate release artifact must be the tested binary**). Older
dev4-baseline +50 gates and the Tier-1 `+20` screen rule are NOT Gate 1.
Documentation drift in the secondary Gate 2 wording is noted but not used to
infer any gate pass.

Phase 2 produced fresh evidence: a gprof profile of the actual source (24 real
FENs, `go depth 12`, 12,161,395 nodes, 15.17 s): `features()` 17.77 %,
`next_move` 10.40 %, `attacks_bb` 9.45 % (460,060,962 calls), TT probe 8.51 %,
`make_move_impl`/`generate_moves` 7.37 % each, `score_moves` 5.86 %, SEE 5.48 %,
`slider_attacks_bb` 5.29 %. Every non-pawn piece's attack bitboard is provably
computed twice per `evaluate()` — a bit-exact redundancy, but bounded at ~7 %
node time => ~+3–8 Elo. A fresh matched-toolchain `bench --depth 16` comparison
(24,211,820 identical nodes, 3 alternating reps) gave median candidate/dev5
NPS ratio **1.0289**, inside local noise (candidate spread 0.4289–0.4654 M),
agreeing with exp-0030 (A2/A1 0.9765, B/A1 0.9906). No bit-exact NPS
step-change exists; performance, search-quality, evaluation-accuracy and
demonstrated-strength effects are kept strictly separate.

Ranked hypotheses (at most three): (1) bit-exact attack-set dedup / stable-sort
ordering — NOT JUSTIFIED (bounded ~+3–8 Elo, far below Gate 1); (2) decisive
Tier-1 replication of `BadCapturePruning` — NOT JUSTIFIED / forbidden by the
frozen exp-0036 closure (UCB +32.81 < +50; "do NOT re-run", "do NOT stack");
(3) a materially stronger evaluator with a measured accuracy→strength link and
inference cost — HIGHEST gate relevance but NOT YET TESTABLE. Missing evidence:
a fresh bullet-matched corpus + frozen accuracy metric, matched-toolchain
inference cost, and a pre-result argument compatible with >= +75 Elo.
`docs/DEV6_POWER_ANALYSIS.md` explicitly says the binding constraint is the
candidate, not sample size (~576 games reject +75; 13,200 games give ±5.2 Elo).

**DECISION: no strength experiment is scientifically defensible at this HEAD;
zero games were played.** The one selected experiment (decisive Gate-1
measurement of a genuinely stronger evaluator) is fully preregistered in
`docs/DEV6_PREREG_EXP0047.md` with §8 thresholds (NOT the +20 screen),
2 x 6,600 games, fresh disjoint suites, 0-forfeit validity, invalid-run
discard, NO authorised retry, single-run compute bound, independent raw-JSONL
decision script and an empty Activation Record. It stays DORMANT until its four
measurable activation conditions are committed. This is not a mission
termination and not a manufactured progress claim.

Integrity re-verification this turn (NOT new strength evidence): Release build
from exact HEAD with portable flags — three frozen bench signatures
`243f9a1c1ba5b36f` / `a14ab62224f837e5` / `e45fa2ec2287eb41`; `ctest` 11/11
PASS; fresh ASan+UBSan `ctest` 11/11 PASS (`benchmarks/dev6-baseline/exp0047_asan_ctest.txt`);
all 17 experimental UCI switches `default false` including `AdaptiveNullR`;
exp-0045 retry decision `−8.9240 [−18.2792,+0.4182]` CLOSE and exp-0046 decision
`+3.5096 [−5.1015,+12.1250]` CLOSED_AS_INCONCLUSIVE reproduced; generic audits
44/0 PASS ×2; SHA256SUMS 36 OK / 0 BAD ×2 exports. Raw gprof evidence:
`benchmarks/dev6-baseline/exp0047_gprof_flat.txt` and
`exp0047_gprof_callgraph.txt`.

Gates UNCHANGED: **1 UNMET, 2 direction-supported, 3 PASS, 4 UNMET**; mission
ACTIVE / NOT COMPLETE; no final candidate artifact, no strength claim, no
default change, no PR/merge/tag/release/deploy/dev7, no absolute/CCRL/FIDE Elo
or gap-to-3000 claim. Next concrete action: regenerate a fresh bullet-matched
corpus with a frozen accuracy metric, measure champion/candidate evaluator
accuracy and matched-toolchain inference cost, and only then activate exp-0047.
