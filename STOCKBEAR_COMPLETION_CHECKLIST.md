# STOCKBEAR — MISSION COMPLETION CHECKLIST

**Authoritative mission-completion gate.** Separate from all experiment reports
and research logs. An incomplete checklist means an incomplete mission.

- **Branch:** `arena/6a6a2ba3-stockbear`
- **Checklist created:** 2026-11-06 at HEAD `d3d40d59ff8b627ae7ce541a8ed59598da8c5898`
- **Status:** **MISSION INCOMPLETE** — one improvement CONFIRMED (exp-0054, +23.54 [+15.69,+31.41]); the +75 / LCB>+50 strength gate is **NOT** met.
- **Latest:** exp-0056 (integral threats+race vs released dev5, 6,800 games) is **INVALID** — the candidate-options null CI **[+0.6520,+37.9077] excludes 0**, failing frozen §5.4. **No strength claim.** Face value +41.01 [+34.36,+47.69] is **withheld**; the auditor's "TOTAL ISSUES: 0" does NOT cover null adequacy (`nulls_ok=False`). Even at face value the configuration **cannot** pass the gate: point < +75 and the CI's upper bound +47.69 < the required LCB +50. **Threats + race is not a sufficient basis for Gate 1; roughly +35 Elo more is needed.** Evidence: `docs/DEV6_EXP0056_REPORT.md`, `benchmarks/recovery/exp0056_independent_raw_audit.json` (`frozen_decision`, run 42338019422). Prior step exp-0055 remains a **SCREEN ADVANCE** (+25.9606 [+17.5818,+34.3697], audit 0 issues), an increment never to be summed with exp-0054.

## Checkbox rules (binding)

1. Never check an item merely because it was attempted.
2. Never check an item because a command returned green without inspecting its actual result.
3. Never check an item based on assumption, estimate, intention or unverified claim.
4. Never check an item while its evidence is missing or contradictory.
5. Never mark an inconclusive outcome as a successful strength improvement.
6. Every checked item MUST cite concrete evidence: report path, raw-data path, test output, artifact hash or commit SHA.
7. If an item is not fully demonstrated it MUST remain `[ ]`.
8. No `N/A`, `waived` or equivalent may bypass a mandatory criterion.
9. The entire checklist is re-audited against actual repository state before completion.

---

## 0. Gate specification — RESOLVED by user decision 2026-11-06

- [x] **0.1 Gate baseline identity resolved and recorded.**
      *Evidence:* user decision in conversation 2026-11-06: "never mind its
      context. Remember my own task and continue with it. dev6 and 75+ elo
      compared to baseline or others." The dev4 wording in the directive was
      carry-over context and is withdrawn. The governing gate is therefore the
      committed frozen dev6 gate, `docs/DEV6_PREREG.md:146-147`:
      **combined point estimate >= +75 Elo AND combined two-sided
      opening-clustered 95% CI lower bound strictly > +50**, against the exact
      released `v0.1.0-dev5` artifact
      `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`
      at champion options (`EvalParams=research-data/params_abc.txt`,
      `TTEval=true`), fixed time 40+4 ms, Hash 16, Threads 1.
- [x] **0.2** The published `v0.1.0-dev4` release asset is downloaded via CI and
      its checksum verified, per the user's explicit provenance choice
      ("fetch_release"). dev4 is retained as a verified historical/reference
      anchor, NOT as the dev6 gate baseline.
      *Evidence:* new lane `.github/workflows/dev4-provenance.yml`, run
      **42338201855** — **success**, every step green. It downloaded all three
      published assets and ran `sha256sum -c`:
      `stockbear-0.1.0-dev4-linux-x64.tar.gz: OK`,
      `stockbear-0.1.0-dev4-windows-x64.zip: OK`. Committed record
      `benchmarks/dev6-baseline/exp_dev4_release_provenance.json` (CI commit
      `b2664f1`) with `all_published_checksums_ok: true` and asset digests
      `bc847d7e…` / `185ef6af…` / `60a1458f…`.
      **Material finding:** the released linux executable is
      `96dad79551e648177a8fb3a45aebecb3ed331a7d0caca6f1a1908073e2ee57c3`, which is
      **NOT** bit-identical to the in-repo tag rebuild
      `1c5b61a755215134…` (`released_equals_tag_rebuild: false`). Both report
      `id name StockBear 0.1.0-dev4` and the same bench signature
      `243f9a1c1ba5b36f`, so they are functionally equivalent but built by
      different toolchains. The in-repo dev4 file is therefore recorded as a
      **rebuild**, exactly as the user's provenance choice was meant to expose.
      This does not affect the gate, whose baseline is dev5 (see 1.5).

