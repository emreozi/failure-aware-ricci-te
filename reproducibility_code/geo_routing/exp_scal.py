"""Scalability experiment on modular core-edge twins of increasing size."""
import json, numpy as np
from geo_routing import topology as T, curvature as C, optimize as O

def agg(x): a=np.array(x,float); return (round(float(a.mean()),3), round(float(a.std()),3))

CFG=[  # label, n_regions, region_size, leaves, n_core, seeds
 ("~550",  6,40, 50, 8,[1,2,3]),
 ("~1200", 8,60, 90,10,[1,2,3]),
 ("~2650",12,80,140,12,[1,2]),
]
rows=[]
for label,nr,rs,lv,nc,seeds in CFG:
    p_intra=min(0.45, 15.0/rs)
    M={'N':[],'E':[],'negfrac':[],'torc':[],
       'lp_u':[],'nlp_u':[],'lp_d':[],'nlp_d':[],'lp_neg':[],'nlp_neg':[],'lp_pos':[],'nlp_pos':[]}
    for sd in seeds:
        G=T.aws_twin(n_regions=nr,region_size=rs,n_core=nc,seed=sd,p_intra=p_intra,leaves_per_region=lv)
        K,torc=C.ollivier_all(G)
        kappa=K
        M['N'].append(G.number_of_nodes()); M['E'].append(G.number_of_edges())
        M['negfrac'].append(float(np.mean([1.0 if k<0 else 0.0 for k in K.values()]))); M['torc'].append(torc)
        b=T.make_demand(G,n_pairs=max(40,G.number_of_nodes()//30),level=3.0,seed=sd,cross_region=True)
        b=calib=O.solve(G,b,kappa,0.0); s=112.0/max(calib['max_util'],1e-6)
        b=T.make_demand(G,n_pairs=max(40,G.number_of_nodes()//30),level=3.0*s,seed=sd,cross_region=True)
        rl=O.solve(G,b,kappa,0.0); rn=O.solve(G,b,kappa,20.0)
        M['lp_u'].append(rl['max_util']);M['nlp_u'].append(rn['max_util'])
        M['lp_d'].append(rl['drop_rate']);M['nlp_d'].append(rn['drop_rate'])
        M['lp_neg'].append(rl['neg_flow_share']);M['nlp_neg'].append(rn['neg_flow_share'])
        M['lp_pos'].append(rl['pos_flow_share']);M['nlp_pos'].append(rn['pos_flow_share'])
    row=dict(label=label,N=int(np.mean(M['N'])),E=int(np.mean(M['E'])),
             negfrac=round(float(np.mean(M['negfrac'])),2),torc=round(float(np.mean(M['torc'])),1),
             lp_u=agg(M['lp_u'])[0],nlp_u=agg(M['nlp_u'])[0],lp_d=agg(M['lp_d'])[0],nlp_d=agg(M['nlp_d'])[0],
             lp_neg=agg(M['lp_neg'])[0],nlp_neg=agg(M['nlp_neg'])[0],lp_pos=agg(M['lp_pos'])[0],nlp_pos=agg(M['nlp_pos'])[0],
             seeds=len(seeds))
    rows.append(row)
    print("%-6s N=%d E=%d negf=%.2f ORC=%.1fs | LPu=%.1f NLPu=%.1f LPd=%.2f NLPd=%.2f pos %.1f->%.1f"%(
        label,row['N'],row['E'],row['negfrac'],row['torc'],row['lp_u'],row['nlp_u'],row['lp_d'],row['nlp_d'],row['lp_pos'],row['nlp_pos']),flush=True)
json.dump(rows,open("results_scal.json","w"),indent=2)
print("saved results_scal.json")
