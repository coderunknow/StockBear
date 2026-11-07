# StockBear DEV6 — INTERIM consolidated report (2026-11-07)

**Mission status: ACTIVE / INCOMPLETE — gate unmet.**
**This is an INTERIM report, not a final one.** Research continues; a final
report may only be written once the gate is demonstrated or a genuine external
hard blocker is established. A negative experiment, an unmet gate, an unchecked
checklist or a finished batch is NOT a stopping condition.
The best valid integrated candidate is **threats+race**, measured directly
against the exact published dev5 artifact at **+40.7732 Elo, 95% CI
[+36.2091, +45.3513]** under the frozen 40+4 ms protocol. Gate 1 requires
**point ≥ +75 AND LCB strictly > +50**. Both clauses fail; the entire interval
lies below +75. No merge, tag, release, prerelease, deploy or completion push is
authorized.

## 1. Repository / candidate / baseline identities

- Branch: `arena/6a6a2ba3-stockbear`.
- Audit HEAD: `ef7c1782636d13279c5008a6f876d8d4015b40e1`; tree
  `e810948133a060cdbbbf6d6e9003e3bb094aea2a`. Remote branch verified equal at
  audit time; this report is committed immediately afterward on the same branch.
- `origin/main`: unchanged at `6e7c2e02881faf93a84990a8345c41ad28bcae11`.
- Public release identity: `v0.1.0-dev5` only; internal VERSION remains
  `0.1.0-dev6`. No dev6/dev7 tag or release exists.
- Gate baseline: published dev5 binary SHA-256
  `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`.
- Best candidate source pin (exp-0062):
  `95606a513c4cc96231fbbba89e04165348c23fbb`; candidate binary SHA-256
  `a32f082b869e6bd2f318691e6760026aaad2c23cbcee201205f598b1eaf1da3d`.
- Candidate config: `research-data/params_exp0055_race.txt`, SHA-256
  `82f93ba7a7b7e8e757c245098f5e2c4f42c866aa25124c73d0ad67ad11f89f01`
  (ThreatDetection 1/1, PassedPawnRace 0/2; KingSliderBattery default 0/0).
- Baseline config: `research-data/params_abc.txt`, SHA-256
  `8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be`.

## 2. Gate measurement (exp-0062) — valid, gate unmet

- Prereg `docs/DEV6_PREREG_EXP0062.md`, SHA-256
  `b7bab412fe0a2c6ca992e188c4d42b14cf9450e86dbdefb1e8004363c6a90365`, frozen
  before dispatch. Run **42356232866** SUCCESS; export **42364780824** SUCCESS.
- Raw mirror: `benchmarks/exp-runs/tier1-export/run-42356232866`.
- Protocol: fixed **40+4 ms**, Hash 16, Threads 1, max-plies 240, TTEval=true;
  fresh openings seed 2026110662, independently verified disjoint; CR1/t
  opening-clustered two-sided 95% interval; symmetric max-ply exclusion.
- Primary: **13,200 games dispatched**, **13,170 scored**, W/D/L
  **5352/4007/3811**, 6,570 clusters. batchA +38.3422 [+31.8866,+44.8242];
  batchB +43.2141 [+36.7652,+49.6928].
- **Combined: +40.7732 [+36.2091, +45.3513]**; bootstrap [+36.1960,+45.3914].
- Nulls: candidate −2.0369 [−11.8305,+7.7534]; stage0 −7.5541
  [−22.7984,+7.6611]; both include zero.
- **Explicit gate confirmation: LCB > +50 is NOT confirmed.** LCB = +36.2091;
  point = +40.7732 < +75; UCB = +45.3513 < +75. Verdict `GATE_UNMET`,
  `gate1_met=false` in `benchmarks/recovery/exp0062_validity.json` (17/17 checks).

## 3. Independent recomputation and data integrity

