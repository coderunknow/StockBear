#!/usr/bin/env python3
"""Independent reference for exp-0053 material-exposure (threat) detection.

Shares NO code with the engine. python-chess generates every attack set, and the
weights / cap are re-implemented here from the written specification. Compares
the engine's `eval_breakdown` counts (via `evaldata`) against this reference on
freshly generated positions.

Specification being verified (per side `us`, enemy `them`):
  by[c]      = union of attacks by colour c's P,N,B,R,Q
  byPawn[c]  = union of attacks by colour c's pawns
  atkUs      = by[us]   | king attacks of us
  defThem    = by[them] | king attacks of them
  hanging    = enemy NON-PAWN pieces & atkUs & ~defThem
  pawnThreat = ANY enemy piece & byPawn[us]
  units      = min(10*|hanging| + 16*|pawnThreat|, 64)
  breakdown contribution, White's viewpoint:
      ThreatDetection += units(White) - units(Black)

Note the reference deliberately builds the unions with its own loop; the engine's
hot path fuses them into pre-existing mobility / king-danger loops. Agreement
therefore checks the fusion, not just the formula.

Usage: check_threats.py --engine build-rel/stockbear --params F [--positions N]
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import tempfile
from pathlib import Path

import chess

W_HANGING = 10
W_PAWN = 16
UNITS_MAX = 64
NON_KING = (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)


def unions(board: chess.Board, color: chess.Color) -> tuple[int, int]:
    """All attacks by `color`, and the pawn-only subset."""
    by = 0
    by_pawn = 0
    for pt in NON_KING:
        for sq in board.pieces(pt, color):
            att = board.attacks_mask(sq)
            by |= att
            if pt == chess.PAWN:
                by_pawn |= att
    return by, by_pawn


def units(board: chess.Board, color: chess.Color) -> int:
    them = not color
    by_us, pawn_us = unions(board, color)
    by_them, _ = unions(board, them)
    by_us |= chess.BB_KING_ATTACKS[board.king(color)]
    by_them |= chess.BB_KING_ATTACKS[board.king(them)]

    enemy = board.occupied_co[them]
    enemy_non_pawn = enemy & ~board.pawns
    hanging = enemy_non_pawn & by_us & ~by_them
    pawn_threat = enemy & pawn_us

    u = W_HANGING * chess.popcount(hanging) + W_PAWN * chess.popcount(pawn_threat)
    return min(u, UNITS_MAX)


def reference(board: chess.Board) -> int:
    return units(board, chess.WHITE) - units(board, chess.BLACK)


def random_positions(n: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    out: list[str] = []
    seen: set[str] = set()
    while len(out) < n:
        b = chess.Board()
        for _ in range(rng.randint(6, 70)):
            moves = list(b.legal_moves)
            if not moves:
                break
            b.push(rng.choice(moves))
            if b.is_game_over():
                break
        if b.is_game_over() or b.is_check():
            continue
        fen = b.fen()
        if fen in seen:
            continue
        seen.add(fen)
        out.append(fen)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--params", required=True)
    ap.add_argument("--positions", type=int, default=600)
    ap.add_argument("--seed", type=int, default=20261112)
    ap.add_argument("--json")
    args = ap.parse_args()

    fens = random_positions(args.positions, args.seed)
    with tempfile.TemporaryDirectory() as td:
        epd = Path(td) / "pos.epd"
        out = Path(td) / "feat.csv"
        epd.write_text("\n".join(fens) + "\n")
        cmd = [args.engine, "evaldata", "--input", str(epd), "--output", str(out),
               "--params", args.params]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print("evaldata failed:", r.stdout[-2000:], r.stderr[-2000:])
            return 2
        lines = [l for l in out.read_text().splitlines() if not l.startswith("#")]

    header = lines[0].split(",")
    try:
        ic = header.index("mg_ThreatDetection")
    except ValueError:
        print("header lacks mg_ThreatDetection; full header:", ",".join(header))
        return 2

    checked = mismatch = nonzero = 0
    examples = []
    for fen, line in zip(fens, lines[1:]):
        row = line.split(",")
        want = reference(chess.Board(fen))
        got = int(row[ic])
        checked += 1
        if want:
            nonzero += 1
        if got != want:
            mismatch += 1
            if len(examples) < 5:
                examples.append({"fen": fen, "engine": got, "reference": want})

    print(f"threat reference check: {checked} positions, {mismatch} mismatches, "
          f"{nonzero} positions with a non-zero term")
    for e in examples:
        print("  MISMATCH", json.dumps(e))
    if args.json:
        Path(args.json).write_text(json.dumps({
            "positions": checked, "mismatches": mismatch,
            "nonzero_positions": nonzero, "seed": args.seed,
            "spec": {"w_hanging": W_HANGING, "w_pawn": W_PAWN, "cap": UNITS_MAX},
            "examples": examples,
            "verdict": "PASS" if mismatch == 0 else "FAIL",
        }, indent=2) + "\n")
    return 0 if mismatch == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
