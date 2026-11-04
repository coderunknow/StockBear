# exp-0038 — dedicated qsearch transposition table (FROZEN before any evaluation game)

Registered before ANY exp-0038 evaluation game. `docs/DEV6_PREREG.md` §8 is
UNCHANGED; no gate, threshold, margin or tolerance is weakened. Written after
exp-0037 closed at its frozen Stage-1 rule.

## 1. Why this direction (independently re-ranked after exp-0037)
`docs/DEV6_RESEARCH_MATRIX.md` ranked qsearch-TT integration #3; with ProbCut
now abandoned it is #1 among unexecuted directions. exp-0037's diagnosis is
that any mechanism which must SPEND a verification subtree before it can save
one is net-negative at the 4 ms/move bullet budget. A qsearch transposition
table instead reuses information already computed, so it is the next
evidence-driven direction. It is NOT assumed to work.

## 2. Hypothesis
Quiescence positions repeat heavily across iterative-deepening iterations and
within a single tree. Caching qsearch bounds by `(Zobrist key, rule50, history
context)` should let repeated nodes cut without re-searching, buying depth at
the 40+4 ms control.

## 3. Implementation (exactly as built, default OFF)
- `SearchParams::qsearchTT = false`; UCI `QSearchTT` check; `bench --param
  qsearchTT=0|1`. Default-off build is bit-identical.
- A **dedicated** direct-mapped 2^16-slot cache inside `Search`, cleared once
  per `go`. It never touches the main transposition table, so shallow qsearch
  entries cannot evict deep entries or leak a `VALUE_NONE` static eval into
  `ttEval` reuse. Bounds are 0 none / 1 exact / 2 lower / 3 upper; mate scores
  are normalised by ply and NEVER stored; a cached lower bound cuts only when
  `value >= beta`, an upper bound only when `value <= alpha`.
- Exact key + rule50 + context match required before reuse. All normal qsearch
  returns store the value under the ORIGINAL window.

## 4. Pre-result PROFILING (not an evaluation game, not a strength result)
- Default-off correctness: ctest 11/11 Release, exact bench
  `243f9a1c1ba5b36f` / `a14ab62224f837e5`, 3x determinism
  `e45fa2ec2287eb41`, `QSearchTT` UCI default false.
- 12-position `bench --depth 16`: OFF 170,160,152 nodes / 50,986,678 us;
  ON 170,159,176 nodes / 52,957,998 us (**-0.0006 % nodes, +3.86 % time**).
- Instrumented build (temporary, source restored afterwards): e.g.
  99,346,894 probes / 2,741,602 hits / 73,388,924 stores on one position.
  **Diagnosis:** hits are plentiful but concentrate on stand-pat / delta /
  no-capture nodes that would return immediately anyway, so they save almost
  no nodes while every node pays a probe+store. Fixed-node/number proxies are
  recorded as MISLEADING in this project's ledger, so this profiling does NOT
  decide the experiment — a real 40+4 ms Tier-1 screen does.

## 5. Frozen Tier-1 screen design
- Runner: `.github/workflows/dev6-tier1.yml`, one dedicated GitHub-hosted
  `ubuntu-latest` VM per matrix job; pinned `source_sha`; **the EXACT packaged
  candidate binary is extracted and tested** (Gate 4 binary identity).
- Control: **FIXED TIME `--base-ms 40 --inc-ms 4`**, hash 16, threads 1,
  max-plies 240; `--nodes` NEVER used.
- ONE binary, single switch: candidate `QSearchTT=true` vs the SAME binary
  `QSearchTT=false`; zero toolchain confound. Both arms use
  `EvalParams=research-data/params_abc.txt` + `TTEval=true`.
- Stage 0 validity null: 400-game 40+4 ms self-match (`QSearchTT=false` vs
  `false`), 0 TIME_FORFEIT, 0 illegal/UCI/crash, 95 % CI includes 0. If it
  FAILS, exp-0038 is INVALID MEASUREMENT and no strength inference is made.
- batch A 1,000 games and batch B 1,000 games on two independent fresh
  disjoint 500-opening suites (seed `2026112101`, 1,400 openings excluding
  every earlier suite); colour-reversed, one pair per opening. Null arm
  400 games `QSearchTT=true` vs `true`.
- Statistics: W/D/L, paired pentanomial, opening-clustered CR1/t two-sided
  95 % CI, both batches separately AND combined, independent recomputation
  from raw JSONL, LLR labelled a normal approximation. No batch selection, no
  post-hoc combination, no threshold changes after results.

## 6. Frozen decision rules (before results)
- **ADVANCE to a preregistered bundle candidate** (bad capture pruning +
  qsearchTT, measured FRESH against exact dev5) only if combined point
  >= +20 Elo AND combined 95 % LCB > 0 AND both batches >= -5 AND null CI
  includes 0 AND 0 forfeits/illegal/UCI failures.
- **CLOSE (inert / overhead)** if combined 95 % UCB < +20 Elo OR combined
  point <= 0. The direction is then ABANDONED, not retuned.
- Inconclusive otherwise -> more samples under the same frozen conditions.
- This is an experiment-level rule; Gate 1 still requires >= +75 with LCB
  > +50 on two independent preregistered FIXED-TIME datasets, and Gate 4
  still requires the exact packaged candidate artifact and final-source CI.

## 7. Expected failure modes
Probe/store overhead exceeds the saved work (predicted by profiling); cached
bounds rarely match a later window; direct-mapped collisions; 2 MB cache clear
per `go` costs a measurable fraction of a 4 ms budget. None justify changing
the frozen design after results.

## 8. Non-claims / integrity
No fixed-node or node-count proxy is presented as fixed-time strength. No
absolute/CCRL/FIDE Elo, no gap-to-3000. No post-hoc stacking. No default
change to `QSearchTT` before gate satisfaction. No PR/merge/tag/release/
deploy/dev7. Raw evidence, audit, fingerprint and SHA-256 manifests are
uploaded as artifacts and mirrored by the deliberate `mode=export` job.
