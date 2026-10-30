# StockBear 0.1.0-dev1 baseline — 2026-10-30

This is a local development measurement, not a competitive-strength certification. Raw, intentionally retained outputs: [perft.csv](perft.csv), [search-depth5.csv](search-depth5.csv), [search-100knodes.csv](search-100knodes.csv), [match PGN](stockfish11-match.pgn), and [match JSONL](stockfish11-match.jsonl). The measured source was the release implementation in the working tree; use the release's CI runs for exact-commit verification. Timings fluctuate between runs.

## Environment

- Linux x86-64, Debian 12, kernel 6.1.158+, glibc 2.36; virtualized Intel Xeon @ 2.60 GHz, 2 visible CPU threads, approximately 3.8 GiB RAM. Runs below used one search thread.
- StockBear: GCC 12.2.0, CMake Release, `-std=c++17 -O3 -Wall -Wextra -Wshadow -Wpedantic`, no `-march=native`/AVX requirement. Linux executable linked `-static-libstdc++ -static-libgcc`, with glibc dynamic. Hash requested 16 MiB; table allocated 16,777,200 bytes.
- Independent reference/adjudicator: `chess` (python-chess) 1.11.2. Optional opponent: Stockfish 11 (`sf_11`), separately built with GCC 12.2.0, `ARCH=x86-64`, `-O3 -msse -flto`; its binary SHA-256 was `b5f8b4737e6111d9ba7239b856414d7e3353ba8282347ab53e1a12f741902587`. Stockfish was an external opponent, never part of StockBear.
- The local benchmark was run on a pre-commit working-tree snapshot of this release implementation. Windows is a CI target, not a locally executed platform. Check GitHub Actions for actual status at the exact release commit; this document does not substitute for it.

## Perft correctness

Nine FENs, including castling, pins, promotions, en-passant check evasion and en-passant discovered-check restrictions, were independently verified with python-chess. The detailed FEN, time and NPS are in the CSV; all expected/actual counts matched:

| Position | Depth | Expected / actual |
|---|---:|---:|
| Initial | 4 | 197,281 |
| Kiwipete | 4 | 4,085,603 |
| Rook/pawn endgame | 5 | 674,624 |
| Promotions and castling | 4 | 422,333 |
| Promotions/check evasions | 4 | 2,103,487 |
| Pinned en passant | 4 | 8,130 |
| En passant captures checker | 4 | 1,234 |
| Promotion choices | 4 | 432,422 |
| Middlegame activity | 4 | 2,238,608 |

All reference totals were recalculated with `scripts/reference_perft.py`. A separate seeded run compared exact legal moves and each depth-two divide branch for **2,000 legal positions + 8 curated cases**, seed `20261030`, against python-chess. One curated case is a deliberately synthetic impossible EP history, used solely to test the resulting geometry. Another earlier independent run compared 4,845 generated legal positions at depth two. Depth-one bulk counting means perft NPS is not search NPS.

## Search samples

The fixed-depth and fixed-node CSV files cover 12 positions including mate-in-one/two, tactical capture, check evasion, mate defense, promotion and stalemate avoidance. At fixed depth 5, examples from the recorded run:

| Position | Best move | Score | Nodes | Time | NPS |
|---|---|---:|---:|---:|---:|
| Starting position | `b1c3` | +25 cp | 17,075 | 12,509 µs | 1,365,017 |
| Complex middlegame | `e2a6` | +7 cp | 168,923 | 116,831 µs | 1,445,874 |
| Mate in two | `b2c3` | mate +2 | 66,245 | 16,194 µs | 4,090,712 |

The raw data contains the full PVs, other positions and fixed-100,000-node run. Repeating fixed-depth and fixed-node suites produced identical moves, scores, nodes and PVs when measured on the same build; timings were excluded from that comparison. A detected bare-king draw ends at depth zero instead of pretending to have searched the requested depth. Very short timings and measured NPS are noisy.

## Exploratory match

Eight games against **Stockfish 11**, with four deterministic openings each played in both colors, were run on the same host. Both were requested to use one thread, 16 MiB hash, and **1.0 second + 0.02 second per move** per side. StockBear table allocation was 16,777,200 bytes; Stockfish manages its own requested Hash allocation. Build flags differ as described above. No Stockfish 19 match was run.

StockBear scored **0 wins, 0 draws, 8 losses**; all eight games ended in checkmate, with no time/illegal-move forfeits or capped games. A Wilson interval over fractional scores is approximately **0%–32.44%**, corresponding to an approximate Elo interval of **−infinity to −127.4** in this harness. The point estimate is −infinity because there were no points. This interval ignores opening-pair dependence, and eight games are far too few for a precise rating; it is only a reproducible smoke-test baseline.

## Tests and limitations

Local Debug and Release CTest runs covered unit, regression, quick/full perft, randomized game stress, UCI integration and 300 seeded malformed/cancellation cases. A Linux GCC ASan+UBSan build was also exercised; rerun the commands in [TESTING.md](../../../docs/TESTING.md) on the exact code being considered for release. The material detector is not a general dead-position solver, UCI draw claims need an external referee, FEN contains no earlier history, search is single-threaded, and advanced search/neural evaluation are absent. Tests do not prove correctness in all positions or strength against any particular engine.
