"""Frozen one-factor sensitivity analysis on the confirmatory topology set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from . import curvature as C
from .analyze_repetita import _bootstrap_ci, _sign_flip_p_value
from .exp_repetita import REPETITA_COMMIT, _tune_strength
from .failure_aware import (
    build_path_catalog,
    curvature_risk,
    edge_key,
    frozen_failure_outcome,
    solve_nominal_te,
)
from .repetita import load_instance, physical_projection


PROTOCOL_ID = "confirmatory-one-factor-sensitivity-v1-2026-07-14"
TOPOLOGIES = [
    "Aconet", "Easynet", "Noel", "Belnet2010", "Garr200109", "Fccn",
    "Packetexchange", "GtsRomania", "Fatman", "Nextgen",
]
CONDITIONS = {
    "k4": {"k_paths": 4, "mlu_slack": 0.02, "alpha": 0.50},
    "k16": {"k_paths": 16, "mlu_slack": 0.02, "alpha": 0.50},
    "mlu0": {"k_paths": 8, "mlu_slack": 0.00, "alpha": 0.50},
    "mlu5": {"k_paths": 8, "mlu_slack": 0.05, "alpha": 0.50},
    "alpha25": {"k_paths": 8, "mlu_slack": 0.02, "alpha": 0.25},
    "alpha75": {"k_paths": 8, "mlu_slack": 0.02, "alpha": 0.75},
}


def run_topology(dataset_root, topology_name):
    topology_path = Path(dataset_root) / f"{topology_name}.graph"
    training = load_instance(
        topology_path, Path(dataset_root) / f"{topology_name}.0000.demands"
    )
    graph = training.graph
    physical = physical_projection(graph)
    physical_edges = sorted({edge_key(u, v) for u, v in graph.edges()})
    curvature_cache = {}
    result = {"topology": topology_name, "nodes": graph.number_of_nodes(), "conditions": {}}

    for condition, settings in CONDITIONS.items():
        started = perf_counter()
        alpha = settings["alpha"]
        if alpha not in curvature_cache:
            values, seconds = C.ollivier_all(physical, alpha=alpha)
            curvature_cache[alpha] = (curvature_risk(values), seconds)
        scores, curvature_seconds = curvature_cache[alpha]
        training_catalog = build_path_catalog(
            graph, training.demands, k_paths=settings["k_paths"]
        )
        baseline_train = solve_nominal_te(
            graph, training.demands, catalog=training_catalog,
            mlu_slack=settings["mlu_slack"],
        )
        if not baseline_train.success:
            raise RuntimeError(f"{topology_name} {condition} training baseline failed")
        strength, tuning_trace = _tune_strength(
            graph, training.demands, training_catalog, scores,
            baseline_train.average_path_cost, settings["mlu_slack"], 0.05,
        )

        losses = {"min_mlu": [], "ollivier": []}
        costs = {"min_mlu": [], "ollivier": []}
        mlus = {"min_mlu": [], "ollivier": []}
        for matrix_index in (1, 2, 3, 4):
            instance = load_instance(
                topology_path,
                Path(dataset_root) / f"{topology_name}.{matrix_index:04d}.demands",
            )
            catalog = build_path_catalog(
                graph, instance.demands, k_paths=settings["k_paths"]
            )
            baseline = solve_nominal_te(
                graph, instance.demands, catalog=catalog,
                mlu_slack=settings["mlu_slack"],
            )
            if not baseline.success:
                raise RuntimeError(
                    f"{topology_name} {condition} TM{matrix_index} min_mlu: {baseline.message}"
                )
            solutions = {
                "min_mlu": baseline,
                "ollivier": solve_nominal_te(
                    graph, instance.demands, catalog=catalog, risk_scores=scores,
                    risk_strength=strength, mlu_slack=settings["mlu_slack"],
                    latency_limit=baseline.average_path_cost * 1.05,
                ),
            }
            for policy, solution in solutions.items():
                if not solution.success:
                    raise RuntimeError(
                        f"{topology_name} {condition} TM{matrix_index} {policy}: {solution.message}"
                    )
                costs[policy].append(solution.average_path_cost)
                mlus[policy].append(solution.mlu)
                for edge in physical_edges:
                    outcome = frozen_failure_outcome(
                        graph, instance.demands, solution, {edge},
                        risk_scores=scores if policy == "ollivier" else None,
                    )
                    losses[policy].append(1.0 - outcome.delivered_fraction)

        result["conditions"][condition] = {
            **settings,
            "selected_strength": strength,
            "tuning_trace": tuning_trace,
            "curvature_seconds": curvature_seconds,
            "mean_loss": {policy: float(np.mean(values)) for policy, values in losses.items()},
            "worst_loss": {policy: float(np.max(values)) for policy, values in losses.items()},
            "mean_path_cost": {policy: float(np.mean(values)) for policy, values in costs.items()},
            "mean_mlu": {policy: float(np.mean(values)) for policy, values in mlus.items()},
            "mean_loss_delta": float(np.mean(losses["ollivier"]) - np.mean(losses["min_mlu"])),
            "path_cost_relative_delta": float(
                np.mean(costs["ollivier"]) / np.mean(costs["min_mlu"]) - 1.0
            ),
            "wall_seconds": perf_counter() - started,
        }
    return result


def analyse(results):
    rng = np.random.default_rng(20260714)
    summary = {}
    for condition in CONDITIONS:
        effects = [row["conditions"][condition]["mean_loss_delta"] for row in results]
        costs = [row["conditions"][condition]["path_cost_relative_delta"] for row in results]
        summary[condition] = {
            **CONDITIONS[condition],
            "mean_loss_delta": float(np.mean(effects)),
            "median_loss_delta": float(np.median(effects)),
            "topology_cluster_bootstrap_95_ci": _bootstrap_ci(effects, rng),
            "descriptive_sign_flip_p_value": _sign_flip_p_value(effects),
            "orc_better": int(sum(value < -1e-12 for value in effects)),
            "orc_worse": int(sum(value > 1e-12 for value in effects)),
            "tied": int(sum(abs(value) <= 1e-12 for value in effects)),
            "mean_path_cost_relative_delta": float(np.mean(costs)),
        }
    return summary


def _markdown(payload):
    lines = [
        "# Frozen one-factor sensitivity analysis",
        "",
        "Positive loss deltas mean ORC is worse than minimum-MLU. These are robustness checks, not replacements for the confirmatory test.",
        "",
        "| Condition | Mean loss delta (pp) | 95% topology bootstrap CI (pp) | ORC better / worse / tied | Path-cost delta |",
        "|---|---:|---:|---:|---:|",
    ]
    for condition, row in payload["summary"].items():
        ci = row["topology_cluster_bootstrap_95_ci"]
        lines.append(
            f"| {condition} | {100 * row['mean_loss_delta']:+.3f} | "
            f"[{100 * ci[0]:+.3f}, {100 * ci[1]:+.3f}] | "
            f"{row['orc_better']} / {row['orc_worse']} / {row['tied']} | "
            f"{100 * row['mean_path_cost_relative_delta']:+.2f}% |"
        )
    return "\n".join(lines) + "\n"


def _write_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(path)


def main():
    workspace = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset-root", type=Path,
        default=workspace / "external" / "Repetita" / "data"
        / "2016TopologyZooUCL_inverseCapacity",
    )
    parser.add_argument(
        "--output", type=Path,
        default=workspace / "reproducibility_code" / "results" / "sensitivity.json",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    results = []
    if args.resume and args.output.exists():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        if existing.get("protocol_id") != PROTOCOL_ID:
            raise ValueError("refusing to resume another protocol")
        results = existing.get("results", [])
    completed = {row["topology"] for row in results}
    for topology in TOPOLOGIES:
        if topology in completed:
            continue
        results.append(run_topology(args.dataset_root, topology))
        payload = {
            "protocol_id": PROTOCOL_ID,
            "repetita_commit": REPETITA_COMMIT,
            "results": results,
            "complete": len(results) == len(TOPOLOGIES),
        }
        if payload["complete"]:
            payload["summary"] = analyse(results)
        _write_atomic(args.output, payload)
        if not args.quiet:
            print(f"completed {topology}")
    payload = json.loads(args.output.read_text(encoding="utf-8"))
    if not payload.get("complete"):
        raise RuntimeError("sensitivity output is incomplete")
    markdown = workspace / "SENSITIVITY_RESULTS.md"
    markdown.write_text(_markdown(payload), encoding="utf-8")
    if not args.quiet:
        print(markdown.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
