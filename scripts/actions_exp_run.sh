#!/bin/bash
# Run one pre-registered experiment job (see benchmarks/exp-runs/trigger.json)
# on a GitHub-hosted runner. Usage: actions_exp_run.sh '<job-json>'
#
# The job is fully self-describing: it builds the immutable dev4 baseline
# from tag v0.1.0-dev4 and the candidate from the current checkout, verifies
# both binaries by SHA-256 and bench signature, runs the requested
# null/match with fixed time control, and writes everything under
# benchmarks/exp-runs/<id>/ (uploaded as a workflow artifact).
#
# Job schema (all keys required unless noted):
#   id                  string, directory name under benchmarks/exp-runs/
#   candidate_options   list of "Name=Value" UCI options for engine A
#                       (the candidate built from THIS checkout)
#   baseline            "dev4" (tag v0.1.0-dev4 build) or "candidate"
#   baseline_options    list of "Name=Value" UCI options for engine B
#   games               int, total games (even; paired openings)
#   seed                int, tournament shuffle seed
#   openings            path to the opening suite (committed file)
#   base_ms / inc_ms    optional, default 40 / 4
#   hash / threads      optional, default 16 / 1
#   max_plies           optional, default 240
#   null_games          optional int, baseline-vs-baseline null match, seed = seed+1
#   ctest               optional bool, run the candidate's ctest first
#   note                optional free text recorded in the manifest
set -euo pipefail
cd "$(dirname "$0")/.."
JOB_JSON="$1"

python3 -m venv .venv
.venv/bin/pip -q install cmake ninja chess numpy

ID=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["id"])' "$JOB_JSON")
OUT="benchmarks/exp-runs/$ID"
mkdir -p "$OUT"

field() { python3 -c 'import json,sys; j=json.loads(sys.argv[1]); print(json.dumps(j.get(sys.argv[2], sys.argv[3])))' "$JOB_JSON" "$1" "$2"; }
opt_args() { # $1 = options list json array, $2 = prefix (--a-option/--b-option)
  python3 -c 'import json,sys; [print(f"{sys.argv[2]}={o}") for o in json.loads(sys.argv[1])]' "$1" "$2"
}

CAND_OPTS=$(field candidate_options '[]')
BASE=$(field baseline '"dev4"')
BASE_OPTS=$(field baseline_options '[]')
GAMES=$(field games '0')
SEED=$(field seed '0')
OPENINGS=$(field openings '""')
BASE_MS=$(field base_ms '40'); INC_MS=$(field inc_ms '4')
HASH=$(field hash '16'); THREADS=$(field threads '1'); MAXPLIES=$(field max_plies '240')
NULL_GAMES=$(field null_games '0'); CTEST=$(field ctest 'false')
NOTE=$(field note '""')

echo "=== job $ID ==="
echo "candidate_options=$CAND_OPTS baseline=$BASE baseline_options=$BASE_OPTS games=$GAMES seed=$SEED openings=$OPENINGS null_games=$NULL_GAMES"

# ---- immutable dev4 baseline from the tag (pinned: plain Release, sha 1c5b61a7...) ----
if [ "$BASE" = "dev4" ] || [ "$NULL_GAMES" != "0" ]; then
  rm -rf /tmp/dev4src
  git worktree add --force /tmp/dev4src v0.1.0-dev4 > /dev/null
  (cd /tmp/dev4src && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release > /dev/null \
     && cmake --build build -j 4 --target stockbear > /dev/null)
  DEV4_BIN=/tmp/dev4src/build/stockbear
  DEV4_SHA=$(sha256sum "$DEV4_BIN" | cut -d' ' -f1)
  DEV4_BENCH=$("$DEV4_BIN" bench 2>&1 | tail -1)
  echo "dev4 sha256=$DEV4_SHA bench=$DEV4_BENCH"
  if [ "$DEV4_SHA" != "1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae" ]; then
    echo "FATAL: dev4 baseline sha mismatch" >&2; exit 1
  fi
  if [ "$DEV4_BENCH" != "243f9a1c1ba5b36f" ]; then
    echo "FATAL: dev4 baseline bench mismatch" >&2; exit 1
  fi
fi

