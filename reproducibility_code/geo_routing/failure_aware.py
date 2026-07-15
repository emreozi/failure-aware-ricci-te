"""Failure-aware, path-based multi-commodity traffic engineering.

This module is the methodological core of the rebuilt Computer Networks paper.
It deliberately separates the routing signal (e.g. Ricci curvature) from the
outcomes used to evaluate resilience (post-failure delivery and utilization).

The nominal optimizer uses the same candidate-path set for every policy and a
two-stage linear program:

1. minimize maximum link utilization (MLU);
2. within a declared MLU slack, minimize latency plus an optional structural
   risk score.

The post-failure optimizer maximizes capacity-feasible delivered traffic on the
residual graph before applying any policy-specific tie-break.  Consequently,
no method receives credit merely for moving flow away from the edges that its
own score labels as risky.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
from typing import Iterable, Mapping, Sequence

import networkx as nx
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix, csr_matrix, hstack, vstack

from .topology import ODDemand


Edge = tuple[int, int]
Path = tuple[int, ...]


def edge_key(u: int, v: int) -> Edge:
    """Canonical key for a physical (bidirectional) link."""

    return (u, v) if u <= v else (v, u)


def _arc_key(G: nx.Graph, u: int, v: int) -> Edge:
    return (u, v) if G.is_directed() else edge_key(u, v)


def path_edges(path: Sequence[int], directed: bool = False) -> tuple[Edge, ...]:
    if directed:
        return tuple((u, v) for u, v in zip(path[:-1], path[1:]))
    return tuple(edge_key(u, v) for u, v in zip(path[:-1], path[1:]))


@dataclass(frozen=True)
class PathRecord:
    commodity: int
    nodes: Path
    edges: tuple[Edge, ...]
    physical_edges: tuple[Edge, ...]
    cost: float


@dataclass
class RoutingSolution:
    success: bool
    message: str
    mlu: float
    average_path_cost: float
    total_demand: float
    path_records: list[PathRecord]
    path_flows: np.ndarray
    edge_loads: dict[Edge, float]
    policy_exposure: float


@dataclass
class FailureOutcome:
    delivered_fraction: float
    max_utilization: float
    average_path_cost: float
    policy_exposure: float
    per_commodity_fraction: list[float]


def _normalise_scores(G: nx.Graph, scores: Mapping[Edge, float] | None) -> dict[Edge, float]:
    supplied = scores or {}
    values = {}
    for u, v in G.edges():
        arc = _arc_key(G, u, v)
        value = supplied.get(arc)
        if value is None:
            value = supplied.get(edge_key(u, v), 0.0)
        values[arc] = max(0.0, float(value))
    vmax = max(values.values(), default=0.0)
    if vmax <= 0.0:
        return {edge: 0.0 for edge in values}
    return {edge: value / vmax for edge, value in values.items()}


def curvature_risk(curvature: Mapping[Edge, float]) -> dict[Edge, float]:
    """Convert curvature into a non-negative risk score without using outcomes."""

    raw = {edge_key(*edge): max(0.0, -float(value)) for edge, value in curvature.items()}
    vmax = max(raw.values(), default=0.0)
    return {edge: (value / vmax if vmax > 0.0 else 0.0) for edge, value in raw.items()}


def degree_risk(G: nx.Graph) -> dict[Edge, float]:
    """Curvature-blind endpoint-degree baseline."""

    degree = dict(G.degree())
    raw = {_arc_key(G, u, v): float(degree[u] * degree[v]) for u, v in G.edges()}
    return _normalise_scores(G, raw)


def betweenness_risk(G: nx.Graph, sample_nodes: int | None = None, seed: int = 0) -> dict[Edge, float]:
    """Curvature-blind edge-betweenness baseline.

    ``sample_nodes`` enables deterministic approximation on large networks.
    """

    if sample_nodes is None or sample_nodes >= G.number_of_nodes():
        raw = nx.edge_betweenness_centrality(G, normalized=True, weight="cost")
    else:
        rng = np.random.default_rng(seed)
        nodes = list(G.nodes())
        sources = list(rng.choice(nodes, size=sample_nodes, replace=False))
        raw = nx.edge_betweenness_centrality_subset(
            G, sources=sources, targets=nodes, normalized=True, weight="cost"
        )
    return _normalise_scores(G, {_arc_key(G, u, v): value for (u, v), value in raw.items()})


def random_risk(G: nx.Graph, seed: int = 0) -> dict[Edge, float]:
    """Seeded placebo score used to detect generic regularisation effects."""

    rng = np.random.default_rng(seed)
    return {_arc_key(G, u, v): float(rng.random()) for u, v in G.edges()}


def build_path_catalog(
    G: nx.Graph,
    demands: Sequence[ODDemand],
    k_paths: int = 8,
    weight: str = "cost",
) -> dict[int, list[Path]]:
    """Build one method-neutral K-shortest-simple-path catalog per commodity."""

    if k_paths < 1:
        raise ValueError("k_paths must be positive")
    catalog: dict[int, list[Path]] = {}
    for commodity, demand in enumerate(demands):
        try:
            generator = nx.shortest_simple_paths(G, demand.source, demand.target, weight=weight)
            catalog[commodity] = [tuple(path) for path in islice(generator, k_paths)]
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            catalog[commodity] = []
    return catalog


def _records_from_catalog(
    G: nx.Graph,
    catalog: Mapping[int, Sequence[Path]],
) -> list[PathRecord]:
    records: list[PathRecord] = []
    for commodity, paths in catalog.items():
        for path in paths:
            edges = path_edges(path, directed=G.is_directed())
            physical_edges = tuple(edge_key(u, v) for u, v in zip(path[:-1], path[1:]))
            cost = sum(float(G[u][v].get("cost", 1.0)) for u, v in zip(path[:-1], path[1:]))
            records.append(PathRecord(commodity=commodity, nodes=tuple(path), edges=edges,
                                      physical_edges=physical_edges, cost=cost))
    return records


def _incidence(
    G: nx.Graph,
    demands: Sequence[ODDemand],
    records: Sequence[PathRecord],
) -> tuple[list[Edge], dict[Edge, int], coo_matrix, coo_matrix]:
    edges = [_arc_key(G, u, v) for u, v in G.edges()]
    edge_index = {edge: idx for idx, edge in enumerate(edges)}

    erows: list[int] = []
    ecols: list[int] = []
    evals: list[float] = []
    drows: list[int] = []
    dcols: list[int] = []
    dvals: list[float] = []
    for path_idx, record in enumerate(records):
        drows.append(record.commodity)
        dcols.append(path_idx)
        dvals.append(1.0)
        for edge in record.edges:
            erows.append(edge_index[edge])
            ecols.append(path_idx)
            evals.append(1.0)

    edge_path = coo_matrix(
        (evals, (erows, ecols)), shape=(len(edges), len(records)), dtype=float
    ).tocsr()
    demand_path = coo_matrix(
        (dvals, (drows, dcols)), shape=(len(demands), len(records)), dtype=float
    ).tocsr()
    return edges, edge_index, edge_path, demand_path


def _path_objective(
    records: Sequence[PathRecord],
    risk: Mapping[Edge, float],
    total_demand: float,
    risk_strength: float,
) -> tuple[np.ndarray, np.ndarray]:
    latency = np.array([record.cost for record in records], dtype=float)
    exposure = np.array(
        [sum(float(risk.get(edge, 0.0)) for edge in record.edges) for record in records],
        dtype=float,
    )
    lat_scale = max(float(np.median(latency)) if latency.size else 1.0, 1e-12)
    risk_positive = exposure[exposure > 0]
    risk_scale = max(float(np.median(risk_positive)) if risk_positive.size else 1.0, 1e-12)
    objective = (latency / lat_scale + risk_strength * exposure / risk_scale) / max(total_demand, 1e-12)
    return objective, exposure


def solve_nominal_te(
    G: nx.Graph,
    demands: Sequence[ODDemand],
    catalog: Mapping[int, Sequence[Path]] | None = None,
    risk_scores: Mapping[Edge, float] | None = None,
    risk_strength: float = 0.0,
    mlu_slack: float = 0.02,
    latency_limit: float | None = None,
    k_paths: int = 8,
) -> RoutingSolution:
    """Solve capacity-aware MCF with a controlled structural-risk tie-break."""

    if not demands or any(d.volume < 0 for d in demands):
        raise ValueError("demands must be non-empty and non-negative")
    if mlu_slack < 0:
        raise ValueError("mlu_slack must be non-negative")
    if latency_limit is not None and latency_limit < 0:
        raise ValueError("latency_limit must be non-negative")
    catalog = dict(catalog or build_path_catalog(G, demands, k_paths=k_paths))
    if any(not catalog.get(idx) for idx in range(len(demands))):
        return RoutingSolution(False, "at least one demand has no candidate path", np.inf, np.inf,
                               sum(d.volume for d in demands), [], np.array([]), {}, np.inf)

    records = _records_from_catalog(G, catalog)
    edges, _, edge_path, demand_path = _incidence(G, demands, records)
    path_count = len(records)
    capacities = np.array([float(G[u][v]["capacity"]) for u, v in edges], dtype=float)
    if np.any(capacities <= 0):
        raise ValueError("all capacities must be positive")

    # Stage 1: exact minimum-MLU routing.
    c1 = np.zeros(path_count + 1)
    c1[-1] = 1.0
    A_ub = hstack([edge_path, csr_matrix(-capacities[:, None])], format="csr")
    b_ub = np.zeros(len(edges))
    A_eq = hstack(
        [demand_path, csr_matrix((len(demands), 1), dtype=float)], format="csr"
    )
    b_eq = np.array([d.volume for d in demands], dtype=float)
    bounds = [(0.0, None)] * (path_count + 1)
    stage1 = linprog(c1, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                     bounds=bounds, method="highs")
    if not stage1.success:
        return RoutingSolution(False, stage1.message, np.inf, np.inf, float(b_eq.sum()),
                               records, np.array([]), {}, np.inf)

    risk = _normalise_scores(G, risk_scores)
    path_obj, exposure = _path_objective(records, risk, float(b_eq.sum()), risk_strength)
    c2 = np.concatenate([path_obj, [0.0]])
    allowed_mlu = float(stage1.x[-1]) * (1.0 + mlu_slack) + 1e-9
    extra = coo_matrix(([1.0], ([0], [path_count])), shape=(1, path_count + 1)).tocsr()
    constraints = [A_ub, extra]
    limits = [b_ub, np.array([allowed_mlu])]
    if latency_limit is not None:
        latency = np.array([record.cost for record in records], dtype=float)
        latency_row = hstack(
            [csr_matrix(latency.reshape(1, -1)), csr_matrix((1, 1), dtype=float)],
            format="csr",
        )
        constraints.append(latency_row)
        limits.append(np.array([latency_limit * float(b_eq.sum())]))
    A2 = vstack(constraints, format="csr")
    b2 = np.concatenate(limits)
    stage2 = linprog(c2, A_ub=A2, b_ub=b2, A_eq=A_eq, b_eq=b_eq,
                     bounds=bounds, method="highs")
    result = stage2 if stage2.success else stage1
    flows = np.maximum(result.x[:path_count], 0.0)
    loads_array = np.asarray(edge_path @ flows).reshape(-1)
    loads = {edge: float(loads_array[idx]) for idx, edge in enumerate(edges)}
    total_demand = float(b_eq.sum())
    avg_cost = float(np.dot(flows, np.array([r.cost for r in records])) / total_demand)
    policy_exposure = float(np.dot(flows, exposure) / total_demand)
    mlu = max((loads[edge] / capacities[idx] for idx, edge in enumerate(edges)), default=0.0)
    return RoutingSolution(True, result.message, float(mlu), avg_cost, total_demand,
                           records, flows, loads, policy_exposure)


def solve_tail_robust_te(
    G: nx.Graph,
    demands: Sequence[ODDemand],
    catalog: Mapping[int, Sequence[Path]] | None = None,
    mlu_slack: float = 0.02,
    latency_limit: float | None = None,
    k_paths: int = 8,
) -> RoutingSolution:
    """Directly minimize worst frozen-route single-physical-link loss.

    The optimizer first finds minimum directional-arc MLU. Within ``mlu_slack``
    and an optional average path-cost limit, it minimizes the maximum total flow
    carried by any physical link (the two directions combined). Dividing this
    exposure by total demand gives the exact worst frozen-route service loss for
    a single physical-link failure.
    """

    scenarios = [frozenset([edge_key(u, v)]) for u, v in G.edges()]
    # Deduplicate the two directions of a physical link in directed instances.
    scenarios = list(dict.fromkeys(scenarios))
    return solve_scenario_risk_te(
        G,
        demands,
        scenarios=scenarios,
        catalog=catalog,
        risk_measure="max",
        mlu_slack=mlu_slack,
        latency_limit=latency_limit,
        k_paths=k_paths,
    )


def _weighted_cvar(losses: np.ndarray, probabilities: np.ndarray, beta: float) -> float:
    """Exact upper-tail CVaR of a finite loss distribution."""

    candidates = np.unique(np.concatenate(([0.0], losses)))
    values = [
        eta + float(np.dot(probabilities, np.maximum(losses - eta, 0.0))) / (1.0 - beta)
        for eta in candidates
    ]
    return float(min(values, default=0.0))


def solve_scenario_risk_te(
    G: nx.Graph,
    demands: Sequence[ODDemand],
    scenarios: Sequence[Iterable[Edge]],
    catalog: Mapping[int, Sequence[Path]] | None = None,
    probabilities: Sequence[float] | None = None,
    risk_measure: str = "cvar",
    beta: float = 0.90,
    mlu_slack: float = 0.02,
    latency_limit: float | None = None,
    k_paths: int = 8,
) -> RoutingSolution:
    """Optimize frozen-route loss over an explicit physical-failure set.

    A path's traffic is lost once if it intersects a scenario, even when the
    scenario contains several failed links.  The lexicographic program first
    minimizes nominal directional-arc MLU, then minimizes expected loss,
    finite-distribution CVaR, or maximum loss under the declared MLU and
    average-path-cost budgets, and finally minimizes latency without worsening
    the optimum scenario risk.  The scenario set is supplied by the experiment
    protocol and is therefore independent of every routing score.
    """

    if not demands or any(d.volume < 0 for d in demands):
        raise ValueError("demands must be non-empty and non-negative")
    if mlu_slack < 0:
        raise ValueError("mlu_slack must be non-negative")
    if latency_limit is not None and latency_limit < 0:
        raise ValueError("latency_limit must be non-negative")
    risk_measure = risk_measure.lower()
    if risk_measure not in {"expected", "cvar", "max"}:
        raise ValueError("risk_measure must be 'expected', 'cvar', or 'max'")
    if risk_measure == "cvar" and not 0.0 < beta < 1.0:
        raise ValueError("beta must lie strictly between zero and one")

    normalized_scenarios = [
        frozenset(edge_key(*edge) for edge in scenario) for scenario in scenarios
    ]
    if not normalized_scenarios or any(not scenario for scenario in normalized_scenarios):
        raise ValueError("scenarios must be non-empty failure sets")
    scenario_count = len(normalized_scenarios)
    if probabilities is None:
        probability_vector = np.full(scenario_count, 1.0 / scenario_count)
    else:
        probability_vector = np.asarray(probabilities, dtype=float)
        if probability_vector.shape != (scenario_count,):
            raise ValueError("probabilities must have one entry per scenario")
        if np.any(probability_vector < 0) or not np.isfinite(probability_vector).all():
            raise ValueError("probabilities must be finite and non-negative")
        probability_sum = float(probability_vector.sum())
        if probability_sum <= 0:
            raise ValueError("probabilities must have positive total mass")
        probability_vector = probability_vector / probability_sum

    catalog = dict(catalog or build_path_catalog(G, demands, k_paths=k_paths))
    if any(not catalog.get(idx) for idx in range(len(demands))):
        return RoutingSolution(False, "at least one demand has no candidate path", np.inf, np.inf,
                               sum(d.volume for d in demands), [], np.array([]), {}, np.inf)

    records = _records_from_catalog(G, catalog)
    edges, _, edge_path, demand_path = _incidence(G, demands, records)
    path_count = len(records)
    capacities = np.array([float(G[u][v]["capacity"]) for u, v in edges], dtype=float)
    if np.any(capacities <= 0):
        raise ValueError("all capacities must be positive")
    demand_vector = np.array([d.volume for d in demands], dtype=float)
    total_demand = float(demand_vector.sum())
    latency = np.array([record.cost for record in records], dtype=float)

    scenario_rows: list[int] = []
    scenario_cols: list[int] = []
    for scenario_idx, scenario in enumerate(normalized_scenarios):
        for path_idx, record in enumerate(records):
            if scenario.intersection(record.physical_edges):
                scenario_rows.append(scenario_idx)
                scenario_cols.append(path_idx)
    scenario_path = coo_matrix(
        (np.ones(len(scenario_rows)), (scenario_rows, scenario_cols)),
        shape=(scenario_count, path_count),
        dtype=float,
    ).tocsr()

    # Variables begin with path flows and U. Risk auxiliaries follow as needed.
    if risk_measure == "expected":
        variable_count = path_count + 1
        risk_objective = np.zeros(variable_count)
        risk_objective[:path_count] = np.asarray(
            probability_vector @ scenario_path
        ).reshape(-1)
        risk_constraints = csr_matrix((0, variable_count), dtype=float)
        risk_limits = np.array([], dtype=float)
    elif risk_measure == "max":
        variable_count = path_count + 2
        risk_objective = np.zeros(variable_count)
        risk_objective[path_count + 1] = 1.0
        risk_constraints = hstack(
            [
                scenario_path,
                csr_matrix((scenario_count, 1), dtype=float),
                csr_matrix(-np.ones((scenario_count, 1))),
            ],
            format="csr",
        )
        risk_limits = np.zeros(scenario_count)
    else:
        # Rockafellar--Uryasev representation: eta + E[(L-eta)+]/(1-beta).
        variable_count = path_count + 2 + scenario_count
        eta_index = path_count + 1
        xi_start = path_count + 2
        risk_objective = np.zeros(variable_count)
        risk_objective[eta_index] = 1.0
        risk_objective[xi_start:] = probability_vector / (1.0 - beta)
        risk_constraints = hstack(
            [
                scenario_path,
                csr_matrix((scenario_count, 1), dtype=float),
                csr_matrix(-np.ones((scenario_count, 1))),
                -csr_matrix(np.eye(scenario_count)),
            ],
            format="csr",
        )
        risk_limits = np.zeros(scenario_count)

    auxiliary_count = variable_count - path_count - 1
    capacity_constraints = hstack(
        [
            edge_path,
            csr_matrix(-capacities[:, None]),
            csr_matrix((len(edges), auxiliary_count), dtype=float),
        ],
        format="csr",
    )
    A_ub = vstack([capacity_constraints, risk_constraints], format="csr")
    b_ub = np.concatenate([np.zeros(len(edges)), risk_limits])
    A_eq = hstack(
        [demand_path, csr_matrix((len(demands), variable_count - path_count), dtype=float)],
        format="csr",
    )
    bounds = [(0.0, None)] * variable_count

    c1 = np.zeros(variable_count)
    c1[path_count] = 1.0
    stage1 = linprog(c1, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=demand_vector,
                     bounds=bounds, method="highs")
    if not stage1.success:
        return RoutingSolution(False, stage1.message, np.inf, np.inf, total_demand,
                               records, np.array([]), {}, np.inf)

    allowed_mlu = float(stage1.x[path_count]) * (1.0 + mlu_slack) + 1e-9
    mlu_row = coo_matrix(
        ([1.0], ([0], [path_count])), shape=(1, variable_count)
    ).tocsr()
    constraints = [A_ub, mlu_row]
    limits = [b_ub, np.array([allowed_mlu])]
    if latency_limit is not None:
        latency_row = hstack(
            [csr_matrix(latency.reshape(1, -1)),
             csr_matrix((1, variable_count - path_count), dtype=float)],
            format="csr",
        )
        constraints.append(latency_row)
        limits.append(np.array([latency_limit * total_demand]))
    A2 = vstack(constraints, format="csr")
    b2 = np.concatenate(limits)
    stage2 = linprog(risk_objective, A_ub=A2, b_ub=b2, A_eq=A_eq, b_eq=demand_vector,
                     bounds=bounds, method="highs")
    if not stage2.success:
        return RoutingSolution(False, stage2.message, np.inf, np.inf, total_demand,
                               records, np.array([]), {}, np.inf)

    risk_row = csr_matrix(risk_objective.reshape(1, -1))
    A3 = vstack([A2, risk_row], format="csr")
    risk_tolerance = 1e-9 * max(1.0, abs(float(stage2.fun)))
    b3 = np.concatenate([b2, [float(stage2.fun) + risk_tolerance]])
    c3 = np.zeros(variable_count)
    c3[:path_count] = latency / max(total_demand, 1e-12)
    stage3 = linprog(c3, A_ub=A3, b_ub=b3, A_eq=A_eq, b_eq=demand_vector,
                     bounds=bounds, method="highs")
    result = stage3 if stage3.success else stage2

    flows = np.maximum(result.x[:path_count], 0.0)
    loads_array = np.asarray(edge_path @ flows).reshape(-1)
    loads = {edge: float(loads_array[idx]) for idx, edge in enumerate(edges)}
    avg_cost = float(np.dot(flows, latency) / max(total_demand, 1e-12))
    mlu = max((loads[edge] / capacities[idx] for idx, edge in enumerate(edges)), default=0.0)
    losses = np.asarray(scenario_path @ flows).reshape(-1) / max(total_demand, 1e-12)
    if risk_measure == "expected":
        policy_exposure = float(np.dot(probability_vector, losses))
    elif risk_measure == "max":
        policy_exposure = float(max(losses, default=0.0))
    else:
        policy_exposure = _weighted_cvar(losses, probability_vector, beta)
    return RoutingSolution(True, result.message, float(mlu), avg_cost, total_demand,
                           records, flows, loads, policy_exposure)


def frozen_failure_outcome(
    G: nx.Graph,
    demands: Sequence[ODDemand],
    solution: RoutingSolution,
    failed_edges: Iterable[Edge],
    risk_scores: Mapping[Edge, float] | None = None,
) -> FailureOutcome:
    """Evaluate a pre-installed routing without post-failure recomputation."""

    failed = {edge_key(*edge) for edge in failed_edges}
    risk = _normalise_scores(G, risk_scores)
    delivered = np.zeros(len(demands), dtype=float)
    loads = {
        _arc_key(G, u, v): 0.0
        for u, v in G.edges()
        if edge_key(u, v) not in failed
    }
    total_cost = 0.0
    total_exposure = 0.0
    for record, flow in zip(solution.path_records, solution.path_flows):
        if flow <= 0.0 or any(edge in failed for edge in record.physical_edges):
            continue
        delivered[record.commodity] += flow
        total_cost += flow * record.cost
        total_exposure += flow * sum(risk.get(edge, 0.0) for edge in record.edges)
        for edge in record.edges:
            loads[edge] += flow

    total_demand = sum(d.volume for d in demands)
    delivered_total = float(delivered.sum())
    max_util = max(
        (load / float(G[u][v]["capacity"]) for (u, v), load in loads.items()),
        default=0.0,
    )
    fractions = [
        float(delivered[idx] / demand.volume) if demand.volume > 0 else 1.0
        for idx, demand in enumerate(demands)
    ]
    return FailureOutcome(
        delivered_fraction=delivered_total / max(total_demand, 1e-12),
        max_utilization=float(max_util),
        average_path_cost=total_cost / max(delivered_total, 1e-12),
        policy_exposure=total_exposure / max(delivered_total, 1e-12),
        per_commodity_fraction=fractions,
    )


def adaptive_failure_outcome(
    G: nx.Graph,
    demands: Sequence[ODDemand],
    failed_edges: Iterable[Edge],
    risk_scores: Mapping[Edge, float] | None = None,
    risk_strength: float = 0.0,
    k_paths: int = 8,
    catalog: Mapping[int, Sequence[Path]] | None = None,
) -> FailureOutcome:
    """Maximize capacity-feasible delivery on the residual graph.

    Delivery is optimized before the policy-specific cost.  This lexicographic
    order makes delivered traffic an independent outcome rather than a renamed
    curvature-exposure score.
    """

    failed = {edge_key(*edge) for edge in failed_edges}
    residual = G.copy()
    residual.remove_edges_from(
        [(u, v) for u, v in residual.edges() if edge_key(u, v) in failed]
    )
    if catalog is None:
        active_catalog = build_path_catalog(residual, demands, k_paths=k_paths)
    else:
        active_catalog = {
            commodity: [
                path
                for path in paths
                if not any(
                    edge_key(u, v) in failed for u, v in zip(path[:-1], path[1:])
                )
            ]
            for commodity, paths in catalog.items()
        }
    records = _records_from_catalog(residual, active_catalog)
    total_demand = sum(d.volume for d in demands)
    if not records:
        return FailureOutcome(0.0, 0.0, np.inf, 0.0, [0.0] * len(demands))

    edges, _, edge_path, demand_path = _incidence(residual, demands, records)
    path_count = len(records)
    capacities = np.array([float(residual[u][v]["capacity"]) for u, v in edges], dtype=float)

    # Capacity and per-commodity upper bounds; paths need not satisfy all demand.
    A_ub = vstack([edge_path, demand_path], format="csr")
    b_ub = np.concatenate([capacities, np.array([d.volume for d in demands])])
    bounds = [(0.0, None)] * path_count
    stage1 = linprog(-np.ones(path_count), A_ub=A_ub, b_ub=b_ub,
                     bounds=bounds, method="highs")
    if not stage1.success:
        return FailureOutcome(0.0, 0.0, np.inf, 0.0, [0.0] * len(demands))
    served_star = float(stage1.x.sum())

    nominal_risk = _normalise_scores(G, risk_scores)
    path_obj, exposure = _path_objective(records, nominal_risk, total_demand, risk_strength)
    delivery_floor = csr_matrix(-np.ones((1, path_count), dtype=float))
    A2 = vstack([A_ub, delivery_floor], format="csr")
    b2 = np.concatenate([b_ub, [-(served_star - 1e-8)]])
    stage2 = linprog(path_obj, A_ub=A2, b_ub=b2, bounds=bounds, method="highs")
    result = stage2 if stage2.success else stage1
    flows = np.maximum(result.x, 0.0)
    served_by_demand = np.asarray(demand_path @ flows).reshape(-1)
    loads_array = np.asarray(edge_path @ flows).reshape(-1)
    max_util = max(
        (loads_array[idx] / capacities[idx] for idx in range(len(edges))), default=0.0
    )
    served = float(flows.sum())
    avg_cost = float(np.dot(flows, np.array([record.cost for record in records])) / max(served, 1e-12))
    avg_exposure = float(np.dot(flows, exposure) / max(served, 1e-12))
    fractions = [
        float(served_by_demand[idx] / demand.volume) if demand.volume > 0 else 1.0
        for idx, demand in enumerate(demands)
    ]
    return FailureOutcome(served / max(total_demand, 1e-12), float(max_util), avg_cost,
                          avg_exposure, fractions)


def random_single_edge_failures(G: nx.Graph, n_scenarios: int, seed: int = 0) -> list[frozenset[Edge]]:
    """Seeded failure scenarios independent of every routing score."""

    edges = sorted({edge_key(u, v) for u, v in G.edges()})
    if n_scenarios > len(edges):
        raise ValueError("n_scenarios exceeds the number of edges")
    rng = np.random.default_rng(seed)
    chosen = rng.choice(len(edges), size=n_scenarios, replace=False)
    return [frozenset([edges[int(idx)]]) for idx in chosen]


def top_ranked_single_edge_failures(
    G: nx.Graph,
    independent_scores: Mapping[Edge, float],
    n_scenarios: int,
) -> list[frozenset[Edge]]:
    """Targeted failures ranked by a declared curvature-independent score."""

    physical_edges = sorted({edge_key(u, v) for u, v in G.edges()})

    def physical_score(edge):
        u, v = edge
        return max(
            float(independent_scores.get(edge, 0.0)),
            float(independent_scores.get((u, v), 0.0)),
            float(independent_scores.get((v, u), 0.0)),
        )

    ranked = sorted(physical_edges, key=lambda edge: (-physical_score(edge), edge))
    return [frozenset([edge]) for edge in ranked[:n_scenarios]]
