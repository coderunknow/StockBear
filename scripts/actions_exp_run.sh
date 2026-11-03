#!/bin/bash
# Run one pre-registered experiment job (see benchmarks/exp-runs/trigger.json)
# on a GitHub-hosted runner. Usage: actions_exp_run.sh '<job-json>'
#
# The job is fully self-describing: it builds the immutable dev4 baseline
# from tag v0.1.0-dev4 and the candidate from the current checkout, verifies
# both binaries by SHA-256 and bench signature, runs the requested
# null/match with fixed time control, and commits everything under
# benchmarks/exp-runs/<id>/ back to the branch (the sandbox cannot download
# workflow logs/artifacts, so the branch IS the results channel).
#
# Job schema (keys required unless noted):
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
#   null_games          optional int, candidate-vs-candidate null, seed = seed+1
#   ctest               optional bool, run the candidate's ctest first
#   build_flags         optional string, CMAKE_CXX_FLAGS override for the
#                       candidate (default: champion flags)
#   note                optional free text recorded in the manifest
set -uo pipefail
cd "$(dirname "$0")/.."
JOB_JSON="$1"
BRANCH="${GITHUB_REF_NAME:-arena/daa69a3b-stockbear}"

jget() { # key default: strings print raw, everything else JSON-encoded
  python3 - "$JOB_JSON" "$1" "$2" <<'EOF'
import json, sys
job = json.loads(sys.argv[1]); key = sys.argv[2]
try: default = json.loads(sys.argv[3])
except Exception: default = sys.argv[3]
v = job.get(key, default)
print(v if isinstance(v, str) else json.dumps(v))
EOF
}
opt_args() { # $1 = options list json array, $2 = prefix (--a-option/--b-option)
  python3 -c 'import json,sys; [print(f"{sys.argv[2]}={o}") for o in json.loads(sys.argv[1])]' "$1" "$2"
}

ID=$(jget id '"unnamed"')
OUT="benchmarks/exp-runs/$ID"
mkdir -p "$OUT"
exec > >(tee -a "$OUT/run.log") 2>&1
echo "=== job $ID start $(date -u +%FT%TZ) run=${GITHUB_RUN_ID:-local} job=${GITHUB_JOB:-local} branch=$BRANCH ==="

fail() {
  echo "FATAL: $*" | tee -a "$OUT/FAIL.txt"
  commit_and_push
  exit 1
}
trap 'echo "ERR at line $LINENO (status $?)" >> "$OUT/FAIL.txt"' ERR

commit_and_push() {
  git config user.email "exp-runner@stockbear.local"
  git config user.name "exp-runner"
  sleep 2   # let the `exec > >(tee ...)` process substitution flush run.log
  for attempt in 1 2 3 4 5 6; do
    git pull --rebase origin "$BRANCH" > /dev/null 2>&1 || git rebase --abort > /dev/null 2>&1 || true
    git add -A "benchmarks/exp-runs/$ID" 2>/dev/null || true
    if git commit --allow-empty -q -m "exp-run[$ID]: results (run ${GITHUB_RUN_ID:-local}, job ${GITHUB_JOB:-local})" 2>/dev/null; then
      if git push -q origin "HEAD:$BRANCH" 2>/dev/null; then
        echo "results pushed to $BRANCH"
        return 0
      fi
    fi
    echo "push attempt $attempt failed; retrying"
    sleep $((attempt * 7))
  done
  echo "WARN: could not push results for $ID" | tee -a "$OUT/FAIL.txt"
  return 1
}

python3 -m venv .venv
.venv/bin/pip -q install cmake ninja chess numpy || fail "pip install failed"
export PATH="$PWD/.venv/bin:$PATH"

CAND_OPTS=$(jget candidate_options '[]')
BASE=$(jget baseline '"dev4"')
BASE_OPTS=$(jget baseline_options '[]')
GAMES=$(jget games '0')
SEED=$(jget seed '0')
OPENINGS=$(jget openings '""')
BASE_MS=$(jget base_ms '40'); INC_MS=$(jget inc_ms '4')
HASH=$(jget hash '16'); THREADS=$(jget threads '1'); MAXPLIES=$(jget max_plies '240')
NULL_GAMES=$(jget null_games '0'); CTEST=$(jget ctest 'false')
BUILD_FLAGS=$(jget build_flags '"-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1"')
NOTE=$(jget note '""')

echo "candidate_options=$CAND_OPTS baseline=$BASE baseline_options=$BASE_OPTS games=$GAMES seed=$SEED openings=$OPENINGS null_games=$NULL_GAMES build_flags=$BUILD_FLAGS"

