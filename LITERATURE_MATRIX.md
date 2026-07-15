# Literature and positioning matrix (Computer Networks rebuild)

This matrix was frozen before inspecting the new double-failure experiment. It
is an argument map, not a claim that risk-aware traffic engineering is new.

| Line of work | Representative evidence | What it already establishes | Boundary of the present study |
|---|---|---|---|
| Robust/oblivious intradomain TE | Applegate & Cohen (SIGCOMM 2003); Wang et al., COPE (SIGCOMM 2006); Wang et al., R3 (SIGCOMM 2010) | Routing can be optimized against demand uncertainty and failures; robust routing is not a new concept. | We do not claim to invent robust TE. We hold nominal MLU and latency budgets fixed and ask whether a topology-only geometric score adds prescriptive value beyond direct outcome-aligned controls. |
| Software-driven WAN TE | Jain et al., B4 (SIGCOMM 2013); Hong et al., SWAN (SIGCOMM 2013) | Centralized multi-commodity optimization is operationally relevant, and utilization/path constraints matter. | Our path-based LP is deliberately smaller and auditable; the contribution is a controlled evidence design, not a production WAN controller. |
| Failure-aware and fast-reconfiguration TE | Liu et al., FFC (SIGCOMM 2014); Gay et al. (INFOCOM 2017); Kumar et al., SMORE (NSDI 2018) | Failure response can be precomputed and segment-routing path sets can provide robust performance. | We evaluate frozen-route loss and an adaptive ceiling separately so that pre-failure structural avoidance is not confused with post-failure recomputation. |
| Probabilistic/risk-aware TE | Bogle et al., TeaVaR (SIGCOMM 2019) | Value-at-Risk style probabilistic availability/utilization optimization already exists. | Expected loss/CVaR/minimax are outcome-aligned controls, not our novelty claim. The new question is the residual value of curvature after matching these direct controls and validating on held-out topologies and failure scenarios. |
| Robust validation and benchmark discipline | Chang et al. (NSDI 2017); Gay et al., REPETITA (2017); Knight et al., Internet Topology Zoo (2011) | TE claims need repeatable benchmarks, robustness checks, and separation of tuning from evaluation. | We predeclare topology/TM/scenario splits, report topology-level paired inference, include negative results, and avoid selecting instances from observed outcomes. |
| Current outcome- and verification-oriented TE | Perry et al., DOTE (NSDI 2023); Namyar et al., MetaOpt (NSDI 2024); Namyar et al., performance-aware mitigation (NSDI 2025); Schneider et al., worst-load verification (NSDI 2025) | Modern TE work evaluates multi-link faults, heuristic performance gaps, end-to-end mitigation outcomes, and worst loads under failures and route changes. | We do not claim production-system or verifier scale. These works sharpen our question: a structural proxy must be tested against the operational quantity it is supposed to improve. |
| Discrete curvature as network descriptor | Ollivier (2009); Ni et al. (INFOCOM 2015); Sreejith et al. (2016); Samal et al. (2018); Saucan et al. (2019) | Curvature captures nonlocal structural organization and can correlate with network fragility. | Descriptive correlation does not imply routing utility. Our primary target is incremental *prescriptive* value under capacity, demand, and latency constraints. |
| Curvature-guided communication-network routing | Chiriac et al. (IEEE Aerospace 2026) | Forman--Ricci curvature and flow can guide hierarchical community decomposition and parallelizable routing in heterogeneous networks. | Our question is complementary: under shared candidate paths and operational budgets, does curvature improve independently measured delivery after physical failures relative to direct scenario-risk controls? |

## Defensible novelty statement

The study is a falsifiable incremental-value audit of discrete curvature for
traffic engineering. Using the same candidate paths, nominal MLU allowance,
latency allowance, traffic matrices, and physical-failure scenarios, it
compares curvature regularization with curvature-blind structural controls,
placebo regularization, and direct scenario-loss objectives. The claim is not
that curvature or risk-aware TE is new; it is that their relationship has not
been tested under this matched, held-out, outcome-aligned design.

## Claims the manuscript must not make

- “The first robust/risk-aware routing formulation.”
- “CVaR is a novel resilience objective.”
- “Negative curvature identifies failed links” unless failure labels are
  operational and independently observed.
- “Curvature improves resilience” unless the held-out paired uncertainty
  interval supports a practically meaningful improvement.
- “Internet-scale” or “carrier-ready” based only on offline REPETITA LPs.
