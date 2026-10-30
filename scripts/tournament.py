#!/usr/bin/env python3
"""Paired-opening two-engine UCI matches. The engines remain external processes.

Optional development dependency: `pip install chess==1.11.2` (move legality,
standard game adjudication, PGN). Normal StockBear execution has no dependency.
For example:
  python scripts/tournament.py --engine-a build-release/stockbear \
      --engine-b /path/to/other-engine --games 8 --base-ms 1000 --inc-ms 20 \
      --pgn match.pgn --jsonl match.jsonl
"""
import argparse
import json
import math
import os
from pathlib import Path
import platform
import queue
import subprocess
import sys
import threading
import time
try:
    import chess
    import chess.pgn
except ImportError:
    sys.exit("Install the optional tournament dependency: pip install chess==1.11.2")


class UciEngine:
    def __init__(self, path, hash_mb, threads):
        self.path = os.path.abspath(path)
        self.p = subprocess.Popen([self.path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, bufsize=1)
        self.out = queue.Queue()
        self.err = []
        self.name = os.path.basename(path)
        self.options = {}
        threading.Thread(target=self._reader, args=(self.p.stdout, self.out), daemon=True).start()
        threading.Thread(target=self._stderr, daemon=True).start()
        try:
            self.send("uci")
            deadline = time.monotonic() + 10
            while True:
                line = self.read(deadline - time.monotonic())
                if line == "uciok":
                    break
                if line.startswith("id name "):
                    self.name = line[8:]
                if line.startswith("option name ") and " type " in line:
                    name = line[len("option name "):].split(" type ", 1)[0]
                    self.options[name.lower()] = name
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"{self.name} did not complete UCI handshake")
            self.effective = {}
            for option, value in (("hash", hash_mb), ("threads", threads)):
                if option in self.options:
                    self.send(f"setoption name {self.options[option]} value {value}")
                    self.effective[option] = f"requested {value}"
                elif option == "threads" and self.name.startswith("StockBear "):
                    if threads != 1:
                        raise ValueError("StockBear supports one search thread; use --threads 1")
                    self.effective[option] = "1 (StockBear single-threaded build)"
                else:
                    self.effective[option] = "not advertised / unverified"
            self.ready()

        except BaseException:
            self.close()
            raise

    @staticmethod
    def _reader(pipe, q):
        for line in iter(pipe.readline, ""):
            q.put(line.strip())
        q.put(None)

    def _stderr(self):
        for line in iter(self.p.stderr.readline, ""):
            # Bounded diagnostic tail; never stored as tournament results.
            self.err.append(line.rstrip())
            if len(self.err) > 100:
                self.err.pop(0)

    def send(self, text):
        if self.p.poll() is not None:
            raise RuntimeError(f"{self.name} exited with {self.p.returncode}: {self.err[-5:]}")
        self.p.stdin.write(text + "\n")
        self.p.stdin.flush()

    def read(self, timeout):
        try:
            line = self.out.get(timeout=max(.001, timeout))
        except queue.Empty as exc:
            raise TimeoutError(f"{self.name} did not respond within {timeout:.2f}s") from exc
        if line is None:
            raise RuntimeError(f"{self.name} exited: {self.err[-5:]}")
        return line

    def ready(self):
        self.send("isready")
        deadline = time.monotonic() + 10
        while True:
            if self.read(deadline - time.monotonic()) == "readyok":
                return
            if time.monotonic() >= deadline:
                raise TimeoutError(f"{self.name} did not become ready")

    def new_game(self):
        self.send("ucinewgame")
        self.ready()

    def bestmove(self, moves, clocks, increment, color):
        suffix = " moves " + " ".join(moves) if moves else ""
        self.send("position startpos" + suffix)
        self.send(f"go wtime {max(0, int(clocks[chess.WHITE]))} "
                  f"btime {max(0, int(clocks[chess.BLACK]))} winc {increment} binc {increment}")
        deadline = time.monotonic() + max(0, clocks[color]) / 1000 + 3
        while True:
            line = self.read(deadline - time.monotonic())
            if line.startswith("bestmove "):
                fields = line.split()
                if len(fields) < 2:
                    raise RuntimeError(f"malformed bestmove from {self.name}: {line}")
                return fields[1]
            if time.monotonic() >= deadline:
                raise TimeoutError(f"{self.name} exceeded its response deadline")

    def close(self):
        if self.p.poll() is None:
            try:
                self.send("quit")
                self.p.wait(timeout=3)
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                self.p.kill()
                self.p.wait(timeout=3)


