#!/usr/bin/env python3
"""One preregistered exp-0048 self-play CORPUS shard on an isolated runner.

This is *training-data generation*, not a strength measurement. Both sides are
the immutable DEV5 champion binary, so the shard cannot produce an Elo claim
and is never pooled with any match. See docs/DEV6_PREREG_EXP0048.md §3.

Invariants (mirroring scripts/dev6_tier1_job.py):
  * NO git pushes and NO result commits: evidence goes to one directory that
    the workflow uploads as a GitHub Actions artifact.
  * The pinned source SHA must equal the checkout, the frozen prereg must be
    present, and the immutable baseline hash must match, or the job fails.
  * Every condition (openings, seed, clock, options, extractor parameters) is
    recorded in a manifest with SHA-256 digests, so a shard is reproducible.
  * ZERO engine failures are required (prereg §3). Time forfeits are legitimate
    40+4 ms outcomes and are counted, never filtered.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV5 = ROOT / "benchmarks/binaries/stockbear-dev5-release"
DEV5_SHA = "391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918"
CHAMPION = ["EvalParams=research-data/params_abc.txt", "TTEval=true"]
# Frozen in each experiment's prereg before any of its corpus games were played.
EXTRACT = ["--min-ply", "12", "--sample-every", "2",
           "--max-positions-per-game", "60", "--min-pieces", "6",
           "--max-abs-material", "1500"]


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", required=True, help="shard id, e.g. s00")
    ap.add_argument("--source-sha", required=True)
    ap.add_argument("--experiment-id", default="exp0048")
    ap.add_argument("--games", type=int, default=750)
    ap.add_argument("--seed", type=int, required=True,
                    help="frozen match seed from the experiment prereg; no default, so a "
                         "new experiment cannot silently inherit a previous seed")
    ap.add_argument("--base-ms", type=int, default=40)
    ap.add_argument("--inc-ms", type=int, default=4)
    ap.add_argument("--hash", type=int, default=16)
    ap.add_argument("--max-plies", type=int, default=240)
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--run-attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    a = ap.parse_args()

    out = ROOT / "benchmarks/exp-runs" / f"corpus-{a.experiment_id}-{a.shard}"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    log = open(out / "run.log", "w", buffering=1)

    def say(*x):
        print(*x, file=log, flush=True)
        print(*x, flush=True)

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert head == a.source_sha, f"source SHA mismatch: {head} != {a.source_sha}"
    prereg = ROOT / f"docs/DEV6_PREREG_{a.experiment_id.upper()}.md"
    assert prereg.is_file(), f"frozen prereg missing: {prereg}"
    assert sha(DEV5) == DEV5_SHA, "immutable dev5 baseline binary changed"
    say("source_sha", head, "prereg_sha256", sha(prereg))
    say("dev5 baseline sha256", DEV5_SHA, "VERIFIED")

    openings = ROOT / f"benchmarks/positions/openings_{a.experiment_id}_corpus_{a.shard}.txt"
    assert openings.is_file(), f"opening shard missing: {openings}"
    suites = ROOT / f"benchmarks/dev6-baseline/{a.experiment_id}_corpus_suites.json"
    suite_meta = json.loads(suites.read_text())
    assert suite_meta["slices"][a.shard] == sha(openings), "opening shard hash drift"
    n_openings = sum(1 for l in openings.read_text().splitlines()
                     if l and not l.startswith("#"))
    assert a.games == 2 * n_openings, f"games {a.games} != 2 x {n_openings} openings"
    say("openings", openings.name, n_openings, "games", a.games, "sha256", sha(openings))

    pgn, jsonl = out / "games.pgn", out / "games.jsonl"
    cmd = [sys.executable, str(ROOT / "scripts/tournament.py"),
           "--engine-a", str(DEV5), "--engine-b", str(DEV5),
           "--games", str(a.games), "--hash", str(a.hash), "--threads", "1",
           "--max-plies", str(a.max_plies), "--openings", str(openings),
           "--seed", str(a.seed), "--base-ms", str(a.base_ms), "--inc-ms", str(a.inc_ms),
           "--pgn", str(pgn), "--jsonl", str(jsonl), "--csv", str(out / "games.csv")]
    for o in CHAMPION:
        cmd += ["--a-option", o, "--b-option", o]
    say("+ " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    assert r.returncode == 0, f"tournament failed with {r.returncode}"

    records = [json.loads(l) for l in jsonl.read_text().splitlines() if '"game"' in l]
    summary = [json.loads(l)["summary"] for l in jsonl.read_text().splitlines()
               if '"summary"' in l]
    assert len(records) == a.games, f"expected {a.games} games, recorded {len(records)}"
    failures = sum(1 for x in records if x.get("engine_failure"))
    assert failures == 0, f"{failures} engine failures: corpus shard INVALID (prereg §3)"
    terms: dict[str, int] = {}
    for x in records:
        terms[x.get("termination", "?")] = terms.get(x.get("termination", "?"), 0) + 1
    forfeits = sum(v for k, v in terms.items() if "FORFEIT" in k.upper())
    say("games", len(records), "engine_failures", failures, "time_forfeits", forfeits)
    say("terminations", json.dumps(terms, sort_keys=True))

    epd, meta = out / "positions.epd", out / "positions.meta.json"
    cmd = [sys.executable, str(ROOT / "scripts/build_tuning_data.py"),
           "--pgn", str(pgn), "--out", str(epd), "--meta", str(meta), *EXTRACT]
    say("+ " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    assert r.returncode == 0, f"position extraction failed with {r.returncode}"
    extracted = json.loads(meta.read_text())
    assert extracted["positions"] == len(epd.read_text().splitlines())
    assert extracted["positions_sha256"] == sha(epd)
    say("positions", extracted["positions"], "sha256", extracted["positions_sha256"])

    manifest = {
        "experiment_id": a.experiment_id, "shard": a.shard, "purpose": "evaluator-fitting-only",
        "source_sha": head, "prereg_sha256": sha(prereg),
        "workflow_run_id": a.run_id, "run_attempt": a.run_attempt,
        "baseline_binary": str(DEV5.relative_to(ROOT)), "baseline_sha256": DEV5_SHA,
        "both_sides": "immutable dev5 champion (self-play)",
        "options": CHAMPION, "base_ms": a.base_ms, "inc_ms": a.inc_ms,
        "hash_mb": a.hash, "threads": 1, "max_plies": a.max_plies,
        "seed": a.seed, "games": a.games, "openings": str(openings.relative_to(ROOT)),
        "openings_sha256": sha(openings), "opening_count": n_openings,
        "engine_failures": failures, "time_forfeits": forfeits, "terminations": terms,
        "extractor": "scripts/build_tuning_data.py", "extractor_sha256": sha(ROOT / "scripts/build_tuning_data.py"),
        "extractor_args": EXTRACT, "positions": extracted["positions"],
        "games_contributing": len({r["game"] for r in extracted["records"]}),
        "skipped": extracted["skipped"],
        "runner": {"os": os.environ.get("RUNNER_OS", platform.system()),
                   "nproc": os.cpu_count(), "platform": platform.platform()},
        "files": {p.name: sha(p) for p in (pgn, jsonl, out / "games.csv", epd, meta)},
        "tournament_summary": summary[0] if summary else None,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    say("shard complete:", out.relative_to(ROOT))
    # Close the log BEFORE hashing: a checksum taken while the log is still
    # open would be stale by the final line and fail export verification.
    log.close()
    hashed = sorted(p for p in out.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt")
    (out / "SHA256SUMS.txt").write_text(
        "\n".join(f"{sha(p)}  {p.name}" for p in hashed) + "\n")


if __name__ == "__main__":
    main()
