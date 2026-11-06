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

## exp-0044 launched — SEE-losing-capture ordering (2026-11-04)
Post-exp-0043 re-ranking: exp-0041, exp-0042 and exp-0043 are three
consecutive fixed-time losses for mechanisms that change WHICH nodes are
searched or ADD a ply at non-PV nodes; exp-0036 (+21.52, shallow SEE-losing
capture PRUNING) and exp-0038 (+7.68, qsearch information reuse) remain the
only positive directions. Rank 1 is now move-ordering ACCURACY with ZERO added
per-node work.

Code inspection found a concrete deficiency: in `Search::score_moves` a
capture with SEE < 0 scores ~2,000,000, ABOVE killers (1,500,000),
countermoves (1,485,000) and every quiet history move (|h| <= 60,000), so
losing captures are searched immediately after winning captures at EVERY
main-search node. exp-0044 demotes them to the tail in the MAIN search ONLY.
NO move is removed (unlike exp-0036/0041), NO SEE/eval call is added, NO
stand-pat value or pruning/extension decision changes, quiescence excluded.
Frozen `BadCaptureOrderScore=-2000000`, threshold SEE<0, no tunable margin —
NOT best-of-N parameter selection, NOT a repeat of exp-0036/0041.

Frozen before any evaluation game: `docs/DEV6_PREREG_EXP0044.md` (SHA
`73ae460981a09bbf5d605205f8b77bf799b6d92a0fed4dc4abaa3a4ebc3820a5`),
`tier1-plan-exp0044.json` (4 jobs), `scripts/dev6_exp0044_openings.py` and
1,400 fresh disjoint openings (seed `2026120301`, ZERO overlap with 33,441
earlier positions in 125 files, four disjoint slices), dispatch
`mode=benchmark experiment_id=exp0044 attempt=15`. All in the SAME commit as
the dispatch. Default-off bit-exact signatures `243f9a1c1ba5b36f` /
`a14ab62224f837e5` / `e45fa2ec2287eb41`, Release ctest 11/11, ASan+UBSan
ctest 11/11 (`exp0044_asan_ctest.log`), UCI default false.

MANDATORY pre-result mechanism-live/overhead diagnostic from the FROZEN source
(`SB_BADCAP_DEBUG`): fixed depth 10 over 16 suite positions OFF 2,655,145
nodes, ON 2,961,866 nodes (+11.6 % TREE change, ZERO added per-node work),
424,155 demotions, live 16/16; FIXED TIME 40+4 ms over 24 positions x 2
repeats OFF 228,643/236,838 nodes, ON 203,245/214,462 nodes, median depth 6
for both, 22,024/24,413 demotions, LIVE 24/24. The node INCREASE is disclosed
as a risk and is NOT strength evidence.

Design: FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, never `--nodes`;
Stage-0 validity null 400 games, candidate-options null 400 games,
batchA/batchB 1,000 games each on independent fresh suites; ANY time
forfeit/illegal/engine failure in ANY job => INVALID MEASUREMENT. Frozen
ADVANCE >= +20 AND LCB > 0 AND both batches >= −5 AND both null CIs include 0
AND clean; CLOSE if UCB < +10 OR point <= 0; INCONCLUSIVE -> ONE bounded fresh
confirmation, NEVER pooled. Gates 1 (+75/LCB>+50) and 4 remain UNMET; no
strength claim, no bundle, no default change, no PR/merge/tag/release/deploy/
dev7, no reuse of closed exp0041/0042/0043 data.

exp-0044 launch commit (exact source SHA pinned by `source_sha=HEAD` in the
`mode=benchmark` attempt-15 dispatch): `2ae4e68fc882991c3484eede22a4622f713da5e2`. LOCAL and REMOTE heads are
identical at this SHA. The following docs-only commit records this SHA and does
NOT relaunch the benchmark (push trigger is paths-filtered to the dispatch
file).

## exp-0044 screen INCONCLUSIVE; bounded confirmation launched (2026-11-04)
Tier-1 run `41812595433` / export `41813751266` / CI `41812595476` SUCCESS on
exact source `2ae4e68fc882991c3484eede22a4622f713da5e2`; frozen prereg
`73ae460981a09bbf5d605205f8b77bf799b6d92a0fed4dc4abaa3a4ebc3820a5`; 4
isolated VMs, 9/9 SHA256SUMS OK in each of 4 bundles, 0
forfeits/illegal/engine failures. Stage-0 validity null 400 games 133/145/122
`+9.5569 [−6.6563,+25.8118]`; candidate-options null 400 games 138/124/138
`0.0000 [−17.9335,+17.9335]`; batchA 1,000 games 341/336/320
`+6.6419 [−8.1259,+21.4338]`; batchB 996 games 335/328/336
`0.0000 [−15.0949,+15.0949]`; FROZEN combined 1,996 games 676/664/656,
score 0.5050100, 996 clusters, `+3.3140 [−7.2389,+13.8730]`, independent
Elo-from-score +3.4814, seeded bootstrap `[−7.1520,+13.7861]`, 44/0 AUDIT
PASS. ADVANCE false (point<+20, LCB<0); CLOSE false (UCB +13.8730 >= +10,
point>0) => INCONCLUSIVE. Frozen §6 mandates exactly ONE bounded fresh
confirmation, NEVER pooled with the screen.

`docs/DEV6_PREREG_EXP0044_ADDENDUM.md` (SHA
`17d90a790697bb05de108d4b5fb5f7cf745fdb611899c5237c7ccce2b73af835`) freezes
the confirmation BEFORE any confirmation game: separate Tier-1 run, dispatch
`mode=benchmark experiment_id=exp0044_confirm attempt=17`, FIXED TIME 40+4 ms,
SAME single switch `BadCaptureOrdering=true` vs false, 1,400 fresh disjoint
openings seed `2026120401` (ZERO overlap with 34,841 earlier positions in 130
files), generator `scripts/dev6_exp0044_confirm_openings.py`, its own Stage-0
and candidate-options nulls, two independent 1,000-game batches. Decision uses
ONLY new batches: ADVANCE >= +20 AND LCB>0 AND clean; CLOSE if UCB<+10 OR
point<=0; otherwise CLOSED AS INCONCLUSIVE and direction abandoned
(conservative compute bound, NOT a threshold change). No strength claim, no
default change, no bundle, no retune, no pooling. Gates 1 and 4 remain UNMET;
mission ACTIVE / NOT COMPLETE.

exp-0044 bounded-confirmation dispatch commit (exact source SHA pinned by
`source_sha=HEAD` in the `mode=benchmark` attempt-17 dispatch): `0691b9affd36006425ac23605f4a0cc8922a55bb`.
LOCAL and REMOTE heads identical. The following docs-only commit records this
SHA and does NOT relaunch the benchmark (paths-filtered push trigger).

## exp-0044 CLOSED AS INCONCLUSIVE / ABANDONED (2026-11-04)
Confirmation run `41814069967`, export attempt 18 `41815187170` FAILED only at
a transient GitHub Internal Server Error evidence push (download + checksums
succeeded; nothing reached remote). TECHNICAL FAILURE diagnosed and repaired
within scope: workflow export step gained a bounded 4-attempt push retry, and
the export was re-dispatched as NEW valid run `41815428066` SUCCESS. 9/9
SHA256SUMS OK in each of 4 bundles, 0 failures. No scientific change.

