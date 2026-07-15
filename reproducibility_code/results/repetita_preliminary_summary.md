# Preliminary topology-clustered REPETITA analysis

This file is a design-validation artifact, not a manuscript result.
Topologies (n=6): Aarnet, Abilene, Airtel, BtEurope, Nsfnet, Sprint.
Positive service-loss deltas mean worse performance than minimum-MLU.

| Method | Mean loss delta (pp) | 95% cluster bootstrap CI (pp) | Better / worse topologies | Mean path-cost delta | Holm p |
|---|---:|---:|---:|---:|---:|
| degree | +0.373 | [+0.206, +0.523] | 0 / 6 | +3.56% | 0.1562 |
| betweenness | -0.013 | [-0.158, +0.128] | 3 / 3 | +3.14% | 0.8750 |
| forman | +0.334 | [+0.142, +0.550] | 0 / 6 | +2.18% | 0.1562 |
| ollivier | +0.339 | [+0.177, +0.527] | 0 / 6 | +2.74% | 0.1562 |
| random_placebo | +0.167 | [-0.056, +0.404] | 2 / 4 | +3.74% | 0.5625 |

Interpretation is intentionally withheld until the preregistered topology set is complete.
