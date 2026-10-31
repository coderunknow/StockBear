#!/usr/bin/env python3
"""Deterministic malformed-protocol and cancellation stress, stdlib only."""
import random
import re
import subprocess
import sys

exe = sys.argv[1]
rng = random.Random(20261030)
commands = ["uci", "isready"]
alphabet = "abcdefghABCDEFGH0123456789 -_/?!"
for i in range(300):
    kind = i % 6
    payload = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 90)))
    if kind == 0:
        commands.append("position fen " + payload)
    elif kind == 1:
        commands.append("position startpos moves " + payload)
    elif kind == 2:
        commands.append("go depth " + payload)
    elif kind == 3:
        commands += ["position startpos", "go nodes " + str(rng.randrange(0, 80)), "stop"]
    elif kind == 4:
        commands += ["position startpos", "go infinite", "stop"]
    else:
        commands.append("setoption name Hash value " + payload)
    if i % 20 == 0:
        commands.append("isready")
commands += ["isready", "quit"]
p = subprocess.run([exe], input="\n".join(commands) + "\n", text=True,
                   capture_output=True, timeout=20)
assert p.returncode == 0, (p.returncode, p.stderr)
lines = p.stdout.splitlines()
assert lines.count("uciok") == 1
assert lines.count("readyok") == commands.count("isready")
bests = [line for line in lines if line.startswith("bestmove ")]

KNOWN = {"depth", "nodes", "movetime", "wtime", "btime", "winc", "binc", "movestogo"}


def number(token, maximum):
    if not token.isdigit():
        return None
    value = int(token)
    return value if value <= maximum else None


def go_is_accepted(command):
    """Mirror of the UCI controller's grammar: unknown *tokens* are ignored,
    malformed values of known parameters reject the whole go command."""
    tokens = command.split()[1:]
    index = 0
    while index < len(tokens):
        key = tokens[index]
        index += 1
        if key == "infinite":
            continue
        if key not in KNOWN:
            continue
        if index >= len(tokens):
            return False
        value = tokens[index]
        index += 1
        maximum = 2 ** 64 - 1 if key == "nodes" else 10 ** 12
        if key in ("wtime", "btime") and len(value) > 1 and value[0] == "-":
            if number(value[1:], maximum) is None:
                return False
            continue
        parsed = number(value, maximum)
        if parsed is None:
            return False
        if key == "depth" and not 1 <= parsed <= 244:
            return False
        if key == "movestogo" and not 1 <= parsed <= 10000:
            return False
    return True


expected_bestmoves = sum(1 for command in commands
                         if command.startswith("go ") and go_is_accepted(command))
assert expected_bestmoves > 90, expected_bestmoves
assert len(bests) == expected_bestmoves, (len(bests), expected_bestmoves)
for line in lines:
    assert line.startswith(("id ", "uciok", "readyok", "option ", "info ", "bestmove ")), line
    if line.startswith("bestmove "):
        assert re.fullmatch(r"bestmove [a-h][1-8][a-h][1-8][qrbn]?", line), line
print(f"PASS 300 deterministic malformed/cancellation cases; {len(bests)} legal-format bestmoves "
      f"for {expected_bestmoves} accepted go commands")
