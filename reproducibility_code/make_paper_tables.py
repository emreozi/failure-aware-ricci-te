"""Generate LaTeX/CSV tables from exact experiment outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).resolve().parent / "results"
OUTPUT = ROOT / "manuscript_cn" / "tables"


def topology_table():
    payload = json.loads((RESULTS / "repetita_confirmatory.json").read_text())
    rows = []
    for result in payload["results"]:
        rows.append(
            {
                "topology": result["topology"],
                "nodes": result["nodes"],
                "directed_arcs": result["directed_arcs"],
                "physical_links": result["physical_links"],
                "parallel_bundles": result["parallel_bundles"],
                "od_pairs": result["nodes"] * (result["nodes"] - 1),
                "failure_cases": 4 * result["physical_links"],
                "orc_strength": result["selected_strengths"]["ollivier"],
            }
        )

    with (OUTPUT / "table1_topologies.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    body = []
    for row in rows:
        body.append(
            "{topology} & {nodes} & {directed_arcs} & {physical_links} & {parallel_bundles} & {od_pairs} & {failure_cases} & {orc_strength:g} \\\\".format(
                **row
            )
        )
    latex = """\\begin{table*}[t]
\\centering
\\caption{Held-out confirmatory REPETITA instances. Failure cases equal four test traffic matrices times all physical single-link failures. Parallel bundles contain only equal-delay, equal-IGP-weight arcs.}
\\label{tab:topologies}
\\small
\\resizebox{\\textwidth}{!}{%
\\begin{tabular}{lrrrrrrr}
\\toprule
Topology & Nodes & Directed arcs & Physical links & Bundles & OD pairs & Failure cases & $\\lambda_{\\mathrm{ORC}}$ \\\\
\\midrule
""" + "\n".join(body) + """
\\bottomrule
\\end{tabular}
}
\\end{table*}
"""
    (OUTPUT / "table1_topologies.tex").write_text(latex, encoding="utf-8")


def scenario_sensitivity_tables():
    payload = json.loads(
        (RESULTS / "scenario_risk_sensitivity_analysis.json").read_text()
    )
    condition_order = [
        "beta90_s160", "beta80_s160", "beta95_s160",
        "beta90_s40", "beta90_s80",
    ]
    labels = {
        "beta90_s160": "Main",
        "beta80_s160": "CVaR level",
        "beta95_s160": "CVaR level",
        "beta90_s40": "Scenario budget",
        "beta90_s80": "Scenario budget",
    }
    comparisons = {
        row["condition"]: row
        for row in payload["comparisons"]
        if row["reference"] == "ollivier"
    }
    body = []
    for condition in condition_order:
        row = comparisons[condition]
        summary = row["summary"]
        ci = summary["cvar90_delta"]["topology_cluster_bootstrap_95_ci"]
        body.append(
            f"{labels[condition]} & {row['beta']:.2f} & up to {row['design_cap']} & "
            f"{100*summary['cvar90_delta']['mean']:+.3f} & "
            f"[{100*ci[0]:+.3f}, {100*ci[1]:+.3f}] & "
            f"{100*summary['mean_loss_delta']['mean']:+.3f} / "
            f"{100*summary['path_cost_relative_delta']['mean']:+.2f}\\% \\\\"
        )
    latex = r"""\begin{table*}[t]
\centering
\caption{One-factor sensitivity of held-out double-failure CVaR TE relative to ORC. Negative CVaR differences favor direct risk control. The main condition is confirmatory; the other rows are protocol-fixed robustness checks.}
\label{tab:scenario-sensitivity}
\small
\resizebox{\textwidth}{!}{%
\begin{tabular}{lrrrrr}
\toprule
Condition & $\beta$ & Design scenarios & CVaR(0.90) $\Delta$ (pp) & 95\% CI (pp) & Mean $\Delta$ / path cost \\
\midrule
""" + "\n".join(body) + r"""
\bottomrule
\end{tabular}
}
\end{table*}
"""
    (OUTPUT / "table_scenario_sensitivity.tex").write_text(latex, encoding="utf-8")

    adaptive = payload["adaptive_recovery_ceiling"]["policy_summary"]
    policy_order = [
        "adaptive", "min_mlu", "ollivier", "single_minimax", "double_cvar90"
    ]
    policy_labels = {
        "adaptive": "Adaptive capacity-feasible ceiling",
        "min_mlu": "Frozen minimum MLU",
        "ollivier": "Frozen Ollivier--Ricci",
        "single_minimax": "Frozen single-link minimax",
        "double_cvar90": "Frozen double-failure CVaR",
    }
    adaptive_body = []
    for policy in policy_order:
        row = adaptive[policy]
        gap = (
            "---" if policy == "adaptive"
            else f"{100*row['recoverable_mean_gap']['mean']:.3f}"
        )
        adaptive_body.append(
            f"{policy_labels[policy]} & {100*row['mean_loss']['mean']:.3f} & "
            f"{100*row['cvar90']['mean']:.3f} & "
            f"{100*row['max_loss']['mean']:.3f} & {gap} \\\\"
        )
    adaptive_latex = r"""\begin{table*}[t]
\centering
\caption{Frozen routing and the capacity-feasible adaptive recovery ceiling on the same 40 held-out double-failure pairs per topology and four test matrices. Values are equal-topology means. Recoverable gap is frozen mean loss minus adaptive mean loss.}
\label{tab:adaptive}
\small
\resizebox{\textwidth}{!}{%
\begin{tabular}{lrrrr}
\toprule
Routing state & Mean loss (pp) & CVaR(0.90) (pp) & Maximum loss (pp) & Recoverable gap (pp) \\
\midrule
""" + "\n".join(adaptive_body) + r"""
\bottomrule
\end{tabular}
}
\end{table*}
"""
    (OUTPUT / "table_adaptive.tex").write_text(adaptive_latex, encoding="utf-8")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    topology_table()
    scenario_sensitivity_tables()
    print(f"saved tables to {OUTPUT}")


if __name__ == "__main__":
    main()
