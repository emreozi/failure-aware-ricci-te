"""Shared publication-quality plotting style."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
import matplotlib.colors as mcolors

# ---- global rcParams ----
rcParams.update({
    "figure.dpi": 200,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "mathtext.fontset": "dejavuserif",
    "axes.titlesize": 13,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 9.5,
    "axes.linewidth": 0.9,
    "axes.edgecolor": "#444444",
    "axes.grid": False,
})

# ---- palette ----
CURV_CMAP = plt.get_cmap("RdYlGn")          # red(neg) -> yellow(0) -> green(pos)
TEAL      = "#0f8a8a"
TEAL_DK   = "#0a6464"
CRIMSON   = "#c0392b"
STEEL     = "#34557a"
AMBER     = "#e08a1e"
GREY      = "#9aa3ad"
INK       = "#1c2530"

def curv_norm(vmin=-0.7, vmax=0.3):
    """Diverging norm centered at 0 for curvature coloring."""
    return mcolors.TwoSlopeNorm(vmin=vmin, vcenter=0.0, vmax=vmax)

def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(length=3, color="#444444")
    return ax
