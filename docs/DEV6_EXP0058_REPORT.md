# exp-0058 report — Tier-1 screen of CaptureHistory
## VALID MEASUREMENT / CLOSE (mechanism rejected) — 2026-11-07

- Prereg `docs/DEV6_PREREG_EXP0058.md`, sha256
  `8722b108b295b95a9049181662cdf3ac5a4100042e5cff79e32cfd658735f3d5`, committed at
  `520f854` **before any exp-0058 game**.
- Run **42343201120** (4 jobs, 5,800 games), all SUCCESS. Export **42344477938**.
- Audit `benchmarks/recovery/exp0058_independent_raw_audit.json` (`frozen_decision`).

## Result

Same-binary ablation, identical EvalParams both arms; only `CaptureHistory`
differs. `BadCapturePruning` and `BadCaptureAllDepths` were `false` throughout, so
this isolated **ordering only**.

| scope | W/D/L | clusters | CR1 Elo | 95% CI |
|---|---|---|---|---|
| batchA | 663 / 675 / 656 | 994 | +1.5729 | [−8.6591, +11.8077] |
| batchB | 662 / 631 / 701 | 994 | −6.6419 | [−17.2118, +3.9157] |
| **FROZEN COMBINED** | **1325 / 1306 / 1357** | **1988** | **−2.5342** | **[−9.8828, +4.8123]** |
| stage0 null (600 g) | — | 299 | +8.7168 | [−8.8905, +26.3690] |
| powered null (1,200 g) | — | 593 | −4.6874 | [−15.7978, +6.4133] |

## Frozen decision

All validity conditions pass: 0 forfeits/illegal/failures, **5,800/5,800 PGN
replayed with 0 inconsistencies**, 54/54 blobs, 44/44 sums, both nulls include 0,
per-arm switch proof, identical arm binaries, stage0 fresh ctest.

**CLOSE** was defined as `UCB < +5` **or** `point ≤ 0`. **Both limbs hold**
(UCB +4.8123 < +5; point −2.5342 ≤ 0) ⇒ **CLOSE (mechanism rejected)**.

No rescale, no retune, no re-run. `CaptureHistory` stays shipped **false**.

## The lesson: node efficiency is not strength

The pre-game probe showed this switch needed **4.65 % fewer nodes at fixed
depth** — the best efficiency signal of the four switches probed, and the reason
it was selected. In actual games it is worth **−2.53 [−9.88, +4.81]**.

The node count was used only as a **liveness/mechanism** check, never as an
effect size, and the game evidence overrules it. Searching fewer nodes to reach
the same depth is not the same as choosing better moves.

## A check bug found and corrected (not a criterion change)

The first validity evaluation reported a failure for "pruning unchanged",
because it looked only in the **explicit** UCI options dict and read `None` for
an option that was never set. Corrected to read *explicit-or-recorded-default*:
`badcapturepruning` and `badcapturealldepths` are both `false` for both arms in
all four jobs. The **check** was wrong; the criterion and the measurement were
not. This is recorded in `validity_check_correction`.

## Mission position

Three consecutive experiments have now failed to add banked strength:
exp-0056 **INVALID** (and its face value shows threats+race cannot reach the
gate), exp-0057 **INCONCLUSIVE** (+11.70), exp-0058 **REJECTED** (−2.53).

Banked evidence remains **exp-0054 only** (+23.5374 [+15.6937, +31.4052]).
Gate 1 requires point ≥ +75 **and** LCB > +50 versus released dev5; roughly
**+35 Elo** of additional confirmable strength is still missing.

Remaining untested ordering switches (`continuationHistory`, `counterMoves`)
both showed **more** nodes at fixed depth (+7.18 %, +9.20 %) — a weaker efficiency
signal than either switch now measured, though that signal has just been shown
not to predict strength.

**Gate status: 1 UNMET, 2 SUPPORTED (exp-0054), 3 PASS, 4 UNMET.
Mission ACTIVE / INCOMPLETE.**
