#!/usr/bin/env python3
"""Exhaust movement-only graphs for two small dead positions with python-chess.

Not a FIDE adjudicator: automatic draw history is deliberately ignored.
Optional development dependency: chess==1.11.2. Independent of StockBear.
"""
from collections import deque
import time
import chess

CASES = [
    ("forced rook capture", "8/8/8/8/8/8/3R4/K1k5 b - - 0 1", 7225),
    ("promotion trap", "6B1/5K1k/8/5N2/8/8/8/8 b - - 0 1", 436665),
]

def identity(board):
    return board.fen(en_passant="fen").rsplit(" ", 2)[0]

def explore(fen):
    initial = identity(chess.Board(fen))
    seen = {initial}
    queue = deque([initial])
    mates = 0
    while queue:
        board = chess.Board(queue.popleft() + " 0 1")
        mates += board.is_checkmate()
        for move in list(board.legal_moves):
            board.push(move)
            child = identity(board)
            board.pop()
            if child not in seen:
                seen.add(child)
                queue.append(child)
    return len(seen), mates

if __name__ == "__main__":
    for name, fen, expected in CASES:
        started = time.monotonic()
        count, mates = explore(fen)
        print(f"{name}: positions={count} mates={mates} seconds={time.monotonic()-started:.2f}", flush=True)
        if mates or count != expected:
            raise SystemExit("Unexpected count or mate")
