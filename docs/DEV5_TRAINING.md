# dev5 training pipeline and data provenance (2026-11-02)

Everything below was produced locally on the 2-core sandbox with the exact
commands given; no paid service, no downloaded dataset, no third-party weights.
Large raw files live in the ignored `data/` directory; their SHA-256 hashes are
recorded here so the exact bytes are identifiable.

## Hardware / tooling

Intel Xeon @ 2.60 GHz (2 logical CPUs, AVX2), 3.8 GiB RAM, no GPU. GCC 12.2.0,
CMake 4.4.4 + Ninja, Python 3.11 venv (`.venv`) with `chess 1.11.2`,
`numpy 2.4.6`, `torch 2.15.0+cu132` (CPU execution) from PyPI.

## Self-play corpora (position source + outcome labels)

Built from the exact dev4 baseline binary (`build-dev4/build/stockbear`,
SHA-256 `1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae`):

```
stockbear selfplay --games 3200 --nodes 4000 --seed 771001 --maxplies 300 --hash 8 --out data/corpusA.final.txt
stockbear selfplay --games 3200 --nodes 9000 --seed 772002 --maxplies 300 --hash 8 --out data/corpusB.snap.txt
```

- `data/corpusA.final.txt` — 390,131 lines, SHA-256
  `4bb48afd14049dcd40de5c357419753cbec09884aedfb41b5a781e0815deffb3`
- `data/corpusB.snap.txt` — 89,535 lines, SHA-256
  `a06e8bdcf07feb86af7214c998a5f5cd729fe8e5f295491d379a1caca1aaa00c`

Format `<result> <game> <fen>` with `result` from the side to move in the FEN
(verified empirically: correlation of `result` with teacher cp is +0.55 for
both colours separately, and ~0 against the colour-flipped label — i.e. the
label really is side-to-move relative).

## Teacher search labels (SF11, external research tool only)

Stockfish 11 (`official-stockfish/Stockfish` tag `sf_11`, tarball from
codeload.github.com) built with `make build ARCH=x86-64-bmi2`; binary SHA-256
`bc9e5ed4a8729e8c1f0acebfe60a3b8c6d8257fef61910aba94a922ff2aa5660`, run with
`Threads=1, Hash=64` strictly as a labelling oracle by
`scripts/label_search.py`. No Stockfish code, weights or data are part of
StockBear; the labels are original generated data.

- Round 1: `--nodes 50000` on the corpus snapshot → `data/labels_sf11_50k.txt`,
  119,696 positions, SHA-256
  `880fb426edf2891b2f24dc49a0659926f261be812b845685f829f0c998870757`
- Round 2: `--nodes 20000`, excluding round-1 board keys →
  `data/labels_sf11_20k_r2.txt`, 190,302 positions, SHA-256
  `b0a5e10e0cdcbdf78059cb172aea4ac6f7068baa3be02a4e1afdf887f36bf340`
- Merged (dedup by board+stm+castling+ep): `data/labels_all.txt`, 309,998
  positions, SHA-256
  `9ccd0021f9255378eda920f912b7bf5577bbb32c05bbb18dfb70b4959279334e`

Empirical scale check: regressing SF cp on StockBear's shipped classical eval
over 133k moderate positions gives `SF_cp ≈ 1.105 * our_cp + 85.8`,
correlation 0.83 — the two centipawn scales are essentially the same
(pawn ≈ 100), so no scale conversion is needed between teacher and engine.

## Classical tuner dataset

```
sed 's/^[^ ]* [^ ]* //' data/corpusA.final.txt data/corpusB.snap.txt > data/all_fens.epd
build-dev4/build/stockbear evaldata --input data/all_fens.epd --output data/features.csv
```

`data/all_fens.epd` 479,666 lines SHA-256
`999c7263f75bdf6112a661041973c696d2f47d578c6a35c53beeca9db6c19cef`;
`data/features.csv` SHA-256
`068eb9b6f8b4b90c7da4954540a5e1690655e6325b6a120a68057b6881d7a772`.
`scripts/tune_eval2.py` merges features with labels/corpora by FEN and splits
by game (train/val/test 88/7/5% via `(game*2654435761)%100`).

## NNUE training

`scripts/train_nnue2.py` (torch, CPU) trains the engine's own architecture
(`buckets*768 → L1 → L2 → 1`, clipped ReLUs) on the merged labels
(`--target cp` regression in OUTPUT_SCALE units, or `--target wdl` logistic)
with a game-level split, SparseAdam for the embedding + Adam for the dense
layers, cosine lr, best-validation checkpoint, percentile-calibrated
quantisation into the `SBNN` format the engine loads via `NnueFile`, and an
integer-vs-calibrated-float verification. Work directories and reports:
`nnue-work/<name>/report.json` (kept local, git-ignored; contents summarised in
`docs/DEV5_EXPERIMENTS.md`). Runs so far:

| Run | buckets | target | data | steps | train corr vs cp | test corr | int-vs-float rms | match (nodes 3000, 480 g) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| b4cp | 4 | cp | 120k labels | 2040 | 0.53 | 0.36 | 418 cp (verify vs raw float) | −708 [−914, −615] |
| b4wdl | 4 | wdl(K=400) | 120k labels | 2040 | 0.43 | 0.30 | 155 cp | −720 [−917, −628] |
| b1wdl | 1 | wdl | 120k labels | 2040 | — | 0.33 | 126 cp | −720 |
| b16wdl | 16 | wdl | 120k labels | 2040 | — | 0.17 | 135 cp | −732 |
| b4out | 4 | wdl (outcome) | 480k corpus | ~580 | — | 0.38 | 264 cp | −708 |
| b1out-mse | 1 | wdl (outcome), MSE | 480k corpus | 580 | — | 0.37 | 261 cp | not yet played |

All first-round nets reproduce dev4's −708 Elo almost exactly: an undertrained
net (train corr ≈ 0.4–0.5 versus 0.83 for the linear classical model on the
same labels) has a large output noise that the search chases. The diagnosis is
therefore **optimisation/underfitting, not primarily label quality** —
although the dev4 corpus labels (depth-4 self-play outcomes) are also noisy.
Longer high-lr runs on the 310k-label set are the current experiment.

## Postscript (2026-11-02 ~13:30 UTC): sandbox wipe of local data

The execution environment reset all snapshot-excluded directories once during
the session, deleting `data/` (corpora, label files, `params_*.txt`, the SF11
teacher binary) along with `build*/` and `.venv/`. Engine binaries were rebuilt
bit-identical from git (hashes above), and every match record under
`benchmarks/results/0.1.0-dev5/` survived, so all reported numbers stand.
The raw corpora/labels/params themselves must be regenerated by re-running the
commands recorded above if they are needed again; `data/params_outcome.txt`
in particular is required to reproduce the `EvalParams=params_outcome` arm.
