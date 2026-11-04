# exp-0042 — max-gain delta pruning in quiescence: CLOSED / ABANDONED

Two fully preregistered Tier-1 40+4 ms isolated-VM runs. No pool/merge of
results was performed: the screen stayed exploratory and only the separate
confirmation decided the experiment (see the addendum's explicit no-pooling
rule). `docs/DEV6_PREREG.md` §8 gates are UNCHANGED.

## Frozen registrations
| document | SHA-256 |
|---|---|
| `docs/DEV6_PREREG_EXP0042.md` (before ANY evaluation game) | `3345325ce3e4fdc98501410bd7fcea2b3b5e7e1aa6b9d6a8139e4ced6b29c62b` |
| `docs/DEV6_PREREG_EXP0042_ADDENDUM.md` (before ANY additional game) | `21b0b1e6b425c8a7083f674d5019f6329dbe57286efcdbc1dedc8c719669bf74` |

## Identity / provenance
| item | screen | bounded confirmation |
|---|---|---|
| exact source SHA | `efd2f22ddf327c8462c8839a2f5bbbcebfd92609` | `ec223feaaa444c24cc135aecdc8fec326d210783` |
| built == packaged == tested binary SHA-256 | `d4a2345149d132995a93ad707c566df1df9b54ea0426ecc77f284d8052b6b3fe` | `d4a2345149d132995a93ad707c566df1df9b54ea0426ecc77f284d8052b6b3fe` |
| frozen build flags | `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4` | `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4` |
| Tier-1 benchmark run | `41802986830` (4 isolated VMs, SUCCESS) | `41804818965` (4 isolated VMs, SUCCESS) |
| Tier-1 export run | `41804342869` | `41806227744` |
| CI on exact source | `41802986854` SUCCESS | `41804818984` SUCCESS |
| artifact IDs / bytes | `13308737307`/947936 B, `13308393701`/951531 B, `13308099707`/730819 B, `13307579813`/734453 B | `13310000209`/732571 B, `13309607699`/739388 B, `13309209799`/948014 B, `13308929953`/949253 B |
| local checksum re-verification | 4/4 SHA256SUMS, 0 failures | 4/4 SHA256SUMS, 0 failures |
| control | FIXED TIME 40+4 ms, Hash16/Threads1/240 plies, NO `--nodes` | identical |

Immutable dev5 baseline `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`.
ONE binary, single default-off switch `MaxGainDelta=true` versus `false`; both
arms `EvalParams=research-data/params_abc.txt` and `TTEval=true`; identical
clocks. Screen suites seed `2026112801`, confirmation suites seed `2026113001`,
each 1,400 openings with programmatic ZERO overlap against all earlier suites.
Raw PGN/JSONL/CSV/summaries/audit/fingerprint/manifest/SHA256SUMS/UCI/run.log
and the exact packaged `.tar.gz` are mirrored under
`benchmarks/exp-runs/tier1-export/run-41802986830/` and
`.../run-41804818965/`.

## Screen — INCONCLUSIVE (not a failure, not a success)
Stage-0 validity null 400 games `−2.6058 [−21.9076,+16.6798]`, 0
forfeits/illegal/UCI failures, CI includes 0 -> PASS. batchA
`+4.8644 [−10.1879,+19.9350]`, batchB `+0.3488 [−14.5041,+15.2030]`, null
`+17.4738 [−1.9909,+37.0488]` (CI includes 0; noisy point estimate disclosed).
Frozen combined `+2.6110 [−7.9556,+13.1825]` on 1,998 games / 998 clusters,
independent Elo-from-score +2.7823, seeded cluster bootstrap
`[−8.0085,+12.8868]`, independent raw-JSONL audit 44/44 AUDIT PASS. ADVANCE
FALSE (point < +20, LCB < 0), CLOSE FALSE (UCB +13.18 >= +10, point > 0) ->
the frozen §5 "more samples" clause was triggered.

## Bounded confirmation — CLOSE
Stage-0 validity null 400 games `+10.5851 [−8.5366,+29.7711]`, 0
forfeits/illegal/UCI failures, CI includes 0 -> PASS. batchA
`−4.1862 [−19.7858,+11.3966]`, batchB `−17.4914 [−33.1133,−1.9399]`, null
`−6.1113 [−24.7147,+12.4570]` includes 0. Frozen combined
`−10.8281 [−21.8567,+0.1787]` on 1,995 games / 995 clusters, independent
Elo-from-score −10.9753, seeded cluster bootstrap `[−21.8526,+0.0000]`,
independent raw-JSONL audit 44/44 AUDIT PASS. ADVANCE FALSE; CLOSE TRUE because
UCB +0.1787 < +10 AND point <= 0 -> **CLOSED, ABANDONED, not retuned**.
`MaxGainDelta` stays default OFF; `deltaMargin=200` stays frozen.

## Dataset disagreement (disclosed, not hidden)
Screen point +2.6110 and confirmation point −10.8281 differ by 13.44 Elo, but
their 95 % CIs overlap on `[−7.9556, +0.1787]`, so this is sampling variation,
not a material contradiction. Crucially the two datasets were NEVER pooled:
the addendum forbids it, so no post-hoc combining could manufacture a
significant result in either direction. Both datasets are reported in full.

## Root-cause classification and diagnosis
Class: **unsuitable hypothesis / search-eval interaction**, NOT an
implementation defect. Release ctest 11/11, ASan+UBSan ctest 11/11, exact
default-off bench/d16/d12 signatures, UCI default false, 3x determinism, 0
illegal moves / time forfeits / UCI failures across both runs. Profiling had
already shown the mechanism is LIVE but that it INCREASES fixed-depth nodes by
13.8 % (543,800 -> 618,920 at d12): returning stand-pat instead of a searched
capture value changes upstream alpha-beta decisions and ordering. The
confirmation shows those changed decisions lose tactical accuracy. This is the
fourth independent confirmation in the project that node-count / throughput
proxies do not predict fixed-time strength, and the second (after exp-0041)
that tightening a qsearch pruning decision does not pay for itself. Do NOT
retune `deltaMargin`, the gain formula or the original conservative check on
these results.

## Gate verdict (unchanged)
- **Gate 1 UNMET** — no >= +75 Elo point with two-sided opening-clustered LCB
  > +50 on two independent preregistered FIXED-TIME batches.
- **Gate 2 direction-supported**, **Gate 3 PASS** (both required nulls include
  zero; all four extra null arms in this experiment also include zero).
- **Gate 4 UNMET for a final candidate** — every experiment's packaged
  artifact/binary/CI linkage is complete and verified, but no final candidate
  release artifact exists.
- **Mission ACTIVE.** No strength claim, no PR/merge/tag/release/deploy/dev7.
