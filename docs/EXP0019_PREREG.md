# exp-0019 pre-registration — margin / aspiration-window screening on GitHub-hosted runners

Date: 2026-11-03. Branch: `arena/daa69a3b-stockbear` (this commit).

## Hypothesis
The confirmed champion's eval params (`params_abc.txt`, sha
`8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be`) widen the
eval distribution ~7-9 % vs the dev4 default params (measured on 2159
self-play positions: |mean| eval 454/462 cp and std 707/719 vs 424/661;
p50 245/249 vs 220). The cp-denominated search margins (futility 110/depth,
reverse-futility 85/depth, qsearch delta 200) were calibrated for the dev4
eval scale, so with the tuned eval they are relatively ~8 % too tight.
Additionally, at 40+4 (depth 3-7, ~7k nodes/move) the aspiration initial
window of 16 cp may cause avoidable re-searches; a wider initial window
trades a little search efficiency for fewer failed windows.

## Implementation
`AspirationWindow`, `FutilityMargin`, `RevFutilityMargin`, `DeltaMargin` are
new UCI spin options (src/uci/uci.cpp, src/search/search.hpp, search.cpp).
Defaults are exactly the dev4 compile-time values (16/110/85/200), so a
default build is bit-identical: bench signature `243f9a1c1ba5b36f`, ctest
11/11 (verified locally on build-exp019, 2026-11-03).

## Conditions (all screens)
- Candidate: binary built from this commit, flags
  `cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1"`,
  bench asserted `243f9a1c1ba5b36f` at runtime; base options
  `EvalParams=research-data/params_abc.txt` + `TTEval=true` (the +47.5
  confirmed champion config), plus the variant option under test.
- Baseline: immutable dev4 binary from tag `v0.1.0-dev4`, sha256
  `1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae`, bench
  `243f9a1c1ba5b36f`, asserted at runtime.
- Match: 40+4 ms fixed time (int-ms wtime/btime, winc/binc 4), hash 16,
  threads 1, max-plies 240, openings `benchmarks/positions/openings_dev4.txt`
  (240 openings, used for prior screens; fresh untouched suites are reserved
  for confirmations), 480 games per screen, distinct seeds.
- Hardware: GitHub-hosted `ubuntu-latest` runner (public repo, no billing),
  dedicated VM per job = CPU-isolated; runner name/arch/CPU recorded in each
  job's manifest.json. Both engines of a match share one runner.
- Stats: opening-clustered CR1 two-sided 95 % CI (Student-t, G-1 df, logistic
  scale) via scripts/tournament.py + match_stats.py; SPRT(0,5) reported.
- Pipeline: `.github/workflows/exp-run.yml` (push-triggered on
  `benchmarks/exp-runs/trigger.json`), `scripts/actions_exp_run.sh`; results
  uploaded as artifacts and committed under `benchmarks/exp-runs/<id>/`.

## Jobs (each 480 g unless noted)
| id | variant option | seed |
|---|---|---|
| smoke-0002 | (champion only, 16 g) | 2026110400 |
| exp0019-null | champion vs champion, 480 g | 2026110410 |
| exp0019-base | none (reference) | 2026110401 |
| exp0019-aw8 | AspirationWindow=8 | 2026110404 |
| exp0019-aw32 | AspirationWindow=32 | 2026110402 |
| exp0019-aw48 | AspirationWindow=48 | 2026110403 |
| exp0019-fut140 | FutilityMargin=140 | 2026110405 |
| exp0019-fut170 | FutilityMargin=170 | 2026110406 |
| exp0019-rfut110 | RevFutilityMargin=110 | 2026110407 |
| exp0019-delta260 | DeltaMargin=260 | 2026110408 |

## Decision rule
Screens are selection-grade only if |effect| exceeds the ~±25 Elo screen
noise at 480 g AND the direction is mechanistically expected. Any variant
with point estimate ≥ +8 over exp0019-base on the same runner lane gets a
second screen on a different seed; only variants confirmed twice go into a
combined candidate for a fresh-suite 4400 g pre-registered confirmation.
No post-hoc selection: all jobs above run regardless of each other's
outcomes. Gate unchanged: LCB95 > +50 vs dev4 at 40+4 on a fresh suite.
