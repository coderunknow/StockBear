#!/usr/bin/env python3
"""Paired-opening two-engine UCI matches. The engines remain external processes.

Optional development dependency: `pip install chess==1.11.2` (move legality,
standard game adjudication, PGN). Normal StockBear execution has no dependency.
For example:
  python scripts/tournament.py --engine-a build-release/stockbear \
      --engine-b /path/to/other-engine --games 8 --base-ms 1000 --inc-ms 20 \
      --pgn match.pgn --jsonl match.jsonl
"""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import platform
import queue
import random
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import match_stats
try:
    import chess
    import chess.pgn
except ImportError:
    sys.exit("Install the optional tournament dependency: pip install chess==1.11.2")


def parse_option_line(line):
    """Parse a UCI `option name ... type ...` line into (name, spec)."""
    rest = line[len("option name "):]
    name, _, tail = rest.partition(" type ")
    spec = {"type": tail.split()[0].lower() if tail.split() else "unknown"}
    for key in ("default", "min", "max"):
        token = f" {key} "
        if token in tail:
            value = tail.split(token, 1)[1]
            # default/min/max are single tokens; combo/string defaults may not be.
            spec[key] = value.split()[0] if value.split() else ""
    if " var " in tail:
        # UCI combo values are free-form strings and may contain spaces, so keep
        # everything between two ` var ` tokens instead of the first word.
        spec["vars"] = [v.strip() for v in tail.split(" var ")[1:]]
    return name, spec


def check_option_value(name, spec, value):
    """Reject a value the engine would refuse, before the match starts.

    Recording an option as "effective" without checking it is how an ablation
    silently turns into "both engines identical": `--a-option NullMove=flase` is
    rejected by the engine with an `info string`, which `ready()` would discard.
    """
    kind = spec.get("type", "unknown")
    if kind == "check":
        if value.strip().lower() not in ("true", "false"):
            raise ValueError(f"option {name!r} expects true or false, got {value!r}")
    elif kind == "spin":
        try:
            number = int(value)
        except ValueError:
            raise ValueError(f"option {name!r} expects an integer, got {value!r}") from None
        if spec.get("min") not in (None, "") and number < int(spec["min"]):
            raise ValueError(f"option {name!r} minimum is {spec['min']}, got {number}")
        if spec.get("max") not in (None, "") and number > int(spec["max"]):
            raise ValueError(f"option {name!r} maximum is {spec['max']}, got {number}")
    elif kind == "combo":
        if value not in spec.get("vars", []):
            raise ValueError(f"option {name!r} expects one of {spec.get('vars')}, got {value!r}")
    elif kind == "button":
        raise ValueError(f"option {name!r} is a button and takes no value")
    # string / unknown types are passed through unchanged.


