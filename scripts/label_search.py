#!/usr/bin/env python3
"""Label positions with a teacher engine's search score (dev5 research tool).

Reads a StockBear self-play corpus (``<result> <game> <fen>`` lines) or a plain
FEN-per-line file, deduplicates exact FENs, optionally samples positions per
game, and asks a teacher engine (any UCI engine, e.g. a pinned Stockfish build
used strictly as an external research tool, never shipped) for a fixed-node
search score of every position. Output lines:

    <cp> <game> <fen>

where ``cp`` is the score from the point of view of the side to move in the
FEN, mate scores mapped to +/-3000. The teacher's binary, options, node budget
and checksum are recorded in the output header comment, so every label is
traceable to an exact teacher configuration.

The teacher is only ever executed as an independent process here; no teacher
code, weights or data are incorporated into StockBear.

Usage:
  python3 scripts/label_search.py --corpus data/corpusA.txt [--corpus ...] \
      --engine data/teacher/Stockfish-sf_11/src/stockfish \
      --nodes 30000 --workers 2 --out data/labels.txt \
      [--min-ply 8] [--sample-every 2] [--max-per-game 40] [--limit N]
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import threading
import queue
from pathlib import Path

import chess


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class Uci:
    def __init__(self, path, options=None):
        self.proc = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.send("uci")
        while True:
            line = self.proc.stdout.readline()
            if not line or line.strip() == "uciok":
                break
        for name, value in (options or {}).items():
            self.send(f"setoption name {name} value {value}")
        self.send("isready")
        while self.proc.stdout.readline().strip() != "readyok":
            pass

    def send(self, text):
        self.proc.stdin.write(text + "\n")
        self.proc.stdin.flush()

    def score_nodes(self, fen, nodes):
        self.send(f"position fen {fen}")
        self.send(f"go nodes {nodes}")
        cp = None
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("teacher died")
            line = line.strip()
            if line.startswith("info") and " score " in line:
                parts = line.split()
                i = parts.index("score")
                if parts[i + 1] == "cp":
                    cp = int(parts[i + 2])
                else:  # mate
                    m = int(parts[i + 2])
                    cp = 3000 if m > 0 else -3000
            elif line.startswith("bestmove"):
                break
        if cp is None:
            cp = 0
        return max(-3000, min(3000, cp))

    def close(self):
        try:
            self.send("quit")
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def read_positions(args):
    """Yield (game, ply, fen). From corpus files or plain FEN files."""
    seen = set()
    count = 0
    for path in args.corpus:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(None, 2)
                if len(parts) == 3 and parts[0] in ("0", "0.5", "1", "1.0", "0.0"):
                    result, game, fen = parts
                    game = int(game)
                else:
                    result, game, fen = None, -1, line
                board = chess.Board(fen)
                ply = board.ply()
                if ply < args.min_ply:
                    continue
                if ply % args.sample_every != 0:
                    continue
                # dedup by the fields the NNUE features actually see
                key = " ".join(fen.split()[:4])
                if key in seen:
                    continue
                seen.add(key)
                yield game, ply, fen, result
                count += 1
                if args.limit and count >= args.limit:
                    return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", action="append", required=True)
    ap.add_argument("--engine", required=True)
    ap.add_argument("--nodes", type=int, default=30000)
    ap.add_argument("--depth", type=int, default=0, help="use depth instead of nodes if > 0")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-ply", type=int, default=8)
    ap.add_argument("--sample-every", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-per-game", type=int, default=40)
    ap.add_argument("--hash", type=int, default=64)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--options", default="", help="extra 'Name=Value,Name=Value' teacher options")
    ap.add_argument("--exclude", default="",
                    help="file with already-labelled positions; their board keys are skipped")
    args = ap.parse_args()

    positions = list(read_positions(args))
    if args.exclude:
        have = set()
        with open(args.exclude, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                have.add(" ".join(line.split(" ", 2)[2].split()[:4]))
        before = len(positions)
        positions = [p for p in positions if " ".join(p[2].split()[:4]) not in have]
        print(f"excluded {before - len(positions)} already-labelled positions", flush=True)
    # Per-game cap on labelled positions.
    per_game = {}
    kept = []
    for game, ply, fen, result in positions:
        if per_game.get(game, 0) >= args.max_per_game:
            continue
        per_game[game] = per_game.get(game, 0) + 1
        kept.append((game, fen, result))
    positions = kept
    print(f"{len(positions)} unique positions to label", flush=True)

    engine_hash = sha256_file(args.engine)
    options = {"Hash": str(args.hash), "Threads": str(args.threads)}
    for item in filter(None, args.options.split(",")):
        name, value = item.split("=", 1)
        options[name] = value

    work = queue.Queue()
    for i, (game, fen, result) in enumerate(positions):
        work.put((i, game, fen, result))
    results = [None] * len(positions)
    lock = threading.Lock()

    def worker():
        eng = Uci(args.engine, options)
        while True:
            try:
                i, game, fen, result = work.get_nowait()
            except queue.Empty:
                break
            cp = eng.score_nodes(fen, args.nodes) if args.depth == 0 else None
            if args.depth:
                eng.send(f"position fen {fen}")
                eng.send(f"go depth {args.depth}")
                cp = None
                while True:
                    line = eng.proc.stdout.readline()
                    if not line:
                        raise RuntimeError("teacher died")
                    line = line.strip()
                    if line.startswith("info") and " score " in line:
                        parts = line.split()
                        j = parts.index("score")
                        cp = int(parts[j + 2]) if parts[j + 1] == "cp" else (3000 if int(parts[j + 2]) > 0 else -3000)
                    elif line.startswith("bestmove"):
                        break
                cp = max(-3000, min(3000, cp or 0))
            with lock:
                results[i] = (cp, game, fen, result)
                if i % 2000 == 0:
                    done = sum(1 for r in results if r)
                    print(f"  labelled {done}/{len(positions)}", flush=True)
        eng.close()

    threads = [threading.Thread(target=worker) for _ in range(args.workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    with open(args.out, "w", encoding="utf-8") as out:
        out.write(f"# teacher={args.engine} sha256={engine_hash} nodes={args.nodes} depth={args.depth} "
                  f"options={options} workers={args.workers} min_ply={args.min_ply} "
                  f"sample_every={args.sample_every}\n")
        n = 0
        for cp, game, fen, result in results:
            if cp is None:
                continue
            out.write(f"{cp} {game} {fen}\n")
            n += 1
    print(f"wrote {n} labels to {args.out}", flush=True)


if __name__ == "__main__":
    main()
