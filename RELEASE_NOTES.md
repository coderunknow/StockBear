> **Development branch status (v0.1.0-dev6, unreleased).** The latest
> **published** prerelease is **v0.1.0-dev5**; its release notes are reproduced
> below. This branch's `VERSION` is `0.1.0-dev6`, which marks *development
> work only*: no dev6 tag, GitHub Release, prerelease or deployment has been
> created, and **no dev6 strength claim is made**. The DEV6 strength gate
> (>= +75 Elo with a two-sided opening-clustered 95% CI lower bound > +50 on
> two independent 6,600-game batches against the immutable dev5 artifact) is
> **not yet met**. The authoritative, current gate verdict and experiment
> inventory live in [`docs/DEV6_CURRENT_STATUS.md`](docs/DEV6_CURRENT_STATUS.md)
> and the append-only [`benchmarks/FAILURE_LEDGER.md`](benchmarks/FAILURE_LEDGER.md).
> The notes below describe the published dev5 release and are unchanged from
> the verified dev5 restoration.

---

# StockBear v0.1.0-dev5 — development prerelease

StockBear is an independent C++17 UCI chess engine. Board, legal move
generation, state management, alpha-beta search, evaluation, dead-position
analysis and the UCI controller are implemented in this repository; it
neither embeds nor calls another engine to select moves. This is an early
development release, not a stable or leading-strength engine.

## What this release is, and what it is not

dev5 is the first release with a **measured, pre-registered strength gain over
the previous release binary**. The gain comes from a tuned evaluation
parameter set plus one search option, both delivered as UCI options — the
default configuration of the binary is unchanged from dev4 (bench signature
`243f9a1c1ba5b36f`, `bench --depth 16` `a14ab62224f837e5`, ctest 11/11).

To play at the measured strength, send (the parameter file ships inside the
release archive):

```
setoption name EvalParams value params_abc.txt
setoption name TTEval value true
```

With exactly those options, this release measured against the pinned dev4
binary (`stockbear-dev4-1c5b61a7`, sha256
`1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae`):

| experiment | build | games | clustered 95 % CI | LCB95 |
|---|---|---|---|---|
| exp-0024 (release artifact) | portable `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4` | 6600 @ 40+4 ms | **+64.7 [+57.5, +72.0]** | **+57.5 > +50 ✓** |
| exp-0023 (native runner build, not shipped) | same + `-march=native` | 6600 @ 40+4 ms | +66.4 [+59.3, +73.6] | +59.3 > +50 ✓ |

Both were pre-registered (committed before the runs), run on fresh untouched
opening suites (exp0002 / exp0001, 2200 paired openings each, excluding all
prior suites), 12 shards x 550 games with distinct seeds, paired openings with
reversed colours, hash 16 MB, threads 1, on isolated GitHub-hosted runners,
with a 1100-game candidate-vs-candidate null (exp-0024: +1.3 [−8.0, +10.6],
exp-0023: −1.3 [−11.7, +9.2] — both consistent with zero). SPRT(0,5) accepted
H1 in both (LLR 28.96 / 30.74). Zero forfeits in exp-0023; exp-0024 had one
time forfeit BY THE BASELINE (counted as its loss per the pre-declared
symmetric policy). All 6600 games are accounted for in both experiments
(6585 adjudicated + 15 unadjudicated = 6600 for exp-0024; 6581 + 19 = 6600 for
exp-0023 — the pooled report's "18" was pair-level, one pair had both games
capped). Independent audits (`scripts/audit_exp0023.py`) recomputed both
experiments from the raw records without sharing code with the original
pooling and reproduced the pooled estimates to full double precision.

**The +64.7 Elo claim attaches to the shipped Linux x64 artifact + the two
options above.** It is NOT claimed for the Windows artifact (separate MSVC
build, same source and options, bench-identical search but not separately
strength-gated), and not for any other build flags.

## What is new in the source

- exp-0019: integer UCI options `AspirationWindow`, `FutilityMargin`,
  `RevFutilityMargin`, `DeltaMargin` (defaults are the dev4 values; changing
  them clears the TT). Screens showed no reliable gain over defaults, so the
  champion config uses defaults for these.
- exp-0022: four new evaluation features (`RookOn7th`, `KnightOutpost`,
  `BackwardPawn`, `PawnChain`) appended with shipped value 0 — the default
  build stays bit-identical (bench-pinned); the tuned `params_abc.txt` gives
  them non-zero values.
