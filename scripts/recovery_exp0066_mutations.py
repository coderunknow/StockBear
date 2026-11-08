#!/usr/bin/env python3
"""exp-0066 mutation matrix for PersistentContinuation.

Detectors: the registered persistent_continuation group for in-process
semantics, and the INTERACTIVE UCI oracle for object-lifetime semantics that the
in-process suite cannot observe (two mutants survived an in-process-only suite
in an earlier cycle for exactly that reason).

Semantics-changing mutants must be KILLED. Semantics-preserving controls must
SURVIVE, proving the detectors respond to behaviour rather than to any edit.
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CPP = ROOT / "src/search/search.cpp"
UCI = ROOT / "src/uci/uci.cpp"
BUILD = ROOT / "build-rel"
PARAMS = "research-data/params_exp0055_race.txt"

COND = "    if (params_.persistentContinuation) {"
DECAY = "        for (std::size_t i = 0; i < ContinuationSlots; ++i) continuation_[i] /= 2;"
REUSE = "                if (params_.persistentHistory || params_.persistentContinuation) {"
OPT = '    else if (key == "persistentcontinuation") flag = &params_.persistentContinuation;'
# Must be UNIQUE: several resets share the same indentation, and a non-unique
# anchor silently mutated the setoption path instead of ucinewgame.
NEWGAME = """            // exp-0065: a new game must forget the previous game's history.
            persistentSearch_.reset();"""
SETOPT_RESET = """    table_.clear();
    // exp-0066: persisted ordering state was learned under the OLD feature set
    // and must not survive a switch flip, exactly like the TT scores above.
    // No-op when every persistence switch is off (pointer is null).
    persistentSearch_.reset();
}"""

# (name, file, anchor, replacement, expect_killed, detector)
MUTANTS = [
    ("live_path_disabled", CPP, COND, "    if (false) {", True, "cpp"),
    ("always_persistent", CPP, COND, "    if (true) {", True, "cpp"),
    ("decay_removed", CPP, DECAY,
     "        for (std::size_t i = 0; i < ContinuationSlots; ++i) continuation_[i] /= 1;", True, "cpp"),
    ("decay_applied_twice", CPP, DECAY,
     "        for (std::size_t i = 0; i < ContinuationSlots; ++i) { continuation_[i] /= 2; continuation_[i] /= 2; }", True, "cpp"),
    ("decay_sign_flip", CPP, DECAY,
     "        for (std::size_t i = 0; i < ContinuationSlots; ++i) continuation_[i] = -continuation_[i] / 2;", True, "cpp"),
    ("clearing_kept_while_on", CPP, DECAY,
     "        for (std::size_t i = 0; i < ContinuationSlots; ++i) continuation_[i] = 0;", True, "cpp"),
    ("only_first_slot_decayed", CPP, DECAY,
     "        for (std::size_t i = 0; i < 1; ++i) continuation_[i] /= 2;", True, "cpp"),
    ("uci_option_misdirected", UCI, OPT,
     '    else if (key == "persistentcontinuation") flag = &params_.ttEval;', True, "uci"),
    ("object_not_reused", UCI, REUSE,
     "                if (params_.persistentHistory) {", True, "uci"),
    ("ucinewgame_does_not_reset", UCI, NEWGAME,
     "            // exp-0065: a new game must forget the previous game's history.", True, "uci"),
    ("setoption_does_not_reset", UCI, SETOPT_RESET, "    table_.clear();\n}", True, "uci"),
    # EQUIVALENCE CONTROLS: identical semantics, different spelling.
    ("control_equivalent_decay_rewrite", CPP, DECAY,
     "        for (std::size_t i = 0; i < ContinuationSlots; ++i) { const int v = continuation_[i]; continuation_[i] = v / 2; }", False, "cpp"),
    ("control_equivalent_condition_rewrite", CPP, COND,
     "    if (params_.persistentContinuation == true) {", False, "cpp"),
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
                t = run([sys.executable, "scripts/check_persistent_continuation_uci.py",
                         "--engine", str(BUILD / "stockbear"), "--params", PARAMS], timeout=300)
                failed = t.returncode != 0
                tail = (t.stdout + t.stderr).strip().replace("\n", " ")[-200:]
            else:
                t = run([str(BUILD / "stockbear_tests"), "persistent_continuation"])
                failed = t.returncode != 0
                tail = (t.stdout + t.stderr).strip().splitlines()[-1]
            status = ("KILLED" if failed else "SURVIVED") if expect_killed else (
                "SURVIVED_AS_EXPECTED" if not failed else "CONTROL_BROKEN")
            results.append({"mutant": name, "file": str(path.relative_to(ROOT)),
                            "detector": detector, "expect_killed": expect_killed,
                            "status": status, "good": failed == expect_killed, "tail": tail})
            print(f"{name}: {status}", flush=True)
            path.write_text(original[path])
    finally:
        for f in files:
            f.write_text(original[f])
        run(["cmake", "--build", str(BUILD), "-j", "2"])
    bad = [r["mutant"] for r in results if not r["good"]]
    out = {"mechanism": "PersistentContinuation", "mutants": results,
           "killed": sum(r["status"] == "KILLED" for r in results),
           "killable": sum(r["expect_killed"] for r in results), "total": len(results),
           "controls_survived": sum(r["status"] == "SURVIVED_AS_EXPECTED" for r in results),
           "bad": bad, "verdict": "PASS" if not bad else "FAIL"}
    (ROOT / "benchmarks/recovery/exp0066_mutation_matrix.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("killed", "killable", "total", "controls_survived", "bad", "verdict")}))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
