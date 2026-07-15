"""Regenerate fig3: illustrative modular core-edge twin schematic, edges colored
by exact Ollivier-Ricci curvature (alpha=0.5). Generic (de-branded) labels."""
import itertools, os, numpy as np, networkx as nx, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.lines import Line2D
from GraphRicciCurvature.OllivierRicci import OllivierRicci

INK="#22303f"; STEEL="#3b6ea5"; AMBER="#e0912f"; CR="#b5324a"; TE="#0f8a8a"; TEDK="#0a6464"
CMAP=plt.get_cmap("RdYlGn"); NORM=Normalize(vmin=-0.55, vmax=0.55)

pos={"C1":(-3.2,1.30),"C2":(0.0,1.98),"C3":(3.2,1.30),
     "Reg-A":(-4.0,-0.45),"Reg-B":(-1.75,-0.70),"Reg-C":(1.75,-0.70),"Reg-D":(4.0,-0.45),
     "wa":(-3.05,-1.75),"ea":(3.05,-1.75),"T":(0.0,-1.30)}
core=["C1","C2","C3"]; regional=["Reg-A","Reg-B","Reg-C","Reg-D"]; az=["wa","ea"]; relay=["T"]
DISP={"C1":"Core\n1","C2":"Core\n2","C3":"Core\n3"}
G=nx.Graph()
G.add_edges_from(itertools.combinations(["C1","Reg-A","Reg-B","wa"],2))
G.add_edges_from(itertools.combinations(["C3","Reg-C","Reg-D","ea"],2))
congested=("C1","C2"); secondary=("C2","C3")
G.add_edge(*congested); G.add_edge(*secondary)
G.add_edges_from([("Reg-B","Reg-D"),("Reg-B","T"),("Reg-D","T"),("T","Reg-A"),("T","Reg-C")])
orc=OllivierRicci(G,alpha=0.5,verbose="ERROR"); orc.compute_ricci_curvature()
K={tuple(sorted((u,v))):orc.G[u][v]["ricciCurvature"] for u,v in orc.G.edges()}
kget=lambda u,v:K[tuple(sorted((u,v)))]

fig,ax=plt.subplots(figsize=(10.6,6.3))
ax.add_patch(FancyBboxPatch((-4.85,0.55),9.7,1.95,boxstyle="round,pad=0.1,rounding_size=0.45",
             fc="none",ec=CR,lw=1.3,ls=(0,(6,4)),alpha=0.85,zorder=0))
ax.add_patch(FancyBboxPatch((-5.0,-2.45),10.0,2.55,boxstyle="round,pad=0.1,rounding_size=0.45",
             fc="none",ec=TEDK,lw=1.3,ls=(0,(6,4)),alpha=0.85,zorder=0))
ax.text(-4.7,2.28,"Tier-1 Core Zone ($\\kappa<0$)",ha="left",fontsize=10.5,color="#a93226",style="italic")
ax.text(-4.85,-2.22,"Regional Transit Mesh ($\\kappa>0$)",ha="left",fontsize=10.5,color="#0a6464",style="italic")
for u,v in G.edges():
    if tuple(sorted((u,v)))==tuple(sorted(congested)): continue
    ax.plot([pos[u][0],pos[v][0]],[pos[u][1],pos[v][1]],color=CMAP(NORM(kget(u,v))),lw=2.4,solid_capstyle="round",zorder=2)
