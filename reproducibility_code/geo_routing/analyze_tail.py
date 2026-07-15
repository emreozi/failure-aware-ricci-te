"""Exploratory topology-clustered analysis of direct tail-risk optimization."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .analyze_repetita import _bootstrap_ci, _sign_flip_p_value


def _stats(result, method):
    rows = result["frozen_raw"][method]
    losses = np.asarray([1.0 - row["delivered_fraction"] for row in rows])
    costs = np.asarray(
        [row["average_path_cost"] for row in result["nominal"][method]], dtype=float
    )
    return {
        "mean_loss": float(losses.mean()),
        "worst_loss": float(losses.max()),
        "path_cost": float(costs.mean()),
    }


def _comparison(results, candidate, reference):
    rows = []
    for result in results:
        a = _stats(result, candidate)
        b = _stats(result, reference)
        rows.append(
            {
                "topology": result["topology"],
                "mean_loss_delta": a["mean_loss"] - b["mean_loss"],
                "worst_loss_delta": a["worst_loss"] - b["worst_loss"],
                "path_cost_relative_delta": a["path_cost"] / b["path_cost"] - 1.0,
            }
        )
    rng = np.random.default_rng(20260714)
    summary = {}
    for metric in ("mean_loss_delta", "worst_loss_delta", "path_cost_relative_delta"):
        values = [row[metric] for row in rows]
        summary[metric] = {
            "mean": float(np.mean(values)),
            "bootstrap_95_ci": _bootstrap_ci(values, rng),
            "sign_flip_p_value": _sign_flip_p_value(values),
            "candidate_better": int(sum(value < 0 for value in values)),
            "candidate_worse": int(sum(value > 0 for value in values)),
        }
    return {"candidate": candidate, "reference": reference, "topologies": rows, "summary": summary}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("results") / "tail_exploratory_analysis.json"
    )
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    results = payload["results"]
    comparisons = [
        _comparison(results, "ollivier", "mlu"),
        _comparison(results, "tail_robust", "mlu"),
        _comparison(results, "tail_robust", "ollivier"),
    ]
    output = {
        "exploratory_only": True,
        "reason": "tail_robust was designed after inspecting confirmatory secondary outcomes",
        "topologies": [result["topology"] for result in results],
        "comparisons": comparisons,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    for comparison in comparisons:
        print(f"{comparison['candidate']} minus {comparison['reference']}")
        for metric, values in comparison["summary"].items():
            print(metric, json.dumps(values))


if __name__ == "__main__":
    main()
