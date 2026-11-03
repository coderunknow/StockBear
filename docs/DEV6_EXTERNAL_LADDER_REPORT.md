# exp-0032 — external rating ladder results (pool-specific INTERNAL rating)

Model: **Bradley-Terry-Davidson** (draw-aware, nu = 0.190) fitted by MLE on **3186 games** across **1600 distinct openings** and 13 engines. Opening-cluster bootstrap: 1000 replicates, two-sided 95% percentile CIs. This is an INTERNAL ladder on a FIXED-NODE control (`--nodes 6000`, 40+4 clock not used), this hardware, these exact pinned binaries. It is NOT a 40+4 fixed-time Elo, NOT CCRL/CEGT/FIDE-comparable.

## Estimated internal ratings (mean 0 by construction)

| engine | internal Elo | 95% CI | games |
|---|---|---|---|
| sf8 | +485.8 | [+407.6, +602.0] | 400 |
| sf10 | +330.8 | [+270.1, +413.0] | 399 |
| sf11-L20 | +312.3 | [+245.9, +387.4] | 399 |
| sf9 | +301.9 | [+243.6, +371.8] | 399 |
| sf11-L16 | -4.3 | [-41.7, +33.5] | 396 |
| sf11-L12 | -9.8 | [-52.1, +31.1] | 397 |
| sf11-L8 | -59.0 | [-94.5, -24.9] | 397 |
| dev6_champion | -169.0 | [-210.6, -134.1] | 635 |
| dev5_rebuilt | -173.9 | [-214.7, -136.3] | 637 |
| dev6_failed | -184.7 | [-227.5, -149.7] | 636 |
| dev4 | -197.9 | [-238.4, -162.3] | 638 |
| dev5_official | -205.0 | [-246.8, -165.7] | 640 |
| sf11-L4 | -427.4 | [-479.7, -388.1] | 399 |

Observed draw rate 0.107; fit NLL 2101.9; per-cell residual RMSE 0.033; converged True.

## Games per pairing / residuals (full table)

| subject | anchor | games | observed score | predicted | residual | Elo CI |
|---|---|---|---|---|---|---|
| dev5_official | sf11-L4 | 80 | 0.719 | 0.744 | -0.025 | [93.60859312193553, 247.36236120904312] |
| dev5_rebuilt | sf11-L4 | 80 | 0.713 | 0.771 | -0.059 | [77.10734173598325, 258.54106977449493] |
| dev6_champion | sf11-L4 | 80 | 0.738 | 0.775 | -0.038 | [111.06916047262007, 263.8759226125428] |
| dev6_failed | sf11-L4 | 79 | 0.848 | 0.762 | +0.086 | [208.03794040131413, 434.48032645764954] |
| dev4 | sf11-L4 | 80 | 0.787 | 0.751 | +0.037 | [145.35020582669068, 341.6078672872124] |
| dev5_official | sf11-L8 | 80 | 0.263 | 0.331 | -0.068 | [-272.9491107980623, -105.28403809698321] |
| dev5_rebuilt | sf11-L8 | 79 | 0.386 | 0.365 | +0.021 | [-138.52711966589274, -28.795604173516388] |
| dev6_champion | sf11-L8 | 80 | 0.381 | 0.370 | +0.011 | [-160.85358273350172, -14.773221010768767] |
| dev6_failed | sf11-L8 | 78 | 0.346 | 0.353 | -0.007 | [-194.04484305389263, -34.29692486385736] |
| dev4 | sf11-L8 | 80 | 0.381 | 0.339 | +0.043 | [-153.39464770425454, -20.909074779870217] |
| dev5_official | sf11-L12 | 80 | 0.300 | 0.281 | +0.019 | [-234.85791107795117, -74.46439802146072] |
| dev5_rebuilt | sf11-L12 | 79 | 0.323 | 0.312 | +0.011 | [-206.35386920057775, -55.924758966874364] |
| dev6_champion | sf11-L12 | 79 | 0.297 | 0.317 | -0.019 | [-243.63268950641972, -66.72496615127727] |
| dev6_failed | sf11-L12 | 80 | 0.263 | 0.301 | -0.038 | [-266.19089604859647, -109.56888760675551] |
| dev4 | sf11-L12 | 79 | 0.316 | 0.288 | +0.029 | [-215.88610656467893, -58.16563367103951] |
| dev5_official | sf11-L16 | 80 | 0.269 | 0.276 | -0.007 | [-255.32200923697778, -107.14147223361499] |
| dev5_rebuilt | sf11-L16 | 80 | 0.338 | 0.306 | +0.031 | [-202.72236237529015, -43.59019506231967] |
| dev6_champion | sf11-L16 | 77 | 0.377 | 0.311 | +0.065 | [-163.89127688679247, -25.732139728804803] |
| dev6_failed | sf11-L16 | 79 | 0.241 | 0.295 | -0.055 | [-303.9617637132355, -125.95594573061403] |
| dev4 | sf11-L16 | 80 | 0.250 | 0.283 | -0.033 | [-271.5807494946312, -125.51897385722275] |
| dev5_official | sf11-L20 | 80 | 0.106 | 0.082 | +0.024 | [-546.5658594940817, -273.902337232464] |
| dev5_rebuilt | sf11-L20 | 80 | 0.094 | 0.093 | +0.001 | [-578.5314475630046, -297.33899809709925] |
| dev6_champion | sf11-L20 | 79 | 0.063 | 0.095 | -0.032 | [-716.7148009937426, -359.13655410269286] |
| dev6_failed | sf11-L20 | 80 | 0.125 | 0.089 | +0.036 | [-494.49068497588604, -246.1514170994378] |
| dev4 | sf11-L20 | 80 | 0.056 | 0.085 | -0.029 | [-741.2850144249657, -384.2743926888673] |
| dev5_official | sf8 | 80 | 0.062 | 0.042 | +0.021 | [-684.4723576674919, -370.54942983312145] |
| dev5_rebuilt | sf8 | 80 | 0.056 | 0.047 | +0.009 | [-868.5059763786116, -370.77230496102425] |
| dev6_champion | sf8 | 80 | 0.044 | 0.048 | -0.004 | [-752.462356880717, -437.62990302042317] |
| dev6_failed | sf8 | 80 | 0.019 | 0.045 | -0.026 | [None, -523.8395060397654] |
| dev4 | sf8 | 80 | 0.044 | 0.043 | +0.001 | [None, -406.87354842742593] |
| dev5_official | sf9 | 80 | 0.125 | 0.086 | +0.039 | [-478.90221046604574, -251.55947113792035] |
| dev5_rebuilt | sf9 | 79 | 0.082 | 0.097 | -0.015 | [-645.0904413804028, -330.17885101063536] |
| dev6_champion | sf9 | 80 | 0.087 | 0.099 | -0.012 | [-594.9129453201026, -310.4005285440921] |
| dev6_failed | sf9 | 80 | 0.094 | 0.093 | +0.001 | [-578.5314475630046, -297.33899809709925] |
| dev4 | sf9 | 80 | 0.075 | 0.088 | -0.013 | [-626.6653117346876, -340.2843200286545] |
| dev5_official | sf10 | 80 | 0.075 | 0.077 | -0.002 | [-650.1733389594824, -335.10657910298283] |
| dev5_rebuilt | sf10 | 80 | 0.087 | 0.087 | +0.001 | [-594.9129453201027, -310.4005285440921] |
| dev6_champion | sf10 | 80 | 0.119 | 0.088 | +0.030 | [-507.8061002644759, -255.8945624701527] |
| dev6_failed | sf10 | 80 | 0.087 | 0.083 | +0.004 | [-611.9227900353573, -306.39444350251534] |
| dev4 | sf10 | 79 | 0.044 | 0.079 | -0.035 | [None, -402.04377399613156] |

