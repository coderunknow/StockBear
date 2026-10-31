#!/usr/bin/env python3
"""Recompute the summary line of a recorded match JSONL, without replaying games.

A tournament JSONL holds one `{"configuration": ...}` line, one `{"game": ...}`
line per game and a final `{"summary": ...}` line. When the statistics code gains
a new estimator the recorded match does not have to be replayed: this script
derives the new summary from the recorded per-game lines and rewrites only that
final line, leaving every game record byte-identical. The output states that the
summary was recomputed so the provenance stays honest.

Usage:
  python3 scripts/recompute_summary.py match.jsonl [--sprt-elo 5] [--in-place]
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match_stats  # noqa: E402


def load(path):
    configuration = None
    games = []
    for number, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        if "configuration" in record and configuration is None:
            configuration = record["configuration"]
        elif "game" in record:
            games.append(record)
        elif "summary" in record:
            continue
        else:
            raise SystemExit(f"{path}:{number}: unrecognised record")
    if configuration is None:
        raise SystemExit(f"{path}: no configuration line")
    if not games:
        raise SystemExit(f"{path}: no game records")
    return configuration, games


def summarise_records(configuration, games, sprt_elo):
    games = sorted(games, key=lambda r: r["game"])
    scores = [r["score_a"] for r in games if r.get("score_a") is not None]
    pair_games = {}
    pair_openings = {}
    for record in games:
        index = record["game"] - 1
        pair = index // 2
        pair_games.setdefault(pair, [None, None])[index % 2] = record["score_a"]
        pair_openings.setdefault(pair, record["opening"])
    pair_scores = []
    openings_of_pairs = []
    for pair in sorted(pair_games):
        first, second = pair_games[pair]
        if first is None or second is None:
            continue
        pair_scores.append(first + second)
        openings_of_pairs.append(pair_openings[pair])
    summary = match_stats.summarise(
        scores, pair_scores,
        match_stats.lmr_step(pair_scores, 0.0, sprt_elo),
        pair_openings=openings_of_pairs)
    summary["unadjudicated"] = len(games) - len(scores)
    summary["config"] = configuration
    summary["recomputed"] = (
        "summary recomputed from the recorded game lines by "
        "scripts/recompute_summary.py; game records are unchanged")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("jsonl")
    parser.add_argument("--sprt-elo", type=float, default=5.0,
                        help="H1 of the SPRT in Elo (default 5)")
    parser.add_argument("--in-place", action="store_true",
                        help="rewrite the file instead of printing to stdout")
    args = parser.parse_args()

    configuration, games = load(args.jsonl)
    summary = summarise_records(configuration, games, args.sprt_elo)
    payload = json.dumps({"summary": summary}, allow_nan=False) + "\n"

    if args.in_place:
        lines = [line.rstrip("\n") for line in open(args.jsonl, encoding="utf-8") if line.strip()]
        lines = [line for line in lines if '"summary"' not in line]
        lines.append(payload.rstrip("\n"))
        temporary = args.jsonl + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        os.replace(temporary, args.jsonl)
        print(f"rewrote the summary line of {args.jsonl}", file=sys.stderr)
    print(payload, end="")
    print(match_stats.format_report(summary), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
