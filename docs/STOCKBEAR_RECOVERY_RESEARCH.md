# StockBear — Recovery Research

**Branch:** `arena/6a6a2ba3-stockbear` · **Status:** mission ACTIVE, Gate 1 UNMET
**Update 2026-11-06 (post-game):** Direction 1 was implemented, preregistered and
played as exp-0052. Result **+4.2031 Elo [−6.9678, +15.3826]** over 2,000 games —
**VALID MEASUREMENT / CLOSED AS INCONCLUSIVE** by the frozen rules. It neither
advances nor is rejected. See `docs/DEV6_EXP0052_REPORT.md`. The ranking below is
retained as written pre-game; §3 Direction 1's "Next action" is now discharged,
and **Direction 2 is the strongest next action**.
**Baseline (unchanged):** released `v0.1.0-dev5`, binary SHA256
`391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`, champion
config `EvalParams=research-data/params_abc.txt`, `TTEval=true`, Hash 16,
Threads 1, **40+4 ms**. Public identity remains `v0.1.0-dev5`; no version bump,
tag or release is made by this work.

Companion: [`STOCKBEAR_RECOVERY_AUDIT.md`](STOCKBEAR_RECOVERY_AUDIT.md) (Phase I
verdict + Phase II profiling). This document is the Phase III direction analysis
and the justification for the Phase IV/V implementation of **exp-0052**.

---

## 1. What the evidence actually says about the bottleneck

| Measurement | Value | Source |
|---|---|---|
| `evaluate()` cost | 166.5 ns/call (60.3 ns `evaluate_lite`) | `evalprof`, Phase II |
| Share of node time in full eval | ≈33% (at ~505 ns/node) | derived, 1.98M nps |
| **Depth reached at 40+4 ms** | **median 5**, mean 5.47 | `champion_depth_probe.json` |
| Nodes per move | 7,187.5 | same |
| King-danger ceiling, linear term | 6 / 21 / 69 / 103 cp | `ksprobe`, Phase II |
| Marginal cp per additional attacker | **constant** | source, `features()` |
| 2× nodes ⇒ measured Elo | **+89.9 [+65.9, +114.7]** | exp-0015 |
| +75 Elo from speed alone requires | **1.78× nodes** | derived |

Three conclusions follow, and they constrain everything below.

**(a) The engine is shallow.** Median depth 5 with captures-only quiescence means
most decisions are made by static evaluation plus a short tactical tail. Eval
quality is not a cosmetic concern here; it *is* most of the playing strength.

**(b) Speed alone cannot reach the gate.** A hypothetical *free* evaluation
buys ~1.37× nodes ≈ **+41 Elo**. Reaching +75 by speed would need 1.78×, which no
available optimization provides. Speed work is funding, not a gate strategy.

**(c) The king-danger term is representationally limited, not mis-tuned.** The
existing terms are `KingDanger<Piece> × (attacks & KingZoneBB).count()`. Being
linear in each attacker count, the total is linear in the whole attack: a lone
knight grazing the zone scores 6 cp, while queen + rook + bishop + knight
converging scores 69 cp. The *marginal* penalty for one more attacker is constant.
Real king danger is superlinear — the fourth attacker is far more dangerous than
the first — and **no scalar retune of these five parameters can express that**.
This is the specific gap exp-0052 targets.

### What was ruled out, and why it stays ruled out

`DESIGN_LOG.md`, `AGENTS_LOG.md` and `benchmarks/FAILURE_LEDGER.md` are
append-only and were read in full. These are **not** re-opened:

- **NNUE** (−652 / −720 Elo), **cp distillation** (−30.6), **learned PST**
  (exp-0049, −159.5). The learned-PST corpus is **BURNED**; it is not refit,
  rescored or relaxed. exp-0051 is CLOSED/NEGATIVE and was independently
  re-audited from raw per-game records in Phase I — the verdict is VALID and
  stands.
- **The six extended features** (exp-0026…0029): 13,200 games, −17.0
  [−21.4, −12.6], isolated ablation ≈ −58 Elo. ABANDONED as a set.
