# Pre-registered short-time confirmation, 2026-11-02

Written before any match on this suite. Candidate frozen at the pawn-safe
mobility engine implementation in commit 728909b, binary SHA-256
`13d3a684002fbd9ed45359ad3561cb598f4befb1e34ec36b92887f8d4b38957a`.
Baseline exact dev4 tag, binary SHA-256
`1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae`.
Version identifiers still dev4; candidate is a research build, not a release.

Screening completed: safe mobility +23.2 [−21.7,+68.9] Elo at 40+4 ms;
same-binary null −14.5 [−67.8,+38.1]. Both inconclusive.

## Fixed protocol

- 1100 games per match, 550 paired/color-reversed openings; no early stopping,
  no repeated significance decisions, no tuning after examining these results.
- New suite generated without engine evaluations by
  `scripts/dev5_confirmation_openings.py`, seed 2026110205. SHA-256
  `75824edb300dbf34b2aa4d2755a47c7e3bc9452a086b6aa74c5ca1f098f54422`.
  550 distinct final positions, no exact final-position overlap with screening.
  542 canonical four-ply families named with full SHA-256 for clustering.
- 40 ms base + 4 ms/move increment, hash 16 MiB requested each, one thread,
  max 240 plies, tournament shuffle seed 2026110205. Existing draw and cap policy.
- Run null first, candidate second, no simultaneous local build/training/match
  job during either. Same harness/options/suite. Sequential block order leaves
  possible temporal scheduler drift; report as a limitation, not randomization.
- Primary estimator: existing opening-clustered CR1/t interval, grouped by
  the four-ply family names. Report pentanomial and unadjudicated games too.
- Sample planning: at least 90% normal-approximation power for +50 Elo under
  variance <= .25 and effectively independent families (see DEV5_PLAN).
  Small family collisions are disclosed; power is approximate, not guaranteed.
- A lower 95% bound >0 supports improvement **only at this short condition**
  if null/forfeit/censoring checks do not invalidate interpretation. A point
  estimate >=50 or >=100 alone does not confirm either target; report lower
  bounds and separate longer-control limitations explicitly.
- If candidate interval crosses zero: inconclusive, no improvement claim.
  If wholly negative: reject. If null excludes zero or systematic forfeits,
  unexpected censoring or scheduler problems appear: withhold strength claim,
  diagnose and design a new prospective study rather than subtracting null Elo.
- No simultaneous search across multiple candidates on this suite. IIR and NNUE
  remain excluded. Longer controls and Stockfish benchmark still required for
  a complete release study; this test alone does not complete the mission.

Reproduction (run sequentially, no other local compute):

```sh
R=benchmarks/results/0.1.0-dev5
for mode in null safe; do
  A=build-dev4/bin/stockbear
  [ "$mode" != safe ] || A=build-safe/stockbear
  .venv/bin/python scripts/tournament.py \
    --engine-a "$A" --engine-b build-dev4/bin/stockbear \
    --games 1100 --base-ms 40 --inc-ms 4 --hash 16 --threads 1 \
    --seed 2026110205 --max-plies 240 \
    --openings benchmarks/positions/openings_dev5_confirmation.txt \
    --jsonl "$R/confirm-$mode-time40_4.jsonl" \
    --pgn "$R/confirm-$mode-time40_4.pgn" > "$R/confirm-$mode-console.txt"
done
```