---

## 0.3 Push-scope interpretation (recorded, not a waiver)

- [ ] **0.3** The distinction between RESEARCH DISPATCH pushes and the FINAL
      completion push is confirmed acceptable to the user.
      *Context:* the benchmark lane is **push-triggered**
      (`.github/workflows/dev6-tier1.yml` `on: push: paths:
      benchmarks/exp-runs/tier1-dispatch.json`); `workflow_dispatch` returns 403
      in this environment. Running the preregistered isolated-VM experiments
      therefore REQUIRES a dispatch commit on the research branch. The directive
      both prohibits pushing before the checklist is complete AND directs
      "use available free compute, isolated runners, and CI resources
      efficiently". These cannot both hold literally.
      *Interpretation applied:* dispatch/export commits to the dedicated non-main
      research branch `arena/6a6a2ba3-stockbear` are the established experiment
      mechanism (used for exp-0051 and exp-0052) and are NOT publication of a
      final candidate. The §8 completion push remains BLOCKED until every
      mandatory item is genuinely satisfied. No merge, tag, release or deploy.
      *This item stays unchecked until the user confirms the interpretation.*

---

## 1. Repository and baseline integrity

- [x] **1.1** `origin/main` is unchanged at `6e7c2e02881faf93a84990a8345c41ad28bcae11`.
      *Evidence:* `git rev-parse origin/main` at 2026-11-07 (HEAD `de20f5f`) returned
      exactly `6e7c2e02881faf93a84990a8345c41ad28bcae11`.
- [x] **1.2** All work is on `arena/6a6a2ba3-stockbear`; no other branch created, renamed or pushed.
      *Evidence:* `git branch` lists only `arena/6a6a2ba3-stockbear` (current) and the
      pre-existing local `main`; `git rev-parse --abbrev-ref HEAD` = the session branch.
      Every push used the explicit refspec `git push origin arena/6a6a2ba3-stockbear`
      (latest: `2ed8955..de20f5f`), and local HEAD == `origin/arena/6a6a2ba3-stockbear`
      == `de20f5faf58bc928a63dff2ed9980b7bcaedb7b1`. Other `arena/*` branches visible
      on the remote pre-date this session and were never fetched, created or pushed here.
- [x] **1.3** The immutable dev4 binary is unmodified: SHA-256 `1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae`.
      *Evidence:* `sha256sum benchmarks/binaries/stockbear-dev4-1c5b61a7` at 2026-11-07
      returned exactly that digest. (Provenance of this file as a *tag rebuild* is
      tracked separately under 0.2 / 1.5, which remain open.)
- [x] **1.4** The immutable dev5 binary is unmodified: SHA-256 `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`.
      *Evidence:* `sha256sum benchmarks/binaries/stockbear-dev5-release` at 2026-11-07
      returned exactly that digest; re-verified after the sandbox reset and `chmod +x`.
- [x] **1.5** The designated gate baseline's provenance is verified as the bit-identical released artifact (not an unverified local rebuild).
      *Evidence:* the gate baseline is **dev5**. `benchmarks/dev6-baseline/manifest.json`
      records task `verify-baseline` executed on a GitHub-hosted runner
      (2026-11-03T12:24:22Z) downloading
      `releases/download/v0.1.0-dev5/stockbear-0.1.0-dev5-linux-x64.tar.gz`
      (release commit `c94571313a1667048468cf6d4e070400dc5ab228`), with raw
      `sha256sum -c` output preserved at
      `benchmarks/exp-runs/exp0025-baseline/checksums.txt`
      (`…linux-x64.tar.gz: OK`, `…windows-x64.zip: OK`). The extracted executable
      digest `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`
      was re-verified locally today (1.4), and the champion `params_abc.txt`
      digest `8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be`
      matches both the shipped and repo copies. See also
      `benchmarks/dev6-baseline/PROVENANCE.md`. Unlike dev4, this baseline is the
      actual published artifact, not a rebuild.
