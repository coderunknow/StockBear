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
assert len(bests) == 100, len(bests)
for line in lines:
    assert line.startswith(("id ", "uciok", "readyok", "option ", "info ", "bestmove ")), line
    if line.startswith("bestmove "):
        assert re.fullmatch(r"bestmove [a-h][1-8][a-h][1-8][qrbn]?", line), line
print(f"PASS 300 deterministic malformed/cancellation cases; {len(bests)} legal-format bestmoves")
