# dev5 benchmarks — what was measured, where the raw records live

All raw match records are under `benchmarks/results/0.1.0-dev5/` (PGN + JSONL
configuration/per-game lines + CSV + console summary). Every headline number in
the docs cites one of those files; the JSONL `configuration` block records both
binary SHA-256s, the opening-file SHA-256, every engine option actually sent,
the clock/node budget, the shuffle seed and the harness version, so each match
is reproducible with the stored command.

## Binaries (rebuilt bit-identical after the sandbox wipe, see DEV5_EXPERIMENTS.md)

| Build | Source | SHA-256 (first 16) | bench depth-4 signature |
| --- | --- | --- | --- |
| dev4 (immutable baseline) | tag `v0.1.0-dev4` | `1c5b61a755215134` | `243f9a1c1ba5b36f` |
| dev5 branch | `7969f8b` + uncommitted FullSoftBudget switch (default off) | `be2341455d59c92c` | `243f9a1c1ba5b36f` |
| safe-mobility research build | `728909b` + `-DSTOCKBEAR_SAFE_MOBILITY=ON` | `13d3a684002fbd9e` | n/a (eval differs) |

## Fixed-node screens (diagnostic; deterministic node budget, ±12% seeded jitter, hash 16, 1 thread, dev4 240-opening suite)

dev5+option vs dev4, opening-clustered 95% CI; full table in DEV5_EXPERIMENTS.md.
Headline arms: same-binary null +5.8 [−24.1,+35.8]; MoveCountPruning −34.9
[−70.1,−0.3] (regression, rejected); `EvalParams=params_outcome` +35.0
[+12.0,+58.3] at 480 g, +25.1 [+5.7,+44.6] at 960 g, +60.7 [+36.1,+85.9] at
n8000, +29.9 [+5.7,+54.4] at n20000; cp-distillation −30.6 [−57.0,−4.5]
(rejected); all NNUE nets −652..−760 at n3000/n8000/n50000 and at output scales
285.71/150/75 (rejected, see DEV5_EXPERIMENTS.md).

## Fixed-time 40+4 ms (primary evidence class for the gate)

Clean runs only (match alone on the 2-core sandbox; concurrent commands inject
±25 Elo common-mode noise — polluted runs are kept as records but not used).
Per-move search ≈ 7k nodes mean (depth 3-7; soft budget ≈ 4 ms, hard ≈ 13 ms).

- dev4 opening suite, 480 g: null (dev5 vs dev5) +13.9 [−9.3,+37.2];
  `EvalParams=params_outcome` +9.4 [−13.9,+32.9]; outcome+`FullSoftBudget`
  −21.0 [−44.4,+2.1]; safe-mobility +2.2 [−21.0,+25.3].
- Pre-registered confirmation on the untouched 550-family suite
  (`openings_dev5_confirmation.txt`, SHA-256 `75824edb...`, seed 2026110205,
  1100 games per match, null first then candidate, both alone):
  null (safe vs safe) +5.4 [−9.8,+20.6]; candidate (safe vs dev4)
  **+15.9 [+0.6,+31.2]** opening-clustered (pentanomial [+0.9,+30.9];
  413-321-364; 2 unadjudicated 240-ply games; no forfeits).

## External benchmark opponent

Stockfish 11 (teacher/benchmark only; binary SHA-256
`bc9e5ed4a8729e8c1f0acebfe60a3b8c6d8257fef61910aba94a922ff2aa5660`,
built from the `sf_11` source tarball) was used solely to produce fixed-node
search labels (`scripts/label_search.py`) for tuning. No Stockfish code,
weights or data were incorporated into StockBear. A pinned Stockfish
*opponent* match (dev5 candidate vs SF11 at fixed time) was planned but not
run: the gate had already failed on the internal confirmation, and the sandbox
later wiped the local teacher binary.
