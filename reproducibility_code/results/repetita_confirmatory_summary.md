# Preliminary topology-clustered REPETITA analysis

This file is a design-validation artifact, not a manuscript result.
Topologies (n=10): Aconet, Belnet2010, Easynet, Fatman, Fccn, Garr200109, GtsRomania, Nextgen, Noel, Packetexchange.
Positive service-loss deltas mean worse performance than minimum-MLU.

| Method | Mean loss delta (pp) | 95% cluster bootstrap CI (pp) | Better / worse topologies | Mean path-cost delta | Holm p |
|---|---:|---:|---:|---:|---:|
| degree | +0.270 | [-0.094, +0.782] | 4 / 5 | +1.17% | 0.8438 |
| betweenness | +0.205 | [-0.159, +0.717] | 5 / 4 | +1.30% | 0.8438 |
| forman | +0.397 | [+0.123, +0.707] | 2 / 6 | +2.28% | 0.2344 |
| ollivier | +0.452 | [+0.077, +0.935] | 4 / 5 | +1.36% | 0.2500 |
| random_placebo | +0.197 | [-0.089, +0.518] | 5 / 4 | +2.70% | 0.8438 |

Interpretation is intentionally withheld until the preregistered topology set is complete.
