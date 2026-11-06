# DEV6 exp-0049 — expressive per-square PST, correctly scaled objective

## VERDICT: NEGATIVE / CLOSED

Both frozen gates failed. **No screen was run. Zero strength games. exp-0047
was NOT activated and its Activation Record remains empty.** No hyperparameter
was changed after seeing the result, and no second fit was performed.

Prereg: `docs/DEV6_PREREG_EXP0049.md`, SHA-256
`05a43ca5afcae55d115c381225132b21e155e780a1c3dda43fe1f3e594c75265` — verified
byte-identical to the value committed before the corpus existed.
Artifacts: `benchmarks/dev6-baseline/exp0049_results/` (checksummed).

---

## 1. What was tested

A 768-parameter per-square piece-placement table (6 piece types x 64 squares x
2 phases), loaded through the default-OFF `PstFile` UCI option, fitted to
self-play outcomes. Three pre-declared differences from the CLOSED exp-0048
protocol, whose objective was degenerate:

| | exp-0048 (closed) | exp-0049 |
|---|---|---|
| L2 regulariser | `1e-5` (pinned optimum to init) | `0` |
| support floor | none | `<200` occurrences ⇒ reset to formulaic |
| deviation cap | none (loader ±2000) | **±150 cp** |
| iterations | 300 | 600 |

The `L2 = 0` choice was informed by an exploratory grid on the **closed**
exp-0048 corpus; that provenance was disclosed in the prereg, that corpus was
declared **BURNED**, and exp-0049 was measured on a **fresh corpus its
hyperparameters never saw**. The support floor and cap were not data-selected.

## 2. Corpus (fresh, disjoint, valid)

Generation run **42171974318** (8/8 isolated `ubuntu-latest` shards, SUCCESS),
export run **42187907151**, mirrored at
`benchmarks/exp-runs/corpus-export/run-42171974318/`. All 5 checksums verified
locally with `sha256sum -c`.

- **6,000 games**, dev5 champion vs dev5 champion, 40+4 ms, Hash 16, Threads 1.
- **261,641 positions**, 5,952 contributing games.
- **0 engine failures, 0 time forfeits.**
- Baseline binary SHA-256 `391cb50e…5bdb918` and prereg hash both match the freeze.
- Split seed 2026110612 ⇒ **4,761 train / 1,191 holdout games** =
  **210,250 / 51,391 rows**.

**Disjointness verified empirically, not just asserted:** the exp-0049 corpus
shares **0 positions** with the burned exp-0048 corpus (201,471 vs 210,971
unique positions), **0 openings** with it, and **0 openings** between its own
corpus and screen suites or between screen batches A and B.

## 3. Accuracy gate — FAILED

Held-out Texel log-loss, identical metric and threshold to exp-0048 (**not**
relaxed to let this candidate pass):

| quantity | value |
|---|---|
| `L_champ` | 0.2418506268 |
| `L_cand` | 0.2358739784 |
| required ceiling `0.97·L_champ` | **0.2345951080** |
| achieved relative reduction | **2.4712 %** |
| required relative reduction | **3 %** |
| `B_champ` → `B_cand` | 0.1036815581 → **0.1014635795** |

The Brier sub-gate **passed** (candidate strictly better). The log-loss sub-gate
**failed**: 2.4712 % against 3 %, a shortfall factor of **1.214x**. The frozen
rule is a **conjunction**, so the gate fails. The candidate needed to be about
21 % better than it was; this is a near miss, not a rounding dispute, and the
threshold was not moved.

All three engine/model identity checks passed on **all 261,641 rows**: (a)
champion counts reproduce `evaluate()`, (b) the Python formulaic rebuild equals
the engine's PST term, (c) the engine loaded with the fitted table equals the
fitted model. The metric describes the engine that would actually play.

Fitted table `exp0049.sbpst`, SHA-256
`6e31a01a6988fd2192259a101a1e089320e9ddeb8d414acf4ed3d05740d6c733`.

## 4. The exp-0048 failure mode WAS fixed

This is the one genuinely positive finding, and it is a *methodological* result,
not a strength result:

| | exp-0048 | exp-0049 |
|---|---|---|
| RMS delta | 0.124 cp | **111.83 cp** |
| max abs delta | 1.22 cp | **150.0 cp** (at the cap) |
| train loss start → end | ~flat | 0.550637 → **0.517245** |

