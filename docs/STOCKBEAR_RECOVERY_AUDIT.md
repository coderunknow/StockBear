# StockBear recovery — Phase I independent benchmark integrity audit

**Auditor's conclusion: exp-0051 is a VALID measurement. The CLOSED / NEGATIVE
verdict is preserved.** The point estimate reproduces to 10 decimal places from
the raw per-game records via an independently written estimator. Two apparent
discrepancies were investigated and both turned out to be **errors in my first
auditor**, not defects in the benchmark. One immaterial reporting nuance was
found and is documented in §6.

This audit shares **no code** with `scripts/match_stats.py`,
`scripts/tournament.py` or `scripts/dev6_exp0038_audit.py`. The auditor is
`scripts/recovery_independent_audit.py`; its machine-readable output is
`benchmarks/recovery/exp0051_independent_raw_audit.json`.

---

## 1. Repository state verified (not assumed)

| item | verified value |
|---|---|
| branch | `arena/6a6a2ba3-stockbear` (session-fixed, active) |
| HEAD at audit start | `18ce74c7050c2254dd8843b257626bdb850a93cd` |
| working tree | clean |
| `origin/main` | `6e7c2e02881faf93a84990a8345c41ad28bcae11` |
| public release tags | `v0.1.0-dev1` … **`v0.1.0-dev5`** (`c94571313a1667048468cf6d4e070400dc5ab228`) |
| latest release | `v0.1.0-dev5`, prerelease, 3 assets |
| open PRs | **#2** (`arena/071accaf-stockbear` → main, WIP dev2, unrelated — left untouched) |
| issues | none (open or closed) |
| remote research branches | 9 `arena/*` + `improve-project-discoverability` + `main` |
| `AGENTS.md` | **does not exist** in this repository (directive listed it "if present") |

**Version-identity discrepancy resolved.** The directive says preserve
`v0.1.0-dev5`; this branch's `VERSION` file reads `0.1.0-dev6`. These do not
conflict: `git show origin/main:VERSION` and the `v0.1.0-dev5` tag both read
`0.1.0-dev5`, and **no `v0.1.0-dev6` tag or release exists**. `0.1.0-dev6` is an
unreleased internal cycle label on a research branch only. The public release
identity is intact and is not changed by this work.

**Baseline identity verified against the committed manifest, not the prompt.**
`benchmarks/dev6-baseline/manifest.json` pins the released dev5 artifact; the
binary is present and hashes correctly:

- `benchmarks/binaries/stockbear-dev5-release` → SHA-256
  `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918` ✅ matches
- executes and reports `id name StockBear 0.1.0-dev5` ✅
- `research-data/params_abc.txt` → `8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be` ✅ matches
- champion runtime `EvalParams=params_abc`, `TTEval=true`, Hash 16, Threads 1,
  40+4 ms ✅ matches `docs/DEV6_PREREG.md` §0/§2

**Consequential distinction.** `docs/DEV6_PREREG.md` §8 Gate 1 requires the
candidate to be compared against **that exact dev5 artifact**. exp-0051 (like
exp-0037…0050) was a **same-binary ablation** — both arms ran the dev6 build
`7b80ce37…`, differing only by `PstFile`. That is the correct design for
isolating one switch, but it is a **Tier-1 screen**, and its verdict cannot be
substituted for a Gate 1 measurement. This is recorded so no later report
conflates the two.

## 2. Method — what "independent" means here

Recomputed from raw `match.jsonl` per-game records and `match.pgn`:

1. **Every game and outcome.** W/D/L recounted; `score_a` cross-checked against
   the `result` string **given colour reversal by game index** (`A` is White on
   even indices). Any contradiction is an issue.
2. **Exclusion accounting.** Reconciled
   `scored = 2 × complete_pairs + orphan_scored_games`; game IDs must be a
   contiguous `1..N` sequence.
