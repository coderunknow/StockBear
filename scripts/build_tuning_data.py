#!/usr/bin/env python3
"""Turn recorded games into a Texel-tuning dataset.

Input is a PGN file produced by `scripts/tournament.py` (StockBear playing
itself). Every position is labelled with the final result of its own game from
the point of view of the side to move, and the game id is kept so the tuner can
split training and holdout sets *by game* instead of by position. Splitting by
position would leak: two positions from one game share the same label and often
the same material, which makes a holdout set look much better than it is.

The dataset is original data: it was produced by StockBear playing StockBear
under the recorded conditions, so there is no third-party licence attached.

Usage:
  python3 scripts/build_tuning_data.py --pgn selfplay.pgn \
      --out positions.epd --meta positions.meta.json
"""
import argparse
import hashlib
import json
from pathlib import Path

import chess
import chess.pgn


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pgn", required=True)
    parser.add_argument("--out", required=True, help="output EPD-style position list (FEN per line)")
    parser.add_argument("--meta", required=True, help="output JSON with per-line result and game id")
    parser.add_argument("--min-ply", type=int, default=12,
                        help="skip the opening (default 12 plies)")
    parser.add_argument("--sample-every", type=int, default=2,
                        help="keep every Nth position (default 2)")
    parser.add_argument("--max-positions-per-game", type=int, default=60)
    parser.add_argument("--min-pieces", type=int, default=6,
                        help="skip positions with fewer than this many pieces")
    parser.add_argument("--max-abs-material", type=int, default=1500,
                        help="skip positions already decided by this much material")
    parser.add_argument("--seed", type=int, default=20261101)
    return parser.parse_args()


VALUE = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
         chess.ROOK: 500, chess.QUEEN: 975}


def material_balance(board):
    total = 0
    for piece_type, value in VALUE.items():
        total += value * (len(board.pieces(piece_type, chess.WHITE)) -
                          len(board.pieces(piece_type, chess.BLACK)))
    return total


def main():
    args = parse_args()
    positions, records, skipped = [], [], {"opening": 0, "material": 0, "pieces": 0,
                                           "in_check": 0, "cap_per_game": 0, "unfinished": 0}
    games = 0
    with open(args.pgn, encoding="utf-8") as stream:
        while True:
            game = chess.pgn.read_game(stream)
            if game is None:
                break
            games += 1
            result = game.headers.get("Result", "*")
            if result not in ("1-0", "0-1", "1/2-1/2"):
                skipped["unfinished"] += 1
                continue
            white_score = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}[result]
            board = game.board()
            kept_here = 0
            ply = 0
            for move in game.mainline_moves():
                board.push(move)
                ply += 1
                if ply < args.min_ply:
                    continue
                if board.is_check():
                    # A position in check is dominated by tactics the static
                    # evaluation never sees; including them would push the tuner
                    # to fit forced lines.
                    skipped["in_check"] += 1
                    continue
                if len(board.piece_map()) < args.min_pieces:
                    skipped["pieces"] += 1
                    continue
                if abs(material_balance(board)) > args.max_abs_material:
                    skipped["material"] += 1
                    continue
                if ply % args.sample_every:
                    continue
                if kept_here >= args.max_positions_per_game:
                    skipped["cap_per_game"] += 1
                    continue
                white_to_move = board.turn == chess.WHITE
                target = white_score if white_to_move else 1.0 - white_score
                positions.append(board.fen(en_passant="fen"))
                records.append({"game": games - 1, "ply": ply, "target": target})
                kept_here += 1
    if not positions:
        raise SystemExit("no positions collected from " + args.pgn)
    out = Path(args.out)
    out.write_text("\n".join(positions) + "\n", encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    meta = {
        "source": "StockBear self-play",
        "pgn": str(args.pgn),
        "pgn_sha256": hashlib.sha256(Path(args.pgn).read_bytes()).hexdigest(),
        "positions_sha256": digest,
        "games": games,
        "positions": len(positions),
        "parameters": {"min_ply": args.min_ply, "sample_every": args.sample_every,
                       "max_positions_per_game": args.max_positions_per_game,
                       "min_pieces": args.min_pieces,
                       "max_abs_material": args.max_abs_material, "seed": args.seed},
        "skipped": skipped,
        "records": records,
        "license": "original data generated by this project; Apache-2.0",
    }
    Path(args.meta).write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    print(f"games {games} positions {len(positions)} sha256 {digest}")
    print("skipped", skipped)
    games_used = len({r['game'] for r in records})
    print(f"games contributing positions: {games_used}")


if __name__ == "__main__":
    main()
