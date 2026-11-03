# v0.1.0-dev6 — External rating ladder (EXECUTED results + preserved historical design)

## §0. Status: LADDER EXECUTED — pool-specific INTERNAL rating, NOT absolute Elo

**Superseding notice.** Everything below `--- Appendix A ---` is the ORIGINAL
design dossier from the earlier cycle, preserved verbatim. Its "NOT COMPLETED /
BLOCKED" status and its 40+4 ms / NNUE-download plan are **superseded** by the
executed ladder described here. Historical text is not silently rewritten.

The external ladder is now **implemented and measured** (M0.2):

| item | result |
|---|---|
| exp-0031 pilot | 10 anchors × 40 games = 400 games, **5 informative anchors** (scores in `[0.20,0.80]`), **0** time forfeits → PROCEED |
| exp-0032 decisive | connected bipartite star: **8 anchors × 5 subjects × 80 games = 3,200 games**; 3,186 adjudicated, 14 `UNADJUDICATED_MAX_PLIES`, **0** time forfeits / illegal moves / UCI failures |
| exp-0032b sensitivity | paired **shared-opening** round-robin (5 subjects, 10 pairings × 200 games) to remove the disjoint-slice confound |
| model | draw-aware **Bradley-Terry-Davidson** MLE, `nu = 0.190`, 1,000 opening-cluster bootstrap replicates, 1,600 clusters, per-cell residual RMSE `0.0328`, NLL `2101.9` |
| control | **fixed node** `go nodes 6000` +/-15 %, hash 16 MB, 1 thread, max 240 plies, paired colour-reversed fresh disjoint openings |

Fixed-node is deliberate: exp-0030 E4 measured `-22.6 [-47.4,+2.0]` with 5
TIME_FORFEIT events on this shared 2-vCPU sandbox, so local fixed-time matches
are clock-noise-confounded. **This ladder's rating is therefore a fixed-node,
pool-specific INTERNAL rating and is NOT a 40+4 ms Elo, NOT CCRL/CEGT/FIDE
comparable, and NOT an absolute rating.**

### Pinned opponent pool (all built from official source archives)

`SF8`, `SF9`, `SF10`, `SF11` (tags `sf_8`..`sf_11`), `Weiss 2.0` (tag `v2.0`).
Exact tag commits, source/binary SHA-256, build commands, UCI option sets and
licence notices: `benchmarks/dev6-baseline/external_opponents.json`,
`docs/DEV6_EXTERNAL_OPPONENTS.md`, `THIRD_PARTY.md`. **Stockfish is an opponent
and benchmark only, never a source-code base.** Weiss 2.0 lacks `go nodes` and
is pinned for future fixed-depth/time diagnostics but **excluded** from the
fixed-node ladder; Weiss master failed to build (C++ enum in a C11 header); BBC
was excluded (no `go nodes`). SF8/9/10 and SF11 `Skill Level 0..20` provide the
strength span; SF11-L20/SF8/SF9/SF10 are deliberately saturated strong anchors
and are retained, never hidden.

### exp-0031 pilot (anchor selection, frozen in `docs/DEV6_PREREG_EXP0031.md`)

dev5 official vs each anchor, 40 games each, `--nodes 6000`: SF11-L0 `0.950`,
L4 `0.762`, L8 `0.400`, L12 `0.275`, L16 `0.237`, L20 `0.125`, SF8 `0.062`,
SF9 `0.025`, SF10 `0.125`, dev4 `0.600`. Informative: **SF11-L4/L8/L12/L16 and
dev4**. 4-game config smoke test was DISCARDED per prereg.

### exp-0032 fitted internal ratings (mean 0; two-sided 95% cluster-bootstrap CI)

| engine | internal Elo | 95% CI | games |
|---|---|---|---|
| sf8 | +485.8 | [+407.6, +602.0] | 400 |
| sf10 | +330.8 | [+270.1, +413.0] | 399 |
| sf11-L20 | +312.3 | [+245.9, +387.4] | 399 |
| sf9 | +301.9 | [+243.6, +371.8] | 399 |
| sf11-L16 | -4.3 | [-41.7, +33.5] | 396 |
| sf11-L12 | -9.8 | [-52.1, +31.1] | 397 |
| sf11-L8 | -59.0 | [-94.5, -24.9] | 397 |
| dev6_champion | -169.0 | [-210.6, -134.1] | 635 |
| dev5_rebuilt | -173.9 | [-214.7, -136.3] | 637 |
| dev6_failed | -184.7 | [-227.5, -149.7] | 636 |
| dev4 | -197.9 | [-238.4, -162.3] | 638 |
| **dev5_official** | **-205.0** | **[-246.8, -165.7]** | 640 |
| sf11-L4 | -427.4 | [-479.7, -388.1] | 399 |

