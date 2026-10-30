# StockBear v0.1.0-dev1 — development prerelease

StockBear is a new independent C++17 UCI engine. Its board, legal move generation, state management, alpha-beta search, evaluation and UCI controller are implemented here; it neither embeds nor calls another engine to select moves. This is an early development release, not a stable or leading-strength engine.

## Included

- Standard chess legal moves, FEN and reversible state, castling, en passant, all promotions, checks, mate/stalemate, repetition and move-count draw detection.
- Iterative deepening, negamax alpha-beta/PVS, quiescence, a bounded transposition table and Zobrist keys, capture ordering, killer/history heuristics, limited check extensions and single-threaded time/cancellation handling.
- Handcrafted tapered material/positional evaluation; **no neural network**.
- UCI `uci`, `isready`, `ucinewgame`, `position`, `go` with depth/nodes/movetime/clocks/increments/movestogo/infinite, `stop`, `quit`, `debug`, and the `Hash` option. Unsupported UCI extensions are listed in the README.
- Perft/divide, deterministic fixed-depth/node benchmark suites, an optional paired UCI match/PGN harness, and CTest plus independent validation tools.

## Evidence

Nine perft positions passed their independently regenerated expected totals, including Kiwipete depth 4 = 4,085,603. A separate seed-20261030 differential run matched python-chess on 2,000 legal positions and eight curated cases at depth two. Local Debug/Release CTest and Linux ASan+UBSan runs exercised the code; check CI for results on the exact release commit and for Windows validation.

On a two-vCPU Xeon 2.60 GHz Linux guest with GCC 12.2 `-O3`, one thread and 16 MiB requested hash, the start-position depth-5 search used 17,075 nodes and 7,764 µs (about 2.20 million nodes/s); the full raw data, hardware, flags and methodology are in [the benchmark report](benchmarks/results/0.1.0-dev1/REPORT.md). An exploratory eight-game, paired-opening match at 1.0 s + 0.02 s against external Stockfish 11 ended 0 wins, 0 draws, 8 losses. The very small sample is not a precise Elo estimate. There was no Stockfish 19 match or superiority claim.

## Platforms and limitations

Linux x64 and Windows 10 x64 are the intended targets; the CI matrix builds and tests Windows and Linux Debug/Release and makes Release artifacts available when its jobs pass. The executable uses no Python or external chess engine at runtime. It does not require AVX-512 or a GPU.

The dead-position detector recognizes common material cases, not all blocked FIDE dead positions. FEN cannot encode pre-FEN repetition history; GUIs/referees must adjudicate draw claims. Search is single-threaded and uses baseline time/evaluation heuristics; no Chess960, pondering, `searchmoves`, MultiPV, tablebases, opening book, neural network or training system is provided. Future work is described in [the roadmap](docs/ROADMAP.md).

Apache-2.0; optional validation and opponent licenses are recorded in [THIRD_PARTY.md](THIRD_PARTY.md).
