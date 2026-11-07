#!/usr/bin/env python3
"""Mutation matrix for the king-slider-battery candidate.

Each mutant is physically written to src/evaluation/evaluation.cpp, rebuilt, and
the registered king_slider_battery test group is run. A mutant is KILLED when
the suite exits nonzero. The original source is always restored and rebuilt.
"""
from __future__ import annotations
import json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/evaluation/evaluation.cpp"
BUILD = ROOT / "build-rel"

MUTANTS = [
    ("live_path_disabled", "const bool batteryOn = king_slider_battery_active();", "const bool batteryOn = false;"),
    ("computed_but_never_applied", "if (batteryOn) {\n            const int battery = std::min(batteryRaw, BatteryUnitsMax);", "if (false) {\n            const int battery = std::min(batteryRaw, BatteryUnitsMax);"),
    ("orthogonal_weight_removed", "constexpr int BatteryWeightOrthogonal = 4;", "constexpr int BatteryWeightOrthogonal = 0;"),
    ("diagonal_weight_removed", "constexpr int BatteryWeightDiagonal   = 3;", "constexpr int BatteryWeightDiagonal   = 0;"),
    ("exactly_one_blocker_becomes_zero", "if (popcount(BetweenBB[s][k] & occ) != 1) return 0;", "if (popcount(BetweenBB[s][k] & occ) != 0) return 0;"),
    ("cap_removed", "return std::min(units, BatteryUnitsMax);", "return units;"),
    ("queen_ignored", "if (pt == Queen && !orthogonal && !diagonal) return 0;", "if (pt == Queen) return 0;"),
    ("breakdown_sign_reversed", "mg(KingSliderBattery) -= sign * battery;", "mg(KingSliderBattery) += sign * battery;"),
]

def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)

def main():
    original = SRC.read_text()
    results = []
    try:
        for name, old, new in MUTANTS:
            assert old in original, f"mutant anchor missing: {name}"
            SRC.write_text(original.replace(old, new, 1))
            b = run(["cmake", "--build", str(BUILD), "-j", "2", "--target", "stockbear_tests"])
            if b.returncode != 0:
                results.append({"mutant": name, "status": "BUILD_FAILED", "killed": True,
                                "detail": b.stdout[-500:] + b.stderr[-500:]})
                continue
            t = run([str(BUILD / "stockbear_tests"), "king_slider_battery"])
            killed = t.returncode != 0
            results.append({"mutant": name, "status": "KILLED" if killed else "SURVIVED",
                            "killed": killed, "exit": t.returncode,
                            "tail": (t.stdout + t.stderr)[-500:]})
            print(name, results[-1]["status"], flush=True)
    finally:
        SRC.write_text(original)
        run(["cmake", "--build", str(BUILD), "-j", "2", "--target", "stockbear_tests"])
    survivors = [r["mutant"] for r in results if not r["killed"]]
    out = {"mechanism": "KingSliderBattery", "mutants": results,
           "killed": sum(r["killed"] for r in results), "total": len(results),
           "survivors": survivors, "verdict": "PASS" if not survivors else "FAIL"}
    dest = ROOT / "benchmarks/recovery/exp0061_battery_mutation_matrix.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("killed", "total", "survivors", "verdict")}))
    return 0 if not survivors else 1

if __name__ == "__main__":
    raise SystemExit(main())
