# exp-0065 — persistent cross-move quiet history (ordering learning)
# FROZEN BEFORE ANY exp-0065 STRENGTH GAME (2026-11-07)

## 1. Hypothesis and source-grounded mechanism

**Weakness (found by reading the code, then confirmed by measurement).**
StockBear throws away ALL ordering learning between moves, twice:

1. `src/search/search.cpp:934–943` — `Search::run()` zeroes `history_`,
   `killers_`, `counterMoves_`, `continuation_`, `captureHistory_` and
   `correction_` at the start of **every** root search.
2. `src/uci/uci.cpp:440` — a **fresh `Search` object** is constructed for every
   `go`, so even without the explicit clearing the tables would be new.

The quiet history table `history_[us][from][to]` is the primary ordering signal
for quiet moves (`search.cpp:295`) and the substrate for history-based
reductions. At the frozen 40+4 ms control the engine reaches **median depth 5**
(`benchmarks/recovery/champion_depth_probe.json`), i.e. only ~10–30k nodes per
move. Every move therefore restarts learning from zero, and the table never
accumulates the cross-position statistics that make it useful. Persisting and
aging quiet history across moves is universal practice in strong engines.

**This also explains a standing puzzle.** Every ordering switch has measured
neutral-to-negative here: exp-0014's ablations were later found to be **no-ops**
(switches already OFF), exp-0058's CaptureHistory was **rejected** (−2.53), and a
fresh pre-registration diagnostic for this cycle measured ContinuationHistory
turn-ON at **+0.43 % nodes** (i.e. slightly WORSE) over 250 positions at depth 7,
with only 67.2 % of trees changing. A learning table that is erased every 40 ms
cannot demonstrate its value; that is a confound in the whole ordering family,
not evidence against ordering.

**Mechanism (ONE knob).** New default-OFF search switch `PersistentHistory`.
When ON:

- `Search::run()` **does not clear** `history_`; instead every entry is **halved**
  (`value / 2`) at the start of the search — a bounded forgetting factor that
  prevents unbounded accumulation and staleness. The existing saturation halving
  at `HistoryLimit = 60000` is unchanged.
- `UciEngine` keeps **one** `Search` object alive across `go` commands and
  recreates it on `ucinewgame`, so the table actually survives between moves.

**Deliberately NOT changed** (so a measured effect is attributable to ONE
mechanism): `killers_` stay cleared per search (they are ply- and position-local,
and persisting them is not standard); `counterMoves_`, `continuation_`,
`captureHistory_`, `correction_` and `qcache_` clearing is unchanged; no update
rule, bonus, clamp, reduction, pruning rule or evaluation term is touched.

**Correctness note.** `evalStack_` is currently NOT reset in `run()`; it is only
zero because the object is fresh. Reusing the object would leak the previous
search's static evals into the `improving` comparison at low plies. This prereg
therefore includes clearing `evalStack_` unconditionally — a no-op for a fresh
object, required for the reused one. Nothing else about object lifetime changes.

## 2. Distinction from prior experiments (no closed verdict reopened)

- **Not exp-0014** (switch ablations, later shown to be no-ops on already-OFF
  switches). No switch is turned on here; the *lifetime* of an existing,
  already-ON table changes.
- **Not exp-0058** (CaptureHistory rejected): `captureHistory_` is untouched and
  remains OFF.
- **Not the ContinuationHistory turn-ON** measured as a diagnostic this cycle:
  `continuation_` is untouched and remains OFF.
- **Not exp-0050** (pawn-structure correction history, rejected): `correction_`
  is untouched and remains OFF.
- **Not exp-0064** (TT identity): the TT and its identity are untouched.
- Never tested: no entry in `benchmarks/FAILURE_LEDGER.md`,
  `docs/DEV6_RESEARCH_MATRIX.md` or the architecture survey concerns history
  lifetime, table persistence, or Search-object reuse.

## 3. Frozen arms and identities

Same-binary ablation on the **current best valid integrated candidate**
(threats+race). Primary batches do not play dev5.

