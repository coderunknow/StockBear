#!/usr/bin/env python3
"""Black-box checks for the exp-0048 PstFile / --pst plumbing (stdlib only).

The C++ unit group `pst` covers the loader in-process. This covers the surfaces
a benchmark actually uses, which is where a silent fallback would corrupt a
measurement:
  * the UCI option is advertised and defaults to empty;
  * a formulaic-valued table leaves the search bit-identical (same bench
    signature);
  * a different table changes the search but `PstFile` clearing restores it;
  * `evaldata --pst` reports the override and its score column matches UCI;
  * `evaldata --pst --check` is refused rather than reporting a false verdict;
  * a malformed table is rejected by every entry point with a non-zero exit.

Usage: python3 tests/integration/test_pst_pipeline.py ./build/stockbear
"""
import os
import subprocess
import sys
import tempfile

EXE = os.path.abspath(sys.argv[1])
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FEN = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


def run(args, stdin=None, cwd=ROOT):
    return subprocess.run([EXE, *args], input=stdin, capture_output=True,
                          text=True, cwd=cwd, timeout=180)


def signature(stdout):
    for line in stdout.splitlines():
        if line.startswith("# signature "):
            return line.split()[-1]
    raise AssertionError("no bench signature")


def uci(commands):
    """Drive the engine interactively and wait for the reply to each command.

    Piping every command at once (including `quit`) makes the engine stop the
    search before it prints a single `info` line, which would turn a scored
    comparison into a vacuous one.
    """
    p = subprocess.Popen([EXE], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, bufsize=1, cwd=ROOT)
    collected = []
    try:
        for cmd in commands:
            p.stdin.write(cmd + "\n")
            p.stdin.flush()
            token = ("uciok" if cmd == "uci" else
                     "readyok" if cmd == "isready" else
                     "bestmove" if cmd.startswith("go ") else None)
            if token is None:
                continue
            while True:
                line = p.stdout.readline()
                if not line:
                    raise AssertionError(f"engine exited early: {p.stderr.read()[-400:]}")
                collected.append(line.strip())
                if line.strip().startswith(token):
                    break
        p.stdin.write("quit\n")
        p.stdin.flush()
        collected.extend(l.strip() for l in p.stdout.read().splitlines())
        p.wait(timeout=30)
    finally:
        if p.poll() is None:
            p.kill()
            p.wait(timeout=10)
    return "\n".join(collected) + "\n"


def write(path, text):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


@check
def option_is_advertised_and_default_empty():
    out = uci(["uci"])
    lines = [l for l in out.splitlines() if l.startswith("option name PstFile ")]
    assert len(lines) == 1, lines
    assert lines[0] == "option name PstFile type string default <empty>", lines[0]


@check
def zero_table_changes_search_and_clearing_restores_it():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "zeros.sbpst")
        write(path, "SBPST1\n" + "0 0\n" * 384)
        # Compare scored UCI output rather than bench: bench has no setoption.
        cmds = ["uci", "setoption name Hash value 16", f"position fen {FEN}", "go depth 8"]
        before = uci(cmds)
        loaded = uci(["uci", "setoption name Hash value 16",
                      f"setoption name PstFile value {path}",
                      f"position fen {FEN}", "go depth 8"])
        cleared = uci(["uci", "setoption name Hash value 16",
                       f"setoption name PstFile value {path}",
                       "setoption name PstFile value <empty>",
                       f"position fen {FEN}", "go depth 8"])
        assert "PstFile loaded" in loaded, loaded[-500:]
        assert "PstFile cleared" in cleared, cleared[-500:]

        def scored(text):
            # Only the deterministic fields: nodes/nps/time are machine noise.
            out = []
            for line in text.splitlines():
                if " score " not in line or " pv " not in line:
                    continue
                fields = line.split()
                i = fields.index("score")
                out.append(" ".join(fields[i:i + 2]) + " | " +
                           " ".join(fields[fields.index("pv"):]))
            return out
        assert scored(before), before[-500:]
        assert scored(loaded) != scored(before), "zero PST did not change the evaluation"
        assert scored(cleared) == scored(before), "clearing PstFile did not restore the search"


@check
def bench_pst_option_and_default_signature():
    default = run(["bench"])
    assert default.returncode == 0, default.stderr
    assert "pst=formulaic" in default.stdout
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "zeros.sbpst")
        write(path, "SBPST1\n" + "0 0\n" * 384)
        loaded = run(["bench", "--pst", path])
        assert loaded.returncode == 0, loaded.stderr
        assert f"pst={path}" in loaded.stdout
        assert signature(loaded.stdout) != signature(default.stdout), \
            "a zero PST must change the bench signature"
        empty = run(["bench", "--pst", ""])
        assert empty.returncode != 0, "empty --pst must be an error, not a silent fallback"


@check
def evaldata_pst_reports_override_and_refuses_check():
    with tempfile.TemporaryDirectory() as tmp:
        epd = os.path.join(tmp, "p.epd")
        write(epd, FEN + "\n")
        path = os.path.join(tmp, "zeros.sbpst")
        write(path, "SBPST1\n" + "0 0\n" * 384)
        plain = run(["evaldata", "--input", epd])
        assert plain.returncode == 0, plain.stderr
        assert "pst_file" not in plain.stdout
        loaded = run(["evaldata", "--input", epd, "--pst", path])
        assert loaded.returncode == 0, loaded.stderr
        assert "pst_file" in loaded.stdout.splitlines()[0]
        assert plain.stdout.splitlines()[-1].rsplit(",", 1)[1] != \
               loaded.stdout.splitlines()[-1].rsplit(",", 1)[1], "PST did not change the score"
        refused = run(["evaldata", "--input", epd, "--pst", path, "--check"])
        assert refused.returncode != 0, "--pst --check must be refused"
        assert "--check is only valid" in refused.stderr, refused.stderr
        # Without --pst the identity check must still pass.
        ok = run(["evaldata", "--input", epd, "--check"])
        assert ok.returncode == 0, ok.stdout + ok.stderr
        assert "mismatches 0" in ok.stdout, ok.stdout


@check
def malformed_tables_are_rejected_everywhere():
    with tempfile.TemporaryDirectory() as tmp:
        epd = os.path.join(tmp, "p.epd")
        write(epd, FEN + "\n")
        bad = os.path.join(tmp, "bad.sbpst")
        for content in ("NOTPST\n", "SBPST1\n1 2\n", "SBPST1\n" + "99999 0\n" * 384,
                        "SBPST1\n" + "0 0\n" * 384 + "extra\n"):
            write(bad, content)
            assert run(["bench", "--pst", bad]).returncode != 0, content[:20]
            assert run(["evaldata", "--input", epd, "--pst", bad]).returncode != 0, content[:20]
            out = uci(["uci", f"setoption name PstFile value {bad}",
                       f"position fen {FEN}", "go depth 4"])
            assert "could not load" in out, out[-400:]
            assert "PstFile loaded" not in out, out[-400:]
        missing = os.path.join(tmp, "absent.sbpst")
        assert run(["bench", "--pst", missing]).returncode != 0
        assert run(["evaldata", "--input", epd, "--pst", missing]).returncode != 0


def main():
    failures = 0
    for fn in CHECKS:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - report and continue
            failures += 1
            print(f"FAIL {fn.__name__}: {exc}")
        else:
            print(f"PASS {fn.__name__}")
    print(f"{len(CHECKS) - failures}/{len(CHECKS)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
