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

## exp-0024 — release-artifact gate: GATE PASSED (2026-11-03, run 41620641753)

- **Question:** does the PORTABLE release artifact build (champion flags
  WITHOUT `-march=native`: `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`,
  x86-64-v3) clear the mandatory +50 gate vs the pinned dev4 binary?
- **Pre-registration:** docs/EXP0024_PREREG.md (committed as `511a756` before
  the run). 12 shards x 550 = 6600 g + 1100 g null on the fresh untouched
  suite `openings_exp0002_confirmation.txt` (sha `90e99b37...`, seed
  2026110502, excludes all prior suites incl. exp0001), candidate = `511a756`
  portable build + params_abc + TTEval, baseline = pinned dev4 `1c5b61a7...`,
  40+4, hash 16, threads 1, seeds 2026110701..712 + null 2026110799,
  GitHub-hosted ubuntu-latest dedicated VMs.
- **Results:** clustered CR1 t(1745): **+64.7 [+57.5, +72.0]** —
  **LCB95 = +57.5 > +50, GATE MET**. W+D+L 2907/1986/1692, 15 unadjudicated
  (game-level = pair-level here), 1 TIME_FORFEIT by the dev4 baseline (8.2 ms
  move; scored as its loss per the symmetric policy, counted not hidden);
  6585 adjudicated + 15 = 6600. Null (1100 g) +1.3 [−8.0, +10.6]. SPRT LLR
  28.96 accept H1. Raw: `benchmarks/exp-runs/exp0024-shard01..12/` +
  `exp0024-null/`; pooled `exp0024-pooled.json/.txt`; write-up
  `docs/EXP0024_CONFIRMATION.md`; independent audit `exp0024-audit.json`
  (scripts/audit_exp0023.py --exp exp0024, zero problems, matches pooled to
  full precision).
- **Classification:** SUCCESS (gate met on the exact shipped configuration).
  exp-0023 (+66.4 [+59.3,+73.6], native build) remains the native-runner
  measurement of the same source; the release claims the exp-0024 number for
  the portable artifact.

---

# v0.1.0-dev6 cycle (2026-11-03) — baseline = EXACT RELEASED dev5

## Cycle framing and correction (read before using older entries)

All entries above from the **dev5 development cycle** (branch
`arena/daa69a3b-stockbear`, exp-0001..exp-0024) used the immutable **dev4**
binary `1c5b61a7…` as baseline. exp-0016/exp-0017 were labelled "dev6"/"dev7"
in that historical cycle but are internal experiments against dev4 with a +50
gate; their results (+47.5/+39.9, LCB below +50) are preserved as history.
**They are NOT the v0.1.0-dev6 mission and cannot satisfy its gate.** The
current cycle (branch `arena/3e6dd5b6-stockbear`, VERSION `0.1.0-dev6`) has a
harder objective: >= +75 Elo with a two-sided opening-clustered 95% CI lower
bound strictly > +50, in two disjoint pre-registered confirmation batches,
against the **exact released v0.1.0-dev5 portable artifact**
(SHA-256 `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`) at
champion options. dev5 already measured +64.7 [+57.5,+72.0] vs dev4 (exp-0024).
Older dev4-baseline "dev6/dev7" confirmations are hereby classified
**INVALID MEASUREMENT for the dev6 gate** (wrong baseline, wrong gate, different
branch/cycle), not erased. Superseding notices appended to
`docs/DEV5_REPORT.md`, `DEV6_RESEARCH.md`, `DEV6_CONFIRMATION.md`,
`DEV7_CONFIRMATION.md`. Active constraints: the entire ledger above (no repeat
of negative directions: small CPU NNUE, cp distillation, FullSoftBudget,
qsearch-lite, PGO/TT/THP micro-opts, incremental eval, disabling dev4
pruning/ordering, best-of-N param selection, fixed-node-only conclusions).

---

## exp-0025 — dev6 baseline provenance (verification, not a strength experiment)

- **ID / source / binary SHAs:** release tag `v0.1.0-dev5` -> commit
  `c94571313a1667048468cf6d4e070400dc5ab228`; `SHA256SUMS.txt` asset SHA
  `8022866bc945145c6c80c437f20f83a534090cadbb3c8aea6334cffda3cd4773`; extracted
  executable SHA `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`;
  shipped == repo `params_abc.txt` SHA
  `8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be`.
- **Hypothesis / test:** the exact released dev5 portable artifact is resolved,
  downloaded from the official release, checksum-verified, extracted, and pinned
  as the immutable baseline (no approximate rebuild). Bench `243f9a1c1ba5b36f`,
  d16 `a14ab62224f837e5`, UCI `0.1.0-dev5`, flags
  `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`.
- **Config / conditions:** free GitHub-hosted ubuntu-latest dedicated VM
  (`dev6-lane.yml` verify-baseline job); both Linux/Windows archives verified
  against the published `SHA256SUMS.txt`; sandbox could NOT reach the CDN
  directly (infrastructure note, exp-0025 prereg).
- **Raw paths:** `benchmarks/exp-runs/exp0025-baseline/` (assets, extract,
  archive listing, checksums); `benchmarks/binaries/stockbear-dev5-release`;
  `benchmarks/dev6-baseline/manifest.json`, `PROVENANCE.md`, `SHA256SUMS.txt`,
  `params_abc_shipped.txt`.
- **Statistics:** n/a (integrity verification; signatures and SHA-256 exact).
- **Decision / classification:** SUCCESS (baseline pinned and immutable).
- **Root cause / recurrence:** the sandbox's outbound allowlist excludes
  `release-assets.githubusercontent.com`; use the free runner for official
  asset acquisition. Audit: `docs/DEV6_PREREG_BASELINE.md`, runner run
  `41635295602` (success).

## exp-0026 — six extended pawn/coordination evaluation features (correctness)

- **ID / source / binary SHAs:** branch `arena/3e6dd5b6-stockbear`; source
  changes in `src/evaluation/eval_params.{hpp,cpp}`,
  `src/evaluation/evaluation.cpp`, `tests/unit/test_eval_baseline.cpp`,
  `benchmarks/params/dev3-shipped.txt`; candidate params
  `research-data/params_dev6_a.txt` SHA
  `e94c05628968474eaa52153a29904361604d34dacb240dfe5c20d4ba040338bd`. Source
  commit `4cd9894…` (engine tree; dispatch tree `28a5c71…`). New default
  eval checksum `0x5d90d35fb2203bde` (was `0x79473f95496c545e`).
- **Hypothesis / chess rationale:** two shipped rows (`BackwardPawn`,
  `PawnChain`) were dead (never counted); two new endgame-relevant features
  (`ConnectedPassed`, `RookBehindPassed`) plus the four existing ones, correctly
  implemented and gated, may add small positional/endgame strength on top of the
  dev5 champion. Falsifier: pre-registered clustered 95% CI point < +75 or
  LCB <= +50. Full rationale: `docs/DEV6_EVAL_FEATURES.md`.
- **Config / conditions:** all six appended (append-only, shipped 0); single
  shared `extended_counts()` used by `features()`, `accumulate_breakdown()` and
  the incremental path; gated so default/champion build is bit-exact and pays
  zero cost. Correctness: ctest 11/11 (41 unit tests), new gating/count unit
  test, `evaldata --check` 600/600, default bench bit-exact, exact `-flto=4`
  portable build reproduces both signatures, UCI `0.1.0-dev6`.
- **Raw paths:** `benchmarks/positions/dev6_eval_features.epd` (600 FENs, seed
  2026110401), `benchmarks/dev6-baseline/eval_features_reference.json`
  (600 positions, 43,200 feature checks, **0 mismatches**), independent oracle
  `scripts/check_dev6_eval_features.py`.
- **Statistics:** correctness counts (all six features exercised); **no playing-
  strength claim from correctness.** Cost measured: ~13% of the combined
  breakdown+evaluate loop when enabled (~0.69 µs/eval), zero when gated off.
- **Decision / classification:** SUCCESS (implementation + independent
  verification). Strength verdict is measured separately in exp-0028/0029, NOT
  assumed here.
- **Root cause / recurrence / audits:** dead rows would silently make any tuning
  of them meaningless; recurrence condition = any new eval row must be counted
  in ALL of `features`/`accumulate_breakdown`/incremental and verified by an
  independent oracle before tuning. Audit: independent python-chess reference
  shares no code with the engine; mirror test with all six coefficients non-zero.
  Continue to fixed-time testing only if a genuine strength hypothesis remains;
  do not tune dead rows again.

---

## exp-0027 — screens on `openings_dev4.txt` (diagnostic, never gate evidence)

- **ID / source / binary SHAs:** pre-registered `docs/DEV6_PREREG.md`; dispatch
  commit `28a5c719721e809759bdb3cf22436e8034cdabbd`; runner candidate binary SHA
  `4b06b1176ad331073430d4350bd7f5e1c9fa2e031f5ee6fe7e88954443730c15`
  (built ubuntu-latest / GCC 13 / glibc 2.39, portable
  `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`, bench `243f9a1c1ba5b36f`);
  baseline = exact released dev5 `391cb50e…` at champion (`params_abc.txt` SHA
  `8a9dc81f…` + `TTEval=true`). Suite `openings_dev4.txt` SHA
  `3feeac711c8eded5a26b84f57e4bf9190b12634558a7a8e5e9a6d34bfcc5250d`.
- **Hypotheses / config / conditions:** (i) primary = candidate `params_dev6_a`
  (SHA `e94c0562…`) vs dev5, 2000 g, seed 2026120101; (ii) integrity control =
  candidate `params_abc` vs dev5 (identical config both sides), 1100 g, seed
  2026120102; (iii) historical reuse = `params_exp0020` (SHA `2a7f103c…`) vs
  dev5, 1100 g, seed 2026120103. All 40+4 ms, hash 16, 1 thread, dedicated
  ubuntu-latest VM.
- **Raw paths:** `benchmarks/exp-runs/exp0027-screen|control|exp0020/`
  (PGN + JSONL + CSV + manifest + report); recomputation
  `benchmarks/dev6-baseline/confirmation_results.json`,
  `scripts/dev6_confirmation_report.py`.
- **Statistics (clustered CR1 / t, ~240 clusters):** primary **−25.0
  [−42.9, −7.3]** (REGRESSION); control **+33.0 [+13.7, +52.5]** (unexpected,
  see below); exp0020 **−12.1 [−33.7, +9.4]** (CI includes 0, INCONCLUSIVE).
  1100/2000 g, W/D/L and pentanomial/termination counts in the confirmation
  report; 6/3/3 unadjudicated max-ply; 0 forfeits, 0 illegal moves, 0 crashes,
  0 UCI failures.
- **Decision / classification:** primary REGRESSION; exp0020 INCONCLUSIVE;
  control INCONCLUSIVE (INVALID MEASUREMENT as an integrity/equivalence check).
- **Root cause / recurrence / audits:** the control's +33 cannot be a config
  error (verified both engines got the identical params file + options from the
  raw `match.jsonl`). It is confounded by the **toolchain**: dev5 was built on
  ubuntu-22.04, the candidate on ubuntu-latest (Ubuntu 24.04 / GCC 13), which can
  change fixed-time NPS even with identical bench signatures; a 1100-game/240-
  cluster screen also has ~±19 Elo noise. My source changes are ruled out as the
  cause: on one machine, at identical `bench --depth 16` node counts, the local
  dev6 build is only 1.015x the released dev5 NPS (52.3 s vs 53.1 s). Nulls
  cannot detect a between-binary NPS difference (both null sides share one
  binary). **Confound-free ablation on the SAME suite/binary/baseline**: switching
  `params_abc` -> `params_dev6_a` costs ≈ **−58 Elo** (+33 -> −25). Required fix
  before any future approval: build both sides in ONE reproducible toolchain,
  verify binary-level NPS equivalence, re-run the control. Prereg ref: §1/§8;
  audit: `docs/DEV6_CONFIRMATION_REPORT.md` "Integrity investigation".
- **Continue / abandon / revisit:** ABANDON `params_exp0020` reuse (no gain);
  ABANDON the six-feature direction (see exp-0028/0029 + ablation); REVISIT the
  integrity control only with a matched-toolchain build.

## exp-0028 — decisive confirmation batch A (candidate vs EXACT dev5)

- **ID / source / binary SHAs:** prereg `docs/DEV6_PREREG.md`; dispatch `28a5c71…`;
  candidate binary `4b06b117…` + `params_dev6_a.txt` (`e94c0562…`) + `TTEval=true`;
  baseline `391cb50e…` + `params_abc.txt` (`8a9dc81f…`) + `TTEval=true`. Master
  suite `openings_exp0028_confirmation.txt` SHA
  `1d69972297f1a2a8f24d4040fb39f8d423f9d013abff6b7c3e266606e36d2c25` (3300
  distinct openings, 6 disjoint 550-opening slices; SHAs in
  `benchmarks/dev6-baseline/decisive_suites.json`). Candidate build flags
  portable `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`, bench
  `243f9a1c1ba5b36f`.
