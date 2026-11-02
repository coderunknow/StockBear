#!/usr/bin/env python3
"""Feature extraction for StockBear's neural evaluation, mirrored from C++.

The engine computes these indices in ``src/evaluation/nnue.cpp``
(``feature_of``). The training pipeline must produce *exactly* the same numbers
or a network is trained on one feature space and evaluated in another, which is
a silent playing-strength bug rather than a crash. ``tests/integration/
test_nnue_features.py`` compares this module against ``stockbear nnue
--features`` on a corpus, and that comparison is part of CI.

Feature layout (see src/evaluation/nnue.hpp):

    kind      = 6 * colour + (pieceType - 1)        # 0..11, kings included
    relSquare = colour of the *square's* rank as seen from the perspective
    bucket    = king_bucket(king square of the perspective, king_buckets)
    index     = bucket * 768 + kind * 64 + relSquare

The "relative square" is ``square`` for the White perspective and
``square ^ 56`` for the Black perspective: a square is identified by how far it
is from the perspective's own back rank, so a mirrored position produces the
same features. The perspective is not the side to move; both perspectives are
always fed to the network, and the network's output is the score for the side
to move (see the mirror argument in docs/DEV4_TRAINING.md).
"""
from __future__ import annotations

import numpy as np

PIECE_KIND = {
    "P": 0, "N": 1, "B": 2, "R": 3, "Q": 4, "K": 5,
    "p": 6, "n": 7, "b": 8, "r": 9, "q": 10, "k": 11,
}
# Value stored per occupied square: kind + 1, so that 0 means "empty" and the
# board array can be a plain uint8.
WHITE_KING = PIECE_KIND["K"] + 1
BLACK_KING = PIECE_KIND["k"] + 1


