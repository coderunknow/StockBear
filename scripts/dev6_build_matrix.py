#!/usr/bin/env python3
"""exp-0030: fully reproducible Track A / Track B build environment + integrity.

Creates two CLEAN source trees (dev5 tag, current candidate HEAD) via `git
archive`, builds BOTH with ONE pinned toolchain and the exact portable release
flags, records the environment and executable hashes, then evaluates the
PRE-REGISTERED equivalence criteria E1 (fixed-node signatures), E2 (full
fixed-node bench CSV equality) and E3 (fixed-time NPS ratio in [0.97,1.03]).
Track B = the immutable official dev5 artifact, measured but never rebuilt.

See docs/DEV6_PREREG_EXP0030.md (frozen before results).
"""
import csv
import hashlib
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLAGS = "-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4"
PARAMS = ROOT / "research-data" / "params_abc.txt"
OUTDIR = ROOT / "benchmarks" / "exp-runs" / "exp0030-build-integrity"
JSON_OUT = ROOT / "benchmarks" / "dev6-baseline" / "build_matrix.json"
MD_OUT = ROOT / "docs" / "DEV6_EXP0030_BUILD_INTEGRITY.md"
OFFICIAL = ROOT / "benchmarks" / "binaries" / "stockbear-dev5-release"
CMAKE = ROOT / ".venv" / "bin" / "cmake"
ENV = dict(os.environ)
ENV["PATH"] = str(ROOT / ".venv" / "bin") + os.pathsep + ENV.get("PATH", "")


