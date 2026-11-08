# exp-0066 — Persistent continuation history — VALID / INCONCLUSIVE

**Status: CLOSED as INCONCLUSIVE. `PersistentContinuation` remains default OFF.**
Gate 1 **UNMET**. Mission **ACTIVE / NOT COMPLETE**. No merge, tag or release.

## 1. Question and single factor

Does keeping the graded **continuation** table alive across root searches inside
one game add strength at fixed time, holding the feature itself ON in both arms?

The source audit (before any measurement) established:

| Fact | Citation |
|---|---|
| `continuation_` is 200,704 ints (~803 KB) | `search.hpp:265,275` |
| Index has **no colour term** (prevType, prevTo, curType, curTo) | `search.hpp:233` |
| Read adds `clamp(cont/4, ±8000)` to quiet history | `search.cpp:296–301` |
| Write is graded, `clamp_history(cont+bonus)`, limit 60000 | `search.cpp:386–389` |
| **Zeroed unconditionally every root search** | former `search.cpp:952` |
| UCI destroys the `Search` after every `go` unless `persistentHistory` | `uci.cpp:445–453` |
| `ContinuationHistory` and `CounterMoves` both ship **false** | built exe option list |

Because the update sites are gated on the feature, persisting an unwritten table
is a **no-op**. Both arms therefore set `ContinuationHistory=true`; **only
lifetime varies**. `CounterMoves` persistence was deliberately **excluded**:
`counterMoves_` is a categorical `Move[PieceNB][64]` reply table that saturates
after one write (`search.hpp:282`, `search.cpp:375,291–293`) — a different and
weaker mechanism. Bundling would repeat the exp-0026 attribution failure.

## 2. Frozen before any game

Prereg `docs/DEV6_PREREG_EXP0066.md`, SHA-256
`96c20de126b9ce8f5ca2031c5a90dfb72e24794462c077651939d1084c215fa3`, freeze commit
**`fc5375c`** — `git log` for that path shows exactly **1** commit. Implementation,
tests and gates were written *after* the freeze.

Decision rule, **derived not copied**: gate gap = 75 − 40.7732 = **34.23 Elo**.
A sub-15 component would require ≥3 further confirmed components to close that
gap, so the repository's promotion-relevant convention (exp-0057/0058/0061) was
adopted — **stricter** than exp-0064/0065's +10/+3:

- **ADVANCE:** point ≥ **+15** AND LCB > 0 AND both batches ≥ −5
- **CLOSE:** UCB < **+5** OR point ≤ 0
- otherwise **INCONCLUSIVE**

## 3. Pre-game gates (all green)

| Gate | Result |
|---|---|
| Bench d4/d6/d7 | `243f9a1c1ba5b36f` / `e06c4352681ae8eb` / `5bceff035f2a4ae4` — exact |
| Registered ctest groups | **21/21** |
| New `persistent_continuation` group | **9/9** |
| Interactive UCI lifetime oracle | **6/6** (persistence across `go`; cross-game isolation ON+OFF; cross-configuration isolation ON+OFF; fresh-engine determinism) |
| Mutation matrix | **11/11 killable KILLED**, **2** equivalence controls SURVIVED |
| Sequential efficacy (20 real games / 2,525 positions, d7) | node ratio **0.966264** ≤ 0.98; **18/20** games ≤ 1.00 → PASS |
| Per-node cost (20,000 nodes × 250 pos) | **0.970741** ≤ 1.10; A/A spread **0.070232** < 0.10; node deviation 0 → PASS |
| Openings | seed **2026110666**, 3,900, 4 disjoint slices, overlap **0**, independently re-verified |

Pre-game signal 0.9663 × 0.9707 ≈ **0.938** time-to-depth — favourable, unlike
exp-0065's ≈1.04. Recorded as a **node/time diagnostic only, never a strength
claim**; the 6,000-game screen decided.

## 4. Result — run 42434718590, export run 42436688031

Freeze `a17e304`; packaged binary `36fe761f20f28a252a977e24bff9a0addf798088619cea97d047ebf202fd87c8`.
7,800 games, 4/4 jobs SUCCESS, one benchmark dispatch + one export dispatch,
1,700 VM-minute budget. Fixed time 40+4 ms, Hash 16, Threads 1, max 240 plies.

