# STOCKBEAR — MISSION COMPLETION CHECKLIST

**Authoritative mission-completion gate.** Separate from all experiment reports
and research logs. An incomplete checklist means an incomplete mission.

- **Branch:** `arena/6a6a2ba3-stockbear`
- **Checklist created:** 2026-11-06 at HEAD `d3d40d59ff8b627ae7ce541a8ed59598da8c5898`
- **Status:** **MISSION INCOMPLETE** — two components CONFIRMED (exp-0054 threats +23.54 [+15.69,+31.41]; exp-0060 race increment +27.01 [+20.87,+33.16]); exp-0062 provides the first VALID direct integral dev5 estimate for threats+race: **+40.7732 [+36.2091,+45.3513]**. The +75 / LCB>+50 strength gate is **NOT** met (point and LCB both fail; UCB +45.35 < +75).
- **Latest:** exp-0064 (extension-agnostic main-TT identity, 7,800 games) is a **VALID SCREEN / INCONCLUSIVE**: primary combined **+5.2399 [+0.0235,+10.4586]** (batchA +6.4045, batchB +4.0753); frozen ADVANCE needed point ≥+10 and frozen CLOSE needed UCB <+3 or point ≤0, so neither fires. 22/22 validity checks PASS; auditor issues 0; 7,800/7,800 PGN replay; both powered nulls include zero. `TTExtensionAgnostic` **remains default OFF**; no extra games, no rescale, no pooling. Evidence: `docs/DEV6_EXP0064_REPORT.md`, `benchmarks/recovery/exp0064_validity.json`, `benchmarks/recovery/exp0064_independent_raw_audit.json` (run 42379450457, export 42381671293). Previous: exp-0063 (battery after semantics-preserving cost optimization, 5,800 games) is a **VALID SCREEN / CLOSED (mechanism rejected)**: prospective cost gate PASS (increment 1.04470 ≤1.05, combined 1.08861 ≤1.10), but primary combined **−6.0300 [−14.1476,+2.0809]**; 16/16 validity checks PASS; see `docs/DEV6_EXP0063_REPORT.md` (run 42365991406, export 42367464017). The battery direction is closed by game evidence. Previous: exp-0062 (decisive integrated threats+race vs exact published dev5, 15,000 games) is a **VALID MEASUREMENT / GATE UNMET**: primary combined **+40.7732 [+36.2091,+45.3513]**, batchA +38.3422, batchB +43.2141; both powered nulls include zero; 17/17 validity checks PASS; auditor issues 0; 15,000/15,000 PGN replay. Evidence: `docs/DEV6_EXP0062_REPORT.md`, `benchmarks/recovery/exp0062_validity.json`, `benchmarks/recovery/exp0062_independent_raw_audit.json` (run 42356232866, export 42364780824). exp-0061 (king-slider battery) remains **BLOCKED BEFORE GAMES** by the prospective CI cost gate (increment 1.17094 > 1.05; combined 1.25063 > 1.10), zero games, no strength verdict; see `docs/DEV6_EXP0061_REPORT.md`. Previous confirmed increment: exp-0060 (passed-pawn race confirmation, 7,800 games) is a **VALID MEASUREMENT / CONFIRMED INCREMENT**: combined **+27.0085 [+20.8746,+33.1592]**, batchA +29.0007, batchB +25.0260; both powered nulls include zero; 16/16 validity checks PASS; 7,800/7,800 PGN replay. Prospective CI cost gate passed before games (A/A spread 0.0155; increment 1.0207; combined 1.0903). Evidence: `docs/DEV6_EXP0060_REPORT.md`, `benchmarks/recovery/exp0060_validity.json`, `benchmarks/recovery/exp0060_independent_raw_audit.json` (run 42352690063). exp-0059 closed pre-game on cost-instrument noise; exp-0058 REJECTED; exp-0057 INCONCLUSIVE; exp-0056 INVALID. Individual Elo estimates are **never summed**; integrated direct-dev5 measurement remains required.

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

