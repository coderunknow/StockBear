# exp-0064 — extension-agnostic main-TT identity (search reuse, not eval)
# FROZEN BEFORE ANY exp-0064 STRENGTH GAME (2026-11-07)

## 1. Hypothesis and source-grounded mechanism

**Weakness (measured, not assumed).** The main transposition table keys every
entry on the tuple `(zobrist key, rule50, historyContext, extensions)`
(`src/search/transposition_table.cpp:11–19,68–76,88–101`; call sites
`src/search/search.cpp:538–542,849`). `extensions` is the **per-path check
extension budget counter** (`search.cpp:533–536`, `MaxCheckExtensions = 3`). It
is not part of the chess position, not part of the draw rules and not part of
mate-distance normalisation. It is mixed into the bucket **index**, so the same
position reached with a different remaining extension budget is stored in a
different bucket and can never be found.

A compile-time-gated instrument (`SB_TT_IDENTITY_DEBUG`, default absent) plus a
sibling-bucket scan measured this on 250 real positions
(`benchmarks/positions/diagnostic_exp0064_ttid.epd`, params_abc + TTEval, Hash 16,
`benchmarks/recovery/exp0064_tt_identity_diagnostic.json`):

| fixed depth | probes | hit rate | identical-position entries blocked ONLY by `extensions`, at depth ≥ request | relative hit gain available |
|---|---:|---:|---:|---:|
| 5 | 348,631 | 0.2832 | 2.73 % of all probes | **+9.6 %** |
| 7 | 1,954,464 | 0.2372 | 4.59 % of all probes | **+19.4 %** |
| 9 | — | 0.2200 | 4.40 % of all probes | **+20.0 %** |

Misses caused only by `rule50` were ≤ 0.021 % and only by `historyContext`
≤ 0.0001 %. The loss is therefore concentrated in exactly one field.

**Mechanism.** One new default-OFF search switch `TTExtensionAgnostic`. When ON,
the main TT is probed **and** stored with extension argument `0`, i.e. the
identity becomes `(zobrist key, rule50, historyContext)`. The Zobrist key,
`rule50` and `historyContext` remain in the identity **unchanged**, so repetition
/ draw soundness and the per-root history salt are untouched. Mate scores keep
their existing `value_to_table`/`value_from_table` ply normalisation. No new
evaluate, SEE, move-generation or verification-subtree call is added; the change
strictly removes one distinguishing dimension.

**Why it can improve strength.** A TT cutoff skips an entire subtree. exp-0015
established on this harness that ~2× effective nodes ≈ +90 Elo at 40+4 ms, so
recovering ~10–20 % of the table's reuse is a plausible single-digit-to-low-double
-digit Elo lever. This is a **hypothesis**, not a claim: only fixed-time games
decide.

## 2. Distinction from prior experiments (no closed verdict reopened)

- **Not** the rejected `historyContext` relaxation: `historyContext` stays in the
  key precisely because it encodes reversible history that draw scores depend on
  (`position.cpp:586–587,627`). Only the effort counter is removed.
- **Not exp-0009** (TT layout: 32-byte entries, pow2 mask, THP). Entry layout,
  bucket count, bucket size and allocation are unchanged.
- **Not exp-0038** (a separate qsearch cache); the qsearch path is untouched.
- **Not exp-0043** (TT-informed singular extension): no extension is added or
  removed from the search itself; the check-extension rule is bit-identical.
- **Not exp-0045/0039** (dead `evaluate()` on TT hits): no eval call is skipped.
- Never tested before: `docs/DEV6_RESEARCH_MATRIX.md:114` still lists TT identity
  /replacement as unexecuted.

## 3. Frozen arms and identities

Same-binary ablation on top of the **current best valid integrated candidate**
(threats+race). Primary batches do not play dev5.

| arm | executable | EvalParams | switch |
|---|---|---|---|
| A | packaged source-pin candidate | `research-data/params_exp0055_race.txt` | `TTEval=true`, `TTExtensionAgnostic=true` |
| B | identical candidate | `research-data/params_exp0055_race.txt` | `TTEval=true`, `TTExtensionAgnostic=false` |

- Eval params SHA-256 (both arms):
  `82f93ba7a7b7e8e757c245098f5e2c4f42c866aa25124c73d0ad67ad11f89f01`.
- Champion params (stage0) `research-data/params_abc.txt` SHA-256
  `8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be`.
