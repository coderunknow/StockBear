# DEV6 mission checkpoint — ACTIVE / INCOMPLETE

Append-only durable checkpoint for the continuation directive. Updated after every
significant step. Gate: point ≥ +75 Elo AND two-sided opening-clustered 95% LCB
strictly > +50, measured **directly** against the exact published dev5 binary.

**Status: ACTIVE / INCOMPLETE. Gate UNMET.**
Best valid direct integral measurement vs published dev5:
**+40.7732 Elo [+36.2091, +45.3513]** (exp-0062). Remaining gap to the point
threshold: **34.23 Elo**.

---

## 2026-11-08 — Step A: repository rehydration (DONE, verified)

Sandbox had reset the checkout to `main` (`6e7c2e0`). Recovered:

- `git fetch origin arena/6a6a2ba3-stockbear` + `git reset --hard origin/…`
  → HEAD **`cbd099aa926e884728fa5ff7043ec455933d1d22`**, equal to
  `git ls-remote origin arena/6a6a2ba3-stockbear`. Working tree clean.
- Tracked files restored: **3,260**.
- `AGENTS.md` **does not exist** (confirmed by `ls`, not assumed). Applicable
  instructions read: `docs/DEV6_CONTINUATION_POLICY.md`,
  `STOCKBEAR_COMPLETION_CHECKLIST.md`, `DESIGN_LOG.md`, `AGENTS_LOG.md`.
- Latest registered experiment ID confirmed from the repository:
  `docs/DEV6_PREREG_EXP0065.md` is the highest → **exp-0066 is free**.
- Dependencies reinstalled with `--break-system-packages`
  (numpy 2.4.6, chess 1.11.2, pyyaml, cmake 4.4.4, ninja).
- `build-rel` rebuilt (53 targets). Verification:
  - bench d4 `243f9a1c1ba5b36f`, d6 `e06c4352681ae8eb`, d7 `5bceff035f2a4ae4`
    — **all three exact**.
  - `ctest`: **100% tests passed out of 20**.
  - dev5 baseline SHA-256 recomputed:
    `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918` — **exact**.
- Remote boundaries re-verified: `origin/main` = `6e7c2e0`, no merge/tag/release.

## 2026-11-08 — Step B: continuation / counter-move lifecycle (DONE, source-verified)

Established by reading source, not assumption:

| fact | citation |
|---|---|
| `continuation_` heap array, `PieceTypeNB*64*PieceTypeNB*64` = 200,704 ints (~803 KB), value-initialized at construction | `src/search/search.hpp:265,275` |
| index = (prevType, prevTo, curType, curTo); **no colour term** | `src/search/search.hpp:233` |
| read for quiet non-killer ordering, gated on `params_.continuationHistory`, contributes `clamp(cont/4, ±8000)` on top of main history | `src/search/search.cpp:296–301` |
| written gated on the same param and `previousPiece != NoPiece`, `cont = clamp_history(cont + bonus)`, `HistoryLimit = 60000`; also receives maluses through `penalise_quiets` → `update_quiet_stats` | `src/search/search.cpp:386–389,403–405,34` |
| **zeroed unconditionally in `run()` on EVERY root search**, independent of every persistence switch | `src/search/search.cpp:952` |
| `counterMoves_` is `Move[PieceNB][64]` — a **categorical single-move reply table**, written once per cutoff, read as a fixed ordering score 1485000 | `src/search/search.hpp:282`; `src/search/search.cpp:375,291–293` |
| `counterMoves_` also zeroed every root search | `src/search/search.cpp:951` |
| UCI builds a **fresh `Search` per `go`** unless `params_.persistentHistory`; exp-0065's switch persists **only `history_`** | `src/uci/uci.cpp:445–453`; `src/search/search.cpp:940–947` |
| `persistentSearch_` is reset **only** on `ucinewgame` | `src/uci/uci.cpp:565–568` |

**Both feature switches ship OFF** — verified from the built executable's own
option list, not from source alone:
`CounterMoves default false`, `ContinuationHistory default false`,
`CaptureHistory default false`, `HistoryMaluses default false`,
`PersistentHistory default false`.
⇒ Persisting these tables while the features are OFF is a **no-op**: the update
sites are gated on the feature param, so nothing is ever written. Any real
treatment must hold the feature ON.

**New latent defect found (affects the persistence mechanism, not exp-0065's
verdict).** `handle_setoption` calls `table_.clear()` at six sites
(`src/uci/uci.cpp:236,245,256,265,294,346`) precisely to keep same-session
ablation honest, but **never resets `persistentSearch_`**. With a persistence
switch ON, history learned under a previous evaluation/feature configuration
would survive a configuration change. The frozen Tier-1 matches are **not**
affected (all options are sent once at startup and `ucinewgame` runs per game,
which does reset), so exp-0065's validity and verdict stand unchanged. The new
work must not inherit this leak.

### Design consequence (justified, to be frozen in the prereg)

