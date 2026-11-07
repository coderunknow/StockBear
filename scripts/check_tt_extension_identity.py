#!/usr/bin/env python3
"""exp-0064 INDEPENDENT soundness oracle for TTExtensionAgnostic.

The C++ unit tests pin the implementation's own contract. This oracle is
independent: it drives the real engine over UCI and verifies every tactical
claim with python-chess, which shares no code with the engine.

Checks, on each sampled position, with the switch ON and OFF:
  1. every PV move is legal in python-chess (no illegal-move corruption);
  2. every reported `score mate N` is REAL: replaying the PV ends in checkmate
     and the PV length is exactly 2*N-1 plies for a mate delivered by the side
     to move (or 2*N for a mate received);
  3. no `score cp` is emitted inside the mate range;
  4. terminal scores agree between arms on checkmate/stalemate positions.

A wrong mate claim is exactly the failure mode a slimmer TT identity could
introduce, so this is the load-bearing soundness evidence.

Usage: check_tt_extension_identity.py --engine PATH --params FILE --epd FILE
                                      [--count N] [--depth D] [--output FILE]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import chess

MATE_BOUND = 30000


class Engine:
    def __init__(self, path: str, params: str, agnostic: bool):
        self.p = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.send("uci")
        self.read_until("uciok")
        self.send("setoption name Hash value 16")
        self.send("setoption name Threads value 1")
        self.send(f"setoption name EvalParams value {params}")
        self.send("setoption name TTEval value true")
        self.send(f"setoption name TTExtensionAgnostic value {'true' if agnostic else 'false'}")
        self.send("isready")
        self.read_until("readyok")
        self.options_seen = True

    def send(self, line: str) -> None:
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()

    def read_until(self, token: str) -> list[str]:
        out = []
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("engine closed stdout")
            line = line.strip()
            out.append(line)
            if line == token or line.startswith(token + " "):
                return out

    def search_nodes(self, fen: str, depth: int) -> int:
        self.send("ucinewgame")
        self.send(f"position fen {fen}")
        self.send(f"go depth {depth}")
        lines = self.read_until("bestmove")
        nodes = 0
        for line in lines:
            if line.startswith("info ") and " nodes " in line:
                toks = line.split()
                nodes = int(toks[toks.index("nodes") + 1])
        return nodes

    def search(self, fen: str, depth: int) -> dict:
        self.send("ucinewgame")
        self.send(f"position fen {fen}")
        self.send(f"go depth {depth}")
        lines = self.read_until("bestmove")
        best = None
        info = None
        for line in lines:
            if line.startswith("bestmove"):
                best = line.split()[1]
            elif line.startswith("info ") and " pv " in line:
                info = line
        result = {"bestmove": best, "mate": None, "cp": None, "pv": []}
        if info:
            toks = info.split()
            if "mate" in toks:
                result["mate"] = int(toks[toks.index("mate") + 1])
            if "cp" in toks:
                result["cp"] = int(toks[toks.index("cp") + 1])
            result["pv"] = info.split(" pv ", 1)[1].split()
        return result

    def close(self) -> None:
        try:
            self.send("quit")
            self.p.wait(timeout=10)
        except Exception:
            self.p.kill()


def verify(fen: str, res: dict) -> list[str]:
    problems = []
    board = chess.Board(fen)
    if res["cp"] is not None and abs(res["cp"]) >= MATE_BOUND:
        problems.append(f"cp score inside mate range: {res['cp']}")
    plies = 0
    for uci in res["pv"]:
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            problems.append(f"unparseable PV move {uci}")
            break
        if move not in board.legal_moves:
            problems.append(f"illegal PV move {uci} at {board.fen()}")
            break
        board.push(move)
        plies += 1
        if board.is_game_over(claim_draw=False):
            break
    if res["mate"] is not None:
        n = res["mate"]
        if n > 0:
            # Side to move mates in n moves => 2n-1 plies, final side is the
            # opponent and it is checkmated.
            if not board.is_checkmate():
                problems.append(f"claimed mate in {n} but PV does not end in checkmate")
            if plies != 2 * n - 1:
                problems.append(f"claimed mate in {n} but PV has {plies} plies (want {2*n-1})")
        elif n < 0:
            if not board.is_checkmate():
                problems.append(f"claimed losing mate {n} but PV does not end in checkmate")
            if plies != 2 * abs(n):
                problems.append(f"claimed losing mate {n} but PV has {plies} plies (want {2*abs(n)})")
        else:
            problems.append("score mate 0 without a terminal position")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--params", required=True)
    ap.add_argument("--epd", required=True)
    ap.add_argument("--count", type=int, default=150)
    ap.add_argument("--depth", type=int, default=7)
    ap.add_argument("--output")
    ap.add_argument("--liveness", action="store_true",
                    help="assert the UCI option reaches the search (exact node pins)")
    args = ap.parse_args()

    if args.liveness:
        # End-to-end UCI wiring proof: the parsed option must reproduce exactly
        # the audited ON/OFF trees. Hash 4, depth 6, EvalParams = the frozen race
        # file; verified deterministic across three consecutive runs.
        fen = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 4"
        pins = {}
        for label, flag in (("off", False), ("on", True)):
            e = Engine(args.engine, args.params, flag)
            e.send("setoption name Hash value 4")
            e.send("isready"); e.read_until("readyok")
            pins[label] = e.search_nodes(fen, 6)
            e.close()
        import hashlib
        expected = {"off": 31377, "on": 31359}
        ok = pins == expected
        out = {"mode": "uci_liveness", "expected": expected, "observed": pins,
               "params_sha256": hashlib.sha256(Path(args.params).read_bytes()).hexdigest(),
               "hash_mb": 4, "depth": 6, "verdict": "PASS" if ok else "FAIL"}
        text = json.dumps(out, indent=2, sort_keys=True)
        print(text)
        if args.output:
            Path(args.output).write_text(text + "\n")
        return 0 if ok else 1

    fens = []
    for line in Path(args.epd).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        # EPD rows here are full FENs; tolerate bare EPD by appending defaults.
        fen = line if len(parts) >= 6 else " ".join(parts[:4]) + " 0 1"
        try:
            board = chess.Board(fen)
        except ValueError:
            continue
        if board.is_valid() and not board.is_game_over(claim_draw=False):
            fens.append(board.fen())
        if len(fens) >= args.count:
            break
    # Deliberate terminal and near-terminal mates, independent of the corpus.
    tactical = [
        "7k/5Q2/6K1/8/8/8/8/8 w - - 0 1",
        "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1",
        "8/8/8/5Q2/k7/8/1K6/8 w - - 0 1",
        "6k1/5ppp/8/8/8/8/5PPP/1R4K1 w - - 0 1",
        "r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4",
    ]
    problems: list[str] = []
    stats = {"positions": 0, "mate_claims_on": 0, "mate_claims_off": 0,
             "pv_moves_verified": 0, "problems": []}
    on = Engine(args.engine, args.params, True)
    off = Engine(args.engine, args.params, False)
    try:
        for fen in tactical + fens:
            board = chess.Board(fen)
            ron = on.search(fen, args.depth)
            roff = off.search(fen, args.depth)
            stats["positions"] += 1
            for label, res in (("ON", ron), ("OFF", roff)):
                found = verify(fen, res)
                problems.extend(f"{label} {fen}: {p}" for p in found)
                stats["pv_moves_verified"] += len(res["pv"])
                if res["mate"] is not None:
                    stats["mate_claims_on" if label == "ON" else "mate_claims_off"] += 1
            # Terminal positions must be scored identically by both arms.
            if board.is_checkmate() or board.is_stalemate():
                if ron["mate"] != roff["mate"] or ron["cp"] != roff["cp"]:
                    problems.append(f"terminal score differs: {fen} ON={ron} OFF={roff}")
    finally:
        on.close()
        off.close()
    stats["problems"] = problems
    stats["verdict"] = "PASS" if not problems else "FAIL"
    text = json.dumps(stats, indent=2, sort_keys=True)
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
