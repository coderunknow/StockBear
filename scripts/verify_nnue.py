#!/usr/bin/env python3
"""Verify that the engine and an independent integer reference agree on a network.

The engine evaluates a position through three separate implementations of the
same integer arithmetic: the portable scalar kernel, the AVX2 kernel, and (when
a network is trained) the Python trainer's quantiser. A disagreement between the
engine and the quantiser means the network that was measured in training is not
the network the engine plays with, which is invisible in play and only shows up
as unexplained weakness.

This script reads a ``.nnue`` file directly, re-implements the integer forward
pass from the file's own bytes (no checkpoint, no engine code), and compares the
result with ``stockbear nnue --eval`` on the same positions. Expected result: a
difference of zero on every position, because both sides use integer arithmetic
with identical rounding.

Usage:
    python3 scripts/verify_nnue.py --net benchmarks/training/dev4-*.nnue \
        --engine build/stockbear --positions fens.txt
"""
from __future__ import annotations

import argparse
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nnue_features  # noqa: E402


def load_network(path: Path) -> dict:
    blob = path.read_bytes()
    magic, version, buckets, l1, l2, act, h2, out, reserved = struct.unpack("<4sHHHHHHHH", blob[:20])
    if magic != b"SBNN" or version != 1:
        raise SystemExit(f"{path}: not an SBNN version 1 network")
    offset = 20
    inputs = 768 * buckets

    def take(count, dtype):
        nonlocal offset
        size = np.dtype(dtype).itemsize * count
        if offset + size > len(blob):
            raise SystemExit(f"{path}: truncated")
        values = np.frombuffer(blob, dtype=dtype, count=count, offset=offset)
        offset += size
        return values

    net = {
        "buckets": buckets,
        "l1": l1,
        "l2": l2,
        "actShift": act,
        "h2Shift": h2,
        "outShift": out,
        "reserved": reserved,
        "w1": take(inputs * l1, "<i2").reshape(inputs, l1).astype(np.int32),
        "b1": take(l1, "<i4").astype(np.int32),
        "w2": take(l2 * 2 * l1, "<i2").reshape(l2, 2 * l1).astype(np.int32),
        "b2": take(l2, "<i4").astype(np.int32),
        "w3": take(l2, "<i2").astype(np.int32),
        "b3": int(take(1, "<i4")[0]),
    }
    if offset != len(blob):
        raise SystemExit(f"{path}: {len(blob) - offset} trailing bytes")
    return net


def reference_eval(net: dict, board: np.ndarray, side: int) -> int:
    w1 = net["w1"]
    acc = np.empty(2 * net["l1"], dtype=np.int32)
    to_move, opponent = nnue_features.ordered_features(board, side, net["buckets"])
    acc[: net["l1"]] = net["b1"] + w1[to_move].sum(axis=0)
    acc[net["l1"] :] = net["b1"] + w1[opponent].sum(axis=0)
    round1 = 1 << (net["actShift"] - 1) if net["actShift"] > 0 else 0
    act = np.clip((acc + round1) >> net["actShift"], 0, 127)
    h2 = net["b2"] + net["w2"] @ act.astype(np.int64)
    round2 = 1 << (net["h2Shift"] - 1) if net["h2Shift"] > 0 else 0
    hid = np.clip((h2 + round2) >> net["h2Shift"], 0, 127)
    raw = net["b3"] + int(net["w3"] @ hid)
    return raw >> net["outShift"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--net", type=Path, required=True)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--positions", type=Path, required=True,
                        help="text file with one FEN per line")
    args = parser.parse_args()

    net = load_network(args.net)
    fens = [line.strip() for line in args.positions.read_text(encoding="ascii").splitlines() if line.strip()]
    if not fens:
        raise SystemExit("no positions")

    proc = subprocess.run([str(args.engine), "nnue", "--net", str(args.net), "--eval",
                           "--input", str(args.positions)],
                          capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise SystemExit(f"engine failed ({proc.returncode}): {proc.stderr.strip()}")
    engine_values = [int(line.split(",")[0]) for line in proc.stdout.splitlines() if "," in line]
    if len(engine_values) != len(fens):
        raise SystemExit(f"engine returned {len(engine_values)} values for {len(fens)} positions")

    mismatches = 0
    worst = 0
    for fen, got in zip(fens, engine_values):
        board, side = nnue_features.fen_to_board(fen)
        want = reference_eval(net, board, side)
        if got != want:
            mismatches += 1
            worst = max(worst, abs(got - want))
            if mismatches <= 5:
                print(f"MISMATCH {fen}: engine {got}, reference {want}")
    if mismatches:
        sys.exit(f"{mismatches}/{len(fens)} mismatches (largest difference {worst} cp)")
    print(f"network verification: {len(fens)} positions, engine == reference on all of them")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
