#!/usr/bin/env python3
"""Transparent UCI proxy that multiplies the clock fields of `go` lines by
FACTOR (wtime/btime/winc/binc). Used to measure the Elo value of extra search
time (proxy for extra NPS) vs an unmodified engine at the same nominal TC."""
import subprocess, sys, re, threading

factor = float(sys.argv[1])
engine = sys.argv[2:]
p = subprocess.Popen(engine, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)

def pump():
    for out in p.stdout:
        sys.stdout.write(out)
        sys.stdout.flush()
    sys.exit(0)

threading.Thread(target=pump, daemon=True).start()

pat = re.compile(r"(wtime|btime|winc|binc) (\d+)")
def scale(line):
    if line.startswith("go "):
        return pat.sub(lambda m: m.group(1) + " " + str(int(int(m.group(2)) * factor)), line)
    return line

for line in sys.stdin:
    try:
        p.stdin.write(scale(line))
        p.stdin.flush()
    except BrokenPipeError:
        break
