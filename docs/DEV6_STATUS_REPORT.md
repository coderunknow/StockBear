# StockBear v0.1.0-dev6 — CURRENT STATUS REPORT (authoritative)

**Date:** 2026-11-03 (Asia/Bangkok) · **Branch:** `arena/3e6dd5b6-stockbear`
**Final source SHA:** `864d6d71f766c6e9b1969b8368b8f9929ba97a45` (LOCAL, unpushed)
**Report commit:** adds only this document. `origin/main` `6e7c2e02881faf93a84990a8345c41ad28bcae11`;
historical pushed head `797f5cbed45433622a54044163d91c73dbd22b75`. `VERSION=0.1.0-dev6`;
**no dev7**, no new version, dev1–dev5 tags unchanged, no PR.

## 1. FINAL STATUS — BLOCKED — NOT COMPLETE (mission ACTIVE)

Acceptance criteria are **NOT** satisfied. The unchanged formal gates of
`docs/DEV6_PREREG.md` §8 take precedence over every informal summary. No
strength claim, no PR, no merge, no tag, no release, no dev7. This is not a
termination after a failed experiment: the mission remains active, the Failure
Ledger is append-only and current, and the exact next action is in §12.

The blocking condition is **measurement infrastructure**, not a lack of
experimentation: on this shared 2-vCPU sandbox, decisive fixed-time matches are
clock-noise-confounded (exp-0030 E4: `-22.6 [-47.4,+2.0]` with 5 TIME_FORFEIT
events). Isolated CI runners and final-source CI require an authorized `git
push`, which has NOT been performed. All work below is local.

### Status taxonomy (explicit)

| Item | Status | Evidence |
|---|---|---|
| Historical dev6 six-feature candidate vs exact dev5 | **FAIL** | `-17.0 [-21.4,-12.6]` combined; batch A `-17.8 [-24.1,-11.5]`, B `-16.2 [-22.4,-10.0]`; ablation ≈ −58 Elo |
| Historical +33.0 Elo `params_abc` control | **INVALID MEASUREMENT** | toolchain-induced (ubuntu-22.04 vs ubuntu-24.04); exp-0030 E1–E3 |
| Gate 1 (>= +75 **and** 95% LCB > +50, both batches positive) | **FAIL / NOT MET** | no candidate reaches it |
| Gate 2 (two independent preregistered datasets) | **FAIL / NOT MET** | no fixed-time candidate |
| Gate 3 (nulls compatible with zero) | **PASS** (historical) | `+0.6 [-9.5,+10.7]`, `-2.5 [-12.8,+7.7]`, combined `-0.9 [-8.1,+6.2]` |
| Gate 4 (correctness + exact packaged binary tested) | **NOT RUN / NOT MET** | no final-source CI; no packaged candidate artifact |
| M0.1 reproducible build environment, Track A/B | **PASS** | exp-0030 E1–E5 |
| M0.2 external ladder implemented + fitted | **PASS (QUALIFIED)** | exp-0031/0032/0032b; subject ordering INCONCLUSIVE |
| exp-0031 pilot (anchors) | **PASS** | 5 informative anchors, 0 forfeits |
| exp-0032 decisive ladder + BTD | **PASS with documented limitation** | 3,186 games, `nu=0.190`, RMSE 0.0328 |
| exp-0032b paired sensitivity | **PASS** (diagnostic) | confound confirmed; star subject ordering unreliable |
| exp-0033 razoring | **FAIL (REJECTED)** | `-25.88 [-36.00,-15.80]` |
| exp-0034 bad-capture pilot | **PASS (ADVANCE)** | `+20.49 [+2.12,+38.97]` |
| exp-0035 bad-capture confirmation | **CONFIRMED — fixed-node only** | `+27.10 [+15.94,+38.33]` |
| Decisive FIXED-TIME confirmation vs exact dev5 | **NOT RUN** | needs isolated runners (authorization) |
| Remote final-source CI on exact final SHA | **NOT RUN** | no push; local equivalents PASS |
| Independent final audit | **PASS** | 179 stored values re-verified from raw JSONL |
| Absolute / CCRL-calibrated Elo; gap to 3,000 | **NOT MEASURED / NOT CALIBRATED** | explicitly not claimed |

## 2. Baseline / candidate binary identities