x0,y0=pos["C1"]; x1,y1=pos["C2"]
ax.plot([x0,x1],[y0,y1],color=CR,lw=3.2,ls=(0,(5,3)),zorder=3)
mx,my=(x0+x1)/2,(y0+y1)/2
ax.add_patch(FancyBboxPatch((mx-1.15,my+0.17),2.30,0.42,boxstyle="round,pad=0.04",fc="white",ec=CR,lw=1.2,zorder=6))
ax.text(mx,my+0.38,"Congested link (114.4%, LP)",ha="center",va="center",fontsize=8.2,color=CR,fontweight="bold",zorder=7)
ax.annotate("",xy=(mx,my+0.02),xytext=(mx,my+0.17),arrowprops=dict(arrowstyle="-",color=CR,lw=0.8),zorder=6)
for u,v in [("C1","Reg-B"),("Reg-B","Reg-D"),("Reg-D","C3"),("C3","C2")]:
    ax.add_patch(FancyArrowPatch(pos[u],pos[v],arrowstyle="-|>",mutation_scale=18,lw=3.6,color=TE,alpha=0.9,shrinkA=16,shrinkB=16,zorder=4,connectionstyle="arc3,rad=0.07"))
ax.annotate("Curvature-aware detour\n(high-$\\kappa$ regional mesh)",xy=(1.1,-0.52),
            xytext=(1.1,0.62),ha="center",fontsize=9.5,color=TEDK,fontweight="bold",
            arrowprops=dict(arrowstyle="-|>",color=TEDK,lw=1.2,connectionstyle="arc3,rad=0.0"),zorder=7)
for n in core:
    ax.scatter(*pos[n],s=1500,c=[INK],edgecolors="white",linewidths=2.0,zorder=8)
    ax.text(*pos[n],DISP[n],ha="center",va="center",color="white",fontsize=8.4,fontweight="bold",zorder=9)
for n in regional:
    ax.scatter(*pos[n],s=520,c=[STEEL],edgecolors="white",linewidths=1.5,zorder=8)
    ax.text(pos[n][0],pos[n][1]-0.40,n,ha="center",va="top",color=STEEL,fontsize=8.6,fontweight="bold",zorder=9)
for n in relay:
    ax.scatter(*pos[n],s=300,c=[AMBER],edgecolors="white",linewidths=1.3,zorder=8)
    ax.text(pos[n][0],pos[n][1]-0.32,"IXP",ha="center",va="center",color="#9a6212",fontsize=7.6,fontweight="bold",zorder=9)
for n in az:
    ax.scatter(*pos[n],s=120,c=["#aeb8c2"],edgecolors="white",linewidths=0.9,zorder=8)
sm=ScalarMappable(norm=NORM,cmap=CMAP); sm.set_array([])
cb=fig.colorbar(sm,ax=ax,fraction=0.034,pad=0.01); cb.set_label("Ollivier-Ricci curvature  $\\kappa$",fontsize=10); cb.outline.set_linewidth(0.6)
leg=[Line2D([0],[0],color=CR,lw=3,ls=(0,(5,3)),label="Congested Tier-1 link (LP)"),
     Line2D([0],[0],color=TE,lw=4,label="Curvature-aware redistributed flow"),
     Line2D([0],[0],marker="o",color="w",markerfacecolor=INK,markersize=11,label="Tier-1 core"),
     Line2D([0],[0],marker="o",color="w",markerfacecolor=STEEL,markersize=9,label="Regional aggregator"),
     Line2D([0],[0],marker="o",color="w",markerfacecolor=AMBER,markersize=8,label="Transit relay (IXP)"),
     Line2D([0],[0],marker="o",color="w",markerfacecolor="#aeb8c2",markersize=7,label="Edge server")]
ax.legend(handles=leg,loc="upper center",frameon=False,fontsize=8.6,bbox_to_anchor=(0.46,-0.012),ncol=3,columnspacing=1.6,handlelength=1.9,handletextpad=0.6)
ax.set_xlim(-5.2,5.2); ax.set_ylim(-2.7,2.65); ax.set_aspect("equal"); ax.axis("off")
fig.subplots_adjust(bottom=0.13,top=0.99,left=0.01,right=0.99)
os.makedirs("figures", exist_ok=True)
fig.savefig("figures/fig3_aws.pdf"); fig.savefig("figures/fig3_aws.png",dpi=150)
print("fig3 regenerated; core=%.3f secondary=%.3f RegB-RegD=%.3f"%(kget(*congested),kget(*secondary),kget("Reg-B","Reg-D")))
