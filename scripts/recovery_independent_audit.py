#!/usr/bin/env python3
"""Genuinely independent raw-record audit of a Tier-1 export.

Shares NO code with scripts/match_stats.py, scripts/tournament.py or
scripts/dev6_exp0038_audit.py. Everything is recomputed from the raw per-game
`match.jsonl` records and the PGN:

  * W/D/L and exclusion accounting (including orphan half-pairs)
  * pair construction by game index, colour reversal checked against the PGN
  * cluster construction and the observations-per-cluster distribution
  * pentanomial counts
  * CR1 cluster-robust variance of the pair mean, re-derived from scratch
  * Student-t 0.975 quantile from an independent incomplete-beta continued
    fraction (NOT the repo's lookup table)
  * Elo-from-score and an independent cluster bootstrap
  * full PGN replay: every move legal, final outcome matches the record
  * time control, options, binary/asset identity, per-arm file-option load proof
  * null-control validity and clock-starvation diagnostics

Usage: recovery_independent_audit.py <export-run-dir> [--pgn-replay] [--json out]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import subprocess
import tarfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# Independent statistics: no import from the repository's own stats module.
# --------------------------------------------------------------------------
def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta (modified Lentz)."""
    tiny, eps = 1e-300, 3e-16
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < eps:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta I_x(a,b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - math.exp(
        lbeta + b * math.log1p(-x) + a * math.log(x)
    ) * _betacf(b, a, 1.0 - x) / b


def student_t_two_sided_p(t: float, df: int) -> float:
    """P(|T| > t) for T ~ t_df, via the incomplete beta identity."""
    return _betai(df / 2.0, 0.5, df / (df + t * t))


def student_t_975(df: int) -> float:
    """t_{0.975,df} by bisection on an independently implemented tail prob."""
    lo, hi = 0.0, 1000.0
    for _ in range(300):
        mid = (lo + hi) / 2.0
        if student_t_two_sided_p(mid, df) > 0.05:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def elo_from_score(s: float) -> float | None:
    if s <= 0.0 or s >= 1.0:
        return None
    return -400.0 * math.log10(1.0 / s - 1.0)


def cr1_clustered(pair_scores: list[float], labels: list[str]) -> dict:
    """CR1 variance of the mean pair score, clustered by `labels`.

    Re-derived: for clusters g with totals T_g and sizes n_g, the sandwich
    variance of the mean is  G/(G-1) * sum_g (T_g - n_g*mbar)^2 / N^2.
    """
    n = len(pair_scores)
    groups: dict[str, list[float]] = defaultdict(list)
    for s, lab in zip(pair_scores, labels):
        groups[lab].append(s)
    G = len(groups)
    mbar = math.fsum(pair_scores) / n
    ss = math.fsum(
        (math.fsum(v) - len(v) * mbar) ** 2 for v in groups.values()
    )
    var = (G / (G - 1.0)) * ss / (n * n)
    se = math.sqrt(var)
    crit = student_t_975(G - 1)
    lo_s = min(1.0, max(0.0, (mbar - crit * se) / 2.0))
    hi_s = min(1.0, max(0.0, (mbar + crit * se) / 2.0))
    # The repository deliberately rounds its t table UP and clamps df>120 to
    # t_{0.975,120}, which is wider than the exact quantile. Reproduce that
    # convention so the stored interval can be checked exactly, while the
    # exact-quantile interval above remains the independent reference.
    crit_conv = max(crit, 1.979931) if G - 1 > 120 else crit
    conv = [elo_from_score(min(1.0, max(0.0, (mbar - crit_conv * se) / 2.0))),
            elo_from_score(min(1.0, max(0.0, (mbar + crit_conv * se) / 2.0)))]
    # naive (unclustered) variance of the mean, for a design-effect check
    naive_var = math.fsum((s - mbar) ** 2 for s in pair_scores) / (n - 1) / n
    return {
        "pairs": n,
        "clusters": G,
        "pair_mean": mbar,
        "score": mbar / 2.0,
        "cr1_stderr": se,
        "naive_stderr": math.sqrt(naive_var),
        "design_effect": (var / naive_var) if naive_var > 0 else None,
        "t_critical_0975": crit,
        "df": G - 1,
        "elo": elo_from_score(mbar / 2.0),
        "elo_ci95": [elo_from_score(lo_s), elo_from_score(hi_s)],
        "elo_ci95_repo_convention": conv,
        "t_critical_repo_convention": crit_conv,
        "obs_per_cluster": dict(sorted(Counter(len(v) for v in groups.values()).items())),
    }


def cluster_bootstrap(labels: list[str], pair_scores: list[float],
                      reps: int = 20000, seed: int = 987654321) -> list[float]:
    """Resample whole opening clusters with replacement; percentile interval."""
    groups: dict[str, list[float]] = defaultdict(list)
    for s, lab in zip(pair_scores, labels):
        groups[lab].append(s)
    keys = sorted(groups)
    totals = [math.fsum(groups[k]) for k in keys]
    sizes = [len(groups[k]) for k in keys]
    G = len(keys)
    rng = random.Random(seed)
    out = []
    for _ in range(reps):
        tot = 0.0
        cnt = 0
        for _ in range(G):
            j = rng.randrange(G)
            tot += totals[j]
            cnt += sizes[j]
        s = tot / cnt / 2.0
        e = elo_from_score(s)
        if e is not None:
            out.append(e)
    out.sort()
    return [out[int(0.025 * len(out))], out[int(0.975 * len(out)) - 1]]


# --------------------------------------------------------------------------
# Raw-record extraction
# --------------------------------------------------------------------------
def load_job(job: Path) -> dict:
    lines = (job / "match.jsonl").read_text().splitlines()
    config = json.loads(lines[0])["configuration"]
    games, summary = [], None
    for ln in lines[1:]:
        d = json.loads(ln)
        if "summary" in d:
            summary = d["summary"]
        else:
            games.append(d)
    return {"config": config, "games": games, "summary": summary}


def pgn_records(job: Path) -> list[dict]:
    """Parse PGN header blocks & movetext without python-chess."""
    txt = (job / "match.pgn").read_text()
    out = []
    for block in re.split(r"\n\s*\n(?=\[Event )", txt.strip()):
        headers = dict(re.findall(r'\[(\w+)\s+"([^"]*)"\]', block))
        body = block.split("]\n", 1)[-1] if "]\n" in block else ""
        body = re.sub(r"\{[^}]*\}", " ", body)
        out.append({"headers": headers, "movetext": body.strip()})
    return out


def audit_job(job: Path, replay: bool) -> dict:
    d = load_job(job)
    cfg, games, stored = d["config"], d["games"], d["summary"]
    issues: list[str] = []
    name = job.name

    # ---- 1. every game outcome, W/D/L, exclusions -------------------------
    scored = [g for g in games if g["score_a"] is not None]
    unscored = [g for g in games if g["score_a"] is None]
    w = sum(1 for g in scored if g["score_a"] == 1)
    dr = sum(1 for g in scored if g["score_a"] == 0.5)
    lo = sum(1 for g in scored if g["score_a"] == 0)
    for key, mine in (("wins", w), ("draws", dr), ("losses", losses_ := lo),
                      ("games", len(scored)), ("unadjudicated", len(unscored))):
        if stored.get(key) != mine:
            issues.append(f"{name}: stored {key}={stored.get(key)} != recomputed {mine}")

    # result string must agree with score_a given colour reversal by index
    for g in games:
        idx = g["game"] - 1
        a_is_white = (idx % 2 == 0)
        res = g["result"]
        if g["score_a"] is None:
            if res != "1/2-1/2" or g["termination"] != "UNADJUDICATED_MAX_PLIES":
                # a drawn-but-unadjudicated game must be explicit
                if res != "*" and g["termination"] == "UNADJUDICATED_MAX_PLIES":
                    issues.append(f"{name}: game {g['game']} unscored with result {res}")
            continue
        expect = 0.5 if res == "1/2-1/2" else (
            1 if ((res == "1-0") == a_is_white) else 0)
        if g["score_a"] != expect:
            issues.append(f"{name}: game {g['game']} score_a={g['score_a']} "
                          f"contradicts result {res} (A white={a_is_white})")

    # ---- 2. pair construction by index, colour reversal, clusters ---------
    pairs: dict[int, dict] = {}
    for g in games:
        pi = (g["game"] - 1) // 2
        pairs.setdefault(pi, {"opening": g["opening"], "slots": {}})
        pairs[pi]["slots"][(g["game"] - 1) % 2] = g["score_a"]
        if pairs[pi]["opening"] != g["opening"]:
            issues.append(f"{name}: pair {pi} mixes openings")
    complete = {k: v for k, v in pairs.items() if None not in v["slots"].values()}
    incomplete = {k: v for k, v in pairs.items() if None in v["slots"].values()}
    pair_scores = [complete[k]["slots"][0] + complete[k]["slots"][1]
                   for k in sorted(complete)]
    labels = [complete[k]["opening"] for k in sorted(complete)]
    orphan_games = sum(1 for v in incomplete.values()
                       for s in v["slots"].values() if s is not None)
    if len(scored) != 2 * len(complete) + orphan_games:
        issues.append(f"{name}: scored-game accounting does not reconcile")

    # games must be exactly 1..N with no gaps/duplicates
    ids = [g["game"] for g in games]
    if ids != list(range(1, len(games) + 1)):
        issues.append(f"{name}: game ids are not a contiguous 1..N sequence")

    # ---- 3. opening assignment vs the frozen suite ------------------------
    suite_path = ROOT / cfg["opening_file"].split("StockBear/")[-1] \
        if "StockBear/" in cfg["opening_file"] else None
    suite_openings = None
    if suite_path and suite_path.is_file():
        suite_openings = [l.strip() for l in suite_path.read_text().splitlines()
                          if l.strip() and not l.startswith("#")]
        if len(games) > 2 * len(suite_openings):
            issues.append(f"{name}: more pairs than suite openings (suite reuse)")
        # The driver shuffles the suite with Random(--seed) before dealing it
        # out, so the frozen permutation must be reproduced to check assignment.
        names = [l.split("|")[0].strip() for l in suite_openings]
        random.Random(cfg["seed"]).shuffle(names)
        bad_slot = None
        for g in games:
            pi = (g["game"] - 1) // 2
            if g["opening"] != names[pi % len(names)]:
                bad_slot = (g["game"], pi, g["opening"], names[pi % len(names)])
                break
        if bad_slot:
            issues.append(f"{name}: game {bad_slot[0]} opening {bad_slot[2]!r} != "
                          f"seeded suite slot {bad_slot[1]} {bad_slot[3]!r}")
        # every opening dealt exactly once => one pair per cluster
        dealt = [names[((g["game"] - 1) // 2) % len(names)] for g in games[::2]]
        if len(set(dealt)) != len(dealt):
            issues.append(f"{name}: an opening is dealt more than once within the job")

    # ---- 4. statistics ----------------------------------------------------
    stats = cr1_clustered(pair_scores, labels)
    penta = [pair_scores.count(v) for v in (2.0, 1.5, 1.0, 0.5, 0.0)]
    if sum(penta) != len(pair_scores):
        issues.append(f"{name}: pentanomial counts do not sum to pair count")
    elo_score = elo_from_score(math.fsum(g["score_a"] for g in scored) / len(scored))
    boot = cluster_bootstrap(labels, pair_scores)

    stored_cl = stored.get("opening_clustered", {})
    for key, mine in (("clusters", stats["clusters"]),):
        if stored_cl.get(key) != mine:
            issues.append(f"{name}: stored clustered {key} != {mine}")
    if stored_cl.get("elo_difference") is not None:
        if abs(stored_cl["elo_difference"] - stats["elo"]) > 1e-6:
            issues.append(f"{name}: stored clustered Elo differs by "
                          f"{abs(stored_cl['elo_difference'] - stats['elo']):.3g}")
        sci = stored_cl.get("elo_ci95") or [None, None]
        # The stored interval uses the repo's rounded-up t table; it must match
        # that convention AND never be narrower than the exact-quantile interval
        # (a narrower-than-nominal gate interval would bias toward passing).
        for i in (0, 1):
            if sci[i] is None:
                continue
            if abs(sci[i] - stats["elo_ci95_repo_convention"][i]) > 1e-6:
                issues.append(f"{name}: stored clustered CI[{i}] {sci[i]} != "
                              f"repo-convention recomputation "
                              f"{stats['elo_ci95_repo_convention'][i]}")
            narrower = (sci[i] > stats["elo_ci95"][i]) if i == 0 else (
                sci[i] < stats["elo_ci95"][i])
            if narrower:
                issues.append(f"{name}: stored CI[{i}] is NARROWER than the exact "
                              f"95% interval (anti-conservative)")
    sp = stored.get("paired", {})
    if sp.get("pentanomial_counts_2_1.5_1_0.5_0") not in (None, penta):
        issues.append(f"{name}: stored pentanomial != {penta}")
    if sp.get("pairs") not in (None, len(pair_scores)):
        issues.append(f"{name}: stored pairs != {len(pair_scores)}")

    # ---- 5. configuration / identity -------------------------------------
    tc = {"base_ms": cfg["base_ms"], "increment_ms": cfg["increment_ms"],
          "nodes_per_move": cfg["nodes_per_move"], "max_plies": cfg["max_plies"],
          "hash": cfg["hash_requested_mb_each"], "threads": cfg["threads_requested_each"]}
    if (tc["base_ms"], tc["increment_ms"]) != (40, 4):
        issues.append(f"{name}: time control is not 40+4 ms")
    if tc["nodes_per_move"]:
        issues.append(f"{name}: node budget used instead of fixed time")
    if tc["max_plies"] != 240 or tc["hash"] != 16 or tc["threads"] != 1:
        issues.append(f"{name}: max_plies/hash/threads deviate from the frozen control")
    # Binary identity must match the DECLARED design, not merely be equal.
    # exp-0051 was a same-binary ablation; exp-0052 deliberately plays the
    # candidate against the EXACT released dev5 artifact, which is the
    # project's required baseline. Requiring equality would reject the correct
    # design, so instead verify each arm against the digest it should have.
    fp_path = job / "fingerprint.json"
    fp = json.loads(fp_path.read_text()) if fp_path.is_file() else {}
    plan_job = fp.get("plan_job") or {}
    cand_sha = fp.get("packaged_binary_sha256")
    dev5_sha = fp.get("dev5_sha256")
    if not plan_job:
        issues.append(f"{name}: no plan_job; cannot verify arm binary identity")
    else:
        for side, key in (("a", "engine_a"), ("b", "engine_b")):
            want_role = plan_job.get(key, "candidate" if side == "a" else "baseline")
            if plan_job.get("null") and side == "b":
                want_role = plan_job.get(key, "candidate")
                if want_role == "baseline":
                    want_role = "candidate"   # null forces both arms to candidate
            want = cand_sha if want_role == "candidate" else dev5_sha
            got = cfg[f"engine_{side}_sha256"]
            if not want:
                issues.append(f"{name}: no expected digest for arm {side} ({want_role})")
            elif got != want:
                issues.append(
                    f"{name}: arm {side} binary {str(got)[:12]} != expected "
                    f"{want_role} digest {str(want)[:12]}")
        if plan_job.get("engine_a") == plan_job.get("engine_b") == "candidate" \
                and not plan_job.get("null") \
                and cfg["engine_a_sha256"] != cfg["engine_b_sha256"]:
            issues.append(f"{name}: declared same-binary ablation but arms differ")

    # ---- 6. terminations / forfeits / clock starvation -------------------
    terms = Counter(g["termination"].split(" (")[0] for g in games)
    forfeits = sum(1 for g in games if "FORFEIT" in g["termination"].upper())
    failures = sum(1 for g in games if g.get("engine_failure"))
    illegal = sum(1 for g in games if "ILLEGAL" in g["termination"].upper())
    for key, mine in (("time_forfeits", forfeits), ("engine_failures", failures)):
        if stored.get(key) not in (None, mine):
            issues.append(f"{name}: stored {key} != {mine}")
    # clock diagnostics: a starved runner shows clocks driven deeply negative
    rem = [g[k] for g in games for k in ("remaining_white_ms", "remaining_black_ms")
           if g.get(k) is not None]
    clock = {"min_remaining_ms": min(rem), "max_remaining_ms": max(rem),
             "negative_clocks": sum(1 for v in rem if v < 0)}

    # ---- 7. PGN cross-check / full replay -------------------------------
    pgn = pgn_records(job)
    if len(pgn) != len(games):
        issues.append(f"{name}: PGN has {len(pgn)} games, jsonl has {len(games)}")
    else:
        for g, p in zip(games, pgn):
            h = p["headers"]
            if h.get("Round") != str(g["game"]) or h.get("Result") != g["result"]:
                issues.append(f"{name}: PGN header mismatch at game {g['game']}")
                break
            if h.get("TimeControl") != "0.04+0.004":
                issues.append(f"{name}: PGN TimeControl {h.get('TimeControl')}")
                break
    replay_info = None
    if replay:
        import chess
        import chess.pgn
        bad = 0
        checked = 0
        with (job / "match.pgn").open() as fh:
            while True:
                gm = chess.pgn.read_game(fh)
                if gm is None:
                    break
                checked += 1
                board = gm.board()
                ok = True
                for mv in gm.mainline_moves():
                    if mv not in board.legal_moves:
                        ok = False
                        break
                    board.push(mv)
                if not ok:
                    bad += 1
                    continue
                term = gm.headers.get("Termination", "")
                res = gm.headers.get("Result")
                if term == "CHECKMATE" and not board.is_checkmate():
                    bad += 1
                elif term == "UNADJUDICATED_MAX_PLIES":
                    if board.outcome(claim_draw=True) is not None:
                        bad += 1
                elif term in ("THREEFOLD_REPETITION", "FIFTY_MOVES",
                              "INSUFFICIENT_MATERIAL", "STALEMATE"):
                    oc = board.outcome(claim_draw=True)
                    if oc is None or oc.result() != res:
                        bad += 1
        replay_info = {"games_replayed": checked, "inconsistent": bad}
        if bad:
            issues.append(f"{name}: {bad} PGN games fail independent replay")

    return {
        "job": name, "issues": issues,
        "wdl": [w, dr, lo], "scored": len(scored), "unscored": len(unscored),
        "complete_pairs": len(complete), "incomplete_pairs": len(incomplete),
        "orphan_scored_games": orphan_games,
        "games_in_primary_estimate": 2 * len(complete),
        "stats": stats, "pentanomial": penta,
        "elo_from_score_all_scored_games": elo_score,
        "cluster_bootstrap_ci95": boot,
        "terminations": dict(terms), "time_forfeits": forfeits,
        "illegal": illegal, "engine_failures": failures,
        "clock": clock, "config": tc,
        "binary_sha256": cfg["engine_a_sha256"],
        "a_options": cfg["engine_a_options"], "b_options": cfg["engine_b_options"],
        "seed": cfg["seed"], "opening_sha256": cfg["opening_sha256"],
        "suite_openings": len(suite_openings) if suite_openings else None,
        "pgn_replay": replay_info,
        "_pair_scores": pair_scores, "_labels": labels,
    }


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def committed_blob(path: str) -> bytes:
    return subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT,
                          capture_output=True, check=True).stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("export_dir")
    ap.add_argument("--pgn-replay", action="store_true")
    ap.add_argument("--json")
    ap.add_argument("--bootstrap-reps", type=int, default=20000)
    args = ap.parse_args()
    D = Path(args.export_dir)
    jobs = sorted(p for p in D.glob("tier1-*") if p.is_dir())
    results = {}
    all_issues = []
    for j in jobs:
        short = re.sub(r"^tier1-exp\d+-tier1-exp\d+-", "", j.name).split("-run")[0]
        r = audit_job(j, args.pgn_replay)
        results[short] = r
        all_issues += r["issues"]
        s = r["stats"]
        print(f"=== {short} ===")
        print(f"  W/D/L {r['wdl']}  scored={r['scored']} unscored={r['unscored']}")
        print(f"  complete pairs={r['complete_pairs']} incomplete={r['incomplete_pairs']} "
              f"orphan scored games={r['orphan_scored_games']} "
              f"games in primary estimate={r['games_in_primary_estimate']}")
        print(f"  clusters={s['clusters']} obs/cluster={s['obs_per_cluster']} "
              f"design effect={s['design_effect']:.6f}")
        print(f"  pentanomial [2,1.5,1,0.5,0]={r['pentanomial']}")
        print(f"  CR1 Elo {s['elo']:+.4f} CI [{s['elo_ci95'][0]:+.4f}, "
              f"{s['elo_ci95'][1]:+.4f}]  t({s['df']})={s['t_critical_0975']:.6f}")
        print(f"  Elo-from-score(all scored) {r['elo_from_score_all_scored_games']:+.4f}"
              f"  bootstrap [{r['cluster_bootstrap_ci95'][0]:+.4f}, "
              f"{r['cluster_bootstrap_ci95'][1]:+.4f}]")
        print(f"  forfeits={r['time_forfeits']} illegal={r['illegal']} "
              f"failures={r['engine_failures']} clock={r['clock']}")
        if r["pgn_replay"]:
            print(f"  PGN replay: {r['pgn_replay']}")
        print(f"  issues: {len(r['issues'])}")
        for i in r["issues"]:
            print("   !", i)

    # ---- combined frozen scope: batchA + batchB only ---------------------
    if "batchA" in results and "batchB" in results:
        ps, lb = [], []
        for b in ("batchA", "batchB"):
            ps += results[b]["_pair_scores"]
            lb += [f"{b}::{x}" for x in results[b]["_labels"]]
        comb = cr1_clustered(ps, lb)
        boot = cluster_bootstrap(lb, ps, reps=args.bootstrap_reps)
        w = sum(results[b]["wdl"][0] for b in ("batchA", "batchB"))
        dr = sum(results[b]["wdl"][1] for b in ("batchA", "batchB"))
        lo = sum(results[b]["wdl"][2] for b in ("batchA", "batchB"))
        raw_overlap = set(results["batchA"]["_labels"]) & set(results["batchB"]["_labels"])
        print("\n=== FROZEN COMBINED batchA+batchB (independent recomputation) ===")
        print(f"  W/D/L {w}/{dr}/{lo}  scored={w+dr+lo}  clusters={comb['clusters']}")
        print(f"  games in primary estimate={comb['pairs']*2}")
        print(f"  CR1 Elo {comb['elo']:+.4f}  CI [{comb['elo_ci95'][0]:+.4f}, "
              f"{comb['elo_ci95'][1]:+.4f}]")
        print(f"  bootstrap [{boot[0]:+.4f}, {boot[1]:+.4f}]")
        print(f"  batch label overlap: {len(raw_overlap)}")
        results["_combined"] = {"wdl": [w, dr, lo], "stats": comb,
                               "bootstrap_ci95": boot,
                               "batch_label_overlap": len(raw_overlap)}

    # ---- integrity: committed blobs, checksums, assets, PST load ---------
    print("\n=== integrity ===")
    tracked = subprocess.run(["git", "ls-files", "--", str(D)], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.split()
    mismatch = [f for f in tracked
                if sha_bytes(committed_blob(f)) != sha_bytes((ROOT / f).read_bytes())]
    print(f"  committed blobs: {len(tracked)-len(mismatch)}/{len(tracked)} match")
    if mismatch:
        all_issues.append(f"committed blob mismatch: {mismatch}")
    sums_ok = sums_tot = 0
    for j in jobs:
        for line in (j / "SHA256SUMS.txt").read_text().splitlines():
            h, _, fn = line.partition("  ")
            fn = fn.strip()
            sums_tot += 1
            t = j / fn
            if t.is_file() and sha_bytes(t.read_bytes()) == h:
                sums_ok += 1
            else:
                all_issues.append(f"checksum failure {j.name}/{fn}")
    print(f"  per-job SHA256SUMS: {sums_ok}/{sums_tot} verified")

    # File-valued options (PstFile AND, from exp-0052, EvalParams) must have
    # positive per-arm load proof. A missing file is NOT fatal to the engine:
    # it prints "could not load" and plays on with fallback tables, which would
    # fake a result. The runner renamed pst_probe_* to option_probe_* when the
    # guard was generalised; accept both so older exports still audit.
    load_proof = {}
    for short, j in zip(results, jobs):
        log = (j / "run.log").read_text()
        verified = re.findall(r"arm ([AB]) (\w+) LOAD VERIFIED (\S+)", log)
        load_proof[short] = [f"arm {a} {opt}: {p}" for a, opt, p in verified]
        # Cross-check the runner's claim against the raw probe output and
        # against the option list the job actually declared.
        fp = j / "fingerprint.json"
        declared = {}
        spec = {}
        if fp.is_file():
            fj = json.loads(fp.read_text())
            spec = fj.get("plan_job") or {}
            if not spec:
                all_issues.append(f"{short}: fingerprint has no plan_job; cannot "
                                  f"verify which options the job declared")
            # Independently confirm the job ran the FROZEN plan's config, by
            # reading the plan out of the pinned source commit rather than
            # trusting the fingerprint's own copy.
            exp_id = fj.get("experiment_id", "")
            mf = j / "manifest.json"
            if not exp_id and mf.is_file():
                exp_id = json.loads(mf.read_text()).get("experiment_id", "")
            if not exp_id:
                all_issues.append(f"{short}: cannot determine experiment_id")
            plan_path = f"benchmarks/exp-runs/tier1-plan-{exp_id}.json"
            src = fj.get("source_sha") or ""
            if src:
                try:
                    blob = subprocess.check_output(
                        ["git", "show", f"{src}:{plan_path}"], cwd=ROOT,
                        text=True, stderr=subprocess.DEVNULL)
                    frozen = {x["id"]: x for x in json.loads(blob)["jobs"]}
                    want = frozen.get(spec.get("id"))
                    if want is None:
                        all_issues.append(f"{short}: job id absent from the frozen plan")
                    else:
                        for k in ("a_options", "b_options", "engine_a", "engine_b",
                                  "games", "seed", "openings", "control", "null",
                                  "prereg_sha256", "assets"):
                            if spec.get(k) != want.get(k):
                                all_issues.append(
                                    f"{short}: {k} differs from the frozen plan")
                except (subprocess.CalledProcessError, KeyError, ValueError):
                    all_issues.append(f"{short}: could not read frozen plan {plan_path} "
                                      f"at pinned source {src[:8]}")
            for side, key in (("A", "a_options"), ("B", "b_options")):
                for o in spec.get(key, []) or []:
                    if "=" in o:
                        k, v = o.split("=", 1)
                        if k.strip().lower() in ("pstfile", "evalparams") and v.strip():
                            declared.setdefault(side, []).append(
                                (k.strip(), v.strip()))
            if spec.get("null"):
                declared["B"] = list(declared.get("A", []))
        for side in ("A", "B"):
            probe = j / f"option_probe_{side}.txt"
            generalised_guard = probe.is_file()
            if not generalised_guard:
                # Exports made before the guard covered EvalParams used
                # pst_probe_*; requiring a runner record that did not exist
                # yet would retroactively invalidate valid historical runs.
                probe = j / f"pst_probe_{side}.txt"
            if not probe.is_file():
                continue
            txt = probe.read_text()
            if "could not load" in txt:
                all_issues.append(f"{short}: probe {side} reports a load failure")
            for opt, path in declared.get(side, []):
                if f"{opt} loaded: {path}" not in txt:
                    all_issues.append(
                        f"{short}: arm {side} declared {opt}={path} but the probe "
                        f"has no positive load confirmation")
                elif generalised_guard and not any(
                        v.startswith(f"arm {side} {opt}: {path}")
                        for v in load_proof[short]):
                    all_issues.append(
                        f"{short}: arm {side} {opt} loaded but the runner did not "
                        f"record LOAD VERIFIED")
        tg = next(j.glob("stockbear-*.tar.gz"), None)
        if tg:
            with tarfile.open(tg, "r:gz") as tf:
                bi = next(m for m in tf.getmembers() if m.name.endswith("BUILD_INFO.json"))
                info = json.load(tf.extractfile(bi))
                for path, digest in (info.get("assets_sha256") or {}).items():
                    members = [m for m in tf.getmembers() if m.name.endswith(Path(path).name)]
                    if not members:
                        all_issues.append(f"{short}: declared asset {path} absent from package")
                        continue
                    actual = sha_bytes(tf.extractfile(members[0]).read())
                    if actual != digest:
                        all_issues.append(f"{short}: packaged asset {path} digest mismatch")
                    repo = ROOT / path
                    if repo.is_file() and sha_bytes(repo.read_bytes()) != actual:
                        all_issues.append(f"{short}: packaged asset differs from repo {path}")
        print(f"  {short}: {load_proof[short] or 'no file-valued option arm'}")

    # ---- null controls ---------------------------------------------------
    print("\n=== null controls ===")
    nulls_ok = True
    for key in ("stage0", "null"):
        if key in results:
            ci = results[key]["stats"]["elo_ci95"]
            ok = ci[0] < 0 < ci[1]
            nulls_ok &= ok
            print(f"  {key}: CI [{ci[0]:+.4f}, {ci[1]:+.4f}] includes 0: {ok}")

    out = {"export_dir": str(D), "jobs": {k: v for k, v in results.items()},
           "committed_blobs": f"{len(tracked)-len(mismatch)}/{len(tracked)}",
           "checksums": f"{sums_ok}/{sums_tot}", "nulls_ok": bool(nulls_ok),
           "option_load_proof": load_proof, "issues": all_issues}
    for v in out["jobs"].values():
        if isinstance(v, dict):
            v.pop("_pair_scores", None)
            v.pop("_labels", None)
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nTOTAL ISSUES: {len(all_issues)}")
    for i in all_issues:
        print(" !", i)
    print("INDEPENDENT AUDIT", "PASS" if not all_issues else "FAIL")
    return 0 if not all_issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
