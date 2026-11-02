#!/usr/bin/env python3
"""Collect the final summary line of every recorded match into one table.

Each experiment is a tournament JSONL whose last line is the summary block. This
script reads only that line, so the table cannot disagree with the raw records:
every number in it is copied from the match that produced it.

Usage:
    python3 scripts/experiment_table.py benchmarks/results/0.1.0-dev4/experiments/*.jsonl
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def summarise(path: Path) -> dict:
    summary = None
    configuration = None
    games = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if "configuration" in record:
                configuration = record["configuration"]
            elif "game" in record:
                games += 1
            elif "summary" in record:
                summary = record["summary"]
    if summary is None:
        raise SystemExit(f"{path}: no summary line")
    paired = summary.get("paired", {})
    cluster = summary.get("opening_clustered", {})
    elo = cluster.get("elo_difference", paired.get("elo_difference"))
    ci = cluster.get("elo_ci95") or paired.get("elo_ci95") or [None, None]
    config = configuration or {}
    condition = (f"nodes {config['nodes_per_move']} jitter {config.get('nodes_jitter', 0)}"
                 if config.get("nodes_per_move") else
                 f"{config.get('base_ms')}+{config.get('increment_ms')} ms")
    return {
        "experiment": path.stem,
        "games": games,
        "condition": condition,
        "score": round(summary["score"] if "score" in summary else paired.get("score", float("nan")), 4),
        "wins": summary.get("wins"),
        "draws": summary.get("draws"),
        "losses": summary.get("losses"),
        "elo": None if elo is None else round(elo, 1),
        "elo_lo": None if ci[0] is None else round(ci[0], 1),
        "elo_hi": None if ci[1] is None else round(ci[1], 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--csv", type=Path, help="also write the table as CSV")
    args = parser.parse_args()
    rows = [summarise(path) for path in sorted(args.inputs)]
    fields = list(rows[0].keys())
    writer = csv.DictWriter(sys.stdout, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", encoding="utf-8", newline="") as handle:
            csv_writer = csv.DictWriter(handle, fieldnames=fields)
            csv_writer.writeheader()
            csv_writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
