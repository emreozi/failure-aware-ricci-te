"""Node-adaptive curvature-penalised min-cost flow QP, solved with OSQP.

min_x  sum_a c_a x_a + pen_a x_a^2
s.t.   A x = b            (flow conservation, net supply/demand b)
       0 <= x <= xcap     (a large box; NOT the reporting capacity)

pen_a = lambda_ij * max(0, -kappa_ij),  lambda_ij = lambda_base*(1+log(d_i d_j/d_avg^2))
(lambda clamped at >=0 for convexity). lambda_base = 0  ==>  linear LP baseline.

Utilisation and packet drop are measured AFTERWARDS against the nominal edge
capacity, so 'drop' is an emergent overflow quantity, never enforced to zero.
"""
import numpy as np
import scipy.sparse as sp
import osqp
import math


def _arcs(G):
    arcs = []
    for u, v in G.edges():
        arcs.append((u, v)); arcs.append((v, u))
    return arcs


def solve(G, b, kappa, lambda_base=10.0, verbose=False, mode='curv'):
    nodes = list(G.nodes())
    idx = {n: i for i, n in enumerate(nodes)}
    arcs = _arcs(G)
    M = len(arcs); N = len(nodes)
    deg = dict(G.degree())
    d_avg = 2.0 * G.number_of_edges() / N

    c = np.ones(M)
    pen = np.zeros(M)
    for a, (u, v) in enumerate(arcs):
        c[a] = G[u][v]["cost"]
        e = tuple(sorted((u, v)))
        k = kappa.get(e, 0.0)
        lam = max(0.0, lambda_base * (1.0 + math.log((deg[u] * deg[v]) / (d_avg ** 2))))
        if mode == 'curv':          # ours: penalise only negative-curvature edges, scaled by |kappa|
            if k < 0: pen[a] = lam * (-k)
        elif mode == 'deg':         # curvature-blind: node-adaptive (degree) quadratic on ALL edges
            pen[a] = lam
        elif mode == 'unif':        # curvature-blind: uniform quadratic congestion on ALL edges
            pen[a] = lambda_base
        elif mode == 'combo':       # uniform congestion + curvature bonus on negative edges
            pen[a] = lambda_base * (1.0 + 3.0*max(0.0,-k))
        else:
            raise ValueError(mode)

    # incidence A (N x M): +1 at tail, -1 at head
    rows, cols, vals = [], [], []
    for a, (u, v) in enumerate(arcs):
        rows += [idx[u], idx[v]]; cols += [a, a]; vals += [1.0, -1.0]
    A = sp.csc_matrix((vals, (rows, cols)), shape=(N, M))

    bvec = np.array([b[n] for n in nodes], dtype=float)
    T = 0.5 * np.abs(bvec).sum()                 # total end-to-end demand
    xcap = max(1.0, T)                           # generous per-arc box

    P = sp.diags(2.0 * pen).tocsc()
    q = c
    C = sp.vstack([A, sp.identity(M, format="csc")], format="csc")
    l = np.concatenate([bvec, np.zeros(M)])
    u = np.concatenate([bvec, np.full(M, xcap)])

    prob = osqp.OSQP()
    prob.setup(P=P, q=q, A=C, l=l, u=u, verbose=verbose,
               eps_abs=1e-5, eps_rel=1e-5, max_iter=20000, polish=True)
    res = prob.solve()
    x = np.maximum(res.x, 0.0)

    # aggregate undirected link loads
    load = {}
    for a, (u, v) in enumerate(arcs):
        e = tuple(sorted((u, v)))
        load[e] = load.get(e, 0.0) + x[a]

    caps = {tuple(sorted((u, v))): G[u][v]["capacity"] for u, v in G.edges()}
    util = {e: load[e] / caps[e] for e in load}
    total_load = sum(load.values()) or 1.0
    overflow = sum(max(0.0, load[e] - caps[e]) for e in load)
    neg_load = sum(load[e] for e in load if kappa.get(e, 0.0) < 0)
    strong_load = sum(load[e] for e in load if kappa.get(e, 0.0) < -0.1)
    pos_load = sum(load[e] for e in load if kappa.get(e, 0.0) > 0)

    return dict(
        status=res.info.status,
        solve_time=res.info.run_time,
        max_util=100.0 * max(util.values()),
        mean_util=100.0 * np.mean(list(util.values())),
        drop_rate=100.0 * overflow / total_load,
        neg_flow_share=100.0 * neg_load / total_load,
        strong_neg_flow_share=100.0 * strong_load / total_load,
        pos_flow_share=100.0 * pos_load / total_load,
        avg_path_len=total_load / (T if T > 0 else 1.0),
        n_overloaded=sum(1 for e in util if util[e] > 1.0),
    )
