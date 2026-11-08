# exp-0066 — persistent continuation history (single-factor lifetime ablation)
# FROZEN BEFORE ANY exp-0066 EXPERIMENT GAME (2026-11-08)

## 1. Hypothesis

A **graded** ordering statistic that is erased after every move cannot
demonstrate its value. `continuation_` is updated by ±depth² on every quiet
cutoff and malus (`src/search/search.cpp:386–389,403–405`) but is **zeroed
unconditionally at the start of every root search**
(`src/search/search.cpp:952`), and the UCI engine additionally destroys the whole
`Search` object after every `go` (`src/uci/uci.cpp:445–453`). At the frozen
40+4 ms control the engine reaches median depth 5, roughly 10–30k nodes per move,
so the table is trained on one move's worth of data and then discarded.

**Hypothesis:** with the feature enabled in both arms, allowing `continuation_`
to persist across moves (with bounded forgetting) improves quiet move ordering
and therefore fixed-time playing strength, relative to erasing it every move.

**Supporting pre-registration evidence.** A diagnostic run this cycle measured
ContinuationHistory turn-ON against the champion over 250 independent positions
at depth 7: node ratio **1.0043** (slightly *worse*), only 67.2 % of trees
changing. That measurement was taken **with the erasure confound present** and is
explicitly **not** treated as evidence against continuation history. exp-0065
established the analogous lifetime effect for the main quiet-history table:
sequential replay of 20 real games gave node ratio **0.9654** with 19/20 games
improving, and the fixed-time screen returned **+9.7673 [+3.3767,+16.1645]**
(INCONCLUSIVE against its own +10 bar; verdict immutable, switch stays OFF).

## 2. Exact treatment and control

