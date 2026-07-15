"""Mechanical integrity checks for submission-upgrade JSON checkpoints."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from .exp_submission_upgrade import POLICIES, PROTOCOL_ID


def _scenario_key(value):
    return tuple(tuple(edge) for edge in value)


def validate(payload, require_complete=False):
    errors = []
    if payload.get("protocol_id") != PROTOCOL_ID:
        errors.append("protocol identifier mismatch")
    if require_complete and payload.get("completed_topologies") != len(
        payload.get("requested_topologies", [])
    ):
        errors.append("experiment is incomplete")
    seen_topologies = set()
    for result in payload.get("results", []):
        name = result["topology"]
        if name in seen_topologies:
            errors.append(f"{name}: duplicated topology")
        seen_topologies.add(name)
        design = {_scenario_key(value) for value in result["design_scenarios"]}
        evaluation = {_scenario_key(value) for value in result["evaluation_scenarios"]}
        if design.intersection(evaluation):
            errors.append(f"{name}: design/evaluation scenarios overlap")
        if not 0 < len(design) <= 160 or not 0 < len(evaluation) <= 160:
            errors.append(f"{name}: scenario cap or non-emptiness violated")
        if result["adaptive_scenarios"] > 40:
            errors.append(f"{name}: adaptive scenario cap violated")
        if set(result["method_summary"]) != set(POLICIES):
            errors.append(f"{name}: policy family mismatch")
        if set(result["score_vs_adaptive_double_failure_impact"]) != {
            "ollivier", "forman", "degree", "betweenness"
        }:
            errors.append(f"{name}: structural score family mismatch")

        baseline_by_tm = {
            row["traffic_matrix"]: row
            for row in result["nominal"]["min_mlu"]
        }
        expected_rows = len(evaluation) * len(result["test_traffic_matrices"])
        for policy in POLICIES:
            if len(result["held_out_raw"][policy]) != expected_rows:
                errors.append(f"{name} {policy}: held-out row count mismatch")
            for row in result["nominal"][policy]:
                values = [row["mlu"], row["average_path_cost"], row["design_objective"]]
                if not all(math.isfinite(value) for value in values):
                    errors.append(f"{name} {policy}: non-finite nominal value")
                limit = 1.05 * baseline_by_tm[row["traffic_matrix"]]["average_path_cost"]
                if row["average_path_cost"] > limit + 1e-7 * max(1.0, limit):
                    errors.append(f"{name} {policy}: latency budget exceeded")
            for row in result["held_out_raw"][policy]:
                if not -1e-9 <= row["service_loss"] <= 1.0 + 1e-9:
                    errors.append(f"{name} {policy}: invalid service loss")
    if errors:
        raise ValueError("\n".join(errors))
    return {
        "valid": True,
        "complete": payload.get("completed_topologies") == len(
            payload.get("requested_topologies", [])
        ),
        "topologies_checked": len(seen_topologies),
    }


def main():
    workspace = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input", type=Path, nargs="?",
        default=workspace / "reproducibility_code" / "results"
        / "submission_upgrade_double_failure.json",
    )
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    print(json.dumps(validate(payload, require_complete=args.require_complete), indent=2))


if __name__ == "__main__":
    main()
