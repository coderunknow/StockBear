# The frozen accuracy gate is passable by a pure rescale

**Status: AUDIT. Zero strength games. No experiment reopened, no verdict changed,
no threshold lowered.**

Evidence: `benchmarks/dev6-baseline/accuracy_gate_validity/` (checksummed).
Reusable script: `scripts/dev6_accuracy_scale_audit.py`.

---

## 1. The finding

The exp-0048/exp-0049 accuracy gate was frozen as

> `L_cand ≤ 0.97 · L_champ` **and** `B_cand ≤ B_champ`, with `p = 1/(1+10^(−s/400))`

That link has a **fixed** scale constant. So the gate is sensitive to the
**magnitude** of the evaluation, not just to its ordering.

Multiply **every** champion parameter by **0.80** and round to integers. Nothing
else changes — no new feature, no refit, no search change. Result on the two
independent corpora:

| corpus | log-loss reduction | Brier non-worsening | **frozen gate** |
|---|---|---|---|
| exp-0049 | **+3.043 %** | yes | **PASS** |
| exp-0048 | **+3.109 %** | yes | **PASS** |

**A one-line uniform rescale clears the gate that two full 6,000-game corpora and
two fitted 768-parameter tables failed.**

## 2. It is not better judgement

A positive linear rescale preserves the ordering of positions. On the integer
scores actually used:

- pairwise ordering sign flips: **0.541 %** / **0.550 %** (integer-rounding ties)
- Spearman rank correlation vs champion: **0.99984** on both corpora

So the "gain" is **probability calibration** against a fixed K=400, not chess
understanding. Shrinking every score toward "drawish" improves log-loss on a
corpus whose outcomes are mostly draws.

## 3. The control that proves it

Fit the loss-minimising positive scalar on the **champion's own** scores on the
same rows (golden-section search), then compare every arm against **that**
reference. A pure rescale adds no information, so its gain must vanish:

| arm | gain vs frozen baseline | gain vs scale-invariant reference |
|---|---|---|
| u80 (exp-0049 corpus) | **+3.043 %** | **−1.096 %** |
| u80 (exp-0048 corpus) | **+3.109 %** | **−1.258 %** |

**Every** rescale factor tested (0.80, 0.85, 0.90, 0.95, 1.05, 1.10) is
**negative** against the scale-invariant reference on **both** corpora — the
correct answer. The frozen gate's PASS is an artifact of comparing against an
uncalibrated baseline at a fixed K.

The fitted optimal champion scale is ≈ **0.62**, i.e. the champion's scores are
substantially over-confident for this outcome distribution. That is a property of
the metric's link, not a defect in the engine.

## 4. Independent corroboration with measured Elo

`params_abc_s095` is verified **byte-for-byte a pure 0.95 rescale** of
`params_abc` (0 entries differ from `round(0.95 × abc)`). From exp-0012:

| arm | log-loss vs abc | measured 40+4 Elo |
|---|---|---|
| `params_abc_s095` | **+0.764 %** better | **+44.9** (3 seeds) |
| `params_abc` | — | **+48.2** (2 seeds) |

Better log-loss, **lower** measured Elo. The −3.3 difference is well inside the
±25 screen noise at 480 games, so this is **not** evidence that rescaling loses
strength — it is evidence that a log-loss improvement arrived **without** an Elo
improvement.

## 5. Caveats, stated plainly

- **A rescale is not a strength no-op.** Search margins (futility, razoring,
  aspiration) are cp-calibrated, so scaling eval does change pruning. The claim
  is *not* that u80 is strength-identical; it is that a **>3 % "accuracy gain" can
  be manufactured without any better position judgement**.
- u80 was **never played**. No strength claim is made for it.
- 6,000 positions per corpus (every 40th row), deterministic and
  score-independent — not the full corpus.
- The loader correctly **rejected** more extreme material rescales (0.50, 0.75,
  1.50) via its range validation. That guard worked as intended.

## 6. What this does and does not change

**Does not change:** exp-0048 and exp-0049 remain **CLOSED / NEGATIVE**. They
failed the bar as frozen, and nothing here re-scores or reopens them. No
historical measurement was altered.

**Does change:** the *interpretation* of that bar. It was never a valid proxy for
evaluator strength. Combined with
`docs/DEV6_ACCURACY_ELO_LINK_AUDIT.md` (no accuracy→Elo calibration exists, and
the regression's 95 % CI spans zero), the accuracy-gating route to exp-0047
activation is unsupported **twice over**: the metric is not scale-invariant, and
its output has no licensed Elo conversion.

This also reframes the two negative results honestly: they were not merely
"candidate failed", they were "candidate failed a bar that a rescale can pass".

## 7. Required of any future accuracy-style gate

1. **Be scale-invariant**, or calibrate the link (K, or a monotone map) for
   **both** arms before comparing, so a pure rescale scores zero.
2. **Validate against measured fixed-time Elo** before gating anything — run the
   audit script as a negative control and require every rescale to score ≤ 0.
3. Otherwise **abandon accuracy gating** and select on fixed-time 40+4 ms
   screens, already the ledger's only trustworthy bullet filter.
4. **Do not lower** the +75/+50 mission thresholds.

## 8. Status

Gates unchanged: **1 UNMET, 2 direction-supported, 3 PASS, 4 UNMET**. Mission
**ACTIVE / NOT COMPLETE**. exp-0047 **DORMANT**, Activation Record empty. No PR
strength claim, no merge/tag/release/deploy.
