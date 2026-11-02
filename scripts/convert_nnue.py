#!/usr/bin/env python3
"""Quantise a trained StockBear network into the integer format the engine loads.

The float network is

    acc   = sum of W1 rows of the active features + b1        (per perspective)
    a     = clip(acc, 0, 1)
    h2    = W2 . [a_white, a_black] + b2
    b     = clip(h2, 0, 1)
    out   = W3 . b + b3
    score = OUTPUT_SCALE * out        (centipawns, side to move)

and the integer network is the same computation with fixed-point weights:

    acc_q  = sum of W1_q rows + b1_q                 (int16, Q1 = 2**s)
    a_q    = clip(acc_q >> act_shift, 0, 127)         (Q1/2**act_shift == 128)
    h2_q   = W2_q . a_q + b2_q                       (int32, Q2 = 2**h2_shift)
    b_q    = clip(h2_q >> h2_shift, 0, 127)
    out_q  = W3_q . b_q + b3_q                       (int32)
    score  = out_q >> out_shift

Every scale is chosen as a power of two, so the integer pipeline is exact apart
from the rounding of the weights themselves, and it is bit-reproducible on any
platform. ``--verify`` re-runs both paths on a corpus and reports the error;
``tests/integration/test_nnue_features.py`` additionally compares the integer
result with what the compiled engine prints.
"""
from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nnue_features  # noqa: E402

MAGIC = b"SBNN"
VERSION = 1


def powers_of_two_at_most(value: float, cap: int) -> int:
    if value < 1:
        return 1
    exponent = int(np.floor(np.log2(value)))
    return 1 << min(exponent, cap)


def measure_ranges(state, boards, sides, percentile: float = 99.9):
    """High-percentile |pre-activation| seen by each clipped ReLU on a calibration set.

    A trained network uses only a slice of the [0, 1] the clip allows, so the
    quantised activations would waste most of their 0..127 range. Rescaling the
    layer *below* the clip by 1/range and the layer above it by range leaves the
    float function unchanged wherever the clip is inactive and uses the whole
    integer range. This is a calibration step, not a change of model.

    The range is a high percentile rather than the maximum: the largest
    pre-activations in a sample are outliers, and scaling to them leaves the
    typical activation using only a handful of the available 128 integer levels
    (measured: mean activation 0.058 with a max-calibrated range, i.e. ~7 levels).
    Units above the percentile saturate at the clip instead, which costs far less
    accuracy than quantising everything coarsely. On the dev4 network this took
    the integer-vs-float error from 16.2 to 11.7 cp rms.
    """
    w1 = state["embed.weight"].detach().numpy().astype(np.float64)
    b1 = state["b1"].detach().numpy().astype(np.float64)
    w2 = state["w2"].detach().numpy().astype(np.float64)
    b2 = state["b2"].detach().numpy().astype(np.float64)
    layer1 = []
    layer2 = []
    for board, side in zip(boards, sides):
        features = nnue_features.ordered_features(board, int(side), 1)
        acc = np.concatenate([b1 + w1[features[0]].sum(axis=0),
                              b1 + w1[features[1]].sum(axis=0)])
        layer1.append(np.abs(acc))
        layer2.append(np.abs(w2 @ np.clip(acc, 0.0, 1.0) + b2))
    if not layer1:
        return 1.0, 1.0
    a1 = float(np.percentile(np.concatenate(layer1), percentile))
    a2 = float(np.percentile(np.concatenate(layer2), percentile))
    return max(a1, 1e-6), max(a2, 1e-6)