- [x] **1.6** `DESIGN_LOG.md`, `AGENTS_LOG.md`, `benchmarks/FAILURE_LEDGER.md` were only appended to; no historical entry rewritten or deleted.
      *Evidence:* `git diff --numstat origin/main..HEAD` gives
      `DESIGN_LOG.md 923 added / 0 removed`, `AGENTS_LOG.md 1718 / 0`,
      `benchmarks/FAILURE_LEDGER.md 1988 / 0`; a grep for removed lines
      (`^-[^-]`) across all three diffs returns **0**.
- [x] **1.7** No historical benchmark artifact, raw record or PGN was modified or deleted.
      *Evidence:* `git diff --name-status origin/main..HEAD -- benchmarks/exp-runs/`
      contains **no `M` or `D` entries** (additions only). Across all of `benchmarks/`
      the only modified paths are `FAILURE_LEDGER.md` (proven append-only in 1.6) and
      `params/dev3-shipped.txt` (the shipped parameter table, extended by appending new
      default-zero rows — not a raw record). `research-data/` has no `M`/`D` entries.
- [x] **1.8** Closed experiments exp-0049/0050/0051/0052 were not reopened, rescored or reinterpreted.
      *Evidence:* `git diff --name-status origin/main..HEAD` over their four reports and
      the exp-0051/0052 independent-audit JSONs shows **`A` (added) only** — never `M`.
      No later prereg reuses their openings; exp-0055's suite generator excludes all
      199 earlier files / 56,841 positions with verified 0 overlap.
- [ ] **1.9** Public release identity remains `v0.1.0-dev5`; no version bump, no dev6/dev7 tag, no release, no deploy, no merge to main.
      *Evidence so far:* `gh api repos/coderunknow/StockBear/releases` lists
      `v0.1.0-dev5` as the newest release — **no dev6/dev7 tag or release exists**, and
      `origin/main` is untouched (1.1). **HELD OPEN deliberately:** the working-tree
      `VERSION` file reads `0.1.0-dev6`, bumped by the pre-existing branch commit
      `a7bf00f` ("dev6 cycle start"), so the engine advertises `StockBear 0.1.0-dev6`
      over UCI while `origin/main:VERSION` is `0.1.0-dev5`. That is an *internal*
      development marker, but the item says "no version bump" and the discrepancy is
      real, so it is **not** checked on an interpretation. Requires explicit resolution.

## 2. Research and experiment discipline

- [ ] **2.1** Every strength-tested experiment has its own preregistration committed BEFORE its first game.
      *Evidence:* per-experiment prereg path + SHA-256 + the commit SHA preceding the run's dispatch.
- [ ] **2.2** Each prereg specifies ID, hypothesis, mechanism, candidate/baseline hashes, frozen ADVANCE/CLOSE/INCONCLUSIVE rules, time control, opening methodology, statistics, power rationale and validity requirements.
      *Evidence:* section-by-section citation into each prereg.
- [ ] **2.3** No preregistered acceptance criterion was altered after results were observed.
      *Evidence:* `git log -p` on each prereg showing no post-result edits.
- [ ] **2.4** Cheap pre-game checks (correctness oracle, scale, cost, liveness, mutation) preceded every substantial compute spend.
      *Evidence:* per-experiment pre-game evidence JSON paths.
- [ ] **2.5** Inconclusive/rejected experiments were preserved with full verdicts and the mission continued to a distinct next direction.
      *Evidence:* ledger entries + subsequent experiment IDs.
- [ ] **2.6** No inconclusive experiment was re-run without a justified preregistered reason.
      *Evidence:* experiment ledger cross-check.
