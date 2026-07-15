# Scenario-risk sensitivity protocol

Protocol id: `scenario-risk-sensitivity-v1-2026-07-14`

This protocol was written before inspecting any outcomes from the additional
scenario-risk sensitivity runs.  The already reported submission-upgrade
experiment remains the confirmatory analysis; the analyses below are labeled
post-upgrade, one-factor robustness checks.

## Fixed data roles

- Topologies: the same twelve held-out multi-failure topologies listed in
  `SUBMISSION_UPGRADE_PROTOCOL.md`.
- Traffic matrices: 0001--0004 for evaluation; matrix 0000 is not used by the
  direct scenario-risk policies.
- Candidate paths: `q=8` loopless paths, shared across policies.
- Nominal feasibility: exact minimum MLU followed by the frozen 2% MLU and 5%
  mean-path-cost allowances.
- Failure universe: unordered pairs of physical links.
- Scenario assignment: the existing SHA-256 design/evaluation split.  The
  evaluation set is fixed at up to 160 scenarios and is never supplied to an
  optimizer.

## One-factor conditions

The main condition is CVaR(0.90) with up to 160 design scenarios.  Four
additional conditions change exactly one factor:

1. CVaR(0.80), 160 design scenarios;
2. CVaR(0.95), 160 design scenarios;
3. CVaR(0.90), 40 design scenarios;
4. CVaR(0.90), 80 design scenarios.

The 40- and 80-scenario sets are deterministic prefixes of the same
hash-ordered 160-scenario design set.  No outcome, curvature value, or routing
solution enters scenario selection.

## Outcomes and summaries

For every condition and topology, frozen-route loss is evaluated on the
Cartesian product of four held-out traffic matrices and the unchanged held-out
evaluation scenarios.  We report equal-topology mean held-out CVaR at the
condition's declared beta, CVaR(0.90), mean loss, maximum loss, nominal path
cost, topology-cluster bootstrap 95% intervals for contrasts with ORC and
minimum-MLU TE, and exact two-sided sign-flip p-values.  These are robustness
checks, not new confirmatory tests; p-values are descriptive and are not used
to redefine the primary endpoint.

## Decision rule

The scenario-risk conclusion is considered qualitatively stable when every
one-factor condition has lower held-out upper-tail loss than ORC in the
equal-topology mean and no condition reverses the direction on CVaR(0.90).
Trade-offs in mean loss and path cost must be reported even when tail loss
improves.
