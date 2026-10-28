"""Reddit collage (2400 x 3000 px). Run from anywhere: python3 reddit/collage.py"""
import json, os, sys
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "code"))
from figlib import *  # noqa: F401,F403
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

D = os.path.join(ROOT, "data")
R = json.load(open(os.path.join(D, "results.json"), encoding="utf-8"))
G = pd.read_csv(os.path.join(D, "games.csv"), keep_default_na=False, na_values=[""])
P = pd.read_csv(os.path.join(D, "places.csv"), keep_default_na=False, na_values=[""])
L = pd.read_csv(os.path.join(D, "links.csv"), keep_default_na=False, na_values=[""])
PAGE = json.load(open(os.path.join(D, "page.json"), encoding="utf-8"))
CPT = {c[1]: (c[2], c[3]) for c in PAGE["countries"]}
LU = L[L.used == 1].merge(P, on="place_id")
SH = {"United States of America": "USA", "United Kingdom": "UK"}
sh = lambda n: SH.get(n, n)
PAPER = "#F4ECDD"; INK = "#22201F"; MUT = "#6E655C"

fig = plt.figure(figsize=(12, 15), dpi=200, facecolor=PAPER)
fig.text(0.045, 0.968, "Set in New York, made in Tokyo?", fontproperties=DISP, fontsize=46, color=INK, va="top")
fig.text(0.045, 0.918, f"Where {R['meta']['games_total']:,} video games tied to real places are set, and where the studios that made them\nare based. From Wikidata and English Wikipedia: famous, Western and Japanese games dominate.",
         family=SER, fontsize=15, color=INK, va="top", linespacing=1.4)

# hero map
ax = fig.add_axes([0.0, 0.47, 1.0, 0.42])
draw_world(ax, default="#E3D8C5", edge=PAPER, lw=0.4)
pc = LU[LU.kind.isin(["local", "region", "historical"])].groupby(["label", "lon", "lat"]).game_qid.nunique().reset_index(name="n")
sc = G[(G.set_on_earth == 1) & (G.made_how == "developer HQ")].groupby(["developer", "made_lon", "made_lat"]).qid.nunique().reset_index(name="n")
mx = max(pc.n.max(), sc.n.max())
games = G[(G.set_on_earth == 1) & G.made_country.notna()][["qid", "made_country"]]
fl = LU[LU.country.notna()][["game_qid", "country"]].drop_duplicates().merge(games, left_on="game_qid", right_on="qid")
pairs = fl[fl.country != fl.made_country].groupby(["made_country", "country"]).size().sort_values(ascending=False)
top = pairs.head(25); fm_ = top.max()
for (a, b), n in top[::-1].items():
    (x1, y1), (x2, y2) = CPT[a], CPT[b]
    xy = arc_xy(x1, y1, x2, y2, k=.2)
    ax.plot(xy[:, 0], xy[:, 1], color=FLOW, lw=0.6 + 7 * np.sqrt(n / fm_), alpha=.18 + .5 * np.sqrt(n / fm_), solid_capstyle="round", zorder=2)
x, y = proj(lonfix(sc.made_lon), sc.made_lat)
ax.scatter(x, y, s=4 + 700 * sc.n / mx, c=MADE, alpha=.75, lw=.5, edgecolors="white", zorder=3)
x, y = proj(lonfix(pc.lon), pc.lat)
ax.scatter(x, y, s=4 + 700 * pc.n / mx, c=SET, alpha=.75, lw=.5, edgecolors="white", zorder=4)
for lab, dx, dy, ha in [("New York City", -20, 34, "right"), ("London", -8, 30, "right"), ("Tokyo", 4, 30, "left"), ("Los Angeles", -14, -30, "right")]:
    r = pc[pc.label == lab].iloc[0]; xx, yy = proj(lonfix(r.lon), r.lat)
    ax.annotate(f"{lab} {int(r.n)}", (xx, yy), xytext=(dx, dy), textcoords="offset points", ha=ha, fontsize=12, family=MONO, color=INK,
                arrowprops=dict(arrowstyle="-", color=INK, lw=.7), zorder=6)
r = sc.sort_values("n").iloc[-1]
ax.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=SET, ms=11, label="where games are set"),
                   plt.Line2D([], [], marker="o", ls="", color=MADE, ms=11, label="where their developers are based"),
                   plt.Line2D([], [], color=FLOW, lw=4, label="studio country to setting country")],
          loc="lower left", bbox_to_anchor=(0.03, 0.02), frameon=False, prop={"family": MONO, "size": 12}, handletextpad=.5)

# routes bar chart
a = fig.add_axes([0.2, 0.25, 0.33, 0.19])
rows = pairs.head(8)[::-1]
a.barh([f"{sh(p)} to {sh(q)}" for p, q in rows.index], rows.values, color=FLOW, height=.68)
for i, v in enumerate(rows.values):
    a.text(v + 6, i, f"{v}", va="center", fontsize=12, family=MONO, color=MUT)
