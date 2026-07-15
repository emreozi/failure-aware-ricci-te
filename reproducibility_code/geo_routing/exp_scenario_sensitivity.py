"""One-factor sensitivity for the held-out double-failure CVaR policy.

The protocol is recorded in ``SCENARIO_RISK_SENSITIVITY_PROTOCOL.md``.  The
original submission-upgrade output is not modified.  Only the four additional
conditions are solved here; the frozen beta=.90, S=160 result remains the
reference condition.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from .exp_submission_upgrade import (
    DEFAULT_TOPOLOGIES,
    _cvar,
    _scenario_json,
    _summary,
    _write_atomic,
    split_double_failures,
)
from .failure_aware import (
    build_path_catalog,
    edge_key,
    frozen_failure_outcome,
    solve_nominal_te,
    solve_scenario_risk_te,
)
from .exp_repetita import REPETITA_COMMIT
from .repetita import load_instance


PROTOCOL_ID = "scenario-risk-sensitivity-v1-2026-07-14"
CONDITIONS = {
    "beta80_s160": {"beta": 0.80, "design_cap": 160},
    "beta95_s160": {"beta": 0.95, "design_cap": 160},
    "beta90_s40": {"beta": 0.90, "design_cap": 40},
    "beta90_s80": {"beta": 0.90, "design_cap": 80},
}


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_topology(
    dataset_root: Path,
    topology_name: str,
    test_indices=(1, 2, 3, 4),
    k_paths: int = 8,
    mlu_slack: float = 0.02,
    latency_slack: float = 0.05,
):
    started_topology = perf_counter()
    topology_path = dataset_root / f"{topology_name}.graph"
    training = load_instance(
        topology_path, dataset_root / f"{topology_name}.0000.demands"
    )
    graph = training.graph
    physical_edges = sorted({edge_key(u, v) for u, v in graph.edges()})
    split = split_double_failures(topology_name, physical_edges, cap=160)
    design_all = split["design"]
    evaluation = split["evaluation"]

    raw = {condition: [] for condition in CONDITIONS}
    nominal = {condition: [] for condition in CONDITIONS}
    solve_seconds = {condition: 0.0 for condition in CONDITIONS}
    evaluation_seconds = {condition: 0.0 for condition in CONDITIONS}

    for matrix_index in test_indices:
        instance = load_instance(
            topology_path,
            dataset_root / f"{topology_name}.{matrix_index:04d}.demands",
        )
        catalog = build_path_catalog(graph, instance.demands, k_paths=k_paths)
        baseline = solve_nominal_te(
            graph, instance.demands, catalog=catalog, mlu_slack=mlu_slack
        )
        if not baseline.success:
            raise RuntimeError(
                f"{topology_name} TM {matrix_index} baseline: {baseline.message}"
            )
        latency_limit = baseline.average_path_cost * (1.0 + latency_slack)

        for condition, settings in CONDITIONS.items():
            scenarios = design_all[: settings["design_cap"]]
            solve_started = perf_counter()
            solution = solve_scenario_risk_te(
                graph,
                instance.demands,
                scenarios=scenarios,
                catalog=catalog,
                risk_measure="cvar",
                beta=settings["beta"],
                mlu_slack=mlu_slack,
                latency_limit=latency_limit,
            )
            solve_seconds[condition] += perf_counter() - solve_started
            if not solution.success:
                raise RuntimeError(
                    f"{topology_name} TM {matrix_index} {condition}: "
                    f"{solution.message}"
                )
            nominal[condition].append({
                "traffic_matrix": matrix_index,
                "mlu": solution.mlu,
                "average_path_cost": solution.average_path_cost,
                "design_objective": solution.policy_exposure,
            })

            evaluation_started = perf_counter()
            for scenario in evaluation:
                outcome = frozen_failure_outcome(
                    graph, instance.demands, solution, scenario
                )
                raw[condition].append({
                    "traffic_matrix": matrix_index,
                    "scenario": _scenario_json(scenario),
                    "service_loss": 1.0 - outcome.delivered_fraction,
                    "max_utilization": outcome.max_utilization,
                })
            evaluation_seconds[condition] += perf_counter() - evaluation_started

    summaries = {}
    for condition, settings in CONDITIONS.items():
        losses = [row["service_loss"] for row in raw[condition]]
        summaries[condition] = {
            "beta": settings["beta"],
            "requested_design_cap": settings["design_cap"],
            "actual_design_scenarios": min(settings["design_cap"], len(design_all)),
            "held_out_evaluation_scenarios": len(evaluation),
            "held_out_mean_loss": float(np.mean(losses)),
            "held_out_cvar_declared": _cvar(losses, beta=settings["beta"]),
            "held_out_cvar90": _cvar(losses, beta=0.90),
            "held_out_max_loss": float(np.max(losses)),
            "held_out_distribution": _summary(losses),
            "nominal_mlu": _summary([row["mlu"] for row in nominal[condition]]),
            "nominal_path_cost": _summary(
                [row["average_path_cost"] for row in nominal[condition]]
            ),
            "solve_seconds": solve_seconds[condition],
            "evaluation_seconds": evaluation_seconds[condition],
        }

    return {
        "topology": topology_name,
        "nodes": graph.number_of_nodes(),
        "directed_arcs": graph.number_of_edges(),
        "physical_links": len(physical_edges),
        "design_scenarios_available": len(design_all),
        "evaluation_scenarios": [_scenario_json(s) for s in evaluation],
        "test_traffic_matrices": list(test_indices),
        "k_paths": k_paths,
        "mlu_slack": mlu_slack,
        "latency_slack": latency_slack,
        "conditions": summaries,
        "nominal": nominal,
        "held_out_raw": raw,
        "topology_wall_seconds": perf_counter() - started_topology,
    }


def main():
    workspace = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=workspace / "external" / "Repetita" / "data"
        / "2016TopologyZooUCL_inverseCapacity",
    )
    parser.add_argument("--topologies", nargs="+", default=DEFAULT_TOPOLOGIES)
    parser.add_argument(
        "--output",
        type=Path,
        default=workspace / "reproducibility_code" / "results"
        / "scenario_risk_sensitivity.json",
    )
    parser.add_argument(
        "--primary-output",
        type=Path,
        default=workspace / "reproducibility_code" / "results"
        / "submission_upgrade_double_failure.json",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if not args.primary_output.exists():
        raise FileNotFoundError("the frozen primary output is required")

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
        result = run_topology(args.dataset_root, name)
        results.append(result)
        payload = {
            "protocol_id": PROTOCOL_ID,
            "protocol_file": "SCENARIO_RISK_SENSITIVITY_PROTOCOL.md",
            "repetita_commit": REPETITA_COMMIT,
            "dataset": "2016TopologyZooUCL_inverseCapacity",
            "primary_output": str(args.primary_output.relative_to(workspace)),
            "primary_output_sha256": _file_sha256(args.primary_output),
            "requested_topologies": args.topologies,
            "completed_topologies": len(results),
            "conditions": CONDITIONS,
            "results": results,
        }
        _write_atomic(args.output, payload)
        if not args.quiet:
            print(name, json.dumps(result["conditions"], indent=2))
            print(f"checkpoint: {args.output}")


if __name__ == "__main__":
    main()
