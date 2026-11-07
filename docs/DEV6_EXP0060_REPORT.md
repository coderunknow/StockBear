# exp-0060 — VALID MEASUREMENT / CONFIRMED INCREMENT (passed-pawn race)

**Verdict: CONFIRMED INCREMENT.** The exp-0055 passed-pawn race term is confirmed
on an independent fixed-time sample: **+27.0085 Elo, two-sided opening-clustered
95% CI [+20.8746, +33.1592]** over threats-only in the identical candidate binary.
This is **not** an integral measurement against published dev5 and **not** Gate 1.
Do not add it to exp-0054; the integrated candidate must be measured directly.

## Frozen registration and compute

- Prereg: `docs/DEV6_PREREG_EXP0060.md`, SHA-256
  `24f143ccb4e524469e322626e14f8690e226ab29ee9d537f15ddf345353e2a18`,
  committed at `8e77e0fec3ee4d919b6aedfc02f89cb9d5c19950` before dispatch `7bdf21c`.
- Technical replacement for exp-0059, which closed **before games** after two
  failed A/A cost calibrations. No exp-0059 strength data existed. exp-0060 changed
  only the pre-game cost instrument/environment, not the scientific contrast or
  strength thresholds.
- Benchmark run **42352690063** SUCCESS; export run **42354629242** SUCCESS,
  raw mirror `benchmarks/exp-runs/tier1-export/run-42352690063`.
- Exactly 7,800 games: 6,000 primary + 1,200 candidate null + 600 stage0.
  Four 420-minute benchmark jobs; prepare/export capped at 10 minutes each.

## Prospective cost gate (checklist 6.8)

The fail-closed prepare-job gate passed before any game:
`benchmarks/exp-runs/tier1-export/run-42352690063/cost-gate-exp0060-run42352690063/verdict.json`.
Median-of-3 paired instrument, 60 A/A + 90 A/B blocks:

| check | value | limit | result |
|---|---:|---:|---|
| A/A spread p90−p10 | 0.01551 | <0.10 | PASS |
| A/A median | 0.99977 | [0.98,1.02] | PASS |
| race increment median | 1.02066 | ≤1.05 | PASS |
| threats+race vs champion median | 1.09025 | ≤1.10 | PASS |

All 13 cost-gate checksums verify. This is a resource diagnostic, not strength.

## Independent results

Auditor: `scripts/recovery_independent_audit.py --pgn-replay`; output
`benchmarks/recovery/exp0060_independent_raw_audit.json` / `.log`.

| job | W/D/L | scored | complete pairs | CR1 Elo | 95% CI |
|---|---:|---:|---:|---:|---|
| batchA | 1165/905/919 | 2989 | 1489 | +29.0007 | [+20.2491,+37.7892] |
| batchB | 1179/853/963 | 2995 | 1495 | +25.0260 | [+16.4271,+33.6557] |
| **combined primary** | **2344/1758/1882** | **5984** | **2984** | **+27.0085** | **[+20.8746,+33.1592]** |
| candidate null | 401/391/403 | 1195 | 595 | −0.8759 | [−11.6011,+9.8476] |
| stage0 null | 201/191/207 | 599 | 299 | −3.4861 | [−18.3424,+11.3574] |

Bootstrap cross-check combined: [+20.8081,+33.1086]. Batch label overlap 0.
Capped max-ply games were excluded symmetrically through complete pairs; no
forfeits/illegal/failures.

## Validity — condition-by-condition

`scripts/recovery_exp0060_validity.py` -> `benchmarks/recovery/exp0060_validity.json`.
All 16 checks PASS, including: cost gate before games; source/prereg/protocol;
identical arm binaries (`9da443d13fcb…`, built=packaged=A=B in every job); explicit
EvalParams/TTEval options; identical recorded defaults; both null CIs include zero;
auditor issues 0; committed blobs 68/68; per-job sums 44/44; positive load proofs;
7,800/7,800 PGN replay, 0 inconsistent; fresh disjoint openings; stage0 ctest 17/17.

## Frozen decision

Point ≥ +20, LCB > 0, both batch points ≥ −5, all validity conditions pass:
**CONFIRMED INCREMENT**. No rescale, retune, additional games or pooling.

## Limitations and next step

The race increment is confirmed, but the threats+race integration has **no valid
direct dev5 estimate** (exp-0056 remains INVALID). Gate 1 remains unmet. A later
integrated gate run must use a fresh preregistration and direct published-dev5
comparison; individual Elo estimates are never summed.
