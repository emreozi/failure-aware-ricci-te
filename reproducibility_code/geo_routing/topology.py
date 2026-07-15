"""Topology and demand generators for the routing experiments.

Each generator returns an undirected networkx.Graph; every edge carries:
  - 'cost'     : linear routing cost c_ij (>0)
  - 'capacity' : nominal link capacity u_ij (>0), used ONLY for reporting
                 utilisation / drops (NOT as a hard optimisation bound).
All randomness is driven by an explicit integer `seed` (reproducible).
"""
import numpy as np
import networkx as nx
from dataclasses import dataclass


@dataclass(frozen=True)
class ODDemand:
    """One origin--destination commodity with a non-negative traffic volume."""

    source: int
    target: int
    volume: float


def _annotate(G, rng, cap_lo=8.0, cap_hi=12.0):
    for u, v in G.edges():
        G[u][v]["cost"] = 1.0
        G[u][v]["capacity"] = float(rng.uniform(cap_lo, cap_hi))
    return G


def ba_network(n=1000, m=3, seed=0):
    rng = np.random.default_rng(seed)
    G = nx.barabasi_albert_graph(n, m, seed=seed)
    return _annotate(G, rng)


def er_network(n=1000, p=None, seed=0, avg_deg=6):
    rng = np.random.default_rng(seed)
    if p is None:
        p = avg_deg / (n - 1)
    G = nx.gnp_random_graph(n, p, seed=seed)
    if not nx.is_connected(G):
        cc = max(nx.connected_components(G), key=len)
        G = nx.convert_node_labels_to_integers(G.subgraph(cc).copy())
    return _annotate(G, rng)


def aws_twin(n_regions=18, region_size=180, n_core=12, seed=0, p_intra=0.14, leaves_per_region=120, homing=2):
    """Hierarchical 'AWS-like' core-edge digital twin.

    * n_core Tier-1 routers -> ring + long chords; the chords are inter-hub
      *bridges* (negative Ollivier-Ricci curvature).
    * n_regions dense ER clusters (region_size each, p_intra) -> positive
      internal curvature; each attaches to one core router via 2 uplinks.
    """
    rng = np.random.default_rng(seed)
    G = nx.Graph()
    core = list(range(n_core))
    G.add_nodes_from(core)
    for i in range(n_core):
        G.add_edge(core[i], core[(i + 1) % n_core])
    for i in range(0, n_core, 2):
        G.add_edge(core[i], core[(i + n_core // 2) % n_core])

    next_id = n_core
    region_hubs = []
    for r in range(n_regions):
        nodes = list(range(next_id, next_id + region_size))
        next_id += region_size
        H = nx.gnp_random_graph(region_size, p_intra, seed=int(rng.integers(1e9)))
        if not nx.is_connected(H):
            comps = list(nx.connected_components(H))
            for k in range(len(comps) - 1):
                H.add_edge(next(iter(comps[k])), next(iter(comps[k + 1])))
        H = nx.relabel_nodes(H, {i: nodes[i] for i in range(region_size)})
        G.add_edges_from(H.edges())
        # attach low-degree leaf/edge servers (resilient periphery, F>=0)
        leaves=list(range(next_id, next_id+leaves_per_region)); next_id+=leaves_per_region
        for lf in leaves:
            G.add_edge(lf, int(rng.choice(nodes)))
        # multi-home each region to `homing` distinct core routers (2 uplinks each)
        chosen = list(rng.choice(n_core, size=min(homing, n_core), replace=False))
        for cc in chosen:
            for a in rng.choice(nodes, size=2, replace=False):
                G.add_edge(core[int(cc)], int(a))
        region_hubs.append((core[chosen[0]], nodes+leaves))

    _annotate(G, rng)
    for i in range(n_core):
        for j in range(n_core):
            if G.has_edge(core[i], core[j]):
                G[core[i]][core[j]]["capacity"] *= 6.0
    G.graph["core"] = core
    G.graph["region_hubs"] = region_hubs
    return G


def make_od_demands(G, n_pairs=40, level=1.0, seed=0, cross_region=True):
    """Generate OD commodities without collapsing their identities.

    Keeping commodities separate is essential for valid traffic-engineering and
    post-failure delivery measurements.  The legacy code aggregated all OD pairs
    into one net-supply vector, which permits unrelated commodities to cancel at
    intermediate terminals.
    """
    rng = np.random.default_rng(seed)
    nodes = list(G.nodes())
    region_hubs = G.graph.get("region_hubs")
    demands = []
    for _ in range(n_pairs):
        if cross_region and region_hubs and len(region_hubs) >= 2:
            ri, rj = rng.choice(len(region_hubs), size=2, replace=False)
            s = int(rng.choice(region_hubs[ri][1]))
            t = int(rng.choice(region_hubs[rj][1]))
        else:
            s, t = (int(x) for x in rng.choice(nodes, size=2, replace=False))
        d = float(rng.uniform(0.5, 1.5)) * level
        demands.append(ODDemand(source=s, target=t, volume=d))
    return demands


def make_demand(G, n_pairs=40, level=1.0, seed=0, cross_region=True):
    """Legacy aggregate net-supply vector.

    New experiments must use :func:`make_od_demands`.  This wrapper is retained
    only so that the archived Physica A experiments remain reproducible.
    """
    b = {n: 0.0 for n in G.nodes()}
    for demand in make_od_demands(
        G,
        n_pairs=n_pairs,
        level=level,
        seed=seed,
        cross_region=cross_region,
    ):
        b[demand.source] += demand.volume
        b[demand.target] -= demand.volume
    return b
