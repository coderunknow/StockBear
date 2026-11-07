# DEV6 architecture survey and ranked next directions (2026-11-07)

Source-grounded investigation while exp-0060 confirmation runs. This document
does not change any frozen experiment, shipped default, or verdict. Line numbers
refer to HEAD `8e77e0fec3ee4d919b6aedfc02f89cb9d5c19950` unless noted.

## Method and constraints

Read: `src/evaluation/evaluation.cpp` (features, threat/race helpers, evaluate),
`src/search/search.cpp` (score_moves, quiescence, negamax, root), `search.hpp`
(SearchParams defaults), `transposition_table.{hpp,cpp}`, `position.cpp`
(historyContext), and failure-ledger headings exp-0001…0059. Ranked by actual
game evidence and representational plausibility, not node savings or convenience.
Gate remains point ≥ +75 and LCB > +50 directly vs published dev5. No single
candidate below is proven gate-compatible; the defensible path is staged
component confirmation followed by direct integrated measurement.

## Ranked candidates

### 1. COMPLETE: passed-pawn race confirmation and direct integration (exp-0060 / exp-0062)

- **Weakness:** shipped passer score is advance-only; no king escort/blockade or
  blocked-path geometry. `evaluation.cpp:368–427` documents the gap; live path in
  `features()` and `evaluate()` around 951–994.
- **Mechanism:** fixed weights own-king 2, enemy-king 2, blocked 6, cap 64;
  one scale row `PassedPawnRace=(0,2)` on top of threats `(1,1)`.
- **Distinction:** exp-0055 screen advance +25.96; exp-0056 invalid integral;
  exp-0026 bundle had no king geometry. Not a retune or bundle.
- **Cost:** exp-0055 fused increment ~1.97%; exp-0060 CI cost gate passed before
  games under prospective ≤5% increment / ≤10% combined limits. Raw gate evidence
  will be exported with run 42352690063.
- **Falsifiable hypothesis:** independent confirmation point ≥ +20, LCB > 0,
  both batches ≥ −5, nulls include zero. Failure closes/rejects per exp-0060 §6.
- **Implementation/validation:** already implemented at `2594479`; 7 tests,
  oracle 800/0, invariant 4000/0, 10/10 mutants, liveness 11/11. exp-0060 uses
  unchanged source/config checksums and fresh disjoint openings.
- **Rank rationale / outcome:** was the only pending component with a valid
  positive screen and a direct confirmation path. exp-0060 CONFIRMED the race
  increment (+27.0085 [+20.8746,+33.1592]) over threats. exp-0062 then measured
  the integrated threats+race candidate DIRECTLY vs published dev5 (15,000
  games): **+40.7732 [+36.2091,+45.3513]**, valid but **GATE UNMET** (point < +75,
  LCB < +50, UCB +45.35 < +75). This closes the race/integration direction as
  insufficient for the gate; it does not authorize summing component estimates.
  Next work must be a distinct source-grounded improvement or a
  semantics-preserving optimization of a cost-blocked mechanism, followed by a
  new direct integrated measurement.

### 2. NEW eval candidate: king-facing slider battery / x-ray alignment

- **Weakness:** `KingDanger*` counts attacks into a fixed king zone
  (`evaluation.cpp:576–590`, breakdown 733–745). A rook/queen aligned with the
  enemy king behind one blocker, or a bishop/queen battery on a diagonal, can be
  strategically dangerous even when the immediate zone-hit count is small.
  exp-0052 added nonlinear concentration of *zone hits*, not ray alignment.
- **Mechanism:** for each side, count enemy sliders on rays to its king with at
  most one intervening blocker; fixed internal weights by slider type/blocker
  count, symmetric cap, middlegame-dominant scale row appended default-zero.
  Reuse existing occupancy and slider attack geometry where possible; no new
  full attack table. Gate flag default OFF.
- **Distinction:** not KingSafetyQuadratic (nonlinear zone hits), not threats
  (material exposure), not PST/king shield. New representational class.
- **Cost:** must be fused into existing king-danger/slider loops and pass the
  same prospective ≤5% increment / ≤10% total eval budget before games. If it
  cannot, optimize semantics-preservingly or reject pre-game.
