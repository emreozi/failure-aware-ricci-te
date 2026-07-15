"""Integrity checks for the scenario-risk sensitivity checkpoint."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path

from .exp_scenario_sensitivity import CONDITIONS, PROTOCOL_ID
from .exp_submission_upgrade import PROTOCOL_ID as PRIMARY_PROTOCOL_ID


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _scenario_key(value):
    return tuple(tuple(edge) for edge in value)


def validate(sensitivity, primary, primary_path: Path, require_complete=False):
    errors = []
    if sensitivity.get("protocol_id") != PROTOCOL_ID:
        errors.append("sensitivity protocol identifier mismatch")
    if primary.get("protocol_id") != PRIMARY_PROTOCOL_ID:
        errors.append("primary protocol identifier mismatch")
    if sensitivity.get("conditions") != CONDITIONS:
        errors.append("condition family mismatch")
    if sensitivity.get("primary_output_sha256") != _file_sha256(primary_path):
        errors.append("primary output hash mismatch")
    if require_complete and sensitivity.get("completed_topologies") != len(
        sensitivity.get("requested_topologies", [])
    ):
        errors.append("sensitivity experiment is incomplete")

    primary_by_topology = {row["topology"]: row for row in primary["results"]}
    seen = set()
    for result in sensitivity.get("results", []):
        name = result["topology"]
        if name in seen:
            errors.append(f"{name}: duplicated topology")
        seen.add(name)
        if name not in primary_by_topology:
            errors.append(f"{name}: absent from primary output")
            continue
        primary_result = primary_by_topology[name]
        sensitivity_eval = {
            _scenario_key(value) for value in result["evaluation_scenarios"]
        }
        primary_eval = {
            _scenario_key(value) for value in primary_result["evaluation_scenarios"]
        }
        if sensitivity_eval != primary_eval:
            errors.append(f"{name}: held-out evaluation set changed")
        if set(result["conditions"]) != set(CONDITIONS):
            errors.append(f"{name}: condition summaries mismatch")
        expected_rows = len(sensitivity_eval) * len(result["test_traffic_matrices"])
        baseline_by_tm = {
            row["traffic_matrix"]: row
            for row in primary_result["nominal"]["min_mlu"]
        }
        for condition, settings in CONDITIONS.items():
            summary = result["conditions"][condition]
            if summary["beta"] != settings["beta"]:
                errors.append(f"{name} {condition}: beta mismatch")
            if summary["requested_design_cap"] != settings["design_cap"]:
                errors.append(f"{name} {condition}: design cap mismatch")
            if not 0 < summary["actual_design_scenarios"] <= settings["design_cap"]:
                errors.append(f"{name} {condition}: invalid scenario count")
            if len(result["held_out_raw"][condition]) != expected_rows:
                errors.append(f"{name} {condition}: held-out row count mismatch")
            for row in result["held_out_raw"][condition]:
                loss = row["service_loss"]
                if not math.isfinite(loss) or not -1e-9 <= loss <= 1.0 + 1e-9:
                    errors.append(f"{name} {condition}: invalid service loss")
            for row in result["nominal"][condition]:
                if not all(math.isfinite(row[key]) for key in (
                    "mlu", "average_path_cost", "design_objective"
                )):
                    errors.append(f"{name} {condition}: non-finite nominal value")
                baseline = baseline_by_tm[row["traffic_matrix"]]["average_path_cost"]
                limit = 1.05 * baseline
                if row["average_path_cost"] > limit + 1e-7 * max(1.0, limit):
                    errors.append(f"{name} {condition}: latency budget exceeded")
    if errors:
        raise ValueError("\n".join(errors))
    return {
        "valid": True,
        "complete": sensitivity.get("completed_topologies") == len(
            sensitivity.get("requested_topologies", [])
        ),
        "topologies_checked": len(seen),
        "conditions_checked": len(CONDITIONS),
    }


def main():
    workspace = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input", type=Path, nargs="?",
        default=workspace / "reproducibility_code" / "results"
        / "scenario_risk_sensitivity.json",
    )
    parser.add_argument(
        "--primary-input", type=Path,
        default=workspace / "reproducibility_code" / "results"
        / "submission_upgrade_double_failure.json",
    )
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    sensitivity = json.loads(args.input.read_text(encoding="utf-8"))
    primary = json.loads(args.primary_input.read_text(encoding="utf-8"))
    print(json.dumps(validate(
        sensitivity, primary, args.primary_input, args.require_complete
    ), indent=2))


if __name__ == "__main__":
    main()