- [ ] **2.7** The strategy is not blind summation of individually inconclusive candidates.
      *Evidence:* final integration measured directly, not inferred (§3.3).

## 3. Confirmed improvements and final candidate integration

- [x] **3.1** At least one improvement is CONFIRMED under its own adequately powered preregistered confirmation (not a screen, not an inconclusive result).
      *Evidence:* `docs/DEV6_EXP0054_REPORT.md` and
      `benchmarks/recovery/exp0054_independent_raw_audit.json` — ThreatDetection,
      4,000 combined games, **+23.5374 Elo, 95% CI [+15.6937, +31.4052]**, both
      batches positive (+20.38 / +26.70), all 7 frozen conditions PASS, audit
      issues 0, 4,800/4,800 PGN replayed. Prereg SHA
      `48e800e804dbaa27b32d369c368b3c7baed42c931a6d6236bc1166a4d5b993ea` committed
      at `dfb4838` before run 42244166583. NOT pooled with the exp-0053 screen.
- [ ] **3.2** Every component of the final candidate is individually supported by adequate independent evidence.
      *Evidence:* per-component confirmation citations.
- [ ] **3.3** The final integrated candidate was measured DIRECTLY against the gate baseline; its strength was not inferred by adding individual Elo estimates.
      *Evidence:* final match raw records + audit.
- [ ] **3.4** All non-qualifying experimental features remain default-OFF in the shipped configuration.
      *Evidence:* shipped parameter file + default bench signatures.

## 4. Final strength measurement (the non-waivable gate)

- [ ] **4.1** The final candidate achieves a **two-sided opening-clustered 95% CI lower bound STRICTLY GREATER THAN +50 Elo** against the designated bit-identical released baseline under fixed-time **40+4 ms**.
      *Evidence:* final audit JSON with the exact LCB value; a lower bound equal to +50 FAILS.
- [ ] **4.2** The comparison used the established frozen protocol: Hash 16, Threads 1, max-plies 240, fixed time (never node budget), established opening-cluster methodology and CR1/t interval.
      *Evidence:* per-job config records independently verified.
- [ ] **4.3** No frozen rule (openings, time control, clustering, CI method, adjudication) was changed after observing results.
      *Evidence:* prereg vs run-config comparison.
- [ ] **4.4** The final sample size meets or exceeds the preregistered final size.
      *Evidence:* game counts reconciled from raw JSONL.
- [ ] **4.5** Both independent batches are positive and reasonably consistent (if the frozen rule requires it).
      *Evidence:* per-batch independently recomputed estimates.

## 5. Statistical and data-integrity validation

- [ ] **5.1** All final game records were independently recomputed from raw per-game JSONL by an auditor sharing no code with the summary producer.
      *Evidence:* auditor script path + output JSON.
- [ ] **5.2** Every final PGN was fully replayed; all moves legal; all outcomes consistent with records.
      *Evidence:* replay counts and inconsistency count (must be 0).
- [ ] **5.3** Zero time forfeits, illegal moves, engine failures or unexplained game failures in the final run (or each is explicitly accounted for under a pre-declared symmetric policy).
      *Evidence:* termination histogram from raw records.
- [ ] **5.4** All validity nulls have CIs including zero.
      *Evidence:* null-job recomputed intervals.
- [ ] **5.5** All committed blob digests and per-job `SHA256SUMS` verify.
      *Evidence:* `verified/total` counts from the auditor.
- [ ] **5.6** Every file-valued UCI option has positive per-arm load proof; no silent fallback occurred.
      *Evidence:* per-arm `LOAD VERIFIED` lines cross-checked against raw probe output and the frozen plan.
- [ ] **5.7** Arm binary identities match the declared design and the pinned baseline digest.
      *Evidence:* fingerprint/config digests vs plan.
- [ ] **5.8** Auditor total issues = 0.
      *Evidence:* final audit JSON `issues: []`.

## 6. Engine correctness and regression testing

- [x] **6.1** Perft and move-generation correctness tests pass.
      *Evidence:* run individually at 2026-11-07: `perft_quick` exit **0** (`Tests: 2,
      failures: 0`), `perft_full` exit **0** (`Tests: 1, failures: 0`), `position_extra`
      exit **0** (`Tests: 4, failures: 0`), `unit` exit **0** (`Tests: 41, failures: 0`,
      includes move-generation/geometry).