def read_openings(path):
    openings = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" not in line:
            raise ValueError(f"invalid opening line: {line}")
        name, moves = line.split("|", 1)
        board = chess.Board()
        for move in moves.split():
            board.push_uci(move)  # validates each move
        openings.append((name.strip(), moves.split()))
    if not openings:
        raise ValueError("opening suite is empty")
    return openings


def elo_for(score):
    if score <= 0:
        return "-inf"
    if score >= 1:
        return "+inf"
    return round(400 * math.log10(score / (1 - score)), 1)


def statistics(results):
    n = len(results)
    wins, draws, losses = results.count(1), results.count(.5), results.count(0)
    if not n:
        return {"games": 0, "wins": 0, "draws": 0, "losses": 0, "note": "no completed games"}
    p = sum(results) / n
    # Approximate Wilson interval on fractional scores. It avoids the false
    # zero-width interval at 0%/100%, but does not model opening-pair effects.
    z = 1.959963984540054
    denominator = 1 + z*z/n
    center = (p + z*z/(2*n)) / denominator
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denominator
    lo, hi = max(0, center-half), min(1, center+half)
    return {"games": n, "wins": wins, "draws": draws, "losses": losses,
            "score": round(p, 4), "score_ci95_approx": [round(lo, 4), round(hi, 4)],
            "elo_difference": elo_for(p), "elo_ci95_approx": [elo_for(lo), elo_for(hi)],
            "ci_method": "Wilson on fractional game scores; approximation ignores pair dependence"}


