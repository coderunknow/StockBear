# dev6 ranked research matrix (2026-11-04, frozen before exp-0037 evaluation)

Evidence base actually read: `docs/DEV6_PREREG.md` §8 (unchanged gates),
`benchmarks/FAILURE_LEDGER.md` (exp-0001…0036), `docs/DEV6_RESEARCH.md`
(dev6 segments 1-3), `docs/DEV4_BENCHMARKS.md`, `docs/DEV5_EXPERIMENTS.md`,
`docs/DEV6_EXP0036_REPORT.md`, `src/search/search.cpp`, `src/search/timeman.cpp`,
`src/evaluation/evaluation.cpp`, `src/uci/uci.cpp`, `scripts/tournament.py`.

## Hard environmental facts that drive the ranking
1. **40+4 ms clock model** (`scripts/tournament.py:322-376`): clocks start at
   40 ms, `clock -= elapsed; if <0 -> TIME_FORFEIT; clock += 4`. The steady-state
   per-move budget IS the 4 ms increment; the 40 ms is a one-time buffer.
   `FullSoftBudget` (exp-0004) was **-21.0 [-44.4,+2.1]**, forfeit-driven.
   **"Use more of the clock" is a confirmed invalid lever — do not repeat.**
2. **NPS is the dominant lever**: dev6 diagnostic `dev4 vs dev4-seeing-half-clock`
   = **+89.9 [+65.9,+114.7]** at 40+4 ⇒ ~2x nodes ≈ +90 Elo. But only
   **bit-exact** speedups count: `qlite` (skip king-danger/mobility in qsearch)
   gave +23 % NPS yet **-32.1 [-55.8,-8.6]**; eval quality in qsearch is
   load-bearing. `PGO`, TT packing, THP, SEE-dedup were neutral; `incremental
   eval` was -27 % NPS. `-mpopcnt -mbmi2 -mlzcnt` gave +12-20 % NPS but only
   **+3.6 [-19.6,+26.9]** Elo — small NPS gains move Elo weakly.
3. **All default-ON pruning/extension/ordering switches are load-bearing**
   (NullMove -28.4, LMR -68.9, Aspiration -83.4, CheckExtension -31.5,
   SEEPruning -71.8 at 40+4). "Disable work for NPS" is DEAD.
4. **Default-OFF dev4 switches are measured negative**: ModernLMR -28.7/-30.9
   (dev4), -7.2 (dev5); MoveCountPruning -39.3/-104.2 (dev4), -34.9 (dev5);
   IIR -14.9/+6.6 (dev4), -1.4 (dev5); Improving -26.4/-13.0 (dev4), +5.8
   (dev5). Do not re-screen these "on" variants without genuinely new evidence.
5. **Evaluation**: `evaluate()` already has tapered MG/EG, PSTs, mobility,
   king danger, pawn shield, passed/connected/backward pawns, rook-on-7th,
   outposts, bishop pair. Champion `params_abc.txt` + `TTEval=true` came from a
   885k-position tune; outcome-retune family plateaus at +40..+48 at 40+4.
   Best-of-N param selection on small screens is a recorded dead end.
6. **Small CPU NNUE** is ~4x slower and much weaker (exp-0001); rejected.
7. **exp-0036 (fixed-time, local dedicated core)**: `BadCapturePruning=true`
   = **+21.52 [+10.28,+32.81]** vs immutable official dev5, 1,994 games,
   both batches positive, nulls clean, 0 forfeits. Gate 1 needs >= +75 with
   LCB > +50, i.e. roughly **+53 more Elo**. A single +10..30 trick will not
   close the gate; a preregistered *bundle* of independently validated gains
   is the only credible path.
8. **Fixed-node ≠ fixed-time**: exp-0035 +27.10 fixed-node vs exp-0036 +21.52
   fixed-time. Fixed-node screens are cheap filters only, never gate evidence.
9. **Gate 4 requires** a packaged candidate artifact that IS the tested binary,
   with source SHA → build → binary SHA → results → CI unambiguously linked,
   CI on the exact final source, and downloadable auditable evidence. Tier 2
   (local dedicated core) can never satisfy it.

## Ranked matrix

| rank | direction | mechanism / novelty | expected Elo | P(real gain) | complexity / risk | detectability | compute | verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | **Tier-1 infrastructure + artifact export** | dispatchable isolated-VM lane, no auto pushes, packaged binary tested, evidence retrievable via git/Contents API | 0 (enabler) | — | medium / low | — | low | **DO FIRST** — Gate 4 hard blocker |
| 2 | **exp-0037 ProbCut** — CLOSED/ABANDONED at frozen Stage-1 rule (+3.78 [−9.34,+16.90], point < +10); do not retune | raised-beta reduced-depth verification cuts the whole subtree; distinct from bad-capture/razoring; default-off switch | +5..25 | 0.45 | low / TT-pollution risk | good (two batches) | ~2.4k games | **CLOSED** (Stage-1 rule, no Stage 2a) |
| 3 | **exp-0038 dedicated qsearch TT** — REGISTERED, Tier-1 40+4 ms screen run 41780333569; profiling found hits concentrated on cheap early-return nodes (−0.0006 % nodes, +3.86 % time) | qsearch currently has NO TT: every stand-pat recomputes full `evaluate()`; cache qsearch bounds under a depth-0 namespace | +10..30 | 0.40 | medium / mate-score & draw-context correctness | good | ~2.4k games | **CLOSED** (Tier-1 +7.68 [−1.07,+16.43]; frozen UCB<+20; abandoned) |
| 4 | **Preregistered bundle** of validated switches (badCapture + ProbCut + …) | new single candidate measured FRESH with its own nulls, NOT post-hoc combining of old results | +35..60 cumulative | 0.35 | low / requires each part isolated first | full Gate-1 sample | ~13.2k games | **exp-0039**, only after 2 & 3 |
| 5 | **Singular / tactical extensions** | re-search a move whose TT value looks singular; check extension currently capped at depth<=3, max 3 | +5..25 | 0.35 | high / search instability | medium | ~2.4k games | deferred |
| 6 | **TT replacement / depth-preferred policy** | protect deep entries from shallow overwrites; also necessary if ProbCut writes shallow entries | +0..10 | 0.25 | low / changes node counts → bench signature risk | weak | ~2.4k games | deferred; bit-exactness first |
| 7 | **Bit-exact eval throughput** (cache mobility/king-danger by pawn structure; vectorise feature loops) | gprof: eval 25-30 % of node time, king danger 18 %, mobility 9 % | +10..40 | 0.20 | high / qlite showed eval quality is critical; must be bit-identical | good | profile first | deferred, high EV but hard |
| 8 | **Aspiration window / margin recalibration** | UCI options already exist; ledger lists as backlog | +0..15 | 0.20 | low / best-of-N param selection is a dead end | weak | ~2.4k games | **REJECT** as primary (repeat pattern) |
| 9 | **Larger bullet-matched tuning corpus / new eval features** | new PST/king-safety terms beyond the six harmful extended features | +10..30 | 0.25 | high / needs accuracy→strength link | medium | large | deferred |
| 10 | **NNUE with accuracy→strength link** | larger net + measured accuracy/Elo relation | unknown | 0.10 | very high / 4x slower small net already failed | — | unavailable | deferred |
| 11 | **Time management / FullSoftBudget / move-overhead** | — | negative | — | — | — | — | **REJECT** (exp-0004, forfeit physics) |
| 12 | **ModernLMR / MoveCountPruning / IIR / Improving / dev3 ordering** | — | negative | — | — | — | — | **REJECT** (measured negative twice) |
| 13 | **PGO / TT packing / THP / SEE-dedup / incremental eval / qlite / small NNUE / razoring** | — | negative/neutral | — | — | — | — | **REJECT** (recorded dead ends) |

