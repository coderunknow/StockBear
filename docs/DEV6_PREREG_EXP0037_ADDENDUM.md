# exp-0037 ADDENDUM — full frozen design (BEFORE any evaluation game)

This addendum supplies every field required by §6 of the mission directive.
`docs/DEV6_PREREG_EXP0037.md` remains the frozen primary prereg; **no frozen
threshold, margin, depth, tolerance or acceptance rule is changed here**. The
addendum only fills in previously unspecified identities/commands/sample
details and adds an explicit efficiency stopping rule. Written before ANY
exp-0037 evaluation game; `docs/DEV6_PREREG.md` §8 is unchanged.

## Hypothesis
At non-PV nodes with remaining depth >= 5, a reduced-depth
(`depth - 4`) null-window search at a raised beta (`beta + 200 cp`, both
frozen) predicts a full-depth fail-high. Cutting there saves the full move
loop; the saved nodes should buy depth at the 40+4 ms control and improve
playing strength. **This is NOT assumed true**: the pre-existing depth-12
diagnostic shows +63 % nodes (overhead dominates at shallow depth) while the
12-position depth-16 bench shows -7.96 % nodes (cutoffs pay off deeper).
The direction is executed to settle that conflict with an honest preregistered
measurement, not because it was preselected.

## Source / build / binary identity
- Source: the exact pinned commit containing this addendum. Its SHA is the
  `source_sha` workflow input and is recorded in every Tier-1
  `manifest.json` / `fingerprint.json`, in `AGENTS_LOG.md`, and in the
  dispatched-run record. CI runs on that same exact HEAD.
- `SearchParams::probCut` default **OFF**, UCI `ProbCut` check, `bench --param
  probCut=0|1`. Default-off build stays bit-identical: bench
  `243f9a1c1ba5b36f`, d16 `a14ab62224f837e5`, d12+params
  `e45fa2ec2287eb41` (3x deterministic).
- Pinned flags `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`, no
  `-march=native`, GCC 12.2.0-14 locally; Tier-1 builds on `ubuntu-latest`
  with the identical flags. Local binary `build-exp0037/stockbear`
  `95c31ab6d214928fe7c5cd68f3aa031abc9f926d29c90d639811ae249e61afb9`;
  the Tier-1 **packaged and extracted** binary is the one Gate 4 refers to.
- Baseline: immutable `benchmarks/binaries/stockbear-dev5-release`
  `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`,
  champion `EvalParams=research-data/params_abc.txt` + `TTEval=true`.
- Validation already passed BEFORE results: ctest 11/11 Release, 11/11
  ASan+UBSan, UCI integration/fuzz, perft, dead-position, determinism.

## Stage 1 — fixed-node screen (Tier 2, deterministic, cheap)
- ONE binary, single switch: candidate `ProbCut=true` vs the SAME binary
  `ProbCut=false`; zero toolchain/binary confound.
- `go nodes 6000` with `--nodes-jitter 0.15` (harness-seeded per game, so
  colour-reversed pairs are non-degenerate), hash 16, threads 1, max-plies 240.
- TWO independent fresh disjoint suites of 300 openings → 600 games each
  (1,200 games combined); plus a 200-opening / 400-game null
  (`ProbCut=true` vs `ProbCut=true`, bit-identical binaries).
- Suites are disjoint slices of `benchmarks/positions/openings_exp0037.txt`
  (seed `2026112001`, 1,820 openings, excluding every earlier suite);
  per-slice SHA-256 recorded. Colour-reversed, one pair per opening.
- Statistics: W/D/L, paired pentanomial, opening-clustered CR1/t two-sided 95 %
  CI, cluster bootstrap, LLR labelled a normal approximation; both batches
  reported separately AND combined; independent recomputation from raw JSONL.
- **Frozen ADVANCE rule (unchanged from the primary prereg)**: combined point
  >= +10 Elo AND combined 95 % LCB > -10 AND both batches >= -5 AND null CI
  includes 0 AND no correctness regression. Otherwise the direction is closed
  (rejected / deferred) and the mission continues to the next ranked direction.

## Stage 2a — Tier-1 fixed-time screen (only if Stage 1 ADVANCES)
- Runner: GitHub-hosted `ubuntu-latest` isolated VM per matrix job
  (`.github/workflows/dev6-tier1.yml`, `workflow_dispatch` only).
- Control: **FIXED TIME `--base-ms 40 --inc-ms 4`**, hash 16, threads 1,
  max-plies 240; `--nodes` NEVER used.
- Stage 0 validity gate: 400-game 40+4 ms null with bit-identical binaries,
  0 TIME_FORFEIT, 0 illegal/UCI failures, CI includes 0 — the same frozen gate
  as exp-0036.
- Two independent fresh disjoint suites of 500 openings → 1,000 games each;
  candidate `ProbCut=true` vs immutable official dev5; plus a 200-opening /
  400-game null. CR1 95 % CIs, both batches + combined.
- **Frozen futility boundary (efficiency, NOT a gate weakening)**: if the
  combined 95 % UCB < +50, Gate 1 is conclusively unmet and exp-0037 closes;
  the 3,300-pairs/batch Stage 2b is unnecessary. If combined point >= +55 AND
  UCB >= +50, Stage 2b (3,300 pairs per batch, ±5.2 Elo combined) is run on
  Tier-1 with unchanged Gates 1–4.
- Gate 4: the EXACT packaged candidate binary is extracted and used by
  `scripts/dev6_tier1_job.py`; source SHA → build → binary SHA → results → CI
  are pinned in `fingerprint.json` / `manifest.json` / `SHA256SUMS.txt`, and
  evidence is uploaded as an artifact and mirrored to git by the deliberate
  `mode=export` job (blob CDN contingency). CI runs on the exact source HEAD.

## Infrastructure smoke (DISCARDED, no strength inference)
A 20-opening / 40-game 40+4 ms null self-match (`ProbCut=false` vs
`ProbCut=false`) validates the Tier-1 workflow, packaging binary identity,
artifact upload, export/checksum verification and retrieval. Its games are
**discarded** and never used for any strength claim.

## Expected failure modes
Verification overhead dominates at the shallow depths reachable in 4 ms
(observed at depth 12) → node loss → regression; TT entries at reduced depth
perturb ordering; a 200 cp margin may be too loose for this eval scale;
isolated-VM clock jitter → forfeits (guarded by Stage 0). None of these
justify changing the frozen margin/depth after results.

## Non-claims / integrity
Fixed-node Stage 1 is NEVER presented as fixed-time strength. No absolute Elo,
no gap-to-3000. No post-hoc combination of experiments, no favourable-batch
selection, no threshold changes after results, no default change to
`ProbCut` before gate satisfaction, no PR/merge/tag/release/deploy/dev7.
