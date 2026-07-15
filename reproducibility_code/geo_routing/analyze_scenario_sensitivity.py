"""Analyze scenario-risk sensitivity and the adaptive recovery ceiling."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .analyze_repetita import _bootstrap_ci, _sign_flip_p_value
from .exp_scenario_sensitivity import CONDITIONS, PROTOCOL_ID
from .exp_submission_upgrade import PROTOCOL_ID as PRIMARY_PROTOCOL_ID, _cvar


PRIMARY_CONDITION = "beta90_s160"
ALL_CONDITIONS = {
    PRIMARY_CONDITION: {"beta": 0.90, "design_cap": 160},
    **CONDITIONS,
}
REFERENCES = ("ollivier", "min_mlu")
ADAPTIVE_POLICIES = (
    "min_mlu", "ollivier", "single_minimax", "double_cvar90"
)
SCORES = ("ollivier", "forman", "degree", "betweenness")


def _losses(rows):
    return np.asarray([row["service_loss"] for row in rows], dtype=float)


def _row_key(row):
    scenario = tuple(tuple(edge) for edge in row["scenario"])
    return int(row["traffic_matrix"]), scenario


def _summary(values, rng):
    values = np.asarray(values, dtype=float)
    return {
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "topology_cluster_bootstrap_95_ci": _bootstrap_ci(values.tolist(), rng),
        "exact_two_sided_sign_flip_p_value": _sign_flip_p_value(values.tolist()),
        "negative": int(np.sum(values < -1e-12)),
        "positive": int(np.sum(values > 1e-12)),
        "tied": int(np.sum(np.abs(values) <= 1e-12)),
    }


def _absolute_summary(values, rng):
    values = np.asarray(values, dtype=float)
    return {
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "topology_cluster_bootstrap_95_ci": _bootstrap_ci(values.tolist(), rng),
    }


def _primary_candidate(primary_result):
    return (
        primary_result["held_out_raw"]["double_cvar90"],
        primary_result["method_summary"]["double_cvar90"]["nominal_path_cost"]["mean"],
    )


def _sensitivity_candidate(sensitivity_result, condition):
    return (
        sensitivity_result["held_out_raw"][condition],
        sensitivity_result["conditions"][condition]["nominal_path_cost"]["mean"],
    )


def _condition_comparison(
    primary_by_topology, sensitivity_by_topology, condition, reference
):
    beta = ALL_CONDITIONS[condition]["beta"]
    topology_rows = []
    for topology, primary_result in primary_by_topology.items():
        if condition == PRIMARY_CONDITION:
            candidate_rows, candidate_cost = _primary_candidate(primary_result)
        else:
            candidate_rows, candidate_cost = _sensitivity_candidate(
                sensitivity_by_topology[topology], condition
            )
        reference_rows = primary_result["held_out_raw"][reference]
        candidate_losses = _losses(candidate_rows)
        reference_losses = _losses(reference_rows)
        if candidate_losses.shape != reference_losses.shape:
            raise ValueError(f"{topology} {condition}: held-out row mismatch")
        reference_cost = primary_result["method_summary"][reference][
            "nominal_path_cost"
        ]["mean"]
        topology_rows.append({
            "topology": topology,
            "declared_cvar_delta": _cvar(candidate_losses, beta) - _cvar(reference_losses, beta),
            "cvar90_delta": _cvar(candidate_losses, 0.90) - _cvar(reference_losses, 0.90),
            "mean_loss_delta": float(candidate_losses.mean() - reference_losses.mean()),
            "max_loss_delta": float(candidate_losses.max() - reference_losses.max()),
            "path_cost_relative_delta": float(candidate_cost / reference_cost - 1.0),
        })
    metrics = [
        "declared_cvar_delta", "cvar90_delta", "mean_loss_delta",
        "max_loss_delta", "path_cost_relative_delta",
    ]
    return {
        "condition": condition,
        "reference": reference,
        "beta": beta,
        "design_cap": ALL_CONDITIONS[condition]["design_cap"],
        "topology_level": topology_rows,
        "summary": {
            # Restart the topology bootstrap for every estimand.  This makes
            # each interval independent of report ordering and reproduces the
            # frozen primary interval for beta=.90, S=160.
            metric: _summary(
                [row[metric] for row in topology_rows],
                np.random.default_rng(20260714),
            )
            for metric in metrics
        },
    }


def _adaptive_summary(primary_results, rng):
    topology_rows = []
    score_rows = {score: [] for score in SCORES}
    for result in primary_results:
        adaptive = result["adaptive_reference"]
        adaptive_losses = _losses(adaptive)
        adaptive_keys = {_row_key(row) for row in adaptive}
        row = {
            "topology": result["topology"],
            "adaptive": {
                "mean_loss": float(adaptive_losses.mean()),
                "cvar90": _cvar(adaptive_losses, 0.90),
                "max_loss": float(adaptive_losses.max()),
                "observations": int(adaptive_losses.size),
            },
            "frozen": {},
        }
        for policy in ADAPTIVE_POLICIES:
            matching = [
                item for item in result["held_out_raw"][policy]
                if _row_key(item) in adaptive_keys
            ]
            if len(matching) != len(adaptive):
                raise ValueError(
                    f"{result['topology']} {policy}: adaptive scenario join mismatch"
                )
            losses = _losses(matching)
            row["frozen"][policy] = {
                "mean_loss": float(losses.mean()),
                "cvar90": _cvar(losses, 0.90),
                "max_loss": float(losses.max()),
                "recoverable_mean_gap": float(losses.mean() - adaptive_losses.mean()),
            }
        topology_rows.append(row)

        for score in SCORES:
            values = [
                item["rho"]
                for item in result["score_vs_adaptive_double_failure_impact"][score]
                if item["rho"] is not None
            ]
            if values:
                score_rows[score].append({
                    "topology": result["topology"],
                    "mean_spearman_rho": float(np.mean(values)),
                    "traffic_matrices": len(values),
                })

    policies = ["adaptive", *ADAPTIVE_POLICIES]
    policy_summary = {}
    for policy in policies:
        source = [
            row["adaptive"] if policy == "adaptive" else row["frozen"][policy]
            for row in topology_rows
        ]
        policy_summary[policy] = {
            metric: _absolute_summary([item[metric] for item in source], rng)
            for metric in ("mean_loss", "cvar90", "max_loss")
        }
        if policy != "adaptive":
            policy_summary[policy]["recoverable_mean_gap"] = _absolute_summary(
                [item["recoverable_mean_gap"] for item in source], rng
            )

    correlation_summary = {}
    for score, rows in score_rows.items():
        values = [row["mean_spearman_rho"] for row in rows]
        correlation_summary[score] = {
            "topology_level": rows,
            "summary": _absolute_summary(values, rng),
        }
    return {
        "scenario_sample_per_topology_tm": 40,
        "topology_level": topology_rows,
        "policy_summary": policy_summary,
        "structural_score_associations": correlation_summary,
    }


def analyse(primary_payload, sensitivity_payload):
    if primary_payload.get("protocol_id") != PRIMARY_PROTOCOL_ID:
        raise ValueError("primary output protocol mismatch")
    if sensitivity_payload.get("protocol_id") != PROTOCOL_ID:
        raise ValueError("sensitivity output protocol mismatch")
    if sensitivity_payload["completed_topologies"] != len(
        sensitivity_payload["requested_topologies"]
    ):
        raise ValueError("refusing to analyze an incomplete sensitivity run")

    primary_by_topology = {
        row["topology"]: row for row in primary_payload["results"]
    }
    sensitivity_by_topology = {
        row["topology"]: row for row in sensitivity_payload["results"]
    }
    if set(primary_by_topology) != set(sensitivity_by_topology):
        raise ValueError("primary and sensitivity topology sets differ")

    rng = np.random.default_rng(20260714)
    comparisons = [
        _condition_comparison(
            primary_by_topology, sensitivity_by_topology, condition, reference
        )
        for reference in REFERENCES
        for condition in ALL_CONDITIONS
    ]
    return {
        "protocol_id": PROTOCOL_ID,
        "topology_count": len(primary_by_topology),
        "conditions": ALL_CONDITIONS,
        "comparisons": comparisons,
        "adaptive_recovery_ceiling": _adaptive_summary(
            primary_payload["results"], rng
        ),
        "runtime": {
            "additional_topology_wall_seconds": float(sum(
                row["topology_wall_seconds"] for row in sensitivity_payload["results"]
            )),
        },
    }


def _write_markdown(analysis, path):
    lines = [
        "# Scenario-risk sensitivity and adaptive recovery",
        "",
        "All values are equal-topology means over twelve topologies. Negative",
        "deltas favor the CVaR policy. Additional conditions are robustness",
        "checks; the beta=.90, S=160 condition remains the frozen primary.",
        "",
        "## One-factor sensitivity versus ORC",
        "",
        "| Condition | Declared CVaR delta (pp) | CVaR90 delta (pp) | Mean delta (pp) | Path cost |",
        "|---|---:|---:|---:|---:|",
    ]
    for condition in ALL_CONDITIONS:
        comparison = next(
            row for row in analysis["comparisons"]
            if row["condition"] == condition and row["reference"] == "ollivier"
        )
        summary = comparison["summary"]
        lines.append(
            "| {condition} | {declared:+.3f} | {cvar90:+.3f} | {mean:+.3f} | {cost:+.2f}% |".format(
                condition=condition,
                declared=100 * summary["declared_cvar_delta"]["mean"],
                cvar90=100 * summary["cvar90_delta"]["mean"],
                mean=100 * summary["mean_loss_delta"]["mean"],
                cost=100 * summary["path_cost_relative_delta"]["mean"],
            )
        )
    lines.extend([
        "",
        "## Adaptive capacity-feasible recovery ceiling",
        "",
        "| Routing state | Mean loss (pp) | CVaR90 (pp) | Max loss (pp) |",
        "|---|---:|---:|---:|",
    ])
    adaptive = analysis["adaptive_recovery_ceiling"]["policy_summary"]
    labels = {
        "adaptive": "Adaptive ceiling",
        "min_mlu": "Frozen minimum MLU",
        "ollivier": "Frozen ORC",
        "single_minimax": "Frozen single minimax",
        "double_cvar90": "Frozen double CVaR(0.90)",
    }
    for policy, label in labels.items():
        item = adaptive[policy]
        lines.append(
            f"| {label} | {100*item['mean_loss']['mean']:.3f} | "
            f"{100*item['cvar90']['mean']:.3f} | {100*item['max_loss']['mean']:.3f} |"
        )
    lines.extend([
        "",
        "## Structural score association with adaptive double-failure loss",
        "",
        "| Score | Mean topology-level Spearman rho | 95% bootstrap interval |",
        "|---|---:|---:|",
    ])
    associations = analysis["adaptive_recovery_ceiling"][
        "structural_score_associations"
    ]
    for score in SCORES:
        item = associations[score]["summary"]
        lo, hi = item["topology_cluster_bootstrap_95_ci"]
        lines.append(f"| {score} | {item['mean']:+.3f} | [{lo:+.3f}, {hi:+.3f}] |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    workspace = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--primary-input", type=Path,
        default=workspace / "reproducibility_code" / "results"
        / "submission_upgrade_double_failure.json",
    )
    parser.add_argument(
        "--sensitivity-input", type=Path,
        default=workspace / "reproducibility_code" / "results"
        / "scenario_risk_sensitivity.json",
    )
    parser.add_argument(
        "--output", type=Path,
        default=workspace / "reproducibility_code" / "results"
        / "scenario_risk_sensitivity_analysis.json",
    )
    parser.add_argument(
        "--markdown", type=Path,
        default=workspace / "SCENARIO_RISK_SENSITIVITY_RESULTS.md",
    )
    args = parser.parse_args()

    primary = json.loads(args.primary_input.read_text(encoding="utf-8"))
    sensitivity = json.loads(args.sensitivity_input.read_text(encoding="utf-8"))
    analysis = analyse(primary, sensitivity)
    args.output.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    _write_markdown(analysis, args.markdown)
    print(json.dumps({
        "output": str(args.output),
        "markdown": str(args.markdown),
        "topologies": analysis["topology_count"],
    }, indent=2))


if __name__ == "__main__":
    main()