class UciEngine:
    def __init__(self, path, hash_mb, threads, extra_options=None):
        self.path = os.path.abspath(path)
        self.p = subprocess.Popen([self.path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, bufsize=1)
        self.out = queue.Queue()
        self.err = []
        self.name = os.path.basename(path)
        self.options = {}
        self.option_specs = {}
        threading.Thread(target=self._reader, args=(self.p.stdout, self.out), daemon=True).start()
        threading.Thread(target=self._stderr, daemon=True).start()
        try:
            self.send("uci")
            deadline = time.monotonic() + 10
            while True:
                line = self.read(deadline - time.monotonic())
                if line == "uciok":
                    break
                if line.startswith("id name "):
                    self.name = line[8:]
                if line.startswith("option name ") and " type " in line:
                    name, spec = parse_option_line(line)
                    self.options[name.lower()] = name
                    self.option_specs[name.lower()] = spec
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"{self.name} did not complete UCI handshake")
            self.effective = {}
            for option, value in (("hash", hash_mb), ("threads", threads)):
                if option in self.options:
                    self.set_option(self.options[option], str(value))
                    self.effective[option] = f"requested {value}"
                elif option == "threads" and self.name.startswith("StockBear "):
                    if threads != 1:
                        raise ValueError("StockBear supports one search thread; use --threads 1")
                    self.effective[option] = "1 (StockBear single-threaded build)"
                else:
                    self.effective[option] = "not advertised / unverified"
            # Additional engine options (used for search-feature ablations such
            # as NullMove=false). Refuse anything the engine does not advertise
            # so a typo cannot silently turn into "both engines identical".
            for item in extra_options or []:
                name, _, value = item.partition("=")
                if not name or not value:
                    raise ValueError(f"expected NAME=VALUE, got {item!r}")
                if name.lower() not in self.options:
                    raise ValueError(f"{self.name} does not advertise option {name!r}")
                canonical = self.options[name.lower()]
                check_option_value(canonical, self.option_specs.get(name.lower(), {}), value)
                self.set_option(canonical, value)
                self.effective[name.lower()] = value
            self.ready()

        except BaseException:
            self.close()
            raise

    @staticmethod
    def _reader(pipe, q):
        for line in iter(pipe.readline, ""):
            q.put(line.strip())
        q.put(None)

    def _stderr(self):
        for line in iter(self.p.stderr.readline, ""):
            # Bounded diagnostic tail; never stored as tournament results.
            self.err.append(line.rstrip())
            if len(self.err) > 100:
                self.err.pop(0)

    def send(self, text):
        if self.p.poll() is not None:
            raise RuntimeError(f"{self.name} exited with {self.p.returncode}: {self.err[-5:]}")
        self.p.stdin.write(text + "\n")
        self.p.stdin.flush()

    def read(self, timeout):
        try:
            line = self.out.get(timeout=max(.001, timeout))
        except queue.Empty as exc:
            raise TimeoutError(f"{self.name} did not respond within {timeout:.2f}s") from exc
        if line is None:
            raise RuntimeError(f"{self.name} exited: {self.err[-5:]}")
        return line

    def ready(self):
        """Send isready and return any `info string` lines seen before readyok."""
        self.send("isready")
        deadline = time.monotonic() + 10
        messages = []
        while True:
            line = self.read(deadline - time.monotonic())
            if line == "readyok":
                return messages
            if line.startswith("info string "):
                messages.append(line)
            if time.monotonic() >= deadline:
                raise TimeoutError(f"{self.name} did not become ready")

    def set_option(self, name, value):
        """Apply an option and fail loudly if the engine refuses it."""
        self.send(f"setoption name {name} value {value}")
        for line in self.ready():
            # StockBear reports a rejected value as `info string setoption: ...`
            # and a failed allocation as `info string Hash allocation failed:
            # ...`; either way the requested value did not take effect, so it
            # must not be recorded as effective.
            lowered = line.lower()
            if "setoption" in lowered or "failed" in lowered or "error" in lowered:
                raise ValueError(f"{self.name} rejected {name}={value}: {line}")

    def new_game(self):
        self.send("ucinewgame")
        self.ready()

    def bestmove(self, moves, clocks, increment, color, nodes=0):
        suffix = " moves " + " ".join(moves) if moves else ""
        self.send("position startpos" + suffix)
        if nodes:
            # Deterministic move limit: the engine cannot lose on the clock, so
            # a node budget is the right control for tests and for reproducing a
            # match on a shared machine.
            self.send(f"go nodes {nodes}")
        else:
            self.send(f"go wtime {max(0, int(clocks[chess.WHITE]))} "
                      f"btime {max(0, int(clocks[chess.BLACK]))} winc {increment} binc {increment}")
        deadline = time.monotonic() + (60 if nodes else max(0, clocks[color]) / 1000 + 3)
        while True:
            line = self.read(deadline - time.monotonic())
            if line.startswith("bestmove "):
                fields = line.split()
                if len(fields) < 2:
                    raise RuntimeError(f"malformed bestmove from {self.name}: {line}")
                return fields[1]
            if time.monotonic() >= deadline:
                raise TimeoutError(f"{self.name} exceeded its response deadline")

    def close(self):
        if self.p.poll() is None:
            try:
                self.send("quit")
                self.p.wait(timeout=3)
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                self.p.kill()
                self.p.wait(timeout=3)


