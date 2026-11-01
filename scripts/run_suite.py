#!/usr/bin/env python3
"""Run StockBear over the EPD suites and record reproducible results.

Two modes:

  tactics     For every position, search with a fixed node budget and check that
              the returned move is one of the pre-proved mating moves. A hit is
              recorded as solved; a search that ends because it exhausted the
              node budget is recorded as "limit reached" even when the move was
              right, so the two can be told apart in the report.

  endgames    Play the position out with the engine on both sides at a fixed
              node budget until checkmate or the fifty-move rule, and let
              python-chess adjudicate the game. These are theoretical wins, so
              only mate inside the fifty-move rule counts as solved.

Raw engine output is kept verbatim next to the JSON so any claim can be
re-checked without re-running the engine.

Usage:
  python3 scripts/run_suite.py --engine build/stockbear --epd benchmarks/tactics/mate_suite.epd \
      --mode tactics --nodes 100000 --json out.json --raw out.txt
"""
import argparse
import json
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import chess


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", required=True)
    parser.add_argument("--epd", required=True)
    parser.add_argument("--mode", choices=("tactics", "endgames"), required=True)
    parser.add_argument("--nodes", type=int, default=100000)
    parser.add_argument("--json", required=True)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--hash", type=int, default=32)
    parser.add_argument("--max-plies", type=int, default=200,
                        help="endgame mode: give up after this many plies")
    return parser.parse_args()


class Engine:
    def __init__(self, path, hash_mb):
        self.process = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, bufsize=1)
        self.log = []
        # A reader thread keeps the deadline in `until` meaningful: a blocking
        # readline() would hang forever if the engine stayed alive but stopped
        # writing, which is exactly the failure this harness must not have.
        self.queue = queue.Queue()
        self.reader = threading.Thread(target=self._pump, daemon=True)
        self.reader.start()
        self.send("uci")
        hello = self.until(lambda line: line == "uciok")
        self.name = next((line[len("id name "):] for line in hello if line.startswith("id name ")),
                         "unknown")
        self.send(f"setoption name Hash value {hash_mb}")
        self.send("isready")
        self.until(lambda line: line == "readyok")
        self.send("ucinewgame")

    def _pump(self):
        for raw in self.process.stdout:
            self.queue.put(raw.rstrip("\r\n"))
        self.queue.put(None)  # end of stream

    def send(self, line):
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()

    def until(self, predicate, timeout=300):
        batch = []
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self.process.kill()
                raise SystemExit(f"timed out waiting for engine; last lines {batch[-5:]}")
            try:
                line = self.queue.get(timeout=remaining)
            except queue.Empty:
                self.process.kill()
                raise SystemExit(f"timed out waiting for engine; last lines {batch[-5:]}")
            if line is None:
                raise SystemExit(f"engine exited; stderr={self.process.stderr.read()}")
            self.log.append(line)
            batch.append(line)
            if predicate(line):
                return batch

    def search(self, fen, nodes):
        self.send("position fen " + fen)
        self.send(f"go nodes {nodes}")
        lines = self.until(lambda line: line.startswith("bestmove "))
        bestmove = lines[-1].split()[1]
        depth = nodes_reported = 0
        mate_line = None
        for line in lines:
            fields = line.split()
            if line.startswith("info ") and "depth" in fields and "pv" in fields:
                depth = int(fields[fields.index("depth") + 1])
                if "nodes" in fields:
                    nodes_reported = int(fields[fields.index("nodes") + 1])
                if mate_line is None and "mate" in fields:
                    mate_line = line
        # Once a forced mate is proved, every further iteration is nearly free
        # (the mate bounds cut the tree immediately), so the reported depth climbs
        # to the search horizon instead of stopping. The interesting numbers are
        # therefore the first mate line and the node count, not the last depth;
        # both are kept so nobody has to guess which one is quoted.
        mate_depth = 0
        if mate_line is not None:
            fields = mate_line.split()
            mate_depth = int(fields[fields.index("depth") + 1])
        self.last_mate_depth = mate_depth
        return bestmove, depth, nodes_reported, lines

    def close(self):
        try:
            self.send("quit")
            self.process.wait(timeout=10)
        except (subprocess.TimeoutExpired, BrokenPipeError):
            self.process.kill()


