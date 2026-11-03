# StockBear Failure Ledger

Append-only record of failed, neutral, regressive and inconclusive experiments.
Corrections are appended with a reference to the original entry; entries are
never deleted. Experiment IDs use `exp-NNNN` (release versions stay at
`v0.1.0-dev5`; `benchmarks/results/0.1.0-devN/` directories are historical
archives only).

Statistical conventions used throughout: Elo differences are opening-clustered
(CR1 on per-opening pair totals, Student-t on G-1 df, logistic scale, two-sided
95% CI) from `scripts/tournament.py` / `scripts/match_stats.py`; "clean" means
the match ran alone on the idle 2-core sandbox. Baseline = immutable dev4
binary SHA-256 `1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae`
(bench `243f9a1c1ba5b36f`), 40+4 ms, hash 16, threads 1, max-plies 240 unless
noted. Hardware: sandbox 2 vCPU (Intel Xeon 2.60 GHz), ~3.9 GB RAM, 20 GB disk.

---

## exp-0001 — NNUE evaluation nets (dev5 cycle, rounds 1-3)

- **ID / date / source:** exp-0001, 2026-11-01..02, commits in dev5 range
  (final verdict in `ef980a0`); binary dev5 `be2341455d59c92c...`.
- **Files / artifacts:** `src/evaluation/nnue*.cpp`, `scripts/train_nnue2.py`,
  `nnue-work/` reports; raw: `benchmarks/results/0.1.0-dev5/` (NNUE screens).
- **Hypothesis:** a small NNUE (HalfKP-style, king buckets 1/4/16, L1 128)
  trained on Stockfish-11 search labels would beat the 32-feature classical
  eval. Evidence: none measured positive; it was the standard architecture.
- **Implementation:** incremental accumulator in Position (nnueStack_),
  quantised inference, output-scale sweep, teacher labels at nodes 50000
  (SF11 binary SHA `bc9e5ed4...`, external teacher only, never incorporated).
- **Conditions:** 479k-position corpus (SHA in `docs/DEV5_TRAINING.md`) + 310k
  SF11 labels; fixed-node screens n3000/n8000/n50000; CPU-only training.
- **Results:** best net b4cp3 (`nnue-work/b4cp3/net.nnue` SHA `6b5aec3d...`):
  n3000 −651.9 [−800.9,−571.2]; n8000 −719.7 [−917.0,−628.2]; n50000 3-1-116.
  Output-scale sweep (285.71/150/75): −651.9 / −759.1 / −759.1. Inference
  bit-exact vs python reference (KQ-vs-K etc.), so no implementation bug.
  Outcome correlation 0.473 vs classical 0.646; Brier 0.205 vs 0.099; output
  std 1127 cp vs 470 cp. NNUE also ~4x slower (0.46M vs 1.85M nps).
- **Classification:** strength regression (+ correctness OK, training failure).
- **Root cause (confirmed):** trained nets are a weaker evaluator than the
  hand-tuned classical one in actual play; underfit (val corr 0.487) and
  miscalibrated output. Not an inference bug (bit-exactness proven).
- **Failure conditions:** at every depth and output scale tried; at 40+4 the
  4x NPS deficit alone would cost ~-180 Elo even before eval weakness.
- **Can it fail again?** Yes — repeating this pipeline (CPU-only training on
  310k SF labels, small net) will reproduce it. A substantially different
  implementation (much larger data, better architecture, fast SIMD inference)
  is theoretically possible but unproven here; GPU is unavailable in the
  sandbox. Avoid: CPU-only torch training of small nets as a strength lever.
- **Lessons / next:** classical eval saturates at ~+10-25 fixed-time but NNUE
  needs orders of magnitude more data/compute than available. Next: focus on
  classical eval + search at bullet, or distillation only with calibrated
  targets (see exp-0004).
- **Decision:** rejected under tested conditions.

## exp-0002 — SF centipawn distillation into classical eval (params_cp)

- **ID / date / source:** exp-0002, 2026-11-02, dev5 range; binary dev5.
- **Files/artifacts:** `scripts/tune_eval2.py --target cp`, `scripts/label_search.py`,
  `benchmarks/results/0.1.0-dev5/screen-n*-params-cp.*`.