Full per-pairing scores/residuals, leave-one-anchor-out sensitivity and raw paths:
`docs/DEV6_EXTERNAL_LADDER_REPORT.md`,
`benchmarks/dev6-baseline/ladder_results.json`,
`benchmarks/dev6-baseline/ladder_cells.json`,
`benchmarks/exp-runs/exp0032-ladder-*/`.

### Honest limitations (NOT hidden)

* **Disjoint-slice confound:** each of the 40 exp-0032 cells used a different
  40-opening slice, so cross-subject comparisons mix strength with slice
  difficulty. The fitted `dev5_official` vs `dev5_rebuilt` gap (~31 internal
  Elo) contradicts exp-0030's bench-identical binaries. exp-0032b (paired,
  shared openings) is the registered sensitivity check; its result is recorded
  in §0b below. Leave-one-anchor-out subject ordering is **unstable** — a
  direct consequence of this noise — and is reported, not smoothed over.
* **SF11 skill anchors are non-monotonic** in this fixed-node pool (L12 ~ L16,
  large L16 -> L20 jump). SF11's `Skill::pick_best` uses a time-seeded PRNG, so
  individual games are not bitwise reproducible; the skill limiter also
  interacts with a node cap. These are retained as measured, not "corrected".
* **Saturated cells** (`sf8`, `sf10` for several subjects) give wide rating CIs
  and are reported. **Generalisation limits:** fixed-node != fixed-time;
  `dev4` is only +12.2 [-22.7, +47.2] vs dev5 in exp-0032b, while the historical
  fixed-time exp-0024 measured +64.7 [+57.5, +72.0] on a different suite — a
  concrete demonstration that the two controls are not interchangeable.
* **Calibration: NOT DEFENSIBLY CALIBRATED.** A rough affine context from SF11's
  own `UCI_Elo` self-rating (slope 1.62, intercept 2449.8, anchor residual SD
  **199 Elo**) puts dev5 at ~2118 "context Elo". SF11 `UCI_Elo` is an
  approximate self-rating for a different time control (60+0.6) and full-strength
  SF; systematic error is unknown and likely large. **No absolute Elo, no CCRL
  equivalence, and NO numeric gap-to-3000 claim is made.** 3,000 Elo remains a
  long-term strategic target only.
* The ladder **does not satisfy any dev6 strength gate**. `docs/DEV6_PREREG.md`
  §8 is unchanged. No PR/merge/tag/release follows from ladder completion.

### §0b. exp-0032b paired shared-opening sensitivity

Registered as an addendum **before results** (prediction frozen in the
`scripts/dev6_ladder_paired.py` docstring): if the star-ladder official/rebuilt
gap is a slice artifact, the three champion binaries must be statistically
indistinguishable on shared openings; `dev6_failed` should remain measurably
weaker than `dev6_champion`.

**Result (10 pairings x 200 games = 2,000 games, single shared 100-opening
suite, identical opening order and seed, colour-reversed, 0 time forfeits):**

| paired BTD internal Elo | value |
|---|---|
| dev5_official | +24.6 |
| dev5_rebuilt | +12.3 |
| dev6_champion | 0.0 |
| dev4 | -16.9 |
| dev6_failed | -20.0 |

Every head-to-head 95% CI includes zero: `dev5_official` vs `dev5_rebuilt`
`+20.9 [-13.6,+55.8]`; `dev5_official` vs `dev6_champion` `+20.9
[-13.6,+55.8]`; `dev6_champion` vs `dev6_failed` `+29.6 [-9.7,+69.7]`;
`dev6_failed` vs `dev4` `+20.9 [-17.9,+60.2]`; `dev5_official` vs `dev4`
`+12.2 [-22.7,+47.2]`.

