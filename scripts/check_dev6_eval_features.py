#!/usr/bin/env python3
"""Independent reference check for the dev6 extended evaluation features.

The engine ships six extended pawn/coordination features (RookOn7th,
KnightOutpost, BackwardPawn, PawnChain, ConnectedPassed, RookBehindPassed)
computed in a single C++ helper shared by features() and accumulate_breakdown().
This script re-implements the SAME geometric predicates from scratch using
python-chess bitboards (sharing NO code with the engine), computes the six raw
counts for a fixed reproducible corpus of legal positions, and compares them
against the engine's own `evaldata` breakdown output (mg_/eg_ columns).

The comparison is a genuine independent oracle: a bug in the engine's masks,
colour handling, or forward/backward ranks will show up as a mismatch.

Usage:
  python3 scripts/check_dev6_eval_features.py \
      --engine build-local/stockbear \
      --params research-data/params_dev6_a.txt \
      --corpus benchmarks/positions/dev6_eval_features.epd \
      --report benchmarks/dev6-baseline/eval_features_reference.json \
      [--regenerate --count 600 --seed 2026110401]
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile

import chess

NAMES = ["RookOn7th", "KnightOutpost", "BackwardPawn",
         "PawnChain", "ConnectedPassed", "RookBehindPassed"]

# --- Independent bitboard helpers (mirror of src/chess/bitboard.cpp init) ---
BB_FILES = chess.BB_FILES
BB_RANKS = chess.BB_RANKS
BB_SQ = chess.BB_SQUARES


def adjacent_files(f):
    b = 0
    if f > 0:
        b |= BB_FILES[f - 1]
    if f < 7:
        b |= BB_FILES[f + 1]
    return b


def forward_ranks(us, r):
    # ranks strictly ahead of r from `us`'s point of view
    b = 0
    if us == chess.WHITE:
        for rr in range(r + 1, 8):
            b |= BB_RANKS[rr]
    else:
        for rr in range(0, r):
            b |= BB_RANKS[rr]
    return b


def passed_pawn_mask(us, sq):
    f, r = chess.square_file(sq), chess.square_rank(sq)
    return forward_ranks(us, r) & (BB_FILES[f] | adjacent_files(f))


def popcount(b):
    return bin(b).count("1")


def pawn_attacks(color, sq):
    # squares attacked by a `color` pawn standing on sq
    return chess.BB_PAWN_ATTACKS[color][sq]


def reference_counts(fen):
    board = chess.Board(fen)
    out = {c: {n: 0 for n in NAMES} for c in (chess.WHITE, chess.BLACK)}
    for us in (chess.WHITE, chess.BLACK):
        them = not us
        pawns = board.pawns & board.occupied_co[us]
        enemy_pawns = board.pawns & board.occupied_co[them]
        rooks = board.rooks & board.occupied_co[us]
        knights = board.knights & board.occupied_co[us]

        # Passed pawns: exactly the shipped rule (leading pawn of a file only).
        passed = 0
        for s in chess.scan_forward(pawns):
            f, r = chess.square_file(s), chess.square_rank(s)
            if not (enemy_pawns & passed_pawn_mask(us, s)) and \
               not (pawns & BB_FILES[f] & forward_ranks(us, r)):
                passed |= BB_SQ[s]

        for s in chess.scan_forward(pawns):
            f, r = chess.square_file(s), chess.square_rank(s)
            # PawnChain: a friendly pawn on a defending square.
            if pawns & pawn_attacks(them, s):
                out[us]["PawnChain"] += 1
            # ConnectedPassed: passer with a passer on an adjacent file.
            if (passed & BB_SQ[s]) and (passed & adjacent_files(f)):
                out[us]["ConnectedPassed"] += 1
            # BackwardPawn.
            stop = s + (8 if us == chess.WHITE else -8)
            if 0 <= stop < 64:
                not_passed = (enemy_pawns & passed_pawn_mask(us, s)) != 0
                enemy_hits_stop = (enemy_pawns & pawn_attacks(us, stop)) != 0
                friendly_defends = (pawns & pawn_attacks(them, stop)) != 0
                behind_neighbour = (pawns & adjacent_files(f) & forward_ranks(us, r)) != 0
                if not_passed and enemy_hits_stop and not friendly_defends and behind_neighbour:
                    out[us]["BackwardPawn"] += 1

        # RookBehindPassed.
        for s in chess.scan_forward(passed):
            f, r = chess.square_file(s), chess.square_rank(s)
            out[us]["RookBehindPassed"] += popcount(
                rooks & BB_FILES[f] & forward_ranks(them, r))

        # KnightOutpost.
        for s in chess.scan_forward(knights):
            r = chess.square_rank(s)
            rel = r if us == chess.WHITE else 7 - r
            if 3 <= rel <= 5 and (pawns & pawn_attacks(them, s)) and \
               not (enemy_pawns & pawn_attacks(us, s)):
                out[us]["KnightOutpost"] += 1

        # RookOn7th.
        for s in chess.scan_forward(rooks):
            r = chess.square_rank(s)
            if r == (6 if us == chess.WHITE else 1):
                out[us]["RookOn7th"] += 1

    # eval_breakdown accumulates from White's point of view: White +1, Black -1.
    return {n: out[chess.WHITE][n] - out[chess.BLACK][n] for n in NAMES}


CRAFTED = [
    # NEGATIVE control: white rook on a2 (rank index 1) is NOT on the 7th
    # rank for White (index 6) -> RookOn7th must be 0.
    "7k/8/8/8/8/8/R7/7K w - - 0 1",
    # white rook on a7 (rank index 6) -> RookOn7th +1.
    "7k/R7/8/8/8/8/8/7K b - - 0 1",
    # black rook on a2 (rank index 1 = Black's 7th) -> RookOn7th -1.
    "7k/8/8/8/8/8/r7/7K b - - 0 1",
    # white knight outpost on d5 supported by e4, no enemy pawn can hit it
    "7k/8/8/3N4/4P3/8/8/7K w - - 0 1",
    # pawn chain: e4 defended by d3 (also two connected passers here)
    "7k/8/8/8/4P3/3P4/8/7K w - - 0 1",
    # connected white passed pawns e5,f5 (no black pawns ahead)
    "7k/8/8/4PP2/8/8/8/7K w - - 0 1",
    # rook behind passed pawn: white a2 pawn passed, white rook a1 behind it
    "7k/8/8/8/8/8/P7/R6K w - - 0 1",
    # two white connected passers (c2,b4) with a black a2 pawn
    "7k/8/8/8/1P6/8/p1P5/7K w - - 0 1",
    # mixed middlegame: exercises BackwardPawn and PawnChain
    "r3k2r/ppp2ppp/2n5/3pp3/1b2P3/2NP1N2/PPP2PPP/R3KB1R w KQkq - 0 1",
]


def generate_corpus(path, count, seed):
    import random
    rng = random.Random(seed)
    fens = list(CRAFTED)
    games = 0
    while len(fens) < count:
        games += 1
        board = chess.Board()
        plies = rng.randint(4, 120)
        for ply in range(plies):
            if board.is_game_over():
                break
            moves = list(board.legal_moves)
            if not moves:
                break
            board.push(rng.choice(moves))
            # Sample positions across the game, favouring pawn-rich phases.
            if ply % 3 == 0 or rng.random() < 0.15:
                fens.append(board.fen())
                if len(fens) >= count:
                    break
    with open(path, "w") as f:
        for fen in fens[:count]:
            f.write(fen + "\n")
    return fens[:count]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="build-local/stockbear")
    ap.add_argument("--params", default="research-data/params_dev6_a.txt")
    ap.add_argument("--corpus", default="benchmarks/positions/dev6_eval_features.epd")
    ap.add_argument("--report", default="benchmarks/dev6-baseline/eval_features_reference.json")
    ap.add_argument("--regenerate", action="store_true")
    ap.add_argument("--count", type=int, default=600)
    ap.add_argument("--seed", type=int, default=2026110401)
    args = ap.parse_args()

    if args.regenerate or not os.path.exists(args.corpus):
        os.makedirs(os.path.dirname(args.corpus), exist_ok=True)
        generate_corpus(args.corpus, args.count, args.seed)
        print(f"generated {args.count} positions -> {args.corpus}")
    with open(args.corpus) as f:
        fens = [ln.strip() for ln in f if ln.strip()]

    with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as tmp:
        csv_path = tmp.name
    try:
        subprocess.run([args.engine, "evaldata", "--input", args.corpus,
                        "--output", csv_path, "--params", args.params],
                       check=True, capture_output=True, text=True)
        with open(csv_path) as f:
            data_lines = [ln for ln in f if not ln.startswith("#")]
        rows = list(csv.DictReader(data_lines))
    finally:
        os.unlink(csv_path)

    assert len(rows) == len(fens), f"row count {len(rows)} != {len(fens)}"
    mismatches = []
    checked = 0
    nonzero = {n: 0 for n in NAMES}
    for i, (fen, row) in enumerate(zip(fens, rows)):
        exp = reference_counts(fen)
        for n in NAMES:
            for phase in ("mg", "eg"):
                got = int(row[f"{phase}_{n}"])
                if got != exp[n]:
                    mismatches.append({"line": i + 1, "fen": fen, "feature": n,
                                       "phase": phase, "engine": got, "reference": exp[n]})
            checked += 1
        for n in NAMES:
            if exp[n] != 0:
                nonzero[n] += 1

    result = {
        "engine": args.engine, "params": args.params, "corpus": args.corpus,
        "corpus_sha256": subprocess.run(["sha256sum", args.corpus], capture_output=True,
                                        text=True).stdout.split()[0],
        "positions": len(fens), "feature_checks": checked * len(NAMES) * 2,
        "positions_with_nonzero_count": nonzero,
        "mismatches": len(mismatches), "mismatch_examples": mismatches[:20],
        "verdict": "PASS" if not mismatches else "FAIL",
    }
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({k: result[k] for k in ("positions", "feature_checks",
          "positions_with_nonzero_count", "mismatches", "verdict")}, indent=2))
    print("report ->", args.report)
    return 0 if not mismatches else 1


if __name__ == "__main__":
    sys.exit(main())
