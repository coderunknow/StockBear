# exp-0042 — max-gain delta pruning in quiescence (FROZEN before any evaluation game)

Registered before ANY exp-0042 evaluation game. `docs/DEV6_PREREG.md` §8 is
UNCHANGED; no gate, threshold, margin or tolerance is weakened.

## 1. Why this direction (re-ranked after exp-0041)
exp-0041 extended a validated pruning decision higher in the tree, saved 42 %
of fixed-depth nodes and still measured `−5.0635 [−15.1810,+5.0454]` Elo at
40+4 ms. The recorded lesson is: prefer mechanisms that improve the ACCURACY
of a decision at roughly the same node count over mechanisms that merely
delete more nodes. The shipped quiescence delta check runs BEFORE move
generation and therefore has to assume the best possible capture is a queen
(`SeeValue[Queen]=975`), plus a frozen `deltaMargin=200`: it can only prune
when the stand-pat score is more than 1175 cp below alpha. Once the legal
captures are generated, the ACTUAL largest available gain is known and is
usually far smaller (a pawn, 100 cp). Using it makes the SAME pruning decision
more accurate without adding any new lossy rule. This is a genuinely new
mechanism, not a parameter change: `deltaMargin=200`, `SeeValue`, SEE, the
original conservative check, the PV/mate/illegal-move machinery and every
other parameter stay frozen.

## 2. Hypothesis
At 40+4 ms the engine reaches shallow depths where quiescence dominates.
Pruning nodes whose available captures cannot plausibly lift the score to
alpha (using their real maximum gain plus the same frozen safety margin)
reduces wasted quiescence work and buys depth without losing tactics, because
the decision is based on the position's actual legal captures rather than a
worst-case constant.

## 3. Exact code change (default OFF)
- `SearchParams::maxGainDelta = false`; UCI `MaxGainDelta`;
  `bench --param maxGainDelta=0|1`.
- In `quiescence`, AFTER the existing `generate_moves(..., GenType::QSearch)`
  and the empty-move-list handling, and only when `!inCheck` (the branch is
  inside the not-in-check path), compute
  `maxGain = max over generated moves of gain_of(pos,m) +
  (PromotionMove ? SeeValue[promotion_type(m)] - SeeValue[Pawn] : 0)` —
  exactly SEE's `gain[0]`, so capture-promotions cannot be under-counted —
  and return the stand-pat value when
  `best + maxGain + params_.deltaMargin <= alpha`.
- The original `best + SeeValue[Queen] + deltaMargin <= alpha` check still
  runs FIRST and unchanged, so this can only prune nodes that pass it. Check
  evasions, mate scores and the legal-move/stalemate logic are untouched.
- Default-off build is bit-identical: bench `243f9a1c1ba5b36f`, d16
  `a14ab62224f837e5`, d12 params `e45fa2ec2287eb41`; Release ctest 11/11;
  ASan+UBSan ctest 11/11; UCI default false.
- Pre-result profiling (NOT strength evidence): `go depth 12` startpos gave
  543,800 nodes / 269 ms OFF and 618,920 nodes / 309 ms ON (+13.8 % nodes).
  The mechanism is demonstrably LIVE — pruning changes returned stand-pat
  values, which changes upstream alpha-beta decisions and history/ordering,
  so total nodes can rise even though more quiescence nodes are cut. Fixed-
  depth/node-count proxies are recorded as MISLEADING three times in this
  project; a real 40+4 ms Tier-1 screen decides.

## 4. Frozen Tier-1 screen design
- `.github/workflows/dev6-tier1.yml`, one dedicated GitHub-hosted
  `ubuntu-latest` VM per matrix job, pinned `source_sha`, EXACT packaged
  candidate binary extracted and tested (Gate 4 identity).
- **FIXED TIME `--base-ms 40 --inc-ms 4`**, Hash 16, Threads 1, max-plies 240,
  **never `--nodes`**. Both arms receive identical 40+4 ms clocks.
- ONE binary, single switch: candidate `MaxGainDelta=true` vs control
  `MaxGainDelta=false`. Zero toolchain confound. Both arms:
  `EvalParams=research-data/params_abc.txt`, `TTEval=true`.
- Stage-0 validity null: 400-game 40+4 ms self-match with CONTROL options,
  0 TIME_FORFEIT / 0 illegal / 0 UCI or engine failure, 95 % CI includes 0.
  If it fails, exp-0042 is INVALID MEASUREMENT and no strength inference.
- batchA 1,000 games and batchB 1,000 games on two independent fresh disjoint
  500-opening suites (seed `2026112801`, 1,400 openings, ZERO overlap with all
  earlier suites, verified programmatically); colour-reversed, one pair per
  opening. Null arm 400 games with CANDIDATE options on both sides.
- Statistics: W/D/L, paired pentanomial, opening-clustered CR1/t two-sided
  95 % CI per batch AND frozen combined, LLR labelled a normal approximation,
  independent recomputation from raw JSONL. No batch selection, no post-hoc
  combining, no threshold changes after results.

## 5. Frozen decision rules (before results)
- **ADVANCE to a preregistered FRESH bundle candidate** (measured against exact
  dev5, NEVER a post-hoc sum) only if combined point >= +20 Elo AND combined
  95 % LCB > 0 AND both batches >= −5 AND null CI includes 0 AND 0
  forfeits/illegal/UCI failures.
- **CLOSE (max-gain delta rejected / abandon)** if combined 95 % UCB < +10
  Elo OR combined point <= 0. Then `MaxGainDelta` stays default OFF and is not
  retuned; `deltaMargin=200` remains frozen.
- Inconclusive otherwise -> more samples under the same frozen conditions.
- Experiment-level rules only. Gate 1 still requires >= +75 with LCB > +50 on
  two independent preregistered FIXED-TIME batches; Gate 4 still requires the
  exact packaged final candidate artifact and CI on its source HEAD.

## 6. Expected failure modes
Delta pruning already ignores multi-move capture sequences; using a tighter
material bound can still discard a real tactical resource and change upstream
alpha-beta behaviour (the +13.8 % fixed-depth node increase is evidence the
tree reacts). It may lose accuracy or destabilise ordering. A node-count change
in EITHER direction does NOT predict fixed-time strength in this project.
None of these justify changing the frozen design after results.

## 7. Non-claims / integrity
No fixed-depth/node-count proxy is presented as fixed-time strength. No
absolute/CCRL/FIDE Elo, no gap-to-3000. No post-hoc stacking, no default
change before gate satisfaction, no PR/merge/tag/release/deploy/dev7. Raw
PGN/JSONL/CSV/summaries/audit/logs/binary and SHA-256 manifests are uploaded
as Actions artifacts and mirrored by a deliberate `mode=export` job.
