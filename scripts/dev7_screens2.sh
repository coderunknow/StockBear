#!/bin/bash
cd "$(dirname "$0")/.."
A=/home/user/bin-backup/stockbear-dev6
B=/home/user/bin-backup/stockbear-dev4
OUT=benchmarks/results/0.1.0-dev7
mkdir -p $OUT
run() {
  local name=$1; shift
  .venv/bin/python scripts/tournament.py --engine-a $A --engine-b $B "$@" \
    --games 480 --base-ms 40 --inc-ms 4 --hash 16 --threads 1 --max-plies 240 \
    --openings benchmarks/positions/openings_dev4.txt \
    --pgn $OUT/clean-time40p4-$name.pgn --jsonl $OUT/clean-time40p4-$name.jsonl --csv $OUT/clean-time40p4-$name.csv 2>&1 | grep -E "^games|clustered"
}
run abc_s095-s2 --a-option EvalParams=research-data/params_abc_s095.txt --a-option TTEval=true --seed 20261411
run abc_s095-s3 --a-option EvalParams=research-data/params_abc_s095.txt --a-option TTEval=true --seed 20261412
run v6-s2       --a-option EvalParams=research-data/params_outcome_v6.txt --a-option TTEval=true --seed 20261413
echo ALL_DONE
