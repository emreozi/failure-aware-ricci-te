"""Held-out REPETITA experiment for failure-aware routing policies.

Traffic matrix 0000 tunes each policy's regularisation strength under common
MLU and latency budgets. Matrices 0001--0004 are untouched evaluation data.
Frozen-route physical single-link failures are exhaustive. Adaptive delivery is
evaluated on the same full set unless an explicit deterministic cap is supplied.
"""

from __future__ import annotations

import argparse
import json
import zlib
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from . import curvature as C
from .failure_aware import (
    adaptive_failure_outcome,
    betweenness_risk,
    build_path_catalog,
    curvature_risk,
    degree_risk,
    edge_key,
    frozen_failure_outcome,
    random_risk,
    solve_nominal_te,
    solve_tail_robust_te,
)
from .repetita import load_instance, physical_projection


REPETITA_COMMIT = "60e679c2f34d9b65b7f256ff6f6963938fa040f9"
DEFAULT_TOPOLOGIES = ["Abilene"]
STRENGTH_GRID = [0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0]


def _summary(values):
    array = np.asarray(values, dtype=float)
    return {
        "mean": float(array.mean()),
        "std": float(array.std(ddof=1)) if len(array) > 1 else 0.0,
        "min": float(array.min()),
        "max": float(array.max()),
        "n": int(len(array)),
    }


def _score_at(scores, edge):
    u, v = edge
    return max(float(scores.get((u, v), 0.0)), float(scores.get((v, u), 0.0)))


def _spearman(scores, impacts, edges):
    x = np.asarray([_score_at(scores, edge) for edge in edges], dtype=float)
    y = np.asarray([impacts[edge] for edge in edges], dtype=float)
    if np.allclose(x, x[0]) or np.allclose(y, y[0]):
        return {"rho": None, "p_value": None}
    result = spearmanr(x, y)
    return {"rho": float(result.statistic), "p_value": float(result.pvalue)}


def _tune_strength(
    graph,
    demands,
    catalog,
    scores,
    baseline_latency,
    mlu_slack,
    latency_slack,
):
    latency_limit = baseline_latency * (1.0 + latency_slack)
    candidates = []
    for strength in STRENGTH_GRID:
        solution = solve_nominal_te(
            graph,
            demands,
            catalog=catalog,
            risk_scores=scores,
            risk_strength=strength,
            mlu_slack=mlu_slack,
        )
        if solution.success:
            candidates.append(
                {
                    "strength": strength,
                    "mlu": solution.mlu,
                    "average_path_cost": solution.average_path_cost,
                    "policy_exposure": solution.policy_exposure,
                    "feasible_latency": solution.average_path_cost <= latency_limit + 1e-9,
                }
            )
    feasible = [candidate for candidate in candidates if candidate["feasible_latency"]]
    if not feasible:
        return 0.0, candidates
    chosen = min(feasible, key=lambda item: (item["policy_exposure"], item["average_path_cost"]))
    return float(chosen["strength"]), candidates


