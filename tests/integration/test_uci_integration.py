#!/usr/bin/env python3
"""Black-box UCI protocol tests, stdlib only, portable to Windows and Linux."""
import os
import queue
import re
import subprocess
import sys
import threading
import time

EXE = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read_version():
    with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as handle:
        return handle.read().strip()
MOVE = re.compile(r"^(?:[a-h][1-8][a-h][1-8][qrbn]?|0000)$")

class Engine:
    def __init__(self):
        self.p = subprocess.Popen([EXE], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, bufsize=1)
        self.queue = queue.Queue()
        self.lines = []
        self.err = []
        threading.Thread(target=self._read, args=(self.p.stdout, self.queue), daemon=True).start()
        threading.Thread(target=self._read_err, daemon=True).start()

    @staticmethod
    def _read(pipe, q):
        for line in iter(pipe.readline, ""):
            q.put(line.rstrip("\r\n"))
        q.put(None)

    def _read_err(self):
        for line in iter(self.p.stderr.readline, ""):
            self.err.append(line)

    def send(self, line):
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()

    def until(self, predicate, timeout=5):
        end = time.monotonic() + timeout
        batch = []
        while time.monotonic() < end:
            try:
                line = self.queue.get(timeout=max(0.001, end-time.monotonic()))
            except queue.Empty:
                break
            if line is None:
                raise AssertionError(f"engine exited early; stderr={self.err}, output={self.lines}")
            assert line.startswith(("id ", "uciok", "readyok", "option ", "info ", "bestmove ")), line
            self.lines.append(line)
            batch.append(line)
            if predicate(line):
                return line, batch
        raise AssertionError(f"timeout waiting for UCI response; stderr={self.err}, output={self.lines[-30:]}")

    def best(self, timeout=5):
        line, batch = self.until(lambda s: s.startswith("bestmove "), timeout)
        fields = line.split()
        assert len(fields) == 2 and MOVE.fullmatch(fields[1]), line
        return fields[1], batch

    def ready(self):
        self.send("isready")
        self.until(lambda x: x == "readyok")

    def close(self):
        if self.p.poll() is None:
            try:
                self.send("quit")
                self.p.wait(timeout=4)
            except (OSError, subprocess.TimeoutExpired):
                self.p.kill()
                self.p.wait(timeout=4)
                raise AssertionError("quit did not stop engine promptly")
        assert self.p.returncode == 0, (self.p.returncode, self.err)


def legal_by_divide(fen):
    result = subprocess.run([EXE, "perft", "1", "--fen", fen, "--divide"],
                            text=True, capture_output=True, timeout=5, check=True)
    return {line.split(":", 1)[0] for line in result.stdout.splitlines() if ": " in line}


