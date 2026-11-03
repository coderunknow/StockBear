# exp-0030 — Reproducible build environment and Track A / Track B measurement integrity

**Pre-registered BEFORE any measurement below is collected.** Purpose: resolve the
previous cycle's unresolved Gate-4 issue — the `params_abc` integrity control
measured +33.0 [+13.7,+52.5] Elo because the released dev5 artifact and the
candidate were built in *different toolchain images* (ubuntu-22.04 release vs
ubuntu-latest/GCC 13 lane). Gate 4 of `docs/DEV6_PREREG.md` requires "no
unexplained difference between benchmarked and packaged binary", so NO new
strength experiment may run until this is controlled. This experiment builds a
fully reproducible comparison environment and measures fixed-node and
fixed-time performance of both source trees under ONE pinned toolchain.

This is an integrity/measurement experiment, NOT a strength claim. It does not
weaken or redefine any dev6 gate. The dev6 strength gates remain exactly those
in `docs/DEV6_PREREG.md` §8 (Gate 1: combined point >= +75 AND two-sided
opening-clustered 95% CI lower bound strictly > +50, both batches positive and
consistent; Gate 2: two independent datasets; Gate 3: nulls include 0;
Gate 4: no unresolved correctness/protocol issue and no unexplained
benchmarked-vs-packaged difference; exact candidate artifact tested).

## 1. Frozen identities

- Starting repo SHA `6e7c2e02881faf93a84990a8345c41ad28bcae11` (= verified
  `origin/main` at audit time). Branch `arena/3e6dd5b6-stockbear`.
- `v0.1.0-dev5` tag object `ae8a6dffa6c6d2845006bd265b23bed3179ec6da` -> commit
  `c94571313a1667048468cf6d4e070400dc5ab228`. Tag/artifacts untouched.
- **Track A1 (dev5 source)**: `git archive v0.1.0-dev5` extracted to a clean
  out-of-tree directory. Archive SHA-256 and file count recorded.
- **Track A2 (candidate source)**: `git archive <this HEAD>` (the tree that
  contains the exp-0026 extended-feature code, shipped values 0 so the default
  build is bit-exact). Archive SHA-256 and exact HEAD SHA recorded.
- **Track B (official artifact)**: `benchmarks/binaries/stockbear-dev5-release`
  SHA-256 `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`,
  extracted from the official dev5 release archives verified against the
  published `SHA256SUMS.txt`. Never rebuilt, never substituted, never renamed.
  It is a separate reference track; a rebuilt dev5 is NEVER described as the
  official release binary.

## 2. Pinned, recorded environment (chosen a priori)

Recorded by `scripts/dev6_build_matrix.py` into
`benchmarks/dev6-baseline/build_matrix.json`:

- OS/kernel, CPU model, CPU ISA availability, vCPU count, RAM, glibc.
- Exact compiler (`gcc --version`), linker (`ld --version`), CMake, Ninja.
- Exact CMake configure line and build target; LTO setting (`-flto=4`).
- Compiler/linker flags: `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4`
  (the portable release recipe; NO `-march=native`), `CMAKE_BUILD_TYPE=Release`.
- Runtime: hash 16 MB, threads 1, `--max-plies 240`, 40+4 ms for fixed-time
  matches, champion `EvalParams=research-data/params_abc.txt` (SHA
  `8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be`) +
  `TTEval=true` where a match is played.
- Executable SHA-256 of every built/official binary; source archive SHAs.

Both Track A source trees are built with the SAME compiler, linker, flags,
CMake version, LTO, build type and target, on the SAME machine, sequentially
(no concurrent CPU work during builds or measurements).

## 3. Pre-registered equivalence & integrity criteria (frozen; no post-hoc tolerances)

- **E1 — fixed-node signatures.** `stockbear bench` (default depth) and
  `stockbear bench --depth 16` signatures must be identical for all three
  binaries and equal to the dev5 release values `243f9a1c1ba5b36f` and
  `a14ab62224f837e5`. Also `bench --depth 12 --params <params_abc>` signatures
  must match between A1 and A2.
- **E2 — fixed-node full-output equivalence.** The complete `bench --depth 12`
  CSV rows (columns `name,bestmove,depth,score_type,score,nodes,hashfull,pv,fen`,
  i.e. EXCLUDING the timing columns `time_us,nps`) must be byte-identical
  between A1 (dev5 rebuilt) and A2 (candidate rebuilt), with default params AND
  with `params_abc`. This is the mechanistic definition of "bit-exact search".
- **E3 — fixed-time throughput equivalence.** Aggregate NPS
  (sum(nodes)/sum(time_us) over the full `bench --depth 12` CSV; minimum
  wall-time of 3 runs per binary) for A2/A1 must lie in **[0.97, 1.03]**.
  The ±3% tolerance is fixed BEFORE measuring: a <3% NPS difference cannot
  plausibly produce a +33 Elo fixed-time gap at 40+4 ms, whereas a larger
  difference would be a real toolchain/code-layout effect requiring diagnosis.
  The official Track B artifact's NPS is reported on the same machine as a
  reference only (it was built by a different image, so it is NOT held to the
  ±3% criterion).
- **E4 — fixed-time control match (corroboration).** A2 (`params_abc`+TTEval)
  vs A1 (`params_abc`+TTEval), >= 400 paired colour-reversed games, 40+4 ms,
  hash 16, 1 thread, fresh opening slice, opening-clustered CR1 two-sided 95%
  CI must INCLUDE 0. This is deliberately underpowered for small effects (<~15
  Elo) and is used only to detect a large systematic offset like the previous
  +33; it does not replace E1–E3. All game events recorded per
  `docs/DEV6_PREREG.md` §4.
- **E5 — decision.** If E1, E2 and E3 all pass, Track A is declared a valid,
  controlled SOURCE-LEVEL comparison environment and the previous +33 Elo
  control is attributed to the build-image mismatch (classified INVALID
  MEASUREMENT for that control only). E4 must not show a significant non-zero
  bias; if it does, diagnose before proceeding. If E1/E2/E3 fail, do NOT start
  any strength experiment; diagnose (compiler, flags, source drift) and repeat
  under a NEW experiment ID. Track B remains a separate, separately reported
  official-artifact reference.

## 4. What this experiment does NOT do

It does not claim any Elo improvement, does not retune parameters, does not
restore the exp-0026 feature bundle, and does not change the dev6 gates or the
baseline. It establishes the measurement foundation (M0.1) required before
exp-0031+ (external ladder, M0.2) and any later strength hypothesis.

## 5. Raw evidence

`benchmarks/dev6-baseline/build_matrix.json`, the build logs and full bench CSVs
under `benchmarks/exp-runs/exp0030-build-integrity/`, and (for E4) its
`match.jsonl` / PGN / CSV. Report: `docs/DEV6_EXP0030_BUILD_INTEGRITY.md`.
Failure Ledger: appended exp-0030 entry.
