# exp-0062 — VALID DIRECT INTEGRAL MEASUREMENT / GATE UNMET

**Verdict: VALID MEASUREMENT — GATE 1 UNMET.** The integrated threats+race
candidate was measured directly against the exact published dev5 artifact under
the frozen Gate-1 protocol. The independent opening-clustered estimate is
**+40.7732 Elo, two-sided 95% CI [+36.2091, +45.3513]** on the fixed primary
sample. This is **below** the required point estimate ≥ +75 and **below** the
required LCB > +50; indeed the entire 95% interval lies below +75. No release,
merge, tag or completion push is authorized.

This is the first **valid** integral dev5 estimate for the current best candidate.
It supersedes no closed verdict: exp-0056 remains INVALID and its face value is
withheld; exp-0054 and exp-0060 component estimates are **not summed**.

## Frozen registration and identities

- Prereg: `docs/DEV6_PREREG_EXP0062.md`, SHA-256
  `b7bab412fe0a2c6ca992e188c4d42b14cf9450e86dbdefb1e8004363c6a90365`, frozen at
  `95606a513c4cc96231fbbba89e04165348c23fbb` before dispatch `619088f`.
- Plan: `benchmarks/exp-runs/tier1-plan-exp0062.json`; budget:
  `benchmarks/recovery/exp0062_compute_budget.json` (15,000 games max, 1,700
  workflow VM-minutes max, one benchmark dispatch + one export dispatch).
- Benchmark run **42356232866** SUCCESS; export run **42364780824** SUCCESS;
  raw mirror `benchmarks/exp-runs/tier1-export/run-42356232866` (export commit
  `c6dab73bfe5809c80878c6be7ab7c3fc518d8b98`).
- Candidate binary SHA-256 (built == packaged == tested in all candidate arms):
  `a32f082b869e6bd2f318691e6760026aaad2c23cbcee201205f598b1eaf1da3d`.
- Baseline: exact published dev5, SHA-256
  `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`.
- Candidate config: `research-data/params_exp0055_race.txt`, SHA-256
  `82f93ba7a7b7e8e757c245098f5e2c4f42c866aa25124c73d0ad67ad11f89f01`
  (ThreatDetection 1/1, PassedPawnRace 0/2; KingSliderBattery default 0/0).
- Baseline config: `research-data/params_abc.txt`, SHA-256
  `8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be`.
- Protocol: fixed **40+4 ms**, Hash 16, Threads 1, max-plies 240, TTEval=true;
  flags `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`. Fresh openings seed
  **2026110662**, 7,500 openings, independently verified disjoint from all
  earlier committed suites (`exp0062_suite_verification.json`, PASS).

## Results (independent recomputation from raw JSONL/PGN)

| arm | games replayed | scored | W/D/L | Elo | 95% CI |
|---|---:|---:|---|---:|---|
| batchA | 6,600 | 6,589 | 2661/1990/1938 | +38.3422 | [+31.8866, +44.8242] |
| batchB | 6,600 | 6,581 | 2691/2017/1873 | +43.2141 | [+36.7652, +49.6928] |
| **primary combined** | **13,200** | **13,170** | **5352/4007/3811** | **+40.7732** | **[+36.2091, +45.3513]** |
| candidate null | 1,200 | 1,197 | 408/376/413 | −2.0369 | [−11.8305, +7.7534] |
| stage0 null | 600 | 599 | 195/196/208 | −7.5541 | [−22.7984, +7.6611] |

Primary exclusions are the pre-declared symmetric `UNADJUDICATED_MAX_PLIES`
policy: batchA 11, batchB 19 (30 total). Nulls are never pooled. Independent
cluster bootstrap for the primary: [+36.1960, +45.3914], consistent with CR1/t.

## Validity and integrity

`scripts/recovery_exp0062_validity.py` → `benchmarks/recovery/exp0062_validity.json`:
**17/17 condition checks PASS**, verdict `GATE_UNMET`, `gate1_met=false`.

- Independent auditor `scripts/recovery_independent_audit.py` (shares no code
  with the summary producer): **TOTAL ISSUES 0**;
  `benchmarks/recovery/exp0062_independent_raw_audit.json`.
- **15,000/15,000 PGNs replayed**, 0 inconsistent; zero time forfeits, illegal
  moves or engine failures in every job.
- Committed blobs **54/54** match; per-job SHA256SUMS **44/44** independently
  verified; frozen config asset digests match recorded input files.
- Positive per-arm file-option load proofs; arm binary identities match the
  declared design (candidate arms use the packaged source-pin binary; primary
  baseline arms use the exact dev5 digest).
- Both powered null CIs include zero. Stage0 fresh ctest **18/18** registered
  groups passed on the packaged candidate.
- No new feature was enabled; the enabled threats+race configuration had passed
  the prospective exp-0060 CI cost gate (combined median 1.09025 ≤ 1.10), and the
  default-off battery row preserves all three established bench signatures.

## Gate decision and consequences

Frozen rule: **GATE MET iff point ≥ +75 AND LCB > +50** on the fixed combined
primary sample with all validity conditions. Observed point **+40.7732** and LCB
**+36.2091** fail both clauses. The upper bound **+45.3513** is also below +75,
so this sample decisively rejects the gate for this configuration rather than
leaving it merely underpowered.

- Best valid direct integral candidate: **threats+race**, +40.7732
  [+36.2091, +45.3513] vs published dev5 at 40+4 ms.
- Gate 1: **UNMET**. Gate 2 (confirmed components): supported by exp-0054 and
  exp-0060, but not additive. Gate 3 (correctness/integrity): PASS for this run.
  Gate 4 (completion authorization): **UNMET**.
- exp-0061 battery remains **BLOCKED BEFORE GAMES** on cost; it was not enabled
  here and contributes no strength evidence.
- No merge, tag, release, prerelease, deploy or new PR; PR #2 untouched.
  `origin/main` remains `6e7c2e0`; public release identity remains dev5.

Mission remains **ACTIVE / INCOMPLETE**. Any further attempt must be a distinct
source-grounded direction (or a semantics-preserving optimization of a blocked
mechanism) with a fresh preregistration, the same gate, and a new direct
integrated measurement; component Elo may never be summed to claim the gate.
