# dev5 execution record and prospective protocol

Status: **research in progress; not release-ready**. Date: 2026-11-02 UTC.
No dev5 strength claim, version bump, tag or release is authorized by the evidence collected so far.

## Verified starting point

Canonical repository: `https://github.com/coderunknow/StockBear`, default branch
`main`, remote head `9ee214096bfe4edde553b46211bc64f0db67e528` at audit.
Working branch: `arena/4dcf45ca-stockbear`. Working tree initially clean.
Exact dev4 annotated tag resolves to `9b5778c97ba3d3141ea61fbf3398b7fc231bbf64`,
matching PR #6's merge commit. Current main adds PR #7's publication verification
record; it is not the dev4 merge commit. Published latest prerelease was dev4.
Outstanding PR #2 is a separate draft and was left untouched.
No AGENTS.md was found. DESIGN_LOG.md and AGENTS_LOG.md were inspected; history
is preserved. Existing architecture, training, benchmarking, CI and release
records were inspected, not replaced.

## Resources and baseline

Sandbox: Intel Xeon @ 2.60 GHz, x86-64, two logical CPUs sharing one physical
core, AVX2 present, approximately 3.8 GiB RAM, no detected NVIDIA utility/GPU.
GCC 12.2.0. Initially no CMake or chess Python package. Installed CMake 4.4.4,
Ninja 1.13.2, chess 1.11.2 and NumPy 2.4.6 in ignored `.venv` using PyPI.
No paid resources, remote jobs or quota-consuming training requested. Available
Actions quotas were not established, so no large CI experiment is assumed free.
Existing CI specifies Linux Ubuntu 22.04 and Windows 2022, Debug and Release.
Clang and Windows execution have not been performed in this sandbox.

The exact tag was extracted with `git archive` into ignored `build-dev4/source`
without changing branches. Release build is `build-dev4/bin/stockbear`.
Default evaluator remains classical, network=none, selected kernel=avx2,
single-threaded. Baseline CTest: 11/11 passed. Depth-6 signature:
`e06c4352681ae8eb`, matching dev4. Reproduction evidence is under
`benchmarks/results/0.1.0-dev5/`.

## Exploratory experiments (not final confirmation)

Preselected 120 games per arm: same-binary null, existing IIR=true, explicitly
loaded recorded dev4 NNUE, and isolated pawn-safe mobility. Fixed nodes=3000,
±12% per-move jitter, seed=20261102, 16 MiB requested hash, existing 240-opening
suite, paired color swaps, 240-ply cap. These are screening samples, not powered
confirmation. Report every arm, including regressions and incomplete games.
No default promotion based on screening. No fixed-time interpretation of
fixed-node measurements. Builds and parallel fixed-node matches may contend;
wall-time/NPS from these runs is not a valid latency comparison.

## Confirmation design, not yet run

Freeze one candidate, use previously untouched independently generated opening
clusters, fixed sample size and paired colors. No peeking/stopping for significance.
At score p=logistic(50 Elo)=0.57146, worst-case independent pair fractional-score
variance 0.25, two-sided alpha=.05 and 90% power, a normal planning approximation
requires ceil((1.96+1.2816)^2 * .25 / (.57146-.5)^2) ≈ 515 clusters,
1030 games. Budget at least 1100 games on independent clusters, plus an actual
same-configuration null control, and revise upward **before confirmation** if
pilot variance/design effects require it. This is an assumption-based planning
calculation, not guaranteed power under dependent opening families or censoring.
Use family-aware opening clustering, not just differently named transpositions.
Run fixed time as primary, fixed nodes as diagnostic; include >=1 s/move when
feasible. Existing 240 openings alone cannot supply 550 independent clusters.

Candidates screened on the same data require selection/multiple-comparison
caution; reserve confirmation clusters and never tune against them. Retain
pentanomial and opening-clustered intervals. Positive estimate with CI crossing
zero is inconclusive. Report target reached only with appropriate confirmation,
not because an estimate rounds above +50 or +100.

## Remaining gates

Training corpus regeneration and leak-free partitions; controlled search-label,
outcome-label and blended training over multiple seeds; latency and memory
profiling; fixed-time/null studies; pinned external Stockfish benchmark; full
sanitizers, compilers and platform QA; exact-head independent review and CI;
PR/merge/tag/package/publication verification. None are implied by this plan.
Do not release while these gates remain incomplete.
