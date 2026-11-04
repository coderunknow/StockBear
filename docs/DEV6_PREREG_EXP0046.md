# exp-0046 preregistration — margin-adaptive null-move reduction
# FROZEN BEFORE ANY exp-0046 EVALUATION GAME (2026-11-04)

## §1 Status and why this is a NEW direction
exp-0045 is CLOSED / ABANDONED: its original run `41817228668` was INVALID
MEASUREMENT (1 TIME_FORFEIT), its Elo DISCARDED, and ONE bounded valid retry
`41818958001` gave frozen combined `-8.9240 [-18.2792,+0.4182]` on 1,993 games
=> CLOSE at `UCB < +10 OR point <= 0`. exp-0041/0042/0043 all lost while
changing which nodes are searched or adding a ply; exp-0044 added ZERO
per-node work and was the only non-negative direction in that group, but is
CLOSED AS INCONCLUSIVE at its frozen addendum compute bound. exp-0039 dead TT
eval elimination is now measured and CLOSED. Do NOT reuse or pool ANY earlier
experiment's data, do NOT retune a closed switch, do NOT repeat exp-0045.

This prereg registers the next ranked direction: a **margin-adaptive
null-move reduction**. The shipped engine uses a FIXED reduction
`SB_NULLMOVE_R + depth/5` for the null-move verification subtree. The
theoretical gap is that the null-move guard already knows `staticEval >=
beta`, but discards the SIZE of that margin: when staticEval is far above beta
the null move is very likely to refute and its verification subtree can be
shallower; when the margin is marginal the shipped depth must be kept. This is
a NEW decision RULE, not a constant retune and not a "delete more nodes"
heuristic: it spends NO new evaluate/SEE/movegen call, NO extra ply and NO
per-node work; it only chooses a shallower depth for an already-existing
subtree using two values already computed for the guard. It is NOT exp-0041
(losing-capture pruning at all depths), NOT exp-0042 (max-gain delta
pruning), NOT exp-0043 (singular extension), NOT exp-0044 (capture ordering)
and NOT exp-0045 (dead eval throughput). No earlier result is reused.

## §2 Mechanism (single frozen switch)
Default-OFF UCI option `AdaptiveNullR` / bench param `adaptiveNullR`. When ON,
at the EXISTING null-move pruning site only (all shipped guards unchanged:
`nullMove && allowNull && !pvNode && !inCheck && !mateWindow && depth >= 3 &&
staticEval >= beta && has_non_pawn_material(pos)`):
```
margin = staticEval - beta                 >= 0 by the guard
extra  = min(AdaptiveNullExtraCap, margin / AdaptiveNullMarginDivisor)
reduction = SB_NULLMOVE_R + depth/5 + extra
```
FROZEN constants chosen BEFORE any game from theory only, NEVER tuned on a
test suite or an Elo result: `AdaptiveNullMarginDivisor = 200` cp per extra
reduction ply, `AdaptiveNullExtraCap = 2`. With the switch OFF the branch is
unreachable and the shipped formula is byte-identical. No other search
decision, no evaluation value, no TT entry, no move ordering, no stand-pat,
no time allocation and no protocol behaviour changes. Only the DEPTH of the
existing null-move verification subtree can become shallower.

## §3 Mandatory pre-result diagnostics (already completed, NOT strength evidence)
Build flags identical to the frozen Tier-1 build:
`-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`.
- Default OFF signatures bit-identical to the shipped default:
  `243f9a1c1ba5b36f` (default bench), `a14ab62224f837e5` (d16 with
  `ttEval=1`), `e45fa2ec2287eb41` (d12 with `params_abc.txt`).
  UCI advertises `AdaptiveNullR type check default false`.
- Release ctest 11/11; ASan+UBSan (address,undefined) ctest 11/11
  (`benchmarks/dev6-baseline/exp0046_asan_ctest.log`).
- Instrumented `SB_ADAPTIVE_NULL_DEBUG` build, 24 REAL exp-0046 suite
  positions, champion options on BOTH arms, FIXED DEPTH 10:
  OFF 4,311,394 nodes, ON 4,252,622 (-1.36 % tree change); ON 44,789
  null-move nodes, 4,133 with extra reduction, 4,721 extra plies,
  mechanism LIVE on 23/24 positions, median depth 10 both.
- Same probe at a 40 ms fixed-time probe (a PROXY for the tournament's 40+4 ms
  control, NOT a strength measurement): OFF 1,006,703 nodes, ON 974,327
  (-3.22 %), 12,664 null nodes, 1,730 changed, 2,231 extra plies, LIVE 22/24,
  median depth 8 both. NO local speedup, NPS or Elo claim is made.
- Diagnostics are reproducibility/liveness evidence ONLY. Fixed-depth or
  fixed-node node-count changes are TREE-CHANGE PROXIES, never strength.

