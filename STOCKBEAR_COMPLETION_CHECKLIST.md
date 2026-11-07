# STOCKBEAR — MISSION COMPLETION CHECKLIST

**Authoritative mission-completion gate.** Separate from all experiment reports
and research logs. An incomplete checklist means an incomplete mission.

- **Branch:** `arena/6a6a2ba3-stockbear`
- **Checklist created:** 2026-11-06 at HEAD `d3d40d59ff8b627ae7ce541a8ed59598da8c5898`
- **Status:** **MISSION INCOMPLETE** — one improvement CONFIRMED (exp-0054, +23.54 [+15.69,+31.41]); the +75 / LCB>+50 strength gate is **NOT** met.

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
- [ ] **0.2** The published `v0.1.0-dev4` release asset is downloaded via CI and
      its checksum verified, per the user's explicit provenance choice
      ("fetch_release"). dev4 is retained as a verified historical/reference
      anchor, NOT as the dev6 gate baseline.
      *Evidence required:* CI job log + asset SHA-256 + committed provenance record.

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

- [ ] **1.1** `origin/main` is unchanged at `6e7c2e02881faf93a84990a8345c41ad28bcae11`.
      *Evidence:* `git rev-parse origin/main` output recorded in the final report.
- [ ] **1.2** All work is on `arena/6a6a2ba3-stockbear`; no other branch created, renamed or pushed.
      *Evidence:* `git reflog` / `git branch` inspection recorded.
- [ ] **1.3** The immutable dev4 binary is unmodified: SHA-256 `1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae`.
      *Evidence:* `sha256sum` output at final SHA.
- [ ] **1.4** The immutable dev5 binary is unmodified: SHA-256 `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`.
      *Evidence:* `sha256sum` output at final SHA.
- [ ] **1.5** The designated gate baseline's provenance is verified as the bit-identical released artifact (not an unverified local rebuild).
      *Evidence:* release-asset checksum verification or documented tag-rebuild equivalence, cited.
- [ ] **1.6** `DESIGN_LOG.md`, `AGENTS_LOG.md`, `benchmarks/FAILURE_LEDGER.md` were only appended to; no historical entry rewritten or deleted.
      *Evidence:* `git diff` of those paths across the mission range showing additions only.
- [ ] **1.7** No historical benchmark artifact, raw record or PGN was modified or deleted.
      *Evidence:* `git diff --stat` over `benchmarks/exp-runs/` showing additions only.
- [ ] **1.8** Closed experiments exp-0049/0050/0051/0052 were not reopened, rescored or reinterpreted.
      *Evidence:* their verdict files unchanged; cited diff.
- [ ] **1.9** Public release identity remains `v0.1.0-dev5`; no version bump, no dev6/dev7 tag, no release, no deploy, no merge to main.
      *Evidence:* `VERSION` contents, `gh api` tag/release listing at final SHA.

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

- [ ] **6.1** Perft and move-generation correctness tests pass.
      *Evidence:* test names, actual output, exit codes.
- [ ] **6.2** Every registered automated test EXECUTES and returns a successful exit code — verified individually, not inferred from a green CTest summary.
      *Evidence:* per-test output and exit status; explicit confirmation that each intended test binary ran.
- [ ] **6.3** Every new test group is actually registered with `add_test()` and appears in CTest output.
      *Evidence:* CTest test listing showing the group by name.
- [ ] **6.4** King-safety, threat-evaluation, parameter-loading and file-loading branches are directly exercised.
      *Evidence:* named tests + independent oracle results.
- [ ] **6.5** Differential/regression tests pass; default shipped behaviour is bit-exact (all established bench signatures).
      *Evidence:* signature values at final SHA.
- [ ] **6.6** Sanitizer runs (ASan/UBSan, and TSan where registered) pass.
      *Evidence:* sanitizer test output and exit codes.
- [ ] **6.7** Mutation testing demonstrates the new mechanism's tests actually detect a dead/incorrect implementation.
      *Evidence:* mutants applied, each KILLED, with output.
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