- [x] **0.3** The distinction between RESEARCH DISPATCH pushes and the FINAL
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
      *Reconciliation:* the standing continuation instruction explicitly preserves
      the project policy that a **completion push** is blocked until mandatory
      checklist items are proved, while documented working-branch CI dispatch and
      evidence-export commits are not completion pushes. Research dispatches have
      remained confined to `arena/6a6a2ba3-stockbear` (e.g. exp-0060 dispatch
      `7bdf21c`, source pin `8e77e0f`); no merge/tag/release/deploy or completion
      push has occurred. This checks the administrative distinction only, not the
      strength gate.

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
- [x] **1.9** Published release identity remains `v0.1.0-dev5`; no public version bump, dev6/dev7 tag, release, deploy, or merge to main. The pre-existing internal DEV6 marker is preserved, not silently changed.
      *Reconciliation:* `docs/DEV6_CONTINUATION_POLICY.md` §1 follows the existing
      internal-cycle/public-release distinction in DESIGN_LOG, CHANGELOG, README,
      recovery audit and exp-0055 §9. `benchmarks/recovery/version/exp0059_identity_audit.json`,
      raw `exp0059_releases.json` and `exp0059_tags.json` verify newest public release
      dev5, no dev6/dev7 tag, main VERSION dev5 and main SHA unchanged. Branch VERSION
      remains the pre-existing dev6 marker introduced by `a7bf00f`; no identity file
      changed. No release action, merge, deploy or new PR was performed. Existing
      PR #2 belongs to a different older branch and was not touched. This is a
      repository-policy reconciliation, not a waiver of the strength gate.

## 2. Research and experiment discipline

- [x] **2.1** Every strength-tested experiment has its own preregistration committed BEFORE its first game.
      *Evidence:* `benchmarks/recovery/prereg_freeze_audit.json` recomputes, for exp-0050…0063, each prereg path, SHA-256 at its freeze commit, freeze commit and earliest benchmark-dispatch commit, and verifies `git merge-base --is-ancestor` for every dispatched experiment (`all_dispatched_pinned_before_dispatch=true`). exp-0059 had zero strength games/no benchmark dispatch (pre-game cost-instrument failure); exp-0061 was dispatched only after its prereg freeze and failed before games.
- [ ] **2.2** Each prereg specifies ID, hypothesis, mechanism, candidate/baseline hashes, frozen ADVANCE/CLOSE/INCONCLUSIVE rules, time control, opening methodology, statistics, power rationale and validity requirements.
      *Evidence:* **Audited by content, not by freeze order.**
      `scripts/recovery_prereg_content_audit.py` →
      `benchmarks/recovery/prereg_content_audit.json` records a line-level citation
      for each of the ten required elements in all **37** preregs: **36 complete**,
      and **15/15 complete** for the mission's strength-experiment preregs
      (exp-0050…exp-0064). 16 preregs resolve elements by *documented* incorporation
      of `docs/DEV6_PREREG.md` §8 (which cites `docs/DEV6_POWER_ANALYSIS.md` for
      power) or by their parent prereg for ADDENDUM/RETRY supplements; both the
      incorporating and the inherited line are stored. Narrow keyword misses were
      investigated and corrected against the actual text (e.g. exp-0056 uses
      "GATE 1 PASS / GATE 1 FAIL / INCONCLUSIVE / NEGATIVE"; exp-0054/0060/0062
      specify the mechanism as exact frozen feature values). **Sole residual:**
      `docs/DEV6_PREREG_BASELINE.md` (exp-0025) states it is "a provenance step, not
      a strength experiment", plays no games, and genuinely lacks frozen
      ADVANCE/CLOSE/INCONCLUSIVE rules, opening methodology, statistics and power
      rationale. Rule 8 forbids N/A/waiver, so this item **remains unchecked**;
      it is not passed by scoping that document away.
