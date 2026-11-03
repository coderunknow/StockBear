#!/bin/bash
# One pre-registered v0.1.0-dev6 experiment job on a GitHub-hosted runner.
# Usage: actions_dev6_lane.sh '<job-json>'
#
# Two task types:
#   task = "verify-baseline": download the OFFICIAL v0.1.0-dev5 release
#          archives, verify them against the published SHA256SUMS.txt, extract
#          the exact portable Linux executable, pin it into
#          benchmarks/binaries/stockbear-dev5-release, record its SHA-256,
#          bench signatures, version and the shipped parameter file, and commit
#          benchmarks/dev6-baseline/ + the binary back to the branch. This is
#          the immutable dev6 baseline; it is NEVER rebuilt or replaced.
#   task = "match": build the candidate from THIS checkout with the pinned
#          portable release flags, verify it is bench-identical, then run an
#          optional candidate-vs-candidate null and a candidate-vs-dev5 match
#          at 40+4 ms. dev5 always plays its champion configuration
#          (EvalParams=research-data/params_abc.txt, TTEval=true) unless
#          baseline_options overrides it. All raw records are committed back.
#
# The dev6 lane deliberately does NOT touch the historical dev4/dev5 exp-run
# pipeline. Results come back through git because the sandbox cannot reach the
# release-asset CDN or download Actions artifacts.
set -uo pipefail
cd "$(dirname "$0")/.."
JOB_JSON="$1"
BRANCH="${GITHUB_REF_NAME:-arena/3e6dd5b6-stockbear}"

jget() { # key default: strings print raw, else JSON-encoded
  python3 - "$JOB_JSON" "$1" "$2" <<'EOF'
import json, sys
job = json.loads(sys.argv[1]); key = sys.argv[2]
try: default = json.loads(sys.argv[3])
except Exception: default = sys.argv[3]
v = job.get(key, default)
print(v if isinstance(v, str) else json.dumps(v))
EOF
}
opt_args() {
  python3 -c 'import json,sys; [print(f"{sys.argv[2]}={o}") for o in json.loads(sys.argv[1])]' "$1" "$2"
}

ID=$(jget id '"unnamed"')
TASK=$(jget task '"match"')
OUT="benchmarks/exp-runs/$ID"
mkdir -p "$OUT"
exec > >(tee -a "$OUT/run.log") 2>&1
echo "=== dev6 job $ID task=$TASK start $(date -u +%FT%TZ) run=${GITHUB_RUN_ID:-local} branch=$BRANCH ==="

