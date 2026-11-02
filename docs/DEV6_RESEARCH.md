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
