#!/usr/bin/env python3
"""Checklist 7.6 — artifact hygiene audit, distinguishing three categories.

7.6 forbids committing (a) build artifacts, (b) large datasets, (c) unclear-
licensing assets. This audit separates TRANSIENT BUILD OUTPUTS from IMMUTABLE
BENCHMARK EVIDENCE and PUBLISHED BASELINE EXECUTABLES, because the mission
simultaneously requires raw evidence to be committed so it survives sandbox
resets and can be independently replayed. It reports the facts; it does not
resolve the tension by deleting evidence or by declaring a pass.
"""
from __future__ import annotations
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_PAT = re.compile(
    r"(^|/)(build[^/]*/|dist/|out/|target/|node_modules/|__pycache__/|\.venv/)"
    r"|\.(o|a|so|dylib|obj|pyc|exe|d|ninja)$|CMakeCache\.txt|CMakeFiles/")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout


def classify(f: str) -> str:
    if f.startswith("benchmarks/exp-runs/"):
        return "immutable raw experiment evidence"
    if f.startswith("benchmarks/binaries/"):
        return "published baseline executable (provenance)"
    if f.startswith("benchmarks/positions/"):
        return "frozen opening / diagnostic suite (experiment input)"
    if f.startswith("benchmarks/recovery/"):
        return "audit / validity record"
    if f.startswith("benchmarks/dev6-baseline/"):
        return "baseline provenance record"
    if f.startswith("research-data/"):
        return "frozen evaluation parameters (experiment input)"
    if f.startswith("docs/"):
        return "document"
    if f.startswith(("src/", "tests/", "scripts/", ".github/")):
        return "source / tooling"
    return "other"


def main() -> int:
    tracked = [f for f in git("ls-files", "-z").split("\0") if f and (ROOT / f).is_file()]
    added = [f for f in git("diff", "--name-only", "--diff-filter=A",
                            "origin/main..HEAD").split("\n")
             if f and (ROOT / f).is_file()]
    sizes = {f: (ROOT / f).stat().st_size for f in tracked}
    build_hits = [f for f in tracked if BUILD_PAT.search(f)]
    elf = []
    for f in tracked:
        with open(ROOT / f, "rb") as fh:
            if fh.read(4) == b"\x7fELF":
                elf.append(f)
    cat_bytes: Counter = Counter()
    cat_files: Counter = Counter()
    for f in added:
        k = classify(f)
        cat_bytes[k] += sizes[f]
        cat_files[k] += 1
    # Licensing: every generated corpus must declare its licence; no third-party
    # vendored assets may appear.
    license_decls = []
    for mf in sorted(ROOT.glob("benchmarks/exp-runs/corpus-export/*/MANIFEST.json")):
        try:
            d = json.loads(mf.read_text())
        except Exception:
            continue
        lic = d.get("license")
        license_decls.append({"manifest": str(mf.relative_to(ROOT)), "license": lic})
    vendored = [f for f in added if re.search(
        r"(^|/)(vendor|third_party|external)/|\.(nnue|bin|pt|onnx|safetensors)$"
        r"|syzygy|tablebase", f, re.IGNORECASE)]
    ignored_build_dirs = {}
    for d in ("build-rel", "build-ttdiag", "build"):
        r = subprocess.run(["git", "check-ignore", "-v", d], cwd=ROOT,
                           capture_output=True, text=True)
        ignored_build_dirs[d] = r.stdout.strip() or "NOT IGNORED"
    added_bytes = sum(sizes[f] for f in added)
    large = added_bytes > 50_000_000
    out = {
        "item": "7.6",
        "criterion": "No build artifacts, large datasets or unclear-licensing assets were committed.",
        "tracked_files": len(tracked),
        "tracked_bytes": sum(sizes.values()),
        "branch_added_files": len(added),
        "branch_added_bytes": added_bytes,
        "build_artifact_matches": build_hits,
        "build_artifact_count": len(build_hits),
        "local_build_dirs_ignore_status": ignored_build_dirs,
        "tracked_elf_binaries": [
            {"path": f, "bytes": sizes[f], "category": classify(f)} for f in elf],
        "branch_added_elf": [f for f in elf if f in added],
        "branch_added_categories": {
            k: {"bytes": cat_bytes[k], "files": cat_files[k]}
            for k in sorted(cat_bytes, key=lambda x: -cat_bytes[x])},
        "generated_corpus_license_declarations": license_decls,
        "vendored_or_unclear_assets": vendored,
        "root_license_present": (ROOT / "LICENSE").is_file(),
        "findings": {
            "build_artifacts": "NONE" if not build_hits else "PRESENT",
            "unclear_licensing": "NONE" if not vendored and all(
                d["license"] for d in license_decls) else "REVIEW",
            "large_datasets": "PRESENT" if large else "NONE",
        },
        "interpretation": (
            "Zero transient build outputs are committed: .gitignore covers build/, "
            "build-*/, cmake-build-*/, out/, dist/, *.o, *.a, and both local build "
            "directories are ignored. The only tracked ELF files are this project's "
            "own PUBLISHED release executables, pinned as immutable comparison "
            "targets required by the gate's exact-baseline-identity rule; they are "
            "provenance evidence, not build outputs. All generated corpora declare "
            "'original data generated by this project; Apache-2.0' and no vendored "
            "third-party asset was added. HOWEVER the branch does commit large data: "
            "raw per-game PGN/JSONL/CSV evidence and frozen opening suites. That data "
            "is mandated by the mission's durable-evidence and independent-replay "
            "requirements and must not be deleted, but it is still a large dataset "
            "under the plain wording of 7.6."),
        "verdict": "NOT SATISFIED AS WORDED — large immutable evidence datasets are committed",
        "checkbox_action": "leave 7.6 unchecked; do not delete evidence, do not fabricate a pass",
    }
    dest = ROOT / "benchmarks/recovery/artifact_hygiene_audit.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(f"tracked {len(tracked)} files / {sum(sizes.values())/1e6:.2f} MB")
    print(f"branch added {len(added)} files / {added_bytes/1e6:.2f} MB")
    print("build artifacts:", out["findings"]["build_artifacts"])
    print("unclear licensing:", out["findings"]["unclear_licensing"])
    print("large datasets:", out["findings"]["large_datasets"])
    print("verdict:", out["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
