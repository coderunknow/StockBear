# Benchmarking methodology

The executable embeds its position suites so measurements do not depend on a checkout. `benchmarks/positions/*.inc` are the source of those suites. Run an optimized Release build on an otherwise idle machine, record the CPU, OS, compiler/flags, version, hash, thread count and exact suite. Do not compare measurements from materially different machines, clocks or builds as if conditions were identical.

## Perft

```sh
./build-release/stockbear perft 5
./build-release/stockbear perft 4 --fen 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1' --divide
./build-release/stockbear bench --perft
python3 scripts/reference_perft.py  # optional python-chess reference
```

The CSV includes the FEN, depth, expected and actual leaf count, elapsed microseconds, NPS and pass/fail; mismatch returns nonzero. At depth one it counts the generated legal moves without making each leaf move, a common bulk-counting optimization. Perft NPS therefore measures a different operation from search NPS. Tiny elapsed times are noisy. Expected totals in the versioned suite were regenerated independently with python-chess 1.11.2.

## Search

```sh
./build-release/stockbear bench --depth 5 --hash 16
./build-release/stockbear bench --nodes 100000 --hash 16
```

Each position gets a freshly cleared table. The CSV identifies the position/FEN, best move, completed depth, cp or mate score, PV, total nodes, elapsed microseconds, NPS and sampled hash fullness (per mille). For a node-limited run, the node total includes a possibly interrupted iteration; the score and PV are from the **last completed** iteration. A detected terminal/drawn root can stop before the node budget with depth zero. With fixed depth/nodes and a fixed build the move/score/node/PV fields are deterministic; wall time and NPS are not. The `hash_requested_mb` is an allocation ceiling, and actual allocated bytes are printed. Scores and tactical accuracy are not Elo measurements.

## Matches

The optional harness uses its own UCI subprocess controller and python-chess for independent legal move checking, draw adjudication and PGN. No opponent is bundled. Supply both engine paths:

```sh
python3 -m pip install chess==1.11.2
python3 scripts/tournament.py --engine-a ./build-release/stockbear \
  --engine-b /path/to/other-uci-engine --games 8 --base-ms 1000 --inc-ms 20 \
  --threads 1 --hash 16 --pgn match.pgn --jsonl match.jsonl
```

Games run sequentially on the same host with the same requested clocks, increment, hash budget and thread count. Each deterministic opening is played twice with colors swapped; opening moves are preplayed without clock charge. Engine options that are absent or cannot be verified are recorded as such. The controller measures wall time including protocol overhead and declares a time or illegal-move forfeit where appropriate. It automatically claims available draws; hitting `--max-plies` without an outcome is recorded as `*`/unadjudicated, not fabricated as a draw. PGN, per-game JSONL, settings and W/D/L are written explicitly.

The reported Elo transform and Wilson interval over fractional scores are only a rough descriptive approximation: they ignore the dependence within opening pairs, draw-rate modeling and other experimental variation. Very small matches, especially zero/all wins, have very wide or infinite bounds and cannot establish a precise Elo or superiority. Record engine versions, CPU, build flags and actual option differences, and use substantially larger independent samples for strength claims.

See [the recorded v0.1.0-dev1 baseline](../benchmarks/results/0.1.0-dev1/REPORT.md) for raw CSV, PGN and JSONL. Optional Stockfish use is as an opponent only; no external engine participates in StockBear's move selection.
