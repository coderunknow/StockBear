#!/usr/bin/env python3
"""exp-0067 mutation matrix for the JOINT persistence composition.

Two detector classes:
  * cpp -> ALL THREE registered persistence groups (joint_persistence plus the
    shipped persistent_history and persistent_continuation groups). The joint
    group pins exact node counts for all four configurations, which is what
    kills aging-RATE mutants; the single-table groups guard against a
    composition edit regressing shipped per-table semantics.
  * uci -> ALL THREE interactive oracles (joint + the shipped persistent_history
    and persistent_continuation oracles). Running the single-table oracles too is
    deliberate: a composition edit such as `||` -> `&&` leaves the JOINT arm
    correct while silently breaking each shipped single-table arm, so a
    joint-only detector would let it survive. Composition must not regress
    already-shipped behaviour.

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

H_COND = "    if (params_.persistentHistory) {"
C_COND = "    if (params_.persistentContinuation) {"
H_DECAY = "                for (int& value : row) value /= 2;"
C_DECAY = "        for (std::size_t i = 0; i < ContinuationSlots; ++i) continuation_[i] /= 2;"
REUSE = "                if (params_.persistentHistory || params_.persistentContinuation) {"
H_OPT = '    else if (key == "persistenthistory") flag = &params_.persistentHistory;'
C_OPT = '    else if (key == "persistentcontinuation") flag = &params_.persistentContinuation;'
# Unique anchor: several resets share this indentation (an exp-0066 lesson).
NEWGAME = """            // exp-0065: a new game must forget the previous game's history.
            persistentSearch_.reset();"""
SETOPT_RESET = """    table_.clear();
    // exp-0066: persisted ordering state was learned under the OLD feature set
    // and must not survive a switch flip, exactly like the TT scores above.
    // No-op when every persistence switch is off (pointer is null).
    persistentSearch_.reset();
}"""

ORACLES = ["check_joint_persistence_uci.py", "check_persistent_history_uci.py",
           "check_persistent_continuation_uci.py"]

# (name, file, anchor, replacement, expect_killed, detector)
MUTANTS = [
    # --- composition: neither branch may be dead -------------------------
    ("history_branch_disabled", CPP, H_COND, "    if (false) {", True, "cpp"),
    ("continuation_branch_disabled", CPP, C_COND, "    if (false) {", True, "cpp"),
    # --- each halving applied exactly once -------------------------------
    ("history_decay_removed", CPP, H_DECAY,
     "                for (int& value : row) value /= 1;", True, "cpp"),
    ("continuation_decay_removed", CPP, C_DECAY,
     "        for (std::size_t i = 0; i < ContinuationSlots; ++i) continuation_[i] /= 1;", True, "cpp"),
    ("history_decay_applied_twice", CPP, H_DECAY,
     "                for (int& value : row) { value /= 2; value /= 2; }", True, "cpp"),
    ("continuation_decay_applied_twice", CPP, C_DECAY,
     "        for (std::size_t i = 0; i < ContinuationSlots; ++i) { continuation_[i] /= 2; continuation_[i] /= 2; }", True, "cpp"),
    ("continuation_clearing_kept_while_on", CPP, C_DECAY,
     "        for (std::size_t i = 0; i < ContinuationSlots; ++i) continuation_[i] = 0;", True, "cpp"),
    ("only_first_continuation_slot_decayed", CPP, C_DECAY,
     "        for (std::size_t i = 0; i < 1; ++i) continuation_[i] /= 2;", True, "cpp"),
    # --- object lifetime / option wiring ---------------------------------
    ("history_option_misdirected", UCI, H_OPT,
     '    else if (key == "persistenthistory") flag = &params_.ttEval;', True, "uci"),
    ("continuation_option_misdirected", UCI, C_OPT,
     '    else if (key == "persistentcontinuation") flag = &params_.ttEval;', True, "uci"),
    ("object_not_reused", UCI, REUSE, "                if (false) {", True, "uci"),
    # Correct for the JOINT arm, breaks BOTH shipped single-table arms; only the
    # single-table oracles can see it.
    ("reuse_requires_both", UCI, REUSE,
     "                if (params_.persistentHistory && params_.persistentContinuation) {", True, "uci"),
    ("ucinewgame_does_not_reset", UCI, NEWGAME,
     "            // exp-0065: a new game must forget the previous game's history.", True, "uci"),
    ("setoption_does_not_reset", UCI, SETOPT_RESET, "    table_.clear();\n}", True, "uci"),
    # --- EQUIVALENCE CONTROLS: identical semantics, different spelling ----
    ("control_equivalent_history_decay", CPP, H_DECAY,
     "                for (int& value : row) { const int v = value; value = v / 2; }", False, "cpp"),
    ("control_equivalent_continuation_decay", CPP, C_DECAY,
     "        for (std::size_t i = 0; i < ContinuationSlots; ++i) { const int v = continuation_[i]; continuation_[i] = v / 2; }", False, "cpp"),
    ("control_equivalent_reuse_demorgan", UCI, REUSE,
     "                if (!(!params_.persistentHistory && !params_.persistentContinuation)) {", False, "uci"),
]


def run(cmd, timeout=1800):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def main():
    files = [CPP, UCI]
    original = {f: f.read_text() for f in files}
    # Every anchor must be UNIQUE, or a mutant silently edits the wrong site.
    for name, path, anchor, _repl, _k, _d in MUTANTS:
        n = original[path].count(anchor)
        assert n == 1, f"anchor for {name} occurs {n} times (must be 1)"
    results = []
    try:
        for name, path, anchor, repl, expect_killed, detector in MUTANTS:
            path.write_text(original[path].replace(anchor, repl, 1))
            target = "stockbear" if detector == "uci" else "stockbear_tests"
            b = run(["cmake", "--build", str(BUILD), "-j", "2", "--target", target])
            if b.returncode != 0:
                failed, tail = True, "BUILD_FAILED " + (b.stdout + b.stderr)[-300:]
            elif detector == "uci":
                failed, notes = False, []
                for oracle in ORACLES:
                    t = run([sys.executable, f"scripts/{oracle}", "--engine",
                             str(BUILD / "stockbear"), "--params", PARAMS], timeout=600)
                    if t.returncode != 0:
                        failed = True
                        notes.append(oracle.replace("check_", "").replace("_uci.py", "") + ":FAIL")
                tail = ",".join(notes) if notes else "all 3 oracles PASS"
            else:
                failed, notes = False, []
                for group in ("joint_persistence", "persistent_history", "persistent_continuation"):
                    t = run([str(BUILD / "stockbear_tests"), group])
                    if t.returncode != 0:
                        failed = True
                        first = next((l for l in (t.stdout + t.stderr).splitlines()
                                      if l.startswith("FAIL")), group + ":FAIL")
                        notes.append(first.split(":")[0].replace("FAIL ", "") + ":FAIL")
                tail = "; ".join(notes) if notes else "all 3 groups PASS"
            status = ("KILLED" if failed else "SURVIVED") if expect_killed else (
                "SURVIVED_AS_EXPECTED" if not failed else "CONTROL_BROKEN")
            results.append({"mutant": name, "file": str(path.relative_to(ROOT)),
                            "detector": detector, "expect_killed": expect_killed,
                            "status": status, "good": failed == expect_killed, "tail": tail})
            print(f"{name}: {status}  [{tail}]", flush=True)
            path.write_text(original[path])
    finally:
        for f in files:
            f.write_text(original[f])
        run(["cmake", "--build", str(BUILD), "-j", "2"])
    bad = [r["mutant"] for r in results if not r["good"]]
    killable = sum(r["expect_killed"] for r in results)
    killed = sum(r["status"] == "KILLED" for r in results)
    out = {"mechanism": "joint persistence (PersistentHistory + PersistentContinuation)",
           "uci_detectors": ORACLES, "mutants": results,
           "killed": killed, "killable": killable, "total": len(results),
           "controls_survived": sum(r["status"] == "SURVIVED_AS_EXPECTED" for r in results),
           "bad": bad, "gate_min_killable": 8,
           "verdict": "PASS" if not bad and killable >= 8 else "FAIL"}
    (ROOT / "benchmarks/recovery/exp0067_mutation_matrix.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("killed", "killable", "total", "controls_survived", "bad", "verdict")}))
    return 0 if out["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())