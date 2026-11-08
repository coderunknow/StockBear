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
- [ ] New experiment preregistered and frozen.
- [ ] Treatment implemented.
- [ ] Cross-move persistence tests passed.
- [ ] Cross-game isolation tests passed.
- [ ] Regression and adversarial (mutant) tests passed.
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

**Next executable task:** write and freeze `docs/DEV6_PREREG_EXP0066.md`
(continuation-history persistence, single-factor, both arms feature-ON), then
implement `PersistentContinuation` default-OFF plus the `setoption` reset fix.