def quantize(state, output_scale: float, gain1: float = 1.0, gain2: float = 1.0):
    w1 = state["embed.weight"].detach().numpy().astype(np.float64) * gain1   # [768][L1]
    b1 = state["b1"].detach().numpy().astype(np.float64) * gain1
    w2 = state["w2"].detach().numpy().astype(np.float64) * (gain2 / gain1)   # [L2][2*L1]
    b2 = state["b2"].detach().numpy().astype(np.float64) * gain2
    w3 = state["w3"].detach().numpy().astype(np.float64) / gain2             # [L2]
    b3 = float(state["b3"].detach().numpy()[0])
    l1 = w1.shape[1]
    l2 = w2.shape[0]

    # First layer: the accumulator must stay inside int16 for 32 active features
    # plus the bias, and act_shift = s - 7 keeps the activation scale at 128.
    headroom = 32000.0 / (32.0 * float(np.abs(w1).max()) + float(np.abs(b1).max()))
    s = int(np.floor(np.log2(headroom)))
    if s < 7:
        raise SystemExit(f"first-layer weights too large to quantise safely (s={s} < 7)")
    s = min(s, 13)
    q1 = 1 << s
    act_shift = s - 7

    # Second layer: h2_shift == log2(Q2) keeps the second activation at 128.
    q2 = powers_of_two_at_most(32767.0 / max(1e-12, float(np.abs(w2).max())), 14)
    h2_shift = int(np.log2(q2))

    # Output layer: choose the largest power-of-two gain that keeps W3 in int16.
    limit = 32767.0 * 128.0 / (output_scale * max(1e-12, float(np.abs(w3).max())))
    out_shift = min(12, max(0, int(np.floor(np.log2(limit)))))
    out_gain = output_scale * (1 << out_shift) / 128.0

    net = {
        "gain1": gain1,
        "gain2": gain2,
        "kingBuckets": 1,
        "l1": l1,
        "l2": l2,
        "actShift": act_shift,
        "h2Shift": h2_shift,
        "outShift": out_shift,
        "w1": np.rint(w1 * q1).astype(np.int16),   # [feature][l1], row major
        "b1": np.rint(b1 * q1).astype(np.int32),
        "w2": np.rint(w2 * q2).astype(np.int16),
        # `h2_q = 128 * q2 * h2`, so the layer-2 bias carries the same factor as
        # the weights and not the plain q2 the activation scale divides out.
        "b2": np.rint(b2 * q2 * 128.0).astype(np.int32),
        "w3": np.rint(w3 * out_gain).astype(np.int16),
        # Likewise `out_q = 128 * out_gain * out`.
        "b3": int(np.rint(b3 * out_gain * 128.0)),
        "scales": {"q1": q1, "q2": q2, "out_gain": float(out_gain), "output_scale": output_scale},
    }
    worst = 32 * int(np.abs(net["w1"]).max()) + int(np.abs(net["b1"]).max())
    if worst > 32000:
        raise SystemExit(f"quantised accumulator can overflow int16 (bound {worst})")
    return net


def serialize(net) -> bytes:
    out = bytearray(MAGIC)
    out += struct.pack("<8H", VERSION, net["kingBuckets"], net["l1"], net["l2"],
                       net["actShift"], net["h2Shift"], net["outShift"], 0)
    out += net["w1"].astype("<i2").tobytes()
    out += net["b1"].astype("<i4").tobytes()
    out += net["w2"].astype("<i2").tobytes()
    out += net["b2"].astype("<i4").tobytes()
    out += net["w3"].astype("<i2").tobytes()
    out += struct.pack("<i", int(net["b3"]))
    return bytes(out)


def integer_eval(net, boards, sides):
    """Reference integer implementation, one batch of boards at a time."""
    l1 = net["l1"]
    out = np.zeros(boards.shape[0], dtype=np.int64)
    for row in range(boards.shape[0]):
        features = nnue_features.ordered_features(boards[row], int(sides[row]), net["kingBuckets"])
        acc = np.zeros((2, l1), dtype=np.int32)
        acc[0] = net["b1"]
        acc[1] = net["b1"]
        for perspective in (0, 1):
            rows = features[perspective]
            acc[perspective] += net["w1"][rows].astype(np.int32).sum(axis=0)
        # Rounded shifts, matching nnue_forward.cpp: truncation would bias every
        # activation downward and shrink the score by a few percent.
        round1 = 1 << (net["actShift"] - 1) if net["actShift"] > 0 else 0
        act = np.clip((acc + round1) >> net["actShift"], 0, 127).reshape(-1).astype(np.int64)
        h2 = net["b2"] + net["w2"].astype(np.int64) @ act
        round2 = 1 << (net["h2Shift"] - 1) if net["h2Shift"] > 0 else 0
        hid = np.clip((h2 + round2) >> net["h2Shift"], 0, 127)
        out[row] = int(net["b3"] + net["w3"].astype(np.int64) @ hid)
    return out >> net["outShift"]


