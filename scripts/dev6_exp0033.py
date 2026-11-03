#!/usr/bin/env python3
"""exp-0033 isolated razoring screen. Frozen design: docs/DEV6_PREREG_EXP0033.md.

ONE binary, ONE UCI switch (`Razoring`) differs between the two sides =>
perfectly isolated ablation with no toolchain confound. 2 disjoint 600-opening
batches x 1200 games = 2400 paired games, fixed-node 6000 +/- 15%. A separate
400-game context match against the immutable official dev5 is context ONLY,
never a gate test.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import match_stats
import pool_matches

PY = ROOT / ".venv" / "bin" / "python"
POS = ROOT / "benchmarks" / "positions"
EXP = ROOT / "benchmarks" / "exp-runs"
OUT = ROOT / "benchmarks" / "dev6-baseline" / "exp0033_results.json"
CAND = str(ROOT / "build-exp0033" / "stockbear")
DEV5 = str(ROOT / "benchmarks" / "binaries" / "stockbear-dev5-release")
ABC = "research-data/params_abc.txt"
NODES, JITTER = 6000, 0.15


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def make_suite(name, seed, count, final):
    if not final.exists():
        subprocess.run([str(PY), str(ROOT / "scripts" / "exp_confirmation_openings.py"),
                        "--name", name, "--seed", str(seed), "--count", str(count)],
                       cwd=ROOT, check=True, capture_output=True)
        (POS / f"openings_{name}_confirmation.txt").rename(final)
    return [l for l in final.read_text().splitlines() if l and not l.startswith("#")]


def run(tag, a_opts, b_path, b_opts, openings_file, games, seed):
    d = EXP / f"exp0033-{tag}"
    d.mkdir(parents=True, exist_ok=True)
    cmd = [str(PY), str(ROOT / "scripts" / "tournament.py"),
           "--engine-a", CAND, "--engine-b", b_path,
           "--games", str(games), "--base-ms", "40", "--inc-ms", "4",
           "--hash", "16", "--threads", "1", "--max-plies", "240",
           "--nodes", str(NODES), "--nodes-jitter", str(JITTER),
           "--openings", str(openings_file), "--seed", str(seed)]
    for o in a_opts:
        cmd += ["--a-option", o]
    for o in b_opts:
        cmd += ["--b-option", o]
    cmd += ["--pgn", str(d / "match.pgn"), "--jsonl", str(d / "match.jsonl"),
            "--csv", str(d / "match.csv")]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        return {"tag": tag, "error": r.stderr[-1000:]}
    recs = [json.loads(l) for l in (d / "match.jsonl").read_text().splitlines()
            if "\"game\"" in l]
    recs.sort(key=lambda x: x["game"])
    pair_scores, pair_openings, terms = [], [], {}
    for k in range(0, len(recs) - 1, 2):
        if k + 1 >= len(recs):
            continue
        a, b = recs[k], recs[k + 1]
        if a["score_a"] is None or b["score_a"] is None:
            continue
        pair_scores.append(a["score_a"] + b["score_a"])
        pair_openings.append(a["opening"])
    for x in recs:
        t = x.get("termination", "?")
        terms[t] = terms.get(t, 0) + 1
    games_ok = [x["score_a"] for x in recs if x["score_a"] is not None]
    s = match_stats.summarise(games_ok, pair_scores,
                              match_stats.lmr_step(pair_scores, 0.0, 5.0),
                              pair_openings=pair_openings)
    cl = s.get("opening_clustered", {})
    return {"tag": tag, "dir": str(d.relative_to(ROOT)),
            "binary_a_sha256": sha(CAND), "binary_b_sha256": sha(b_path),
            "openings_sha256": sha(openings_file), "seed": seed,
            "games": len(games_ok), "unadjudicated": len(recs) - len(games_ok),
            "wins": s["wins"], "draws": s["draws"], "losses": s["losses"],
            "score": (s["wins"] + 0.5*s["draws"]) / max(1, len(games_ok)),
            "elo": cl.get("elo_difference"), "ci95": cl.get("elo_ci95"),
            "clusters": cl.get("clusters"), "llr_normal_approx": s.get("llr"),
            "terminations": terms,
            "time_forfeit": sum(v for k, v in terms.items() if "FORFEIT" in k.upper()),
            "illegal": sum(v for k, v in terms.items() if "ILLEGAL" in k.upper())}


def main():
    master = POS / "openings_exp0033.txt"
    lines = make_suite("exp0033", 2026111201, 1200, master)
    assert len(lines) == 1200, len(lines)
    slices = []
    for i, tag in enumerate(("batchA", "batchB")):
        p = POS / f"openings_exp0033_{tag}.txt"
        p.write_text("\n".join(lines[i*600:(i+1)*600]) + "\n")
        slices.append(p)
    ctx = POS / "openings_exp0033_context.txt"
    make_suite("exp0033c", 2026111202, 200, ctx)

    results = []
    common_a = [f"EvalParams={ABC}", "TTEval=true", "Razoring=true"]
    common_b = [f"EvalParams={ABC}", "TTEval=true", "Razoring=false"]
    for i, tag in enumerate(("batchA", "batchB")):
        r = run(tag, common_a, CAND, common_b, slices[i], 1200, 2026111300 + i)
        results.append(r)
        print(f"{tag}: " + (f"ERROR {r['error'][:150]}" if "error" in r else
              f"score {r['score']:.4f} +{r['wins']}={r['draws']}-{r['losses']} "
              f"Elo {r['elo']:+.2f} {r['ci95']} forfeits {r['time_forfeit']}"), flush=True)
    # context only: razoring ON vs immutable official dev5 (different source)
    c = run("context-vs-dev5", common_a, DEV5,
            [f"EvalParams={ABC}", "TTEval=true"], ctx, 400, 2026111400)
    results.append(c)
    print("context-vs-dev5: " + (f"ERROR {c['error'][:150]}" if "error" in c else
          f"score {c['score']:.4f} Elo {c['elo']:+.2f} {c['ci95']}"), flush=True)

    # combined, pooled by the pre-registered rule (all games, no subsetting)
    ok = [r for r in results if r["tag"].startswith("batch") and "error" not in r]
    combined = None
    if len(ok) == 2:
        allpairs, allgames, pair_openings = [], [], []
        for r in ok:
            recs = [json.loads(l) for l in (ROOT / r["dir"] / "match.jsonl").read_text().splitlines()
                    if "\"game\"" in l]
            recs.sort(key=lambda x: x["game"])
            gs = [x["score_a"] for x in recs if x["score_a"] is not None]
            allgames += gs
            for k in range(0, len(recs) - 1, 2):
                if recs[k]["score_a"] is not None and recs[k+1]["score_a"] is not None:
                    allpairs.append(recs[k]["score_a"] + recs[k+1]["score_a"])
                    pair_openings.append(recs[k]["opening"])
        s = match_stats.summarise(allgames, allpairs,
                                  match_stats.lmr_step(allpairs, 0.0, 5.0),
                                  pair_openings=pair_openings)
        combined = {"wins": s["wins"], "draws": s["draws"], "losses": s["losses"],
                    "games": len(allgames), "elo": s.get("opening_clustered", {}).get("elo_difference"),
                    "ci95": s.get("opening_clustered", {}).get("elo_ci95"),
                    "score": (s["wins"] + 0.5*s["draws"]) / max(1, len(allgames))}
        print("combined:", json.dumps(combined), flush=True)
    OUT.write_text(json.dumps({
        "experiment": "exp-0033", "prereg": "docs/DEV6_PREREG_EXP0033.md",
        "control": "same binary, Razoring=true vs false",
        "candidate_binary_sha256": sha(CAND),
        "official_dev5_sha256": sha(DEV5),
        "master_suite_sha256": sha(master),
        "p1_bench_depth12_nodes": {"razoring_off": 6562637, "razoring_on": 6339128,
                                   "delta_pct": -3.4},
        "p1_startpos_go_depth12_nodes": {"razoring_off": 543800, "razoring_on": 733944,
                                         "delta_pct": 34.96},
        "results": results, "combined": combined}, indent=2) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
