import json, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
CR="#b5324a"; TE="#0f8a8a"; ST="#3b6ea5"; INK="#22303f"; GR="#9aa7b2"
plt.rcParams.update({"font.size":11,"axes.spines.top":False,"axes.spines.right":False,
                     "figure.dpi":150,"savefig.bbox":"tight"})
D="figures/"; os.makedirs(D, exist_ok=True)

# ---------- fig4: sensitivity (results_exp1.json) ----------
e1=json.load(open("results_exp1.json"))
lams=["0.0","1.0","10.0","50.0","100.0"]; x=np.arange(len(lams))
maxu=[e1[l]["max_util"]["mean"] for l in lams]
pos =[e1[l]["pos_flow"]["mean"] for l in lams]
path=[e1[l]["path"]["mean"] for l in lams]
fig,ax=plt.subplots(figsize=(7.2,4.4)); ax2=ax.twinx(); ax2.spines["right"].set_visible(True)
ax.plot(x,maxu,"-o",color=CR,lw=2.2,label="Max link utilization (%)")
ax.plot(x,pos,"-s",color=TE,lw=2.2,label=r"Flow on $\kappa>0$ (%)")
ax2.plot(x,path,"--^",color=ST,lw=1.8,label="Avg. path length (hops)")
ax.set_xticks(x); ax.set_xticklabels([r"$0$",r"$1$",r"$10$",r"$50$",r"$100$"])
ax.set_xlabel(r"Base penalty multiplier $\lambda_{\mathrm{base}}$")
ax.set_ylabel("Percent (%)"); ax2.set_ylabel("Avg. path length (hops)",color=ST)
ax2.tick_params(axis="y",colors=ST)
l1,la1=ax.get_legend_handles_labels(); l2,la2=ax2.get_legend_handles_labels()
ax.legend(l1+l2,la1+la2,loc="lower center",bbox_to_anchor=(0.5,1.01),ncol=3,
          frameon=False,fontsize=9,columnspacing=1.3,handletextpad=0.5,handlelength=2.0)
fig.subplots_adjust(top=0.88)
fig.savefig(D+"fig4_sensitivity.pdf"); fig.savefig(D+"fig4_sensitivity.png"); plt.close(fig)

# ---------- fig5: scalability (results_scal.json) ----------
sc=json.load(open("results_scal.json"))
N=[r["N"] for r in sc]; lpu=[r["lp_u"] for r in sc]; nlpu=[r["nlp_u"] for r in sc]; torc=[r["torc"] for r in sc]
fig,(axL,axR)=plt.subplots(1,2,figsize=(10.6,4.3))
xi=np.arange(len(N)); w=0.36
axL.bar(xi-w/2,lpu,w,color=CR,label="LP ($L_1$)")
axL.bar(xi+w/2,nlpu,w,color=TE,label="Geometric NLP")
axL.axhline(100,color=GR,ls=":",lw=1)
axL.set_xticks(xi); axL.set_xticklabels([str(n) for n in N])
axL.set_xlabel("Network size $N$"); axL.set_ylabel("Max link utilization (%)")
axL.legend(frameon=False,fontsize=8.5,loc="lower center",bbox_to_anchor=(0.5,1.01),ncol=2,columnspacing=1.3,handletextpad=0.5)
axR.plot(N,torc,"-o",color=INK,lw=2.2)
axR.set_xscale("log"); axR.set_yscale("log")
axR.set_xlabel("Network size $N$"); axR.set_ylabel("Exact ORC time (s)")
for xv,yv in zip(N,torc): axR.annotate(f"{yv:.1f}s",(xv,yv),textcoords="offset points",xytext=(4,5),fontsize=8)

fig.subplots_adjust(top=0.86); fig.savefig(D+"fig5_macro.pdf"); fig.savefig(D+"fig5_macro.png"); plt.close(fig)

# ---------- fig6: large twin (results_bigtwin.json) ----------
bt=json.load(open("results_bigtwin.json"))
fig,(axL,axR)=plt.subplots(1,2,figsize=(10.6,4.3))
grp=["Max link\nutilization (%)","Overflow packet\nloss proxy (%)"]
lp=[bt["lp"]["u"],bt["lp"]["d"]]; nlp=[bt["nlp"]["u"],bt["nlp"]["d"]]
xi=np.arange(2); w=0.36
axL.bar(xi-w/2,lp,w,color=CR,label="LP ($L_1$)")
axL.bar(xi+w/2,nlp,w,color=TE,label="Geometric NLP")
axL.axhline(100,color=GR,ls=":",lw=1)
axL.set_xticks(xi); axL.set_xticklabels(grp); axL.set_ylabel("Value")
axL.legend(frameon=False,fontsize=8.5,loc="lower center",bbox_to_anchor=(0.5,1.01),ncol=2,columnspacing=1.3,handletextpad=0.5)
for i,(a,b) in enumerate(zip(lp,nlp)):
    axL.annotate(f"{a:.1f}",(i-w/2,a),textcoords="offset points",xytext=(0,3),ha="center",fontsize=8)
    axL.annotate(f"{b:.1f}",(i+w/2,b),textcoords="offset points",xytext=(0,3),ha="center",fontsize=8)
labels=["Exact ORC\n(all edges)","QP solve\n(LP)","QP solve\n(NLP)"]
vals=[bt["t_full_orc"],bt["lp"]["solve"],bt["nlp"]["solve"]]
axR.bar(np.arange(3),vals,color=[INK,CR,TE])
axR.set_xticks(np.arange(3)); axR.set_xticklabels(labels); axR.set_ylabel("Time (s)")
for i,v in enumerate(vals): axR.annotate(f"{v:.1f}s",(i,v),textcoords="offset points",xytext=(0,3),ha="center",fontsize=8)

fig.subplots_adjust(top=0.86); fig.savefig(D+"fig6_aws_perf.pdf"); fig.savefig(D+"fig6_aws_perf.png"); plt.close(fig)
print("regenerated fig4,fig5,fig6 from real results")
