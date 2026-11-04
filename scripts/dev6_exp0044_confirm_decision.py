#!/usr/bin/env python3
"""Reproduce the FROZEN exp-0044 confirmation decision from RAW games.

The generic `dev6_exp0038_audit.py` prints the prereg §6 default
("INCONCLUSIVE -> more samples"). The exp-0044 ADDENDUM, frozen BEFORE any
confirmation game, explicitly overrides that branch with an experiment-level
COMPUTE BOUND: if neither ADVANCE nor CLOSE holds, exp-0044 is CLOSED AS
INCONCLUSIVE and the direction is abandoned. This script applies that frozen
override and never pools the screen with the confirmation.

Usage: .venv/bin/python scripts/dev6_exp0044_confirm_decision.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import match_stats  # noqa: E402

RUN = ROOT / "benchmarks/exp-runs/tier1-export/run-41814069967"
ADVANCE_POINT = 20.0
CLOSE_UCB = 10.0
BATCH_MIN = -5.0


def load(suffix: str):
    dirs = sorted(d for d in RUN.glob("tier1-*") if d.name.endswith(suffix))
    assert len(dirs) == 1, (suffix, dirs)
    rs = [json.loads(l) for l in (dirs[0] / "match.jsonl").read_text().splitlines()
          if '"game"' in l]
    rs.sort(key=lambda x: x["game"])
    return dirs[0], rs


def pair_scores(recs):
    pairs, openings = [], []
    for k in range(0, len(recs) - 1, 2):
        x, y = recs[k], recs[k + 1]
        if x["score_a"] is not None and y["score_a"] is not None:
            pairs.append(x["score_a"] + y["score_a"])
            openings.append(x["opening"])
    return pairs, openings


def main() -> int:
    parts = {}
    combined_scores, combined_pairs, combined_openings = [], [], []
    for name in ("batchA", "batchB", "null", "stage0"):
        d, rs = load(f"-{name}-run41814069967")
        ps, po = pair_scores(rs)
        scores = [x["score_a"] for x in rs if x["score_a"] is not None]
        s = match_stats.summarise(scores, ps, match_stats.lmr_step(ps, 0.0, 5.0),
                                  pair_openings=po)
        cl = s.get("opening_clustered", {})
        terms = [str(x.get("termination", "")) for x in rs]
        bad = sum(1 for t in terms
                  if "FORFEIT" in t.upper() or "ILLEGAL" in t.upper()
                  or "FAILURE" in t.upper())
        parts[name] = {"games": len(scores), "elo": cl.get("elo_difference"),
                       "ci": cl.get("elo_ci95"), "clean": bad == 0,
                       "bad_terminations": bad, "terminations": dict(
                           (t, terms.count(t)) for t in sorted(set(terms)))}
        print(f"{name:8s} games={len(scores):5d} Elo={parts[name]['elo']:9.4f} "
              f"CI={[round(v, 4) for v in parts[name]['ci']]}")
        if name in ("batchA", "batchB"):
            combined_scores += scores
            combined_pairs += ps
            combined_openings += po
    s = match_stats.summarise(combined_scores, combined_pairs,
                              match_stats.lmr_step(combined_pairs, 0.0, 5.0),
                              pair_openings=combined_openings)
    cl = s["opening_clustered"]
    point, lcb, ucb = cl["elo_difference"], cl["elo_ci95"][0], cl["elo_ci95"][1]
    clean = all(parts[k]["clean"] for k in parts)
    nulls_ok = all(parts[k]["ci"][0] <= 0 <= parts[k]["ci"][1]
                   for k in ("null", "stage0"))
    batches_ok = all(parts[k]["elo"] >= BATCH_MIN for k in ("batchA", "batchB"))
    advance = point >= ADVANCE_POINT and lcb > 0 and batches_ok and nulls_ok and clean
    close = ucb < CLOSE_UCB or point <= 0
    print(f"\nFROZEN COMBINED (confirmation ONLY, NEVER pooled with screen): "
          f"games={len(combined_scores)} point={point:.4f} CI=[{lcb:.4f},{ucb:.4f}]")
    print(f"ADVANCE={advance} CLOSE={close} clean={clean} nulls_ok={nulls_ok} "
          f"batches_ok={batches_ok}")
    if advance:
        verdict = "ADVANCE"
    elif close:
        verdict = "CLOSE"
    else:
        # Frozen ADDENDUM compute bound, registered BEFORE these games.
        verdict = "CLOSED_AS_INCONCLUSIVE (frozen addendum compute bound; NO further samples)"
    print("VERDICT:", verdict)
    assert verdict.startswith("CLOSED_AS_INCONCLUSIVE"), verdict
    assert abs(point - 13.5977) < 0.01 and abs(lcb - 2.1746) < 0.01
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
