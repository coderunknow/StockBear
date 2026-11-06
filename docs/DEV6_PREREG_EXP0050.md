# exp-0050 preregistration — pawn-structure correction history
# FROZEN BEFORE ANY exp-0050 EVALUATION GAME (2026-11-06)

## §1 Status and why this is a NEW direction

exp-0048 and exp-0049 are both **CLOSED / NEGATIVE** and their corpora are
**BURNED**. Do NOT refit, rescore, reopen or pool either. exp-0047 remains
**DORMANT** with an empty Activation Record.

Two audits this cycle removed the evaluator-accuracy route entirely:

- `docs/DEV6_ACCURACY_ELO_LINK_AUDIT.md` — the accuracy→Elo evidence that
  exp-0047 §3.3 cites **does not exist**; a 9-variant regression gives a slope
  whose 95 % CI **spans zero** (t = 1.64 vs crit 2.36).
- `docs/DEV6_ACCURACY_GATE_VALIDITY.md` — the frozen accuracy gate is
  **passable by a pure 0.80 rescale** of every champion parameter on **both**
  corpora (+3.043 %, +3.109 %). A scale-invariant replacement was built
  (`scripts/eval_accuracy.py`) and it too is **not** a significant Elo predictor.

**Therefore exp-0050 is deliberately NOT an evaluator-accuracy experiment.** It
is a **SEARCH** change, judged **only** by fixed-time 40+4 ms games against the
same-binary control. No accuracy gate, no log-loss threshold, no corpus fit and
no accuracy→Elo conversion is used or needed. This is the route both audits
independently recommended.

**Non-repetition (Gate 4).** `correction history` appears **nowhere** in
`benchmarks/FAILURE_LEDGER.md` as a tried or closed direction, and the source
contained **no** correction/eval-bias table before this commit (verified by
grep over `src/search/`). It is NOT exp-0041 (losing-capture pruning), NOT
exp-0042 (max-gain delta), NOT exp-0043 (singular extension), NOT exp-0044
(capture ordering), NOT exp-0045 (dead-eval throughput), NOT exp-0046
(adaptive null R), and NOT the exp-0048/0049 PST fits: it changes **no
evaluation parameter** and adds **no evaluation feature**. It learns a bias
from the search's own verdicts at runtime.

**Chess rationale.** The handcrafted tapered eval is systematically biased in a
way that depends on the **pawn skeleton** — it cannot see passed-pawn races,
blocked chains, or colour-complex holes. The search repeatedly discovers that
its own verdict differs from the static eval in the same direction for the same
pawn structure. Feeding that observed error back into the **pruning margins**
makes reverse-futility, null-move and futility decisions better informed, at the
cost of one table lookup per node.

## §2 Mechanism (single frozen switch)

Default-OFF UCI option `CorrectionHistory` / bench param `correctionHistory`.

- Table: `16384` slots × 2 colours of `int`, indexed by a hash of **only** the
  two pawn bitboards (pieces deliberately excluded so the bias generalises
  across piece placements). Cleared by `run()`.
- **Read** (once per non-check, non-mate node): the value used for heuristic
  pruning margins becomes `raw + entry/256`, clamped away from mate scores.
- **Write** (node exit): only when the node completed (`!aborted_`), is not a
  check or mate node, the best move was **quiet or absent**, and the bound is
  consistent (`!(Lower && best <= raw)` and `!(Upper && best > raw)`).
  Update `entry += (clamp(error*min(depth,8)/8) - entry)/8`, clamped to ±32 cp.
- **The RAW eval is what the TT stores**, never the corrected one, so the
  learned bias can never compound through TT reuse.

**ALL constants frozen from theory BEFORE any game, never tuned on a suite or
an Elo result:** `CorrectionSlots = 16384`, `CorrectionScale = 256`,
`CorrectionLimit = 32 cp`, `CorrectionUpdateCap = 8 cp`,
`CorrectionDepthDivisor = 8`, decay divisor `8`.

With the switch OFF every new branch is unreachable and the shipped search is
**bit-identical**. No evaluation value, no eval parameter, no move ordering, no
stand-pat, no time allocation and no protocol behaviour changes.

## §3 Mandatory pre-result diagnostics (completed; NOT strength evidence)

Build flags identical to the frozen Tier-1 build:
`-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`.

- **Default-OFF signatures bit-identical** to the shipped default:
  `243f9a1c1ba5b36f` (default d4), `a14ab62224f837e5` (d16),
  `e45fa2ec2287eb41` (d12 + `params_abc.txt`). Re-verified after restoring
  both mutation probes.
- UCI advertises `CorrectionHistory type check default false`.
- Release **ctest 14/14**; ASan+UBSan (address,undefined) **ctest 14/14**.
- New group `correction_history` **5/5**: proven mates unchanged, forced mates
  identical, legal PV, table cleared between runs, OFF bit-identical.
- **LIVENESS (the exp-0038 lesson).** Champion options both arms, FIXED DEPTH
  10, 12-position bench suite: OFF **1,418,459** nodes, ON **1,410,036**
  (**−0.59 %** tree change), mechanism live on **7/12** positions, 1/12
  bestmove changed, median depth 10 both. Bench signature changes
  `a5bc21eff5ebdd93` → `41b64ac8ec3e97a`, so the switch is demonstrably not inert.