- [x] **2.3** No preregistered acceptance criterion was altered after results were observed.
      *Evidence:* `git log --oneline -- <path>` returns **exactly 1 commit** for every
      preregistration `docs/DEV6_PREREG_EXP0050.md` … `EXP0057.md` and for every frozen
      plan `tier1-plan-exp0053.json` … `exp0057.json` — i.e. none was ever edited after
      creation. `git merge-base --is-ancestor` confirms each prereg commit precedes its
      dispatch commit (exp-0055 `2594479`→`de20f5f`; exp-0056 `ec7c9c4`→`b769f1e`;
      exp-0057 `0f60282`→`97c7263`). The one in-flight change (exp-0055 scale eg 1→2)
      was made with **0 games played**, recorded as an appended amendment with
      `thresholds_changed: false` and the original values preserved verbatim; and
      exp-0056's failing null was **honoured**, not relaxed, producing an INVALID
      verdict against the mission's own interest. The same single-commit freeze
      holds for exp-0058/0059/0060/0061/0062 preregs and plans; exp-0062 prereg
      `b7bab412…` was created at `95606a5` before dispatch `619088f` and never
      edited after the 15,000-game result.
- [x] **2.4** Cheap pre-game checks (correctness oracle, scale, cost, liveness, mutation) preceded every substantial compute spend.
      *Evidence:* exp-0053/0054 threats oracle+mutation+ctest; exp-0055/0060 race oracle 800/0, scale, 10/10 mutants, liveness, prospective cost gate (`exp0060_validity.json`); exp-0061 battery oracle/scale/mutation/liveness then cost FAIL before games; exp-0062 no new feature enabled — enabled config had passed exp-0060 prospective cost gate and fresh suite verification PASS before 15,000 games; exp-0063 oracle 800/0, evaldata 4000/0, 11/11 mutants, liveness 12/12, ctest 18/18, bench exact, then fresh prospective cost PASS before 5,800 games (`exp0063_battery_*.json`, `exp0063_suite_verification.json`, cost verdict).
- [x] **2.5** Inconclusive/rejected experiments were preserved with full verdicts and the mission continued to a distinct next direction.
      *Evidence:* `benchmarks/FAILURE_LEDGER.md` preserves exp-0050/0051 negative, exp-0052 inconclusive, exp-0056 INVALID, exp-0057 inconclusive, exp-0058 rejected, exp-0059/0061 pre-game cost blocks, exp-0062 GATE UNMET and exp-0063 CLOSED (battery rejected); each was followed by a distinct next direction (exp-0053→0054→0055→0060→0061→0062→0063). No closed verdict was rescored.
- [x] **2.6** No inconclusive experiment was re-run without a justified preregistered reason.
      *Evidence:* Ledger cross-check: exp-0052 was not rerun; exp-0056 INVALID was not retried as the same integral claim; exp-0057/0058 closed; exp-0060 was a preregistered technical replacement for exp-0059’s failed pre-game cost instrument with zero exp-0059 strength data; exp-0062 is a new direct integral design, not a rerun of an inconclusive experiment.
- [x] **2.7** The strategy is not blind summation of individually inconclusive candidates.
      *Evidence:* exp-0062 measured the integrated threats+race candidate DIRECTLY vs published dev5 (`docs/DEV6_EXP0062_REPORT.md`, run 42356232866): +40.7732 [+36.2091,+45.3513]. The report explicitly forbids summing exp-0054 +23.5374 and exp-0060 +27.0085; exp-0056’s invalid face value remains withheld.

## 3. Confirmed improvements and final candidate integration

- [x] **3.1** At least one improvement is CONFIRMED under its own adequately powered preregistered confirmation (not a screen, not an inconclusive result).
      *Evidence:* `docs/DEV6_EXP0054_REPORT.md` and
      `benchmarks/recovery/exp0054_independent_raw_audit.json` — ThreatDetection,
      4,000 combined games, **+23.5374 Elo, 95% CI [+15.6937, +31.4052]**, both
      batches positive (+20.38 / +26.70), all 7 frozen conditions PASS, audit
      issues 0, 4,800/4,800 PGN replayed. Prereg SHA
      `48e800e804dbaa27b32d369c368b3c7baed42c931a6d6236bc1166a4d5b993ea` committed
      at `dfb4838` before run 42244166583. NOT pooled with the exp-0053 screen.
