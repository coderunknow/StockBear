# exp-0061 — pre-game cost gate failed; no strength measurement

**Verdict: BLOCKED BEFORE GAMES (cost gate failed).** Zero exp-0061 games,
zero benchmark jobs, one evidence-export dispatch. This is not an Elo result
and not a confirmation/rejection of the battery mechanism's strength.

## Frozen intent

`docs/DEV6_PREREG_EXP0061.md` SHA-256
`2c518e70a312aa4793fae695860d7fae9d8392d377f0b5ee894643f00aa67617`,
frozen at `91166e5fbbec5ffba1566bd80a43f8bb80199928`, dispatched at `97438f8`.
Candidate: `KingSliderBattery=(10,0)` on top of threats+race, same-binary
ablation. Correctness pre-game evidence was green: oracle 800/0, ctest 18/18,
8/8 mutants killed, evaldata --check 4000/0, liveness 12/12 tree changes,
scale RMS 14.43 inside the frozen envelope.

## Cost gate result

Run **42355810868** prepare job failed closed; export **42355938905** preserved
`benchmarks/exp-runs/tier1-export/run-42355810868/cost-gate-exp0061-run42355810868`.
Median-of-3 CI instrument, 60 A/A + 90 A/B blocks:

| check | value | limit | result |
|---|---:|---:|---|
| A/A spread | 0.02792 | <0.10 | PASS |
| A/A median | 0.99954 | [0.98,1.02] | PASS |
| battery increment over race | **1.17094** | ≤1.05 | **FAIL** |
| battery+race+threats vs champion | **1.25063** | ≤1.10 | **FAIL** |

All 13 cost-gate checksums verify. The instrument was calibrated; the candidate
is genuinely too expensive under the prospective budget. No games were started.

## Disposition

Do not relax the limit or quote strength. exp-0061 closes at its pre-game
resource gate. A future battery variant requires a new identity, a semantics-
preserving optimization or a explicitly different mechanism, fresh prereg and
the same numeric limits. The default shipped row remains 0; bench signatures
unchanged. Mission continues with the confirmed threats+race integration and
other source-grounded directions.