## Why direction 2 (ProbCut) is executed first, not because it was preselected
It was independently re-evaluated above. It is the cheapest **genuinely new**
search mechanism with a low correctness risk and a clean same-binary
single-switch ablation; it is also already frozen in
`docs/DEV6_PREREG_EXP0037.md` before any result, so executing it costs no
new preregistration and respects "never tune on the test set". Direction 3
(qsearch TT) has higher theoretical upside but materially higher correctness
risk, so it is sequenced after ProbCut's implementation/validation patterns
are proven. Direction 4 is the only realistic route to +75 and is explicitly
registered as a FRESH candidate, not as a post-hoc sum.

## Scheduler / compute trade-off (explicit)
- **Tier 2 (local 2-vCPU dedicated core)**: profiling, fixed-node screens,
  correctness, determinism, cheap fixed-time screens with the frozen Stage-0
  validity gate. ~0.6 s/game → 1,200 games ≈ 12 min. NOT gate evidence.
- **Tier 1 (GitHub-hosted `ubuntu-latest`, one dedicated VM per matrix job)**:
  all decisive 40+4 ms matches. Public repo → no billing. Shard into
  1,100-game jobs (~18 min each) so retries are cheap and no single job
  exceeds 420 min.
- **Screen size**: 600 games/batch gives ±17 Elo; 1,000 games/batch ±13 Elo.
  A +20 Elo effect is detectable with ~1,000 games/batch; a +75 Elo effect
  needs only ~600. **Full Gate-1 confirmation**: 3,300 pairs/batch
  (±7.4/batch, ±5.2 combined) — reserved ONLY for a candidate whose Tier-1
  screen point >= +55, because spending 13,200 games on a +20 candidate is
  wasteful (exp-0036 already proved that).
- **No duplicate runs**: `workflow_dispatch` only, `concurrency` group per
  (experiment, source SHA), pinned `source_sha` input, fingerprint recorded.

## Execution loop
`Inspect → Research → Rank → Preregister → Implement → Validate →
Benchmark → Audit → Diagnose → Record → Continue.` Every experiment closes
at its own frozen rule; the mission never closes on a failed experiment.

## Post-exp-0037 re-ranking evidence (added before exp-0038 results)

- exp-0037 confirmed a structural rule: at the 40+4 ms budget any mechanism
  that must SPEND a verification subtree before saving one is net-negative.
  exp-0038 (qsearch TT) was chosen because it reuses information rather than
  buying it with a new subtree; it is still NOT assumed to work.
- **exp-0039 (dead static evaluation on TT hits) was eliminated at profiling**,
  not benchmarked: a bit-exact fix was built and validated, but the measurable
  speedup (~2.9 %) sat below the ~7 % build-layout / shared-vCPU noise floor
  measured on the identical code path. See DESIGN_LOG and FAILURE_LEDGER for
  exact numbers. This is an explicit sample-size/precision/cost decision: no
  Tier-1 games were spent on an unresolvable effect.
- qsearch already prunes SEE<0 captures when `seePruning` is enabled, so
  "qsearch losing-capture pruning" is NOT a new direction; it is shipped.
- Ranked unexecuted directions after exp-0038: (5) singular/tactical
  extensions, (6) TT replacement policy, (7) bit-exact eval throughput,
  (9) larger bullet-matched eval corpus. A preregistered FRESH bundle of
  validated mechanisms remains the only credible route to Gate 1 and must
  never be a post-hoc sum of earlier point estimates.

## exp-0038 closure and evidence-driven re-ranking (2026-11-04)

exp-0038 was a genuine Tier-1 40+4 ms isolated-VM experiment, not a proxy:
Stage-0 validity PASS (0 forfeits), null PASS, both batches positive, combined
`+7.6755 [−1.0670, +16.4278]` on 1,996 games / 996 clusters, independent audit
44/44 PASS. It closed at the FROZEN UCB < +20 rule; see
`docs/DEV6_EXP0038_REPORT.md`. Consequently no bundle including qsearchTT may
be proposed from these results (the frozen ADVANCE condition was not met).

New structural evidence now changes the ranking of time allocation. Reading
`TimeManager::start` with the actual 40+4 ms tournament clock shows
`usable = remaining - 10`, `slice = remaining/30`, `target = slice +
3*increment/4` (~4 ms at remaining=40 ms), `hard = min(usable, remaining/3,
target*4)` (~13 ms), plus early stops at 55-70 % of that soft budget. Both
engine arms therefore think roughly the 4 ms increment and leave the 40 ms
banked clock almost untouched for the whole game. exp-0004's `FullSoftBudget`
only removed early stops at that SAME tiny soft budget and caused forfeits on a
shared 2-vCPU host; it did NOT test the SIZE of the soft budget. exp-0038 has
now demonstrated 0 forfeits on isolated Tier-1 VMs. A self-correcting banked-
time allocation that spends part of the initial clock in the opening and
converges back to the increment is therefore a DIFFERENT, still-unexecuted
mechanism with the largest remaining expected upside (roughly +1-2 plies of
depth in the first ~10 moves). It is re-ranked from REJECT to NEXT (exp-0040),
but only with a preregistered Stage-0 forfeit-safety gate, identical 40+4 ms
clocks for both arms, and no per-move movetime injection. This is a re-ranking
on new code/measurement evidence, not a repeat of exp-0004.

