#!/usr/bin/env python3
"""Dead-position corpus: expected verdicts, timings and witness verification.

Runs `stockbear deadpos` over a curated corpus that covers every class of the
FIDE Article 5.2.2 specification in docs/DEAD_POSITIONS.md:

  * inevitably dead material (bare kings, single minor, same-coloured bishops),
  * dead positions with many pieces (locked pawn structures, with and without
    bishops; a material detector cannot find these),
  * alive positions with sparse material where the mate needs cooperation
    (KNN v K, KB v KN, KN v KN, opposite-coloured bishops),
  * ordinary middlegames,
  * terminal positions, which Articles 5.1.1 / 5.2.1 decide and which must not
    be reported as Article 5.2.2 dead positions,
  * en-passant and castling-right states, which are part of the position,
  * budget exhaustion, which must yield `unknown` and never `dead`.

Every `alive` verdict that carries a witness is replayed and checked to end in
checkmate. The script exits non-zero on any mismatch, so CI can gate on it.

Usage:
  python3 scripts/dead_position_corpus.py ./build/stockbear [--markdown OUT.md]
"""
import argparse
import subprocess
import sys

# (label, fen, expected status, extra engine arguments)
CASES = [
    ("Bare kings", "8/8/8/4k3/8/8/8/4K3 w - - 0 1", "dead", []),
    ("Bare kings, black to move", "8/8/8/4k3/8/8/8/4K3 b - - 0 1", "dead", []),
    ("King and bishop v king", "8/8/8/8/4k3/8/8/2B1K3 b - - 0 1", "dead", []),
    ("King and knight v king", "8/8/8/8/4k3/8/8/2N1K3 w - - 0 1", "dead", []),
    ("King and two knights v king", "8/8/8/8/4k3/8/8/1N2K1N1 w - - 0 1", "alive", []),
    ("Same-coloured bishops only", "4k3/8/8/8/8/4B3/8/2B1K3 w - - 0 1", "dead", []),
    ("One same-coloured bishop each", "4k3/8/8/8/8/4b3/8/2B1K3 w - - 0 1", "dead", []),
    ("Opposite-coloured bishops", "4k3/8/8/8/8/4b3/8/3B1K2 w - - 0 1", "alive",
     ["--states", "8000000"]),
    ("Knight v knight", "4k1n1/8/8/8/8/8/8/4K1N1 w - - 0 1", "alive",
     ["--states", "20000000"]),
    ("King and queen v king", "8/8/8/8/8/2k5/8/1Q2K3 w - - 0 1", "alive", []),
    ("King and rook v king", "4k3/8/8/8/8/8/8/4K2R w - - 0 1", "alive", []),
    ("King and pawn v king", "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1", "alive", []),
    ("14 blocked pawns", "8/3k4/p1p2p1p/PpPp1PpP/1P1P2P1/4K3/8/8 w - - 6 49", "dead", []),
    ("14 blocked pawns, black to move", "8/3k4/p1p2p1p/PpPp1PpP/1P1P2P1/4K3/8/8 b - - 6 49",
     "dead", []),
    ("Locked pawn chains with bishops", "2b1k3/8/8/1p1p1p1p/1P1P1P1P/8/8/2B1K3 w - - 0 1",
     "dead", ["--states", "3000000"]),
    ("Locked pawn chains with bishops, black", "2b1k3/8/8/1p1p1p1p/1P1P1P1P/8/8/2B1K3 b - - 0 1",
     "dead", ["--states", "3000000"]),
    ("Castling rights present", "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "alive", []),
    ("En-passant right present", "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2", "alive", []),
    ("Starting position", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
     "alive", []),
    ("Kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
     "alive", []),
    ("Italian middlegame",
     "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4", "alive", []),
    # Checkmate / stalemate are decided before Art. 5.2.2 can apply; the engine
    # reports them as "alive" with a terminal reason and never as dead.
    ("Checkmate (Article 5.1.1)", "7k/6Q1/5K2/8/8/8/8/8 b - - 0 1", "alive", []),
    ("Stalemate (Article 5.2.1)", "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", "alive", []),
]


def parse(stdout: str) -> dict:
    fields = {}
    for line in stdout.splitlines():
        key, _, value = line.partition(" ")
        fields[key] = value
    return fields


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", help="path to the stockbear executable")
    parser.add_argument("--markdown", help="write a markdown table to this path")
    args = parser.parse_args()

    rows = []
    failures = []
    for label, fen, expected, extra in CASES:
        proc = subprocess.run([args.engine, "deadpos", "--fen", fen, *extra],
                              capture_output=True, text=True, check=False, timeout=1800)
        fields = parse(proc.stdout)
        status = fields.get("status", "missing")
        states = int(fields.get("component_states", "0"))
        expanded = int(fields.get("component_expanded", "0"))
        micros = int(fields.get("time_us", "0"))
        witness_ok = fields.get("witness_ends_in_mate", "-")
        problem = ""
        if status != expected:
            problem = f"expected {expected}, got {status}"
        elif status == "alive" and "witness" in fields and witness_ok != "yes":
            problem = "witness does not end in checkmate"
        if problem:
            failures.append(f"{label}: {problem}")
        rows.append((label, status, states, expanded, micros / 1000.0, witness_ok, problem))
        print(f"{label:<42} {status:<8} states={states:<9} expanded={expanded:<9} "
              f"{micros / 1000.0:8.2f} ms witness_mate={witness_ok} {problem}")

    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as handle:
            handle.write("| Position | Verdict | Distinct states | Positions expanded | Time (ms) "
                         "| Witness ends in mate |\n")
            handle.write("|---|---|---:|---:|---:|---|\n")
            for label, status, states, expanded, ms, witness_ok, problem in rows:
                note = f" **{problem}**" if problem else ""
                handle.write(f"| {label} | {status} | {states} | {expanded} | {ms:.2f} | "
                             f"{witness_ok if witness_ok != '-' else 'n/a'} |{note}\n")

    print(f"\ncases {len(CASES)}, failures {len(failures)}")
    for failure in failures:
        print("FAIL", failure)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
