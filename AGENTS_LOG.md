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

## 2026-10-31 — dev2 investigation

- Fetched remote tags and inspected GitHub releases, PRs and workflows. The
  annotated dev1 tag resolves to `dab34b0adb278ed474d64e1a700f7555e416ef4e`,
  equal to the branch base and current main; no existing worktree edits or
  AGENTS.md instructions were found. Existing dev1 CI push run
  https://github.com/coderunknow/StockBear/actions/runs/41017753636 succeeded.
- Rebuilt dev1 and the initial research prototype using the same GCC 12.2,
  CMake 3.16.8 and Release flags. Engine binaries were byte-identical; fixed
  depth five raw CSV and limitations are in `benchmarks/results/0.1.0-dev2/`.
  No strength improvement was measured. Stockfish 19 was identified via the
  official release API but not downloaded or used in a match.
- GCC Release, Debug and ASan+UBSan CTest passed 7/7 after the additions.
  Python-chess 1.11.2 differential test: 2,000 seeded positions plus eight
  curated, seed 20261031, passed; tournament smoke and timeout regression passed.
  Independent movement-graph enumeration: 7,225 and 436,665 states respectively,
  with zero mates, agrees with C++ count tests. This is not general verification.
- The promotion test initially exhausted a 20,000-position budget; increasing
  the explicit budget to 500,000 completed the graph. No exhaustion was
  interpreted as a dead result. See `docs/DEAD_POSITION_RESEARCH.md` for scope,
  proofs conditional on move generation, and missing release gates.
- Rechecked the nine reference perft totals and parser with python-chess; all
  passed. Updated packaging to include third-party notices, test extracted
  archives and compare uploaded draft assets against local checksums. These
  workflow changes have not been exercised by a release dispatch. The minimum
  CMake test used `cmake -E chdir ... ctest`; `ctest --test-dir` from CMake
  3.16 is unsupported and initially found no tests, so it was not counted.