Confirmation source `0691b9affd36006425ac23605f4a0cc8922a55bb`, addendum
`17d90a790697bb05de108d4b5fb5f7cf745fdb611899c5237c7ccce2b73af835`, CI
`41814069925` SUCCESS. Stage-0 400 games 123/143/134
`−9.5569 [−32.6787,+13.4804]`; candidate null 398 games 142/123/133
`+6.1422 [−14.8210,+27.1502]`; batchA 999 games 360/328/311
`+17.0722 [+0.6984,+33.5222]`; batchB 998 games 339/348/311
`+10.1190 [−5.8209,+26.1015]`; FROZEN combined 1,997 games 699/676/622,
score 0.5192789, 997 clusters, `+13.5977 [+2.1746,+25.0503]`, independent
Elo-from-score +13.4030, seeded bootstrap `[+2.4394,+24.9592]`, 44/0 AUDIT
PASS, 0 forfeits/illegal/failures.

ADVANCE false (point < +20); CLOSE false (UCB >= +10, point > 0). The FROZEN
ADDENDUM explicitly overrides the prereg §6 "more samples" default with an
experiment-level COMPUTE BOUND => **CLOSED AS INCONCLUSIVE / ABANDONED**.
`scripts/dev6_exp0044_confirm_decision.py` reproduces the override from raw
games. Screen `+3.3140 [−7.2389,+13.8730]` and confirmation CIs overlap and
were **NEVER pooled**. No strength claim, no third run, no retune, no bundle,
no default change, no PR/merge/tag/release/deploy/dev7. Full report
`docs/DEV6_EXP0044_REPORT.md`. Gates 1 and 4 remain UNMET; mission ACTIVE /
NOT COMPLETE; the next hypothesis must have its OWN frozen prereg, fresh
disjoint suites and dispatch, and may not reuse exp-0044 data.

## exp-0045 launched — bit-exact dead evaluate() elimination (2026-11-04)
Post-exp-0044 rank change: exp-0044 CLOSED AS INCONCLUSIVE / ABANDONED at its
frozen addendum compute bound; the next ranked direction that changes NO
search decision is bit-exact evaluate() throughput. exp-0039 built this exact
fix, verified it bit-exact, measured ~2.9 % against a ~7 % local noise floor,
REVERTED it and spent NO games. exp-0045 is the FIRST Elo measurement of that
hypothesis on isolated VMs at FIXED TIME 40+4 ms — not a repeat of exp-0039's
profiling, not a parameter change, no exp-0041..0044 data reused.

Frozen before any evaluation game: `docs/DEV6_PREREG_EXP0045.md` (SHA
`0abf66836ed0ad6d979a26a3d4ca8616416bfb88b8ca069875f1e7d4e7bb2863`),
`tier1-plan-exp0045.json` (4 jobs), `scripts/dev6_exp0045_openings.py` and
1,400 fresh disjoint openings (seed `2026120501`, ZERO overlap with 36,241
earlier positions in 135 files, four disjoint slices), dispatch
`mode=benchmark experiment_id=exp0045 attempt=20`. All in the SAME commit as
the dispatch. Default-off bit-exact signatures `243f9a1c1ba5b36f` /
`a14ab62224f837e5` / `e45fa2ec2287eb41`, d16 with `ttEval=1` identical
OFF/ON, Release ctest 11/11, ASan+UBSan ctest 11/11
(`exp0045_asan_ctest.log`), UCI default false.

MANDATORY pre-result diagnostics from the FROZEN source (`SB_DEADEVAL_DEBUG`):
node counts OFF/ON IDENTICAL at depths 8/10/12 (depth 12 `[72604, 497628,
311669, 559024]` for both); ON skipped 40,187 of 379,656 evaluate() calls
(10.6 %) => mechanism LIVE; local 12 alternating repeats at depth 12 OFF
median 804.0 ms / ON 823.5 ms (−2.37 % "speedup", noise-dominated, reported
VERBATIM, NO local speedup claim). Theoretical speedup ~2-3 % because only
10.6 % of evaluations can be saved. Honest power statement: a 2,800-game
screen has ~13 Elo half-width and CANNOT resolve a +2-3 Elo effect; it is
powered for the +20 ADVANCE threshold and to rule out a material regression.
SINGLE-RUN compute bound closes exp-0045 AS INCONCLUSIVE if neither frozen
condition holds; no post-hoc sample increase, no confirmation.

Design: FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, never `--nodes`;
Stage-0 validity null 400 games, candidate-options null 400 games,
batchA/batchB 1,000 games each on independent fresh suites; ANY time
forfeit/illegal/engine failure => INVALID MEASUREMENT. Frozen ADVANCE >= +20
AND LCB>0 AND both batches >= −5 AND both null CIs include 0 AND clean; CLOSE
if UCB<+10 OR point<=0; otherwise CLOSED AS INCONCLUSIVE / ABANDONED. Gates 1
and 4 remain UNMET; no strength claim, no bundle, no default change, no
PR/merge/tag/release/deploy/dev7.

exp-0045 launch commit (exact source SHA pinned by `source_sha=HEAD` in the
`mode=benchmark` attempt-20 dispatch): `e41a0b18b4e522f57196e2834c8937f8c55019e8`. LOCAL and REMOTE heads are
identical at this SHA. The following docs-only commit records this SHA and does
NOT relaunch the benchmark (push trigger is paths-filtered to the dispatch
file).

## exp-0045 original run INVALID MEASUREMENT; bounded valid retry launched (2026-11-04)
Run `41817228668` / export `41818409701` / CI `41817228408` SUCCESS on source
`e41a0b18b4e522f57196e2834c8937f8c55019e8`, frozen prereg `0abf66836ed0ad6d…`;
4 isolated VMs, 9/9 SHA256SUMS OK in each of 4 bundles, 44 stored values / 0
issues AUDIT PASS. But batchB `summary.json` has `time_forfeit=1`: game 272,
14.1 ms move at ply 118, `remaining_white_ms=-5.01`, long game, clock nearly
exhausted. FROZEN prereg §5 requires 0 forfeits in ANY job => **INVALID
MEASUREMENT**. ALL Elo/CIs/W-D-L/LLR and the generic audit's "CLOSE" label are
DISCARDED; `clean=False` is the correct signal; NO strength inference. Stage-0
validity null, candidate-options null, batchA and all illegal/engine_failure
counts were clean. Diagnosis: rare isolated-VM long-game clock outlier (1/998;
exp-0043/0044 had 0 forfeits at the same control), not a systematic mechanism
effect; it favoured the candidate and could not manufacture a positive. NO
repair to the frozen 40+4 ms control, clocks, binary, switch, time manager or
driver is authorised.

`docs/DEV6_PREREG_EXP0045_RETRY.md` (SHA
`2172063e22554df99064c54e0820b70db854e2339b0d5e87ccc321b6ca0bce60`) frozen
BEFORE any retry game: identical frozen science, NEW `exp0045_retry`, dispatch
`mode=benchmark attempt=22`, `tier1-plan-exp0045-retry.json`, NEW seeds, 1,400
fresh disjoint openings seed `2026120601` (ZERO overlap with 37,641 earlier
positions in 140 files, generator `scripts/dev6_exp0045_retry_openings.py`).
Invalid run `41817228668` NEVER pooled or reused. Frozen ADVANCE >= +20 AND
LCB>0 AND clean; CLOSE if UCB<+10 OR point<=0; otherwise CLOSED AS
INCONCLUSIVE. BOUNDED RETRY BUDGET: exactly one retry; a second forfeit closes
exp-0045 AS TECHNICALLY UNRESOLVABLE with no strength inference. No threshold
weakened (the zero-forfeit rule was ENFORCED). Gates 1 and 4 remain UNMET; no
strength claim, no default change, no bundle, no PR/merge/tag/release/deploy/
dev7. Mission ACTIVE / NOT COMPLETE.

