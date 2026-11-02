#!/usr/bin/env python3
"""Train StockBear's neural evaluation from a self-play corpus.

Pipeline (docs/DEV4_TRAINING.md):

1. ``prepare``  - parse every ``<result> <game> <fen>`` corpus file into a
   compact ``uint8[N, 64]`` board array. Features are derived from that array at
   training time with ``scripts/nnue_features.py``, which is a mirror of the
   engine's C++ feature function and is differentially tested against it.
2. ``train``    - three-layer network, ``2*768 -> L1 -> L2 -> 1``, trained on the
   game result from the side to move's point of view. Splits are made **by
   game**, never by position: two positions from one game share a result and
   would otherwise leak between training and validation.
3. ``convert``  - quantise to the integer format the engine loads and verify the
   quantised evaluation against the float network.

Reproducibility: the corpus is identified by the SHA-256 of every input file,
the split is a deterministic function of the game id, and the seed, batch size,
learning-rate schedule and architecture are written into the checkpoint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nnue_features  # noqa: E402

# The engine interprets one unit of the network output as OUTPUT_SCALE
# centipawns (see convert_nnue.py). Keeping the far end of the pipeline fixed
# here means a trained checkpoint is immediately comparable with the classical
# evaluation's scale.
OUTPUT_SCALE = 300.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare(inputs, workdir: Path, limit_per_file=None):
    """Parses the corpus files into workdir/boards.npy (+ side/result/game)."""
    workdir.mkdir(parents=True, exist_ok=True)
    manifest_path = workdir / "manifest.json"
    fingerprint = {"inputs": [(str(p), sha256_file(Path(p))) for p in inputs]}
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        if old.get("inputs") == [list(x) for x in fingerprint["inputs"]]:
            print(f"reusing prepared corpus in {workdir}")
            return json.loads((workdir / "manifest.json").read_text())
        print("corpus changed; re-preparing")

    boards, sides, results, games = [], [], [], []
    game_offset = 0
    total = 0
    for path in inputs:
        path = Path(path)
        board, side, result, game = nnue_features.read_selfplay(str(path), limit_per_file)
        boards.append(board)
        sides.append(side)
        results.append(result)
        games.append(game + game_offset)
        game_offset += int(game.max()) + 1 if game.size else 0
        total += board.shape[0]
        print(f"  {path.name}: {board.shape[0]} positions, {game_offset} games so far")
    board = np.concatenate(boards)
    side = np.concatenate(sides)
    result = np.concatenate(results)
    game = np.concatenate(games)
    np.save(workdir / "boards.npy", board)
    np.save(workdir / "side.npy", side)
    np.save(workdir / "result.npy", result)
    np.save(workdir / "game.npy", game)

    # Deterministic game-level split. Games are numbered per input file, so the
    # split is stable when a corpus is extended by a later generation run.
    game64 = game.astype(np.int64)
    bucket = (game64 * 2654435761) % 100
    split = np.where(bucket < 5, 2, np.where(bucket < 12, 1, 0)).astype(np.int8)  # 2=test
    np.save(workdir / "split.npy", split)
    manifest = {
        "inputs": [list(x) for x in fingerprint["inputs"]],
        "positions": int(board.shape[0]),
        "games": int(game.max()) + 1 if game.size else 0,
        "split_positions": {str(k): int((split == k).sum()) for k in (0, 1, 2)},
        "duplicate_positions": int(board.shape[0] - np.unique(board, axis=0).shape[0]),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    return manifest


class Nnue(nn.Module):
    def __init__(self, features: int, l1: int, l2: int):
        super().__init__()
        self.features = features
        self.l1 = l1
        self.l2 = l2
        # Sparse first layer: the gradient touches only the rows of active
        # features, which is what makes a 768-row embedding trainable on CPU.
        self.embed = nn.EmbeddingBag(features, l1, mode="sum", sparse=True)
        self.b1 = nn.Parameter(torch.zeros(l1))
        self.w2 = nn.Parameter(torch.empty(l2, 2 * l1))
        self.b2 = nn.Parameter(torch.zeros(l2))
        self.w3 = nn.Parameter(torch.empty(l2))
        self.b3 = nn.Parameter(torch.zeros(1))
        # Initialisation matters here more than usual: the first layer is a sum of
        # ~35 sparse rows, so its scale decides whether the clipped ReLUs see a
        # signal at all. Too small and every pre-activation sits at the bottom of
        # the clip, the network output is constant, and the loss never moves.
        #
        #   * w1 standard deviation s gives an accumulator standard deviation of
        #     about sqrt(35)*s, so s = 0.3 puts the pre-activation near 1.
        #   * the clipped ReLU then has mean m and the layer-2 pre-activation has
        #     a random per-unit offset m * sum_i w2[j][i]; b2 cancels it at
        #     initialisation so no unit starts dead.
        self.embed.weight.data.uniform_(-0.55, 0.55)
        bound2 = 0.15
        nn.init.uniform_(self.w2, -bound2, bound2)
        activation_mean = 0.32
        self.b2.data.copy_(-activation_mean * self.w2.data.sum(dim=1))
        nn.init.uniform_(self.w3, -1.0 / math.sqrt(l2), 1.0 / math.sqrt(l2))

    def forward_from_accumulator(self, acc: torch.Tensor) -> torch.Tensor:
        a = torch.clamp(acc, 0.0, 1.0)
        hidden = torch.clamp(a @ self.w2.t() + self.b2, 0.0, 1.0)
        return hidden @ self.w3 + self.b3

    def forward(self, flat, offsets):
        # `offsets` has 2*B + 1 entries; EmbeddingBag wants one entry per bag and
        # lets the final bag run to the end of `flat`.
        acc = self.embed(flat, offsets[:-1]) + self.b1
        acc = acc.view(-1, 2 * self.l1)
        return self.forward_from_accumulator(acc)


def load_split(workdir: Path):
    boards = np.load(workdir / "boards.npy", mmap_mode="r")
    side = np.load(workdir / "side.npy")
    result = np.load(workdir / "result.npy")
    split = np.load(workdir / "split.npy")
    return boards, side, result, split


def batch_arrays(boards, side, rows):
    """boards: mmap uint8[N,64]; rows: array of indices -> (flat, offsets).

    The side to move travels with the row: the feature bags are emitted side-to-
    move first (see `nnue_features.ordered_features`), which is the only ordering
    that makes the training target a function of the input.
    """
    block = np.ascontiguousarray(boards[rows])
    flat, offsets = nnue_features.batch_indices(block, side[rows])
    return flat, offsets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", default=[], help="self-play corpus file")
    parser.add_argument("--workdir", type=Path, default=Path("nnue-work"))
    parser.add_argument("--out", type=Path, required=True, help="checkpoint prefix")
    parser.add_argument("--l1", type=int, default=128)
    parser.add_argument("--l2", type=int, default=32)
    parser.add_argument("--batch", type=int, default=8192)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--lr-final", type=float, default=2e-5)
    parser.add_argument("--seed", type=int, default=20261101)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--limit-per-file", type=int, default=None)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--time-budget", type=float, default=0.0,
                        help="stop after this many seconds (checkpoint is still written)")
    args = parser.parse_args()

    torch.set_num_threads(args.threads)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    # The checkpoint path's parent may not exist yet; creating it here keeps a
    # long run from dying at the first epoch boundary after all the work is done.
    args.out.with_suffix(".pt").parent.mkdir(parents=True, exist_ok=True)
    manifest = prepare(args.input, args.workdir, args.limit_per_file)
    if args.prepare_only:
        return 0

    boards, side, result, split = load_split(args.workdir)
    train_rows = np.nonzero(split == 0)[0]
    val_rows = np.nonzero(split == 1)[0]
    print(f"train {train_rows.size} / val {val_rows.size} positions")

    model = Nnue(768, args.l1, args.l2)
    sparse_params = [model.embed.weight]
    dense_params = [p for n, p in model.named_parameters() if n != "embed.weight"]
    opt_sparse = torch.optim.SparseAdam(sparse_params, lr=args.lr)
    opt_dense = torch.optim.Adam(dense_params, lr=args.lr)

    steps_per_epoch = max(1, train_rows.size // args.batch)
    total_steps = steps_per_epoch * args.epochs
    rng = np.random.default_rng(args.seed)
    start = time.time()
    history = []

    def lr_at(step: int) -> float:
        frac = min(1.0, step / max(1, total_steps))
        # cosine decay from --lr to --lr-final
        return args.lr_final + 0.5 * (args.lr - args.lr_final) * (1 + math.cos(math.pi * frac))

    def evaluate(rows, max_rows=200000):
        model.eval()
        rows = rows[:max_rows]
        losses = []
        with torch.no_grad():
            for begin in range(0, rows.size, args.batch):
                chunk = rows[begin : begin + args.batch]
                flat, offsets = batch_arrays(boards, side, chunk)
                p = torch.sigmoid(model(torch.from_numpy(flat), torch.from_numpy(offsets)))
                target = torch.from_numpy(result[chunk].astype(np.float32))
                losses.append(float(((p - target) ** 2).mean()))
        model.train()
        return float(np.mean(losses))

    step = 0
    # A small network on a few million positions overfits long before it runs out
    # of steps, and the overfit epoch is the one that plays *worse*: the exported
    # network must therefore be the best-validation checkpoint, not the last.
    best_val = float("inf")
    best_epoch = -1
    best_state = None
    for epoch in range(args.epochs):
        order = rng.permutation(train_rows)
        running = 0.0
        count = 0
        for begin in range(0, steps_per_epoch * args.batch, args.batch):
            if args.time_budget and time.time() - start > args.time_budget:
                print("time budget reached")
                break
            chunk = order[begin : begin + args.batch]
            lr = lr_at(step)
            for group in opt_sparse.param_groups:
                group["lr"] = lr
            for group in opt_dense.param_groups:
                group["lr"] = lr * 4.0
            flat, offsets = batch_arrays(boards, side, chunk)
            flat_t = torch.from_numpy(flat)
            off_t = torch.from_numpy(offsets)
            target = torch.from_numpy(result[chunk].astype(np.float32))
            opt_sparse.zero_grad(set_to_none=True)
            opt_dense.zero_grad(set_to_none=True)
            p = torch.sigmoid(model(flat_t, off_t))
            loss = ((p - target) ** 2).mean()
            loss.backward()
            opt_sparse.step()
            opt_dense.step()
            running += float(loss.detach())
            count += 1
            step += 1
            if count % 50 == 0:
                print(f"epoch {epoch} step {step}/{total_steps} lr {lr:.2e} "
                      f"loss {running / count:.6f} ({time.time() - start:.0f}s)", flush=True)
        val = evaluate(val_rows)
        train_loss = running / max(1, count)
        history.append({"epoch": epoch, "train": train_loss, "val": val, "lr": lr_at(step)})
        if val < best_val:
            best_val, best_epoch = val, epoch
            best_state = {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
        print(f"epoch {epoch}: train {train_loss:.6f} val {val:.6f} "
              f"(best {best_val:.6f} @ epoch {best_epoch})", flush=True)
        checkpoint = args.out.with_suffix(".pt")
        torch.save({
            "state": model.state_dict(),
            "l1": args.l1,
            "l2": args.l2,
            "features": 768,
            "output_scale": OUTPUT_SCALE,
            "history": history,
            "args": vars(args) | {"out": str(args.out), "workdir": str(args.workdir)},
            "corpus": manifest,
        }, checkpoint)
    print("wrote", args.out.with_suffix(".pt"))
    if best_state is not None:
        best_path = args.out.with_suffix(".best.pt")
        torch.save({
            "state": best_state,
            "l1": args.l1,
            "l2": args.l2,
            "features": 768,
            "output_scale": OUTPUT_SCALE,
            "history": history,
            "best_epoch": best_epoch,
            "best_val": best_val,
            "args": vars(args) | {"out": str(args.out), "workdir": str(args.workdir)},
            "corpus": manifest,
        }, best_path)
        print(f"wrote {best_path} (epoch {best_epoch}, val {best_val:.6f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