commit_and_push() {
  git config user.email "dev6-runner@stockbear.local"
  git config user.name "dev6-runner"
  sleep 2
  for attempt in 1 2 3 4 5 6; do
    git pull --rebase origin "$BRANCH" > /dev/null 2>&1 || git rebase --abort > /dev/null 2>&1 || true
    git add -A "benchmarks/exp-runs/$ID" benchmarks/dev6-baseline benchmarks/binaries 2>/dev/null || true
    # [skip ci]: these are data-only result commits; the exact-head CI is run
    # separately on the source commit. Avoids N redundant full-matrix CI runs.
    if git commit --allow-empty -q -m "dev6-run[$ID]: results (run ${GITHUB_RUN_ID:-local}, job ${GITHUB_JOB:-local}) [skip ci]" 2>/dev/null; then
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
fail() {
  echo "FATAL: $*" | tee -a "$OUT/FAIL.txt"
  commit_and_push
  exit 1
}
trap 'echo "ERR at line $LINENO (status $?)" >> "$OUT/FAIL.txt"' ERR

python3 -m venv .venv
.venv/bin/pip -q install cmake ninja chess numpy || fail "pip install failed"
export PATH="$PWD/.venv/bin:$PATH"

BUILD_FLAGS=$(jget build_flags '"-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4"')
CAND_OPTS=$(jget candidate_options '[]')
BASE_OPTS=$(jget baseline_options '["EvalParams=research-data/params_abc.txt","TTEval=true"]')
GAMES=$(jget games '0')
SEED=$(jget seed '0')
OPENINGS=$(jget openings '"benchmarks/positions/openings_dev4.txt"')
BASE_MS=$(jget base_ms '40'); INC_MS=$(jget inc_ms '4')
HASH=$(jget hash '16'); THREADS=$(jget threads '1'); MAXPLIES=$(jget max_plies '240')
NULL_GAMES=$(jget null_games '0'); CTEST=$(jget ctest 'false')
NOTE=$(jget note '""')
echo "id=$ID task=$TASK build_flags=$BUILD_FLAGS games=$GAMES seed=$SEED null_games=$NULL_GAMES"
echo "candidate_options=$CAND_OPTS baseline_options=$BASE_OPTS openings=$OPENINGS note=$NOTE"

DEV5_TAG="v0.1.0-dev5"
BASE_URL="https://github.com/coderunknow/StockBear/releases/download/${DEV5_TAG}"
DEV5_BIN="benchmarks/binaries/stockbear-dev5-release"
MANIFEST="benchmarks/dev6-baseline/manifest.json"

# ---------------------------------------------------------------------------
# Task 1: establish the immutable dev5 baseline from the official release.
# ---------------------------------------------------------------------------
if [ "$TASK" = "verify-baseline" ]; then
  mkdir -p "$OUT/assets" "$OUT/extract" benchmarks/dev6-baseline
  for f in SHA256SUMS.txt stockbear-0.1.0-dev5-linux-x64.tar.gz stockbear-0.1.0-dev5-windows-x64.zip; do
    curl -fsSL "$BASE_URL/$f" -o "$OUT/assets/$f" || fail "download $f failed"
  done
  echo "=== release assets downloaded ==="
  ls -l "$OUT/assets"
  echo "=== published SHA256SUMS.txt ==="
  cat "$OUT/assets/SHA256SUMS.txt" | tee benchmarks/dev6-baseline/SHA256SUMS.txt
  ( cd "$OUT/assets" && sha256sum -c SHA256SUMS.txt ) | tee "$OUT/checksums.txt" || fail "checksum verification failed"

  tar xzf "$OUT/assets/stockbear-0.1.0-dev5-linux-x64.tar.gz" -C "$OUT/extract" || fail "tar extract failed"
  echo "=== archive contents ==="
  find "$OUT/extract" -type f -printf '%p %s bytes\n' | tee "$OUT/archive_contents.txt"
  EXTRACTED=$(find "$OUT/extract" -type f -name 'stockbear' | head -1)
  [ -n "$EXTRACTED" ] || fail "stockbear executable not found in archive"
  cp "$EXTRACTED" "$DEV5_BIN" && chmod +x "$DEV5_BIN" || fail "pin baseline binary failed"

  DEV5_SHA=$(sha256sum "$DEV5_BIN" | cut -d' ' -f1)
  DEV5_BENCH=$("$DEV5_BIN" bench 2>&1 | sed -n 's/.*signature //p' | tail -1)
  DEV5_D16=$("$DEV5_BIN" bench --depth 16 2>&1 | sed -n 's/.*signature //p' | tail -1)
  DEV5_VER=$(printf 'uci\nquit\n' | "$DEV5_BIN" 2>&1 | grep -m1 'id name' || true)
  echo "dev5 sha256=$DEV5_SHA bench=$DEV5_BENCH d16=$DEV5_D16 version=$DEV5_VER"
  [ "$DEV5_BENCH" = "243f9a1c1ba5b36f" ] || fail "dev5 bench mismatch: $DEV5_BENCH"
  [ "$DEV5_D16" = "a14ab62224f837e5" ] || fail "dev5 d16 mismatch: $DEV5_D16"

  # Capture the param file shipped inside the archive and compare to the repo's
  # champion param file (the published strength claim used params_abc + TTEval).
  SHIPPED_PARAMS=$(find "$OUT/extract" -type f -name 'params_abc.txt' | head -1 || true)
  SHIPPED_PARAMS_SHA=""
  REPO_PARAMS_SHA=$(sha256sum research-data/params_abc.txt | cut -d' ' -f1)
  if [ -n "$SHIPPED_PARAMS" ]; then
    SHIPPED_PARAMS_SHA=$(sha256sum "$SHIPPED_PARAMS" | cut -d' ' -f1)
    cp "$SHIPPED_PARAMS" benchmarks/dev6-baseline/params_abc_shipped.txt
  fi
  echo "shipped params_abc sha=$SHIPPED_PARAMS_SHA repo params_abc sha=$REPO_PARAMS_SHA"

  export DEV5_SHA DEV5_BENCH DEV5_D16 DEV5_VER SHIPPED_PARAMS_SHA REPO_PARAMS_SHA CPUINFO NPROC

  python3 - "$JOB_JSON" "$MANIFEST" <<'EOF' || fail "manifest write failed"
import json, sys, platform, datetime, os
job = json.loads(sys.argv[1])
m = {
    "task": "verify-baseline",
    "job": job,
    "ran_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "runner": {
        "os": os.environ.get("RUNNER_OS", ""),
        "arch": os.environ.get("RUNNER_ARCH", ""),
        "nproc": os.environ.get("NPROC", ""),
        "cpuinfo": os.environ.get("CPUINFO", ""),
        "note": "GitHub-hosted ubuntu-latest dedicated VM; public repo => no billing",
    },
    "platform": platform.platform(),
    "git_head": os.popen("git rev-parse HEAD").read().strip(),
    "release_tag": "v0.1.0-dev5",
    "release_commit": "c94571313a1667048468cf6d4e070400dc5ab228",
    "release_asset_url": "https://github.com/coderunknow/StockBear/releases/download/v0.1.0-dev5/stockbear-0.1.0-dev5-linux-x64.tar.gz",
    "sha256sums_txt_sha256": os.popen("sha256sum benchmarks/dev6-baseline/SHA256SUMS.txt | cut -d' ' -f1").read().strip(),
    "dev5_binary_path": "benchmarks/binaries/stockbear-dev5-release",
    "dev5_binary_sha256": os.environ.get("DEV5_SHA", ""),
    "dev5_bench_signature": os.environ.get("DEV5_BENCH", ""),
    "dev5_bench_depth16_signature": os.environ.get("DEV5_D16", ""),
    "dev5_uci_id_name": os.environ.get("DEV5_VER", ""),
    "dev5_build_flags": "-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4 (x86-64-v3 portable)",
    "dev5_compiler": "GitHub-hosted ubuntu-22.04 image GCC (release.yml package job)",
    "dev5_champion_options": {"EvalParams": "research-data/params_abc.txt", "TTEval": "true"},
    "shipped_params_abc_sha256": os.environ.get("SHIPPED_PARAMS_SHA", ""),
    "repo_params_abc_sha256": os.environ.get("REPO_PARAMS_SHA", ""),
    "published_strength_claim": "exp-0024 portable artifact +64.7 [+57.5,+72.0] vs dev4 (6600 g @ 40+4 ms)",
    "immutable": True,
}
json.dump(m, open(sys.argv[2], "w"), indent=2)
EOF

  {
    echo "# v0.1.0-dev6 — immutable dev5 baseline provenance"
    echo
    echo "This file is generated by the free GitHub-hosted dev6 research lane from the"
    echo "OFFICIAL, UNMODIFIED v0.1.0-dev5 GitHub release. All decisive dev6 strength"
    echo "comparisons use benchmarks/binaries/stockbear-dev5-release with its champion"
    echo "runtime options; this binary is never rebuilt, moved, or replaced."
    echo
    echo "- Release tag: v0.1.0-dev5 (commit c94571313a1667048468cf6d4e070400dc5ab228)"
    echo "- Linux archive: stockbear-0.1.0-dev5-linux-x64.tar.gz (verified against published SHA256SUMS.txt)"
    echo "- Windows archive: stockbear-0.1.0-dev5-windows-x64.zip (verified against published SHA256SUMS.txt)"
    echo "- Exact executable SHA-256: $DEV5_SHA"
    echo "- bench signature: $DEV5_BENCH ; bench --depth 16: $DEV5_D16"
    echo "- UCI: $DEV5_VER"
    echo "- Build flags: -mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4 (portable x86-64-v3, no -march=native)"
    echo "- Champion runtime: EvalParams=research-data/params_abc.txt, TTEval=true"
    echo "- shipped params_abc.txt SHA-256: $SHIPPED_PARAMS_SHA"
    echo "- repo   params_abc.txt SHA-256: $REPO_PARAMS_SHA"
    echo "- Published strength claim (vs dev4): exp-0024 +64.7 [+57.5,+72.0], 6600 g @ 40+4 ms"
    echo
    echo "Full machine-readable record: benchmarks/dev6-baseline/manifest.json"
    echo "Raw lane log, checksums and archive listing: benchmarks/exp-runs/$ID/"
  } > benchmarks/dev6-baseline/PROVENANCE.md

  echo "=== verify-baseline done ==="
  commit_and_push
  exit 0
