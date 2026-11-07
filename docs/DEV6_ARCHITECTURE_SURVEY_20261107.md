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

### 2. CLOSED: king-facing slider battery / x-ray alignment (exp-0061 cost block; exp-0063 rejected)

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
- **Rank rationale / outcome:** plausible representational gap, but confidence
  was moderate-low. Implemented with an explicit **16-point cap** and default-off
  row; correctness/liveness passed. exp-0061 **FAILED the prospective CI cost gate
  before games** (increment 1.17094, combined 1.25063). exp-0063 then applied a
  semantics-preserving optimization (hoisted ray masks + aligned-slider loops),
  passed a fresh prospective cost gate (increment 1.04470, combined 1.08861), but
  the 5,800-game screen was **CLOSED / mechanism rejected**: −6.0300
  [−14.1476,+2.0809] over threats+race, nulls valid. The battery direction is now
  closed by game evidence, not merely cost. No rescale/retune/pooling; exp-0060
  pin untouched.

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

## Immediate execution rule / post-exp-0063 disposition

The race confirmation and direct integration are complete: exp-0060 confirmed
the race increment; exp-0062 measured threats+race directly vs dev5 at +40.7732
[+36.2091,+45.3513] — valid but Gate 1 UNMET (UCB +45.35 < +75). The battery
direction is closed: exp-0061 cost-blocked, exp-0063 cost-passed but screen
rejected (−6.03). No historical verdict is reopened and no component Elo is
summed.

Remaining ranked directions are low-prior or cost-risky: single-feature passer
support (negative bundle ancestry, likely >5% cost), continuation/counter-move
ordering (ordering-family failures), TT history relaxation (draw-soundness risk,
rejected), speed-only work (bounded ~+3–8 Elo, cannot reach gate). None has
positive game evidence or a credible standalone path to the +75 / LCB>+50 gate.
Any further attempt requires a fresh source-grounded hypothesis, prereg,
prospective cost/correctness gates and a new direct integrated measurement; it
must not reinterpret closed verdicts. The current blocker is the non-waivable
strength gate, not infrastructure or correctness.

### 7. INCONCLUSIVE: extension-agnostic main-TT identity (exp-0064)

- **Mechanism + source location:** `src/search/transposition_table.cpp:11–19,
  68–101` mixes the per-path check-extension **budget** into the bucket index and
  the entry comparison; call sites `src/search/search.cpp:542–543,850`. The
  counter is search effort, not position, draw rules or mate normalisation.
- **Current implementation/config:** shipped identity is
  `(key, rule50, historyContext, extensions)`; `MaxCheckExtensions = 3`. New
  default-OFF switch `TTExtensionAgnostic` drops only the fourth field, via one
  shared helper used at both probe and store.
- **Prior experiments:** none on this field. Distinct from §5 (historyContext
  relaxation, rejected for draw soundness — untouched), exp-0009 (entry layout /
  THP), exp-0038 (separate qsearch cache), exp-0043 (singular extension),
  exp-0045 (dead eval on TT hits). `DEV6_RESEARCH_MATRIX.md:114` still lists TT
  identity/replacement as unexecuted.
- **Why still worth testing — measured, not assumed:** gated sibling-bucket
  instrument on 250 positions at Hash 16 shows 2.73 % / 4.59 % / 4.40 % of *all*
  probes at depths 5/7/9 are blocked **only** by this field by a deep-enough
  entry ⇒ +9.6 % / +19.4 % / +20.0 % relative hit gain available. rule50-only
  ≤0.021 %, context-only ≤0.0001 %.
- **Expected benefit / uncertainty:** exp-0015's law (~2× nodes ≈ +90 Elo) makes
  a single-digit-to-low-double-digit gain plausible; uncertainty is high because
  extra cutoffs can also return shallower/less accurate values. Fixed-depth nodes
  fell to 0.9119× at d7 — an efficiency signal, **not** a strength claim.
- **Correctness risk + controls:** a slimmer identity could corrupt mate or draw
  scores. Controls: rule50/context isolation pinned by unit tests and a 720,000-
  check model oracle; python-chess replay of every mate claim (2,453 PV moves,
  10 mates/arm, 0 problems); 13/13 mutants killed with a surviving control;
  all three bench signatures exact.
- **Runtime risk + controls:** no new evaluate/SEE/movegen call site; frozen
  fixed-depth wall-time guard ≤1.10× passed at 0.9593 (d5) / 0.8679 (d7).