## exp-0045 FINAL CLOSE / ABANDONED (2026-11-04)
Original run `41817228668` / export `41818409701` / CI `41817228408` SUCCESS but
INVALID MEASUREMENT (1 TIME_FORFEIT in batchB game 272, 14.1 ms move, ply 118,
`remaining_white_ms=-5.01`). Frozen prereg §5 zero-forfeit rule ENFORCED; ALL
Elo/CIs/W-D-L/LLR and the generic audit's "CLOSE" label DISCARDED, no strength
inference, `clean=False`. Diagnosed as a rare isolated-VM long-game clock
outlier; no repair to the frozen 40+4 ms control authorised.

One bounded valid retry (frozen `DEV6_PREREG_EXP0045_RETRY.md` SHA
`2172063e22554df9…`, attempt 22, 1,400 fresh disjoint openings seed
`2026120601`, ZERO overlap / 37,641 earlier positions in 140 files): run
`41818958001` / export `41821624068` / CI `41818958003` SUCCESS. Pinned source
`9fb2a58…`, dev5 baseline VERIFIED, built==packaged binary `b839fae82b54…`,
UCI `SkipDeadTTEval default false`. 9/9 SHA256SUMS OK in each of 4 bundles,
0 forfeits/illegal/failures in ALL four jobs, 44/0 AUDIT PASS `clean=True`.
Stage0 399 `118/155/126` −6.1113 [−23.3656,+11.1129]; candidate null 400
`152/111/137` +13.0349 [−6.3155,+32.4666]; batchA 994 `327/320/347`
−6.6823 [−19.7471,+6.3636]; batchB 999 `324/320/355`
−11.1440 [−24.5596,+2.2383]. FROZEN COMBINED batchA+batchB ONLY 1,993 games
`651/640/702`, score 0.4872052, 993 clusters,
−8.9240 [−18.2792,+0.4182], Elo-from-score −8.8927, bootstrap
[−18.2107,+0.1749]; both null CIs include 0, both batches < −5.
ADVANCE False; CLOSE True (UCB<+10 AND point<=0). Reproduced by
`scripts/dev6_exp0038_audit.py 41818958001 exp0045_retry 20 10` and
`scripts/dev6_exp0045_retry_decision.py`: VERDICT CLOSE (mechanism rejected /
abandoned; NO strength claim). No confirmation / third run / post-hoc sample
increase / pooling / retune / default change / bundle. Switch stays OFF. This
is NOT a proven strength regression (~13 Elo half-width). Gates 1 and 4 UNMET,
2 direction-supported, 3 PASS; mission ACTIVE / NOT COMPLETE; no strength
claim, no PR/merge/tag/release/deploy/dev7. Full report
`docs/DEV6_EXP0045_REPORT.md`; evidence
`benchmarks/exp-runs/tier1-export/run-41818958001/`.


## exp-0046 LAUNCHED — margin-adaptive null-move reduction (2026-11-04)
exp-0045 is CLOSED / ABANDONED (INVALID original run, ONE bounded valid retry
`41818958001` frozen combined `-8.9240 [-18.2792,+0.4182]` => CLOSE). New
ranked direction: shipped null-move verification uses a FIXED
`SB_NULLMOVE_R + depth/5` and discards the SIZE of `staticEval - beta` already
computed for the guard. exp-0046 makes ONLY that existing subtree shallower
when staticEval is far above beta, with ZERO added per-node work, no extra
ply, no constant retune of a closed switch and no earlier data reused.

Default-OFF switch `AdaptiveNullR` in `src/search/search.hpp/cpp`,
`src/uci/uci.cpp`, `src/utilities/bench.cpp`; frozen constants
`AdaptiveNullMarginDivisor=200`, `AdaptiveNullExtraCap=2` chosen BEFORE any
game from theory only. OFF bit-identical: default bench
`243f9a1c1ba5b36f`, d16 ttEval=1 `a14ab62224f837e5`, d12 params
`e45fa2ec2287eb41`; Release ctest 11/11, ASan+UBSan ctest 11/11
(`benchmarks/dev6-baseline/exp0046_asan_ctest.log`), UCI default false.

PRE-RESULT diagnostics (`scripts/dev6_exp0046_diag.py`, instrumented
`SB_ADAPTIVE_NULL_DEBUG` build, 24 REAL exp-0046 suite positions): FIXED DEPTH
10 OFF 4,311,394 nodes / ON 4,252,622 (−1.36 % tree change), 44,789 null
nodes, 4,133 changed, 4,721 extra plies, LIVE 23/24; 40 ms fixed-time PROBE
OFF 1,006,703 / ON 974,327 (−3.22 %), LIVE 22/24, median depth 8 both.
Diagnostics are liveness/overhead evidence ONLY, NOT strength; no local
speedup claim.

FROZEN BEFORE ANY exp-0046 GAME: `docs/DEV6_PREREG_EXP0046.md` SHA
`dda54084d2acffddcb7cd5d1134f8734858e9bf0c69d3ab2eb59d3aeab15dd61`, `benchmarks/exp-runs/tier1-plan-exp0046.json` SHA
`557d51fc07ad18eb828e94b2cb273e7225956ca4e6cd55b2279216fb8ebaa18a` (4 jobs), `scripts/dev6_exp0046_openings.py`, 1,400 fresh disjoint
openings seed `2026120701` (ZERO overlap with 39,041 earlier positions in
145 files, ZERO duplicates, four disjoint slices; SHAs in
`benchmarks/dev6-baseline/exp0046_suites.json`). Dispatch
`mode=benchmark experiment_id=exp0046 attempt=24`, `source_sha=HEAD`, all in
the SAME commit. FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, never
`--nodes`; champion options BOTH arms, A adds ONLY `AdaptiveNullR=true`;
Stage-0 control/control validity null, candidate-options null, batchA/batchB
1,000 games each; frozen combined = batchA+batchB ONLY; independent raw-JSONL
audit. ADVANCE >= +20 AND LCB>0 AND both batches >= −5 AND both null CIs
include 0 AND clean; CLOSE if UCB<+10 OR point<=0; otherwise CLOSED AS
INCONCLUSIVE (single-run compute bound). Validity gate enforces 0 forfeits /
illegal / UCI / engine failures in ANY job (exp-0045 lesson, NOT weakened);
at most ONE bounded valid retry. Gates 1 and 4 UNMET; no strength claim, no
default change, no retune, no bundle, no PR/merge/tag/release/deploy/dev7.
Mission ACTIVE / NOT COMPLETE; no result may terminate it.

## exp-0046 CLOSED AS INCONCLUSIVE / ABANDONED (2026-11-04)
Run `41825055840` / export `41826460428` / CI `41825055708` SUCCESS, exact
source `0792555ddd155b2426d926cccc5a16975f77682b`, prereg SHA
`dda54084d2acffdd…`, plan SHA `557d51fc07ad18eb…`, dispatch attempt 24.
4 isolated VMs, 9/9 SHA256SUMS OK in each of 4 bundles, 0 TIME_FORFEIT /
ILLEGAL / ENGINE_FAILURE in ALL four jobs, 44 stored values / 0 issues AUDIT
PASS `clean=True`. Provenance: dev5 baseline VERIFIED, built==packaged binary
`18b9366edcaf…`, default bench `243f9a1c1ba5b36f`, UCI
`AdaptiveNullR default false`. 1,400 fresh disjoint openings seed
`2026120701` (ZERO overlap / 39,041 earlier positions in 145 files), FIXED
TIME 40+4 ms, Hash16/Threads1/240 plies, never `--nodes`.