- **Hypothesis:** distilling SF11 cp labels into the 32-feature linear model
  would transfer teacher strength.
- **Results:** 480 g fixed-node: −30.6 [−57.0,−4.5]. Consistent with dev3's
  finding that the feature set saturates.
- **Classification:** strength regression.
- **Root cause:** 32 linear tapered features cannot represent SF's eval; cp
  distillation also miscalibrates search margins (cp scale changes).
- **Can it fail again?** Yes, same reason. Avoid raw-cp distillation into this
  feature set. Alternative: outcome labels (exp-0005) or richer features.
- **Decision:** rejected under tested conditions.

## exp-0003 — Search ablation regressions (dev5: MoveCountPruning, ModernLMR; ordering switches)

- **ID / date / source:** exp-0003, 2026-11-02, dev5 range (commits up to
  `ef980a0`); binaries dev5 `be234145...`, safe `13d3a6840...`.
- **Results (clean 40+4, 480 g):** MoveCountPruning −34.9; ModernLMR −7.2;
  continuation-history ordering switch −17.5 [−39.6,+4.5]; ch+cap −3.6
  [−25.8,+18.5]; null control +13.9 [−9.3,+37.2]. dev5 confirmation (1100 g,
  untouched suite `75824edb...`, seed 2026110205): safe-mobility candidate
  **+15.9 [+0.6,+31.2]**, null +5.4 [−9.8,+20.6] -> gate failed.
- **Classification:** strength regression (pruning switches) / inconclusive
  (dev5 champion below gate).
- **Root cause:** at 40+4 (depth 3-7, ~7k nodes/move) every pruning switch
  removes tactically load-bearing work; the safe-mobility eval tweak is real
  but only ~+16.
- **Can it fail again?** The specific switches: yes. Lesson: at bullet,
  aggressive pruning is net-negative; ordering tweaks are noise.
- **Decision:** rejected; dev5 cycle closed with gate FAILED (`ef980a0`).

## exp-0004 — FullSoftBudget time-management switch

- **ID / date / source:** exp-0004, 2026-11-02, `7969f8b`+ (committed in
  `ef980a0`); binary dev5 `be234145...`, default off, bench unchanged.
- **Hypothesis:** using the whole soft budget (~4 ms) instead of stopping at
  55-70% (stable/clock early stops) gains nodes at 40+4.
- **Results:** clean 40+4 with params_outcome: −21.0 [−44.4,+2.1] vs +9.4
  without. Harness clock model (`scripts/tournament.py:322-376`): clock =
  40 ms start, −elapsed, +4/move, forfeit at <0 -> steady-state budget is the
  4 ms increment; spending exactly 4 ms/move leaves zero slack, and sandbox
  stalls (observed 12-99 ms moves) cause TIME_FORFEITs (scored as losses).
- **Classification:** strength regression (forfeit-driven) + invalid lever.
- **Root cause (confirmed):** equilibrium usage is capped by the increment;
  extra per-move time only shrinks the safety buffer. More time per move is
  NOT available at 40+4.
- **Can it fail again?** Yes; any "use more of the clock" variant at 40+4
  fails the same way. Avoid. Alternative: NPS (exp-0010) only.
- **Decision:** rejected under tested conditions; kept as default-off switch.

## exp-0005 — Outcome-label Texel tuning, 479k corpus (params_outcome, dev5)

- **ID / date / source:** exp-0005, 2026-11-02, dev5; artifacts
  `benchmarks/results/0.1.0-dev5/screen-n*-params-outcome.*`.
- **Results:** fixed-node n3000 +35.0 [+12.0,+58.3], n960 +25.1, n8000 +60.7,
  n20000 +29.9; but clean 40+4 only +9.4 [−13.9,+32.9]. Fixed-node gains do
  NOT transfer to fixed-time bullet (time-management early stops + per-move
  overhead dilute them).
- **Classification:** inconclusive-to-positive but below gate; measurement
  lesson.
