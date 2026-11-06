#!/usr/bin/env python3
"""exp-0048: fit a full per-square piece-square table to the frozen corpus.

Every hyperparameter here is frozen in docs/DEV6_PREREG_EXP0048.md §8 and was
written before the corpus existed. This script performs ONE fit and writes ONE
table; there is no sweep, no selection and no post-screen retuning.

Pipeline
--------
1. Read the combined corpus (MANIFEST.json + corpus.epd.gz + records).
2. Split BY GAME with the frozen seed; the optimiser never sees holdout rows.
3. Ask the engine itself for the champion design matrix (`stockbear evaldata`),
   so the non-PST part of the score is the engine's own integer arithmetic.
4. Verify two identities on EVERY row before fitting:
     a) the champion counts reproduce the engine's `score` column exactly;
     b) the formulaic PST rebuilt in Python reproduces the champion's PST term
        exactly, so the initial candidate is bit-identical to the champion.
   Either failure aborts: a silently wrong design matrix is the classic way to
   "improve" an evaluator that was never actually measured.
5. Full-batch Adam on the training rows only.
6. Report held-out log-loss / Brier for champion and candidate, and write the
   SBPST1 table plus a JSON report with every hash.

Usage:
  python3 scripts/dev6_exp0048_fit.py --corpus DIR --engine ./build-rel/stockbear \
      --params research-data/params_abc.txt --out DIR
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import random
import subprocess
from pathlib import Path

import chess
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PIECES = (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING)
PST_NAMES = ("PstPawnRank", "PstPawnFile", "PstKnightCenter", "PstBishopCenter",
             "PstRookRank", "PstRookFile", "PstRookCenter", "PstQueenCenter",
             "PstKingRank", "PstKingFile", "PstKingCenter")
# Frozen hyperparameters (prereg §8).
ITERATIONS = 300
LEARNING_RATE = 5.0
BETA1, BETA2, EPS = 0.9, 0.999, 1e-8
L2 = 1e-5
HOLDOUT_FRACTION = 0.2
HOLDOUT_SEED = 2026110602
ENTRY_LIMIT = 2000
KNOWN_WIN = 10000
K = math.log(10.0) / 400.0  # p = sigmoid(K * s) == 1/(1+10^(-s/400))


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_params(path: Path) -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        name, mg, eg = line.split()
        out[name] = (int(mg), int(eg))
    return out


def formulaic_tables(params: dict[str, tuple[int, int]]) -> tuple[np.ndarray, np.ndarray]:
    """Rebuild src/evaluation/evaluation.cpp::build_tables() in Python."""
    mg = np.zeros((6, 64), dtype=np.int64)
    eg = np.zeros((6, 64), dtype=np.int64)
    for idx in range(64):
        f = idx % 8
        rank = 7 - idx // 8          # table is rank-8-first, White's view
        file_center = min(f, 7 - f)
        center = file_center + min(rank, 7 - rank)
        p = params
        mg[0, idx] = rank * p["PstPawnRank"][0] + file_center * p["PstPawnFile"][0]
        eg[0, idx] = rank * p["PstPawnRank"][1] + file_center * p["PstPawnFile"][1]
        mg[1, idx] = center * p["PstKnightCenter"][0]
        eg[1, idx] = center * p["PstKnightCenter"][1]
        mg[2, idx] = center * p["PstBishopCenter"][0]
        eg[2, idx] = center * p["PstBishopCenter"][1]
        mg[3, idx] = rank * p["PstRookRank"][0] + file_center * p["PstRookFile"][0]
        eg[3, idx] = center * p["PstRookCenter"][1]
        mg[4, idx] = center * p["PstQueenCenter"][0]
        eg[4, idx] = center * p["PstQueenCenter"][1]
        mg[5, idx] = rank * p["PstKingRank"][0] + file_center * p["PstKingFile"][0]
        eg[5, idx] = center * p["PstKingCenter"][1]
    return mg, eg


def trunc_div24(num: np.ndarray) -> np.ndarray:
    """C++ integer `/ 24` truncates toward zero; Python `//` floors."""
    return np.sign(num) * (np.abs(num) // 24)


def taper(mg: np.ndarray, eg: np.ndarray, phase: np.ndarray) -> np.ndarray:
    return np.clip(trunc_div24(mg * phase + eg * (24 - phase)), -KNOWN_WIN, KNOWN_WIN)


def logloss10(score: np.ndarray, target: np.ndarray) -> float:
    z = np.clip(K * score, -700, 700)
    p = 1.0 / (1.0 + np.exp(-z))
    p = np.clip(p, 1e-15, 1 - 1e-15)
    return float(-np.mean(target * np.log10(p) + (1 - target) * np.log10(1 - p)))


def brier(score: np.ndarray, target: np.ndarray) -> float:
    p = 1.0 / (1.0 + np.exp(-np.clip(K * score, -700, 700)))
    return float(np.mean((p - target) ** 2))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, help="directory produced by dev6_corpus_combine.py")
    ap.add_argument("--engine", required=True)
    ap.add_argument("--params", default="research-data/params_abc.txt")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    corpus, out = Path(a.corpus), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((corpus / "MANIFEST.json").read_text())
    for name, info in manifest["files"].items():
        assert sha(corpus / name) == info["gz_sha256"], f"corpus file changed: {name}"
    with gzip.open(corpus / "corpus.epd.gz", "rt") as g:
        fens = g.read().splitlines()
    with gzip.open(corpus / "corpus.records.json.gz", "rt") as g:
        records = json.load(g)
    assert len(fens) == len(records) == manifest["positions"]
    params_path = ROOT / a.params if not Path(a.params).is_absolute() else Path(a.params)
    params = read_params(params_path)
    print(f"corpus: {manifest['games']} games, {len(fens)} positions, "
          f"source {manifest['source_sha'][:12]}")

    # ---- frozen by-game split ---------------------------------------------
    games = sorted({r["game"] for r in records})
    shuffled = list(games)
    random.Random(HOLDOUT_SEED).shuffle(shuffled)
    n_holdout = math.ceil(HOLDOUT_FRACTION * len(games))
    holdout_games = set(shuffled[:n_holdout])
    is_holdout = np.array([r["game"] in holdout_games for r in records])
    target = np.array([r["target"] for r in records], dtype=np.float64)
    print(f"split: {len(games)} games -> {len(games) - n_holdout} train / "
          f"{n_holdout} holdout; rows {int((~is_holdout).sum())} train / "
          f"{int(is_holdout.sum())} holdout")
    assert n_holdout > 0 and (~is_holdout).any()

    # ---- champion design matrix from the engine itself ---------------------
    work = out / "work"
    work.mkdir(exist_ok=True)
    all_epd = work / "all.epd"
    all_epd.write_text("\n".join(fens) + "\n")
    design = work / "design.csv"
    cmd = [str(Path(a.engine).resolve()), "evaldata", "--input", str(all_epd),
           "--params", str(params_path), "--output", str(design)]
    print("+ " + " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, f"evaldata failed: {r.stderr[-2000:]}"
    lines = design.read_text().splitlines()
    assert lines[0].startswith("# stockbear evaldata")
    header = lines[1].split(",")
    rows = [l.split(",") for l in lines[2:] if l]
    assert len(rows) == len(fens), f"design rows {len(rows)} != {len(fens)}"
    assert header[0] == "fen" and header[1] == "phase" and header[-1] == "score"
    n_par = (len(header) - 3) // 2
    names = [h[3:] for h in header[2:2 + n_par]]
    assert [h[3:] for h in header[2 + n_par:-1]] == names
    counts_mg = np.array([[int(v) for v in row[2:2 + n_par]] for row in rows], dtype=np.int64)
    counts_eg = np.array([[int(v) for v in row[2 + n_par:-1]] for row in rows], dtype=np.int64)
    phase = np.array([int(row[1]) for row in rows], dtype=np.int64)
    engine_score = np.array([int(row[-1]) for row in rows], dtype=np.int64)
    assert np.array_equal(phase, np.clip(phase, 0, 24))
    par_mg = np.array([params.get(n, (0, 0))[0] for n in names], dtype=np.int64)
    par_eg = np.array([params.get(n, (0, 0))[1] for n in names], dtype=np.int64)
    pst_mask = np.array([n in PST_NAMES for n in names])
    assert pst_mask.sum() == len(PST_NAMES)

    stm_white = np.array([f.split()[1] == "w" for f in fens])
    sign = np.where(stm_white, 1, -1).astype(np.int64)
    total_mg = counts_mg @ par_mg
    total_eg = counts_eg @ par_eg
    nonpst_mg = counts_mg @ np.where(pst_mask, 0, par_mg)
    nonpst_eg = counts_eg @ np.where(pst_mask, 0, par_eg)
    champion_recomputed = sign * taper(total_mg, total_eg, phase)
    bad = int(np.count_nonzero(champion_recomputed != engine_score))
    assert bad == 0, f"champion design matrix does not reproduce evaluate(): {bad} rows"
    print(f"identity (a): champion counts reproduce evaluate() on all {len(fens)} rows")

    # ---- sparse PST design -------------------------------------------------
    init_mg, init_eg = formulaic_tables(params)
    row_idx, col_idx, val = [], [], []
    for i, fen in enumerate(fens):
        board = chess.Board(fen)
        for sq, piece in board.piece_map().items():
            pt = PIECES.index(piece.piece_type)
            idx = (sq ^ 56) if piece.color == chess.WHITE else sq
            row_idx.append(i)
            col_idx.append(pt * 64 + idx)
            val.append(1 if piece.color == chess.WHITE else -1)
    row_idx = np.array(row_idx, dtype=np.int64)
    col_idx = np.array(col_idx, dtype=np.int64)
    val = np.array(val, dtype=np.float64)
    n_rows, n_feat = len(fens), 384

    def matvec(theta: np.ndarray) -> np.ndarray:
        return np.bincount(row_idx, weights=val * theta[col_idx], minlength=n_rows)

    pst_mg = np.rint(matvec(init_mg.reshape(-1))).astype(np.int64)
    pst_eg = np.rint(matvec(init_eg.reshape(-1))).astype(np.int64)
    bad_mg = int(np.count_nonzero(pst_mg != total_mg - nonpst_mg))
    bad_eg = int(np.count_nonzero(pst_eg != total_eg - nonpst_eg))
    assert bad_mg == 0 and bad_eg == 0, f"formulaic PST rebuild mismatch: mg {bad_mg}, eg {bad_eg}"
    print(f"identity (b): Python formulaic PST == engine PST term on all {len(fens)} rows")

    # ---- fit on training rows only ----------------------------------------
    tr = np.flatnonzero(~is_holdout)
    tr_row_mask = (~is_holdout)[row_idx]
    tr_rows, tr_cols, tr_vals = row_idx[tr_row_mask], col_idx[tr_row_mask], val[tr_row_mask]
    # Local (training) row numbering for the sparse scatter.
    local = np.full(n_rows, -1, dtype=np.int64)
    local[tr] = np.arange(len(tr))
    tr_local = local[tr_rows]
    n_tr = len(tr)
    ph_tr = phase[tr].astype(np.float64)
    w_mg, w_eg = ph_tr / 24.0, (24.0 - ph_tr) / 24.0
    sgn_tr = sign[tr].astype(np.float64)
    base_mg = nonpst_mg[tr].astype(np.float64)
    base_eg = nonpst_eg[tr].astype(np.float64)
    y = target[tr]

    theta = np.concatenate([init_mg.reshape(-1), init_eg.reshape(-1)]).astype(np.float64)
    theta0 = theta.copy()
    m = np.zeros_like(theta)
    v = np.zeros_like(theta)
    clamp_rows = 0
    for it in range(1, ITERATIONS + 1):
        pm = np.bincount(tr_local, weights=tr_vals * theta[:n_feat][tr_cols], minlength=n_tr)
        pe = np.bincount(tr_local, weights=tr_vals * theta[n_feat:][tr_cols], minlength=n_tr)
        mg = base_mg + pm
        eg = base_eg + pe
        raw = sgn_tr * (mg * w_mg + eg * w_eg)
        clamped = np.abs(raw) > KNOWN_WIN
        clamp_rows = max(clamp_rows, int(clamped.sum()))
        s = np.clip(raw, -KNOWN_WIN, KNOWN_WIN)
        p = 1.0 / (1.0 + np.exp(-np.clip(K * s, -700, 700)))
        # d(mean natural-log loss)/ds = K*(p - y)/n; the clamp kills the tail.
        g_s = K * (p - y) / n_tr * (~clamped)
        g_m = g_s * sgn_tr * w_mg
        g_e = g_s * sgn_tr * w_eg
        grad = np.empty_like(theta)
        grad[:n_feat] = np.bincount(tr_cols, weights=tr_vals * g_m[tr_local], minlength=n_feat)
        grad[n_feat:] = np.bincount(tr_cols, weights=tr_vals * g_e[tr_local], minlength=n_feat)
        delta = theta - theta0
        grad += 2.0 * L2 * delta
        m = BETA1 * m + (1 - BETA1) * grad
        v = BETA2 * v + (1 - BETA2) * grad * grad
        mhat = m / (1 - BETA1 ** it)
        vhat = v / (1 - BETA2 ** it)
        theta -= LEARNING_RATE * mhat / (np.sqrt(vhat) + EPS)
        if it % 50 == 0 or it == 1:
            loss = float(np.mean(np.logaddexp(0.0, K * s) - y * K * s))
            pen = L2 * float(np.sum(delta * delta))
            print(f"iter {it:3d}  train_ln_loss {loss:.6f}  l2 {pen:.6f}  "
                  f"max|delta| {np.max(np.abs(delta)):.2f}", flush=True)

    # ---- final table: round half away from zero, clip ----------------------
    delta = theta - theta0
    rounded = np.sign(theta) * np.floor(np.abs(theta) + 0.5)
    final = np.clip(rounded, -ENTRY_LIMIT, ENTRY_LIMIT).astype(np.int64)
    clipped = int(np.count_nonzero(rounded != final))
    final_mg, final_eg = final[:n_feat].reshape(6, 64), final[n_feat:].reshape(6, 64)

    def candidate_score(mg_tab: np.ndarray, eg_tab: np.ndarray) -> np.ndarray:
        cm = nonpst_mg + np.rint(matvec(mg_tab.reshape(-1))).astype(np.int64)
        ce = nonpst_eg + np.rint(matvec(eg_tab.reshape(-1))).astype(np.int64)
        return sign * taper(cm, ce, phase)

    cand = candidate_score(final_mg, final_eg)
    init_score = candidate_score(init_mg, init_eg)
    assert np.array_equal(init_score, engine_score), "initialised candidate != champion"

    ho = is_holdout
    metrics = {
        "holdout_rows": int(ho.sum()), "train_rows": int((~ho).sum()),
        "holdout_games": n_holdout, "train_games": len(games) - n_holdout,
        "L_champ": logloss10(engine_score[ho], target[ho]),
        "L_cand": logloss10(cand[ho], target[ho]),
        "B_champ": brier(engine_score[ho], target[ho]),
        "B_cand": brier(cand[ho], target[ho]),
        "L_champ_train": logloss10(engine_score[~ho], target[~ho]),
        "L_cand_train": logloss10(cand[~ho], target[~ho]),
    }
    metrics["relative_logloss_reduction"] = 1.0 - metrics["L_cand"] / metrics["L_champ"]
    metrics["accuracy_threshold_met"] = bool(
        metrics["L_cand"] <= 0.97 * metrics["L_champ"] and metrics["B_cand"] <= metrics["B_champ"])

    pst_path = out / "exp0048.sbpst"
    body = ["SBPST1"]
    for pt in range(6):
        for idx in range(64):
            body.append(f"{int(final_mg[pt, idx])} {int(final_eg[pt, idx])}")
    pst_path.write_text("\n".join(body) + "\n")

    # ---- identity (c): the ENGINE agrees with the fitted table --------------
    # Without this the reported holdout metric would describe a Python model,
    # not the evaluator that will actually play. Re-run evaldata with --pst on
    # every corpus position and require exact agreement on all rows.
    pst_design = work / "design_pst.csv"
    cmd = [str(Path(a.engine).resolve()), "evaldata", "--input", str(all_epd),
           "--params", str(params_path), "--pst", str(pst_path), "--output", str(pst_design)]
    print("+ " + " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, f"evaldata --pst failed: {r.stderr[-2000:]}"
    pst_lines = pst_design.read_text().splitlines()
    assert "pst_file" in pst_lines[0], "engine did not report the PST override as active"
    engine_cand = np.array([int(l.rsplit(",", 1)[1]) for l in pst_lines[2:] if l], dtype=np.int64)
    assert len(engine_cand) == len(cand)
    bad_cand = int(np.count_nonzero(engine_cand != cand))
    assert bad_cand == 0, f"engine PST evaluation disagrees with the fitted model on {bad_cand} rows"
    print(f"identity (c): engine with PstFile == fitted model on all {len(fens)} rows")

    report = {
        "experiment_id": "exp0048",
        "corpus_manifest_sha256": sha(corpus / "MANIFEST.json"),
        "corpus_source_sha": manifest["source_sha"],
        "corpus_games": manifest["games"], "corpus_positions": manifest["positions"],
        "params_file": str(Path(a.params)), "params_sha256": sha(params_path),
        "engine_sha256": sha(Path(a.engine)),
        "prereg_sha256": sha(ROOT / "docs/DEV6_PREREG_EXP0048.md"),
        "hyperparameters": {"iterations": ITERATIONS, "learning_rate": LEARNING_RATE,
                            "beta1": BETA1, "beta2": BETA2, "eps": EPS, "l2": L2,
                            "init": "champion formulaic tables", "batch": "full"},
        "split": {"by": "game", "seed": HOLDOUT_SEED, "holdout_fraction": HOLDOUT_FRACTION},
        "identity_checks": {"champion_counts_reproduce_evaluate": True,
                            "formulaic_pst_rebuild_exact": True,
                            "initialised_candidate_equals_champion": True,
                            "engine_with_pst_equals_fitted_model": True},
        "max_clamped_training_rows": clamp_rows, "entries_clipped_to_limit": clipped,
        "delta_abs_max": float(np.max(np.abs(delta))),
        "delta_rms": float(np.sqrt(np.mean(delta * delta))),
        "metrics": metrics,
        "pst_file": pst_path.name, "pst_sha256": sha(pst_path),
    }
    (out / "FIT_REPORT.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "SHA256SUMS.txt").write_text(
        "\n".join(f"{sha(p)}  {p.name}" for p in sorted(out.iterdir())
                  if p.is_file() and p.name != "SHA256SUMS.txt") + "\n")
    print(json.dumps(metrics, indent=2))
    print(f"accuracy threshold met: {metrics['accuracy_threshold_met']}")
    print(f"wrote {pst_path} sha256 {report['pst_sha256']}")


if __name__ == "__main__":
    main()