fi

# ---------------------------------------------------------------------------
# Task 2: candidate build + fixed-time matches vs the exact dev5 binary.
# ---------------------------------------------------------------------------
[ -x "$DEV5_BIN" ] || fail "immutable dev5 baseline missing: run verify-baseline first"
[ -f "$MANIFEST" ] || fail "baseline manifest missing"
EXPECT_SHA=$(python3 -c "import json;print(json.load(open('$MANIFEST'))['dev5_binary_sha256'])")
DEV5_SHA=$(sha256sum "$DEV5_BIN" | cut -d' ' -f1)
[ "$DEV5_SHA" = "$EXPECT_SHA" ] || fail "dev5 baseline sha mismatch: $DEV5_SHA != $EXPECT_SHA"
DEV5_BENCH=$("$DEV5_BIN" bench 2>&1 | sed -n 's/.*signature //p' | tail -1)
[ "$DEV5_BENCH" = "243f9a1c1ba5b36f" ] || fail "dev5 baseline bench mismatch: $DEV5_BENCH"
echo "dev5 baseline verified sha256=$DEV5_SHA bench=$DEV5_BENCH"

cmake -S . -B build-exp -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="$BUILD_FLAGS" > /dev/null || fail "candidate configure failed"
cmake --build build-exp -j 4 --target stockbear > /dev/null || fail "candidate build failed"
CAND_BIN=build-exp/stockbear
CAND_SHA=$(sha256sum "$CAND_BIN" | cut -d' ' -f1)
CAND_BENCH=$("$CAND_BIN" bench 2>&1 | sed -n 's/.*signature //p' | tail -1)
echo "candidate sha256=$CAND_SHA bench=$CAND_BENCH flags=$BUILD_FLAGS"
[ "$CAND_BENCH" = "243f9a1c1ba5b36f" ] || fail "candidate bench signature changed: $CAND_BENCH"