- **Root cause:** at fixed time the engine spends ~2.7-4 ms/move regardless;
  fixed-node screens measure a different regime. (Confirmed by dev6/dev7.)
- **Can it fail again?** As a *screening signal* it is unreliable at bullet;
  40+4 screens are the only trustworthy filter. Outcome tuning itself is
  worth keeping (+9..+48 depending on corpus, see exp-0012/0016).
- **Decision:** reusable with modifications (bigger bullet-matched corpus,
  exp-0012).

## exp-0006 — dev6 search-knob variants (SB_* compile-time knobs)

- **ID / date / source:** exp-0006, 2026-11-02..03, commit `1dc4a3c` (knobs),
  variant builds `vbuild-{nullr2,nullr4,lmr0,fut80,delta350,bank,nullr1,nullr0,fut60,nr2f80}`.
- **Hypothesis:** dev4's pruning constants (nullmove R=3, futility 110,
  rev-futility 85, LMR base 1, delta 200) are not optimal at 40+4.
- **Results:** n3000 240 g screens misleading (nullr2 +33.4 [+5.6,+61.6]);
  n8000 nullr2 −22.6 [−45.8,+0.5]; clean 40+4 nullr2 **−2.2 [−25.3,+21.0]**
  (seed 20261261). All other knobs ≈ 0 at 40+4.
- **Classification:** neutral at the decisive time control; n3000 screen
  invalid for pruning changes.
- **Root cause (confirmed):** dev4's pruning is already near the bullet
  optimum; fixed-node screens overvalue node-count reduction.
- **Can it fail again?** Yes — do not trust n3000 for pruning knobs. Decide
  at n8000 + clean 40+4 only.
- **Decision:** rejected under tested conditions (knobs kept in source as
  compile-time research hooks, defaults = dev4 values).

## exp-0007 — qsearch lite eval (SB_QEVAL_LITE)

- **ID / date / source:** exp-0007, 2026-11-03, `1dc4a3c` hooks; build
  `vbuild-qliteseec`.
- **Hypothesis:** qsearch is ~90% of nodes; skipping mobility+king-danger in
  qsearch stand-pat would give +23% NPS (measured) -> more depth at 40+4.
- **Results:** nps d16 2.44-2.49M vs 1.97-2.19M (+23%), but clean 40+4
  **−32.1 [−55.8,−8.6]** (seed 20261281).
- **Classification:** strength regression.
- **Root cause (confirmed):** stand-pat eval quality (king danger, mobility)
  is tactically critical even in qsearch; NPS gain (+~26 Elo by the
  half-clock slope) < eval loss (~58 Elo).
- **Can it fail again?** Yes — any qsearch eval simplification. Avoid.
  Alternative: keep full eval, cut its cost bit-exactly (exp-0013).
- **Decision:** rejected under tested conditions (hook kept, default off).

## exp-0008 — PGO build (-fprofile-generate/-use) and -mtune=native

- **ID / date / source:** exp-0008, 2026-11-03, `vbuild-pgogen`/`vbuild-pgo`
  (not committed; command in `docs/DEV6_RESEARCH.md`).
- **Hypothesis:** profile-guided optimization would speed the hot search loops.
- **Implementation:** -fprofile-generate build trained on nps.sh depths
  8/12/16/20 + 48 selfplay games at 40+4, then -fprofile-use -mtune=native.
- **Results:** depth-16 nodes identical (19229509; semantics unchanged), nps
  1.92-2.19M vs dev4 1.94-2.15M — neutral within noise.
- **Classification:** neutral result (performance).
- **Root cause:** hot code is lookup/cache-miss bound (magic bitboards, 16 MB TT
  random probes), which PGO cannot fix.
- **Can it fail again?** Likely neutral again on this code. Avoid unless the
  hot loop becomes compute-bound.
- **Decision:** rejected (neutral); not carried into candidates.

## exp-0009 — TT layout micro-opts (32B entries / pow2 mask / THP madvise)

