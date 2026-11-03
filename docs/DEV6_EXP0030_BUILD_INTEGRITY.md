# exp-0030 — reproducible build environment & Track A/B integrity

**E5 decision: PASS** (E1 PASS, E2 PASS, E3 PASS). Integrity/measurement experiment, NOT a strength claim. Pre-registered in `docs/DEV6_PREREG_EXP0030.md` with tolerances frozen before measurement.

## Pinned environment

```json
{
  "os": "Linux-6.1.158+-x86_64-with-glibc2.36",
  "cpu_model": "Intel(R) Xeon(R) Processor @ 2.60GHz",
  "cpu_isa_relevant": [
    "abm",
    "avx",
    "avx2",
    "bmi1",
    "bmi2",
    "fma",
    "popcnt",
    "sse4_2",
    "ssse3"
  ],
  "nproc": 2,
  "ram_mb": 3940,
  "gcc": "gcc (Debian 12.2.0-14+deb12u1) 12.2.0",
  "ld": "GNU ld (GNU Binutils for Debian) 2.40",
  "cmake": "cmake version 4.4.4",
  "glibc": "glibc 2.36",
  "cxx_flags": "-mpopcnt -mbmi2 -mlzcnt -DSB_SEE_CACHE=1 -flto=4",
  "lto": "-flto=4 (in CXX_FLAGS)",
  "build_type": "Release",
  "march_native": false,
  "generator": "Ninja",
  "runtime": {
    "hash_mb": 16,
    "threads": 1,
    "max_plies": 240,
    "fixed_time": "40+4 ms",
    "champion_params": "research-data/params_abc.txt",
    "champion_params_sha256": "8a9dc81fa5921e5b642c790ffa3cf84c2ba68f2193023c19dc7f3f7cea86d0be"
  }
}
```

## Identities

- **A1_dev5_rebuilt**: `build-dev5/stockbear` SHA-256 `214cbed002e58fbc94d74a089491bba94634e9e8d06b782992548fdacaa9b501`
- **A2_candidate_rebuilt**: `build-cand/stockbear` SHA-256 `28b40cd691cc4c2b892aad27f42f4c62b50962e0d8183b9fdc339e1563d66538`
- **B_official_release**: `benchmarks/binaries/stockbear-dev5-release` SHA-256 `391cb50e13ab99168aba0255482554ab5e59d1a34af810bf8f4d2c88e5bdb918`
- **A1_dev5_rebuilt** source: tree `v0.1.0-dev5`, commit `c94571313a1667048468cf6d4e070400dc5ab228`, archive SHA-256 `4107ff56bfacf2b4ad61a05e1928c1de24720d26a4fa112f6fadc1c759746eaa`, 775 files.
- **A2_candidate_rebuilt** source: tree `HEAD`, commit `4ba68115992a92c2c71ef477354e867092525c68`, archive SHA-256 `899ae35a83ba2a7f2e78ace3391952ee886d527ae70a670ac3f73baf0dd28c2d`, 911 files.

## E1 — fixed-node signatures

| binary | bench d6 | bench d16 | bench d12 params_abc |
|---|---|---|---|
| A1_dev5_rebuilt | 243f9a1c1ba5b36f | a14ab62224f837e5 | e45fa2ec2287eb41 |
| A2_candidate_rebuilt | 243f9a1c1ba5b36f | a14ab62224f837e5 | e45fa2ec2287eb41 |
| B_official_release | 243f9a1c1ba5b36f | a14ab62224f837e5 | e45fa2ec2287eb41 |

E1: **PASS**.

## E2 — full fixed-node bench CSV equality (A1 vs A2)

| params | rows | differing rows | identical |
|---|---|---|---|
| default | 12/12 | 0 | True |
| params_abc | 12/12 | 0 | True |

E2: **PASS** (timing columns excluded).

## E3 — fixed-time throughput (NPS, best of 3 runs each)

| binary | nodes | time (s) | NPS |
|---|---|---|---|
| A1_dev5_rebuilt | 6,449,299 | 2.566 | 2.514M |
| A2_candidate_rebuilt | 6,449,299 | 2.628 | 2.455M |
| B_official_release | 6,449,299 | 2.590 | 2.490M |

A2/A1 NPS ratio = **0.9765**, pre-registered tolerance [0.97, 1.03] -> **PASS**. Official Track B / A1 = 0.9906 (reference only, built by a different image).

## Interpretation

E1–E3 pass: Track A is a valid, controlled SOURCE-LEVEL comparison environment (identical fixed-node search and matched fixed-time throughput under one pinned toolchain). The previous +33 Elo `params_abc` control is therefore attributable to the ubuntu-22.04 (dev5 release) vs ubuntu-latest/GCC 13 (lane) build-image mismatch — classified INVALID MEASUREMENT for that control only. Track B (official artifact) remains a separately reported reference; a rebuilt dev5 is never described as the official release binary.

Raw: `benchmarks/exp-runs/exp0030-build-integrity/` (build.log + all bench CSVs), machine-readable `benchmarks/dev6-baseline/build_matrix.json`.

## E4 — fixed-time control match (corroboration)

A2(candidate rebuilt, `params_abc`+TTEval) vs A1(dev5 rebuilt, same), 400 paired games, 40+4 ms, fresh disjoint 200-opening slice: +130 =114 -156, clustered CR1 **-22.6 [-47.4, +2.0] Elo**, 200 clusters. Criterion (CI includes 0): **PASS**.

TIME_FORFEIT events: 5 ({'TIME_FORFEIT (StockBear 0.1.0-dev6, 47.3ms move)': 1, 'TIME_FORFEIT (StockBear 0.1.0-dev6, 30.9ms move)': 1, 'TIME_FORFEIT (StockBear 0.1.0-dev6, 4.7ms move)': 1, 'TIME_FORFEIT (StockBear 0.1.0-dev6, 10.2ms move)': 1, 'TIME_FORFEIT (StockBear 0.1.0-dev5, 16.9ms move)': 1}). Local shared 2-vCPU sandbox: time forfeits and a negative point estimate are consistent with documented local fixed-time noise (ledger, +/-25 Elo). Decisive matches must use isolated runners. The previous +33 Elo control used a DIFFERENT toolchain image; under the matched toolchain here the large positive offset is absent. This local result is NOT used as strength evidence.

Raw E4: `benchmarks/exp-runs/exp0030-control/` (PGN/JSONL/CSV/pooled.json).
