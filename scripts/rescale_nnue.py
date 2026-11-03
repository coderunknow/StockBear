#!/usr/bin/env python3
"""Re-quantise a trained checkpoint with an empirically calibrated output scale.

A network distilled from teacher centipawns can end up with a much larger
output swing than the classical evaluation (measured: std 1127 cp vs 470 cp on
the same positions), which makes the search chase phantom advantages. This
script measures the regression slope of the raw network output against the
teacher cp on moderate positions and rescales the output layer so the engine's
centipawn scale matches the teacher's (pawn = 100), then re-quantises and
verifies. The float checkpoint is not modified.

Usage:
  python3 scripts/rescale_nnue.py --checkpoint net.pt --workdir nnue-work/b4cp3 \
      --out nnue-work/b4cp3/net-scaled.nnue [--band 800] [--base-scale 300]
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nnue_features  # noqa: E402
from train_nnue2 import Nnue, batch_arrays, measure_ranges, quantize, serialize, integer_eval  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--band", type=float, default=800.0)
    ap.add_argument("--base-scale", type=float, default=300.0)
    ap.add_argument("--fixed-scale", type=float, default=0.0,
                    help="if > 0, use this output scale directly instead of the measured slope")
    ap.add_argument("--rows", type=int, default=60000)
    args = ap.parse_args()

    ck = torch.load(args.checkpoint, weights_only=False)
    buckets = ck["buckets"]
    model = Nnue(ck["features"], ck["l1"], ck["l2"])
    model.load_state_dict(ck["state"])
    model.eval()
    boards = np.load(args.workdir / "boards.npy", mmap_mode="r")
    side = np.load(args.workdir / "side.npy")
    value = np.load(args.workdir / "value.npy")
    split = np.load(args.workdir / "split.npy")
    rows = np.nonzero(split == 0)[0][: args.rows]
    with torch.no_grad():
        outs = []
        for begin in range(0, len(rows), 4096):
            chunk = rows[begin:begin + 4096]
            fl, off = batch_arrays(boards, side, chunk, buckets)
            outs.append(model(torch.from_numpy(fl), torch.from_numpy(off)).reshape(-1).numpy())
    out = np.concatenate(outs)
    v = value[rows].astype(np.float64)
    m = np.abs(v) <= args.band
    # slope of teacher cp on raw output, through the origin, moderate band
    slope = float((out[m] @ v[m]) / max(1e-12, (out[m] ** 2).sum()))  # v = slope * out
    scale = args.fixed_scale if args.fixed_scale > 0 else slope  # engine cp = scale * raw_out
    print(f"slope teacher_cp/raw_out = {slope:.4f} on {int(m.sum())} positions "
          f"(|cp|<={args.band}) -> output_scale {args.base_scale} -> {scale:.2f}")

    cal_rows = rows[:20000]
    r1, r2 = measure_ranges(model, boards, side, buckets, cal_rows)
    net = quantize(model, scale, 1.0 / r1, 1.0 / r2, buckets)
    blob = serialize(net)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(blob)
    print(f"wrote {args.out} ({len(blob)} bytes) sha256 {hashlib.sha256(blob).hexdigest()}")

    # verify int vs calibrated float and eval statistics on held-out rows
    te = np.nonzero(split == 2)[0][:5000]
    with torch.no_grad():
        fl, off = batch_arrays(boards, side, te, buckets)
        g1, g2 = 1.0 / r1, 1.0 / r2
        acc = model.embed(torch.from_numpy(fl), torch.from_numpy(off[:-1])) + model.b1
        a = torch.clamp(acc.view(-1, 2 * model.l1) * g1, 0.0, 1.0)
        h = torch.clamp(a @ (model.w2.t() * (g2 / g1)) + model.b2 * g2, 0.0, 1.0)
        fout = (h @ (model.w3 * (1.0 / g2)) + model.b3[0] / g2).numpy() * scale
    inte = integer_eval(net, np.ascontiguousarray(boards[te]), side[te], buckets)
    vte = value[te].astype(np.float64)
    m = np.abs(vte) <= args.band
    print(f"verify: int-vs-float rms {np.sqrt(((inte - fout) ** 2).mean()):.1f} cp, "
          f"int std {inte.std():.1f}, teacher-cp std (band) {vte[m].std():.1f}, "
          f"corr(int, teacher) {np.corrcoef(inte, vte)[0, 1]:.4f}")


if __name__ == "__main__":
    main()
