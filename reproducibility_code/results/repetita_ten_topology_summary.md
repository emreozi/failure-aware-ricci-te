# Preliminary topology-clustered REPETITA analysis

This file is a design-validation artifact, not a manuscript result.
Topologies (n=10): Aarnet, Abilene, Airtel, BtEurope, Goodnet, Nsfnet, Oxford, Quest, Sprint, Uninet.
Positive service-loss deltas mean worse performance than minimum-MLU.

| Method | Mean loss delta (pp) | 95% cluster bootstrap CI (pp) | Better / worse topologies | Mean path-cost delta | Holm p |
|---|---:|---:|---:|---:|---:|
| degree | +0.313 | [+0.203, +0.427] | 0 / 10 | +3.24% | 0.0098 |
| betweenness | +0.097 | [-0.089, +0.350] | 5 / 5 | +3.39% | 0.9531 |
| forman | +0.346 | [+0.170, +0.529] | 0 / 10 | +2.47% | 0.0098 |
| ollivier | +0.402 | [+0.183, +0.707] | 0 / 10 | +2.39% | 0.0098 |
| random_placebo | +0.066 | [-0.083, +0.238] | 5 / 5 | +2.95% | 0.9531 |

Interpretation is intentionally withheld until the preregistered topology set is complete.
