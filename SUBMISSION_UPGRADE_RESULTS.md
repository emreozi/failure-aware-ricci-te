# Frozen held-out double-failure analysis

Experimental unit: topology (n=12). Negative deltas favor the candidate.

## Primary contrast

Double-failure CVaR(0.90) TE minus Ollivier--Ricci TE, evaluated only on held-out scenarios:

- equal-topology mean delta: -1.297 percentage points
- median delta: -1.048 percentage points
- topology-cluster bootstrap 95% interval: [-2.074, -0.554] percentage points
- exact two-sided sign-flip p: 0.015625
- better / worse / tied topologies: 7 / 3 / 2

## Policy comparisons

| Candidate | Reference | CVaR delta (pp) | 95% CI (pp) | Mean-loss delta (pp) | Max-loss delta (pp) | Path-cost delta |
|---|---|---:|---:|---:|---:|---:|
| double_cvar90 | ollivier | -1.297 | [-2.074, -0.554] | +0.281 | -0.875 | +1.90% |
| single_minimax | min_mlu | -0.936 | [-1.451, -0.436] | +0.094 | -2.072 | +0.97% |
| double_expected | min_mlu | +0.156 | [-0.551, +0.887] | -0.149 | +0.654 | +1.60% |
| double_cvar90 | min_mlu | -0.881 | [-1.474, -0.283] | +0.648 | -0.628 | +3.76% |
| double_minimax | min_mlu | -0.593 | [-1.191, -0.025] | +0.240 | -0.410 | +2.37% |
| single_minimax | ollivier | -1.353 | [-2.172, -0.635] | -0.272 | -2.319 | -0.84% |
| double_expected | ollivier | -0.261 | [-0.839, +0.301] | -0.515 | +0.408 | -0.21% |
| double_minimax | ollivier | -1.009 | [-1.838, -0.223] | -0.126 | -0.657 | +0.53% |

The primary contrast was fixed before outcome inspection. Secondary p-values are stored with Holm adjustments in the JSON output.
