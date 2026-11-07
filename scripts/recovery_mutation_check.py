#!/usr/bin/env python3
"""Apply source mutants and verify the registered tests KILL each one.

exp-0052 lesson: a live-but-linear mutant passed all 93 assertions, and a
gate-removed mutant passed ctest while the independent oracle caught it.
Correctness and sign tests do not pin curve SHAPE or GATING. The only way to know
a test suite detects a broken mechanism is to break it and watch the suite fail.

Each mutant is applied to a working copy, built, and the target test group is run.
A mutant that still PASSES is a SURVIVOR and means the suite is blind to that
defect. The original source is always restored, even on failure.

Usage: recovery_mutation_check.py --source src/evaluation/evaluation.cpp \
           --build build-rel --group threats --json out.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (name, old, new, why_it_matters)
MUTANTS = [
    ("computed_but_never_applied",
     "        threatMg = diff * par.mg[std::size_t(ThreatDetection)];\n"
     "        threatEg = diff * par.eg[std::size_t(ThreatDetection)];",
     "        threatMg = 0;\n        threatEg = 0;",
     "a term that is computed but never added is correct-looking dead code"),
    ("defended_mask_removed",
     "    const Bitboard hanging = enemyNonPawn & atkUs & ~defThem;",
     "    const Bitboard hanging = enemyNonPawn & atkUs;",
     "defended pieces would count as hanging; sign/linearity tests still pass"),
    ("pawn_component_removed",
     "    const int units = ThreatWeightHanging * popcount(hanging)\n"
     "                    + ThreatWeightPawn    * popcount(pawnThreat);",
     "    const int units = ThreatWeightHanging * popcount(hanging);",
     "pawn threats are the larger component and must be independently pinned"),
    ("hanging_component_removed",
     "    const int units = ThreatWeightHanging * popcount(hanging)\n"
     "                    + ThreatWeightPawn    * popcount(pawnThreat);",
     "    const int units = ThreatWeightPawn * popcount(pawnThreat);",
     "hanging pieces must be independently pinned"),
    ("cap_removed",
     "    return std::min(units, ThreatUnitsMax);",
     "    return units;",
     "without the cap the term can swamp the cp-calibrated pruning margins"),
    ("pawns_counted_as_hanging_targets",
     "    const Bitboard enemyNonPawn = enemy & ~p.pieces(them, Pawn);",
     "    const Bitboard enemyNonPawn = enemy;",
     "a pawn attacked by a piece is not a material-exposure threat"),
    ("sign_flipped",
     "        const int diff = threat_units(p, White, tu) - threat_units(p, Black, tu);",
     "        const int diff = threat_units(p, Black, tu) - threat_units(p, White, tu);",
     "a flipped sign would make the engine help its opponent"),
]


# exp-0055 passed-pawn race. The formula lives in race_passer_units() (shared by
# the live FUSED path in features() and the standalone breakdown walker), so a
# formula mutant hits both. Clamp mutants are applied to BOTH paths separately
# because each has its own clamp; mutating only one would leave the other live.
RACE_MUTANTS = [
    ("computed_but_never_applied",
     "        out.mg += race * mgp(PassedPawnRace);\n"
     "        out.eg += race * egp(PassedPawnRace);",
     "        (void)race;",
     "a term computed but never added is correct-looking dead code"),
    ("own_king_escort_removed",
     "    return advance * (RaceWeightOwnKing * (7 - ownD)\n"
     "                    - RaceWeightEnemyKing * (7 - enemyD)\n"
     "                    - (blocked ? RaceWeightBlocked : 0));",
     "    return advance * (- RaceWeightEnemyKing * (7 - enemyD)\n"
     "                    - (blocked ? RaceWeightBlocked : 0));",
     "the escort half is the term's main positive contribution"),
    ("enemy_king_blockade_removed",
     "    return advance * (RaceWeightOwnKing * (7 - ownD)\n"
     "                    - RaceWeightEnemyKing * (7 - enemyD)\n"
     "                    - (blocked ? RaceWeightBlocked : 0));",
     "    return advance * (RaceWeightOwnKing * (7 - ownD)\n"
     "                    - (blocked ? RaceWeightBlocked : 0));",
     "the defending king's blockade decides most pawn races"),
    ("blocked_path_penalty_removed",
     "    return advance * (RaceWeightOwnKing * (7 - ownD)\n"
     "                    - RaceWeightEnemyKing * (7 - enemyD)\n"
     "                    - (blocked ? RaceWeightBlocked : 0));",
     "    return advance * (RaceWeightOwnKing * (7 - ownD)\n"
     "                    - RaceWeightEnemyKing * (7 - enemyD));",
     "a blocked passer is not a promotion threat"),
    ("advance_weighting_removed",
     "    return advance * (RaceWeightOwnKing * (7 - ownD)",
     "    return 1 * (RaceWeightOwnKing * (7 - ownD)",
     "an advanced passer is worth far more than one on rank 2"),
    ("live_path_cap_removed",
     "        const int race = std::clamp(raceRaw, -RaceUnitsMax, RaceUnitsMax);",
     "        const int race = raceRaw;",
     "without the clamp the LIVE term can swamp cp-calibrated pruning margins"),
    ("breakdown_path_cap_removed",
     "    return std::clamp(units, -RaceUnitsMax, RaceUnitsMax);",
     "    return units;",
     "the breakdown clamp must match the live clamp or the paths drift"),
    ("chebyshev_replaced_by_manhattan",
     "    return std::max(df, dr);",
     "    return df + dr;",
     "a king moves diagonally; manhattan mis-ranks escort vs blockade"),
    ("live_path_scores_non_passers",
     "        if (!(enemyPawns & PassedPawnMaskBB[us][s])) {\n"
     "            // A doubled pawn behind another is not an independently useful",
     "        if (true) {\n"
     "            // A doubled pawn behind another is not an independently useful",
     "only genuine passers may contribute in the LIVE path"),
    ("live_path_disabled",
     "    const bool raceOn = passed_pawn_race_active();",
     "    const bool raceOn = false;",
     "the live path must actually run when the parameter is enabled"),
]


def run(cmd: list[str], timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="src/evaluation/evaluation.cpp")
    ap.add_argument("--build", default="build-rel")
    ap.add_argument("--group", default="threats")
    ap.add_argument("--mechanism", default="threats", choices=["threats", "race"])
    ap.add_argument("--json")
    args = ap.parse_args()

    mutants = RACE_MUTANTS if args.mechanism == "race" else MUTANTS
    src = ROOT / args.source
    original = src.read_text()
    results = []
    try:
        # Baseline: the real implementation must PASS first.
        b = run(["ninja", "-C", args.build])
        assert b.returncode == 0, f"baseline build failed:\n{b.stdout[-2000:]}"
        base = run([str(ROOT / args.build / "stockbear_tests"), args.group])
        baseline_pass = base.returncode == 0
        print(f"[baseline] {args.group}: {'PASS' if baseline_pass else 'FAIL'}")
        if not baseline_pass:
            print(base.stdout[-2000:])
            return 2

        for name, old, new, why in mutants:
            if original.count(old) != 1:
                results.append({"mutant": name, "status": "NOT_APPLIED",
                                "reason": f"anchor count {original.count(old)} != 1"})
                print(f"[SKIP] {name}: anchor count {original.count(old)} != 1")
                continue
            src.write_text(original.replace(old, new, 1))
            b = run(["ninja", "-C", args.build])
            if b.returncode != 0:
                # A mutant that does not compile is not a meaningful survivor.
                results.append({"mutant": name, "status": "BUILD_FAILED",
                                "why": why})
                print(f"[BUILD FAILED] {name}")
                src.write_text(original)
                continue
            r = run([str(ROOT / args.build / "stockbear_tests"), args.group])
            killed = r.returncode != 0
            fails = [l for l in r.stdout.splitlines() if l.startswith("FAIL")]
            results.append({"mutant": name, "status": "KILLED" if killed else "SURVIVED",
                            "exit_code": r.returncode, "why": why,
                            "first_failure": fails[0] if fails else None})
            print(f"[{'KILLED' if killed else 'SURVIVED'}] {name}"
                  + (f"  <- {fails[0]}" if fails else ""))
            src.write_text(original)
    finally:
        src.write_text(original)
        run(["ninja", "-C", args.build])
        restored = src.read_text() == original
        print(f"\nsource restored: {'VERIFIED' if restored else 'MISMATCH'}")

    survivors = [r["mutant"] for r in results if r["status"] == "SURVIVED"]
    out = {"group": args.group, "baseline": "PASS", "mutants": results,
           "survivors": survivors, "source_restored": restored,
           "verdict": "PASS" if not survivors and restored else "FAIL"}
    if args.json:
        (ROOT / args.json).write_text(json.dumps(out, indent=2) + "\n")
    print("verdict:", out["verdict"], "| survivors:", survivors or "none")
    return 0 if out["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
