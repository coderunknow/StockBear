# dev5 architecture research, interim

## Independently implemented candidates

### Pawn-safe classical mobility

Hypothesis: counting squares defended by enemy pawns as activity overvalues
unsafe piece placement. Existing material, PST, pawn structure, king safety,
search and all scalar coefficients are held constant. Only N/B/R/Q mobility
excludes enemy pawn attacks. Friendly occupancy remains excluded. It is not
legal mobility and does not account for pins or all enemy attacks.

Implemented in the production evaluator and the parameter-feature breakdown.
The optional CMake switch `STOCKBEAR_SAFE_MOBILITY=ON` creates the isolated
research build; default OFF preserves dev4 exactly. The independent published
constant evaluator test still tests unchanged dev2 behavior in normal builds.
In research builds its sole adjusted feature uses the pawn-attack table directly
as an oracle, rather than sharing the implementation's mobility-mask helper.
A focused unit test asserts Nd4 mobility 8 versus 7 when Pf7 controls e6.

The first candidate CTest exposed the expected historical evaluator equality
failure (41 versus 39 cp on Kiwipete). Rather than dropping the test, extended
the independent reference with the precisely isolated experimental feature.
Both default and research builds now pass all 11 CTest entries. No tests were
removed. This extension does not assert that safe mobility improves strength.

Fixed-node screening: +40.7 Elo [−9.3,+92.5], inconclusive. Experimental only.
No default promotion or version bump.

### King-conditioned piece-square features

Implemented vectorized training feature batches for the engine's existing
4/16/64 king buckets. Tested against scalar features for both STM orders,
all king squares and multiple pieces. This removes a research bottleneck only.
Trainer CLI/model sizing and converter still use the one-bucket model; end-to-end
bucketed training is **not** claimed as implemented.

This engine representation includes kings and absolute piece colors. It is
not traditional HalfKP. In particular, Black perspective mirrors ranks but does
not swap piece colors. That convention is internally consistent with the
existing model but does not exploit full color symmetry in shared embeddings.
Changing it requires a new format/feature identity, independently retrained
weights, loader compatibility policy, and complete differential tests. Never
reinterpret the old model in a newly normalized feature space.

## HalfKP investigation

Primary technical documentation inspected (algorithms only; no source/weights
copied into StockBear):

- official-stockfish/nnue-pytorch, commit
  `c625702757b58999611b006b5a03e3e1c5e142ea`,
  [NNUE principles and HalfKP](https://github.com/official-stockfish/nnue-pytorch/blob/c625702757b58999611b006b5a03e3e1c5e142ea/docs/nnue.md).
- [Architecture history at the same revision](https://github.com/official-stockfish/nnue-pytorch/blob/c625702757b58999611b006b5a03e3e1c5e142ea/docs/nnue_architecture_history.md).

Traditional HalfKP conditions each non-king piece-square feature on its own
perspective's king square: 64×10×64 = 40960 inputs. Each perspective must orient
squares and normalize piece allegiance consistently. Relevant king moves
require refreshing that perspective's accumulator. Ordinary moves need only
removed/added piece rows. At width 128, int16 first-layer storage alone would
be 10 MiB, versus 192 KiB for StockBear's 768×128 one-bucket embedding;
64-bucket StockBear's king-inclusive layout would be 12 MiB. Parameter storage
is a calculation, not measured memory residency or inference performance.

Not selected for production yet: no controlled training data/targets comparison
establishes that capacity is the current bottleneck. A 4-bucket pilot and a
symmetry-normalized smaller representation are lower-cost intermediate studies.
A HalfKP implementation must retain scalar reference and test king refresh,
castling, EP, captures, promotions, undo, scalar/AVX2 equivalence before kernels
are optimized. None of those future HalfKP implementation gates is claimed done.

## Selection status

Classical dev4 stays default. No new neural model trained. No neural, hybrid or
larger-network candidate has met a playing-strength gate. Research tooling is
not a substitute for measured strength per time.
