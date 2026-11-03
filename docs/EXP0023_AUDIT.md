# exp-0023 independent audit report (2026-11-03)

Auditor tool: `scripts/audit_exp0023.py` (committed; does **not** import
`scripts/match_stats.py` — every number below is recomputed from the raw
per-shard `match.jsonl` records with an independent implementation of the
CR1 clustered CI, the paired pentanomial estimate, SPRT, and the full
game accounting). Machine-readable output:
`benchmarks/exp-runs/exp0023-audit.json`.

## Verdict

**All checks pass; zero problems found. Gate re-derived from raw evidence:
LCB95 = +59.29 > +50 → MET.**

## What was verified

- **Raw evidence complete**: 12 shards x 550 game records = 6600 records
  present in `benchmarks/exp-runs/exp0023-shard01..12/match.jsonl` (plus the
  per-shard `match.csv`, `match.pgn`, `manifest.json`, `match.report.txt`).
  Game ids are 1..550 per shard. Null: 1100 records in `exp0023-null`.
- **Per-shard manifests**: candidate git_head = `737c6f4` (the frozen,
  pre-registered candidate) in every shard; dev4 baseline sha256
  `1c5b61a7…` and bench signature `243f9a1c1ba5b36f` asserted for BOTH
  binaries in every manifest; opening-suite sha256 `32537dd8…`; distinct
  seeds 2026110601..612 (null 2026110699); options
  `EvalParams=research-data/params_abc.txt` + `TTEval=true`; build flags
  `-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -march=native -flto=4`;
  TC 40+4 ms, hash 16 MB, threads 1, max-plies 240 — all match the
  pre-registration (`docs/EXP0023_PREREG.md`).
- **Suite integrity**: all 3300 distinct openings used across the shards are
  members of the preregistered suite `openings_exp0001_confirmation.txt`
  (sha256 `32537dd843e8cb1e…`, 2200 pairs). The suite file and the
  pre-registration doc are unmodified since the preregistration commit
  `737c6f4` (`git diff 737c6f4..HEAD` empty for both). The suite was first
  referenced by any trigger at `737c6f4` (committed 09:19:37Z); the decisive
  run 41610113495 was created 09:19:40Z — the pre-registration strictly
  predates the run, and no earlier run used the suite.
- **Pairing**: every pair shares one opening and the white engine alternates
  between the two distinct engine names across the two games (3300 pairs,
  colours reversed).
- **Statistics recomputed independently** (no shared code with the original
  pooling): 3282 pooled pairs, 1775 opening clusters, CR1 variance with
  Student-t(1774) critical value 1.98 → **+66.43168556793715 Elo,
  95 % CI [+59.29464952230903, +73.62455454285343]** — matches
  `exp0023-pooled.json` to full double precision (`cross_check.match =
  true`). Paired pentanomial +66.4 [+59.9, +73.0]; SPRT(0,5) LLR 30.74 →
  accept H1. Null (candidate vs candidate, 1100 g): −1.3 [−11.7, +9.2] —
  consistent with zero, i.e. no infrastructure bias.
- **Forfeits**: 0 in all 6600 games. Terminations: CHECKMATE 4653,
  THREEFOLD_REPETITION 1792, INSUFFICIENT_MATERIAL 124, FIFTY_MOVES 9,
  STALEMATE 3, UNADJUDICATED_MAX_PLIES 19.

## The 6599-vs-6600 reconciliation (resolved)

The pooled report prints `unadjudicated: 18`, and
2949 W + 1928 D + 1704 L + 18 = 6599, which looks one game short. The audit
shows this is a **pair-level vs game-level counting conflation, not a
missing game**:

- Game-level accounting from the raw records: 6600 games =
  **6581 adjudicated** (2949 W + 1928 D + 1704 L = 6581) + **19
  unadjudicated** games (termination `UNADJUDICATED_MAX_PLIES`), with
  0 forfeits. 6581 + 19 = 6600 exactly.
- The pooled figure 18 counts **unadjudicated pairs**, not games: exactly one
  pair had BOTH of its games reach max-plies, so pair-level 18 corresponds
  to game-level 19. No game is missing, no shard is short (each has exactly
  550), and no unfavourable observation was excluded — unadjudicated games
  are counted and reported, and excluded only from the W/D/L scores per the
  pre-declared policy.

## Failure ledger

`benchmarks/FAILURE_LEDGER.md` records exp-0023 as GATE PASSED and preserves
all earlier failed gates (dev5/dev6/dev7 confirmations, exp-0019/0020/0021
screens). No experiment was deleted; failed runs keep their raw records.
