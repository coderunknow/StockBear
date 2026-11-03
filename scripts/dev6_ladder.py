#!/usr/bin/env python3
"""exp-0032 decisive external ladder: connected bipartite (star) design.

Frozen design in docs/DEV6_PREREG_EXP0031.md §3. Every SUBJECT plays every
ANCHOR on a FRESH, DISJOINT 40-opening slice, 80 paired games per cell,
fixed-node 6000 +/- 15% (CPU-clock-immune). 8 anchors x 5 subjects = 40 cells
= 3200 games. Writes a cell.json identity record per cell (SF11 skill levels
share one binary, so UCI names alone cannot distinguish anchors).
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import match_stats

BIN = ROOT / "benchmarks" / "binaries"
POS = ROOT / "benchmarks" / "positions"
EXP = ROOT / "benchmarks" / "exp-runs"
OUT = ROOT / "benchmarks" / "dev6-baseline" / "ladder_cells.json"
PY = ROOT / ".venv" / "bin" / "python"
PARAMS_ABC = "research-data/params_abc.txt"
PARAMS_DEV6A = "research-data/params_dev6_a.txt"
CAND = str(ROOT / "build-cand" / "stockbear")
NODES, JITTER, GAMES = 6000, 0.15, 80

SUBJECTS = [
    ("dev5_official", str(BIN / "stockbear-dev5-release"),
     [f"EvalParams={PARAMS_ABC}", "TTEval=true"]),
    ("dev5_rebuilt", str(ROOT / "build-dev5" / "stockbear"),
     [f"EvalParams={PARAMS_ABC}", "TTEval=true"]),
    ("dev6_champion", CAND, [f"EvalParams={PARAMS_ABC}", "TTEval=true"]),
    ("dev6_failed", CAND, [f"EvalParams={PARAMS_DEV6A}", "TTEval=true"]),
    ("dev4", str(BIN / "stockbear-dev4-1c5b61a7"), []),
]
ANCHORS = [
    ("sf11-L4", str(BIN / "external" / "stockfish-sf11"), ["Skill Level=4"]),
    ("sf11-L8", str(BIN / "external" / "stockfish-sf11"), ["Skill Level=8"]),
    ("sf11-L12", str(BIN / "external" / "stockfish-sf11"), ["Skill Level=12"]),
    ("sf11-L16", str(BIN / "external" / "stockfish-sf11"), ["Skill Level=16"]),
    ("sf11-L20", str(BIN / "external" / "stockfish-sf11"), ["Skill Level=20"]),
    ("sf8", str(BIN / "external" / "stockfish-sf8"), []),
    ("sf9", str(BIN / "external" / "stockfish-sf9"), []),
    ("sf10", str(BIN / "external" / "stockfish-sf10"), []),
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def make_slices(n_cells, per=40):
    master = POS / "openings_exp0032_ladder.txt"
    if not master.exists():
        subprocess.run([str(PY), str(ROOT / "scripts" / "exp_confirmation_openings.py"),
                        "--name", "exp0032l", "--seed", "2026110801",
                        "--count", str(n_cells * per)],
                       cwd=ROOT, check=True, capture_output=True)
        gen = POS / "openings_exp0032l_confirmation.txt"
        gen.rename(master)
    lines = [l for l in master.read_text().splitlines() if l and not l.startswith("#")]
    assert len(lines) == n_cells * per, (len(lines), n_cells * per)
    out = []
    for i in range(n_cells):
        p = POS / f"openings_exp0032_s{i+1:02d}.txt"
        p.write_text("\n".join(lines[i*per:(i+1)*per]) + "\n")
        out.append(p)
    return sha(master), out


def run_cell(subj, anchor, slice_path, seed, idx):
    sid, sb, sopts = subj
    aid, ab, aopts = anchor
    d = EXP / f"exp0032-ladder-{aid}-{sid}"
    d.mkdir(parents=True, exist_ok=True)
    cmd = [str(PY), str(ROOT / "scripts" / "tournament.py"),
           "--engine-a", sb, "--engine-b", ab,
           "--games", str(GAMES), "--base-ms", "40", "--inc-ms", "4",
           "--hash", "16", "--threads", "1", "--max-plies", "240",
           "--nodes", str(NODES), "--nodes-jitter", str(JITTER),
           "--openings", str(slice_path), "--seed", str(seed)]
    for o in sopts:
        cmd += ["--a-option", o]
    for o in aopts:
        cmd += ["--b-option", o]
    cmd += ["--pgn", str(d / "match.pgn"), "--jsonl", str(d / "match.jsonl"),
            "--csv", str(d / "match.csv")]
    cell = {"cell": idx + 1, "subject": sid, "anchor": aid,
            "subject_binary": sb, "subject_sha256": sha(sb),
            "subject_options": sopts,
            "anchor_binary": ab, "anchor_sha256": sha(ab),
            "anchor_options": aopts,
            "opening_slice": str(slice_path.relative_to(ROOT)),
            "opening_slice_sha256": sha(slice_path), "seed": seed,
            "games": GAMES, "nodes": NODES, "nodes_jitter": JITTER,
            "command": " ".join(cmd)}
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        cell["error"] = r.stderr[-1000:]
        (d / "cell.json").write_text(json.dumps(cell, indent=2) + "\n")
        return cell
    recs = []
    for line in (d / "match.jsonl").read_text().splitlines():
        o = json.loads(line)
        if "game" in o:
            recs.append(o)
    recs.sort(key=lambda x: x["game"])
    pair_scores, pair_openings, terms = [], [], {}
    for k in range(0, len(recs) - 1, 2):
        a, b = recs[k], recs[k+1]
        if a["score_a"] is None or b["score_a"] is None:
            continue
        pair_scores.append(a["score_a"] + b["score_a"])
        pair_openings.append(a["opening"])
    for x in recs:
        t = x.get("termination", "?")
        terms[t] = terms.get(t, 0) + 1
    games = [x["score_a"] for x in recs if x["score_a"] is not None]
    summ = match_stats.summarise(games, pair_scores,
                                 match_stats.lmr_step(pair_scores, 0.0, 5.0),
                                 pair_openings=pair_openings)
    cl = summ.get("opening_clustered", {})
    cell.update({"games_completed": len(games), "wins": summ["wins"],
                 "draws": summ["draws"], "losses": summ["losses"],
                 "score": (summ["wins"] + 0.5*summ["draws"]) / max(1, len(games)),
                 "elo": cl.get("elo_difference"), "ci95": cl.get("elo_ci95"),
                 "clusters": cl.get("clusters"), "terminations": terms,
                 "unadjudicated": len(recs) - len(games),
                 "time_forfeit": sum(v for k, v in terms.items() if "FORFEIT" in k.upper())})
    (d / "cell.json").write_text(json.dumps(cell, indent=2) + "\n")
    return cell


def main():
    cells = []
    master_sha, slices = make_slices(len(SUBJECTS) * len(ANCHORS))
    i = 0
    for anchor in ANCHORS:
        for subj in SUBJECTS:
            c = run_cell(subj, anchor, slices[i], 2026110900 + i, i)
            cells.append(c)
            if "error" in c:
                print(f"[{i+1:02d}/40] {c['subject']:16s} vs {c['anchor']:9s} ERROR {c['error'][:120]}")
            else:
                print(f"[{i+1:02d}/40] {c['subject']:16s} vs {c['anchor']:9s} "
                      f"score {c['score']:.3f} +{c['wins']}={c['draws']}-{c['losses']} "
                      f"forfeits {c['time_forfeit']}", flush=True)
            i += 1
    OUT.write_text(json.dumps({"experiment": "exp-0032",
        "prereg": "docs/DEV6_PREREG_EXP0031.md",
        "design": "connected bipartite star: 8 anchors x 5 subjects, 80 paired games/cell",
        "control": {"nodes": NODES, "nodes_jitter": JITTER, "hash": 16,
                    "threads": 1, "max_plies": 240},
        "master_suite_sha256": master_sha, "cells": cells}, indent=2) + "\n")
    ok = [c for c in cells if "error" not in c]
    print(f"done: {len(ok)}/40 cells, {sum(c['games_completed'] for c in ok)} games, "
          f"{sum(c['time_forfeit'] for c in ok)} time forfeits")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
