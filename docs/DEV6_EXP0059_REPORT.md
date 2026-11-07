# exp-0059 — pre-game cost gate failed; no strength measurement

**Verdict: BLOCKED BEFORE GAMES.** Zero exp-0059 games, zero benchmark
dispatches, zero export dispatches. This is not an Elo result and not a
confirmation or rejection of the race mechanism.

## Frozen intent

`docs/DEV6_PREREG_EXP0059.md` SHA-256
`9c35f08d7c4c11a0bd326fc89c3bfa76170e487dcbad99fc2154748138069d92`,
committed at `b5f522810b7a744a54a79236227585f5f3a754a5`, repeated exp-0055's
race-vs-threats increment with frozen configs and fresh openings. The prospective
budget is `benchmarks/recovery/exp0059_compute_budget.json`. No historical
budget was backdated. Suite verification passed independently:
`benchmarks/recovery/exp0059_suite_verification.json`.

## Measurement and failure

The unchanged engine was rebuilt Release/Ninja with the frozen flags; ctest
17/17 and all three shipped bench signatures passed before this experiment.
The diagnostic probe was linked against `build-rel/libstockbear_core.a` with
`-O3 -std=c++17 -mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4 -pthread`.
Corpus: 4,000 committed FENs, seed 20261116, SHA-256
`a1046aa3e7e3bfac3b016203e8d9dafef99432e3552a2719204a19da28ec1cb3`.

| calibration | blocks | median B/A | p10 | p90 | spread | result |
|---|---:|---:|---:|---:|---:|---|
| 1, unpinned | 60 | 1.0014 | 0.9385 | 1.0553 | **0.1167** | FAIL (<0.10 required) |
| 2, CPU 0 pinned | 60 | 1.0032 | 0.9600 | 1.0743 | **0.1143** | FAIL (<0.10 required) |

Raw per-block times and input hashes:
`benchmarks/recovery/exp0059_cost_aa_raw.json` and
`benchmarks/recovery/exp0059_cost_aa2_raw.json`. Logs and summaries share the
same prefixes. The second attempt was the explicitly permitted isolated
calibration; it also failed. The two-attempt limit is exhausted.

**Execution error disclosed:** the initial shell sequence ran exploratory A/B
measurements after the first failed A/A before the result was inspected. Those
files (`exp0059_cost_increment_*`, `exp0059_cost_combined_*`) are retained but
are **UNINTERPRETABLE** under the failed calibration and are not used for any
budget decision. The second attempt was guarded by an assertion; it stopped
before further A/B measurement. No games were dispatched in either case.

## Disposition

Do not relax the spread limit, quote the exploratory ratios as a pass, or
silently call a third attempt one of the first two. exp-0059 closes at its
pre-game resource gate. The scientific confirmation remains outstanding.
A replacement experiment must have a new identity and a prospectively frozen,
noise-resistant cost instrument before any games; the strength contrast and
acceptance thresholds remain unchanged. No result-driven strength retry has
occurred because no strength data was collected.
