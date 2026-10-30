#!/usr/bin/env python3
"""Regression: an unrecognized suite row must never be silently skipped."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from reference_perft import parse_cases

valid = 'PERFT("sample", "8/8/8/8/8/8/8/8 w - - 0 1", 3, 123ULL)'
assert parse_cases(["// comment", valid]) == [("sample", "8/8/8/8/8/8/8/8 w - - 0 1", "3", "123")]
for bad in ["PERFT(bad)", valid + " ignored", "   PERFT(\"name\", \"fen\", 2, 10UL)",
            'PERFT ("sample", "fen", 3, 123ULL)']:
    try:
        parse_cases([valid, bad])
    except ValueError as exc:
        assert "unparsable perft row" in str(exc), exc
    else:
        raise AssertionError(f"malformed suite row accepted: {bad}")
print("PASS reference perft parser rejects unrecognized and partially matched suite rows")