def play_game(a, b, index, opening, base_ms, inc_ms, max_plies):
    opening_name, opening_moves = opening
    white, black = (a, b) if index % 2 == 0 else (b, a)
    board = chess.Board()
    game = chess.pgn.Game()
    game.headers.update({"Event": "StockBear paired-opening match", "Site": "local",
                         "White": white.name, "Black": black.name,
                         "Round": str(index + 1), "Opening": opening_name,
                         "TimeControl": f"{base_ms/1000:g}+{inc_ms/1000:g}"})
    node = game
    for text in opening_moves:
        move = board.parse_uci(text)
        board.push(move)
        node = node.add_variation(move)
    moves = opening_moves.copy()
    clocks = {chess.WHITE: float(base_ms), chess.BLACK: float(base_ms)}
    for engine in (a, b):
        engine.new_game()
    termination = None
    result = "*"
    while len(moves) < max_plies:
        outcome = board.outcome(claim_draw=True)
        if outcome is not None:
            result = outcome.result()
            termination = outcome.termination.name
            break
        color = board.turn
        engine = white if color == chess.WHITE else black
        start = time.monotonic_ns()
        error = None
        text = None
        try:
            text = engine.bestmove(moves, clocks, inc_ms, color)
        except (RuntimeError, TimeoutError, OSError) as exc:
            error = exc
        elapsed = (time.monotonic_ns() - start) / 1_000_000
        clocks[color] -= elapsed
        if clocks[color] < 0:
            result = "0-1" if color == chess.WHITE else "1-0"
            termination = f"TIME_FORFEIT ({engine.name}, {elapsed:.1f}ms move)"
            break
        if error is None:
            try:
                move = chess.Move.from_uci(text)
                if move not in board.legal_moves:
                    raise ValueError(f"illegal move {text}")
            except ValueError as exc:
                error = exc
        if error is not None:
            result = "0-1" if color == chess.WHITE else "1-0"
            termination = f"ENGINE_FAILURE ({engine.name}: {error})"
            break
        board.push(move)
        node = node.add_variation(move)
        moves.append(move.uci())
        clocks[color] += inc_ms
    if termination is None:
        outcome = board.outcome(claim_draw=True)
        if outcome is not None:
            result, termination = outcome.result(), outcome.termination.name
        else:
            termination = "UNADJUDICATED_MAX_PLIES"
    game.headers["Result"] = result
    game.headers["Termination"] = termination
    score_a = None
    if result == "1/2-1/2":
        score_a = .5
    elif result in ("1-0", "0-1"):
        white_won = result == "1-0"
        score_a = 1 if (white is a) == white_won else 0
    return game, {"game": index+1, "opening": opening_name, "white": white.name,
                  "black": black.name, "result": result, "score_a": score_a,
                  "termination": termination, "plies": len(moves),
                  "remaining_white_ms": round(clocks[chess.WHITE], 2),
                  "remaining_black_ms": round(clocks[chess.BLACK], 2)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-a", required=True)
    parser.add_argument("--engine-b", required=True)
    parser.add_argument("--games", type=int, default=8, help="even number; paired colors per opening")
    parser.add_argument("--base-ms", type=int, default=1000)
    parser.add_argument("--inc-ms", type=int, default=20)
    parser.add_argument("--hash", type=int, default=16, help="requested MB for each engine")
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--max-plies", type=int, default=300)
    parser.add_argument("--openings", default=str(Path(__file__).resolve().parents[1] /
                                                 "benchmarks/positions/openings.txt"))
    parser.add_argument("--pgn", default="match.pgn")
    parser.add_argument("--jsonl", default="match.jsonl")
    args = parser.parse_args()
    if args.games < 2 or args.games % 2:
        parser.error("--games must be positive and even")
    if args.base_ms < 1 or args.inc_ms < 0 or not 1 <= args.hash <= 512 or args.threads < 1 or args.max_plies < 1:
        parser.error("invalid clock, hash, thread or ply limit")
    openings = read_openings(args.openings)
    engines = []
    try:
        engines.append(UciEngine(args.engine_a, args.hash, args.threads))
        engines.append(UciEngine(args.engine_b, args.hash, args.threads))
        a, b = engines
        config = {"engine_a": a.name, "engine_b": b.name,
                  "engine_a_path": a.path, "engine_b_path": b.path,
                  "engine_a_options": a.effective, "engine_b_options": b.effective,
                  "base_ms": args.base_ms, "increment_ms": args.inc_ms,
                  "hash_requested_mb_each": args.hash, "threads_requested_each": args.threads,
                  "host": platform.platform(), "machine": platform.machine(),
                  "python_chess": chess.__version__, "opening_file": args.openings,
                  "policy": "claimable draws automatically claimed; capped games unadjudicated"}
        print(json.dumps({"configuration": config}), flush=True)
        scores = []
        with open(args.pgn, "w", encoding="utf-8") as pgn, open(args.jsonl, "w", encoding="utf-8") as log:
            log.write(json.dumps({"configuration": config}) + "\n")
            for i in range(args.games):
                game, record = play_game(a, b, i, openings[(i//2) % len(openings)],
                                         args.base_ms, args.inc_ms, args.max_plies)
                if i:
                    print(file=pgn)  # one separator between games, none after the last
                print(game, file=pgn, flush=True)
                log.write(json.dumps(record) + "\n"); log.flush()
                print(json.dumps(record), flush=True)
                if record["score_a"] is not None:
                    scores.append(record["score_a"])
            summary = statistics(scores)
            summary["unadjudicated"] = args.games - len(scores)
            log.write(json.dumps({"summary": summary}) + "\n")
            print(json.dumps({"summary": summary}), flush=True)
    finally:
        for e in engines:
            e.close()

if __name__ == "__main__":
    main()