All other rankings are unchanged; singular/tactical extensions, TT replacement
and bit-exact eval throughput remain deferred. No direction is claimed
exhausted, and no experiment result can terminate the mission.

## exp-0040 closed at profiling; exp-0041 is the new ranked top direction

exp-0040 is NOT a repeat of exp-0004: it changed the SIZE of the soft budget
(`increment + remaining/20`) while keeping both early stops and the hard-budget
reserve. It was eliminated at profiling with an instrumented confirmation that
the switch is live (soft 4 -> 6 ms, hard 13 ms) but the search tree is
bit-identical (depth 6, 12,539 nodes, 5 ms) because `SB_EARLY_PERMILLE=550`
and `SB_CLOCK_PERMILLE=700` dominate at 40+4 ms. Time allocation is therefore
**REJECT again, on new evidence**, and any future candidate in this family must
first prove it changes the search tree at 40+4 ms. No Tier-1 games spent.

**exp-0041** (extend validated losing-capture pruning to all remaining depths
with the frozen `BadCaptureMargin=100`) is re-ranked to **NEXT / EXECUTING**.
Rationale: exp-0036 is the only mechanism with positive fixed-time evidence;
exp-0037/0038 failed by spending work before saving it; exp-0040 failed by
changing a budget that another gate absorbs. Extending WHERE a validated
mechanism applies is the remaining direction that demonstrably changes the
search tree (−42.1 % fixed-depth-12 nodes) without adding per-node overhead.
It is a scope hypothesis, not best-of-N parameter selection: margin, SEE,
PV/mate/check/hash guards and all other parameters are frozen. Frozen prereg,
fresh suites, Stage-0 validity gate and Tier-1 40+4 ms screen are registered
before any evaluation game. Expected upside +10..30 Elo; complexity low;
regression risk medium (deep sacrifices / ordering instability); statistical
detectability good with two 1,000-game batches; architecture compatibility
high. Gate 1 (+75 / LCB > +50) is still far away; a fresh FRESH-measured
bundle of validated mechanisms, never a post-hoc sum, remains the only
credible route and is only authorised by a frozen ADVANCE rule.

Unexecuted ranked alternatives remain singular/tactical extensions, TT
replacement policy, bit-exact qsearch eval throughput (requires its OWN
prereg, not a silent reuse of the abandoned exp-0038 cache), and a larger
bullet-matched eval corpus / NNUE-with-accuracy-link. No direction is claimed
exhausted. The mission is NOT terminated by any of these closures.

## exp-0041 closure and re-ranking

exp-0041 is a genuine Tier-1 40+4 ms result, not a proxy: Stage-0 validity
PASS, null PASS, combined `−5.0635 [−15.1810, +5.0454]` on 1,995 games / 995
clusters, independent audit 44/44 PASS with a seeded cluster bootstrap. It
closed at the FROZEN UCB < +10 and point <= 0 rule. batchB `−12.5887` also
fails the frozen "both batches >= −5" condition, so no ADVANCE and no bundle.
`BadCaptureAllDepths` is ABANDONED; `BadCaptureMargin=100` stays frozen.

Consequence for the ranking: three independent throughput/node-saving
directions (portable flags, qlite, exp-0041) have now failed to convert to
fixed-time strength. Downgrade ALL "delete more nodes" directions. Raise
mechanisms that improve the ACCURACY of a decision at roughly the same node
count: (1) singular/tactical extensions with a genuine re-search, (2) TT
replacement / depth-preferred policy, (3) move-ordering accuracy
(capture/continuation history with a fresh prereg, noting default-OFF dev4
switches were previously negative), (4) a NEW frozen prereg for bit-exact
qsearch `evaluate()` throughput, (5) a larger bullet-matched eval corpus with
an explicit accuracy-to-strength link. Time allocation stays REJECT on the
exp-0040 evidence. No direction is claimed exhausted; the mission is NOT
terminated by any closure. Gate 1 remains UNMET.

## exp-0042 is the executing direction; ranked alternatives after exp-0041

exp-0042 (`MaxGainDelta`) is the first direction chosen under the post-exp-0041
ranking rule "improve decision accuracy rather than delete nodes". It reuses
the already-generated legal quiescence captures to replace a worst-case queen
constant with the position's ACTUAL maximum gain (SEE gain[0], promotion-safe),
keeping the original conservative check and the frozen `deltaMargin=200`. It
is a scope-free algorithmic change, not best-of-N parameter selection. Frozen
prereg, programmatic zero-overlap opening suites (1,400 vs 29,202 earlier
openings), ASan/UBSan validation and a Tier-1 40+4 ms screen are in place
before any evaluation game. Expected upside +5..25 Elo; complexity low;
regression risk medium (stand-pat decisions are load-bearing, cf. qlite);
statistical detectability good with two 1,000-game batches; architecture
compatibility high.

Remaining ranked unexecuted directions: singular/tactical extensions (note the
exp-0037 warning that verification subtrees are expensive at 4 ms — any such
prereg MUST include a mechanism-live and overhead diagnostic), TT replacement
policy (likely INERT at 40+4 ms because a 16 MB TT is far from full at ~10k-30k
nodes/move, so profile before spending a tournament), a NEW frozen prereg for
bit-exact qsearch `evaluate()` throughput (never a silent reuse of the
abandoned exp-0038 cache; note a +3-8 Elo bit-exact NPS effect is NOT
detectable with 2,000 games, so it needs a much larger sample), and a larger
bullet-matched eval corpus with an explicit accuracy-to-strength link. Gate 1
(+75 / LCB > +50) remains far away; no direction is claimed exhausted and the
mission is NOT terminated by any closure.

## exp-0042 closure (two Tier-1 runs, no pooling)

exp-0042 screen: `+2.6110 [−7.9556,+13.1825]` on 1,998 games -> INCONCLUSIVE
under frozen rules, which triggered the preregistered "more samples" clause.
Bounded confirmation on 1,995 fresh games: `−10.8281 [−21.8567,+0.1787]` ->
CLOSE / ABANDONED. Both runs had Stage-0 validity PASS (0 forfeits), nulls
including zero, 44/44 independent AUDIT PASS and seeded cluster bootstrap
agreement. Screen and confirmation CIs overlap; they were NEVER pooled, per the
frozen addendum. `MaxGainDelta` stays OFF; `deltaMargin=200` frozen.

