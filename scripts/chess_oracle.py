#!/usr/bin/env python3
"""Independent, non-StockBear chess oracle used to certify test positions.

Why this exists: a tactics or endgame suite is worthless if the engine under
test decides which answers count as correct. Every position in
`benchmarks/tactics/` is therefore certified here, by a search written from
scratch on top of python-chess (GPL-3.0) and sharing no code with StockBear's
engine. The oracle only proves forced mates; it never claims anything weaker,
so a disagreement can always be examined by hand on the printed variation.

Scores use python-chess's centipawn convention with a large mate offset, so a
positive score of MATE - k means "the side to move mates in k plies".
"""
import chess

MATE = 100000


def _child_score(board, move, max_plies, memo):
    """Mate score for the side to move after `move`, with the distance counted.

    Returns None when nothing is proven inside the budget, 0 for a drawn
    continuation, and a mate score whose distance is measured from the position
    *before* `move`, so a mate in three plies and a mate in one ply can never
    compare equal.
    """
    board.push(move)
    try:
        if board.is_checkmate():
            return MATE - 1
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
        if max_plies <= 1:
            return None
        child = forced_mate(board, max_plies - 1, memo)
        if child is None:
            return None
        if child == 0:
            return 0
        # Same mate, one ply further away, seen from the other side. The sign
        # decides which way the distance moves: a mate for us gets one ply
        # longer (MATE - k becomes MATE - (k + 1)), and a mate for the opponent
        # gets one ply further away too (-MATE + k becomes -MATE + (k + 1)).
        return (-child - 1) if child < 0 else (1 - child)
    finally:
        board.pop()


def forced_mate(board, max_plies, memo=None):
    """Best mate score for the side to move within `max_plies`, or None.

    Returns MATE - k when the side to move can force mate in k plies against
    best defence, -MATE + k when it is the side to move that gets mated, 0 for
    a draw that is already on the board, and None when nothing is proven inside
    the ply budget (which is *not* evidence that the position is drawn).

    A negative result is only reported when every legal move has been scored:
    an unexplored move might be a draw or a win, so with any unknown branch an
    "I am getting mated" claim would be unsound. A *positive* result is a
    witness — one move that provably mates — and stands on its own.
    """
    if memo is None:
        memo = {}
    key = (board._transposition_key(), max_plies)
    if key in memo:
        return memo[key]
    best = None
    unknown = False
    for move in board.legal_moves:
        value = _child_score(board, move, max_plies, memo)
        if value is None:
            unknown = True
            continue
        if best is None or value > best:
            best = value
    if best is not None and best <= 0 and unknown:
        best = None
    memo[key] = best
    return best


def mate_within(board, plies):
    """True when the side to move can force mate in at most `plies` plies.

    A boolean proof search instead of a scored one: it stops at the first
    mating line, which makes scanning hundreds of game positions for tactics
    practical, while still proving that *every* defensive reply loses.
    """
    if plies <= 0:
        return False
    for move in board.legal_moves:
        board.push(move)
        if board.is_checkmate():
            board.pop()
            return True
        if plies >= 3 and not board.is_stalemate() and _all_replies_lose(board, plies - 1):
            board.pop()
            return True
        board.pop()
    return False


def _all_replies_lose(board, plies):
    """True when, with the defender to move, every reply still loses by `plies`."""
    if plies <= 0:
        return False
    for move in board.legal_moves:
        board.push(move)
        if board.is_checkmate():
            board.pop()
            return False
        if board.is_stalemate() or not mate_within(board, plies - 1):
            board.pop()
            return False
        board.pop()
    return True


def mate_distance(board, max_plies):
    """Plies to forced mate for the side to move, or None."""
    value = forced_mate(board, max_plies)
    if value is None or value <= 0:
        return None
    return MATE - value


def acceptable_moves(board, max_plies):
    """UCI moves that keep the forced mate inside `max_plies` plies.

    A position usually has several equally winning moves; the suite must accept
    all of them, otherwise it measures agreement with one arbitrary choice.
    """
    best = forced_mate(board, max_plies)
    if best is None or best <= 0:
        return []
    chosen = []
    memo = {}
    for move in board.legal_moves:
        score = _child_score(board, move, max_plies, memo)
        if score is not None and score == best:
            chosen.append(move.uci())
    return chosen


def principal_variation(board, max_plies):
    """One line proving the mate, for human inspection of any disagreement."""
    line = []
    b = board.copy()
    depth = max_plies
    while depth > 0 and not b.is_checkmate() and not b.is_stalemate():
        best = forced_mate(b, depth)
        if best is None or best <= 0:
            break
        chosen = None
        for move in b.legal_moves:
            if _child_score(b, move, depth, {}) == best:
                chosen = move
                break
        if chosen is None:
            break
        line.append(b.san(chosen))
        b.push(chosen)
        depth -= 1
    return line


if __name__ == "__main__":
    import sys
    fen = sys.argv[1]
    plies = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    board = chess.Board(fen)
    print("mate_plies", mate_distance(board, plies))
    print("acceptable", acceptable_moves(board, plies))
    print("pv", principal_variation(board, plies))