- **Switch ablations** (exp-0011): LMR −68.9, Aspiration −83.4, SEEPruning −71.8,
  CheckExtension −31.5, NullMove −28.4. These features are load-bearing.
- **Pruning/history retunes, correction history, time management, PGO, TT
  layout, THP, best-of-N params.** All measured, all closed. exp-0040 showed
  banked time produced **bit-identical trees** — any time-management idea must
  first prove the tree changes at all.
- **qsearch-lite** (−32.1), **incremental eval** (−27% NPS).

The strongest *measured* direction remains **exp-0036 BadCapturePruning,
+21.52 [+10.28, +32.81]** — real, but a Gate 1 FAIL on its own.

### Two instrument failures that shape the method

Both selection instruments this project previously relied on are unusable:

1. **Accuracy does not predict Elo.** exp-0049 improved held-out log-loss by
   2.4712% and *lost ~160 Elo*. Any accuracy-based screen needs a defensible
   calibration argument; none exists here.
2. **A frozen NPS gate on shared CI is invalid** (58–80% false-reject rate).
   Timing claims require a paired, A/A-calibrated design on one machine, and
   even then are reported as local measurements only.

Therefore the pre-game evidence for a candidate is **correctness + scale +
cost + liveness**, and the only instrument that decides strength is a
**fixed-time game match**.

---

## 2. External primary research

Sources were fetched directly, not recalled. Effect sizes are quoted with their
original conditions because those conditions rarely match ours.

