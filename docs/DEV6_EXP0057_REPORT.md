# exp-0057 report — Tier-1 screen of BadCapturePruning
## VALID MEASUREMENT / CLOSED AS INCONCLUSIVE (2026-11-07)

- Prereg `docs/DEV6_PREREG_EXP0057.md`, sha256
  `cdbf6dbe59a0ce9f7bb4992623a93ea830e060118c7c4329d9ac78966e3e39e3`, committed at
  `0f60282` **before any exp-0057 game**.
- Run **42341407630** (4 jobs, 5,800 games), all SUCCESS. Export **42342776434**.
- Audit `benchmarks/recovery/exp0057_independent_raw_audit.json` (`frozen_decision`).

## Result

Same-binary ablation: identical binary **and** identical EvalParams
(`params_exp0055_race.txt`) on both arms; only `BadCapturePruning` differs
(A `true`, B `false`). `BadCaptureAllDepths` stayed `false`.

| scope | W/D/L | clusters | CR1 Elo | 95% CI |
|---|---|---|---|---|
| batchA | — | 997 | +10.2832 | [−0.8969, +21.4846] |
| batchB | — | 993 | +13.1269 | [+2.3939, +23.8850] |
| **FROZEN COMBINED** | **1432 / 1258 / 1300** | **1990** | **+11.7020** | **[+3.9577, +19.4580]** |
| stage0 null | — | 300 | −5.8 | [−21.4428, +9.7983] |
| **powered** candidate null (1,200 g) | — | 600 | −7.6 | [−17.0272, +1.8824] |

Bootstrap [+3.9285, +19.4873]. **Batch gap only 2.84 Elo.**

## Frozen decision

Every validity condition passed (11/11), including per-arm switch proof
(`A=true, B=false` in both primaries, equal within each null) and identical arm
binaries in all four jobs. 0 forfeits/illegal/failures; **5,800/5,800 PGN replayed,
0 inconsistent**; 54/54 blobs; 44/44 sums; stage0 fresh ctest.

- **ADVANCE** required point ≥ **+15**, LCB > 0, batch gap ≤ 20, nulls OK.
  Point **+11.70 < +15** ⇒ **blocked**. Every other condition passed.
- **CLOSE** required UCB < +5 or point ≤ 0. Neither holds (UCB +19.46).
- ⇒ **CLOSED AS INCONCLUSIVE.**

No strength claim, no default change, no rescale, no retune, no re-run, no
post-hoc sample increase. `BadCapturePruning` stays shipped **false**.

## Two useful findings

**The powered null fixed the exp-0056 problem.** Raising the candidate null from
400 to 1,200 games (and stage0 to 600) produced [−17.03, +1.88] and
[−21.44, +9.80] — both comfortably including 0. The spurious null rejection did
not recur, supporting the diagnosis that a ±19 Elo instrument was too weak to be
a hard validity gate. The criterion itself was never relaxed.

**The Tier-2 anchor regressed, as history predicted.** exp-0036's local-core
**+21.52 [+10.28, +32.81]** became **+11.70 [+3.96, +19.46]** on isolated Tier-1
VMs. That is the same regression pattern exp-0017 recorded, and it is why Tier-2
screens were never treated as banked evidence.

## Where this leaves the mission

Gate 1 needs point ≥ +75 and LCB > +50 vs released dev5. exp-0056 established that
threats + race **cannot** reach it (face-value CI upper bound +47.69 < +50). This
screen adds no banked strength. The binding need remains roughly **+35 Elo** of
independent, confirmable improvement.

Untested ordering mechanisms that remain credible, each requiring its own
preregistration: `captureHistory` (−4.65 % nodes at fixed depth in the liveness
probe), `continuationHistory`, `counterMoves`. All are shipped OFF in **both**
dev5 and the candidate, and exp-0014's "-off" ablations were therefore no-ops.

**Gate status: 1 UNMET, 2 SUPPORTED (exp-0054), 3 PASS, 4 UNMET.
Mission ACTIVE / INCOMPLETE.**
