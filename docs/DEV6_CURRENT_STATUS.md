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
| 3 | **PASS** | Both required null experiments include zero in their CIs; exp-0038, exp-0041 and exp-0042 nulls additionally pass. |
| 4 | **UNMET for a final candidate** | Tier-1 infrastructure is verified end-to-end (packaged identity, SHA-256, git + Contents API retrieval, 0/9 and 0/4 checksum failures, CI on exact source), but no exact final candidate release artifact has been tested. |

No strength claim. No PR, approval, merge, tag, release or deploy while any
gate is unmet. 3,000 Elo is a long-term strategic target only; no absolute,
universal, CCRL/FIDE or numeric gap-to-3000 claim. No dev7.

## Experiment status vs mission status
- **Experiment status: exp-0043 LAUNCHED / EXECUTING.** exp-0042 is
  CLOSED/ABANDONED; exp-0041, exp-0038, exp-0037, exp-0036 are CLOSED;
  exp-0039 and exp-0040 were eliminated at profiling.
- **Mission status: ACTIVE, NOT COMPLETE.** Gates 1 and 4 remain UNMET. No
  experiment terminal state is a mission terminal state. No genuine blocker:
  the supported dispatch mechanism works; the earlier export-only dispatch was
  an ordinary research state, not a blocker.
- **Exact current source SHA:** `__EXP0043_SOURCE_SHA__` (the exp-0043
  dispatch commit; also pinned by `source_sha=HEAD` in
  `benchmarks/exp-runs/tier1-dispatch.json`). Local HEAD and remote head are
  recorded in `AGENTS_LOG.md`; working tree is clean.
- **Reproducible benchmark evidence:** exp-0042 screen `41802986830` / export
  `41804342869` / CI `41802986854` and confirmation `41804818965` / export
  `41806227744` / CI `41804818984`; both four isolated-VM jobs SUCCESS, 4/4
  SHA256SUMS with 0 failures, independent raw-JSONL audits 44/0 PASS. Screen
  `+2.6110 [−7.9556,+13.1825]` INCONCLUSIVE; confirmation
  `−10.8281 [−21.8567,+0.1787]` CLOSE, **NEVER pooled**. Earlier exp-0041
  `41782954038` / export `41784088471` `−5.0635 [−15.1810,+5.0454]`; exp-0038
  `41780333569` / export `41781546677` `+7.6755 [−1.0670,+16.4278]`. Full
  provenance in `docs/DEV6_EXP0042_REPORT.md`, `docs/DEV6_EXP0041_REPORT.md`,
  `docs/DEV6_EXP0038_REPORT.md` and `benchmarks/exp-runs/tier1-export/`.

## What is operational now
- `.github/workflows/dev6-tier1.yml`: `workflow_dispatch` + deliberate
  `benchmarks/exp-runs/tier1-dispatch.json` push trigger (paths-filtered, so a
  docs-only push does NOT launch another benchmark); `prepare`, one isolated
  `ubuntu-latest` VM per matrix benchmark job, artifact upload, and a
  deliberate `mode=export` job using `actions/download-artifact(run-id)` with
  checksum verification and ONE `[skip ci]` evidence commit. Benchmarks never
  push results. `workflow_dispatch` is unusable with the current token (HTTP
  403); the push trigger is the supported path and was used for attempt 13.
- Verified evidence runs: smoke `41778365897` (40-game null self-match,
  **DISCARDED**), exp-0038 `41780333569`, exp-0041 `41782954038`,
  exp-0042 `41802986830` and `41804818965` — all exported and
  checksum-reverified locally. `benchmarks/dev6-baseline/tier1_verification.json`
  records the smoke PASS. CI on every relevant source HEAD is SUCCESS.
- Independent audits: `scripts/dev6_audit.py` (215 stored values across
  exp-0031..0037) and `scripts/dev6_exp0038_audit.py` (44 stored values plus a
  seeded opening-cluster bootstrap) — both AUDIT PASS.

## Closed experiments this cycle
- **exp-0036** BadCapturePruning: Tier-2 fixed-time `+21.5238 [10.2819,
  32.8108]`, closed at preregistered futility UCB < +50. Not Tier-1.
- **exp-0037** ProbCut: fixed-node Stage-1 `+3.7766 [−9.3368, +16.9008]`,
  closed at frozen Stage-1 rule (point < +10), no Stage 2a. Default OFF.
- **exp-0038** dedicated qsearch TT: Tier-1 fixed-time `+7.6755 [−1.0670,
  +16.4278]`, closed at frozen UCB < +20 (inert/overhead). Default OFF.
- **exp-0039** dead static evaluation on TT hits: eliminated at profiling
  (bit-exact fix measured <= 2.9 % against a ~7 % build/CPU noise floor),
  source reverted, no games played.
- **exp-0040** banked-time allocation: eliminated at profiling; the confirmed
  live soft-budget increase (4 -> 6 ms) left the tree bit-identical because the
  55 %/70 % early stops dominate at 40+4 ms. No games spent, switch stays OFF.
