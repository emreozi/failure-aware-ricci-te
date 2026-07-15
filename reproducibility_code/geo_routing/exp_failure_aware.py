"""Pilot driver for the rebuilt failure-aware routing study.

The pilot is intentionally small enough for design validation. It must not be
quoted as a paper result. The full experiment will later add real backbone
topologies, held-out traffic matrices, more seeds, and corrected inference.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import networkx as nx
import numpy as np
from scipy.stats import spearmanr

from . import curvature as C
from . import topology as T
from .failure_aware import (
    adaptive_failure_outcome,
    betweenness_risk,
    build_path_catalog,
    curvature_risk,
    degree_risk,
    edge_key,
    frozen_failure_outcome,
    random_risk,
    random_single_edge_failures,
    solve_nominal_te,
    top_ranked_single_edge_failures,
)


def _scaled_demands(demands, factor):
    return [T.ODDemand(d.source, d.target, d.volume * factor) for d in demands]


def _summary(values):
    array = np.asarray(values, dtype=float)
    return {
        "mean": float(array.mean()),
        "std": float(array.std(ddof=1)) if len(array) > 1 else 0.0,
        "min": float(array.min()),
        "max": float(array.max()),
        "n": int(len(array)),
    }


def _outcome_summary(outcomes):
    return {
        "delivered_fraction": _summary([o.delivered_fraction for o in outcomes]),
        "max_utilization": _summary([o.max_utilization for o in outcomes]),
        "average_path_cost": _summary([o.average_path_cost for o in outcomes]),
    }


def _spearman(scores, impacts, edges):
    x = np.asarray([scores.get(edge, 0.0) for edge in edges], dtype=float)
    y = np.asarray([impacts.get(edge, 0.0) for edge in edges], dtype=float)
    if np.allclose(x, x[0]) or np.allclose(y, y[0]):
        return {"rho": None, "p_value": None}
    result = spearmanr(x, y)
    return {"rho": float(result.statistic), "p_value": float(result.pvalue)}


def run_seed(seed=1, target_mlu=0.85, k_paths=8, mlu_slack=0.05):
    graph = T.aws_twin(
        n_regions=4,
        region_size=15,
        n_core=6,
        seed=seed,
        p_intra=0.28,
        leaves_per_region=10,
        homing=2,
    )
    base_demands = T.make_od_demands(
        graph, n_pairs=24, level=1.0, seed=1000 + seed, cross_region=True
    )
    catalog = build_path_catalog(graph, base_demands, k_paths=k_paths)
    unscaled = solve_nominal_te(graph, base_demands, catalog=catalog, mlu_slack=0.0)
    if not unscaled.success:
        raise RuntimeError(unscaled.message)
    demands = _scaled_demands(base_demands, target_mlu / max(unscaled.mlu, 1e-12))

    forman, t_forman = C.forman_all(graph)
    ollivier, t_ollivier = C.ollivier_all(graph, alpha=0.5)
    scores = {
        "degree": degree_risk(graph),
        "betweenness": betweenness_risk(graph),
        "forman": curvature_risk(forman),
        "ollivier": curvature_risk(ollivier),
        "random_placebo": random_risk(graph, seed=9000 + seed),
    }
    policies = {"mlu": ({}, 0.0)}
    policies.update({name: (score, 1.0) for name, score in scores.items()})

    nominal = {}
    solutions = {}
    for name, (score, strength) in policies.items():
        solution = solve_nominal_te(
            graph,
            demands,
            catalog=catalog,
            risk_scores=score,
            risk_strength=strength,
            mlu_slack=mlu_slack,
        )
        if not solution.success:
            raise RuntimeError(f"{name}: {solution.message}")
        solutions[name] = solution
        nominal[name] = {
            "mlu": solution.mlu,
            "average_path_cost": solution.average_path_cost,
            "policy_exposure": solution.policy_exposure,
        }

    edges = [edge_key(u, v) for u, v in graph.edges()]
    neutral = solutions["mlu"]
    adaptive_impact = {}
    frozen_neutral_impact = {}
    for edge in edges:
        scenario = {edge}
        adaptive = adaptive_failure_outcome(graph, demands, scenario, k_paths=k_paths)
        frozen = frozen_failure_outcome(graph, demands, neutral, scenario)
        adaptive_impact[edge] = 1.0 - adaptive.delivered_fraction
        frozen_neutral_impact[edge] = 1.0 - frozen.delivered_fraction

    correlations = {
        name: {
            "adaptive_capacity_feasible_loss": _spearman(score, adaptive_impact, edges),
            "frozen_neutral_route_loss": _spearman(score, frozen_neutral_impact, edges),
        }
        for name, score in scores.items()
    }

    scenario_sets = {
        "random_single_edge": random_single_edge_failures(
            graph, min(24, graph.number_of_edges()), seed=7000 + seed
        ),
        "betweenness_targeted": top_ranked_single_edge_failures(
            graph, scores["betweenness"], min(12, graph.number_of_edges())
        ),
        # Evaluation-only oracle stress set; impact labels never train or tune a policy.
        "impact_oracle_stress": top_ranked_single_edge_failures(
            graph, adaptive_impact, min(12, graph.number_of_edges())
        ),
    }

    evaluations = {}
    for scenario_name, scenarios in scenario_sets.items():
        evaluations[scenario_name] = {}
        for policy_name, (score, strength) in policies.items():
            frozen_outcomes = [
                frozen_failure_outcome(
                    graph, demands, solutions[policy_name], failed, risk_scores=score
                )
                for failed in scenarios
            ]
            adaptive_outcomes = [
                adaptive_failure_outcome(
                    graph,
                    demands,
                    failed,
                    risk_scores=score,
                    risk_strength=strength,
                    k_paths=k_paths,
                )
                for failed in scenarios
            ]
            evaluations[scenario_name][policy_name] = {
                "frozen": _outcome_summary(frozen_outcomes),
                "adaptive": _outcome_summary(adaptive_outcomes),
            }

    bridges = [edge_key(u, v) for u, v in nx.bridges(graph)]
    return {
        "seed": seed,
        "pilot_only": True,
        "topology": {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "bridges": len(bridges),
        },
        "traffic": {
            "commodities": len(demands),
            "target_mlu": target_mlu,
            "total_demand": sum(d.volume for d in demands),
            "k_paths": k_paths,
            "mlu_slack": mlu_slack,
        },
        "curvature_seconds": {"forman": t_forman, "ollivier": t_ollivier},
        "nominal": nominal,
        "score_vs_independent_failure_impact": correlations,
        "failure_evaluations": evaluations,
        "impact_distribution": {
            "adaptive": _summary(list(adaptive_impact.values())),
            "frozen_neutral": _summary(list(frozen_neutral_impact.values())),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--output", type=Path, default=Path("results") / "failure_aware_pilot.json"
    )
    args = parser.parse_args()
    result = run_seed(seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["score_vs_independent_failure_impact"], indent=2))
    print(f"saved {args.output}")


if __name__ == "__main__":
    main()