if [ "$CTEST" = "true" ]; then
  ( cd build-exp && ctest --output-on-failure 2>&1 | tail -3 ) || fail "ctest failed"
fi

A_OPT_ARGS=(); while IFS= read -r line; do [ -n "$line" ] && A_OPT_ARGS+=("$line"); done < <(opt_args "$CAND_OPTS" "--a-option")
B_OPT_ARGS=(); while IFS= read -r line; do [ -n "$line" ] && B_OPT_ARGS+=("$line"); done < <(opt_args "$BASE_OPTS" "--b-option")

SUITE_SHA=$(sha256sum "$OPENINGS" | cut -d' ' -f1)
CPUINFO=$(grep -m1 'model name' /proc/cpuinfo || true)
NPROC=$(nproc)
export DEV5_SHA DEV5_BENCH CAND_SHA CAND_BENCH SUITE_SHA CPUINFO NPROC
python3 - "$JOB_JSON" "$OUT/manifest.json" <<'EOF' || fail "manifest write failed"
import json, sys, platform, datetime, os
job = json.loads(sys.argv[1])
m = {
    "job": job,
    "ran_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "git_head": os.popen("git rev-parse HEAD").read().strip(),
    "git_head_subject": os.popen("git log -1 --format=%s").read().strip(),
    "runner": {"os": os.environ.get("RUNNER_OS",""), "nproc": os.environ.get("NPROC",""),
               "cpuinfo": os.environ.get("CPUINFO",""),
               "note": "GitHub-hosted ubuntu-latest dedicated VM; public repo => no billing"},
    "platform": platform.platform(),
    "baseline": "EXACT released v0.1.0-dev5 portable binary (benchmarks/binaries/stockbear-dev5-release)",
    "dev5_sha256": os.environ.get("DEV5_SHA",""),
    "dev5_bench": os.environ.get("DEV5_BENCH",""),
    "candidate_sha256": os.environ.get("CAND_SHA",""),
    "candidate_bench": os.environ.get("CAND_BENCH",""),
    "candidate_build_flags": job.get("build_flags", "-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4"),
    "opening_suite": job.get("openings", ""),
    "opening_suite_sha256": os.environ.get("SUITE_SHA",""),
    "baseline_options": job.get("baseline_options", ["EvalParams=research-data/params_abc.txt","TTEval=true"]),
}
json.dump(m, open(sys.argv[2], "w"), indent=2)
EOF