- **ID / date / source:** exp-0009, 2026-11-02..03; builds `vbuild-ttpow2`
  (pow2 mask: nps −5%, reverted), `vbuild-tt32` (32B entry/64B bucket; bench
  identical but bucket count changes -> depth-16 nodes 19.2M->27.2M, nps
  neutral; reverted in `27ba7d4`), THP MADV_HUGEPAGE on the TT allocation
  (`vbuild-thp`, in tree at `fd3b5e1`, nps neutral).
- **Classification:** neutral result (performance).
- **Root cause:** TT probe cost is dominated by DRAM/L3 cache misses on a 16 MB
  randomly-probed table; entry packing and huge pages do not change miss cost.
- **Can it fail again?** Probably neutral again. Avoid further TT-layout
  micro-tuning at hash 16.
- **Decision:** rejected (neutral); THP hint kept (harmless, bench-identical).

## exp-0010 — ISA flags -mpopcnt -mbmi2 -mlzcnt (POSITIVE, recorded for completeness)

- **ID / date / source:** exp-0010, 2026-11-03, champion builds; finding in
  `docs/DEV6_RESEARCH.md`.
- **Finding:** Release used plain -O3, so every popcount was a
  `call __popcountdi2` (57 call sites, objdump-verified). Adding
  `-mpopcnt -mbmi2 -mlzcnt` makes it one instruction: **+12-20% NPS,
  bit-exact** (bench `243f9a1c1ba5b36f`, depth-16 nodes 19229509, ctest 11/11).
  Clean 40+4 screen: +3.6 [−19.6,+26.9] alone — small NPS gains move bullet
  Elo only weakly, but it is free and kept in the champion.
- **Classification:** positive (kept). Note for the record: not a failure.

## exp-0011 — Option-flip screens at 40+4 (disable pruning/extensions for NPS)

- **ID / date / source:** exp-0011, 2026-11-03, `benchmarks/results/0.1.0-dev6/clean-time40p4-opt-*.jsonl`
  (seeds 20261290-95), binary dev5 `be234145...`.
- **Results (clean 40+4, 480 g each):** NullMove=false −28.4 [−52.0,−5.1];
  LMR=false −68.9 [−92.1,−46.4]; Aspiration=false −83.4 [−107.6,−59.9];
  CheckExtension=false −31.5 [−55.2,−8.1]; IIR=false 0.0 [−23.3,+23.3];
  SEEPruning=false −71.8 [−97.1,−47.2].
- **Classification:** strength regression (all except IIR neutral).
- **Root cause (confirmed):** at depth 3-7 every pruning/extension is
  tactically load-bearing; "fewer nodes of work" is not "more strength".
  Raw node count is not the objective — useful depth is.
- **Can it fail again?** Yes. Avoid disabling any of these at 40+4.
- **Decision:** rejected under tested conditions.

## exp-0012 — Outcome retune on 885k-position corpus (params_outcome_v2..v6) + bullet corpus (params_bullet_b1..b3, params_abc)

- **ID / date / source:** exp-0012, 2026-11-03, `research-data/params_*.txt`
  (committed), corpora SHA-256 in `docs/DEV6_RESEARCH.md` (corpusA f89be2ef...,
  corpusB 45bdf0d3..., corpusC 1a88e4dc... — corpora are large, gitignored
  locally, regenerable via `stockbear selfplay` / tournament.py + pgn_to_corpus.py).
- **Results:** tuner val ~0.503-0.515, test ~0.470-0.495. Clean 40+4 480 g
  screens (nps1 binary + TTEval): outv2 pooled +41.2 (5 seeds), abc +48.2 (2),
  bullet-b1 +32.4 (2), v6 +50.3 (2), abc_s095 +44.9 (3), v3 +10.2, v5 +21.0,
  b2 +22.7, b3 +19.6. Huge seed variance (±25 at 480 g): single screens are
  not selection-grade evidence.
- **Classification:** inconclusive per-set; the family is positive
  (confirmed +39.9..+47.5, see exp-0016/0017).
- **Root cause of variance:** opening-cluster variance at 480 g; param-set
  differences of ±10 Elo are within noise. More bullet-matched data helped
  the tuner's test metric (0.495 vs 0.470) but not reliably the play.
