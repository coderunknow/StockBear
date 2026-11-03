# dev5 experiment records (working directory)

Raw records of every dev5 experiment, kept next to the reports. Regenerate any
match with the command stored in the `config` block of its JSONL summary line.

Fixed-node screens (240 games, nodes=3000, jitter 12%, seed 20261102/3, dev4
240-opening suite, hash 16 MiB, 1 thread) are robust to CPU contention because
the node budget is deterministic; fixed-time matches must run alone on an idle
machine.

| File | Experiment |
| --- | --- |
| `sanity-dev5-vs-dev4-n3000.*` | current-branch default build vs exact dev4 tag binary, 40 games (harness sanity) |
| `screen-n3000-null.*` | same-binary null control, seed 20261103 |
| `screen-n3000-{IIR,ModernLMR,MoveCountPruning,Improving,TTEval}.*` | isolated dev4 search switches retested at nodes 3000 |
| `confirm-*` | pre-registered fixed-time confirmation on the untouched 550-family suite (added when run) |

Training-data provenance (all local, hashes in `docs/DEV5_TRAINING.md`):
`data/corpusA.snap.txt`, `data/corpusB.snap.txt` — deterministic `stockbear
selfplay` corpora from the dev4 binary (seeds 771001 @ nodes 4000, 772002 @
nodes 9000); `data/labels_sf11_50k.txt` — SF11 (`sf_11`, binary SHA-256
`bc9e5ed4a8729e8c1f0acebfe60a3b8c6d8257fef61910aba94a922ff2aa5660`,
Threads=1, Hash=64) fixed-node-50000 search labels, produced by
`scripts/label_search.py` (teacher used as an external research tool only).
The large raw corpora stay in the ignored `data/` directory; their SHA-256
and exact regeneration commands are recorded in the docs.

Later additions (2026-11-02 second half): fixed-node NNUE screens
(`screen-n{3000,8000}-nnue-*`, `screen-n{3000,8000,20000}-eval-*`,
`screen-n3000-safe-plus-outcome`, `screen-n8000-null`, `deep-n{50000,200000}-b4cp3scaled`,
`sweep-n8000-s{150,75}`), clean fixed-time 40+4 ms screens
(`clean-time40p4-*.{pgn,jsonl,csv}` — run with no other local compute; earlier
`screen-time40p4-*` runs had concurrent load and ±25 Elo common-mode noise),
and the pre-registered confirmation `confirm-{null,safe}-time40_4.*`
(openings_dev5_confirmation.txt SHA-256 75824edb..., seed 2026110205,
1100 games per match: null +5.4 [−9.8,+20.6], candidate +15.9 [+0.6,+31.2]
opening-clustered; gate lower bound > +50 NOT met).

Note: the sandbox wiped `build*/`, `.venv/` and the gitignored `data/` once;
binaries were rebuilt bit-identical (hashes in docs/DEV5_EXPERIMENTS.md),
but `data/params_*.txt` and the raw corpora are gone — see
`docs/DEV5_EXPERIMENTS.md` "Environment incident".
