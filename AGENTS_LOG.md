# Development log (append-only)

## 2026-10-30 — implementation and local verification

- Inspected the repository, branch, initial commit, tags, remote and existing instructions before editing. The working tree was clean and only the Apache-2.0 license existed; no unrelated user files were changed.
- Implemented core rules, search/evaluation, UCI, CLI, benchmark/tournament tools, tests, documentation and CI. Debug and Release CTest, Linux GCC ASan+UBSan, independent python-chess perft and differential checks were run locally; the versioned report records environment and actual outputs. The nine reference perft cases passed. Seed `20261030` matched 2,000 generated legal positions plus eight curated cases at depth two; an earlier independent check covered 4,845 generated positions. CI/Windows and release operations must be checked against the eventual exact head, not inferred from these local runs.
- **Magic generator edge-mask bug:** the original edge exclusion removed an entire rook file on edge squares; corrected edge selection. **Magic output truncation:** `%X` printed only the low 32 bits of 64-bit candidates; replaced it with a correctly typed 64-bit format and regenerated constants. Verification: startup occupancy-subset collision checks, independent ray-comparison unit test and full perft suite.
- **Capture undo bug:** the captured piece was read from the parent state after popping, not the state being popped. Save it before pop; regression `capture_unmake_restores_captured_piece` plus perft and randomized unwinding pass.
- **En-passant bugs:** hypothetical attack tests still counted a removed pawn, and hashing raw EP targets incorrectly distinguished positions where capture is illegal. Mask attackers by hypothetical occupancy and hash only legally capturable EP; regressions cover capture of the checker, a pinned EP pawn and a synthetic EP slider-block case. Move generation and repetition/hash checks pass against the independent reference.
- **FEN symbol mapping:** rook/queen and black indices were serialized incorrectly. Corrected the mapping; start and special-position round-trip tests pass.
- **Draw claims:** initially only current-position claims were exposed. Added intended-move claim detection and separate automatic thresholds, with tests for an impending threefold, the 99th halfmove, and checkmate precedence.
- **Search history isolation:** TT bounds can depend on rule-50 clocks, repetition history, the search-root boundary and extension budget. Included those contexts; added retained-table/new-root regression. `go infinite` on terminal positions was also changed to wait for `stop`, with a black-box regression.
- **Benchmark timing:** zero-millisecond results initially produced misleading NPS when treated as one microsecond. Added actual microsecond measurements; the recorded CSV uses those measurements.
- Built Stockfish 11 externally as an optional opponent and ran eight paired games at 1 s + 20 ms, one thread and 16 MiB requested hash each. StockBear lost 0–8. This tiny sample and approximate interval are reported without a claim about Stockfish 19 or competitive superiority.
- Release decision is gated on reviewing the complete diff, passing CI on the exact PR head and merged commit, and verifying the authorized merge/tag/prerelease operations; local results alone are not a substitute.

## 2026-10-30 — pre-commit review

- The complete staged-diff whitespace check found a trailing blank line in the recorded PGN. The tournament writer now separates games without adding a redundant final blank line; the PGN smoke test verifies both game parsing and legality after the change. No game moves or outcomes were altered.
- The final API review found that callers bypassing legal-move generation could ask `make_move` to capture a king. The public entry point now rejects that before mutating state; `public_make_move_never_captures_a_king` verifies the error and exact state preservation. Normal engine callers still pass generated legal moves.
- Regenerated the versioned benchmarks after the king-capture API guard; the new eight-game paired Stockfish 11 smoke match again ended 0–8. Recorded CSV/PGN/JSONL reflect the final guarded engine build rather than the earlier preliminary run.

## 2026-10-30 — hosted verification and release packaging

