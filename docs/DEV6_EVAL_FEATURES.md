# dev6 exp-0026 — extended evaluation features: rationale, semantics, cost, correctness

This document records the classical-evaluation research of the dev6 cycle. It is
a genuine implementation with correctness tests and independent verification;
its **playing-strength verdict is measured, not assumed** (see
`docs/DEV6_CONFIRMATION.md` and the Failure Ledger). The dev5 champion evaluator
is a 36-entry linear tapered model; dev6 audits its largest representational
limitations and adds/fixes pawn-structure and piece-coordination terms.

## Audit finding: two shipped features were dead rows

`eval_params.hpp` shipped four "exp-0022" feature ids
(`RookOn7th`, `KnightOutpost`, `BackwardPawn`, `PawnChain`). Only the first two
were actually computed in `features()`/`accumulate_breakdown()` and in exp-0020's
param file; **`BackwardPawn` and `PawnChain` were declared, ranged and tunable but
never counted** — their contributions were permanently zero. The default-off
`SB_INCREMENTAL_EVAL` path maintained none of the four. dev6 fixes all of this.

## Feature set (6 "extended" features), signs, phases

All six are appended to the table (append-only contract), shipped with value 0,
so the **default build is bit-identical** to dev5 (`bench 243f9a1c1ba5b36f`,
`bench --depth 16 a14ab62224f837e5`, ctest 11/11). Counts are from White's point
of view (White `+1`, Black `−1`); mg/eg counts are identical for each feature;
score = clamp(taper(Σ mg·count, Σ eg·count, phase)). Feature values are loaded
from an `EvalParams` file, so an isolated ablation is a params file with that
feature = 0 on the **same binary**. Ranges are `[-100, 200]` for all six.

| feature | chess rationale | expected sign |
|---|---|---|
| `RookOn7th` | a rook on the 7th rank attacks the enemy pawn base and restricts the king | bonus (mg, eg) |
| `KnightOutpost` | an advanced, pawn-defended knight that cannot be chased by an enemy pawn is a durable outpost | bonus (mg>eg) |
| `BackwardPawn` | a pawn that has fallen behind its neighbours, whose stop square is enemy-controlled and undefended, is a lasting weakness/hole | penalty (mg, eg) |
| `PawnChain` | a pawn defended by a friendly pawn is resilient; connected chains resist attack | small bonus |
| `ConnectedPassed` (new) | two passed pawns on adjacent files support each other and are far stronger than a lone passer | bonus (eg>mg) |
| `RookBehindPassed` (new) | a rook behind a friendly passed pawn (on the same file, on ranks behind it) supports its advance — classic endgame technique | bonus (eg>mg) |

### Exact predicates (independently re-implemented in Python)

Let `us` be the side, `them = ~us`, `pawns`/`enemyPawns`/`rooks`/`knights` the
respective bitboards. `PawnAttacksBB[color][sq]` = squares a `color` pawn on
`sq` attacks; `PassedPawnMaskBB[us][sq]` and `ForwardRanksBB[us][rank]` are the
shipped masks.

- **Passed pawn** (used by `ConnectedPassed`/`RookBehindPassed`): the shipped
  rule — no enemy pawn in `PassedPawnMaskBB[us][s]` and no friendly pawn ahead on
  `s`'s file (leading pawn of the file only).
- `PawnOn7th`: `rank_of(s) == 6` (White) or `1` (Black).
- `KnightOutpost`: relative rank 3..5, `(pawns & PawnAttacksBB[them][s]) != 0`
  (pawn-supported), `(enemyPawns & PawnAttacksBB[us][s]) == 0` (not attackable
  by an enemy pawn).
- `PawnChain` for pawn `s`: `(pawns & PawnAttacksBB[them][s]) != 0` (a friendly
  pawn on a defending square).
- `BackwardPawn` for pawn `s`, `stop = s ± 8`:
  `(enemyPawns & PassedPawnMaskBB[us][s]) != 0` (not passed) AND
  `(enemyPawns & PawnAttacksBB[us][stop]) != 0` (stop square attacked by enemy
  pawn) AND `(pawns & PawnAttacksBB[them][stop]) == 0` (stop square not defended
  by a friendly pawn) AND
  `(pawns & AdjacentFilesBB[file] & ForwardRanksBB[us][rank]) != 0` (a friendly
  pawn on an adjacent file is already ahead — the pawn has fallen behind).
- `ConnectedPassed` for passed pawn `s`: `(passed & AdjacentFilesBB[file]) != 0`.
- `RookBehindPassed` per passed pawn `s`: `popcount(rooks & FileBB[file] &
  ForwardRanksBB[them][rank])`.

## Implementation design (correctness and cost)

- A **single shared helper** `extended_counts(p, us)` computes all six raw
  counts; `features()` (live search), `accumulate_breakdown()` (tuner/offline)
  and `cheap_feature_counts()`/`all_feature_counts()` (default-off incremental
  path) all use it, so the live evaluation and the breakdown cannot drift.
  The exp-0022 incremental-path caveat is closed.
- **Gating**: `evaluation_rebuild_tables()` sets a flag that is true only when at
  least one extended parameter is non-zero. When false (shipped set and dev5
  champion `params_abc`), the extended routine is not called at all — the
  default/champion build is bit-exact AND pays **zero** extra per-node cost.
  This protects the cp-calibrated NPS regime documented in the Failure Ledger.
- **Cost (measured, pure eval, 20000 positions, `evaldata`, identical 32 champion
  coefficients)**: extended ON ~0.1165 s vs OFF ~0.1028 s per 20k
  (breakdown+evaluate) — +13.3% of that loop (~0.69 µs/eval), i.e. a small
  single-`evaluate()` overhead; zero when gated off. Bench signatures remain
  `243f9a1c1ba5b36f` / `a14ab62224f837e5` for the default set.

## Correctness verification (all passing)

1. `ctest` 11/11 (unit, perft, UCI, dead positions, nnue, tournament harness,
   statistics); 41 unit tests including the perturbed-parameter
   `evaluation_breakdown_matches_evaluate` mirror check that now exercises the
   extended path (all six coefficients non-zero).
2. New unit test `dev6_extended_pawn_features_counts_and_gating`: gating (all
   zero with the shipped set), 8 hand-verifiable per-feature counts (incl. a
   negative control and Black/White sign), mg==eg counts, and
   `evaluate() == eval_from_breakdown()` on feature-rich positions.
3. **Independent reference**: `scripts/check_dev6_eval_features.py` re-implements
   the six predicates from scratch with python-chess bitboards (sharing no code
   with the engine) and compares against `evaldata` breakdown over a fixed
   reproducible 600-position corpus. Result: **600 positions, 43,200 feature
   checks, 0 mismatches** (`benchmarks/dev6-baseline/eval_features_reference.json`),
   with all six features exercised (non-zero counts in 6/51/146/374/20/27
   positions respectively).
4. `evaldata --check` with extended params: 600 positions, 0 mismatches.
5. Default-set bench bit-exact; version string `0.1.0-dev6`.

## Hypothesis and falsification

H1: small, correctly-implemented pawn/coordination priors on top of the dev5
champion add fixed-time strength. Falsified by the pre-registered clustered
95% CI (see `docs/DEV6_PREREG.md`, `docs/DEV6_CONFIRMATION.md`): a combined point
< +75 or LCB95 <= +50 closes this direction. Values in
`research-data/params_dev6_a.txt` are **hypothesis-driven priors**, not tuned on
validation loss; the fixed-time playing-strength match is the sole arbiter, per
the Failure Ledger's lesson that validation-loss gains and best-of-N param
selection do not transfer.
