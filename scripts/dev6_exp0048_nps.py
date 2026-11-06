#!/usr/bin/env python3
"""exp-0048 §5 cost gate: matched-toolchain NPS at BIT-IDENTICAL node counts.

Both arms are the SAME binary; only the loaded evaluation differs (champion
formulaic PST vs the fitted PstFile). Fixed *depth* cannot give identical node
counts once eval values differ, so the frozen protocol searches a fixed NODE
budget per position and compares nodes/second.

Protocol (frozen in docs/DEV6_PREREG_EXP0048.md §5 before the corpus existed):
  * the 12 compiled-in bench FENs (benchmarks/positions/search.inc);
  * `stockbear bench --nodes N --params <champion> [--pst <table>]`, one fresh
    process per arm per repetition, Hash 16, one thread;
  * >= 3 repetitions in the order A,B / B,A / A,B on one idle machine;
  * ratio = median(candidate nps) / median(champion nps), gate [0.97, 1.03].

Why `bench --nodes` and not the UCI `go nodes` loop: the UCI `info` line reports
the node count of the last COMPLETED iteration, so a node-limited UCI search
reports a different, eval-dependent total for each arm (measured during the
pre-corpus smoke test: 1,853,814 vs 1,393,400). `bench --nodes` reports the true
searched node count, which is exactly N for every position that reaches the
budget. That makes the node-matched requirement actually satisfiable.

Structural inclusion rule (fixed before measurement, independent of which arm
is faster): a position contributes to the timing aggregate iff BOTH arms
searched exactly N nodes. Positions where either arm terminated early (forced
mate / stalemate / bare kings) are reported with their exact node counts but
excluded from the ratio, because a search that ends at a forced terminal does
not measure evaluator throughput. The included set must be identical across
repetitions and must contain at least half the suite.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAMPION_PARAMS = "research-data/params_abc.txt"


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run_arm(engine: str, nodes: int, hash_mb: int, pst: str | None, tag: str,
            out: Path) -> dict:
    cmd = [engine, "bench", "--nodes", str(nodes), "--hash", str(hash_mb),
           "--params", str(ROOT / CHAMPION_PARAMS)]
    if pst:
        cmd += ["--pst", pst]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=1800)
    assert r.returncode == 0, f"bench failed: {r.stderr[-2000:]}"
    (out / f"bench_{tag}.csv").write_text(r.stdout)
    lines = r.stdout.splitlines()
    header = next(l for l in lines if l.startswith("name,"))
    body = [l for l in lines if l.startswith('"')]
    rows = list(csv.DictReader(io.StringIO(header + "\n" + "\n".join(body))))
    assert rows, "no bench rows parsed"
    return {"command": cmd, "rows": [
        {"position": x["name"], "nodes": int(x["nodes"]), "time_us": int(x["time_us"]),
         "depth": int(x["depth"]), "bestmove": x["bestmove"]} for x in rows]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--pst", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--nodes", type=int, default=300000)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--hash", type=int, default=16)
    a = ap.parse_args()
    assert a.reps >= 3, "the frozen protocol requires at least 3 alternating repetitions"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    engine = str(Path(a.engine).resolve())
    pst = str(Path(a.pst).resolve())

    reps = []
    included_sets = []
    for r in range(a.reps):
        order = ["champion", "candidate"] if r % 2 == 0 else ["candidate", "champion"]
        entry = {"repetition": r + 1, "order": order, "arms": {}}
        for arm in order:
            entry["arms"][arm] = run_arm(engine, a.nodes, a.hash,
                                         pst if arm == "candidate" else None,
                                         f"r{r + 1}_{arm}", out)
        c = {x["position"]: x for x in entry["arms"]["champion"]["rows"]}
        d = {x["position"]: x for x in entry["arms"]["candidate"]["rows"]}
        assert set(c) == set(d), "arms searched different position sets"
        included, excluded = [], []
        for name in c:
            if c[name]["nodes"] == a.nodes and d[name]["nodes"] == a.nodes:
                included.append(name)
            else:
                excluded.append({"position": name, "champion_nodes": c[name]["nodes"],
                                 "candidate_nodes": d[name]["nodes"]})
        assert len(included) * 2 >= len(c), f"only {len(included)}/{len(c)} positions node-matched"
        included_sets.append(sorted(included))
        for arm in ("champion", "candidate"):
            rows = [x for x in entry["arms"][arm]["rows"] if x["position"] in included]
            total_nodes = sum(x["nodes"] for x in rows)
            total_us = sum(x["time_us"] for x in rows)
            entry["arms"][arm].update({"included_positions": sorted(included),
                                       "total_nodes": total_nodes, "total_time_us": total_us,
                                       "nps": 1e6 * total_nodes / total_us if total_us else None})
        entry["excluded_terminal_positions"] = excluded
        entry["node_counts_bit_identical"] = all(
            c[n]["nodes"] == d[n]["nodes"] for n in included)
        print(f"rep {r + 1}: included {len(included)}/{len(c)}  "
              f"champion nps {entry['arms']['champion']['nps']:.0f}  "
              f"candidate nps {entry['arms']['candidate']['nps']:.0f}", flush=True)
        reps.append(entry)

    assert all(s == included_sets[0] for s in included_sets), \
        "the node-matched position set changed between repetitions"
    identical = all(e["node_counts_bit_identical"] for e in reps)
    champ = [e["arms"]["champion"]["nps"] for e in reps]
    cand = [e["arms"]["candidate"]["nps"] for e in reps]
    assert all(x is not None for x in champ + cand), "an arm reported zero elapsed time"
    mc, md = statistics.median(champ), statistics.median(cand)
    ratio = md / mc
    passed = bool(identical and 0.97 <= ratio <= 1.03)
    report = {
        "experiment_id": "exp0048", "gate": "prereg §5 / exp-0047 §3.2",
        "engine_sha256": sha(Path(engine)), "pst_sha256": sha(Path(a.pst)),
        "champion_params_sha256": sha(ROOT / CHAMPION_PARAMS),
        "nodes_per_position": a.nodes, "hash_mb": a.hash, "threads": 1,
        "repetitions": a.reps, "included_positions": included_sets[0],
        "node_counts_bit_identical": identical,
        "champion_nps": champ, "candidate_nps": cand,
        "champion_nps_median": mc, "candidate_nps_median": md, "ratio": ratio,
        "band": [0.97, 1.03], "passed": passed,
        "reps": reps,
    }
    (out / "NPS_GATE.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "SHA256SUMS.txt").write_text(
        "\n".join(f"{sha(p)}  {p.name}" for p in sorted(out.iterdir())
                  if p.is_file() and p.name != "SHA256SUMS.txt") + "\n")
    print(json.dumps({k: report[k] for k in ("node_counts_bit_identical", "champion_nps_median",
                                             "candidate_nps_median", "ratio", "passed")}, indent=2))
    if not passed:
        raise SystemExit("COST GATE FAILED: NPS ratio outside [0.97, 1.03]")


if __name__ == "__main__":
    main()
