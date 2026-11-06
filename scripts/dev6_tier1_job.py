#!/usr/bin/env python3
"""One preregistered Tier-1 benchmark job on a GitHub-hosted isolated VM.

Design invariants (see .github/workflows/dev6-tier1.yml and
docs/DEV6_RESEARCH_MATRIX.md):
  * NO git pushes, NO result commits. Evidence is written to one directory and
    uploaded by the workflow as a GitHub Actions artifact.
  * The EXACT packaged candidate binary is extracted from the package and is
    the binary that plays the match (Gate 4).
  * The source SHA, prereg SHA, build flags, package/binary SHA, opening SHA,
    seeds, time control and options are pinned in a fingerprint + manifest.
  * Retries cannot silently change conditions: all conditions derive from the
    pinned source_sha and the frozen plan in that commit.
"""
import argparse, hashlib, json, os, platform, re, shutil, subprocess, sys, tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import match_stats

DEV5 = ROOT / "benchmarks/binaries/stockbear-dev5-release"
DEV5_SHA = "391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918"
DEFAULT_BENCH = "243f9a1c1ba5b36f"
DEFAULT_FLAGS = "-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4"
CHAMPION = ["EvalParams=research-data/params_abc.txt", "TTEval=true"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tool(name):
    found = shutil.which(name)
    if found:
        return found
    local = Path(sys.executable).parent / name
    return str(local) if local.exists() else name


def run(cmd, **kw):
    print("+ " + " ".join(str(x) for x in cmd), flush=True)
    kw.setdefault("cwd", ROOT)
    return subprocess.run([str(x) for x in cmd], **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True, help="JSON job spec from the frozen plan")
    ap.add_argument("--source-sha", required=True)
    ap.add_argument("--experiment-id", required=True)
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    ap.add_argument("--run-attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    a = ap.parse_args()
    job = json.loads(a.job)
    job_id = job["id"]
    out = ROOT / "benchmarks/exp-runs" / f"tier1-{a.experiment_id}-{job_id}"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    log = open(out / "run.log", "w", buffering=1)
    def say(*x):
        print(*x, file=log, flush=True)
        print(*x, flush=True)

    # ---- 1. pinned source / frozen prereg / immutable baseline -------------
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    say("source_sha pinned", a.source_sha, "actual", head)
    assert head == a.source_sha, "source SHA mismatch: benchmark must run on the pinned commit"
    prereg = ROOT / job.get("prereg", f"docs/DEV6_PREREG_{a.experiment_id.upper()}.md")
    assert prereg.is_file(), f"frozen prereg missing: {prereg}"
    prereg_sha = sha(prereg)
    # The plan pins the prereg digest it was frozen against. Enforce it, do not
    # merely record it: otherwise the prereg could be edited after freezing and
    # the job would still run and still stamp the NEW digest into its manifest,
    # silently laundering a post-hoc protocol change into "frozen" evidence.
    expected_prereg_sha = job.get("prereg_sha256")
    assert expected_prereg_sha, f"job {job_id} does not pin prereg_sha256"
    assert prereg_sha == expected_prereg_sha, (
        f"frozen prereg CHANGED: plan pins {expected_prereg_sha}, "
        f"{prereg.relative_to(ROOT)} is {prereg_sha}")
    say("frozen prereg SHA VERIFIED against plan", prereg_sha)
    assert sha(DEV5) == DEV5_SHA, "immutable dev5 baseline binary changed"
    say("prereg", prereg.relative_to(ROOT), prereg_sha)
    say("dev5 baseline sha256", DEV5_SHA, "VERIFIED")

    # ---- 2. build candidate from the pinned source --------------------------
    flags = job.get("build_flags", DEFAULT_FLAGS)
    build = ROOT / f"build-tier1-{job_id}"
    if build.exists():
        shutil.rmtree(build)
    cmake, ninja = tool("cmake"), tool("ninja")
    r = run([cmake, "-S", ".", "-B", build, "-G", "Ninja",
             "-DCMAKE_BUILD_TYPE=Release", f"-DCMAKE_CXX_FLAGS={flags}",
             "-DCMAKE_MAKE_PROGRAM=" + ninja, "-DSTOCKBEAR_BUILD_TESTS=OFF"],
            stdout=log, stderr=subprocess.STDOUT)
    assert r.returncode == 0, "cmake configure failed"
    r = run([cmake, "--build", build, "-j", "2", "--target", "stockbear"],
            stdout=log, stderr=subprocess.STDOUT)
    assert r.returncode == 0, "candidate build failed"
    built = build / "stockbear"
    built_sha = sha(built)
    say("candidate built sha256", built_sha, "flags", flags)

    def bench(extra=()):
        p = subprocess.run([str(built), "bench", *extra], cwd=ROOT,
                           capture_output=True, text=True, timeout=300)
        m = re.findall(r"signature\s+([0-9a-f]{8,})", p.stdout + p.stderr)
        return m[-1] if m else ""

    sig = bench()
    say("default bench signature", sig)
    assert sig == DEFAULT_BENCH, f"candidate changed shipped bench signature: {sig}"

    # ---- 3. PACKAGE the candidate and test the EXTRACTED binary ------------
    pkg = out / f"stockbear-dev6-{built_sha[:12]}.tar.gz"
    staging = ROOT / f"package-tier1-{job_id}"
    if staging.exists():
        shutil.rmtree(staging)
    (staging / "research-data").mkdir(parents=True)
    shutil.copy2(built, staging / "stockbear")
    shutil.copy2(ROOT / "research-data/params_abc.txt", staging / "research-data/params_abc.txt")
    info = {
        "source_sha": head, "experiment_id": a.experiment_id, "job_id": job_id,
        "workflow_run_id": a.run_id, "run_attempt": a.run_attempt,
        "build_flags": flags, "compiler": subprocess.run(
            ["c++", "--version"], capture_output=True, text=True).stdout.splitlines()[0],
        "cmake": subprocess.run([cmake, "--version"], capture_output=True, text=True).stdout.splitlines()[0],
        "runner": {"os": os.environ.get("RUNNER_OS", ""), "nproc": os.cpu_count(),
                   "platform": platform.platform()},
        "binary_sha256": built_sha,
        "params_sha256": sha(ROOT / "research-data/params_abc.txt"),
        "default_bench_signature": sig,
        "build_command": f"cmake -S . -B build-tier1 -G Ninja -DCMAKE_BUILD_TYPE=Release "
                         f"-DCMAKE_CXX_FLAGS='{flags}' -DSTOCKBEAR_BUILD_TESTS=OFF && "
                         f"cmake --build build-tier1 -j2 --target stockbear",
    }
    (staging / "BUILD_INFO.json").write_text(json.dumps(info, indent=2) + "\n")
    lines = []
    for rel in ("stockbear", "research-data/params_abc.txt", "BUILD_INFO.json"):
        lines.append(f"{sha(staging / rel)}  {rel}")
    (staging / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")
    (staging / "README.txt").write_text(
        "StockBear v0.1.0-dev6 Tier-1 candidate package.\n"
        "The extracted ./stockbear is the EXACT binary used in this job's matches.\n"
        "Verify with: sha256sum -c SHA256SUMS.txt\n")
    with tarfile.open(pkg, "w:gz") as t:
        for f in sorted(staging.rglob("*")):
            t.add(f, arcname=str(f.relative_to(staging)))
    pkg_sha = sha(pkg)
    extracted_dir = ROOT / f"build-tier1-pkg-{job_id}"
    if extracted_dir.exists():
        shutil.rmtree(extracted_dir)
    extracted_dir.mkdir(parents=True)
    with tarfile.open(pkg) as t:
        t.extractall(extracted_dir)
    candidate = extracted_dir / "stockbear"
    candidate.chmod(0o755)
    assert sha(candidate) == built_sha, "packaged binary differs from built binary"
    chk = subprocess.run(["sha256sum", "-c", "SHA256SUMS.txt"], cwd=extracted_dir,
                         capture_output=True, text=True)
    say("package sha256", pkg_sha)
    say("package checksum verification:", chk.stdout.strip())
    assert chk.returncode == 0, "package SHA256SUMS verification failed"
    say("GATE 4 BINARY IDENTITY: tested binary == packaged binary == built binary", built_sha)

    # ---- 4. optional correctness gate --------------------------------------
    if job.get("ctest", False):
        tb = ROOT / f"build-tier1-tests-{job_id}"
        if tb.exists():
            shutil.rmtree(tb)
        r = run([cmake, "-S", ".", "-B", tb, "-G", "Ninja",
                 "-DCMAKE_BUILD_TYPE=Release", f"-DCMAKE_CXX_FLAGS={flags}",
                 "-DCMAKE_MAKE_PROGRAM=" + ninja,
                 "-DSTOCKBEAR_BUILD_TESTS=ON", "-DSTOCKBEAR_REQUIRE_PYTHON_TESTS=ON"],
                stdout=log, stderr=subprocess.STDOUT)
        assert r.returncode == 0
        r = run([cmake, "--build", tb, "-j", "2"], stdout=log, stderr=subprocess.STDOUT)
        assert r.returncode == 0
        r = run([tool("ctest"), "--output-on-failure"], cwd=tb,
                stdout=log, stderr=subprocess.STDOUT)
        assert r.returncode == 0, "ctest failed"
        say("ctest PASS")
    uci = subprocess.run([str(candidate)], cwd=ROOT, input="uci\nquit\n",
                         capture_output=True, text=True, timeout=30)
    (out / "uci.txt").write_text(uci.stdout)
    say("candidate UCI default switches:",
        [l for l in uci.stdout.splitlines() if "ProbCut" in l or "BadCapturePruning" in l])

    # ---- 5. match ----------------------------------------------------------
    games = int(job.get("games", 0))
    assert games > 0 and games % 2 == 0, "games must be a positive even number"
    openings = ROOT / job["openings"]
    assert openings.is_file(), f"opening suite missing: {openings}"
    opening_sha = sha(openings)
    control = job.get("control", {"base_ms": 40, "inc_ms": 4})
    a_opts = job.get("a_options", CHAMPION)
    b_opts = job.get("b_options", CHAMPION)
    engines = {"candidate": candidate, "baseline": DEV5}
    ea = engines.get(job.get("engine_a", "candidate"), job.get("engine_a"))
    eb = engines.get(job.get("engine_b", "baseline"), job.get("engine_b"))
    if job.get("null", False):
        ea = eb = candidate
        b_opts = list(a_opts)
    assert Path(ea).is_file() and Path(eb).is_file(), "engine binary missing"
    cmd = [sys.executable, str(ROOT / "scripts/tournament.py"),
           "--engine-a", ea, "--engine-b", eb,
           "--games", games, "--hash", job.get("hash", 16),
           "--threads", job.get("threads", 1), "--max-plies", job.get("max_plies", 240),
           "--openings", openings, "--seed", job["seed"],
           "--pgn", out / "match.pgn", "--jsonl", out / "match.jsonl", "--csv", out / "match.csv"]
    if "nodes" in control:
        cmd += ["--nodes", control["nodes"], "--nodes-jitter", control.get("nodes_jitter", 0.15)]
    else:
        cmd += ["--base-ms", control.get("base_ms", 40), "--inc-ms", control.get("inc_ms", 4)]
    for o in a_opts:
        cmd += ["--a-option", o]
    for o in b_opts:
        cmd += ["--b-option", o]
    r = run(cmd, stdout=log, stderr=subprocess.STDOUT)
    assert r.returncode == 0, f"tournament failed with {r.returncode}"

    # ---- 6. independent recomputation from raw JSONL ------------------------
    recs = [json.loads(l) for l in (out / "match.jsonl").read_text().splitlines()
            if '"game"' in l]
    recs.sort(key=lambda x: x["game"])
    pairs, pair_openings = [], []
    for k in range(0, len(recs) - 1, 2):
        x, y = recs[k], recs[k + 1]
        if x["score_a"] is not None and y["score_a"] is not None:
            pairs.append(x["score_a"] + y["score_a"])
            pair_openings.append(x["opening"])
    game_scores = [x["score_a"] for x in recs if x["score_a"] is not None]
    s = match_stats.summarise(game_scores, pairs,
                              match_stats.lmr_step(pairs, 0.0, 5.0),
                              pair_openings=pair_openings)
    cl = s.get("opening_clustered", {})
    terms = {}
    for x in recs:
        t = x.get("termination", "?")
        terms[t] = terms.get(t, 0) + 1
    score = (s["wins"] + 0.5 * s["draws"]) / max(1, len(game_scores))
    independent_elo = match_stats.finite_or_none(match_stats.score_to_elo(score))
    summary = {
        "job_id": job_id, "experiment_id": a.experiment_id, "games": len(game_scores),
        "unadjudicated": len(recs) - len(game_scores),
        "wins": s["wins"], "draws": s["draws"], "losses": s["losses"],
        "score": score,
        "elo": cl.get("elo_difference"), "ci95": cl.get("elo_ci95"),
        "clusters": cl.get("clusters"), "terminations": terms,
        "time_forfeit": sum(v for k, v in terms.items() if "FORFEIT" in k.upper()),
        "illegal": sum(v for k, v in terms.items() if "ILLEGAL" in k.upper()),
        "engine_failure": sum(v for k, v in terms.items() if "FAILURE" in k.upper()),
        "independent_elo_from_score": independent_elo,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    with open(out / "audit.txt", "w") as fh:
        fh.write("INDEPENDENT RECOMPUTATION FROM RAW match.jsonl\n")
        fh.write(f"records={len(recs)} adjudicated={len(game_scores)} pairs={len(pairs)} "
                 f"clusters={cl.get('clusters')}\n")
        fh.write(f"W/D/L = {s['wins']}/{s['draws']}/{s['losses']} score={summary['score']:.6f}\n")
        fh.write(f"CR1/t opening-clustered Elo = {cl.get('elo_difference')} "
                 f"95% CI = {cl.get('elo_ci95')}\n")
        fh.write(f"independent Elo-from-score  = {independent_elo}\n")
        fh.write(f"terminations = {json.dumps(terms, sort_keys=True)}\n")
        fh.write(f"TIME_FORFEIT={summary['time_forfeit']} ILLEGAL={summary['illegal']} "
                 f"ENGINE_FAILURE={summary['engine_failure']}\n")
    say("SUMMARY", json.dumps({k: summary[k] for k in
        ("games", "wins", "draws", "losses", "elo", "ci95", "clusters",
         "time_forfeit", "illegal", "engine_failure")}))

    # ---- 7. fingerprint + manifest + checksums -----------------------------
    fingerprint = {
        "source_sha": head, "prereg_sha256": prereg_sha,
        "plan_job": job, "build_flags": flags,
        "built_binary_sha256": built_sha, "packaged_binary_sha256": sha(candidate),
        "package_sha256": pkg_sha, "dev5_sha256": DEV5_SHA,
        "opening_suite_sha256": opening_sha, "control": control,
        "a_options": a_opts, "b_options": b_opts,
        "engine_a": str(ea), "engine_b": str(eb),
        "default_bench_signature": sig,
    }
    fp = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()
    (out / "fingerprint.json").write_text(json.dumps(
        {"fingerprint_sha256": fp, **fingerprint}, indent=2) + "\n")
    manifest = {
        "workflow_run_id": a.run_id, "workflow_run_attempt": a.run_attempt,
        "job_id": job_id, "experiment_id": a.experiment_id,
        "source_sha": head, "runner": info["runner"], "toolchain": {
            "compiler": info["compiler"], "cmake": info["cmake"]},
        "fingerprint_sha256": fp,
        "artifact_channel": "GitHub Actions artifact; export mode mirrors to git "
                            "for Contents-API retrieval (blob CDN blocked)",
        "benchmark_scripts_never_push": True,
        "summary": summary,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    sums = []
    for f in sorted(out.rglob("*")):
        if f.is_file() and f.name not in ("SHA256SUMS.txt", "run.log"):
            sums.append(f"{sha(f)}  {f.relative_to(out)}")
    (out / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n")
    say("fingerprint", fp)
    say("evidence files", len(sums) + 2, "under", out.relative_to(ROOT))
    say("=== Tier-1 job COMPLETE ===")
    log.close()


if __name__ == "__main__":
    main()
