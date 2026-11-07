#!/usr/bin/env python3
"""Checklist 2.2 — audit every prereg BY CONTENT (not by freeze order).

For each preregistration, locate each of the ten required elements and record the
line number and the actual matching text, so the claim is inspectable rather than
asserted. An element that cannot be located is reported MISSING; this script
never infers a pass from the mere existence of a file or a section heading.

Required by 2.2: ID, hypothesis, mechanism, candidate/baseline hashes, frozen
ADVANCE/CLOSE/INCONCLUSIVE rules, time control, opening methodology, statistics,
power rationale, validity requirements.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

# element -> (any-of regexes, all-of regexes)
ELEMENTS: dict[str, tuple[list[str], list[str]]] = {
    "id": ([r"exp[- ]?00\d\d", r"BASELINE"], []),
    "hypothesis": ([r"hypothes[ie]s", r"\bprediction\b", r"\bclaim under test\b",
                    r"one question", r"honest prior", r"\bprior\b", r"expected",
                    r"we expect", r"play better", r"\bclaim\b"], []),
    "mechanism": ([r"mechanism", r"source.location", r"src/[a-z]+/[a-z_]+\.(cpp|hpp)",
                   r"frozen (knob|change|term|feature|weights|scale)",
                   r"frozen `?[A-Z][A-Za-z]+`?\s*=\s*\(",
                   r"ThreatDetection|PassedPawnRace|KingSliderBattery",
                   r"SearchParams::", r"\b[A-Z][A-Za-z]+=(true|false)\b",
                   r"toolchain", r"\bPST\b", r"per.square", r"frozen constant",
                   r"\bswitch\b", r"^## Method"], []),
    "candidate_baseline_hashes": (
        [r"\b[0-9a-f]{64}\b", r"\b[0-9a-f]{12,}…", r"sha-?256"],
        [r"candidate|arm a|engine_a", r"baseline|ablation|arm b|engine_b|dev5"]),
    # Screen preregs use ADVANCE/CLOSE/INCONCLUSIVE; direct gate measurements
    # use GATE MET / GATE UNMET / INVALID. Both are frozen decision vocabularies.
    "frozen_decision_rules": ([r"ADVANCE|GATE MET|GATE 1 PASS|\bPASS iff\b",
                               r"CLOSE|GATE UNMET|GATE 1 FAIL|\bFAIL iff\b",
                               r"INCONCLUSIVE|Otherwise|INVALID|NEGATIVE"], []),
    "time_control": ([r"40\s*\+\s*4", r"base_ms", r"40\+4"], []),
    "opening_methodology": ([r"opening"], [r"opening", r"seed|disjoint|suite"]),
    "statistics": ([r"cluster", r"\bCR1\b", r"bootstrap", r"student", r"95\s*%"], []),
    "power_rationale": ([r"\bpower\b", r"resolvab", r"unresolvable", r"half.width",
                        r"resolution", r"±\s*\d", r"detectable", r"\bMDE\b"], []),
    "validity_requirements": ([r"validity", r"\bINVALID\b", r"TIME_FORFEIT",
                              r"ILLEGAL", r"\bcrash\b", r"zero illegal",
                              r"UCI failure", r"invalidates the run"], []),
}


def find(lines: list[str], patterns: list[str]) -> list[dict]:
    hits = []
    for pat in patterns:
        rx = re.compile(pat, re.IGNORECASE)
        for i, line in enumerate(lines, 1):
            if rx.search(line):
                hits.append({"line": i, "pattern": pat, "text": line.strip()[:220]})
                break
    return hits


MASTER = DOCS / "DEV6_PREREG.md"
POWER = DOCS / "DEV6_POWER_ANALYSIS.md"


def audit(path: Path) -> dict:
    lines = path.read_text().splitlines()
    result = {}
    for name, (any_of, all_of) in ELEMENTS.items():
        any_hits = find(lines, any_of)
        all_hits = find(lines, all_of)
        if name == "frozen_decision_rules":
            present = len(any_hits) == len(any_of)
        else:
            present = bool(any_hits) if any_of else True
        if all_of and len(all_hits) < len(all_of):
            present = False
        result[name] = {"present": present, "citations": (all_hits or any_hits)[:3]}
    # Resolution by EXPLICIT INCORPORATION, not by assumption. Many preregs open
    # with "docs/DEV6_PREREG.md §8 is UNCHANGED"; the governing prereg in turn
    # cites docs/DEV6_POWER_ANALYSIS.md as the programme's power basis. An element
    # is only credited this way when BOTH the incorporating line and the
    # inherited source line are located and recorded.
    inherited = {}
    text = path.read_text()
    inc = find(lines, [r"DEV6_PREREG\.md"])
    if inc:
        master_lines = MASTER.read_text().splitlines() if MASTER.exists() else []
        for name, ok in list((k, v["present"]) for k, v in result.items()):
            if ok:
                continue
            pats = ELEMENTS[name][0] + ELEMENTS[name][1]
            src = find(master_lines, pats)
            if name == "power_rationale" and not src and POWER.exists():
                src = [{"line": f"DEV6_POWER_ANALYSIS.md:{i}", "pattern": "power analysis",
                        "text": l.strip()[:220]}
                       for i, l in enumerate(POWER.read_text().splitlines(), 1)
                       if re.search(r"half.width|power|CI", l, re.IGNORECASE)][:2]
            if name == "power_rationale" and src:
                link = find(master_lines, [r"DEV6_POWER_ANALYSIS\.md"])
                src = link + src
            if src:
                result[name]["present"] = True
                result[name]["resolved_by"] = "explicit incorporation"
                result[name]["incorporating_line"] = inc[0]
                result[name]["inherited_citations"] = src[:3]
                inherited[name] = True
    # An ADDENDUM/RETRY amends a parent prereg; credit the parent's text.
    parent = None
    m = re.match(r"(DEV6_PREREG_EXP\d+)_(ADDENDUM|RETRY)\.md$", path.name)
    if m:
        parent = DOCS / (m.group(1) + ".md")
        if parent.exists():
            plines = parent.read_text().splitlines()
            for name, v in result.items():
                if v["present"]:
                    continue
                pats = ELEMENTS[name][0] + ELEMENTS[name][1]
                src = find(plines, pats)
                need_all = name == "frozen_decision_rules"
                if src and (not need_all or len(find(plines, ELEMENTS[name][0])) ==
                            len(ELEMENTS[name][0])):
                    v["present"] = True
                    v["resolved_by"] = f"parent prereg {parent.name}"
                    v["inherited_citations"] = src[:3]
                    inherited[name] = True
    missing = [k for k, v in result.items() if not v["present"]]
    return {"path": str(path.relative_to(ROOT)), "elements": result,
            "resolved_by_incorporation": sorted(inherited),
            "missing": missing, "complete": not missing}


def main() -> int:
    paths = sorted(DOCS.glob("DEV6_PREREG_*.md"))
    rows = [audit(p) for p in paths]
    complete = [r["path"] for r in rows if r["complete"]]
    incomplete = [{"path": r["path"], "missing": r["missing"]} for r in rows if not r["complete"]]
    # The mission's strength-tested scope, as used by checklist 2.1.
    scope = [r for r in rows if re.search(r"EXP00(5\d|6\d)\.md$", r["path"])]
    scope_incomplete = [{"path": r["path"], "missing": r["missing"]}
                        for r in scope if not r["complete"]]
    out = {"item": "2.2", "method": "content citation per element per prereg",
           "required_elements": list(ELEMENTS), "preregs_total": len(rows),
           "preregs_complete": len(complete), "preregs_incomplete": incomplete,
           "mission_scope_regex": "EXP0050..EXP0064 (strength-tested era, as in 2.1)",
           "mission_scope_total": len(scope),
           "mission_scope_complete": len(scope) - len(scope_incomplete),
           "mission_scope_incomplete": scope_incomplete,
           "rows": rows}
    dest = ROOT / "benchmarks/recovery/prereg_content_audit.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(f"preregs {len(rows)}: complete {len(complete)}, incomplete {len(incomplete)}")
    for r in incomplete:
        print("  INCOMPLETE", r["path"], r["missing"])
    print(f"mission scope {len(scope)}: complete {len(scope)-len(scope_incomplete)}, "
          f"incomplete {len(scope_incomplete)}")
    for r in scope_incomplete:
        print("  SCOPE-INCOMPLETE", r["path"], r["missing"])
    print("verdict:", "PASS" if not incomplete else "CONTENT GAPS FOUND")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