def run_topology(
    dataset_root,
    topology_name,
    test_indices=(1, 2, 3, 4),
    k_paths=8,
    mlu_slack=0.02,
    latency_slack=0.05,
    max_adaptive_links=None,
    include_tail_robust=False,
):
    topology_path = Path(dataset_root) / f"{topology_name}.graph"
    train_path = Path(dataset_root) / f"{topology_name}.0000.demands"
    training = load_instance(topology_path, train_path)
    graph = training.graph
    physical = physical_projection(graph)
    physical_edges = sorted({edge_key(u, v) for u, v in graph.edges()})
    if max_adaptive_links is not None and len(physical_edges) > max_adaptive_links:
        rng = np.random.default_rng(zlib.crc32(topology_name.encode("utf-8")))
        indices = sorted(
            int(index)
            for index in rng.choice(
                len(physical_edges), size=max_adaptive_links, replace=False
            )
        )
        adaptive_edges = [physical_edges[index] for index in indices]
    else:
        adaptive_edges = physical_edges

    forman, t_forman = C.forman_all(physical)
    ollivier, t_ollivier = C.ollivier_all(physical, alpha=0.5)
    scores = {
        "degree": degree_risk(physical),
        "betweenness": betweenness_risk(physical),
        "forman": curvature_risk(forman),
        "ollivier": curvature_risk(ollivier),
        "random_placebo": random_risk(
            physical, seed=zlib.crc32(topology_name.encode("utf-8"))
        ),
    }

    training_catalog = build_path_catalog(graph, training.demands, k_paths=k_paths)
    baseline_train = solve_nominal_te(
        graph, training.demands, catalog=training_catalog, mlu_slack=mlu_slack
    )
    if not baseline_train.success:
        raise RuntimeError(f"training baseline failed for {topology_name}: {baseline_train.message}")

    strengths = {"mlu": 0.0}
    tuning = {}
    for method, score in scores.items():
        strengths[method], tuning[method] = _tune_strength(
            graph,
            training.demands,
            training_catalog,
            score,
            baseline_train.average_path_cost,
            mlu_slack,
            latency_slack,
        )

    policy_names = [*strengths]
    if include_tail_robust:
        policy_names.append("tail_robust")
    raw = {method: [] for method in policy_names}
    correlations = {method: [] for method in scores}
    nominal = {method: [] for method in policy_names}
    adaptive_reference = []

    for matrix_index in test_indices:
        demand_path = Path(dataset_root) / f"{topology_name}.{matrix_index:04d}.demands"
        instance = load_instance(topology_path, demand_path)
        catalog = build_path_catalog(graph, instance.demands, k_paths=k_paths)
        solutions = {}
        for method, strength in strengths.items():
            score = scores.get(method, {})
            solution = solve_nominal_te(
                graph,
                instance.demands,
                catalog=catalog,
                risk_scores=score,
                risk_strength=strength,
                mlu_slack=mlu_slack,
            )
            if not solution.success:
                raise RuntimeError(f"{topology_name} TM {matrix_index} {method}: {solution.message}")
            solutions[method] = solution
            nominal[method].append(
                {
                    "traffic_matrix": matrix_index,
                    "mlu": solution.mlu,
                    "average_path_cost": solution.average_path_cost,
                }
            )
        if include_tail_robust:
            robust = solve_tail_robust_te(
                graph,
                instance.demands,
                catalog=catalog,
                mlu_slack=mlu_slack,
                latency_limit=solutions["mlu"].average_path_cost * (1.0 + latency_slack),
            )
            if not robust.success:
                raise RuntimeError(
                    f"{topology_name} TM {matrix_index} tail_robust: {robust.message}"
                )
            solutions["tail_robust"] = robust
            nominal["tail_robust"].append(
                {
                    "traffic_matrix": matrix_index,
                    "mlu": robust.mlu,
                    "average_path_cost": robust.average_path_cost,
                }
            )

        adaptive_impacts = {}
        for edge in adaptive_edges:
            outcome = adaptive_failure_outcome(
                graph,
                instance.demands,
                {edge},
                k_paths=k_paths,
                catalog=catalog,
            )
            adaptive_impacts[edge] = 1.0 - outcome.delivered_fraction
            adaptive_reference.append(
                {
                    "traffic_matrix": matrix_index,
                    "edge": list(edge),
                    "delivered_fraction": outcome.delivered_fraction,
                    "max_utilization": outcome.max_utilization,
                }
            )

        for method, score in scores.items():
            correlations[method].append(
                {
                    "traffic_matrix": matrix_index,
                    **_spearman(score, adaptive_impacts, adaptive_edges),
                }
            )

        for method, solution in solutions.items():
            score = scores.get(method, {})
            for edge in physical_edges:
                outcome = frozen_failure_outcome(
                    graph, instance.demands, solution, {edge}, risk_scores=score
                )
                raw[method].append(
                    {
                        "traffic_matrix": matrix_index,
                        "edge": list(edge),
                        "delivered_fraction": outcome.delivered_fraction,
                        "max_utilization": outcome.max_utilization,
                        "average_path_cost": outcome.average_path_cost,
                    }
                )

    method_summary = {}
    for method, rows in raw.items():
        method_summary[method] = {
            "frozen_delivered_fraction": _summary([row["delivered_fraction"] for row in rows]),
            "frozen_service_loss": _summary([1.0 - row["delivered_fraction"] for row in rows]),
            "nominal_mlu": _summary([row["mlu"] for row in nominal[method]]),
            "nominal_path_cost": _summary(
                [row["average_path_cost"] for row in nominal[method]]
            ),
        }

    return {
        "topology": topology_name,
        "nodes": graph.number_of_nodes(),
        "directed_arcs": graph.number_of_edges(),
        "parallel_arcs_collapsed": graph.graph["parallel_arcs_collapsed"],
        "parallel_bundles": graph.graph["parallel_bundles"],
        "physical_links": len(physical_edges),
        "adaptive_failure_links": len(adaptive_edges),
        "adaptive_failures_exhaustive": len(adaptive_edges) == len(physical_edges),
        "training_traffic_matrix": 0,
        "test_traffic_matrices": list(test_indices),
        "k_paths": k_paths,
        "mlu_slack": mlu_slack,
        "latency_slack": latency_slack,
        "tail_robust_included": include_tail_robust,
        "curvature_seconds": {"forman": t_forman, "ollivier": t_ollivier},
        "selected_strengths": strengths,
        "tuning_trace": tuning,
        "method_summary": method_summary,
        "score_vs_adaptive_failure_impact": correlations,
        "nominal": nominal,
        "frozen_raw": raw,
        "adaptive_reference": adaptive_reference,
    }


def main():
    workspace = Path(__file__).resolve().parents[2]
    default_dataset = (
        workspace
        / "external"
        / "Repetita"
        / "data"
        / "2016TopologyZooUCL_inverseCapacity"
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, default=default_dataset)
    parser.add_argument("--topologies", nargs="+", default=DEFAULT_TOPOLOGIES)
    parser.add_argument(
        "--output", type=Path, default=Path("results") / "repetita_pilot.json"
    )
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--max-adaptive-links", type=int)
    parser.add_argument("--include-tail-robust", action="store_true")
    args = parser.parse_args()
    results = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for name in args.topologies:
        results.append(
            run_topology(
                args.dataset_root,
                name,
                max_adaptive_links=args.max_adaptive_links,
                include_tail_robust=args.include_tail_robust,
            )
        )
        payload = {
            "pilot_only": args.topologies == DEFAULT_TOPOLOGIES,
            "repetita_commit": REPETITA_COMMIT,
            "dataset": "2016TopologyZooUCL_inverseCapacity",
            "completed_topologies": len(results),
            "requested_topologies": args.topologies,
            "results": results,
        }
        temporary_output = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary_output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary_output.replace(args.output)
    if not args.quiet:
        for result in results:
            print(result["topology"], json.dumps(result["method_summary"], indent=2))
        print(f"saved {args.output}")


if __name__ == "__main__":
    main()
