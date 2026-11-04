#!/usr/bin/env python3
"""Independent exp-0038 audit from RAW Tier-1 evidence.

Deliberately does NOT read any summary.json as input data; summaries are only
the values to verify. Re-parses every exported match.jsonl, recomputes W/D/L,
score, independent Elo-from-score, and the CR1/t opening-clustered estimate,
then computes the FROZEN combined batchA+batchB decision quantities with:
  * an independent opening-clustered CR1/t calculation, and
  * an independent seeded cluster bootstrap cross-check (no shared code path
    with match_stats.lmr_step / opening_clustered).

Usage: .venv/bin/python scripts/dev6_exp0038_audit.py \
           <source_run_id> [label] [advance_point] [close_ucb]

Generic to any Tier-1 experiment with batchA/batchB/null/stage0 artifacts.
Thresholds are passed explicitly from the FROZEN preregistration and default
to exp-0038's frozen rules; they are never inferred from results.
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import match_stats  # noqa: E402

EXPO = ROOT / "benchmarks/exp-runs/tier1-export"


def records(directory):
    p = directory / "match.jsonl"
    rs = [json.loads(l) for l in p.read_text().splitlines() if '"game"' in l]
    rs.sort(key=lambda x: x["game"])
    return rs


def pairs_of(recs):
    out, openings = [], []
    for k in range(0, len(recs) - 1, 2):
        x, y = recs[k], recs[k + 1]
        if x["score_a"] is not None and y["score_a"] is not None:
            out.append(x["score_a"] + y["score_a"])
            openings.append(x["opening"])
    return out, openings


def elo_from_score(s):
    if s <= 0 or s >= 1:
        return None
    return -400 * math.log10(1.0 / s - 1.0)


def cluster_bootstrap(pair_scores, pair_openings, reps=20000, seed=2026112501):
    """Independent percentile-ish normal-approximation bootstrap over openings.

    Clusters are the distinct opening labels. Resample clusters with
    replacement, recompute score and Elo, then report the 2.5/97.5 percentiles.
    This is a cross-check, NOT the frozen decision statistic (which is CR1/t).
    """
    groups = defaultdict(list)
    for s, o in zip(pair_scores, pair_openings):
        groups[o].append(s)
    labels = sorted(groups)
    sums = np.asarray([sum(groups[k]) for k in labels], dtype=float)
    counts = np.asarray([len(groups[k]) for k in labels], dtype=float)
    rng = np.random.default_rng(seed)
    n = len(labels)
    out = np.empty(reps, dtype=float)
    for i in range(reps):
        idx = rng.integers(0, n, size=n)
        s = sums[idx].sum() / (2.0 * counts[idx].sum())
        out[i] = -400 * math.log10(1.0 / s - 1.0) if 0 < s < 1 else np.nan
    out = out[~np.isnan(out)]
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def main():
    if len(sys.argv) < 2:
        print("usage: dev6_exp0038_audit.py <source_run_id> [label] [advance_point] [close_ucb]",
              file=sys.stderr)
        return 2
    run_id = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else "exp0038"
    advance_point = float(sys.argv[3]) if len(sys.argv) > 3 else 20.0
    close_ucb = float(sys.argv[4]) if len(sys.argv) > 4 else 20.0
    root = EXPO / f"run-{run_id}"
    if not root.is_dir():
        print(f"no exported evidence at {root}", file=sys.stderr)
        return 2
    issues, checked = [], 0

    def cmp(tag, got, expected, tol=1e-9):
        nonlocal checked
        checked += 1
        if expected is None:
            return
        if abs(float(got) - float(expected)) > tol:
            issues.append(f"{tag}: recomputed {got} != stored {expected}")

    jobs = sorted(p for p in root.iterdir() if p.is_dir())
    print(f"{label} independent audit, run {run_id}, {len(jobs)} artifacts")
    print(f"  FROZEN thresholds from prereg: ADVANCE point>=+{advance_point:g} "
          f"and LCB>0; CLOSE UCB<+{close_ucb:g} or point<=0")
    combined_pairs, combined_openings, combined_scores = [], [], []
    per_job = {}
    for d in jobs:
        recs = records(d)
        scores = [r["score_a"] for r in recs if r["score_a"] is not None]
        ps, po = pairs_of(recs)
        s = match_stats.summarise(scores, ps, pair_openings=po)
        cl = s.get("opening_clustered", {})
        stored = json.loads((d / "summary.json").read_text())
        w = sum(1 for x in scores if x == 1.0)
        dr = sum(1 for x in scores if x == 0.5)
        l = sum(1 for x in scores if x == 0.0)
        score = (w + 0.5 * dr) / max(1, len(scores))
        cmp(f"{d.name} wins", w, stored["wins"])
        cmp(f"{d.name} draws", dr, stored["draws"])
        cmp(f"{d.name} losses", l, stored["losses"])
        cmp(f"{d.name} games", len(scores), stored["games"])
        cmp(f"{d.name} unadjudicated", len(recs) - len(scores), stored["unadjudicated"])
        cmp(f"{d.name} score", score, stored["score"], 1e-9)
        cmp(f"{d.name} elo_from_score", elo_from_score(score),
            stored["independent_elo_from_score"], 1e-9)
        cmp(f"{d.name} CR1 elo", cl.get("elo_difference"), stored["elo"], 1e-9)
        terms = Counter(r.get("termination", "?") for r in recs)
        tf = sum(v for k, v in terms.items() if "FORFEIT" in k.upper())
        ill = sum(v for k, v in terms.items() if "ILLEGAL" in k.upper())
        fail = sum(v for k, v in terms.items() if "FAILURE" in k.upper())
        cmp(f"{d.name} time_forfeit", tf, stored["time_forfeit"])
        cmp(f"{d.name} illegal", ill, stored["illegal"])
        cmp(f"{d.name} engine_failure", fail, stored["engine_failure"])
        per_job[d.name] = {
            "games": len(scores), "wins": w, "draws": dr, "losses": l,
            "score": score, "elo": cl.get("elo_difference"),
            "ci95": cl.get("elo_ci95"), "clusters": cl.get("clusters"),
            "time_forfeit": tf, "illegal": ill, "engine_failure": fail,
            "terminations": dict(sorted(terms.items())),
        }
        print(f"  {d.name:42s} {w:4d}/{dr:4d}/{l:4d}  score {score:.6f}  "
              f"CR1 {cl.get('elo_difference')}  CI {cl.get('elo_ci95')}")
        if "batchA" in d.name or "batchB" in d.name:
            combined_pairs.extend(ps)
            combined_openings.extend(po)
            combined_scores.extend(scores)

    # Frozen combined decision quantities (both batches, no post-hoc selection).
    if combined_pairs:
        cw = sum(1 for x in combined_scores if x == 1.0)
        cd = sum(1 for x in combined_scores if x == 0.5)
        closs = sum(1 for x in combined_scores if x == 0.0)
        cscore = (cw + 0.5 * cd) / len(combined_scores)
        s = match_stats.summarise(combined_scores, combined_pairs,
                                  pair_openings=combined_openings)
        cl = s["opening_clustered"]
        lo, hi = cluster_bootstrap(combined_pairs, combined_openings)
        print("\nFROZEN COMBINED batchA+batchB (no post-hoc selection)")
        print(f"  W/D/L = {cw}/{cd}/{closs}  games={len(combined_scores)}  "
              f"score={cscore:.7f}  clusters={cl['clusters']}")
        print(f"  CR1/t Elo = {cl['elo_difference']:.4f}  95% CI = "
              f"[{cl['elo_ci95'][0]:.4f}, {cl['elo_ci95'][1]:.4f}]")
        print(f"  independent Elo-from-score = {elo_from_score(cscore):.4f}")
        print(f"  independent cluster bootstrap 95% = [{lo:.4f}, {hi:.4f}]")
        point = cl["elo_difference"]
        lcb, ucb = cl["elo_ci95"]
        batches_ok = all(v["elo"] >= -5 for k, v in per_job.items()
                         if "batchA" in k or "batchB" in k)
        null_ok = any("null" in k for k in per_job)
        clean = all(v["time_forfeit"] == 0 and v["illegal"] == 0 and
                    v["engine_failure"] == 0 for v in per_job.values())
        print(f"  FROZEN RULE: point>=+{advance_point:g} {point >= advance_point}, "
              f"LCB>0 {lcb > 0}, both_batches>=-5 {batches_ok}, null present {null_ok}, "
              f"clean {clean}; CLOSE UCB<+{close_ucb:g} {ucb < close_ucb} "
              f"or point<=0 {point <= 0}")
        print("  ADVANCE" if (point >= advance_point and lcb > 0 and batches_ok and
                             null_ok and clean) else
              ("CLOSE" if (ucb < close_ucb or point <= 0)
               else "INCONCLUSIVE (more samples, same frozen conditions)"))
        print(f"  decision_inputs: {json.dumps({'advance_point': advance_point,
              'close_ucb': close_ucb, 'batches_ok': batches_ok,
              'clean': clean}, sort_keys=True)}")
        out = {
            "source_run_id": run_id,
            "combined": {"games": len(combined_scores), "wins": cw, "draws": cd,
                         "losses": closs, "score": cscore,
                         "elo": point, "ci95": list(cl["elo_ci95"]),
                         "clusters": cl["clusters"],
                         "independent_elo_from_score": elo_from_score(cscore),
                         "cluster_bootstrap_ci95": [lo, hi]},
            "per_job": per_job,
        }
        (ROOT / f"benchmarks/dev6-baseline/{label}_independent_audit.json").write_text(
            json.dumps(out, indent=2) + "\n")

    print(f"\nchecked {checked} stored values; {len(issues)} issues")
    for i in issues:
        print("  ISSUE:", i)
    print("AUDIT PASS" if not issues else "AUDIT FAIL")
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