- **Priority / disposition:** **INCONCLUSIVE / default OFF.** Screen measured
  **+5.2399 [+0.0235,+10.4586]** over 6,000 primary games; frozen ADVANCE bar
  was point ≥+10, frozen CLOSE bar was UCB <+3 or point ≤0, so neither fired.
  The mechanism is real (8.8 % fewer nodes at equal depth) but the lever is
  small. No extra games bought, no promotion. Calibration for future
  efficiency hypotheses: discount the node→Elo mapping, because recovered TT
  hits return shallower values.

## Disposition update after the exp-0064 investigation (append-only)

The earlier "remaining directions are low-prior" paragraph above was written
before this investigation and is superseded **only** in its claim that no
measured opportunity remained. A concrete, quantified loss of TT reuse was found
in a field that is not part of the chess position, and it is now under a frozen
preregistered screen. No closed verdict was reopened, no historical measurement
was edited, and no component Elo is summed. Gate 1 remains **UNMET** and the
mission remains **ACTIVE**.

### 8. INCONCLUSIVE: persistent cross-move quiet history (exp-0065)

- **Mechanism + source location:** `src/search/search.cpp:934–943` zeroes
  `history_` (and every other ordering table) at the start of EVERY root search,
  and `src/uci/uci.cpp:440` builds a **fresh `Search` per `go`**. Quiet-ordering
  learning is therefore discarded twice per move. At 40+4 ms (median depth 5,
  ~10–30k nodes/move) the primary ordering table never accumulates anything.
- **Current implementation/config:** `history_[us][from][to]`, bonus `depth²`,
  clamp ±60000 with saturation halving. New default-OFF `PersistentHistory`
  carries the table across searches with a bounded halving and keeps one
  `Search` alive until `ucinewgame`. Killers stay cleared; counter-move,
  continuation, capture, correction and qsearch tables are untouched.
- **Prior experiments:** none on table lifetime. This is also the **confound**
  behind the ordering family's neutral record: exp-0014's ablations were no-ops
  on already-OFF switches, exp-0058 rejected CaptureHistory, and a fresh
  diagnostic this cycle measured ContinuationHistory turn-ON at **+0.43 % nodes**
  (slightly worse) over 250 positions — a table erased every 40 ms cannot show
  its value.
- **Measured opportunity:** sequential replay of **20 real games / 2,525
  positions** at depth 7 gives node ratio **0.9654**, with **19/20 games**
  individually improving. An independent-position corpus cannot see this
  mechanism at all, which is why the diagnostic replays games in move order.
- **Expected benefit / uncertainty:** 3.5 % fewer nodes maps to only a few Elo by
  exp-0015's law, and exp-0064 taught us to discount that mapping further.
  Per-node overhead measured **1.0776** (A/A spread 0.0859, so noisy), which
  combined with the node ratio gives ~1.04 time-to-depth — the fixed-time effect
  could honestly be neutral or negative. The 6,000-game screen is the arbiter.
- **Correctness risk + controls:** reused object could leak state. Pinned: a
  reused object with the switch OFF is indistinguishable from a fresh one;
  `ucinewgame` resets; terminal/mate scores unchanged; interactive UCI lifetime
  oracle; **9/9** killable mutants killed with **2** equivalence controls
  surviving. `evalStack_` clear is provably a no-op (write at `:622` precedes the
  guarded read at `:628`) and is recorded as defensive hardening, not a fix.
- **Runtime risk + controls:** no evaluation change; frozen **fixed-node** cost
  guard ≤1.10 passed at 1.0776.
- **Priority / disposition:** **INCONCLUSIVE / default OFF.** Screen measured
  **+9.7673 [+3.3767,+16.1645]**; the frozen ADVANCE bar was point ≥+10, missed
  by 0.23 Elo, so neither ADVANCE nor CLOSE fired. No rounding, no extra games,
  no promotion. The structural finding is real and the evidence points the right
  way, but the bar governs.

### 9. NEXT (unregistered): persistence for the still-erased ordering tables

- **Mechanism + source:** `search.cpp` still zeroes `continuation_`,
  `counterMoves_` and `captureHistory_` every root search. exp-0065 fixed only
  `history_`. The same "erased every 40 ms" confound therefore still applies to
  these tables, and the ContinuationHistory turn-ON diagnostic (node ratio
  **1.0043**, slightly worse) was measured WITH that confound present.
- **Why worth testing:** continuation history is a large ordering lever in
  strong engines; it has never been measured with a table that can actually
  learn across moves. Requires its OWN prereg; exp-0065 games may NOT be pooled.
- **Risk:** per-node update cost on a ~200k-entry table; must pass a fixed-node
  guard. Correctness risk low (pure ordering heuristic).
- **Controls:** same-binary ablation, powered nulls, fresh disjoint openings,
  sequential-replay efficacy gate, mutation matrix, default-OFF bench pins.
- **Priority:** highest unregistered. **Not yet preregistered — no games.**
