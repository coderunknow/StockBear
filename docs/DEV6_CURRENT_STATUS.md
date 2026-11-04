# StockBear v0.1.0-dev6 — CURRENT AUTHORITATIVE STATUS (2026-11-04)

Older reports `docs/DEV6_STATUS_REPORT.md` and
`docs/DEV6_POST_AUTHORIZATION_REPORT.md` are superseded for this cycle; they
remain historical records. This document is the current gate verdict.

## Verdict: MISSION ACTIVE — NOT COMPLETE
`docs/DEV6_PREREG.md` §8 gates are **unchanged and unweakened**.

| gate | verdict | basis |
|---|---|---|
| 1 | **UNMET** | No fixed-time 40+4 ms candidate with point >= +75 AND two-sided opening-clustered 95 % LCB > +50 on both independent positive batches. Best preregistered fixed-time evidence remains exp-0036 `+21.5238 [10.2819, 32.8108]` (Tier-2 dedicated core), closed at its frozen futility boundary; exp-0038 `+7.6755 [−1.0670, +16.4278]` (Tier-1 isolated VMs), closed inert/overhead. |
| 2 | **direction-supported** | exp-0036 on both independent datasets under the existing spec. |
| 3 | **PASS** | Both required null experiments include zero in their CIs; exp-0038 null `+0.8818 [−15.6419, +17.4096]` additionally passes. |
| 4 | **UNMET for a final candidate** | Tier-1 infrastructure is verified end-to-end (packaged identity, SHA-256, git + Contents API retrieval, 0/9 and 0/4 checksum failures, CI on exact source), but no exact final candidate release artifact has been tested. |

No strength claim. No PR, approval, merge, tag, release or deploy while any
gate is unmet. 3,000 Elo is a long-term strategic target only; no absolute,
universal, CCRL/FIDE or numeric gap-to-3000 claim. No dev7.

## What is operational now
- `.github/workflows/dev6-tier1.yml`: `workflow_dispatch` + deliberate
  `benchmarks/exp-runs/tier1-dispatch.json` push trigger; `prepare`, one
  isolated `ubuntu-latest` VM per matrix benchmark job, artifact upload, and a
  deliberate `mode=export` job using `actions/download-artifact(run-id)` with
  checksum verification and ONE `[skip ci]` evidence commit (including forced
  `*.log` files). Benchmarks never push results.
- Verified evidence runs: smoke `41778365897` (40-game null self-match,
  **DISCARDED**, no strength inference) and exp-0038 `41780333569` (4 jobs,
  2,792 scheduled games, Stage-0 validity PASS, 0 forfeits). Both exported and
  checksum-reverified locally; `benchmarks/dev6-baseline/tier1_verification.json`
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
  Full report `docs/DEV6_EXP0038_REPORT.md`.
- **exp-0039** dead static evaluation on TT hits: eliminated at profiling
  (bit-exact fix measured <= 2.9 % against a ~7 % build/CPU noise floor),
  source reverted, no games played.
- **exp-0040** banked-time allocation: eliminated at profiling; the confirmed
  live soft-budget increase (4 -> 6 ms) left the tree bit-identical because the
  55 %/70 % early stops dominate at 40+4 ms. No games spent, switch stays OFF.

## Closed: exp-0041 (Tier-1 fixed-time, isolated VMs)
- **exp-0041** losing-capture pruning at ALL remaining depths: frozen prereg
  `docs/DEV6_PREREG_EXP0041.md` (SHA `2f5c1b08…`), 1,400 fresh disjoint
  openings, Stage-0 validity PASS (0 forfeits), null PASS, frozen combined
  `−5.0635 [−15.1810, +5.0454]` on 1,995 games / 995 clusters, independent
  audit 44/44 PASS. Closed at frozen UCB < +10 and point <= 0; ABANDONED, no
  bundle, no retune, switch default OFF. The −42.1 % fixed-depth-12 node
  saving was profiling and is NOT strength evidence. Full report
  `docs/DEV6_EXP0041_REPORT.md`. Gate verdict above is unchanged.

## Exact continuation state (for the next cycle)
Branch `arena/3e6dd5b6-stockbear`; working tree clean; all default strength
switches OFF; immutable dev5 binary/tag, `main`, and all historical artifacts
untouched. Tier-1 dispatch file is at `mode=export`, attempt 8 (no benchmark
will auto-run on the next push unless it is deliberately changed). Ranked
unexecuted directions: singular/tactical extensions, TT replacement policy, a
NEW frozen prereg for bit-exact qsearch eval throughput (never a silent reuse
of the abandoned exp-0038 cache), and a larger bullet-matched eval corpus /
NNUE-with-accuracy-link. Each must be frozen before any evaluation game, with
a Stage-0 validity gate, two independent fresh suites, a null, and the
frozen Gate-1 criteria unchanged. Gate 1 (+75 / LCB > +50) remains far away;
a FRESH-measured bundle of validated mechanisms is only authorised by a
frozen ADVANCE rule, never a post-hoc sum. Mission ACTIVE, NOT COMPLETE.


## Exact continuation state
Branch `arena/3e6dd5b6-stockbear`; local HEAD and remote head are recorded in
`AGENTS_LOG.md`; working tree is clean apart from in-progress registration
work. All default strength switches remain OFF; champion parameters, immutable
dev5 binary/tag and `main` are untouched. The mission continues with the
ranked directions in `docs/DEV6_RESEARCH_MATRIX.md`; a failed experiment or
futility boundary closes ONLY that experiment, never the mission.
