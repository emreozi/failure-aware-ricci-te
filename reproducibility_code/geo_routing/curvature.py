"""Discrete Forman--Ricci and exact Ollivier--Ricci curvature.

The portable Ollivier implementation below avoids the ``fork``-only
multiprocessing path in GraphRicciCurvature 0.5.3.2, which fails on Windows.
For every requested edge it constructs the alpha-lazy neighbourhood measures
and solves the exact Earth Mover's Distance problem with POT.
"""
import time
import networkx as nx
import numpy as np
import ot
from GraphRicciCurvature.FormanRicci import FormanRicci


def forman_all(G):
    """Augmented Forman-Ricci on every edge. Returns (dict edge->F, seconds)."""
    t0 = time.perf_counter()
    fr = FormanRicci(G.copy(), verbose="ERROR")
    fr.compute_ricci_curvature()
    F = {tuple(sorted((u, v))): d["formanCurvature"]
         for u, v, d in fr.G.edges(data=True)}
    return F, time.perf_counter() - t0


def _edge_key(u, v):
    return tuple(sorted((u, v)))


def _lazy_measure(G, node, alpha):
    neighbours = list(G.neighbors(node))
    support = [node] + neighbours
    mass = np.zeros(len(support), dtype=float)
    mass[0] = alpha
    if neighbours:
        mass[1:] = (1.0 - alpha) / len(neighbours)
    else:
        mass[0] = 1.0
    return support, mass


def _support_distances(G, sources, weight=None):
    """Shortest-path cache sufficient for adjacent-edge neighbourhoods."""
    if weight is None:
        # For an edge (u,v), any x in N[u] and y in N[v] are at most three
        # hops apart via x-u-v-y.
        return {
            source: dict(nx.single_source_shortest_path_length(G, source, cutoff=3))
            for source in sources
        }
    return {
        source: dict(nx.single_source_dijkstra_path_length(G, source, weight=weight))
        for source in sources
    }


def ollivier_subset(G, edges, alpha=0.5, weight=None):
    """Exact Ollivier--Ricci curvature on a requested edge subset.

    Parameters
    ----------
    weight:
        Optional NetworkX edge attribute used as the ground metric.  ``None``
        gives the unweighted hop metric used by the rebuilt routing study.
    """
    t0 = time.perf_counter()
    requested = [_edge_key(*edge) for edge in edges]
    if not requested:
        return {}, 0.0
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must lie in [0, 1]")

    measures = {}
    support_nodes = set()
    for u, v in requested:
        if not G.has_edge(u, v):
            raise ValueError(f"requested non-edge {(u, v)}")
        for node in (u, v):
            if node not in measures:
                measures[node] = _lazy_measure(G, node, alpha)
                support_nodes.update(measures[node][0])
    distances = _support_distances(G, support_nodes, weight=weight)

    K = {}
    for u, v in requested:
        support_u, mass_u = measures[u]
        support_v, mass_v = measures[v]
        ground = np.empty((len(support_u), len(support_v)), dtype=float)
        for i, source in enumerate(support_u):
            for j, target in enumerate(support_v):
                ground[i, j] = float(distances[source][target])
        edge_length = float(distances[u][v])
        wasserstein = float(ot.emd2(mass_u, mass_v, ground))
        K[(u, v)] = 1.0 - wasserstein / edge_length
    return K, time.perf_counter() - t0


def ollivier_all(G, alpha=0.5, weight=None):
    """Exact Ollivier-Ricci on ALL edges (the 'Pure ORC' baseline)."""
    return ollivier_subset(G, G.edges(), alpha=alpha, weight=weight)


def hybrid_curvature(G, frc_threshold=0.0, frc_percentile=None, alpha=0.5):
    """FRC pre-filter -> exact ORC only on flagged (F < threshold) edges.

    Returns kappa dict (0 on unflagged/resilient edges), and a timing/report
    dict. This is the paper's hybrid pipeline.
    """
    F, t_frc = forman_all(G)
    if frc_percentile is not None:
        import numpy as _np
        cut = _np.percentile(list(F.values()), frc_percentile)
        flagged = [e for e, f in F.items() if f <= cut]
    else:
        flagged = [e for e, f in F.items() if f < frc_threshold]
    K, t_orc = ollivier_subset(G, flagged, alpha=alpha)
    kappa = {e: 0.0 for e in F}
    for e, k in K.items():
        kappa[e] = k
    rep = dict(n_edges=G.number_of_edges(), n_flagged=len(flagged),
               t_frc=t_frc, t_orc=t_orc, t_total=t_frc + t_orc,
               frac_flagged=len(flagged) / max(1, G.number_of_edges()))
    return kappa, rep
