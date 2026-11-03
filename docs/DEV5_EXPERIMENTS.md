# dev5 experiment log (2026-11-02, in progress)

All matches are paired, colour-reversed games on the 240-opening dev4 suite
(`benchmarks/positions/openings_dev4.txt`), hash 16 MiB, one thread, 240-ply
cap, per-move node jitter 12% (fixed-node runs) so the pentanomial has variance.
Elo intervals quoted are the opening-clustered (CR1, Student-t) two-sided 95%
intervals from `scripts/match_stats.py`. Raw JSONL/PGN records live in
`benchmarks/results/0.1.0-dev5/`.

Baselines: exact dev4 tag `v0.1.0-dev4` = `9b5778c9`, Release build SHA-256
`1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae`
(reproduced this session; bench depth-4 signature `243f9a1c1ba5b36f` matches).
Current-branch default build (`build-dev5/stockbear`, SHA-256
`2a9f388f...`) is behaviour-identical to dev4 (CTest 11/11; sanity match
40 games at nodes 3000: −61 [−120, −6], small-sample noise between two
identical engines).

## Fixed-node screens, nodes=3000, jitter 12%

| Arm (engine A option) | Games | W-D-L | Elo [95% CI] | Verdict |
| --- | --- | --- | --- | --- |
| null (dev4 vs dev4, seed 20261103) | 240 | 89-66-85 | +5.8 [−24.1, +35.8] | null OK |
| `IIR=true` | 240 | 90-59-91 | −1.4 [−32.1, +29.2] | reject (retest of dev4) |
| `ModernLMR=true` | 240 | 81-73-86 | −7.2 [−39.0, +24.4] | reject |
| `MoveCountPruning=true` | 240 | 79-58-103 | −34.9 [−70.1, −0.3] | reject (regression) |
| `Improving=true` | 240 | 88-68-84 | +5.8 [−26.3, +38.0] | reject |
| `TTEval=true` | 240 | 92-56-92 | +0.0 [−32.4, +32.4] | reject |
| `EvalParams=params_cp` (LS distillation of SF labels; buggy interleaved export) | 480 | 88-95-294 | −159.0 [−190.2, −130.1] | reject (tuner bug found & fixed) |
| `EvalParams=params_outcome` (fixed tuner) | 480 | 159-132-187 | −21.9 [−47.1, +3.0] | superseded |
| `EvalParams=params_blend` | 480 | 170-155-155 | +10.9 [−13.1, +34.9] | inconclusive |
| `EvalParams=params_search` | 480 | 158-142-179 | −14.5 [−39.8, +10.5] | inconclusive |
| `EvalParams=params_cp` (fixed tuner) | 480 | 162-114-203 | −30.6 [−57.0, −4.5] | reject |
| `EvalParams=params_outcome` (fixed tuner) | 480 | 190-147-142 | **+35.0 [+12.0, +58.3]** | keep (screening) |
| `EvalParams=params_outcome` (fixed tuner) | 960 | 380-267-312 | **+25.1 [+5.7, +44.6]** | confirmed >0, below gate |

The four tuner targets (`cp`, `outcome`, `blend`, `search`) were produced by
`scripts/tune_eval2.py` from 479,666 self-play positions (dev4 binary, seeds
771001@4k nodes and 772002@9k nodes; corpora SHA-256 in
`benchmarks/results/0.1.0-dev5/README.md` and `docs/DEV5_TRAINING.md`) with
119,696 SF11 search labels (`nodes 50000`, teacher SHA-256
`bc9e5ed4...a922ff2aa5660`). Game-level split (train/val/test 88/7/5% by game
hash). Result: outcome-label Texel tuning is the only classical arm that beats
dev4; distilling raw SF centipawns into the 32-feature linear model regresses
(−30 Elo), consistent with dev3's finding that this feature set saturates.

## NNUE training (scripts/train_nnue2.py, torch, CPU)

See `docs/DEV5_TRAINING.md` for the data pipeline and per-run reports under
`nnue-work/` (kept local; hashes and configs in the reports). First-round nets
(buckets 1/4/16, wdl or cp targets, 40 epochs @ batch 2048) underfit: train-set
correlation with teacher cp ≈ 0.43 versus 0.83 for the linear classical model,
so they are not yet candidates. Longer/higher-lr runs and a second label round
are in progress at the time of writing.

## NNUE final verdict (rounds 2-3, output-scale sweep) — REJECTED for dev5

Best net b4cp3 (310k SF11 labels, buckets 4, L1 128, wd 3e-4, 100 epochs;
val corr 0.487, `nnue-work/b4cp3/net.nnue` SHA-256 6b5aec3d...) loses at every
depth and every output scale tried: n3000 −651.9 [−800.9,−571.2],
n8000 −719.7 [−917.0,−628.2], n50000 3-1-116 of 120; re-quantized output-scale
sweep at n8000: scale 285.71 (teacher slope) −651.9, scale 150 −759.1
[−624.9,−], scale 75 −759.1 [−624.9,−] (240 g each, seed 20261117; nets
`net-scaled.nnue` b8bc49d7..., `net-s150.nnue` 73d0c180..., `net-s75.nnue`
5585bc29...). Diagnosis, all checks done:

- Engine inference is **bit-exact** vs the python integer evaluator on 4 FENs
  (KQ-vs-K w −596 / mirrored b −1087 / startpos +815 / +162) — no sign, bucket
  or accumulator bug. The committed dev4 net itself evaluates both sides of
  KQ-vs-K as losing.
