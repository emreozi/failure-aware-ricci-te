import json, os, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
CR="#b5324a"; TE="#0f8a8a"; ST="#6b7b8c"; GR="#9aa7b2"
plt.rcParams.update({"font.size":11,"axes.spines.top":False,"axes.spines.right":False,"savefig.bbox":"tight"})
d=json.load(open("results_baseline.json"))["modular"]
labels=["LP","Uniform-Q","Degree-Q","Curvature\n(ours)","Combo"]
keys=["lp","unif","deg","curv","combo"]
util=[d[k]["util"][0] for k in keys]; br=[d[k]["neg"][0] for k in keys]
cols=[CR,ST,ST,TE,ST]
fig,(a,b)=plt.subplots(1,2,figsize=(10.4,4.2))
a.bar(range(5),util,color=cols); a.axhline(100,color=GR,ls=":",lw=1)
a.set_xticks(range(5)); a.set_xticklabels(labels,fontsize=9); a.set_ylabel("Max link utilization (%)")
a.set_title("Peak utilization (lower = better)",fontsize=11)
for i,v in enumerate(util): a.annotate(f"{v:.0f}",(i,v),textcoords="offset points",xytext=(0,3),ha="center",fontsize=8.5)
b.bar(range(5),br,color=cols)
b.set_xticks(range(5)); b.set_xticklabels(labels,fontsize=9); b.set_ylabel(r"Flow on negatively curved bridges (%)")
b.set_title("Structural resilience (lower = better)",fontsize=11)
for i,v in enumerate(br): b.annotate(f"{v:.1f}",(i,v),textcoords="offset points",xytext=(0,3),ha="center",fontsize=8.5)
b.set_ylim(0,max(br)*1.25)
os.makedirs("figures",exist_ok=True)
fig.savefig("figures/fig7_baseline.pdf"); fig.savefig("figures/fig7_baseline.png",dpi=150)
print("Figure_7 üretildi; util",util,"br",br)
