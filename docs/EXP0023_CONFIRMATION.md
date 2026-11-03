# exp-0023 confirmation — GATE RESULT: PASSED

Date: 2026-11-03. Pre-registered in `docs/EXP0023_PREREG.md` (committed as
`737c6f4` BEFORE the run; suite committed earlier, untouched before this run).

## Result

Candidate (branch `arena/daa69a3b-stockbear` @ `737c6f4`, built with
`-DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-mpopcnt -mbmi2 -mlzcnt
-DSB_SEE_CACHE=1 -march=native -flto=4"`, options `EvalParams=
research-data/params_abc.txt` + `TTEval=true`) vs the immutable baseline
`benchmarks/binaries/stockbear-dev4-1c5b61a7` (sha256
`1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae`):

**6600 games, 40+4 ms, hash 16, threads 1, fresh suite
`openings_exp0001_confirmation.txt` (sha256 `32537dd8...`, 2200 paired
openings, seed 2026110501, excludes all prior suites):**

| estimator | Elo | two-sided 95 % CI |
|---|---|---|
| naive (Wilson) | +66.5 | [+58.0, +75.1] |
| paired pentanomial | +66.4 | [+59.9, +73.0] |
| **opening-clustered CR1, t(1774)** | **+66.4** | **[+59.3, +73.6]** |

**LCB95 = +59.3 > +50 → the mandatory gate is MET.** SPRT(0,5) LLR 30.74 →
accept H1. W+D+L = 2949/1928/1704 of 6600 games; 18 unadjudicated
(max-plies); **0 forfeits/crashes** (terminations: 4653 checkmate, 1792
threefold, 124 insufficient material, 9 fifty-moves, 3 stalemate, 19
unadjudicated). Raw records: `benchmarks/exp-runs/exp0023-shard01..12/`
(pgn/jsonl/csv/manifest per shard), pooled estimate:
`benchmarks/exp-runs/exp0023-pooled.json` / `.txt` (via
`scripts/pool_matches.py`).

**Null (candidate vs candidate, 1100 g, seed 2026110699, same suite):**
−1.3 [−11.7, +9.2] clustered — includes 0, no lane bias.

## Pre-registration compliance
- Source SHA: `737c6f473ed86677e3b79146f0e97bf1d3099369` (frozen; the runner
  manifests record `git_head` = this commit for every shard).
- Binary identity: baseline pinned binary, sha asserted per job; candidate
  sha recorded per shard manifest (differs across runner CPU models because
  of `-march=native`; search behaviour pinned by runtime-asserted bench
  `243f9a1c1ba5b36f` AND bench --depth 16 `a14ab62224f837e5` on both binaries,
  plus ctest 11/11 locally).
- Options/flags/TC/hash/threads/seeds/suite-hash/game-count: as pre-registered
  (shards 550 g x 12, seeds 2026110601..2026110612; null seed 2026110699).
- Hardware: GitHub-hosted `ubuntu-latest` runners, dedicated VM per job
  (CPU-isolated); observed AMD EPYC 7763 and EPYC 9V45, 4 vCPU, glibc 2.39;
  recorded per job in manifest.json (`runner` block). Public repo → no cost.
- Stat method: opening-clustered CR1 (per-opening pair totals, Student-t on
  G−1 df, logistic scale), pooled across shards; paired pentanomial and
  SPRT(0,5) reported alongside. Forfeit policy: symmetric, predeclared
  (none occurred).
- Shards: 12 x 550 = 6600 games; each shard an independent seeded sample of
  the same suite; pairs rebuilt per shard then pooled.
- No peeking: shards ran as parallel isolated jobs; pooling done only after
  all 12 completed (run `41610113495`).

## Screens that led here (all 480 g @ 40+4 on openings_dev4.txt, runner lane)
- exp0019-base (plain champion flags + params_abc + TTEval): +44.0 [+20.5,+67.9]; null +7.3 [−9.2,+23.7].
- exp0021-native-base (same source, `-march=native -flto=4`): +71.4 [+47.6,+95.8]; null −10.2 [−27.0,+6.6].
- exp0020-native (fresh 6000-game/636k-position corpus retune incl. the
  exp-0022 features, native build): +80.2 [+55.4,+105.9] — promising but
  within screen noise of exp0021; NOT in the confirmed candidate.
- exp-0019 margin/aspiration variants (plain and native builds): all within
  ±25 of their base; rfut110 the only mild positive (+56.5 plain / +76.8
  native vs +44.0/+71.4 bases) — left out of the frozen candidate, noted for
  future work.

## Verdict
The gate (LCB95 strictly > +50 vs the original dev4 baseline at 40+4,
hash 16, threads 1, fresh pre-registered suite) is **MET at +59.3**.
Version stays `v0.1.0-dev5`; the winning recipe is: dev4 source + popcnt/
bmi2/lzcnt/SEE-cache flags + `-march=native -flto` + `params_abc` + `TTEval`.