def positive_finite_float(text):
    """argparse type for the SPRT hypothesis: finite and strictly positive.

    `nan` or `inf` would propagate into the summary, where the strict-JSON
    writer (allow_nan=False) would then fail after the games had already been
    played. Reject the value at argument-parsing time instead.
    """
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if not math.isfinite(value) or value <= 0.0:
        raise argparse.ArgumentTypeError(f"expected a finite positive Elo, got {text!r}")
    return value


def read_openings(path):
    openings = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" not in line:
            raise ValueError(f"invalid opening line: {line}")
        name, moves = line.split("|", 1)
        board = chess.Board()
        for move in moves.split():
            board.push_uci(move)  # validates each move
        openings.append((name.strip(), moves.split()))
    if not openings:
        raise ValueError("opening suite is empty")
    return openings


def elo_for(score):
    if score <= 0:
        return "-inf"
    if score >= 1:
        return "+inf"
    return round(400 * math.log10(score / (1 - score)), 1)


def statistics(results):
    n = len(results)
    wins, draws, losses = results.count(1), results.count(.5), results.count(0)
    if not n:
        return {"games": 0, "wins": 0, "draws": 0, "losses": 0, "note": "no completed games"}
    p = sum(results) / n
    # Approximate Wilson interval on fractional scores. It avoids the false
    # zero-width interval at 0%/100%, but does not model opening-pair effects.
    z = 1.959963984540054
    denominator = 1 + z*z/n
    center = (p + z*z/(2*n)) / denominator
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denominator
    lo, hi = max(0, center-half), min(1, center+half)
    return {"games": n, "wins": wins, "draws": draws, "losses": losses,
            "score": round(p, 4), "score_ci95_approx": [round(lo, 4), round(hi, 4)],
            "elo_difference": elo_for(p), "elo_ci95_approx": [elo_for(lo), elo_for(hi)],
            "ci_method": "Wilson on fractional game scores; approximation ignores pair dependence"}


