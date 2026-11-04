# exp-0041 — losing-capture pruning at ALL remaining depths (FROZEN before any evaluation game)

Registered before ANY exp-0041 evaluation game. `docs/DEV6_PREREG.md` §8 is
UNCHANGED; no gate, threshold, margin or tolerance is weakened.

## 1. Why this direction (independently re-ranked after exp-0038 and exp-0040)
exp-0036 established `BadCapturePruning` (skip captures with SEE < −100 at
remaining depth <= 3) as the ONLY mechanism with positive fixed-time evidence
(`+21.5238 [10.2819, 32.8108]`, Tier-2 dedicated core), closed only at the
preregistered Gate-1 futility boundary, NOT because the mechanism was wrong.
exp-0037 (ProbCut) and exp-0038 (qsearch TT) both failed because they SPEND
work before saving work, or save work only at already-cheap nodes. exp-0040
(banked-time allocation) was eliminated at profiling: a confirmed-live soft
budget increase (4 → 6 ms, hard 13 ms) left the search tree bit-identical
(depth 6, 12,539 nodes, 5 ms) because the 55 %/70 % early-stop gates dominate
at 40+4 ms. The next evidence-driven direction is therefore to take a
VALIDATED mechanism and extend WHERE it applies, rather than add overhead.

## 2. Hypothesis
A capture whose static exchange evaluation is below the FROZEN
`BadCaptureMargin = 100` is refuted at every remaining depth, not only at
depth <= 3. Applying the identical test higher in the tree skips whole
subtrees, buys depth at 40+4 ms, and does not lose real tactics often enough
to matter. This is a scope hypothesis, NOT a parameter change:
`BadCaptureMargin=100`, the SEE implementation, PV/mate/check/hash-move
guards and every other search parameter stay exactly as validated.

## 3. Exact code change (default OFF)
- `SearchParams::badCaptureAllDepths = false`; UCI `BadCaptureAllDepths`;
  `bench --param badCaptureAllDepths=0|1`.
- The exp-0034 guard `... && depth <= 3)` becomes
  `... && (depth <= 3 || params_.badCaptureAllDepths))`.
- Default-off build is bit-identical: bench `243f9a1c1ba5b36f`, d16
  `a14ab62224f837e5`, d12 params `e45fa2ec2287eb41`; Release ctest 11/11;
  ASan+UBSan ctest 11/11; UCI default false.
- Pre-result profiling (NOT strength evidence): `go depth 12` startpos with
  `BadCapturePruning=true` gives 757,239 nodes / 400 ms with the scope switch
  OFF and 438,131 nodes / 236 ms ON (−42.1 % nodes). The mechanism is
  demonstrably LIVE, unlike exp-0040. Fixed-depth proxies are recorded as
  MISLEADING for strength; a real 40+4 ms Tier-1 screen decides.

## 4. Frozen Tier-1 screen design
- `.github/workflows/dev6-tier1.yml`, one dedicated GitHub-hosted
  `ubuntu-latest` VM per matrix job, pinned `source_sha`, EXACT packaged
  candidate binary extracted and tested (Gate 4 identity).
- **FIXED TIME `--base-ms 40 --inc-ms 4`**, Hash 16, Threads 1, max-plies 240,
  **never `--nodes`**. Both arms receive identical 40+4 ms clocks; no movetime
  injection and no time-allocation difference between arms.
- ONE binary, single scope switch: candidate
  `BadCapturePruning=true, BadCaptureAllDepths=true` vs control
  `BadCapturePruning=true` (the validated exp-0036 configuration). Zero
  toolchain confound; this isolates ONLY the depth-scope extension.
  Both arms: `EvalParams=research-data/params_abc.txt`, `TTEval=true`.
- Stage-0 validity null: 400-game 40+4 ms self-match with the CONTROL options,
  0 TIME_FORFEIT / 0 illegal / 0 UCI or engine failure, 95 % CI includes 0.
  If it fails, exp-0041 is INVALID MEASUREMENT and no strength inference.
- batchA 1,000 games and batchB 1,000 games on two independent fresh disjoint
  500-opening suites (seed `2026112601`, 1,400 openings excluding every
  earlier suite); colour-reversed, one pair per opening. Null arm 400 games
  with CANDIDATE options on both sides.
- Statistics: W/D/L, paired pentanomial, opening-clustered CR1/t two-sided
  95 % CI per batch AND frozen combined, LLR labelled a normal approximation,
  independent recomputation from raw JSONL. No batch selection, no post-hoc
  combining, no threshold changes after results.

## 5. Frozen decision rules (before results)
- **ADVANCE to a preregistered FRESH bundle candidate** (measured against exact
  dev5, never a post-hoc sum) only if combined point >= +20 Elo AND combined
  95 % LCB > 0 AND both batches >= −5 AND null CI includes 0 AND 0
  forfeits/illegal/UCI failures.
- **CLOSE (scope extension rejected / abandon)** if combined 95 % UCB < +10
  Elo OR combined point <= 0. Then `BadCaptureAllDepths` stays default OFF and
  is not retuned.
- Inconclusive otherwise -> more samples under the same frozen conditions.
- Experiment-level rules only. Gate 1 still requires >= +75 with LCB > +50 on
  two independent preregistered FIXED-TIME batches; Gate 4 still requires the
  exact packaged final candidate artifact and CI on its source HEAD.

## 6. Expected failure modes
SEE < −100 can be a sound deep sacrifice or a necessary interposition; pruning
higher in the tree may lose tactics or destabilise move ordering. A large node
saving at fixed depth does NOT guarantee fixed-time strength (portable flags
gave +12–20 % NPS but only `+3.6 [−19.6,+26.9]` Elo; qlite gave +23 % NPS but
`−32.1 [−55.8,−8.6]` Elo). None of these justify changing the frozen design
after results.

## 7. Non-claims / integrity
No fixed-depth/node-count proxy is presented as fixed-time strength. No
absolute/CCRL/FIDE Elo, no gap-to-3000. No post-hoc stacking, no default
change before gate satisfaction, no PR/merge/tag/release/deploy/dev7. Raw
PGN/JSONL/CSV/summaries/audit/logs/binary and SHA-256 manifests are uploaded
as Actions artifacts and mirrored by a deliberate `mode=export` job.
