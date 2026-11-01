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
count and PV of every position — in `--depth` and `--nodes` mode. Both fields are
reproducible there; `--movetime` (and any other time-limited run) depends on the
machine, so those runs print `# signature unavailable (movetime mode is not
deterministic)` instead of a fingerprint that would change between runs of one
build. Two builds or two parameter settings that
differ anywhere in those fields have different signatures, so behaviour
regressions can be caught without comparing timings. CI runs the same command
twice and compares a *narrowed* projection of the output, not the whole text: the
CSV contains wall-clock microseconds, NPS and `hashfull`, which legitimately vary
between runs on the same binary. The check requires both runs to agree on the
`# StockBear` header line, the `# signature` line and the deterministic columns
(name, best move, depth, score, nodes, PV) of every row, and ignores the timing
columns.

For fixed depth/nodes the move, score, node and PV fields are deterministic;
wall time, NPS and `hashfull` are not. Node counts are the primary optimisation
metric because they are machine-independent. A feature ablation is reported as
nodes *and* time, and any ablation that changes the tree shape is read with care:
turning a pruning feature off can reduce node counts at a fixed depth for
ordering reasons, which says nothing about strength. Strength claims come only
from matches.

The `NullMove`, `LMR`, `Aspiration`, `Futility`, `ReverseFutility`, `SEEPruning`,
`CheckExtension`, `CounterMoves`, `ContinuationHistory`, `CaptureHistory`,
`HistoryMaluses` and `LMRHistory` UCI options expose the same switches, so the
tournament harness can measure a feature by strength. The last five default to
off because the dev3 matches found no benefit; they are kept switchable so the
measurement can be repeated. **Set every switch explicitly on both sides** and
keep the record's `configuration` line: it stores the options that were sent to
each engine *and* the defaults each engine advertised, so the configuration can
be read out of the evidence years later, when a build's defaults have changed —
as they did within dev3 itself:

```sh
python3 scripts/tournament.py --engine-a ./build-release/stockbear \
  --engine-b ./build-release/stockbear --a-option NullMove=false \
  --games 200 --base-ms 80 --inc-ms 8
```

### Released signatures

Record the `# signature` of the shipped build, because a changed signature means
behaviour changed and needs an explanation. For `v0.1.0-dev3` (and, by
construction, `v0.1.0-dev2`):

| build | depth | signature |
| --- | --- | --- |
| shipped defaults | 6 | `e06c4352681ae8eb` |
| shipped defaults | 7 | `5bceff035f2a4ae4` |
| all five dev3 ordering switches on | 6 | `8d99b4e28a6231a0` |
| all five dev3 ordering switches on | 7 | `f6103610012f7f9d` |
| tuned evaluation candidate A (`tuning/variantA.txt`) | 6 | `269a852faa999f37` |

The shipped rows are identical to the rebuilt `v0.1.0-dev2` binary, which is the
intended outcome of shipping the dev2 search and evaluation with the new switches
turned off. A signature is a statement about these twelve positions only: the
review fix that made a null move clear the "previous move" slot changed how
quiets are ordered after a null move without altering any of these rows, and it
did change play in deeper endgames. Use the signature to catch a regression on
the suite, and a match to measure behaviour. Per-set node counts for the shipped build at depth 6/7:

| suite | depth 6 nodes | depth 7 nodes |
| --- | --- | --- |
| total, 12 embedded positions | 108,910 | 250,053 |

The all-on configuration costs about 8 % more time at equal depth (118,548 and
255,021 nodes) without winning a match, which is why it is not the default. The
full list of ablations and both feature matches is in
`benchmarks/results/0.1.0-dev3/REPORT.md`.

### Fixed node budgets

`--nodes N` replaces the clock with `go nodes N` for every move. Nothing can be
lost on time, so the same command reproduces the same moves on a loaded machine,
which is what the CI smoke test uses:

```sh
python3 scripts/tournament.py --engine-a ./build-release/stockbear \
  --engine-b ./build-release/stockbear --games 2 --nodes 2000 --max-plies 20 \
  --pgn match.pgn --jsonl match.jsonl
```

A node budget is not a time control, so a match played this way is a search-quality
comparison, not a tournament result: record it as such and do not quote an Elo
estimate from it without the usual paired-opening sample.

## Matches

A match is only evidence for the configuration its record describes. The harness
writes a `configuration` line first and a `summary` line last; the first is the
one that proves what was played (engine names, paths, per-engine option values,
per-engine advertised defaults, node budget, seed, opening file, host), so quote
it next to any result and do not reconstruct a configuration from the command
line you think you typed.

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
* an **opening-clustered** interval around the same pentanomial mean: the suite
  replays each opening several times, so even pairs are not independent. The CR1
  variance is computed from per-opening cluster totals with a Student-t critical
  value on G-1 degrees of freedom. This is the interval quoted in the release;
  when the record has fewer than two distinct openings, no clustered interval is
  reported;
* a normal-approximation **SPRT** log-likelihood ratio against `H0: 0 Elo` and
  `H1: +5 Elo` with α = β = 0.05 (bounds ±2.94), which is a stopping aid and is
  labelled as an approximation, not a proof. `tournament.py` plays the requested
  number of games and evaluates the LLR afterwards, so a crossed bound is
  reported as a crossing on the finished sample, not as an early stop.

A recorded match does not have to be replayed when the estimators change:
`scripts/recompute_summary.py` rewrites only the trailing summary line from the
unchanged per-game records and marks the result as recomputed.

Elo is always quoted with an interval and a sample size. A point estimate alone
is not evidence, and a small match with an all-wins or all-losses record has an
infinite or extremely wide bound; the report prints that interval rather than a
number. The Elo transform itself assumes the model `score = 1/(1+10^(-Δ/400))`
and is only descriptive.

## External opponent

The tuning pipeline has its own record: `docs/TUNING.md` documents the dataset,
the trainer command lines, the parameter sets and the match that rejected each
candidate. A tuning-loss improvement is not a strength result; every candidate
must be matched against the shipped binary, one binary on both sides differing
only in the `EvalParams` file, and a candidate is shipped only on a match that
is not negative. In dev3 none was, so `benchmarks/params/dev3-shipped.txt` is
byte-identical to `benchmarks/params/dev2-baseline.txt`.

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