def load_epd(path):
    """Minimal EPD reader: FEN, `bm` (SAN) and `id`."""
    entries = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        ops = [op.strip() for op in line.split(";") if op.strip()]
        head = ops[0].split(' id "')[0]
        fen = head.split(" bm ")[0]
        # EPD board descriptions carry four fields; the engine's FEN parser is
        # strict, so pad with a zeroed halfmove clock and move number. Neither
        # affects a fixed-node search from a fresh position.
        if len(fen.split()) == 4:
            fen = fen + " 0 1"
        bm = []
        if " bm " in head:
            bm = head.split(" bm ", 1)[1].split()
        identifier = "?"
        for op in ops:
            if ' id "' in op:
                identifier = op.split(' id "', 1)[1].split('"')[0]
            elif op.startswith("id "):
                identifier = op[3:].strip().strip('"')
        entries.append({"fen": fen, "id": identifier, "bm": bm})
    return entries


def run_tactics(engine, entries, nodes):
    results = []
    for entry in entries:
        board = chess.Board(entry["fen"])
        start = time.monotonic()
        bestmove, depth, nodes_reported, lines = engine.search(entry["fen"], nodes)
        elapsed = time.monotonic() - start
        accepted = set()
        for token in entry["bm"]:
            try:
                accepted.add(board.parse_san(token).uci())
            except ValueError:
                accepted.add(token)
        hit = bestmove in accepted
        limit_reached = nodes_reported >= nodes
        results.append({
            "id": entry["id"],
            "fen": entry["fen"],
            "bestmove": bestmove,
            "accepted": sorted(accepted),
            "solved": hit,
            "limit_reached": limit_reached,
            "nodes": nodes_reported,
            "depth": depth,
            "mate_depth": engine.last_mate_depth,
            "time_ms": round(elapsed * 1000),
            "mate_score": next((line for line in reversed(lines)
                                if line.startswith("info ") and "score mate" in line), ""),
        })
        print(f"{entry['id']}: {bestmove} {'OK' if hit else 'MISS'} "
              f"nodes={nodes_reported} depth={depth} {'(limit)' if limit_reached else ''}")
    return results


def run_endgames(engine, entries, nodes, max_plies):
    results = []
    for entry in entries:
        board = chess.Board(entry["fen"])
        plies = 0
        start = time.monotonic()
        moves = []
        illegal = None
        while plies < max_plies and not board.is_game_over(claim_draw=True):
            bestmove, _, nodes_reported, _ = engine.search(board.fen(), nodes)
            if bestmove == "0000":
                break
            move = chess.Move.from_uci(bestmove)
            if move not in board.legal_moves:
                illegal = bestmove
                break
            moves.append(bestmove)
            board.push(move)
            plies += 1
        elapsed = time.monotonic() - start
        mated = board.is_checkmate()
        results.append({
            "id": entry["id"],
            "fen": entry["fen"],
            "illegal_move": illegal,
            "mate": mated,
            "solved": bool(mated and plies <= max_plies and illegal is None),
            "plies": plies,
            "moves": moves,
            "termination": ("CHECKMATE" if mated else
                            "FIFTY_MOVE" if board.is_fifty_moves() else
                            "SEVENTYFIVE_MOVE" if board.is_seventyfive_moves() else
                            "STALEMATE" if board.is_stalemate() else
                            "INSUFFICIENT" if board.is_insufficient_material() else
                            "PLY_LIMIT"),
            "time_ms": round(elapsed * 1000),
        })
        print(f"{entry['id']}: {'mate' if mated else 'no mate'} in {plies} plies")
    return results


def main():
    args = parse_args()
    engine = Engine(args.engine, args.hash)
    try:
        entries = load_epd(args.epd)
        if args.mode == "tactics":
            results = run_tactics(engine, entries, args.nodes)
        else:
            results = run_endgames(engine, entries, args.nodes, args.max_plies)
    finally:
        engine.close()
        Path(args.raw).parent.mkdir(parents=True, exist_ok=True)
        Path(args.raw).write_text("\n".join(engine.log) + "\n", encoding="utf-8")
    solved = sum(1 for r in results if r.get("solved"))
    summary = {
        "engine": engine.name,
        "engine_sha256": "",
        "mode": args.mode,
        "epd": args.epd,
        "epd_sha256": __import__("hashlib").sha256(Path(args.epd).read_bytes()).hexdigest(),
        "nodes": args.nodes,
        "positions": len(results),
        "solved": solved,
        "limit_reached": sum(1 for r in results if r.get("limit_reached")),
        "failures": [r["id"] for r in results if not r.get("solved")],
        "results": results,
    }
    binary = Path(args.engine)
    if binary.is_file():
        summary["engine_sha256"] = __import__("hashlib").sha256(binary.read_bytes()).hexdigest()
    Path(args.json).write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(f"{solved}/{len(results)} solved; failures: {summary['failures']}")
    return 0 if solved == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