- **Can it fail again?** Best-of-N param selection on dev openings overfits;
  confirmed values regress toward the family mean (~+45). Avoid selecting
  on single 480 g screens. Next: tune on much larger bullet corpus and/or
  pin material values (search margins are cp-calibrated).
- **Decision:** kept as champion component (params_abc / params_outcome_v6);
  family plateau ~+45 true.

## exp-0013 — Incremental evaluation (SB_INCREMENTAL_EVAL)

- **ID / date / source:** exp-0013, 2026-11-03, `fd3b5e1`; default OFF.
- **Implementation:** raw per-param feature counts in StateInfo, maintained by
  make_move deltas (attackers_to on from/to/captured squares + explicit
  moved/captured pieces; cheap terms recomputed per move; castling/king-move
  fall back to full recompute); evaluate() applies active params to counts.
- **Correctness:** verified bit-exact — standalone evalcheck (500 random games
  x 100 plies x 7 seeds, counts vs full recompute after every move) OK; bench
  `243f9a1c1ba5b36f`; depth-16 nodes 19229509; ctest 11/11. Bugs found and
  fixed during development: cheap-range zeroing clobbered mobility ids;
  `s == them` never-true condition; king falling into KD-Queen default.
- **Results (performance):** NPS 1.74-1.84M vs 2.49-2.55M for the
  non-incremental build — **−27% NPS**. The per-move delta work (3-6
  attackers_to reverse-magic lookups + cheap-term recompute, x2 sides) costs
  more than the saved features() calls (~60 lookups/node).
- **Classification:** performance regression (correctness OK).
- **Root cause (confirmed):** eval cost at 40+4 is dominated by irreducible
  attack-lookups; the delta bookkeeping adds lookups instead of removing them.
- **Failure conditions:** any per-move occupancy-delta scheme on this feature
  set. A different implementation (e.g., full recompute cached per position
  hash, or feature set without occupancy-dependent terms) could differ, but
  occupancy-dependent terms are exactly the expensive ones.
- **Can it fail again?** This implementation: yes, reliably. Keep gated off.
- **Decision:** rejected under tested conditions (default off; code kept for
  reference).

## exp-0014 — dev6 switch ablations on champion params (HistoryMaluses etc.)

- **ID / date / source:** exp-0014, 2026-11-03, `benchmarks/results/0.1.0-dev7/clean-time40p4-v6-*.jsonl`
  (seeds 20261420-27, 20261430), binary = champion build.
- **Results (480 g, v6+tteval baseline pooled +50.3):** HistoryMaluses=false
  +54.0/+57.2 (pooled +55.6 — but see exp-0017: confirmed LOWER); LMRHistory-off
  +47.7; CaptureHistory-off +35.7; ContinuationHistory-off +32.8;
  CounterMoves-off +31.3; ReverseFutility-off +28.4; Improving-off +27.7;
  Futility-off −2.2.
- **Classification:** neutral (all within ±25 screen noise of baseline).
- **Root cause:** default-on is at least as good at 40+4; screen noise ±25.
- **Decision:** defaults kept; HistoryMaluses=false was carried into the dev7
  candidate on the strength of 2 screens and then confirmed lower (selection
  noise) — lesson recorded.

## exp-0015 — Half-clock / 2x-clock wrap diagnostics (valid lever identification)

- **ID / date / source:** exp-0015, 2026-11-02..03, `research-data/clockwrap.py`,
  `wrap05.sh`, `wrap2x.sh`; artifacts `benchmarks/results/0.1.0-dev6/clean-time40p4-{halfclock,2xclock}.*`.
- **Results:** dev4 vs dev4-seeing-half-clock (clean 40+4, 479 g, seed
  20261271): **+89.9 [+65.9,+114.7] clustered, SPRT LLR 3.22 accept H1** —
  2x nodes ≈ +90 Elo at 40+4. 2x-clock direction INVALID (harness drains the
  real 40 ms clock; 9 forfeits all A losses; −43.8 was forfeits, not strength).
- **Classification:** diagnostic (not a failure); established NPS/nodes as
  the dominant lever at 40+4 and the harness clock model.