| role | path | SHA-256 |
|---|---|---|
| Exact released dev5 (Track B, immutable, never rebuilt) | `benchmarks/binaries/stockbear-dev5-release` | `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918` |
| A1 dev5 source rebuild (Track A, same toolchain) | `build-dev5/stockbear` | `214cbed002e58fbc94d74a089491bba94634e9e8d06b782992548fdacaa9b501` |
| A2 dev6 source rebuild (exp-0030) | `build-cand/stockbear` | `28b40cd691cc4c2b892aad27f42f4c62b50962e0d8183b9fdc339e1563d66538` |
| exp-0033 candidate (razoring switch) | `build-exp0033/stockbear` | `c412125179d5873ec4ae5cb4a06c728dc081986724666e27f8cad241fa8c57b3` |
| **exp-0034/0035 candidate** (bad-capture switch) | `build-exp0034/stockbear` | `075ec955a65acad4624cc6d3f4998763aaa7b968e4d01a27e73cd9dfd4c77d82` |
| dev4 pinned predecessor | `benchmarks/binaries/stockbear-dev4-1c5b61a7` | `1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae` |

Official dev5 is **never** called a rebuild. Champion config everywhere:
`EvalParams=research-data/params_abc.txt` (SHA
`8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be`) +
`TTEval=true`, Hash 16 MB, Threads 1.

## 3. Source changes in this continuation

- Prior cycle (already committed, NOT restored): six zero-gated extended eval
  IDs (`RookOn7th`, `KnightOutpost`, `BackwardPawn`, `PawnChain`,
  `ConnectedPassed`, `RookBehindPassed`) with `gExtendedEval` gating — measured
  REGRESSION, left zero, never silently re-enabled.
- New: `SearchParams::razoring` finally implemented (exp-0033, **default OFF**,
  frozen margin schedule `{0,125,175,300}` cp) and exposed as UCI `Razoring`.
  **REJECTED, not promoted to default.**
- New: `SearchParams::badCapturePruning` (exp-0034/0035, **default OFF**): skip
  non-hash captures with `SEE < -100` cp at depth ≤ 3 in non-PV / non-check /
  non-mate-window nodes, reusing SEE already computed by `score_moves()`;
  UCI `BadCapturePruning`; portable fallback when `SB_SEE_CACHE` is off.
- `bench --param` accepts both switches; `params_text` records them.
- New scripts: `dev6_build_matrix.py`, `dev6_opponent_manifest.py`,
  `dev6_ladder_pilot.py`, `dev6_ladder.py`, `fit_ladder.py`,
  `dev6_ladder_paired.py`, `dev6_exp0033.py`, `dev6_exp0034.py`,
  `dev6_exp0035.py`, `dev6_audit.py`; preregs
  `DEV6_PREREG_EXP0030/0031/0033/0034/0035.md`; docs/ledger/THIRD_PARTY.
- **All default builds remain bit-identical to dev5**: `bench --depth 4`
  `243f9a1c1ba5b36f`, `bench --depth 16` `a14ab62224f837e5`, `bench --depth 12
  --params params_abc` `e45fa2ec2287eb41`. StockBear remains an independent
  C++ implementation; Stockfish was used ONLY as an opponent/benchmark, never
  as a source-code base.

## 4. Build / toolchain / measurement provenance (M0.1, exp-0030)

Linux 6.1.158+ x86_64, glibc 2.36, Intel Xeon 2.60 GHz
(popcnt/bmi2/avx2/abm), 2 vCPU / 3.9 GB; GCC 12.2.0-14+deb12u1, GNU ld 2.40,
CMake 4.4.4, Ninja; `-DCMAKE_BUILD_TYPE=Release -G Ninja
-DCMAKE_CXX_FLAGS="-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4"`,
**no `-march=native`**. Full hashes/build logs in
`benchmarks/dev6-baseline/build_matrix.json`,
`benchmarks/exp-runs/exp0030-build-integrity/`.

E1 all three binaries share all three bench signatures. E2 12/12 fixed-node
bench CSV rows byte-identical A1 vs A2. E3 best-of-3 NPS A2/A1 `0.9765` inside
frozen `[0.97,1.03]`, B/A1 `0.9906`. E4 local fixed-time control
`-22.6 [-47.4,+2.0]` with 5 TIME_FORFEIT events — CI includes 0 but confirms
shared-clock noise; **not strength evidence**. E5 PASS. Track A is a valid
controlled source-level comparison; Track B stays separate and immutable.

All strength screens after exp-0030 use **fixed-node** `go nodes 6000` ±15 %,
`--max-plies 240`, paired colour-reversed fresh openings, 40+4 ms clock present
but not used for adjudication — immune to the shared-clock confound.

## 5. Full strength results (two-sided opening-clustered CR1 95 % CIs)