- **Hypothesis:** H1, the six extended features deliver >= +75 Elo with
  LCB95 > +50 vs exact dev5. Falsifier: point < +75 or LCB <= +50.
- **Config / conditions:** 6 shards x 1100 g = 6600 g, 40+4 ms, hash 16, 1
  thread, `--max-plies 240`, paired colour-reversed, one pair per distinct
  opening (NO repeats within batch), seeds 2026120201..0206, 6 dedicated
  ubuntu-latest VMs (AMD EPYC 7763, 4 vCPU), no concurrent CPU work. Null:
  `exp0028-null`, 1100 g candidate-vs-identical, seed 2026120299.
- **Raw paths:** `benchmarks/exp-runs/exp0028-shard01..06/` and
  `exp0028-null/` (PGN/JSONL/CSV/manifest/report per job); pooled recomputation
  `benchmarks/dev6-baseline/confirmation_results.json`.
- **Statistics:** 6600 g, +2090 =2071 −2418 (47.51%), clustered CR1
  **−17.8 Elo [−24.1, −11.5]**, 3279 clusters, t=1.980 on 3278 df, paired
  −17.8 [−24.1, −11.6], pentanomial [234,610,1358,740,337], SPRT (approx.) LLR
  −10.04; 21 unadjudicated max-ply; 0 forfeits / 0 illegal / 0 crashes / 0 UCI
  failures; 2 STALEMATE. Null **+0.6 [−9.5, +10.7]** (includes 0, PASS).
  Leave-one-shard-out points −14.1..−21.2 (stable).
- **Decision / classification:** **REGRESSION** (H1 falsified, batch negative).
- **Root cause / recurrence / audits:** small hand-set linear pawn/coordination
  priors on top of an already-tuned champion eval degrade fixed-time play;
  consistent with the ledger's lesson that validation-loss/prior reasoning does
  not transfer to playing strength. Recurrence condition: any eval term added
  without fixed-time evidence. Audit: independent recomputation from raw JSONL
  by `scripts/dev6_confirmation_report.py`; nulls clean; integrity confound
  documented (exp-0027 control). Continue/abandon: ABANDON this feature set.

## exp-0029 — decisive confirmation batch B (independent, disjoint suite)

- **ID / source / binary SHAs:** identical candidate/baseline/build to exp-0028
  (candidate `4b06b117…` + `params_dev6_a.txt` `e94c0562…`; dev5 `391cb50e…` +
  `params_abc.txt` `8a9dc81f…`), but a **disjoint fresh** master suite
  `openings_exp0029_confirmation.txt` SHA
  `c491a9e5182bd41748a638bd7d987225b6a233e18e8e91ac2758053350f17b3e` (3300
  distinct openings, verified disjoint from batch A and ALL historical suites).
- **Hypothesis / config / conditions:** same H1; 6 shards x 1100 g = 6600 g,
  seeds 2026120301..0306, null `exp0029-null` 1100 g seed 2026120399; all other
  conditions identical to exp-0028.
- **Raw paths:** `benchmarks/exp-runs/exp0029-shard01..06/`, `exp0029-null/`.
- **Statistics:** 6600 g, +2049 =2185 −2356 (47.67%), clustered CR1
  **−16.2 Elo [−22.4, −10.0]**, 3290 clusters, paired −16.2 [−22.3, −10.0],
  SPRT (approx.) LLR −9.56; 10 unadjudicated max-ply; 0 adversarial engine
  events; 3 STALEMATE. Null **−2.5 [−12.8, +7.7]** (includes 0, PASS).
- **Decision / classification:** **REGRESSION** (independent replication of
  exp-0028; both batches negative and reasonably consistent −17.8 / −16.2).

## COMBINED decisive verdict (the dev6 gate)

- **Statistics:** 13200 games, +4139 =4256 −4774 (47.59%), pooled opening-
  clustered CR1 **−17.0 Elo, 95% CI [−21.4, −12.6]**, 6569 clusters, t=1.980
  on 6568 df; paired pentanomial −17.0 [−21.4, −12.6]; cluster bootstrap
  (2000 reps) [−21.4, −12.6]; SPRT (normal approximation) LLR −19.61; combined
  null −0.9 [−8.1, +6.2]. 31 unadjudicated max-ply, 0 forfeits / 0 illegal /
  0 crashes / 0 UCI failures / 5 STALEMATE. Power analysis
  (`docs/DEV6_POWER_ANALYSIS.md`) shows the design had ample power to detect
  +75; it instead decisively excludes it.
- **Gate results:** Gate 1 point >= +75 **FAIL** (−17.0); Gate 1 LCB > +50
  **FAIL** (−21.4); Gate 2 both batches positive **FAIL**; consistency **PASS**;
  Gate 3 nulls include 0 **PASS**; Gate 4 no unresolved engine-failure
  regression **PASS**; overall **FAIL / GATE NOT MET**.
- **Classification:** **REGRESSION** for the candidate; **INVALID MEASUREMENT**
  (confounded) for the integrity control; **SUCCESS** for the null controls and
  the measurement design; **INFRASTRUCTURE FAILURE** (cosmetic) for concurrent
  push-retry empty commits (all 17 result dirs verified intact; history not
  rewritten).
- **Root cause:** the six extended linear features are harmful at 40+4 ms
  (≈ −58 Elo isolated ablation; −17 Elo net vs dev5 across 13200 games).
  Recurrence conditions: do not re-tune or recombine this feature set without a
  genuinely new, pre-registered, correctness-verified hypothesis and matched
  toolchain; do not resurrect dead rows; do not claim strength from correctness.
- **Continue / abandon / revisit:** ABANDON this feature set and this param file.
  CONTINUE research on materially different hypotheses per
  `docs/DEV6_3000_ROADMAP.md` (M0 rating foundation first, then a genuinely
  stronger evaluator with a measured accuracy->strength link). REVISIT only the
  toolchain-integrity control with matched builds. No cherry-picking: all screens
  and both batches reported in full.
- **Authorization / audits:** NO PR, NO merge, NO `v0.1.0-dev6` tag, NO release,
  NO dev7, NO approval sought (all require explicit user authorization and a
  passing gate). CodeRabbit review on an exact final PR head: **SKIPPED / not
  applicable** — no PR is eligible while the gate is unmet; documented manual
  audit = `scripts/dev6_confirmation_report.py` independent recomputation,
  `scripts/check_dev6_eval_features.py` python-chess oracle, ctest 11/11, CI run
  `41638608619` (success) and lane run `41638608427` (success) on source head
  `28a5c71…`. Full report: `docs/DEV6_REPORT.md`.

---

## exp-0030 — reproducible build environment + Track A/B integrity (M0.1)

- **ID / prereg:** `docs/DEV6_PREREG_EXP0030.md` (committed before measurement;
  tolerances frozen a priori). Script `scripts/dev6_build_matrix.py`.
- **Hypothesis / rationale:** the previous `params_abc` control's +33.0
  [+13.7,+52.5] Elo was a build-image artifact (dev5 released from ubuntu-22.04,
  candidate built by the lane on ubuntu-latest/GCC 13). Gate 4 of
  `docs/DEV6_PREREG.md` requires "no unexplained difference between benchmarked
  and packaged binary", so no strength experiment may run until this is
  controlled. Rebuild BOTH source trees in ONE pinned toolchain and measure
  fixed-node and fixed-time performance.
- **Baseline / candidate identities:** A1 = `git archive v0.1.0-dev5` (commit
  `c945713…`, archive SHA `4107ff56…`), rebuilt; A2 = `git archive <HEAD>`
  (current dev6 source, extended features shipped 0), rebuilt; B = official
  immutable artifact `391cb50e…` (Track B, NEVER rebuilt/renamed). Executable
  SHAs: A1 `214cbed002e58fbc94d74a089491bba94634e9e8d06b782992548fdacaa9b501`,
  A2 `28b40cd691cc4c2b892aad27f42f4c62b50962e0d8183b9fdc339e1563d66538`,
  B `391cb50e…`. Full hashes in `benchmarks/dev6-baseline/build_matrix.json`.
- **Build environment (recorded):** Linux 6.1.158+ x86_64, glibc 2.36, Intel
  Xeon 2.60GHz (popcnt/bmi2/avx2/abm), 2 vCPU, 3.9 GB; GCC 12.2.0, GNU ld
  2.40, CMake 4.4.4, Ninja; `-DCMAKE_BUILD_TYPE=Release -G Ninja
  -DCMAKE_CXX_FLAGS="-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4"`,
  NO `-march=native`; hash 16, threads 1, `--max-plies 240`, champion
  `params_abc.txt` + `TTEval=true`. Builds sequential, no concurrent CPU work.
- **Commands / raw paths:** `scripts/dev6_build_matrix.py` (also
  `--finalize-only`); `benchmarks/exp-runs/exp0030-build-integrity/`
  (build.log + 9 full bench CSVs); `benchmarks/exp-runs/exp0030-control/`
  (400-game PGN/JSONL/CSV/pooled.json); `benchmarks/dev6-baseline/build_matrix.json`.
- **Statistics / results (pre-registered criteria):**
  - **E1 fixed-node signatures PASS**: all three binaries `bench`
    `243f9a1c1ba5b36f`, `bench --depth 16` `a14ab62224f837e5`,
    `bench --depth 12 --params params_abc` `e45fa2ec2287eb41`.
  - **E2 full fixed-node CSV PASS**: 12/12 bench rows byte-identical A1 vs A2
    (default and params_abc, timing columns excluded) — bit-exact search.
  - **E3 fixed-time NPS PASS**: A1 2.514M, A2 2.455M, B 2.490M; ratio A2/A1
    **0.9765** inside frozen tolerance [0.97,1.03]; B/A1 0.9906 (reference only).
  - **E4 fixed-time control PASS**: A2 vs A1, 400 paired games, fresh disjoint
    200-opening slice (SHA `f3f03dc9…`), clustered CR1 **−22.6 [−47.4,+2.0]
    Elo**, CI includes 0. 5 TIME_FORFEIT events (4 candidate, 1 dev5), 0
    illegal/crash/UCI failures. Point estimate negative and forfeits are
    consistent with documented LOCAL 2-vCPU fixed-time noise (±25 Elo); decisive
    matches must use isolated runners. Not used as strength evidence.
  - **E5 decision PASS** (E1+E2+E3+E4).
- **Classification:** SUCCESS (measurement-integrity foundation). The +33 Elo
  control is confirmed toolchain-induced: under a matched toolchain no large
  positive offset exists; candidate is 2.35% SLOWER (gating branch), so it can
  only be slightly weaker, never +33 stronger, at fixed time.
- **Root cause / recurrence / audits:** different compiler images produce NPS
  differences that masquerade as eval strength at 40+4 ms. Recurrence condition:
  any comparison between binaries built by different toolchains. REQUIRED FIX
  (now applied): Track A = both sides built in ONE pinned toolchain; Track B =
  official artifact measured separately and NEVER described as a rebuild.
  Audit: independent full bench-CSV differential, signature match, 3-run NPS,
  400-game control, all SHAs recorded. Do not use the shared local sandbox for
  decisive fixed-time matches (time forfeits); use isolated runners.
- **Continue / abandon / revisit:** CONTINUE to exp-0031 (M0.2 external ladder).
  Do NOT repeat the +33 control on mismatched toolchains. Next gate prerequisite
  satisfied: Track A is a valid controlled source-level comparison environment.

## exp-0031 — external ladder pilot (M0.2 anchor selection)

- **ID / class:** exp-0031, MEASUREMENT / anchor-selection pilot (not a strength
  gate test). Prereg `docs/DEV6_PREREG_EXP0031.md` §2, committed BEFORE results
  (`5415c87`).
- **Hypothesis:** a fixed-node, strength-limited multi-level opponent pool can
  produce >= 2 non-saturated ("informative", score in `[0.20,0.80]`) anchors
  bracketing the exact released dev5 without any external binary/network CDN.
- **Identities:** subject = immutable official dev5
  `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`,
  `EvalParams=research-data/params_abc.txt`, `TTEval=true`. Anchors = pinned
  `benchmarks/binaries/external/` SF8/SF9/SF10/SF11 (source/binary SHA-256 in
  `benchmarks/dev6-baseline/external_opponents.json`) and dev4
  `1c5b61a7…`; SF11 `Skill Level 0/4/8/12/16/20`.