- **Decision:** kept as methodology evidence; only wrap factors < 1.0 are
  valid probes.

## exp-0016 — dev6 pre-registered confirmation (champion: popcnt+SEE-cache build + params_abc + TTEval)

- **ID / date / source:** exp-0016, 2026-11-03, pre-registered in `2d571ce`;
  suite `openings_dev6_confirmation.txt` SHA `99682ada...` (seed 2026110206,
  2200 pairs, untouched); candidate binary `build-dev6` SHA `15f1daa0...`
  (bench `243f9a1c1ba5b36f`, d16 nodes 19229509, ctest 11/11); baseline
  `1c5b61a7...`.
- **Conditions:** 4400 g, 40+4, hash 16, threads 1, max-plies 240, seed
  2026110207, run alone. Null (same binary both sides, 1100 g, seed
  2026110208): −3.5 [−17.3,+10.2], 4 unadjudicated, no forfeits.
- **Results:** **+47.5 [+39.5,+55.6]** clustered (paired +47.5 [+39.6,+55.5],
  SPRT LLR 14.07 accept H1); 4389 adjudicated, 11 unadjudicated, W+D+L
  1854+1276+1259, 3 TIME_FORFEIT (baseline-side stall moves 12.7/19.5/28.6 ms).
  Raw: `benchmarks/results/0.1.0-dev6/confirm-{null,champ}-time40_4.*`.
- **Classification:** gate failure (LCB +39.5 ≤ +50). Not a strength
  regression — the candidate is genuinely ~+47.
- **Root cause of gate miss:** true point ~+47.5 vs required ~+54+ at 4400 g.
- **Decision:** gate NOT met, no PR; evidence committed (`c4da1f8`).

## exp-0017 — dev7 pre-registered confirmation (champion: same build + params_outcome_v6 + TTEval + HistoryMaluses=false)

- **ID / date / source:** exp-0017, 2026-11-03, pre-registered in `25fd70a`;
  suite `openings_dev7_confirmation.txt` SHA `98208a6e...` (seed 2026110307,
  2200 pairs, excludes dev4/dev5/dev6 suites); candidate binary SHA
  `15f1daa0...` (byte-identical backup used because the wiper deleted `build*/`
  mid-run; sha verified in results).
- **Conditions:** 4400 g, 40+4, hash 16, threads 1, seed 2026110309, alone.
  Null 1100 g seed 2026110308: −4.1 [−18.2,+9.9], 3 unadjudicated.
- **Results:** **+39.9 [+31.9,+47.9]** clustered (paired +39.9 [+31.9,+47.8],
  SPRT LLR 11.65); 4376 adjudicated, 24 unadjudicated, 1 TIME_FORFEIT
  (baseline side, 20.8 ms). Raw: `benchmarks/results/0.1.0-dev7/confirm-*`.
- **Classification:** gate failure (LCB +31.9 ≤ +50). Note: the +55.6 screen
  pooled value for this param set was selection noise — confirmed value
  regressed to +39.9, below dev6's abc (+47.5).
- **Root cause:** champion family plateaus at +40..+48 true point at 40+4;
  param-set selection on dev screens does not transfer.
- **Decision:** gate NOT met, no PR; evidence committed (`b8e7fd2`, `fd3b5e1`).

## exp-0018 — Sandbox wipe / reset incidents (infrastructure)

- **ID / date:** exp-0018, 2026-11-02 ~13:30 UTC and 2026-11-03 ~03:00-05:00
  UTC (multiple partial and full resets).
- **What happened:** gitignored/excluded dirs (`build*/`, `.venv/`, `data/`,
  `/tmp`) and untracked files (research corpora, `/home/user/bin-backup/`)
  were wiped; at least once the local branch was reset to `7969f8b`.
- **Recovery (confirmed working):** all work was pushed, so
  `git reset --hard origin/arena/daa69a3b-stockbear` restored it; `.venv`
  recreated via `pip install cmake ninja chess numpy`; `git fetch --unshallow
  origin && git fetch origin --tags`; dev4 baseline rebuilt from tag
  `v0.1.0-dev4` in a worktree -> SHA `1c5b61a7...` bit-identical, bench
  `243f9a1c1ba5b36f`; champion rebuilt with the pinned command -> bench
  identical. Committed recovery script: `scripts/recover_env.sh`.