## Rating-pool coverage, model fit, sensitivity

- Rating range: -427.4 .. +485.8 internal Elo.
- Saturated cells (score <=0.05 or >=0.95): ['sf10', 'sf8'] — retained, never hidden.
- Leave-one-anchor-out subject order:
  - drop sf10: dev5_rebuilt > dev6_champion > dev6_failed > dev4 > dev5_official
  - drop sf11-L12: dev6_champion > dev6_failed > dev5_rebuilt > dev4 > dev5_official
  - drop sf11-L16: dev6_failed > dev5_rebuilt > dev6_champion > dev4 > dev5_official
  - drop sf11-L20: dev6_champion > dev5_rebuilt > dev4 > dev6_failed > dev5_official
  - drop sf11-L4: dev6_champion > dev5_rebuilt > dev5_official > dev6_failed > dev4
  - drop sf11-L8: dev6_champion > dev5_rebuilt > dev6_failed > dev5_official > dev4
  - drop sf8: dev6_champion > dev5_rebuilt > dev6_failed > dev4 > dev5_official
  - drop sf9: dev6_champion > dev5_rebuilt > dev6_failed > dev4 > dev5_official

## Contextual calibration (QUALIFIED, not a claim)

- Status: **NOT DEFENSIBLY CALIBRATED**. SF11 UCI_Elo is an approximate self-rating for a different time control (60+0.6) and full-strength SF; mapping a fixed-node pool onto it is a rough context only. The gap to 3000 Elo is NOT asserted.
- Rough affine context from SF11's own `UCI_Elo` anchors (slope 1.620, intercept 2449.8, anchor residual SD 199 Elo): dev5-official ≈ **2118 Elo context**. This is an approximate SELF-anchored number with unknown, likely large systematic error.

- sf11-L4: internal -427.4 vs SF11 UCI_Elo context 1785
- sf11-L8: internal -59.0 vs SF11 UCI_Elo context 2113
- sf11-L12: internal -9.8 vs SF11 UCI_Elo context 2409
- sf11-L16: internal -4.3 vs SF11 UCI_Elo context 2686
- sf11-L20: internal +312.3 vs SF11 UCI_Elo context 2951

**The numeric gap to 3,000 Elo is NOT defensible from this pool and is NOT asserted.** 3,000 Elo remains a long-term strategic target. Published CCRL ratings and SF11 UCI_Elo are contextual anchors only.

Raw: `benchmarks/exp-runs/exp0032-ladder-*/` (PGN/JSONL/CSV/cell.json), `benchmarks/dev6-baseline/ladder_cells.json`, machine-readable `benchmarks/dev6-baseline/ladder_results.json`. Opponent identities: `docs/DEV6_EXTERNAL_OPPONENTS.md`.