- **exp-0041** losing-capture pruning at ALL remaining depths: frozen combined
  `−5.0635 [−15.1810, +5.0454]` on 1,995 games, 44/44 audit PASS. CLOSED at
  frozen UCB < +10 and point <= 0; ABANDONED, no bundle, no retune. The
  −42.1 % fixed-depth-12 node saving was profiling, NOT strength evidence.
- **exp-0042** max-gain delta pruning: screen `+2.6110 [−7.9556,+13.1825]`
  INCONCLUSIVE, bounded confirmation `−10.8281 [−21.8567,+0.1787]` CLOSE /
  ABANDONED. Two Tier-1 runs, each with Stage-0 validity PASS, null PASS and
  44/0 audit PASS; CIs overlap and were **NEVER pooled**. `MaxGainDelta` stays
  OFF, `deltaMargin=200` frozen. Full report `docs/DEV6_EXP0042_REPORT.md`.

## Executing: exp-0043 (Tier-1 fixed-time, isolated VMs)
- **Why this experiment:** after exp-0042 the ranked matrix puts
  singular/tactical extensions FIRST and demands a mechanism-live plus
  overhead diagnostic (exp-0037 showed verification subtrees are expensive at
  4 ms). exp-0041/0042 closed the whole "delete or re-decide quiescence
  nodes" family; stand-pat values are load-bearing.
- **Next experiment and why:** exp-0043 freezes a **TT-evidence singular
  extension with NO verification subtree**. The canonical re-search variant is
  DEFERRED, not abandoned — the deviation from the matrix wording is declared
  in advance in `docs/DEV6_PREREG_EXP0043.md` (SHA
  `e9fe40f053c9f479835c05efc3bf592547024090c1a315281ec727f0096f31dc`) so a
  null result cannot be misattributed to a mechanism that was never tested.
  It changes WHICH MAIN-SEARCH moves get an extra ply: no stand-pat rewrite,
  no new lossy qsearch rule, no default-ON feature disabled.
- **Frozen before games:** prereg, `tier1-plan-exp0043.json`, the dispatch
  (`mode=benchmark`, attempt 13), source (default OFF, bit-exact signatures
  `243f9a1c1ba5b36f` / `a14ab62224f837e5` / `e45fa2ec2287eb41`, Release 11/11,
  ASan+UBSan 11/11, UCI default false), and 1,400 fresh disjoint openings
  (seed `2026120201`, ZERO overlap with 32,041 earlier positions / 120 files,
  generator `scripts/dev6_exp0043_openings.py`).
- **Mandatory diagnostics (pre-result, NOT strength):** fixed depth 10 =>
  +13.9 % nodes (2,655,145 -> 3,024,895), 8,072 extensions; at the EXACT
  40+4 ms control the switch is LIVE on 23/24 suite positions (~22 extensions
  per search), median completed depth unchanged (6), node totals within fixed-
  time noise. Fixed-depth/node proxies are NOT strength evidence.
- **Design:** FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, never `--nodes`;
  ONE binary, single switch `TTSingularExtension=true` vs `false`; Stage-0
  validity null (0 forfeits required), candidate-options null, batchA 1,000
  and batchB 1,000 games on independent fresh suites, combined frozen before
  the run, independent raw-JSONL audit. Frozen decision rules: ADVANCE only if
  combined point >= +20 AND LCB > 0 AND both batches >= −5 AND both null CIs
  include 0 AND 0 forfeits/illegal/UCI failures; CLOSE if UCB < +10 OR point
  <= 0; INCONCLUSIVE -> exactly ONE bounded fresh confirmation under a new
  frozen addendum, NEVER pooled. ADVANCE alone does NOT satisfy Gate 1.

## Remaining work / gates
Gates 1 (+75 / LCB > +50 on two independent preregistered FIXED-TIME batches)
and 4 (exact packaged final-candidate binary/source/CI linkage with no
correctness, illegal-move, protocol or time-forfeit regression and no
unexplained benchmarked-vs-packaged difference) are UNMET. A FRESH-measured
bundle of independently validated mechanisms, never a post-hoc sum, is the
only credible route and is authorised only by a frozen ADVANCE rule. No final
candidate artifact exists. The remaining ranked directions are recorded in
`docs/DEV6_RESEARCH_MATRIX.md`. After the exp-0043 result: ADVANCE -> continue
validation/subsequent gates; INCONCLUSIVE -> preregistered bounded
confirmation; CLOSE -> document, update matrix and launch the next hypothesis;
TECHNICAL FAILURE -> diagnose, repair within scope, validate and retry with a
valid new run. No closure terminates the mission.

## Workspace reconciliation (earlier this cycle)
A fresh sandbox presented a clone at the original base commit with a stale
turn-end patchset overlay and no `.venv`. The overlay was preserved in a git
stash (`stash@{0}`, stale exp0037-era patchset; do not pop or drop without
need); `git fetch` + `git reset --hard FETCH_HEAD` aligned the local branch to
remote. All documents, plans, raw evidence and scripts were verified present;
`.venv` rebuilt with cmake 4.4.4 / ninja 1.13.2 / numpy 2.4.6 / chess 1.11.2 /
PyYAML 6.0.3. No force push, no shared-history rewrite, no scientific
conclusion changed.
