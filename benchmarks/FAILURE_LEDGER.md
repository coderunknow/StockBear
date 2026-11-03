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