Both arms run the **identical packaged candidate binary** with
`EvalParams=research-data/params_exp0055_race.txt`, `TTEval=true`, and
**`ContinuationHistory=true` in BOTH arms**. The feature is ON in both arms
because it ships OFF and its update sites are gated on the feature param
(verified from the executable's own option list) — persisting an unwritten table
would be a no-op and would test nothing.

| arm | ContinuationHistory | PersistentContinuation | everything else |
|---|---|---|---|
| **A (treatment)** | `true` | **`true`** | identical |
| **B (control)** | `true` | **`false`** | identical |

The **single varying factor is table lifetime**. No evaluation term, update
rule, bonus, clamp, ordering weight, reduction or pruning rule differs.

## 3. Independent vs combined evaluation — choice and justification

**Choice: continuation history ONLY. Counter-move persistence is NOT bundled and
NOT tested here.**

Justification from source, not preference:

- `continuation_` is a **graded int statistic** (`search.hpp:275`, 200,704
  entries) accumulated by ±depth². Its signal quality is a direct function of
  sample count, so per-move erasure is a first-order confound.
- `counterMoves_` is a **categorical single-move reply table**
  (`search.hpp:282`, `Move[PieceNB][64]`): one cutoff overwrites the slot
  (`search.cpp:375`) and ordering reads it as a fixed score 1485000
  (`search.cpp:291–293`). It **saturates after a single write**; it does not need
  accumulation, so persistence is a materially different and weaker mechanism.
- Testing them together would produce an unattributable bundle — exactly the
  failure recorded for the exp-0026 six-feature bundle. The mission requires
  distinct mechanisms to stay distinct.

A factorial 2×2 was considered and rejected: at a fixed 7,800-game budget it
halves the power of every contrast, and the counter-move factor has a weak
mechanistic prior for the reason above. Counter-move persistence, if pursued,
requires its **own** preregistration and may not pool these games.

## 4. Expected behavioural and search-tree effects

- Ordering: quiet moves that have historically been good replies in similar
  piece-motion contexts should be tried earlier, raising the first-move cutoff
  rate.
- Tree: at fixed depth, fewer nodes over a **move sequence**; little or no effect
  on an isolated position searched once from an empty table (which is why the
  efficacy gate below replays real games in order).
- Score: fixed-depth scores may shift slightly because ordering changes which
  lines are searched first; this is expected and is not a correctness failure.
- Cost: one extra pass over ~803 KB per search for the forgetting factor, plus
  the table updates that **both** arms already pay.
- Direction is **not** guaranteed: stale statistics from an unrelated position
  can misorder moves. The frozen decision rule handles a negative outcome.

## 5. Identity (hashes)

- EvalParams, both arms: `research-data/params_exp0055_race.txt`, SHA-256
  `82f93ba7a7b7e8e757c245098f5e2c4f42c866aa25124c73d0ad67ad11f89f01`.
- Published dev5 gate baseline (provenance only, **not** an arm here): SHA-256
  `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`,
  re-verified in this checkout.
- The candidate binary SHA-256 is produced by the runner and enforced
  `built == packaged == arm A == arm B` in every job.
- Shipped defaults unchanged; all three bench signatures must remain exact:
  d4 `243f9a1c1ba5b36f`, d6 `e06c4352681ae8eb`, d7 `5bceff035f2a4ae4`.
- This preregistration's own SHA-256 is pinned in the plan and in every job.

## 6. Primary strength metric

Logistic **Elo** from the paired score, computed on **complete colour-reversed
opening pairs only**, from the frozen combined primary sample (batchA + batchB).
Wins/draws/losses and the excluded-game accounting are reported alongside.
Node counts, depth reached and time-to-depth are **never** strength evidence.

## 7. Time control and opening methodology

Fixed **40+4 ms**, Hash **16 MB**, Threads **1**, max **240 plies**; build flags
`-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`. Never `--nodes` for strength.
Claimable draws are claimed; 240-ply capped games are unadjudicated and excluded
**symmetrically by complete pair**, and the exclusion count is reported.

Fresh openings from `scripts/dev6_exp0066_openings.py`, seed **2026110666**,
**3,900** distinct 8-ply openings in four mutually disjoint slices, each final
position rejected against **every** earlier committed suite. Independently
re-derived with `scripts/recovery_verify_suites.py` (which does not import the
generator). One pair per opening; colours reversed within a pair.
**No exp-0065 games, and no earlier games, are pooled.**

## 8. Statistical analysis and CI construction

Two-sided **opening-clustered CR1** variance of the pair mean with a
**95 % Student-t** interval on `G−1` degrees of freedom, `G` = number of complete
opening clusters. Independent **cluster bootstrap** (20,000 resamples) as a
cross-check. Both are recomputed from raw `match.jsonl` by
`scripts/recovery_independent_audit.py`, which shares no code with the repo's
match statistics, plus full PGN replay. Batch label overlap must be zero.
Nulls are analysed separately and **never pooled** into the primary estimate.

## 9. Sample size, compute budget and stopping rules

| job | games | pairs | A | B |
|---|---:|---:|---|---|
| stage0 | 600 | 300 | control config | identical (null + fresh ctest) |
| batchA | 3,000 | 1,500 | treatment | control |
| batchB | 3,000 | 1,500 | treatment | control |
| null | 1,200 | 600 | treatment | identical |

**Exactly 7,800 games**; primary estimate = batchA + batchB = **6,000 games**.
Exactly four benchmark jobs at `timeout-minutes: 420` (1,680 benchmark
VM-minutes) plus prepare/export ceilings of 10 minutes each ⇒ **1,700 workflow
VM-minutes maximum**. One benchmark dispatch, one export dispatch. Public
GitHub-hosted runners only; no paid service.

Power: at 6,000 games this methodology yields roughly ±9–10 Elo half-width near
the expected effect, so a true zero cannot produce LCB > 0 except by a ~2.5 %
tail event, and the point bar below is the binding constraint.

**Stopping:** no adaptive games, no optional extension, no repeated sampling
until favourable, no favourable-batch selection. A failed null is **INVALID**,
not a retry. Infrastructure failure **before any game** may be retried once with
the identical plan and the failure documented.

## 10. Validity, mutant tests and independent audit

Pre-game engineering gates (all required before the first game):

1. **Default-off equivalence:** all three bench signatures exact.
2. **Registered tests:** every registered group executes individually and exits
   0 (**21** groups after this change); fresh stage0 ctest in CI.
3. **Cross-move persistence:** with the switch ON, consecutive searches on one
   object must observably carry continuation state; with OFF the table must be
   exactly zero at entry. The TT is cleared before every probe search so the
   test measures table lifetime and **not** transposition reuse (a previously
   recorded test-design error).
4. **Cross-game isolation:** `ucinewgame` must fully reset; a configuration
   change via `setoption` must also reset the persisted object (see §11 note);
   no state may cross between games.
5. **Determinism / no corruption:** a reused object with the switch OFF must be
   indistinguishable from a fresh one; TT identity, mate distances, stalemate
   and draw scores unchanged; perft and dead-position suites unchanged. Mate
   fixtures must be genuine checkmates, not stalemates (a previously recorded
   fixture error).
6. **Mutation matrix:** ≥ 8 semantics-changing mutants, **all KILLED**, plus
   semantics-preserving controls that must **SURVIVE**. Lifetime mutants that
   the in-process suite cannot observe must be detected by an **interactive UCI
   oracle** (a previously recorded gap where two mutants survived).
7. **Sequential-replay efficacy gate (frozen).** Replay **20 real games** in move
   order (deterministically the first 20 complete games with ≥40 positions from
   `run-42356232866` batchA), fixed depth 7, Hash 16, both arms
   `ContinuationHistory=true`, one object per game for the treatment and a fresh
   object per position for the control. Proceed only if **overall node ratio
   ≤ 0.98** AND a **majority of games individually ≤ 1.00**. Otherwise close
   **before any game**. Efficacy evidence, never a strength claim.
8. **Per-node cost guard (frozen).** No evaluation change, so the policy's
   `evaluate()` instrument does not apply. Substitute: wall time at a **fixed
   node budget** (20,000 nodes/position, 250-position corpus, median of 3
   alternating OFF/OFF/ON/ON blocks), both arms `ContinuationHistory=true`.
   Require ON/OFF **≤ 1.10** and A/A spread **< 0.10**. Fixed-node timing isolates
   per-node overhead; fixed-depth timing would confound it with tree size.

Any gate failure blocks games for that implementation; optimize without changing
semantics and remeasure under the same limit. **Never relax a limit after
observation.**

Measurement-quality caveat carried forward from exp-0065: a cheap fixed-node
probe with ~8 % A/A noise over-predicted cost and wrongly suggested a negative
fixed-time effect. The guard is a **regression gate**, not an Elo predictor.

## 11. Frozen ADVANCE / CLOSE / INCONCLUSIVE criteria

**Derivation (not copied from exp-0065).** The mission gate needs point ≥ +75
against dev5; the best valid direct integral measurement is **+40.7732**, so the
remaining gap is **34.23 Elo**. A component worth less than roughly 15 Elo would
require at least three further independently confirmed components to close that
gap, which is a poor use of the mission's remaining compute given the observed
component yield. The repository's established screen convention for
promotion-relevant increments (exp-0057, exp-0058, exp-0061) is **+15 / LCB > 0 /
both batches ≥ −5**, with CLOSE at **UCB < +5**. That convention is adopted here
**because the mission arithmetic justifies it**, and it is **stricter** than the
+10/+3 bars used by exp-0064 and exp-0065. It is fixed before any game.

On the frozen 6,000-game combined primary sample, with **all** validity
conditions passing:

- **SCREEN ADVANCE** iff point ≥ **+15** AND LCB **> 0** AND both batch points
  ≥ **−5**.
- **CLOSE (mechanism rejected)** iff UCB **< +5** OR point **≤ 0**.
- Otherwise **INCONCLUSIVE**.

Consequences: ADVANCE requires a separate preregistered confirmation on fresh
openings before the mechanism counts as an independently supported component.
INCONCLUSIVE keeps the switch **default OFF** and forbids extra games, rescaling,
pooling or re-reading the bar. No component Elo is ever summed. **This screen
cannot satisfy Gate 1**, which still requires a direct integrated measurement
against the exact published dev5 executable.

## 12. Artifacts, hashes and reproducibility

Committed before closure: this prereg (single commit, never edited after
freeze), the frozen plan and numeric budget, the opening generator and all four
slices with SHA-256s, the independent suite verification, the efficacy and cost
gate JSONs with their digests pinned in the plan, the mutation matrix, the UCI
oracle output, the raw export (per-game `match.jsonl`, PGN, fingerprints,
`SHA256SUMS`, option load proofs), the independent raw audit, the
condition-by-condition validity JSON, and the closure report. Every dispatched
job records source SHA, prereg SHA-256, build flags, binary SHA-256, effective
defaults and explicit per-arm options. All 7,800 PGNs must replay with every move
legal and zero inconsistencies.

**Implementation note (in scope, required for isolation).** `handle_setoption`
clears the TT at six sites but never resets `persistentSearch_`
(`src/uci/uci.cpp:236,245,256,265,294,346,565–568`). Persisted ordering state must
not survive a configuration change, so the reset is added alongside the new
switch. It is a **no-op whenever every persistence switch is OFF** (the pointer
is null), so shipped behaviour and all bench signatures are unchanged. This does
not alter exp-0065's frozen matches, which set options once at startup and issue
`ucinewgame` per game.

No merge, tag, release, prerelease, deploy or completion push follows from this
experiment.
