#!/usr/bin/env python3
"""Independent reference for exp-0055 passed-pawn promotion race.

Shares NO code with the engine. Geometry is rebuilt here from the written
specification and compared against the engine's `eval_breakdown` counts (via
`evaldata`) on freshly generated positions.

Specification (per side `us`, enemy `them`), using the SHIPPED passed-pawn rule:
  passed(s)  = no enemy pawn in the forward span on s's file or adjacent files,
               AND no friendly pawn strictly ahead on s's file
  advance    = rank(s) for White, 7 - rank(s) for Black
  stop       = s + 8 (White) / s - 8 (Black)
  ownD       = min(chebyshev(own king, stop), 7)
  enemyD     = min(chebyshev(enemy king, stop), 7)
  blocked    = any enemy piece strictly ahead of s on s's file
  units     += advance * (2*(7-ownD) - 2*(7-enemyD) - (6 if blocked else 0))
  units      = clamp(units, -64, +64)
  breakdown contribution, White's viewpoint:
      PassedPawnRace += units(White) - units(Black)

Usage: check_passed_pawn_race.py --engine build-rel/stockbear --params F
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import tempfile
from pathlib import Path

import chess

W_OWN = 2
W_ENEMY = 2
W_BLOCKED = 6
UNITS_MAX = 64


def forward_ranks(color: chess.Color, rank: int) -> int:
    """Ranks strictly ahead of `rank` for `color` (engine ForwardRanksBB)."""
    bb = 0
    rng = range(rank + 1, 8) if color == chess.WHITE else range(rank - 1, -1, -1)
    for r in rng:
        bb |= chess.BB_RANKS[r]
    return bb


def adjacent_files(file: int) -> int:
    bb = 0
    if file > 0:
        bb |= chess.BB_FILES[file - 1]
    if file < 7:
        bb |= chess.BB_FILES[file + 1]
    return bb


def passed_mask(color: chess.Color, sq: int) -> int:
    f, r = chess.square_file(sq), chess.square_rank(sq)
    return forward_ranks(color, r) & (chess.BB_FILES[f] | adjacent_files(f))


def chebyshev(a: int, b: int) -> int:
    return max(abs(chess.square_file(a) - chess.square_file(b)),
               abs(chess.square_rank(a) - chess.square_rank(b)))


def units(board: chess.Board, color: chess.Color) -> int:
    them = not color
    own_pawns = board.pieces(chess.PAWN, color)
    enemy_pawns = board.pieces(chess.PAWN, them)
    enemy_all = board.occupied_co[them]
    own_k = board.king(color)
    enemy_k = board.king(them)
    forward = 8 if color == chess.WHITE else -8

    total = 0
    for s in own_pawns:
        f, r = chess.square_file(s), chess.square_rank(s)
        if enemy_pawns & passed_mask(color, s):
            continue
        ahead_same_file = own_pawns & chess.BB_FILES[f] & forward_ranks(color, r)
        if ahead_same_file:
            continue
        advance = r if color == chess.WHITE else 7 - r
        stop = s + forward
        if not (0 <= stop < 64):
            continue
        own_d = min(chebyshev(own_k, stop), 7)
        enemy_d = min(chebyshev(enemy_k, stop), 7)
        blocked = bool(enemy_all & chess.BB_FILES[f] & forward_ranks(color, r))
        total += advance * (W_OWN * (7 - own_d)
                            - W_ENEMY * (7 - enemy_d)
                            - (W_BLOCKED if blocked else 0))
    return max(-UNITS_MAX, min(total, UNITS_MAX))


def reference(board: chess.Board) -> int:
    return units(board, chess.WHITE) - units(board, chess.BLACK)


def random_positions(n: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    out: list[str] = []
    seen: set[str] = set()
    while len(out) < n:
        b = chess.Board()
        for _ in range(rng.randint(10, 90)):
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
    ap.add_argument("--positions", type=int, default=800)
    ap.add_argument("--seed", type=int, default=20261115)
    ap.add_argument("--json")
    args = ap.parse_args()

    fens = random_positions(args.positions, args.seed)
    with tempfile.TemporaryDirectory() as td:
        epd = Path(td) / "pos.epd"
        out = Path(td) / "feat.csv"
        epd.write_text("\n".join(fens) + "\n")
        r = subprocess.run([args.engine, "evaldata", "--input", str(epd),
                            "--output", str(out), "--params", args.params],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print("evaldata failed:", r.stdout[-1500:], r.stderr[-1500:])
            return 2
        lines = [l for l in out.read_text().splitlines() if not l.startswith("#")]

    header = lines[0].split(",")
    try:
        ic = header.index("eg_PassedPawnRace")
    except ValueError:
        print("header lacks eg_PassedPawnRace; header:", ",".join(header))
        return 2

    checked = mismatch = nonzero = 0
    examples = []
    for fen, line in zip(fens, lines[1:]):
        want = reference(chess.Board(fen))
        got = int(line.split(",")[ic])
        checked += 1
        if want:
            nonzero += 1
        if got != want:
            mismatch += 1
            if len(examples) < 5:
                examples.append({"fen": fen, "engine": got, "reference": want})

    print(f"passed-pawn race reference check: {checked} positions, {mismatch} "
          f"mismatches, {nonzero} positions with a non-zero term")
    for e in examples:
        print("  MISMATCH", json.dumps(e))
    if args.json:
        Path(args.json).write_text(json.dumps({
            "positions": checked, "mismatches": mismatch,
            "nonzero_positions": nonzero, "seed": args.seed,
            "spec": {"w_own": W_OWN, "w_enemy": W_ENEMY,
                     "w_blocked": W_BLOCKED, "cap": UNITS_MAX},
            "examples": examples,
            "verdict": "PASS" if mismatch == 0 else "FAIL",
        }, indent=2) + "\n")
    return 0 if mismatch == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
