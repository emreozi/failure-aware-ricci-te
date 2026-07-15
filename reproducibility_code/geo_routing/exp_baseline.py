"""Curvature vs curvature-agnostic penalties at MATCHED latency budget.
Shows: agnostic penalties win on peak utilization; only curvature reduces
flow on structurally-critical (negatively curved) bridges."""
import json, numpy as np
from geo_routing import topology as T, curvature as C, optimize as O
LAMS=[0.3,1,3,10,30,100,300]
METH=['lp','unif','deg','curv','combo']
def matched(G,b,k,mode,target):
    best=None
    for lam in LAMS:
        r=O.solve(G,b,k,lambda_base=lam,mode=mode)
        if not np.isfinite(r['max_util']): continue
        d=abs(r['avg_path_len']-target)
        if best is None or d<best[0]: best=(d,r)
    return best[1]
def run(makeG,cross,seeds):
    acc={m:{x:[] for x in ['util','drop','path','neg','strong']} for m in METH}
    for sd in seeds:
        G=makeG(sd); k,_=C.hybrid_curvature(G,frc_threshold=0.0)
        b=T.make_demand(G,n_pairs=60,level=3.0,seed=sd,cross_region=cross)
        lp=O.solve(G,b,k,0.0,mode='curv'); s=115.0/lp['max_util']
        b=T.make_demand(G,n_pairs=60,level=3.0*s,seed=sd,cross_region=cross)
        lp=O.solve(G,b,k,0.0,mode='curv'); tg=lp['avg_path_len']*1.12
        for m in METH:
            r=lp if m=='lp' else matched(G,b,k,m,tg)
            acc[m]['util'].append(r['max_util']); acc[m]['drop'].append(r['drop_rate'])
            acc[m]['path'].append(r['avg_path_len']); acc[m]['neg'].append(r['neg_flow_share'])
            acc[m]['strong'].append(r['strong_neg_flow_share'])
    return {m:{x:(round(float(np.mean(v)),2),round(float(np.std(v)),2)) for x,v in d.items()} for m,d in acc.items()}
res={'modular':run(lambda sd:T.aws_twin(n_regions=8,region_size=60,n_core=10,seed=sd,p_intra=0.30,leaves_per_region=90,homing=2),True,[1,2,3]),
     'ba':run(lambda sd:T.ba_network(800,3,sd),False,[1,2,3])}
json.dump(res,open("results_baseline.json","w"),indent=2)
for g in res:
    print("\n=== %s ==="%g)
    print("%-6s %8s %7s %7s %8s"%("mode","maxUtil","drop%","path","brFlow%"))
    for m in METH:
        d=res[g][m]; print("%-6s %8.1f %7.2f %7.2f %8.1f"%(m,d['util'][0],d['drop'][0],d['path'][0],d['neg'][0]))
print("\nsaved results_baseline.json")
