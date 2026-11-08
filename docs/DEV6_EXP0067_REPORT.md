# exp-0067 — joint persistence — **INVALID (author error in the dispatched plan)**

**Verdict: INVALID.** The run measured **treatment versus treatment**, not
treatment versus control. It contains **no information** about the joint
persistence contrast and **must not** be interpreted as evidence for or against
it. Gate 1 remains **UNMET**; mission **ACTIVE**. No merge, tag, release or deploy.

## 1. What went wrong (my error, stated plainly)

The plan generator I wrote for exp-0067 took a **single** `persist` flag per job
and emitted it into **both** arms:

```python
j.update({... "a_options": opts(persist), "b_options": opts(persist) ...})
```

exp-0066's generator had taken **two** parameters (`a_on`, `b_on`). Collapsing them
to one silently destroyed the causal contrast. The dispatched plan therefore set
`PersistentHistory=true, PersistentContinuation=true` in **arm A and arm B** of
both primary batches. The engines really were configured identically — this is a
**plan defect**, not a recording artifact and not a harness bug.

Verified directly against the frozen plan and the exported per-job
`match.jsonl` configuration: batchA and batchB both show
`a == b == {persistenthistory: true, persistentcontinuation: true}`.

## 2. How it was caught

The post-hoc validity script failed closed on exactly the two conditions the
prereg required:

- `explicit_switch_values` — arm B did not carry the control values;
- `primary_arms_differ_only_by_persistence_options` — the arms did not differ at all.

**28/30** checks passed; those two failed ⇒ **INVALID**. The independent raw audit
had reported `INDEPENDENT AUDIT PASS` with 0 issues, 54/54 blobs, 44/44 checksums
and 7,800/7,800 PGN replays. **That banner is not validity** — the auditor checks
integrity and consistency, not whether the intended causal contrast exists. This
is precisely why the prereg required a separate condition-by-condition check.

## 3. The numbers, correctly labelled

Run **42440539874** (4/4 SUCCESS), export **42442512528**, binary
`36fe761f20f28a252a977e24bff9a0addf798088619cea97d047ebf202fd87c8`.

| Slice | Games | What it actually compared | Elo | 95 % CI |
|---|---|---|---|---|
| batchA | 3,000 | joint **vs joint** (accidental A/A) | −2.5581 | [−10.1751, +5.0564] |
| batchB | 3,000 | joint **vs joint** (accidental A/A) | +6.3960 | [−0.7509, +13.5482] |
| "primary" | 6,000 | joint **vs joint** | +1.9186 | [−3.3021, +7.1402] |
| null | 1,200 | joint vs joint (intended null) | +7.8843 | [−3.3303, +19.1155] |
| stage0 | 600 | erase vs erase (intended null) | −2.9050 | [−19.7161, +13.8924] |

Every interval includes zero, which is what identical arms should produce. That
is a consistency observation about the harness at n=6,000, **not** a finding about
joint persistence, and it does not rescue the experiment.

## 4. Disposition under the frozen preregistration

Prereg `docs/DEV6_PREREG_EXP0067.md`, SHA-256
`e96fa243cef02263ed0fafc6cc47a8505843b4f8eec8f6c88e85fce25803efc1`, frozen at
`ce9ddef` (1 commit, never edited).

- §8 declares the run **INVALID** unless the primary arms differ only by the
  intervention options. They do not differ ⇒ **INVALID**.
- §8 permits a retry only for an **infrastructure failure before any game**, with
  the **identical plan**. This was neither: all 7,800 games completed, and a
  correct plan is by definition **not** the identical plan.
- §8 states **"partial-game reruns require a new experiment id."**
- §11 forbids result-driven retry, extension or additional dispatch.

Therefore exp-0067 is **closed INVALID**. The plan is **not** quietly repaired and
re-dispatched under this id. The question moves to a **new experiment id with its
own preregistration**. All exp-0067 evidence, including the invalid run, is
**preserved**; nothing was deleted or overwritten.

**No threshold was touched.** No pooling with exp-0065/0066. No component Elo was
summed. exp-0065 and exp-0066 remain CLOSED/INCONCLUSIVE with their original
evidence and default-OFF outcomes.

## 5. Process fix (so this cannot recur silently)

Added `scripts/recovery_validate_plan.py`, a **pre-dispatch** validator that
asserts the causal contrast exists in the plan itself: primary arms must differ,
must differ **only** by the declared intervention options, must carry the declared
treatment/control values, null arms must be identical, feature-enables must be
present in both arms, and protocol/counts/slices must match.

Proven on both plans before use:

| Plan | Result |
|---|---|
| exp-0067 (defective) | **DO_NOT_DISPATCH**, 18/24, 6 defects pinpointed |
| exp-0066 (correct) | **SAFE_TO_DISPATCH**, 24/24 |

Had this run before dispatch, 7,800 games would not have been wasted. It is now a
mandatory gate for every future dispatch.

## 6. What exp-0067 did establish (mechanism-level, still valid)

The implementation and gate work is independent of the broken match and stands:

- Composition source audit **14/14**: both branches independent, each halving
  exactly once, all five non-graded tables still erased, UCI reuse is `||`,
  **6/6** `setoption` TT-clear paths reset persisted state.
- **No new search semantics** — the packaged binary is byte-identical to
  exp-0066's (`36fe761f…`), independently confirming that only options differ.
- ctest **22/22**; `joint_persistence` group **8/8**; UCI oracle **8/8**.
- Mutations **14/14 killable KILLED**, **3** equivalence controls SURVIVED.
- Efficacy **0.974289** (18/20 games improving); per-node cost **1.026725**,
  A/A spread **0.032082**.

**A real detector gap was found and fixed here:** five aging-**rate** mutants
initially survived because the group asserted only node-count *inequality*. Exact
node pins for all four configurations now kill all five. Detectors were also
widened to all three persistence groups and all three UCI oracles, so a
composition edit (`||` → `&&`) that keeps the joint arm correct while breaking both
shipped single-table arms is caught.

**Honest pre-game signal, unchanged:** the joint node ratio **0.9743** is *worse*
than either single table (0.9654 / 0.9663) and joint per-node cost **1.0267** gives
time-to-depth ≈ **1.0003** — essentially neutral. The frozen sub-additivity prior
remains the live expectation.

## 7. Mission-level gate status

**Gate 1 UNMET.** Best valid integral remains **+40.7732 [+36.2091, +45.3513]**
against dev5 `391cb50e…`; gap **34.23 Elo** to the +75 point requirement. Checklist
**49 complete / 9 open / 58**. PR #2 **OPEN** and untouched; release remains
`v0.1.0-dev5`. Experiment completion — and *a fortiori* an invalid experiment — is
**not** mission completion. The mission continues.
