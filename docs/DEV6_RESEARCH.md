# dev6 research log — continuing the +50 Elo gate cycle (branch arena/daa69a3b-stockbear)

Status: **IN PROGRESS — +50 ELO GATE NOT MET** (dev5 confirmation ended at
+15.9 [+0.6, +31.2]; see docs/DEV5_REPORT.md). Baseline stays the immutable dev4
tag binary `1c5b61a755215134...` (bench `243f9a1c1ba5b36f`). All decisive fixed-time
matches run alone on the 2-core sandbox (no concurrent compute); fixed-node
screens are deterministic and may run contended. Raw records:
`benchmarks/results/0.1.0-dev6/`. New local data lives in `research-data/`
(deliberately NOT gitignored so sandbox cleanups cannot delete it; only
manifests/hashes get committed).

## Candidate dashboard

| ID | Source | Binary | Hypothesis | n3000 screen | n8000 screen | 40+4 clean | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C0 dev4 | tag v0.1.0-dev4 | 1c5b61a7... | baseline | — | — | — | reference |
| mo-* | build-dev5 + UCI switch | be234145... | dev3 ordering switches help at bullet | ch +36.3[+5.8,+67.5]; others ≤+9 | ch −1.5[−22.4,+19.4] | ch −17.5[−39.6,+4.5]; ch+cap −3.6[−25.8,+18.5] | reject |
| nullr2 | vbuild-nullr2 (-DSB_NULLMOVE_R=2) | | less null-move reduction helps at shallow depth | **+33.4 [+5.6,+61.6]** | −22.6 [−45.8,+0.5] | pending | investigate at 40+4 |
| nullr1/nullr0 | vbuild-* | | even less nullmove | −14.5 / +2.9 | — | — | reject |
| fut80/fut60 | vbuild-* | | stronger futility | +20.3 / +4.3 | fut80 −2.9 | — | reject |
| lmr0/bank/delta350 | vbuild-* | | less LMR / bank time / wider delta | +10.1 / +10.1 / −18.8 | — | — | reject |
| outcome-v2 | retuned EvalParams (research-data) | build-dev5 + option | outcome-label tuning on 885k-position corpus | pending | pending | pending | pending |

## Environment notes

- 2026-11-02 ~13:30 UTC the sandbox wiped gitignored dirs (`build*/`, `.venv/`,
  `data/`) once; binaries rebuilt bit-identical, `data/` lost (dev5 audit in
  docs/DEV5_AUDIT.md). New data goes to non-ignored `research-data/`.
- Search knobs are now compile-time overridable in src/search/search.cpp
  (`SB_NULLMOVE_R`, `SB_FUTILITY_MARGIN`, `SB_REV_FUTILITY_MARGIN`, `SB_LMR_BASE`,
  `SB_DELTA_MARGIN`, `SB_EARLY_STABLE`, `SB_EARLY_PERMILLE`, `SB_CLOCK_PERMILLE`);
  defaults reproduce dev4 exactly (default build hash unchanged be234145...,
  bench 243f9a1c1ba5b36f, CTest 11/11).
- Variant builds live in `vbuild-<name>/` (not gitignored, survive cleanups).

## Pipeline state (2026-11-02)

- `research-data/corpusA.txt` (563,289 positions, dev4 selfplay --games 4600
  --nodes 4000 --seed 881001) and `research-data/corpusB.txt` (--games 2500
  --nodes 9000 --seed 882002) — outcome labels `<result> <game> <fen>`.
- Next: `sed 's/^[^ ]* [^ ]* //' research-data/corpus*.txt > research-data/all_fens.epd`,
  `build-dev4/build/stockbear evaldata --input research-data/all_fens.epd --output research-data/features.csv`,
  then `scripts/tune_eval2.py --target outcome` with both corpora as `--corpus`.

## dev6 segment 2 update (2026-11-02, NPS-first diagnosis)

