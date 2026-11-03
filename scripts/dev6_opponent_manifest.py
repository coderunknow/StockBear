#!/usr/bin/env python3
"""Pin the exp-0031/0032 external-ladder opponent pool (reproducible identities).

All opponents were fetched as SOURCE archives from codeload.github.com (an
allowed host), built locally with a pinned GCC 12.2.0 toolchain, and committed
as immutable binaries under benchmarks/binaries/external/. No CDN / no network
weights were needed: Stockfish 8-11 and Weiss 2.0 are classical-eval releases.
This script recomputes binary hashes and writes the machine-readable manifest.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "benchmarks" / "binaries" / "external"
OUT = ROOT / "benchmarks" / "dev6-baseline" / "external_opponents.json"
MD = ROOT / "docs" / "DEV6_EXTERNAL_OPPONENTS.md"

GCC = "gcc (Debian 12.2.0-14+deb12u1) 12.2.0 (GNU ld 2.40, glibc 2.36)"
SF_FLAGS = "make -j2 build ARCH=x86-64-modern COMP=gcc (-msse3 -mpopcnt -DUSE_POPCNT, -O3 -DNDEBUG)"
WEISS_FLAGS = "make -j2 basic CFLAGS='-std=gnu11 -O3 -flto=auto -mpopcnt -mbmi2 -DNDEBUG' CC=gcc"

SOURCES = [
    {"id": "sf8", "engine": "Stockfish", "version": "8 64 POPCNT", "tag": "sf_8",
     "commit": "369eff437cc081eb4b8ab5f519cf3f86b79e87d0",
     "url": "https://github.com/official-stockfish/Stockfish",
     "archive_sha256": "e2b77d801d8837c22c2391b8cae08622c1434a2bb5947ddb08b081e1ad35c76c",
     "binary": "stockfish-sf8", "license": "GPL-3.0", "build": SF_FLAGS,
     "uci_name": "Stockfish 8 64 POPCNT", "network_required": False,
     "rating_source": "Stockfish official release sf_8; published CCRL 40/4 ratings are CONTEXT ONLY, not a rating in this pool",
     "options": {"Skill Level": "spin 0..20 (default 20)", "Hash": "spin", "Threads": "spin"}},
    {"id": "sf9", "engine": "Stockfish", "version": "9 64 POPCNT", "tag": "sf_9",
     "commit": "378c8bdbb8f930472fc4316aa6c417802294bbad",
     "url": "https://github.com/official-stockfish/Stockfish",
     "archive_sha256": "d0f33765376b381868d13cc8bfd4e1fa51040074b7ab388cc93b613dd88f67c4",
     "binary": "stockfish-sf9", "license": "GPL-3.0", "build": SF_FLAGS,
     "uci_name": "Stockfish 9 64 POPCNT", "network_required": False,
     "rating_source": "Stockfish official release sf_9; published CCRL 40/4 ratings CONTEXT ONLY",
     "options": {"Skill Level": "spin 0..20", "Hash": "spin", "Threads": "spin"}},
    {"id": "sf10", "engine": "Stockfish", "version": "10 64 POPCNT", "tag": "sf_10",
     "commit": "b4c239b625285307c5871f1104dc3fb80aa6d5d2",
     "url": "https://github.com/official-stockfish/Stockfish",
     "archive_sha256": "c19c5377daa6f92d798849a1295441d987d25a1b9ae44256e19907ee10c63dd3",
     "binary": "stockfish-sf10", "license": "GPL-3.0", "build": SF_FLAGS,
     "uci_name": "Stockfish 10 64 POPCNT", "network_required": False,
     "rating_source": "Stockfish official release sf_10; published CCRL 40/4 ratings CONTEXT ONLY",
     "options": {"Skill Level": "spin 0..20", "Hash": "spin", "Threads": "spin"}},
    {"id": "sf11", "engine": "Stockfish", "version": "11 64 POPCNT", "tag": "sf_11",
     "commit": "c3483fa9a7d7c0ffa9fcc32b467ca844cfb63790",
     "url": "https://github.com/official-stockfish/Stockfish",
     "archive_sha256": "802261cc601b67bed00c0ef7d21e2125959630f0852a06db9fc9bd74f440b199",
     "binary": "stockfish-sf11", "license": "GPL-3.0", "build": SF_FLAGS,
     "uci_name": "Stockfish 11 64 POPCNT", "network_required": False,
     "rating_source": ("Stockfish official release sf_11; its UCI_Elo option is an INTERNAL "
                       "CCRL-anchored self-rating (1350..2850; mapping "
                       "E = 1346.6 + 143.4*level^0.806 from src/search.cpp, anchored to "
                       "goldfish 1.13 = 2000 and an Ordo fit for 60+0.6 matches). It is "
                       "APPROXIMATE and NOT a certified external rating of this pool."),
     "options": {"Skill Level": "spin 0..20 (default 20)",
                 "UCI_LimitStrength": "check (default false)",
                 "UCI_Elo": "spin 1350..2850 (default 1350)",
                 "Hash": "spin", "Threads": "spin"}},
    {"id": "weiss2", "engine": "Weiss", "version": "2.0", "tag": "v2.0",
     "commit": "0db49c7270f5c6286a983390a5ea2780e1e0c9f4",
     "url": "https://github.com/TerjeKir/weiss",
     "archive_sha256": "ddcd263e493987bd7408a5267bc708f667142e5a3f47b0912cd122f2be643a98",
     "binary": "weiss-v2.0", "license": "GPL-3.0", "build": WEISS_FLAGS,
     "uci_name": "Weiss 2.0", "network_required": False,
     "rating_source": "Weiss official release v2.0; published CCRL ratings CONTEXT ONLY",
     "go_nodes": False,
     "note": ("Independent (non-Stockfish) engine, built from the tagged release. Excluded "
              "from the FIXED-NODE ladder because it does not parse `go nodes` (uci.c "
              "supports wtime/btime/inc/movestogo/movetime/depth/mate only); pinned here "
              "for future fixed-depth/fixed-time diagnostics. Weiss master HEAD was also "
              "attempted and failed to compile (bitboard.h uses a C++ enum with an "
              "underlying type but the Makefile compiles as C11) - documented, not hidden."),
     "options": {"Hash": "spin", "Threads": "spin"}},
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    recs = []
    for s in SOURCES:
        r = dict(s)
        p = BIN / s["binary"]
        r["binary_path"] = str(p.relative_to(ROOT))
        r["binary_sha256"] = sha(p) if p.exists() else "MISSING"
        r["binary_size_bytes"] = p.stat().st_size if p.exists() else 0
        r["compiler"] = GCC
        r["portable_flags_no_march_native"] = True
        r["cpu"] = "Intel Xeon 2.60GHz, popcnt/bmi2/avx2/abm, 2 vCPU"
        recs.append(r)
    manifest = {
        "purpose": "exp-0031/0032 external rating ladder opponent pool (M0.2)",
        "acquisition": "source tarballs from codeload.github.com (allowed host); no release CDN, no NNUE weights",
        "build_environment": {"os": "Debian 12 / glibc 2.36 / Linux 6.1.158+ x86_64",
                              "gcc": GCC, "cpu": "Intel Xeon 2.60GHz, 2 vCPU"},
        "immutable": True,
        "skill_anchor_mapping_sf11": {"formula": "E = 1346.6 + 143.4 * level^0.806 (from SF11 src/search.cpp)",
                                      "levels": {str(l): round(1346.6 + 143.4 * l ** 0.806, 1)
                                                 for l in range(0, 21)}},
        "opponents": recs,
    }
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")

    L = ["# exp-0031/0032 — external ladder opponent pool (pinned identities)", "",
         "All opponents were built from **official source archives fetched via "
         "`codeload.github.com`** (an allowed host) with a pinned GCC 12.2.0 / ld 2.40 / "
         "glibc 2.36 toolchain, no `-march=native` in the pinned commands, no NNUE network "
         "files (classical-eval releases), and committed as immutable binaries under "
         "`benchmarks/binaries/external/`. GPL-3.0 notices: see `THIRD_PARTY.md`. "
         "These are OPPONENTS/benchmark references only; no Stockfish or Weiss source, "
         "weights, or implementation code was copied into StockBear.", "",
         "| id | engine / version | tag | source commit | binary SHA-256 (short) | go nodes | license |",
         "|---|---|---|---|---|---|---|"]
    for r in recs:
        L.append(f"| {r['id']} | {r['engine']} {r['version']} | {r['tag']} | "
                 f"`{r['commit'][:12]}` | `{r['binary_sha256'][:16]}…` | "
                 f"{r.get('go_nodes', True)} | {r['license']} |")
    L += ["", "Full archive/binary SHAs, exact build commands, UCI option sets and "
          "rating-source qualifications: `benchmarks/dev6-baseline/external_opponents.json`.", "",
          "## Rating-system qualifications (critical)", "",
          "- Stockfish 8/9/10/11 and Weiss 2.0 are exact official releases with exact "
          "source commits and binary SHAs. Published CCRL/CEGT ratings are **contextual "
          "anchors only** — different hardware, time control, engine population and "
          "methodology; they are NOT interchangeable with this ladder's internal rating.",
          "- SF11 `UCI_Elo` is an **internal, approximate, self-reported** strength "
          "limiter anchored by Stockfish's own CCRL/Ordo fit (`E = 1346.6 + 143.4·level^0.806`, "
          "from `src/search.cpp`). Integer `Skill Level` is used for reproducible anchors; "
          "its mapped Elo is recorded as approximate context, not a certified external rating.",
          "- `Skill::pick_best` uses a time-seeded PRNG, so individual games are not "
          "bitwise reproducible; the ladder is statistically reproducible (fixed binaries, "
          "options, openings, seeds, reported CIs).",
          "- This ladder reports a **pool-specific internal rating** (fixed-node control, "
          "this hardware, these exact binaries) with CIs. NO absolute/CCRL/FIDE-comparable "
          "Elo is claimed, and the gap to 3,000 Elo is NOT asserted from it.", ""]
    MD.write_text("\n".join(L) + "\n")
    print(f"wrote {OUT} and {MD} ({len(recs)} opponents)")
    for r in recs:
        print(f"  {r['id']:8s} {r['binary_sha256'][:16]}  size={r['binary_size_bytes']}")


if __name__ == "__main__":
    main()