- **Build/runtime env:** GCC 12.2.0, no `-march=native`, `-mpopcnt -mbmi2
  -mlzcnt -DSB_SEE_CACHE=1 -flto=4`; SF built `make -j2 build
  ARCH=x86-64-modern COMP=gcc`. Fixed-node `go nodes 6000` +/-15 %, hash 16,
  threads 1, max 240 plies, paired colour-reversed fresh openings; 40 games per
  anchor, 10 disjoint 20-opening slices. 4-game config smoke DISCARDED.
- **Commands / raw:** `scripts/dev6_ladder_pilot.py`, `scripts/tournament.py`,
  `scripts/match_stats.py`; `benchmarks/exp-runs/exp0031-pilot-*/`,
  `benchmarks/exp-runs/exp0031-smoke/` (DISCARDED),
  `benchmarks/dev6-baseline/ladder_pilot.json`.
- **Results:** SF11-L0 0.950, L4 0.762, L8 0.400, L12 0.275, L16 0.237, L20
  0.125, SF8 0.062, SF9 0.025, SF10 0.125, dev4 0.600. **5 informative
  anchors** (SF11-L4/L8/L12/L16, dev4), **0** time forfeits / illegal / UCI
  failures. Decision (frozen rule, >=2 informative): **PROCEED**.
- **Outcome / classification:** SUCCESS (pilot objective). Deviations disclosed
  in prereg §6.1 (match seeds `2026110710..0719` vs frozen
  `2026110701..0710`; clerical only).
- **Lessons / non-repeatable:** strength-limited SF11 skill levels DO bracket
  dev5 at fixed nodes; full-strength SF8/9/10 saturate. Do not retry blocked
  release-CDN downloads; codeload source builds work. Never present SF11
  `UCI_Elo` as a certified external rating.
- **Next:** exp-0032 decisive ladder.

## exp-0032 — decisive external rating ladder + BTD fit (M0.2)

- **ID / class:** exp-0032, MEASUREMENT / rating estimation. Prereg
  `docs/DEV6_PREREG_EXP0031.md` §3 + §6.2 (deviation disclosed).
- **Hypothesis:** a connected bipartite ladder with a draw-aware BTD model yields
  a reproducible pool-specific internal rating with honest uncertainty,
  saturation handling and model diagnostics, with dev5 AND dev6 in one pool.
- **Design / control:** 8 anchors (SF11-L4/L8/L12/L16/L20 + SF8/SF9/SF10) x
  5 subjects (dev4, dev5_official, dev5_rebuilt, dev6_champion,
  dev6_failed) x 80 games = **3,200 games**, 40 fresh disjoint 40-opening
  slices, fixed-node 6000 +/-15 %, hash 16, threads 1, max 240 plies.
  `scripts/dev6_ladder.py`, `scripts/fit_ladder.py`.
- **Raw:** `benchmarks/exp-runs/exp0032-ladder-*/` (PGN/JSONL/CSV/cell.json),
  `benchmarks/dev6-baseline/ladder_cells.json`, `ladder_results.json`,
  `docs/DEV6_EXTERNAL_LADDER_REPORT.md`.
- **Results:** 3,186 adjudicated games, 14 `UNADJUDICATED_MAX_PLIES`, **0**
  TIME_FORFEIT / illegal / crash / UCI failures, 1,600 clusters. BTD MLE
  `nu=0.190`, NLL 2101.9, per-cell residual RMSE 0.0328, 1,000 cluster
  bootstrap replicates. Internal ratings (mean 0, 95% CI): sf8 +485.8
  [+407.6,+602.0], sf10 +330.8 [+270.1,+413.0], sf11-L20 +312.3
  [+245.9,+387.4], sf9 +301.9 [+243.6,+371.8], sf11-L16 -4.3 [-41.7,+33.5],
  sf11-L12 -9.8 [-52.1,+31.1], sf11-L8 -59.0 [-94.5,-24.9],
  dev6_champion -169.0 [-210.6,-134.1], dev5_rebuilt -173.9 [-214.7,-136.3],
  dev6_failed -184.7 [-227.5,-149.7], dev4 -197.9 [-238.4,-162.3],
  dev5_official **-205.0 [-246.8,-165.7]**, sf11-L4 -427.4 [-479.7,-388.1].
  Saturated cells (sf8, sf10) retained.
- **Calibration:** **NOT DEFENSIBLY CALIBRATED.** Rough affine context from
  SF11's own `UCI_Elo` (slope 1.62, intercept 2449.8, anchor residual SD
  **199 Elo**) gives dev5 ~2118 "context Elo"; systematic error unknown and
  likely large. NO absolute Elo, NO CCRL equivalence, NO gap-to-3000 claim.
- **Outcome / classification:** PARTIAL SUCCESS — ladder implemented and fitted
  with qualified results, but the **disjoint-slice confound** makes the ordering
  of the five StockBear subjects unreliable (`dev5_official` rated ~31 internal
  Elo BELOW bench-identical `dev5_rebuilt`, contradicting exp-0030). Leave-one-
  anchor-out subject ordering is unstable. SF11 skill anchors are non-monotonic
  (L12~L16, big L16->L20 jump); SF11 `Skill::pick_best` is time-seeded and not
  bitwise reproducible.
- **Root cause:** assigning a DIFFERENT opening slice to each cell mixes slice
  difficulty with engine strength in cross-cell comparisons. Recording this, not
  smoothing it.
- **Lessons / non-repeatable:** never allocate disjoint slices across cells whose
  ratings will be compared; use a shared paired opening set. Fixed-node !=
  fixed-time. Do not claim subject-level ordering from a star ladder with
  per-cell slices.
- **Next:** exp-0032b paired shared-opening sensitivity (registered addendum),
  then update ladder docs; exp-0033 strength direction.

## exp-0032b — paired shared-opening sensitivity (confound check)

- **ID / class:** exp-0032b, registered ADDENDUM (prediction frozen BEFORE its
  results in `scripts/dev6_ladder_paired.py` docstring), MEASUREMENT diagnostic.
- **Hypothesis:** the star ladder's ~31 internal-Elo official/rebuilt gap is an
  opening-slice artifact, so the three champion binaries must be statistically
  indistinguishable on a SHARED opening set; `dev6_failed` should remain
  measurably weaker than `dev6_champion`.
- **Design / control:** 5 subjects full round-robin (10 pairings x 200 games =
  2,000 games), ONE shared 100-opening suite (SHA `e281ae5e0ab5bd30…`), identical
  opening order via seed `2026111100`, colour-reversed, fixed-node 6000 +/-15 %,
  hash 16, threads 1, max 240 plies. `scripts/dev6_ladder_paired.py`.
- **Raw:** `benchmarks/exp-runs/exp0032b-paired-*/`,
  `benchmarks/dev6-baseline/ladder_paired.json`.
- **Results:** paired BTD (`nu=0.472`) internal Elo: dev5_official +24.6,
  dev5_rebuilt +12.3, dev6_champion 0.0, dev4 -16.9, dev6_failed -20.0. Every
  head-to-head 95% CI includes zero: official/rebuilt +20.9 [-13.6,+55.8],
  official/champion +20.9 [-13.6,+55.8], champion/failed +29.6 [-9.7,+69.7],
  failed/dev4 +20.9 [-17.9,+60.2], official/dev4 +12.2 [-22.7,+47.2].
  **0** time forfeits.
- **Outcome / classification:** Prediction 1 CONFIRMED (three champion binaries
  indistinguishable; paired fit REVERSES the star ordering -> star-ladder
  subject ordering unreliable). Prediction 2 NOT CONFIRMED (champion/failed
  point estimate right direction but 200 games underpowered for ~20 Elo; no
  strength conclusion). Fixed-node/fixed-time non-interchangeability confirmed:
  official/dev4 `+12.2 [-22.7,+47.2]` here vs historical fixed-time exp-0024
  `+64.7 [+57.5,+72.0]`.
- **Lessons:** M0.2 ladder is implemented with a defensible QUALIFIED result,
  but only the anchor separation / coverage is reliable; subject-level ratings
  must come from the paired design WITH its CIs. 200 games/pairing cannot
  resolve ~20 Elo effects: future paired screens need >= ~1,000 games/pairing.
- **Next:** exp-0033 isolated strength direction; no gate weakened.

## exp-0033 — isolated razoring ablation (REJECTED)

- **ID / class:** exp-0033, SEARCH-EFFICIENCY / strength SCREEN (not a gate
  test). Prereg `docs/DEV6_PREREG_EXP0033.md`, frozen BEFORE implementation.
- **Hypothesis:** at shallow depth a node far below alpha can be confirmed as a
  fail-low by a null-window qsearch, saving nodes without losing strength.
  `SearchParams::razoring` existed but was unimplemented/unexposed — a
  genuinely unmeasured direction, not a recorded dead end.
- **Identities / control:** ONE binary `build-exp0033/stockbear` SHA
  `c412125179d5873ec4ae5cb4a06c728dc081986724666e27f8cad241fa8c57b3`,
  `Razoring=true` vs `Razoring=false`; same `params_abc.txt` + `TTEval=true`,
  Hash 16, Threads 1. Zero toolchain confound. Context baseline immutable
  official dev5 `391cb50e…` (separately, context ONLY).
- **Build/runtime:** GCC 12.2.0, `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1
  -flto=4`, no `-march=native`, Release/Ninja/CMake 4.4.4. Fixed-node
  `go nodes 6000` +/-15 %, max 240 plies. Two disjoint 600-opening batches
  (fresh, excluded all earlier suites), colour-reversed, 1,200 games each.
- **Commands / raw:** `scripts/dev6_exp0033.py`, `scripts/tournament.py`,
  `scripts/match_stats.py`; `benchmarks/exp-runs/exp0033-batchA|batchB|context-vs-dev5/`
  (PGN/JSONL/CSV), `benchmarks/dev6-baseline/exp0033_results.json`.
- **P1 efficiency (MIXED, reported honestly):** `bench --depth 12` total nodes
  OFF 6,562,637 -> ON 6,339,128 (**-3.4 %**), PASS as literally preregistered;
  but `position startpos; go depth 12` OFF 543,800 -> ON 733,944
  (**+34.96 %**), and a 10-position diverse sample was ON/OFF 0.8585. The
  saving is position-dependent and small; the regression is real at startpos.
- **P2 correctness PASS:** default-off signatures exact `243f9a1c1ba5b36f`
  (d4) / `a14ab62224f837e5` (d16); Release CTest 11/11; ASan+UBSan CTest
  11/11; python-chess oracle 600 positions / 43,200 checks / 0 mismatches;
  3x `bench --depth 12` signature `e45fa2ec2287eb41` deterministic; 0
  TIME_FORFEIT / illegal / crash / UCI failures across all matches.
- **P3 strength (REJECT):** batch A `-16.54 [-31.06,-2.09]` Elo
  (`+386=370-443`, score 0.4762); batch B `-35.27 [-49.40,-21.26]`
  (`+354=368-476`, score 0.4491); **combined `-25.88 [-36.00,-15.80]`**
  (2,397 adjudicated games, `+740=738-919`, score 0.4627, 1,197 clusters).
  Context vs dev5 `-28.87 [-53.58,-4.45]` (400 games). 3
  `UNADJUDICATED_MAX_PLIES` games excluded per documented rule.
- **Decision (frozen rule):** combined point < +10, LCB < -10, both batches
  < -5 -> **REJECT / CLOSE exp-0033**. No fixed-time Elo claim (P4). No gate
  pass, no PR/merge/tag/release.
- **Root cause:** verifying a fail-low with qsearch costs a full qsearch at
  EVERY triggered shallow node; when captures lift the stand-pat back to alpha
  the node is then searched anyway, so the extra work is not recovered. Worse,
  returning a qsearch bound as the node value perturbs TT entries and PV
  propagation at depth <= 3, losing tactical accuracy at the shallow depths
  that dominate a 6,000-node search. Net effect: -26 Elo.
- **Lessons / non-repeatable:** do NOT repeat razoring with a different margin,
  depth cut-off or schedule — that would be tuning on these results. Do NOT
  apply qsearch-verified whole-node pruning at depth <= 3. Productive
  alternative: prune INDIVIDUAL bad moves using information already computed
  (SEE) rather than pruning the whole node.
- **Next:** exp-0034 (registered BEFORE its results, materially different
  mechanism: SEE-based bad-capture pruning), then a larger shared-opening
  confirmation with isolated runners if it advances. Mission ACTIVE.

## exp-0034 — SEE bad-capture pruning pilot (ADVANCE, not a gate pass)

- **ID / class:** exp-0034, POST-REJECTION materially different direction, PILOT
  SCREEN. Prereg `docs/DEV6_PREREG_EXP0034.md`, frozen BEFORE results.
  Registered because exp-0033 was REJECTED (-25.88 Elo combined).
