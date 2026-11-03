# exp-0025 — pre-registration: immutable dev5 baseline provenance

Committed before the baseline-verification run. This is a provenance step, not
a strength experiment; it establishes the comparison target for the whole
`v0.1.0-dev6` cycle.

## Hypothesis / purpose

The `v0.1.0-dev6` acceptance gate compares the candidate to the **exact released
`v0.1.0-dev5` artifact**, not to dev4 and not to a locally rebuilt approximation.
Before any dev6 strength measurement we must obtain, verify and pin that exact
executable and confirm its champion runtime configuration matches the published
strength claim.

## Immutable target

- Annotated tag `v0.1.0-dev5` resolves to commit
  `c94571313a1667048468cf6d4e070400dc5ab228` (tag object `ae8a6dffa6c6d2845006bd265b23bed3179ec6da`).
- Official release assets (immutable, published 2026-11-03):
  - `SHA256SUMS.txt` (asset 705317890)
  - `stockbear-0.1.0-dev5-linux-x64.tar.gz` (asset 705317899)
  - `stockbear-0.1.0-dev5-windows-x64.zip` (asset 705317895)
- Published portable build flags:
  `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4` (x86-64-v3, no `-march=native`).
- Champion runtime: `EvalParams=research-data/params_abc.txt`, `TTEval=true`.
- Published strength claim (vs dev4): exp-0024 portable artifact
  **+64.7 [+57.5, +72.0]**, 6600 games @ 40+4 ms, hash 16 MB, 1 thread,
  null +1.3 [−8.0, +10.6]. Sources: `docs/EXP0024_PREREG.md`,
  `docs/EXP0024_CONFIRMATION.md`, `benchmarks/exp-runs/exp0024-audit.json`.

## Method

1. A free GitHub-hosted `ubuntu-latest` runner (the sandbox cannot reach the
   release-asset CDN) downloads all three official release assets.
2. `sha256sum -c SHA256SUMS.txt` verifies both archives against the published
   checksums. A mismatch invalidates the run (INFRASTRUCTURE FAILURE).
3. The Linux executable is extracted, pinned to
   `benchmarks/binaries/stockbear-dev5-release`, and its SHA-256 recorded.
4. Integrity checks: `bench` signature must equal `243f9a1c1ba5b36f`,
   `bench --depth 16` must equal `a14ab62224f837e5`, UCI `id name` recorded.
5. The `params_abc.txt` shipped inside the archive is captured and its SHA-256
   compared with `research-data/params_abc.txt` (the champion file used in
   exp-0024, SHA-256 `8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be`).
6. All evidence is committed to the branch under `benchmarks/dev6-baseline/`
   and `benchmarks/exp-runs/exp0025-baseline/` so it survives sandbox resets.

## Frozen decisions

- The dev5 binary is never rebuilt, moved, or replaced during dev6.
- All decisive dev6 strength comparisons use this exact binary at champion
  runtime options; screens that use a bench-identical local reproduction are
  labelled as such and are never used as gate evidence.
- No dev4-based measurement can satisfy the dev6 gate. The historical
  exp-0016/exp-0017 ("dev6"/"dev7" labels on branch
  `arena/daa69a3b-stockbear`) measured against dev4 during the dev5 cycle and
  are retained only as historical context.

## Success / failure criteria for THIS step

- SUCCESS: all three assets checksum-match; both bench signatures match; the
  exact executable SHA-256 and shipped/repo param SHA-256 are recorded and
  committed; provenance manifest is machine-readable.
- INFRASTRUCTURE FAILURE: any download, checksum, or bench mismatch. In that
  case the dev6 gate cannot be evaluated and the incident is recorded in the
  Failure Ledger.
