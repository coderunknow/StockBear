# v0.1.0-dev6 — decisive-experiment pre-registration (exp-0027 / exp-0028 / exp-0029)

**This document is committed BEFORE any result below is collected.** It freezes
the hypotheses, binaries, configuration, opening suites, seeds, statistical
methods, exclusion rules, null controls and success/failure thresholds for the
three experiments of the dev6 cycle. Any change to candidate code, parameters,
time control, baseline, or opening suite requires a NEW experiment identity and
a NEW pre-registration. Baseline for all strength claims is the **exact released
`v0.1.0-dev5` artifact**, never dev4.

## 0. Frozen identities (SHA-pinned)

- **Baseline executable** (immutable, `benchmarks/binaries/stockbear-dev5-release`):
  SHA-256 `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`;
  `bench` `243f9a1c1ba5b36f`, `bench --depth 16` `a14ab62224f837e5`;
  UCI `StockBear 0.1.0-dev5`; built `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`
  (portable x86-64-v3); release commit `c94571313a1667048468cf6d4e070400dc5ab228`.
  Provenance: `benchmarks/dev6-baseline/manifest.json`, `docs/DEV6_PREREG_BASELINE.md`.
- **Baseline runtime (champion)** — the configuration of the published +64.7 claim:
  `EvalParams=research-data/params_abc.txt`
  (SHA-256 `8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be`), `TTEval=true`.
- **Candidate source**: this branch's tree at dispatch (version `0.1.0-dev6`). The
  exact source SHA, candidate executable SHA-256 and build flags are recorded per
  job in `benchmarks/exp-runs/<id>/manifest.json` (`git_head`, `candidate_sha256`,
  `candidate_build_flags`) by the lane, which builds from the checkout.
- **Candidate build flags** (the exact portable release configuration):
  `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4` (no `-march=native`).
  Candidate `bench` must remain `243f9a1c1ba5b36f` (default set bit-exact).
- **Candidate parameter sets** (SHA-256):
  - `params_dev6_a.txt` `e94c05628968474eaa52153a29904361604d34dacb240dfe5c20d4ba040338bd`
    — champion coefficients + six extended features enabled (the primary candidate).
  - `params_abc.txt` `8a9dc81f…` — extended features 0 (integrity/ablation control).
  - `params_exp0020.txt` `2a7f103c6adf37572cbc0af27b99fe989b43de9caff336880f4d2a6e750d26c3`
    — historical, previously UNCONFIRMED, reused as a fully-reported screen.

## 1. Hypotheses

- **H1 (primary)**: enabling six correctly-implemented pawn-structure/coordination
  features on top of the dev5 champion improves fixed-time (40+4 ms) playing
  strength over the exact released dev5 champion by at least +75 Elo.
  Chess rationale, feature semantics, cost and correctness evidence:
  `docs/DEV6_EVAL_FEATURES.md`. Falsified if combined point < +75 or LCB95 <= +50.
- **H0-integrity (control)**: the dev6 binary with `params_abc` (extended gated off)
  is behaviourally identical to the released dev5 champion (~0 Elo). A material
  deviation would indicate a hidden source/binary difference (candidate-integrity
  failure) and invalidate all strength comparisons.
- **Null**: candidate-vs-identical-candidate produces a 95% interval containing 0.
- **exp-0020 reuse**: reports whether the previously-unconfirmed fresh-corpus retune
  is stronger than the dev5 champion; reported in full regardless of sign (no
  cherry-picking; it is NOT the frozen candidate).

## 2. Conditions (identical for every match)

- Time control **40+4 ms** (`--base-ms 40 --inc-ms 4`), hash **16 MB** per engine,
  threads **1**, `--max-plies 240`, paired colour-reversed openings, identical
  adjudication (claimable draws auto-claimed; capped games unadjudicated).
- Engine A (candidate) options as listed per job; Engine B (baseline) always
  `EvalParams=research-data/params_abc.txt`, `TTEval=true`.
- Runner: free GitHub-hosted `ubuntu-latest` (4 vCPU, dedicated VM per matrix
  job), `scripts/actions_dev6_lane.sh`; results committed under
  `benchmarks/exp-runs/<id>/` (PGN + JSONL + CSV + manifest + report). No
  concurrent CPU work on the runner during matches; no local compute in the
  sandbox is used for gate evidence.
- Build/compiler: GitHub-hosted ubuntu image GCC, `cmake -DCMAKE_BUILD_TYPE=Release`.

## 3. Statistical methods (frozen)

- Primary estimator: **opening-clustered CR1 variance with a two-sided 95%
  Student-t interval on G-1 df**, logistic Elo scale
  (`scripts/match_stats.py::opening_clustered`), pooled across shards with
  `scripts/pool_matches.py` (clusters = distinct opening names).
- Also reported per batch and combined: paired pentanomial, game-level W/D/L,
  score %, Elo point estimate, 95% CI, cluster count, complete/incomplete pairs,
  time forfeits, illegal moves, crashes, max-ply/unadjudicated, all terminations,
  and SPRT (clearly labelled a normal approximation).
- Cluster bootstrap / heterogeneity sensitivity where practical; conversion
  between fractional score and Elo is `400*log10(s/(1-s))` on the pair-mean/2.
- **Do not** use naive Wilson as the primary claim; **do not** treat the two games
  of an opening as independent.