- **Mechanism:** skip non-hash CAPTURES with `SEE < -100` cp at depth <= 3 in
  non-PV / non-check / non-mate-window nodes, reusing the SEE already computed
  by `score_moves()`. Distinct from razoring (which pruned whole nodes via a
  qsearch verification). `BadCapturePruning` UCI `check`, default OFF.
- **Identities / control:** ONE binary `build-exp0034/stockbear` SHA
  `075ec955a65acad4624cc6d3f4998763aaa7b968e4d01a27e73cd9dfd4c77d82`, switch
  ON vs OFF; `params_abc.txt` + `TTEval=true`, Hash 16, Threads 1. Built in a
  SEPARATE directory so exp-0033's in-flight binary stayed immutable.
- **Build/runtime / raw:** same pinned GCC 12.2.0 toolchain; fixed-node 6000
  +/-15 %, max 240 plies; 2 disjoint 400-opening batches x 400 games = 800
  games. `scripts/dev6_exp0034.py`,
  `benchmarks/exp-runs/exp0034-batchA|batchB/`,
  `benchmarks/dev6-baseline/exp0034_results.json`.
- **P1 PASS:** `bench --depth 12` nodes 6,562,637 -> 5,821,954 (**-11.29 %**).
  Default-off signatures exact `243f9a1c1ba5b36f` / `a14ab62224f837e5`.
- **P2 PASS:** CTest 11/11, python-chess oracle 600/43,200/0, 2x deterministic
  `e45fa2ec2287eb41`, 0 TIME_FORFEIT / illegal / crash / UCI failures.
- **P3:** batch A `+27.12 [+1.47,+53.06]` (score 0.5401, +152=127-120, 1
  unadjudicated); batch B `+13.90 [-12.41,+40.38]` (0.5200, +148=120-132);
  **combined `+20.49 [+2.12,+38.97]`** (799 games, +300=247-252, score 0.5300,
  399 clusters). 0 forfeits.
- **Decision (frozen):** point >= +10, LCB > -10, both batches >= -5, P1/P2
  PASS -> **ADVANCE** to exp-0035 larger confirmation. **NOT a dev6 gate
  pass, NOT a strength claim** (800 games, fixed-node, same-binary ablation;
  Gate 1 needs >= +75 with LCB > +50 on two fixed-time datasets vs dev5).
- **Outcome / limitation:** two driver crashes occurred while FORMATTING /
  recombining results (first: `pair_openings` omitted -> None Elo; second: an
  unadjudicated `None` pair in the combined loop). NO result JSON was written
  by either crashed run; the completed rerun's raw games are unchanged and were
  finalised by an independent recomputation. Both defects are corrected in the
  committed driver and disclosed here. 800 games cannot resolve more than a
  large effect; the CI is wide.
- **Lessons / non-repeatable:** do not claim strength from a pilot; do not
  re-tune the frozen 100 cp margin on these results. Shared paired openings and
  >= ~1,000 games/batch are needed. Fixed-time confirmation requires isolated
  runners.
- **Next:** exp-0035 (2 x 1,000 primary + 600 Track A context games), then
  isolated-runner fixed-time work only after explicit authorization.

## exp-0035 — larger fixed-node confirmation of bad-capture pruning (CONFIRMED, fixed-node only)

- **ID / class:** exp-0035, CONFIRMATION (fixed-node). Prereg
  `docs/DEV6_PREREG_EXP0035.md`, frozen BEFORE results; triggered by exp-0034's
  frozen ADVANCE rule. NOT a dev6 gate test.
- **Hypothesis:** `BadCapturePruning=true` is stronger than `false` at fixed
  nodes with a tighter CI, and the switch-ON candidate is not worse than an
  identical-toolchain dev5 rebuild.
- **Identities:** primary ONE binary `build-exp0034/stockbear`
  `075ec955a65acad4624cc6d3f4998763aaa7b968e4d01a27e73cd9dfd4c77d82` (ON vs
  OFF). Track A context: same candidate (ON) vs `build-dev5/stockbear`
  `214cbed002e58fbc94d74a089491bba94634e9e8d06b782992548fdacaa9b501`
  (`git archive v0.1.0-dev5` rebuilt in the SAME pinned toolchain), both
  `params_abc.txt` + `TTEval=true`. Official dev5 `391cb50e…` remains
  immutable, NOT used here and never relabelled.
- **Build/runtime / raw:** GCC 12.2.0, `-mpopcnt -mbmi2 -mlzcnt
  -DSB_SEE_CACHE=1 -flto=4`, no `-march=native`, Release/Ninja/CMake 4.4.4;
  fixed-node 6000 +/-15 %, hash 16, threads 1, max 240 plies. Two disjoint
  1,000-opening batches x 1,000 games = 2,000 primary games + 600 Track A
  context games on a third fresh 300-opening slice (2,600 games total).
  `scripts/dev6_exp0035.py`, `benchmarks/exp-runs/exp0035-batchA|batchB|trackA/`,
  `benchmarks/dev6-baseline/exp0035_results.json`.
- **Results (two-sided opening-clustered CR1 95 % CI):**
  - batch A `+22.75 [+7.28,+38.31]` (score 0.5331, +376=311-310)
  - batch B `+31.51 [+15.40,+47.76]` (score 0.5428, +384=309-299)
  - **combined `+27.10 [+15.94,+38.33]`** (1,989 adjudicated games,
    +760=620-609, score 0.5380, 989 clusters)
  - Track A context (candidate ON vs identical-toolchain dev5 rebuild)
    `+19.19 [-0.76,+39.28]` (score 0.5275, +230=172-197, 600 games)
  - **0** TIME_FORFEIT / illegal / crash / UCI failures; 11
    `UNADJUDICATED_MAX_PLIES` exclusions (documented rule).
- **Correctness:** default-off signatures exact `243f9a1c1ba5b36f` /
  `a14ab62224f837e5`; CTest 11/11 Release and 11/11 ASan+UBSan; python-chess
  oracle 600/43,200/0; 3x deterministic `e45fa2ec2287eb41`.
- **Independent audit:** `scripts/dev6_audit.py` re-parsed every raw
  `match.jsonl` from scratch: **179 stored values verified, AUDIT PASS**;
  independent Elo-from-score +26.43 agrees with stored CR1 +27.10.
- **Decision (frozen):** combined point >= +10, combined LCB > 0, both batches
  >= -5, Track A CI lower bound > -10, correctness PASS ->
  **CONFIRMED (fixed-node only)**.
- **NOT claimed:** this is NOT a dev6 gate pass, NOT a fixed-time Elo, NOT an
  absolute/CCRL rating, and NOT a gap-to-3000 estimate. Gate 1 requires >= +75
  with LCB > +50 on two independent FIXED-TIME datasets against exact dev5;
  Gate 4 requires final-source CI and the exact packaged binary.
- **Root cause of the gain (mechanism, evidence-backed):** skipping clearly
  losing captures at shallow depth removes ~11 % of fixed-depth nodes and
  avoids polluting the TT/PV with hopeless capture lines; the same-binary
  switch isolation makes the ~+27 Elo attributable to the mechanism rather
  than to a toolchain or opening-set difference.
- **Lessons / non-repeatable:** do NOT re-tune the frozen 100 cp margin on this
  result; do NOT promote the switch to default before a fixed-time isolated
  confirmation (would change the shipped bench signature); do NOT claim a
  strength gate pass from fixed-node evidence alone.
- **Next:** decisive FIXED-TIME confirmation on isolated CI runners with
  unchanged Gate 1/2/3/4, exact packaged candidate artifact, and final-source
  CI. Requires explicit authorization for a push. Mission ACTIVE.

---

## FINAL-SOURCE CI — exp-0036 context (2026-11-04)

- **Classification:** PASS (not a strength gate).
- Run `41770918367`, `push`, head `03868dafc6f644abb5b53caf2ef6ef1dda14e830`,
  conclusion `success`, 9/9 jobs (Clang Release, ASan+UBSan, Min CMake 3.16,
  Independent reference, ThreadSanitizer, ubuntu-22.04 Debug/Release,
  windows-2022 Debug/Release). Evidence
  `benchmarks/dev6-baseline/final_source_ci.json`.
- Artifact IDs `13294612578` (linux), `13295120861` (windows),
  `13295575626` (dead-position). Download BLOCKED by
  `productionresultssa6.blob.core.windows.net` EOF (outside sandbox allow-list);
  not retried unchanged. CI build image omits the pinned portable flags, so a
  CI artifact is NOT the Track A match binary; Gate 4 unaffected.

## exp-0036 — FIXED-TIME confirmation of exp-0035 (40+4 ms, 2026-11-04)

- **Classification:** **FIXED TIME / GATE NOT MET — conclusively blocked.**
  Closed at the pre-registered futility boundary (combined 95 % UCB +32.81 <
  +50). Gate 1 FAIL; Gate 4 UNMET. NOT an invalid measurement: Stage-0
  validity gate PASSED with 0 TIME_FORFEITs. NOT a noisy conclusion and NOT a
  gate pass.
- **Hypothesis:** the fixed-node `+27.10 [+15.94,+38.33]` Elo of
  `BadCapturePruning=true` (exp-0035) translates into a fixed-time gain large
  enough to satisfy Gate 1 (>= +75 and 95 % LCB > +50).
- **Prereg:** `docs/DEV6_PREREG_EXP0036.md`, SHA
  `430fe96ebd4095e7a4df84716f0b909f175f04cd95cfd4e55c303346f03e610d`, frozen
  before any fixed-time game; Gates 1–4 reproduced verbatim, unweakened.
- **Runner:** Tier 1 (GitHub isolated VM) **BLOCKED by the one-push
  authorization boundary** (lane has no `workflow_dispatch`, is absent on
  `main`, and its `commit_and_push` performs further remote writes). Tier 2
  executed: LOCAL dedicated core, `taskset -c 1`, no concurrent CPU work,
  pre-registered validity gate. Tier 2 is NOT a dedicated VM.
- **Source / binary / params / build env:** pushed source SHA `03868da`;
  candidate `build-exp0034/stockbear`
  `075ec955a65acad4624cc6d3f4998763aaa7b968e4d01a27e73cd9dfd4c77d82`
  (GCC 12.2.0-14, ld 2.40, glibc 2.36, CMake 4.4.4, Ninja, Release,
  `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`, no `-march=native`);
  official dev5 `391cb50e13ab9...`; Track A rebuild
  `214cbed002e58f...`; `EvalParams=research-data/params_abc.txt`,
  `TTEval=true`, Hash16, Threads1, max-plies 240. Local CPU Xeon 2.60 GHz,
  2 vCPU, CPU 1 dedicated.
- **Commands / env:** `scripts/dev6_exp0036.py --all` ->
  `scripts/tournament.py --base-ms 40 --inc-ms 4 --hash 16 --threads 1
  --max-plies 240 --a-option BadCapturePruning=true`; fresh disjoint suites
  seed `2026111901` (1,600 openings), arm seeds `2026112000..2026112103`;
  `--nodes` NEVER used. Log `benchmarks/exp-runs/exp0036-run.log`.
- **Raw paths:** `benchmarks/exp-runs/exp0036-{stage0,batchA,batchB,null,trackA}/`,
  `benchmarks/dev6-baseline/exp0036_results.json`, `docs/DEV6_EXP0036_REPORT.md`.
- **Statistics:** Stage 0 null -10.43 [-31.86,+10.93] (400 games), 0 forfeits,
  NPS ratio 1.0059 in [0.97,1.03] -> validity PASS. batchA +17.14
  [+1.24,+33.12] (1,000), batchB +25.91 [+10.03,+41.91] (997), **combined
  +21.52 [+10.28,+32.81]** (1,994 games, `+735=645-614`, score 0.5303, 994
  clusters), null -1.75 [-22.39,+18.87] (400), Track A +26.24
  [+0.99,+51.77] (400). 0 TIME_FORFEIT / illegal / crash / UCI failure in all
  arms; 6 UNADJUDICATED_MAX_PLIES exclusions. CR1/t opening-clustered
  two-sided 95 % CI. Independent audit: 201 stored values, AUDIT PASS;
  Elo-from-score +21.11 vs stored CR1 +21.52.
- **Gate evaluation:** Gate 1 **FAIL** (point +21.52 < +75; LCB +10.28 not >
  +50); both batches positive and consistent (sub-clauses pass). Gate 2
  direction supported by both datasets. Gate 3 PASS (both nulls include 0).
  Gate 4 **UNMET** (no packaged candidate release artifact; CI artifacts are a
  different build image and undownloadable; Tier 2 not an isolated VM).
- **Outcome / root cause:** the mechanism produces a modest, reproducible
  fixed-time gain (~+21 Elo), roughly a quarter of the +75 gate; the fixed-node
  +27 Elo did NOT translate into a gate-sized fixed-time gain. Gate 4 is
  structurally blocked: no packaged candidate artifact exists, and decisive
  Tier-1 isolated-runner confirmation needs a new prereg + trigger commit and
  result pushes, i.e. a SECOND remote write not authorized here.