- On PR head `fe79cf045fe42d0392bb9f268da632aefe36c389`, both push and pull-request CI runs passed all seven jobs, including Windows Debug/Release, Clang, ASan/UBSan and the independent reference job. Those results apply only to that head, not subsequent commits.
- Direct download of GitHub Actions artifacts from this sandbox was blocked by the artifact storage host. Added a manually dispatched, guarded GitHub-runner release workflow: it checks an annotated tag, default-branch ancestry and a successful exact-commit push-to-main CI run, rebuilds/tests Linux and Windows binaries, creates a draft with both archives and checksums, verifies the assets, then publishes it as a prerelease. No tag or release is created before merge and verification.
- Kilo and Qodo reported exhausted credits/trial; Copilot reported insufficient quota. Their notices are not substantive approvals. CodeRabbit's initially skipped review was explicitly requested and is in progress; inspect its eventual findings on the applicable head before the merge decision.
- CodeRabbit's explicitly requested review completed substantively on `fe79cf045fe42d0392bb9f268da632aefe36c389`. Verified and addressed its findings: documented `ctest --test-dir` was incompatible with the declared CMake 3.16 minimum (replaced with `cmake -E chdir`; all seven tests pass with CMake/CTest 3.16.8); GUI-supplied negative remaining clocks could leave a UCI client without a search (bounded negative `wtime`/`btime` now clamp to zero, with positive/negative/malformed protocol tests); and mutable GitHub Action tags were replaced by the current upstream tag commit SHAs with checkout credentials not persisted. These changes require new exact-head CI and review verification.
- Re-ran the baseline after the review-driven UCI change; the recorded paired match again finished 0–8 against Stockfish 11. The stored search/perft timings and PGNs now correspond to that rebuilt implementation.
- The completed review also noted that a malformed `PERFT(...)` row could be silently skipped by the independent reference parser. Confirmed the issue, made the parser reject unrecognized or partially matched rows, and added a dedicated regression run in the reference CI job. Added a CMake 3.16 CI job so the compatibility regression remains covered. The proposed removal of `ExtMove` initializers was deferred: no profile demonstrates benefit, and retaining initialization is safer than an unmeasured micro-optimization.
- Parsed and statically linted both workflows locally with PyYAML, actionlint and zizmor. Zizmor's default policy reported no findings; pedantic mode reported only low-level suggestions. Release publication now serializes concurrent runs for a tag and documents its narrowly scoped token permissions. The CI matrix values flagged as possible shell interpolation are fixed literals, not external input; CI jobs are intentionally not canceled by concurrency rules so mandatory checks are not skipped.

## 2026-10-31 — dev2 implementation and verification

- Re-validated the dev2 tree from scratch: Release reconfigure, 52 C++ unit
  cases, 8 CTest entries (the dead-position group was missing from CTest and now
  has its own entry, `deadpos`), plus the UCI integration, fuzz, tournament and
  statistics scripts. Found and fixed several real defects:
  - `unmake_null_move()` decremented `fullmoveNumber_` although
    `make_null_move()` never incremented it, so every null move drifted the FEN
    counters. Removed the decrement; added `test_position_extra.cpp` with
    null-move round-trip, repeated-null, in-sequence unwind and en-passant-key
    tests (registered in CMake).
  - `scripts/match_stats.format_report()` raised `KeyError` when the SPRT had no
    bounds (too few pairs or a degenerate sample), i.e. the report crashed on the
    very runs that produced no decision. It now prints the note instead, and the
    summary includes the game count the tournament integration test expects.
  - The UCI controller rejected a whole `go` command on an unknown token, which
    contradicts the specification and makes GUIs that send `ponder` or
    `searchmoves` unusable. Unknown tokens are now ignored (malformed values of
    supported parameters are still rejected); the fuzz test's oracle was
    rewritten to mirror that grammar, and the integration test now checks a
    `go depth 2 ponder searchmoves ...` command still returns a legal move.
  - `tests/integration/test_uci_integration.py` asserted the literal dev1 version
    string; it now reads `VERSION` and also requires complete `info` lines
    (seldepth, score, nodes, nps, hashfull, time, pv).
  - The `--help` text did not mention `--movetime`, `--param` or the `deadpos`
    depth option.
- Dead-position evidence produced and recorded: 23-case corpus (0 failures,
  witnesses replayed), independent python-chess reference comparison (10
  compared, 0 failures at a 400,000-state cap, with two `KN` v `K` cases skipped
  there and re-run at a 1,500,000-state cap), and two new exhaustive unit tests
  over all legal two-king placements and all legal three-piece bishop/knight
  placements with either side to move. The exhaustive test initially failed on
  positions that are *stalemate* (terminal under Article 5.2.1, hence reported
  `alive`-terminal, never `dead`); the assertion now distinguishes terminal
  positions from dead ones, which is the correct reading of the rules.
- Measurements (recorded with raw files): depth-6 suite 1,683,192 → 276,352 nodes
  and 1,041 → 257 ms; depth-7 8,276,659 → 516,138 nodes and 3,605 → 397 ms;
  depth-7 ablations for seven features; `bench` signature `838a0a824cb1686f`
  (depth 6) and `ff1cf4d5109617aa` (depth 7).