Consequence: exp-0041 (delete more nodes) and exp-0042 (make a qsearch pruning
decision more accurate) have both failed. Quiescence stand-pat values are
load-bearing in this engine, consistent with the earlier qlite rejection.
Downgrade the entire family of "change which qsearch nodes are searched".
Re-rank the remaining unexecuted directions: (1) singular/tactical extensions
with a genuine re-search — but exp-0037 proved verification subtrees are
expensive at 4 ms, so any prereg MUST first show the mechanism is live and
quantify its overhead; (2) move-ordering accuracy improvements that do NOT
rewrite stand-pat values; (3) TT replacement policy — profile first, since a
16 MB TT is far from full at ~10k-30k nodes/move and is likely inert at 40+4
ms; (4) a NEW frozen prereg for bit-exact qsearch `evaluate()` throughput,
sized from the power analysis (a +3-8 Elo NPS effect is NOT detectable with
2,000 games); (5) a larger bullet-matched eval corpus with an explicit
accuracy-to-strength link. Gate 1 (+75 / LCB > +50) remains far away; no
direction is claimed exhausted, no result terminates the mission, and no
strength claim is made.


## exp-0043 is the executing direction (post-exp-0042 rank 1)

exp-0042 CLOSED/ABANDONED after a screen `+2.6110 [−7.9556,+13.1825]` and an
independent bounded confirmation `−10.8281 [−21.8567,+0.1787]` (NEVER pooled).
With exp-0041 and exp-0042 both failing, the family "delete or re-decide
quiescence nodes" is DOWNGRADED: stand-pat values are load-bearing (consistent
with the qlite rejection). The first ranked unexecuted direction is therefore
now executing: **singular/tactical extensions**, with the mandatory
mechanism-live and overhead diagnostic demanded after exp-0037.

`docs/DEV6_PREREG_EXP0043.md` (SHA `e9fe40f053c9f4798…`) freezes a
**TT-evidence singular extension with NO verification subtree**. Canonical
singular extensions verify singularity by re-searching alternatives; exp-0037
(ProbCut) spent a verification subtree per candidate node and CLOSED at
`+3.7766 [−9.3368,+16.9008]`, so repeating it unchanged would repeat a
recorded negative direction. exp-0043 instead uses evidence ALREADY in the TT:
a slightly-shallower lower bound well above beta implies every alternative
failed on the previous iteration, so the (always first-ordered) hash move is
searched one ply deeper. The deviation from the matrix's "genuine re-search"
wording is DECLARED IN ADVANCE in the prereg; the canonical re-search variant
is deferred, not abandoned. This changes WHICH MAIN-SEARCH moves get an extra
ply: it rewrites no stand-pat value, adds no lossy qsearch rule and disables
no default-ON pruning/extension. Genuinely new mechanism, not a parameter
change.

Mandatory pre-result diagnostics from the FROZEN source (instrumented
`SB_SINGULAR_DEBUG` build, real exp-0043 suite positions):
- fixed depth 10, 16 positions: OFF 2,655,145 nodes, ON 3,024,895 nodes
  (**+13.9 % overhead**), 15,000 triggers / 8,072 applied extensions;
- FIXED TIME 40+4 ms, 24 positions × 2 repeats: OFF 222,636 / 217,259 nodes,
  ON 218,959 / 225,368 nodes, median completed depth 6 for both,
  1,093 / 1,092 triggers and 548 / 516 extensions, LIVE on 23/24 positions.

So the switch demonstrably changes the tree at the EXACT Tier-1 control, at a
bounded cost and without losing completed depth. The earlier `go depth 12`
startpos probe found 0 triggers; suite positions are the preregistered probe.
Fixed-depth/node proxies are recorded three times as MISLEADING here, so these
numbers are a VALIDITY and overhead check only — a real 40+4 ms Tier-1 screen
decides. Frozen constants (chosen from liveness/overhead, NEVER from Elo):
`SingularMinDepth=3`, `SingularDepthSlack=3`, `SingularMargin=50`,
`MaxSingularExtensions=2`; no retuning after results. 1,400 fresh openings,
seed `2026120201`, ZERO overlap with 32,041 earlier positions in 120 files,
four disjoint slices; Stage-0 validity null, candidate-options null, two
independent 1,000-game batches, isolated VMs, independent raw-JSONL audit.

Expected upside +5..30 Elo; complexity medium (per-path extension counter
restored on every return); regression risk medium (stale TT evidence, extra
plies consuming the 4 ms increment, ordering/TT-replacement interactions);
statistical detectability good with 2,000 paired games. Gate 1 (+75 / LCB > +50)
remains far away; a FRESH-measured bundle of validated mechanisms, never a
post-hoc sum, is still the only credible route and is authorised only by a
frozen ADVANCE rule.

Remaining ranked unexecuted directions: canonical singular extension with a
genuine (carefully budgeted) re-search — only after exp-0043 closes and the
overhead budget is re-measured; move-ordering accuracy that does NOT rewrite
stand-pat values; TT replacement/depth policy — PROFILE FIRST, a 16 MB TT is
far from full at ~10k-30k nodes/move and is likely inert at 40+4 ms; a NEW
frozen prereg for bit-exact qsearch `evaluate()` throughput sized from the
power analysis (+3-8 Elo is NOT detectable with 2,000 games; never a silent
reuse of the abandoned exp-0038 cache); a larger bullet-matched eval corpus
with an explicit accuracy-to-strength link. Time allocation stays REJECT.
No direction is claimed exhausted, no result terminates the mission, and no
strength claim is made.


## exp-0043 CLOSED (Tier-1 40+4 ms, no pooling, 44/0 audit PASS)

exp-0043 (TT-evidence singular extension, NO verification subtree) is a genuine
Tier-1 result, not a proxy: run `41809643084` / export `41810711486` / CI
`41809642415` SUCCESS, source `5ea5ad2…`, prereg
`e9fe40f053c9f4798…`, packaged=tested binary `c2ef506c5c6e…`, 4 isolated VMs,
9/9 SHA256SUMS OK in each of 4 bundles, 0 forfeits/illegal/engine failures,
both nulls including zero. Stage-0 `−13.1005 [−29.9568,+3.6943]`, null
`+11.2956 [−7.4505,+30.1078]`, batchA `−9.7895 [−25.2667,+5.6489]`, batchB
`−10.8390 [−25.2969,+3.5814]`, FROZEN combined `−10.3142 [−20.8915,+0.2440]`
on 1,994 games / 994 clusters, independent bootstrap `[−20.6467,+0.1748]`,
44/0 AUDIT PASS. CLOSE at the frozen `UCB < +10 OR point <= 0` rule; no
ADVANCE, no bundle, no retune, no confirmation run, switch stays OFF. Report
`docs/DEV6_EXP0043_REPORT.md`.

