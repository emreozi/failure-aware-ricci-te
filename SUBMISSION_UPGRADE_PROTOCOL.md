# Frozen submission-upgrade protocol for Computer Networks

Frozen on 2026-07-14 before running any experiment described below. The
existing exploratory, confirmatory, and tail-validation results were already
known. No outcome from the new topology set or the new double-failure scenario
study had been inspected when this protocol was written.

## 1. Purpose

The submission upgrade has three aims:

1. place the work against robust, failure-aware, and risk-aware traffic
   engineering rather than only against structural graph scores;
2. test whether conclusions survive path-set, utilization-budget, and
   curvature-parameter changes, and report adaptive recovery, runtime, and
   scalability;
3. generalize the single-link tail control to a scenario-based risk-aware
   traffic-engineering formulation supporting expected loss, CVaR, and minimax
   objectives for multi-link failures.

## 2. New method

For a declared set of physical-link failure scenarios, a path is counted once
as lost when it intersects one or more failed links. All scenario-aware methods
first minimize directional-arc MLU. Within the same MLU and mean-path-cost
budgets used by the other policies, they optimize one of:

- uniform expected frozen-route service loss;
- CVaR at beta = 0.90;
- maximum frozen-route service loss.

The existing single-link `tail_robust` model is treated as the special case of
the scenario-minimax formulation where every scenario contains one physical
link. A third lexicographic stage minimizes mean path cost without worsening
the attained risk value.

## 3. New held-out multi-failure topology set

The following twelve previously unused REPETITA topologies are fixed before
outcome inspection:

Sago, Pacificwave, Ibm, Highwinds, Internetmci, Restena, Marnet, BtAsiaPac,
Harnet, Bandcon, HiberniaUs, and Azrena.

Inclusion depends only on availability of graph and traffic-matrix files
0000--0004 and on successful parsing. A topology may be excluded only for a
documented parser error, disconnected demanded OD pair, or solver failure that
persists after a method-neutral numerical tolerance correction. It may not be
replaced on the basis of an outcome.

Traffic matrix 0000 is used for tuning structural regularization. Matrices
0001--0004 are held out for every reported outcome. Candidate paths are the
same eight delay-shortest simple paths for every policy. Nominal MLU slack is
2% and the mean-path-cost budget is 5% relative to minimum-MLU TE.

## 4. Double-failure scenario split

All unordered pairs of distinct physical links define the scenario universe.
Within each topology, scenarios are assigned deterministically by a SHA-256
hash of the topology name and sorted link-pair representation:

- design set: hash parity 0;
- evaluation set: hash parity 1.

If either set exceeds 160 scenarios, the 160 scenarios with the smallest hash
values in that set are retained. Scenario selection uses no routing score,
traffic outcome, or curvature value. Uniform probabilities are used within the
design set. The evaluation set is never supplied to a scenario-aware solver.

## 5. Policies

The held-out double-failure study compares:

1. minimum-MLU TE;
2. Ollivier--Ricci regularization, tuned on matrix 0000;
3. single-link scenario-minimax TE;
4. double-failure expected-loss TE;
5. double-failure CVaR(0.90) TE;
6. double-failure scenario-minimax TE.

All policies use identical candidate paths and matched MLU and latency budgets.

## 6. Outcomes and inference

The experimental unit is the topology.

### Primary outcome

For each topology, compute CVaR(0.90) of frozen-route service loss across the
Cartesian product of held-out traffic matrices and held-out double-failure
scenarios. The primary paired contrast is:

double-failure CVaR TE minus Ollivier--Ricci TE.

Negative values favor the new method. Report the equal-topology mean, median,
topology-cluster bootstrap 95% interval, exact two-sided topology sign-flip
p-value, and better/worse/tied topology counts.

### Secondary outcomes

- the same CVaR contrast against minimum-MLU TE;
- mean and maximum held-out double-failure service loss;
- nominal MLU and relative mean path cost;
- contrasts for expected-loss and scenario-minimax TE;
- adaptive capacity-feasible service loss on a deterministic sample of at most
  40 held-out scenarios per topology and traffic matrix;
- Spearman association of ORC, degree, betweenness, and Forman scores with
  adaptive service loss.

Holm correction is applied across policy comparisons within each secondary
outcome family. Adaptive delivery is a policy-neutral recovery ceiling and is
not presented as a policy win.

## 7. Frozen sensitivity analysis

On the original ten-topology confirmatory set, repeat the ORC-versus-MLU
comparison with one factor changed at a time from the base setting
(K=8, MLU slack=2%, ORC alpha=0.5):

- K=4 and K=16;
- MLU slack=0% and 5%;
- ORC alpha=0.25 and 0.75.

Report topology-level mean single-link frozen-loss effects and relative path
costs. These analyses are robustness checks, not new confirmatory tests.

## 8. Runtime and scalability

Record wall-clock time for parsing, path generation, curvature, tuning, nominal
optimization, scenario optimization, frozen evaluation, and adaptive
evaluation. Record peak process memory where portable measurement is
available.

The fixed scalability sequence is GtsHungary (30 nodes), Geant2012 (40),
Surfnet (50), Garr201112 (61), and Latnet (69). It uses matrix 0000, K=4, the
same 2% MLU and 5% latency budgets, and reports feasibility and timing rather
than mixing these instances into confirmatory inference.

## 9. Decision and change control

No topology, failure scenario, endpoint, or inferential method may be changed
after outcome inspection merely to improve a result. Code defects may be
fixed only with a regression test and a dated note describing whether prior
outputs were affected.

The Computer Networks manuscript will claim a constructive risk-aware routing
contribution only if the new method improves held-out tail risk without
violating the matched MLU and latency budgets. Otherwise the result will be
reported as negative and the journal strategy will be reconsidered rather than
selectively omitting it.
