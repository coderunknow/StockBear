#!/usr/bin/env python3
"""Pool sharded tournament results into one clustered estimate.

Each shard jsonl (scripts/tournament.py output) has a {"configuration": ...}
first line, one JSON record per game, and a {"summary": ...} last line. Pairs
are rebuilt per shard (games 2k and 2k+1 share an opening, colours reversed),
then all shards' pairs are pooled and scored with match_stats' opening-
clustered CR1 estimator. Shards may replay the same opening; clustering by
opening is exactly what the CR1 variance is for.

Usage:
  python3 scripts/pool_matches.py --out pooled.json --report pooled.txt \
      shard1.jsonl shard2.jsonl ...
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match_stats


def load_shard(path):
    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "configuration" in obj or "summary" in obj:
                continue
            records.append(obj)
    records.sort(key=lambda r: r["game"])
    games, pair_scores, pair_openings, unadj = [], [], [], 0
    for k in range(0, len(records) - 1, 2):
        a, b = records[k], records[k + 1]
        assert a["opening"] == b["opening"], f"pair {k} openings differ in {path}"
        games.append(a["score_a"])
        games.append(b["score_a"])
        if a["score_a"] is None or b["score_a"] is None:
            unadj += 1
            continue
        pair_scores.append(a["score_a"] + b["score_a"])
        pair_openings.append(a["opening"])
    return games, pair_scores, pair_openings, unadj, records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", default=None)
    ap.add_argument("--sprt-elo", type=float, default=5.0)
    args = ap.parse_args()

    games, pair_scores, pair_openings = [], [], []
    unadj = 0
    terminations = {}
    shards = []
    for path in args.jsonl:
        g, ps, po, u, records = load_shard(path)
        games += g
        pair_scores += ps
        pair_openings += po
        unadj += u
        for r in records:
            terminations[r.get("termination", "?")] = terminations.get(r.get("termination", "?"), 0) + 1
        shards.append({"file": path, "games": len(g), "pairs": len(ps), "unadjudicated": u})

    adjudicated = [s for s in games if s is not None]
    summary = match_stats.summarise(adjudicated, pair_scores,
                                    match_stats.lmr_step(pair_scores, 0.0, args.sprt_elo),
                                    pair_openings=pair_openings)
    summary["shards"] = shards
    summary["games_total"] = len(games)
    summary["unadjudicated"] = unadj
    summary["terminations"] = terminations
    out = {"summary": summary}
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(out, handle, indent=2, allow_nan=False)
    text = match_stats.format_report(summary)
    print(text)
    print(f"shards {len(shards)} games {len(games)} (+{summary['wins']} ={summary['draws']} "
          f"-{summary['losses']}) unadjudicated {unadj} terminations {terminations}")
    if args.report:
        with open(args.report, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
            handle.write(f"shards {len(shards)} games {len(games)} unadjudicated {unadj} "
                         f"terminations {terminations}\n")


if __name__ == "__main__":
    main()
