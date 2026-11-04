#!/usr/bin/env python3
"""Reproduce the FROZEN exp-0045 bounded-retry decision from RAW games.

Run 41817228668 is INVALID MEASUREMENT (one TIME_FORFEIT in batchB) under the
frozen exp-0045 prereg §5 zero-forfeit rule; ALL of its Elo is DISCARDED and it
is NEVER pooled here. `docs/DEV6_PREREG_EXP0045_RETRY.md`, frozen BEFORE any
retry game, registers exactly ONE valid new run with identical science and the
same ADVANCE / CLOSE / compute-bound rules.

The generic `dev6_exp0038_audit.py` reaches CLOSE for this run too. This script
independently recomputes the decision from raw `match.jsonl`, and additionally
ENFORCES the validity gate (0 forfeits / illegal / engine failures in ALL four
jobs) that the generic audit reports as `clean`.

Usage: .venv/bin/python scripts/dev6_exp0045_retry_decision.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import match_stats  # noqa: E402

RUN_ID = "41818958001"
INVALID_RUN_ID = "41817228668"
RUN = ROOT / "benchmarks" / "exp-runs" / "tier1-export" / f"run-{RUN_ID}"
ADVANCE_POINT = 20.0
CLOSE_UCB = 10.0
BATCH_MIN = -5.0


def load(suffix: str):
    dirs = sorted(d for d in RUN.glob("tier1-*") if d.name.endswith(suffix))
    assert len(dirs) == 1, (suffix, dirs)
    d = dirs[0]
    rs = [json.loads(l) for l in (d / "match.jsonl").read_text().splitlines()
          if '"game"' in l]
    rs.sort(key=lambda x: x["game"])
    return d, rs


def pair_scores(recs):
    pairs, openings = [], []
    for k in range(0, len(recs) - 1, 2):
        x, y = recs[k], recs[k + 1]
        if x["score_a"] is not None and y["score_a"] is not None:
            pairs.append(x["score_a"] + y["score_a"])
            openings.append(x["opening"])
    return pairs, openings


def main() -> int:
    assert RUN.is_dir(), RUN
    assert INVALID_RUN_ID not in str(RUN)
    parts = {}
    combined_scores, combined_pairs, combined_openings = [], [], []
    for name in ("batchA", "batchB", "null", "stage0"):
        d, rs = load(f"-{name}-run{RUN_ID}")
        summary = json.loads((d / "summary.json").read_text())
        ps, po = pair_scores(rs)
        scores = [x["score_a"] for x in rs if x["score_a"] is not None]
        s = match_stats.summarise(scores, ps, match_stats.lmr_step(ps, 0.0, 5.0),
                                  pair_openings=po)
        cl = s.get("opening_clustered", {})
        terms = [str(x.get("termination", "")) for x in rs]
        bad = sum(1 for t in terms
                  if "FORFEIT" in t.upper() or "ILLEGAL" in t.upper()
                  or "FAILURE" in t.upper())
        # Enforce BOTH the stored counts and an independent raw-JSONL scan.
        assert summary["time_forfeit"] == 0 and summary["illegal"] == 0 \
            and summary["engine_failure"] == 0 and bad == 0, (name, summary, bad)
        parts[name] = {"games": len(scores), "elo": cl.get("elo_difference"),
                       "ci": cl.get("elo_ci95"), "clean": True,
                       "bad_terminations": bad}
        print(f"{name:8s} games={len(scores):5d} Elo={parts[name]['elo']:9.4f} "
              f"CI={[round(v, 4) for v in parts[name]['ci']]} "
              f"forfeit/illegal/failure=0/0/0")
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
    print(f"\nFROZEN COMBINED (RETRY batchA+batchB ONLY; invalid run "
          f"{INVALID_RUN_ID} NEVER pooled): "
          f"games={len(combined_scores)} point={point:.4f} "
          f"CI=[{lcb:.4f},{ucb:.4f}]")
    print(f"ADVANCE={advance} CLOSE={close} clean={clean} "
          f"nulls_ok={nulls_ok} batches_ok={batches_ok}")
    if advance:
        verdict = "ADVANCE"
    elif close:
        verdict = "CLOSE (mechanism rejected / abandoned; NO strength claim)"
    else:
        # Frozen single-run COMPUTE BOUND, registered BEFORE these games.
        verdict = "CLOSED_AS_INCONCLUSIVE (frozen single-run compute bound; NO further samples)"
    print("VERDICT:", verdict)
    assert verdict.startswith("CLOSE ("), verdict
    assert abs(point - (-8.9240)) < 0.01 and abs(lcb - (-18.2792)) < 0.01 \
        and abs(ucb - 0.4182) < 0.01, (point, lcb, ucb)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
