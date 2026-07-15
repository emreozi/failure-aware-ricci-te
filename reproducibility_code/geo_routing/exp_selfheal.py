"""Discrete Ricci Flow self-healing experiment (validates Assumption 2 / Thm 3).
w_ij(t+1) = w_ij(t)*(1 - eta*kappa_ij(t)); recompute exact ORC each epoch.
Track mean |kappa| on initially-negative edges, |E_crit|, max|kappa|."""
import json, numpy as np, networkx as nx
from geo_routing import topology as T, curvature as C

def orc_weighted(G):
    kappa,_=C.ollivier_all(G, alpha=0.5, weight="weight")
    return kappa

def run(seed=1, eta=0.3, epochs=8):
    G=T.aws_twin(n_regions=8,region_size=60,n_core=10,seed=seed,p_intra=0.30,leaves_per_region=90,homing=2)
    for u,v in G.edges(): G[u][v]["weight"]=1.0
    k0=orc_weighted(G)
    S=[e for e,k in k0.items() if k<0]            # initial bottleneck set
    E=G.number_of_edges()
    traj=[]
    for t in range(epochs):
        k=orc_weighted(G)
        meanabs=float(np.mean([abs(k[e]) for e in S])) if S else 0.0
        ncrit=int(sum(1 for e in k.values() if e<0))
        maxabs=float(max(abs(v) for v in k.values()))
        traj.append(dict(t=t, mean_abs_kappa_S=round(meanabs,4), n_crit=ncrit,
                         crit_frac=round(ncrit/E,3), max_abs_kappa=round(maxabs,4)))
        # update weights
        for (u,v) in G.edges():
            e=tuple(sorted((u,v)))
            G[u][v]["weight"]=max(1e-6, G[u][v]["weight"]*(1-eta*k[e]))
    return dict(seed=seed,eta=eta,E=E,S_size=len(S),traj=traj)

if __name__=="__main__":
    out=run()
    for r in out["traj"]:
        print("t=%d mean|k|_S=%.4f  |Ecrit|=%d (%.1f%%)  max|k|=%.3f"%(
            r["t"],r["mean_abs_kappa_S"],r["n_crit"],100*r["crit_frac"],r["max_abs_kappa"]))
    json.dump(out,open("results_selfheal.json","w"),indent=2)
    print("saved results_selfheal.json  (initial bottleneck edges S=%d of E=%d)"%(out["S_size"],out["E"]))
