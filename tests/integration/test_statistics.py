#!/usr/bin/env python3
"""Known-value tests for scripts/match_stats.py (standard library only).

These pin down the statistics the tournament report quotes, so a regression in
the interval arithmetic cannot silently produce a nicer-looking Elo claim.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "scripts"))

import match_stats  # noqa: E402


def close(a, b, tol=1e-6):
    return abs(a - b) <= tol


def test_wilson_known_value():
    # Wilson 95% interval for 5 successes out of 10 is [0.2366, 0.7634].
    result = match_stats.wilson([1.0] * 5 + [0.0] * 5)
    assert result["games"] == 10
    assert close(result["score"], 0.5)
    lo, hi = result["ci95"]
    assert close(lo, 0.23659, 1e-4), lo
    assert close(hi, 0.76341, 1e-4), hi
    # The interval must stay inside [0, 1] for degenerate samples.
    all_wins = match_stats.wilson([1.0] * 20)
    assert all_wins["ci95"][0] > 0.0 and all_wins["ci95"][1] <= 1.0


def test_interval_shrinks_with_more_games():
    small = match_stats.wilson([1.0, 0.0] * 5)
    large = match_stats.wilson([1.0, 0.0] * 50)
    small_width = small["ci95"][1] - small["ci95"][0]
    large_width = large["ci95"][1] - large["ci95"][0]
    assert large_width < small_width, (small_width, large_width)


def test_elo_transform():
    assert close(match_stats.score_to_elo(0.5), 0.0)
    assert close(match_stats.score_to_elo(0.75), 400.0 * math.log10(3.0))
    assert match_stats.score_to_elo(1.0) == float("inf")
    assert match_stats.score_to_elo(0.0) == float("-inf")


def test_pentanomial_matches_hand_computation():
    # Four opening pairs worth 2, 2, 1.5 and 0.5 points: mean 1.5, i.e. a 75%
    # score. The variance is taken over pair scores, which is what makes the
    # interval honour the dependence between the two games of an opening.
    pairs = [2.0, 2.0, 1.5, 0.5]
    result = match_stats.pentanomial(pairs)
    mean = sum(pairs) / len(pairs)
    variance = sum((p - mean) ** 2 for p in pairs) / (len(pairs) - 1)
    stderr = math.sqrt(variance / len(pairs))
    assert close(result["pair_score_mean"], mean)
    assert close(result["pair_score_stderr"], stderr)
    assert close(result["score"], mean / 2.0)
    assert close(result["elo_difference"], 400.0 * math.log10(0.75 / 0.25))
    lo, hi = result["elo_ci95"]
    assert lo < result["elo_difference"]
    # A 75 % score with only four pairs has no finite upper bound once the
    # interval is clamped at 100 %, so the upper end is serialised as null
    # rather than as the invalid JSON token "Infinity".
    assert hi is None or hi > result["elo_difference"]
    assert result["pentanomial_counts_2_1.5_1_0.5_0"] == [2, 1, 0, 1, 0]


def test_pentanomial_needs_pairs():
    assert "note" in match_stats.pentanomial([2.0])


def test_sprt_decisions():
    strong = match_stats.lmr_step([2.0] * 170 + [1.5] * 30, 0.0, 5.0)
    assert strong["decision"] == "accept H1", strong
    weak = match_stats.lmr_step([0.6] * 170 + [0.5] * 30, 0.0, 5.0)
    assert weak["decision"] == "accept H0", weak
    neutral = match_stats.lmr_step([1.5, 0.5] * 10, 0.0, 5.0)
    assert neutral["decision"] == "continue", neutral
    assert neutral["lower_bound"] < neutral["llr"] < neutral["upper_bound"]
    # A degenerate sample (every pair identical) has no variance information,
    # so the step must say so rather than report a decision.
    degenerate = match_stats.lmr_step([2.0] * 5, 0.0, 5.0)
    assert degenerate["decision"] == "continue"
    assert "degenerate" in degenerate["note"]


def test_summary_is_valid_strict_json():
    # Every match summary must survive a strict JSON round trip, including
    # all-wins and all-losses samples where Elo is unbounded.
    import json
    for scores, pairs in (([1.0] * 20, [2.0] * 10),
                          ([0.0] * 20, [0.0] * 10),
                          ([1.0, 0.5, 0.0, 1.0], [1.5, 1.0])):
        summary = match_stats.summarise(scores, pairs,
                                        match_stats.lmr_step(pairs, 0.0, 5.0))
        text = json.dumps({"summary": summary}, allow_nan=False)
        assert "Infinity" not in text and "NaN" not in text
        assert json.loads(text)["summary"]["paired"] is not None
    all_wins = match_stats.summarise([1.0] * 20, [2.0] * 10,
                                     match_stats.lmr_step([2.0] * 10, 0.0, 5.0))
    assert all_wins["paired"]["elo_difference"] is None
    assert "elo_ci95" in all_wins["paired"]
    # The human-readable report still shows the unbounded direction.
    assert "-inf" in match_stats.format_report(all_wins) or "+inf" in match_stats.format_report(all_wins)


def test_report_contains_uncertainty_and_sample_size():
    summary = match_stats.summarise([1.0, 0.5, 0.0, 1.0], [1.5, 1.0],
                                    match_stats.lmr_step([1.5, 1.0], 0.0, 5.0))
    text = match_stats.format_report(summary)
    assert "games 4:" in text
    assert "opening pairs" in text
    assert "Elo" in text and "[" in text and "]" in text
    assert "sprt" in text


def main():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    failures = 0
    for test in tests:
        try:
            test()
            print("PASS", test.__name__)
        except Exception as error:  # noqa: BLE001 - report every failure
            failures += 1
            print("FAIL", test.__name__, error)
    print(f"tests {len(tests)}, failures {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
