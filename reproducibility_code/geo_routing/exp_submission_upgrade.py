"""Frozen submission-upgrade experiment for held-out double-link failures.

The protocol is documented in ``SUBMISSION_UPGRADE_PROTOCOL.md``.  Failure
scenario membership depends only on SHA-256 hashes of topology and edge labels;
no routing outcome is inspected when constructing the design/evaluation split.
Results are written atomically after every topology and may be resumed.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
from time import perf_counter
import tracemalloc
import zlib

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
    solve_nominal_te,
    solve_scenario_risk_te,
    solve_tail_robust_te,
)
from .exp_repetita import REPETITA_COMMIT, _tune_strength
from .repetita import load_instance, physical_projection


PROTOCOL_ID = "submission-upgrade-v1-frozen-2026-07-14"
DEFAULT_TOPOLOGIES = [
    "Sago", "Pacificwave", "Ibm", "Highwinds", "Internetmci", "Restena",
    "Marnet", "BtAsiaPac", "Harnet", "Bandcon", "HiberniaUs", "Azrena",
]
POLICIES = [
    "min_mlu", "ollivier", "single_minimax", "double_expected",
    "double_cvar90", "double_minimax",
]


def _scenario_digest(topology: str, scenario) -> str:
    label = ";".join(f"{u}-{v}" for u, v in sorted(scenario))
    return sha256(f"{topology}|{label}".encode("utf-8")).hexdigest()


def split_double_failures(topology: str, physical_edges, cap: int = 160):
    """Return deterministic, disjoint design and held-out evaluation sets."""

    buckets = {"design": [], "evaluation": []}
    for pair in combinations(sorted(physical_edges), 2):
        scenario = frozenset(pair)
        digest = _scenario_digest(topology, scenario)
        bucket = "design" if int(digest[-1], 16) % 2 == 0 else "evaluation"
        buckets[bucket].append((digest, scenario))
    result = {}
    for name, rows in buckets.items():
        rows.sort(key=lambda item: item[0])
        result[name] = [scenario for _, scenario in rows[:cap]]
    if not result["design"] or not result["evaluation"]:
        raise ValueError(f"{topology} has no non-empty double-failure split")
    return result


def _summary(values):
    x = np.asarray(values, dtype=float)
    return {
        "mean": float(x.mean()),
        "std": float(x.std(ddof=1)) if x.size > 1 else 0.0,
        "min": float(x.min()),
        "max": float(x.max()),
        "n": int(x.size),
    }


def _cvar(values, beta=0.90):
    x = np.asarray(values, dtype=float)
    candidates = np.unique(np.concatenate(([0.0], x)))
    return float(min(
        eta + np.maximum(x - eta, 0.0).mean() / (1.0 - beta)
        for eta in candidates
    ))


def _scenario_json(scenario):
    return [list(edge) for edge in sorted(scenario)]


def _scenario_structural_score(scores, scenario):
    values = []
    for u, v in scenario:
        values.append(max(float(scores.get((u, v), 0.0)),
                          float(scores.get((v, u), 0.0))))
    return float(sum(values))


def run_topology(
    dataset_root,
    topology_name,
    test_indices=(1, 2, 3, 4),
    k_paths=8,
    mlu_slack=0.02,
    latency_slack=0.05,
    scenario_cap=160,
    adaptive_scenario_cap=40,
):
    topology_started = perf_counter()
    tracemalloc.start()
    topology_path = Path(dataset_root) / f"{topology_name}.graph"
    training = load_instance(
        topology_path, Path(dataset_root) / f"{topology_name}.0000.demands"
    )
    graph = training.graph
    physical = physical_projection(graph)
    physical_edges = sorted({edge_key(u, v) for u, v in graph.edges()})
    scenario_split = split_double_failures(topology_name, physical_edges, cap=scenario_cap)
    design_scenarios = scenario_split["design"]
    evaluation_scenarios = scenario_split["evaluation"]
    if adaptive_scenario_cap is None:
        adaptive_scenarios = evaluation_scenarios
    else:
        adaptive_scenarios = evaluation_scenarios[:adaptive_scenario_cap]

    forman, forman_seconds = C.forman_all(physical)
    curvature_started = perf_counter()
    ollivier, reported_curvature_seconds = C.ollivier_all(physical, alpha=0.5)
    ollivier_seconds = perf_counter() - curvature_started
    orc_scores = curvature_risk(ollivier)
    score_sets = {
        "ollivier": orc_scores,
        "forman": curvature_risk(forman),
        "degree": degree_risk(physical),
        "betweenness": betweenness_risk(physical),
    }

    training_catalog = build_path_catalog(graph, training.demands, k_paths=k_paths)
    baseline_train = solve_nominal_te(
        graph, training.demands, catalog=training_catalog, mlu_slack=mlu_slack
    )
    if not baseline_train.success:
        raise RuntimeError(f"training baseline failed for {topology_name}: {baseline_train.message}")
    orc_strength, tuning_trace = _tune_strength(
        graph, training.demands, training_catalog, orc_scores,
        baseline_train.average_path_cost, mlu_slack, latency_slack,
    )

    raw = {policy: [] for policy in POLICIES}
    nominal = {policy: [] for policy in POLICIES}
    solve_seconds = defaultdict(float)
    adaptive_rows = []
    correlations = {method: [] for method in score_sets}

    for matrix_index in test_indices:
        instance = load_instance(
            topology_path,
            Path(dataset_root) / f"{topology_name}.{matrix_index:04d}.demands",
        )
        catalog_started = perf_counter()
        catalog = build_path_catalog(graph, instance.demands, k_paths=k_paths)
        catalog_seconds = perf_counter() - catalog_started

        solutions = {}
        started = perf_counter()
        solutions["min_mlu"] = solve_nominal_te(
            graph, instance.demands, catalog=catalog, mlu_slack=mlu_slack
        )
        solve_seconds["min_mlu"] += perf_counter() - started
        if not solutions["min_mlu"].success:
            raise RuntimeError(
                f"{topology_name} TM {matrix_index} min_mlu: "
                f"{solutions['min_mlu'].message}"
            )
        latency_limit = solutions["min_mlu"].average_path_cost * (1.0 + latency_slack)

        started = perf_counter()
        solutions["ollivier"] = solve_nominal_te(
            graph, instance.demands, catalog=catalog, risk_scores=orc_scores,
            risk_strength=orc_strength, mlu_slack=mlu_slack,
            latency_limit=latency_limit,
        )
        solve_seconds["ollivier"] += perf_counter() - started

        started = perf_counter()
        solutions["single_minimax"] = solve_tail_robust_te(
            graph, instance.demands, catalog=catalog, mlu_slack=mlu_slack,
            latency_limit=latency_limit,
        )
        solve_seconds["single_minimax"] += perf_counter() - started

        for policy, measure in (
            ("double_expected", "expected"),
            ("double_cvar90", "cvar"),
            ("double_minimax", "max"),
        ):
            started = perf_counter()
            solutions[policy] = solve_scenario_risk_te(
                graph, instance.demands, scenarios=design_scenarios,
                catalog=catalog, risk_measure=measure, beta=0.90,
                mlu_slack=mlu_slack, latency_limit=latency_limit,
            )
            solve_seconds[policy] += perf_counter() - started

        for policy, solution in solutions.items():
            if not solution.success:
                raise RuntimeError(
                    f"{topology_name} TM {matrix_index} {policy}: {solution.message}"
                )
            nominal[policy].append({
                "traffic_matrix": matrix_index,
                "mlu": solution.mlu,
                "average_path_cost": solution.average_path_cost,
                "design_objective": solution.policy_exposure,
                "catalog_seconds": catalog_seconds if policy == "min_mlu" else 0.0,
            })

        adaptive_by_scenario = {}
        adaptive_started = perf_counter()
        for scenario in adaptive_scenarios:
            outcome = adaptive_failure_outcome(
                graph, instance.demands, scenario, k_paths=k_paths, catalog=catalog
            )
            key = _scenario_digest(topology_name, scenario)
            loss = 1.0 - outcome.delivered_fraction
            adaptive_by_scenario[key] = loss
            adaptive_rows.append({
                "traffic_matrix": matrix_index,
                "scenario": _scenario_json(scenario),
                "service_loss": loss,
                "max_utilization": outcome.max_utilization,
            })
        solve_seconds["adaptive_ceiling"] += perf_counter() - adaptive_started

        if adaptive_by_scenario:
            impacts = [
                adaptive_by_scenario[_scenario_digest(topology_name, scenario)]
                for scenario in adaptive_scenarios
            ]
            for method, method_scores in score_sets.items():
                structural = [
                    _scenario_structural_score(method_scores, scenario)
                    for scenario in adaptive_scenarios
                ]
                if np.allclose(structural, structural[0]) or np.allclose(impacts, impacts[0]):
                    rho, p_value = None, None
                else:
                    corr = spearmanr(structural, impacts)
                    rho, p_value = float(corr.statistic), float(corr.pvalue)
                correlations[method].append({
                    "traffic_matrix": matrix_index, "rho": rho, "p_value": p_value,
                    "n": len(impacts),
                })

        evaluation_started = perf_counter()
        for policy, solution in solutions.items():
            for scenario in evaluation_scenarios:
                outcome = frozen_failure_outcome(
                    graph, instance.demands, solution, scenario,
                    risk_scores=orc_scores if policy == "ollivier" else None,
                )
                raw[policy].append({
                    "traffic_matrix": matrix_index,
                    "scenario": _scenario_json(scenario),
                    "service_loss": 1.0 - outcome.delivered_fraction,
                    "max_utilization": outcome.max_utilization,
                })
        solve_seconds["held_out_evaluation"] += perf_counter() - evaluation_started

    summaries = {}
    for policy, rows in raw.items():
        losses = [row["service_loss"] for row in rows]
        summaries[policy] = {
            "held_out_double_failure_mean_loss": float(np.mean(losses)),
            "held_out_double_failure_cvar90": _cvar(losses, beta=0.90),
            "held_out_double_failure_max_loss": float(np.max(losses)),
            "held_out_double_failure_distribution": _summary(losses),
            "nominal_mlu": _summary([row["mlu"] for row in nominal[policy]]),
            "nominal_path_cost": _summary(
                [row["average_path_cost"] for row in nominal[policy]]
            ),
        }

    _, peak_python_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "topology": topology_name,
        "nodes": graph.number_of_nodes(),
        "directed_arcs": graph.number_of_edges(),
        "physical_links": len(physical_edges),
        "double_failure_pairs": len(physical_edges) * (len(physical_edges) - 1) // 2,
        "design_scenarios": [_scenario_json(s) for s in design_scenarios],
        "evaluation_scenarios": [_scenario_json(s) for s in evaluation_scenarios],
        "adaptive_scenarios": len(adaptive_scenarios),
        "adaptive_exhaustive_over_held_out": len(adaptive_scenarios) == len(evaluation_scenarios),
        "training_traffic_matrix": 0,
        "test_traffic_matrices": list(test_indices),
        "k_paths": k_paths,
        "mlu_slack": mlu_slack,
        "latency_slack": latency_slack,
        "cvar_beta": 0.90,
        "ollivier_alpha": 0.5,
        "ollivier_strength": orc_strength,
        "ollivier_tuning_trace": tuning_trace,
        "curvature_seconds": {
            "forman": forman_seconds,
            "ollivier": ollivier_seconds,
            "ollivier_internal": reported_curvature_seconds,
        },
        "solve_seconds": dict(solve_seconds),
        "topology_wall_seconds": perf_counter() - topology_started,
        "python_tracemalloc_peak_bytes": peak_python_bytes,
        "memory_note": "Python allocator peak only; native HiGHS allocations are not included.",
        "method_summary": summaries,
        "score_vs_adaptive_double_failure_impact": correlations,
        "nominal": nominal,
        "held_out_raw": raw,
        "adaptive_reference": adaptive_rows,
    }


def _write_atomic(output, payload):
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(output)


def main():
    workspace = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset-root", type=Path,
        default=workspace / "external" / "Repetita" / "data"
        / "2016TopologyZooUCL_inverseCapacity",
    )
    parser.add_argument("--topologies", nargs="+", default=DEFAULT_TOPOLOGIES)
    parser.add_argument(
        "--output", type=Path,
        default=workspace / "reproducibility_code" / "results"
        / "submission_upgrade_double_failure.json",
    )
    parser.add_argument("--scenario-cap", type=int, default=160)
    parser.add_argument("--adaptive-scenario-cap", type=int, default=40)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    results = []
    if args.resume and args.output.exists():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        if existing.get("protocol_id") != PROTOCOL_ID:
            raise ValueError("refusing to resume an output from another protocol")
        results = existing.get("results", [])
    completed = {row["topology"] for row in results}
    for name in args.topologies:
        if name in completed:
            continue
        result = run_topology(
            args.dataset_root, name, scenario_cap=args.scenario_cap,
            adaptive_scenario_cap=args.adaptive_scenario_cap,
        )
        results.append(result)
        payload = {
            "protocol_id": PROTOCOL_ID,
            "protocol_file": "SUBMISSION_UPGRADE_PROTOCOL.md",
            "repetita_commit": REPETITA_COMMIT,
            "dataset": "2016TopologyZooUCL_inverseCapacity",
            "requested_topologies": args.topologies,
            "completed_topologies": len(results),
            "results": results,
        }
        _write_atomic(args.output, payload)
        if not args.quiet:
            print(name, json.dumps(result["method_summary"], indent=2))
            print(f"checkpoint: {args.output}")


if __name__ == "__main__":
    main()