# ---- candidate from this checkout (champion flags) ----
cmake -S . -B build-exp -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS="-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1" > /dev/null
cmake --build build-exp -j 4 --target stockbear > /dev/null
CAND_BIN=build-exp/stockbear
CAND_SHA=$(sha256sum "$CAND_BIN" | cut -d' ' -f1)
CAND_BENCH=$("$CAND_BIN" bench 2>&1 | tail -1)
echo "candidate sha256=$CAND_SHA bench=$CAND_BENCH"
if [ "$CAND_BENCH" != "243f9a1c1ba5b36f" ]; then
  echo "FATAL: candidate bench signature changed (must stay 243f9a1c1ba5b36f)" >&2; exit 1
fi

if [ "$CTEST" = "true" ]; then
  cmake --build build-exp -j 4 > /dev/null   # full target so ctest finds the binary
  (cd build-exp && ctest --output-on-failure | tail -5)
fi

if [ "$BASE" = "dev4" ]; then B_BIN="$DEV4_BIN"; else B_BIN="$CAND_BIN"; fi

A_OPT_ARGS=(); while IFS= read -r line; do [ -n "$line" ] && A_OPT_ARGS+=("$line"); done < <(opt_args "$CAND_OPTS" "--a-option")
B_OPT_ARGS=(); while IFS= read -r line; do [ -n "$line" ] && B_OPT_ARGS+=("$line"); done < <(opt_args "$BASE_OPTS" "--b-option")

SUITE_SHA=$(sha256sum "$OPENINGS" | cut -d' ' -f1)
CPUINFO=$(grep -m1 'model name' /proc/cpuinfo || true)
NPROC=$(nproc)

write_manifest() {
python3 - "$JOB_JSON" "$OUT/manifest.json" <<'EOF'
import json, sys, platform, datetime, os
job = json.loads(sys.argv[1])
manifest = {
    "job": job,
    "ran_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "runner": {
        "name": os.environ.get("RUNNER_NAME", ""),
        "arch": os.environ.get("RUNNER_ARCH", ""),
        "os": os.environ.get("RUNNER_OS", ""),
        "nproc": os.environ.get("NPROC", ""),
        "cpuinfo": os.environ.get("CPUINFO", ""),
        "note": "GitHub-hosted runner, dedicated VM per job (CPU-isolated); public repo => no billing",
    },
    "platform": platform.platform(),
    "git_head": os.popen("git rev-parse HEAD").read().strip(),
    "git_head_subject": os.popen("git log -1 --format=%s").read().strip(),
    "dev4_sha256": os.environ.get("DEV4_SHA", ""),
    "dev4_bench": os.environ.get("DEV4_BENCH", ""),
    "candidate_sha256": os.environ.get("CAND_SHA", ""),
    "candidate_bench": os.environ.get("CAND_BENCH", ""),
    "opening_suite": job["openings"],
    "opening_suite_sha256": os.environ.get("SUITE_SHA", ""),
    "build_flags": "cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS='-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1' (candidate); plain Release (dev4 tag)",
}
with open(sys.argv[2], "w") as f:
    json.dump(manifest, f, indent=2)
EOF
}
export DEV4_SHA DEV4_BENCH CAND_SHA CAND_BENCH SUITE_SHA CPUINFO NPROC
write_manifest

run_match() { # name games seed engineA engineB
  local name=$1 games=$2 seed=$3 ea=$4 eb=$5
  echo "=== match $name: $games games seed $seed ==="
  .venv/bin/python scripts/tournament.py --engine-a "$ea" --engine-b "$eb" \
    "${A_OPT_ARGS[@]}" "${B_OPT_ARGS[@]}" \
    --games "$games" --base-ms "$BASE_MS" --inc-ms "$INC_MS" --hash "$HASH" \
    --threads "$THREADS" --max-plies "$MAXPLIES" \
    --openings "$OPENINGS" --seed "$seed" \
    --pgn "$OUT/$name.pgn" --jsonl "$OUT/$name.jsonl" --csv "$OUT/$name.csv" 2>&1 \
    | grep -E "^games|clustered|paired|sprt|naive" | tee "$OUT/$name.report.txt"
}

if [ "$NULL_GAMES" != "0" ]; then
  # null: candidate vs candidate (or baseline vs baseline) — same binary both sides
  run_match "null" "$NULL_GAMES" "$((SEED + 1))" "$CAND_BIN" "$CAND_BIN"
fi
run_match "match" "$GAMES" "$SEED" "$CAND_BIN" "$B_BIN"

echo "=== job $ID done ==="
ls -la "$OUT"