- **Lessons learned:** (1) a validity-gated dedicated CORE can produce clean
  zero-forfeit fixed-time data locally, but that is not equivalent to a
  dedicated VM and cannot satisfy Gate 4; (2) fixed-node gains are unreliable
  proxies for fixed-time gains — exp-0035 +27.10 fixed-node vs exp-0036 +21.52
  fixed-time are DIFFERENT quantities, never interchangeable; (3) a frozen
  futility/upper-bound stopping rule closes an experiment cheaply without
  weakening gates; (4) recording the authorization boundary as an experimental
  limitation is mandatory, not optional.
- **Non-repeatable / dead ends:** do NOT re-run the whole-screen 40+4 ms
  confirmation this cycle (UCB already < +50); do NOT present Tier-2 results
  as Tier-1 isolated-runner evidence; do NOT claim Gate 1/4 passes; do NOT
  stack badCapturePruning with another switch post hoc; do NOT tune
  `BadCaptureMargin=100` on these results; do NOT enable `BadCapturePruning`
  by default before isolated-runner confirmation; do NOT repeat razoring,
  small CPU NNUE, extended features, or other recorded dead ends.
- **Next experiment:** `docs/DEV6_PREREG_EXP0037.md` — **ProbCut**, isolated
  default-off switch, fixed-node screen then Tier-1 fixed-time, Gates 1–4
  unchanged. NOT executed: requires new explicit authorization for the
  additional push. Ranked ahead of qsearch-TT, endgame eval knowledge, NNUE
  with an accuracy→strength link, and any stacking.

---

## Tier-1 infrastructure — repaired (2026-11-04)

- **Classification:** infrastructure fix, NOT a strength experiment.
- **Root cause of the previous blocker:** `dev6-lane.yml` was triggered only by
  a push to `benchmarks/exp-runs/dev6-trigger.json`, had no
  `workflow_dispatch`, and `scripts/actions_dev6_lane.sh:commit_and_push()`
  pushed result commits. A new experiment therefore needed a second remote
  write AND generated further automatic ones. Both the job-logs endpoint and
  the artifact `/zip` endpoint 302 to
  `productionresultssa6.blob.core.windows.net`, which is outside the sandbox
  allow-list (EOF), so artifacts could not be downloaded locally.
- **Repair:** `.github/workflows/dev6-tier1.yml` (`workflow_dispatch` only,
  pinned `source_sha`, `mode=benchmark|export`, isolated `ubuntu-latest` VM
  per matrix job, `concurrency` guard, no benchmark-time pushes, full artifact
  bundles) + `scripts/dev6_tier1_job.py` (pinned build, exact dev5 SHA, exact
  bench signature, packaged-and-extracted binary identity for Gate 4,
  CR1/t independent recomputation, fingerprint/manifest/SHA256SUMS).
- **Artifact contingency:** a deliberate, separately dispatched `mode=export`
  job downloads artifacts from the pinned run via
  `actions/download-artifact(run-id)` (server-side, supported interface),
  verifies every `SHA256SUMS.txt`, and makes ONE explicit evidence commit.
  Evidence then becomes retrievable via `git` and the GitHub Contents API
  (`api.github.com`), both reachable. No bypass, no fabricated hashes.
- **Legacy lane:** `dev6-lane.yml` automatic `push: paths` trigger removed and
  an explicit `legacy_confirm == 'yes'` guard added; the old script is kept
  read-only for provenance and is not invoked. No duplicate executions.
- **Verification:** to be recorded in `docs/DEV6_TIER1_INFRASTRUCTURE.md`
  from the actual dispatched smoke run + exported artifact.

## exp-0037 — ProbCut (REGISTERED, results pending)

- **Status:** preregistered and implemented; NO evaluation game has been used
  for a strength claim yet. This entry is the pre-result record; the closing
  entry (classification, root cause, decision, next action) is appended after
  the frozen Stage-1 screen.
- **Preregs:** `docs/DEV6_PREREG_EXP0037.md` (primary, unchanged) +
  `docs/DEV6_PREREG_EXP0037_ADDENDUM.md` (full frozen design before results).
- **Hypothesis / mechanism:** raised-beta (`beta + 200 cp`, frozen) reduced
  depth (`depth - 4`, frozen) null-window search at non-PV `depth >= 5`
  predicts a full-depth fail-high; cutting saves the move loop.
- **Source / binary:** exact pinned source SHA in Tier-1 manifests; local
  `build-exp0037/stockbear`
  `95c31ab6d214928fe7c5cd68f3aa031abc9f926d29c90d639811ae249e61afb9`; pinned
  flags `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`; default OFF.
- **Correctness (before results):** ctest 11/11 Release, 11/11 ASan+UBSan,
  UCI integration/fuzz, perft, dead-position, exact bench
  `243f9a1c1ba5b36f` / `a14ab62224f837e5`, 3x determinism
  `e45fa2ec2287eb41`, `ProbCut` UCI default false.
- **Pre-result diagnostics (recorded, not used as a decision):** startpos
  depth 12 ON 888,947 nodes vs OFF 543,800 (+63 %); 12-position depth-16
  bench ON 156,640,123 vs OFF 170,160,152 (-7.96 %). Shallow overhead vs
  deep cutoffs — the preregistered screen settles it.
- **Frozen rules:** Stage 1 fixed-node 2x600 games, ADVANCE only if combined
  >= +10, LCB > -10, both batches >= -5, null includes 0, clean correctness.
  Stage 2a only on Tier-1 fixed-time 40+4 ms; futility UCB < +50 closes.
  Gates 1-4 UNCHANGED. No default change, no PR/merge/tag/release.

### exp-0037 CLOSING ENTRY (2026-11-04, fixed-node screen)

- **Classification:** **CLOSED at the frozen Stage-1 rule / direction ABANDONED**
  (weak positive, far below the advance threshold). NOT an invalid measurement
  and NOT a strength claim. Fixed-node only.
- **Source SHA:** the pinned source commit `e982e6f` (ProbCut implementation);
  local binary `build-exp0037/stockbear`
  `95c31ab6d214928fe7c5cd68f3aa031abc9f926d29c90d639811ae249e61afb9`.
- **Settings:** ONE binary, single switch `ProbCut=true` vs `ProbCut=false`,
  `go nodes 6000 --nodes-jitter 0.15`, hash 16, threads 1, max-plies 240,
  fresh disjoint suites seed `2026112001` (300+300+200 openings), seeds
  `2026112100..02`. Raw `benchmarks/exp-runs/exp0037-{stage1A,stage1B,null}/`.
- **Results (two-sided opening-clustered CR1 95 % CI):** batch A
  **+6.41 [-12.26,+25.12]** (600 g), batch B **+1.16 [-17.30,+19.63]**
  (598 g), **combined +3.78 [-9.34,+16.90]** (1,198 g,
  `+416=379-403`, score 0.5054, 598 clusters); null **+10.43
  [-12.01,+32.95]** (400 g) includes 0; 0 TIME_FORFEIT / illegal / crash /
  UCI failures; 2 UNADJUDICATED_MAX_PLIES exclusions.
- **Independent audit:** `scripts/dev6_audit.py` re-parses all raw JSONL;
  combined independent Elo-from-score +3.76 vs stored CR1 +3.78; AUDIT PASS.
- **Frozen rule:** combined >= +10 AND LCB > -10 AND both batches >= -5 AND
  null includes 0 AND clean. LCB -9.34 > -10 PASS; point +3.78 < +10 FAIL ->
  **CLOSED, no Stage 2a**. No threshold changed after results.
- **Root cause (evidence-backed, not intuition):** the pre-result depth-12
  diagnostic (+63 % nodes with ProbCut ON at startpos) was the correct
  predictor. At the 40+4 ms control the steady-state per-move budget is the
  4 ms increment, so reachable depths are shallow (~6-8); a `depth - 4`
  verification search at `beta + 200 cp` is then mostly pure overhead and
  rarely produces a cutoff. The deeper -7.96 % node saving at depth 16 is
  irrelevant at bullet TC. TT entries at reduced depth also perturb ordering.
  The mechanism's economics at this time control are structurally unfavourable.
- **Decision:** ABANDONED, not deferred for a margin/depth retune. Retuning
  the frozen 200 cp margin or the depth-4 reduction on these results would be
  superficial parameter change, and the recorded dead ends already show
  best-of-N knob selection does not produce gate-sized gains. Do NOT repeat
  ProbCut this cycle. `ProbCut` stays default OFF.
- **Next action:** exp-0038 (rank 1 after this closure) — qsearch
  transposition-table integration with bit-exact static-eval reuse, isolated
  default-off switch, preregistered before any evaluation game. Mission ACTIVE.

## exp-0038 — dedicated qsearch transposition table (IN PROGRESS, not a result)

Registered before any evaluation game. Hypothesis, exact code change, pinned
suites/plan, 40+4 ms control, Stage-0 validity gate and frozen decision rules
are in `docs/DEV6_PREREG_EXP0038.md`. Pre-result profiling (d16 -0.0006 %
nodes / +3.86 % time; instrumented hits concentrated on cheap early-return
nodes) is a diagnostic, NOT a strength result and NOT a decision. This entry
will be completed with exact source SHA, binary SHA-256, W/D/L, CR1/t CIs,
independent recomputation, root-cause class and abandon/defer/redesign outcome
after the preregistered Tier-1 screen. No vague "optimization unsuccessful".

## exp-0039 — dead static evaluation on TT hits (ELIMINATED AT PROFILING)

Exact source SHA inspected: `2aacf4a643d5066526a33dd1d0f7f504b52e87f9`.
Hypothesis: remove a full `evaluate()` call whose result is discarded whenever
`TTEval=true` and a TT entry is present; bit-exact NPS gain should buy depth
at 40+4 ms. Settings: `bench --depth 16/12 --param ttEval=0|1`, pinned flags
`-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`, five repeats. Raw results:
default d16 signature `a14ab62224f837e5` and 170,160,152 nodes identical
before/after; d12 signature `2c7cea9dc3051590` and 6,449,299 nodes identical;
ctest 11/11. Timings were noise-dominated (same old binary: 2.6273 s at
ttEval=0 vs 2.4443 s at ttEval=1; two builds on the identical ttEval=0 path
differed ~7 %). Why eliminated: the residual ~2.9 % is below build-layout and
shared-vCPU noise, so there is no credible Elo upside and no defensible
fixed-time measurement; profiling is the correct place to stop. Abandoned as a
strength direction; source reverted, no games played, no strength claim. Next
action remains the preregistered Tier-1 exp-0038 result and independent audit.

## exp-0038 — FINAL RESULT: CLOSED / ABANDONED at frozen UCB < +20

Exact source SHA `2aacf4a643d5066526a33dd1d0f7f504b52e87f9`; packaged and
tested candidate binary SHA-256
`30874fbc1e6c7da03b4571d1c316fb082b0b151350d1d7ea86e5a7abb18931f0` (built ==
packaged == tested); dev5 baseline `391cb50e…`. Pinned flags
`-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`. Tier-1 isolated VMs, run
`41780333569`, export `41781546677`, CI `41780333461` SUCCESS, artifacts
`13298354527`,`13298614709`,`13299405640`,`13299640420`; 4/4 SHA256SUMS 0
failures. FIXED TIME 40+4 ms, Hash16/Threads1/maxplies240, NO `--nodes`;
same binary `QSearchTT=true` vs `false`; fresh disjoint suites seed
`2026112101` (1,400 openings).

Hypothesis: a dedicated 2^16 qsearch bound cache should let repeated
quiescence positions cut without re-searching, buying depth at 40+4 ms.
Raw/audited results: Stage-0 validity null 399 games `−8.7314 [−27.2458,
+9.7335]`, 0 forfeits/illegal/UCI failures, CI includes 0 -> PASS. batchA 999
games 351/330/318 `+11.1440 [−0.9681,+23.2833]`; batchB 997 games
347/314/336 `+4.1946 [−8.4247,+16.8249]`; null 397 games 132/133/132
`+0.8818 [−15.6419,+17.4096]` includes 0; FROZEN COMBINED 1,996 games
698/644/654, score 0.5110220, `+7.6755 [−1.0670,+16.4278]`, 996 clusters.
Independent raw-JSONL audit `scripts/dev6_exp0038_audit.py`: 44 stored values,
0 issues, AUDIT PASS; independent Elo-from-score +7.6601; seeded cluster
bootstrap `[−1.0465,+16.4072]`.