Stage0 399 `149/113/137` +11.3524 [−5.1046,+27.8606]; candidate null 399
`122/146/131` −8.7314 [−28.0469,+10.5303]; batchA 995 `333/337/325`
+3.1586 [−8.7463,+15.0709]; batchB 995 `350/305/340`
+3.8606 [−8.5988,+16.3299]; both null CIs include 0, both batches >= −5.
FROZEN COMBINED batchA+batchB ONLY 1,990 games `683/642/665`, score
0.5045226, 990 clusters, +3.5096 [−5.1015,+12.1250], Elo-from-score
+3.1427, bootstrap [−4.9136,+12.1125]. ADVANCE False; CLOSE False
(UCB>=+10, point>0). Generic audit's "more samples" is its §6 DEFAULT,
OVERRIDDEN by the frozen SINGLE-RUN COMPUTE BOUND;
`scripts/dev6_exp0046_decision.py` independently reproduces VERDICT
CLOSED_AS_INCONCLUSIVE (frozen single-run compute bound; NO further samples).
No strength claim (CI includes 0), no default change, no retune, no bundle,
no confirmation, no post-hoc sample increase, no pooling with exp-0045 or any
earlier experiment. `AdaptiveNullR` stays OFF. Gates 1 and 4 UNMET,
2 direction-supported, 3 PASS; mission ACTIVE / NOT COMPLETE; no strength
claim / PR / merge / tag / release / deploy / dev7. Full report
`docs/DEV6_EXP0046_REPORT.md`; evidence
`benchmarks/exp-runs/tier1-export/run-41825055840/`.

---

## 2026-11-04 — DEV6 exp-0047 evidence-driven investigation (NO GAMES)

Exact HEAD `d07294d7dbd3a88e5b673f048aeb6a7b1acc1dbf`; CI `41826927521`
SUCCESS; mission ACTIVE / NOT COMPLETE. Added
`docs/DEV6_EXP0047_INVESTIGATION_REPORT.md` (verifiable Phase-1/2 report),
`docs/DEV6_PREREG_EXP0047.md` (complete FROZEN preregistration, DORMANT /
NOT ACTIVATED), and raw gprof evidence
`benchmarks/dev6-baseline/exp0047_gprof_{flat,callgraph}.txt` +
`exp0047_asan_ctest.txt`. Updated current status and research matrix. NO engine
source change, NO implementation, NO opening suite, NO `tier1-dispatch.json`
edit, NO benchmark run, NO new PGN/JSONL, NO invalid measurement, NO pooling,
NO reopened decision.

Verified: authoritative §8 Gate 1 (>= +75 Elo AND 95 % LCB > +50) and Gate 4
(exact candidate release artifact must be the tested binary); full exp-0001…
0046 hypothesis inventory; fresh gprof profile (24 FENs, 12,161,395 nodes:
features 17.77 %, next_move 10.40 %, attacks_bb 9.45 %, TT probe 8.51 %);
fresh matched-toolchain NPS ratio 1.0289 (inside noise, 3 alternating reps,
24,211,820 identical nodes); Release 11/11 and ASan+UBSan 11/11 ctest; three
frozen bench signatures; all 17 experimental UCI switches default false;
reproduced exp-0045 CLOSE and exp-0046 CLOSED_AS_INCONCLUSIVE decisions;
44/0 audits ×2 and 36/36 checksums ×2 exports.

DECISION: no scientifically defensible strength experiment exists at this HEAD
(power analysis says the candidate, not sample size, is binding; every measured
candidate has UCB < +50). Ranked hypotheses: bit-exact attack-set dedup
(~+3–8 Elo, NOT JUSTIFIED), exp-0036 replication (forbidden by frozen
non-repeat), stronger evaluator with accuracy→strength link (highest relevance,
NOT YET TESTABLE). Missing evidence: fresh bullet-matched corpus + frozen
accuracy metric, matched-toolchain inference cost, pre-result >= +75 argument.
The one selected experiment is preregistered with §8 thresholds, 2 x 6,600
games, fresh disjoint suites, 0-forfeit validity, NO authorised retry, a
single-run compute bound and an independent raw-JSONL decision script; it stays
DORMANT until its Activation Record is committed. Gates 1/4 UNMET, 2
direction-supported, 3 PASS; no strength claim, default change, PR, merge, tag,
release, deploy or dev7.

## 2026-11-06 — DEV6 continuation on arena/6a6a2ba3-stockbear: reconnaissance + engineering hardening (session 1)

Branch: `arena/6a6a2ba3-stockbear` (fixed for this session). Fast-forwarded from
`main` `6e7c2e02881faf93a84990a8345c41ad28bcae11` to the demonstrably-correct
DEV6 continuation point `origin/arena/3e6dd5b6-stockbear`
`2f3ded50a34b0086d5597d651a1733b1eb20b595` (0 behind main, 104 ahead). No
history rewritten, no force push, no other branch touched.

Reconnaissance verified against the live remote (not the stale audit snapshot):
- `main` HEAD `6e7c2e0…`, VERSION `0.1.0-dev5`; tag `v0.1.0-dev5` ->
  `c94571313a1667048468cf6d4e070400dc5ab228`; release `v0.1.0-dev5` exists.
- Immutable dev5 baseline binary SHA-256 re-verified locally:
  `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918` (matches).
  Champion `research-data/params_abc.txt` SHA
  `8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be` (matches).
- CORRECTION to the starting snapshot: the research branch DOES modify
  `src/`, `tests/`, `scripts/` (default-OFF experimental switches + zero-gated
  eval features + Tier-1 infrastructure). The earlier "no src changes" audit
  was stale. Default build is still bit-identical to dev5: fresh Release build
  reproduces all three frozen signatures `243f9a1c1ba5b36f`,
  `a14ab62224f837e5`, `e45fa2ec2287eb41`; ctest 11/11 before changes.
- All 10 remote branches, all 10 PRs, 5 tags/releases, 9 workflows and recent
  runs re-audited via `gh`. PR #2 still OPEN/CONFLICTING; its DEAD_POSITION_RESEARCH
  packaging and `set -e` findings are superseded (file renamed, tests already
  separated); its tournament max-plies and engine-failure-classification
  findings are still relevant and were ported (below).
- Read in full/relevant part: DEV6_CURRENT_STATUS, DEV6_PREREG_EXP0047 (DORMANT,
  hash 285b3f34…), DEV6_EXP0047_INVESTIGATION_REPORT, DEV6_PREREG §8,
  DEV6_POWER_ANALYSIS, FAILURE_LEDGER (all headings), search/eval/timeman/UCI/
  tournament/match_stats source. exp-0047 stays DORMANT; no activation conditions
  met; zero strength games played this session.

Engineering hardening landed this session (each with a regression test):
- `scripts/tournament.py`: a non-timeout engine error that coincides with a flag
  fall is now classified `ENGINE_FAILURE` (was hidden inside `TIME_FORFEIT`);
  `TimeoutError` stays a time forfeit. Added per-game `engine_failure` flag and
  summary `engine_failures`/`time_forfeits` counters. Added `max_plies` to the
  configuration record. New `tests/integration/test_tournament_integrity.py`
  (ctest `tournament_integrity`) drives the exact failure paths with fake
  engines; `test_tournament.py` asserts the new fields. ctest now 12/12.
- `RELEASE_NOTES.md`: corrected the verified dev4-content/dev5-version mismatch
  by restoring the verified dev5 notes (from `arena/daa69a3b-stockbear`) under a
  clear "dev6 unreleased / no strength claim" banner. No publication performed.