## §4 Frozen design, control and suites
- FIXED TIME `--base-ms 40 --inc-ms 4`, Hash 16, Threads 1, 240 plies,
  **never `--nodes`**; ONE packaged binary; four isolated `ubuntu-latest`
  VMs/jobs; independent raw-JSONL recomputation of W/D/L, score, CR1/t Elo,
  opening-clustered 95 % CI, bootstrap, terminations and Elo-from-score.
- BOTH arms champion `EvalParams=research-data/params_abc.txt` and
  `TTEval=true`. A adds ONLY `AdaptiveNullR=true`; B has the switch OFF.
- `null=true` jobs copy A options to BOTH engines; the Stage-0 validity null
  uses CONTROL options (no switch) on both sides.
- 1,400 FRESH DISJOINT 8-ply openings from
  `scripts/dev6_exp0046_openings.py`, seed `2026120701`: ZERO exact
  final-position overlap with **39,041** earlier committed positions in
  **145** files, ZERO duplicates, four mutually disjoint slices. Slice SHA-256
  in `benchmarks/dev6-baseline/exp0046_suites.json`.
- Jobs: `tier1-exp0046-stage0` 400 games seed 2026120710 (control/control
  validity null, fresh ctest on the packaged binary);
  `tier1-exp0046-null` 400 games seed 2026120713 (candidate options both);
  `tier1-exp0046-batchA` 1,000 games seed 2026120711;
  `tier1-exp0046-batchB` 1,000 games seed 2026120712.
- **FROZEN COMBINED = batchA + batchB ONLY**, never the nulls, never any other
  experiment. `scripts/dev6_exp0038_audit.py <run> exp0046 20 10` reproduces.

## §5 Validity gate (exp-0045 lesson, enforced not weakened)
Stage-0 and candidate-options null CIs must both include 0, and there must be
**0 TIME_FORFEIT / 0 ILLEGAL / 0 UCI / 0 ENGINE_FAILURE in ANY of the four
jobs, else INVALID MEASUREMENT**: ALL Elo from that run is DISCARDED, no
strength inference and no decision from it. A bounded retry budget of exactly
ONE valid new run (own frozen prereg, fresh disjoint suites, NEVER pooled) is
pre-authorised for a technical failure; a second failure CLOSES exp-0046 AS
TECHNICALLY UNRESOLVABLE with no strength inference. No threshold may be
weakened after results.

## §6 Frozen decision rules (registered BEFORE any game)
- **ADVANCE to a preregistered FRESH bundle candidate** (measured against the
  exact immutable dev5 baseline, NEVER a post-hoc sum) ONLY if frozen combined
  point >= +20 Elo AND combined two-sided opening-clustered 95 % LCB > 0 AND
  both batches >= -5 AND both null CIs include 0 AND 0 forfeits / illegal /
  UCI / engine failures in ALL four jobs.
- **CLOSE (mechanism rejected / abandoned)** if combined 95 % UCB < +10 Elo
  OR combined point <= 0.
- **If neither condition holds, exp-0046 is CLOSED AS INCONCLUSIVE** by a
  SINGLE-RUN COMPUTE BOUND: no strength claim, no default change, no bundle,
  no retune, no confirmation and NO post-hoc sample increase. The direction is
  abandoned. Exactly ONE bounded valid retry is permitted for a technical
  failure (§5), never for an inconclusive Elo result.
- **ADVANCE alone does NOT satisfy Gate 1.** Gate 1 still requires combined
  point >= +75 Elo AND combined 95 % LCB > +50 on two independent
  preregistered FIXED-TIME batches, both positive and consistent; Gate 4
  still requires an exact final-candidate packaged binary/source/CI linkage
  with no correctness/illegal-move/protocol/time-forfeit regression and no
  unexplained benchmarked-vs-packaged difference. `docs/DEV6_PREREG.md` §8 is
  unchanged and unweakened.

## §7 Power and integrity
A 2,800-game screen has ~13 Elo half-width and CANNOT resolve a small effect;
it is powered for the +20 ADVANCE threshold and to rule out a material
regression only. Full-sized confirmation is reserved by the preregistered
scheduler for a screen point >= +55, never triggered post hoc here. Expected
upside is modest (a shallower null verification subtree may improve depth at
fixed time); regression risk is real because null-move pruning is
load-bearing. NO local speedup / Elo / absolute / CCRL / FIDE Elo or
gap-to-3000 claim. No strength claim, no default change, no retune of closed
switches, no pooling, no post-hoc best-of-N selection, no PR / merge / tag /
release / deploy / dev7 while any gate is unmet. A normal technical failure,
invalid measurement, CI failure, inconclusive result or closed result CANNOT
terminate the mission. Immutable dev5 baseline
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`,
`origin/main` and all historical evidence stay untouched.
