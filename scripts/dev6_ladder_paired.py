#!/usr/bin/env python3
"""exp-0032b PAIRED shared-opening sensitivity ladder (registered addendum).

exp-0032's 40 disjoint opening slices confound engine strength with slice
difficulty: the fitted official/rebuilt dev5 gap (~30 internal Elo) contradicts
exp-0030's bench-identical binaries. This supplementary experiment removes that
confound: all 5 subjects play a full round-robin on ONE shared 100-opening suite
with the SAME seed (=> identical opening ORDER), colour-reversed. 10 pairings x
200 games = 2000 games, fixed-node 6000 +/- 15%.

Prediction (frozen before results): if the star-ladder gap is an opening-slice
artifact, dev5_official, dev5_rebuilt and dev6_champion will be statistically
indistinguishable (all CIs include 0); dev6_failed will remain measurably weaker
than dev6_champion (the -17 Elo regression is real, not a slice artifact).
"""
import hashlib
import itertools
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import match_stats
import fit_ladder

BIN = ROOT / "benchmarks" / "binaries"
POS = ROOT / "benchmarks" / "positions"
EXP = ROOT / "benchmarks" / "exp-runs"
OUT = ROOT / "benchmarks" / "dev6-baseline" / "ladder_paired.json"
PY = ROOT / ".venv" / "bin" / "python"
ABC = "research-data/params_abc.txt"
D6A = "research-data/params_dev6_a.txt"
CAND = str(ROOT / "build-cand" / "stockbear")
SUBJECTS = [
    ("dev5_official", str(BIN / "stockbear-dev5-release"), [f"EvalParams={ABC}", "TTEval=true"]),
    ("dev5_rebuilt", str(ROOT / "build-dev5" / "stockbear"), [f"EvalParams={ABC}", "TTEval=true"]),
    ("dev6_champion", CAND, [f"EvalParams={ABC}", "TTEval=true"]),
    ("dev6_failed", CAND, [f"EvalParams={D6A}", "TTEval=true"]),
    ("dev4", str(BIN / "stockbear-dev4-1c5b61a7"), []),
]
GAMES, NODES, JITTER, SEED = 200, 6000, 0.15, 2026111100


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def make_suite():
    p = POS / "openings_exp0032b_paired.txt"
    if not p.exists():
        subprocess.run([str(PY), str(ROOT / "scripts" / "exp_confirmation_openings.py"),
                        "--name", "exp0032b", "--seed", "2026111001", "--count", "100"],
                       cwd=ROOT, check=True, capture_output=True)
        (POS / "openings_exp0032b_confirmation.txt").rename(p)
    return p


def run(a, b, suite):
    d = EXP / f"exp0032b-paired-{a[0]}-{b[0]}"
    d.mkdir(parents=True, exist_ok=True)
    cmd = [str(PY), str(ROOT / "scripts" / "tournament.py"),
           "--engine-a", a[1], "--engine-b", b[1],
           "--games", str(GAMES), "--base-ms", "40", "--inc-ms", "4",
           "--hash", "16", "--threads", "1", "--max-plies", "240",
           "--nodes", str(NODES), "--nodes-jitter", str(JITTER),
           "--openings", str(suite), "--seed", str(SEED)]
    for o in a[2]:
        cmd += ["--a-option", o]
    for o in b[2]:
        cmd += ["--b-option", o]
    cmd += ["--pgn", str(d / "match.pgn"), "--jsonl", str(d / "match.jsonl"),
            "--csv", str(d / "match.csv")]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        return {"a": a[0], "b": b[0], "error": r.stderr[-800:]}
    recs = [json.loads(l) for l in (d / "match.jsonl").read_text().splitlines()
            if "\"game\"" in l]
    recs.sort(key=lambda x: x["game"])
    pair_scores, pair_openings, terms = [], [], {}
    for k in range(0, len(recs) - 1, 2):
        x, y = recs[k], recs[k + 1]
        if x["score_a"] is None or y["score_a"] is None:
            continue
        pair_scores.append(x["score_a"] + y["score_a"])
        pair_openings.append(x["opening"])
    for x in recs:
        t = x.get("termination", "?")
        terms[t] = terms.get(t, 0) + 1
    games = [x["score_a"] for x in recs if x["score_a"] is not None]
    s = match_stats.summarise(games, pair_scores,
                              match_stats.lmr_step(pair_scores, 0.0, 5.0),
                              pair_openings=pair_openings)
    cl = s.get("opening_clustered", {})
    return {"a": a[0], "b": b[0], "dir": str(d.relative_to(ROOT)),
            "games": len(games), "unadjudicated": len(recs) - len(games),
            "wins": s["wins"], "draws": s["draws"], "losses": s["losses"],
            "score_a": (s["wins"] + 0.5*s["draws"]) / max(1, len(games)),
            "elo_a_minus_b": cl.get("elo_difference"), "elo_ci95": cl.get("elo_ci95"),
            "clusters": cl.get("clusters"), "terminations": terms,
            "time_forfeit": sum(v for k, v in terms.items() if "FORFEIT" in k.upper())}


def main():
    suite = make_suite()
    pairings = []
    for a, b in itertools.combinations(SUBJECTS, 2):
        res = run(a, b, suite)
        pairings.append(res)
        if "error" in res:
            print(f"{a[0]:16s} vs {b[0]:16s} ERROR {res['error'][:100]}", flush=True)
        else:
            print(f"{a[0]:16s} vs {b[0]:16s} score {res['score_a']:.3f} "
                  f"+{res['wins']}={res['draws']}-{res['losses']} "
                  f"Elo {res['elo_a_minus_b']:+.1f} {res['elo_ci95']} "
                  f"forfeits {res['time_forfeit']}", flush=True)

    # joint BTD fit on the paired games only (shared openings => no slice confound)
    games = []
    for p in pairings:
        if "error" in p:
            continue
        for line in (ROOT / p["dir"] / "match.jsonl").read_text().splitlines():
            o = json.loads(line)
            if "\"game\"" not in line or o.get("score_a") is None:
                continue
            games.append({"i": p["a"], "j": p["b"], "score": o["score_a"],
                          "cluster": o["opening"]})
    engines = sorted({g["i"] for g in games} | {g["j"] for g in games})
    f = fit_ladder.fit(games, engines)
    elo = {e: float(f["elo"][k]) for k, e in enumerate(engines)}
    print("\npaired BTD (shared openings):",
          json.dumps({k: round(v, 1) for k, v in
                      sorted(elo.items(), key=lambda x: -x[1])}, indent=2))
    OUT.write_text(json.dumps({
        "experiment": "exp-0032b", "purpose": "paired shared-opening sensitivity to exp-0032",
        "prereg_addendum": "docs/DEV6_PREREG_EXP0031.md",
        "suite": str(suite.relative_to(ROOT)), "suite_sha256": sha(suite),
        "seed": SEED, "games_per_pairing": GAMES, "nodes": NODES,
        "nodes_jitter": JITTER, "pairings": pairings,
        "paired_btd_nu": f["nu"], "paired_btd_internal_elo": elo},
        indent=2) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