The mandatory mechanism-live/overhead diagnostic DID its job: the switch was
LIVE on 23/24 suite positions at the exact 40+4 ms control, so this is a real
negative result for the mechanism, not an inert experiment. Cost was +13.9 %
fixed-depth-10 nodes with median completed depth unchanged.

New structural evidence: exp-0041, exp-0042 and exp-0043 are THREE consecutive
losses for mechanisms that change WHICH nodes are searched or ADD a ply at
non-PV nodes at 40+4 ms. The only positive fixed-time directions remain
exp-0036 (shallow losing-capture pruning) and exp-0038 (qsearch information
reuse), both of which change decisions without buying a new subtree. The
canonical singular extension with a genuine re-search is now DEFERRED again:
exp-0043's measured overhead budget says a verification subtree is even less
affordable than a single extra ply, so it must not be screened unchanged.

Re-ranked unexecuted directions: (1) move-ordering ACCURACY changes with
measured ZERO or near-zero per-node overhead (pure ordering, no stand-pat
rewrite, no new pruning/extension decision, no best-of-N parameter selection);
(2) TT replacement / depth-preferred policy — PROFILE FIRST, 16 MB TT likely
inert at ~10k-30k nodes/move; (3) a NEW frozen prereg for bit-exact qsearch
`evaluate()` throughput, sized from the power analysis (+3-8 Elo is NOT
detectable with 2,000 games; never a silent reuse of the abandoned exp-0038
cache); (4) a larger bullet-matched eval corpus with an explicit
accuracy-to-strength link. Time allocation stays REJECT. Gate 1 (+75 / LCB >
+50) remains far away; a FRESH-measured bundle validated by a frozen ADVANCE
rule, never a post-hoc sum, is still the only credible route. No direction is
claimed exhausted, no result terminates the mission, no strength claim.


## exp-0044 is the executing direction (post-exp-0043 rank 1)

exp-0043 CLOSED/ABANDONED at `−10.3142 [−20.8915,+0.2440]` with a mechanism
PROVEN live at 40+4 ms (23/24 suite positions) and +13.9 % fixed-depth node
overhead. exp-0041, exp-0042 and exp-0043 are three consecutive losses for
mechanisms that change WHICH nodes are searched or ADD a ply at non-PV nodes.
The positive directions remain exp-0036 (shallow SEE-losing-capture PRUNING,
+21.52) and exp-0038 (qsearch information reuse, +7.68). Rank 1 is now
**move-ordering ACCURACY with ZERO added per-node work**.

Reading `Search::score_moves` found a concrete, previously untested
deficiency: a capture with SEE < 0 scores ~2,000,000, which is ABOVE killers
(1,500,000), countermoves (1,485,000) and every quiet history move
(|history| <= 60,000). Losing captures are therefore searched immediately
after winning captures at EVERY main-search node. Strong engines order bad
captures LAST. `docs/DEV6_PREREG_EXP0044.md` (SHA
`73ae460981a09bbf5d605205f8b77bf799b6d92a0fed4dc4abaa3a4ebc3820a5`) freezes a
pure ordering change: demote SEE-losing non-promotion captures to the tail in
the MAIN search ONLY. NO move is removed (exp-0036 removed them at depth <= 3;
exp-0041 extended that removal and lost), NO SEE/eval call is added, NO stand-
pat value or pruning/extension decision changes, and QUIESCENCE is excluded
(it already skips SEE<0 captures). Frozen `BadCaptureOrderScore = -2000000`,
frozen threshold SEE < 0 — no tunable margin, so this is NOT best-of-N
parameter selection and NOT a repeat of exp-0036/0041.

Mandatory pre-result diagnostics from the FROZEN source (instrumented
`SB_BADCAP_DEBUG`): fixed depth 10 over 16 suite positions OFF 2,655,145
nodes, ON 2,961,866 nodes (**+11.6 % tree change, ZERO added per-node work**),
424,155 demotions, LIVE 16/16; FIXED TIME 40+4 ms over 24 positions x 2
repeats OFF 228,643/236,838 nodes, ON 203,245/214,462 nodes, median completed
depth 6 for both, 22,024/24,413 demotions, LIVE 24/24. The fixed-depth node
INCREASE is disclosed as a risk (bad captures sometimes give check or refute
quickly) and is NOT spun as a positive; fixed-depth/node proxies are recorded
three times as MISLEADING here. A real 40+4 ms Tier-1 screen decides.

1,400 fresh openings, seed `2026120301`, ZERO overlap with 33,441 earlier
positions in 125 files, four disjoint slices; Stage-0 validity null,
candidate-options null, two independent 1,000-game batches, isolated VMs,
independent raw-JSONL audit. Strict validity rule: ANY time forfeit, illegal
move or engine failure in ANY of the four jobs => INVALID MEASUREMENT.

Expected upside +5..30 Elo; complexity LOW (one score constant plus an
explicit mainSearch flag); regression risk MEDIUM (sacrifices, check-giving
losing captures, moveCount/LMR interactions); statistical detectability good
with 2,000 paired games; architecture compatibility high. Gate 1 (+75 / LCB >
+50) remains far away; a FRESH-measured bundle validated by a frozen ADVANCE
rule, never a post-hoc sum, is still the only credible route.

Remaining ranked unexecuted directions: canonical singular extension with a
genuine re-search (DEFERRED again — exp-0043's measured overhead budget says
a verification subtree is even less affordable than one extra ply); TT
replacement/depth policy — CODE INSPECTION shows generation- and
depth-preferred replacement is ALREADY SHIPPED in
`src/search/transposition_table.cpp`, and a 16 MB TT is far from full at
~10k-30k nodes/move, so this direction is likely already inert at 40+4 ms and
must be profiled before any games; a NEW frozen prereg for bit-exact qsearch
`evaluate()` throughput sized from the power analysis (+3-8 Elo is NOT
detectable with 2,000 games); a larger bullet-matched eval corpus with an
explicit accuracy-to-strength link. Time allocation stays REJECT (exp-0004
forfeit-driven, exp-0040 inert). No direction is claimed exhausted, no result
terminates the mission, no strength claim is made.


## exp-0044 screen INCONCLUSIVE -> frozen bounded confirmation