| arm | executable | EvalParams | switch |
|---|---|---|---|
| A | packaged source-pin candidate | `research-data/params_exp0055_race.txt` | `TTEval=true`, `PersistentHistory=true` |
| B | identical candidate | `research-data/params_exp0055_race.txt` | `TTEval=true`, `PersistentHistory=false` |

- EvalParams SHA-256 (both arms):
  `82f93ba7a7b7e8e757c245098f5e2c4f42c866aa25124c73d0ad67ad11f89f01`.
- Published dev5 baseline (provenance only, not an arm here):
  `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`.
- The candidate binary SHA-256 is recorded by the runner and enforced
  built == packaged == tested in every job.
- Shipped default stays OFF; all three established bench signatures must remain
  exact: depth-4 `243f9a1c1ba5b36f`, depth-6 `e06c4352681ae8eb`,
  depth-7 `5bceff035f2a4ae4`.

## 4. Implementation scope (frozen)

1. `SearchParams::persistentHistory = false` + UCI check option
   `PersistentHistory` (default false).
2. `Search::run()`: when ON, halve `history_` instead of zeroing it; when OFF,
   the existing zeroing is bit-identical. `evalStack_` cleared unconditionally.
3. `UciEngine`: reuse one `Search` across `go` **only when the switch is ON**;
   recreate on `ucinewgame`. With the switch OFF the current fresh-object path is
   preserved exactly.
4. New registered test group `persistent_history`.
5. `scripts/probes/switch_liveness.cpp` learns the new switch name; a new
   sequential-replay diagnostic probe `scripts/probes/history_lifetime.cpp`.
Nothing in evaluation, move generation, pruning, extensions, reductions, time
management or the TT is modified.

## 5. Pre-game engineering gates (ALL required BEFORE games)

1. **Default-off equivalence:** all three bench signatures exact.
2. **Registered tests:** every registered group executes individually and exits 0
   (20 groups after this change), including the new group; fresh stage0 ctest in CI.
3. **Lifetime unit tests:** with the switch ON, a second `run()` on the same
   object must observe non-zero history carried over and halved; with OFF the
   table must be exactly zero at entry. `ucinewgame` must reset it. Killers,
   counter-moves, continuation, capture and correction tables must be cleared
   identically in both arms. `evalStack_` must not leak between searches.
4. **Determinism / no state corruption:** repeated identical command sequences
   produce identical node counts and best moves; `perft` and the dead-position
   suite unchanged; mate and stalemate scores unchanged.
5. **Mutation matrix:** ≥ 8 semantics-changing mutants, **all KILLED**, including
   live-path-disabled, always-on, decay removed, decay applied twice, decay sign
   flipped, object not reused, and `ucinewgame` not resetting. The two lifetime
   mutants are detected by an **interactive UCI oracle**
   (`scripts/check_persistent_history_uci.py`), because the in-process test group
   constructs `Search` directly and cannot observe `UciEngine`'s object lifetime.
   Plus **two semantics-preserving controls** that must SURVIVE: an equivalent
   spelling of the decay, and removal of the `evalStack_` clear — the latter is
   provably unobservable, since `search.cpp:622` writes `evalStack_[ply]` before
   the only read at `:628`, which is guarded by `ply >= 2`, so the value read was
   always written earlier in the same search. It is defensive hardening.
6. **Sequential-replay efficacy gate (frozen, experiment-specific).** Because
   this mechanism only exists ACROSS moves, an independent-position corpus cannot
   measure it. The frozen diagnostic replays **real games in move order** from the
   committed exp-0062 raw PGN evidence, searching each position at fixed depth 7
   with a reused object (ON) versus a fresh object (OFF), on **20 games**
   (deterministically the first 20 complete non-capped games of
   `run-42356232866` batchA). Requirement to proceed: **overall node ratio
   ON/OFF ≤ 0.98** AND a majority of games individually ≤ 1.00. If the ordering
   does not actually improve under game-like conditions, the experiment
   **closes before any game** — no strength run is spent. This is an efficacy
   gate, NOT a strength claim.
