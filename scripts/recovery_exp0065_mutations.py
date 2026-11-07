#!/usr/bin/env python3
"""exp-0065 mutation matrix for PersistentHistory. Detector = registered
persistent_history group (plus the interactive UCI check for wiring mutants).
Semantics-changing mutants must be KILLED; one equivalence control must SURVIVE."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CPP = ROOT / "src/search/search.cpp"
UCI = ROOT / "src/uci/uci.cpp"
BUILD = ROOT / "build-rel"
COND = "    if (params_.persistentHistory) {"
DECAY = "                for (int& value : row) value /= 2;"
EVALSTACK = "    std::fill(std::begin(evalStack_), std::end(evalStack_), 0);"
REUSE = "                if (params_.persistentHistory) {\n                    if (!persistentSearch_)"
NEWGAME = "            persistentSearch_.reset();"

MUTANTS = [
    ("live_path_disabled", CPP, COND, "    if (false) {", True, "cpp"),
    ("always_persistent", CPP, COND, "    if (true) {", True, "cpp"),
    ("decay_removed", CPP, DECAY, "                for (int& value : row) value /= 1;", True, "cpp"),
    ("decay_applied_twice", CPP, DECAY,
     "                for (int& value : row) { value /= 2; value /= 2; }", True, "cpp"),
    ("decay_sign_flip", CPP, DECAY, "                for (int& value : row) value = -value / 2;", True, "cpp"),
    ("decay_only_one_color", CPP,
     "        for (auto& color : history_)\n            for (auto& row : color)\n                for (int& value : row) value /= 2;",
     "        for (auto& color : history_)\n            for (auto& row : color)\n                for (int& value : row) value = (&color == &history_[0]) ? value / 2 : value;", True, "cpp"),
    ("uci_option_misdirected", UCI,
     '    else if (key == "persistenthistory") flag = &params_.persistentHistory;',
     '    else if (key == "persistenthistory") flag = &params_.ttEval;', True, "uci"),
    ("object_not_reused", UCI, REUSE,
     "                if (false) {\n                    if (!persistentSearch_)", True, "uci"),
    ("ucinewgame_does_not_reset", UCI, NEWGAME, "", True, "uci"),
    # EQUIVALENCE CONTROL, not a killable mutant: search.cpp writes
    # evalStack_[ply] = staticEval (line 622) BEFORE the only read (line 628),
    # and that read is guarded by ply >= 2, so evalStack_[ply-2] was always
    # written earlier in the SAME search. Stale values can never be read; the
    # unconditional clear is defensive hardening with no observable behaviour.
    ("control_evalstack_clear_is_defensive", CPP, EVALSTACK, "", False, "cpp"),
    ("control_equivalent_decay_rewrite", CPP, DECAY,
     "                for (int& value : row) { const int v = value; value = v / 2; }", False, "cpp"),
]


def run(cmd, timeout=1800):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def main():
    files = [CPP, UCI]
    original = {f: f.read_text() for f in files}
    results = []
    try:
        for name, path, anchor, repl, expect_killed, detector in MUTANTS:
            assert anchor in original[path], f"anchor missing: {name}"
            path.write_text(original[path].replace(anchor, repl, 1))
            target = "stockbear" if detector == "uci" else "stockbear_tests"
            b = run(["cmake", "--build", str(BUILD), "-j", "2", "--target", target])
            if b.returncode != 0:
                failed, tail = True, "BUILD_FAILED " + (b.stdout + b.stderr)[-300:]
            elif detector == "uci":
                t = run([sys.executable, "scripts/check_persistent_history_uci.py",
                         "--engine", str(BUILD / "stockbear"),
                         "--params", "research-data/params_exp0055_race.txt"], timeout=300)
                failed = t.returncode != 0
                tail = (t.stdout + t.stderr).strip().replace("\n", " ")[-200:]
            else:
                t = run([str(BUILD / "stockbear_tests"), "persistent_history"])
                failed = t.returncode != 0
                tail = (t.stdout + t.stderr).strip().splitlines()[-1]
            status = ("KILLED" if failed else "SURVIVED") if expect_killed else (
                "SURVIVED_AS_EXPECTED" if not failed else "CONTROL_BROKEN")
            results.append({"mutant": name, "file": str(path.relative_to(ROOT)),
                            "expect_killed": expect_killed, "detector": detector, "status": status,
                            "good": failed == expect_killed, "tail": tail})
            print(f"{name}: {status}", flush=True)
            path.write_text(original[path])
    finally:
        for f in files:
            f.write_text(original[f])
        run(["cmake", "--build", str(BUILD), "-j", "2"])
    bad = [r["mutant"] for r in results if not r["good"]]
    out = {"mechanism": "PersistentHistory", "mutants": results,
           "killed": sum(r["status"] == "KILLED" for r in results),
           "killable": sum(r["expect_killed"] for r in results), "total": len(results),
           "control_survived": any(r["status"] == "SURVIVED_AS_EXPECTED" for r in results),
           "bad": bad, "verdict": "PASS" if not bad else "FAIL"}
    (ROOT / "benchmarks/recovery/exp0065_mutation_matrix.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("killed", "killable", "total", "control_survived", "bad", "verdict")}))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