- **Falsifiable hypothesis:** same-binary screen on top of the best confirmed
  eval shows point ≥ +15 with LCB > 0 and powered nulls; otherwise close.
  No claim it can alone reach +75.
- **Implementation/validation plan:** append one row; independent python-chess
  ray/blocker oracle; breakdown/live/incremental agreement; mutation matrix
  including live-path-disabled; liveness probe; cost gate; fresh disjoint
  openings; preregistered numeric compute budget.
- **Rank rationale / outcome:** plausible representational gap, but no game
  evidence yet; king-safety nonlinear attempt was inconclusive, so confidence was
  moderate-low. Implemented with an explicit **16-point cap** and default-off row;
  correctness/liveness passed (800/0 oracle, 8/8 mutants, 18/18 tests, depth-8
  probe). exp-0061 then **FAILED the prospective CI cost gate before games**
  (increment median 1.17094 > 1.05; combined 1.25063 > 1.10; A/A calibrated), so it
  is closed as blocked with zero games and no strength claim. Any future attempt
  must be a semantics-preserving optimization or a distinct mechanism under the
  same limits and a fresh prereg. exp-0060 pin untouched.

### 3. Single-feature passed-pawn rook support / connected passer revisit

- **Weakness:** passer score lacks rook-behind/adjacent-passer support;
  `extended_counts()` around `evaluation.cpp:255–280`.
- **Mechanism:** one feature at a time, default-zero row already present.
- **Distinction/problem:** exp-0026 six-feature bundle regressed and was
  abandoned; exp-0027/0028/0029 closed the bundle. A single-feature ablation is
  scientifically different but historically adjacent and may be perceived as
  reopening a closed direction. Requires explicit justification and no bundle.
- **Cost:** existing gated extended path; historical enabled cost ~13% combined
  loop, likely too high for current ≤5% increment unless fused/optimized.
- **Hypothesis/validation:** only if candidate 2 fails and a single mechanism can
  be isolated without retuning the bundle; oracle/cost/liveness/mutations.
- **Rank rationale:** lower because of negative bundle evidence and cost risk.

### 4. Proper turn-on of continuation/counter-move ordering

- **Weakness:** quiet ordering uses main history/killers; continuation/counter
  tables exist but ship OFF (`search.hpp:71–72`, `search.cpp:291–300,374–390`).
- **Mechanism:** enable one switch, same-binary ablation.
- **Distinction/problem:** dev3 ordering bundle measured neutral/negative in
  source comments; exp-0014 ablations were no-ops on already-off switches;
  exp-0058 CaptureHistory rejected. Continuation is distinct but same family.
- **Cost:** small table updates; node savings are not strength evidence.
- **Hypothesis/validation:** bounded screen only if eval directions exhaust;
  powered nulls and fresh openings.
- **Rank rationale:** low prior plausibility after ordering-family failures.

### 5. REJECTED: TT history-context relaxation

- **Weakness:** main TT keys on `history_context` (`search.cpp:538`,
  `transposition_table.cpp:66–126`), lowering hit rate.
- **Why rejected:** `position.cpp:586–587,627` shows historyContext encodes known
  reversible history; relaxing it can reuse values across different repetition
  histories and compromise draw soundness. Not a safe strength lever without a
  separate correctness proof. No experiment.

### 6. REJECTED for gate: speed-only micro-optimizations

- **Weakness:** profile shows attack recomputation / next_move overhead
  (exp-0047). Shared AttackMap was bit-exact but slower and reverted.
- **Why rejected:** exp-0047 bounded bit-exact speed ceiling ~+3–8 Elo; speed
  alone cannot reach +75. Use only as liveness/cost diagnostics.

## Immediate execution rule

Do not insert any new feature into exp-0060's source pin. After exp-0060 is
exported and independently audited: if confirmed, freeze a direct integrated
threats+race gate prereg; if not, close per its frozen rule. Candidate 2 is the
next *new mechanism* to design, but only with a fresh prereg, cost gate, and
numeric budget. No historical verdict is reopened.
