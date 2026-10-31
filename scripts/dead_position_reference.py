#!/usr/bin/env python3
"""Independent reference check for StockBear's FIDE 5.2.2 dead-position analyzer.

This script deliberately re-implements the decision procedure from scratch on top
of python-chess (move generation, make/unmake, mate detection). It never calls
StockBear's own move generator, so agreement is evidence that StockBear's
analyzer and legal move generation are consistent with an independent
implementation.

The article 5.2.2 question is decided here by enumerating the complete reachable
state component (placement, side to move, castling rights, en-passant square)
and testing whether any member of it is checkmate. That is exact but expensive,
so positions whose component exceeds --max-states are reported as skipped
instead of guessed.

Usage:
  python3 scripts/dead_position_reference.py ./build/stockbear [--positions FILE]
"""
import argparse
import subprocess
import sys
from collections import deque

try:
    import chess
except ImportError:  # pragma: no cover - development dependency only
    sys.exit("Install the optional reference dependency: pip install chess==1.11.2")


def state_key(board):
    return " ".join([
        board.board_fen(),
        "w" if board.turn == chess.WHITE else "b",
        board.castling_xfen().replace("-", "-"),
        chess.square_name(board.ep_square) if board.ep_square is not None else "-",
    ])


def reference_status(fen, max_states):
    """Return (status, states) where status is 'alive', 'dead' or 'skipped'."""
    board = chess.Board(fen, chess960=False)
    board.clear_stack()
    if board.is_checkmate() or board.is_stalemate():
        return "terminal", 0
    seen = {state_key(board)}
    queue = deque([board])
    states = 1
    while queue:
        board = queue.popleft()
        # Materialise the move list: iterating the lazy generator while the
        # board is pushed and popped is not safe in python-chess.
        for move in list(board.legal_moves):
            board.push(move)
            key = state_key(board)
            if key not in seen:
                if board.is_checkmate():
                    return "alive", states
                seen.add(key)
                states += 1
                if states > max_states:
                    return "skipped", states
                queue.append(board.copy(stack=False))
            board.pop()
    return "dead", states


def engine_status(binary, fen, max_states, witness_nodes, witness_depth):
    out = subprocess.run(
        [binary, "deadpos", "--fen", fen, "--states", str(max_states),
         "--witness-nodes", str(witness_nodes), "--witness-depth", str(witness_depth)],
        check=False, capture_output=True, text=True, timeout=1800,
    )
    fields = {}
    for line in out.stdout.splitlines():
        key, _, value = line.partition(" ")
        fields[key] = value
    return fields


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", help="path to the StockBear executable")
    parser.add_argument("--positions", help="optional file with one FEN per line")
    parser.add_argument("--max-states", type=int, default=400000,
                        help="reference search cap; larger components are skipped")
    parser.add_argument("--full", action="store_true",
                        help="also check pawnless three-piece endgames, whose "
                             "components need hundreds of thousands of python-chess "
                             "positions and therefore several minutes")
    args = parser.parse_args()

    positions = []
    if args.positions:
        with open(args.positions, encoding="utf-8") as handle:
            positions = [line.strip() for line in handle if line.strip() and not line.startswith("#")]
    else:
        # A deterministic spread over the three-piece space, where the component
        # is small enough for an exhaustive independent enumeration, plus
        # locked pawn positions whose component is small by construction.
        cheap = [
            "8/8/8/4k3/8/8/8/4K3 w - - 0 1",
            "8/8/8/4k3/8/8/8/4K3 b - - 0 1",
            "8/8/8/8/4k3/8/8/2B1K3 w - - 0 1",
            "8/8/8/8/8/2k5/8/1Q2K3 w - - 0 1",
            "8/8/8/8/4k3/8/8/1R2K3 b - - 0 1",
            "8/3k4/p1p2p1p/PpPp1PpP/1P1P2P1/4K3/8/8 w - - 6 49",
            "8/3k4/p1p2p1p/PpPp1PpP/1P1P2P1/4K3/8/8 b - - 6 49",
            "4k3/4p3/4P3/8/8/8/8/4K3 w - - 0 1",
            "4k3/4p3/4P3/8/8/8/8/4K3 b - - 0 1",
        ]
        expensive = [
            "8/8/8/8/4k3/8/8/2B1K3 b - - 0 1",
            "8/8/8/8/4k3/8/8/2N1K3 w - - 0 1",
            "8/8/8/8/4k3/8/8/2N1K3 b - - 0 1",
        ]
        positions = cheap + (expensive if args.full else [])

    failures = 0
    compared = 0
    skipped = 0
    for fen in positions:
        status, states = reference_status(fen, args.max_states)
        if status in ("skipped", "terminal"):
            skipped += 1
            print(f"SKIP  reference={status} states={states} {fen}")
            continue
        fields = engine_status(args.engine, fen, max_states=3000000,
                               witness_nodes=150000, witness_depth=12)
        engine = fields.get("status")
        if engine is None:
            failures += 1
            print(f"FAIL  engine produced no verdict for {fen}")
            continue
        if engine != status:
            failures += 1
            print(f"FAIL  engine={engine} reference={status} states={states} {fen}")
        else:
            compared += 1
            print(f"OK    {status} states={states} {fen}")
    print(f"\ncompared {compared}, skipped {skipped}, failures {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
