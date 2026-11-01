#!/usr/bin/env python3
"""Build StockBear's regression suite of forced mates and simple endgames.

Every tactical position comes from a StockBear self-play game that ended in
checkmate, and every one is re-proved here by `scripts/chess_oracle.py`, an
independent mate search built on python-chess. The suite therefore contains
only moves that are provably correct, and it accepts *all* moves that force
mate in the same number of plies, so a passing run never depends on agreeing
with one arbitrary choice.

Endgame positions are constructed, not recorded: they are random legal
K+Q vs K and K+R vs K placements with the defender's king away from the edge.
Those are theoretical wins; the suite requires the engine to deliver mate
inside the fifty-move rule, and python-chess adjudicates the resulting game.

Usage:
  python3 scripts/make_tactics_suite.py --pgn selfplay.pgn \
      --positions benchmarks/tactics/mate_suite.epd \
      --endgames benchmarks/tactics/endgame_suite.epd \
      --manifest benchmarks/tactics/suite.manifest.json
"""
import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import chess
import chess.pgn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chess_oracle import MATE, acceptable_moves, forced_mate, mate_within, principal_variation  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pgn", required=True)
    parser.add_argument("--positions", required=True)
    parser.add_argument("--endgames", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--max-per-distance", type=int, default=20)
    parser.add_argument("--endgames-per-type", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20261101)
    return parser.parse_args()


def material_key(board):
    return tuple(len(board.pieces(piece, chess.WHITE)) for piece in
                 (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)) + \
           tuple(len(board.pieces(piece, chess.BLACK)) for piece in
                 (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN))


def collect_mates(pgn, max_per_distance):
    """Positions a fixed distance before a mate, re-proved by the oracle."""
    chosen = {3: [], 5: []}
    seen = set()
    games = 0
    with open(pgn, encoding="utf-8") as stream:
        while True:
            game = chess.pgn.read_game(stream)
            if game is None:
                break
            games += 1
            moves = list(game.mainline_moves())
            if not moves:
                continue
            board = game.board()
            for move in moves:
                board.push(move)
            if not board.is_checkmate():
                continue
            for distance in (3, 5):
                if len(moves) < distance + 8 or len(chosen[distance]) >= max_per_distance:
                    continue
                target = len(moves) - distance
                position = game.board()
                for move in moves[:target]:
                    position.push(move)
                if position.is_check() or position.is_game_over():
                    continue
                if not mate_within(position, distance):
                    continue
                key = (material_key(position), position.turn)
                if key in seen:
                    continue
                moves_uci = acceptable_moves(position, distance)
                moves_ok = [position.san(chess.Move.from_uci(uci)) for uci in moves_uci]
                if not moves_ok or moves[target].uci() not in moves_uci:
                    continue
                # The engine's own game move must be one of the accepted moves:
                # if the oracle disagrees with the game, the position is not
                # understood well enough to ship in a regression suite.
                seen.add(key)
                chosen[distance].append({
                    "board": position.copy(),
                    "bm": moves_ok,
                    "game": games - 1,
                    "ply": target,
                    "played": moves[target].uci(),
                    "pv": principal_variation(position, distance),
                })
    return chosen, games


def random_endgames(pieces, count, rng):
    """Random legal K+piece vs K placements, not already mate in one."""
    board_class = chess.Board
    found = []
    attempts = 0
    while len(found) < count and attempts < 200000:
        attempts += 1
        squares = rng.sample(range(64), 3)
        strong_king, extra, weak_king = squares
        board = board_class(None)
        board.clear()
        board.set_piece_at(strong_king, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(extra, chess.Piece(pieces, chess.WHITE))
        board.set_piece_at(weak_king, chess.Piece(chess.KING, chess.BLACK))
        board.turn = chess.WHITE
        if not board.is_valid():
            continue
        # Keep the defender off the edge: a cornered king is a mate-in-two
        # exercise, not a conversion test.
        file_index = chess.square_file(weak_king)
        rank_index = chess.square_rank(weak_king)
        if file_index in (0, 7) or rank_index in (0, 7):
            continue
        if mate_within(board, 3):
            continue
        found.append(board.fen())
    return found


def write_epd(path, entries, header):
    lines = []
    for line in header:
        lines.append("# " + line)
    for entry in entries:
        ops = []
        if entry.get("bm"):
            ops.append("bm " + " ".join(entry["bm"]) + ";")
        ops.append(f'id "{entry["id"]}";')
        for key, value in entry.get("comments", {}).items():
            ops.append(f'{key} "{value}";')
        lines.append(" ".join(entry["fen"].split()[:4] + ops))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    chosen, games = collect_mates(args.pgn, args.max_per_distance)
    rng = random.Random(args.seed)
    entries = []
    index = {3: 0, 5: 0}
    for distance in (3, 5):
        for case in chosen[distance]:
            index[distance] += 1
            entries.append({
                "fen": case["board"].fen(),
                "bm": case["bm"],
                "id": f"mate{index[distance]:02d}-{distance}ply",
                "comments": {"c0": f"self-play mate in {distance} plies",
                             "c1": f"game {case['game']} ply {case['ply']}",
                             "c2": "pv " + " ".join(case["pv"])},
            })
    write_epd(args.positions, entries,
              ["StockBear dev3 tactics suite (EPD).",
               "Source: StockBear self-play games (Apache-2.0, generated by this project).",
               "Certified by scripts/chess_oracle.py (independent mate proof on python-chess).",
               "bm lists every move that forces mate in the stated number of plies.",
               f"Games scanned: {games}."])

    endgames = []
    counter = 0
    for piece, label in ((chess.QUEEN, "KQK"), (chess.ROOK, "KRK")):
        for fen in random_endgames(piece, args.endgames_per_type, rng):
            counter += 1
            endgames.append({"fen": fen, "bm": [],
                             "id": f"{label.lower()}-{counter:02d}",
                             "comments": {"c0": "three-man endgame, theoretical win",
                                          "c1": "must mate inside 50 moves"}})
    write_epd(args.endgames, endgames,
              ["StockBear dev3 endgame conversion suite (EPD).",
               "Source: constructed random placements (original data, Apache-2.0).",
               "Every position is a theoretical win; the runner requires mate",
               "inside the fifty-move rule, adjudicated by python-chess."])

    pgn_bytes = Path(args.pgn).read_bytes()
    manifest = {
        "pgn": args.pgn,
        "pgn_sha256": hashlib.sha256(pgn_bytes).hexdigest(),
        "games_scanned": games,
        "tactics": len(entries),
        "endgames": len(endgames),
        # The keys name the files they hash, so a reader never has to guess which
        # suite a digest belongs to; the committed manifest uses the same ones.
        "mate_suite_sha256": hashlib.sha256(Path(args.positions).read_bytes()).hexdigest(),
        "endgame_suite_sha256": hashlib.sha256(Path(args.endgames).read_bytes()).hexdigest(),
        "oracle": "scripts/chess_oracle.py (own mate proof on python-chess " + chess.__version__ + ")",
        "seed": args.seed,
        "note": "A position is only included when the oracle proves a forced mate "
                "and the recorded game move is one of the accepted moves.",
    }
    Path(args.manifest).write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