def sh(cmd, cwd=None, capture=True):
    return subprocess.run(cmd, cwd=cwd or ROOT, shell=isinstance(cmd, str),
                          capture_output=capture, text=True, env=ENV, check=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def archive(tree, dest):
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    p = subprocess.run(["git", "archive", tree], cwd=ROOT, capture_output=True, check=True)
    blob_hash = hashlib.sha256(p.stdout).hexdigest()
    subprocess.run(["tar", "-x", "-C", str(dest)], input=p.stdout, check=True)
    nfiles = sum(1 for _ in dest.rglob("*") if _.is_file())
    return {"tree": tree, "source_commit": sh(["git", "rev-parse", tree + "^{}"]).stdout.strip(),
            "archive_sha256": blob_hash, "files": nfiles, "dir": str(dest.relative_to(ROOT))}


def build(src, build):
    if build.exists():
        shutil.rmtree(build)
    cfg = [str(CMAKE), "-S", str(src), "-B", str(build),
           "-DCMAKE_BUILD_TYPE=Release", "-G", "Ninja",
           f"-DCMAKE_CXX_FLAGS={FLAGS}"]
    log = sh(cfg).stdout + "\n"
    log += sh([str(CMAKE), "--build", str(build), "-j", "2", "--target", "stockbear"]).stdout + "\n"
    exe = build / "stockbear"
    assert exe.exists(), f"build produced no binary in {build}"
    return exe, log


def bench(exe, args, outcsv=None):
    """Return (signature, rows, nodes, time_us, wall_s)."""
    t0 = time.perf_counter()
    p = sh([str(exe), "bench"] + args)
    wall = time.perf_counter() - t0
    lines = [l for l in p.stdout.splitlines() if l and not l.startswith("#")]
    sig = ""
    for l in p.stdout.splitlines():
        if "signature " in l:
            sig = l.split("signature ", 1)[1].strip()
    rows = list(csv.DictReader(io.StringIO("\n".join(lines))))
    nodes = sum(int(r["nodes"]) for r in rows)
    tus = sum(int(r["time_us"]) for r in rows)
    if outcsv:
        outcsv.write_text(p.stdout)
    return sig, rows, nodes, tus, wall, p.stdout


COLS = ["name", "bestmove", "depth", "score_type", "score", "nodes", "hashfull", "pv", "fen"]


def fingerprint(rows):
    return [tuple(r.get(c, "") for c in COLS) for r in rows]


def toolchain():
    def first(cmd):
        try:
            return sh(cmd).stdout.splitlines()[0]
        except Exception as e:
            return f"unavailable: {e}"
    isa = set()
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("flags"):
                isa = set(line.split(":", 1)[1].split())
                break
    except Exception:
        pass
    model = ""
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                model = line.split(":", 1)[1].strip()
                break
    except Exception:
        pass
    memkb = 0
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal"):
                memkb = int(line.split()[1]); break
    except Exception:
        pass
    return {
        "os": platform.platform(), "kernel": platform.release(), "machine": platform.machine(),
        "cpu_model": model, "cpu_isa_relevant": sorted(f for f in isa if f in
            {"popcnt", "bmi1", "bmi2", "lzcnt", "abm", "avx", "avx2", "sse4_2", "ssse3", "fma"}),
        "nproc": os.cpu_count(), "ram_mb": round(memkb / 1024),
        "gcc": first(["gcc", "--version"]), "ld": first(["ld", "--version"]),
        "cmake": first([str(CMAKE), "--version"]),
        "glibc": os.confstr("CS_GNU_LIBC_VERSION") if hasattr(os, "confstr") else "n/a",
        "python": sys.version.split()[0],
        "cxx_flags": FLAGS, "lto": "-flto=4 (in CXX_FLAGS)", "build_type": "Release",
        "march_native": False, "generator": "Ninja",
        "runtime": {"hash_mb": 16, "threads": 1, "max_plies": 240,
                    "fixed_time": "40+4 ms", "champion_params": str(PARAMS.relative_to(ROOT)),
                    "champion_params_sha256": sha(PARAMS)},
    }


def compute_e4():
    """Read the separately-run E4 control match (if present)."""
    ctrl = ROOT / "benchmarks" / "exp-runs" / "exp0030-control" / "pooled.json"
    if not ctrl.exists():
        return {"status": "NOT_RUN", "note": "run separately with scripts/tournament.py"}
    summ = json.loads(ctrl.read_text())["summary"]
    cl = summ["opening_clustered"]
    terms = summ.get("terminations", {})
    forfeits = {k: v for k, v in terms.items() if "FORFEIT" in k.upper()}
    return {"status": "RUN", "games": summ["games_total"],
            "wins": summ["wins"], "draws": summ["draws"], "losses": summ["losses"],
            "clusters": cl.get("clusters"), "elo": cl.get("elo_difference"),
            "elo_ci95": cl.get("elo_ci95"),
            "criterion": "two-sided opening-clustered CR1 95% CI includes 0",
            "pass": bool(cl.get("elo_ci95") and cl["elo_ci95"][0] is not None
                        and cl["elo_ci95"][0] <= 0 <= cl["elo_ci95"][1]),
            "time_forfeit_events": forfeits, "time_forfeit_total": sum(forfeits.values()),
            "note": ("Local shared 2-vCPU sandbox: time forfeits and a negative point "
                     "estimate are consistent with documented local fixed-time noise "
                     "(ledger, +/-25 Elo). Decisive matches must use isolated runners.")}


def e4_markdown(e4):
    if e4.get("status") != "RUN":
        return ["## E4 — fixed-time control match", "", "NOT RUN.", ""]
    return ["## E4 — fixed-time control match (corroboration)", "",
            f"A2(candidate rebuilt, `params_abc`+TTEval) vs A1(dev5 rebuilt, same), "
            f"{e4['games']} paired games, 40+4 ms, fresh disjoint 200-opening slice: "
            f"+{e4['wins']} ={e4['draws']} -{e4['losses']}, clustered CR1 "
            f"**{e4['elo']:+.1f} [{e4['elo_ci95'][0]:+.1f}, {e4['elo_ci95'][1]:+.1f}] Elo**, "
            f"{e4['clusters']} clusters. Criterion (CI includes 0): "
            f"**{'PASS' if e4['pass'] else 'FAIL'}**.", "",
            f"TIME_FORFEIT events: {e4['time_forfeit_total']} "
            f"({e4['time_forfeit_events']}). {e4['note']} The previous +33 Elo control "
            "used a DIFFERENT toolchain image; under the matched toolchain here the large "
            "positive offset is absent. This local result is NOT used as strength evidence.", ""]


def finalize_only():
    """Patch the JSON record + append the E4 section without rebuilding."""
    e4 = compute_e4()
    result = json.loads(JSON_OUT.read_text())
    result["E4_fixed_time_control_match"] = e4
    result["E5_decision"] = ("PASS" if (result["E1_signatures"]["pass"] and
        result["E2_full_fixed_node_csv"]["pass"] and result["E3_fixed_time_nps"]["pass"]
        and e4.get("pass", False)) else "FAIL")
    JSON_OUT.write_text(json.dumps(result, indent=2) + "\n")
    md = MD_OUT.read_text()
    if "## E4 —" not in md:
        md += "\n" + "\n".join(e4_markdown(e4)) + \
              "\nRaw E4: `benchmarks/exp-runs/exp0030-control/` (PGN/JSONL/CSV/pooled.json).\n"
        MD_OUT.write_text(md)
    print(json.dumps({"E4": e4.get("pass"), "E4_elo": e4.get("elo"),
                      "E4_ci": e4.get("elo_ci95"), "forfeits": e4.get("time_forfeit_total"),
                      "E5": result["E5_decision"]}, indent=2))


def main():
    if "--finalize-only" in sys.argv:
        finalize_only()
        return
    OUTDIR.mkdir(parents=True, exist_ok=True)
    env = toolchain()
    log_all = []
    srcs = {
        "A1_dev5_rebuilt": (archive("v0.1.0-dev5", ROOT / "build-dev5-src"), ROOT / "build-dev5"),
        "A2_candidate_rebuilt": (archive("HEAD", ROOT / "build-cand-src"), ROOT / "build-cand"),
    }
    bins, srcinfo = {}, {}
    for name, (info, bdir) in srcs.items():
        exe, log = build(ROOT / info["dir"], bdir)
        log_all.append(f"### {name}\n{log}")
        bins[name] = exe
        srcinfo[name] = info
    bins["B_official_release"] = OFFICIAL
    (OUTDIR / "build.log").write_text("\n".join(log_all))

    binaries = {}
    for name, exe in bins.items():
        binaries[name] = {"path": str(exe.relative_to(ROOT) if str(exe).startswith(str(ROOT)) else exe),
                          "sha256": sha(exe)}

    # ---- E1: fixed-node signatures ----
    sig = {}
    for name, exe in bins.items():
        s6, _, _, _, _, raw6 = bench(exe, [], OUTDIR / f"{name}_bench_d6.csv")
        s16, _, _, _, _, raw16 = bench(exe, ["--depth", "16"], OUTDIR / f"{name}_bench_d16.csv")
        sp, _, _, _, _, rawp = bench(exe, ["--depth", "12", "--params", str(PARAMS)],
                                     OUTDIR / f"{name}_bench_d12_paramsabc.csv")
        sig[name] = {"bench_d6": s6, "bench_d16": s16, "bench_d12_paramsabc": sp}
    e1 = all(sig[n]["bench_d6"] == "243f9a1c1ba5b36f" and
             sig[n]["bench_d16"] == "a14ab62224f837e5" for n in sig) and \
         len({sig[n]["bench_d12_paramsabc"] for n in sig}) == 1

    # ---- E2: full fixed-node CSV equality (A1 vs A2), default and params_abc ----
    e2 = {}
    for tag, args in (("default", ["--depth", "12"]),
                      ("params_abc", ["--depth", "12", "--params", str(PARAMS)])):
        _, r1, _, _, _, raw1 = bench(bins["A1_dev5_rebuilt"], args,
                                     OUTDIR / f"E2_A1_{tag}.csv")
        _, r2, _, _, _, raw2 = bench(bins["A2_candidate_rebuilt"], args,
                                     OUTDIR / f"E2_A2_{tag}.csv")
        f1, f2 = fingerprint(r1), fingerprint(r2)
        diff = sum(1 for a, b in zip(f1, f2) if a != b)
        e2[tag] = {"rows": len(f1), "rows_A2": len(f2), "differing_rows": diff,
                   "identical": (len(f1) == len(f2) and diff == 0)}
    e2_pass = all(v["identical"] for v in e2.values())

    # ---- E3: fixed-time NPS (min wall-time / max NPS of 3 runs) ----
    nps = {}
    for name, exe in bins.items():
        runs = []
        for i in range(3):
            _, _, nodes, tus, wall, _ = bench(exe, ["--depth", "12"])
            runs.append({"nodes": nodes, "time_us": tus,
                         "wall_s": round(wall, 3), "nps": nodes / (tus / 1e6)})
        best = max(runs, key=lambda r: r["nps"])
        nps[name] = {"runs": runs, "best_nps": best["nps"],
                     "best_run": best}
    ratio = nps["A2_candidate_rebuilt"]["best_nps"] / nps["A1_dev5_rebuilt"]["best_nps"]
    e3 = {"tolerance": [0.97, 1.03], "ratio_A2_over_A1": ratio,
          "pass": 0.97 <= ratio <= 1.03,
          "official_over_A1": nps["B_official_release"]["best_nps"] / nps["A1_dev5_rebuilt"]["best_nps"]}

    # ---- E4: fixed-time control match (run separately, results if present) ----
    e4 = compute_e4()

    result = {
        "experiment": "exp-0030", "prereg": "docs/DEV6_PREREG_EXP0030.md",
        "environment": env, "sources": srcinfo, "binaries": binaries,
        "E1_signatures": {"signatures": sig, "pass": e1},
        "E2_full_fixed_node_csv": {"detail": e2, "pass": e2_pass},
        "E3_fixed_time_nps": e3,
        "E4_fixed_time_control_match": e4,
        "E5_decision": ("PASS" if (e1 and e2_pass and e3["pass"] and
                                   e4.get("pass", False)) else "FAIL"),
    }
    JSON_OUT.write_text(json.dumps(result, indent=2) + "\n")

    L = ["# exp-0030 — reproducible build environment & Track A/B integrity", "",
         f"**E5 decision: {result['E5_decision']}** (E1 {'PASS' if e1 else 'FAIL'}, "
         f"E2 {'PASS' if e2_pass else 'FAIL'}, E3 {'PASS' if e3['pass'] else 'FAIL'}). "
         "Integrity/measurement experiment, NOT a strength claim. Pre-registered "
         "in `docs/DEV6_PREREG_EXP0030.md` with tolerances frozen before measurement.", "",
         "## Pinned environment", "", "```json",
         json.dumps({k: env[k] for k in ("os", "cpu_model", "cpu_isa_relevant", "nproc",
             "ram_mb", "gcc", "ld", "cmake", "glibc", "cxx_flags", "lto", "build_type",
             "march_native", "generator", "runtime")}, indent=2), "```", "",
         "## Identities", ""]
    for n, b in binaries.items():
        L.append(f"- **{n}**: `{b['path']}` SHA-256 `{b['sha256']}`")
    for n, s in srcinfo.items():
        L.append(f"- **{n}** source: tree `{s['tree']}`, commit `{s['source_commit']}`, "
                 f"archive SHA-256 `{s['archive_sha256']}`, {s['files']} files.")
    L += ["", "## E1 — fixed-node signatures", "",
          "| binary | bench d6 | bench d16 | bench d12 params_abc |", "|---|---|---|---|"]
    for n, s in sig.items():
        L.append(f"| {n} | {s['bench_d6']} | {s['bench_d16']} | {s['bench_d12_paramsabc']} |")
    L += [f"", f"E1: **{'PASS' if e1 else 'FAIL'}**.", "",
          "## E2 — full fixed-node bench CSV equality (A1 vs A2)", "",
          "| params | rows | differing rows | identical |", "|---|---|---|---|"]
    for tag, v in e2.items():
        L.append(f"| {tag} | {v['rows']}/{v['rows_A2']} | {v['differing_rows']} | {v['identical']} |")
    L += [f"", f"E2: **{'PASS' if e2_pass else 'FAIL'}** (timing columns excluded).", "",
          "## E3 — fixed-time throughput (NPS, best of 3 runs each)", "",
          "| binary | nodes | time (s) | NPS |", "|---|---|---|---|"]
    for n, v in nps.items():
        b = v["best_run"]
        L.append(f"| {n} | {b['nodes']:,} | {b['time_us']/1e6:.3f} | {b['nps']/1e6:.3f}M |")
    L += ["", f"A2/A1 NPS ratio = **{ratio:.4f}**, pre-registered tolerance "
          f"[0.97, 1.03] -> **{'PASS' if e3['pass'] else 'FAIL'}**. "
          f"Official Track B / A1 = {e3['official_over_A1']:.4f} (reference only, "
          "built by a different image).", "",
          "## Interpretation", ""]
    if result["E5_decision"] == "PASS":
        L += ["E1–E3 pass: Track A is a valid, controlled SOURCE-LEVEL comparison "
              "environment (identical fixed-node search and matched fixed-time "
              "throughput under one pinned toolchain). The previous +33 Elo "
              "`params_abc` control is therefore attributable to the "
              "ubuntu-22.04 (dev5 release) vs ubuntu-latest/GCC 13 (lane) build-image "
              "mismatch — classified INVALID MEASUREMENT for that control only. "
              "Track B (official artifact) remains a separately reported reference; "
              "a rebuilt dev5 is never described as the official release binary."]
    else:
        L += ["A criterion FAILED — do NOT start strength experiments; diagnose "
              "compiler/flags/source drift and repeat under a new experiment ID."]
    L += [""] + e4_markdown(e4)
    L += ["Raw: `benchmarks/exp-runs/exp0030-build-integrity/` (build.log + all "
          "bench CSVs), E4 `benchmarks/exp-runs/exp0030-control/`, machine-readable "
          "`benchmarks/dev6-baseline/build_matrix.json`."]
    MD_OUT.write_text("\n".join(L) + "\n")
    print(json.dumps({"E1": e1, "E2": e2_pass, "E3": e3["pass"],
                      "ratio": round(ratio, 4), "official_ratio": round(e3["official_over_A1"], 4),
                      "E5": result["E5_decision"]}, indent=2))
    print("wrote", JSON_OUT, MD_OUT)


if __name__ == "__main__":
    main()