- [x] **3.2** Every component of the final candidate is individually supported by adequate independent evidence.
      *Evidence:* ThreatDetection: exp-0054 CONFIRMED +23.5374 [+15.6937,+31.4052] vs dev5 (`docs/DEV6_EXP0054_REPORT.md`). PassedPawnRace increment: exp-0060 CONFIRMED +27.0085 [+20.8746,+33.1592] over threats in the identical binary (`docs/DEV6_EXP0060_REPORT.md`). Both had powered nulls and independent audits; the final candidate contains only these two enabled components.
- [x] **3.3** The final integrated candidate was measured DIRECTLY against the gate baseline; its strength was not inferred by adding individual Elo estimates.
      *Evidence:* exp-0062 raw records + independent audit: `benchmarks/exp-runs/tier1-export/run-42356232866`, `benchmarks/recovery/exp0062_independent_raw_audit.json`, `docs/DEV6_EXP0062_REPORT.md`. Direct candidate-vs-dev5 primary combined +40.7732 [+36.2091,+45.3513]; no component summation.
- [x] **3.4** All non-qualifying experimental features remain default-OFF in the shipped configuration.
      *Evidence:* Shipped/default configuration remains bit-exact: all three established bench signatures exact with experimental rows default-zero (`exp0061_bench_signatures.log`, `tests/unit/test_eval_baseline.cpp` pin `0x64662610d489aade`). KingSliderBattery is default 0/0 and was not enabled in exp-0062; candidate race config sha `82f93ba7…` enables only ThreatDetection/PassedPawnRace.

## 4. Final strength measurement (the non-waivable gate)

- [ ] **4.1** The final candidate achieves a **two-sided opening-clustered 95% CI lower bound STRICTLY GREATER THAN +50 Elo** against the designated bit-identical released baseline under fixed-time **40+4 ms**.
      *Evidence:* **FAIL / UNMET** — exp-0062 independent audit LCB = **+36.2091** (point +40.7732, CI [+36.2091,+45.3513]) vs exact dev5; gate also requires point ≥ +75. `benchmarks/recovery/exp0062_validity.json` verdict GATE_UNMET, gate1_met=false. A lower bound equal to +50 would also fail; this is strictly below.
- [x] **4.2** The comparison used the established frozen protocol: Hash 16, Threads 1, max-plies 240, fixed time (never node budget), established opening-cluster methodology and CR1/t interval.
      *Evidence:* exp-0062 per-job `fingerprint.json`/`match.jsonl` independently verified by `recovery_exp0062_validity.py` (17/17): control {base_ms:40,inc_ms:4}, hash 16, threads 1, max_plies 240, TTEval=true; CR1/t opening-clustered interval; fresh disjoint opening suites; no node budget.
- [x] **4.3** No frozen rule (openings, time control, clustering, CI method, adjudication) was changed after observing results.
      *Evidence:* Prereg `docs/DEV6_PREREG_EXP0062.md` sha `b7bab412…` frozen at `95606a5` before dispatch; exported fingerprints carry the same prereg sha and plan jobs. No post-result edit: validity check `source_prereg_protocol` PASS; git history shows the prereg/plan created before run 42356232866.
- [x] **4.4** The final sample size meets or exceeds the preregistered final size.
      *Evidence:* Raw JSONL reconciliation: 15,000 games dispatched/replayed (6,600+6,600+1,200+600). Primary dispatched 13,200 as preregistered; 13,170 scored after the pre-declared symmetric max-ply exclusions (batchA 11, batchB 19). Nulls 1,197 and 599 scored. Auditor replay counts match exactly.
- [x] **4.5** Both independent batches are positive and reasonably consistent (if the frozen rule requires it).
      *Evidence:* Independent per-batch estimates: batchA +38.3422 [+31.8866,+44.8242], batchB +43.2141 [+36.7652,+49.6928]; both positive, gap 4.87 Elo, combined +40.7732. No batch-label overlap (auditor).

## 5. Statistical and data-integrity validation

- [x] **5.1** All final game records were independently recomputed from raw per-game JSONL by an auditor sharing no code with the summary producer.
      *Evidence:* `scripts/recovery_independent_audit.py` (shares no code with summary producer) recomputed all exp-0062 jobs from raw `match.jsonl`; output `benchmarks/recovery/exp0062_independent_raw_audit.json`, log `exp0062_independent_audit.log`; TOTAL ISSUES 0.
