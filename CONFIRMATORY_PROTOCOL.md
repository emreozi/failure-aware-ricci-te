# Frozen confirmatory protocol

Frozen: 14 July 2026, Europe/Istanbul, before running any failure-aware outcome
on the confirmatory topologies listed below.

This local protocol separates the exploratory design-validation runs from the
next held-out test. It is not a claim of registry-backed preregistration.

## Research question and primary hypothesis

Research question: at matched maximum-link-utilization and latency budgets, does
an Ollivier--Ricci risk regularizer improve single-physical-link-failure service
delivery beyond capacity-aware minimum-MLU traffic engineering?

For topology `g`, let `L_ORC,g` and `L_MLU,g` be mean frozen-route service loss
over all test traffic matrices and all physical single-link failures. The
topology-level primary effect is:

`Delta_g = L_ORC,g - L_MLU,g`.

- `Delta < 0` supports a resilience benefit.
- `Delta = 0` means no improvement.
- `Delta > 0` means the curvature regularizer is harmful on this outcome.

The primary test is two-sided at alpha = 0.05 using an exact topology-level
sign-flip permutation test. The mean effect and a topology-cluster bootstrap 95%
confidence interval are reported. Physical links and traffic matrices are not
treated as independent experimental units.

## Data freeze

- Source: REPETITA `2016TopologyZooUCL_inverseCapacity`.
- Repository commit: `60e679c2f34d9b65b7f256ff6f6963938fa040f9`.
- Training traffic matrix: `0000` only.
- Untouched test traffic matrices: `0001`, `0002`, `0003`, `0004`.
- Confirmatory topologies (fixed order):
  1. Aconet
  2. Easynet
  3. Noel
  4. Belnet2010
  5. Garr200109
  6. Fccn
  7. Packetexchange
  8. GtsRomania
  9. Fatman
  10. Nextgen

All ten were checked before freezing: 17--23 nodes, strongly connected directed
routing graph, five demand matrices, and no unequal-cost parallel arcs.

The following are exploratory and cannot enter the confirmatory test: Aarnet,
Abilene, Airtel, BtEurope, Goodnet, Nsfnet, Oxford, Quest, Sprint, and Uninet.
Rediris is excluded because it contains unequal-cost parallel arcs that the
simple directed-arc model cannot collapse without approximation. Geant2012 is a
separate scalability case and is excluded from this confirmatory inference.

## Fixed routing protocol

- Preserve directed arc capacities and directed OD commodities.
- Treat a physical link failure as simultaneous removal of both directed arcs.
- Collapse parallel arcs only when their IGP weight and delay are equal; sum
  their capacities and report the bundle count.
- Compute curvature on the undirected physical projection and copy the physical
  score to both directed arcs.
- Candidate paths: eight method-neutral shortest simple paths per OD, using
  REPETITA delay as path cost.
- Stage 1: minimize maximum link utilization using the actual directed
  capacities.
- Stage 2: allow at most 2% MLU slack, then minimize delay plus the method score.
- Tune score strength only on traffic matrix `0000` over the fixed grid
  `{0.03, 0.1, 0.3, 1, 3, 10, 30}`.
- Accept at most 5% training path-cost increase relative to the minimum-MLU
  solution; among feasible strengths choose minimum score exposure.
- No failure outcome may be used for tuning.

## Policies

Primary comparison:

- exact unweighted Ollivier--Ricci risk versus minimum MLU.

Secondary controls:

- augmented Forman--Ricci risk;
- endpoint-degree-product risk;
- edge-betweenness risk;
- seeded random-placebo risk.

Secondary policy-vs-MLU sign-flip tests receive Holm correction. The primary ORC
test is reported separately and is not selected from these secondary results.

## Outcomes

Primary outcome:

- mean frozen-route service loss after physical single-link failure.

Secondary outcomes:

- worst frozen-route service loss;
- nominal maximum link utilization;
- nominal mean delay/path cost;
- capacity-feasible adaptive delivered fraction;
- Spearman association between each pre-failure structural score and adaptive
  service loss.

Frozen-route failures are exhaustive. Adaptive outcomes use all physical links
when there are at most 24; otherwise 24 links are sampled without replacement
using the topology-name CRC32 seed. This sampling affects only secondary
adaptive outcomes, not the exhaustive primary outcome.

## Sensitivity analyses (not part of the primary test)

- candidate-path budgets K = 4 and K = 16;
- MLU slack = 0% and 5%;
- random double-link failures;
- exact ORC alpha = 0.25 and 0.75;
- separate reporting by topology size and density.

Sensitivity analyses cannot replace the primary specification or be used to
select a preferred headline result.

## Frozen implementation hashes

- `failure_aware.py`: `4F416628576D465B884C7F423AF3913337D17CF352B38C8600E42BF1E2F6C21C`
- `repetita.py`: `495A448E2CB345D51F62720EB2D78D844BD9A73F3501F9997C12B3DD061A8281`
- `exp_repetita.py`: `B4D490E958B6841FE73461AD5237D0B4D1CABF73E5F0B7B1280B31812B029432`
- `analyze_repetita.py`: `6F0E3F93C6069AA3F89B0CADE8714DE73D17A2835FDEFA5B19C539CBEB118655`

Any implementation change after this freeze must be documented, justified,
re-tested, and followed by a new hash before the confirmatory run. Changes made
after inspecting confirmatory outcomes invalidate the confirmatory label.
