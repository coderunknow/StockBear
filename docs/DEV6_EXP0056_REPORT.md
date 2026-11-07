# exp-0056 report — integral candidate vs released dev5
## INVALID MEASUREMENT (2026-11-07) — no strength claim

- Prereg `docs/DEV6_PREREG_EXP0056.md`, sha256
  `6437c2cf71ee8483be707f6fc1b2c624b33fd9551be1e316846862d904c6e90f`, committed
  at `ec7c9c4` **before any exp-0056 game**.
- Run **42338019422** (4 jobs, 6,800 games) — all jobs SUCCESS.
  Export run **42340004695**, mirrored at
  `benchmarks/exp-runs/tier1-export/run-42338019422/`.
- Audit: `benchmarks/recovery/exp0056_independent_raw_audit.json` (`frozen_decision`),
  full stdout in `exp0056_independent_audit_stdout.txt`.

> **Recovery note.** This verdict was first computed on 2026-11-07 and then lost
> when the sandbox reset to `origin/main`, because the verdict commit had not yet
> been pushed. It was **regenerated from the intact raw export** at `104f34a`.
> The recomputation reproduced every number exactly, including the failing null
> CI. Raw evidence was never at risk; only the derived write-up was.

## 1. Why this run is INVALID

Prereg §5.4 requires **both** validity nulls' 95% CIs to include 0.

| null | Elo | 95% CI | includes 0 |
|---|---|---|---|
| stage0 (control/control) | +14.9243 | [−0.9393, +30.8504] | yes |
| **candidate-options null** | **+19.2246** | **[+0.6520, +37.9077]** | **NO** |

Prereg §6: *"Any §5 failure ⇒ INVALID MEASUREMENT: no strength claim of any
kind."* That rule is applied as written.

**A trap worth recording:** the auditor printed `TOTAL ISSUES: 0` and
`INDEPENDENT AUDIT PASS`. That is **not** a validity verdict. Null adequacy is
tracked separately (`nulls_ok`), and it is **False** here. Treating the green
audit banner as proof of validity would have manufactured a false strength
claim — exactly the failure mode the mission's checkbox rules forbid.

Everything else passed: 0 forfeits / illegal / engine failures, **6,800/6,800 PGN
replayed with 0 inconsistencies**, 54/54 blobs, 44/44 checksums, 0 batch opening
overlap, stage0 fresh ctest 17/17, and correct per-arm load proof (A = race
config; B = `params_abc` on the released dev5 binary).

## 2. Face value — WITHHELD, recorded only for transparency

| scope | W/D/L | clusters | CR1 Elo | 95% CI |
|---|---|---|---|---|
| batchA | 1170 / 927 / 896 | 1493 | +31.8538 | [+22.4798, +41.2744] |
| batchB | 1256 / 911 / 823 | 1490 | +50.2476 | [+40.8251, +59.7441] |
| combined | 2426 / 1838 / 1719 | 2983 | +41.0128 | [+34.3622, +47.6935] |

**These are not results.** They are withheld because the measurement is invalid.

Two further reasons not to trust the pooled number even informally:

- **Batch inconsistency.** +31.85 vs +50.25 is an **18.4 Elo** gap; the CIs overlap
  only in the sliver [40.83, 41.27].
- **The nulls drifted the same way.** Both leaned positive (+14.9, +19.2), the
  direction that would inflate an arm-A estimate.

## 3. Is the runner biased? Diagnostic, not an excuse

All six same-binary validity nulls from the three recent experiments:

| experiment | stage0 | candidate null |
|---|---|---|
| exp-0054 | −3.53 | −3.47 |
| exp-0055 | −5.21 | +3.47 |
| exp-0056 | +14.92 | **+19.22** |

Mean **+4.23 Elo**, signs `− − − + + +`. A **fixed** arm-A bias would show a
consistent sign; these do not. A colour split of the raw null records shows only
the ordinary White advantage (arm A ≈0.58 as White, ≈0.47 as Black), which the
paired design cancels.

The most likely explanation is therefore the **~5% false-positive rate inherent
in a 400-game null**: at ~±19 Elo resolution it is a weak instrument to use as a
hard gate. **That does not rescue this run.** The criterion was pre-declared and
is applied as written. The lesson is about *design*: future preregistrations must
**power the null** instead of gating on a coin-flip.

## 4. The decisive strategic finding

Even taken at face value, this configuration **cannot pass Gate 1**:

- point **+41.01** is far below the required **+75**;
- the entire CI's **upper** bound **+47.69** is below the required **LCB > +50**.

No re-analysis and no larger sample can fix that. The preregistration predicted
this in advance ("a roughly additive integral (~+50) would fail the +75 point
requirement"), and the data agree.

**Conclusion: threats + passed-pawn race is not a sufficient basis for Gate 1.**
Roughly **+35 Elo or more** of additional, independently justified strength is
required. Both parameters stay shipped **0**.

## 5. Disposition

- exp-0056 **CLOSED as INVALID**. Its 3,400 openings and 6,800 games are burned;
  they are never pooled with anything.
- No default change, no PR strength claim, no merge, tag, release or deploy.
- Banked evidence remains **exp-0054 only** (+23.5374 [+15.6937, +31.4052],
  CONFIRMED). exp-0055's screen advance stands as a screen.
- Next actions, each requiring its own preregistration:
  1. a **distinct strength direction** — more strength is the binding need;
  2. when an integral is worth measuring again, use a **properly powered null**
     and a pre-declared batch-consistency rule, on fresh openings.

**Gate status: 1 UNMET, 2 SUPPORTED (exp-0054), 3 PASS, 4 UNMET.
Mission ACTIVE / INCOMPLETE.**