Why failed: unsuitable hypothesis / search interaction. Instrumented profiling
showed millions of hits concentrated on stand-pat, delta and no-capture nodes
that already return immediately, so the cache pays a probe+store at EVERY
qsearch node and saves almost no subtree work (d16 −0.0006 % nodes, +3.86 %
time). At the ~4 ms effective increment the overhead cancels the small reuse
benefit. Not an implementation defect: Release ctest 11/11, ASan+UBSan 11/11,
exact default-off bench/d16/d12 signatures, 3x determinism, 0 illegal/forfeit.
Decision: frozen §6 UCB `+16.4278 < +20` -> CLOSE; no ADVANCE (point < +20,
LCB < 0), no Stage 2a, no retune of cache size/hash/margin, no repeat, no
bundle containing qsearchTT, `QSearchTT` stays default OFF. ABANDONED.
Next action: continue ranked directions and independent audits; see
`docs/DEV6_CURRENT_STATUS.md`. No vague "optimization unsuccessful".

## exp-0040 — banked-time allocation (ELIMINATED AT PROFILING, no games played)

Exact source state: local implementation of `SearchParams::bankedTime`,
UCI `BankedTime`, `bench --param bankedTime=0|1`,
`TimeManager::start(limits, side, bankedTime)` with
`target = increment + remaining/20` (versus shipped
`remaining/30 + 3*increment/4`). Hypothesis: at 40+4 ms both arms currently
think only ~4 ms and leave the 40 ms banked clock unused; spending part of it
early should buy depth. This is NOT exp-0004 `FullSoftBudget` (both early stops
remain, hard budget still reserves the 10 ms overhead, identical clocks).

Validation: Release ctest 11/11, ASan+UBSan ctest 11/11, exact default-off
bench/d16/d12 signatures, UCI default false. A temporary instrumented build
confirmed the switch is LIVE: `go wtime 40 btime 40 winc 4 binc 4` reported
`bankedTime=0 remaining=40 increment=4 target=4 soft=4 hard=13` and
`bankedTime=1 ... target=6 soft=6 hard=13`. Raw profiling on startpos and a
middlegame FEN, 5 repetitions each: OFF and ON both produced **depth 6,
12,539 nodes, engine time 5 ms** — bit-identical trees. Why failed: the
`SB_EARLY_PERMILLE=550` stable-move stop and `SB_CLOCK_PERMILLE=700` clock stop
dominate at this control; at 5 ms elapsed the usage is 1250 per mille of a
4 ms soft budget and 833 per mille of a 6 ms budget, so both break after the
same iteration and the soft-budget size is irrelevant. Root-cause class:
**search-interaction / unsuitable hypothesis**, not an implementation defect.
Decision: ABANDONED at profiling, no Tier-1 games spent, no strength claim, no
retune of the divisor (that would be best-of-N parameter selection, a recorded
dead end). The switch remains default OFF so the profiling is reproducible.
Methodological rule added: any future time-allocation candidate must FIRST
demonstrate at 40+4 ms that it changes the search tree, before a tournament is
spent. Next action: exp-0041 (frozen prereg, mechanism confirmed live).

## exp-0041 — FINAL RESULT: CLOSED / ABANDONED at frozen UCB < +10 and point <= 0

Exact source SHA `87f82854db525da05c5bc5bcc746dd4cf7014698`; frozen prereg
SHA `2f5c1b08…`; packaged/tested binary SHA-256 recorded in
`docs/DEV6_EXP0041_REPORT.md`; dev5 baseline `391cb50e…`. Tier-1 isolated VMs
run `41782954038`, export `41784088471`, CI `41782954037` SUCCESS; 4/4
SHA256SUMS 0 failures. FIXED TIME 40+4 ms, Hash16/Threads1/maxplies240, NO
`--nodes`; same binary `BadCapturePruning=true,BadCaptureAllDepths=true` vs
validated control `BadCapturePruning=true`; 1,400 fresh disjoint openings seed
`2026112601`.

Hypothesis: SEE < −100 captures (frozen `BadCaptureMargin=100`) are refuted at
all remaining depths, not just depth <= 3, so extending the validated
exp-0036 mechanism buys depth. Raw/audited results: Stage-0 validity null
399 games `+6.9846 [−11.4958,+25.5046]`, 0 forfeits/illegal/UCI failures,
CI includes 0 -> PASS. batchA 998 games 346/313/339
`+2.4419 [−11.4054,+16.2969]`; batchB 997 games 322/316/359
`−12.5887 [−27.3582,+2.1355]`; null 398 games 135/128/135
`−1.7547 [−20.3714,+16.8518]` includes 0; FROZEN COMBINED 1,995 games
668/629/698, score 0.4924812, `−5.0635 [−15.1810,+5.0454]`, 995 clusters.
Independent raw-JSONL audit 44 stored values, 0 issues, AUDIT PASS;
independent Elo-from-score −5.2250; seeded cluster bootstrap
`[−15.0242,+5.0635]`.

Why failed: unsuitable hypothesis / search-eval interaction, NOT an
implementation defect (Release/ASan ctest 11/11, exact default-off
signatures, 0 illegal/forfeit). Profiling proved the mechanism was LIVE
(−42.1 % fixed-depth-12 nodes), but deleting SEE<−100 captures higher in the
tree removes sound deep sacrifices / interpositions and destabilises ordering;
the extra depth does not pay for the lost tactical accuracy. Decision: frozen
§5 UCB `+5.0454 < +10` and point <= 0 -> CLOSE; no ADVANCE (point < +20,
LCB < 0, batchB < −5), no bundle, no retune of the frozen margin, switch stays
default OFF. ABANDONED. Next action: continue ranked directions and
independent audits; see `docs/DEV6_CURRENT_STATUS.md`. No vague "optimization
unsuccessful".

## exp-0042 — max-gain delta pruning (REGISTERED; results pending)

Frozen before any evaluation game: `docs/DEV6_PREREG_EXP0042.md`, SHA
`3345325ce3e4fdc98501410bd7fcea2b3b5e7e1aa6b9d6a8139e4ced6b29c62b`.
Hypothesis, exact code change (`MaxGainDelta`, default OFF), pinned flags,
40+4 ms control, Stage-0 validity gate, two independent 1,000-game batches,
400-game null, frozen ADVANCE/CLOSE rules and expected failure modes are all in
the prereg. Pre-result validation: Release ctest 11/11, ASan+UBSan ctest 11/11,
exact default-off bench/d16/d12 signatures, UCI default false. Pre-result
profiling (NOT a result): `go depth 12` startpos 543,800 nodes / 269 ms OFF vs
618,920 nodes / 309 ms ON; the mechanism is LIVE but node counts are a
misleading proxy. This entry will be completed with exact source SHA, binary
SHA-256, W/D/L, CR1/t CIs, independent recomputation, root-cause class and
abandon/defer/redesign outcome after the preregistered Tier-1 screen. No vague
"optimization unsuccessful".

## exp-0042 SCREEN — INCONCLUSIVE (not a failure, not a success)

Exact source SHA `efd2f22ddf327c8462c8839a2f5bbbcebfd92609`; frozen prereg SHA
`3345325ce3e4fdc98501410bd7fcea2b3b5e7e1aa6b9d6a8139e4ced6b29c62b`. Tier-1
isolated VMs run `41802986830`, export `41804342869`, CI `41802986854`
SUCCESS; 4/4 SHA256SUMS, 0 failures. FIXED TIME 40+4 ms, Hash16/Threads1/
maxplies240, NO `--nodes`; same binary `MaxGainDelta=true` vs `false`; 1,400
fresh disjoint openings (seed 2026112801, zero overlap with 29,202 earlier).
Raw/audited results: Stage-0 validity null 400 games 137/123/140
`−2.6058 [−21.9076,+16.6798]`, 0 forfeits/illegal/UCI failures, CI includes
0 -> PASS; batchA 1,000 games 357/300/343 `+4.8644 [−10.1879,+19.9350]`;
batchB 998 games 336/328/334 `+0.3488 [−14.5041,+15.2030]`; null 399 games
144/131/124 `+17.4738 [−1.9909,+37.0488]` (CI includes 0; unusually large
noise point estimate is disclosed); frozen combined 1,998 games 693/628/677,
score 0.5040040, `+2.6110 [−7.9556,+13.1825]`, 998 clusters. Independent
raw-JSONL audit 44 stored values, 0 issues, AUDIT PASS; independent Elo-from-
score +2.7823; seeded cluster bootstrap `[−8.0085,+12.8868]`.

Decision under UNCHANGED frozen §5: ADVANCE FALSE (point +2.61 < +20, LCB
< 0); CLOSE FALSE (UCB +13.18 >= +10 and point > 0) -> **INCONCLUSIVE**, which
the prereg explicitly routes to "more samples under the same frozen
conditions". No strength claim, no default change, no retune, no bundle.
`docs/DEV6_PREREG_EXP0042_ADDENDUM.md` (SHA
`21b0b1e6b425c8a7083f674d5019f6329dbe57286efcdbc1dedc8c719669bf74`) freezes a
BOUNDED additional sample (two fresh 1,000-game batches + null + Stage-0,
separate Tier-1 run, NO pooling with this screen) with the SAME thresholds and
a conservative experiment-level compute bound. Root-cause class is deliberately
NOT assigned yet: the observed effect is statistically indistinguishable from
zero. This entry will be completed after the confirmation.

## exp-0042 CONFIRMATION — FINAL RESULT: CLOSED / ABANDONED

Exact source SHA `ec223feaaa444c24cc135aecdc8fec326d210783`; addendum SHA
`21b0b1e6b425c8a7083f674d5019f6329dbe57286efcdbc1dedc8c719669bf74`;
packaged/tested binary SHA-256 in `docs/DEV6_EXP0042_REPORT.md`; dev5 baseline
`391cb50e…`. Tier-1 isolated VMs run `41804818965`, export `41806227744`, CI
`41804818984` SUCCESS; 4/4 SHA256SUMS 0 failures. FIXED TIME 40+4 ms,
Hash16/Threads1/maxplies240, NO `--nodes`; same binary `MaxGainDelta=true` vs
`false`; 1,400 fresh disjoint confirmation openings seed `2026113001`.

Raw/audited results: Stage-0 validity null 400 games 147/116/134
`+10.5851 [−8.5366,+29.7711]`, 0 forfeits/illegal/UCI failures, CI includes
0 -> PASS; batchA 998 games 340/306/352 `−4.1862 [−19.7858,+11.3966]`;
batchB 997 games 300/346/351 `−17.4914 [−33.1133,−1.9399]`; null 399 games
127/138/134 `−6.1113 [−24.7147,+12.4570]` includes 0; FROZEN COMBINED 1,995
games 640/652/703, score 0.4842105, `−10.8281 [−21.8567,+0.1787]`,
995 clusters. Independent raw-JSONL audit 44 stored values, 0 issues, AUDIT
PASS; independent Elo-from-score −10.9753; seeded cluster bootstrap
`[−21.8526,+0.0000]`. Screen (`+2.6110 [−7.9556,+13.1825]`) and confirmation
CIs overlap; they were NEVER pooled per the frozen addendum.

Why failed: unsuitable hypothesis / search-eval interaction, NOT an
implementation defect. Making the quiescence delta decision more accurate
relative to actual capture gains still returns stand-pat values instead of
searched capture values, which changes upstream alpha-beta decisions and
ordering (profiling: +13.8 % fixed-depth nodes) and loses tactical accuracy.
Decision: frozen §5/addendum UCB `+0.1787 < +10` and point <= 0 -> CLOSE; no
ADVANCE (point < +20, LCB < 0, batchB < −5), no bundle, no retune of the
frozen `deltaMargin=200`, `MaxGainDelta` stays default OFF. ABANDONED. Next
action: continue ranked directions and independent audits; see
`docs/DEV6_CURRENT_STATUS.md`. No vague "optimization unsuccessful".

## exp-0043 launched — TT-evidence singular extension (2026-11-04)
After exp-0042 CLOSED/ABANDONED (screen `+2.6110 [−7.9556,+13.1825]`
INCONCLUSIVE, bounded confirmation `−10.8281 [−21.8567,+0.1787]` CLOSE, NEVER
pooled), the mission remains ACTIVE/NOT COMPLETE. The post-exp-0042 rank-1
direction is now executing WITHOUT re-running or modifying exp0042, reusing
confirmation data, bypassing preregistration or weakening gates.

Mechanism: `SearchParams::ttSingularExtension=false`; in `negamax` a
slightly-shallower TT LOWER bound >= beta + 50 cp at depth >= 3 marks the
always-first hash move singular, and that ONE move is searched a ply deeper.
`MaxSingularExtensions=2` is path-scoped via a counter restored on every
return; `SingularDepthSlack=3`. NO verification subtree (exp-0037 CLOSED at
`+3.7766 [−9.3368,+16.9008]`), NO stand-pat rewrite, NO new qsearch pruning
rule, NO default-ON feature disabled. The canonical genuine re-search variant
is DEFERRED and the deviation is DECLARED IN ADVANCE in the prereg.

