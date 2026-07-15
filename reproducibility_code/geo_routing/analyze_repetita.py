"""Topology-clustered analysis of REPETITA experiment outputs."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np


METHODS = ["degree", "betweenness", "forman", "ollivier", "random_placebo"]


def _scenario_key(row):
    return int(row["traffic_matrix"]), tuple(row["edge"])


def _topology_deltas(result, method):
    baseline = {_scenario_key(row): row for row in result["frozen_raw"]["mlu"]}
    candidate = {_scenario_key(row): row for row in result["frozen_raw"][method]}
    if baseline.keys() != candidate.keys():
        raise ValueError(f"scenario mismatch for {result['topology']} {method}")
    keys = sorted(baseline)
    loss_delta = np.asarray(
        [
            (1.0 - candidate[key]["delivered_fraction"])
            - (1.0 - baseline[key]["delivered_fraction"])
            for key in keys
        ],
        dtype=float,
    )
    baseline_cost = np.mean(
        [row["average_path_cost"] for row in result["nominal"]["mlu"]]
    )
    method_cost = np.mean(
        [row["average_path_cost"] for row in result["nominal"][method]]
    )
    return {
        "mean_loss_delta": float(loss_delta.mean()),
        "worst_loss_delta": float(
            max(1.0 - row["delivered_fraction"] for row in candidate.values())
            - max(1.0 - row["delivered_fraction"] for row in baseline.values())
        ),
        "path_cost_relative_delta": float(method_cost / baseline_cost - 1.0),
    }


def _bootstrap_ci(values, rng, replicates=20000):
    values = np.asarray(values, dtype=float)
    indices = rng.integers(0, len(values), size=(replicates, len(values)))
    means = values[indices].mean(axis=1)
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def _sign_flip_p_value(values):
    values = np.asarray([value for value in values if not np.isclose(value, 0.0)], dtype=float)
    if not len(values):
        return 1.0
    observed = abs(float(values.mean()))
    if len(values) <= 20:
        statistics = [
            abs(float(np.mean(values * np.asarray(signs))))
            for signs in itertools.product((-1.0, 1.0), repeat=len(values))
        ]
        return float(np.mean(np.asarray(statistics) >= observed - 1e-15))
    rng = np.random.default_rng(20260714)
    signs = rng.choice((-1.0, 1.0), size=(200000, len(values)))
    statistics = np.abs((signs * values).mean(axis=1))
    return float((np.sum(statistics >= observed) + 1) / (len(statistics) + 1))


def _holm_adjust(p_values):
    ordered = sorted(p_values, key=p_values.get)
    adjusted = {}
    running = 0.0
    total = len(ordered)
    for rank, method in enumerate(ordered):
        running = max(running, (total - rank) * p_values[method])
        adjusted[method] = min(1.0, running)
    return adjusted


def analyse(results):
    rng = np.random.default_rng(20260714)
    topology_rows = {method: [] for method in METHODS}
    for result in results:
        for method in METHODS:
            topology_rows[method].append(
                {"topology": result["topology"], **_topology_deltas(result, method)}
            )

    raw_p = {
        method: _sign_flip_p_value(
            [row["mean_loss_delta"] for row in topology_rows[method]]
        )
        for method in METHODS
    }
    adjusted_p = _holm_adjust(raw_p)
    summary = {}
    for method in METHODS:
        loss = [row["mean_loss_delta"] for row in topology_rows[method]]
        worst = [row["worst_loss_delta"] for row in topology_rows[method]]
        cost = [row["path_cost_relative_delta"] for row in topology_rows[method]]
        summary[method] = {
            "mean_service_loss_delta": float(np.mean(loss)),
            "cluster_bootstrap_95_ci": _bootstrap_ci(loss, rng),
            "median_service_loss_delta": float(np.median(loss)),
            "topologies_better_than_mlu": int(sum(value < 0 for value in loss)),
            "topologies_worse_than_mlu": int(sum(value > 0 for value in loss)),
            "mean_worst_case_loss_delta": float(np.mean(worst)),
            "mean_path_cost_relative_delta": float(np.mean(cost)),
            "sign_flip_p_value": raw_p[method],
            "holm_adjusted_p_value": adjusted_p[method],
        }
    return {"topology_level": topology_rows, "summary": summary}


def _markdown(analysis, topology_names):
    lines = [
        "# Preliminary topology-clustered REPETITA analysis",
        "",
        "This file is a design-validation artifact, not a manuscript result.",
        f"Topologies (n={len(topology_names)}): {', '.join(topology_names)}.",
        "Positive service-loss deltas mean worse performance than minimum-MLU.",
        "",
        "| Method | Mean loss delta (pp) | 95% cluster bootstrap CI (pp) | Better / worse topologies | Mean path-cost delta | Holm p |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for method in METHODS:
        row = analysis["summary"][method]
        ci = row["cluster_bootstrap_95_ci"]
        lines.append(
            "| {method} | {mean:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {better} / {worse} | {cost:+.2f}% | {p:.4f} |".format(
                method=method,
                mean=100.0 * row["mean_service_loss_delta"],
                lo=100.0 * ci[0],
                hi=100.0 * ci[1],
                better=row["topologies_better_than_mlu"],
                worse=row["topologies_worse_than_mlu"],
                cost=100.0 * row["mean_path_cost_relative_delta"],
                p=row["holm_adjusted_p_value"],
            )
        )
    lines.extend(
        [
            "",
            "Interpretation is intentionally withheld until the preregistered topology set is complete.",
        ]
    )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("results") / "repetita_preliminary_analysis.json"
    )
    parser.add_argument(
        "--markdown", type=Path, default=Path("results") / "repetita_preliminary_summary.md"
    )
    args = parser.parse_args()
    merged = []
    seen = set()
    for path in args.inputs:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for result in payload["results"]:
            if result["topology"] in seen:
                raise ValueError(f"duplicate topology: {result['topology']}")
            seen.add(result["topology"])
            merged.append(result)
    analysis = analyse(merged)
    output = {
        "preliminary_only": True,
        "experimental_unit": "topology",
        "multiple_comparison_correction": "Holm across five policy-vs-MLU tests",
        "topologies": sorted(seen),
        **analysis,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    args.markdown.write_text(_markdown(analysis, sorted(seen)), encoding="utf-8")
    print(args.markdown.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
