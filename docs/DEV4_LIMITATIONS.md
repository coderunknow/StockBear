# StockBear dev4 — limitations

Everything here is a limitation of what dev4 *is*, not a list of things that were
merely left undone. Where a limitation could be mistaken for a result, the
distinction is stated explicitly.

## 1. Strength

* **dev4 is not measurably stronger than dev3.** The default configuration is
  dev3's configuration: every feature added in dev4 is off by default, and the
  depth-6/depth-7 benchmark signatures are byte-identical to dev3's. The
  regression match at fixed nodes reproduced the same-binary null control
  *exactly*, i.e. bit-identical play. This is a "no regression" result, not an
  improvement, and it must be read as such.
* Every candidate that was measured came out neutral or negative
  (`DEV4_BENCHMARKS.md` §4). None of them was shipped on.
* The learned evaluation is **much weaker** than the classical one at the node
  budgets measured (−708 Elo, 95 % CI [−1011, −405]). It is available behind an
  option and is not the default. It is not a "close call" that might have gone
  the other way with more games.

## 2. Measurement

* **Time control.** The fixed-time condition is 40 ms + 4 ms per move. That is
  far faster than tournament play, and it was chosen because a 1 s/move match
  would take roughly ten times the wall clock on a single core. Results at 40 ms
  are not guaranteed to transfer to longer controls; they are the only ones
  measured.
* **Interval width.** A single 400-game fixed-node experiment resolves about
  ±35 Elo (95 %), and a 160-game fixed-time experiment about ±65 Elo. A genuine
  +20 Elo effect would be invisible in either. Nothing in this release claims to
  detect effects that small.
* **Harness noise, including false positives.** Identical engines do not score
  exactly 0.500 through this harness: the fixed-node null control measured
  −12.3 [−34.2, +9.5] and the fixed-time null −30.5 [−65.9, +4.3]. Worse, the
  dev3-vs-dev4 fixed-time comparison — two builds that produce *identical node
  counts* and identical play at fixed nodes — measured +29.0 [+1.5, +56.9], a
  lower bound above zero for a difference that cannot exist. A single fixed-time
  match can therefore produce a confident-looking result from scheduling noise
  alone; the fixed-time numbers in this release are labelled inconclusive for
  that reason, and only differences that also appear at fixed nodes (or that are
  far larger than ~65 Elo) are treated as real.
* **No opponent other than itself.** There is no Stockfish in this environment
  (the dev2-era builds do not satisfy dev4's independence and provenance rules
  for *this* release's evidence, and the dev3 attempt to build Stockfish 19
  failed), so all dev4 evidence is self-play between StockBear builds. That is
  the right control for an A/B change and the wrong tool for estimating absolute
  strength.
* **Adjudication.** Games end on real rules only (checkmate, stalemate,
  repetition, 50-move, insufficient material) or on a real clock loss. No resign
  or score-based adjudication is used, so a match that ends early does so because
  a game ended.

## 3. Learned evaluation

* **No king buckets.** The shipped format supports 1/4/16/64 buckets and the
  engine refreshes both perspectives when a king moves, but the trainer only
  builds single-bucket batches. The network therefore has no king-relative
  knowledge.
* **Small network, small data.** 768→128→32 trained on 3.07 M positions from a
  depth-4 engine. Validation MSE 0.147 against a 0.207 constant-predictor
  baseline is a weak evaluator, and the playing-strength measurement reflects it.
* **Noisy labels.** Targets are game results, which are a very high-variance
  signal for a mid-game position. See `DEV4_TRAINING.md` §8 for what to do
  instead.
* **Training time.** 8.5 minutes of CPU training on one core. This is a budget
  limitation, not a claim that longer training would not help; the validation
  curve had not flattened.

## 4. Engine

* **Single-threaded.** No SMP. A `Threads` option is not advertised, because
  multi-threaded search is not implemented and advertising it would be a feature
  claim the binary cannot honour.
* **No endgame tablebases, no opening book.** Both are deliberate: a book hides
  search weakness and tablebases add a large data set with its own licence and
  provenance burden for a gain invisible at these match lengths.
* **No 50-move / progress awareness in the search** (inherited from dev3). The
  evaluation does not know how close a position is to a draw by the fifty-move
  rule.
* **Very low node counts are weak.** At 6,000 nodes the engine still makes
  obvious positional errors; the depth-6 analysis positions in
  `benchmarks/` show it (a retreat to `b1a3` scored +457 cp in a developed
  middlegame).
* **Evaluation scale is a fixed constant.** One network output unit is worth
  300 cp; that mapping is a modelling choice, not a tuned parameter.

## 5. Platform and verification

* **Binaries are built by CI, not by hand, for Windows.** The Linux x64 binary is
  built and tested here; the Windows x64 binary is produced by the GitHub Actions
  packaging job and its tests are the ones CI runs. It has not been executed on a
  Windows machine by the author of this release, and the report says so rather
  than claiming hands-on Windows verification.
* **Sanitiser and cross-compiler configurations are CI-only.** The local sandbox
  has one compiler (GCC 12.2.0) and cannot run the ASan/UBSan/TSan, clang or
  Windows matrix; those results come from CI and are linked, not reproduced.
* **Memory.** The sandbox has 3 GB of RAM; training with a 3 M-position corpus
  peaks near 1.5 GB. Larger corpora would need a different batching strategy.

## 6. Documentation and audit

* The dev3 release notes said the `unit` group had 37 tests; the source has 39 at
  that tag (and 46 after dev4 adds `test_nnue.cpp`). The number came from a
  hand-written count. It is corrected here and in `RELEASE_NOTES.md`, and
  `docs/TESTING.md` now states the count as a property of the tree rather than of
  a document.
* dev3's report described an untested evaluation candidate as a match loss; dev4's
  documentation distinguishes "not tested" from "tested and lost" everywhere, and
  the dev3 report is annotated rather than rewritten.
* Any figure from dev3 that could be mistaken for a dev4 result is either
  re-measured here or explicitly labelled as a dev3 number.