- Auditor: `scripts/recovery_independent_audit.py` (shares no code with the
  summary producer). Output:
  `benchmarks/recovery/exp0062_independent_raw_audit.json`, log
  `benchmarks/recovery/exp0062_independent_audit.log`; **TOTAL ISSUES 0**.
- **15,000/15,000 PGNs replayed**, 0 inconsistent; zero time forfeits, illegal
  moves or engine failures. Committed blobs **54/54**; per-job SHA256SUMS
  **44/44**; positive per-arm file-option load proofs; exact dev5 baseline digest.
- exp-0063 battery screen was independently audited the same way:
  `exp0063_independent_raw_audit.json`, validity 16/16, 5,800/5,800 replay,
  68/68 blobs, 44/44 job sums, 13/13 cost sums, issues 0.

## 4. Immutable verdicts (valid vs invalid)

| experiment | verdict | key estimate / reason |
|---|---|---|
| exp-0050/0051 | CLOSED negative | correction history / PST fixed-time negative |
| exp-0052 | INCONCLUSIVE | king-safety quadratic +4.2031 (historical anchor, not pooled) |
| exp-0053 | SCREEN ADVANCE | threats screen +24.6338 |
| exp-0054 | CONFIRMED | threats vs dev5 **+23.5374 [+15.6937,+31.4052]** |
| exp-0055 | SCREEN ADVANCE | race screen +25.9606 |
| exp-0056 | **INVALID** | null excluded 0; face value withheld |
| exp-0057 | INCONCLUSIVE | +11.7020 |
| exp-0058 | REJECTED | CaptureHistory −2.5342 |
| exp-0059 | BLOCKED pre-game | cost-instrument A/A noise; zero games |
| exp-0060 | CONFIRMED INCREMENT | race over threats **+27.0085 [+20.8746,+33.1592]** |
| exp-0061 | BLOCKED pre-game | battery cost FAIL (1.17094 / 1.25063); zero games |
| exp-0062 | **VALID / GATE UNMET** | direct threats+race vs dev5 **+40.7732 [+36.2091,+45.3513]** |
| exp-0063 | VALID / CLOSED | optimized battery cost PASS (1.04470 / 1.08861), screen **−6.0300 [−14.1476,+2.0809]**, mechanism rejected |

Component Elo is **never summed**. exp-0062 is the only valid direct integral
dev5 estimate for the current best candidate. exp-0056 remains invalid and is
not used. Closed experiments were not reopened or rescored.

## 5. Correctness, cost and CI

- Registered tests: **18/18**, invoked individually in
  `benchmarks/recovery/exp0063_individual_ctest.log` (`registered=18`,
  `ANY_FAILURE=0`); stage0 CI ctest 18/18 in both exp-0062 and exp-0063.
- Default shipped behavior bit-exact: bench depth-4 `243f9a1c1ba5b36f`, depth-6
  `e06c4352681ae8eb`, depth-7 `5bceff035f2a4ae4`; eval-table pin
  `0x64662610d489aade`.
- Battery correctness: oracle 800/0 (197 non-zero), evaldata 4000/0, mutation
  matrices 8/8 (exp-0061) and 11/11 (exp-0063), liveness depth-8 12/12 trees.
- Prospective cost gates: exp-0060 enabled threats+race PASS (increment 1.02066,
  combined 1.09025); exp-0061 battery FAIL; exp-0063 optimized battery PASS
  (increment 1.04470, combined 1.08861) before its screen.
- CI on audit HEAD `ef7c178`: run **42367825791** **success**, all 9 jobs green,
  including Linux ThreadSanitizer and Linux ASan + UBSan.

## 6. Checklist audit

`STOCKBEAR_COMPLETION_CHECKLIST.md`: **49 checked / 9 open / 58 total**
(`benchmarks/recovery/checklist_audit_20261107.json`; append-only violation
false; raw-artifact non-additions empty). The nine open items are **2.2, 4.1,
7.6 and 8.1–8.6**:

- **2.2 — audited BY CONTENT, still open.**
  `scripts/recovery_prereg_content_audit.py` →
  `benchmarks/recovery/prereg_content_audit.json` locates each of the ten required
  elements in every prereg with a line-level citation. Result: **36/37 complete**,
  and **15/15** of the mission's strength-experiment preregs (exp-0050…0064)
  complete. Sixteen preregs resolve one or more elements by *documented*
  incorporation (`docs/DEV6_PREREG.md` §8, which cites
  `docs/DEV6_POWER_ANALYSIS.md`) or by their parent prereg for ADDENDUM/RETRY
  files; both the incorporating line and the inherited line are recorded.
  The single residual is `docs/DEV6_PREREG_BASELINE.md` (exp-0025), which
  self-declares "a provenance step, not a strength experiment", plays no games,
  and therefore genuinely has no frozen ADVANCE/CLOSE/INCONCLUSIVE rules, opening
  methodology, statistics or power rationale. Because checklist rule 8 forbids
  N/A or waiver, **2.2 remains unchecked** rather than being passed by scoping
  that document away.
- **4.1** non-waivable strength gate: **FAIL** (LCB +36.2091, point +40.7732).
- **7.6 — investigated and distinguished, still open.**
  `scripts/recovery_artifact_hygiene_audit.py` →
  `benchmarks/recovery/artifact_hygiene_audit.json`: **zero** build-artifact
  matches across 3,117 tracked files; `.gitignore` covers `build/`, `build-*/`,
  `cmake-build-*/,` `out/`, `dist/`, `*.o`, `*.a`, and both local build directories
  are confirmed ignored. The only tracked ELF files are this project's **own
  published release executables** pinned as immutable comparison targets
  (`stockbear-dev5-release`, `stockbear-dev4-1c5b61a7`, and the exp-0025
  extraction) — provenance evidence, not transient build outputs. Licensing is
  clean: every generated corpus manifest declares "original data generated by
  this project; Apache-2.0" and no vendored third-party asset was added.
  **However**, the branch commits **303.16 MB** across 2,342 added files, of which
  **221.00 MB** is immutable raw per-game tier1 evidence and **12.75 MB** frozen
  opening suites. That data is mandated by the durable-evidence and
  independent-replay requirements and must not be deleted, but it is still a
  large dataset under the plain wording of 7.6, so **7.6 remains unchecked**.
- **8.1–8.6** completion push authorization blocked by §4.1 (and the open §2.2 /
  §7.6 audit items). No completion push has been made.

## 7. Blockers and research disposition

The blocker is the **non-waivable strength gate**, not infrastructure or
correctness. The best candidate is decisively below gate in the fixed 13,200-game
primary sample (UCB +45.35 < +75). The battery representational direction is now
closed by game evidence after a cost-passing optimized screen. Remaining surveyed
directions are low-prior or cost-risky: single-feature passer support (negative
bundle ancestry, likely cost >5%), continuation/counter-move ordering (ordering
family failures), TT history-context relaxation (draw-soundness risk, rejected),
and speed-only micro-optimizations (bounded ~+3–8 Elo, cannot reach +75). None
has positive game evidence or a credible standalone path to +75 / LCB>+50.

Any continuation must introduce a distinct source-grounded hypothesis with a
fresh preregistration, prospective correctness/cost gates, numeric budget, and a
new direct integrated dev5 measurement. It must not sum component estimates,
reuse a failed cost gate as a pass, or reinterpret closed verdicts.

## 8. Authorization / release safety

- No merge to main; `origin/main` remains `6e7c2e0`.
- No new tag, release, prerelease or deploy; latest public release remains
  `v0.1.0-dev5`.
- Pre-existing PR #2 remains OPEN and untouched (its head is a different historical
  branch, not this session branch).
- All work is on `arena/6a6a2ba3-stockbear`; research dispatch/evidence pushes are
  not completion pushes. The final completion push remains unauthorized.