- [x] **5.2** Every final PGN was fully replayed; all moves legal; all outcomes consistent with records.
      *Evidence:* Auditor PGN replay: batchA 6,600, batchB 6,600, null 1,200, stage0 600 = **15,000/15,000**, inconsistent=0 in every job (`exp0062_independent_raw_audit.json`).
- [x] **5.3** Zero time forfeits, illegal moves, engine failures or unexplained game failures in the final run (or each is explicitly accounted for under a pre-declared symmetric policy).
      *Evidence:* Raw termination histograms: TIME_FORFEIT=0, ILLEGAL=0, ENGINE_FAILURE=0 in all four jobs. The only primary exclusions are 30 pre-declared symmetric UNADJUDICATED_MAX_PLIES games (11+19); null exclusions 3+1 under the same policy.
- [x] **5.4** All validity nulls have CIs including zero.
      *Evidence:* Candidate null −2.0369 [−11.8305,+7.7534] and stage0 null −7.5541 [−22.7984,+7.6611] both include zero (independent auditor; validity checks `null_null_includes_zero` and `stage0_null_includes_zero` PASS).
- [x] **5.5** All committed blob digests and per-job `SHA256SUMS` verify.
      *Evidence:* Auditor: committed blobs **54/54** match; per-job SHA256SUMS **44/44** verified. Validity script independently re-hashed all 44 per-job files and matched recorded input-file digests for both configs.
- [x] **5.6** Every file-valued UCI option has positive per-arm load proof; no silent fallback occurred.
      *Evidence:* Per-arm positive load proofs in exported `option_probe_A/B.txt` and auditor `option_load_proof`: batchA/B race vs champion, null race/race, stage0 champion/champion; no `could not load` fallback. Validity check PASS.
- [x] **5.7** Arm binary identities match the declared design and the pinned baseline digest.
      *Evidence:* Fingerprints/configs: candidate arms built==packaged==tested sha `a32f082b869e…`; primary baseline arms sha `391cb50e13ab…` exactly equal pinned published dev5; null/stage0 arms identical candidate binary. Validity `binary_identities` PASS.
- [x] **5.8** Auditor total issues = 0.
      *Evidence:* `benchmarks/recovery/exp0062_independent_raw_audit.json` has `issues: []`; auditor log ends `TOTAL ISSUES: 0 / INDEPENDENT AUDIT PASS`.

## 6. Engine correctness and regression testing

- [x] **6.1** Perft and move-generation correctness tests pass.
      *Evidence:* run individually at 2026-11-07: `perft_quick` exit **0** (`Tests: 2,
      failures: 0`), `perft_full` exit **0** (`Tests: 1, failures: 0`), `position_extra`
      exit **0** (`Tests: 4, failures: 0`), `unit` exit **0** (`Tests: 41, failures: 0`,
      includes move-generation/geometry).
- [x] **6.2** Every registered automated test EXECUTES and returns a successful exit code — verified individually, not inferred from a green CTest summary.
      *Evidence:* after registering `king_slider_battery`, all **18** registered
      tests were invoked one-by-one (`ctest -R '^name$'`) with each exit captured;
      `benchmarks/recovery/exp0063_individual_ctest.log` (and earlier `exp0061_individual_ctest.log`) records `registered=18`,
      18 `EXIT=0` lines and `ANY_FAILURE=0`. Earlier direct group run had 14 C++
      groups / 110 assertions plus 3 Python integration tests; the new C++ group
      adds 4 assertions (live contribution, exact blockers, cap, ortho/diag split).
- [x] **6.3** Every new test group is actually registered with `add_test()` and appears in CTest output.
      *Evidence:* `CMakeLists.txt` registers `passed_pawn_race` and
      `king_slider_battery`; `ctest -N` lists `Test #9: passed_pawn_race`,
      `Test #10: king_slider_battery` and **Total Tests: 18**. Both execute
      individually in `exp0061_individual_ctest.log`. (This check exists because
      exp-0052's `king_safety` group was initially never registered.)
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
      afterwards). Battery mechanism: exp-0061 8/8 KILLED and exp-0063 optimized
      implementation **11/11 KILLED** (`exp0063_battery_mutation_matrix.json`),
      including both ray-mask-empty mutants and queen-ignored on both ray classes.
      Earlier mechanisms: threats 7/7 KILLED, king-safety 3/3 KILLED.
