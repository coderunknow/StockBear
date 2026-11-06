#!/usr/bin/env python3
"""Measure the depth/nodes actually reached under the harness's 40+4 ms clock.

The match harness (scripts/tournament.py) starts each side at 40 ms, subtracts
elapsed per move, then adds the 4 ms increment. Steady state is therefore driven
by the increment, not by a 40 ms think. This probe reproduces that clock model
over a real game so the reported depth is the depth the engine actually gets in
a decisive match, rather than a `go movetime 40` fiction.

Diagnostic only: makes NO strength claim and plays no gate games.
"""
from __future__ import annotations
import argparse
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

import chess

FENS = {
    "startpos": chess.STARTING_FEN,
    "opening": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 4",
    "middlegame": "r2q1rk1/pp2ppbp/2np1np1/2p5/2P1P3/2NP1NP1/PP3PBP/R1BQ1RK1 w - - 0 10",
    "kiwipete": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "endgame": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
}


class Engine:
    def __init__(self, path, options):
        self.p = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.send("uci")
        self.read_until("uciok")
        for k, v in options.items():
            self.send(f"setoption name {k} value {v}")
        self.send("isready")
        self.read_until("readyok")

    def send(self, s):
        self.p.stdin.write(s + "\n")
        self.p.stdin.flush()

    def read_until(self, token):
        lines = []
        while True:
            ln = self.p.stdout.readline()
            if not ln:
                break
            lines.append(ln.rstrip())
            if ln.strip() == token or ln.startswith(token + " "):
                break
        return lines

    def go(self, fen, wtime, btime, winc, binc):
        self.send(f"position fen {fen}")
        self.send(f"go wtime {int(wtime)} btime {int(btime)} winc {int(winc)} binc {int(binc)}")
        lines = self.read_until("bestmove")
        depth = nodes = None
        nps = None
        for ln in lines:
            m = re.search(r"\bdepth (\d+)", ln)
            if m:
                depth = int(m.group(1))
            m = re.search(r"\bnodes (\d+)", ln)
            if m:
                nodes = int(m.group(1))
            m = re.search(r"\bnps (\d+)", ln)
            if m:
                nps = int(m.group(1))
        bm = lines[-1].split()[1] if lines and lines[-1].startswith("bestmove") else None
        return {"depth": depth, "nodes": nodes, "nps": nps, "bestmove": bm}

    def close(self):
        self.send("quit")
        try:
            self.p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.p.kill()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("engine")
    ap.add_argument("--params", default="research-data/params_abc.txt")
    ap.add_argument("--extra", action="append", default=[], help="Extra UCI option K=V")
    ap.add_argument("--moves", type=int, default=40)
    ap.add_argument("--json")
    args = ap.parse_args()
    opts = {"Hash": "16", "EvalParams": args.params, "TTEval": "true"}
    for e in args.extra:
        k, v = e.split("=", 1)
        opts[k] = v
    eng = Engine(args.engine, opts)
    board = chess.Board()
    clock = {chess.WHITE: 40.0, chess.BLACK: 40.0}
    rows = []
    import time
    for i in range(args.moves):
        if board.is_game_over(claim_draw=True):
            break
        side = board.turn
        t0 = time.monotonic()
        r = eng.go(board.fen(), clock[chess.WHITE], clock[chess.BLACK], 4, 4)
        el = (time.monotonic() - t0) * 1000
        clock[side] -= el
        if clock[side] < 0:
            print(f"FORFEIT at move {i}", file=sys.stderr)
            break
        clock[side] += 4
        r["ply"] = i
        r["elapsed_ms"] = round(el, 2)
        r["clock_after"] = round(clock[side], 2)
        rows.append(r)
        try:
            board.push_uci(r["bestmove"])
        except Exception:
            break
    eng.close()
    depths = [r["depth"] for r in rows if r["depth"]]
    nodes = [r["nodes"] for r in rows if r["nodes"]]
    nps = [r["nps"] for r in rows if r["nps"]]
    summary = {
        "moves": len(rows),
        "depth_median": statistics.median(depths) if depths else None,
        "depth_mean": round(statistics.mean(depths), 2) if depths else None,
        "depth_hist": {str(d): depths.count(d) for d in sorted(set(depths))},
        "nodes_median": statistics.median(nodes) if nodes else None,
        "nps_median": statistics.median(nps) if nps else None,
        "elapsed_ms_median": round(statistics.median(r["elapsed_ms"] for r in rows), 2),
        "options": opts,
    }
    print(json.dumps(summary, indent=2))
    if args.json:
        Path(args.json).write_text(json.dumps({"summary": summary, "moves": rows}, indent=2) + "\n")


if __name__ == "__main__":
    main()
