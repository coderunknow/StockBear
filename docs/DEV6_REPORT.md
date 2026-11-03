> **SUPERSEDING STATUS NOTICE (append-only).** This report describes the
> historical cycle that ended at pushed commit `797f5cbed45433622a54044163d91c73dbd22b75`
> (gate FAIL, no PR/tag/release). Its overall verdict remains valid for that
> cycle. Two statements are now **superseded**: (1) "external rating ladder NOT
> COMPLETED" — the ladder was subsequently executed (see
> `docs/DEV6_EXTERNAL_LADDER.md` §0 and `docs/DEV6_EXTERNAL_LADDER_REPORT.md`);
> (2) "M0 measurement foundation not established" — see
> `docs/DEV6_EXP0030_BUILD_INTEGRITY.md`. Subsequent local experiments
> exp-0031..exp-0035 and the CURRENT overall status are in
> **`docs/DEV6_STATUS_REPORT.md`**, which is authoritative. No dev6 gate is
> met and no release action has been taken.
>
> ---
>
# StockBear v0.1.0-dev6 — Final research report

**Verdict: the mandatory strength gate is NOT MET.** The candidate is a measured
**regression** of −17.0 Elo (95% CI [−21.4, −12.6]) against the exact released
dev5 artifact. No strength claim, no release PR, no merge, no tag, no release,
no `v0.1.0-dev7` were made. Everything below is committed to the branch so it
survives sandbox resets. This report distinguishes **Verified / Partially
verified / Not yet verified / Inconclusive / Failed / Skipped / Blocked**.

## 0. Status taxonomy (summary)

| item | status |
|---|---|
| Exact released dev5 baseline resolved, verified, pinned | **Verified** |
| dev6 source correctness (build, ctest, independent oracle, bench) | **Verified** |
| Two disjoint pre-registered decisive batches executed (13,200 games) | **Verified** |
| Primary strength gate (+75 / LCB>+50) | **Failed** (candidate is −17.0 Elo) |
| Null controls compatible with zero | **Verified** |
| Independent recomputation of raw results | **Verified** |
| Integrity control (candidate == dev5 at same params) | **Inconclusive** (confounded, see §5) |
| `params_exp0020` reuse screen | **Inconclusive** |
| External multi-engine rating ladder | **Not yet verified / Blocked** (§7) |
| Absolute rating and gap to 3,000 Elo | **Not yet verified** (no measured pool) |
| CodeRabbit review on exact final PR head | **Skipped / not applicable** (no PR eligible) |
| CI + full test matrix on exact source head | **Verified** (both runs success) |
| Merge / tag / release / deployment | **Blocked** — requires explicit user approval, gate unmet |
| Branch started from a separately verified `origin/main` SHA | **Partially verified** (§9) |

## 1. Provenance and exact identities

- Repository `https://github.com/coderunknow/StockBear`, default branch `main`.
- Starting repo SHA (clean working branch at session start):
  `6e7c2e02881faf93a84990a8345c41ad28bcae11`.