def play_game(a, b, index, opening, base_ms, inc_ms, max_plies, nodes=0):
    opening_name, opening_moves = opening
    white, black = (a, b) if index % 2 == 0 else (b, a)
    board = chess.Board()
    game = chess.pgn.Game()
    game.headers.update({"Event": "StockBear paired-opening match", "Site": "local",
                         "White": white.name, "Black": black.name,
                         "Round": str(index + 1), "Opening": opening_name,
                         "TimeControl": (f"nodes/{nodes}" if nodes else
                                          f"{base_ms/1000:g}+{inc_ms/1000:g}")})
    node = game
    for text in opening_moves:
        move = board.parse_uci(text)
        board.push(move)
        node = node.add_variation(move)
    moves = opening_moves.copy()
    clocks = {chess.WHITE: float(base_ms), chess.BLACK: float(base_ms)}
    for engine in (a, b):
        engine.new_game()
    termination = None
    result = "*"
    while len(moves) < max_plies:
        outcome = board.outcome(claim_draw=True)
        if outcome is not None:
            result = outcome.result()
            termination = outcome.termination.name
            break
        color = board.turn
        engine = white if color == chess.WHITE else black
        start = time.monotonic_ns()
        error = None
        text = None
        try:
            text = engine.bestmove(moves, clocks, inc_ms, color, nodes)
        except (RuntimeError, TimeoutError, OSError) as exc:
            error = exc
        elapsed = (time.monotonic_ns() - start) / 1_000_000
        if not nodes:
            clocks[color] -= elapsed
        if not nodes and clocks[color] < 0:
            result = "0-1" if color == chess.WHITE else "1-0"
            termination = f"TIME_FORFEIT ({engine.name}, {elapsed:.1f}ms move)"
            break
        if error is None:
            try:
                move = chess.Move.from_uci(text)
                if move not in board.legal_moves:
                    raise ValueError(f"illegal move {text}")
            except ValueError as exc:
                error = exc
        if error is not None:
            result = "0-1" if color == chess.WHITE else "1-0"
            termination = f"ENGINE_FAILURE ({engine.name}: {error})"
            break
        board.push(move)
        node = node.add_variation(move)
        moves.append(move.uci())
        if not nodes:
            clocks[color] += inc_ms
    if termination is None:
        outcome = board.outcome(claim_draw=True)
        if outcome is not None:
            result, termination = outcome.result(), outcome.termination.name
        else:
            termination = "UNADJUDICATED_MAX_PLIES"
    game.headers["Result"] = result
    game.headers["Termination"] = termination
    score_a = None
    if result == "1/2-1/2":
        score_a = .5
    elif result in ("1-0", "0-1"):
        white_won = result == "1-0"
        score_a = 1 if (white is a) == white_won else 0
    return game, {"game": index+1, "opening": opening_name, "white": white.name,
                  "black": black.name, "result": result, "score_a": score_a,
                  "termination": termination, "plies": len(moves),
                  "remaining_white_ms": round(clocks[chess.WHITE], 2),
                  "remaining_black_ms": round(clocks[chess.BLACK], 2)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-a", required=True)
    parser.add_argument("--engine-b", required=True)
    parser.add_argument("--a-option", action="append", default=[], metavar="NAME=VALUE",
                        help="extra engine option for engine A (repeatable; used for ablations)")
    parser.add_argument("--b-option", action="append", default=[], metavar="NAME=VALUE",
                        help="extra engine option for engine B (repeatable)")
    parser.add_argument("--games", type=int, default=8, help="even number; paired colors per opening")
    parser.add_argument("--base-ms", type=int, default=1000)
    parser.add_argument("--inc-ms", type=int, default=20)
    parser.add_argument("--hash", type=int, default=16, help="requested MB for each engine")
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--max-plies", type=int, default=300)
    parser.add_argument("--nodes", type=int, default=0, metavar="N",
                        help="search N nodes per move instead of using the clock "
                             "(deterministic; no time forfeits)")
    parser.add_argument("--openings", default=str(Path(__file__).resolve().parents[1] /
                                                 "benchmarks/positions/openings.txt"))
    parser.add_argument("--pgn", default="match.pgn")
    parser.add_argument("--jsonl", default="match.jsonl")
    # Guarded below: the three outputs are opened in write mode, so two options
    # naming one file would overwrite each other's records.
    parser.add_argument("--csv", default=None, help="optional per-game CSV output")
    parser.add_argument("--seed", type=int, default=20261031,
                        help="deterministic opening-order shuffle seed")
    parser.add_argument("--sprt-elo", type=positive_finite_float, default=5.0,
                        help="H1 Elo gain for the reported SPRT log-likelihood ratio")
    args = parser.parse_args()
    if args.games < 2 or args.games % 2:
        parser.error("--games must be positive and even")
    if args.base_ms < 1 or args.inc_ms < 0 or not 1 <= args.hash <= 512 or args.threads < 1 or args.max_plies < 1 or args.nodes < 0:
        parser.error("invalid clock, hash, thread or ply limit")
    # The PGN, JSONL and CSV outputs are opened in write mode; if two options
    # name the same file the later open truncates the earlier one and the
    # match record is destroyed. Compare resolved paths, not the raw strings.
    outputs = {"pgn": Path(args.pgn).resolve(), "jsonl": Path(args.jsonl).resolve()}
    if args.csv:
        outputs["csv"] = Path(args.csv).resolve()
    if len(set(outputs.values())) != len(outputs):
        parser.error("--pgn, --jsonl and --csv must name different files")
    openings = read_openings(args.openings)
    # Deterministic shuffle: with a fixed seed a match is reproducible, and the
    # paired structure (each opening played twice with reversed colours) is kept.
    random.Random(args.seed).shuffle(openings)
    engines = []
    # Initialised before the engines are constructed: an option-validation error
    # in UciEngine must not turn the cleanup path into an UnboundLocalError and
    # leak an already started engine.
    csv_handle = None
    try:
        engines.append(UciEngine(args.engine_a, args.hash, args.threads, args.a_option))
        engines.append(UciEngine(args.engine_b, args.hash, args.threads, args.b_option))
        a, b = engines
        config = {"engine_a": a.name, "engine_b": b.name,
                  "engine_a_path": a.path, "engine_b_path": b.path,
                  "engine_a_options": a.effective, "engine_b_options": b.effective,
                  "base_ms": args.base_ms, "increment_ms": args.inc_ms,
                  "nodes_per_move": args.nodes,
                  "hash_requested_mb_each": args.hash, "threads_requested_each": args.threads,
                  "host": platform.platform(), "machine": platform.machine(),
                  "python_chess": chess.__version__, "opening_file": args.openings,
                  "seed": args.seed,
                  "policy": "claimable draws automatically claimed; capped games unadjudicated"}
        print(json.dumps({"configuration": config}), flush=True)
        scores = []
        pair_scores = []
        pair_games = {}
        pair_openings = {}
        openings_of_pairs = []
        csv_writer = None
        if args.csv:
            csv_handle = open(args.csv, "w", encoding="utf-8", newline="")
            csv_writer = csv.writer(csv_handle)
            csv_writer.writerow(["game", "opening", "white", "black", "result",
                                 "score_a", "termination", "plies",
                                 "remaining_white_ms", "remaining_black_ms"])
        with open(args.pgn, "w", encoding="utf-8") as pgn, open(args.jsonl, "w", encoding="utf-8") as log:
            log.write(json.dumps({"configuration": config}) + "\n")
            for i in range(args.games):
                game, record = play_game(a, b, i, openings[(i//2) % len(openings)],
                                         args.base_ms, args.inc_ms, args.max_plies,
                                         args.nodes)
                if i:
                    print(file=pgn)  # one separator between games, none after the last
                print(game, file=pgn, flush=True)
                log.write(json.dumps(record) + "\n"); log.flush()
                print(json.dumps(record), flush=True)
                if csv_writer is not None:
                    csv_writer.writerow([record["game"], record["opening"], record["white"],
                                         record["black"], record["result"],
                                         "" if record["score_a"] is None else record["score_a"],
                                         record["termination"], record["plies"],
                                         record["remaining_white_ms"], record["remaining_black_ms"]])
                if record["score_a"] is not None:
                    scores.append(record["score_a"])
                # Pair accumulation is keyed by the pair index, not by opening
                # name: the two games of a pair are indices 2k and 2k+1, and a
                # pair contributes a pentanomial observation only when *both*
                # games were adjudicated. Pairing by name would let an
                # unadjudicated game leave a half-filled pair behind and let a
                # later game of the same opening (the suite is reused) merge
                # into the wrong pair.
                pair_index = i // 2
                if pair_index not in pair_games:
                    pair_games[pair_index] = [None, None]
                    pair_openings[pair_index] = record["opening"]
                pair_games[pair_index][i % 2] = record["score_a"]
            for index in sorted(pair_games):
                first, second = pair_games[index]
                if first is None or second is None:
                    continue
                pair_scores.append(first + second)
                # The opening label travels with the pair so the clustered
                # interval can group pairs that replay the same opening.
                openings_of_pairs.append(pair_openings[index])
            summary = match_stats.summarise(scores, pair_scores,
                                            match_stats.lmr_step(pair_scores, 0.0,
                                                                 args.sprt_elo),
                                            pair_openings=openings_of_pairs)
            summary["unadjudicated"] = args.games - len(scores)
            summary["config"] = {"engine_a": a.name, "engine_b": b.name,
                                 "base_ms": args.base_ms, "increment_ms": args.inc_ms,
                                 "nodes_per_move": args.nodes,
                                 "hash_mb_each": args.hash, "threads_each": args.threads,
                                 "openings": args.openings, "seed": args.seed,
                                 "max_plies": args.max_plies}
            # allow_nan=False makes a non-finite value fail loudly instead of
            # writing "Infinity", which is not valid JSON (RFC 8259).
            summary_text = json.dumps({"summary": summary}, allow_nan=False)
            log.write(summary_text + "\n")
            print(summary_text, flush=True)
            print(match_stats.format_report(summary), flush=True)
    finally:
        if csv_handle is not None:
            csv_handle.close()
        for e in engines:
            e.close()

if __name__ == "__main__":
    main()
