#!/bin/bash
# Pre-registered dev7 confirmation runner (docs/DEV7_CONFIRMATION.md).
# Engine paths are the byte-identical backups (sha-pinned) because the sandbox
# wiper deletes build*/ ; shas are recorded in the docs and results.
cd "$(dirname "$0")/.."
OUT=benchmarks/results/0.1.0-dev7
A=/home/user/bin-backup/stockbear-dev6   # sha256 15f1daa086fa7226181260ac795ad7ad58de58d254c3043d656b2d0e1534aa09
B=/home/user/bin-backup/stockbear-dev4   # sha256 1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae
OPTS=(--a-option EvalParams=research-data/params_outcome_v6.txt --a-option TTEval=true --a-option HistoryMaluses=false)
SUITE=benchmarks/positions/openings_dev7_confirmation.txt
echo "=== NULL 1100 g seed 2026110308 ==="
.venv/bin/python scripts/tournament.py --engine-a $A --engine-b $A "${OPTS[@]}" --b-option EvalParams=research-data/params_outcome_v6.txt --b-option TTEval=true --b-option HistoryMaluses=false \
  --games 1100 --base-ms 40 --inc-ms 4 --hash 16 --threads 1 --max-plies 240 \
  --openings $SUITE --seed 2026110308 \
  --pgn $OUT/confirm-null-time40_4.pgn --jsonl $OUT/confirm-null-time40_4.jsonl --csv $OUT/confirm-null-time40_4.csv 2>&1 | grep -E "^games|clustered|sprt"
echo "=== CANDIDATE 4400 g seed 2026110309 ==="
.venv/bin/python scripts/tournament.py --engine-a $A --engine-b $B "${OPTS[@]}" \
  --games 4400 --base-ms 40 --inc-ms 4 --hash 16 --threads 1 --max-plies 240 \
  --openings $SUITE --seed 2026110309 \
  --pgn $OUT/confirm-champ-time40_4.pgn --jsonl $OUT/confirm-champ-time40_4.jsonl --csv $OUT/confirm-champ-time40_4.csv 2>&1 | grep -E "^games|clustered|sprt"
echo CONFIRM_ALL_DONE