| experiment | control | games | point Elo | 95 % CI | verdict |
|---|---|---|---|---|---|
| historical confirmation combined | dev6 six-feature vs exact dev5 | 13,200 | **−17.0** | [−21.4,−12.6] | FAIL |
| historical batch A | same | 6,600 | −17.8 | [−24.1,−11.5] | FAIL |
| historical batch B | same | 6,600 | −16.2 | [−22.4,−10.0] | FAIL |
| historical nulls | identical params | 2,200 | −0.9 | [−8.1,+6.2] | PASS |
| exp-0030 E4 | A2 vs A1 (matched toolchain, fixed-time) | 400 | −22.6 | [−47.4,+2.0] | integrity PASS, noisy |
| exp-0033 A | razoring ON vs OFF (same binary) | 1,200 | −16.54 | [−31.06,−2.09] | FAIL |
| exp-0033 B | same | 1,197 | −35.27 | [−49.40,−21.26] | FAIL |
| exp-0033 combined | same | 2,397 | **−25.88** | [−36.00,−15.80] | **REJECT** |
| exp-0033 context | razoring ON vs official dev5 | 400 | −28.87 | [−53.58,−4.45] | corroborating |
| exp-0034 A | bad-capture ON vs OFF (same binary) | 400 | +27.12 | [+1.47,+53.06] | PASS |
| exp-0034 B | same | 399 | +13.90 | [−12.41,+40.38] | PASS |
| exp-0034 combined | same | 799 | +20.49 | [+2.12,+38.97] | **ADVANCE** |
| exp-0035 A | bad-capture ON vs OFF (same binary) | 1,000 | +22.75 | [+7.28,+38.31] | PASS |
| exp-0035 B | same | 989 | +31.51 | [+15.40,+47.76] | PASS |
| **exp-0035 combined** | same | **1,989** | **+27.10** | **[+15.94,+38.33]** | **CONFIRMED (fixed-node only)** |
| exp-0035 Track A context | candidate ON vs same-toolchain dev5 rebuild | 600 | +19.19 | [−0.76,+39.28] | CI includes 0 |
| exp-0032b paired (illustrative) | dev5_official vs dev5_rebuilt, shared openings | 200 | +20.9 | [−13.6,+55.8] | INCONCLUSIVE |

All reported point estimates include uncertainty; no subset was selected, no
negative batch hidden, no game excluded except the documented
`UNADJUDICATED_MAX_PLIES` rule. **No fixed-time Elo for any new candidate has
been measured.** `+27.10` is a fixed-node, same-binary, single-switch effect on
this hardware — it is **not** a +75 gate pass and **not** a release-worthy
strength claim.

## 6. External ladder (M0.2) — opponents, versions, rating sources, TC, rating

Sources built from official `codeload.github.com` archives (no blocked release
CDN, no NNUE weights). Exact tag commits, source/binary SHA-256s, build
commands, UCI option sets and GPL-3.0 notices:
`benchmarks/dev6-baseline/external_opponents.json`,
`docs/DEV6_EXTERNAL_OPPONENTS.md`, `THIRD_PARTY.md`.

| opponent | version / commit | binary SHA-256 (prefix) | role |
|---|---|---|---|
| Stockfish 8 | `sf_8` `369eff437cc…` | `1f573009…` | ladder anchor |
| Stockfish 9 | `sf_9` `378c8bdbb8…` | `865ca811…` | ladder anchor |
| Stockfish 10 | `sf_10` `b4c239b625…` | `39a43e23…` | ladder anchor |
| Stockfish 11 | `sf_11` `c3483fa9a7…` | `59503c60…` | 6 skill levels (`Skill Level 0/4/8/12/16/20`) |
| Weiss 2.0 | `v2.0` `0db49c7270…` | `de9ab528…` | pinned for future fixed-depth/time diagnostics; **excluded** (no `go nodes`) |

Builds: `make -j2 build ARCH=x86-64-modern COMP=gcc` (SF), `make -j2 basic
CFLAGS="-std=gnu11 -O3 -flto=auto -mpopcnt -mbmi2 -DNDEBUG" CC=gcc` (Weiss);
GCC 12.2.0, no `-march=native`. Weiss **master** failed to compile (C++ enum in
C11 header); BBC excluded (no `go nodes`, no Makefile). Both recorded, neither
retried unchanged.

**TC:** fixed-node `6000` ±15 %, Hash 16, Threads 1, max 240 plies, paired
colour-reversed fresh openings — NOT 40+4 fixed time. exp-0031 pilot 400 games
found 5 informative anchors (SF11-L4/L8/L12/L16, dev4), 0 forfeits; 4-game
config smoke DISCARDED. exp-0032: 8 anchors × 5 subjects × 80 games = 3,200
games (3,186 adjudicated, 14 unadjudicated, 0 forfeits).

