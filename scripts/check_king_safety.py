#!/usr/bin/env python3
"""Independent reference for exp-0052 nonlinear king safety.

Shares NO code with the engine: python-chess generates every attack set, and the
attack-unit weights / saturating curve are re-implemented here from the written
specification. Compares the engine's `eval_breakdown` counts (via `evaldata`)
against this reference on freshly generated positions.

Specification being verified (per side `us`, enemy `them`):
  zone   = king-adjacent squares | king square | one rank toward the enemy
  units  = sum over enemy N/B/R/Q of W[pt] * |attacks(pt) ∩ zone|,
           computed ONLY if `them` has a queen (queen gate)
  curve  = min(units, 32)^2 // 16
  breakdown contribution, White's viewpoint:
      KingSafetyQuadratic += black_curve - white_curve
  (the row enters with a negative sign because danger to us hurts us)

Usage: check_king_safety.py --engine build-rel/stockbear --params F [--positions N]
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import chess

WEIGHT = {chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 3, chess.QUEEN: 5}
INDEX_MAX = 32


def king_zone(board: chess.Board, color: chess.Color) -> chess.Bitboard:
    """King square + adjacent + one rank toward the enemy (engine KingZoneBB)."""
    sq = board.king(color)
    z = chess.BB_KING_ATTACKS[sq] | chess.BB_SQUARES[sq]
    # The engine ORs the king-attack bitboard shifted one rank toward the enemy
    # (bitboard.cpp: ki | square_bb(sq) | (ki << 8) for White, >> 8 for Black).
    ki = chess.BB_KING_ATTACKS[sq]
    shifted = ((ki << 8) & chess.BB_ALL) if color == chess.WHITE else (ki >> 8)
    return ki | chess.BB_SQUARES[sq] | shifted


def counts(board: chess.Board, color: chess.Color) -> int:
    them = not color
    zone = king_zone(board, color)
    units = 0
    if board.pieces(chess.QUEEN, them):
        for pt, w in WEIGHT.items():
            for sq in board.pieces(pt, them):
                att = board.attacks_mask(sq)
                units += w * chess.popcount(att & zone)
    u = max(0, min(units, INDEX_MAX))
    curve = (u * u) // 16
    return curve


def reference(board: chess.Board) -> int:
    return counts(board, chess.BLACK) - counts(board, chess.WHITE)


def random_positions(n: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    out = []
    seen = set()
    while len(out) < n:
        b = chess.Board()
        for _ in range(rng.randint(6, 60)):
            moves = list(b.legal_moves)
            if not moves:
                break
            b.push(rng.choice(moves))
            if b.is_game_over():
                break
        if b.is_game_over():
            continue
        if b.is_check():
            continue  # breakdown is compared on non-check positions
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
    ap.add_argument("--positions", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20261107)
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
        iq = header.index("mg_KingSafetyQuadratic")
    except ValueError:
        print("header lacks the exp-0052 columns; saw:", header[:8], "...")
        print("full header:", ",".join(header))
        return 2
    checked = mismatch = 0
    examples = []
    nonzero = 0
    for fen, line in zip(fens, lines[1:]):
        row = line.split(",")
        b = chess.Board(fen)
        rq = reference(b)
        gq = int(row[iq])
        checked += 1
        if rq:
            nonzero += 1
        if gq != rq:
            mismatch += 1
            if len(examples) < 5:
                examples.append({"fen": fen, "engine": gq, "reference": rq})
    print(f"king-safety reference check: {checked} positions, {mismatch} mismatches, "
          f"{nonzero} positions with a non-zero term")
    for e in examples:
        print("  MISMATCH", json.dumps(e))
    if args.json:
        Path(args.json).write_text(json.dumps({
            "positions": checked, "mismatches": mismatch,
            "nonzero_positions": nonzero, "seed": args.seed,
            "examples": examples}, indent=2) + "\n")
    # A reference that only ever sees zeros proves nothing.
    if nonzero == 0:
        print("FAIL: the term never fired; the corpus does not exercise it")
        return 1
    return 1 if mismatch else 0


if __name__ == "__main__":
    sys.exit(main())