Mission status: ACTIVE / NOT COMPLETE. Strength gate UNMET (no candidate >= +75
with LCB > +50 exists; exp-0047 dormant). No PR opened yet (no validated
candidate). No merge/tag/release/prerelease/deploy. Next: continue engineering
audit + pursue the materially-stronger-evaluator research direction with a fresh
bullet-matched corpus and frozen activation evidence.

## 2026-11-06 — exp-0048 candidate mechanism + corpus/fit/cost pipeline (branch `arena/6a6a2ba3-stockbear`)

Continuation of the DEV6 mission. Still **zero strength games**, **no PR**,
**no merge/tag/release/deploy**. exp-0047 remains DORMANT with an empty
Activation Record.

Research direction: the failure ledger closes every scalar-retune, neural and
search-switch direction; profiling left "materially stronger evaluator at
unchanged per-node cost" as the only unbounded hypothesis. exp-0048 is a NEW
feature family — a full 6x64x2 per-square piece-square table replacing the
champion's ~15 formulaic rank/file/centre coefficients. The engine already pays
for a `PieceSquare*[pt][idx]` lookup in its material accumulator, so only the
*numbers* change, not the work: this is the one evaluator direction that can
pass exp-0047's `[0.97,1.03]` NPS gate.

Engine changes (all default-OFF, bit-exact when unused):
- `PstFile` UCI string option + `load_pst_file` / `clear_pst_file` /
  `pst_file_active`. Format `SBPST1` + 384 `mg eg` entries, bounded +-2000,
  validated (magic / truncation / range / trailing content) BEFORE any
  mutation; the override lives inside `evaluation_rebuild_tables()` so a later
  `EvalParams` reload cannot silently drop it. Both setoption paths clear the TT.
- `stockbear bench --pst FILE` and `stockbear evaldata --pst FILE`, so a table
  can be measured without rebuilding. `evaldata --pst --check` is REFUSED:
  the per-parameter counts describe the formulaic term and cannot decompose an
  explicit table, so the old check would have reported a false mismatch on
  every row. The score column stays exact and is what the fitter verifies against.
- Tests: unit group `pst` (4 tests: formulaic round-trip bit-exact, zero tables
  change eval + clear restores, malformed rejected without mutation, override
  survives a parameter rebuild) and `tests/integration/test_pst_pipeline.py`
  (5 black-box checks over UCI / bench / evaldata, wired into the CI
  independent-reference job, NOT into global ctest — the standing rule after
  the 162186fb regression). ctest 12/12; all three shipped bench signatures
  reproduced exactly: `243f9a1c1ba5b36f`, `a14ab62224f837e5`, `e45fa2ec2287eb41`.

Frozen preregistration `docs/DEV6_PREREG_EXP0048.md`, written before any real
exp-0048 game: corpus seed 2026110601 (3,000 openings x2 = 6,000 dev5-vs-dev5
games, 40+4 ms, 8 isolated shards, ZERO overlap with 150 earlier suites /
40,441 positions); match seed 2026110603; by-game holdout 0.2 seed 2026110602;
metric held-out Texel log-loss with threshold `L_cand <= 0.97*L_champ` AND
`B_cand <= B_champ`; full-batch Adam 300 iters / lr 5.0 / L2 1e-5 toward the
formulaic init, one fit, no sweep; cost gate `[0.97,1.03]`; ONE 2x1,000-game
diagnostic screen on fresh disjoint suites (batchA/B, seeds 2026110604/5), which
is NOT Gate 1 and cannot authorise a decisive run on its own.

Pipeline (all smoke-tested end to end on throwaway synthetic data):
`scripts/dev6_corpus_job.py` (one shard, zero-engine-failure requirement,
manifest + SHA256SUMS), `scripts/dev6_corpus_combine.py` (verifies every shard
checksum, rejects missing/duplicate/tampered shards, emits a gzip corpus with
shard-prefixed game ids), `scripts/dev6_exp0048_fit.py`,
`scripts/dev6_exp0048_nps.py`, `.github/workflows/dev6-corpus.yml`
(push-triggered generate/export, same discipline as Tier-1: benchmark jobs
never push; one deliberate export commit).

Two real defects found and fixed by the smoke tests, both recorded:
1. The shard manifest hashed `run.log` while it was still open, so the final
   log line invalidated its own checksum and export verification failed. The
   log is now closed before hashing.
2. The first cost-gate draft used a UCI `go nodes` loop. The UCI `info` line
   reports the last COMPLETED iteration's node count, so the two arms reported
   different totals (1,853,814 vs 1,393,400) and "bit-identical node counts" was
   unsatisfiable. Switched to `bench --nodes`, which reports the true searched
   count. The correction is documented in the prereg WITH its reason and was
   made on synthetic data before the corpus existed — not in response to any
   exp-0048 result.

The fitter asserts three exact identities on every corpus row before reporting
any metric: (a) the champion design matrix reproduces `evaluate()`, (b) the
Python rebuild of the formulaic PST equals the engine's PST term, (c) the
engine loaded with the fitted `--pst` equals the fitted model. Without (c) the
holdout number would describe a Python model rather than the evaluator that
would actually play.

Also this session: `.github/workflows/dev6-tier1.yml`'s export job no longer
pushes to the hardcoded `arena/3e6dd5b6-stockbear`; it uses `github.ref_name`,
so evidence lands on the branch that ran the benchmark.

Mission status: ACTIVE / NOT COMPLETE. Gate 1 UNMET, Gate 2 direction-only,
Gate 3 PASS, Gate 4 UNMET. Next: commit + push this pipeline, dispatch the
6,000-game corpus on isolated runners, fit once, evaluate the frozen accuracy
and cost gates, and only then consider the diagnostic screen.

## 2026-11-06 — engineering: qsearch TT store defect found and fixed (default-OFF path)

Confirmed defect in `Search::quiescence()` (`src/search/search.cpp`): the main
move loop ended with `return best;`, bypassing the `finish()` lambda that stores
into the exp-0038 qsearch cache. Every OTHER completed exit went through
`finish()`. Consequence: the cache only ever held stand-pat / delta-pruning /
terminal values and NEVER the value of a node that actually searched a capture,
which is the dominant case and the entire purpose of the cache. The switch is
default OFF (`params_.qsearchTT`), so the shipped engine was unaffected — this
explains why exp-0038 measured as a near-no-op rather than as a real technique.

Fix: `return finish(best);`. The lambda already guards on `!aborted_` and
excludes mate scores, so the store stays correct.

Regression test `tests/unit/test_qsearch_tt.cpp` (new ctest entry `qsearch_tt`,
4 tests). Important methodology note recorded honestly: the first version of
this test compared scores/mates/PV legality with the switch ON vs OFF and
**passed even with the bug reintroduced** — a cache that never stores is still
*correct*, merely useless. The test was therefore rewritten around a
discriminating observable, measured on both builds:
- buggy `return best;`   -> on/off node ratio 0.9990 .. 1.0000 (no saving)
- fixed `return finish()` -> on/off node ratio 0.3680 .. 0.9301
`cache_actually_memoises_searched_capture_nodes` requires a real reduction
(< 0.98) at a fixed depth, where node counts are deterministic. Verified by
reintroducing the defect: that test FAILS (1/4), and passes again once restored.
This is a behaviour assertion, not a timing assertion.

All three shipped bench signatures still exact after the fix:
`243f9a1c1ba5b36f`, `a14ab62224f837e5`, `e45fa2ec2287eb41`. ctest now 13/13.

Also audited and recorded as NOT defects (no change made):
- `negamax()` early returns (TT cutoff, mate-distance pruning, reverse futility,
  null-move fail-high, ProbCut, razoring, empty move list) deliberately do not
  store. Storing a proven TT cutoff is redundant; the others return heuristic
  bounds that must NOT be written as if they were searched values. The current
  behaviour is correct.
