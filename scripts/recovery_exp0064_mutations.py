#!/usr/bin/env python3
"""exp-0064 mutation matrix for TTExtensionAgnostic.

Each mutant is physically written to the real source, rebuilt, and detected by
the registered tt_extension_identity group and/or the independent interactive
UCI liveness oracle. A semantics-changing mutant is KILLED when its detector
fails. One semantics-preserving CONTROL must SURVIVE, proving the detectors
respond to behaviour rather than to any source edit. Sources are always
restored and rebuilt.
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HPP = ROOT / "src/search/search.hpp"
CPP = ROOT / "src/search/search.cpp"
UCI = ROOT / "src/uci/uci.cpp"
BUILD = ROOT / "build-rel"
PARAMS = "research-data/params_exp0055_race.txt"
EPD = "benchmarks/positions/diagnostic_exp0064_ttid.epd"

HELPER = "    return agnostic ? 0 : extensions;"
PROBE = "tt_.probe(pos.key(), pos.rule50(), context, ttExtensions);"
STORE = "tt_.store(pos.key(), pos.rule50(), context, ttExtensions, bestMove,"
UCIBR = '    else if (key == "ttextensionagnostic") flag = &params_.ttExtensionAgnostic;'

# (name, file, anchor, replacement, detector, expect_killed)
MUTANTS = [
    ("live_path_disabled", HPP, HELPER, "    return extensions;", "cpp", True),
    ("always_agnostic", HPP, HELPER, "    return 0;", "cpp", True),
    ("inverted_switch", HPP, HELPER, "    return agnostic ? extensions : 0;", "cpp", True),
    ("budget_off_by_one", HPP, HELPER, "    return agnostic ? 0 : extensions + 1;", "cpp", True),
    ("shipped_default_on", HPP, "    bool ttExtensionAgnostic = false;",
     "    bool ttExtensionAgnostic = true;", "cpp", True),
    ("probe_only_agnostic_store_keeps_budget", CPP, STORE,
     "tt_.store(pos.key(), pos.rule50(), context, extensions, bestMove,", "cpp", True),
    ("store_only_agnostic_probe_keeps_budget", CPP, PROBE,
     "tt_.probe(pos.key(), pos.rule50(), context, extensions);", "cpp", True),
    ("probe_history_context_dropped", CPP, PROBE,
     "tt_.probe(pos.key(), pos.rule50(), 0, ttExtensions);", "cpp", True),
    ("store_history_context_dropped", CPP, STORE,
     "tt_.store(pos.key(), pos.rule50(), 0, ttExtensions, bestMove,", "cpp", True),
    ("probe_rule50_dropped", CPP, PROBE,
     "tt_.probe(pos.key(), 0, context, ttExtensions);", "cpp", True),
    ("store_rule50_dropped", CPP, STORE,
     "tt_.store(pos.key(), 0, context, ttExtensions, bestMove,", "cpp", True),
    ("uci_option_misdirected", UCI, UCIBR,
     '    else if (key == "ttextensionagnostic") flag = &params_.ttEval;', "uci", True),
    ("uci_option_removed", UCI, UCIBR, "", "uci", True),
    # CONTROL: identical semantics, different spelling. MUST survive.
    ("control_equivalent_rewrite", HPP, HELPER,
     "    if (agnostic) { return 0; }\n    return extensions;", "both", False),
]


def run(cmd, timeout=1800):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def detect(kind: str) -> tuple[bool, str]:
    """Returns (detector_failed, tail)."""
    tails = []
    failed = False
    if kind in ("cpp", "both"):
        b = run(["cmake", "--build", str(BUILD), "-j", "2", "--target", "stockbear_tests"])
        if b.returncode != 0:
            return True, "BUILD_FAILED " + (b.stdout + b.stderr)[-400:]
        t = run([str(BUILD / "stockbear_tests"), "tt_extension_identity"])
        failed = failed or t.returncode != 0
        tails.append("cpp:" + (t.stdout + t.stderr).strip().splitlines()[-1])
    if kind in ("uci", "both"):
        b = run(["cmake", "--build", str(BUILD), "-j", "2", "--target", "stockbear"])
        if b.returncode != 0:
            return True, "BUILD_FAILED " + (b.stdout + b.stderr)[-400:]
        t = run([sys.executable, "scripts/check_tt_extension_identity.py",
                 "--engine", str(BUILD / "stockbear"), "--params", PARAMS,
                 "--epd", EPD, "--liveness"], timeout=300)
        failed = failed or t.returncode != 0
        tails.append("uci:" + (t.stdout + t.stderr).strip().replace("\n", " ")[-220:])
    return failed, " | ".join(tails)


def main() -> int:
    files = [HPP, CPP, UCI]
    original = {f: f.read_text() for f in files}
    results = []
    try:
        for name, path, anchor, replacement, kind, expect_killed in MUTANTS:
            assert anchor in original[path], f"anchor missing: {name}"
            path.write_text(original[path].replace(anchor, replacement, 1))
            failed, tail = detect(kind)
            if expect_killed:
                status = "KILLED" if failed else "SURVIVED"
            else:
                status = "SURVIVED_AS_EXPECTED" if not failed else "CONTROL_BROKEN"
            good = failed == expect_killed
            results.append({"mutant": name, "file": str(path.relative_to(ROOT)),
                            "detector": kind, "expect_killed": expect_killed,
                            "status": status, "good": good, "tail": tail})
            print(f"{name}: {status}", flush=True)
            path.write_text(original[path])
    finally:
        for f in files:
            f.write_text(original[f])
        run(["cmake", "--build", str(BUILD), "-j", "2"])
    bad = [r["mutant"] for r in results if not r["good"]]
    killed = sum(1 for r in results if r["status"] == "KILLED")
    killable = sum(1 for r in results if r["expect_killed"])
    out = {"mechanism": "TTExtensionAgnostic", "mutants": results,
           "killed": killed, "killable": killable, "total": len(results),
           "control_survived": any(r["status"] == "SURVIVED_AS_EXPECTED" for r in results),
           "bad": bad, "verdict": "PASS" if not bad else "FAIL"}
    dest = ROOT / "benchmarks/recovery/exp0064_mutation_matrix.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("killed", "killable", "total",
                                         "control_survived", "bad", "verdict")}))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
