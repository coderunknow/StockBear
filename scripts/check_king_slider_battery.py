#!/usr/bin/env python3
"""Independent reference for the king-facing slider battery candidate.

Shares NO engine code. Geometry is rebuilt from the written specification and
compared against `evaldata` breakdown counts on freshly generated positions.

Specification (per side `us`, enemy `them`):
  For each enemy Bishop/Rook/Queen on square s, with our king k:
    orthogonal = same file or same rank
    diagonal   = abs(file diff) == abs(rank diff) != 0
    Rook counts only orthogonal; Bishop only diagonal; Queen either.
    blockers = popcount(occupancy & between(s, k))
    if blockers == 1: units += 3 if diagonal else 4
  units = min(units, 16)
  White-positive breakdown count = units(Black) - units(White)
  (enemy batteries hurt `us`, so the count enters with the opposite sign).
"""
from __future__ import annotations
import argparse, chess, json, random, subprocess, tempfile
from pathlib import Path

W_ORTH = 4
W_DIAG = 3
CAP = 16

def aligned(pt, s, k):
    df = abs(chess.square_file(s) - chess.square_file(k))
    dr = abs(chess.square_rank(s) - chess.square_rank(k))
    orth = df == 0 or dr == 0
    diag = df == dr and df != 0
    if pt == chess.ROOK: return orth, False
    if pt == chess.BISHOP: return False, diag
    if pt == chess.QUEEN: return orth, diag
    return False, False

def units(board, color):
    them = not color
    k = board.king(color)
    occ = board.occupied
    total = 0
    for pt in (chess.BISHOP, chess.ROOK, chess.QUEEN):
        for s in board.pieces(pt, them):
            orth, diag = aligned(pt, s, k)
            if not orth and not diag: continue
            if (occ & chess.between(s, k)).bit_count() != 1: continue
            total += W_DIAG if diag else W_ORTH
    return min(total, CAP)

def reference(board):
    return units(board, chess.BLACK) - units(board, chess.WHITE)

def random_positions(n, seed):
    rng = random.Random(seed)
    out, seen = [], set()
    while len(out) < n:
        b = chess.Board()
        for _ in range(rng.randint(10, 90)):
            moves = list(b.legal_moves)
            if not moves: break
            b.push(rng.choice(moves))
            if b.is_game_over(): break
        if b.is_game_over() or b.is_check(): continue
        fen = b.fen()
        if fen in seen: continue
        seen.add(fen); out.append(fen)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--positions", type=int, default=800)
    ap.add_argument("--seed", type=int, default=20261117)
    ap.add_argument("--json")
    a = ap.parse_args()
    fens = random_positions(a.positions, a.seed)
    with tempfile.TemporaryDirectory() as td:
        epd = Path(td)/"pos.epd"; out = Path(td)/"feat.csv"; params = Path(td)/"battery.txt"
        epd.write_text("\n".join(fens)+"\n")
        params.write_text("KingSliderBattery 1 1\n")
        r = subprocess.run([a.engine, "evaldata", "--input", str(epd), "--output", str(out),
                            "--params", str(params)], capture_output=True, text=True)
        if r.returncode != 0:
            print("evaldata failed:", r.stdout[-1500:], r.stderr[-1500:]); return 2
        lines = [l for l in out.read_text().splitlines() if not l.startswith("#")]
    header = lines[0].split(",")
    try: ic = header.index("mg_KingSliderBattery")
    except ValueError:
        print("header lacks mg_KingSliderBattery"); return 2
    checked = mismatch = nonzero = 0; examples = []
    for fen, line in zip(fens, lines[1:]):
        want = reference(chess.Board(fen)); got = int(line.split(",")[ic])
        checked += 1
        if want: nonzero += 1
        if got != want:
            mismatch += 1
            if len(examples) < 5: examples.append({"fen": fen, "engine": got, "reference": want})
    print(f"king-slider-battery reference check: {checked} positions, {mismatch} mismatches, {nonzero} non-zero")
    for e in examples: print("  MISMATCH", json.dumps(e))
    if a.json:
        Path(a.json).write_text(json.dumps({"positions": checked, "mismatches": mismatch,
            "nonzero_positions": nonzero, "seed": a.seed,
            "spec": {"w_orth": W_ORTH, "w_diag": W_DIAG, "cap": CAP},
            "examples": examples, "verdict": "PASS" if mismatch == 0 else "FAIL"}, indent=2)+"\n")
    return 0 if mismatch == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
