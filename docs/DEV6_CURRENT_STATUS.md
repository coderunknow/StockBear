# StockBear v0.1.0-dev6 — CURRENT AUTHORITATIVE STATUS (2026-11-04)

Older reports `docs/DEV6_STATUS_REPORT.md` and
`docs/DEV6_POST_AUTHORIZATION_REPORT.md` are superseded for this cycle; they
remain historical records. This document is the current gate verdict.

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
- **Experiment status: exp-0045 LAUNCHED / EXECUTING.** exp-0044 is
  CLOSED AS INCONCLUSIVE / ABANDONED (screen + bounded confirmation);
  exp-0043, exp-0042,
  exp-0041, exp-0038, exp-0037 and exp-0036 are CLOSED; exp-0039 and exp-0040
  were eliminated at profiling.
- **Mission status: ACTIVE, NOT COMPLETE.** Gates 1 and 4 remain UNMET. No
  experiment terminal state is a mission terminal state. No genuine blocker:
  the supported dispatch mechanism works; the earlier export-only dispatch and
  two transient GitHub `Internal Server Error` push rejections were ordinary
  transient research states, both resolved by a plain retry.
- **Exact current source SHA:** `e41a0b18b4e522f57196e2834c8937f8c55019e8` (the exp-0045 dispatch
  commit, pinned by `source_sha=HEAD`).
- **Exact source SHAs:** exp-0044 screen `2ae4e68fc882991c3484eede22a4622f713da5e2`,
  bounded confirmation `0691b9affd36006425ac23605f4a0cc8922a55bb`, exp-0043
  `5ea5ad21348f39dabad1da3e8cb098f798087295`. Current branch HEAD is recorded
  in `AGENTS_LOG.md`; all were pinned by `source_sha=HEAD` in their dispatch. Local HEAD and remote head are recorded
  in `AGENTS_LOG.md`; working tree is clean.
- **Reproducible benchmark evidence:** exp-0045 is EXECUTING (no results
  yet; frozen prereg `0abf66836ed0ad6d…`, plan, fresh suites and dispatch
  attempt 20). exp-0044 screen `41812595433` /
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
  `docs/DEV6_EXP0043_REPORT.md`, `docs/DEV6_EXP0042_REPORT.md`,
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

## Executing: exp-0045 (Tier-1 fixed-time, isolated VMs)
- **Why selected:** exp-0044 is closed, and the next ranked unexecuted
  direction that changes NO search decision is bit-exact `evaluate()`
  throughput. exp-0039 built this exact fix, verified it bit-exact, measured
  ~2.9 % locally against a ~7 % noise floor, REVERTED it and spent NO games.
  That was a precision/cost decision, not a negative strength result.
  exp-0045 is the FIRST Elo measurement of the hypothesis, on isolated VMs at
  FIXED TIME 40+4 ms. Not a repeat of exp-0039's profiling, not a parameter
  change of a failed idea, and no exp-0041..0044 data reused.
- **Mechanism:** `SkipDeadTTEval` (default OFF) skips the `evaluate(pos)`
  whose result is immediately overwritten when a main-TT hit supplies a valid
  static eval. Values are BIT-IDENTICAL at any fixed node count; only time per
  node can change. No TT/move/score/stand-pat/pruning/extension/ordering
  decision changes, no added per-node work, no new forfeit mechanism.
- **Mandatory diagnostics (pre-result):** node counts OFF/ON IDENTICAL at
  depths 8/10/12 (e.g. depth 12 `[72604, 497628, 311669, 559024]`); ON
  skipped 40,187 of 379,656 `evaluate()` calls (10.6 %) so the mechanism is
  LIVE; local 12-repeat timing OFF 804.0 ms / ON 823.5 ms (−2.37 % "speedup",
  noise-dominated, reported verbatim, NO local speedup claim). Only ~10.6 % of
  evaluations are skippable => the theoretical speedup is ~2-3 %.
- **Power, explicitly:** a 2,000-game screen has ~13 Elo half-width and CANNOT
  resolve a +2-3 Elo effect; full-sized confirmation is reserved by the
  preregistered scheduler for screen point >= +55. exp-0045 is powered for
  the +20 ADVANCE threshold and to rule out a material regression only. A
  SINGLE-RUN COMPUTE BOUND closes it as INCONCLUSIVE if neither frozen
  condition holds. No post-hoc sample increase.
- **Frozen before games:** `docs/DEV6_PREREG_EXP0045.md` (SHA
  `0abf66836ed0ad6d979a26a3d4ca8616416bfb88b8ca069875f1e7d4e7bb2863`),
  `tier1-plan-exp0045.json` (4 jobs), dispatch `mode=benchmark attempt=20`,
  source (default OFF, bit-exact signatures `243f9a1c1ba5b36f` /
  `a14ab62224f837e5` / `e45fa2ec2287eb41`, d16 with `ttEval=1` identical
  OFF/ON, Release 11/11, ASan+UBSan 11/11, UCI default false), and 1,400
  fresh disjoint openings (seed `2026120501`, ZERO overlap with 36,241 earlier
  positions / 135 files).
- **Design:** FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, never `--nodes`;
  ONE binary, single switch `SkipDeadTTEval=true` vs `false`; Stage-0 validity
  null (0 forfeits required), candidate-options null, batchA 1,000 and
  batchB 1,000 games on independent fresh suites, combined frozen before the
  run, independent raw-JSONL audit. Frozen ADVANCE >= +20 AND LCB > 0 AND
  both batches >= −5 AND both null CIs include 0 AND clean; CLOSE if
  UCB < +10 OR point <= 0; otherwise CLOSED AS INCONCLUSIVE / ABANDONED
  (single-run compute bound, no confirmation). ADVANCE alone does NOT satisfy
  Gate 1.

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
any games. After exp-0045: ADVANCE -> continue validation/subsequent gates; CLOSE or
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
