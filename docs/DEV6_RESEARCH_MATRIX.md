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