- [x] **6.8** Performance/resource overhead measured with a calibrated instrument and within the declared budget.
      *Evidence:* exp-0060 prospective fail-closed CI cost gate,
      `benchmarks/exp-runs/tier1-export/run-42352690063/cost-gate-exp0060-run42352690063/verdict.json`
      and raw `aa_raw.json` / `increment_raw.json` / `combined_raw.json`.
      Median-of-3 paired instrument: A/A spread **0.01551 < 0.10**, A/A median
      **0.99977** in [0.98,1.02]; race increment median **1.02066 ≤ 1.05**;
      threats+race vs champion median **1.09025 ≤ 1.10**. All 13 cost-gate
      checksums verify; gate ran before any game. Historical exp-0055 cost JSON
      was not retroactively budgeted; exp-0059’s failed local calibrations are
      preserved as a pre-game instrument failure, not a pass. exp-0063 battery
      optimization also passed a fresh prospective gate before games: A/A spread
      0.02631, increment median **1.04470 ≤1.05**, combined **1.08861 ≤1.10**
      (`run-42365991406/cost-gate-exp0063-run42365991406/verdict.json`, 13/13 sums);
      exp-0061’s failed gate remains a failure, not retroactively budgeted.
- [x] **6.9** No unintended regression in existing engine functionality.
      *Evidence:* 2026-11-07 at HEAD `1ea329c` (engine tree unchanged since
      `2594479`): `benchmarks/recovery/exp0060_ctest.log` — **17/17 passed,
      ctest_exit=0**; `benchmarks/recovery/exp0060_bench_signatures.log` — exact
      depth-4 `243f9a1c1ba5b36f`, depth-6 `e06c4352681ae8eb`, depth-7
      `5bceff035f2a4ae4`. Node-budget self-play sanity (not strength evidence):
      `exp0060_selfplay_sanity.log` reports 2 games / 101 positions / 0 discarded;
      `exp0060_selfplay_sanity_validation.json` validates all 101 emitted FEN rows
      with python-chess, 0 invalid. Initial `.pgn` extension was a labeling error
      and was corrected to `.txt` before any strength claim.

## 7. Final artifact and reproducibility audit

- [x] **7.1** The final executable identity is verified and its hash recorded.
      *Evidence:* Packaged candidate binary SHA-256 `a32f082b869e6bd2f318691e6760026aaad2c23cbcee201205f598b1eaf1da3d`, equal to built and tested binary in every candidate arm (`fingerprint.json`, validity `binary_identities`).
- [x] **7.2** The baseline executable identity is verified and its hash recorded.
      *Evidence:* Baseline executable SHA-256 `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`, matched to the pinned published dev5 digest in fingerprints and runner assertion (`dev5 baseline sha256 … VERIFIED`).
- [x] **7.3** The final source SHA, prereg SHA and opening-suite SHA are pinned and enforced in the run.
      *Evidence:* Fingerprints enforce source sha `95606a513c4cc96231fbbba89e04165348c23fbb`, prereg sha `b7bab412…`, opening-suite shas (batchA `efeaac4d…`, batchB `8761cc60…`, null `e33350c2…`, stage0 `12be22cc…`); runner verifies pinned plan/prereg/baseline before games.
- [x] **7.4** Raw records, PGNs, checksums, configs and analysis scripts are committed and reproducible.
      *Evidence:* Export directory `benchmarks/exp-runs/tier1-export/run-42356232866` contains raw JSONL/PGN/CSV, configs, fingerprints, probes, checksums and packages; analysis scripts `recovery_independent_audit.py` and `recovery_exp0062_validity.py` are committed and were re-run locally to reproduce the audit/validity JSONs.
