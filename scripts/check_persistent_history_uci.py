#!/usr/bin/env python3
"""exp-0065 independent INTERACTIVE UCI oracle for object lifetime.

The in-process test group constructs Search directly and therefore cannot see
whether UciEngine actually reuses the object or resets it on ucinewgame. This
drives the real engine over a pipe and asserts both:

  1. REUSE: with the switch ON, a move sequence must produce different node
     counts than the identical sequence with OFF (the carried table is live).
  2. RESET: with ON, the first search after `ucinewgame` must reproduce exactly
     the first search of a brand-new game (no history leaks across games).
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

A = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 4"
B = "r2q1rk1/pp2ppbp/2np1np1/8/2BNP3/2N1BP2/PPPQ2PP/2KR3R w - - 5 11"


class Engine:
    def __init__(self, path, params, on):
        self.p = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.send("uci"); self.until("uciok")
        for line in ("setoption name Hash value 16", "setoption name Threads value 1",
                     f"setoption name EvalParams value {params}",
                     "setoption name TTEval value true",
                     f"setoption name PersistentHistory value {'true' if on else 'false'}"):
            self.send(line)
        self.send("isready"); self.until("readyok")

    def send(self, s):
        self.p.stdin.write(s + "\n"); self.p.stdin.flush()

    def until(self, tok):
        out = []
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("engine closed stdout")
            line = line.strip(); out.append(line)
            if line == tok or line.startswith(tok + " "):
                return out

    def nodes(self, fen, depth=7):
        self.send(f"position fen {fen}")
        self.send(f"go depth {depth}")
        n = 0
        for line in self.until("bestmove"):
            if line.startswith("info ") and " nodes " in line:
                t = line.split(); n = int(t[t.index("nodes") + 1])
        return n

    def newgame(self):
        self.send("ucinewgame"); self.send("isready"); self.until("readyok")

    def close(self):
        try:
            self.send("quit"); self.p.wait(timeout=10)
        except Exception:
            self.p.kill()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--params", required=True)
    ap.add_argument("--output")
    a = ap.parse_args()
    seq = {}
    reset = {}
    for label, on in (("on", True), ("off", False)):
        e = Engine(a.engine, a.params, on)
        e.newgame()
        first = e.nodes(A)
        vals = [first, e.nodes(B), e.nodes(A), e.nodes(B)]
        e.newgame()
        after = e.nodes(A)
        seq[label] = vals
        reset[label] = {"first": first, "after_ucinewgame": after, "equal": first == after}
        e.close()
    reuse_live = seq["on"] != seq["off"]
    reset_ok = reset["on"]["equal"] and reset["off"]["equal"]
    ok = reuse_live and reset_ok
    out = {"mode": "uci_lifetime", "sequence_nodes": seq, "reset": reset,
           "reuse_live": reuse_live, "ucinewgame_resets": reset_ok,
           "params_sha256": hashlib.sha256(Path(a.params).read_bytes()).hexdigest(),
           "verdict": "PASS" if ok else "FAIL"}
    text = json.dumps(out, indent=2, sort_keys=True)
    print(text)
    if a.output:
        Path(a.output).write_text(text + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