The recurrence condition imposed after exp-0048 — *verify the table actually
moves and training loss falls before freezing* — was satisfied. The table moved
by ~900x the exp-0048 RMS. **exp-0049 therefore failed on measured merit, not on
a degenerate objective.** That distinction matters: unlike exp-0048, this run
says something real about the mechanism.

## 5. Cost gate — FAILED as measured, but the measurement is not conclusive

`bench --nodes 300000`, 3 alternating reps, fresh process per arm per rep,
7/12 positions included by the frozen structural rule, **node counts
bit-identical** between arms.

| rep | champion nps | candidate nps | ratio |
|---|---|---|---|
| 1 | 3,421,354 | 3,430,330 | 1.00262 |
| 2 | 4,073,549 | 3,826,342 | 0.93931 |
| 3 | 4,076,799 | 3,865,972 | 0.94829 |

Frozen statistic (median ratio) = **0.93931**, outside `[0.97, 1.03]` ⇒ **FAIL**.

**Honest caveat, recorded rather than used to excuse the result:** the champion
arm varied **19.2 %** across repetitions *against itself* — same binary, same
options — which is larger than the ~6 % difference being measured. This shared
2-core sandbox cannot resolve a 3 % NPS band. The recorded FAIL is the frozen
statistic as measured; it is **not** evidence that the PST genuinely costs 6 %
per node (exp-0048 measured 1.00967 on the same mechanism, and node counts are
bit-identical here, so the added work per node is a table lookup).

**It was not re-run.** No retry is authorised, and re-running until the number
looked better would be exactly the selective measurement this protocol forbids.
The accuracy gate closes the candidate independently, so the cost ambiguity
changes no decision.

## 6. Diagnosis: the pre-declared cap is strongly binding

**291 of 768** phase entries hit the ±150 cp cap, and the unconstrained optimum
wanted deviations up to **1,288.7 cp**. 62 phase entries were reset by the
support floor. So the fitted table is heavily constrained by a bound chosen
a priori for chess plausibility, and the fit is pressing hard against it.

This is the obvious place a tuning loop would start. **It was not touched.**
Relaxing the cap after seeing that it binds would be post-hoc selection on the
confirmation corpus, and would make the 3 % threshold meaningless. Any cap
change is a **new hypothesis** requiring a **new prereg** and a **new fresh
corpus** — the exp-0049 corpus and holdout are now **BURNED** for confirmation.

It is also not established that relaxing the cap would help *strength*.
Unconstrained per-square values in the hundreds of centipawns are large enough
to distort material balance and king safety; better outcome-prediction on
self-play data is not the same thing as better play. That question is open, not
answered favourably.

## 7. What was NOT done

- No hyperparameter changed after seeing data. No second fit. No sweep. No
  best-of-N. No cap relaxation. No threshold relaxation.
- The §7 diagnostic screen was **NOT** run — it is gated on §5 AND §6, both of
  which failed.
- **Zero strength games.** exp-0047 **NOT** activated; Activation Record empty.
- No pooling with any earlier experiment. No historical result rewritten.
- No PR strength claim, no merge, tag, release, prerelease or deploy.

## 8. Gate status (unchanged)

**1 UNMET, 2 direction-supported, 3 PASS, 4 UNMET.** Mission **ACTIVE / NOT
COMPLETE**. A 2.47 % accuracy gain is not evidence of +75 Elo and no such claim
is made.

## 9. Environment note

The sandbox was reset mid-experiment: the local checkout reverted to `main` and
build artifacts and pip packages were lost. All work was already pushed, so the
branch was restored by `git fetch` + `git merge --ff-only` to `37c1cd1`. The
restore was **verified**, not assumed: the prereg hash matched the frozen value,
and a fresh Release rebuild reproduced all three frozen bench signatures
exactly (`243f9a1c1ba5b36f`, `a14ab62224f837e5`, `e45fa2ec2287eb41`) with
`ctest` 13/13 and matching dev5/params hashes. No experiment state was lost and
no measurement was repeated because of the reset.

One provenance bug was fixed: the reused NPS script hardcoded
`experiment_id=exp0048` in its output. It now takes `--experiment-id`, and the
label in this run's artifact was corrected **after** measurement with an
explicit note; every timing, node count, ratio and verdict field was verified
unchanged.