exp-0044 (demote SEE-losing captures to the tail in the main search only) is a
genuine Tier-1 40+4 ms result: run `41812595433` / export `41813751266` / CI
`41812595476` SUCCESS, source `2ae4e68…`, prereg `73ae460981a09bbf5…`,
packaged=tested binary, 4 isolated VMs, 9/9 SHA256SUMS OK in each of 4
bundles, 0 forfeits/illegal/engine failures, both nulls including zero.
Stage-0 `+9.5569 [−6.6563,+25.8118]`, candidate null `0.0000
[−17.9335,+17.9335]`, batchA `+6.6419 [−8.1259,+21.4338]`, batchB `0.0000
[−15.0949,+15.0949]`, FROZEN combined `+3.3140 [−7.2389,+13.8730]` on 1,996
games / 996 clusters, independent bootstrap `[−7.1520,+13.7861]`, 44/0 AUDIT
PASS. ADVANCE false, CLOSE false => **INCONCLUSIVE** under the frozen §6 rule.

This is the FIRST non-negative combined point since exp-0038, and both batches
met the frozen ">= −5" condition, but the LCB is still negative and the point
is far below +20. Per the frozen prereg this triggers exactly ONE bounded
confirmation run, registered BEFORE any additional game in
`docs/DEV6_PREREG_EXP0044_ADDENDUM.md` (SHA `17d90a790697bb05…`) with 1,400
fresh disjoint openings (seed `2026120401`, ZERO overlap / 34,841 earlier),
its own nulls, and a strict NO-POOLING rule. If the confirmation is neither
ADVANCE nor CLOSE, exp-0044 closes AS INCONCLUSIVE and the direction is
abandoned as low expected value — a conservative compute bound, not a
threshold change.

Learning so far: a pure ordering change with ZERO added per-node work is the
first of the four recent directions not to lose outright, but its screen point
(+3.31) is within noise. Even an ADVANCE would not approach Gate 1 (+75 /
LCB > +50). No strength claim is made. Ranked alternatives remain unchanged:
canonical singular extension with genuine re-search (deferred), TT replacement
(ALREADY SHIPPED generation/depth-preferred; profile before games), a NEW
properly powered frozen prereg for bit-exact qsearch `evaluate()` throughput,
and a larger bullet-matched eval corpus. Mission ACTIVE / NOT COMPLETE.


## exp-0044 bounded confirmation -> CLOSED AS INCONCLUSIVE (compute bound)

Confirmation `41814069967` / export (retry) `41815428066` / CI `41814069925`
SUCCESS, source `0691b9a…`, addendum `17d90a790697bb05…`, 4 isolated VMs,
9/9 SHA256SUMS OK in each of 4 bundles, 0 forfeits/illegal/engine failures,
44/0 AUDIT PASS. Stage-0 `−9.5569 [−32.6787,+13.4804]`, candidate null
`+6.1422 [−14.8210,+27.1502]`, batchA `+17.0722 [+0.6984,+33.5222]`, batchB
`+10.1190 [−5.8209,+26.1015]`; FROZEN combined `+13.5977 [+2.1746,+25.0503]`
on 1,997 games / 997 clusters, independent bootstrap `[+2.4394,+24.9592]`.
ADVANCE false (point +13.5977 < +20), CLOSE false (UCB +25.0503 >= +10,
point > 0) => the FROZEN ADDENDUM compute bound gives **CLOSED AS
INCONCLUSIVE / ABANDONED**: no third run, no retune, no bundle, no default
change, no strength claim. Screen and confirmation CIs overlap and were NEVER
pooled. `scripts/dev6_exp0044_confirm_decision.py` reproduces the override
from raw games (the generic audit CLI prints the prereg §6 "more samples"
default, which the addendum explicitly overrides).

Technical repair, no scientific change: export attempt 18 failed ONLY at a
transient GitHub `Internal Server Error` evidence push; the workflow export
step now has a bounded 4-attempt retry and the export was re-dispatched as a
new valid run. Report `docs/DEV6_EXP0044_REPORT.md`.

Learning: exp-0044 is the first direction since exp-0038 to produce two
consecutive non-negative frozen combined points (+3.31, +13.60), and it did so
with ZERO added per-node work — unlike exp-0041/0042/0043, all of which lost
while changing which nodes are searched or adding a ply. But neither point
reached the frozen +20 ADVANCE threshold, and Gate 1 (+75 / LCB > +50) is
still far away. The specific `BadCaptureOrdering` mechanism and any retune are
ABANDONED; a genuinely DIFFERENT mechanism requires its own frozen prereg and
fresh suites and may not reuse exp-0044 data. Ranked alternatives unchanged.
Mission ACTIVE / NOT COMPLETE; no direction is claimed exhausted.


## exp-0045 is the executing direction (post-exp-0044 rank change)

exp-0044 CLOSED AS INCONCLUSIVE / ABANDONED at its frozen addendum compute
bound (screen `+3.3140 [−7.2389,+13.8730]`, confirmation
`+13.5977 [+2.1746,+25.0503]`, NEVER pooled). Its specific mechanism and any
retune are abandoned. exp-0041/0042/0043 all lost while changing which nodes
are searched or adding a ply; exp-0044 was the first non-negative result since
exp-0038 and added ZERO per-node work.

The next ranked unexecuted direction that changes NO search decision is
**bit-exact `evaluate()` throughput**, explicitly requested as a NEW properly
powered frozen prereg. exp-0039 built exactly this fix (dead static evaluation
on TT hits), verified it bit-exact, measured ~2.9 % locally against a ~7 %
shared-vCPU noise floor, REVERTED it, and spent NO games / made NO Elo or
speedup claim. That was a precision/cost decision, not a negative strength
result. `docs/DEV6_PREREG_EXP0045.md` (SHA
`0abf66836ed0ad6d9…`) therefore freezes the FIRST Elo measurement of the
hypothesis, on isolated VMs at FIXED TIME 40+4 ms, with a single default-off
switch `SkipDeadTTEval`.

Mandatory pre-result diagnostics from the FROZEN source: node counts OFF/ON
IDENTICAL at depths 8/10/12; ON skips 40,187 of 379,656 `evaluate()` calls
(10.6 %) so the mechanism is LIVE; local 12-repeat timing OFF 804.0 ms / ON
823.5 ms (−2.37 %, noise-dominated, reported verbatim, NO speedup claim).
Only ~10.6 % of evaluations are skippable, so the theoretical speedup is
~2-3 %. Honest POWER STATEMENT: a 2,800-game screen has ~13 Elo half-width
and cannot resolve a +2-3 Elo effect; it is powered only for the +20 ADVANCE
threshold and to rule out a material regression. A SINGLE-RUN compute bound
closes exp-0045 AS INCONCLUSIVE if neither frozen condition holds; no
post-hoc sample increase, no confirmation.

