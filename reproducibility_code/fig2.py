"""Figure 2 -- Flow optimization under the node-adaptive NLP model: traffic from
S to D avoids the penalized inter-hub bridge and is redistributed across
positively-curved relay nodes. Arrow width encodes optimal flow x*.
This is an illustrative schematic of the mechanism, not a data plot."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Circle
import style as S

fig, ax = plt.subplots(figsize=(9.0, 5.2))

pos = {
    "S":  (-3.0, 0.0),
    "H1": (-1.2, 0.55), "H2": (1.2, 0.55),
    "r1": (-1.6, -1.25), "r2": (0.0, -1.7), "r3": (1.6, -1.25),
    "D":  (3.0, 0.0),
}
# flows: (u, v, flow, kind)  kind in {bridge, feed, detour}
edges = [
    ("S", "H1", 0.9, "feed"),
    ("H1", "H2", 0.12, "bridge"),     # penalized -> almost zero
    ("H2", "D", 0.9, "feed"),
    ("S", "r1", 2.6, "detour"),
    ("r1", "r2", 2.6, "detour"),
    ("r2", "r3", 2.6, "detour"),
    ("r3", "D", 2.6, "detour"),
]

def draw_edge(u, v, flow, kind):
    x0, y0 = pos[u]; x1, y1 = pos[v]
    if kind == "bridge":
        col, ls, alpha = S.CRIMSON, (0, (4, 3)), 0.9
        lw = 1.6
    elif kind == "detour":
        col, ls, alpha = S.TEAL, "-", 0.95
        lw = 1.4 + flow * 1.7
    else:
        col, ls, alpha = S.STEEL, "-", 0.8
        lw = 1.2 + flow * 1.2
    arr = FancyArrowPatch((x0, y0), (x1, y1),
                          arrowstyle="-|>", mutation_scale=16 + flow*4,
                          lw=lw, color=col, linestyle=ls, alpha=alpha,
                          shrinkA=20, shrinkB=20, zorder=2,
                          connectionstyle="arc3,rad=0.0")
    ax.add_patch(arr)

for u, v, f, k in edges:
    draw_edge(u, v, f, k)

# nodes
node_style = {
    "S":  ("S", S.INK, "white", 1300),
    "D":  ("D", S.INK, "white", 1300),
    "H1": ("$H_1$", "#8a3324", "white", 1050),
    "H2": ("$H_2$", "#8a3324", "white", 1050),
    "r1": ("$r_1$", S.TEAL_DK, "white", 820),
    "r2": ("$r_2$", S.TEAL_DK, "white", 820),
    "r3": ("$r_3$", S.TEAL_DK, "white", 820),
}
for n, (lbl, fc, tc, sz) in node_style.items():
    ax.scatter(*pos[n], s=sz, c=[fc], edgecolors="white", linewidths=1.6, zorder=4)
    ax.text(*pos[n], lbl, ha="center", va="center", color=tc,
            fontsize=12, fontweight="bold", zorder=5)

# labels / annotations
mid = ((pos["H1"][0]+pos["H2"][0])/2, (pos["H1"][1]+pos["H2"][1])/2)
ax.annotate("Penalized bottleneck  ($\\lambda_{ij}\\!\\uparrow$)\n"
            "$x^{*}_{H_1,H_2}\\approx 0$",
            xy=mid, xytext=(0.0, 1.95), ha="center", fontsize=10.5, color=S.CRIMSON,
            arrowprops=dict(arrowstyle="-|>", color=S.CRIMSON, lw=1.4))
ax.text(0.0, -0.35, "Redistributed flow through\npositively-curved relays\n$\\kappa(r_i,r_j) > 0$", ha="center", va="center", fontsize=10.5, color=S.TEAL_DK)
ax.text(-3.0, -0.62, "source", ha="center", fontsize=9, color=S.GREY)
ax.text( 3.0, 0.62, "destination", ha="center", fontsize=9, color=S.GREY)

# legend (proxy)
from matplotlib.lines import Line2D
leg = [Line2D([0],[0], color=S.TEAL, lw=4, label="Optimal NLP flow $x^{*}$ (width $\\propto$ load)"),
       Line2D([0],[0], color=S.CRIMSON, lw=1.8, ls=(0,(4,3)), label="Penalized bridge (evacuated)"),
       Line2D([0],[0], color=S.STEEL, lw=2, label="Residual hub feed")]
ax.legend(handles=leg, loc="lower left", frameon=True, framealpha=0.95,
          edgecolor="#cccccc", bbox_to_anchor=(-0.02, -0.02))

ax.set_xlim(-4.0, 4.2); ax.set_ylim(-2.7, 2.35)
ax.set_aspect("equal"); ax.axis("off")
fig.savefig("fig2_flow.pdf"); fig.savefig("fig2_flow.png", dpi=150)
print("Figure 2 written.")