Frozen before any evaluation game: `docs/DEV6_PREREG_EXP0043.md` (SHA
`e9fe40f053c9f479835c05efc3bf592547024090c1a315281ec727f0096f31dc`),
`tier1-plan-exp0043.json` (4 jobs), `scripts/dev6_exp0043_openings.py` and
1,400 fresh disjoint openings (seed `2026120201`, ZERO overlap with 32,041
earlier positions in 120 files, four disjoint slices), and dispatch
`mode=benchmark experiment_id=exp0043 attempt=13`. All committed in the SAME
commit as the dispatch. Default-off bit-exact signatures
`243f9a1c1ba5b36f` / `a14ab62224f837e5` / `e45fa2ec2287eb41`, Release ctest
11/11, ASan+UBSan ctest 11/11 (`exp0043_asan_ctest.log`), UCI default false.

MANDATORY pre-result mechanism-live/overhead diagnostic from the FROZEN
source (instrumented `SB_SINGULAR_DEBUG` build, real suite positions):
fixed depth 10 over 16 positions OFF 2,655,145 nodes ON 3,024,895 nodes
(+13.9 % overhead), 15,000 triggers / 8,072 extensions; FIXED TIME 40+4 ms
over 24 positions x 2 repeats OFF 222,636/217,259 nodes ON 218,959/225,368
nodes, median depth 6 both, 1,093/1,092 triggers and 548/516 extensions,
LIVE on 23/24 positions. A startpos `go depth 12` probe found 0 triggers;
suite positions are the preregistered probe. These are VALIDITY/overhead
checks, NOT strength evidence.

Design: FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, never `--nodes`;
Stage-0 validity null 400 games (0 forfeits required), candidate-options null
400 games, batchA/batchB 1,000 games each on independent fresh suites;
combined frozen before the run, independent raw-JSONL audit, 4 isolated VMs,
exact packaged tested binary. Frozen ADVANCE >= +20 point AND LCB > 0 AND
both batches >= −5 AND both null CIs include 0 AND 0 failures; CLOSE if
UCB < +10 OR point <= 0; INCONCLUSIVE -> ONE bounded fresh confirmation,
NEVER pooled. Gates 1 (+75/LCB>+50) and 4 remain UNMET; no strength claim,
no bundle, no default change, no PR/merge/tag/release/deploy/dev7.

## exp-0043 CLOSED / ABANDONED (2026-11-04)
Tier-1 run `41809643084` (4 isolated VMs SUCCESS), export `41810711486`
SUCCESS, CI `41809642415` SUCCESS on exact source
`5ea5ad21348f39dabad1da3e8cb098f798087295`. Frozen prereg
`e9fe40f053c9f479835c05efc3bf592547024090c1a315281ec727f0096f31dc`, plan
`3141fb1f487184459b52d644d3187f201dbd70216455469768613e0aebff2e70`,
packaged=tested binary
`c2ef506c5c6ebf9c3197c52903f61ccbf5326f16221c3c96a5bb3a8dc4420409`,
1,400 fresh disjoint openings seed `2026120201` (0 overlap / 32,041 earlier).
FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, no `--nodes`; one binary,
single switch `TTSingularExtension=true` vs `false`. All 4 bundles 9/9
SHA256SUMS OK, 0 failures.

Mandatory mechanism-live diagnostic: LIVE on 23/24 suite positions at the
exact 40+4 ms control (548/516 extensions across 24 positions x 2 repeats),
median depth 6 unchanged, +13.9 % fixed-depth-10 node overhead. VALID
negative, not an inert experiment.

Stage-0 validity null 399 games 128/129/142 `−13.1005 [−29.9568,+3.6943]`,
0 forfeits/illegal/UCI failures, CI includes 0 -> PASS. Candidate-options
null 400 games 145/123/132 `+11.2956 [−7.4505,+30.1078]`, includes 0.
batchA 997 games 333/302/362 `−9.7895 [−25.2667,+5.6489]`; batchB 997 games
321/325/351 `−10.8390 [−25.2969,+3.5814]`. FROZEN combined 1,994 games
654/627/713, score 0.4852056, `−10.3142 [−20.8915,+0.2440]`, 994 clusters,
independent Elo-from-score −10.2832, seeded cluster bootstrap
`[−20.6467,+0.1748]`. `dev6_exp0038_audit.py 41809643084 exp0043 20 10`
-> 44 stored values, 0 issues, AUDIT PASS.

FROZEN RULE: ADVANCE false (point < +20, LCB < 0, both batches < −5);
CLOSE true (UCB +0.2440 < +10 AND point <= 0). => CLOSE / ABANDONED. Not
INCONCLUSIVE, so no confirmation run and no fresh suites spent.
`TTSingularExtension` stays OFF; frozen constants NOT retuned; no bundle, no
strength claim, no default change, no PR/merge/tag/release/deploy/dev7.
Full report `docs/DEV6_EXP0043_REPORT.md`. Gates 1 and 4 remain UNMET;
mission ACTIVE / NOT COMPLETE; next hypothesis is being selected and launched.

## exp-0044 launched — SEE-losing-capture ordering (2026-11-04)
Post-exp-0043 re-ranking: exp-0041, exp-0042 and exp-0043 are three
consecutive fixed-time losses for mechanisms that change WHICH nodes are
searched or ADD a ply at non-PV nodes; exp-0036 (+21.52, shallow SEE-losing
capture PRUNING) and exp-0038 (+7.68, qsearch information reuse) remain the
only positive directions. Rank 1 is now move-ordering ACCURACY with ZERO added
per-node work.

Code inspection found a concrete deficiency: in `Search::score_moves` a
capture with SEE < 0 scores ~2,000,000, ABOVE killers (1,500,000),
countermoves (1,485,000) and every quiet history move (|h| <= 60,000), so
losing captures are searched immediately after winning captures at EVERY
main-search node. exp-0044 demotes them to the tail in the MAIN search ONLY.
NO move is removed (unlike exp-0036/0041), NO SEE/eval call is added, NO
stand-pat value or pruning/extension decision changes, quiescence excluded.
Frozen `BadCaptureOrderScore=-2000000`, threshold SEE<0, no tunable margin —
NOT best-of-N parameter selection, NOT a repeat of exp-0036/0041.

Frozen before any evaluation game: `docs/DEV6_PREREG_EXP0044.md` (SHA
`73ae460981a09bbf5d605205f8b77bf799b6d92a0fed4dc4abaa3a4ebc3820a5`),
`tier1-plan-exp0044.json` (4 jobs), `scripts/dev6_exp0044_openings.py` and
1,400 fresh disjoint openings (seed `2026120301`, ZERO overlap with 33,441
earlier positions in 125 files, four disjoint slices), dispatch
`mode=benchmark experiment_id=exp0044 attempt=15`. All in the SAME commit as
the dispatch. Default-off bit-exact signatures `243f9a1c1ba5b36f` /
`a14ab62224f837e5` / `e45fa2ec2287eb41`, Release ctest 11/11, ASan+UBSan
ctest 11/11 (`exp0044_asan_ctest.log`), UCI default false.

MANDATORY pre-result mechanism-live/overhead diagnostic from the FROZEN source
(`SB_BADCAP_DEBUG`): fixed depth 10 over 16 suite positions OFF 2,655,145
nodes, ON 2,961,866 nodes (+11.6 % TREE change, ZERO added per-node work),
424,155 demotions, live 16/16; FIXED TIME 40+4 ms over 24 positions x 2
repeats OFF 228,643/236,838 nodes, ON 203,245/214,462 nodes, median depth 6
for both, 22,024/24,413 demotions, LIVE 24/24. The node INCREASE is disclosed
as a risk and is NOT strength evidence.

Design: FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, never `--nodes`;
Stage-0 validity null 400 games, candidate-options null 400 games,
batchA/batchB 1,000 games each on independent fresh suites; ANY time
forfeit/illegal/engine failure in ANY job => INVALID MEASUREMENT. Frozen
ADVANCE >= +20 AND LCB > 0 AND both batches >= −5 AND both null CIs include 0
AND clean; CLOSE if UCB < +10 OR point <= 0; INCONCLUSIVE -> ONE bounded fresh
confirmation, NEVER pooled. Gates 1 (+75/LCB>+50) and 4 remain UNMET; no
strength claim, no bundle, no default change, no PR/merge/tag/release/deploy/
dev7, no reuse of closed exp0041/0042/0043 data.

## exp-0044 screen INCONCLUSIVE; bounded confirmation launched (2026-11-04)
Tier-1 run `41812595433` / export `41813751266` / CI `41812595476` SUCCESS on
exact source `2ae4e68fc882991c3484eede22a4622f713da5e2`; frozen prereg
`73ae460981a09bbf5d605205f8b77bf799b6d92a0fed4dc4abaa3a4ebc3820a5`; 4
isolated VMs, 9/9 SHA256SUMS OK in each of 4 bundles, 0
forfeits/illegal/engine failures. Stage-0 validity null 400 games 133/145/122
`+9.5569 [−6.6563,+25.8118]`; candidate-options null 400 games 138/124/138
`0.0000 [−17.9335,+17.9335]`; batchA 1,000 games 341/336/320
`+6.6419 [−8.1259,+21.4338]`; batchB 996 games 335/328/336
`0.0000 [−15.0949,+15.0949]`; FROZEN combined 1,996 games 676/664/656,
score 0.5050100, 996 clusters, `+3.3140 [−7.2389,+13.8730]`, independent
Elo-from-score +3.4814, seeded bootstrap `[−7.1520,+13.7861]`, 44/0 AUDIT
PASS. ADVANCE false (point<+20, LCB<0); CLOSE false (UCB +13.8730 >= +10,
point>0) => INCONCLUSIVE. Frozen §6 mandates exactly ONE bounded fresh
confirmation, NEVER pooled with the screen.

`docs/DEV6_PREREG_EXP0044_ADDENDUM.md` (SHA
`17d90a790697bb05de108d4b5fb5f7cf745fdb611899c5237c7ccce2b73af835`) freezes
the confirmation BEFORE any confirmation game: separate Tier-1 run, dispatch
`mode=benchmark experiment_id=exp0044_confirm attempt=17`, FIXED TIME 40+4 ms,
SAME single switch `BadCaptureOrdering=true` vs false, 1,400 fresh disjoint
openings seed `2026120401` (ZERO overlap with 34,841 earlier positions in 130
files), generator `scripts/dev6_exp0044_confirm_openings.py`, its own Stage-0
and candidate-options nulls, two independent 1,000-game batches. Decision uses
ONLY new batches: ADVANCE >= +20 AND LCB>0 AND clean; CLOSE if UCB<+10 OR
point<=0; otherwise CLOSED AS INCONCLUSIVE and direction abandoned
(conservative compute bound, NOT a threshold change). No strength claim, no
default change, no bundle, no retune, no pooling. Gates 1 and 4 remain UNMET;
mission ACTIVE / NOT COMPLETE.

## exp-0044 CLOSED AS INCONCLUSIVE / ABANDONED (2026-11-04)
Confirmation run `41814069967`, export attempt 18 `41815187170` FAILED only at
a transient GitHub Internal Server Error evidence push (download + checksums
succeeded; nothing reached remote). TECHNICAL FAILURE diagnosed and repaired
within scope: workflow export step gained a bounded 4-attempt push retry, and
the export was re-dispatched as NEW valid run `41815428066` SUCCESS. 9/9
SHA256SUMS OK in each of 4 bundles, 0 failures. No scientific change.

Confirmation source `0691b9affd36006425ac23605f4a0cc8922a55bb`, addendum
`17d90a790697bb05de108d4b5fb5f7cf745fdb611899c5237c7ccce2b73af835`, CI
`41814069925` SUCCESS. Stage-0 400 games 123/143/134
`−9.5569 [−32.6787,+13.4804]`; candidate null 398 games 142/123/133
`+6.1422 [−14.8210,+27.1502]`; batchA 999 games 360/328/311
`+17.0722 [+0.6984,+33.5222]`; batchB 998 games 339/348/311
`+10.1190 [−5.8209,+26.1015]`; FROZEN combined 1,997 games 699/676/622,
score 0.5192789, 997 clusters, `+13.5977 [+2.1746,+25.0503]`, independent
Elo-from-score +13.4030, seeded bootstrap `[+2.4394,+24.9592]`, 44/0 AUDIT
PASS, 0 forfeits/illegal/failures.