* **Prediction 1 CONFIRMED:** the three champion binaries are statistically
  indistinguishable on shared openings; the star ladder's ~31 internal-Elo
  `dev5_official`/`dev5_rebuilt` gap was an opening-slice artifact. The paired
  fit even **reverses** the subject ordering (`dev5_official` is highest here,
  lowest in the star ladder). Conclusion: **the star ladder's ordering of the
  five StockBear subjects is not reliable; only its anchor separation and the
  pooled anchor rating coverage are usable.** This is reported, not hidden.
* **Prediction 2 NOT CONFIRMED:** `dev6_champion` vs `dev6_failed` is `+29.6
  [-9.7,+69.7]` — right direction (consistent with the recorded -17 Elo
  regression) but **not significant** at 200 games. The paired suite is
  underpowered for a ~20 Elo effect; no strength conclusion is drawn from it.
* `nu` differs (`0.472` paired vs `0.190` star) because the paired pool is
  similar-strength StockBear builds with a much higher draw rate; this is a
  pool property, not a contradiction.
* Consequence for M0.2: the ladder **is** implemented with a defensible,
  qualified result, but subject-level ratings must be taken from the paired
  design with its CIs, and the fixed-node/fixed-time non-interchangeability is
  explicit. No dev6 gate is affected.

Raw: `benchmarks/exp-runs/exp0032b-paired-*/`,
`benchmarks/dev6-baseline/ladder_paired.json`,
`docs/DEV6_EXTERNAL_LADDER_REPORT.md` §"Paired sensitivity".

--- Appendix A — original cycle design dossier (preserved verbatim, SUPERSEDED) ---

# v0.1.0-dev6 — External rating ladder: methodology, opponent dossier, and status

## Historical status (SUPERSEDED by §0 below): NOT COMPLETED (PARTIAL / BLOCKED)

**An external multi-engine rating ladder was not executed in this cycle.** This
is one of the mandatory acceptance gates (Gate 5); because it is unmet, and the
primary strength gate is also unmet, **no release PR is opened**. This document
records the reproducible design, the exact researched opponent identities, the
one real internal anchor that exists, the precise blockers, and what is required
to complete it. No absolute Elo rating is claimed or fabricated.

### Why it is blocked (exact, honest)

1. The sandbox's outbound network reaches only `github.com`, `codeload.github.com`,
   `api.github.com` and package registries. Official engine binaries/networks are
   served from `release-assets.githubusercontent.com` / project sites, which the
   sandbox cannot reach; only the free GitHub-hosted runner can fetch them. A
   dedicated ladder lane would have to download, checksum-pin and store every
   opponent binary + NNUE file (see §4) — engineering not spent this cycle because
   the primary gate is unmet (running a full ladder cannot make the release
   eligible) and the efficiency rules forbid spending most games on it.
