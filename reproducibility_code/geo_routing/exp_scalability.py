"""Fixed feasibility/timing sequence for the submission-upgrade protocol."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter
import tracemalloc

from . import curvature as C
from .exp_repetita import REPETITA_COMMIT, _tune_strength
from .exp_submission_upgrade import split_double_failures
from .failure_aware import (
    build_path_catalog,
    curvature_risk,
    edge_key,
    solve_nominal_te,
    solve_scenario_risk_te,
    solve_tail_robust_te,
)
from .repetita import load_instance, physical_projection


PROTOCOL_ID = "scalability-v1-frozen-2026-07-14"
TOPOLOGIES = ["GtsHungary", "Geant2012", "Surfnet", "Garr201112", "Latnet"]


def _timed(call):
    started = perf_counter()
    result = call()
    return result, perf_counter() - started


def run_topology(dataset_root, topology_name):
    tracemalloc.start()
    total_started = perf_counter()
    topology_path = Path(dataset_root) / f"{topology_name}.graph"
    demand_path = Path(dataset_root) / f"{topology_name}.0000.demands"
    instance, parsing_seconds = _timed(lambda: load_instance(topology_path, demand_path))
    graph = instance.graph
    physical = physical_projection(graph)
    physical_edges = sorted({edge_key(u, v) for u, v in graph.edges()})

    curvature_pair, curvature_seconds = _timed(
        lambda: C.ollivier_all(physical, alpha=0.5)
    )
    curvature_values, curvature_internal_seconds = curvature_pair
    scores = curvature_risk(curvature_values)
    catalog, path_seconds = _timed(
        lambda: build_path_catalog(graph, instance.demands, k_paths=4)
    )
    min_mlu, min_mlu_seconds = _timed(
        lambda: solve_nominal_te(
            graph, instance.demands, catalog=catalog, mlu_slack=0.02
        )
    )
    if not min_mlu.success:
        raise RuntimeError(f"{topology_name} minimum-MLU failed: {min_mlu.message}")
    tuning_started = perf_counter()
    strength, tuning_trace = _tune_strength(
        graph, instance.demands, catalog, scores, min_mlu.average_path_cost, 0.02, 0.05
    )
    tuning_seconds = perf_counter() - tuning_started
    orc, orc_seconds = _timed(
        lambda: solve_nominal_te(
            graph, instance.demands, catalog=catalog, risk_scores=scores,
            risk_strength=strength, mlu_slack=0.02,
            latency_limit=min_mlu.average_path_cost * 1.05,
        )
    )
    latency_limit = min_mlu.average_path_cost * 1.05
    single, single_seconds = _timed(
        lambda: solve_tail_robust_te(
            graph, instance.demands, catalog=catalog, mlu_slack=0.02,
            latency_limit=latency_limit,
        )
    )
    design = split_double_failures(topology_name, physical_edges, cap=160)["design"]
    cvar, cvar_seconds = _timed(
        lambda: solve_scenario_risk_te(
            graph, instance.demands, scenarios=design, catalog=catalog,
            risk_measure="cvar", beta=0.90, mlu_slack=0.02,
            latency_limit=latency_limit,
        )
    )
    _, peak_python_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    def solution_row(solution):
        return {
            "success": solution.success,
            "message": solution.message,
            "mlu": solution.mlu,
            "average_path_cost": solution.average_path_cost,
            "objective_exposure": solution.policy_exposure,
            "path_variables": len(solution.path_records),
        }

    return {
        "success": True,
        "topology": topology_name,
        "nodes": graph.number_of_nodes(),
        "directed_arcs": graph.number_of_edges(),
        "physical_links": len(physical_edges),
        "commodities": len(instance.demands),
        "k_paths": 4,
        "double_failure_design_scenarios": len(design),
        "selected_orc_strength": strength,
        "tuning_trace": tuning_trace,
        "solutions": {
            "min_mlu": solution_row(min_mlu),
            "ollivier": solution_row(orc),
            "single_minimax": solution_row(single),
            "double_cvar90": solution_row(cvar),
        },
        "seconds": {
            "parsing": parsing_seconds,
            "curvature": curvature_seconds,
            "curvature_internal": curvature_internal_seconds,
            "path_generation": path_seconds,
            "min_mlu": min_mlu_seconds,
            "orc_tuning": tuning_seconds,
            "orc_final": orc_seconds,
            "single_minimax": single_seconds,
            "double_cvar90": cvar_seconds,
            "total": perf_counter() - total_started,
        },
        "python_tracemalloc_peak_bytes": peak_python_bytes,
        "memory_note": "Python allocator only; native solver allocations excluded.",
    }


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
        default=workspace / "reproducibility_code" / "results" / "scalability.json",
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
        try:
            result = run_topology(args.dataset_root, topology)
        except (ValueError, RuntimeError) as error:
            # The frozen sequence reports feasibility; it does not replace an
            # unsupported instance with an outcome-selected topology.
            result = {
                "success": False,
                "topology": topology,
                "error_type": type(error).__name__,
                "message": str(error),
            }
        results.append(result)
        payload = {
            "protocol_id": PROTOCOL_ID,
            "repetita_commit": REPETITA_COMMIT,
            "complete": len(results) == len(TOPOLOGIES),
            "results": results,
        }
        _write_atomic(args.output, payload)
        if not args.quiet:
            print(f"completed {topology}")


if __name__ == "__main__":
    main()