- On 910 positions sampled from real 40+4 games, b4cp3's eval correlates with
  the game outcome only 0.473 (classical 0.646) and has Brier score 0.205 vs
  classical 0.099; its output std on label positions is 1127 cp vs classical
  470 cp. A depth-8 trace shows it playing +570..+1182 cp "winning" moves in
  equal positions and getting mated. The trained nets are simply a weaker
  evaluator than the hand-tuned classical one in actual play; shrinking the
  output scale does not fix the correlation. NNUE is abandoned for this cycle.

## Fixed-time 40+4 ms screens (2026-11-02, second half)

Harness lesson recorded: any concurrent command on the 2-core sandbox during a
fixed-time match injects ~±25 Elo of common-mode noise (polluted runs: null
−30.5 [−52.4,−8.8], slot probe +15.9 [−14.0,+46.1] on identical binaries). Only
the **clean** runs below (match alone, no other local compute) are used for
decisions. dev5 binary be2341455d59c92c... (branch + FullSoftBudget switch,
default off; bench signature unchanged 243f9a1c1ba5b36f), dev4
1c5b61a755215134..., dev4 opening suite, hash 16, threads 1, 240 plies.

| Candidate (engine A vs dev4) | Games/seed | WDL | Elo, clustered 95% CI | Note |
| --- | --- | --- | --- | --- |
| null (dev5 vs dev5) | 480 / 20261127 | 141-156-183+ | +13.9 [−9.3, +37.2] | clean control, includes 0 |
| `EvalParams=params_outcome` | 480 / 20261128 | 183-127-170 | +9.4 [−13.9, +32.9] | best fixed-node candidate; ~0 at fixed time |
| `EvalParams=params_outcome` + `FullSoftBudget=true` | 480 / 20261129 | 155-141-184 | −21.0 [−44.4, +2.1] | FullSoftBudget rejected at 40+4 |
| safe-mobility build (728909b) | 480 / 20261130 | 168-147-164 | +2.2 [−21.0, +25.3] | pre-registered candidate; ~0 at fixed time |

Per-move search at 40+4 ms measured directly: mean ≈ 7.0k nodes (range 3.7k-12.5k,
depth 3-7); soft budget ≈ 4 ms, hard ≈ 13 ms. Fixed-node screens (+25 at n3000,
+60.7 at n8000, +29.9 at n20000 for params_outcome) do **not** transfer to fixed
time 40+4 (≈ +9 clean) — time-management early stops, per-move clock overhead
and node-count variance dilute the fixed-node gain.

## FullSoftBudget experiment (implemented, rejected)

`SearchParams::fullSoftBudget` + UCI option `FullSoftBudget` (default false;
src/search/search.cpp, search.hpp, uci/uci.cpp). When on, the search skips the
`stable>=6 & >550 permille` and `>700 permille` early soft stops and always uses
the whole soft budget. Fixed-node behavior is unchanged (bench signature
243f9a1c1ba5b36f; CTest 11/11 on the rebuilt binary). Clean 40+4 screen above:
−21.0 vs +9.4 without — at 40+4 the soft slice is only ~4 ms and spending all
of it every move costs more (clock pressure in long games) than the extra nodes
gain. Kept in the tree as a default-off ablation switch, documented here.

## Pre-registered confirmation, 40+4 ms, untouched suite (RUN, gate FAILED)

Per docs/DEV5_CONFIRMATION.md: openings_dev5_confirmation.txt (SHA-256
75824edb...), shuffle/tournament seed 2026110205, 1100 games per match, 40+4 ms,
hash 16 MiB, 1 thread, max 240 plies, run alone, null first then candidate.
Raw records: `benchmarks/results/0.1.0-dev5/confirm-{null,safe}-time40_4.*`.

| Match | Games (adjudicated) | WDL | Elo, opening-clustered 95% CI |
| --- | --- | --- | --- |
| null: safe vs safe | 1100 (1098) | 401-313-384 | +5.4 [−9.8, +20.6] |
| candidate: safe vs dev4 | 1100 (1098) | 413-321-364 | **+15.9 [+0.6, +31.2]** |

Gate: two-sided 95% CI lower bound strictly > +50 Elo → **+0.6, NOT MET**.
Pentanomial paired interval [+0.9, +30.9]; 2 unadjudicated (240-ply cap) games
per match; no forfeits. The pre-registered candidate is a small, statistically
marginal improvement at 40+4 ms — far below the +50 gate — so the dev5 hard
gate FAILS and no PR is opened.

## Environment incident (2026-11-02, ~13:30 UTC)

The sandbox reset every snapshot-excluded directory (`build*/`, `.venv/`, and
the gitignored `data/`) mid-session, killing one match at game 381/480. All
three engine binaries were rebuilt **bit-identical** to the pinned SHA-256
(dev4 1c5b61a7..., dev5 be234145..., safe 13d3a684...; bench 243f9a1c1ba5b36f;
CTest 11/11), so every recorded match remains valid. `data/` (self-play
corpora, SF11 label files, `params_*.txt` including `params_outcome.txt`,
teacher binary) was local-only; its SHA-256 provenance is recorded in
docs/DEV5_TRAINING.md and benchmarks/results/0.1.0-dev5/README.md, but the
files themselves (notably `data/params_outcome.txt`) are not recoverable
without re-running the whole pipeline. Consequence: runtime-loaded
`EvalParams` candidates cannot be re-measured or shipped from this workspace
as-is; the pre-registered confirmation therefore used the compile-time
safe-mobility candidate, which needs no data files.