3. **Pair construction.** Pairs rebuilt by index (`2k`, `2k+1`), *not* by opening
   label — matching the driver's documented reason (a label-keyed merge could
   absorb a later game into a half-filled pair). A pair enters the pentanomial
   only when both games are adjudicated.
4. **Opening assignment.** The suite is **shuffled** with `Random(seed)` before
   dealing. The permutation was reproduced from the frozen seed and every game's
   opening compared to its slot. Also asserted each opening is dealt once.
5. **Cluster construction.** Groups built from pair opening labels; the
   observations-per-cluster histogram is reported rather than assumed.
6. **CR1 variance** re-derived from the sandwich form
   `G/(G−1) · Σ_g (T_g − n_g·m̄)² / N²`, with a Student-t interval on `G−1` df.
7. **Student-t quantile** computed **from scratch** via a modified-Lentz
   continued fraction for the regularised incomplete beta and bisection on
   `P(|T|>t)=0.05` — deliberately **not** the repository's lookup table.
8. **Pentanomial** counts, **Elo-from-score**, and an **independent cluster
   bootstrap** (20,000 resamples of whole clusters, own RNG/seed).
9. **Full PGN replay** with `python-chess`: every move legality-checked and the
   final position verified consistent with the recorded termination.
10. Configuration, binary/asset identity, PST load proof, nulls, clock starvation.

## 3. Results of the recomputation

| slice | W/D/L | scored | complete pairs | clusters | obs/cluster | independent CR1 Elo | exact-quantile 95 % CI |
|---|---|---|---|---|---|---|---|
| batchA | 199/194/604 | 997 | 497 | 497 | all 1 | −149.8621 | [−169.8911, −130.7305] |
| batchB | 174/195/626 | 995 | 495 | 495 | all 1 | −169.5038 | [−189.1181, −150.8439] |
| stage0 null | 132/127/139 | 398 | 198 | 198 | all 1 | −5.2646 | [−21.5471, +10.9948] |
| candidate null | 134/136/128 | 398 | 198 | 198 | all 1 | +4.3870 | [−14.2126, +23.0119] |
| **combined** | **373/389/1230** | **1,992** | **992** | **992** | all 1 | **−159.5439** | **[−173.4477, −146.1023]** |

- Combined independent cluster bootstrap: **[−173.3082, −146.0248]**.
- Pentanomial `[2,1.5,1,0.5,0]`: batchA `[10,37,166,107,177]`,
  batchB `[7,27,145,143,173]` — both reproduce the stored counts exactly.
- **Point estimate −159.54391986351052 matches the reported value exactly.**
- Stored combined CI `[−173.5745, −145.9839]` is **wider** than the exact interval
  (see §5.2) — conservative, i.e. the safe direction for a gate.

**Cluster construction is the frozen one.** Every cluster contains exactly one
pair (`obs/cluster = {1: N}` in all four jobs), so the **design effect is exactly
1.000000** and CR1 reduces to the independent-pairs variance, as
`docs/DEV6_POWER_ANALYSIS.md` predicts for one pair per opening. The label
semantics were verified, not trusted: 500 openings dealt once each per batch.

**Disjointness verified at position level, not by label.** Replaying every
opening's moves with `python-chess` and comparing final FENs:
batchA 500, batchB 500, stage0 200, null 200 unique positions, and **all six
pairwise intersections are 0** (A∩B, A∩S, A∩N, B∩S, B∩N, S∩N).

## 4. Validity findings

| check | independent result |
|---|---|
| time forfeits / illegal / engine failures | **0 / 0 / 0** in all four jobs |
| PGN replay | **2,800 / 2,800 games replayed, 0 inconsistent** |
| committed export blobs | **50 / 50** re-hashed from `git show HEAD:<path>` |
| per-job `SHA256SUMS.txt` | **40 / 40** verified |
| both null CIs include 0 | **yes** (stage0 and candidate) |
| binary identity | `engine_a_sha256 == engine_b_sha256` in every job (correct ablation) |
| time control | `base_ms 40`, `increment_ms 4`, `nodes_per_move 0`, `max_plies 240`, Hash 16, Threads 1 ✅ |
| PST load | `arm A PstFile LOAD VERIFIED` in batchA/batchB/null; arm B too in null; stage0 has no PST arm (correct) |
| packaged asset | PST extracted from **every** tar.gz re-hashes to `6e31a01a…6c733`, equals `BUILD_INFO.assets_sha256` and the repo file |
| clock starvation | **0 negative clocks**; min remaining 13.29 ms, max 43.32 ms across all jobs — no runner starvation |