2. Established engines (Stockfish, Berserk, Ethereal, RubiChess, Koivisto) are
   ~3500–3650 on CCRL 40/4 4-CPU lists [1](https://computerchess.org.uk/4040/rating_list_all.html)
   [2](https://www.computerchess.org/). StockBear is an early development engine
   (dev5 measured only +64.7 Elo over its own dev4 predecessor at 40+4 ms). A
   direct match at equal 40+4 would be **saturated (~0% score)** and carry no
   rating information. The mission requires a pilot to find a non-saturated
   anchor that brackets StockBear's strength; that pilot was not run.
3. No absolute pool rating for dev5 was measured, so the numeric gap to a
   "3,000 Elo" target is **unknown and is not estimated**. Published CCRL/CEGT
   numbers are contextual anchors only, explicitly NOT interchangeable with this
   ladder's time control, hardware, engine population and methodology.

## 1. Opponent selection (researched, verifiable identities)

Candidate anchor families and their provenance (identity to be SHA-pinned before
use; no opponent was silently substituted):

| engine | version (candidate) | source | license | notes |
|---|---|---|---|---|
| Stockfish | 17.1 / 17 / 16.1 | https://github.com/official-stockfish/Stockfish | GPL-3.0 [1](https://github.com/official-stockfish/Stockfish) | needs NNUE network (ODbL-trained data); `UCI_LimitStrength`/`Skill Level` or node cap for a non-saturated anchor |
| Berserk | 14 / 20250606 | github.com/jhonnold/berserk | GPL-3.0 | NNUE; ~3627 CCRL [3](https://computerchess.org.uk/4040/rating_list_all.html) |
| Ethereal | 14.25 / 14.00 | github.com/AndyGrant/Ethereal | GPL-3.0 | ~3578–3600 CCRL [1](https://computerchess.org.uk/4040/rating_list_all.html) |
| RubiChess | 20240112 | github.com/Matthies/RubiChess | GPL-3.0 | ~3600 CCRL [1](https://computerchess.org.uk/4040/rating_list_all.html) |
| Koivisto | 9.0 | https://github.com/Luecx/Koivisto | GPL-3.0 [5](https://github.com/Luecx/Koivisto) | ~3560 CCRL [2](https://www.computerchess.org/) |

For every opponent the ladder must record: name, version, source URL, exact
release/commit, executable SHA-256, NNUE/network SHA-256, build flags, runtime
options, license, CPU compatibility, and use immutable binaries throughout.
**Do not copy Stockfish (or any engine) source, networks, or weights into the
StockBear codebase** — opponents/teachers only, StockBear source stays independent.

## 2. Pilot to find informative anchors (to be run first)

Run a small 40+4 ms, hash 16, 1-thread pilot of dev5 against a **strength-limited**
reference (e.g. Stockfish with `UCI_LimitStrength=true` at several `Skill Level`
values, or a fixed low node/movetime cap), plus a weak open-source engine, to find
the pair of anchors whose scores against StockBear are in the informative
0.2–0.8 band. Only then allocate decisive ladder games primarily to opponents
that bracket StockBear. Wasting most games on ~0% or ~100% opponents is
forbidden. Record exact handicap settings so the anchor is reproducible.

## 3. Rating methodology (reproducible, not yet executed)

- Consistent pool: same 40+4 ms, same hardware class (GitHub-hosted ubuntu-latest),
  same hash policy (16 MB), same thread count (1), same paired colour-reversed
  opening methodology, opening-cluster-aware statistics, both dev5 and the dev6
  candidate in the SAME pool.
- Draw-aware multi-opponent model: **Bradley-Terry-Davidson** (explicit draw
  parameter) or a validated equivalent, fitted by maximum likelihood on the
  game-level results with an opening-cluster bootstrap for 95% CIs.
- Report: estimated internal ladder rating + 95% CI per engine, games per
  pairing, opponent-specific score and Elo difference, rating-pool coverage,
  model fit / residual diagnostics, and leave-one-opponent-out sensitivity.
- Clearly label the result a **pool-specific internal rating** (this hardware,
  these exact binaries, 40+4 ms), not a universal/CCRL/FIDE-comparable rating.

## 4. Reproducible ladder lane (design, not yet built)

Reuse `.github/workflows/dev6-lane.yml`'s download-and-pin pattern: a job fetches
each official release asset from the runner (which has full internet), verifies
it against the publisher's checksums, records executable + network SHA-256, pins
them under `benchmarks/binaries/external/` (gitignored large binaries; immutable
SHA-manifest committed), and runs `scripts/tournament.py` for each pairing.
A committed `scripts/fit_ladder.py` performs the BTD fit and bootstrap. All
results (JSONL/PGN/CSV/manifests) committed under `benchmarks/exp-runs/exp0030-ladder/`.

## 5. The one real anchor that exists (INTERNAL, not external)

The immutable in-repo dev4 binary `benchmarks/binaries/stockbear-dev4-1c5b61a7`
(SHA-256 `1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae`,
bench `243f9a1c1ba5b36f`) is an exact, reproducible predecessor. exp-0024
measured the **exact released dev5** at champion config at **+64.7 [+57.5,+72.0]
Elo vs dev4** (6600 games, 40+4 ms) — a real cross-version anchor on a
StockBear-internal scale. This is NOT an external rating and is NOT on a
3000-Elo absolute scale; it is the only numerically measured anchor available and
is included so a future cycle can chain external anchors onto it.

## 6. What completion requires (user decision / future work)

1. A decision to spend a dedicated free-runner ladder batch (binaries + NNUE
   download, exact SHA pinning, pilot, decisive pairings, BTD fit) — estimated
   several thousand games, all free compute but a separate experiment identity
   (exp-0030+), pre-registered before results.
2. A clearly specified reference pool (opponent set + handicaps + exact binaries)
   so any "3,000 Elo" statement can name the pool, opponents, time control,
   hardware, versions and statistical uncertainty. Until such a measurement
   exists, **no claim that StockBear has any absolute rating, and no claim that
   it is at/near 3,000 Elo, is made.**

See `docs/DEV6_3000_ROADMAP.md` for the evidence-driven staged plan.
