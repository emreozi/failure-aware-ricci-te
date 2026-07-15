# Confirmatory REPETITA result

Date: 14 July 2026

Protocol: `CONFIRMATORY_PROTOCOL.md`

Data: ten held-out REPETITA topologies; traffic matrix `0000` used only for
regularization tuning; matrices `0001`--`0004` used for evaluation. The primary
outcome is exhaustive frozen-route service loss over every physical single-link
failure. The experimental unit is the topology.

## Primary result: Ollivier--Ricci versus minimum MLU

- Mean service-loss difference (ORC minus MLU): **+0.4515 percentage points**.
- Topology-cluster bootstrap 95% CI: **[+0.0772, +0.9354] percentage points**.
- Exact two-sided topology-level sign-flip p-value: **0.0625**.
- Direction by topology: ORC better on 4, worse on 5, tied on 1.
- Mean nominal path-cost difference: **+1.365%**.

Decision under the frozen alpha = 0.05 rule: **do not reject the null**. The
experiment provides no evidence that the ORC regularizer improves mean
single-link-failure service delivery beyond capacity-aware minimum-MLU routing.
The observed point estimate is in the harmful direction, but the confirmatory
permutation test does not justify declaring a non-zero harm effect at 5%.

This is not an equivalence result: no smallest effect size of interest or
equivalence margin was preregistered. The defensible wording is "no evidence of
improvement," not "the methods are equivalent."

## Secondary policy comparisons

All deltas are method minus minimum MLU. Holm p-values correct the five
secondary method-vs-MLU tests.

| Policy | Mean service-loss delta (pp) | Bootstrap 95% CI (pp) | Raw sign-flip p | Holm p | Mean path-cost delta |
|---|---:|---:|---:|---:|---:|
| Degree | +0.2695 | [-0.0945, +0.7821] | 0.3711 | 0.8438 | +1.171% |
| Betweenness | +0.2054 | [-0.1594, +0.7173] | 0.5703 | 0.8438 | +1.304% |
| Forman--Ricci | +0.3968 | [+0.1228, +0.7068] | 0.0469 | 0.2344 | +2.284% |
| Ollivier--Ricci | +0.4515 | [+0.0772, +0.9354] | 0.0625 | 0.2500 | +1.365% |
| Random placebo | +0.1969 | [-0.0894, +0.5178] | 0.2812 | 0.8438 | +2.696% |

No secondary comparison survives the specified family-wise correction.

## Exploratory tail-risk signal

ORC reduced the mean across-topology worst-failure loss by 2.780 percentage
points, despite worsening mean failure loss. This apparent tail trade-off is
driven mainly by Belnet2010 (-17.183 pp worst-loss difference) and Fccn
(-11.415 pp). It was a secondary outcome, is heterogeneous, and was inspected
after the primary analysis. It must therefore be labeled exploratory and tested
against explicit robust/CVaR traffic-engineering baselines before it can support
a manuscript claim.

That post-confirmatory test was subsequently performed with a direct
`tail_robust` LP that minimizes maximum physical-link flow exposure within the
same MLU and latency budgets:

- versus MLU, `tail_robust` changed worst-failure loss by **-5.556 pp** on
  average (bootstrap 95% CI [-10.540, -1.349] pp; sign-flip p = 0.0156; better
  on all 7 non-tied topologies);
- versus ORC, `tail_robust` changed worst-failure loss by **-2.776 pp**
  (bootstrap 95% CI [-4.830, -0.980] pp; p = 0.0078; better on all 8 non-tied
  topologies);
- `tail_robust` and ORC had no clear path-cost difference (-0.185% on average;
  p = 0.709).

This comparison is exploratory because `tail_robust` was designed after the
confirmatory secondary outcome was inspected. It nevertheless shows that the
observed tail signal is not unique to curvature and motivates a separately
held-out validation of direct robust optimization.

That separate validation was subsequently frozen and completed on ten new
topologies. Tail-robust reduced worst-failure loss relative to ORC by **2.246
pp** (95% CI [0.871, 3.596] pp improvement; exact p = 0.03125) without a detected
mean-loss or path-cost difference. Relative to minimum MLU it reduced worst loss
by **2.543 pp** (p = 0.0078), with essentially unchanged mean loss and 1.70%
higher path cost. See `TAIL_VALIDATION_PROTOCOL.md` and
`TAIL_VALIDATION_RESULTS.md`.

## Consequence for the rebuilt paper

The rejected manuscript's central claim---that curvature uniquely improves
structural resilience---is not retained. The evidence instead supports a more
precise research contribution:

1. structural-score correlation with a vulnerable link is not the same as
   routing utility;
2. at matched MLU and latency budgets, curvature regularization does not improve
   average post-failure delivery on the held-out real-backbone test;
3. any possible tail-risk benefit must be compared with an optimizer that
   directly targets tail risk, not only with minimum MLU.