Continuation history is a **graded statistic** updated by ±depth² and is exactly
the kind of table that needs many samples; erasing it every ~40 ms is the
confound. The counter-move table is **categorical and saturates after a single
write**, so cross-move accumulation is a materially different and weaker
mechanism. They are therefore **not bundled** — bundling would repeat the
exp-0026 six-feature attribution failure. exp-0066 treats **continuation
history only**, holding `ContinuationHistory=true` in **both** arms so the single
varying factor is table lifetime.

---

## Live checklist (directive §10) — evidence-backed

- [x] Repository state and prior protocols rehydrated — HEAD `cbd099a` == remote;
      bench d4/d6/d7 exact; ctest 20/20; dev5 `391cb50e…` verified.
- [x] Continuation/counter-move lifecycle independently verified — source
      citations above + executable option-list check.
- [x] New experiment preregistered and frozen — `docs/DEV6_PREREG_EXP0066.md`
      SHA-256 `96c20de126b9ce8f5ca2031c5a90dfb72e24794462c077651939d1084c215fa3`,
      freeze commit `fc5375c`, `git log` shows exactly **1** commit for the file.
- [x] Treatment implemented — `PersistentContinuation` default OFF; bench
      d4/d6/d7 all exact; option advertised `default false`.
- [x] Cross-move persistence tests passed — `persistent_continuation` group
      9/9; TT cleared before every probe so lifetime (not TT reuse) is measured.
- [x] Cross-game isolation tests passed — interactive UCI oracle 6/6 including
      `cross_game_isolation_on` and `cross_configuration_isolation_on`.
- [x] Regression and adversarial (mutant) tests passed — **11/11** killable
      KILLED, **2** equivalence controls SURVIVED; ctest **21/21**.
- [ ] Primary experiment executed.
- [ ] Statistical analysis independently verified.
- [ ] Verdict formally recorded.
- [ ] Outstanding audit obligations resolved legitimately or retained unresolved
      (2.2 and 7.6 currently retained UNRESOLVED with honest evidence).
- [ ] Next research direction registered and executed while the gate is unmet.
- [ ] Final candidate directly compared against published dev5.
- [ ] Final candidate satisfies BOTH thresholds.
- [ ] All required audits and evidence complete.
- [ ] Final report and repo state independently verified.

## 2026-11-08 — Steps C/D complete (DONE, verified)

- Prereg frozen at `fc5375c` (1 commit, digest `96c20de1…`), **before** any
  implementation measurement or game.
- Implemented `PersistentContinuation` (default OFF) + reuse of the Search when
  either persistence switch is ON + reset of persisted state on **all six**
  `handle_setoption` TT-clear paths (verified programmatically: 6 clears,
  6 resets).
- New registered group `persistent_continuation`: **9/9**; full suite **21/21**;
  bench d4/d6/d7 **exact**.
- Interactive UCI oracle: **6/6** checks PASS (persistence across `go`,
  cross-game isolation ON and OFF, cross-configuration isolation ON and OFF,
  determinism across fresh engines).
- Mutation matrix: **11/11 killable KILLED**, **2** controls SURVIVED.
- Frozen efficacy gate: 20 real games / 2,525 positions, node ratio **0.966264**
  (≤0.98), **18/20** games improving → **PASS**. Corpus byte-identical to the
  exp-0065 selection rule, proving the rule was followed.
- Frozen per-node cost gate: ratio **0.970741** (≤1.10), A/A spread **0.070232**
  (<0.10), node-count deviation 0 → **PASS**.
- Openings seed **2026110666**, 3,900, 254 files / 96,841 positions excluded,
  overlap **0**; independently re-verified **PASS**.

### Two errors caught by verification during this step (recorded, not hidden)

1. My first UCI oracle asserted that repeated searches of one position within a
   single engine must be equal. That is **false**: the TT persists across `go`,
   so a later search legitimately costs fewer nodes. Replaced with a determinism
   check across **fresh engines**. Same class of confound as the earlier
   "lifetime test measured TT reuse" lesson.
2. The `ucinewgame_does_not_reset` mutant initially **survived** because its
   anchor matched the first identically-indented `persistentSearch_.reset()`,
   which lives in `handle_setoption`, not `ucinewgame`. Made the anchor unique
   (asserted exactly 1 occurrence); the mutant is now **KILLED**.

**Next executable task:** dispatch the frozen exp-0066 benchmark (7,800 games),
then export, independently audit, apply the frozen decision rule, and record the
verdict. Gate remains UNMET; mission ACTIVE.

## 2026-11-08 — exp-0066 CLOSED as VALID / INCONCLUSIVE

Benchmark **42434718590** 4/4 SUCCESS; export **42436688031**; binary
`36fe761f20f2…`. Primary 6,000 games / 2,985 clusters →
**+11.3524 [+5.3008,+17.4110]**. Validity **26/26**; auditor issues **0**;
**7,800/7,800** PGN replayed, 0 inconsistent; both powered nulls include 0.