**Rating model:** draw-aware Bradley-Terry-Davidson MLE, `nu = 0.190`, mean-zero
scale `Elo_i = (400/ln10)·r_i`, 1,600 opening clusters, 1,000 cluster
bootstrap replicates, NLL 2101.9, per-cell residual RMSE 0.0328, full
leave-one-anchor-out sensitivity. Ratings (pool-specific INTERNAL, 95 % CI):

`sf8 +485.8 [+407.6,+602.0]`, `sf10 +330.8 [+270.1,+413.0]`,
`sf11-L20 +312.3 [+245.9,+387.4]`, `sf9 +301.9 [+243.6,+371.8]`,
`sf11-L16 -4.3 [-41.7,+33.5]`, `sf11-L12 -9.8 [-52.1,+31.1]`,
`sf11-L8 -59.0 [-94.5,-24.9]`, `dev6_champion -169.0 [-210.6,-134.1]`,
`dev5_rebuilt -173.9 [-214.7,-136.3]`, `dev6_failed -184.7 [-227.5,-149.7]`,
`dev4 -197.9 [-238.4,-162.3]`, **`dev5_official -205.0 [-246.8,-165.7]`**,
`sf11-L4 -427.4 [-479.7,-388.1]`.

**Rating sources / qualifications:** SF11 `UCI_Elo`/`Skill Level` are the
engine's OWN approximate internal strength limiters
(`E = 1346.6 + 143.4·level^0.806`, time-seeded `Skill::pick_best`, not bitwise
reproducible) — **not** certified CCRL/CEGT/FIDE ratings. Published CCRL 40/4
figures (~3500–3650 for top engines) are contextual only. A rough affine
context fit to SF11 `UCI_Elo` gives slope 1.62, intercept 2449.8, anchor
residual SD **199 Elo**, dev5 ≈ 2118 "context Elo" — explicitly marked
**NOT DEFENSIBLY CALIBRATED**, with unknown and likely large systematic error.
**No absolute Elo, no CCRL equivalence, and NO numeric gap-to-3000 claim.**
3,000 Elo remains a long-term strategic target only.

**Confound, disclosed:** exp-0032 gave each cell a different opening slice, so
cross-subject comparisons mix strength with slice difficulty; the fitted
`dev5_official`/`dev5_rebuilt` gap contradicts exp-0030's bench-identical
binaries and leave-one-anchor-out ordering is unstable. exp-0032b (paired,
shared 100-opening suite, 2,000 games) confirmed the artifact and even
**reversed** the subject ordering. Therefore **the star ladder's ordering of
the five StockBear subjects is NOT reliable**; only anchor separation/coverage
is usable. SF11 skill anchors are non-monotonic in this pool (L12≈L16, large
L16→L20 jump); saturated cells retained. Fixed-node ≠ fixed-time: dev5 vs dev4
is `+12.2 [-22.7,+47.2]` here but `+64.7 [+57.5,+72.0]` in fixed-time exp-0024
on a different suite.

## 7. Experiments / preregistrations (all frozen before their results)

`docs/DEV6_PREREG.md` §8 (unchanged, authoritative),
`docs/DEV6_PREREG_EXP0030.md`, `DEV6_PREREG_EXP0031.md` (§6 transparency
corrections, append-only), `DEV6_PREREG_EXP0033.md`,
`DEV6_PREREG_EXP0034.md`, `DEV6_PREREG_EXP0035.md`. Deviations are disclosed,
never silently absorbed: pilot match seeds `2026110710..0719` vs frozen
`2026110701..0710` (clerical); exp-0032 used 8 anchors/5 subjects rather than
the drafted role assignment (3,200 games ≥ 1,600 target, graph still connected,
dev5 and dev6 both present). No acceptance criterion, tolerance, informative
band, statistic or decision rule was changed post-hoc. Two result-processing
defects (missing `pair_openings`, unadjudicated `None` pairs) were found, fixed
and disclosed in the ledger; no result JSON from a crashed run was used.

## 8. CI / engineering correctness

- Local Release (tests + `STOCKBEAR_REQUIRE_PYTHON_TESTS=ON`): **11/11 PASS**.
- Local Debug + ASan/UBSan: **11/11 PASS**.
- Independent python-chess eval-feature oracle: 600 positions / 43,200 checks /
  **0 mismatches** (re-run for exp-0033 and exp-0034 binaries).
