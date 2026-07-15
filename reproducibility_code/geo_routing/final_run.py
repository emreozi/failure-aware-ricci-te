"""Final experiment suite on MODULAR core-edge topologies (curvature selective).
Saves results_exp{1,2,3}.json. Run experiments one at a time (CLI arg)."""
import json, sys, time, numpy as np
from geo_routing import topology as T, curvature as C, optimize as O

SEEDS=[1,2,3]
def agg(xs):
    a=np.array(xs,float); return dict(mean=round(float(a.mean()),3), std=round(float(a.std()),3))

def calibrate(G,b,kappa,target=110.0):
    """Scale demand so LP (lambda=0) max utilisation ~ target%."""
    r=O.solve(G,b,kappa,lambda_base=0.0)
    s=target/max(r['max_util'],1e-6)
    return {n:v*s for n,v in b.items()}

def med_twin(sd):
    return T.aws_twin(n_regions=8,region_size=60,n_core=10,seed=sd,p_intra=0.30,leaves_per_region=90)
def big_twin(sd):
    return T.aws_twin(n_regions=18,region_size=90,n_core=12,seed=sd,p_intra=0.20,leaves_per_region=190)

def exp1():
    lambdas=[0.0,1.0,10.0,50.0,100.0]
    D={lam:{'max_util':[],'drop':[],'strong_neg_flow':[],'pos_flow':[],'path':[]} for lam in lambdas}
    for sd in SEEDS:
        G=med_twin(sd); kappa,_=C.hybrid_curvature(G,frc_threshold=0.0)
        b=T.make_demand(G,n_pairs=60,level=3.0,seed=sd,cross_region=True)
        b=calibrate(G,b,kappa,target=115.0)
        for lam in lambdas:
            r=O.solve(G,b,kappa,lambda_base=lam)
            D[lam]['max_util'].append(r['max_util']); D[lam]['drop'].append(r['drop_rate'])
            D[lam]['strong_neg_flow'].append(r['strong_neg_flow_share'])
            D[lam]['pos_flow'].append(r['pos_flow_share']); D[lam]['path'].append(r['avg_path_len'])
        print("exp1 seed",sd,"done",flush=True)
    out={str(l):{k:agg(v) for k,v in d.items()} for l,d in D.items()}
    json.dump(out,open("results_exp1.json","w"),indent=2); print("exp1 saved")

def exp2():
    def run(gen,cross,label):
        R={'lp':{'max_util':[],'drop':[],'neg_flow':[],'pos_flow':[]},
           'nlp':{'max_util':[],'drop':[],'neg_flow':[],'pos_flow':[]},'neg_frac':[]}
        for sd in SEEDS:
            G=gen(sd); kappa,_=C.hybrid_curvature(G,frc_threshold=0.0)
            R['neg_frac'].append(float(np.mean([1.0 if k<0 else 0.0 for k in kappa.values()])))
            b=T.make_demand(G,n_pairs=70,level=3.0,seed=sd,cross_region=cross)
            b=calibrate(G,b,kappa,target=115.0)
            rl=O.solve(G,b,kappa,0.0); rn=O.solve(G,b,kappa,50.0)
            for tg,r in [('lp',rl),('nlp',rn)]:
                R[tg]['max_util'].append(r['max_util']); R[tg]['drop'].append(r['drop_rate'])
                R[tg]['neg_flow'].append(r['neg_flow_share']); R[tg]['pos_flow'].append(r['pos_flow_share'])
            print("exp2",label,"seed",sd,"done",flush=True)
        return {'lp':{k:agg(v) for k,v in R['lp'].items()},'nlp':{k:agg(v) for k,v in R['nlp'].items()},
                'neg_frac':agg(R['neg_frac'])}
    out={'modular':run(med_twin,True,'modular'),
         'ba':run(lambda sd:T.ba_network(1000,3,sd),False,'ba')}
    json.dump(out,open("results_exp2.json","w"),indent=2); print("exp2 saved")

def exp3():
    sd=1; G=big_twin(sd); N,E=G.number_of_nodes(),G.number_of_edges()
    print("big twin N=%d E=%d"%(N,E),flush=True)
    F,t_frc=C.forman_all(G)
    Kfull,t_full=C.ollivier_all(G)
    neg_full={e for e,k in Kfull.items() if k<0}
    print("full ORC %.1fs neg_frac=%.3f"%(t_full,len(neg_full)/E),flush=True)
    frontier=[]
    for pc in [5,10,20,40]:
        cut=np.percentile(list(F.values()),pc)
        flagged=[e for e,f in F.items() if f<=cut]
        K,t_orc=C.ollivier_subset(G,flagged)
        hit={e for e,k in K.items() if k<0}
        rec=len(hit&neg_full)/max(1,len(neg_full))
        frontier.append(dict(pct=pc,frac_flagged=round(len(flagged)/E,3),recall=round(rec,3),
                             t_orc=round(t_orc,2),speedup=round(t_full/max(t_orc+t_frc,1e-6),2)))
        print(" pc=%d frac=%.2f recall=%.2f orc=%.1fs speedup=%.1f"%(pc,len(flagged)/E,rec,t_orc,t_full/max(t_orc+t_frc,1e-6)),flush=True)
    kappa_full={e:(k if k<0 else 0.0) for e,k in Kfull.items()}
    b=T.make_demand(G,n_pairs=150,level=3.0,seed=sd,cross_region=True)
    b=calibrate(G,b,kappa_full,target=112.0)
    rl=O.solve(G,b,kappa_full,0.0); rn=O.solve(G,b,kappa_full,20.0)
    out=dict(N=N,E=E,t_frc=round(t_frc,3),t_full_orc=round(t_full,2),neg_frac=round(len(neg_full)/E,3),
             frontier=frontier,
             lp=dict(max_util=round(rl['max_util'],1),drop=round(rl['drop_rate'],3),neg_flow=round(rl['neg_flow_share'],1),solve=round(rl['solve_time'],2)),
             nlp=dict(max_util=round(rn['max_util'],1),drop=round(rn['drop_rate'],3),neg_flow=round(rn['neg_flow_share'],1),solve=round(rn['solve_time'],2)))
    json.dump(out,open("results_exp3.json","w"),indent=2)
    print("exp3 saved: LP maxutil=%.1f drop=%.2f | NLP maxutil=%.1f drop=%.2f"%(rl['max_util'],rl['drop_rate'],rn['max_util'],rn['drop_rate']))

if __name__=="__main__":
    {'1':exp1,'2':exp2,'3':exp3}[sys.argv[1]]()
