# exp-0024 confirmation — release-artifact gate: PASSED

Date: 2026-11-03. Pre-registered in `docs/EXP0024_PREREG.md` (committed as
`511a756` before the run; fresh suite `openings_exp0002_confirmation.txt`,
sha256 `90e99b37daae8c1c5e12cd1a1b54743e8ee8aac20b52f78b38d20bbb4d7342de`,
2200 paired openings, seed 2026110502, excludes every position of ALL earlier
suites including exp0001 — previously untouched).

## Why

exp-0023 measured +66.4 on a `-march=native` runner build. Such a binary is
specific to the build runner's CPU and is NOT shipped. The release artifacts
(`.github/workflows/release.yml`) are built with the portable subset
`-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4` (x86-64-v3). exp-0024
gates exactly that artifact configuration against the same immutable dev4
baseline, so the shipped binary's strength claim has its own evidence.

## Result

Candidate: branch @ `511a756` (engine source identical to the exp-0023
candidate `737c6f4` — `git diff 737c6f4..511a756 -- src/` is empty), built
`-DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-mpopcnt -mbmi2 -mlzcnt
-DSB_SEE_CACHE=1 -flto=4"` (NO `-march=native`), options
`EvalParams=research-data/params_abc.txt` + `TTEval=true`.
Baseline: `benchmarks/binaries/stockbear-dev4-1c5b61a7` (sha256
`1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae`),
sha- and bench-asserted per job.

**6600 games (12 shards x 550, seeds 2026110701..712), 40+4 ms, hash 16,
threads 1, suite exp0002, GitHub-hosted ubuntu-latest dedicated VMs:**

| estimator | Elo | two-sided 95 % CI |
|---|---|---|
| naive (Wilson) | +64.8 | [+56.3, +73.4] |
| paired pentanomial (3285 pairs) | +64.7 | [+58.1, +71.4] |
| **opening-clustered CR1, t(1745)** | **+64.7** | **[+57.5, +72.0]** |

**LCB95 = +57.5 > +50 → the release-artifact gate is MET.** SPRT(0,5) LLR
28.96 → accept H1. W+D+L = 2907/1986/1692 of 6600 games (6585 adjudicated +
15 unadjudicated at max-plies = 6600; 6585 + 15 = 6600 exactly). **One
TIME_FORFEIT by the dev4 baseline** (8.2 ms move over the 40+4 budget),
scored as its loss per the pre-declared symmetric policy — counted, not
hidden. Terminations: 4598 checkmate, 1851 threefold, 123 insufficient
material, 10 fifty-moves, 2 stalemate, 15 unadjudicated, 1 time forfeit.
Raw: `benchmarks/exp-runs/exp0024-shard01..12/` + `exp0024-null/`; pooled:
`benchmarks/exp-runs/exp0024-pooled.json/.txt`; null pooled:
`exp0024-null-pooled.json/.txt`.

**Null (candidate vs candidate, 1100 g, seed 2026110799):** +1.3
[−8.0, +10.6] clustered — includes 0, no lane bias.

## Independent audit

`scripts/audit_exp0023.py --exp exp0024` recomputes everything from the raw
jsonl without importing `match_stats`: **+64.7259 [+57.4674, +72.0407]**
(1746 clusters, 3285 pairs) — matches `exp0024-pooled.json` to full double
precision; all 12 manifests verified (git_head `511a756`, dev4 sha, bench
`243f9a1c1ba5b36f` both binaries, suite sha `90e99b37...`, seeds, options,
portable build flags, TC 40+4 hash16 threads1); every opening used is in the
suite; colours reversed per pair; prereg doc + suite unmodified since
`511a756`. Output: `benchmarks/exp-runs/exp0024-audit.json`. Zero problems.

## Reading vs exp-0023

Portable artifact build +64.7 [+57.5, +72.0] vs native runner build +66.4
[+59.3, +73.6] — the intervals overlap almost completely; the ~1.7 Elo
difference is the `-march=native` codegen margin on the runner CPU and is
inside the noise. Both gates pass with LCB95 strictly above +50.
