# exp-0037 — ProbCut (isolated next direction), preregistered BEFORE results

Registered after exp-0036 closed at its frozen futility boundary, per the
persistent-continuation protocol (classify, root-cause, ledger, rank materially
different approaches, preregister next). **NOT executed:** the single authorized
remote write has been consumed; isolated-runner lanes need further
authorization. `docs/DEV6_PREREG.md` §8 is unchanged.

## Ranking of materially different directions (evidence-driven)
| rank | direction | mechanism | expected value / risk |
|---|---|---|---|
| 1 | **ProbCut** (chosen) | shallow reduced-depth search predicts a deep fail-high; skips remaining moves | distinct pruning family from bad-capture pruning/razoring; low correctness risk; switchable; expected +10..30 Elo |
| 2 | quiescence TT probe | reuse cached stand-pat/bounds in qsearch | distinct; medium risk (ply-dependent mate scores, draw detection) |
| 3 | endgame eval knowledge | opposition / king activity / rook activity, NOT the six harmful extended features | distinct eval architecture; needs accuracy + strength validation |
| 4 | NNUE with accuracy→strength link | learned eval with a measured accuracy-to-Elo link | high potential, high compute; small CPU NNUE already a recorded dead end |
| 5 | stack badCapturePruning + ProbCut | combination | ONLY after each isolated, under a SEPARATE prereg (no post-hoc stacking) |

## Frozen design (for when authorization permits)
- `SearchParams::probCut` default OFF, UCI `ProbCut` check; at non-PV,
  depth >= 5, no mate window, run a reduced-depth null-window search at
  `beta + frozen margin (200 cp)`; if it fails high, return the value.
  Margin frozen here, NOT tuned on any test set.
- Isolation: ONE binary, ONE switch; identical `params_abc` + `TTEval=true`,
  hash 16, threads 1. Default-off bench signatures must stay
  `243f9a1c1ba5b36f` / `a14ab62224f837e5`.
- Stage 1: fixed-node screen (2 disjoint batches x 600 games) with CR1 95 %
  CI, CTest/ASan/UBSan/oracle/determinism; ADVANCE only if point >= +10 and
  LCB > -10 and both batches >= -5.
- Stage 2: **fixed-time 40+4 ms on Tier-1 isolated GitHub VMs** with two
  independent preregistered batches, clean nulls, unchanged Gates 1–4, exact
  packaged candidate artifact, and final-source CI on the exact head.
  Requires a NEW explicit authorization for the additional push.
- No fixed-node result will ever be presented as fixed-time strength; no
  absolute Elo / gap-to-3000; no gate weakening; no PR/merge/tag/release.