- Search determinism: 3× `bench --depth 12` identical `e45fa2ec2287eb41`.
- Default-off bench signatures bit-exact vs dev5 (§3). UCI handshake and both
  new `check` options verified; no illegal moves, UCI failures, crashes or
  TIME_FORFEIT events in any fixed-node screen.
- Historical remote CI `41646472979` succeeded on `797f5cb` (9 jobs); decisive
  lane `41638608427` succeeded (17 jobs). **No CI has run on any current local
  commit** — remote final-source CI tied to the exact final SHA is **NOT RUN**
  and requires an authorized push. Clang/Windows/TSan matrix jobs were not
  reproducible locally (no clang); recorded as a limitation.

## 9. Independent final audit

`scripts/dev6_audit.py` re-parses EVERY raw `match.jsonl` from scratch (exp-0031,
0032, 0032b, 0033, 0034, 0035) and compares W/D/L, game counts and scores
against the stored summaries: **179 stored values verified, AUDIT PASS, 0
mismatches**. Independent Elo-from-score cross-checks: exp-0033 −25.99 vs
stored CR1 −25.88; exp-0034 +20.90 vs +20.49; exp-0035 +26.43 vs +27.10.
Full CI/audit on a passing candidate is still **NOT RUN**.

## 10. Failure Ledger / docs currency

Append-only `benchmarks/FAILURE_LEDGER.md` now contains exp-0030 through
exp-0035 (including the exp-0032b sensitivity), with IDs, hypotheses,
identities, SHAs, build env, config, prereg, commands, raw paths, stats,
outcomes, root causes, lessons, non-repeatable approaches and next experiments.
Updated: `docs/DEV6_EXTERNAL_LADDER.md` (§0 supersedes the preserved Appendix A
design dossier), `DEV6_EXTERNAL_LADDER_REPORT.md`, `DEV6_EXTERNAL_OPPONENTS.md`,
`DEV6_3000_ROADMAP.md`, `DEV6_REPORT.md` (superseding notice), `THIRD_PARTY.md`
(GPL notices), `CHANGELOG.md`, `DESIGN_LOG.md`, `AGENTS_LOG.md`. Historical
verdicts were never rewritten — superseding notices were appended.

## 11. Unresolved limitations (explicit)

1. Gates 1/2/4 UNMET; no fixed-time candidate result, no exact packaged
   candidate artifact tested, no final-source CI. Gate 3 passed only for the
   historical nulls.
2. `+27.10 [+15.94,+38.33]` is a **fixed-node, same-binary, single-switch**
   effect. It is not transferable to a fixed-time Elo (exp-0030 clock noise;
   the historical +33 was a toolchain artifact). Track A context
   `+19.19 [-0.76,+39.28]` has a CI that includes zero.
3. `BadCapturePruning` remains **default OFF**; enabling it by default would
   change the shipped bench signature and require a fresh artifact + CI cycle.
4. Ladder subject ordering unreliable (§6); calibration NOT DEFENSIBLY
   CALIBRATED; no absolute Elo / gap-to-3000.
5. Local sandbox 2 vCPU shared clock; Clang/Windows/TSan CI jobs not
   reproducible here; SF11 skill limiter is time-seeded (games not bitwise
   reproducible but reproducible from `--seed` + node budget).
6. No remote writes since the ASK directive; all commits after historical
   `797f5cb` are local and unpushed.

## 12. Authorization status and EXACT next action

**Authorization: ASK.** Since the ASK directive: **zero** `git push`, zero PR,
zero merge, zero tag, zero release, zero dev7, zero modification to the dev5
tag/artifact. The last push (`797f5cb`) predates the directive and is NOT future
authorization.

**Terminal state: BLOCKED — NOT COMPLETE (mission ACTIVE).** Not SUCCESS, not
READY FOR AUTHORIZATION for a release: gates are unmet.

**Exact next action (requires explicit approval):** push the current local
commits `4ba6811..864d6d7` (plus the report-only commit) **only** to
`arena/3e6dd5b6-stockbear`, then run on isolated CI runners (a) final-source CI
on the exact head, (b) a preregistered fixed-time confirmation of exp-0035's
`BadCapturePruning=true` candidate against the exact released dev5 with
unchanged Gates 1–4, the exact packaged candidate artifact, both independent
batches, clean nulls and verified-disjoint opening clusters — with a new
experiment ID and a prereg frozen before results. If that fails, the
persistent-continuation protocol applies: classify, inspect raw evidence,
root-cause, ledger append, rank materially different approaches, preregister
the next experiment. No PR/merge/tag/release is implied by this push request.