- Published dev5 baseline (provenance only, not an arm here) SHA-256
  `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`.
- The candidate binary SHA-256 is recorded by the runner and enforced
  built == packaged == tested in every job.
- Shipped default stays OFF; all three established bench signatures must remain
  exact: depth-4 `243f9a1c1ba5b36f`, depth-6 `e06c4352681ae8eb`,
  depth-7 `5bceff035f2a4ae4`.

## 4. Implementation scope (frozen)

1. `SearchParams::ttExtensionAgnostic = false` + UCI check option
   `TTExtensionAgnostic` (default false).
2. One testable free helper `tt_identity_extensions(bool agnostic, int extensions)`
   in `search.hpp`, used at BOTH the probe and the store call site.
3. Compile-time-gated diagnostic counters (`SB_TT_IDENTITY_DEBUG`) and the
   `scripts/probes/ttidentity.cpp` probe. Absent from shipped/candidate builds.
4. `scripts/probes/switch_liveness.cpp` learns the new switch name.
5. New registered test group `tt_extension_identity`; no existing test weakened.
Nothing else in evaluation, move generation, pruning, extensions, ordering,
time management or the TT layout is modified.

## 5. Pre-game engineering gates (all required BEFORE games)

1. **Default-off equivalence:** all three bench signatures exact.
2. **Registered tests:** every registered group executes individually and exits 0
   (19 groups after this change), including the new group; fresh stage0 ctest in CI.
3. **Independent identity oracle:** a python-chess/standalone oracle asserts that
   with the switch ON the TT returns an entry stored under a different extension
   budget for the identical position, and still REFUSES entries whose
   `historyContext` or `rule50` differ.
4. **Soundness tests:** known mate-in-1/2/3 positions must still be solved with
   correct mate distances with the switch ON; forced-repetition draw positions
   must still score draw; `perft` and dead-position suites unchanged.
5. **Mutation matrix:** ≥ 8 semantics-changing mutants, **all KILLED**, including
   live-path-disabled ("switch present but never applied"), probe/store
   asymmetry in both directions, `historyContext` also dropped, and `rule50` also
   dropped. Plus **one semantics-preserving control** mutant that must SURVIVE,
   proving the suite detects behaviour changes rather than any source edit.
6. **Liveness:** fixed-depth probe must show the switch actually changes the
   search tree (non-zero effect) on a majority of probe positions.
7. **Search-cost regression guard (experiment-specific, prospective).** The
   policy's evaluation-cost instrument does not apply: this change adds no
   evaluation work and the evalprof probe cannot exercise a search switch. The
   frozen substitute is a fixed-depth same-binary A/B on the 250-position
   diagnostic corpus, median of 3 alternating blocks: candidate wall time must
   be **≤ 1.10×** the ablation at depths 5 and 7 (a regression guard, NOT a
   benefit claim), and the source diff must add no evaluate/SEE/movegen call.
   Failure blocks games for this implementation; optimize without changing
   semantics and remeasure under the same limit. Never relax the limit.
8. **File-valued options:** positive per-arm load proof for `EvalParams`.

## 6. Protocol, openings, sample, compute budget

Fixed **40+4 ms**, Hash 16, Threads 1, max-plies 240; flags
`-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`. Claimable draws claimed;
240-ply capped games are unadjudicated and excluded symmetrically by complete
pair. Fresh generator `scripts/dev6_exp0064_openings.py`, seed **2026110664**,
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
roughly ±9 Elo near the expected effect, so a true zero cannot pass the LCB > 0
requirement and a true +15 has a good chance to advance.

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
3. Explicit `TTExtensionAgnostic` value recorded per arm AND the recorded
   effective defaults audited (an unset option takes its recorded default).
4. Zero time forfeits, illegal moves, engine failures or crashes; capped `*`
   games are the declared symmetric exclusion and are counted.
5. Stage0 and candidate-null 95 % intervals **each include zero**. The audit
   banner alone is insufficient; every condition is checked explicitly.
6. Primary slices disjoint from each other and from all previous suites.
7. All committed blobs and per-job SHA256SUMS verify; assets self-contained.
8. All 7,800 PGNs replayed, every move legal, zero inconsistencies.
9. Fresh ctest on the packaged candidate in stage0 passes (19 registered groups).
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
completion push follows from this experiment. If the screen advances, the next
steps are confirmation, then further mechanisms, then a new direct integrated
dev5 measurement; component Elo estimates are never summed.