- Working branch (this session's fixed, dedicated dev6 research branch):
  `arena/3e6dd5b6-stockbear`. `VERSION` = `0.1.0-dev6` on the branch; released
  version remains `v0.1.0-dev5`.
- `v0.1.0-dev5` annotated tag object `ae8a6dffa6c6d2845006bd265b23bed3179ec6da`
  -> commit `c94571313a1667048468cf6d4e070400dc5ab228` (merge of PR #10). Tag and
  release assets were **never** rewritten, moved or deleted.
- **Immutable baseline**: `benchmarks/binaries/stockbear-dev5-release`,
  SHA-256 `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`,
  extracted from the official `stockbear-0.1.0-dev5-linux-x64.tar.gz` verified
  against the published `SHA256SUMS.txt` (both Linux + Windows archives verified).
  `bench` `243f9a1c1ba5b36f`, `bench --depth 16` `a14ab62224f837e5`, UCI
  `StockBear 0.1.0-dev5`. Build flags `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1
  -flto=4` (portable x86-64-v3, no `-march=native`), ubuntu-22.04 GCC. Champion
  runtime `EvalParams=research-data/params_abc.txt` (SHA
  `8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be`, shipped ==
  repo) + `TTEval=true`. Published claim: +64.7 [+57.5,+72.0] vs dev4 (exp-0024).
  Provenance: `benchmarks/dev6-baseline/{manifest.json,PROVENANCE.md,SHA256SUMS.txt,params_abc_shipped.txt}`.
- Key commits: `a7bf00f` (dev6 cycle start / exp-0025 prereg), `cbd2e85`
  (runner-pushed exp-0025 baseline results), `4cd9894` (exp-0026 implementation),
  `28a5c719721e809759bdb3cf22436e8034cdabbd` (**exact source head** that all
  decisive matches, CI run `41638608619` and lane run `41638608427` used). Later
  commits are results/data/documentation only and do not change engine code.
  Final branch tip: see `git rev-parse HEAD` in the completion summary.

## 2. Objective and pre-registered gate

Genuine, independently-confirmed playing-strength improvement over the EXACT
released dev5 artifact: combined fixed-time point estimate >= +75 Elo, two-sided
opening-clustered 95% CI lower bound strictly > +50, both independent
pre-registered confirmation batches positive and reasonably consistent, null
controls compatible with zero, exact portable release artifact/config tested.
Primary benchmark 40+4 ms, hash 16 MB, 1 thread, paired openings with reversed
colours, identical adjudication/time management, dedicated isolated runner, no
concurrent CPU work. Statistics: opening-clustered CR1 variance with two-sided
95% Student-t CI (primary), plus paired pentanomial, W/D/L, score/Elo, SPRT
(labelled approximate), cluster bootstrap and leave-one-shard-out sensitivity.
Full pre-registration (frozen before any result): `docs/DEV6_PREREG.md`;
baseline prereg `docs/DEV6_PREREG_BASELINE.md`; power analysis
`docs/DEV6_POWER_ANALYSIS.md`.

Stale/contradictory docs were corrected by APPENDED superseding notices (never
rewritten): `docs/DEV5_REPORT.md`, `docs/DEV6_RESEARCH.md`,
`docs/DEV6_CONFIRMATION.md`, `docs/DEV7_CONFIRMATION.md`, `docs/ROADMAP.md`,
`CHANGELOG.md`, `README.md`, `DESIGN_LOG.md`, `AGENTS_LOG.md`,
`benchmarks/FAILURE_LEDGER.md` (all append-only). The older "dev6/dev7"
confirmations measured a +50 gate against **dev4** in the dev5 cycle; they are
historical and cannot satisfy this gate.

## 3. Hypotheses and code changes

Audit finding: of the four shipped "exp-0022" extended eval ids, `RookOn7th`
and `KnightOutpost` were computed, but `BackwardPawn` and `PawnChain` were
**dead rows** (declared/ranged/tunable, never counted); the default-off
incremental path maintained none of them.

H1: six correctly-implemented pawn-structure/coordination features on top of the
dev5 champion improve 40+4 ms strength by >= +75 Elo. Chess rationale and exact
predicates: `docs/DEV6_EVAL_FEATURES.md`. Changes:
- `src/evaluation/eval_params.{hpp,cpp}`: append `ConnectedPassed`,
  `RookBehindPassed` (append-only table, 36 -> 38 ids, shipped 0). New default
  checksum `0x5d90d35fb2203bde` (was `0x79473f95496c545e`);
  `benchmarks/params/dev3-shipped.txt` + `tests/unit/test_eval_baseline.cpp`
  updated accordingly.
- `src/evaluation/evaluation.cpp`: one shared `extended_counts(p, us)` helper
  used by `features()`, `accumulate_breakdown()` and the incremental path, so
  live eval and offline breakdown cannot diverge; gated behind an "any extended
  param non-zero" flag so the default/champion build is bit-exact and pays zero
  extra per-node cost.
- `research-data/params_dev6_a.txt` (SHA `e94c0562…`): champion 32 rows +
  six hypothesis-driven priors (`RookOn7th 10 14`, `KnightOutpost 6 4`,
  `BackwardPawn -10 -8`, `PawnChain 2 2`, `ConnectedPassed 8 16`,
  `RookBehindPassed 5 10`). NOT tuned on validation loss.
- New lane `.github/workflows/dev6-lane.yml`, `scripts/actions_dev6_lane.sh`,
  `scripts/check_dev6_eval_features.py`, `scripts/dev6_power_analysis.py`,
  `scripts/dev6_decisive_openings.py`, `scripts/dev6_confirmation_report.py`,
  two disjoint 3300-opening decisive suites (+ 12 slice files).

**Correctness (Verified):** ctest 11/11 (41 unit tests incl. a new gating/count
test and a perturbed-parameter mirror test with all six coefficients non-zero);
independent python-chess oracle over 600 reproducible positions — 43,200
feature checks, **0 mismatches** (`benchmarks/dev6-baseline/eval_features_reference.json`);
`evaldata --check` 600/600; default bench bit-exact; exact `-flto=4` portable
build reproduces both bench signatures; UCI `0.1.0-dev6`; cost ~13% of the
combined breakdown+evaluate loop when enabled (~0.69 µs/eval), zero when gated
off. No `-march=native` in the portable config.

## 4. Complete experiment table (all results reported, no cherry-picking)

Conditions for every match: 40+4 ms, hash 16 MB, 1 thread, `--max-plies 240`,
paired colour-reversed openings, dedicated ubuntu-latest VM (AMD EPYC 7763,
4 vCPU, glibc 2.39), candidate binary SHA `4b06b117…` (portable `-flto=4`),
baseline `391cb50e…` at champion options. Primary estimator = clustered CR1/t.

| ID | design | games | point Elo | 95% CI | classification |
|---|---|---|---|---|---|
| exp-0025 | baseline provenance (verification) | n/a | n/a | n/a | SUCCESS (Verified) |
| exp-0026 | 6 extended features correctness | n/a | no strength claim | n/a | SUCCESS (Verified) |
| exp-0027 screen (primary, params_dev6_a) | candidate vs dev5, `openings_dev4.txt` | 2000 | −25.0 | [−42.9, −7.3] | REGRESSION |
| exp-0027 control (params_abc) | candidate vs dev5, same suite | 1100 | +33.0 | [+13.7, +52.5] | INCONCLUSIVE (confounded) |
| exp-0027 exp0020 | candidate(params_exp0020) vs dev5 | 1100 | −12.1 | [−33.7, +9.4] | INCONCLUSIVE |
| exp-0028 decisive batch A | params_dev6_a vs dev5, fresh suite A | 6600 | −17.8 | [−24.1, −11.5] | REGRESSION |
| exp-0028 null | candidate vs identical | 1100 | +0.6 | [−9.5, +10.7] | SUCCESS (null PASS) |
| exp-0029 decisive batch B | params_dev6_a vs dev5, disjoint suite B | 6600 | −16.2 | [−22.4, −10.0] | REGRESSION |
| exp-0029 null | candidate vs identical | 1100 | −2.5 | [−12.8, +7.7] | SUCCESS (null PASS) |
| **COMBINED decisive** | batch A + B | **13200** | **−17.0** | **[−21.4, −12.6]** | **REGRESSION / GATE FAIL** |

Combined: +4139 =4256 −4774 (47.59%), 6569 distinct opening clusters, t=1.980
on 6568 df, paired pentanomial −17.0 [−21.4, −12.6], cluster bootstrap (2000
reps) [−21.4, −12.6], SPRT (normal approximation) LLR −19.61. Terminal events:
8913 CHECKMATE, 4010 THREEFOLD_REPETITION, 230 INSUFFICIENT_MATERIAL, 11
FIFTY_MOVES, 5 STALEMATE, 31 UNADJUDICATED_MAX_PLIES; **0 TIME_FORFEIT, 0
illegal moves, 0 crashes, 0 UCI failures**. Unadjudicated games excluded from
score and counted; no outcome hidden or changed. Leave-one-shard-out points
−14.1..−21.2 (stable). Power analysis from exp-0024 raw records showed the
13,200-game design had expected half-width ~5 Elo at a true +75 (ample power);
it decisively excludes +75.

**Gate evaluation:** point >= +75 FAIL; LCB > +50 FAIL; both batches positive
FAIL; consistency PASS; nulls include 0 PASS; no unresolved engine-failure
regression PASS; overall **FAIL**.

Negative/neutral/invalid experiments from the whole Failure Ledger remained
active constraints and were NOT repeated (small CPU NNUE, cp distillation,
FullSoftBudget, qsearch-lite, PGO/TT/THP micro-opts, incremental eval, disabling
dev4 pruning/ordering, best-of-N param selection, fixed-node-only conclusions).
Raw paths: `benchmarks/exp-runs/exp0027-*`, `exp0028-*`, `exp0029-*`
(PGN + JSONL + CSV + manifest + report each). Machine-readable recomputation:
`benchmarks/dev6-baseline/confirmation_results.json`; full numbers
`docs/DEV6_CONFIRMATION_REPORT.md`; ledger `benchmarks/FAILURE_LEDGER.md`.

## 5. Integrity investigation (unexplained control difference) — Inconclusive

The `params_abc` control should have been ~0 Elo but measured +33.0
[+13.7,+52.5]. Verified from raw `match.jsonl` that this is NOT a config error
(both engines received the identical params file + options). Leading cause:
**toolchain mismatch** — dev5 was built on ubuntu-22.04, the candidate on
ubuntu-latest (Ubuntu 24.04 / GCC 13), which can change fixed-time NPS despite
identical bench signatures; plus the screen's ~240 clusters carry ~±19 Elo.
My source changes are ruled out (local same-machine `bench --depth 16`: dev6
1.015x dev5 NPS, 52.3 s vs 53.1 s at identical node counts; extended routine not
called for the shipped set). Nulls cannot detect a between-binary NPS difference.

**Confound-free ablation** (same suite, same binary, same baseline, only
`EvalParams` differs): +33.0 (`params_abc`) -> −25.0 (`params_dev6_a`) ≈ **−58
Elo** from the features. This is the primary algorithmic conclusion: the six
features are **harmful**, and the candidate lost by −17 Elo across 13,200 games
*despite* a possible ~+33 Elo build advantage. This unexplained
benchmarked-vs-packaged difference is recorded as required; it did not need
resolution for an approval decision because no approval is sought (gate unmet).
Required fix for any future cycle: build BOTH sides in one reproducible
toolchain/image, verify binary-level NPS equivalence, re-run the control before
any strength comparison. Classified INVALID MEASUREMENT as an equivalence check.

## 6. dev5 -> dev6 comparison (the actual question)

| | dev5 (released) | dev6 candidate |
|---|---|---|
| binary | `391cb50e…` (ubuntu-22.04) | `4b06b117…` (ubuntu-24.04) |
| eval | 36-term champion, `params_abc` | 38 ids, six extended features enabled |
| bench | `243f9a1c1ba5b36f` | identical (default set gated off) |
| measured vs dev5 champion | 0 (reference) | **−17.0 [−21.4, −12.6] Elo** |

dev6 is **not** an improvement; it is a regression with a tight, independently
replicated, null-clean interval. Combined with the toolchain confound, the
honest statement is that dev6's added evaluation is worse, and no release is
warranted.

## 7. External rating ladder and 3,000-Elo calibration — Not yet verified / Blocked

`docs/DEV6_EXTERNAL_LADDER.md` (status NOT COMPLETED / BLOCKED) records: exact
researched opponent identities/versions/sources/licenses (Stockfish 17.1/17/
16.1, Berserk 14, Ethereal 14.25, RubiChess 20240112, Koivisto 9.0), a
reproducible pilot-to-bracket design, a draw-aware Bradley-Terry-Davidson
multi-opponent model with cluster bootstrap, leave-one-out sensitivity, and
pool-specific interpretation. Published CCRL/CEGT ratings are contextual only,
explicitly not interchangeable. Blockers: official binaries/NNUE are served from
a CDN the sandbox cannot reach (runner-only), established engines are ~3500-3650
CCRL so a 40+4 match would be saturated, and no non-saturated anchor/pilot was
run; the primary gate is unmet so a full ladder cannot make the release eligible.

The only real anchor is INTERNAL: dev5 = +64.7 [+57.5,+72.0] vs the pinned dev4
binary (exp-0024). **No absolute pool rating was measured, so the numeric gap
to 3,000 Elo is UNKNOWN and is not estimated; no absolute rating is claimed.**
`docs/DEV6_3000_ROADMAP.md` gives the evidence-driven staged plan (M0 rating
foundation -> M1 reliably beat dev5 -> M2 eval gap -> M3 search -> M4 SMP ->
M5 re-rate), separating tactical/positional/endgame/search/time-management/
performance weaknesses, with measurable milestones and no fabricated timeline.
3,000 Elo is a long-term strategic target, not a claim.

## 8. Hardware / software / build / resources / CI / review

- Sandbox: 2 vCPU Xeon (AVX2/BMI2/POPCNT/LZCNT), ~3.8 GB RAM; Debian GCC 12;
  `.venv` cmake/ninja/numpy/python-chess/scipy. No paid compute, no GPU, no
  secrets/permission changes, no external engine source/networks copied into
  StockBear.
- Decisive compute: free GitHub-hosted `ubuntu-latest` dedicated VMs (AMD EPYC
  7763, 4 vCPU, glibc 2.39, GCC 13), 17 matrix jobs, lane run `41638608427`
  (18m11s, SUCCESS). All matches isolated per job, no concurrent CPU work.
- Build: `cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-mpopcnt -mbmi2
  -mlzcnt -DSB_SEE_CACHE=1 -flto=4"`; both bench signatures reproduced;
  ctest 11/11 locally.
- CI run `41638608619` (4m21s, SUCCESS) on exact source head `28a5c71…` — the
  full matrix (Debug/Release, Clang, ASan/UBSan, TSan where configured). Earlier
  CI `41635295493` and baseline lane `41635295602` also SUCCESS.
- **CodeRabbit / PR review: SKIPPED (not applicable).** No PR is eligible while
  any mandatory gate is unmet; a review of an earlier or non-final SHA is not
  approval. Documented manual audit instead: independent recomputation from raw
  JSONL (`scripts/dev6_confirmation_report.py`, shares no code with the match
  harness's summary), independent python-chess feature oracle, ctest 11/11,
  per-job manifest SHA verification, and this report. When (if) a passing
  candidate exists, a complete CodeRabbit review on the exact final PR head must
  be requested and tracked (not started / in progress / finished with findings /
  skipped / failed / rate-limited), and substantive findings fixed and retested.
- Infrastructure note: concurrent result pushes produced cosmetic duplicate
  empty `[skip ci]` commits; all 17 result dirs verified intact; history was not
  rewritten (no destructive remote operations).

## 9. Constraint reconciliation — Partially verified

"Start from verified current main; create a dedicated dev6 research branch": the
session toolchain fixed this working branch to `arena/3e6dd5b6-stockbear` and it
already existed locally at `6e7c2e02881faf93a84990a8345c41ad28bcae11`; a
separate `git rev-parse origin/main` verification before branching was NOT
recorded, and a new branch was not created (the fixed one was used and pushed).
This is **Partially verified**, stated honestly rather than claimed. No
destructive remote operation was used to "fix" it (that requires approval).
Everything else (dedicated branch, VERSION, immutable dev5 tag/artifacts, no
dev7, no release without approval) was observed.

## 10. Authorization status

- Authorised work performed: inspection, implementation, research branch,
  commits/pushes to the dev6 branch, free CI/experiments, docs/logs — all done.
- **NOT done, and NOT authorised:** merge, `v0.1.0-dev6` tag, publish/modify any
  GitHub release, deployment/production, paid compute, secret/permission changes,
  destructive remote operations, and **opening any release PR** (a PR is opened
  only after ALL mandatory gates/audits/exact-head checks pass; they did not).
- No approval was sought because the gate is unmet. If a future candidate passes,
  a complete PR + exact-head CodeRabbit review + explicit user authorization for
  merge/tag/release are still required.
EOF
echo "DEV6_REPORT.md written"