Frozen ADVANCE point bar **+15** → missed by **3.65 Elo** ⇒ **INCONCLUSIVE**.
UCB **+17.41** also fails the CLOSE bar, so the mechanism is **not refuted**.
`PersistentContinuation` **remains default OFF**; not promoted to champion.
No rounding, no extra games, no batch selection, no threshold relaxation.

**No pooling with exp-0065** (different seed + switch) and **no summing** of
+9.7673 and +11.3524 — the two tables feed the same quiet-ordering path.

### Checklist state (unchanged: 49 complete / 9 open / 58)

Open: 2.2 (baseline prereg gap), 4.1, 7.6 (large datasets present), 8.1–8.6
(mission-completion items). exp-0066 adds a 37th→38th complete prereg for the
2.2 keyword sweep but does **not** close 2.2, because
`DEV6_PREREG_BASELINE.md` remains incomplete. Nothing was deleted to pass a check.

### Gate status

**UNMET.** Best valid integral **+40.7732 [+36.2091,+45.3513]**; gap **34.23 Elo**
to the +75 point requirement. No merge, tag or release. PR #2 remains OPEN and
untouched; release remains `v0.1.0-dev5`.

**Next executable task:** the mission needs a **new mechanism**, not another
~10 Elo increment. Candidates that remain untested and are *not* on the rejected
list: a joint graded-table persistence treatment (own prereg required, no
pooling), and the confirmed-missing evaluation terms (tempo/side-to-move,
bad-bishop, space, OCB drawish scaling). Each requires its own preregistration
and may not inherit exp-0065/0066 samples. Given two consecutive sub-bar
increments, a further single-table screen is **not** a credible gate lever and
should not be run merely to show activity.

## 2026-11-08 — exp-0067 registered, implemented and gated (no games yet)

Step 1 re-verified HEAD/worktree; `AGENTS.md` does not exist in this repository.
exp-0066's verdict, evidence and thresholds are untouched.

**Candidate selection was measured, not asserted** (read-only, on committed
evidence): pure OCB occurs in **58/3000 games (1.93 %)** / **0.56 %** of positions
⇒ absolute ceiling **+6.71 Elo** even converting every such game to a win →
**rejected as underpowered by construction**. Bad bishop shares **27.5 %**
variance with the existing `MobilityBishop` (r = −0.5247); space shares **15.4 %**
with total mobility (r = −0.3931) → both **deferred as partially redundant**.
Tempo is a constant offset with a weak prior → deferred. **Joint persistence
selected**: the only candidate with direct positive in-engine evidence.

Prereg `docs/DEV6_PREREG_EXP0067.md` SHA-256
`e96fa243cef02263ed0fafc6cc47a8505843b4f8eec8f6c88e85fce25803efc1`, frozen at
**`ce9ddef`** (exactly 1 commit) before implementation measurements and games.

**No new search semantics**: both switches already exist and ship false. The work
was proving the **composition**. All pre-game gates PASS:

| Gate | Result |
|---|---|
| Composition source audit | 14/14 checks; both branches independent, each halving exactly once, all 5 non-graded tables still erased, 6/6 `setoption` resets |
| Bench d4/d6/d7 | exact |
| ctest | **22/22** |
| `joint_persistence` group | **8/8** |
| Interactive UCI oracle | **8/8** (incl. joint ≠ history-only and joint ≠ continuation-only) |
| Mutations | **14/14 killable KILLED**, **3** controls SURVIVED |
| Efficacy (20 games / 2,525 pos, d7) | **0.974289** ≤ 0.98; **18/20** improving |
| Per-node cost (20k × 250) | **1.026725** ≤ 1.10; A/A spread **0.032082** |
| Openings | seed **2026110667**, 3,900, overlap **0**, independently verified |

### A real detector gap found and fixed (recorded, not hidden)

Five aging-**rate** mutants (halving removed / applied twice / only first slot
decayed, for either table) initially **SURVIVED**: the group asserted only node
count *inequality*, which is blind to the rate. Fixed by pinning **exact** node
counts for all four configurations (OFF `{29153,37911,29153,37911}`, history-only
`{29153,58093,28620,49940}`, continuation-only `{29153,37916,25730,36912}`, joint
`{29153,57921,28610,47611}`). All five are now KILLED. The mutation detectors were
also widened to run **all three** persistence groups and **all three** UCI
oracles, because a composition edit like `||` → `&&` leaves the joint arm correct
while silently breaking both shipped single-table arms.

**Honest pre-game signal:** joint node ratio **0.9743** is *worse* than either
single table (0.9654 / 0.9663), and joint per-node cost **1.0267** gives
time-to-depth ≈ **1.0003** — essentially neutral, materially less favourable than
exp-0066's ≈0.938. Consistent with the frozen sub-additivity prior. Not an Elo
claim.

**Next executable task:** dispatch the frozen 7,800-game benchmark, export,
independently audit, apply the frozen PROMOTE/CLOSE rule, record the verdict.
Gate 1 remains **UNMET**; mission **ACTIVE**.