def main():
    e = Engine()
    try:
        version = read_version()
        e.send("uci")
        _, hello = e.until(lambda x: x == "uciok")
        assert any(x.startswith(f"id name StockBear {version}") for x in hello), hello
        assert any(x.startswith("option name Hash type spin") for x in hello), hello
        assert not any("Threads" in x for x in hello), hello
        e.ready()
        e.send("setoption name Hash value 1")
        e.ready()
        e.send("setoption name Hash value nope")
        e.until(lambda x: x.startswith("info string setoption:"))
        e.send("go depth bad")
        e.until(lambda x: x.startswith("info string go:"))
        e.ready()

        fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2"
        legal = legal_by_divide(fen)
        e.send("position startpos moves e2e4 e7e5")
        e.send("position startpos moves e2e5")  # must leave prior position intact
        e.until(lambda x: x.startswith("info string position:"))
        e.send("go depth 3")
        best, lines = e.best()
        assert best in legal, (best, legal)
        assert any(re.match(r"^info depth 3\b.*\bscore (cp|mate) -?\d+\b.*\bnodes \d+\b.*\bpv ", x)
                   for x in lines), lines
        # Every info line must be complete enough for a GUI: depth, score, node
        # count, hash fullness and a principal variation.
        assert any(re.match(r"^info depth \d+ seldepth \d+ score (cp|mate) -?\d+ nodes \d+ "
                            r"nps \d+ hashfull \d+ time \d+ pv [a-h][1-8][a-h][1-8]", x)
                   for x in lines), lines

        e.send("position startpos")
        start_legal = legal_by_divide("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        e.send("go nodes 100")
        best, lines = e.best()
        assert best in start_legal, best
        for line in lines:
            match = re.search(r"\bnodes (\d+)", line)
            if match: assert int(match.group(1)) <= 100, line
        e.send("go movetime 50")
        before = time.monotonic(); best, _ = e.best(3)
        assert best in start_legal and time.monotonic() - before < 2, best
        e.send("go wtime 1000 btime 1000 winc 10 binc 10 movestogo 20")
        best, _ = e.best(3)
        assert best in start_legal, best
        # Some GUIs send an already-expired negative remaining time.
        e.send("go wtime -7 btime 60000")
        best, _ = e.best(3)
        assert best in start_legal, best
        # Unknown tokens ("ponder", GUI extensions) must be ignored without
        # abandoning the search, as the UCI specification asks. A searchmoves
        # list that mixes one legal move with an illegal one keeps the legal
        # move and reports the other, instead of failing the whole search.
        e.send("go depth 2 ponder searchmoves e2e4 e7e5")
        best, lines = e.best(3)
        assert best == "e2e4", best
        assert any(x.startswith("info string go: searchmoves ignores illegal move e7e5")
                   for x in lines), lines
        e.send("go winc -1")
        _, invalid_clock = e.until(lambda x: x.startswith("info string go:"))
        assert not any(x.startswith("bestmove ") for x in invalid_clock), invalid_clock
        e.send("go wtime -not-a-number")
        _, malformed_clock = e.until(lambda x: x.startswith("info string go:"))
        assert not any(x.startswith("bestmove ") for x in malformed_clock), malformed_clock

        # Black's clock, not White's, must govern a black-to-move search.
        black_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        black_legal = legal_by_divide(black_fen)
        e.send("position startpos moves e2e4")
        before = time.monotonic()
        e.send("go wtime 60000 btime 100 winc 10 binc 20 movestogo 20")
        best, _ = e.best(3)
        assert best in black_legal and time.monotonic() - before < 1, best
        e.send("go wtime 60000 btime -7")
        best, _ = e.best(3)
        assert best in black_legal, best
        e.send("position startpos")

        e.send("go infinite")
        e.until(lambda x: x.startswith("info depth "))
        e.send("isready")
        _, while_searching = e.until(lambda x: x == "readyok")
        assert not any(x.startswith("bestmove ") for x in while_searching), while_searching
        e.send("stop")
        best, _ = e.best(3)
        assert best in start_legal, best
        e.ready()

        e.send("position fen 7k/6Q1/5K2/8/8/8/8/8 b - - 0 1")
        e.send("go infinite")
        time.sleep(0.03)  # allow a buggy terminal search to finish before isready
        e.send("isready")
        _, terminal_search = e.until(lambda x: x == "readyok")
        assert not any(x.startswith("bestmove ") for x in terminal_search), terminal_search
        e.send("stop")
        best, _ = e.best()
        assert best == "0000", best
        e.send("go depth 3")
        best, _ = e.best()
        assert best == "0000", best

        # Exercise position FEN + en-passant move and repeated searches.
        after_ep = "7k/8/3P4/8/4K3/8/8/8 b - - 0 2"
        after_legal = legal_by_divide(after_ep)
        e.send("position fen 7k/8/8/3pP3/4K3/8/8/8 w - d6 0 2 moves e5d6")
        for _ in range(4):
            e.send("go depth 2")
            best, _ = e.best()
            assert best in after_legal, best
        e.send("ucinewgame")
        e.ready()
        # Quit during active search should not deadlock.
        e.send("position startpos")
        e.send("go infinite")
        e.until(lambda x: x.startswith("info depth "))
    finally:
        e.close()
    print("PASS UCI handshake, options, positions, limits, cancellation, terminal and repeated searches")

    # --- searchmoves and MultiPV, in a fresh engine --------------------------
    e = Engine()
    try:
        e.send("uci")
        _, hello = e.until(lambda x: x == "uciok")
        assert any(x.startswith("option name MultiPV type spin default 1 min 1 max 8")
                   for x in hello), hello
        e.ready()
        e.send("position startpos")

        # A restriction to two quiet moves must pick one of them, at every kind
        # of limit, and never a move outside the list.
        for limits in ("depth 4", "nodes 3000", "movetime 60",
                       "wtime 5000 btime 5000 winc 50 binc 50"):
            e.send(f"go {limits} searchmoves e2e4 d2d4")
            best, lines = e.best(10)
            assert best in ("e2e4", "d2d4"), (limits, best, lines[-3:])

        # A restriction to one bad move must still return that move: the GUI
        # asked for a search over exactly this list.
        e.send("position fen 7k/8/8/8/8/8/8/K5Q1 w - - 0 1")
        e.send("go depth 4 searchmoves a1b1")
        best, _ = e.best(10)
        assert best == "a1b1", best

        # An invalid FEN must be rejected and leave the previous position in
        # place, rather than searching something the GUI did not ask for.
        e.send("position fen 7k/8/8/8/8/8/8/K6Q w - - 0 1")
        _, rejected = e.until(lambda x: x.startswith("info string position:"))
        assert "side not to move is in check" in rejected[0] or "in check" in rejected[0], rejected
        e.send("go depth 2")
        best, _ = e.best(10)
        assert best in legal_by_divide("7k/8/8/8/8/8/8/K5Q1 w - - 0 1"), best

        # An entirely illegal list is reported and then ignored.
        e.send("position startpos")
        e.send("go depth 2 searchmoves e2e5 z9z9")
        best, lines = e.best(10)
        assert any(x.startswith("info string go: searchmoves ignores illegal move e2e5") for x in lines), lines
        assert any(x.startswith("info string go: searchmoves has no legal move") for x in lines), lines
        assert best in legal_by_divide("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"), best

        # A searchmoves list followed by a real keyword must not swallow it.
        e.send("go searchmoves e2e4 depth 3")
        best, _ = e.best(10)
        assert best == "e2e4", best

        # MultiPV: three distinct moves with three distinct, ranked lines.
        e.send("setoption name MultiPV value 3")
        e.ready()
        e.send("position startpos")
        e.send("go depth 5")
        best, lines = e.best(15)
        info = [x for x in lines if x.startswith("info depth 5 ")]
        tagged = [x for x in info if " multipv " in x]
        assert len(tagged) == 3, info[-5:]
        indexed = {}
        for line in tagged:
            fields = line.split()
            index = int(fields[fields.index("multipv") + 1])
            move = fields[fields.index("pv") + 1]
            score_index = fields.index("score")
            kind, value = fields[score_index + 1], int(fields[score_index + 2])
            assert kind in ("cp", "mate"), line
            assert index not in indexed, tagged
            indexed[index] = (move, value if kind == "cp" else value * 30000)
        assert sorted(indexed) == [1, 2, 3], indexed
        moves = [indexed[i][0] for i in (1, 2, 3)]
        assert len(set(moves)) == 3, moves
        assert best == moves[0], (best, moves)
        assert indexed[1][1] >= indexed[2][1] >= indexed[3][1], indexed

        # Fewer legal moves than requested: report what exists, never invent a
        # line or crash.
        e.send("position fen 7k/8/8/8/8/8/6q1/K7 w - - 0 1")
        legal = legal_by_divide("7k/8/8/8/8/8/6q1/K7 w - - 0 1")
        e.send("go depth 4")
        best, lines = e.best(15)
        reported = [x for x in lines if " multipv " in x and x.startswith("info depth 4 ")]
        assert 1 <= len(reported) <= min(3, len(legal)), (len(reported), legal)
        assert best in legal, best

        # Back to single PV: no multipv tag, one line per depth.
        e.send("setoption name MultiPV value 1")
        e.ready()
        e.send("position startpos")
        e.send("go depth 4")
        _, lines = e.best(15)
        assert not any(" multipv " in x for x in lines), lines
    finally:
        e.close()
    print("PASS UCI searchmoves and MultiPV over depth, nodes, movetime and clocks")

if __name__ == "__main__":
    main()
