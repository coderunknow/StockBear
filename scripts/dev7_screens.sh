#!/bin/bash
# dev7 param-set triage screens: champion binary + TTEval + various EvalParams,
# clean 40+4, 480 g each, vs dev4, on the dev4 exploratory openings, run ALONE.
cd "$(dirname "$0")/.."
A=/home/user/bin-backup/stockbear-dev6   # sha 15f1daa0... == build-dev6
B=/home/user/bin-backup/stockbear-dev4   # sha 1c5b61a7... == dev4 baseline
OUT=benchmarks/results/0.1.0-dev7
mkdir -p $OUT
run() {
  local name=$1; shift
  .venv/bin/python scripts/tournament.py --engine-a $A --engine-b $B "$@" \
    --games 480 --base-ms 40 --inc-ms 4 --hash 16 --threads 1 --max-plies 240 \
    --openings benchmarks/positions/openings_dev4.txt \
    --pgn $OUT/clean-time40p4-$name.pgn --jsonl $OUT/clean-time40p4-$name.jsonl --csv $OUT/clean-time40p4-$name.csv 2>&1 | grep -E "^games|clustered"
}
i=1
for p in params_outcome_v5 params_outcome_v6 params_bullet_b2 params_bullet_b3 params_abc_s095 params_abc_s105 params_abc_s110; do
  run $p --a-option EvalParams=research-data/$p.txt --a-option TTEval=true --seed $((20261400+i))
  i=$((i+1))
done
echo ALL_DONE
