# Design log (append-only)

## 2026-10-30 — independent engine baseline

- The repository initially contained only the Apache-2.0 license. Keep that license; implement the engine rather than importing an existing engine.
- Use a mailbox plus per-type/per-color bitboards, generated magic slider tables, owned per-ply state and reversible incremental updates. Detect legality by checks/pins and post-en-passant king safety. Preserve raw FEN EP separately from legally relevant EP in repetition keys.
- Use single-threaded iterative-deepening alpha-beta/PVS and quiescence before considering speculative pruning. Check extensions are capped. Context-sensitive TT tags include the known reversible path, rule-50 count, root boundary and extension budget; this is conservative for draw correctness and intentionally sacrifices some cross-path TT hits.
- Choose independently derived, tapered handcrafted features rather than a fake or untrained neural-network claim. Do not add NNUE/MCTS/training scaffolding without implementation and evidence.
- Keep UCI input on the main thread and one search on a joinable worker. Stop is atomic; every state-changing command joins first. Bound time/node/hash usage and preserve a legal root fallback.
- Distinguish claimable versus automatic draw status, including intended-move claims. Search deliberately assumes claims and treats internal cycles as draws; the GUI/referee owns actual game adjudication. Recognize common dead-material signatures but document that arbitrary blocked dead positions are not fully solved.
- Make the C++ executable self-contained apart from OS runtime libraries; Python and python-chess are optional development tools. Keep external opponents outside the repository and do not use them for engine search.
- Record perft/search/match methodology and actual results under the versioned benchmark directory. Perft uses leaf bulk counting, so its NPS must not be compared to search NPS.