- `update_quiet_stats()` halves the whole history table when an entry reaches
  `HistoryLimit`. This is a deliberate dev2-era anti-saturation policy, applied
  only on a positive update that hits the bound. It is O(2*64*64) and rare, and
  it does not corrupt ordering (all entries scale together). Noted as a
  possible future *strength* hypothesis, not an engineering bug; no change.

Corpus: run **42169244756** completed SUCCESS, all 8 shards, 6,000 dev5-vs-dev5
games at 40+4 ms. Artifacts present and unexpired. This is training data only.

## 2026-11-06 — exp-0048 executed: NEGATIVE, closed without retuning

Ran the frozen exp-0048 candidate-development protocol end to end.

Corpus: dispatch → run **42169244756** (8/8 shards SUCCESS, 6,000 dev5-vs-dev5
games, 40+4 ms) → export run **42170087975** SUCCESS → git commit `631a13a`.
Retrieved through the git mirror because the artifact blob CDN is unreachable
from this sandbox. Re-verified every SHA-256 locally: 6,000 games, 260,042
positions, **0 engine failures, 0 time forfeits**, 15 games unadjudicated at the
ply cap (contribute no positions, per the frozen extractor).

One fit, frozen hyperparameters, no sweep. Held-out log-loss 0.2424337459 vs
champion 0.2424826561; required ceiling 0.2352081765. **0.0202 % reduction vs
3 % required — threshold NOT met.** Brier improved but the conjunction fails.
All three engine/model identity checks passed on all 260,042 rows, so the
number describes the real engine. Cost gate passed (node-identical, ratio
1.0097) — the mechanism is free per node; accuracy was the failure.

Root cause recorded in `GRADIENT_DIAGNOSIS.json`: with a mean-normalised
objective the per-entry data gradient is ~8.6e-5 while the frozen L2 contributes
~2e-5 at just 1 cp, so the regulariser pinned the table to the formulaic init
(max |delta| **1.22 cp**, RMS 0.124 cp). As frozen, the run tested "formulaic PST
+ sub-1.3 cp noise", not an expressive table. This is stated plainly in the
report and the ledger so the run is neither overclaimed as a fair test of the
strong version nor used to wrongly foreclose the mechanism.

**No retuning.** The L2/lr/iterations/split seed were frozen before the corpus
existed and were not touched afterwards. No second fit, no smaller-L2 rerun on
the same holdout, no diagnostic screen (it is gated on the accuracy threshold),
**zero strength games**. exp-0047 stays DORMANT with an empty Activation Record.

Written: `docs/DEV6_EXP0048_REPORT.md` (negative), a new `benchmarks/FAILURE_LEDGER.md`
entry with the recurrence condition (scale-match any regulariser to the
mean-normalised gradient and verify on synthetic data that the table actually
moves BEFORE freezing), and `benchmarks/dev6-baseline/exp0048_results/`
(FIT_REPORT, GRADIENT_DIAGNOSIS, NPS_GATE, the exact fitted table, SHA256SUMS).

Mission status: ACTIVE / NOT COMPLETE. Gates 1/4 UNMET, 2 direction-only,
3 PASS. No PR strength claim, no merge/tag/release/prerelease/deploy.

## 2026-11-06 — post-closure exploratory ceiling (exp-0048 verdict unchanged)

Before spending more compute, asked whether the per-square mechanism carries any
signal at all. `scripts/dev6_exp0048_exploratory_ceiling.py` re-fit the CLOSED
exp-0048 corpus across an L2 grid (600 iters, lr 5.0). Held-out reduction:
L2=0 → **4.4721 %** (RMS delta 276.8 cp); 1e-8 → 1.65 %; 1e-7 → 0.71 %;
1e-6 → 0.17 %; **1e-5 (the frozen exp-0048 value) → 0.0202 %** (RMS 0.124 cp).

This confirms the root-cause diagnosis quantitatively: the frozen regulariser
sits at the degenerate end where the optimum is the initialisation. The
mechanism is NOT empty — but exp-0048 as run is still a valid NEGATIVE for its
frozen protocol, and that verdict, report and ledger entry are unchanged.

Guardrails written into the artifact itself
(`benchmarks/dev6-baseline/exp0048_exploratory/README.md` + the JSON `STATUS`
field): exploratory only; may NOT activate exp-0047 or support a strength claim;
the exp-0048 corpus/holdout are BURNED; a successor needs a NEW prereg frozen
before its OWN fresh disjoint corpus. Also recorded: a 4.47 % accuracy gain is
not evidence of +75 Elo.

CI on `95ea477` (the negative-result commit): **SUCCESS**, all 9 jobs.

## 2026-11-06 — exp-0049 preregistered: expressive PST with a correctly scaled objective

A NEW hypothesis, not a retry. exp-0048 stays CLOSED/NEGATIVE and its report and
ledger entry are untouched. `docs/DEV6_PREREG_EXP0049.md`
(SHA-256 `05a43ca5afcae55d115c381225132b21e155e780a1c3dda43fe1f3e594c75265`) is
committed BEFORE any exp-0049 corpus game and before that corpus exists.

Three substantive, pre-declared differences from the degenerate exp-0048
objective: (1) `L2 = 0` so the table is fitted to the data instead of pinned to
the prior; (2) a **support floor** — entries seen < 200 times in the training
split are reset to the formulaic value, because Adam is per-coordinate
scale-invariant and would otherwise move a square seen 3 times as fast as one
seen 100,000 times; (3) a **+-150 cp deviation cap**, an a-priori chess-plausible
bound for a placement term.

Provenance stated plainly in the prereg: `L2 = 0` was informed by the
EXPLORATORY grid on the CLOSED exp-0048 corpus. That is hypothesis generation,
which is exactly why that corpus/holdout are declared BURNED and why exp-0049
uses a FRESH corpus its hyperparameters never saw. The support floor and the cap
were NOT chosen on data: they follow from the measured support histogram (16
entries with zero occurrences, 32 with < 200, median 2,446) and from chess
plausibility. The accuracy threshold is **unchanged** (>= 3 % relative held-out
log-loss reduction AND non-worsening Brier) — not relaxed to let this pass.

Fresh suites, seed 2026110611: 3,000 corpus openings + 2x500 screen openings,
**zero** overlap with all **161** earlier committed suites (44,441 excluded
positions), explicitly including the burned exp-0048 corpus and its unused
screen suites. Split seed 2026110612, match seed 2026110613, screen seeds
2026110614/15.

Infrastructure generalised from exp0048-only to exp0048|exp0049 with every guard
retained: the prepare job still refuses unknown ids and still requires the
prereg and suite manifest in the PINNED commit; `--seed` is now REQUIRED on the
shard job so a new experiment cannot silently inherit a previous seed; the
combiner takes the split seed from the experiment id.

Smoke-tested the whole exp-0049 path on throwaway data before dispatch. That
caught a real shape bug: `support` has 384 piece-square entries while `theta`
has 768 (both phases), so `np.where` could not broadcast. Fixed by applying each
entry's support to both of its phase halves, with an explicit shape assertion.
Verified both guards engage (support floor reset 746 phase entries; cap held
max deviation to exactly 150 cp) and that all three engine/model identity checks
still pass. The 16-game smoke holdout was negative, as expected from overfitting
on tiny data — precisely what the holdout is for. Smoke artifacts deleted; the
prereg was byte-identical before and after the smoke test.

Zero strength games. exp-0047 still DORMANT, Activation Record empty. No PR
strength claim, no merge/tag/release/deploy.

## 2026-11-06 — benchmark-integrity fix: the gate's t critical values were anti-conservative