| Slice | Games | Clusters | Elo | 95 % CI |
|---|---|---|---|---|
| batchA | 3,000 | 1,490 | **+12.8306** | [+4.2045, +21.4726] |
| batchB | 3,000 | 1,495 | **+9.8796** | [+1.3818, +18.3892] |
| **Primary (A+B only)** | **6,000** | **2,985** | **+11.3524** | **[+5.3008, +17.4110]** |
| Candidate null | 1,200 | 597 | −0.0000 | [−10.9458, +10.9458] |
| stage0 null | 600 | 298 | +1.7489 | [−13.1064, +16.6105] |

Both powered nulls include zero. Bootstrap CI [+5.2963, +17.4154] agrees with the
cluster-robust CI. Batch-label overlap 0.

**Validity 26/26 PASS.** Auditor issues **0**; committed blobs **54/54**; per-job
SHA256SUMS **44/44**; **7,800/7,800** PGN replayed, **0** inconsistent; **0** time
forfeits, illegal moves or engine failures; identical binary in every arm and
across jobs; explicit per-arm switch values; primary arms differ **only** by the
switch; `ContinuationHistory=true` in both arms of every job; shipped default
recorded `false`; identical recorded defaults; option-load proof ≥2 per job;
stage0 ctest **21/21**.

## 5. Verdict and what was NOT done

Observed **+11.3524** against a frozen **+15** point bar — **missed by 3.65 Elo**.
LCB was > 0 and both batches positive, but the ADVANCE criterion is conjunctive.
CLOSE required UCB < +5 or point ≤ 0; UCB is **+17.41**, so the mechanism is
**not** refuted either. The frozen rule yields **INCONCLUSIVE**.

No rounding, no extra games, no favourable batch selection, no criterion
re-reading, no post-hoc threshold relaxation. `PersistentContinuation` stays
**default OFF** and is **not** added to the champion.

## 6. Honest interpretation

The evidence is **positive but insufficient at the preregistered bar**: the point
estimate is ~2.1× its own standard error and the CI excludes zero. This is a real
signal that the frozen bar declined to promote, not a null result. Two
consecutive persistence increments have now landed in this band (exp-0065
+9.7673, exp-0066 +11.3524), which is consistent with each erased graded table
being worth roughly ten Elo — and consistent with **neither alone** being a lever
that closes a 34.23 Elo gap.

What may **not** be concluded:

- **No pooling.** exp-0065 and exp-0066 used different opening seeds and different
  switches; combining their samples is explicitly forbidden by both preregs.
- **No summing.** +9.77 + +11.35 ≠ +21.1. Overlapping mechanisms on the same
  quiet-ordering path can interact sub-additively or super-additively; the sum is
  not an estimate of anything.
- **No integral claim.** These were same-binary ablations on threats+race, never
  matches against dev5. Best valid integral remains **+40.7732
  [+36.2091, +45.3513]**; **Gate 1 UNMET**, gap **34.23 Elo**.

A future **joint** persistence treatment (both graded tables, or a shared aging
schedule) is a legitimate new hypothesis but requires **its own preregistration**
and fresh games; it cannot be inferred from these two samples.

## 7. Defect fixed in scope

`handle_setoption` cleared the TT at **six** sites but never reset
`persistentSearch_`, so persisted ordering state could survive a configuration
change. All six paths now reset (verified: 6 clears, 6 resets). This is a **no-op
when every persistence switch is OFF**, bench signatures are unchanged, and the
frozen exp-0065 matches set options once at startup with `ucinewgame` per game, so
**exp-0065's verdict stands**.

## 8. Errors caught by my own verification

1. An early UCI oracle check required repeated searches of one position **within
   one engine** to be node-identical. False: the TT persists across `go`, so later
   searches legitimately cost fewer nodes. Replaced with a **fresh-engine**
   determinism comparison.
2. The `ucinewgame_does_not_reset` mutant initially **survived** because its
   anchor matched the first identically-indented `persistentSearch_.reset()`,
   which lives in `handle_setoption`. Made the anchor unique (asserted exactly 1
   occurrence); the mutant is now **KILLED**.
3. The validity script's first adaptation failed an assertion because I assumed
   the template's structure; I then read the real code. Its UCI-schema assumption
   (list vs name→bool map) also failed loudly and was corrected. Failing closed
   was the correct behaviour.