- **Classification:** infrastructure failure (recovered).
- **Lessons:** only git-committed files are wipe-safe; binaries are
  reproducible from git + recorded commands, which is the verified backup.
  Decisive matches must be re-runnable; decisive matches run with zero other
  CPU work (concurrent-CPU noise measured ±25-30 Elo).

---

## Standing lessons (summary)

1. At 40+4 the harness clock caps sustainable usage at the 4 ms increment;
   more nodes must come from NPS, and only bit-exact NPS counts (qlite
   proved eval quality in qsearch dominates).
2. All dev4 pruning/extensions/ordering switches are load-bearing at depth
   3-7 (disabling any regressed 2-83 Elo). Do not re-screen "off" variants.
3. Fixed-node screens (n3000) are misleading for pruning/params; decide at
   n8000 + clean 40+4; even 480 g 40+4 screens have ±25 Elo noise — never
   select on one screen.
4. Eval outcome-tuning family plateaus at ~+40..+48 true at 40+4
   (confirmed twice on untouched suites). Needed for the gate: ~+54 point.
5. NPS micro-levers tried: popcnt/bmi2/lzcnt (+12-20% NPS, kept, but only
   ~+4-14 Elo at 40+4), PGO/THP/TT-packing/SEE-dedup (neutral),
   incremental eval (−27% NPS, rejected).
6. NNUE under sandbox compute limits is far weaker AND 4x slower — rejected.
7. Next highest-EV directions (see research backlog in docs/DEV6_RESEARCH.md):
   margin recalibration for the retuned eval scale, larger bullet-matched
   tuning corpora, aspiration-window tuning, and any genuinely new eval
   features — each must be screened at clean 40+4 and confirmed on a fresh
   pre-registered untouched suite.

## exp-0019 — margin / aspiration-window UCI options + runner screens

- **ID / date / source:** exp-0019, 2026-11-03, commit `582e4b1` (options +
  Actions pipeline); first runner batch failed on a lost setoption handler
  edit (`unknown option AspirationWindow`), fixed and re-verified (bench
  `243f9a1c1ba5b36f`, setoption accepted) before the decisive batch.
- **Implementation:** `AspirationWindow`, `FutilityMargin`, `RevFutilityMargin`,
  `DeltaMargin` UCI spin options (defaults 16/110/85/200 = dev4 values, so the
  default build is bit-identical). Eval-scale diagnostic behind the hypothesis:
  tuned params widen the eval distribution ~7-9 % (2159 self-play positions:
  |mean| 454-462 cp, std 707-719 vs 424/661 for defaults), so cp margins are
  relatively ~8 % tight.
- **Runner lane results (GitHub-hosted ubuntu-latest, AMD EPYC 7763, 4 vCPU,
  dedicated VM, 480 g @ 40+4 hash16 threads1, openings_dev4.txt):**
  exp0019-base (champion params_abc+TTEval, plain flags) **+44.0
  [+20.5,+67.9]** clustered; null **+7.3 [-9.2,+23.7]** (includes 0). Variant
  screens re-run in the exp-0023 batch (see benchmarks/exp-runs/exp0019-*).
- **Classification:** pending (screens running); base confirms the champion
  family at ~+44-48 on a second hardware lane.

## exp-0020 — bigger bullet-matched tuning corpus (in progress)

- **ID / date / source:** exp-0020, 2026-11-03; 6000-game self-play corpus at
  ~4.5k nodes/move (jittered 80-120 %, approximating the ~7k nodes/move
  measured at 40+4), seed 20261104001, generated with build-dev6.
- **Plan:** evaldata features + `tune_eval2.py --target outcome` on the fresh
  corpus (more restarts/epochs), then a runner screen vs dev4. Corpus and
  tuner outputs are kept under /tmp + research-data (corpora are large and
  gitignored; hashes recorded in the run notes).

## exp-0021 — `-march=native -flto` candidate build (POSITIVE, big)

