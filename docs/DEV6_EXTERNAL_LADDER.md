# v0.1.0-dev6 — External rating ladder: methodology, opponent dossier, and status

## Status: NOT COMPLETED (PARTIAL / BLOCKED)

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