- **Breakthrough diagnostic**: clean 40+4, 479 g, seed 20261271 — dev4 vs
  dev4-seeing-half-clock (`research-data/wrap05.sh`): **+89.9 [+65.9,+114.7]
  clustered, SPRT LLR 3.22 accept H1** ⇒ at 40+4, 2x nodes ~= +90 Elo. NPS is
  the dominant lever. (2x-clock direction is INVALID: harness drains the real
  40 ms clock -> forfeits.)
- gprof per-node cost: eval/features ~25-30% (king-danger ~18% of node time,
  mobility ~9% by nps.sh ablation), TT probe ~14%, make/unmake+check-info
  ~13.6%, negamax self 7.4%, SEE ~5.7%, movegen 5.4%, score_moves 4.6%.
- Harness clock model (scripts/tournament.py:322-376): clocks start at 40 ms,
  `clock -= elapsed; if <0 forfeit; clock += 4`. Steady-state per-move budget
  is the 4 ms increment; the 40 ms is a one-time buffer. FullSoftBudget (use
  whole soft slice every move) was already rejected in dev5 (-21.0 clean) via
  forfeit risk. So: more nodes must come from NPS, not from time.
- Experiments this segment (all clean 40+4 480 g alone unless noted):
  - qlite+seec (SB_QEVAL_LITE=1: qsearch stand-pat skips mobility+king-danger;
    SB_SEE_CACHE=1: reuse score_moves SEE in qsearch loop, bench-identical):
    nps +23% at depth 16 BUT **-32.1 [-55.8,-8.6]** (seed 20261281) -> qsearch
    eval quality (king danger/mobility in stand-pat) is critical. REJECTED.
  - seec alone: bench 243f9a1c1ba5b36f (bit-identical), nps ~neutral. kept as
    free no-op.
  - PGO (-fprofile-generate trained on nps.sh d8-20 + 48 selfplay games at
    40+4, then -fprofile-use -mtune=native, vbuild-pgo): nodes identical at
    d16 (19229509), nps ~neutral. REJECTED (lookup/cache-bound code).
  - TT entry packed 32B / bucket 64B = one cache line (vbuild-tt32, rule50
    clamped to 16 bits; bench 243f9a1c1ba5b36f; depth-16 nodes changed
    19.2M->27.2M because bucket count changed -> different collisions):
    nps ~neutral. No-op, kept available.
  - TTEval=true: +12.5 [-11.2,+36.4] (seed 20261272) — inconclusive.
  - nullr2 clean: -2.2 [-25.3,+21.0] (seed 20261261).
- IN FLIGHT: six UCI option-flip screens at clean 40+4 (NullMove/LMR/
  Aspiration/CheckExtension/IIR/SEEPruning=false, seeds 20261290-95) —
  "less work per node => more depth at fixed time" plays.
- Remaining NPS plan (bit-exact only): incremental eval (target eval 27%->~8%
  of node time, must keep bench 243f9a1c1ba5b36f and ctest 11/11), make/unmake
  micro-opts. Gate math: need point >= ~+58 at 4400 g for LCB95>+50.

## MAJOR NPS FINDING: popcount is a libgcc CALL in release builds

`src/chess/bitboard.hpp` uses `__builtin_popcountll` but the Release build is
plain `-O3` (no `-mpopcnt`), so every popcount compiles to `call
__popcountdi2` (57 call sites in the dev4 binary, objdump-verified). popcount
is used in mobility, king-danger, pawn structure, movegen... Candidate fix:
build with `-mpopcnt -mbmi2 -mlzcnt` (ubiquitous since 2013; sandbox Xeon has
them). Semantics unchanged -> bench must stay 243f9a1c1ba5b36f. To be measured
(after the in-flight option screens finish, to keep them clean):
vbuild-popcnt, nps.sh depth 16/20 vs dev4.

## dev6 segment 3 (2026-11-02): popcnt + outcome-v2 params

