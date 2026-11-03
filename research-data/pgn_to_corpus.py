#!/usr/bin/env python3
"""Convert a tournament.py selfplay PGN into a `<result> <game> <fen>` corpus.

Result is from the point of view of the side to move: 1 / 0.5 / 0.
Mirrors the format of research-data/corpusA.txt (stockbear selfplay output).
"""
import argparse
import chess
import chess.pgn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pgn", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-plies", type=int, default=8,
                    help="skip the first N plies of each game (opening book-ish noise)")
    args = ap.parse_args()

    n = 0
    with open(args.pgn) as f, open(args.out, "w") as out:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            res = game.headers.get("Result", "*")
            if res == "1-0":
                white = 1.0
            elif res == "0-1":
                white = 0.0
            elif res == "1/2-1/2":
                white = 0.5
            else:
                continue  # unfinished/unadjudicated games carry no outcome label
            board = game.board()
            for i, move in enumerate(game.mainline_moves()):
                board.push(move)
                if i + 1 < args.min_plies:
                    continue
                r = white if board.turn == chess.WHITE else 1.0 - white
                r = int(r) if r in (0.0, 1.0) else 0.5
                out.write(f"{r} {n} {board.fen()}\n")
            n += 1
    print(f"games={n} lines written to {args.out}")


if __name__ == "__main__":
    main()
