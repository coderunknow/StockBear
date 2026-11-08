#!/usr/bin/env python3
"""exp-0067 independent INTERACTIVE UCI oracle for JOINT graded-state lifetime.

The in-process test group constructs Search directly, so it cannot observe
UciEngine's object lifetime. Two mutants survived an in-process-only suite in an
earlier cycle for exactly that reason. This drives the real engine over a pipe.

Both persistence switches are flipped TOGETHER -- that composition is the
exp-0067 intervention. ContinuationHistory=true in every case so the continuation
table is actually written. Adds a check that the joint arm differs from EACH
single-table arm, which is what proves neither branch is dead:

  1. PERSISTENCE ACROSS go: with the switch ON a move sequence must produce
     different node counts than the identical sequence with OFF.
  2. CROSS-GAME ISOLATION: the first search after `ucinewgame` must reproduce
     exactly the first search of a brand-new game.
  3. CROSS-CONFIGURATION ISOLATION: a `setoption` that clears the TT must also
     discard persisted ordering state, so the next search reproduces the
     virgin-configuration result. (handle_setoption clears the TT at six sites;
     before this experiment none of them reset the persisted Search.)
  4. DETERMINISM WHEN OFF: two FRESH engines with the switch OFF must produce
     identical sequences. (Within one engine the TT persists across `go`, so a
     later search of the same position legitimately costs fewer nodes; comparing
     those would confound transposition reuse with non-determinism.)
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

A = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 4"
B = "r2q1rk1/pp2ppbp/2np1np1/8/2BNP3/2N1BP2/PPPQ2PP/2KR3R w - - 5 11"


class Engine:
    def __init__(self, path, params, on, single=None):
        self.p = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.send("uci"); self.until("uciok")
        for line in ("setoption name Hash value 16", "setoption name Threads value 1",
                     f"setoption name EvalParams value {params}",
                     "setoption name TTEval value true",
                     "setoption name ContinuationHistory value true",
                     f"setoption name PersistentHistory value {'true' if on else 'false'}",
                     f"setoption name PersistentContinuation value {'true' if on else 'false'}"):
            self.send(line)
        if single == "history":
            self.send("setoption name PersistentContinuation value false")
        elif single == "continuation":
            self.send("setoption name PersistentHistory value false")
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

    def setoption(self, name, value):
        self.send(f"setoption name {name} value {value}")
        self.send("isready"); self.until("readyok")

    def close(self):
        try:
            self.send("quit"); self.p.wait(timeout=10)
        except Exception:
            self.p.kill()


def probe(path, params, on, single=None):
    e = Engine(path, params, on, single)
    e.newgame()
    first = e.nodes(A)
    seq = [first, e.nodes(B), e.nodes(A), e.nodes(B)]
    # (2) cross-game isolation
    e.newgame()
    after_newgame = e.nodes(A)
    # (3) cross-configuration isolation: dirty the table, then flip a boolean
    # option (which clears the TT) and re-measure the virgin position.
    e.nodes(B); e.nodes(A)
    e.setoption("TTEval", "true")
    after_setoption = e.nodes(A)
    e.close()
    return {"sequence": seq, "first": first,
            "after_ucinewgame": after_newgame,
            "after_setoption": after_setoption,
            "newgame_isolated": first == after_newgame,
            "setoption_isolated": first == after_setoption}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--params", required=True)
    ap.add_argument("--output")
    a = ap.parse_args()
    on = probe(a.engine, a.params, True)
    off = probe(a.engine, a.params, False)
    # Determinism must be measured across FRESH engines. Within one engine the
    # TT persists across `go`, so a later search of the same position legitimately
    # costs fewer nodes; asserting equality there would confound transposition
    # reuse with non-determinism (an error made in an earlier cycle).
    off_again = probe(a.engine, a.params, False)
    only_h = probe(a.engine, a.params, True, "history")
    only_c = probe(a.engine, a.params, True, "continuation")
    checks = {
        "persistence_across_go": on["sequence"] != off["sequence"],
        "cross_game_isolation_on": on["newgame_isolated"],
        "cross_configuration_isolation_on": on["setoption_isolated"],
        "cross_game_isolation_off": off["newgame_isolated"],
        "cross_configuration_isolation_off": off["setoption_isolated"],
        "off_path_is_deterministic_across_fresh_engines":
            off["sequence"] == off_again["sequence"],
        "joint_differs_from_history_only": on["sequence"] != only_h["sequence"],
        "joint_differs_from_continuation_only": on["sequence"] != only_c["sequence"],
    }
    ok = all(checks.values())
    out = {"mode": "uci_joint_lifetime", "on": on, "off": off,
           "history_only": only_h, "continuation_only": only_c,
           "checks": checks,
           "params_sha256": hashlib.sha256(Path(a.params).read_bytes()).hexdigest(),
           "verdict": "PASS" if ok else "FAIL"}
    text = json.dumps(out, indent=2, sort_keys=True)
    print(text)
    if a.output:
        Path(a.output).write_text(text + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
