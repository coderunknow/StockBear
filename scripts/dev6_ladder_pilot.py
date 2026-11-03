#!/usr/bin/env python3
"""exp-0031 ladder pilot: find non-saturated anchors bracketing dev5.

Frozen design in docs/DEV6_PREREG_EXP0031.md. Subject = exact released dev5
artifact at champion options. Fixed-node 6000 +/- 15% (CPU-clock-immune),
40 paired games per anchor on a fresh, disjoint 20-opening slice, 10 anchors.
Results discarded for the 4-game config smoke test (run separately).
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import match_stats

BIN = ROOT / "benchmarks" / "binaries"
POS = ROOT / "benchmarks" / "positions"
EXP = ROOT / "benchmarks" / "exp-runs"
OUT = ROOT / "benchmarks" / "dev6-baseline" / "ladder_pilot.json"
PY = ROOT / ".venv" / "bin" / "python"
DEV5 = str(BIN / "stockbear-dev5-release")
SF11 = str(BIN / "external" / "stockfish-sf11")
NODES = 6000
JITTER = 0.15

# (id, engine_b, list of --b-option values, wrapper label)
ANCHORS = [
    ("sf11-L0", SF11, ["Skill Level=0"], "SF11 skill 0"),
    ("sf11-L4", SF11, ["Skill Level=4"], "SF11 skill 4"),
    ("sf11-L8", SF11, ["Skill Level=8"], "SF11 skill 8"),
    ("sf11-L12", SF11, ["Skill Level=12"], "SF11 skill 12"),
    ("sf11-L16", SF11, ["Skill Level=16"], "SF11 skill 16"),
    ("sf11-L20", SF11, ["Skill Level=20"], "SF11 full strength"),
    ("sf8", str(BIN / "external" / "stockfish-sf8"), [], "SF8 full"),
    ("sf9", str(BIN / "external" / "stockfish-sf9"), [], "SF9 full"),
    ("sf10", str(BIN / "external" / "stockfish-sf10"), [], "SF10 full"),
    ("dev4", str(BIN / "stockbear-dev4-1c5b61a7"), [], "dev4 internal"),
]
INFORMATIVE = (0.20, 0.80)


def make_slices():
    master = POS / "openings_exp0031_pilot.txt"
    if not master.exists():
        subprocess.run([str(PY), str(ROOT / "scripts" / "exp_confirmation_openings.py"),
                        "--name", "exp0031p", "--seed", "2026110701", "--count", "200"],
                       cwd=ROOT, check=True, capture_output=True)
        # exp_confirmation_openings.py names it openings_exp0031p_confirmation.txt
        gen = POS / "openings_exp0031p_confirmation.txt"
        gen.rename(master)
    lines = [l for l in master.read_text().splitlines() if l and not l.startswith("#")]
    assert len(lines) == 200, f"expected 200 openings, got {len(lines)}"
    slices = []
    for i in range(10):
        p = POS / f"openings_exp0031_pilot_s{i+1:02d}.txt"
        p.write_text("\n".join(lines[i*20:(i+1)*20]) + "\n")
        slices.append(p)
    import hashlib
    return hashlib.sha256(master.read_bytes()).hexdigest(), slices


def run_cell(anchor_id, engine_b, b_opts, slice_path, seed):
    d = EXP / f"exp0031-pilot-{anchor_id}"
    d.mkdir(parents=True, exist_ok=True)
    cmd = [str(PY), str(ROOT / "scripts" / "tournament.py"),
           "--engine-a", DEV5, "--engine-b", engine_b,
           "--games", "40", "--base-ms", "40", "--inc-ms", "4",
           "--hash", "16", "--threads", "1", "--max-plies", "240",
           "--nodes", str(NODES), "--nodes-jitter", str(JITTER),
           "--openings", str(slice_path), "--seed", str(seed),
           "--a-option", "EvalParams=research-data/params_abc.txt",
           "--a-option", "TTEval=true"]
    for o in b_opts:
        cmd += ["--b-option", o]
    cmd += ["--pgn", str(d / "match.pgn"), "--jsonl", str(d / "match.jsonl"),
            "--csv", str(d / "match.csv")]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        return {"id": anchor_id, "error": r.stderr[-800:]}
    recs = []
    for line in (d / "match.jsonl").read_text().splitlines():
        o = json.loads(line)
        if "game" in o:
            recs.append(o)
    pair_scores, pair_openings, terms = [], [], {}
    recs.sort(key=lambda x: x["game"])
    for k in range(0, len(recs) - 1, 2):
        a, b = recs[k], recs[k+1]
        if a["score_a"] is None or b["score_a"] is None:
            continue
        pair_scores.append(a["score_a"] + b["score_a"])
        pair_openings.append(a["opening"])
    for x in recs:
        t = x.get("termination", "?")
        terms[t] = terms.get(t, 0) + 1
    games = [x["score_a"] for x in recs if x["score_a"] is not None]
    summ = match_stats.summarise(games, pair_scores,
                                 match_stats.lmr_step(pair_scores, 0.0, 5.0),
                                 pair_openings=pair_openings)
    cl = summ.get("opening_clustered", {})
    score = summ["wins"] + 0.5 * summ["draws"]
    score /= max(1, len(games))
    return {"id": anchor_id, "label": next(a[3] for a in ANCHORS if a[0] == anchor_id),
            "engine_b": engine_b, "b_options": b_opts,
            "opening_slice": str(slice_path.relative_to(ROOT)), "seed": seed,
            "games": len(games), "wins": summ["wins"], "draws": summ["draws"],
            "losses": summ["losses"], "score": score,
            "elo": (cl.get("elo_difference")), "ci95": cl.get("elo_ci95"),
            "clusters": cl.get("clusters"), "terminations": terms,
            "unadjudicated": len(recs) - len(games),
            "time_forfeit": sum(v for k, v in terms.items() if "FORFEIT" in k.upper()),
            "informative": INFORMATIVE[0] <= score <= INFORMATIVE[1]}


def main():
    master_sha, slices = make_slices()
    results = []
    for i, (aid, eb, opts, _) in enumerate(ANCHORS):
        res = run_cell(aid, eb, opts, slices[i], 2026110710 + i)
        results.append(res)
        if "error" in res:
            print(aid, "ERROR", res["error"][:200])
        else:
            print(f"{aid:10s} score {res['score']:.3f}  W/D/L "
                  f"+{res['wins']}={res['draws']}-{res['losses']}  "
                  f"informative={res['informative']}  forfeits={res['time_forfeit']}")
    informative = [r for r in results if r.get("informative")]
    out = {"experiment": "exp-0031", "prereg": "docs/DEV6_PREREG_EXP0031.md",
           "control": {"nodes": NODES, "nodes_jitter": JITTER, "hash": 16,
                       "threads": 1, "max_plies": 240, "games_per_anchor": 40},
           "subject": "exact released dev5 391cb50e... at params_abc + TTEval",
           "pilot_suite_sha256": master_sha,
           "informative_band": list(INFORMATIVE), "results": results,
           "informative_anchors": [r["id"] for r in informative],
           "saturated_anchors": [r["id"] for r in results if r.get("informative") is False],
           "decision": ("PROCEED" if len(informative) >= 2 else
                        "EXPAND_POOL_UNDER_NEW_SUBID")}
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print("decision:", out["decision"], "informative:", out["informative_anchors"])
    print("wrote", OUT)


if __name__ == "__main__":
    main()
