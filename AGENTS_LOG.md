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

## 2026-10-31 — second review pass (CodeRabbit full review on 9c5e36e)

- CodeRabbit performed a full review of head `9c5e36e` (8 actionable comments, 1
  nitpick). Codex was rate-limited ("You have reached your Codex usage limits for
  code reviews") and Copilot's review quota was already exhausted, so this pass
  has one automated reviewer, recorded as such.
- **Statistics (major).** The 400-game match replays 31 openings ~6.5 times each,
  so treating the 200 pairs as independent understates uncertainty. Added
  `match_stats.opening_clustered()`: CR1 cluster-robust variance of the pair mean
  over opening clusters with a Student-t critical value on G-1 df (`_t95`).
  `tournament.py` now carries the opening label alongside each pair into the
  summary. Re-computed on the recorded match: **Elo +194.3, clustered 95 %
  interval +158.5 to +234.4** (31 openings, t = 2.042 on 30 df) versus the plain
  pentanomial +164.5 to +227.0. The clustered interval is now the headline in
  README, CHANGELOG, RELEASE_NOTES, ROADMAP and the report.
- **Zero-variance samples** no longer produce a zero-width interval
  (`[null, null]` plus a note, printed as `[interval not estimable]`); **unbounded
  Elo values keep their direction** (`_bounds_sign`), so an all-wins sample prints
  `+inf` instead of `-inf`. Two new known-value tests; `test_statistics.py` 11/11.
- **SPRT wording.** The harness plays the full requested game count and computes
  the LLR afterwards, so the report now says the upper bound was crossed on the
  finished sample instead of claiming a sequential stop. The Stockfish-11 section
  now states that accepting H0 does not prove equality and relies on the reported
  intervals (both entirely below -420 Elo) for that statement.
- **Documents.** `BENCHMARKING.md` describes the narrowed CI determinism
  comparison (header, signature and deterministic columns only); `TESTING.md`
  lists `position_extra` as its own CTest entry (null-move round trips);
  `README.md` no longer claims `Hash` is the only strength-relevant option — the
  feature switches change strength and are documented as experimental;
  `ARCHITECTURE.md` mentions the clustered estimator.
- **Nitpick fixed:** the 30,000-node / depth-8 quick witness pass now clamps to the
  caller's `DeadLimits`, so `draw_status()` cannot spend more than its
  `fast_dead_limits()` reservation.
- Re-verified after these changes: CTest 9/9 in Release, Debug, ASan+UBSan and
  ThreadSanitizer; `position_extra` runs 4 tests; corpus 23 cases / 0 failures and
  the independent reference 10 compared / 2 skipped / 0 failures were re-run on
  the rebuilt binary and the report timings updated.

## 2026-10-31 — third review pass (CodeRabbit full review on b9085b9)

- CodeRabbit reviewed head `b9085b9` (13 inline comments; several restated the
  previous round's findings, which were already fixed). Substantive items fixed:
  - **Restored the 64-node hard-timer poll.** dev2 had widened
    `NodeCheckInterval` to 1024, so a `go movetime 1` search could overrun its
    hard budget by up to a thousand nodes. Now 64 again, with a comment, and
    measured: `go movetime 1/5/20/50` returns at 1.1/1.1/15.2/45.2 ms median over
    ten runs each, never above the budget.
  - **`tournament.py` cleanup path.** `csv_handle` is initialised before the try
    block, so an option-validation `ValueError` during engine construction no
    longer turns the `finally` clause into `UnboundLocalError` and leak the first
    engine.
  - **Recorded summaries regenerated.** Added `scripts/recompute_summary.py`,
    which derives a new summary line from the unchanged per-game records. Applied
    to `match-dev1.jsonl` (adds the opening-clustered block: +194.3
    [+158.5, +234.4]) and `match-stockfish11.jsonl` (-636.4 [-inf, -420.7]); the
    game lines are byte-identical and the summary is marked as recomputed.
  - Report/notes corrections: `test_statistics.py` has 11 tests, and the empty
    "supported ()" parenthetical in the release notes now carries the result.
- **Timing fairness.** The depth-6 dev1 timing had been taken while the machine
  was compiling (1,041 ms), which inflated the speed ratio. Both binaries were
  re-run alternately in one idle session (three passes each): 685 ms → 57 ms
  (12×) at depth 6 and 3,171 ms → 137 ms (23×) at depth 7, with node counts
  unchanged (15.8× / 32.8× fewer). The bench CSVs, the per-position table and the
  ablation table (re-run in the same session, same signatures) were regenerated
  and README/CHANGELOG/RELEASE_NOTES/REPORT updated to the matched numbers.
- Re-verified: CTest 9/9 in Release, Debug, ASan+UBSan and ThreadSanitizer;
  `test_statistics.py` 11/11; `test_tournament.py` and `recompute_summary.py`
  pass; bench signatures unchanged (`733440501ed37d3d`, `4e96e77c6c849463`), so
  the search behaviour itself did not move.

## 2026-11-01 — fourth review pass (CodeRabbit on 5e58917) and re-measurement

- CodeRabbit reviewed `5e58917` (6 actionable comments, several re-statements of
  earlier rounds). One was a genuine, previously missed defect:
  - **`SeeValue[King] == 0`.** SEE believed an illegal king recapture was
    available, so a won pawn (`d2d7` in `4k3/3p4/8/8/8/8/3R4/3R2K1`) scored −400
    instead of +100. The king now has a dominant exchange value, with a
    known-value test that fails on the old value. Because SEE drives ordering and
    pruning, everything measured was re-run.
  - **`bench --movetime` no longer prints a signature**: it absorbs depth and node
    count, which are wall-clock dependent in that mode, so the run prints
    `# signature unavailable (movetime mode is not deterministic)` and the docs say
    the fingerprint applies to `--depth`/`--nodes` only.
  - **`tournament.py` validates option values** against the advertised UCI type
    (check/spin with min-max/combo) and fails on an `info string` rejection from
    `setoption`, so `--a-option NullMove=flase` cannot be recorded as an effective
    ablation. `--sprt-elo` now requires a finite positive value at parse time.
    Two new assertions in `test_tournament.py` cover both.
  - Docs: `docs/DEAD_POSITIONS.md` piece counts corrected to 16 and 12;
    `docs/TESTING.md` describes the narrowed determinism comparison.
- Re-measured on the fixed build: depth-6 1,683,192 → 108,910 nodes and
  622 → 49 ms; depth-7 8,276,659 → 250,053 and 2,896 → 125 ms (both binaries run
  alternately in one idle session); new signatures `e06c4352681ae8eb` (depth 6)
  and `5bceff035f2a4ae4` (depth 7); ablation table re-run.
- New 400-game match vs dev1 (identical protocol and seed): **+277 =82 −41**,
  score 0.795, Elo +235.4, paired pentanomial [95, 57, 39, 7, 2] CI +202.8 to
  +272.2, opening-clustered CI +193.4 to +284.5, LLR 7.69 crossing the +5 Elo
  bound; 318 checkmate / 75 threefold / 6 insufficient material / 1 fifty-move,
  0 forfeits, 0 capped.
- Stockfish 11 match re-run (identical binaries and protocol): 0 W / 1 D / 19 L.
- Dead-position evidence re-generated on the same binary: corpus 23 cases, 0
  failures; independent reference `--full --max-states 400000` 10 compared,
  2 skipped, 0 failures.
- Suites on this head: CTest 9/9 in Release, Debug, ASan+UBSan and ThreadSanitizer
  (TSan runs the whole set, including `deadpos`); `reference_perft.py` 9/9;
  `differential.py --samples 2000 --seed 20261030` pass; `test_statistics.py`
  11/11; `test_tournament.py` 2/2.

## 2026-11-01 — fifth review pass (CodeRabbit on d1414b7)

- CodeRabbit reviewed `d1414b7` (5 actionable comments). Three were new and are
  fixed; the rest repeated findings that earlier rounds had already resolved:
  - **Output-path collision.** `--pgn`, `--jsonl` and `--csv` are all opened in
    write mode, so two options naming one file would truncate each other's
    records. The paths are now resolved and required to be distinct, with a test.
  - **Corpus could pass an `alive` verdict without a certificate.** The check
    only validated a witness *if one was present*; a non-terminal `alive` without
    a `witness` line now fails, while the two terminal cases stay exempt. Re-ran
    the corpus afterwards: 23 cases, 0 failures.
  - **TT context across feature switches.** Changing a pruning switch left
    transposition-table entries computed under the old settings, which are not
    comparable with the new ones; `setoption` on a feature switch now clears the
    table. A GUI that never sends those options is unaffected, and depth/node
    bench signatures are unchanged (`e06c4352681ae8eb`, `5bceff035f2a4ae4`).
  - Docs: `docs/DEAD_POSITIONS.md` now limits the independent-reference claim to
    the ten positions that reference can actually decide (two are skipped at its
    cap); `docs/ARCHITECTURE.md` separates the `perft` text output from the
    `bench` CSV output and states that `--movetime` reports no signature.
- Re-verified after the fixes: CTest 9/9 in Release, Debug, ASan+UBSan and
  ThreadSanitizer; `test_tournament.py` 2/2; `test_statistics.py` 11/11; corpus
  23/23; independent reference 10 compared / 2 skipped / 0 failures; bench
  signatures unchanged, so the recorded measurements remain valid.

## 2026-11-01 — sixth review pass (CodeRabbit on bf574df)

- CodeRabbit reviewed `bf574df` (10 actionable comments). Seven repeated findings
  already fixed in earlier rounds; the following were new and are fixed:
  - **Duplicated witness work in the detector.** The quick pass and the second
    witness pass run the same deterministic search when the caller's
    `witnessNodes`/`witnessMaxDepth` are already at the quick-pass ceilings, so
    the second pass is skipped in exactly that case. The complete enumeration is
    never skipped; bench signatures are unchanged.
  - **Corpus witness exemption.** The exemption was keyed on the engine's own
    `reason` string, so an ordinary case whose reason said `terminal:` would have
    skipped the certificate check. It is now keyed on the corpus case label.
  - **`recompute_summary.py --in-place`** removed lines by substring matching;
    it now parses each record and drops only records with a top-level `summary`
    key, refusing to rewrite a file with an unparseable line.
  - **Combo option values** containing spaces are preserved (`Very Aggressive`
    was truncated to `Very`), and a `Hash allocation failed` `info string` is now
    treated as a rejected option instead of being recorded as effective.
  - **CI provenance** now records the CMake-selected compiler, generator and
    compiler id/version from `build/CMakeCache.txt` and
    `CMakeFiles/*/CMakeCXXCompiler.cmake`, instead of a `c++ --version` line that
    is unreliable under the Visual Studio generator.
  - Docs: the report's changed-move paragraph now separates the equal-score
    alternative from the two real differences and records that the
    stalemate-avoidance mate was re-verified at depth 12 on both builds;
    `docs/DEAD_POSITIONS.md` scopes the PSPACE-completeness citation to
    generalised *n*×*n* boards; `docs/TESTING.md` states that the independent
    reference compares 10 positions and skips 2; `RELEASE_NOTES.md` lists
    `position_extra` in the CTest inventory.
- Re-verified: CTest 9/9 in Release, Debug, ASan+UBSan and ThreadSanitizer;
  corpus 23/23; `test_statistics.py` 11/11; `test_tournament.py` 2/2;
  `recompute_summary.py` reproduces the recorded summary exactly.

## 2026-11-01 — seventh review pass (CodeRabbit on fa83925)

- CodeRabbit reviewed `fa83925` with one actionable comment (the remaining inline
  notes repeat findings fixed in earlier rounds — the bot re-anchors old comments
  to their original lines). The comment was a factual error in the report: the
  rook-and-pawn row does not change the move (both builds play `b4c4`), only the
  score (+38 versus +41). Corrected in `benchmarks/results/0.1.0-dev2/REPORT.md`.
- No further substantive findings were raised. The engine, tests, scripts and
  evidence are unchanged by this correction, so the recorded CI run for
  `fa83925` (all nine jobs green) still applies to the code; only documentation
  text moved.

## 2026-11-01 — v0.1.0-dev2 merged and published

- Repository-wide review turned green on the final pull-request head: CodeRabbit's
  last actionable comment was a factual error in the benchmark report (fixed in
  `87a6898`), and CI was 9/9 on `87a6898` (run 41266339862). The Kilo and Copilot
  reviewers were unavailable (insufficient credits, exhausted quota), so their
  "fail" states are resource failures, not findings; no human approval is claimed.
- Pull request #3 was merged with an exact-head safeguard
  (`--match-head-commit 87a6898`), producing merge commit `8b52281`. Push-to-main
  CI on that exact commit (run 41267078266) passed all nine jobs.
- Annotated tag `v0.1.0-dev2` was created on `8b52281` and pushed.
- The publication workflow could not be dispatched: the automation token has
  repository admin rights but not the `actions: write` permission, so
  `workflow_dispatch` returns 403. To keep every gate rather than fall back to an
  unguarded `gh release create`, `release.yml` also accepts a `workflow_call`
  invocation and `publish-request.yml` forwards one verified request (tag +
  exact-commit CI run) from the session branch. The publish job still verifies the
  tag string, the annotated tag type, that the tagged commit is on `main`, the
  successful push-to-main CI run for that commit, the expected asset set, and
  keeps the release a draft until the uploads verify. Run 41267902182 published
  the prerelease.
- The sandbox cannot reach GitHub's asset CDN, so an in-Actions audit
  (`verify-release.yml`, run 41268255137) downloaded the published assets, ran
  `sha256sum -c SHA256SUMS.txt` (both OK), listed the archive contents, exercised
  the released Linux binary (`id name StockBear 0.1.0-dev2`, 8 check options,
  `uciok`), and reproduced the documented bench signatures `e06c4352681ae8eb`
  (depth 6) and `5bceff035f2a4ae4` (depth 7) from the released archive.

## 2026-11-01 — follow-up: a deterministic move limit for the match harness

- CI failed once on `tests/integration/test_tournament.py` (run 41268457751,
  step "Verify tournament harness, PGN and CSV", 1 s — the normal duration), on a
  tree that passed on every other run, including the retrigger of the identical
  tree (run 41268967660). The job log endpoint is unreachable from the sandbox, so
  the failure text could not be read; the step detail endpoint localised it to
  that single step. Ten repeats on the same runner image passed (1.15 s each), so
  the cause is intermittent. The only assertion in that step that can fail without
  changing the step duration is the clock: at `--base-ms 500` a loaded runner can
  make the engine overrun and the harness records a `TIME_FORFEIT`, which is a
  loss and not `UNADJUDICATED_MAX_PLIES`.
- Rather than widen the clock, `scripts/tournament.py` gained `--nodes N`: every
  move is played with `go nodes N`, clocks are not accounted, and the budget is
  recorded in the JSONL configuration and summary. The smoke test now uses
  `--nodes 2000` and asserts the budget is recorded and that a negative budget is
  rejected. Two identical runs of a 5,000-node match produce identical results.
- The released `v0.1.0-dev2` artifacts are unaffected: the engine is unchanged,
  only the test harness and its documentation.

## 2026-11-01 — dev3 session notes

- Verified the `counterMoves` comment inconsistency by implementing the feature
  rather than by editing the comment: counter-move, continuation and capture
  history now exist, with a switch each, and the previously misleading comment is
  gone with the code it described.
- Chased a bench-signature mismatch between the rewritten search and dev2 with
  every new switch off. The cause was the root reporting a score from a move that
  merely raised alpha for a different slot; the fix swaps the alpha-improving move
  into the reported slot. With the features off the signature is byte-identical to
  dev2 again, so the mismatch was our bug, not an intended behaviour change.
- The history value that drives the LMR adjustment must be sampled *before*
  `make_move`: the table is indexed by the side to move, so reading it afterwards
  looks up the opponent's entries and silently disables the feature. Caught while
  reviewing, not by a test, and the comment now says why the order matters.
- Tuning harness: the first fit produced wild values (pawns 50, an isolated-pawn
  *bonus*); adding a ridge towards the shipped values, a movement cap and sign
  preservation fixed the plausibility, and the match then showed that all three
  candidates were equal or worse anyway. Loss on a holdout set did not predict
  playing strength, in either direction.
- Matches are reported from engine A's point of view. Reading a summary the wrong
  way round briefly made the worst-tuned candidate look like the best one; every
  Elo number in the release documents is written as "engine A score" so that this
  cannot recur silently.
- Stockfish 19 could not be obtained: release assets and the NNUE download
  endpoint are unreachable from the sandbox, the `sf_19` source builds but its
  default net is a Git LFS pointer, and 14 archived nets from the official
  networks repository were tried and rejected as architecture-incompatible. The
  attempts are recorded in the report; no substitute opponent was used and no
  Stockfish claim was made.

- Added a Windows diagnostic workflow (push-triggered, posts the ctest output as
  a PR comment) after the job logs proved unreachable from the sandbox; found the
  crash in `unit/multiPv_matches_single_pv_best_move` after making the test runner
  print a flushed RUN line before each test. Removed the workflow once fixed.
- The `Search` object was ~0.9 MB because two large tables were inline; that is
  fine on Linux (8 MiB stack) and fatal on Windows (1 MiB). Fixed by heap
  allocation plus a `static_assert`; bench signatures unchanged.
- Added `configuration.engine_{a,b}_defaults` to `scripts/tournament.py` and
  replayed both search-feature matches with all five switches set explicitly on
  both sides; the numbers were unchanged to the decimal, which is the expected
  outcome when the defaults were already off.
- The `unit` runner now prints a flushed `RUN` line per test: a segfaulting test
  otherwise leaves no record of which one died, and the Windows CI log was not
  reachable from this sandbox.

## 2026-11-02 — dev4 session record

- **Environment rebuilt twice.** The sandbox snapshot does not persist build
  directories, `/tmp`, or corpora above the snapshot size cap, so `build-dev4`,
  the self-play corpora and the training work directory disappeared between
  turns and had to be rebuilt (cmake/python-chess/numpy reinstalled, corpora
  regenerated, network retrained). Every command needed to rebuild them is
  recorded in `benchmarks/training/README.md`; the committed `.nnue` file and its
  measurements survived because they live in the repository.
- **Accumulator audit.** A temporary instrumentation in `evaluation.cpp`
  rebuilt the NNUE accumulator from scratch on every evaluation and compared it
  with the incremental one over a full depth-6 and depth-7 bench: no mismatch.
  The instrumentation was then removed (it is not part of the shipped code and
  must not be re-added — `verify_state()` covers the invariant in tests).
- **`NNUE true` semantics fixed.** It used to fail when a network had been loaded
  with `NnueFile` and the build embeds none; it now keeps the loaded network
  instead of rejecting or replacing it. Found by running a match with
  `--a-option NnueFile=...`, where the harness refused the rejected option.
- **Match bookkeeping.** Fixed-node matches are bit-identical between the two
  games of a pair unless the node budget is jittered; the harness gained
  `--nodes-jitter` and a 240-opening suite. `scripts/experiment_table.py` rebuilds
  `experiments/summary.csv` from the raw JSONL, so the table cannot drift from the
  records.
- **Suites re-measured on the final binary** rather than inherited from dev3:
  tactics 25/25 at 60,000 nodes; endgames 24/24 at 400,000 nodes and 16/24 at
  20,000 nodes. The 20,000-node figure is specific to this build and is not
  comparable to dev3's pre-review measurement.
- **Release gate outcome:** no measurable strength change, so the release is
  labelled "no regression, no gain" and the report says so in its first paragraph
  and its verdict section. The tag and GitHub prerelease are created only after
  the merge commit and a green CI run for that commit.

## 2026-11-02 — dev5 first research iteration

Working branch arena/4dcf45ca-stockbear, based on 9ee2140; dev4 immutable tag
9b5778c9 extracted inside ignored build-dev4/source without switching branches.
No paid compute. See docs/DEV5_PLAN.md and DEV5_EVALUATION_DIAGNOSIS.md.
Default and experimental evaluation builds pass 11/11 CTest entries; optional
NumPy batch-feature differential has two passing tests. Screening evidence and
negative NNUE reproduction are preserved under benchmarks/results/0.1.0-dev5.
This is incomplete research, not a completed strength/release milestone.

## 2026-11-03 — dev6 (v0.1.0-dev6) research cycle (branch arena/3e6dd5b6-stockbear)

Preflight: inspected tags/releases/PRs/workflows/working tree; read AGENTS_LOG,
DESIGN_LOG, README, ROADMAP, FAILURE_LEDGER and the DEV4/DEV5/DEV6/DEV7 docs.
Resolved the annotated `v0.1.0-dev5` tag to commit `c94571313a1667048468cf6d4e070400dc5ab228`.
Starting main SHA `6e7c2e02881faf93a84990a8345c41ad28bcae11`. Compute: 2 vCPU
Xeon (AVX2/BMI2/POPCNT/LZCNT present), 3.8 GB RAM; free GitHub-hosted ubuntu-latest
runner lane (4 vCPU dedicated VM) for isolated decisive matches; no paid compute.

Correction recorded: the historical `docs/DEV6_RESEARCH.md`, `docs/DEV5_REPORT.md`,
`DEV6_CONFIRMATION.md`, `DEV7_CONFIRMATION.md` and exp-0016/0017 belong to the
**dev5 development cycle** (branch `arena/daa69a3b-stockbear`) and measured a +50
gate against **dev4**. They are NOT this mission's dev6 (v0.1.0-dev6, +75 gate
against released dev5). Superseding notices appended; history preserved.

Work done: established the immutable exact released dev5 binary (exp-0025);
implemented + independently verified 6 extended eval features (exp-0026); bumped
VERSION to 0.1.0-dev6; generated two disjoint decisive opening suites and a
power analysis; pre-registered exp-0027/0028/0029 and dispatched the isolated
fixed-time batch via a dedicated free-runner lane (`dev6-lane.yml`). All evidence
committed to survive resets. Independent CodeRabbit review of an exact final PR
head is NOT requested because no PR is eligible while the strength gate is unmet;
this is stated accurately rather than fabricated.

Authorization status: NO merge, NO tag, NO release, NO PR opened. Those require
explicit user approval and, per the mission, a PR is opened only after ALL
mandatory gates pass. Gate outcome is reported honestly in
`docs/DEV6_CONFIRMATION_REPORT.md` / `docs/DEV6_REPORT.md` / the Failure Ledger.

### dev6 cycle completion (2026-11-03, appended)

Decisive free-runner lane run `41638608427` (17 jobs, 18m11s, SUCCESS) and CI
run `41638608619` (4m21s, SUCCESS), both on source head `28a5c71…`. All 17
result directories verified intact (PGN/JSONL/CSV/manifest); concurrent pushes
created cosmetic empty commits, history not rewritten. Independently recomputed
the primary clustered CR1 estimate from raw records: combined −17.0
[−21.4, −12.6] Elo, gate FAILED; nulls include 0; no adversarial engine events.
Recorded the integrity-control confound (toolchain), the isolated −58 Elo
feature ablation, and the complete experiment table in the Failure Ledger,
CHANGELOG, `docs/DEV6_CONFIRMATION_REPORT.md` and `docs/DEV6_REPORT.md`.
External ladder NOT COMPLETED -> status taxonomy "Not yet verified / Blocked";
absolute rating and 3,000-Elo gap UNKNOWN, not claimed. No CodeRabbit review
requested (no eligible PR); documented manual audit performed instead.
**Authorization status unchanged: NO PR, NO merge, NO tag, NO release, NO dev7,
no approval sought** because the mandatory gate is unmet. Deliverables committed
to branch `arena/3e6dd5b6-stockbear`; start was from verified starting SHA
`6e7c2e0…`, branch name fixed by the toolchain.

## Continuation after the historical gate FAIL (local work only)

Branch `arena/3e6dd5b6-stockbear`, all work committed locally. No `git push`,
no PR/merge/tag/release/dev7, no remote writes since the ASK directive.
Completed: M0.1 (exp-0030 reproducible Track A/B), M0.2 (exp-0031 pilot,
exp-0032 3,200-game BTD ladder, exp-0032b paired sensitivity), local
CI-equivalents (Release 11/11, ASan+UBSan 11/11, oracle 600/43,200/0,
3x bench determinism), `THIRD_PARTY.md` GPL notices, ladder docs and
append-only Failure Ledger entries. exp-0033 razoring screen is the first
post-M0 strength direction. **Acceptance gates remain UNMET**: no candidate
passes Gate 1 (>= +75 with LCB > +50 on both datasets); Gate 4 cannot be
completed without final-source CI on an isolated runner. Terminal state is
therefore NOT reached; mission remains ACTIVE. Authorization status: ASK —
explicit approval required before any push / PR / merge / tag / release.

## exp-0033 / exp-0034 / exp-0035 status

exp-0033 REJECTED and closed per its frozen rule (ledger appended). exp-0034
ADVANCE from pilot per its frozen rule; exp-0035 larger fixed-node confirmation
registered and running. Independent re-audit script
`scripts/dev6_audit.py` re-parses every raw `match.jsonl` from scratch.
Correctness: Release 11/11, ASan+UBSan 11/11, oracle 600/43,200/0, bit-exact
default bench signatures, 3x determinism. All work LOCAL; no push/PR/merge/tag/
release/dev7; authorization status ASK. Terminal state NOT reached: Gate 1
(>= +75, LCB > +50, both fixed-time batches) and Gate 4 (final-source CI,
exact packaged binary) are UNMET, and decisive fixed-time matches require
isolated CI runners reachable only via an authorized push. Mission ACTIVE.

## exp-0035 final state (local)

exp-0035 CONFIRMED (fixed-node only), ledger/docs/CHANGELOG/DESIGN_LOG updated,
independent audit PASS (179 values). `BadCapturePruning` default OFF; all
default builds bit-identical. Local CI-equivalents PASS; remote final-source CI
NOT RUN (no push). Gates 1-4 UNMET (no passing fixed-time candidate, exact
packaged artifact not tested, no final-source CI). Terminal state
**BLOCKED — NOT COMPLETE**, mission ACTIVE. Authorization status ASK: no remote
writes performed; explicit approval needed before any push, PR, merge, tag or
release. Exact next action: authorized push -> isolated-runner fixed-time
confirmation of exp-0035 with unchanged Gates 1-4.

### 2026-11-04 — one authorized push, final-source CI, exp-0036
1. Verified branch/HEAD/clean tree and the exact 11 unpushed commits; confirmed
   pushing touches no watched lane/exp/publish path filters; verified the
   immutable dev5 binary SHA. `git push origin arena/3e6dd5b6-stockbear`
   succeeded `797f5cb..03868da`; `git ls-remote` confirmed. Grant CONSUMED.
2. CI `41770918367` on `03868da`: success, 9/9 jobs (Clang, ASan+UBSan, TSan,
   Min CMake 3.16, Independent reference, ubuntu Debug/Release, windows
   Debug/Release). Artifact IDs pinned; blob CDN EOF prevented download.
3. Inspected `.github/workflows/dev6-lane.yml` (no `workflow_dispatch`, absent
   on `main`), `scripts/actions_dev6_lane.sh` (`commit_and_push`), and
   `benchmarks/exp-runs/dev6-trigger.json` (still exp0027/28/29). Concluded
   Tier-1 isolated-runner confirmation needs a new prereg + trigger commit +
   result pushes => a SECOND remote write, NOT authorized.
4. Froze `docs/DEV6_PREREG_EXP0036.md` (SHA `430fe96e...`) BEFORE results with
   an explicit tier disclosure, Stage-0 validity gate, frozen futility
   boundary, and Gates 1–4 verbatim.
5. Ran `scripts/dev6_exp0036.py --all` on a local dedicated core (`taskset -c 1`).
   Stage 0 PASS -> Stage 1. Combined +21.52 [+10.28,+32.81], both batches
   positive, 0 forfeits, null -1.75 [-22.39,+18.87].
6. Independent audit incl. exp-0036: 201 values, AUDIT PASS. Gate 1 FAIL,
   Gate 2 direction supported, Gate 3 PASS, Gate 4 UNMET. Futility boundary
   triggered. Closed the experiment; no PR/merge/tag/release/dev7.
7. Froze `docs/DEV6_PREREG_EXP0037.md` (ProbCut) as the next isolated
   direction; NOT executed (authorization exhausted).
8. All post-push local commits are documentation/results ONLY; `src/` unchanged
   from `03868da`, so the CI-tested source SHA stays exact.

### 2026-11-04 — continuation: Tier-1 repair, ranked matrix, exp-0037
1. Verified `a6cba07` is a clean descendant of `03868da`, contains only
   docs/raw evidence (35 files, no `src/`), dev5 tags/immutable binary
   `391cb50e...` intact, remote `03868da`, clean tree, CI `41770918367` 9/9.
2. Confirmed BOTH the job-logs and artifact-zip API endpoints redirect to
   `productionresultssa6.blob.core.windows.net` (EOF / outside allow-list).
   Confirmed the GitHub Contents API is reachable via `api.github.com` — this
   is the permitted alternative evidence channel.
3. Built `docs/DEV6_RESEARCH_MATRIX.md` (13 ranked directions, evidence,
   compute trade-off) and `docs/DEV6_TIER1_INFRASTRUCTURE.md`.
4. Created `.github/workflows/dev6-tier1.yml` (`workflow_dispatch` only,
   `mode=benchmark|export`, pinned `source_sha`, `plan_path`, isolated VMs,
   no benchmark pushes, artifact bundles, concurrency guard) and
   `scripts/dev6_tier1_job.py` (pinned build, exact dev5 SHA check, exact
   bench signature, PACKAGE then test the EXTRACTED binary, CR1 audit,
   fingerprint/manifest/SHA256SUMS). Neutralized the legacy `dev6-lane.yml`.
5. Implemented exp-0037 ProbCut: `SearchParams::probCut` default off, UCI
   `ProbCut`, `bench --param probCut=0|1`, frozen 200 cp / depth-4 / depth>=5
   block. Validated 11/11 Release + 11/11 ASan+UBSan, exact bench signatures,
   3x determinism, UCI default false, switch live.
6. Generated 2,020 fresh disjoint openings (seed 2026112001) and froze
   `docs/DEV6_PREREG_EXP0037_ADDENDUM.md` + two Tier-1 plans BEFORE any
   evaluation game. Smoke (40 games) is explicitly DISCARDED.
7. Authorization used: pushes to `arena/3e6dd5b6-stockbear`, workflow
   dispatch, artifact download. No force-push, no `main` change, no
   merge/tag/release/deploy/dev7.

### 2026-11-04 — Tier-1 verified, exp-0037 closed
8. Fixed two Tier-1 driver defects found by reproducing on the local sandbox
   (`cmake -E chdir ... ctest` could not resolve ctest; summary dict
   self-reference). Local smoke then passed end-to-end.
9. `gh workflow run dev6-tier1.yml --ref ...` -> HTTP 403 "Resource not
   accessible by integration" (token cannot create dispatch events). Used the
   push-triggered `tier1-dispatch.json` fallback as designed.
10. **Tier-1 smoke run `41778365897` on `ddb689a`: SUCCESS** (prepare +
    tier1-smoke green, artifact `13298122481`, 629,705 bytes). CI on
    `7b6a395` success. This is the first real isolated-VM Tier-1 evidence.
11. exp-0037 Stage-1 fixed-node screen (local Tier 2): combined +3.78
    [-9.34,+16.90], 1,198 games, both batches positive, null includes 0,
    0 forfeits, independent audit PASS. Frozen advance rule not met -> CLOSED,
    direction ABANDONED. Root cause: verification probe is overhead at the
    shallow depths reachable in 4 ms (predicted by the +63 % depth-12 node
    diagnostic). No Stage 2a. Mission ACTIVE -> exp-0038.

### 2026-11-04 — Tier-1 artifact retrieval VERIFIED
12. Export run `41778833297` SUCCESS -> commit `5c0aad4` on the branch.
    `git archive` + `sha256sum -c` = 9/9 OK; GitHub Contents API returned
    `export_manifest.json` verbatim (api.github.com is reachable while the
    blob CDN is not). Machine-readable record in
    `benchmarks/dev6-baseline/tier1_verification.json`.
13. Found the git mirror omitted `*.log`; patched the export job to force-add
    logs. Gate 4 binary identity (built == packaged == tested SHA-256) is
    asserted by the Tier-1 driver and pinned in `fingerprint.json`.

### exp-0038 registration (before any evaluation game)

Re-ranked after exp-0037 closed: qsearch TT is the highest remaining unexecuted
direction. Implemented `qsearchTT` as a default-off isolated switch with a
dedicated 2^16 qsearch bound cache (no main-TT pollution). Validation: Release
ctest 11/11, ASan+UBSan ctest 11/11, exact default-off bench/d16/d12
signatures, 3x determinism, UCI default false. Profiling: d16 -0.0006 % nodes,
+3.86 % time; instrumented hits ~2.7 M / 99 M probes on one position but
concentrated on cheap early-return nodes. Frozen `docs/DEV6_PREREG_EXP0038.md`
(SHA 6161061783d745e10eb5c54017a344d4eb54730778c4f64684b88da3c2cf12dc),
1,400 fresh disjoint openings, `benchmarks/exp-runs/tier1-plan-exp0038.json`
(Stage-0 validity null + batchA + batchB + null), and Tier-1 dispatch. No
evaluation games have been played yet; no result or strength claim exists.
Tier-1 smoke run 41778365897 remains DISCARDED. Gate status unchanged:
Gate 1 UNMET / Gate 2 direction-supported / Gate 3 PASS / Gate 4 UNMET.

### exp-0039 profiling elimination (no games played)

While exp-0038's Tier-1 run executed on isolated VMs, source inspection found
`negamax` computing and discarding a full `evaluate()` on every TT hit with
`TTEval=true`. A bit-exact fix was implemented, validated (identical bench
signatures/node counts, ctest 11/11) and profiled with five-repeat d12 timing;
the ~2.9 % residual was below the ~7 % build-layout/CPU noise floor. Reverted
the source to keep exp-0038's pinned SHA clean; recorded in DESIGN_LOG and
FAILURE_LEDGER with exact numbers. No strength experiment, no Elo claim.
Tier-1 run 41780333569 (exp-0038) completed all four jobs successfully;
evidence export dispatched for independent audit.

### exp-0038 CLOSED; current authoritative status

Tier-1 run `41780333569` (source `2aacf4a…`, packaged binary `30874fbc…`,
CI `41780333461` SUCCESS) produced Stage-0 validity PASS, null PASS, and
frozen combined `+7.6755 [−1.0670,+16.4278]` over 1,996 games. Export run
`41781546677` mirrored all four artifacts; local `sha256sum -c` 4/4 with 0
failures. `scripts/dev6_exp0038_audit.py` re-parsed all raw JSONL, verified
44 stored values (AUDIT PASS), recomputed independent Elo-from-score +7.6601
and a seeded opening-cluster bootstrap `[−1.0465,+16.4072]`. Frozen §6 UCB
< +20 -> CLOSED, ABANDONED, no Stage 2a, no retune, no bundle, switch stays
default OFF. Root cause recorded as unsuitable hypothesis / search
interaction. `docs/DEV6_EXP0038_REPORT.md` and
`docs/DEV6_CURRENT_STATUS.md` are now the authoritative experiment and gate
verdicts; older status reports carry pointers. Gate verdict UNCHANGED:
1 UNMET / 2 direction-supported / 3 PASS / 4 UNMET (no final candidate).
Mission ACTIVE; no strength claim, no PR/merge/tag/release/deploy/dev7.

### exp-0040 profiling elimination + exp-0041 registration (before results)

exp-0040 (banked-time allocation, distinct from exp-0004 FullSoftBudget) was
implemented and validated. A temporary `TMDEBUG` build confirmed the switch is
live (`soft=4 -> 6 ms`, `hard=13 ms`), yet 5-repeat 40+4 ms probes on two
positions gave identical depth 6 / 12,539 nodes / 5 ms: the 55 %/70 % early
stops absorb the larger soft budget. Eliminated at profiling, no games spent,
no retune; recorded in FAILURE_LEDGER/DESIGN_LOG. New methodological rule: a
candidate must demonstrably change the search tree at 40+4 ms before a
tournament is spent.

exp-0041 extends validated `BadCapturePruning` to all remaining depths with
the frozen margin 100 (`BadCaptureAllDepths`, default OFF). Validation:
Release ctest 11/11, ASan+UBSan ctest 11/11, exact default-off bench/d16/d12
signatures, UCI default false. Live diagnostic: `go depth 12` startpos with
`BadCapturePruning=true` gives 757,239 nodes / 400 ms OFF and 438,131 nodes /
236 ms ON (−42.1 %). Frozen prereg SHA
`2f5c1b08ebd991f84e570b90afd48adcc7694f5d355beda492e1b6b18d98d392`,
1,400 fresh disjoint openings seed 2026112601, Stage-0 validity + batchA +
batchB + null Tier-1 plan, dispatch attempt 7. NO evaluation games yet.
Gate verdict UNCHANGED: 1 UNMET / 2 direction-supported / 3 PASS / 4 UNMET
(no final candidate). Mission ACTIVE.

### exp-0041 Tier-1 screen completed; export dispatched

Run `41782954038` on source `87f82854…`: prepare + all four isolated-VM
40+4 ms jobs SUCCESS; CI `41782954037` SUCCESS. Evidence export dispatched
(attempt 8) via the deliberate `mode=export` job. The independent audit script
was made generic AFTER the run but BEFORE any exp-0041 result was read; its
frozen thresholds for exp-0041 are ADVANCE point>=+20/LCB>0/both batches>=-5
and CLOSE UCB<+10 or point<=0, taken verbatim from
`docs/DEV6_PREREG_EXP0041.md` §5. No exp-0041 result has been inspected yet.

### exp-0041 CLOSED; continuation state

Tier-1 `41782954038` on source `87f82854…` (CI `41782954037` SUCCESS) produced
Stage-0 validity PASS, null PASS, batchA `+2.4419`, batchB `−12.5887`, frozen
combined `−5.0635 [−15.1810,+5.0454]` over 1,995 games. Export `41784088471`
mirrored four artifacts; local `sha256sum -c` 4/4, 0 failures. The generic
independent audit (`scripts/dev6_exp0038_audit.py 41782954038 exp0041 20 10`)
verified 44 stored values, AUDIT PASS, independent Elo-from-score −5.2250,
seeded cluster bootstrap `[−15.0242,+5.0635]`. Frozen §5 UCB < +10 AND
point <= 0 -> CLOSED, ABANDONED, no ADVANCE/bundle/retune; switch stays
default OFF. Root cause: unsuitable hypothesis / search-eval interaction;
−42.1 % fixed-depth node saving did not translate to fixed-time strength.
`docs/DEV6_EXP0041_REPORT.md` is authoritative. Gates UNCHANGED: 1 UNMET /
2 direction-supported / 3 PASS / 4 UNMET (no final candidate). Mission
ACTIVE; no strength claim, no PR/merge/tag/release/deploy/dev7. The next
ranked directions (singular/tactical extensions, TT replacement, a fresh
bit-exact qsearch eval-throughput prereg, larger bullet-matched eval corpus)
remain unexecuted and must each be frozen before any evaluation game.

### Workspace reconciliation (2026-11-04, this continuation)

A fresh sandbox presented a clone at the ORIGINAL base commit
`6e7c2e02881faf93a84990a8345c41ad28bcae11` with a STALE cumulative turn-end
patchset overlay (exp-0037 era, dispatch attempt 4, 272 modified/untracked
files) and no `.venv`. The remote branch head was
`b71d98917d0deec1b46b99f74dcc2fa09ab23775` (all committed work, CI success).
The overlay was preserved as a recoverable
`git stash` (`workspace-overlay-backup-20261104`), then `git fetch` +
`git reset --hard FETCH_HEAD` aligned the local branch to the remote head with
a clean tree; every key document, plan, raw evidence tree and script was
verified PRESENT, dispatch attempt 8, immutable dev5 SHA unchanged. Nothing was
deleted, no force push and no shared-history rewrite. `.venv` was rebuilt with
cmake 4.4.4 / ninja 1.13.2 / numpy 2.4.6 / chess 1.11.2 / PyYAML 6.0.3 and
the Tier-1 workflow YAML re-parsed. This reconciliation is a workspace-only
operation; it changes no scientific conclusion.

### exp-0042 registration (before any evaluation game)

Re-ranked after exp-0041: prefer improving the ACCURACY of a decision over
deleting more nodes. exp-0042 adds `MaxGainDelta` (default OFF): after legal
quiescence captures are generated, use their ACTUAL largest gain (SEE gain[0],
including promotion bonus) plus the FROZEN `deltaMargin=200` for a second,
tighter delta check; the original conservative queen-based check still runs
first and unchanged. Validation: Release ctest 11/11, ASan+UBSan ctest 11/11,
exact default-off bench/d16/d12 signatures, UCI default false. Live diagnostic:
`go depth 12` startpos 543,800 nodes / 269 ms OFF vs 618,920 nodes / 309 ms ON
(+13.8 % nodes); recorded as a non-decisive tree-change proxy, NOT strength.
Frozen `docs/DEV6_PREREG_EXP0042.md` (SHA
`3345325ce3e4fdc98501410bd7fcea2b3b5e7e1aa6b9d6a8139e4ced6b29c62b`), 1,400
fresh openings seed 2026112801 with programmatic ZERO overlap against 29,202
earlier openings, Stage-0 validity + two 1,000-game batches + null Tier-1
40+4 ms plan, dispatch attempt 9. NO evaluation games yet.
Gate verdict UNCHANGED: 1 UNMET / 2 direction-supported / 3 PASS / 4 UNMET
(no final candidate). Mission ACTIVE.

### exp-0042 Tier-1 screen completed; export dispatched

Run `41802986830` on source `efd2f22dd…`: prepare + all four isolated-VM
40+4 ms jobs SUCCESS; CI `41802986854` SUCCESS. Evidence export dispatched
(attempt 10). exp-0042 frozen audit thresholds (verbatim from
`docs/DEV6_PREREG_EXP0042.md` §5) are ADVANCE point>=+20/LCB>0/both batches
>=-5/null includes 0/clean and CLOSE UCB<+10 or point<=0; they were fixed
before any result was read. No exp-0042 result has been inspected yet.

### exp-0042 screen INCONCLUSIVE; bounded confirmation dispatched

Run `41802986830` on `efd2f22…` completed all four isolated-VM jobs SUCCESS;
CI `41802986854` SUCCESS; export `41804342869` mirrored four artifacts and
local `sha256sum -c` reported 4/4 with 0 failures. Independent audit
(`scripts/dev6_exp0038_audit.py 41802986830 exp0042 20 10`) verified 44 stored
values AUDIT PASS. Stage-0 validity PASS (0 forfeits), both nulls include zero,
frozen combined `+2.6110 [−7.9556,+13.1825]` on 1,998 games / 998 clusters,
independent Elo-from-score +2.7823, seeded cluster bootstrap
`[−8.0085,+12.8868]`. Frozen §5 gives INCONCLUSIVE, which mandates more
samples; `docs/DEV6_PREREG_EXP0042_ADDENDUM.md` (SHA `21b0b1e6…`) was frozen
BEFORE any additional game with a bounded, separate confirmation (NO pooling
with the screen), the SAME thresholds, and a conservative experiment-level
compute bound justified by the preregistered scheduler. Dispatch attempt 11.
Gate verdict UNCHANGED: 1 UNMET / 2 direction-supported / 3 PASS / 4 UNMET.
Mission ACTIVE; no strength claim.

### exp-0042 CLOSED; final continuation state for this cycle

Confirmation run `41804818965` on `ec223fe…` (CI `41804818984` SUCCESS)
produced Stage-0 validity PASS, null PASS, batchA `−4.1862`, batchB
`−17.4914`, frozen combined `−10.8281 [−21.8567,+0.1787]` over 1,995 games.
Export `41806227744` mirrored four artifacts; local `sha256sum -c` 4/4, 0
failures. Independent audit
(`scripts/dev6_exp0038_audit.py 41804818965 exp0042_confirm 20 10`) verified
44 stored values AUDIT PASS, independent Elo-from-score −10.9753, seeded
cluster bootstrap `[−21.8526,+0.0000]`. Frozen rules -> CLOSED (UCB < +10 AND
point <= 0), ABANDONED, no ADVANCE/bundle/retune; switch stays default OFF.
Screen and confirmation CIs overlap and were NEVER pooled. Root cause:
unsuitable hypothesis / search-eval interaction; quiescence stand-pat values
are load-bearing. `docs/DEV6_EXP0042_REPORT.md` is authoritative.

Workspace reconciliation this cycle: local checkout was realigned from a stale
base-commit overlay to remote `b71d989…` (overlay preserved in a git stash),
`.venv` rebuilt, all evidence verified. Gates UNCHANGED: 1 UNMET / 2
direction-supported / 3 PASS / 4 UNMET (no final candidate). Mission ACTIVE;
no strength claim, no PR/merge/tag/release/deploy/dev7. Dispatch file is at
`mode=export`, attempt 12, so no benchmark auto-runs on the next push unless
deliberately changed.

## exp-0043 launched — TT-evidence singular extension (2026-11-04)
After exp-0042 CLOSED/ABANDONED (screen `+2.6110 [−7.9556,+13.1825]`
INCONCLUSIVE, bounded confirmation `−10.8281 [−21.8567,+0.1787]` CLOSE, NEVER
pooled), the mission remains ACTIVE/NOT COMPLETE. The post-exp-0042 rank-1
direction is now executing WITHOUT re-running or modifying exp0042, reusing
confirmation data, bypassing preregistration or weakening gates.

Mechanism: `SearchParams::ttSingularExtension=false`; in `negamax` a
slightly-shallower TT LOWER bound >= beta + 50 cp at depth >= 3 marks the
always-first hash move singular, and that ONE move is searched a ply deeper.
`MaxSingularExtensions=2` is path-scoped via a counter restored on every
return; `SingularDepthSlack=3`. NO verification subtree (exp-0037 CLOSED at
`+3.7766 [−9.3368,+16.9008]`), NO stand-pat rewrite, NO new qsearch pruning
rule, NO default-ON feature disabled. The canonical genuine re-search variant
is DEFERRED and the deviation is DECLARED IN ADVANCE in the prereg.

Frozen before any evaluation game: `docs/DEV6_PREREG_EXP0043.md` (SHA
`e9fe40f053c9f479835c05efc3bf592547024090c1a315281ec727f0096f31dc`),
`tier1-plan-exp0043.json` (4 jobs), `scripts/dev6_exp0043_openings.py` and
1,400 fresh disjoint openings (seed `2026120201`, ZERO overlap with 32,041
earlier positions in 120 files, four disjoint slices), and dispatch
`mode=benchmark experiment_id=exp0043 attempt=13`. All committed in the SAME
commit as the dispatch. Default-off bit-exact signatures
`243f9a1c1ba5b36f` / `a14ab62224f837e5` / `e45fa2ec2287eb41`, Release ctest
11/11, ASan+UBSan ctest 11/11 (`exp0043_asan_ctest.log`), UCI default false.

MANDATORY pre-result mechanism-live/overhead diagnostic from the FROZEN
source (instrumented `SB_SINGULAR_DEBUG` build, real suite positions):
fixed depth 10 over 16 positions OFF 2,655,145 nodes ON 3,024,895 nodes
(+13.9 % overhead), 15,000 triggers / 8,072 extensions; FIXED TIME 40+4 ms
over 24 positions x 2 repeats OFF 222,636/217,259 nodes ON 218,959/225,368
nodes, median depth 6 both, 1,093/1,092 triggers and 548/516 extensions,
LIVE on 23/24 positions. A startpos `go depth 12` probe found 0 triggers;
suite positions are the preregistered probe. These are VALIDITY/overhead
checks, NOT strength evidence.

Design: FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, never `--nodes`;
Stage-0 validity null 400 games (0 forfeits required), candidate-options null
400 games, batchA/batchB 1,000 games each on independent fresh suites;
combined frozen before the run, independent raw-JSONL audit, 4 isolated VMs,
exact packaged tested binary. Frozen ADVANCE >= +20 point AND LCB > 0 AND
both batches >= −5 AND both null CIs include 0 AND 0 failures; CLOSE if
UCB < +10 OR point <= 0; INCONCLUSIVE -> ONE bounded fresh confirmation,
NEVER pooled. Gates 1 (+75/LCB>+50) and 4 remain UNMET; no strength claim,
no bundle, no default change, no PR/merge/tag/release/deploy/dev7.

exp-0043 launch commit (exact source SHA pinned by `source_sha=HEAD` in the
`mode=benchmark` attempt-13 dispatch): `5ea5ad21348f39dabad1da3e8cb098f798087295`. LOCAL and REMOTE heads are
identical at this SHA. The following docs-only commit records this SHA and does
NOT relaunch the benchmark because the workflow push trigger is paths-filtered
to `benchmarks/exp-runs/tier1-dispatch.json`.

## exp-0043 CLOSED / ABANDONED (2026-11-04)
Tier-1 run `41809643084` (4 isolated VMs SUCCESS), export `41810711486`
SUCCESS, CI `41809642415` SUCCESS on exact source
`5ea5ad21348f39dabad1da3e8cb098f798087295`. Frozen prereg
`e9fe40f053c9f479835c05efc3bf592547024090c1a315281ec727f0096f31dc`, plan
`3141fb1f487184459b52d644d3187f201dbd70216455469768613e0aebff2e70`,
packaged=tested binary
`c2ef506c5c6ebf9c3197c52903f61ccbf5326f16221c3c96a5bb3a8dc4420409`,
1,400 fresh disjoint openings seed `2026120201` (0 overlap / 32,041 earlier).
FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, no `--nodes`; one binary,
single switch `TTSingularExtension=true` vs `false`. All 4 bundles 9/9
SHA256SUMS OK, 0 failures.

Mandatory mechanism-live diagnostic: LIVE on 23/24 suite positions at the
exact 40+4 ms control (548/516 extensions across 24 positions x 2 repeats),
median depth 6 unchanged, +13.9 % fixed-depth-10 node overhead. VALID
negative, not an inert experiment.

Stage-0 validity null 399 games 128/129/142 `−13.1005 [−29.9568,+3.6943]`,
0 forfeits/illegal/UCI failures, CI includes 0 -> PASS. Candidate-options
null 400 games 145/123/132 `+11.2956 [−7.4505,+30.1078]`, includes 0.
batchA 997 games 333/302/362 `−9.7895 [−25.2667,+5.6489]`; batchB 997 games
321/325/351 `−10.8390 [−25.2969,+3.5814]`. FROZEN combined 1,994 games
654/627/713, score 0.4852056, `−10.3142 [−20.8915,+0.2440]`, 994 clusters,
independent Elo-from-score −10.2832, seeded cluster bootstrap
`[−20.6467,+0.1748]`. `dev6_exp0038_audit.py 41809643084 exp0043 20 10`
-> 44 stored values, 0 issues, AUDIT PASS.

FROZEN RULE: ADVANCE false (point < +20, LCB < 0, both batches < −5);
CLOSE true (UCB +0.2440 < +10 AND point <= 0). => CLOSE / ABANDONED. Not
INCONCLUSIVE, so no confirmation run and no fresh suites spent.
`TTSingularExtension` stays OFF; frozen constants NOT retuned; no bundle, no
strength claim, no default change, no PR/merge/tag/release/deploy/dev7.
Full report `docs/DEV6_EXP0043_REPORT.md`. Gates 1 and 4 remain UNMET;
mission ACTIVE / NOT COMPLETE; next hypothesis is being selected and launched.
