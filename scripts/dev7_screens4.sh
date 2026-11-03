#!/bin/bash
cd "$(dirname "$0")/.."
A=/home/user/bin-backup/stockbear-dev6
B=/home/user/bin-backup/stockbear-dev4
OUT=benchmarks/results/0.1.0-dev7
.venv/bin/python scripts/tournament.py --engine-a $A --engine-b $B \
  --a-option EvalParams=research-data/params_outcome_v6.txt --a-option TTEval=true --a-option HistoryMaluses=false \
  --games 480 --base-ms 40 --inc-ms 4 --hash 16 --threads 1 --max-plies 240 \
  --openings benchmarks/positions/openings_dev4.txt --seed 20261430 \
  --pgn $OUT/clean-time40p4-v6-hmoff-s2.pgn --jsonl $OUT/clean-time40p4-v6-hmoff-s2.jsonl --csv $OUT/clean-time40p4-v6-hmoff-s2.csv 2>&1 | grep -E "^games|clustered"
echo DONE
