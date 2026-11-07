#!/usr/bin/env python3
"""Repository-level checklist evidence audit (not a strength verdict).

Parses the authoritative checklist, checks that cited workspace paths exist,
re-verifies immutable binary digests, branch/main identity, append-only logs,
and raw-artifact addition-only policy. Writes a JSON record. It deliberately
does NOT mark items complete; it only exposes missing evidence for human audit.
"""
from __future__ import annotations
import hashlib, json, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()

def main():
    text = (ROOT / "STOCKBEAR_COMPLETION_CHECKLIST.md").read_text()
    items = []
    for m in re.finditer(r"- \[(x| )\] \*\*(\d+\.\d+)[^*]*\*\*(.*?)(?=\n- \[(?:x| )\] \*\*\d+\.\d+|\n## |\n---|\Z)", text, re.S):
        checked, ident, body = m.group(1) == "x", m.group(2), m.group(3)
        paths = re.findall(r"`([^`]+)`", body)
        filelike = [p for p in paths if ("/" in p or p.endswith((".md", ".json", ".txt", ".cpp", ".hpp", ".yml"))) and not p.startswith(("git ", "gh ", "ctest", "sha256sum", "http", "benchmarks/exp-runs/tier1-dispatch.json"))]
        missing = [p for p in filelike if not (ROOT / p.split(":")[0]).exists()]
        items.append({"id": ident, "checked": checked, "cited_filelike": filelike, "missing_paths": missing})
    out = {
        "head": git("rev-parse", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "main_sha": git("rev-parse", "origin/main"),
        "version_branch": (ROOT / "VERSION").read_text().strip(),
        "version_main": git("show", "origin/main:VERSION"),
        "checked": sum(i["checked"] for i in items),
        "open": sum(not i["checked"] for i in items),
        "total": len(items),
        "items": items,
        "binary_sha256": {
            "dev5": sha("benchmarks/binaries/stockbear-dev5-release"),
            "dev4_rebuild": sha("benchmarks/binaries/stockbear-dev4-1c5b61a7"),
        },
    }
    ns = git("diff", "--numstat", "origin/main..HEAD", "--", "DESIGN_LOG.md", "AGENTS_LOG.md", "benchmarks/FAILURE_LEDGER.md")
    out["append_only_numstat"] = ns
    out["append_only_violation"] = any(line.split("\t")[1] != "0" for line in ns.splitlines() if line)
    raw = git("diff", "--name-status", "origin/main..HEAD", "--", "benchmarks/exp-runs/")
    out["raw_artifact_non_additions"] = [l for l in raw.splitlines() if l and not l.startswith("A")]
    dest = ROOT / "benchmarks/recovery/checklist_audit_20261107.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("head", "checked", "open", "total", "append_only_violation", "raw_artifact_non_additions")}, indent=2))
    missing_checked = [(i["id"], i["missing_paths"]) for i in items if i["checked"] and i["missing_paths"]]
    print("checked items with missing cited paths:", missing_checked)

if __name__ == "__main__":
    main()