1,400 fresh openings seed `2026120501`, ZERO overlap with 36,241 earlier
positions in 135 files, four disjoint slices; Stage-0 validity null,
candidate-options null, two independent 1,000-game batches, isolated VMs,
independent raw-JSONL audit. Expected upside +0..5 Elo (below resolution);
complexity LOW (one dead call removed); regression risk LOW (bit-exact values,
no added work); statistical detectability WEAK for the expected effect, which
is exactly why the compute bound is preregistered. Gate 1 (+75 / LCB > +50)
remains far away; a FRESH-measured bundle validated by a frozen ADVANCE rule,
never a post-hoc sum, is still the only credible route.

Remaining ranked alternatives: canonical singular extension with a genuine
re-search (deferred on exp-0043 measured overhead), TT replacement/depth
policy (ALREADY SHIPPED generation/depth-preferred; profile before games), a
larger bullet-matched eval corpus with an explicit accuracy-to-strength link,
and move-ordering rules with genuinely NEW mechanisms (exp-0044's specific
switch is abandoned). Time allocation stays REJECT. No direction is claimed
exhausted, no result terminates the mission, no strength claim is made.


## exp-0045 original run INVALID MEASUREMENT -> bounded valid retry

Run `41817228668` / export `41818409701` / CI `41817228408` SUCCESS, source
`e41a0b18…`, prereg `0abf66836ed0ad6d…`, 4 isolated VMs, 9/9 SHA256SUMS OK in
each of 4 bundles, 44 stored values / 0 issues AUDIT PASS — but batchB had ONE
`TIME_FORFEIT` (game 272, 14.1 ms move, ply 118, `remaining_white_ms=-5.01`).
The FROZEN prereg §5 zero-forfeit rule in ANY job is ENFORCED: **INVALID
MEASUREMENT**, all Elo DISCARDED, no strength inference, and the generic
audit's "CLOSE" label is explicitly NOT usable (`clean=False`). Stage-0 and
candidate nulls were clean, batchA clean, 0 illegal/engine failures. exp-0043
and exp-0044 recorded 0 forfeits across ~4,000 games each at the same control,
so this is a rare long-game isolated-VM timing outlier, not a mechanism effect;
it favoured the candidate arm and could not manufacture a positive result.

Per the mission's TECHNICAL FAILURE rule, `docs/DEV6_PREREG_EXP0045_RETRY.md`
(SHA `2172063e22554df9…`) was frozen BEFORE any retry game: diagnose (done),
no out-of-scope repair to the frozen 40+4 ms control, and ONE valid NEW run of
the identical science with entirely fresh data — new experiment id
`exp0045_retry`, new dispatch attempt 22, 1,400 fresh disjoint openings seed
`2026120601` (ZERO overlap / 37,641 earlier positions in 140 files), never
pooled with the invalid run. A BOUNDED RETRY BUDGET closes exp-0045 as
TECHNICALLY UNRESOLVABLE if the retry also has any forfeit. No threshold was
weakened; the zero-forfeit rule was enforced. The bit-exact dead-eval
hypothesis remains UNRESOLVED (no Elo may be quoted from the invalid run), and
Gates 1 and 4 remain UNMET. Mission ACTIVE / NOT COMPLETE; no direction is
claimed exhausted.


## exp-0045 FINAL: CLOSE / ABANDONED (INVALID run + one bounded valid retry)

The first Elo measurement of the bit-exact dead `evaluate()` elimination
(`SkipDeadTTEval`, default OFF; exp-0039 eliminated it at profiling). Original
run `41817228668` (source `e41a0b18…`, prereg `0abf66836ed0ad6d…`, export
`41818409701`, CI `41817228408`) had ONE `TIME_FORFEIT` (batchB game 272,
14.1 ms move, ply 118, `remaining_white_ms=-5.01`) => **INVALID MEASUREMENT**
under frozen prereg §5's zero-forfeit rule; ALL Elo DISCARDED, no strength
inference, generic audit `clean=False` / "CLOSE" label NOT usable. exp-0043 and
exp-0044 had 0 forfeits across ~4,000 games at the same control: a rare
isolated-VM long-game clock outlier, not a mechanism effect, favouring the
candidate arm. No threshold weakened; the rule was ENFORCED.

`docs/DEV6_PREREG_EXP0045_RETRY.md` (SHA
`2172063e22554df99064c54e0820b70db854e2339b0d5e87ccc321b6ca0bce60`), frozen
BEFORE any retry game, authorised exactly ONE valid new run of identical
science with fresh disjoint data (seed `2026120601`, ZERO overlap with 37,641
earlier positions / 140 files), NEVER pooled, and a bounded retry budget.
Run `41818958001` / export `41821624068` / CI `41818958003` SUCCESS: 9/9
SHA256SUMS OK ×4 bundles, 0 forfeits/illegal/failures in ALL jobs, 44/0 AUDIT
PASS `clean=True`, built==packaged binary `b839fae82b54…`. FROZEN COMBINED
batchA+batchB ONLY: 1,993 games `651/640/702`, score 0.4872052,
**−8.9240 [−18.2792,+0.4182]**, Elo-from-score −8.8927, bootstrap
[−18.2107,+0.1749], 993 clusters; both null CIs include 0; both batches < −5.
ADVANCE False; CLOSE True (UCB<+10 AND point<=0). Independent reproduction:
`scripts/dev6_exp0045_retry_decision.py`. **exp-0045 CLOSED / ABANDONED**,
switch OFF, no strength claim / default change / retune / bundle / pooling /
confirmation / post-hoc sample increase. NOT a proven regression at ~13 Elo
half-width. Gates 1 and 4 UNMET; mission ACTIVE / NOT COMPLETE. Report
`docs/DEV6_EXP0045_REPORT.md`; evidence
`benchmarks/exp-runs/tier1-export/run-41818958001/`.

**Next hypothesis must be selected with its OWN frozen prereg, fresh disjoint
suites, Stage-0 validity null, candidate null, isolated VMs and independent
raw-game audit.** Do NOT repeat exp-0045 (the direction is closed), exp-0044
confirmation, or any recorded negative/neutral direction without genuinely new
evidence. A normal technical failure, invalid measurement, CI failure,
inconclusive or closed result cannot terminate the mission.