- [x] **6.2** Every registered automated test EXECUTES and returns a successful exit code — verified individually, not inferred from a green CTest summary.
      *Evidence:* all **17** registered groups invoked one-by-one with `$?` captured
      immediately (never through a pipe). 14 C++ groups via `stockbear_tests`:
      unit 41, nnue 7, pst 4, position_extra 4, qsearch_tt 4, correction_history 5,
      king_safety 7, threats 8, passed_pawn_race 7, regression 6, perft_quick 2,
      stress 1, perft_full 1, deadpos 13 — **110 assertions, every exit=0, 0 failures**.
      3 Python integration tests run directly against `./build-rel/stockbear`, each
      exit=0: `uci_integration` ("PASS UCI EvalParams loading, spaced paths, invalid
      file and reset"), `uci_fuzz` ("PASS 300 deterministic malformed/cancellation
      cases; 101 legal-format bestmoves for 101 accepted go commands"),
      `nnue_features` ("11 positions, 2 perspectives each, 0 mismatches").
      Aggregate `ANY_FAILURE=0`.
- [x] **6.3** Every new test group is actually registered with `add_test()` and appears in CTest output.
      *Evidence:* `CMakeLists.txt:190` `add_test(NAME passed_pawn_race COMMAND
      stockbear_tests passed_pawn_race)`; `ctest -N` lists **`Test #9: passed_pawn_race`**
      and `Total Tests: 17`. The group also appears as `9/17 ... Passed` in the
      ASan/UBSan ctest run. (This check exists because exp-0052's `king_safety` group
      was initially never registered and CTest silently skipped it.)
- [x] **6.4** King-safety, threat-evaluation, parameter-loading and file-loading branches are directly exercised.
      *Evidence:* `king_safety` 7 tests exit 0, `threats` 8 tests exit 0,
      `passed_pawn_race` 7 tests exit 0. Parameter/file loading is exercised by
      `uci_integration` (explicitly covers "EvalParams loading, spaced paths, invalid
      file and reset") and by `tests/unit/test_eval_baseline.cpp` (checksum pin
      `0x849cc5a968fd9b1eULL`, malformed-row rejection). Independent oracles:
      `check_king_safety.py`, `check_threats.py` (800/0), `check_passed_pawn_race.py`
      (800 positions, **0 mismatches**, 352 non-zero).
- [x] **6.5** Differential/regression tests pass; default shipped behaviour is bit-exact (all established bench signatures).
      *Evidence:* at 2026-11-07 with `PassedPawnRace` shipped 0, all three established
      signatures reproduce **exactly**: depth-4 `243f9a1c1ba5b36f`, depth-6
      `e06c4352681ae8eb`, depth-7 `5bceff035f2a4ae4` (documented in
      `docs/DEV5_BENCHMARKS.md:14` and `docs/DEV4_BENCHMARKS.md:79`). `regression`
      6 tests exit 0; `nnue_features` differential 0 mismatches. The race-ON vs
      pre-fusion refactor was additionally proven value-identical on 4,000 positions.
- [x] **6.6** Sanitizer runs (ASan/UBSan, and TSan where registered) pass.
      *Evidence:* local `build-asan` (`-fsanitize=address,undefined`) ctest run:
      **17/17 passed, process exit 0**, total 84.80 s, with `passed_pawn_race`
      appearing as `9/17 ... Passed 1.66 sec`. TSan **is** registered
      (`.github/workflows/ci.yml:198` "Linux ThreadSanitizer"), and CI run
      **42336347927** on `de20f5fa` completed **success** with all 9 jobs green,
      including `Linux ThreadSanitizer` and `Linux ASan + UBSan`.
- [x] **6.7** Mutation testing demonstrates the new mechanism's tests actually detect a dead/incorrect implementation.
      *Evidence:* `benchmarks/recovery/exp0055_mutation_matrix.json` — **10/10 KILLED,
      `survivors: []`, verdict PASS**, each mutant physically written to the source,
      rebuilt and the suite re-run: computed_but_never_applied, own_king_escort_removed,
      enemy_king_blockade_removed, blocked_path_penalty_removed,
      advance_weighting_removed, live_path_cap_removed, breakdown_path_cap_removed,
      chebyshev_replaced_by_manhattan, live_path_scores_non_passers,
      **live_path_disabled**. Source restoration verified (bench depth-4 sig unchanged
      afterwards). Earlier mechanisms: threats 7/7 KILLED, king-safety 3/3 KILLED.
- [ ] **6.8** Performance/resource overhead measured with a calibrated instrument and within the declared budget.
      *Evidence:* paired A/A-calibrated cost measurement JSON.
- [ ] **6.9** No unintended regression in existing engine functionality.
      *Evidence:* full test suite + signature + self-play sanity results.

## 7. Final artifact and reproducibility audit

- [ ] **7.1** The final executable identity is verified and its hash recorded.
      *Evidence:* SHA-256 of the packaged binary, matched to the tested binary.
- [ ] **7.2** The baseline executable identity is verified and its hash recorded.
      *Evidence:* SHA-256 matched to the pinned digest.
- [ ] **7.3** The final source SHA, prereg SHA and opening-suite SHA are pinned and enforced in the run.
      *Evidence:* fingerprint fields + runner assertions.
- [ ] **7.4** Raw records, PGNs, checksums, configs and analysis scripts are committed and reproducible.
      *Evidence:* export directory listing + re-run of the analysis reproducing the numbers.
- [ ] **7.5** Results reproduce on the actual execution environment.
      *Evidence:* documented environment + reproducibility check.
- [ ] **7.6** No build artifacts, large datasets or unclear-licensing assets were committed.
      *Evidence:* `git ls-files` inspection + patch size.

## 8. Final commit, CI and pre-push authorization

> **NO PUSH until every item in §0–§7 above is genuinely `[x]` with evidence.**

- [ ] **8.1** The full final audit was run against the exact final commit SHA.
      *Evidence:* audit output referencing that SHA.
- [ ] **8.2** The exact final commit SHA is established and recorded.
      *Evidence:* `git rev-parse HEAD`.
- [ ] **8.3** Every mandatory pre-push checkbox (§0–§7) is `[x]` and independently re-verified against actual repository state.
      *Evidence:* re-audit record; any unproven item remains `[ ]` and BLOCKS the push.
- [ ] **8.4** Push performed only after 8.3, to `arena/6a6a2ba3-stockbear` only.
      *Evidence:* push output.
- [ ] **8.5** The remote branch contains the exact intended commit SHA, independently verified.
      *Evidence:* `git ls-remote` / `gh api` ref lookup.
- [ ] **8.6** Required post-push CI passed on that exact SHA.
      *Evidence:* run ID, conclusion, per-job results, headSha equality.
- [ ] **8.7** Final report contains all nine required elements (candidate SHA, baseline identity, games/W-D-L/Elo/CI, explicit LCB > +50 confirmation, independent recomputation evidence, correctness/CI results, checklist path, remote SHA, disclosed limitations).
      *Evidence:* final report path.

---

## Current disposition

**MISSION INCOMPLETE.** The gate is the frozen dev6 gate: **point >= +75 Elo AND
two-sided opening-clustered 95% LCB strictly > +50 vs the released dev5
champion** at 40+4 ms.

Progress: exp-0050 closed negative; exp-0051 closed negative; exp-0052 closed
inconclusive (+4.20 [-6.97,+15.38]); exp-0053 SCREEN ADVANCE (+24.63
[+13.10,+36.22]); **exp-0054 CONFIRMED IMPROVEMENT (+23.54 [+15.69,+31.41])** —
the mission's first banked gain. One ~+23.5 Elo term reaches neither the +75
point requirement nor the +50 LCB requirement. Further distinct confirmed
improvements are required, and the integrated candidate must then be measured
DIRECTLY against the released baseline (never inferred by adding estimates).
Execution continues with passed-pawn evaluation.
