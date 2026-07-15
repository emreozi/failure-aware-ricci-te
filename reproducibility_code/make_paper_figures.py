"""Generate Computer Networks manuscript figures from exact JSON results."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).resolve().parent / "results"
OUTPUT = ROOT / "manuscript_cn" / "figures"

BLUE = "#3465a4"
ORANGE = "#d07c24"
GREEN = "#3a8f6b"
GREY = "#7a7a7a"
LIGHT = "#d9d9d9"


def _style():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def paired_effects():
    payload = json.loads((RESULTS / "repetita_confirmatory_analysis.json").read_text())
    rows = payload["topology_level"]["ollivier"]
    rows = sorted(rows, key=lambda row: row["mean_loss_delta"])
    names = [row["topology"] for row in rows]
    values = 100.0 * np.asarray([row["mean_loss_delta"] for row in rows])
    summary = payload["summary"]["ollivier"]
    mean = 100.0 * summary["mean_service_loss_delta"]
    ci = 100.0 * np.asarray(summary["cluster_bootstrap_95_ci"])

    fig, ax = plt.subplots(figsize=(6.7, 4.2), constrained_layout=True)
    y = np.arange(len(names))
    ax.axvline(0.0, color=GREY, lw=1.0)
    ax.hlines(y, 0.0, values, color=LIGHT, lw=1.6)
    colors = [ORANGE if value > 0 else BLUE for value in values]
    ax.scatter(values, y, c=colors, s=35, zorder=3, edgecolor="white", linewidth=0.5)
    for yi, value in zip(y, values):
        display_value = 0.0 if abs(value) < 0.0005 else value
        ax.text(
            value + 0.035,
            yi,
            f"{display_value:+.3f}" if display_value else "0.000",
            va="center",
            ha="left",
            fontsize=8,
        )
    ax.set_yticks(y, names)
    ax.set_xlabel("ORC minus minimum-MLU service loss (percentage points)")
    ax.set_title(
        "Held-out physical single-link failures\nNegative favors ORC; positive favors minimum MLU",
        loc="left",
        weight="bold",
        fontsize=10,
        pad=9,
    )
    summary_y = len(names) + 0.45
    ax.errorbar(
        mean,
        summary_y,
        xerr=np.array([[mean - ci[0]], [ci[1] - mean]]),
        fmt="D",
        color="black",
        capsize=3,
        markersize=5,
        lw=1.2,
    )
    ax.text(ci[1] + 0.04, summary_y, f"mean {mean:+.3f} pp", va="center", fontsize=8)
    ax.set_yticks([*y, summary_y], [*names, "Topology mean"])
    ax.set_ylim(-0.8, len(names) + 1.2)
    ax.invert_yaxis()
    ax.text(
        0.99,
        0.01,
        "Exact two-sided topology sign-flip p = 0.0625",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8,
        color=GREY,
    )
    fig.savefig(OUTPUT / "fig1_confirmatory_paired_effects.pdf", bbox_inches="tight")
    fig.savefig(OUTPUT / "fig1_confirmatory_paired_effects.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def tail_slope():
    payload = json.loads((RESULTS / "repetita_tail_validation.json").read_text())
    methods = ["mlu", "ollivier", "tail_robust"]
    labels = ["Minimum MLU", "Ollivier--Ricci", "Direct tail-robust"]
    x = np.arange(3)

    topology_values = []
    names = []
    for result in payload["results"]:
        names.append(result["topology"])
        values = []
        for method in methods:
            losses = [
                100.0 * (1.0 - row["delivered_fraction"])
                for row in result["frozen_raw"][method]
            ]
            values.append(max(losses))
        topology_values.append(values)
    topology_values = np.asarray(topology_values)

    fig, ax = plt.subplots(figsize=(6.7, 4.3), constrained_layout=True)
    for values in topology_values:
        ax.plot(x, values, color=LIGHT, lw=1.0, marker="o", ms=3, zorder=1)
    means = topology_values.mean(axis=0)
    ax.plot(x, means, color="black", lw=2.2, marker="D", ms=6, zorder=4, label="Topology mean")
    for xi, value in zip(x, means):
        ax.text(xi, value + 1.0, f"{value:.2f}%", ha="center", va="bottom", fontsize=8, weight="bold")
    ax.set_xticks(x, ["Minimum MLU", "Ollivier–Ricci", "Direct tail-robust"])
    ax.set_ylabel("Worst frozen-route service loss (%)")
    ax.set_title(
        "Direct tail-risk optimization lowers the worst failure loss\nEach light line is one topology; lower is better",
        loc="left",
        weight="bold",
        fontsize=10,
        pad=9,
    )
    ax.set_xlim(-0.2, 2.2)
    ax.text(2.04, means[2], "Topology mean", va="center", fontsize=8, weight="bold")
    ax.text(
        0.99,
        0.01,
        "Separate held-out tail validation",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8,
        color=GREY,
    )
    fig.savefig(OUTPUT / "fig2_tail_robust_slope.pdf", bbox_inches="tight")
    fig.savefig(OUTPUT / "fig2_tail_robust_slope.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def double_failure_cvar():
    payload = json.loads((RESULTS / "submission_upgrade_analysis.json").read_text())
    comparison = payload["primary_contrast"]
    rows = sorted(comparison["topology_level"], key=lambda row: row["cvar90_delta"])
    names = [row["topology"] for row in rows]
    values = 100.0 * np.asarray([row["cvar90_delta"] for row in rows])
    summary = comparison["summary"]["cvar90"]
    mean = 100.0 * summary["mean"]
    ci = 100.0 * np.asarray(summary["topology_cluster_bootstrap_95_ci"])

    fig, ax = plt.subplots(figsize=(6.7, 4.8), constrained_layout=True)
    y = np.arange(len(names))
    ax.axvline(0.0, color=GREY, lw=1.0)
    ax.hlines(y, 0.0, values, color=LIGHT, lw=1.6)
    colors = [BLUE if value < 0 else ORANGE if value > 0 else GREY for value in values]
    ax.scatter(values, y, c=colors, s=35, zorder=3, edgecolor="white", linewidth=0.5)
    for yi, value in zip(y, values):
        ax.text(
            value + 0.06, yi, f"{value:+.3f}" if abs(value) > 0.0005 else "0.000",
            va="center", ha="left", fontsize=8,
        )
    summary_y = len(names) + 0.45
    ax.errorbar(
        mean, summary_y,
        xerr=np.array([[mean - ci[0]], [ci[1] - mean]]),
        fmt="D", color="black", capsize=3, markersize=5, lw=1.2,
    )
    ax.set_yticks([*y, summary_y], [*names, "Topology mean"])
    ax.set_xlabel("Double-CVaR TE minus ORC CVaR loss (percentage points)")
    ax.set_title(
        "Held-out double-link failures\nNegative favors direct scenario-risk TE",
        loc="left", weight="bold", fontsize=10, pad=9,
    )
    ax.set_ylim(-0.8, len(names) + 1.2)
    ax.invert_yaxis()
    fig.savefig(OUTPUT / "fig3_double_failure_cvar.pdf", bbox_inches="tight")
    fig.savefig(OUTPUT / "fig3_double_failure_cvar.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    _style()
    paired_effects()
    tail_slope()
    double_failure_cvar()
    print(f"saved figures to {OUTPUT}")


if __name__ == "__main__":
    main()