## exp-0046 is the executing direction (post-exp-0045 rank change)

exp-0045 FINAL CLOSE / ABANDONED: INVALID original run `41817228668` (all Elo
DISCARDED) + ONE bounded valid retry `41818958001` frozen combined
`-8.9240 [-18.2792,+0.4182]` on 1,993 games, CLOSE at `UCB<+10 OR point<=0`,
NEVER pooled. The bit-exact dead-`evaluate()` direction is abandoned; no
strength claim, no default change, no retune, no bundle.

Next ranked direction: **margin-adaptive null-move reduction**. exp-0041/0042/
0043 lost while changing which nodes are searched or adding a ply; exp-0044
added ZERO per-node work and was the only non-negative direction of that group
(CLOSED AS INCONCLUSIVE at its compute bound). The shipped null-move
verification subtree uses a FIXED `SB_NULLMOVE_R + depth/5`; the guard already
computes `staticEval >= beta` but discards the SIZE of the margin. exp-0046
makes ONLY that existing subtree shallower when staticEval is far above beta
(frozen 200 cp per extra ply, hard cap 2), keeping the shipped depth when the
margin is marginal. This is a NEW decision RULE with ZERO added per-node work:
no new evaluate/SEE/movegen call, no extra ply, no retune of a closed switch,
no earlier data reused or pooled. Not "delete more nodes", not a constant
retune, not exp-0041/0042/0043/0044/0045.

Pre-result diagnostics from the FROZEN default-OFF source: signatures
`243f9a1c1ba5b36f` / `a14ab62224f837e5` / `e45fa2ec2287eb41`, Release 11/11,
ASan+UBSan 11/11, UCI default false; instrumented `SB_ADAPTIVE_NULL_DEBUG`
over 24 REAL suite positions at FIXED DEPTH 10 OFF 4,311,394 / ON 4,252,622
nodes (−1.36 % tree change), 44,789 null nodes, 4,133 changed, 4,721 extra
plies, LIVE 23/24; 40 ms fixed-time PROBE OFF 1,006,703 / ON 974,327
(−3.22 %), LIVE 22/24, median depth 8 both. Diagnostics are NOT strength and
imply NO local speedup claim.

`docs/DEV6_PREREG_EXP0046.md` (SHA `dda54084d2acffddcb7cd5d1134f8734858e9bf0c69d3ab2eb59d3aeab15dd61`) and
`tier1-plan-exp0046.json` (SHA `557d51fc07ad18eb828e94b2cb273e7225956ca4e6cd55b2279216fb8ebaa18a`) FROZEN BEFORE ANY exp-0046 GAME.
1,400 fresh openings seed `2026120701`, ZERO overlap with 39,041 earlier
positions in 145 files; Stage-0 validity null, candidate-options null, two
independent 1,000-game batches, isolated VMs, independent raw-JSONL audit,
FIXED TIME 40+4 ms, never `--nodes`. Validity gate enforces 0
forfeits/illegal/UCI/engine failures in ANY job (exp-0045 lesson, NOT
weakened); at most ONE bounded valid retry with its own frozen prereg.
Expected upside modest, regression risk real (null move is load-bearing),
statistical detectability ~13 Elo half-width. ADVANCE >= +20 AND LCB>0 AND
both batches >= −5 AND both null CIs include 0 AND clean; CLOSE if UCB<+10
OR point<=0; otherwise CLOSED AS INCONCLUSIVE by the single-run compute
bound. ADVANCE alone does NOT satisfy Gate 1.

Remaining ranked alternatives: canonical singular extension with a genuine
re-search (deferred on exp-0043 overhead), TT replacement/depth policy
(ALREADY SHIPPED generation/depth-preferred; profile before games), a larger
bullet-matched eval corpus with an explicit accuracy-to-strength link, and
move-ordering rules with genuinely NEW mechanisms. Time allocation stays
REJECT. No direction is claimed exhausted, no result terminates the mission,
no strength claim is made; Gates 1 and 4 remain UNMET.


## exp-0046 FINAL: CLOSED AS INCONCLUSIVE / ABANDONED

Run `41825055840` / export `41826460428` / CI `41825055708` SUCCESS, exact
source `0792555ddd155b2426d926cccc5a16975f77682b`, prereg
`dda54084d2acffdd…`, plan `557d51fc07ad18eb…`. 4 isolated VMs, 9/9
SHA256SUMS OK ×4 bundles, 0 forfeits/illegal/failures in ALL jobs, 44/0
AUDIT PASS `clean=True`, built==packaged binary `18b9366edcaf…`, UCI
`AdaptiveNullR default false`. Stage0 399 +11.3524 [−5.1046,+27.8606];
candidate null 399 −8.7314 [−28.0469,+10.5303]; batchA 995
+3.1586 [−8.7463,+15.0709]; batchB 995 +3.8606 [−8.5988,+16.3299]; both
null CIs include 0, both batches >= −5. FROZEN COMBINED batchA+batchB ONLY
1,990 games `683/642/665`, score 0.5045226,
**+3.5096 [−5.1015,+12.1250]**, Elo-from-score +3.1427, bootstrap
[−4.9136,+12.1125], 990 clusters. ADVANCE False; CLOSE False (UCB>=+10,
point>0). Generic audit "more samples" is its §6 DEFAULT, OVERRIDDEN by the
FROZEN single-run COMPUTE BOUND; `scripts/dev6_exp0046_decision.py`
reproduces **CLOSED_AS_INCONCLUSIVE (NO further samples)**. No strength claim
(the CI includes zero), no default change, no retune, no bundle, no
confirmation, no post-hoc sample increase, no pooling. `AdaptiveNullR` stays
OFF; the margin-adaptive null-move reduction direction is abandoned. Gates 1
and 4 UNMET, 2 direction-supported, 3 PASS; mission ACTIVE / NOT COMPLETE.
Report `docs/DEV6_EXP0046_REPORT.md`; evidence
`benchmarks/exp-runs/tier1-export/run-41825055840/`.

**Next hypothesis must have its OWN frozen prereg, fresh disjoint suites,
Stage-0 validity null, candidate null, isolated VMs, FIXED TIME 40+4 ms and
an independent raw-game audit.** Do NOT repeat exp-0046, exp-0045, exp-0044
confirmation, or any recorded negative/neutral direction without genuinely
new evidence. A normal technical failure, invalid measurement, CI failure,
inconclusive or closed result cannot terminate the mission.