- Independent recomputation from raw records by a reviewer that does not share
  code with the pooling (see `scripts/audit_exp0023.py` pattern) is required
  before any success claim.

## 4. Exclusion / adversarial-event rules (frozen, symmetric)

- TIME_FORFEIT, ILLEGAL_MOVE, CRASH, UCI-protocol failure, MAX_PLY / unadjudicated:
  recorded individually with timing/termination detail; genuine engine-caused
  illegal moves, crashes and protocol failures are counted as losses for the
  offending engine and never hidden. Unadjudicated (max-ply) games are excluded
  from the score and counted. External runner starvation is distinguished via
  recorded per-move times; a batch contaminated by infrastructure is invalidated
  only under this pre-declared rule and repeated with a new seed.
- Sensitivity results showing how exceptional events affect the estimate are
  reported. No game outcome is silently changed or removed.

## 5. Opening suites (fresh, immutable, disjoint)

Generated by `scripts/dev6_decisive_openings.py` (8-ply openings, canonical
four-ply family names, final positions deduplicated, excluding **all** earlier
suites in `benchmarks/positions/` and each other). Verified: batch A ∩ batch B
= 0, A ∩ historical = 0, B ∩ historical = 0. Full machine-readable record:
`benchmarks/dev6-baseline/decisive_suites.json`.

- **Batch A / exp-0028**: master `openings_exp0028_confirmation.txt`
  SHA-256 `1d69972297f1a2a8f24d4040fb39f8d423f9d013abff6b7c3e266606e36d2c25`,
  3300 distinct paired openings, split into 6 immutable slices of 550
  (`openings_exp0028_shard01..06.txt`). 6 shards × 1100 games = 6600 games.
- **Batch B / exp-0029**: master `openings_exp0029_confirmation.txt`
  SHA-256 `c491a9e5182bd41748a638bd7d987225b6a233e18e8e91ac2758053350f17b3e`,
  3300 distinct paired openings, 6 slices of 550. 6600 games.
- Each shard uses ONLY its 550-opening slice with `--games 1100`, so
  `openings[(pair) % 550]` uses every opening exactly once -> **no repeated
  opening within a batch**. A and B share no opening. Neither was used for
  candidate selection.
- **Screen jobs** (exp-0027) use the established `openings_dev4.txt` (screening
  only, never gate evidence).
- Statistical power from exp-0024 raw records: `docs/DEV6_POWER_ANALYSIS.md`
  (combined 13200-game expected half-width ~5 Elo at a true +75; ample power).

## 6. Shard plan and seeds (frozen)

| job | candidate options | games | suite | seed |
|---|---|---|---|---|
| exp0027-screen | params_dev6_a + TTEval | 2000 | openings_dev4.txt | 2026120101 |
| exp0027-control | params_abc + TTEval | 1100 | openings_dev4.txt | 2026120102 |
| exp0027-exp0020 | params_exp0020 + TTEval | 1100 | openings_dev4.txt | 2026120103 |
| exp0028-shard01..06 | params_dev6_a + TTEval | 1100 each | exp0028 slice 01..06 | 2026120201..0206 |
| exp0028-null | params_dev6_a + TTEval (both sides) | null 1100 | exp0028 slice 01 | 2026120298 (null seed +1) |
| exp0029-shard01..06 | params_dev6_a + TTEval | 1100 each | exp0029 slice 01..06 | 2026120301..0306 |
| exp0029-null | params_dev6_a + TTEval (both sides) | null 1100 | exp0029 slice 01 | 2026120398 (null seed +1) |

Engine order, colour (reversed within each pair) and shard/seed assignment are
fixed above; seeds are distinct across all jobs. Exact per-job commands and
runner metadata are in each `manifest.json`/`run.log`.

## 7. Null controls

Two candidate-vs-identical-candidate nulls (1100 games each, one per decisive
batch/environment). Each 95% interval must include zero. If a null shows
significant non-zero bias: (1) do NOT subtract the bias, (2) do NOT declare
success, (3) diagnose runner/scheduling/colour/engine-side/time-management,
(4) repair, (5) pre-register and run a valid new confirmation.

## 8. Success and failure thresholds (frozen; not weakened after results)

- **Gate 1 (primary)**: COMBINED (exp-0028 + exp-0029) point estimate >= +75 Elo
  AND combined two-sided opening-clustered 95% CI lower bound **strictly > +50**;
  BOTH batches show a positive point estimate; neither shows a material
  contradictory regression; the two batches are reasonably consistent.
- **Gate 2**: combined result supported by both independent pre-registered datasets.
- **Gate 3**: nulls compatible with zero.
- **Gate 4**: no unresolved correctness/illegal-move/protocol/time-forfeit
  regression; no unexplained difference between benchmarked and packaged binary.
- The exact candidate release artifact must be the tested binary.
- If ANY gate is unmet -> **FAILURE / gate not met**: no strength claim, no PR,
  no merge, no tag, no release. Results still preserved and reported in full.

## 9. Decision rule for exp-0027 screens

exp-0027 is diagnostic (screening), never gate evidence. A clear regression
there is recorded and the direction is closed per the Failure Ledger. The
decisive batches were pre-registered and frozen in the same commit as this
document, before any result existed; all results are reported without
cherry-picking. A strong first batch followed by a contradictory second batch
is NOT success (Gate 2).