The PST check matters because a missing `PstFile` is **not fatal**: the engine
prints `could not load` and continues with formulaic tables, which in a
same-binary ablation makes arm A identical to B and manufactures a clean fake
null. The load is proven from committed bytes rather than from job status.

## 5. Discrepancies investigated

### 5.1 "Opening does not match suite slot 0" — MY error, not the benchmark's
My first auditor compared game openings to the **file order** of the suite.
`scripts/tournament.py:454` calls `random.Random(args.seed).shuffle(openings)`
before dealing. Reproducing `Random(2026120911).shuffle` yields slot 0
`EXP0051 0754 (d2d4 b8a6 d4d5 e7e6)`, exactly the recorded game 1. **Auditor
corrected**; all four jobs then match every slot.

### 5.2 Stored CI wider than my exact interval — DELIBERATE and conservative
`match_stats._T975` rounds every entry **up** and clamps `df > 120` to
`t_{0.975,120} = 1.979931`. Exact quantiles are smaller:

| df | repo | exact | delta |
|---|---|---|---|
| 197 | 1.979931 | 1.972079 | +0.007852 |
| 494 | 1.979931 | 1.964778 | +0.015153 |
| 991 | 1.979931 | 1.962361 | +0.017570 |

So the stored interval is **never narrower than nominal 95 %**. My auditor now
checks the stored CI against that convention **and separately asserts it is not
narrower than the exact interval** (which would bias a lower bound upward, toward
passing). Both assertions pass. Impact on the verdict: **none** — the sign and
both CLOSE triggers are unchanged under either interval.

### 5.3 Immaterial reporting nuance (the only real finding)
The headline "1,992 scored games" is correct as a count of *scored* games, but
the paired CR1 estimate uses **1,984** games (992 complete pairs). **8 orphan
games** from 8 half-filled pairs are scored yet excluded from the paired
estimator, because their partner hit `UNADJUDICATED_MAX_PLIES`. This is the
preregistered behaviour and is **correct** — a pentanomial observation requires
both games. It is a presentational subtlety, not a defect: it affects neither
the point estimate nor the verdict. Future reports should state both numbers.

## 6. Confirmed vs unconfirmed root causes

**Confirmed by this audit:** the measurement is internally sound — identity,
disjointness, pairing, clustering, variance, nulls, terminations and replay all
verify. The frozen table really was loaded, and it really lost ~160 Elo.

**NOT confirmed (carried as hypothesis, not proof):** the *causal* claim that
±150-cap saturation and RMS δ 111.83 cp distorted centipawn-calibrated pruning
margins. That is consistent with the magnitude and with the code paths
(`staticEval` feeds futility, reverse-futility and delta margins), but exp-0051
manipulated the whole table at once and **cannot isolate** which channel caused
the loss. Establishing causality would require a separate, preregistered
factorial experiment. It is **not** evidence that the evaluation architecture as
a whole is defective.

## 7. Classification

**VALID.** Not INVALID MEASUREMENT (no integrity, identity, validity or
statistical defect found). Not INCONCLUSIVE (both frozen CLOSE triggers fire by a
wide margin under two independent variance computations). The
**CLOSED / NEGATIVE** verdict stands. exp-0051 was not re-run and its artifact
was not modified.

Per the directive, a valid negative does not complete the mission. Phase II/III
continue in `docs/STOCKBEAR_RECOVERY_RESEARCH.md`.