- Option-flip screens at clean 40+4 480 g (all vs dev4, alone): NullMove=false
  -28.4 [-52.0,-5.1]; LMR=false -68.9 [-92.1,-46.4]; Aspiration=false
  -83.4 [-107.6,-59.9]; CheckExtension=false -31.5 [-55.2,-8.1];
  IIR=false 0.0 [-23.3,+23.3]; SEEPruning=false -71.8 [-97.1,-47.2].
  => every pruning/extension switch is load-bearing at 40+4; "disable work
  for NPS" is DEAD. Only bit-exact speedups count.
- **popcnt build** (`-mpopcnt -mbmi2 -mlzcnt`; release was plain -O3 so every
  popcount was a `call __popcountdi2`, 57 call sites): vbuild-nps1 =
  popcnt+seec, bench 243f9a1c1ba5b36f, depth-16 nodes identical 19229509,
  ctest 11/11, nps +12-20% (2.24-2.46M vs 1.94-2.15M).
  Clean 40+4 screen (seed 20261300): **+3.6 [-19.6,+26.9]** — small NPS gains
  move Elo only weakly at 40+4.
- THP madvise on TT (vbuild-thp): bench/nodes identical, nps neutral -> dropped.
- PGO: neutral -> dropped. TT 32B packing: changes bucket count -> node counts
  change at depth 16 -> reverted to keep candidate bit-exact.
- qlite (skip mobility+king-danger in qsearch stand-pat): nps +23% but
  **-32.1 [-55.8,-8.6]** -> eval quality in qsearch is critical; dead.
- Outcome retunes on the 885k corpus: v2 (K=600) ... v6 (K=600-700), all
  val ~0.503-0.505 test ~0.470-0.472, mutually similar.
  **nps1 + params_outcome_v2, clean 40+4 480 g seed 20261311:
  +48.5 [+24.0,+73.5] clustered** (478 g) — the big dev6 result so far.
  (v2 alone was -26.1 at n3000: fixed-node screens misleading again.)
- In flight: nps1+outv2+TTEval (seed 20261321), nps1+outv3 (seed 20261322).
- Pre-registered confirmation suite ready: openings_dev6_confirmation.txt
  sha256 99682ada... seed 2026110206, 2200 pairs, committed in f443472 BEFORE
  any dev6 candidate ran on it. Plan: champion commit (binary sha) then
  4400 g alone, gate LCB95 > +50.

## Sandbox reset incident (2026-11-03 ~03:0x UTC) + recovery

- Mid-confirmation the sandbox was reset: local branch back at 7969f8b,
  `.venv/`, `build*/`, `vbuild-*/`, `/tmp` and untracked research-data corpora
  (corpusA/B/C, features CSVs) wiped. All dev6 work was already pushed
  (2d571ce), so `git reset --hard origin/arena/daa69a3b-stockbear` restored it.
- Recovery: `.venv` recreated (pip cmake ninja chess numpy), `git fetch
  --unshallow origin && git fetch origin --tags`, dev4 baseline rebuilt from
  tag `v0.1.0-dev4` in a worktree -> sha256 1c5b61a7... bit-identical, bench
  243f9a1c1ba5b36f; build-dev6 rebuilt with the pinned command -> sha256
  15f1daa0... bit-identical to the pre-registered champion, bench identical,
  depth-16 nodes 19229509, ctest 11/11.
- Found+fixed: the tt32 revert had only been committed for the .cpp, not the
  .hpp (frankenstein 32B entry at 2d571ce); 27ba7d4 restores the original
  TTEntry layout so the tree matches the pinned binary exactly.
- Confirmation re-run from scratch via committed `scripts/dev6_confirmation_run.sh`
  (null 1100 g seed 2026110208, then candidate 4400 g seed 2026110207, alone).
- Param-set triage at clean 40+4 480 g (dev4 openings, nps1+params+TTEval=true):
  outv2: +58.0/+30.7/+30.0/+28.3/+58.7 (mean +41.2); abc: +41.6/+54.7 (mean +48.2);
  bullet-b1: +40.7/+24.0 (mean +32.4); outv2 without tteval: +48.5.
  Champion selected: build-dev6 + params_abc + TTEval=true.