# ---- immutable dev4 baseline: the pinned binary committed in the repo ----
# (The gate's baseline is the exact v0.1.0-dev4 binary 1c5b61a7...; committing it
#  keeps runner matches literally on that binary instead of a rebuild whose
#  sha depends on the runner's compiler.)
if [ "$BASE" = "dev4" ] || [ "$NULL_GAMES" != "0" ]; then
  DEV4_BIN=benchmarks/binaries/stockbear-dev4-1c5b61a7
  [ -x "$DEV4_BIN" ] || fail "pinned dev4 binary missing: $DEV4_BIN"
  DEV4_SHA=$(sha256sum "$DEV4_BIN" | cut -d' ' -f1)
  DEV4_BENCH=$("$DEV4_BIN" bench 2>&1 | sed -n 's/.*signature //p' | tail -1)
  DEV4_D16=$("$DEV4_BIN" bench --depth 16 2>&1 | sed -n 's/.*signature //p' | tail -1)
  echo "dev4 sha256=$DEV4_SHA bench=$DEV4_BENCH bench-d16=$DEV4_D16"
  [ "$DEV4_SHA" = "1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae" ] || fail "dev4 baseline sha mismatch: $DEV4_SHA"
  [ "$DEV4_BENCH" = "243f9a1c1ba5b36f" ] || fail "dev4 baseline bench mismatch: $DEV4_BENCH"
  [ "$DEV4_D16" = "a14ab62224f837e5" ] || fail "dev4 baseline d16 signature mismatch: $DEV4_D16"
fi

# ---- candidate from this checkout ----
cmake -S . -B build-exp -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS="$BUILD_FLAGS" > /dev/null || fail "candidate configure failed"
cmake --build build-exp -j 4 --target stockbear > /dev/null || fail "candidate build failed"
CAND_BIN=build-exp/stockbear
CAND_SHA=$(sha256sum "$CAND_BIN" | cut -d' ' -f1)
CAND_BENCH=$("$CAND_BIN" bench 2>&1 | sed -n 's/.*signature //p' | tail -1)
echo "candidate sha256=$CAND_SHA bench=$CAND_BENCH flags=$BUILD_FLAGS"
[ "$CAND_BENCH" = "243f9a1c1ba5b36f" ] || fail "candidate bench signature changed: $CAND_BENCH"

if [ "$CTEST" = "true" ]; then
  (cd build-exp && ctest --output-on-failure 2>&1 | tail -3) || fail "ctest failed"
fi

if [ "$BASE" = "dev4" ]; then B_BIN="$DEV4_BIN"; else B_BIN="$CAND_BIN"; fi

A_OPT_ARGS=(); while IFS= read -r line; do [ -n "$line" ] && A_OPT_ARGS+=("$line"); done < <(opt_args "$CAND_OPTS" "--a-option")
B_OPT_ARGS=(); while IFS= read -r line; do [ -n "$line" ] && B_OPT_ARGS+=("$line"); done < <(opt_args "$BASE_OPTS" "--b-option")

SUITE_SHA=$(sha256sum "$OPENINGS" | cut -d' ' -f1)
CPUINFO=$(grep -m1 'model name' /proc/cpuinfo || true)
NPROC=$(nproc)

export DEV4_SHA DEV4_BENCH CAND_SHA CAND_BENCH SUITE_SHA CPUINFO NPROC
python3 - "$JOB_JSON" "$OUT/manifest.json" <<'EOF' || fail "manifest write failed"
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
    "candidate_build_flags": job.get("build_flags", "-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1"),
    "dev4_build": "cmake -DCMAKE_BUILD_TYPE=Release (plain) from tag v0.1.0-dev4",
}
with open(sys.argv[2], "w") as f:
    json.dump(manifest, f, indent=2)
EOF

run_match() { # name games seed engineA engineB
  local name=$1 games=$2 seed=$3 ea=$4 eb=$5
  echo "=== match $name: $games games seed $seed ==="
  .venv/bin/python scripts/tournament.py --engine-a "$ea" --engine-b "$eb" \
    "${A_OPT_ARGS[@]}" "${B_OPT_ARGS[@]}" \
    --games "$games" --base-ms "$BASE_MS" --inc-ms "$INC_MS" --hash "$HASH" \
    --threads "$THREADS" --max-plies "$MAXPLIES" \
    --openings "$OPENINGS" --seed "$seed" \
    --pgn "$OUT/$name.pgn" --jsonl "$OUT/$name.jsonl" --csv "$OUT/$name.csv" \
    > "$OUT/$name.stdout.log" 2>&1
  local rc=$?
  grep -E "^games|clustered|paired|sprt|naive" "$OUT/$name.stdout.log" | tee "$OUT/$name.report.txt" || true
  [ $rc -eq 0 ] || fail "tournament $name exited $rc (see $name.stdout.log)"
}

if [ "$NULL_GAMES" != "0" ]; then
  run_match "null" "$NULL_GAMES" "$((SEED + 1))" "$CAND_BIN" "$CAND_BIN"
fi
run_match "match" "$GAMES" "$SEED" "$CAND_BIN" "$B_BIN"

echo "=== job $ID done $(date -u +%FT%TZ) ==="
commit_and_push
