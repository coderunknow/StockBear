#!/usr/bin/env python3
"""Does eval accuracy predict fixed-time Elo in this project? An anchor check.

exp-0047 §3.3 requires a pre-result argument that a candidate's accuracy gain is
compatible with >= +75 Elo, citing "historical NPS->Elo and accuracy->Elo
evidence" in the failure ledger. This script audits whether that evidence
actually exists, using the ONE pair in the project with a precisely measured
fixed-time Elo: dev4 -> dev5, +64.7 [+57.5, +72.0] over 6,600 games (exp-0024,
run 41620641753, clustered CR1 t(1745)).

Both binaries are immutable and committed, so their evaluators can be scored on
identical positions with identical labels at ZERO cost in strength games.

CAVEATS, stated up front because they bound every conclusion:
  * The +64.7 is a BUNDLE (portable build flags + params_abc + TTEval), not an
    eval-only delta. It cannot be attributed to evaluation accuracy alone.
  * Labels come from dev5-vs-dev5 self-play, so the position distribution and
    outcomes are dev5's own. Any such bias would FAVOUR dev5.
  * params_abc was tuned at K=600 with natural-log loss; the frozen exp-0048/49
    metric is log10 at K=400. K-sensitivity is therefore reported, not assumed.
  * This is an AUDIT of existing evidence, not a new strength measurement. It
    activates nothing and reopens nothing.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import match_stats as ms  # noqa: E402


def sha(p: Path) -> str:
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def extract(engine: Path, epd: Path, out: Path, params: Path | None) -> np.ndarray:
    cmd = [str(engine), "evaldata", "--input", str(epd), "--output", str(out)]
    if params:
        cmd += ["--params", str(params)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, f"evaldata failed: {r.stderr[-800:]}"
    lines = out.read_text().splitlines()
    hdr = next(l for l in lines if l.startswith("fen,"))
    body = [l for l in lines if not l.startswith("#") and not l.startswith("fen,")]
    rows = list(csv.DictReader([hdr] + body))
    return np.array([int(x["score"]) for x in rows], dtype=np.float64)


def clustered_paired(diff: np.ndarray, codes: np.ndarray, n_clusters: int) -> dict:
    """CR1 clustered SE of the mean paired difference, clustered by game."""
    n = len(diff)
    mean = float(diff.mean())
    resid = np.bincount(codes, weights=diff) - np.bincount(codes) * mean
    var = (n_clusters / (n_clusters - 1.0)) * float(resid @ resid) / (n * n)
    se = math.sqrt(var)
    t = ms._t95(n_clusters - 1)
    return {"mean": mean, "se": se, "t_stat": mean / se if se else None,
            "ci95": [mean - t * se, mean + t * se],
            "distinguishable_from_zero": bool(se and abs(mean / se) >= t)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--stride", type=int, default=40)
    ap.add_argument("--max-positions", type=int, default=6000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    corpus = Path(a.corpus)

    with gzip.open(corpus / "corpus.epd.gz", "rt") as g:
        fens = g.read().splitlines()
    with gzip.open(corpus / "corpus.records.json.gz", "rt") as g:
        recs = json.load(g)
    assert len(fens) == len(recs)
    # Score-independent, outcome-independent deterministic subsample.
    idx = list(range(0, len(fens), a.stride))[:a.max_positions]
    epd = out / "positions.epd"
    epd.write_text("\n".join(fens[i] for i in idx) + "\n")
    y = np.array([recs[i]["target"] for i in idx], dtype=np.float64)
    games = [recs[i]["game"] for i in idx]
    uniq = sorted(set(games)); gi = {g: i for i, g in enumerate(uniq)}
    codes = np.array([gi[g] for g in games]); G = len(uniq)

    dev4 = ROOT / "benchmarks/binaries/stockbear-dev4-1c5b61a7"
    dev5 = ROOT / "benchmarks/binaries/stockbear-dev5-release"
    params = ROOT / "research-data/params_abc.txt"
    arms = {
        "dev4_default": extract(dev4, epd, out / "dev4_default.csv", None),
        "dev5_default": extract(dev5, epd, out / "dev5_default.csv", None),
        "dev5_params_abc": extract(dev5, epd, out / "dev5_abc.csv", params),
    }

    def losses(s, k, base):
        p = np.clip(1.0 / (1.0 + np.power(10.0, -s / k)), 1e-12, 1 - 1e-12)
        if base == "log10":
            return -(y * np.log10(p) + (1 - y) * np.log10(1 - p))
        return -(y * np.log(p) + (1 - y) * np.log(1 - p))

    def brier_rows(s, k):
        p = 1.0 / (1.0 + np.power(10.0, -s / k))
        return (p - y) ** 2

    # Champion runtime is dev5 + params_abc; the released dev4 ran its defaults.
    base_arm, champ_arm = arms["dev4_default"], arms["dev5_params_abc"]
    sensitivity = []
    for k in (400.0, 600.0):
        for lb in ("log10", "ln"):
            la, lc = losses(base_arm, k, lb), losses(champ_arm, k, lb)
            st = clustered_paired(lc - la, codes, G)
            sensitivity.append({
                "K": k, "log_base": lb, "L_baseline": float(la.mean()),
                "L_champion": float(lc.mean()),
                "relative_change_pct": 100.0 * st["mean"] / float(la.mean()),
                "paired": st,
                "champion_more_accurate": bool(st["mean"] < 0)})
    bs = clustered_paired(brier_rows(champ_arm, 400.0) - brier_rows(base_arm, 400.0), codes, G)

    report = {
        "purpose": "Audit whether historical accuracy->Elo evidence exists for exp-0047 §3.3",
        "scope": "AUDIT of existing evidence. Zero strength games. Activates/reopens nothing.",
        "corpus": str(corpus), "corpus_manifest_sha256": sha(corpus / "MANIFEST.json"),
        "subsampling": f"every {a.stride}th row, first {a.max_positions}; score/outcome independent",
        "n_positions": len(idx), "clusters_games": G,
        "binaries": {"dev4": sha(dev4), "dev5": sha(dev5)},
        "params_abc_sha256": sha(params),
        "measured_elo_champion_vs_dev4": 64.7, "measured_elo_ci95": [57.5, 72.0],
        "elo_provenance": "exp-0024, run 41620641753, 6600 games, clustered CR1 t(1745)",
        "elo_is_bundle_not_eval_only": True,
        "arms_identical_dev4_default_vs_dev5_default": bool(
            np.array_equal(arms["dev4_default"], arms["dev5_default"])),
        "reason_defaults_identical": (
            "params_abc does not assign the four dev5-only features "
            "(RookOn7th/KnightOutpost/BackwardPawn/PawnChain), so with it the two "
            "binaries score identically; dev5's default weights for them are 0."),
        "logloss_sensitivity": sensitivity,
        "brier_paired_K400": bs,
        "brier_champion_more_accurate": bool(bs["mean"] < 0),
    }
    frozen = next(s for s in sensitivity if s["K"] == 400.0 and s["log_base"] == "log10")
    report["frozen_metric_result"] = {
        "metric": "Texel log10 loss at K=400 (the frozen exp-0048/49 metric)",
        "relative_change_pct": frozen["relative_change_pct"],
        "ci95_pct": [100.0 * c / frozen["L_baseline"] for c in frozen["paired"]["ci95"]],
        "champion_more_accurate": frozen["champion_more_accurate"],
        "distinguishable_from_zero": frozen["paired"]["distinguishable_from_zero"]}
    signs = {s["champion_more_accurate"] for s in sensitivity}
    report["logloss_sign_stable_across_K_and_base"] = (len(signs) == 1)
    report["metrics_disagree"] = (
        frozen["champion_more_accurate"] != report["brier_champion_more_accurate"])
    (out / "ACCURACY_ELO_ANCHOR.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "SHA256SUMS.txt").write_text(
        "".join(f"{sha(p)}  {p.name}\n" for p in sorted(out.iterdir())
                if p.is_file() and p.name != "SHA256SUMS.txt"))
    print(json.dumps({k: report[k] for k in (
        "n_positions", "clusters_games", "frozen_metric_result",
        "brier_champion_more_accurate", "metrics_disagree",
        "logloss_sign_stable_across_K_and_base")}, indent=2))


if __name__ == "__main__":
    main()