- **ID / date / source:** exp-0021, 2026-11-03; runner job `exp0021-native-*`
  with `build_flags="-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -march=native
  -flto=4"`.
- **Correctness:** bench `243f9a1c1ba5b36f` and bench --depth 16
  `a14ab62224f837e5` asserted at runtime on the runner; locally the same
  flags gave identical startpos d16 nodes; integer-only code, so vectorised
  codegen is bit-exact. Sandbox NPS under load: 1.55-1.96M vs 1.35-1.43M for
  the plain build (~+15-35 %).
- **Result (runner lane, 480 g @ 40+4):** **+71.4 [+47.6,+95.8]** clustered
  vs pinned dev4, with champion params_abc+TTEval; null -10.2 [-27.0,+6.6].
  vs the plain-flags base (+44.0 [+20.5,+67.9]) on the same lane — ~+27 Elo
  from NPS alone, consistent with the measured 2x-nodes ~ +90 Elo slope.
- **Classification:** positive (kept). Carried into the exp-0023 decisive
  confirmation candidate.

## exp-0022 — new eval features with zero defaults (in progress)

- **ID / date / source:** exp-0022, 2026-11-03, working tree at the exp-0023
  push: appended `RookOn7th`, `KnightOutpost`, `BackwardPawn`, `PawnChain`
  (enum + table rows with shipped value 0, range [-100,200]; counts added to
  both `features()` and `accumulate_breakdown()`; dev3-shipped.txt extended;
  checksum test updated to `0x79473f95496c545e`).
- **Correctness:** bench `243f9a1c1ba5b36f` (defaults are 0 -> bit-identical),
  ctest 11/11, `evaldata --check` 0 mismatches on 2159 positions.
- **Plan:** tune them on the exp-0020 corpus (they stay 0 for the frozen
  exp-0023 candidate because params_abc.txt does not mention them), then
  screen any non-zero set on the runner lane.
- **Caveat recorded:** the default-off SB_INCREMENTAL_EVAL path does not
  maintain the new ids.

## exp-0023 — decisive confirmation — GATE PASSED

- **Pre-registration:** docs/EXP0023_PREREG.md (committed as `737c6f4` before
  the run). 12 shards x 550 = 6600 g + 1100 g null on the fresh untouched
  suite `openings_exp0001_confirmation.txt` (sha `32537dd8...`, seed
  2026110501, excludes all prior suites), candidate = `737c6f4` built with
  `-march=native -flto=4` + params_abc + TTEval, baseline = pinned dev4
  binary `1c5b61a7...`, 40+4, hash 16, threads 1, seeds 2026110601..612 +
  null 2026110699, GitHub-hosted ubuntu-latest runners (dedicated VM,
  AMD EPYC 7763/9V45).
- **Results (2026-11-03, run 41610113495):** clustered CR1 t(1774):
  **+66.4 [+59.3, +73.6]** — **LCB95 = +59.3 > +50, GATE MET**.
  W+D+L 2949/1928/1704, 18 unadjudicated, 0 forfeits; null (1100 g)
  −1.3 [−11.7,+9.2]. SPRT LLR 30.74 accept H1. Raw:
  `benchmarks/exp-runs/exp0023-shard01..12/` + `exp0023-null/`, pooled in
  `benchmarks/exp-runs/exp0023-pooled.json/.txt`; full write-up
  `docs/EXP0023_CONFIRMATION.md`.
- **Classification:** SUCCESS (gate met). Screens leading here: exp0019-base
  +44.0 [+20.5,+67.9]; exp0021-native +71.4 [+47.6,+95.8]; exp0020-native
  (fresh-corpus retune) +80.2 [+55.4,+105.9] (promising, unconfirmed);
  margin/aspiration variants within noise of their bases (rfut110 mildly
  positive, not in the frozen candidate).
- **Runner infra note:** jobs push results back to the branch because the
  sandbox cannot download Actions logs/artifacts; a `FATAL ... exited 1`
  FAIL.txt on a job WITH a complete match.report.txt is a benign engine
  cleanup exception after the summary (results complete).