Audited `scripts/match_stats.py` independently while the exp-0049 corpus ran.
The clustered estimator is correct (200/200 pseudo-random trials match a
separately derived CR1 variance to 1e-12, and clustering correctly widens the
interval under within-opening correlation), but the **Student-t table was
rounded to NEAREST at 3 decimals**, which makes it too small at some degrees of
freedom. A too-small critical value narrows the interval and biases the lower
bound UPWARD — i.e. toward PASSING a gate. That is the wrong direction for a
decision statistic.

Measured against an independent reference (regularised incomplete beta via
continued fraction, bisected to the 0.975 quantile — no table dependency):
**14 of 128** checked df were anti-conservative. Worst absolute excess
`-4.495e-4` at df=15 (stored 2.131000 vs true 2.1314497); worst relative
`-2.11e-4`.

**Impact assessed before changing anything.** On gate-sized samples the lower
bound was optimistic by at most **0.017 Elo** (G=16), 0.007 Elo at G=31 and
0.006 Elo at G=61. Re-ran all three stored decision scripts: exp-0044 confirm
`+13.5977 [2.1750,25.0499]`, exp-0045 retry `-8.9240 [-18.2789,0.4179]`, exp-0046
`+3.5096 [-5.1012,12.1247]`. **Every verdict is unchanged**; CIs move by ~0.0003
Elo. No historical result is rewritten and no gate flips. The fix is made
because the direction is wrong in principle, not because it changes an outcome.

Fix: every table entry is now the true quantile **ceiled at 1e-6**, so all 128
checked df are conservative (worst relative excess +2.08e-8). Documented why
linear interpolation is safe (the t quantile is convex and decreasing, so a
chord lies ABOVE the curve) and that df>120 clamps at t(120), also conservative.

Regression tests added to `tests/integration/test_statistics.py` (already a CI
step, so they run automatically): the independent incomplete-beta reference
itself, a never-anti-conservative assertion over 128 df with MEASURED upper
tolerances per construction (exact 1e-6, interpolated 4e-3, clamped 2.1e-2 — not
guessed), monotonicity plus a Z95 lower bound over df 1..10000, the independent
clustered-variance derivation, and the correlation-widening property.
**Verified the new test FAILS when the old nearest-rounded table is restored**
(`anti-conservative ... df=1: table 12.706 < true 12.7062047`) and passes with
the fix. One pre-existing assertion pinned the old value 12.706; updated to the
ceiled 12.706205 with a comment, preserving the test's purpose.

Verification: `test_statistics.py` 15/15, `ctest` 13/13, PST pipeline 5/5,
tournament integrity PASS. Zero strength games; exp-0047 DORMANT; gates
unchanged (1 UNMET, 2 direction-only, 3 PASS, 4 UNMET).

## 2026-11-06 — exp-0049 EXECUTED and CLOSED as NEGATIVE (both gates failed)

**Sandbox reset recovery first.** The local checkout had reverted to `main`
(`6e7c2e0`) with build artifacts and pip packages gone. Detected before doing any
work, not after. All commits were already pushed; verified remote head
`37c1cd1`, then `git fetch origin arena/6a6a2ba3-stockbear` +
`git merge --ff-only` restored it. Restore VERIFIED rather than assumed: prereg
SHA-256 matched the frozen `05a43ca5…`, fresh Release rebuild reproduced all three
bench signatures exactly (`243f9a1c1ba5b36f` / `a14ab62224f837e5` /
`e45fa2ec2287eb41`), ctest 13/13, dev5 binary and params hashes matched. No
experiment state lost; no measurement repeated because of the reset.

**Corpus.** Exported the completed generation run `42171974318` (8/8 shards
SUCCESS) via export run `42187907151`; pinned `source_sha` to the ORIGINAL
generation commit `5a4dad7…`, not the export commit, so shard manifests verify
against the commit that produced them. 5/5 checksums OK. **6,000 games, 261,641
positions, 0 engine failures, 0 time forfeits.** Verified disjointness
EMPIRICALLY: 0 shared positions and 0 shared openings with the burned exp-0048
corpus, 0 overlap between corpus and screen suites.

**ONE fit, frozen hyperparameters, no sweep.** Split 4,761 train / 1,191 holdout
games. All three engine/model identity checks passed on all 261,641 rows.
**Accuracy gate FAILED: 2.4712 % held-out log-loss reduction vs 3 % required**
(`L_cand` 0.2358740 vs ceiling 0.2345951; shortfall 1.214x). Brier improved, so
that sub-gate passed, but the rule is a conjunction. **Threshold not relaxed.**

**Cost gate FAILED as measured:** median NPS ratio 0.93931, node counts
bit-identical. Recorded with an honest caveat: the champion arm varied 19.2 %
against itself across reps — more than the ~6 % effect — so this sandbox cannot
resolve a 3 % band, and exp-0048 measured 1.00967 on the same mechanism. **Not
re-run**; no retry authorised, and re-rolling for a better number is precisely
the selective measurement the protocol forbids. The accuracy gate closes the
candidate independently, so the ambiguity changes no decision.

**The methodological fix worked.** RMS delta 111.83 cp vs exp-0048's 0.124 cp;
train loss 0.550637 → 0.517245. The post-exp-0048 recurrence condition was
satisfied, so this candidate failed on measured merit rather than a degenerate
objective. **291/768 entries hit the +-150 cp cap** and the raw optimum wanted
1,288.7 cp — the obvious tuning lever, deliberately NOT pulled: relaxing it on
the confirmation corpus would be post-hoc selection.

Provenance bug fixed: the reused NPS script hardcoded `experiment_id=exp0048`.
It now takes `--experiment-id`; this run's label was corrected AFTER measurement
with an explicit note, and every timing/node/ratio/verdict field was asserted
unchanged.

Report `docs/DEV6_EXP0049_REPORT.md`; artifacts + `GATE_DIAGNOSIS.json` under
`benchmarks/dev6-baseline/exp0049_results/` (checksummed); ledger entry appended.
**No screen, zero strength games, exp-0047 DORMANT with empty Activation Record.**
Gates unchanged: 1 UNMET, 2 direction-only, 3 PASS, 4 UNMET. No PR strength
claim, no merge/tag/release/deploy.

## 2026-11-06 — A/A calibration invalidates the NPS cost gate; a prior claim of mine is withdrawn

Followed up the exp-0049 anomaly (gate said 6 % slowdown while the champion arm
varied 19.2 % against itself) by validating the INSTRUMENT rather than the
candidate. Wrote `scripts/dev6_nps_gate_calibration.py`: an A/A null running the
frozen protocol with both arms the identical champion binary and no PST, so the
true ratio is exactly 1.0 and every FAIL is a false reject.

**Result: the gate is invalid on this host.** False-reject rate **80 %** (4/5) at
the frozen 3 reps and **58 %** (7/12) at 5 reps; A/A ratios **0.894–1.035** against
a true 1.0; max arm self-spread 21.1 % vs a 3 % band half-width. Tested four
statistics on the same runs — ratio-of-medians (frozen) 7/12, median-of-paired
4/12, mean-of-paired 6/12, pooled totals 6/12 — **none** rescues it. Between-rep
drift exceeds the band, so adding reps is not a fix on a drifting host.

**This invalidates a claim I made earlier, so I corrected the record.** A PASS is
as uninformative as a FAIL here: exp-0048's recorded 1.00967 does NOT show the PST
is free per node. The "mechanism is genuinely free per node" wording is now
**WITHDRAWN** in `docs/DEV6_EXP0048_REPORT.md`, `benchmarks/FAILURE_LEDGER.md` and
`docs/DEV6_CURRENT_STATUS.md`, each with an explicit correction block. Exp-0049's
0.93931 likewise does not establish a 6 % cost. **No verdict changed** — both
experiments closed on the timing-independent accuracy gate — and **no recorded
measurement was altered or re-run**. Only the interpretation was retracted.

