# exp-0043 — TT-evidence singular extension (FROZEN before ANY evaluation game)

Registered before ANY exp-0043 evaluation game. `docs/DEV6_PREREG.md` §8 is
UNCHANGED: Gate 1 still requires a >= +75 Elo point AND a combined two-sided
opening-clustered 95 % LCB > +50 on two independent preregistered FIXED-TIME
batches (§8 names exp-0028 + exp-0029), both positive, no material
contradictory regression and reasonable consistency; Gate 2 direction-supported
by both independent datasets; Gate 3 nulls compatible with zero; Gate 4 the
exact packaged final-candidate binary/source/CI linkage and no
correctness/illegal-move/protocol/time-forfeit regression or unexplained
benchmarked-vs-packaged-binary difference. No gate, threshold, margin or
tolerance is weakened. This document is experiment-level only.

## 1. Why this direction (post-exp-0042 re-ranking)
`docs/DEV6_RESEARCH_MATRIX.md` ranks singular/tactical extensions FIRST after
exp-0042, with a MANDATORY mechanism-live and overhead diagnostic because
exp-0037 (ProbCut) proved verification subtrees are expensive at 4 ms.
exp-0041 (−42.1 % fixed-depth nodes, `−5.0635 [−15.1810,+5.0454]` Elo) and
exp-0042 (screen `+2.6110 [−7.9556,+13.1825]`, bounded confirmation
`−10.8281 [−21.8567,+0.1787]`, NEVER pooled) closed the family "delete or
re-decide quiescence nodes"; quiescence stand-pat values are load-bearing.
A singular extension changes WHICH MAIN-SEARCH moves receive an extra ply. It
rewrites no stand-pat value, adds no lossy qsearch rule, and does not disable
any default-ON pruning/extension (all of which are load-bearing). This is the
first ranked unexecuted direction and it is a genuinely new mechanism, not a
parameter change of a failed experiment.

## 2. Declared deviation from the matrix's "genuine re-search" wording
Canonical singular extensions verify singularity with a reduced-depth
re-search of every alternative move. exp-0037 spent a verification subtree at
each candidate node and CLOSED at `+3.7766 [−9.3368,+16.9008]` (fixed-node),
so doing the same again would be repeating a recorded negative direction.
exp-0043 therefore uses ONLY evidence ALREADY IN THE TT: a lower bound found
at nearly the same depth and well above beta means all alternatives failed to
reach that value in the previous iteration, i.e. the hash move is singular.
There is NO verification subtree and NO extra per-node work; the only cost is
the extra ply of the hash move itself. The canonical re-search variant is NOT
abandoned — it is deferred until this variant either ADVANCEs (then any
re-search add-on needs its OWN prereg) or CLOSEs with a re-measured overhead
budget. This deviation is declared in advance so a null result cannot be
misattributed to a mechanism that was never tested.

## 3. Hypothesis and exact code change (default OFF)
At 40+4 ms the engine reaches depth ~5-8, where a single tactical shot can
decide the game. A node whose TT lower bound is far above beta has one move
that refutes all alternatives; searching that move one ply deeper should
improve the accuracy of cutoffs and of PV-adjacent tactics more than the extra
nodes cost. Mechanism: `SearchParams::ttSingularExtension = false` (UCI
`TTSingularExtension`, `bench --param ttSingularExtension=0|1`). In
`Search::negamax`, AFTER the existing TT cutoff (so only shallower,
non-cutting entries remain) and BEFORE static evaluation:

```
if (ttSingularExtension && !pvNode && !inCheck &&
    depth >= SingularMinDepth && hashMove != MOVE_NONE &&
    entry && entry->bound == Lower &&
    entry->depth >= depth - SingularDepthSlack &&
    singularExtensions_ < MaxSingularExtensions) {
    ttValue = value_from_table(entry->value, ply);
    if (|ttValue| < MATE_BOUND && ttValue >= beta + SingularMargin)
        singularExt = 1;
}
if (mateWindow) singularExt = 0;
```

`hashMove` is always ordered first; that move alone is searched at
`depth - 1 + 1` (one ply deeper) instead of `depth - 1`. `singularExtensions_`
is incremented around that child call and decremented on return, so the cap is
PATH-SCOPED and the negamax signature / TT `extensions` context are unchanged.
Check evasions, mate scores, the legal-move/stalemate logic, LMR, PVS, null
move, ProbCut, razoring, reverse futility, SEE and every other parameter are
untouched.

**FROZEN constants, chosen ONLY from the pre-result mechanism-live / overhead
diagnostic (§4), never from Elo:** `SingularMinDepth=3`,
`SingularDepthSlack=3`, `SingularMargin=50`, `MaxSingularExtensions=2`. They
are NOT retuned after results. `deltaMargin=200` and every other frozen value
stay frozen.

Default-off build is bit-identical: bench `243f9a1c1ba5b36f`, d16
`a14ab62224f837e5`, d12 params `e45fa2ec2287eb41`; Release ctest 11/11;
ASan+UBSan ctest 11/11 (`benchmarks/dev6-baseline/exp0043_asan_ctest.log`);
UCI `TTSingularExtension` default false. Every dev6 strength switch remains
default OFF.

## 4. MANDATORY mechanism-live and overhead diagnostic (BEFORE games)
Instrumented `SB_SINGULAR_DEBUG` build from the FROZEN source, counting
triggers and actually-applied extensions at each `Search::run()`.

- FIXED DEPTH 10, 16 exp-0043 suite positions (deterministic tree):
  OFF 2,655,145 nodes / 0 triggers / 0 extensions;
  ON 3,024,895 nodes / 15,000 triggers / 8,072 extensions.
  Overhead = **+13.9 % nodes** at fixed depth. The mechanism is LIVE.
