# Dev6 Tier-1 infrastructure (2026-11-04)

## Problem that was fixed
| defect | evidence | fix |
|---|---|---|
| No manual dispatch | `dev6-lane.yml` had `on: push: paths:` only | new `dev6-tier1.yml` has `workflow_dispatch` **and** a deliberate push-dispatched `tier1-dispatch.json` |
| Benchmark scripts pushed results | `actions_dev6_lane.sh:commit_and_push()` + `[skip ci]` result commits | `scripts/dev6_tier1_job.py` contains **zero** git write operations; only `mode=export` makes one explicit, separately dispatched commit |
| Automatic duplicate runs | old lane fired on any change to three watched paths | new lane has one narrow watched path + `concurrency: dev6-tier1-${{ github.ref }}`, `cancel-in-progress: false` |
| No packaged candidate | Gate 4 unmet | driver builds → packages a tarball → **extracts and tests the extracted binary**, asserting built == packaged == tested SHA-256 |
| No downloadable evidence | both job-logs and artifact `/zip` endpoints 302 to blocked `productionresultssa6.blob.core.windows.net` (EOF) | `mode=export` uses `actions/download-artifact(run-id)` server-side, verifies every `SHA256SUMS.txt`, and mirrors to git; evidence is then retrievable via `git` and `api.github.com` Contents API |
| Retries could change conditions | plan was outside the pinned source | every condition derives from the pinned `source_sha` + the frozen plan read with `git show <sha>:<plan>`; a `fingerprint.json` hash is written per job |
| Artifact hashes unpinned | — | `manifest.json` pins workflow run id, attempt, source SHA, toolchain, binary/package SHA, opening-suite SHA, seeds, options, summary; `SHA256SUMS.txt` covers every evidence file |

## GitHub default-branch constraint (recorded, not bypassed)
GitHub only registers a `workflow_dispatch` workflow once the workflow file
exists on the **default branch**; once registered it can be dispatched against
any branch/tag. This mission must not modify `main`, so `dev6-tier1.yml` also
supports a deliberate commit to `benchmarks/exp-runs/tier1-dispatch.json`
(a push-triggered mechanism proven to work on this branch by the historical
lane runs `41635295602` / `41638608427`). Both mechanisms feed the identical
`prepare` job and the identical frozen plan; no security control is bypassed
and no `main` change is made. `source_sha` may be `HEAD`, which `prepare`
resolves to an exact SHA and pins in every manifest.

## Workflow contract
Inputs / dispatch-file fields: `mode` (`benchmark|export`), `experiment_id`,
`source_sha`, `plan_path`, `source_run_id`. `prepare` resolves config, asserts
the source commit exists, reads the plan **from that commit**, validates it and
emits the job matrix. `benchmark` runs one `ubuntu-latest` VM per matrix job:
pinned build → exact dev5 SHA check → exact bench signature → package →
extract → optional ctest → match → independent CR1/t recomputation →
fingerprint/manifest/SHA256SUMS → `actions/upload-artifact@v4`.
`export` downloads artifacts of a pinned run, verifies checksums, records
artifact IDs from the API, and makes ONE deliberate evidence commit.

## Runner isolation
Each matrix job is a separate GitHub-hosted `ubuntu-latest` VM (not a shared
sandbox core). Tier 2 (local `taskset -c 1`) remains exploration/validation
only and is never reported as Tier 1. Fixed-time 40+4 ms matches always use
`--base-ms/--inc-ms`; `--nodes` is only used for explicitly labelled
fixed-node screens, never for gate evidence.

## Verified integration limitation (2026-11-04)
`gh workflow run dev6-tier1.yml --ref arena/3e6dd5b6-stockbear ...` returned
`HTTP 403: Resource not accessible by integration` on the sandbox's GitHub App
token: the token can read runs/artifacts and push commits but cannot create
workflow dispatch events. Combined with the default-branch registration rule,
this makes the deliberate `tier1-dispatch.json` commit the operative
(push-triggered) manual dispatch mechanism. Both mechanisms remain in the
workflow for environments where the token permits dispatch. No security
control is bypassed.

## Verification status
Filled in from the actual dispatched smoke run and exported artifact; see
`benchmarks/dev6-baseline/tier1_verification.json`. Until that file records a
PASS, no Tier-1 result is claimed.

## VERIFICATION: PASS (2026-11-04)
- Smoke workflow run `41778365897` on source `ddb689a`: `prepare` + `tier1-smoke`
  both **success** on a dedicated `ubuntu-latest` VM. Artifact
  `13298122481` (`tier1-exp0037-tier1-smoke-run41778365897`, 629,705 bytes).
- Export workflow run `41778833297` **success**, evidence commit `5c0aad4`
  under `benchmarks/exp-runs/tier1-export/run-41778365897/`.
- Independent retrieval: `git archive origin/... | tar -x` + `sha256sum -c`
  → **9/9 OK**; GitHub Contents API (`api.github.com`) returned
  `export_manifest.json` verbatim. The blocked blob CDN was not used.
- Gate 4 binary identity asserted on the runner: built == packaged == tested
  SHA-256; `fingerprint.json` pins source SHA, build flags, package SHA,
  opening SHA, seeds, options and control.
- Full machine-readable record:
  `benchmarks/dev6-baseline/tier1_verification.json`.
- The 40 smoke games are DISCARDED (null self-match, no strength inference).
- Defect found and fixed: `.gitignore`'s `*.log` excluded `run.log` from the
  git mirror (the Actions artifact always had it). The export job now
  force-adds logs; this fix applies to all future exports.
