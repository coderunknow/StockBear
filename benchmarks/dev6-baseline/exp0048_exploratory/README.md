# EXPLORATORY ONLY — not a preregistered result

`EXPLORATORY_CEILING.json` was produced by
`scripts/dev6_exp0048_exploratory_ceiling.py` AFTER exp-0048 was closed as a
negative result. It answers one engineering question: does an expressive
per-square table carry any real outcome signal, or was the whole mechanism
empty?

**Answer: the mechanism carries signal.** Held-out log-loss reduction on the
CLOSED exp-0048 corpus, by L2 weight (600 Adam iterations, lr 5.0):

| L2 | holdout reduction | RMS delta (cp) | max delta (cp) |
|---|---|---|---|
| 0 | **4.4721 %** | 276.8 | 1371.4 |
| 1e-8 | 1.6495 % | 21.4 | 81.5 |
| 1e-7 | 0.7088 % | 5.5 | 26.6 |
| 1e-6 | 0.1735 % | 0.98 | 8.4 |
| **1e-5 (frozen exp-0048)** | **0.0202 %** | **0.124** | **1.22** |

The frozen exp-0048 value sits at the degenerate end: its optimum is the
initialisation. That is the root cause of the negative result, now confirmed
quantitatively rather than merely estimated.

## Hard limits on the use of this file

- These numbers are **exploratory hypothesis generation**. They may NOT
  activate exp-0047, fill any Activation Record, or support any strength claim.
- The exp-0048 corpus and its holdout are **BURNED** for confirmatory purposes.
  A successor hypothesis must use a **fresh corpus**, disjoint from this one
  and from every prior suite.
- The L2 grid is **not** model selection for a reported result. It informs a
  new preregistration that must be frozen before its own fresh data exists.
- The exp-0048 verdict is unchanged: **NEGATIVE / CLOSED**. This file does not
  rehabilitate it, and the exp-0048 report and ledger entry stand as written.
- Better outcome prediction is **not** evidence of +75 Elo. Only a fixed-time
  match can establish that, and the mission's gate is unchanged.