- [x] **7.5** Results reproduce on the actual execution environment.
      *Evidence:* Execution environment documented in each `match.jsonl` configuration (host/machine/python_chess) and `export_manifest.json`; GitHub-hosted ubuntu-latest run 42356232866 succeeded. Independent local re-analysis of the exported raw records reproduces the combined +40.7732 [+36.2091,+45.3513] and all null intervals.
- [ ] **7.6** No build artifacts, large datasets or unclear-licensing assets were committed.
      *Evidence:* `scripts/recovery_artifact_hygiene_audit.py` →
      `benchmarks/recovery/artifact_hygiene_audit.json`, over all **3,117** tracked
      files and the **2,342** files added by this branch.
      **Build artifacts: NONE** — zero matches for build directories, object
      files, static/shared libraries, CMake caches, `*.pyc`, `node_modules`;
      `.gitignore` covers `build/`, `build-*/`, `cmake-build-*/`, `out/`, `dist/`,
      `*.o`, `*.a`, and `git check-ignore -v` confirms `build-rel` and
      `build-ttdiag` are ignored. **Unclear licensing: NONE** — every generated
      corpus manifest declares "original data generated by this project;
      Apache-2.0", a root `LICENSE` exists, and no vendored/third-party/NNUE/
      tablebase asset was added. The only tracked ELF files are this project's
      **own published release executables** pinned as immutable comparison targets
      (`benchmarks/binaries/stockbear-dev5-release`,
      `benchmarks/binaries/stockbear-dev4-1c5b61a7`,
      `benchmarks/exp-runs/exp0025-baseline/extract/stockbear`) — required
      provenance evidence, **not** transient build outputs.
      **Large datasets: PRESENT** — the branch adds **303.16 MB**, including
      **221.00 MB** of immutable raw per-game tier1 evidence (PGN/JSONL/CSV) and
      **12.75 MB** of frozen opening/diagnostic suites. This data is mandated by the
      durable-evidence and independent-replay requirements and is **not** deleted;
      but it is a large dataset under the plain wording, so this item **remains
      unchecked** rather than being waived or reworded into a pass.

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
- [x] **8.7** Final report contains all nine required elements (candidate SHA, baseline identity, games/W-D-L/Elo/CI, explicit LCB > +50 confirmation, independent recomputation evidence, correctness/CI results, checklist path, remote SHA, disclosed limitations).
      *Evidence:* `docs/DEV6_FINAL_REPORT_20261107.md` §§1–8: candidate/source/binary SHAs, dev5 baseline digest, exp-0062 games/W-D-L/+40.7732 [+36.2091,+45.3513], explicit “LCB > +50 is NOT confirmed”, independent auditor/replay evidence, ctest/bench/CI run 42367825791, checklist path/counts, audit HEAD/remote SHA, and disclosed limitations/blockers. This does not authorize a completion push; §8.3 remains blocked by §4.1.

---

## Current disposition

**MISSION INCOMPLETE.** The gate is the frozen dev6 gate: **point >= +75 Elo AND
two-sided opening-clustered 95% LCB strictly > +50 vs the released dev5
champion** at 40+4 ms.

Progress: exp-0050/0051 closed negative; exp-0052 inconclusive; exp-0053 screen
advance; **exp-0054 CONFIRMED threats (+23.54 [+15.69,+31.41])**; exp-0055 screen
advance; exp-0056 INVALID integral; exp-0057 inconclusive; exp-0058 rejected;
exp-0059 pre-game cost failure; **exp-0060 CONFIRMED race increment (+27.01
[+20.87,+33.16])**; exp-0061 battery BLOCKED pre-game on cost; **exp-0062 VALID
direct integral threats+race vs dev5: +40.7732 [+36.2091,+45.3513], GATE UNMET**;
exp-0063 optimized battery cost PASS but screen **CLOSED/rejected (−6.03
[−14.15,+2.08])**.
The integrated candidate now has a valid direct dev5 estimate, but it is far
below the +75 / LCB>+50 gate (UCB +45.35 < +75). Component Elo is not additive.
Further distinct source-grounded improvements and a new direct integrated gate
measurement are required before any completion push. No merge/tag/release is
authorized.