- **MUTATION-VERIFIED regression.** Two deliberate mutants were built and the
  liveness assertion **FAILED** for both, while every correctness assertion
  still PASSED: (a) update call removed (table never written); (b) apply site
  disabled (table never read). Both were reverted and 14/14 + all three
  signatures re-verified. A correctness-only test cannot detect a dead
  mechanism; this one can.
- Node-count changes at fixed depth are **TREE-CHANGE PROXIES, never strength**.
  No local speedup, NPS or Elo claim is made.

## §4 Frozen design, control and suites

- FIXED TIME `--base-ms 40 --inc-ms 4`, Hash 16, Threads 1, 240 plies,
  **never `--nodes`**; ONE packaged binary; four isolated `ubuntu-latest`
  VMs/jobs; independent raw-JSONL recomputation of W/D/L, score, CR1/t Elo,
  opening-clustered 95 % CI, terminations and Elo-from-score.
- BOTH arms champion `EvalParams=research-data/params_abc.txt` and
  `TTEval=true`. A adds ONLY `CorrectionHistory=true`; B has it OFF.
- `null=true` jobs copy A options to BOTH engines; the Stage-0 validity null
  uses CONTROL options (no switch) on both sides.
- 1,400 FRESH DISJOINT 8-ply openings from `scripts/dev6_exp0050_openings.py`,
  seed `2026120801`: **ZERO** exact final-position overlap with **48,441**
  earlier committed positions in **172** files, ZERO duplicates, four mutually
  disjoint slices (independently re-verified). Slice SHA-256 in
  `benchmarks/dev6-baseline/exp0050_suites.json`.
- Jobs: `tier1-exp0050-stage0` 400 games seed `2026120810` (control/control
  validity null, fresh ctest on the packaged binary);
  `tier1-exp0050-null` 400 games seed `2026120813` (candidate options both);
  `tier1-exp0050-batchA` 1,000 games seed `2026120811`;
  `tier1-exp0050-batchB` 1,000 games seed `2026120812`.
- **FROZEN COMBINED = batchA + batchB ONLY**, never the nulls, never any other
  experiment.

## §5 Validity gate (enforced, not weakened)

Stage-0 and candidate-options null CIs must both include 0, and there must be
**0 TIME_FORFEIT / 0 ILLEGAL / 0 UCI / 0 ENGINE_FAILURE in ANY of the four
jobs, else INVALID MEASUREMENT**: ALL Elo from that run is DISCARDED, with no
strength inference and no decision from it. A bounded retry budget of exactly
ONE valid new run (own frozen prereg, fresh disjoint suites, NEVER pooled) is
pre-authorised for a technical failure; a second failure CLOSES exp-0050 AS
TECHNICALLY UNRESOLVABLE with no strength inference. No threshold may be
weakened after results.

**No separate NPS cost gate is used.** The frozen fixed-depth NPS instrument was
proven INVALID on the shared sandbox (A/A false-reject 7/12) and is valid only
on an isolated host with same-session A/A re-validation. Fixed-time games
already charge every per-node cost against the candidate, which is the
quantity of interest, so no NPS ratio is claimed or required here.

## §6 Frozen decision rules (registered BEFORE any game)

- **ADVANCE to a preregistered FRESH bundle candidate** (measured against the
  exact immutable dev5 baseline, NEVER a post-hoc sum) ONLY if frozen combined
  point >= +20 Elo AND combined two-sided opening-clustered 95 % LCB > 0 AND
  both batches >= −5 AND both null CIs include 0 AND 0 forfeits / illegal /
  UCI / engine failures in ALL four jobs.
- **CLOSE (mechanism rejected / abandoned)** if combined 95 % UCB < +10 Elo
  OR combined point <= 0.
- **If neither holds, exp-0050 is CLOSED AS INCONCLUSIVE** by a SINGLE-RUN
  COMPUTE BOUND: no strength claim, no default change, no bundle, no retune, no
  confirmation and NO post-hoc sample increase. Exactly ONE bounded valid retry
  is permitted for a technical failure (§5), never for an inconclusive result.
- **ADVANCE does NOT satisfy Gate 1.** Gate 1 still requires combined point
  >= +75 Elo AND combined 95 % LCB > +50 on two independent preregistered
  FIXED-TIME batches, both positive and consistent; Gate 4 still requires an
  exact final-candidate packaged binary/source/CI linkage with no
  correctness/illegal-move/protocol/time-forfeit regression.
  `docs/DEV6_PREREG.md` §8 is unchanged and unweakened.

## §7 Power and integrity

A 2,000-game confirmation has ~13 Elo half-width: it is powered for the +20
ADVANCE threshold and to rule out a material regression, **not** to resolve a
small effect. Expected upside is modest; regression risk is real because the
corrected eval feeds load-bearing pruning decisions. The ±32 cp clamp and the
quiet-best-move/bound-consistency write guards are the safety boundary, and
they are frozen.

NO local speedup / Elo / absolute / CCRL / FIDE Elo or gap-to-3000 claim. No
strength claim, no default change, no retune of closed switches, no pooling, no
post-hoc best-of-N selection, no PR / merge / tag / release / deploy / dev7
while any gate is unmet. A technical failure, invalid measurement, CI failure,
inconclusive result or closed result CANNOT terminate the mission. Immutable
dev5 baseline
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`,
`origin/main` and all historical evidence stay untouched.
