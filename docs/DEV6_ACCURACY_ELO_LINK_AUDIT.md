# The accuracy→Elo link required by exp-0047 §3.3 does not exist

**Status: AUDIT of existing evidence. Zero strength games. Nothing activated,
nothing reopened, nothing re-tuned.**

Evidence: `benchmarks/dev6-baseline/accuracy_elo_anchor/` (checksummed, raw
extractor output preserved). Script: `scripts/dev6_accuracy_elo_anchor.py`.

---

## 1. Why this audit was run

exp-0048 and exp-0049 both failed a frozen **≥ 3 % held-out log-loss reduction**
gate. Before proposing a third evaluator candidate, I checked what that 3 % bar
is actually calibrated against.

`docs/DEV6_PREREG_EXP0047.md` §3.3 requires, before any decisive game:

> a pre-result argument, from (1) and (2) and the historical NPS→Elo and
> **accuracy→Elo evidence in `benchmarks/FAILURE_LEDGER.md`**, that the
> candidate's true fixed-time effect is compatible with ≥ +75 Elo.

So I went looking for that accuracy→Elo evidence.

## 2. Finding 1 — the cited evidence is not in the ledger

Searching the whole ledger for an accuracy/Elo pairing returns **nothing**. What
does exist is a **NPS→Elo** slope (~**+90 Elo per 2× nodes**, exp-0021/0009), used
repeatedly and soundly. There is no accuracy→Elo pair anywhere.

Only **exp-0048 and exp-0049** ever measured evaluator accuracy at all, and **both
closed before a single strength game**. So no experiment in this project has ever
observed an accuracy gain *and* its strength effect. The mapping §3.3 appeals to
has never been measured.

The older tuning runs (exp-0005, exp-0012) did record a tuner loss alongside Elo
screens, but they cannot calibrate a slope:

| param set | test loss | corpus size | 480-game Elo |
|---|---|---|---|
| `outcome_v2` | 0.471739 | 885,422 | +41.2 |
| `abc` | 0.475244 | 1,099,486 | +48.2 |
| `bullet_b1` | 0.495176 | 214,064 | +32.4 |

The ordering **inverts** between the two best-loss sets (better loss, less Elo),
each loss was computed on its **own** corpus so they are not comparable, and the
total Elo spread (15.8) is **smaller than the ±25 screen noise** the ledger itself
records at that sample size.

## 3. Finding 2 — a real anchor, built at zero game cost

The project has one high-confidence fixed-time Elo: **dev5 vs dev4 =
+64.7 [+57.5, +72.0]**, 6,600 games, clustered CR1 *t*(1745), exp-0024 run
`41620641753`. Both binaries are immutable and committed, so their evaluators can
be scored on **identical positions with identical labels** from an existing
corpus — an accuracy delta for **zero** strength games.

Both arms were scored on 6,000 positions (every 40th row, deterministic and
score-independent) from each of the two independent corpora, with uncertainty as
a **paired CR1 clustered SE over games**.

First, a fact worth recording: with `params_abc` the two binaries produce
**byte-identical scores on every row**. `params_abc` does not assign dev5's four
extra features (`RookOn7th`, `KnightOutpost`, `BackwardPawn`, `PawnChain`) and
dev5's default weights for them are zero. The eval-accuracy delta is therefore
entirely the `params_abc` retune, not new features.

| corpus | K=400 (frozen metric) | K=600 (tuner's own K) | Brier favours champion? |
|---|---|---|---|
| exp-0049 | **+0.486 %** worse, *t*=3.16 (sig.) | −0.102 % better, *t*=−0.98 (n.s.) | yes (n.s.) |
| exp-0048 | +0.161 % worse, *t*=1.09 (n.s.) | **−0.326 %** better, *t*=−2.4 (sig.) | yes (sig.) |

*(positive = champion less accurate)*

**A +64.7 Elo improvement coexists with an eval-accuracy change under 0.5 % in
magnitude whose sign flips with the logistic constant K, on both corpora.**
Brier and log-loss disagree in sign on both.

## 4. What this does and does not show

**It does NOT show that accuracy gains fail to produce Elo.** The +64.7 is a
**bundle** — portable build flags + `params_abc` + TTEval — and much of it
plausibly comes from NPS, which has a known slope. Attributing it to evaluation
would be exactly the error this project already documented on mismatched
toolchains. Labels and positions also come from dev5 self-play, which would bias
*in favour* of dev5 if anything.

**It does show two things that matter:**

1. **Elo gains can arrive with essentially no accuracy change.** So accuracy is
   not a necessary condition for strength, and no slope can be fitted from this
   anchor.
2. **The 3 % bar is not calibrated to anything.** It was a plausible-sounding
   threshold, not a quantity derived from a measured accuracy→Elo relationship.
   The frozen metric's sign even depends on K, and `params_abc` was tuned at
   K=600 while the gate measures at K=400.

## 5. Consequence: §3.3 is currently unsatisfiable

For any accuracy-driven candidate, §3.3 demands an argument from historical
accuracy→Elo evidence **that does not exist**. This is a **structural blocker**,
not a candidate failure — a third PST candidate scoring 4 % instead of 2.47 %
would still hit it, because there is no way to convert either number into an
Elo expectation.

This also retro-explains why exp-0048/0049 could never have activated exp-0047
even on a pass: clearing the accuracy gate would have produced a number with no
licensed interpretation.

## 6. What would resolve it (not done here)

- **Preregister a calibration experiment**: several evaluator variants spanning a
  range of accuracy deltas, each measured for **both** accuracy on one common
  corpus **and** fixed-time 40+4 ms Elo, so a slope can be fitted with
  uncertainty. That is a real cost in games and needs its own prereg.
- **Or abandon accuracy as the gate variable** and select directly on fixed-time
  strength screens, which the ledger already calls the only trustworthy filter
  at bullet.
- **Do not** lower the +75/+50 thresholds or the 3 % bar to manufacture a pass.

## 7. Status

Gates unchanged: **1 UNMET, 2 direction-supported, 3 PASS, 4 UNMET**. Mission
**ACTIVE / NOT COMPLETE**. exp-0047 **DORMANT**, Activation Record empty. No
candidate measured for strength, no PR strength claim, no merge/tag/release.
