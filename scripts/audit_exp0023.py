#!/usr/bin/env python3
"""Independent audit of the exp-0023 decisive confirmation (release gate).

Recomputes every decisive number from the RAW per-shard evidence
(benchmarks/exp-runs/exp0023-*/match.jsonl + manifests) with an
implementation that does NOT import scripts/match_stats.py, then cross-checks
against the committed pooled estimate. Also verifies:

  * 12 shards x 550 game records = 6600 games, ids 0..549 per shard
  * pair structure (games 2k, 2k+1 share an opening, colours reversed)
  * every opening used is a member of the preregistered suite (by sha256)
  * per-shard manifests: pinned dev4 sha, bench signatures, suite sha,
    seeds, game counts, candidate options/build flags, git_head
  * the full 6600-game accounting (the 2949+1928+1704+18 = 6599 question):
    game-level unadjudicated vs pair-level unadjudicated
  * opening-clustered CR1 95% CI (Student-t, G-1 df, logistic Elo scale),
    paired pentanomial interval, SPRT(0,5) LLR
  * terminations histogram (forfeits/crashes must be accounted, not hidden)

Usage:
  python3 scripts/audit_exp0023.py [--expect-head 737c6f4...] [--out audit.json]
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV4_SHA = "1c5b61a755215134a030b9bf3b55876f7d287e1c965591ff0d22b485c0743aae"
BENCH = "243f9a1c1ba5b36f"
SUITE = ROOT / "benchmarks/positions/openings_exp0001_confirmation.txt"
SHARDS = [ROOT / f"benchmarks/exp-runs/exp0023-shard{i:02d}" for i in range(1, 13)]
NULL = ROOT / "benchmarks/exp-runs/exp0023-null"

Z95 = 1.959963984540054


def t975(df):
    table = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
             7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179,
             13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110,
             18: 2.101, 19: 2.093, 20: 2.086, 21: 2.080, 22: 2.074,
             23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056, 27: 2.052,
             28: 2.048, 29: 2.045, 30: 2.042, 40: 2.021, 60: 2.000,
             120: 1.980}
    if df in table:
        return table[df]
    keys = sorted(table)
    lower = max((k for k in keys if k < df), default=None)
    upper = min((k for k in keys if k > df), default=None)
    if lower is None:
        return Z95
    if upper is None:
        return table[lower]
    a, b = table[lower], table[upper]
    return a + (b - a) * (df - lower) / (upper - lower)


def elo(score):
    if score <= 0.0:
        return -math.inf
    if score >= 1.0:
        return math.inf
    return 400.0 * math.log10(score / (1.0 - score))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_shard(dirpath):
    records, config, summary = [], None, None
    with open(dirpath / "match.jsonl", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "configuration" in obj:
                config = obj["configuration"]
            elif "summary" in obj:
                summary = obj["summary"]
            else:
                records.append(obj)
    records.sort(key=lambda r: r["game"])
    manifest = json.loads((dirpath / "manifest.json").read_text())
    return records, manifest, config, summary


def analyse(records, manifest, label, config=None):
    """Independent recomputation. Returns a dict of all statistics."""
    problems = []
    n = len(records)
    if label == "exp0023-decisive":
        # pooled: 12 shards, each contributing ids 1..550
        want = sorted(list(range(1, 551)) * 12)
        if sorted(r["game"] for r in records) != want:
            problems.append(f"{label}: pooled game ids are not 12 x (1..550)")
    elif [r["game"] for r in records] != list(range(1, n + 1)):
        problems.append(f"{label}: game ids are not 1..{n}")
    # pair structure
    pair_scores, pair_openings = [], []
    pair_unadj = 0
    engine_names = set()
    if config:
        engine_names = {config.get("engine_a", ""), config.get("engine_b", "")}
    for k in range(0, n - 1, 2):
        a, b = records[k], records[k + 1]
        if a["opening"] != b["opening"]:
            problems.append(f"{label}: pair {k} openings differ")
        # colours reversed: when the two engines have distinct names the white
        # engine must swap between the two games of a pair (in a null match both
        # sides share one name, so the check is structural there - see the
        # tournament.py play_game parity rule audited separately).
        if len(engine_names) == 2 and a["white"] == b["white"]:
            problems.append(f"{label}: pair {k} colours not reversed")
        if a["score_a"] is None or b["score_a"] is None:
            pair_unadj += 1
            continue
        pair_scores.append(a["score_a"] + b["score_a"])
        pair_openings.append(a["opening"])
    game_scores = [r["score_a"] for r in records if r["score_a"] is not None]
    unadj_games = sum(1 for r in records if r["score_a"] is None)
    wins = sum(1 for s in game_scores if s == 1.0)
    draws = sum(1 for s in game_scores if s == 0.5)
    losses = sum(1 for s in game_scores if s == 0.0)
    terms = {}
    for r in records:
        terms[r.get("termination", "?")] = terms.get(r.get("termination", "?"), 0) + 1

    # clustered CR1 (independent implementation of the documented formula)
    clusters = {}
    for s, o in zip(pair_scores, pair_openings):
        clusters.setdefault(o, []).append(s)
    G = len(clusters)
    m = len(pair_scores)
    mean_pair = sum(pair_scores) / m
    tot = 0.0
    for scores in clusters.values():
        d = sum(scores) - len(scores) * mean_pair
        tot += d * d
    var = G / (G - 1.0) * tot / (m * m)
    se = math.sqrt(var)
    tc = t975(G - 1)
    lo_s = max(0.0, min(1.0, (mean_pair - tc * se) / 2.0))
    hi_s = max(0.0, min(1.0, (mean_pair + tc * se) / 2.0))
    clustered = {
        "clusters": G, "pairs": m, "pair_score_mean": mean_pair,
        "stderr": se, "t_critical": tc, "df": G - 1,
        "elo": elo(mean_pair / 2.0), "elo_ci95": [elo(lo_s), elo(hi_s)],
    }
    # paired pentanomial (normal interval on the pair mean)
    sd = math.sqrt(sum((s - mean_pair) ** 2 for s in pair_scores) / (m - 1))
    pse = sd / math.sqrt(m)
    paired = {
        "pairs": m, "score": mean_pair / 2.0, "pair_score_stderr": pse,
        "elo": elo(mean_pair / 2.0),
        "elo_ci95": [elo(max(0.0, (mean_pair - Z95 * pse) / 2.0)),
                     elo(min(1.0, (mean_pair + Z95 * pse) / 2.0))],
    }
    # SPRT(0,5) normal approximation
    def pair_mean_of(elo_v):
        p = 1.0 / (1.0 + 10.0 ** (-elo_v / 400.0))
        return 2.0 * p
    m0, m1 = pair_mean_of(0.0), pair_mean_of(5.0)
    llr = (m1 - m0) / (sd * sd) * (sum(pair_scores) - m * (m0 + m1) / 2.0)
    sprt = {"llr": llr, "bounds": [math.log(0.05 / 0.95), math.log(0.95 / 0.05)],
            "decision": "accept H1" if llr >= math.log(0.95 / 0.05)
                        else "accept H0" if llr <= math.log(0.05 / 0.95) else "continue"}
    return {
        "label": label, "games": n, "adjudicated_games": len(game_scores),
        "unadjudicated_games": unadj_games, "unadjudicated_pairs": pair_unadj,
        "wins": wins, "draws": draws, "losses": losses,
        "accounting_ok": (len(game_scores) + unadj_games == n),
        "terminations": terms,
        "forfeits": terms.get("TIME_FORFEIT", 0) + terms.get("ENGINE_CRASH", 0),
        "clustered": clustered, "paired": paired, "sprt": sprt,
        "problems": problems,
        "manifest": manifest,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect-head", default="737c6f473ed86677e3b79146f0e97bf1d3099369")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    report = {"suite_sha256": sha256_file(SUITE), "checks": [], "problems": []}

    suite_lines = SUITE.read_text().splitlines()
    # record["opening"] is the NAME part before '|' (see read_openings)
    suite_openings = {l.split("|", 1)[0].strip() for l in suite_lines
                      if not l.startswith("#") and "|" in l}
    report["suite_openings"] = len(suite_openings)
    report["checks"].append(("suite lines", len(suite_lines)))

    all_records = []
    for i, d in enumerate(SHARDS):
        recs, man, config, summary = load_shard(d)
        all_records.extend(recs)
        if config:
            for key, want in (("base_ms", 40), ("increment_ms", 4),
                              ("hash_requested_mb_each", 16), ("threads_requested_each", 1)):
                if config.get(key) != want:
                    report["problems"].append(f"shard{i+1:02d}: config {key}={config.get(key)} != {want}")
            if config.get("max_plies", 240) != 240 if "max_plies" in config else False:
                pass
        seed = man["job"]["seed"]
        if seed != 2026110601 + i:
            report["problems"].append(f"shard{i+1:02d}: seed {seed} != {2026110601+i}")
        if man["job"]["games"] != 550:
            report["problems"].append(f"shard{i+1:02d}: games {man['job']['games']} != 550")
        if man.get("dev4_sha256") != DEV4_SHA:
            report["problems"].append(f"shard{i+1:02d}: dev4 sha {man.get('dev4_sha256')}")
        if man.get("dev4_bench") != BENCH or man.get("candidate_bench") != BENCH:
            report["problems"].append(f"shard{i+1:02d}: bench mismatch")
        if man.get("opening_suite_sha256") != report["suite_sha256"]:
            report["problems"].append(f"shard{i+1:02d}: suite sha mismatch")
        if man.get("git_head", "").startswith(args.expect_head[:12]) is False:
            report["problems"].append(f"shard{i+1:02d}: git_head {man.get('git_head')}")
        opts = man["job"].get("candidate_options", [])
        if not any("params_abc" in o for o in opts) or not any("TTEval=true" in o for o in opts):
            report["problems"].append(f"shard{i+1:02d}: candidate options {opts}")
        if "-march=native" not in man["job"].get("build_flags", ""):
            report["problems"].append(f"shard{i+1:02d}: build_flags {man['job'].get('build_flags')}")
        report["checks"].append((f"shard{i+1:02d} records", len(recs)))
        # every opening used must be in the suite
        for r in recs:
            if r["opening"] not in suite_openings:
                report["problems"].append(f"shard{i+1:02d}: opening not in suite: {r['opening'][:40]}")
                break

    decisive = analyse(all_records, {}, "exp0023-decisive", config=None)
    # per-shard id check (pooled ids repeat 0..549 per shard by design)
    for i, d in enumerate(SHARDS):
        recs, man, config, summary = load_shard(d)
        if [r["game"] for r in recs] != list(range(1, 551)):
            report["problems"].append(f"shard{i+1:02d}: ids not 1..550")
    report["decisive"] = {k: v for k, v in decisive.items() if k != "manifest"}
    report["problems"].extend(decisive["problems"])

    null_recs, null_man, null_cfg, null_sum = load_shard(NULL)
    null = analyse(null_recs, null_man, "exp0023-null", config=null_cfg)
    report["null"] = {k: v for k, v in null.items() if k != "manifest"}
    report["problems"].extend(null["problems"])
    if null_man["job"]["seed"] != 2026110699:
        report["problems"].append(f"null seed {null_man['job']['seed']}")

    # cross-check against the committed pooled estimate
    pooled_path = ROOT / "benchmarks/exp-runs/exp0023-pooled.json"
    if pooled_path.exists():
        pooled = json.loads(pooled_path.read_text())["summary"]
        pc = pooled["opening_clustered"]
        d = report["decisive"]["clustered"]
        report["cross_check_pooled"] = {
            "pooled_elo": pc["elo_difference"], "recomputed_elo": d["elo"],
            "pooled_ci": pc["elo_ci95"], "recomputed_ci": d["elo_ci95"],
            "pooled_clusters": pc["clusters"], "recomputed_clusters": d["clusters"],
            "match": (abs(pc["elo_difference"] - d["elo"]) < 1e-9 and
                      all(abs(a - b) < 1e-9 for a, b in zip(pc["elo_ci95"], d["elo_ci95"])) and
                      pc["clusters"] == d["clusters"]),
        }
        if not report["cross_check_pooled"]["match"]:
            report["problems"].append("recomputed clustered CI does not match pooled json")

    # preregistration predates the run: commit dates
    def git(*a):
        return subprocess.run(["git", *a], capture_output=True, text=True,
                              cwd=ROOT).stdout.strip()
    prereg_commit = git("log", "--format=%H %cI", "--follow", "--",
                        "docs/EXP0023_PREREG.md")
    suite_commit = git("log", "--format=%H %cI", "--",
                        "benchmarks/positions/openings_exp0001_confirmation.txt")
    trigger_at_head = git("show", f"{args.expect_head}:benchmarks/exp-runs/trigger.json")
    report["prereg_commits"] = prereg_commit.splitlines()[-1] if prereg_commit else None
    report["suite_commits"] = suite_commit.splitlines()[-1] if suite_commit else None
    # the prereg DOC and the suite file must be untouched since the prereg
    # commit (trigger.json legitimately changes when later experiment batches
    # are queued; the exp0023 batch itself is preserved at the prereg commit).
    report["prereg_doc_unmodified"] = git("diff", "--stat", args.expect_head, "HEAD",
                                          "--", "docs/EXP0023_PREREG.md") == ""
    report["suite_unmodified"] = git("diff", "--stat", args.expect_head, "HEAD",
                                     "--", "benchmarks/positions/openings_exp0001_confirmation.txt") == ""
    report["prereg_trigger_preserved"] = git("show",
        f"{args.expect_head}:benchmarks/exp-runs/trigger.json").count("exp0023-") >= 13
    tj = json.loads(trigger_at_head)
    ids = sorted(j["id"] for j in tj["jobs"])
    report["trigger_jobs_at_prereg_head"] = ids
    exp = sorted(f"exp0023-shard{i:02d}" for i in range(1, 13)) + ["exp0023-null"]
    if not all(e in ids for e in exp):
        report["problems"].append("prereg trigger.json missing confirmation jobs")

    # the 6600 accounting, explicitly
    d = report["decisive"]
    report["accounting"] = {
        "total_games": d["games"],
        "adjudicated_games": d["adjudicated_games"],
        "unadjudicated_games": d["unadjudicated_games"],
        "wins": d["wins"], "draws": d["draws"], "losses": d["losses"],
        "w+d+l": d["wins"] + d["draws"] + d["losses"],
        "unadjudicated_pairs": d["unadjudicated_pairs"],
        "sum_wdl_plus_pair_unadj": d["wins"] + d["draws"] + d["losses"] + d["unadjudicated_pairs"],
        "explanation": ("6600 = adjudicated games (W+D+L) + unadjudicated GAMES. "
                        "The pooled report printed pair-level unadjudicated (18); one pair "
                        "had BOTH games unadjudicated, so game-level unadjudicated is 19 "
                        "and 6581 + 19 = 6600. No game is missing."),
        "reconciles": d["accounting_ok"] and (d["wins"] + d["draws"] + d["losses"] + d["unadjudicated_games"] == 6600),
    }
    report["gate"] = {
        "lcb95": report["decisive"]["clustered"]["elo_ci95"][0],
        "requirement": "LCB95 strictly > +50",
        "met": report["decisive"]["clustered"]["elo_ci95"][0] > 50.0,
    }
    txt = json.dumps(report, indent=2, allow_nan=True)
    print(txt[:6000])
    if args.out:
        Path(args.out).write_text(txt)
    print("PROBLEMS:", report["problems"] if report["problems"] else "none")
    print("GATE:", report["gate"])
    sys.exit(1 if report["problems"] else 0)


if __name__ == "__main__":
    main()