7. **Per-node cost guard (frozen).** The policy's evaluate()-cost instrument does
   not apply (no evaluation change). The frozen substitute measures **wall time
   at a FIXED NODE budget** (same binary, 250-position corpus, 20,000 nodes per
   position, median of 3 alternating blocks): ON/OFF **≤ 1.10**, A/A spread
   **< 0.10**. Fixed-node timing isolates per-node overhead, which is the real
   risk at fixed time; fixed-depth timing would confound it with tree size.
8. **File-valued options:** positive per-arm load proof for `EvalParams`.

Any gate failure blocks games for this implementation. Optimize without changing
semantics and remeasure under the same limits; never relax a limit.

## 6. Protocol, openings, sample, compute budget

Fixed **40+4 ms**, Hash 16, Threads 1, max-plies 240; flags
`-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`. Claimable draws claimed;
240-ply capped games are unadjudicated and excluded symmetrically by complete
pair. Fresh generator `scripts/dev6_exp0065_openings.py`, seed **2026110665**,
**3,900** distinct 8-ply openings in four disjoint slices, independently verified
against every earlier committed suite. No earlier games are pooled.

| job | games | pairs | A | B | purpose |
|---|---:|---:|---|---|---|
| stage0 | 600 | 300 | race, switch OFF | identical | control null + fresh ctest |
| batchA | 3,000 | 1,500 | race, switch ON | race, switch OFF | primary |
| batchB | 3,000 | 1,500 | race, switch ON | race, switch OFF | independent primary |
| null | 1,200 | 600 | race, switch ON | identical | powered candidate null |

Primary estimate = batchA + batchB only (**6,000 games**), two-sided
opening-clustered CR1 95 % Student-t, independent cluster bootstrap cross-check.
Nulls are never pooled. Power: at 6,000 games the established methodology gives
roughly ±9 Elo near the expected effect, so a true zero cannot pass LCB > 0.

**Exact compute budget:** **7,800 games**; exactly **four** benchmark jobs at
`timeout-minutes: 420` = 1,680 benchmark VM-minutes, plus prepare/export ceilings
of 10 minutes each = **1,700 workflow VM-minutes maximum**. One benchmark
dispatch, one export dispatch. Public GitHub-hosted runners only; no paid
service. No adaptive games, no result-driven rerun. Infrastructure failure before
any game may be retried once with the identical plan and the failure documented;
a failed null is INVALID, not a retry.

## 7. Validity — every condition required

1. Frozen prereg/plan/source/config/opening identities enforced by the runner.
2. All arms use the identical packaged candidate binary; per-arm positive
   `EvalParams` load proof; no silent fallback.
3. Explicit `PersistentHistory` value recorded per arm AND recorded effective
   defaults audited; primary arms must differ **only** by this switch.
4. Zero time forfeits, illegal moves, engine failures or crashes; capped `*`
   games are the declared symmetric exclusion and are counted.
5. Stage0 and candidate-null 95 % intervals **each include zero**. The audit
   banner alone is insufficient.
6. Primary slices disjoint from each other and from all previous suites.
7. All committed blobs and per-job SHA256SUMS verify; assets self-contained.
8. All 7,800 PGNs replayed, every move legal, zero inconsistencies.
9. Fresh ctest on the packaged candidate in stage0 passes (20 registered groups).
10. Exact fixed-time protocol and recorded effective defaults in every job.

Any failure ⇒ **INVALID MEASUREMENT**, no strength claim.

## 8. Frozen decision

On the fixed 6,000-game combined primary sample, with all validity conditions:

- **SCREEN ADVANCE** iff point ≥ **+10**, LCB **> 0**, and both batch points
  ≥ **−5**. A separate preregistered confirmation on fresh openings is then
  required before the mechanism counts as an independently supported component.
- **CLOSE (mechanism rejected)** iff UCB **< +3** or point **≤ 0**.
- Otherwise **INCONCLUSIVE**. No rescale, no retune, no extra games, no pooling,
  no favourable-batch selection.

Gate 1 remains **point ≥ +75 AND two-sided opening-clustered 95 % LCB strictly
> +50, measured DIRECTLY against the exact published dev5 executable**. This
screen cannot satisfy Gate 1. No merge, tag, release, prerelease, deploy or
completion push follows from this experiment. Component Elo estimates are never
summed.
