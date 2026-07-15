"""Topology-clustered analysis for the frozen submission-upgrade experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .analyze_repetita import _bootstrap_ci, _holm_adjust, _sign_flip_p_value
from .exp_submission_upgrade import POLICIES, PROTOCOL_ID


METRIC_KEYS = {
    "cvar90": "held_out_double_failure_cvar90",
    "mean_loss": "held_out_double_failure_mean_loss",
    "max_loss": "held_out_double_failure_max_loss",
}


def _topology_metric(result, policy, metric):
    return float(result["method_summary"][policy][METRIC_KEYS[metric]])


def _comparison(results, candidate, reference):
    rows = []
    for result in results:
        row = {"topology": result["topology"]}
        for metric in METRIC_KEYS:
            row[f"{metric}_delta"] = (
                _topology_metric(result, candidate, metric)
                - _topology_metric(result, reference, metric)
            )
        candidate_cost = result["method_summary"][candidate]["nominal_path_cost"]["mean"]
        reference_cost = result["method_summary"][reference]["nominal_path_cost"]["mean"]
        candidate_mlu = result["method_summary"][candidate]["nominal_mlu"]["mean"]
        reference_mlu = result["method_summary"][reference]["nominal_mlu"]["mean"]
        row["path_cost_relative_delta"] = candidate_cost / reference_cost - 1.0
        row["mlu_relative_delta"] = candidate_mlu / reference_mlu - 1.0
        rows.append(row)

    rng = np.random.default_rng(20260714)
    summary = {}
    for metric in [*METRIC_KEYS, "path_cost_relative", "mlu_relative"]:
        key = f"{metric}_delta"
        values = [row[key] for row in rows]
        summary[metric] = {
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "topology_cluster_bootstrap_95_ci": _bootstrap_ci(values, rng),
            "exact_two_sided_sign_flip_p_value": _sign_flip_p_value(values),
            "candidate_better": int(sum(value < -1e-12 for value in values)),
            "candidate_worse": int(sum(value > 1e-12 for value in values)),
            "tied": int(sum(abs(value) <= 1e-12 for value in values)),
        }
    return {
        "candidate": candidate,
        "reference": reference,
        "topology_level": rows,
        "summary": summary,
    }


def analyse(payload):
    if payload.get("protocol_id") != PROTOCOL_ID:
        raise ValueError("input does not match the frozen submission-upgrade protocol")
    results = payload["results"]
    if len(results) != len(payload["requested_topologies"]):
        raise ValueError("refusing to analyze an incomplete experiment")

    primary = _comparison(results, "double_cvar90", "ollivier")
    secondary_pairs = [
        (candidate, reference)
        for reference in ("min_mlu", "ollivier")
        for candidate in ("single_minimax", "double_expected", "double_cvar90", "double_minimax")
        if candidate != reference
    ]
    secondary = [_comparison(results, *pair) for pair in secondary_pairs]

    # Holm within each outcome/reference family, as frozen in the protocol.
    holm = {}
    for reference in ("min_mlu", "ollivier"):
        matching = [row for row in secondary if row["reference"] == reference]
        for metric in METRIC_KEYS:
            raw = {
                row["candidate"]: row["summary"][metric]["exact_two_sided_sign_flip_p_value"]
                for row in matching
            }
            holm[f"{metric}_vs_{reference}"] = {
                "raw": raw, "adjusted": _holm_adjust(raw)
            }

    correlations = {}
    score_names = ["ollivier", "forman", "degree", "betweenness"]
    for score_name in score_names:
        correlations[score_name] = []
    for result in results:
        for score_name in score_names:
            rhos = [
                row["rho"]
                for row in result["score_vs_adaptive_double_failure_impact"][score_name]
                if row["rho"] is not None
            ]
            correlations[score_name].append({
                "topology": result["topology"],
                "mean_spearman_rho": float(np.mean(rhos)) if rhos else None,
                "traffic_matrices_with_defined_rho": len(rhos),
            })

    return {
        "protocol_id": PROTOCOL_ID,
        "experimental_unit": "topology",
        "topology_count": len(results),
        "topologies": [result["topology"] for result in results],
        "primary_contrast": primary,
        "secondary_contrasts": secondary,
        "holm_families": holm,
        "structural_scores_vs_adaptive_double_failure_loss": correlations,
        "runtime": {
            "total_topology_wall_seconds": float(sum(r["topology_wall_seconds"] for r in results)),
            "per_topology_wall_seconds": {
                r["topology"]: r["topology_wall_seconds"] for r in results
            },
            "python_allocator_peak_bytes_max": int(max(
                r["python_tracemalloc_peak_bytes"] for r in results
            )),
            "memory_limit": "native HiGHS allocations are not measured",
        },
    }


def _markdown(analysis):
    primary = analysis["primary_contrast"]["summary"]["cvar90"]
    ci = primary["topology_cluster_bootstrap_95_ci"]
    lines = [
        "# Frozen held-out double-failure analysis",
        "",
        f"Experimental unit: topology (n={analysis['topology_count']}). Negative deltas favor the candidate.",
        "",
        "## Primary contrast",
        "",
        "Double-failure CVaR(0.90) TE minus Ollivier--Ricci TE, evaluated only on held-out scenarios:",
        "",
        f"- equal-topology mean delta: {100 * primary['mean']:+.3f} percentage points",
        f"- median delta: {100 * primary['median']:+.3f} percentage points",
        f"- topology-cluster bootstrap 95% interval: [{100 * ci[0]:+.3f}, {100 * ci[1]:+.3f}] percentage points",
        f"- exact two-sided sign-flip p: {primary['exact_two_sided_sign_flip_p_value']:.6f}",
        f"- better / worse / tied topologies: {primary['candidate_better']} / {primary['candidate_worse']} / {primary['tied']}",
        "",
        "## Policy comparisons",
        "",
        "| Candidate | Reference | CVaR delta (pp) | 95% CI (pp) | Mean-loss delta (pp) | Max-loss delta (pp) | Path-cost delta |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    all_comparisons = [analysis["primary_contrast"], *analysis["secondary_contrasts"]]
    seen = set()
    for comparison in all_comparisons:
        identity = (comparison["candidate"], comparison["reference"])
        if identity in seen:
            continue
        seen.add(identity)
        summary = comparison["summary"]
        ci = summary["cvar90"]["topology_cluster_bootstrap_95_ci"]
        lines.append(
            "| {candidate} | {reference} | {cvar:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {mean:+.3f} | {maximum:+.3f} | {cost:+.2f}% |".format(
                candidate=comparison["candidate"], reference=comparison["reference"],
                cvar=100 * summary["cvar90"]["mean"], lo=100 * ci[0], hi=100 * ci[1],
                mean=100 * summary["mean_loss"]["mean"],
                maximum=100 * summary["max_loss"]["mean"],
                cost=100 * summary["path_cost_relative"]["mean"],
            )
        )
    lines.extend([
        "",
        "The primary contrast was fixed before outcome inspection. Secondary p-values are stored with Holm adjustments in the JSON output.",
    ])
    return "\n".join(lines) + "\n"


def main():
    workspace = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input", type=Path,
        nargs="?",
        default=workspace / "reproducibility_code" / "results"
        / "submission_upgrade_double_failure.json",
    )
    parser.add_argument(
        "--output", type=Path,
        default=workspace / "reproducibility_code" / "results"
        / "submission_upgrade_analysis.json",
    )
    parser.add_argument(
        "--markdown", type=Path,
        default=workspace / "SUBMISSION_UPGRADE_RESULTS.md",
    )
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    analysis = analyse(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    args.markdown.write_text(_markdown(analysis), encoding="utf-8")
    print(args.markdown.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
