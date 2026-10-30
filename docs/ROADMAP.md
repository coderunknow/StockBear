# Roadmap

## v0.1.0-dev2 priorities

1. Expand independent move-generation/property tests, especially rare en-passant, promotion, repetition and malformed-history edge cases; reproduce any reported bug before fixing it.
2. Improve FIDE dead-position adjudication beyond the current material signatures, and make claim decisions less simplistic in search. Keep the GUI/referee responsible for actual claims.
3. Improve time management, search ordering, evaluation and performance using controlled ablations, fixed suites and substantially larger paired matches. Only add reductions/pruning after correctness and strength validation.
4. Improve tournament statistics, opening diversity and uncertainty estimates, including dependence between paired openings; publish complete methodology and failures.
5. Broaden compiler/platform coverage and automate reproducible signed release provenance if practical.

## Longer-term research (not implemented)

An evaluation interface and independent position/search code allow later experimentation with independently trained NNUE, transformer evaluation, policy-value networks, supervised learning, self-play, reinforcement learning, MCTS or alpha-beta/MCTS hybrids, distributed training, GPU inference, parameter optimization and evolutionary approaches. None is included in this development release. Training/data provenance, licenses, cost, testing and credible tournament evidence must precede any strength claim. Surpassing a leading engine is an aspirational research goal, not a result established by this release.
