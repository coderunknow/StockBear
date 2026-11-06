#!/usr/bin/env python3
"""Combine verified exp-0048 corpus shards into one fitting dataset.

Input: a directory containing one subdirectory per shard, each produced by
`scripts/dev6_corpus_job.py` (manifest.json, SHA256SUMS.txt, games.pgn,
games.jsonl, positions.epd, positions.meta.json).

Every shard checksum is verified before anything is read, every shard must
report ZERO engine failures, and the shard set must be exactly the expected
one -- a missing shard is an error, never a silently smaller corpus.

Output (in --out):
  corpus.epd.gz          concatenated positions, shard order s00..sNN
  corpus.records.json.gz [{"game": "s00:0", "ply": 12, "target": 1.0}, ...]
                         game ids are shard-prefixed so games from different
                         shards can never collide in the by-game split
  corpus.pgn.gz          concatenated raw PGNs (audit trail)
  corpus.jsonl.gz        concatenated raw per-game JSONL (audit trail)
  MANIFEST.json          hashes, counts, per-shard provenance, split policy
  SHA256SUMS.txt

The split itself is NOT performed here: it is defined by the frozen prereg and
applied by the fitter, so this file stays a pure, verifiable concatenation.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_shard(d: Path) -> dict:
    sums = d / "SHA256SUMS.txt"
    assert sums.is_file(), f"{d}: SHA256SUMS.txt missing"
    for line in sums.read_text().splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        name = name.lstrip("*")
        target = d / name
        assert target.is_file(), f"{d}: listed file {name} missing"
        assert sha(target) == digest, f"{d}: checksum mismatch for {name}"
    m = json.loads((d / "manifest.json").read_text())
    assert m["engine_failures"] == 0, f"{d}: shard has engine failures"
    assert m["games"] == len([l for l in (d / "games.jsonl").read_text().splitlines()
                              if '"game"' in l]), f"{d}: game count mismatch"
    meta = json.loads((d / "positions.meta.json").read_text())
    lines = (d / "positions.epd").read_text().splitlines()
    assert len(lines) == meta["positions"] == len(meta["records"]), f"{d}: position count mismatch"
    assert sha(d / "positions.epd") == meta["positions_sha256"], f"{d}: EPD hash mismatch"
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", required=True, help="directory holding shard subdirectories")
    ap.add_argument("--out", required=True)
    ap.add_argument("--experiment-id", default="exp0048")
    ap.add_argument("--expect", default="s00,s01,s02,s03,s04,s05,s06,s07")
    ap.add_argument("--source-run-id", default="local")
    a = ap.parse_args()

    root = Path(a.shards)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    expected = a.expect.split(",")
    dirs = []
    for shard in expected:
        matches = [p for p in root.rglob("manifest.json")
                   if json.loads(p.read_text()).get("shard") == shard
                   and json.loads(p.read_text()).get("experiment_id") == a.experiment_id]
        assert len(matches) == 1, f"expected exactly one directory for shard {shard}, found {len(matches)}"
        dirs.append((shard, matches[0].parent))
    found = {json.loads(p.read_text())["shard"] for p in root.rglob("manifest.json")}
    assert found == set(expected), f"unexpected shard set: {sorted(found)} != {sorted(expected)}"

    manifests = {shard: verify_shard(d) for shard, d in dirs}
    source_shas = {m["source_sha"] for m in manifests.values()}
    assert len(source_shas) == 1, f"shards built from different source SHAs: {source_shas}"
    seeds = {m["seed"] for m in manifests.values()}
    controls = {(m["base_ms"], m["inc_ms"], m["hash_mb"], m["threads"], m["max_plies"])
                for m in manifests.values()}
    assert len(controls) == 1, f"inconsistent match conditions: {controls}"
    opening_hashes = [m["openings_sha256"] for m in manifests.values()]
    assert len(set(opening_hashes)) == len(opening_hashes), "duplicate opening shard"

    epd_lines: list[str] = []
    records: list[dict] = []
    pgn_chunks: list[str] = []
    jsonl_chunks: list[str] = []
    for shard, d in dirs:
        meta = json.loads((d / "positions.meta.json").read_text())
        epd_lines.extend((d / "positions.epd").read_text().splitlines())
        for r in meta["records"]:
            records.append({"game": f"{shard}:{r['game']}", "ply": r["ply"], "target": r["target"]})
        pgn_chunks.append((d / "games.pgn").read_text().rstrip("\n"))
        jsonl_chunks.append((d / "games.jsonl").read_text().rstrip("\n"))
    assert len(epd_lines) == len(records)

    def write_gz(name: str, text: str) -> dict:
        raw = text.encode("utf-8")
        p = out / name
        # mtime=0 keeps the archive byte-reproducible for a given input.
        with gzip.GzipFile(filename="", mode="wb", fileobj=p.open("wb"), mtime=0) as g:
            g.write(raw)
        return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                "gz_bytes": p.stat().st_size, "gz_sha256": sha(p)}

    files = {
        "corpus.epd.gz": write_gz("corpus.epd.gz", "\n".join(epd_lines) + "\n"),
        "corpus.records.json.gz": write_gz("corpus.records.json.gz",
                                           json.dumps(records, separators=(",", ":"))),
        "corpus.pgn.gz": write_gz("corpus.pgn.gz", "\n\n".join(pgn_chunks) + "\n"),
        "corpus.jsonl.gz": write_gz("corpus.jsonl.gz", "\n".join(jsonl_chunks) + "\n"),
    }
    games = sum(m["games"] for m in manifests.values())
    contrib = len({r["game"] for r in records})
    manifest = {
        "experiment_id": a.experiment_id,
        "purpose": "evaluator-fitting-only; NEVER a strength batch",
        "source_sha": next(iter(source_shas)),
        "source_run_id": a.source_run_id,
        "prereg": f"docs/DEV6_PREREG_{a.experiment_id.upper()}.md",
        "prereg_sha256": manifests[expected[0]]["prereg_sha256"],
        "baseline_sha256": manifests[expected[0]]["baseline_sha256"],
        "conditions": {"base_ms": manifests[expected[0]]["base_ms"],
                       "inc_ms": manifests[expected[0]]["inc_ms"],
                       "hash_mb": manifests[expected[0]]["hash_mb"],
                       "threads": manifests[expected[0]]["threads"],
                       "max_plies": manifests[expected[0]]["max_plies"],
                       "options": manifests[expected[0]]["options"], "seeds": sorted(seeds)},
        "shards": expected, "games": games, "positions": len(records),
        "games_contributing_positions": contrib,
        "engine_failures": sum(m["engine_failures"] for m in manifests.values()),
        "time_forfeits": sum(m["time_forfeits"] for m in manifests.values()),
        "split_policy": {"by": "game", "holdout_fraction": 0.2, "seed": 2026110602,
                         "rule": "sorted unique game ids, random.Random(seed).shuffle, "
                                 "first ceil(0.2*G) ids are holdout"},
        "game_id_format": "<shard>:<per-shard game index from build_tuning_data>",
        "files": files,
        "per_shard": {s: {k: m[k] for k in ("games", "positions", "openings", "openings_sha256",
                                            "engine_failures", "time_forfeits", "terminations",
                                            "skipped", "runner", "workflow_run_id")}
                      for s, m in manifests.items()},
        "license": "original data generated by this project; Apache-2.0",
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    hashed = sorted(p for p in out.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt")
    (out / "SHA256SUMS.txt").write_text("\n".join(f"{sha(p)}  {p.name}" for p in hashed) + "\n")
    print(f"combined {len(expected)} shards: {games} games, {len(records)} positions, "
          f"{contrib} contributing games, {manifest['engine_failures']} engine failures, "
          f"{manifest['time_forfeits']} time forfeits")
    print("gz bytes:", sum(f["gz_bytes"] for f in files.values()))


if __name__ == "__main__":
    main()
