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
i=20
for sw in Futility ReverseFutility CounterMoves ContinuationHistory CaptureHistory HistoryMaluses LMRHistory Improving; do
  run v6-$sw-off --a-option EvalParams=research-data/params_outcome_v6.txt --a-option TTEval=true --a-option $sw=false --seed $((20261400+i))
  i=$((i+1))
done
echo ALL_DONE
