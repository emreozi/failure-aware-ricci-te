# Consistency audit for the Computer Networks rebuild

Date: 14 July 2026

## Canonical sources

- Active code: `reproducibility_code/`
- Active planning document: `REVISION_PLAN_COMPUTER_NETWORKS.md`
- Legacy manuscript: `main.tex` (read-only evidence source until claims are revalidated)
- `repo/`, `github_repo/`, `_ovl/`, `arsiv/`, and `arsiv_pdf/` are legacy copies.
  They must not be edited in parallel with the canonical source.

## Blocking inconsistencies found

1. The legacy optimizer collapses distinct OD pairs into one net-supply vector.
   This is not a valid multi-commodity traffic-engineering model because flows
   from unrelated OD pairs can cancel at common terminals.
2. Nominal link capacities are not optimization constraints.  A separate large
   box bound is enforced and capacity is used only to calculate an ex-post
   overflow proxy.
3. The legacy resilience claim is circular: the optimizer penalizes edges whose
   curvature is negative and then calls reduced flow on those same edges
   resilience.  No independent failure outcome establishes the claim.
4. The manuscript states an interior-point nonlinear-programming implementation,
   whereas the released code solves a convex QP with OSQP.
5. The hybrid curvature field assigns zero to uncomputed edges; it cannot be
   described as exact Ollivier--Ricci curvature on the whole graph.
6. The paper equates negative curvature with links whose failure fragments the
   graph, but this relation is neither definitional nor established by the
   reported experiments.
7. The digital-twin terminology is unsupported because the generator is not
   calibrated or validated against an operational network.
8. The theorem and Ricci-flow claims exceed what the implementation and numerical
   evidence establish.  They are quarantined pending independent re-derivation.
9. GraphRicciCurvature 0.5.3.2 calls the Unix-only `fork` multiprocessing
   context and the released exact-ORC pipeline fails on Windows.  The canonical
   implementation now uses a platform-independent exact optimal-transport
   calculation and tests it on a graph with known curvature.

## Corrections implemented in the new experimental core

- OD identities are preserved with `ODDemand` and `make_od_demands`.
- Every method uses a common, method-neutral candidate-path catalog.
- Stage 1 minimizes maximum link utilization using actual capacities.
- Stage 2 permits only a declared MLU slack and then applies latency/risk costs.
- Frozen-route resilience is measured as traffic delivered after edge failures.
- Adaptive resilience maximizes capacity-feasible delivered traffic before any
  method-specific tie-break.
- Random and targeted failure scenarios are generated independently of the
  curvature score under evaluation.
- Degree, betweenness, and seeded-random scores are first-class controls.
- REPETITA directed capacities and OD directions are preserved. Equal-cost
  parallel arcs are represented as capacity bundles; the collapsed arc and
  bundle counts are recorded for every topology.

## Claims that remain quarantined

No new manuscript may currently claim that curvature:

- identifies cut edges or failure-critical links;
- improves post-failure delivery;
- is uniquely necessary for resilience;
- yields self-healing behavior;
- beats capacity-aware traffic engineering;
- scales to operational backbones.

Each claim can be restored only if the new real/synthetic experiments support it
under held-out failure scenarios, uncertainty estimates, and corrected
multiple-comparison procedures.

## Submission-upgrade audit outcome

The following additions were completed after the initial audit under
`SUBMISSION_UPGRADE_PROTOCOL.md` and its dated change log:

- Structural and scenario-risk policies now have the same explicit per-matrix
  MLU and 5% mean-path-cost budgets.
- Expected-loss, finite-distribution CVaR, and minimax objectives count a path
  once when it intersects a multi-link failure scenario.
- Double-link design/evaluation sets are deterministic, disjoint, capped, and
  independent of routing scores and outcomes.
- Twelve previously unused topologies complete the held-out double-failure set;
  the output passes mechanical scenario, policy, latency, finiteness, and row-
  count validation.
- The frozen primary double-CVaR-minus-ORC effect is -1.297 percentage points
  (topology bootstrap 95% CI [-2.074,-0.554], exact sign-flip p=0.015625).
  Mean loss is not claimed to improve; its observed +0.281-point trade-off is
  reported.
- All six frozen ORC sensitivity variants remain in the harmful direction
  relative to minimum MLU.
- Post-upgrade scenario-risk sensitivity retains a lower CVaR(0.90) than ORC
  at CVaR levels 0.80 and 0.95 and with 80 design scenarios. With only 40
  design scenarios the estimate remains negative but its interval crosses
  zero; this dependence is reported rather than hidden.
- The adaptive capacity-feasible ceiling is now reported numerically on the
  same held-out scenario sample. Betweenness has a stronger topology-level
  association with adaptive loss than either Ricci score, so the structural
  signal is not described as uniquely geometric.
- Four fixed scalability instances solve through 69 nodes. Garr201112 remains
  in the sequence as an unsupported unequal-cost-parallel-arc case and is not
  replaced.
- Thirteen unit tests pass, the final JSON integrity audit passes, and the PDF
  builds without undefined references, undefined citations, or overfull boxes.

The audit therefore supports direct failure-risk control as a constructive TE
result. It does not restore any claim that curvature itself improves routing,
that the implementation models packet queues, or that it is carrier-ready.