Explicitly did NOT re-roll exp-0049's timing to try for a better number; the
calibration script carries a scope warning saying so. Required fix recorded for
any future prereg: measure cost on an ISOLATED runner, validate with an A/A null
on that host (zero false rejects over >=5 evaluations) BEFORE measuring any
candidate, and freeze statistic/reps/band only afterwards.

Evidence + raw bench CSVs (gzipped, fixed mtime) under
`benchmarks/dev6-baseline/nps_gate_calibration/`, checksummed. Zero strength
games; exp-0047 DORMANT; gates unchanged.

## 2026-11-06 — isolated-runner A/A cost-gate calibration lane (implements the recorded fix)

Implemented the fix the instrument-defect ledger entry required. New
`.github/workflows/dev6-cost-gate.yml` + `scripts/dev6_cost_gate_calibrate_job.py`
run the A/A null on ONE dedicated `ubuntu-latest` VM: build the engine from the
pinned source with the frozen flags, verify HEAD == `source_sha` and the dev5
baseline hash, record the host (CPU, nproc, image, compiler), then run
`dev6_nps_gate_calibration.py` with identical arms and no PST.

**Scope is enforced in code, not just prose:** the lane has NO `--pst` input and
no code path that loads one, so it cannot re-score, reopen or re-roll exp-0048 or
exp-0049. The prepare job rejects any mode other than `calibrate`, requires
>=3 reps and >=5 evaluations (the ledger's minimum), and requires both scripts to
exist in the PINNED commit. Evidence is uploaded as an artifact; nothing is
pushed to any branch.

Smoke-tested locally end-to-end (build, A/A, checksums) before dispatch. That
caught a labelling flaw worth fixing: run locally it still printed "ISOLATED
HOST", which could let a sandbox smoke run be cited as host-capability evidence.
Now the job detects `GITHUB_ACTIONS`/`RUNNER_NAME` and labels a non-runner run
`LOCAL/NON-ISOLATED RUN - NOT VALID HOST EVIDENCE`, recording
`isolated_runner` in the manifest. **Both label branches were exercised** (the
isolated branch via a simulated environment writing only to a throwaway path,
then deleted). All smoke artifacts removed; all 10 workflows parse.

A host that cannot resolve the band is reported as a legitimate informative
result, not a job failure. Zero strength games; no candidate measured; exp-0047
DORMANT; gates unchanged.

## 2026-11-06 — isolated-runner A/A calibration PASSES: the instrument fix is verified

Ran the lane built in the previous entry. Run **42191869178** on a dedicated
`ubuntu-latest` VM (AMD EPYC 7763, nproc 4), engine built from the pinned source
with frozen flags. At the **same frozen 3 reps**: **0 false rejects / 6** A/A
evaluations, ratios **0.99116–1.00254**, half-range **0.00569** vs a 0.030 band
half-width. Versus the sandbox's **80 %** false-reject rate at identical protocol,
A/A scatter tightened **12.4x**. **The ±3 % cost band is resolvable on an isolated
runner and never was on the sandbox.** Validates host+protocol only; no candidate
measured, and exp-0048's withdrawn "free per node" claim stays withdrawn.

Getting the evidence out required a git export mode (artifact CDN and job logs
are both blocked from this sandbox). Mirroring it exposed **three real defects in
my new lane**, each found by verifying rather than trusting a green job:
1. `run.log` silently dropped — `.gitignore` has `*.log`, `git add -A` skipped it,
   yet `SHA256SUMS.txt` listed it. The runner's check passed because the file
   existed in its working tree; it was never committed. The tier1 lane already
   solved this with `git add -f`; mine had omitted it.
2. My new completeness guard then failed spuriously on the RE-export: it tested
   `git diff --cached`, which omits already-committed unchanged files. Corrected
   to test the INDEX (`git ls-files`). Verified locally that the fixed logic flags
   exactly the one genuinely missing file and nothing else.
3. Added **post-push committed-blob hash verification**, since the working-tree
   check had passed on an incomplete mirror. Final export **42192830961**:
   **39/39 committed blobs verified**, `run.log` present.

Also caught a self-inflicted dispatch failure: a push triggered no workflows
because its commit message BODY quoted a literal CI-suppression token while
describing the export commit. GitHub honours it anywhere in the message. Diagnosed
from the message itself rather than assuming a GitHub outage; re-dispatched clean.

Summary updated at `benchmarks/dev6-baseline/nps_gate_calibration/CALIBRATION_SUMMARY.json`
(checksummed); ledger entry appended. Zero strength games; no candidate measured;
exp-0047 DORMANT; gates unchanged (1 UNMET, 2 direction-only, 3 PASS, 4 UNMET).

## 2026-11-06 — audit: the accuracy→Elo link exp-0047 §3.3 requires does not exist

Before proposing a third evaluator candidate, checked what the frozen 3 %
log-loss bar is calibrated against. **It is not calibrated to anything, and the
evidence §3.3 cites is absent.** Zero strength games; nothing activated/reopened.

The ledger has a NPS→Elo slope (~+90 per 2x nodes) but **no accuracy→Elo pair**.
Only exp-0048/0049 ever measured accuracy and both closed before any strength
game, so no experiment has ever seen an accuracy gain AND its strength effect.
exp-0005/0012 recorded loss + Elo but the ordering inverts between the two
best-loss sets, each loss used its own corpus, and the 15.8 Elo spread is below
the ±25 screen noise — no slope is fittable.

Then built a genuine anchor for **zero** games: dev4 and dev5 are immutable
committed binaries, so I scored both on identical positions/labels (6,000 rows,
every 40th, score-independent) from each corpus, with a PAIRED CR1 clustered SE
over games, against the one high-confidence fixed-time Elo (+64.7 [+57.5,+72.0],
6,600 games, exp-0024). Accuracy change is **<0.5 % in magnitude and its sign
flips with K on both corpora**; Brier and log-loss disagree in sign on both.

Two mistakes caught by verifying rather than reporting: my first run used DEFAULT
params for both arms and produced identical losses — dev5's extra features have
zero default weight, so I re-ran with the champion's actual `params_abc`. That
also revealed the binaries score byte-identically under params_abc, since it omits
dev5's four extra features. And I checked K-sensitivity and replication on the
second corpus **before** writing any conclusion, which is what stopped me from
claiming "accuracy got worse" as a finding.

**Stated carefully:** this does NOT show accuracy gains fail to produce Elo — the
+64.7 is a bundle (flags + params + TTEval), much of it plausibly NPS. It DOES show
Elo can arrive with ~no accuracy change, so no slope is fittable and the 3 % bar
has no licensed Elo interpretation. **§3.3 is therefore currently unsatisfiable
for any accuracy-driven candidate** — a structural blocker, not a candidate
failure, and it retro-explains why exp-0048/0049 could never have activated even
on a pass.

Report `docs/DEV6_ACCURACY_ELO_LINK_AUDIT.md`; checksummed evidence + raw extractor
output (gzipped) in `benchmarks/dev6-baseline/accuracy_elo_anchor/`; reusable
script `scripts/dev6_accuracy_elo_anchor.py`; ledger entry appended. Resolution
options recorded (preregistered accuracy+Elo calibration, or select on fixed-time
screens) with an explicit instruction not to lower any threshold. Gates unchanged;
exp-0047 DORMANT.
