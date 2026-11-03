#!/bin/bash
# Pre-registered dev6 confirmation runner (see docs/DEV6_CONFIRMATION.md).
# Null first (same binary both sides), then candidate vs dev4, both ALONE.
cd "$(dirname "$0")/.."
OUT=benchmarks/results/0.1.0-dev6
PY=.venv/bin/python
echo "=== NULL: build-dev6 vs build-dev6, 1100 g, seed 2026110208 ==="
$PY scripts/tournament.py --engine-a build-dev6/stockbear --engine-b build-dev6/stockbear \
  --a-option EvalParams=research-data/params_abc.txt --a-option TTEval=true \
  --b-option EvalParams=research-data/params_abc.txt --b-option TTEval=true \
  --games 1100 --base-ms 40 --inc-ms 4 --hash 16 --threads 1 --max-plies 240 \
  --openings benchmarks/positions/openings_dev6_confirmation.txt --seed 2026110208 \
  --pgn $OUT/confirm-null-time40_4.pgn --jsonl $OUT/confirm-null-time40_4.jsonl --csv $OUT/confirm-null-time40_4.csv 2>&1 | grep -E "^games|clustered|sprt"
echo "=== CANDIDATE: build-dev6(+abc+tteval) vs dev4, 4400 g, seed 2026110207 ==="
$PY scripts/tournament.py --engine-a build-dev6/stockbear --engine-b build-dev4/build/stockbear \
  --a-option EvalParams=research-data/params_abc.txt --a-option TTEval=true \
  --games 4400 --base-ms 40 --inc-ms 4 --hash 16 --threads 1 --max-plies 240 \
  --openings benchmarks/positions/openings_dev6_confirmation.txt --seed 2026110207 \
  --pgn $OUT/confirm-champ-time40_4.pgn --jsonl $OUT/confirm-champ-time40_4.jsonl --csv $OUT/confirm-champ-time40_4.csv 2>&1 | grep -E "^games|clustered|sprt"
echo CONFIRM_ALL_DONE