- Matches: a 400-game paired match on an idle machine ended +159 =132 −109
  (score 0.5625, paired Elo +43.7 [95 %: +14.3, +73.7], SPRT LLR 0.93 →
  continue, no forfeits or capped games). An earlier 400-game run that overlapped
  compilation produced mass `TIME_FORFEIT`s and reported a *better* score (+191
  =109 −100); it was discarded rather than published, and the incident is
  recorded in the report.
- External opponent: Stockfish 19 (`sf_19`, source SHA-256 recorded) could not be
  built because its NNUE network files are unreachable from this environment
  (build fails at `network.o`); Stockfish 11 was built from source
  (`ARCH=x86-64-bmi2`, binary SHA-256 recorded) and won 20–0 at 100 ms + 10 ms
  with no draws or forfeits. The report states that this says nothing about
  Stockfish 19.
- Verification: CTest Debug 8/8, Release 8/8, ASan+UBSan 8/8,
  ThreadSanitizer 3/3 on `unit|regression|uci_integration`; independent perft,
  differential (2,000 positions), tournament, statistics, dead-position corpus
  and dead-position reference scripts all pass locally.
- Documentation rewritten for dev2: README (including ScrispChess-Extended Custom
  UCI Engine Manager import instructions), CHANGELOG, RELEASE_NOTES, ROADMAP,
  ARCHITECTURE, TESTING, BENCHMARKING, THIRD_PARTY, a new
  `docs/DEAD_POSITIONS.md` and `benchmarks/results/0.1.0-dev2/REPORT.md`.
- Open items at the time of writing: exact-head CI, CodeRabbit review, merge,
  tag and release remain to be verified on the final head; nothing in this log
  claims those operations succeeded.

## 2026-10-31 — review fixes on the dev2 head, re-verification

- Classified the PR #3 review comments (Copilot review did not run — quota; Codex
  2 × P1; CodeRabbit 16 actionable + 4 nitpicks) and fixed every substantive one.
- **SEE correctness defect (real, found by review):** the exchange fold dropped the
  final recapture. Knight × defended pawn scored +100 instead of −220. Refactored
  into `static_exchange_evaluation()`, fixed the fold, added known-value unit tests
  (verified the test FENs with `perft --divide` first). All previously published
  dev2 measurements were re-measured on the fixed build; the old +43.7 Elo match
  was discarded and regenerated.
- **Tournament script:** pairs are accumulated by game index and only complete
  pairs are scored; summaries are serialised with `allow_nan=False` and unbounded
  Elo intervals become `null` (`finite_or_none`/`_num_or_inf`) so the JSONL is
  strict RFC 8259. `test_statistics.py` 8/8 including a strict-JSON test.
- **CI:** the determinism step resolves the binary as
  `build/<config>/stockbear.exe` in the Visual Studio multi-config matrix; the
  `windows-2022 / Debug` job failure was diagnosed from the step script because the
  log download itself returned `EOF` from blob storage.
- **Dead-position reporting:** `states` (distinct) separated from `expanded`
  (budget unit), printed by `bench`/`deadpos` and by the corpus script; the header
  soundness comment was rewritten to claim only closure-by-prefixing.
- **CMake:** added the `position_extra` CTest entry (9 entries).
- Re-measured on the fixed build: depth-6 suite 106,558 nodes / 52.3 ms
  (signature `733440501ed37d3d`), depth-7 252,556 / 121.7 ms
  (`4e96e77c6c849463`), ablation table, 400-game dev1 match (+250 =103 −47,
  Elo +194.3 [+164.5, +227.0], SPRT accept H1, 0 forfeits, 0 capped), 20 games
  vs Stockfish 11 (0 W / 1 D / 19 L), corpus 23 cases 0 failures, independent
  reference `--full --max-states 400000` 10 compared / 2 skipped / 0 failures.
- Suites: CTest Release 9/9, Debug 9/9, ASan+UBSan 9/9, TSan 4/4; reference perft,
  differential (2,000 + 8 positions, seed 20261030), tournament and statistics
  scripts green.
- Docs corrected to the re-measured values (README, CHANGELOG, RELEASE_NOTES,
  ROADMAP, BENCHMARKING, DEAD_POSITIONS, REPORT.md); DESIGN_LOG carries an appended
  correction instead of an edit to the earlier entry.
- Still open at the time of writing: commit/push of these fixes, exact-head CI,
  CodeRabbit re-review of the final head, merge, tag and release. Nothing in this
  log claims those succeeded.
