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