- FIXED TIME `go wtime 40 btime 40 winc 4 binc 4`, 24 exp-0043 suite
  positions, 2 repeats: OFF 222,636 / 217,259 nodes, median depth 6,
  0 triggers, 0 extensions; ON 218,959 / 225,368 nodes, median depth 6,
  1,093 / 1,092 triggers and 548 / 516 extensions, LIVE on **23 of 24**
  positions (~22 extensions per search). Node totals differ by −1.7 % / +3.7 %,
  within run-to-run fixed-time noise; median completed depth is unchanged.

Interpretation: the switch genuinely changes the search tree at the EXACT
Tier-1 control, with a bounded ~14 % fixed-depth node cost and no loss of
completed depth. Three prior experiments recorded that fixed-depth/node-count
proxies DO NOT predict fixed-time strength, so these numbers are a validity
and overhead check ONLY — a real 40+4 ms Tier-1 screen decides. The earlier
`go depth 12` startpos probe (0 triggers) was a poor liveness probe and is NOT
used as evidence either way; suite positions are the preregistered probe.

## 5. Frozen Tier-1 screen design
- `.github/workflows/dev6-tier1.yml`, one dedicated GitHub-hosted
  `ubuntu-latest` VM per matrix job, pinned `source_sha`, EXACT packaged
  candidate binary extracted and tested (Gate 4 identity).
- **FIXED TIME `--base-ms 40 --inc-ms 4`**, Hash 16, Threads 1, max-plies 240,
  **never `--nodes`**. Both arms receive identical 40+4 ms clocks.
- ONE binary, single switch: candidate `TTSingularExtension=true` vs control
  `TTSingularExtension=false`. Zero toolchain confound. Both arms:
  `EvalParams=research-data/params_abc.txt`, `TTEval=true`.
- Stage-0 validity null: 400-game 40+4 ms self-match with CONTROL options on
  both sides, 0 TIME_FORFEIT / 0 illegal / 0 UCI or engine failure, 95 % CI
  includes 0. If it fails, exp-0043 is INVALID MEASUREMENT and no strength
  inference. A second 400-game null with CANDIDATE options on both sides checks
  the enabled switch itself; its CI must include 0.
- batchA 1,000 games and batchB 1,000 games on two independent fresh disjoint
  500-opening suites, generated by `scripts/dev6_exp0043_openings.py` with seed
  `2026120201` (1,400 openings total; 200 stage0 + 200 null + 500 + 500);
  programmatic ZERO exact-final-position overlap with **32,041** earlier
  committed positions across 120 earlier files and ZERO duplicates within the
  1,400. Colour-reversed, one pair per opening. Slice SHA-256 values are in
  `benchmarks/dev6-baseline/exp0043_suites.json`.
- Statistics: W/D/L, paired pentanomial, opening-clustered CR1/t two-sided
  95 % CI per batch AND frozen combined, LLR labelled a normal approximation,
  independent recomputation from raw JSONL. No batch selection, no post-hoc
  combining, no threshold changes after results. Combined = batchA + batchB
  ONLY, frozen before the run; the Stage-0 and null games are NEVER pooled in.
- Raw PGN/JSONL/CSV/summaries/audit/fingerprint/manifest/SHA256SUMS/UCI/run.log
  and the exact packaged `.tar.gz` are uploaded per job and mirrored by a
  deliberate `mode=export` job after results.

## 6. Frozen decision rules (before results)
- **ADVANCE to a preregistered FRESH bundle candidate** (measured against exact
  dev5, NEVER a post-hoc sum) only if combined point >= +20 Elo AND combined
  95 % LCB > 0 AND both batches >= −5 AND both null CIs include 0 AND 0
  forfeits/illegal/UCI/engine failures. ADVANCE alone does NOT satisfy Gate 1.
- **CLOSE (mechanism rejected / abandon)** if combined 95 % UCB < +10 Elo OR
  combined point <= 0. Then `TTSingularExtension` stays default OFF and is not
  retuned; no bundle, no default change.
- **INCONCLUSIVE otherwise** -> exactly ONE bounded confirmation run under a
  fresh frozen addendum and a NEW disjoint 1,400-opening suite, committed
  BEFORE those games, with the SAME 40+4 ms design, the SAME rules and its
  OWN Stage-0/null jobs. Screen and confirmation are separate experiments and
  are **NEVER pooled** (exp-0042 precedent). A confirmation CLOSE ends exp-0043.
- Experiment-level rules only. Gate 1 still requires >= +75 with LCB > +50 on
  two independent preregistered FIXED-TIME batches; Gate 4 still requires the
  exact packaged final candidate artifact and CI on its source HEAD. No
  experiment outcome terminates the mission.

## 7. Expected failure modes
TT evidence is noisy at shallow depth: a "well above beta" lower bound may be
a stale/transposed entry, so the extension can be spent on a move that is not
truly singular. Extra plies consume the 4 ms increment and can change which
depth completes (measured: median depth unchanged in the diagnostic, but
tournament play is different). Extensions interact with history/killer ordering
and TT replacement, which can destabilise later iterations. The +13.9 % fixed-
depth node cost may convert to a fixed-time LOSS, as exp-0041 did. A node-count
change in EITHER direction does NOT predict fixed-time strength in this
project. None of these justify changing the frozen design after results.

## 8. Non-claims / integrity
No fixed-depth/node-count proxy is presented as fixed-time strength. No
absolute/CCRL/FIDE Elo, no gap-to-3000. No post-hoc stacking, no pooling of
independent runs, no default change before gate satisfaction, no PR/merge/tag/
release/deploy/dev7, no strength claim. The immutable dev5 baseline
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`, `main`,
and all historical evidence remain untouched.