ADVANCE false (point < +20); CLOSE false (UCB >= +10, point > 0). The FROZEN
ADDENDUM explicitly overrides the prereg §6 "more samples" default with an
experiment-level COMPUTE BOUND => **CLOSED AS INCONCLUSIVE / ABANDONED**.
`scripts/dev6_exp0044_confirm_decision.py` reproduces the override from raw
games. Screen `+3.3140 [−7.2389,+13.8730]` and confirmation CIs overlap and
were **NEVER pooled**. No strength claim, no third run, no retune, no bundle,
no default change, no PR/merge/tag/release/deploy/dev7. Full report
`docs/DEV6_EXP0044_REPORT.md`. Gates 1 and 4 remain UNMET; mission ACTIVE /
NOT COMPLETE; the next hypothesis must have its OWN frozen prereg, fresh
disjoint suites and dispatch, and may not reuse exp-0044 data.

## exp-0045 launched — bit-exact dead evaluate() elimination (2026-11-04)
Post-exp-0044 rank change: exp-0044 CLOSED AS INCONCLUSIVE / ABANDONED at its
frozen addendum compute bound; the next ranked direction that changes NO
search decision is bit-exact evaluate() throughput. exp-0039 built this exact
fix, verified it bit-exact, measured ~2.9 % against a ~7 % local noise floor,
REVERTED it and spent NO games. exp-0045 is the FIRST Elo measurement of that
hypothesis on isolated VMs at FIXED TIME 40+4 ms — not a repeat of exp-0039's
profiling, not a parameter change, no exp-0041..0044 data reused.

Frozen before any evaluation game: `docs/DEV6_PREREG_EXP0045.md` (SHA
`0abf66836ed0ad6d979a26a3d4ca8616416bfb88b8ca069875f1e7d4e7bb2863`),
`tier1-plan-exp0045.json` (4 jobs), `scripts/dev6_exp0045_openings.py` and
1,400 fresh disjoint openings (seed `2026120501`, ZERO overlap with 36,241
earlier positions in 135 files, four disjoint slices), dispatch
`mode=benchmark experiment_id=exp0045 attempt=20`. All in the SAME commit as
the dispatch. Default-off bit-exact signatures `243f9a1c1ba5b36f` /
`a14ab62224f837e5` / `e45fa2ec2287eb41`, d16 with `ttEval=1` identical
OFF/ON, Release ctest 11/11, ASan+UBSan ctest 11/11
(`exp0045_asan_ctest.log`), UCI default false.

MANDATORY pre-result diagnostics from the FROZEN source (`SB_DEADEVAL_DEBUG`):
node counts OFF/ON IDENTICAL at depths 8/10/12 (depth 12 `[72604, 497628,
311669, 559024]` for both); ON skipped 40,187 of 379,656 evaluate() calls
(10.6 %) => mechanism LIVE; local 12 alternating repeats at depth 12 OFF
median 804.0 ms / ON 823.5 ms (−2.37 % "speedup", noise-dominated, reported
VERBATIM, NO local speedup claim). Theoretical speedup ~2-3 % because only
10.6 % of evaluations can be saved. Honest power statement: a 2,800-game
screen has ~13 Elo half-width and CANNOT resolve a +2-3 Elo effect; it is
powered for the +20 ADVANCE threshold and to rule out a material regression.
SINGLE-RUN compute bound closes exp-0045 AS INCONCLUSIVE if neither frozen
condition holds; no post-hoc sample increase, no confirmation.

Design: FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, never `--nodes`;
Stage-0 validity null 400 games, candidate-options null 400 games,
batchA/batchB 1,000 games each on independent fresh suites; ANY time
forfeit/illegal/engine failure => INVALID MEASUREMENT. Frozen ADVANCE >= +20
AND LCB>0 AND both batches >= −5 AND both null CIs include 0 AND clean; CLOSE
if UCB<+10 OR point<=0; otherwise CLOSED AS INCONCLUSIVE / ABANDONED. Gates 1
and 4 remain UNMET; no strength claim, no bundle, no default change, no
PR/merge/tag/release/deploy/dev7.

## exp-0045 original run INVALID MEASUREMENT; bounded valid retry launched (2026-11-04)
Run `41817228668` / export `41818409701` / CI `41817228408` SUCCESS on source
`e41a0b18b4e522f57196e2834c8937f8c55019e8`, frozen prereg `0abf66836ed0ad6d…`;
4 isolated VMs, 9/9 SHA256SUMS OK in each of 4 bundles, 44 stored values / 0
issues AUDIT PASS. But batchB `summary.json` has `time_forfeit=1`: game 272,
14.1 ms move at ply 118, `remaining_white_ms=-5.01`, long game, clock nearly
exhausted. FROZEN prereg §5 requires 0 forfeits in ANY job => **INVALID
MEASUREMENT**. ALL Elo/CIs/W-D-L/LLR and the generic audit's "CLOSE" label are
DISCARDED; `clean=False` is the correct signal; NO strength inference. Stage-0
validity null, candidate-options null, batchA and all illegal/engine_failure
counts were clean. Diagnosis: rare isolated-VM long-game clock outlier (1/998;
exp-0043/0044 had 0 forfeits at the same control), not a systematic mechanism
effect; it favoured the candidate and could not manufacture a positive. NO
repair to the frozen 40+4 ms control, clocks, binary, switch, time manager or
driver is authorised.

`docs/DEV6_PREREG_EXP0045_RETRY.md` (SHA
`2172063e22554df99064c54e0820b70db854e2339b0d5e87ccc321b6ca0bce60`) frozen
BEFORE any retry game: identical frozen science, NEW `exp0045_retry`, dispatch
`mode=benchmark attempt=22`, `tier1-plan-exp0045-retry.json`, NEW seeds, 1,400
fresh disjoint openings seed `2026120601` (ZERO overlap with 37,641 earlier
positions in 140 files, generator `scripts/dev6_exp0045_retry_openings.py`).
Invalid run `41817228668` NEVER pooled or reused. Frozen ADVANCE >= +20 AND
LCB>0 AND clean; CLOSE if UCB<+10 OR point<=0; otherwise CLOSED AS
INCONCLUSIVE. BOUNDED RETRY BUDGET: exactly one retry; a second forfeit closes
exp-0045 AS TECHNICALLY UNRESOLVABLE with no strength inference. No threshold
weakened (the zero-forfeit rule was ENFORCED). Gates 1 and 4 remain UNMET; no
strength claim, no default change, no bundle, no PR/merge/tag/release/deploy/
dev7. Mission ACTIVE / NOT COMPLETE.

## exp-0045 FINAL CLOSE / ABANDONED (2026-11-04)
Original run `41817228668` / export `41818409701` / CI `41817228408` SUCCESS but
INVALID MEASUREMENT (1 TIME_FORFEIT in batchB game 272, 14.1 ms move, ply 118,
`remaining_white_ms=-5.01`). Frozen prereg §5 zero-forfeit rule ENFORCED; ALL
Elo/CIs/W-D-L/LLR and the generic audit's "CLOSE" label DISCARDED, no strength
inference, `clean=False`. Diagnosed as a rare isolated-VM long-game clock
outlier; no repair to the frozen 40+4 ms control authorised.

One bounded valid retry (frozen `DEV6_PREREG_EXP0045_RETRY.md` SHA
`2172063e22554df9…`, attempt 22, 1,400 fresh disjoint openings seed
`2026120601`, ZERO overlap / 37,641 earlier positions in 140 files): run
`41818958001` / export `41821624068` / CI `41818958003` SUCCESS. Pinned source
`9fb2a58…`, dev5 baseline VERIFIED, built==packaged binary `b839fae82b54…`,
UCI `SkipDeadTTEval default false`. 9/9 SHA256SUMS OK in each of 4 bundles,
0 forfeits/illegal/failures in ALL four jobs, 44/0 AUDIT PASS `clean=True`.
Stage0 399 `118/155/126` −6.1113 [−23.3656,+11.1129]; candidate null 400
`152/111/137` +13.0349 [−6.3155,+32.4666]; batchA 994 `327/320/347`
−6.6823 [−19.7471,+6.3636]; batchB 999 `324/320/355`
−11.1440 [−24.5596,+2.2383]. FROZEN COMBINED batchA+batchB ONLY 1,993 games
`651/640/702`, score 0.4872052, 993 clusters,
−8.9240 [−18.2792,+0.4182], Elo-from-score −8.8927, bootstrap
[−18.2107,+0.1749]; both null CIs include 0, both batches < −5.
ADVANCE False; CLOSE True (UCB<+10 AND point<=0). Reproduced by
`scripts/dev6_exp0038_audit.py 41818958001 exp0045_retry 20 10` and
`scripts/dev6_exp0045_retry_decision.py`: VERDICT CLOSE (mechanism rejected /
abandoned; NO strength claim). No confirmation / third run / post-hoc sample
increase / pooling / retune / default change / bundle. Switch stays OFF. This
is NOT a proven strength regression (~13 Elo half-width). Gates 1 and 4 UNMET,
2 direction-supported, 3 PASS; mission ACTIVE / NOT COMPLETE; no strength
claim, no PR/merge/tag/release/deploy/dev7. Full report
`docs/DEV6_EXP0045_REPORT.md`; evidence
`benchmarks/exp-runs/tier1-export/run-41818958001/`.


## exp-0046 LAUNCHED — margin-adaptive null-move reduction (2026-11-04)
exp-0045 is CLOSED / ABANDONED (INVALID original run, ONE bounded valid retry
`41818958001` frozen combined `-8.9240 [-18.2792,+0.4182]` => CLOSE). New
ranked direction: shipped null-move verification uses a FIXED
`SB_NULLMOVE_R + depth/5` and discards the SIZE of `staticEval - beta` already
computed for the guard. exp-0046 makes ONLY that existing subtree shallower
when staticEval is far above beta, with ZERO added per-node work, no extra
ply, no constant retune of a closed switch and no earlier data reused.

Default-OFF switch `AdaptiveNullR` in `src/search/search.hpp/cpp`,
`src/uci/uci.cpp`, `src/utilities/bench.cpp`; frozen constants
`AdaptiveNullMarginDivisor=200`, `AdaptiveNullExtraCap=2` chosen BEFORE any
game from theory only. OFF bit-identical: default bench
`243f9a1c1ba5b36f`, d16 ttEval=1 `a14ab62224f837e5`, d12 params
`e45fa2ec2287eb41`; Release ctest 11/11, ASan+UBSan ctest 11/11
(`benchmarks/dev6-baseline/exp0046_asan_ctest.log`), UCI default false.

PRE-RESULT diagnostics (`scripts/dev6_exp0046_diag.py`, instrumented
`SB_ADAPTIVE_NULL_DEBUG` build, 24 REAL exp-0046 suite positions): FIXED DEPTH
10 OFF 4,311,394 nodes / ON 4,252,622 (−1.36 % tree change), 44,789 null
nodes, 4,133 changed, 4,721 extra plies, LIVE 23/24; 40 ms fixed-time PROBE
OFF 1,006,703 / ON 974,327 (−3.22 %), LIVE 22/24, median depth 8 both.
Diagnostics are liveness/overhead evidence ONLY, NOT strength; no local
speedup claim.

FROZEN BEFORE ANY exp-0046 GAME: `docs/DEV6_PREREG_EXP0046.md` SHA
`dda54084d2acffddcb7cd5d1134f8734858e9bf0c69d3ab2eb59d3aeab15dd61`, `benchmarks/exp-runs/tier1-plan-exp0046.json` SHA
`557d51fc07ad18eb828e94b2cb273e7225956ca4e6cd55b2279216fb8ebaa18a` (4 jobs), `scripts/dev6_exp0046_openings.py`, 1,400 fresh disjoint
openings seed `2026120701` (ZERO overlap with 39,041 earlier positions in
145 files, ZERO duplicates, four disjoint slices; SHAs in
`benchmarks/dev6-baseline/exp0046_suites.json`). Dispatch
`mode=benchmark experiment_id=exp0046 attempt=24`, `source_sha=HEAD`, all in
the SAME commit. FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, never
`--nodes`; champion options BOTH arms, A adds ONLY `AdaptiveNullR=true`;
Stage-0 control/control validity null, candidate-options null, batchA/batchB
1,000 games each; frozen combined = batchA+batchB ONLY; independent raw-JSONL
audit. ADVANCE >= +20 AND LCB>0 AND both batches >= −5 AND both null CIs
include 0 AND clean; CLOSE if UCB<+10 OR point<=0; otherwise CLOSED AS
INCONCLUSIVE (single-run compute bound). Validity gate enforces 0 forfeits /
illegal / UCI / engine failures in ANY job (exp-0045 lesson, NOT weakened);
at most ONE bounded valid retry. Gates 1 and 4 UNMET; no strength claim, no
default change, no retune, no bundle, no PR/merge/tag/release/deploy/dev7.
Mission ACTIVE / NOT COMPLETE; no result may terminate it.