def king_bucket(relative_king: int, buckets: int) -> int:
    """Must match ``nnue::king_bucket`` in src/evaluation/nnue.cpp."""
    if buckets <= 1:
        return 0
    file = relative_king & 7
    rank = relative_king >> 3
    if buckets == 4:
        return rank // 2
    if buckets == 16:
        return (rank // 2) * 4 + file // 2
    if buckets == 64:
        return relative_king
    return (rank * buckets) // 8


def parse_placement(placement: str) -> np.ndarray:
    """FEN piece placement -> uint8[64] of (kind + 1), 0 = empty, a1 = 0."""
    board = np.zeros(64, dtype=np.uint8)
    rank, file = 7, 0
    for ch in placement:
        if ch == "/":
            rank -= 1
            file = 0
        elif "1" <= ch <= "8":
            file += ord(ch) - ord("0")
        else:
            board[rank * 8 + file] = PIECE_KIND[ch] + 1
            file += 1
    return board


def fen_to_board(fen: str):
    """Returns (board[64] uint8, side_to_move) where side 0 = White."""
    fields = fen.split()
    board = parse_placement(fields[0])
    side = 0 if fields[1] == "w" else 1
    return board, side


def board_features(board: np.ndarray, king_buckets: int = 1):
    """Feature index arrays for both perspectives of one position.

    ``board`` is a uint8[64] of (kind + 1). Returns a list of two sorted int32
    arrays, one per perspective, matching ``stockbear nnue --features``.
    """
    occupied = np.nonzero(board)[0]
    kinds = board[occupied].astype(np.int32) - 1
    out = []
    for perspective in (0, 1):
        rel = occupied if perspective == 0 else (occupied ^ 56)
        bucket = 0
        if king_buckets > 1:
            king_squares = occupied[kinds == (5 if perspective == 0 else 11)]
            if king_squares.size != 1:
                raise ValueError("position must contain exactly one king per side")
            rel_king = int(king_squares[0]) if perspective == 0 else int(king_squares[0]) ^ 56
            bucket = king_bucket(rel_king, king_buckets)
        feat = bucket * 768 + kinds * 64 + rel
        out.append(np.sort(feat.astype(np.int32)))
    return out


def ordered_features(board: np.ndarray, side: int, king_buckets: int = 1):
    """Feature rows of one position in the order the network expects.

    The engine's input is ``[side to move, opponent]``: the first half is the
    perspective of the side whose turn it is. Feeding the same board with the
    other side to move therefore swaps the halves, which is what lets the network
    learn a score for the side to move (and what makes it antisymmetric once
    trained). Ordering by colour instead is a silent bug: the input would then
    not depend on whose turn it is, while the target does, and the best fit is a
    constant 0.5 -- a network that trains "successfully" and plays at the
    strength of a null evaluation.
    """
    white, black = board_features(board, king_buckets)
    return (white, black) if side == 0 else (black, white)


def batch_indices(boards: np.ndarray, sides: np.ndarray, king_buckets: int = 1):
    """Vectorised feature indices for a batch of positions.

    ``boards`` is uint8[B, 64] and ``sides`` uint8[B] (0 = White to move).
    Returns ``(flat, offsets)`` ready for ``torch.nn.EmbeddingBag(mode="sum")``:
    rows ``2*b`` and ``2*b+1`` hold the side-to-move and the opponent perspective
    of position ``b``, so the resulting ``[2B, L1]`` tensor reshapes to
    ``[2B*L1]``-per-row layout ``[B, 2*L1]`` expected by the SIMD kernel.
    """
    mask = boards > 0
    counts = mask.sum(axis=1).astype(np.int64)
    total = int(counts.sum())
    offsets = np.zeros(boards.shape[0] + 1, dtype=np.int64)
    np.cumsum(counts, out=offsets[1:])

    positions = np.repeat(np.arange(boards.shape[0], dtype=np.int64), counts)
    squares = np.nonzero(mask)[1].astype(np.int64)
    kinds = boards[positions, squares].astype(np.int64) - 1

    base0 = kinds * 64 + squares          # White's perspective
    base1 = kinds * 64 + (squares ^ 56)   # Black's perspective
    if king_buckets > 1:
        raise NotImplementedError("king-bucketed batches are not used by the shipped net")
    white_to_move = sides[positions] == 0
    first = np.where(white_to_move, base0, base1)
    second = np.where(white_to_move, base1, base0)
    flat = np.empty(2 * total, dtype=np.int64)
    starts = offsets[positions]
    index = np.arange(total, dtype=np.int64)
    flat[index + starts] = first
    flat[index + starts + counts[positions]] = second

    doubled = np.repeat(counts, 2)
    bag_offsets = np.zeros(2 * boards.shape[0] + 1, dtype=np.int64)
    np.cumsum(doubled, out=bag_offsets[1:])
    return flat, bag_offsets


def read_selfplay(path: str, limit: int | None = None):
    """Reads a ``<result> <game> <fen>`` corpus file.

    Returns ``(boards uint8[N,64], side uint8[N], result float32[N],
    game int32[N])`` with ``result`` from the point of view of the side to move.
    """
    boards, sides, results, games = [], [], [], []
    with open(path, "r", encoding="ascii", errors="strict") as handle:
        for line in handle:
            if not line or line[0] == "#":
                continue
            result, game, fen = line.rstrip("\n").split(" ", 2)
            board, side = fen_to_board(fen)
            boards.append(board)
            sides.append(side)
            results.append(float(result))
            games.append(int(game))
            if limit is not None and len(boards) >= limit:
                break
    return (
        np.stack(boards) if boards else np.zeros((0, 64), dtype=np.uint8),
        np.array(sides, dtype=np.uint8),
        np.array(results, dtype=np.float32),
        np.array(games, dtype=np.int32),
    )


if __name__ == "__main__":
    import sys

    for argument in sys.argv[1:]:
        board, side = fen_to_board(argument)
        features = board_features(board, 1)
        print(side, "|", " ".join(str(v) for v in features[0]))
        print(side, "|", " ".join(str(v) for v in features[1]))