def float_eval(state, boards, sides, output_scale, gain1=1.0, gain2=1.0):
    w1 = state["embed.weight"].detach().numpy().astype(np.float64) * gain1
    b1 = state["b1"].detach().numpy().astype(np.float64) * gain1
    w2 = state["w2"].detach().numpy().astype(np.float64) * (gain2 / gain1)
    b2 = state["b2"].detach().numpy().astype(np.float64) * gain2
    w3 = state["w3"].detach().numpy().astype(np.float64) / gain2
    b3 = float(state["b3"].detach().numpy()[0])
    values = np.zeros(boards.shape[0])
    for row in range(boards.shape[0]):
        features = nnue_features.ordered_features(boards[row], int(sides[row]), 1)
        acc = np.concatenate([b1 + w1[features[0]].sum(axis=0),
                              b1 + w1[features[1]].sum(axis=0)])
        a = np.clip(acc, 0.0, 1.0)
        hidden = np.clip(np.maximum(w2 @ a + b2, 0.0), 0.0, 1.0)
        values[row] = output_scale * float(w3 @ hidden + b3)
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", type=Path, help="corpus file whose positions are checked")
    parser.add_argument("--calibrate", type=Path, help="corpus file used to measure activation ranges")
    parser.add_argument("--calibrate-positions", type=int, default=4000)
    parser.add_argument("--verify-positions", type=int, default=2000)
    parser.add_argument("--output-scale", type=float, default=None,
                        help="centipawns per network output unit; defaults to the "
                             "value stored in the checkpoint. Raising it makes the "
                             "engine score every position more extremely, which the "
                             "search's absolute margins (null move, reverse futility, "
                             "futility) are calibrated for, so it is a playing-strength "
                             "decision and must be measured, not guessed")
    args = parser.parse_args()

    checkpoint = torch.load(args.checkpoint, weights_only=False)
    state = checkpoint["state"]
    output_scale = float(checkpoint.get("output_scale", 300.0))
    if args.output_scale is not None:
        output_scale = float(args.output_scale)
    if args.calibrate:
        boards, sides, _, _ = nnue_features.read_selfplay(str(args.calibrate), args.calibrate_positions)
    elif args.verify:
        boards, sides, _, _ = nnue_features.read_selfplay(str(args.verify), args.verify_positions)
    else:
        boards = np.zeros((0, 64), dtype=np.uint8)
    if boards.shape[0]:
        range1, range2 = measure_ranges(state, boards, sides)
        gain1, gain2 = 1.0 / range1, 1.0 / range2
        print(f"calibration on {boards.shape[0]} positions: activation ranges "
              f"{range1:.4f} / {range2:.4f} -> gains {gain1:.3f} / {gain2:.3f}")
    else:
        gain1 = gain2 = 1.0
    net = quantize(state, output_scale, gain1, gain2)
    blob = serialize(net)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(blob)
    print(f"wrote {args.output} ({len(blob)} bytes), sha256 {hashlib.sha256(blob).hexdigest()}")
    print(f"l1={net['l1']} l2={net['l2']} act_shift={net['actShift']} "
          f"h2_shift={net['h2Shift']} out_shift={net['outShift']} scales={net['scales']}")

    if args.verify:
        boards, sides, results, _ = nnue_features.read_selfplay(str(args.verify), args.verify_positions)
        integer = integer_eval(net, boards, sides)
        floating = float_eval(state, boards, sides, output_scale, gain1, gain2)
        diff = integer - floating
        correlation = float(np.corrcoef(integer.astype(np.float64), floating)[0, 1])
        print(f"verify on {boards.shape[0]} positions: "
              f"max |int - float| = {np.abs(diff).max():.1f} cp, "
              f"mean = {diff.mean():+.2f} cp, rms = {np.sqrt((diff ** 2).mean()):.2f} cp, "
              f"correlation = {correlation:.6f}")
        print(f"integer eval: mean {integer.mean():+.1f} std {integer.std():.1f} "
              f"min {integer.min()} max {integer.max()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
