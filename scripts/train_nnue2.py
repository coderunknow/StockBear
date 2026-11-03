#!/usr/bin/env python3
"""dev5 NNUE trainer (v2): king buckets + teacher-search labels.

Same architecture and integer format as dev4 (``scripts/train_nnue.py`` +
``scripts/convert_nnue.py``, kept unchanged for provenance), with three
differences that docs/DEV4_TRAINING.md §8 called for:

1. ``--buckets 1|4|16|64`` selects the engine's king-bucketed feature space
   (``nnue_features.batch_indices`` supports all of them and is
   differentially tested against the C++ engine). The quantiser writes the
   bucket count into the ``SBNN`` header, which the engine reads at load time.
2. ``--target cp`` trains directly on teacher search scores (``<cp> <game>
   <fen>`` files from ``scripts/label_search.py``) as a regression in units of
   ``OUTPUT_SCALE`` centipawns; ``--target wdl`` trains the dev4 objective
   (sigmoid output vs win probability, from outcome or search labels);
   ``--mix-cp``/``--mix-wdl`` blend the two losses.
3. Best-validation checkpointing with a time budget, several seeds via
   ``--seed``.

The teacher engine is only ever executed as an external process by
``label_search.py``; no teacher code, weights or datasets are incorporated
here. Every corpus input is hashed into the report.

Usage:
  python3 scripts/train_nnue2.py --input labels.txt [--input corpus.txt] \
      --buckets 4 --l1 128 --l2 32 --target cp --epochs 30 \
      --out work/net --report work/report.json [--time-budget 1800]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nnue_features  # noqa: E402

OUTPUT_SCALE = 300.0
LN10 = math.log(10.0)
MAGIC = b"SBNN"
VERSION = 1


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sigmoid_log10(s, k):
    return 1.0 / (1.0 + np.exp(-np.clip(s / k, -6, 6) * LN10))


class Nnue(nn.Module):
    def __init__(self, features, l1, l2):
        super().__init__()
        self.features = features
        self.l1 = l1
        self.l2 = l2
        self.embed = nn.EmbeddingBag(features, l1, mode="sum", sparse=True)
        self.b1 = nn.Parameter(torch.zeros(l1))
        self.w2 = nn.Parameter(torch.empty(l2, 2 * l1))
        self.b2 = nn.Parameter(torch.zeros(l2))
        self.w3 = nn.Parameter(torch.empty(l2))
        self.b3 = nn.Parameter(torch.zeros(1))
        self.embed.weight.data.uniform_(-0.55, 0.55)
        nn.init.uniform_(self.w2, -0.15, 0.15)
        activation_mean = 0.32
        self.b2.data.copy_(-activation_mean * self.w2.data.sum(dim=1))
        nn.init.uniform_(self.w3, -1.0 / math.sqrt(l2), 1.0 / math.sqrt(l2))

    def forward_from_accumulator(self, acc):
        a = torch.clamp(acc, 0.0, 1.0)
        hidden = torch.clamp(a @ self.w2.t() + self.b2, 0.0, 1.0)
        return hidden @ self.w3 + self.b3

    def forward(self, flat, offsets):
        acc = self.embed(flat, offsets[:-1]) + self.b1
        return self.forward_from_accumulator(acc.view(-1, 2 * self.l1))


def prepare(inputs, workdir):
    workdir.mkdir(parents=True, exist_ok=True)
    boards_l, sides_l, values_l, games_l = [], [], [], []
    offset = 0
    fingerprint = []
    total = 0
    for path in inputs:
        path = Path(path)
        fingerprint.append([str(path), sha256_file(path)])
        b, s, v, g = nnue_features.read_selfplay(str(path))
        boards_l.append(b)
        sides_l.append(s)
        values_l.append(v)
        games_l.append(g + offset)
        offset += int(g.max()) + 1 if g.size else 0
        total += b.shape[0]
        print(f"  {path.name}: {b.shape[0]} positions ({offset} games so far)", flush=True)
    boards = np.concatenate(boards_l)
    side = np.concatenate(sides_l)
    value = np.concatenate(values_l)
    game = np.concatenate(games_l)
    game64 = game.astype(np.int64)
    bucket = (game64 * 2654435761) % 100
    split = np.where(bucket < 5, 2, np.where(bucket < 12, 1, 0)).astype(np.int8)
    np.save(workdir / "boards.npy", boards)
    np.save(workdir / "side.npy", side)
    np.save(workdir / "value.npy", value)
    np.save(workdir / "game.npy", game)
    np.save(workdir / "split.npy", split)
    manifest = {"inputs": fingerprint, "positions": int(total), "games": int(offset),
                "split": {str(k): int((split == k).sum()) for k in (0, 1, 2)}}
    (workdir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def batch_arrays(boards, side, rows, buckets):
    block = np.ascontiguousarray(boards[rows])
    flat, offsets = nnue_features.batch_indices(block, side[rows], buckets)
    return flat, offsets


# ---- quantisation (dev4 scheme, buckets-aware) ------------------------------

def powers_of_two_at_most(value, cap):
    if value < 1:
        return 1
    return 1 << min(int(np.floor(np.log2(value))), cap)


def measure_ranges(model, boards, sides, buckets, rows, percentile=99.9):
    w1 = model.embed.weight.detach().numpy().astype(np.float64)
    b1 = model.b1.detach().numpy().astype(np.float64)
    w2 = model.w2.detach().numpy().astype(np.float64)
    b2 = model.b2.detach().numpy().astype(np.float64)
    l1 = model.l1
    acts1, acts2 = [], []
    for begin in range(0, len(rows), 4096):
        chunk = rows[begin:begin + 4096]
        flat, offsets = batch_arrays(boards, sides, chunk, buckets)
        # manual accumulator build (vectorised over the batch)
        # features come in 2 bags per row
        n = len(chunk)
        feats = np.split(flat, offsets[1:-1]) if False else None
        # use embedding bag forward to get acc directly
        with torch.no_grad():
            acc = model.embed(torch.from_numpy(flat),
                              torch.from_numpy(offsets[:-1])).numpy() + b1
        acc = acc.reshape(n, 2, l1)
        a = np.clip(acc, 0.0, 1.0).reshape(n, 2 * l1)
        acts1.append(np.abs(acc))
        acts2.append(np.abs(a @ w2.T + b2))
    a1 = float(np.percentile(np.concatenate([x.ravel() for x in acts1]), percentile))
    a2 = float(np.percentile(np.concatenate([x.ravel() for x in acts2]), percentile))
    return max(a1, 1e-6), max(a2, 1e-6)


def quantize(model, output_scale, gain1, gain2, buckets):
    w1 = model.embed.weight.detach().numpy().astype(np.float64) * gain1
    b1 = model.b1.detach().numpy().astype(np.float64) * gain1
    w2 = model.w2.detach().numpy().astype(np.float64) * (gain2 / gain1)
    b2 = model.b2.detach().numpy().astype(np.float64) * gain2
    w3 = model.w3.detach().numpy().astype(np.float64) / gain2
    b3 = float(model.b3.detach().numpy()[0])
    l1, l2 = model.l1, model.l2
    headroom = 32000.0 / (32.0 * float(np.abs(w1).max()) + float(np.abs(b1).max()))
    s = int(np.floor(np.log2(headroom)))
    if s < 7:
        raise SystemExit(f"first-layer weights too large to quantise (s={s})")
    s = min(s, 13)
    q1 = 1 << s
    act_shift = s - 7
    q2 = powers_of_two_at_most(32767.0 / max(1e-12, float(np.abs(w2).max())), 14)
    h2_shift = int(np.log2(q2))
    limit = 32767.0 * 128.0 / (output_scale * max(1e-12, float(np.abs(w3).max())))
    out_shift = min(12, max(0, int(np.floor(np.log2(limit)))))
    out_gain = output_scale * (1 << out_shift) / 128.0
    net = {
        "kingBuckets": buckets, "l1": l1, "l2": l2,
        "actShift": act_shift, "h2Shift": h2_shift, "outShift": out_shift,
        "w1": np.rint(w1 * q1).astype(np.int16),
        "b1": np.rint(b1 * q1).astype(np.int32),
        "w2": np.rint(w2 * q2).astype(np.int16),
        "b2": np.rint(b2 * q2 * 128.0).astype(np.int32),
        "w3": np.rint(w3 * out_gain).astype(np.int16),
        "b3": int(np.rint(b3 * out_gain * 128.0)),
    }
    worst = 32 * int(np.abs(net["w1"]).max()) + int(np.abs(net["b1"]).max())
    if worst > 32000:
        raise SystemExit(f"quantised accumulator can overflow int16 ({worst})")
    return net


def serialize(net):
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


def integer_eval(net, boards, sides, buckets):
    l1 = net["l1"]
    out = np.zeros(boards.shape[0], dtype=np.int64)
    for row in range(boards.shape[0]):
        features = nnue_features.ordered_features(boards[row], int(sides[row]), buckets)
        acc = np.zeros((2, l1), dtype=np.int32)
        acc[0] = net["b1"]
        acc[1] = net["b1"]
        for p in (0, 1):
            acc[p] += net["w1"][features[p]].astype(np.int32).sum(axis=0)
        r1 = 1 << (net["actShift"] - 1) if net["actShift"] > 0 else 0
        act = np.clip((acc + r1) >> net["actShift"], 0, 127).reshape(-1).astype(np.int64)
        h2 = net["b2"] + net["w2"].astype(np.int64) @ act
        r2 = 1 << (net["h2Shift"] - 1) if net["h2Shift"] > 0 else 0
        hid = np.clip((h2 + r2) >> net["h2Shift"], 0, 127)
        out[row] = int(net["b3"] + net["w3"].astype(np.int64) @ hid)
    return out >> net["outShift"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", action="append", required=True)
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True, help="checkpoint prefix; .nnue written next to it")
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--buckets", type=int, default=1, choices=[1, 4, 16, 64])
    ap.add_argument("--l1", type=int, default=128)
    ap.add_argument("--l2", type=int, default=32)
    ap.add_argument("--target", choices=["cp", "wdl"], default="cp")
    ap.add_argument("--loss", choices=["auto", "bce", "mse"], default="auto",
                    help="auto: MSE on sigmoid output for wdl targets (dev4 objective), MSE on raw output for cp")
    ap.add_argument("--mix-cp", type=float, default=1.0)
    ap.add_argument("--mix-wdl", type=float, default=0.0)
    ap.add_argument("--k", type=float, default=400.0, help="cp->WDL scale for wdl targets")
    ap.add_argument("--cp-clip", type=float, default=1200.0)
    ap.add_argument("--batch", type=int, default=8192)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--lr-final", type=float, default=2e-5)
    ap.add_argument("--seed", type=int, default=20261102)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--weight-decay", type=float, default=0.0)
    ap.add_argument("--time-budget", type=float, default=0.0)
    ap.add_argument("--output-scale", type=float, default=OUTPUT_SCALE,
                    help="centipawns per raw network output unit in the quantised net; "
                         "with a wdl target t=sigmoid_log10(cp/K) the raw output is "
                         "ln(10)*cp/K, so output-scale K/ln(10) makes engine cp match teacher cp")
    ap.add_argument("--calibrate-positions", type=int, default=20000)
    args = ap.parse_args()

    torch.set_num_threads(args.threads)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    manifest = prepare(args.input, args.workdir)
    boards = np.load(args.workdir / "boards.npy", mmap_mode="r")
    side = np.load(args.workdir / "side.npy")
    value = np.load(args.workdir / "value.npy")
    split = np.load(args.workdir / "split.npy")
    tr = np.nonzero(split == 0)[0]
    va = np.nonzero(split == 1)[0]
    te = np.nonzero(split == 2)[0]
    print(f"train {tr.size} val {va.size} test {te.size}")

    features = args.buckets * 768
    model = Nnue(features, args.l1, args.l2)
    opt_sparse = torch.optim.SparseAdam([model.embed.weight], lr=args.lr)
    dense = [p for n, p in model.named_parameters() if n != "embed.weight"]
    opt_dense = torch.optim.Adam(dense, lr=args.lr, weight_decay=args.weight_decay)

    # targets
    def target_t(rows):
        v = value[rows].astype(np.float32)
        if args.target == "cp":
            return torch.from_numpy(np.clip(v, -args.cp_clip, args.cp_clip) / OUTPUT_SCALE)
        t = sigmoid_log10(v, args.k) if np.abs(v).max() > 1.5 else v
        return torch.from_numpy(t.astype(np.float32))

    def wdl_t(rows):
        v = value[rows]
        t = sigmoid_log10(v, args.k) if np.abs(v).max() > 1.5 else v
        return torch.from_numpy(t.astype(np.float32))

    steps_per_epoch = max(1, tr.size // args.batch)
    total_steps = steps_per_epoch * args.epochs
    rng = np.random.default_rng(args.seed)
    start = time.time()

    def lr_at(step):
        frac = min(1.0, step / max(1, total_steps))
        return args.lr_final + 0.5 * (args.lr - args.lr_final) * (1 + math.cos(math.pi * frac))

    def evaluate(rows, max_rows=100000):
        model.eval()
        rows = rows[:max_rows]
        losses, corrs = [], []
        with torch.no_grad():
            for begin in range(0, rows.size, args.batch):
                chunk = rows[begin:begin + args.batch]
                flat, offsets = batch_arrays(boards, side, chunk, args.buckets)
                out = model(torch.from_numpy(flat), torch.from_numpy(offsets)).reshape(-1)
                t = target_t(chunk)
                if args.target == "cp":
                    losses.append(float(((out - t) ** 2).mean()))
                    corrs.append(float(np.corrcoef(out.numpy() * OUTPUT_SCALE,
                                                   value[chunk].astype(np.float64))[0, 1]))
                else:
                    tt = wdl_t(chunk)
                    if args.loss == "bce":
                        p = torch.clamp(torch.sigmoid(out), 1e-7, 1 - 1e-7)
                        losses.append(float(-(tt * torch.log(p) + (1 - tt) * torch.log(1 - p)).mean()))
                    else:
                        p = torch.sigmoid(out)
                        losses.append(float(((p - tt) ** 2).mean()))
        model.train()
        return float(np.mean(losses)), (float(np.mean(corrs)) if corrs else float("nan"))

    best_val = float("inf")
    best_state = None
    best_epoch = -1
    history = []
    step = 0
    for epoch in range(args.epochs):
        if args.time_budget and time.time() - start > args.time_budget:
            print("time budget reached", flush=True)
            break
        order = rng.permutation(tr)
        running, count = 0.0, 0
        for begin in range(0, steps_per_epoch * args.batch, args.batch):
            if args.time_budget and time.time() - start > args.time_budget:
                break
            chunk = order[begin:begin + args.batch]
            lr = lr_at(step)
            for g in opt_sparse.param_groups:
                g["lr"] = lr
            for g in opt_dense.param_groups:
                g["lr"] = lr * 4.0
            flat, offsets = batch_arrays(boards, side, chunk, args.buckets)
            out = model(torch.from_numpy(flat), torch.from_numpy(offsets)).reshape(-1)
            loss = torch.zeros(())
            if args.target == "cp" or args.mix_cp > 0:
                t = target_t(chunk)
                loss = loss + args.mix_cp * ((out - t) ** 2).mean()
            if args.target == "wdl" or args.mix_wdl > 0:
                tt = wdl_t(chunk)
                if args.loss == "bce":
                    p = torch.clamp(torch.sigmoid(out), 1e-7, 1 - 1e-7)
                    loss = loss + args.mix_wdl * (-(tt * torch.log(p) + (1 - tt) * torch.log(1 - p)).mean())
                else:
                    p = torch.sigmoid(out)
                    loss = loss + args.mix_wdl * ((p - tt) ** 2).mean()
            opt_sparse.zero_grad(set_to_none=True)
            opt_dense.zero_grad(set_to_none=True)
            loss.backward()
            opt_sparse.step()
            opt_dense.step()
            running += float(loss.detach())
            count += 1
            step += 1
            if count % 50 == 0:
                print(f"epoch {epoch} step {step}/{total_steps} lr {lr:.2e} "
                      f"loss {running / count:.6f} ({time.time() - start:.0f}s)", flush=True)
        vl, corr = evaluate(va)
        history.append({"epoch": epoch, "train": running / max(1, count), "val": vl,
                        "val_cp_corr": corr})
        print(f"epoch {epoch}: train {running / max(1, count):.6f} val {vl:.6f} "
              f"cp_corr {corr:.4f} (best {best_val:.6f} @ {best_epoch})", flush=True)
        if vl < best_val:
            best_val, best_epoch = vl, epoch
            best_state = {n: t.detach().clone() for n, t in model.state_dict().items()}

    ckpt = {"state": best_state if best_state else model.state_dict(),
            "l1": args.l1, "l2": args.l2, "features": features,
            "buckets": args.buckets, "output_scale": OUTPUT_SCALE,
            "history": history, "best_epoch": best_epoch, "best_val": best_val,
            "args": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
            "corpus": manifest}
    args.out.with_suffix(".pt").parent.mkdir(parents=True, exist_ok=True)
    torch.save(ckpt, args.out.with_suffix(".pt"))
    print("wrote", args.out.with_suffix(".pt"))

    # quantise the best checkpoint
    model2 = Nnue(features, args.l1, args.l2)
    model2.load_state_dict(best_state if best_state else model.state_dict())
    model2.eval()
    cal_rows = tr[:args.calibrate_positions]
    r1, r2 = measure_ranges(model2, boards, side, args.buckets, cal_rows)
    print(f"calibration: ranges {r1:.4f}/{r2:.4f}")
    net = quantize(model2, args.output_scale, 1.0 / r1, 1.0 / r2, args.buckets)
    blob = serialize(net)
    nnue_path = args.out.with_suffix(".nnue")
    nnue_path.write_bytes(blob)
    print(f"wrote {nnue_path} ({len(blob)} bytes) sha256 {hashlib.sha256(blob).hexdigest()}")

    # verify: integer vs *calibrated* float (the gains are compensated in w2/w3,
    # so the calibrated float equals the trained float wherever the clip is
    # inactive; saturation differences are intended, as in dev4) on a held-out slice
    ver_rows = te[:5000]
    with torch.no_grad():
        # calibrated float forward: acc scaled by gain1, w2 by gain2/gain1, w3 by 1/gain2
        fl, off = batch_arrays(boards, side, ver_rows, args.buckets)
        g1, g2 = 1.0 / r1, 1.0 / r2
        acc = model2.embed(torch.from_numpy(fl), torch.from_numpy(off[:-1])) + model2.b1
        a = torch.clamp(acc.view(-1, 2 * model2.l1) * g1, 0.0, 1.0)
        h = torch.clamp(a @ (model2.w2.t() * (g2 / g1)) + model2.b2 * g2, 0.0, 1.0)
        fout = (h @ (model2.w3 * (1.0 / g2)) + model2.b3[0] / g2).numpy() * args.output_scale
    inte = integer_eval(net, np.ascontiguousarray(boards[ver_rows]), side[ver_rows], args.buckets)
    diff = inte.astype(np.float64) - fout
    vcp = value[ver_rows].astype(np.float64)
    report = {
        "buckets": args.buckets, "l1": args.l1, "l2": args.l2, "target": args.target,
        "output_scale": args.output_scale,
        "mix_cp": args.mix_cp, "mix_wdl": args.mix_wdl, "k": args.k,
        "seed": args.seed, "epochs": args.epochs, "best_epoch": best_epoch,
        "best_val": best_val, "history": history, "corpus": manifest,
        "nnue_sha256": hashlib.sha256(blob).hexdigest(), "nnue_bytes": len(blob),
        "quant": {"actShift": net["actShift"], "h2Shift": net["h2Shift"],
                  "outShift": net["outShift"], "range1": r1, "range2": r2},
        "verify": {
            "positions": int(len(ver_rows)),
            "int_vs_float_max_cp": float(np.abs(diff).max()),
            "int_vs_float_mean_cp": float(diff.mean()),
            "int_vs_float_rms_cp": float(np.sqrt((diff ** 2).mean())),
            "int_vs_teacher_corr": float(np.corrcoef(inte.astype(np.float64), vcp)[0, 1]),
            "int_vs_teacher_rms_cp": float(np.sqrt(((inte.astype(np.float64) - vcp) ** 2).mean())),
            "float_vs_teacher_corr": float(np.corrcoef(fout, vcp)[0, 1]),
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2))
    print(json.dumps(report["verify"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