run_match() { # name games seed engineA engineB
  local name=$1 games=$2 seed=$3 ea=$4 eb=$5
  echo "=== match $name: $games games seed $seed A=$ea B=$eb ==="
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

if [ "$GAMES" = "0" ] && [ "$NULL_GAMES" = "0" ]; then
  fail "job has neither games nor null_games"
fi
if [ "$NULL_GAMES" != "0" ]; then
  # Null: candidate vs the SAME candidate binary, with candidate options on both
  # sides; baseline_options are irrelevant here.
  NULL_B_OPT_ARGS=(); while IFS= read -r line; do [ -n "$line" ] && NULL_B_OPT_ARGS+=("$line"); done < <(opt_args "$CAND_OPTS" "--b-option")
  echo "=== null: $NULL_GAMES games seed $((SEED + 1)) ==="
  .venv/bin/python scripts/tournament.py --engine-a "$CAND_BIN" --engine-b "$CAND_BIN" \
    "${A_OPT_ARGS[@]}" "${NULL_B_OPT_ARGS[@]}" \
    --games "$NULL_GAMES" --base-ms "$BASE_MS" --inc-ms "$INC_MS" --hash "$HASH" \
    --threads "$THREADS" --max-plies "$MAXPLIES" \
    --openings "$OPENINGS" --seed "$((SEED + 1))" \
    --pgn "$OUT/null.pgn" --jsonl "$OUT/null.jsonl" --csv "$OUT/null.csv" \
    > "$OUT/null.stdout.log" 2>&1
  rc=$?
  grep -E "^games|clustered|paired|sprt|naive" "$OUT/null.stdout.log" | tee "$OUT/null.report.txt" || true
  [ $rc -eq 0 ] || fail "tournament null exited $rc"
fi
if [ "$GAMES" != "0" ]; then
  run_match "match" "$GAMES" "$SEED" "$CAND_BIN" "$DEV5_BIN"
fi

echo "=== dev6 job $ID done $(date -u +%FT%TZ) ==="
commit_and_push