## dev6 CONFIRMATION RESULT (pre-registered, untouched suite) — GATE FAILED

- Null (build-dev6 vs itself, 1100 g, seed 2026110208, dev6 suite): **-3.5
  [-17.3, +10.2]**, 4 unadjudicated, no forfeits — clean.
- Candidate (build-dev6 sha 15f1daa0 + params_abc sha 8a9dc81f + TTEval=true)
  vs dev4 (sha 1c5b61a7), **4400 g, seed 2026110207, 40+4, hash 16, 1 thread,
  max-plies 240, run alone** on openings_dev6_confirmation.txt
  (sha 99682ada..., 2200 pairs):
  **clustered Elo +47.5 [+39.5, +55.6]** (t=1.980 on 2188 df), paired +47.5
  [+39.6, +55.5], SPRT LLR 14.07 accept H1. 4389 adjudicated (11 unadjudicated
  max-plies), W+D+L = 1854+1276+1259, 3 TIME_FORFEITs (baseline side, 12.7/19.5/
  28.6 ms stall moves), no crashes. Raw: benchmarks/results/0.1.0-dev6/
  confirm-{null,champ}-time40_4.*
- **GATE: LCB95 = +39.5, NOT strictly > +50 -> NOT MET. No PR.**
- Note: engine paths in the run were the byte-identical backups
  /home/user/bin-backup/stockbear-{dev4,dev6} because the sandbox wiper kept
  deleting build*/ between null and candidate; sha256 match the
  pre-registered values exactly.
- Champion composition: -mpopcnt/-mbmi2/-mlzcnt + SB_SEE_CACHE (bit-exact,
  bench 243f9a1c1ba5b36f, d16 nodes 19229509, ctest 11/11) + outcome-tuned
  EvalParams (params_abc, 1.1M-position corpus) + TTEval=true.

## dev7 CONFIRMATION RESULT (pre-registered dev7 suite) — GATE FAILED again

- Null (champ vs itself, 1100 g, seed 2026110308, dev7 suite 98208a6e):
  **-4.1 [-18.2, +9.9]**, 3 unadjudicated, clean.
- Candidate (build-dev6 sha 15f1daa0 + params_outcome_v6 sha 8b9a421e +
  TTEval=true + HistoryMaluses=false) vs dev4 (1c5b61a7), 4400 g, seed
  2026110309, 40+4, hash 16, 1 thread, alone:
  **clustered +39.9 [+31.9, +47.9]** (t=1.980 on 2175 df), paired +39.9
  [+31.9, +47.8], SPRT LLR 11.65. 4376 adjudicated, 24 unadjudicated.
  Raw: benchmarks/results/0.1.0-dev7/confirm-*.  **LCB +31.9 <= +50: GATE NOT
  MET, no PR.**
- Confirmed values so far: dev6 suite abc+tteval +47.5 [+39.5,+55.6];
  dev7 suite v6+tteval+hmoff +39.9 [+31.9,+47.9]. Screen maxima (+55.6) were
  selection noise; the champion family truly sits at +40..+48 point.
- Switch ablations at 40+4 (v6+tteval baseline +50.3 pooled): all default-on
  switches are >= their off value except HistoryMaluses-off (+54.0/+57.2,
  but confirmed lower). Futility-off -2.2, ReverseFutility-off +28.4,
  CounterMoves-off +31.3, ContinuationHistory-off +32.8, CaptureHistory-off
  +35.7, LMRHistory-off +47.7, Improving-off +27.7.
- Remaining lever: bit-exact NPS via incremental eval (popcnt gave x1.12 NPS
  -> +3.6 [-19.6,+26.9], consistent with the +90/doubling slope within noise;
  x1.2-1.25 could add +15-30).