| Source | Finding | Transferable? |
|---|---|---|
| [MadChess 3.0 king safety](https://www.madchess.net/2020/08/16/madchess-3-0-beta-6794c89-king-safety/) | **+63 Elo**; saturating non-linear danger table, index Σ(hits×weight)/8; computed **inside the mobility loop** | Mechanism and shared-loop design: **yes**. Number: **no** — measured at 2 min + 1 s and **bundled with a root aspiration-window change** |
| MadChess 2.0 non-linear king-safety table | **+27 Elo**, cleaner isolation | Closest honest anchor |
| [Rebel/CPW-style term (jedi-knights #21)](https://github.com/jedi-knights/chess-engine/pull/21) | weights N2 B2 R3 Q5; saturating quadratic, **MG-only**, **per-side queen gate**; cost warning −40% middlegame nodes | Structure **yes**; the cost warning drove our fused-loop design |
| [TalkChess quadratic king danger](https://talkchess.com/viewtopic.php?t=81031) | `weight²/(factor+1)`, gated on ≥2 attackers **and** queen present | Queen gate corroboration |
| [Ascaniusfish #42](https://github.com/Ascanius3791/Ascaniusfish/issues/42) | acceptance bar **nps loss ≤ 10%** | Adopted as our cost bar |
| Stockfish king-danger patches (2019) | **+1.9 … +3 Elo** each | **Not** a transferable anchor: SF already has non-linear danger; these are marginal refinements to a mature term |
| [Vizvezdenec on eval terms](https://www.reddit.com/r/chess/comments/1075weq/) | threats are "really important … always overlooked"; king danger typically (mg×2, eg 0) | Supports Direction 2 and our MG-only taper |
| SF classical threat magnitudes | ThreatBySafePawn S(175,168), Hanging S(52,30), ThreatByRank S(16,3) | Scale-setting reference for Direction 2 |

**Honest synthesis:** the external anchors for replacing a *linear* king-danger
term with a non-linear one are **+27 to +63 Elo**, the upper figure confounded.
**None of them supports +75 Elo from one eval term.** Gate 1 at +75 with a
two-sided 95% LCB > +50 is, on this evidence, a multi-change target. Saying
otherwise would be fabrication.

---

## 3. Ranked directions

Ranking is by **expected research value** — mechanism plausibility × evidence
quality × cost to falsify — not by ease of implementation or profile share.

### Direction 1 — Non-linear king-danger concentration · **RANK 1 · IMPLEMENTED as exp-0052**

- **Novelty.** Genuinely new *representation* for this engine. Not a retune of
  `KingDanger*`, not a switch ablation, not a repackage of any closed experiment.
  The existing five parameters cannot express superlinearity at any value.
- **Mechanism.** Replace "sum of per-piece linear hits" with
  `curve(Σ weight[pt] × |attacks(pt) ∩ KingZone|)`, weights `{N2,B2,R3,Q5}`,
  `curve(u) = min(u,32)²/16`, **middlegame-only**, **skipped when the attacking
  side has no queen**. Concentration is punished super-linearly; a lone attacker
  is nearly free. At depth 5, where static eval dominates, correctly ranking
  "three pieces converging" above "three pieces scattered" should change moves.
- **Expected effect.** External anchors +27…+63 Elo (upper confounded). Our
  honest prior is **+10 to +35 Elo**, materially reduced by our deliberately
  conservative scale (§4). **This does not reach Gate 1 alone and is not
  presented as if it does.**
- **Runtime.** Attack sets are reused from the loop that already exists; the
  added work is integer accumulation plus one multiply. Measured paired cost
  **+0.65%** median, far inside the ≤10% bar. The naive two-knob prototype that
  recomputed attacks cost **~20%** and was rejected.
- **Complexity.** One appended parameter, one shared helper, three call paths
  kept consistent by construction.
- **Risks.** (i) Eval/pruning interaction — a large danger swing invalidates
  cp-calibrated futility margins; this is *the* failure mode of exp-0049 and is
  addressed by the pre-declared scale criterion. (ii) Double-counting with the
  existing linear `KingDanger*` terms, which remain active. (iii) `KingZoneBB`
  is coarse (~12 squares, one rank forward), so the term measures proximity more
  than true mating nets. (iv) +10…+35 is inside the noise band of a small match,
  so an underpowered run would be uninformative rather than negative.
- **Falsification.** A Tier-1 screen against the exact dev5 artifact at 40+4 ms.
  **ADVANCE only if the point estimate ≥ +20 Elo; CLOSE if the upper confidence
  bound < +10 Elo.** Anything between is INCONCLUSIVE and does not advance.
  A negative or null result closes this direction; it is not re-scaled and
  re-run, because that would be a strength sweep.
- **Next action.** ~~Freeze the prereg, then run the screen.~~ **DONE.** Played as
  exp-0052: **+4.2031 [−6.9678, +15.3826]**, CLOSED AS INCONCLUSIVE. Not rejected,
  not advanced; may not be re-run or re-scaled. The conservative scale that made
  the result attributable also made it too small for a ±13 Elo screen to resolve.

### Direction 2 — Threat / hanging-piece awareness · **RANK 2**

- **Novelty.** StockBear has **no threat term at all**. Undefended pieces and
  pieces attacked by lesser-valued attackers are invisible to static eval.
  Distinct from Direction 1 (king-local) and from the abandoned six-feature set
  (which contained no threat term).
- **Mechanism.** Bonus for enemy pieces attacked by a cheaper attacker, and for
  hanging (attacked, undefended) pieces; magnitudes anchored to SF's classical
  `ThreatBySafePawn` / `Hanging` scale. `attacks_by_color` is already computed.
- **Expected effect.** Externally described as high-value and commonly
  overlooked; **no clean isolated public Elo number was found**, so the prior is
  wide and weak: **+0 to +40 Elo**. It ranks below Direction 1 on *evidence
  quality*, not on plausibility.
- **Runtime.** Needs an defended-squares mask; ~one extra pass over attacked
  sets. Estimated +3…8% eval — must be measured, not assumed.
- **Complexity.** Moderate; several new parameters, so attribution discipline
  (one knob, or a pre-declared bundle) matters.
- **Risks.** Overlaps materially with search: at depth 5 many threats are
  already resolved tactically, so the term may be redundant. Double-counting
  with `SEE`-based pruning. Higher scale risk than Direction 1 because threat
  bonuses are large.
- **Falsification.** Same screen protocol; CLOSE if UCB < +10.
- **Next action.** Only after Direction 1 resolves. Prototype behind a
  default-off flag, measure scale/cost/liveness first.

### Direction 3 — Attack-set reuse / evaluation caching · **RANK 3 (funding, not a gate strategy)**

- **Novelty.** Not new as an idea, and explicitly *not* claimed as a strength
  direction. Every N/B/R/Q attack set is computed **twice** per `evaluate()`;
  ~8 of ~16 slider lookups are redundant; there is no `StateInfo` attack cache.
- **Mechanism.** Compute each side's attack sets once, share across mobility,
  king danger, shield and the new term. Bit-exact by construction.
- **Expected effect.** Eval is ~33% of node time; deduplicating roughly half the
  slider work plausibly yields **+8…+15 Elo** via the exp-0015 anchor. Well below
  gate. Its real value is **funding** the runtime budget that Directions 1–2
  consume.
- **Runtime.** Strictly non-negative in principle; must be verified with the
  paired A/A-calibrated probe, not asserted.
- **Complexity.** Low–moderate, but touches the hot path.
- **Risks.** A bit-exactness regression would silently change strength and
  invalidate comparisons. The three bench signatures are the guard. Note
  exp-0052 already implements *local* reuse for its own term.
- **Falsification.** All three signatures must be unchanged; if any changes, the
  refactor is wrong, not "a different engine". Cost must improve outside the
  A/A spread.
- **Next action.** Defer until a strength direction needs the budget. Doing it
  now would confound exp-0052's measurement.

### Considered and ranked below the cut

- **Quiet checks in quiescence.** Real gap (qsearch is captures/promotions only,
  so king attacks are structurally invisible at depth 5) and a public ~+9 Elo
  hint exists, but the sample was tiny and the node cost at 40+4 ms is likely
  prohibitive. Worth a *screen* later; not a +75 candidate.
- **Pawn-attack-aware mobility, richer pawn shield, passed-pawn king proximity.**
  Plausible but adjacent to the abandoned six-feature bundle; needs a careful
  argument that it is not a repackage before any implementation.
- **Efficient learned evaluation (small net / int8 / incremental).** Ruled out by
  measurement, not fashion: NNUE −652/−720, distillation −30.6, learned PST
  −159.5 with a burned corpus, incremental eval −27% NPS. Re-entering this
  direction requires a *new* mechanism argument plus a fresh corpus and an
  explicit answer to why the eval/pruning scale interaction would differ. Not
  justified now.

---

## 4. The pre-declared scale criterion (the exp-0049 lesson)

exp-0049 lost ~160 Elo while *improving* log-loss. Its eval perturbation had
**RMS 111.83 cp**, with 291/768 entries pinned at a ±150 cap. StockBear's pruning
margins are calibrated in centipawns — futility 110, reverse-futility 85, delta
200 — so a term whose typical swing rivals those margins does not merely add
information, it **detunes the search**.

Before measuring any strength, the following criterion was declared for
exp-0052:

> On a fixed diagnostic corpus, the eval-score perturbation must have
> **p99 ≤ 120 cp** and **RMS < 40 cp** (comfortably below the smallest pruning
> margin, 85 cp).

Results on 3,000 random-play positions (`benchmarks/recovery/exp0052_eval_scale.json`):

| Configuration | RMS δ | p99 \|δ\| | max \|δ\| | Verdict |
|---|---|---|---|---|
| divisor 8, coef 6, cap 64 (first attempt) | **187.85** | — | 1621 | **REJECTED pre-game** — worse than exp-0049 |
| divisor 16, coef 1, cap 64 | 31.31 | 138 | 271 | FAIL (p99 > 120) |
| **divisor 16, coef 1, cap 32 (frozen)** | **13.87** | **56** | **64** | **PASS** |

Eval-score sd ratio 1.0072; mean δ −0.36 cp. The cap of 32 units is the p99 of
the observed per-side attack-unit distribution (33), so it clips only the
extreme ~1% of sides.

Two integrity notes, recorded deliberately:

1. The criterion was **not relaxed** when the second configuration failed. The
   *implementation* was tightened instead.
2. An intermediate measurement returned identical numbers after a source edit
   because the probe binary was statically linked to a stale library. It was
   caught, relinked and re-measured. Any future probe must be relinked after
   every source change.

This scaling is intentionally conservative and **lowers the expected effect
size**. That trade is deliberate: a term that detunes pruning cannot be
attributed, and an uninterpretable −160 Elo teaches less than a clean small
result.

---

## 5. Implementation and pre-game evidence (exp-0052)

**One** appended parameter, `KingSafetyQuadratic`, shipped **0** (default-OFF).
Table is 39 entries. Frozen candidate: `research-data/params_exp0052_ks.txt`
= champion + `KingSafetyQuadratic 1 0`. **One configuration; no strength sweep.**

| Check | Result | Artifact |
|---|---|---|
| Default-OFF bit-exact | `243f9a1c1ba5b36f` / `a14ab62224f837e5` / `e45fa2ec2287eb41` — all three unchanged | Phase II/IV |
| Unit tests | **ctest 15/15** (7 king-safety tests) | — |
| Independent oracle (python-chess) | **1,000 positions, 0 mismatches**, 624 non-zero | `exp0052_king_safety_oracle.json` |
| Breakdown/evaluate invariant | **3,997 positions, 0 mismatches**, max\|diff\| 0 | Phase IV |
| Scale criterion | **PASS** (RMS 13.87, p99 56, max 64) | `exp0052_eval_scale.json` |
| Paired eval cost, A/A-calibrated | median **+0.65%**, p10 0.9689, p90 1.0430 | `exp0052_eval_cost.json` |
| Liveness (fixed depth 10, identical positions) | **10/11** trees change, 3 bestmoves differ, nodes −10.14% | `exp0052_liveness.json` |
| ASan + UBSan (Debug) | clean | Phase IV |

**Mutation testing.** Three mutants were physically applied and each **KILLED**
by ctest: (1) computed-but-never-applied, (2) linear instead of quadratic,
(3) queen gate removed. Mutants 2 and 3 **initially survived** — correctness and
sign tests do not pin *curve shape* or *gating*. A superlinearity assertion and a
gate-discriminating queenless position were added, derived from the oracle rather
than hand-labelled.

**An infrastructure defect found and fixed.** The `king_safety` test group had no
`add_test()` entry, so **ctest reported 14/14 PASS while the test binary reported
a failure**. New groups must be confirmed present in ctest output, not merely
compiling. This is exactly the class of silent gap that lets a dead mechanism
ship.

**What this evidence does and does not establish.** It establishes that the
feature is correct, cheap, live, and scale-safe. It establishes **nothing** about
Elo. exp-0050 passed comparable checks and measured −1.57 [−10.12, +6.98];
exp-0051 passed correctness checks and measured −159.5. Liveness is necessary,
not sufficient.

---

## 6. Gate status and the honest path forward

| Gate | Requirement | Status |
|---|---|---|
| 1 | +75 Elo point, combined two-sided opening-clustered 95% **LCB > +50**, both batches positive and consistent, validity pass | **UNMET** |
| 2 | Plausible mechanism, evidence-backed | Direction-supported |
| 3 | Baseline preserved, features default-off, evidence intact | **PASS** |
| 4 | Independent raw-evidence audit of the decisive run | **UNMET** (no decisive run yet) |

**No strength claim is made.** exp-0052 is implemented and pre-game-verified, not
validated. The next action is a **Tier-1 SCREEN**, explicitly *not* a Gate-1
decisive run: ADVANCE at point estimate ≥ +20 Elo, CLOSE if UCB < +10 Elo.
Rationale: ~576 games suffice for LCB > +50 *if* the true effect really were
+75, so **candidate quality is the binding constraint, not sample size**.
Spending thousands of decisive games on a term whose external anchors top out
near +63 (confounded) would be poor research economy.

**On reaching +75 credibly.** The realistic path is several *separately
preregistered, independently confirmed* gains, each surviving its own screen and
its own confirmation — not one term, and not a post-hoc stack of screened
numbers. Screen results are never pooled with confirmation results. If the
combination eventually reaches the gate it must be measured **as a single frozen
configuration against the exact dev5 artifact**, with both batches positive.

If exp-0052 closes negative, the strongest next action is **Direction 2
(threats)**, with Direction 3 as runtime funding. The mission remains **ACTIVE**.
Nothing here authorizes lowering +75/+50, reopening a closed experiment, reusing
a burned corpus, or editing a prereg after results.
