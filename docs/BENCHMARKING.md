# Benchmarking methodology

The executable embeds its position suites, so measurements do not depend on a
checkout. `benchmarks/positions/*.inc` are the source of those suites. Run an
optimized Release build on an otherwise idle machine and record the CPU, OS,
compiler/flags, version, hash, thread count and exact suite. Do not compare
measurements from materially different machines, clocks or builds as if
conditions were identical.

## Perft

```sh
./build-release/stockbear perft 5
./build-release/stockbear perft 4 --fen 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1' --divide
./build-release/stockbear bench --perft
python3 scripts/reference_perft.py  # optional python-chess reference
```

At depth one the suite counts generated legal moves without making each leaf
move (bulk counting), so perft NPS measures a different operation from search
NPS. Tiny elapsed times are noisy. Expected totals were regenerated
independently with python-chess 1.11.2.

## Search benchmarks and ablations

```sh
./build-release/stockbear bench --depth 6 --hash 16
./build-release/stockbear bench --nodes 100000 --hash 16
./build-release/stockbear bench --movetime 200 --hash 16
./build-release/stockbear bench --depth 7 --param nullMove=0
```

The CSV on stdout identifies each position's FEN, best move, completed depth,
cp/mate score, nodes, elapsed microseconds, NPS, hash fullness and PV. Every run
also prints a header line with the version, mode, requested/allocated hash and
the active `SearchParams`, plus a final `# signature <hex>` line: a
deterministic FNV-1a fingerprint of the name, best move, depth, score, node
count and PV of every position. Two builds or two parameter settings that
differ anywhere in those fields have different signatures, so behaviour
regressions can be caught without comparing timings. CI runs the same command
twice and requires byte-identical output.

For fixed depth/nodes the move, score, node and PV fields are deterministic;
wall time, NPS and `hashfull` are not. Node counts are the primary optimisation
metric because they are machine-independent. A feature ablation is reported as
nodes *and* time, and any ablation that changes the tree shape is read with care:
turning a pruning feature off can reduce node counts at a fixed depth for
ordering reasons, which says nothing about strength. Strength claims come only
from matches.

The `NullMove`, `LMR`, `Aspiration`, `Futility`, `ReverseFutility`, `SEEPruning`
and `CheckExtension` UCI options expose the same switches, so the tournament
harness can measure a feature by strength:

```sh
python3 scripts/tournament.py --engine-a ./build-release/stockbear \
  --engine-b ./build-release/stockbear --a-option NullMove=false \
  --games 200 --base-ms 80 --inc-ms 8
```

## Matches

The harness uses its own UCI subprocess controller and python-chess for
independent legal-move checking, draw adjudication and PGN. No opponent is
bundled. Supply both engine paths:

```sh
python3 -m pip install chess==1.11.2
python3 scripts/tournament.py --engine-a ./build-release/stockbear \
  --engine-b /path/to/other-uci-engine --games 400 --base-ms 80 --inc-ms 8 \
  --hash 16 --pgn match.pgn --jsonl match.jsonl --csv match.csv --seed 20261031
```

Rules that the harness enforces so a result cannot be inflated:

* every opening from `benchmarks/positions/openings.txt` is played twice with
  colours reversed, at identical clocks, increment, hash and thread settings;
* opening moves are preplayed without clock charge, and the opening order is
  shuffled with a recorded seed;
* wall time includes protocol overhead, and a clock overrun or an illegal move
  terminates the game as a **loss for the offender**. The recorded termination
  strings are `TIME_FORFEIT (<engine>, <n>ms move)` for a clock overrun and
  `ENGINE_FAILURE (<engine>: illegal move <uci>)` (or another engine error) for an
  illegal move, crash or protocol failure — there is no bare `ILLEGAL_MOVE` value,
  so filter by prefix;
* claimable draws are claimed by the controller exactly as the rules allow;
  fivefold/75-move/insufficient-material/dead-position endings are recorded with
  their rule;
* a game that reaches `--max-plies` **without an outcome is recorded as `*`
  (`UNADJUDICATED_MAX_PLIES`) and excluded from the score** — never converted
  into a draw;
* engine options that are absent or unverifiable are recorded as such.

Uncertainty is reported by `scripts/match_stats.py`:

* a naive Wilson interval over all games (ignores the dependence between the two
  games of an opening pair) — kept only as a reference;
* a **pentanomial** estimate that treats each opening pair as one observation
  with score in `{0, 0.5, 1, 1.5, 2}`, reporting the pair-score mean, its
  standard error and a 95 % normal interval on the implied Elo, plus the counts
  of the five pair outcomes;
* a normal-approximation **SPRT** log-likelihood ratio against `H0: 0 Elo` and
  `H1: +5 Elo` with α = β = 0.05 (bounds ±2.94), which is a stopping aid and is
  labelled as an approximation, not a proof.

Elo is always quoted with an interval and a sample size. A point estimate alone
is not evidence, and a small match with an all-wins or all-losses record has an
infinite or extremely wide bound; the report prints that interval rather than a
number. The Elo transform itself assumes the model `score = 1/(1+10^(-Δ/400))`
and is only descriptive.

## External opponent

Stockfish is used **only** as an external opponent; it never participates in
StockBear's move selection and is not bundled. Pin both the version tag and the
SHA-256 of the exact source archive you built, record the build command and the
resulting binary checksum, and report the match with the same paired-opening,
colour-reversed, identical-time-control protocol. A loss is reported as a loss.
The dev2 report records what could and could not be obtained in the build
environment and does not claim results it did not run.

## Recorded results

Each development release keeps its raw evidence under
`benchmarks/results/<version>/`: benchmark CSV, ablation CSV, per-game JSONL,
CSV, PGN, the full console report and a `REPORT.md` that states the environment,
the exact commands and the interpretation, including experiments that failed.
