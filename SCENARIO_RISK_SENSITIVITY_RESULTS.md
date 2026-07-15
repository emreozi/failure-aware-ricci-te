# Scenario-risk sensitivity and adaptive recovery

All values are equal-topology means over twelve topologies. Negative
deltas favor the CVaR policy. Additional conditions are robustness
checks; the beta=.90, S=160 condition remains the frozen primary.

## One-factor sensitivity versus ORC

| Condition | Declared CVaR delta (pp) | CVaR90 delta (pp) | Mean delta (pp) | Path cost |
|---|---:|---:|---:|---:|
| beta90_s160 | -1.297 | -1.297 | +0.281 | +1.90% |
| beta80_s160 | -1.469 | -1.343 | +0.126 | +1.59% |
| beta95_s160 | -1.106 | -1.212 | +0.253 | +1.94% |
| beta90_s40 | -0.310 | -0.310 | +0.278 | +1.16% |
| beta90_s80 | -1.100 | -1.100 | +0.299 | +1.72% |

## Adaptive capacity-feasible recovery ceiling

| Routing state | Mean loss (pp) | CVaR90 (pp) | Max loss (pp) |
|---|---:|---:|---:|
| Adaptive ceiling | 12.210 | 30.794 | 39.517 |
| Frozen minimum MLU | 20.328 | 38.245 | 45.386 |
| Frozen ORC | 20.332 | 38.785 | 45.747 |
| Frozen single minimax | 20.478 | 37.593 | 44.070 |
| Frozen double CVaR(0.90) | 20.923 | 37.536 | 44.883 |

## Structural score association with adaptive double-failure loss

| Score | Mean topology-level Spearman rho | 95% bootstrap interval |
|---|---:|---:|
| ollivier | +0.428 | [+0.317, +0.548] |
| forman | +0.305 | [+0.191, +0.419] |
| degree | +0.182 | [+0.032, +0.341] |
| betweenness | +0.551 | [+0.422, +0.669] |