for s in ("top", "right", "bottom", "left"): a.spines[s].set_visible(False)
a.set_xticks([]); a.tick_params(length=0, labelsize=12.5); a.set_facecolor(PAPER)
for t in a.get_yticklabels(): t.set_family(MONO); t.set_color(INK)
fig.text(0.045, 0.452, "BUSIEST ROUTES FROM STUDIO TO SETTING (GAMES)", family=MONO, fontsize=11.5, color=MUT)

# big numbers
nums = [(f"{R['home']['usa']['share_home'] * 100:.0f}%  {R['home']['japan']['share_home'] * 100:.0f}%", SET,
         "of American and Japanese studios'\ngames are set at home. British\nstudios: " + f"{R['home']['uk']['share_home'] * 100:.0f}%; they set more games in\nthe USA ({R['flow']['United Kingdom>United States of America']}) than in the UK ({R['flow']['United Kingdom>United Kingdom']})."),
        (f"{R['made_share3'] * 100:.0f}%" if "made_share3" in R else "", MADE, "of games with a known maker\nwere made in the USA, Japan or the UK."),
        (f"0 of {R['spot']['egypt']['games']}", INK, "games set in Egypt (with a known\nmaker) were made in Egypt.")]
mc = R["made_count"]
share3 = (mc["United States of America"] + mc["Japan"] + mc["United Kingdom"]) / R["made_cov"]["known"]
nums[1] = (f"{share3 * 100:.0f}%", MADE, nums[1][2])
for (big, col, small), y in zip(nums, [0.455, 0.336, 0.259]):
    fig.text(0.6, y, big, fontproperties=DISP, fontsize=31, color=col, va="top")
    fig.text(0.6, y - 0.036, small, family=SER, fontsize=12.5, color=INK, va="top", linespacing=1.25)

# space strip
fig.text(0.045, 0.19, "AND OFF EARTH", family=MONO, fontsize=11.5, color=MUT)
bb = R["space"]["by_body"]
bodies = [("Moon", bb["Moon"], ("#D9D6D0", "#8F8B84"), .068), ("Mars", bb["Mars"], ("#E08A5A", "#8E3B1C"), .057), ("Titan", bb["Titan"], ("#E9B45A", "#9A6120"), .045),
          ("Venus", bb["Venus"], ("#F1DCA0", "#B8923F"), .036), ("Sun", bb["Sun"], ("#FFE08A", "#F08A1C"), .028), ("Mercury", bb["Mercury"], ("#BDB5AD", "#6D655E"), .024)]
sa = fig.add_axes([0.03, 0.07, 0.62, 0.11]); sa.set_xlim(0, 1); sa.set_ylim(0, 1); sa.axis("off"); sa.set_facecolor(PAPER)
xs = [0.08, 0.27, 0.44, 0.585, 0.72, 0.85]
for (nm, n, (c1, c2), r), xc in zip(bodies, xs):
    asp = 0.11 * 15 / (0.62 * 12)
    for k in range(14, 0, -1):
        t = k / 14
        col = np.array(plt.matplotlib.colors.to_rgb(c1)) * (1 - t) + np.array(plt.matplotlib.colors.to_rgb(c2)) * t
        sa.add_patch(plt.matplotlib.patches.Ellipse((xc - r * .25 * (1 - t), .66 + r / asp * .25 * (1 - t)), 2 * r * t, 2 * r * t / asp, color=col, lw=0))
    sa.text(xc, .66 - r / asp - .06, f"{nm}\n{n}", ha="center", va="top", fontsize=12.5, family=MONO, color=INK, linespacing=1.15)
ma = fig.add_axes([0.7, 0.075, 0.27, 0.075]); ma.set_facecolor(PAPER)
decs = ["1980", "1990", "2000", "2010", "2020"]
xx = np.arange(5)
ma.bar(xx - .2, [R["space"]["moon_by_decade"][d] for d in decs], .38, color=MOON)
ma.bar(xx + .2, [R["space"]["mars_by_decade"][d] for d in decs], .38, color=MARS)
ma.set_xticks(xx); ma.set_xticklabels(["80s", "90s", "00s", "10s", "20s"], family=MONO, fontsize=11)
for s in ("top", "right", "left"): ma.spines[s].set_visible(False)
ma.spines["bottom"].set_color(MUT); ma.set_yticks([]); ma.tick_params(length=0)
fig.text(0.7, 0.176, f"Moon {bb['Moon']} vs Mars {bb['Mars']},\nby release decade", family=MONO, fontsize=11.5, color=INK, va="top", linespacing=1.25)
fig.text(0.7, 0.172, "", family=MONO)

fig.text(0.045, 0.018, "Data: Wikidata (CC0) via QLever, and English Wikipedia's \"Video games set in\" categories (English Wikipedia contributors, CC BY-SA 4.0),\n"
         f"retrieved {R['meta']['retrieved']}. Countries: Natural Earth. Towns: GeoNames (CC BY 4.0). Made = developer headquarters as recorded today.\n"
         "Analysis and chart: Tristan Hotham, with Python and matplotlib. Interactive: maps.tristanhotham.com/games-on-the-map",
         family=MONO, fontsize=9.5, color=MUT, linespacing=1.45)
fig.savefig(os.path.join(HERE, "set_here_made_there.png"), facecolor=PAPER, dpi=200)
print("ok")
