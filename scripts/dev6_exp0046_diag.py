#!/usr/bin/env python3
"""PRE-RESULT mechanism-live/overhead diagnostic for exp-0046 (NOT strength).

Runs the instrumented `build-exp0046-diag/stockbear` (compiled with
-DSB_ADAPTIVE_NULL_DEBUG=1) over 24 REAL exp-0046 suite positions, OFF/ON, at
FIXED DEPTH 10 and at a 40 ms fixed-time probe. Reports node counts, the
ADAPTIVENULLDEBUG counters and the fraction of positions where the mechanism
actually changed the null-move reduction. NO Elo, NO strength claim, NO tuning.

Usage: .venv/bin/python scripts/dev6_exp0046_diag.py
"""
from __future__ import annotations
import re
import statistics
import subprocess
import sys
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "build-exp0046-diag" / "stockbear"
SUITE = ROOT / "benchmarks" / "positions" / "openings_exp0046_stage0.txt"
N = 24
CHAMPION = ["EvalParams=research-data/params_abc.txt", "TTEval=true"]


def fens() -> list[str]:
    out = []
    for line in SUITE.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        moves = line.split("|", 1)[1].split()
        b = chess.Board()
        for m in moves:
            b.push_uci(m)
        out.append(b.fen())
        if len(out) == N:
            break
    assert len(out) == N
    return out


def probe(fen: str, on: bool, mode: str) -> dict:
    cmds = ["setoption name Hash value 16"]
    for opt in CHAMPION:
        k, v = opt.split("=", 1)
        cmds.append(f"setoption name {k} value {v}")
    cmds.append(f"setoption name AdaptiveNullR value {'true' if on else 'false'}")
    cmds.append("isready")
    cmds.append(f"position fen {fen}")
    cmds.append("go depth 10" if mode == "depth" else "go movetime 40")
    # The UCI search runs on a worker thread: `quit` would stop it immediately.
    # Wait for `bestmove` on stdout BEFORE sending quit.
    p = subprocess.Popen([str(BIN)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, cwd=ROOT)
    p.stdin.write("\n".join(cmds) + "\n")
    p.stdin.flush()
    lines = []
    for line in p.stdout:
        lines.append(line)
        if line.startswith("bestmove"):
            break
    p.stdin.write("quit\n")
    p.stdin.flush()
    p.stdin.close()
    stdout = "".join(lines)
    stderr = p.stderr.read()
    p.wait(timeout=30)
    nodes = [int(x) for x in re.findall(r"\bnodes (\d+)", stdout)]
    depths = [int(x) for x in re.findall(r"\bdepth (\d+)", stdout)]
    dbg = re.search(r"ADAPTIVENULLDEBUG switches=(\d+) null_nodes=(\d+) "
                    r"changed=(\d+) extra_plies=(\d+) nodes=(\d+)", stderr)
    assert dbg is not None, (stdout[-500:], stderr[-500:])
    return {"nodes": nodes[-1] if nodes else 0,
            "depth": depths[-1] if depths else 0,
            "null_nodes": int(dbg.group(2)), "changed": int(dbg.group(3)),
            "extra": int(dbg.group(4))}


def main() -> int:
    assert BIN.is_file(), BIN
    fs = fens()
    for mode in ("depth", "time"):
        agg = {}
        for on in (False, True):
            rs = [probe(f, on, mode) for f in fs]
            agg[on] = {
                "nodes": sum(r["nodes"] for r in rs),
                "null_nodes": sum(r["null_nodes"] for r in rs),
                "changed": sum(r["changed"] for r in rs),
                "extra": sum(r["extra"] for r in rs),
                "live_positions": sum(1 for r in rs if r["changed"] > 0),
                "median_depth": statistics.median(r["depth"] for r in rs),
            }
        off, on = agg[False], agg[True]
        print(f"[{mode}] OFF nodes={off['nodes']} null_nodes={off['null_nodes']} "
              f"changed={off['changed']} median_depth={off['median_depth']}")
        print(f"[{mode}] ON  nodes={on['nodes']} null_nodes={on['null_nodes']} "
              f"changed={on['changed']} extra_plies={on['extra']} "
              f"live={on['live_positions']}/{len(fs)} median_depth={on['median_depth']}")
        if off["nodes"]:
            print(f"[{mode}] node change = {100*(on['nodes']-off['nodes'])/off['nodes']:+.2f}%")
        assert off["changed"] == 0 and on["changed"] > 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
