"""Figure 1 -- Canonical sub-structures: two hub-and-spoke stars joined by an
inter-hub bridge, edges colored by REAL Ollivier-Ricci curvature."""
import numpy as np, networkx as nx
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from GraphRicciCurvature.OllivierRicci import OllivierRicci
import style as S

rng = np.random.default_rng(7)

# ---- build the canonical motif ----
G = nx.Graph()
H1, H2 = "H1", "H2"
left_leaves  = [f"a{i}" for i in range(6)]
right_leaves = [f"b{i}" for i in range(6)]
for l in left_leaves:  G.add_edge(H1, l)
for l in right_leaves: G.add_edge(H2, l)
G.add_edge(H1, H2)                      # the inter-hub bridge

# ---- real Ollivier-Ricci curvature (alpha = 0.5) ----
orc = OllivierRicci(G, alpha=0.5, verbose="ERROR")
orc.compute_ricci_curvature()
Gc = orc.G
kappa = {(u, v): Gc[u][v]["ricciCurvature"] for u, v in Gc.edges()}

# ---- manual symmetric layout (leaves fan on the OUTER hemisphere only) ----
pos = {}
pos[H1] = (-1.0, 0.0); pos[H2] = (1.0, 0.0)
r = 1.05
n = len(left_leaves)
left_angles  = np.linspace(np.deg2rad(115), np.deg2rad(245), n)   # fan left
right_angles = np.linspace(np.deg2rad(-65), np.deg2rad(65),  n)   # fan right
for l, th in zip(left_leaves, left_angles):
    pos[l] = (-1.0 + r*np.cos(th), r*np.sin(th))
for l, th in zip(right_leaves, right_angles):
    pos[l] = (1.0 + r*np.cos(th), r*np.sin(th))

fig, ax = plt.subplots(figsize=(8.6, 4.0))
norm = S.curv_norm(vmin=min(kappa.values()) - 0.02, vmax=max(kappa.values()) + 0.02)

# edges
for (u, v), k in kappa.items():
    is_bridge = {u, v} == {H1, H2}
    lw = 5.2 if is_bridge else 2.0
    ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
            color=S.CURV_CMAP(norm(k)), lw=lw,
            solid_capstyle="round", zorder=1)

# nodes
deg = dict(G.degree())
for n in G.nodes():
    is_hub = n in (H1, H2)
    ax.scatter(*pos[n], s=900 if is_hub else 220,
               c=[S.INK] if is_hub else ["#ffffff"],
               edgecolors=S.INK, linewidths=1.6 if is_hub else 1.1, zorder=3)
    if is_hub:
        ax.text(*pos[n], n, color="white", ha="center", va="center",
                fontsize=12, fontweight="bold", zorder=4)

# annotations
kb = kappa.get((H1, H2), kappa.get((H2, H1)))
ks = np.mean([kappa[e] for e in kappa if H1 in e and e != (H1, H2) and e != (H2, H1)])
ax.annotate(f"Inter-hub bridge\n$\\kappa(H_1,H_2) = {kb:.2f}\\;\\ll 0$",
            xy=(0, 0.0), xytext=(0, 0.86), ha="center", fontsize=10.5, color=S.CRIMSON,
            arrowprops=dict(arrowstyle="-|>", color=S.CRIMSON, lw=1.6))
ax.text(-1.0, -1.26, f"Hub-and-spoke star\n$\\kappa(H_1,\\ell_i)={ks:+.2f}\\geq 0$",
        ha="center", fontsize=10, color="#1e7a3c")
ax.text( 1.0, -1.26, f"Hub-and-spoke star\n$\\kappa(H_2,\\ell_j)={ks:+.2f}\\geq 0$",
        ha="center", fontsize=10, color="#1e7a3c")

sm = ScalarMappable(norm=norm, cmap=S.CURV_CMAP); sm.set_array([])
cb = fig.colorbar(sm, ax=ax, fraction=0.04, pad=0.02)
cb.set_label("Ollivier–Ricci curvature  $\\kappa$", fontsize=10.5)
cb.outline.set_linewidth(0.6)

ax.set_xlim(-2.5, 2.5); ax.set_ylim(-1.5, 1.12)
ax.set_aspect("equal"); ax.axis("off")
fig.savefig("fig1_canonical.pdf", bbox_inches="tight", pad_inches=0.03)
fig.savefig("fig1_canonical.png", dpi=150, bbox_inches="tight", pad_inches=0.03)
print("Figure 1 written. bridge kappa =", round(kb,3), "| mean spoke kappa =", round(ks,3))