- Compile-time ablations (`STOCKBEAR_SAFE_MOBILITY`, `SB_INCREMENTAL_EVAL`,
  `SB_QEVAL_LITE`, `SB_SEE_CACHE`) are all OFF by default; the release build
  enables only `SB_SEE_CACHE=1` (a semantics-preserving reuse of the SEE
  result, bench-pinned) plus the x86-64-v3 ISA flags.
- Linux TT allocation asks for transparent huge pages (`madvise` hint only;
  contents and behaviour unchanged).
- `FullSoftBudget` UCI switch (default off) for the dev5 time-management
  experiment; off in the champion config.
- Tests: 11/11 ctest entries (unit, perft, UCI, dead positions, nnue,
  tournament harness, statistics, nnue_features differential).

## Verification

- CI on the exact release commit: Linux Debug/Release, Windows Debug/Release,
  Linux Clang Release, ASan+UBSan, ThreadSanitizer, minimum CMake 3.16,
  independent reference/statistics/dead-positions jobs — all green (see the
  CI run linked below; this document does not substitute for it).
- Clean local Release build of the release commit: ctest **11/11**, perft(6)
  119,060,324, `bench` signature `243f9a1c1ba5b36f`, `bench --depth 16`
  `a14ab62224f837e5`, UCI smoke (`uci`/`isready`/`go depth`/`bestmove`).
- The packaged Linux binary is additionally exercised by the post-publish
  verification job (uci handshake, version string, both bench signatures).

## Evidence

- [exp-0023 pre-registration](docs/EXP0023_PREREG.md) and
  [confirmation](docs/EXP0023_CONFIRMATION.md) — native-build gate +66.4
  [+59.3, +73.6].
- [exp-0024 pre-registration](docs/EXP0024_PREREG.md) and
  [confirmation](docs/EXP0024_CONFIRMATION.md) — **release-artifact gate
  +64.7 [+57.5, +72.0]**.
- [independent audit report](docs/EXP0023_AUDIT.md) and the machine-readable
  audits `benchmarks/exp-runs/exp0023-audit.json` / `exp0024-audit.json`
  (recomputed from raw records by `scripts/audit_exp0023.py`).
- Raw match records (PGN + JSONL + CSV + per-shard manifests):
  [exp-0023 shards](benchmarks/exp-runs/exp0023-shard01/),
  [exp-0023 null](benchmarks/exp-runs/exp0023-null/),
  [exp-0024 shards](benchmarks/exp-runs/exp0024-shard01/),
  [exp-0024 null](benchmarks/exp-runs/exp0024-null/); pooled estimates
  `exp0023-pooled.json` / `exp0024-pooled.json`.
- [append-only failure ledger](benchmarks/FAILURE_LEDGER.md) — every failed
  gate and screen (dev5 +15.9, dev6 +47.5, dev7 +39.9, NNUE −652..−760,
  option-off ablations, ...) is preserved with its raw records.
- [dev4 evidence report](benchmarks/results/0.1.0-dev4/REPORT.md) and
  [research docs](docs/).

## Compatibility

- Linux x64 artifact: requires **x86-64-v3** (POPCNT, BMI2, LZCNT — Intel
  Haswell 2013+ / AMD Excavator 2015+). It is NOT built with
  `-march=native` and runs on any such CPU; the exp-0024 +64.7 Elo was
  measured on exactly this build.
- Windows x64 artifact: MSVC build with `/arch:AVX2` (AVX2 required) and the
  same `SB_SEE_CACHE=1` define; same source and options, bench-identical
  search, but not separately strength-gated.
- Standard UCI: `uci`, `isready`, `ucinewgame`, `position`, `go`
  (depth/nodes/movetime/clocks/increments/movestogo/infinite/searchmoves),
  `stop`, `quit`, `debug`, `info` lines. Options: `Hash`, `MultiPV`,
  `EvalParams`, `NNUE`, `NnueFile`, the boolean search switches, the four
  integer margin options, `FullSoftBudget`. No `Threads` option: the search
  is single-threaded. Ponder, Chess960, opening book and tablebases are not
  implemented. The NNUE network is not embedded; `NNUE true` reports that it
  cannot be honoured (the measured network loses ~700 Elo to the classical
  evaluation and is not shipped as default — see the dev4 notes).

## Known limitations / deferred research

- exp-0020 (fresh-corpus retune, screen +80.2 [+55.4, +105.9] on the native
  build) is **unconfirmed future research**, not part of this release's
  claims.
- The strength numbers are at 40+4 ms per move on server CPUs; absolute Elo
  depends on hardware and time control.
- All experiments, including failures, are preserved under
  `benchmarks/exp-runs/` with their pre-registrations.
