# v0.1.0-dev4 — published release assets (recorded after publication)

This file records the artifacts that were actually published, so the release can
be audited without trusting the report that preceded it. It was added after the
tag was created; the evidence report at the tag is
[`REPORT.md`](https://github.com/coderunknow/StockBear/blob/v0.1.0-dev4/benchmarks/results/0.1.0-dev4/REPORT.md).

## Release

| Item | Value |
| --- | --- |
| Tag | `v0.1.0-dev4` (annotated) |
| Tagged commit | `9b5778c97ba3d3141ea61fbf3398b7fc231bbf64` — merge commit of PR #6, parents `32e7d9d` (main) and `6bd81fa` (branch head) |
| Release | <https://github.com/coderunknow/StockBear/releases/tag/v0.1.0-dev4> — prerelease, not draft |
| Exact-commit CI (push to `main`) | run [41392388489](https://github.com/coderunknow/StockBear/actions/runs/41392388489) — all jobs passed |
| CI on the tag itself | run [41392403332](https://github.com/coderunknow/StockBear/actions/runs/41392403332) — passed |
| Packaging run | [41393160832](https://github.com/coderunknow/StockBear/actions/runs/41393160832) — built both archives from the tag, re-verified the tag/CI gates, created a draft, checked the asset set, published |

## Assets

| Asset | Size | SHA-256 |
| --- | --- | --- |
| `stockbear-0.1.0-dev4-linux-x64.tar.gz` | 607,343 B | `bc847d7e29be20abd19e17274a1996d2559a3f6cdfcc175b3f96c02de676d721` |
| `stockbear-0.1.0-dev4-windows-x64.zip` | 283,158 B | `185ef6afde387dec7acc0394f496d7199c7adf0e9fc443d91c087798d311c7e1` |
| `SHA256SUMS.txt` | 207 B | `60a1458f4af5df977e79968702bb56f172717115bcf02792a05ff3f8e0dd6aaf` |

## Verification actually performed on the published assets

The manifest and the archives are on a CDN that the development sandbox cannot
reach, so the check ran inside Actions
(run [41393380621](https://github.com/coderunknow/StockBear/actions/runs/41393380621),
evidence also posted as a comment on PR #6):

```
$ sha256sum -c SHA256SUMS.txt
stockbear-0.1.0-dev4-linux-x64.tar.gz: OK
stockbear-0.1.0-dev4-windows-x64.zip: OK

$ tar tzf stockbear-0.1.0-dev4-linux-x64.tar.gz
./  ./README.md  ./stockbear  ./LICENSE

$ python3 -c 'import zipfile; ...' stockbear-0.1.0-dev4-windows-x64.zip
LICENSE  README.md  stockbear.exe

$ ./stockbear uci | head -12
id name StockBear 0.1.0-dev4
id author The StockBear developers
option name Hash type spin default 16 min 1 max 512
...

$ ./stockbear bench --depth 6 | head -1
# StockBear 0.1.0-dev4; threads=1; network=none; kernel=avx2; ...

$ ./stockbear bench --depth 6 | tail -1
# signature e06c4352681ae8eb
$ ./stockbear bench --depth 7 | tail -1
# signature 5bceff035f2a4ae4
```

The two signatures are the dev3 signatures recorded in the report, and
`network=none` confirms the shipped binary carries no neural network.

## What was **not** verified

* The Windows archive was **not executed on a Windows machine by hand**. It is
  built and tested by the Windows CI jobs (`windows-2022 / Debug` and
  `windows-2022 / Release` both passed for the tagged commit), and the packaged
  archive's contents were listed, but "it runs on my Windows box" is not a claim
  this release makes.
* The external code-review bot (`Kilo Code Review`) failed with
  *"Insufficient credits to run review"*. That is a billing state of a third-party
  app, not a finding about the code; purchasing credits is outside this project's
  zero-expenditure rule, so the review was not run. The release therefore rests on
  the self-review recorded in `REPORT.md` §18 and on CI, and says so.
