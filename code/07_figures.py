"""Step 7. Static figures: blog (release/blog/b_*.png, 1520 px wide), paper (release/paper/f_*.png) and header.png.
Run: python3 code/07_figures.py   (fonts from FONT_DIR, see code/figlib.py)
"""
import json, os, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, DATA
from figlib import *  # noqa: F401,F403
from matplotlib.collections import LineCollection
import matplotlib.pyplot as plt

R = json.load(open(os.path.join(DATA, "results.json"), encoding="utf-8"))
G = pd.read_csv(os.path.join(DATA, "games.csv"), keep_default_na=False, na_values=[""])
P = pd.read_csv(os.path.join(DATA, "places.csv"), keep_default_na=False, na_values=[""])
L = pd.read_csv(os.path.join(DATA, "links.csv"), keep_default_na=False, na_values=[""])
LU = L[L.used == 1].merge(P, on="place_id")
BLOG = os.path.join(ROOT, "release", "blog"); PAPER = os.path.join(ROOT, "release", "paper")
os.makedirs(BLOG, exist_ok=True); os.makedirs(PAPER, exist_ok=True)
NE_PTS = {}
import json as _j
for f in _j.load(open(os.path.join(DATA, "countries.json")))["features"]:
    pass
PAGE = json.load(open(os.path.join(DATA, "page.json"), encoding="utf-8"))
CPT = {c[1]: (c[2], c[3]) for c in PAGE["countries"]}
SHORT = {"United States of America": "USA", "United Kingdom": "UK"}
sh = lambda n: SHORT.get(n, n)


def save(fig, name, paper):
    if paper:
        fig.savefig(os.path.join(PAPER, "f_" + name + ".png"), dpi=200)
    else:
        fig.savefig(os.path.join(BLOG, "b_" + name + ".png"), dpi=100)
    plt.close(fig)


def place_counts():
    d = LU[LU.kind.isin(["local", "region", "historical"])].groupby(["label", "lon", "lat"]).game_qid.nunique().reset_index(name="n")
    return d


def studio_counts():
    e = G[(G.set_on_earth == 1) & (G.made_how == "developer HQ")]
    return e.groupby(["developer", "made_lon", "made_lat"]).qid.nunique().reset_index(name="n")


def fig_map(paper=False, w=15.2):
    k = 0.62 if paper else 1
    fig = plt.figure(figsize=(w, w * 0.47))
    ax = fig.add_axes([0, 0, 1, 1])
    draw_world(ax, default="#E6DED0", edge="#FBF8F2", lw=0.4)
    pc, sc = place_counts(), studio_counts()
    mx = max(pc.n.max(), sc.n.max())
    x, y = proj(lonfix(sc.made_lon), sc.made_lat)
    ax.scatter(x, y, s=(5 + 900 * sc.n / mx) * k * k * 1.4, c=MADE, alpha=.7, lw=.6, edgecolors="white", zorder=3)
    x, y = proj(lonfix(pc.lon), pc.lat)
    ax.scatter(x, y, s=(5 + 900 * pc.n / mx) * k * k * 1.4, c=SET, alpha=.72, lw=.6, edgecolors="white", zorder=4)
    for lab, dx, dy, ha in [("New York City", 0, 28, "center"), ("London", -6, 22, "right"), ("Tokyo", 8, 18, "left"), ("Los Angeles", -10, -22, "right")]:
        r = pc[pc.label == lab].iloc[0]
        xx, yy = proj(lonfix(r.lon), r.lat)
        ax.annotate(f"{lab}\n{int(r.n)} set", (xx, yy), xytext=(dx * k, dy * k), textcoords="offset points", ha=ha, fontsize=13 * k,
                    family=MONO, color=FG, linespacing=1.1, zorder=6)
    for lab, dx, dy, ha in [("Kyoto", 30, -32, "left")]:
        pass
    ax.legend(handles=[plt.Line2D([], [], marker="o", ls="", color=SET, ms=12 * k, label="where games are set (cities, regions, landmarks)"),
                       plt.Line2D([], [], marker="o", ls="", color=MADE, ms=12 * k, label="where the developer has its headquarters")],
              loc="lower left", bbox_to_anchor=(0.01, 0.04), frameon=False, fontsize=13 * k, handletextpad=.4)
    save(fig, "map", paper)


def fig_cities(paper=False, w=15.2):
    k = 0.62 if paper else 1
    rows = R["top_cities"][:15][::-1]
    fig, ax = plt.subplots(figsize=(w, w * 0.5))
    fig.subplots_adjust(left=.2, right=.96, top=.97, bottom=.11)
    ax.barh([r["name"] for r in rows], [r["games"] for r in rows], color=SET, height=.7)
    for i, r in enumerate(rows):
        ax.text(r["games"] + 5, i, f'{r["games"]:,}', va="center", fontsize=13 * k, color=MUTED)
    style_axes(ax); ax.tick_params(labelsize=14 * k); ax.set_xlabel("games set in the city", fontsize=13 * k, color=MUTED)
    save(fig, "cities", paper)


def fig_flows(paper=False, w=15.2):
    """Flow map: studio country to setting country, the 40 busiest routes."""
    k = 0.62 if paper else 1
    F = []
    games = G[(G.set_on_earth == 1) & G.made_country.notna()][["qid", "made_country"]]
    sc = LU[LU.country.notna()][["game_qid", "country"]].drop_duplicates().merge(games, left_on="game_qid", right_on="qid")
    pairs = sc[sc.country != sc.made_country].groupby(["made_country", "country"]).size().sort_values(ascending=False).head(40)
    fig = plt.figure(figsize=(w, w * 0.47)); ax = fig.add_axes([0, 0, 1, 1])
    draw_world(ax, default="#E9E2D6", edge="#FBF8F2", lw=0.4)
    mx = pairs.max()
    for (a, b), n in pairs[::-1].items():
        (x1, y1), (x2, y2) = CPT[a], CPT[b]
        xy = arc_xy(x1, y1, x2, y2, k=.2)
        ax.plot(xy[:, 0], xy[:, 1], color=FLOW, lw=(0.6 + 9 * np.sqrt(n / mx)) * k, alpha=.25 + .6 * np.sqrt(n / mx), solid_capstyle="round", zorder=3)
        ax.scatter(*xy[-1], s=(8 + 60 * n / mx) * k * k, color=SET, zorder=4, lw=0)
    lines = "\n".join(f"{sh(a)} to {sh(b)}: {n}" for (a, b), n in pairs.head(6).items())
    ax.text(0.02, 0.05, "Busiest routes, studio country\nto setting country (games)\n\n" + lines, transform=ax.transAxes, fontsize=13 * k, va="bottom",
            color=FG, linespacing=1.35, family=MONO, bbox=dict(boxstyle="round,pad=.5", fc=BG, ec=RULE, alpha=.92))
    save(fig, "flows", paper)


def fig_home(paper=False, w=15.2):
    k = 0.62 if paper else 1
    rows = R["home_share"][::-1]
    fig, ax = plt.subplots(figsize=(w, w * 0.45))
    fig.subplots_adjust(left=.2, right=.95, top=.97, bottom=.1)
    ax.barh([sh(r["country"]) for r in rows], [r["share_home"] * 100 for r in rows], color=MADE, height=.68)
    for i, r in enumerate(rows):
        ax.text(r["share_home"] * 100 + .8, i, f'{r["share_home"] * 100:.0f}%  ({r["home"]:,} of {r["games"]:,})', va="center", fontsize=12 * k, color=MUTED)
    style_axes(ax); ax.tick_params(labelsize=13 * k); ax.set_xlim(0, 80)
    ax.set_xlabel("share of the country's placed games that are set at home (%)", fontsize=12 * k, color=MUTED)
    save(fig, "home", paper)


def fig_trend(paper=False, w=15.2):
    k = 0.62 if paper else 1
    keys = ["New York City", "Tokyo", "London", "Los Angeles", "Moscow and the Soviet Union", "Egypt"]
    cols = ["#CF3F35", "#156B87", "#7B3F8C", "#C98A12", "#4F6D2F", "#8C5A3C"]
    decs = ["1980", "1990", "2000", "2010", "2020"]
    fig, ax = plt.subplots(figsize=(w, w * 0.5)); fig.subplots_adjust(left=.07, right=.8, top=.96, bottom=.1)
    ends = []
    for kk, c in zip(keys, cols):
        v = [R["share_series"][kk][d] * 100 for d in decs]
        ax.plot(range(5), v, color=c, lw=2.6 * k * 1.3, marker="o", ms=6 * k)
        ends.append([v[-1], kk, c])
    ends.sort()
    last = -9
    for v, kk, c in ends:
        y = max(v, last + 0.5); last = y
        ax.text(4.12, y, kk.replace("Moscow and the Soviet Union", "Moscow and the USSR"), color=c, fontsize=13 * k, va="center")
    ax.set_xticks(range(5)); ax.set_xticklabels([d + "s" for d in decs]); style_axes(ax, "y"); ax.tick_params(labelsize=13 * k)
    ax.set_ylabel("% of the decade's placed games", fontsize=12 * k, color=MUTED); ax.set_ylim(0, None)
    save(fig, "trend", paper)


def fig_space(paper=False, w=15.2):
    k = 0.62 if paper else 1
    decs = ["1970", "1980", "1990", "2000", "2010", "2020"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(w, w * 0.4), gridspec_kw={"width_ratios": [1.1, 1]})
    fig.subplots_adjust(left=.13, right=.97, top=.93, bottom=.13, wspace=.28)
    bb = R["space"]["by_body"]
    order = ["Outer space", "Moon", "Mars", "Titan", "Venus", "Jupiter's moons", "Sun", "Mercury"]
    cols = {"Outer space": SPACE, "Moon": MOON, "Mars": MARS}
    a1.barh(order[::-1], [bb.get(o, 0) for o in order[::-1]], color=[cols.get(o, "#B59A5A") for o in order[::-1]], height=.68)
    for i, o in enumerate(order[::-1]):
        a1.text(bb.get(o, 0) + 4, i, str(bb.get(o, 0)), va="center", fontsize=12 * k, color=MUTED)
    style_axes(a1); a1.tick_params(labelsize=13 * k); a1.set_title("games by body", fontsize=13 * k, color=MUTED, loc="left")
    x = np.arange(6)
    a2.bar(x - .2, [R["space"]["moon_by_decade"][d] for d in decs], .38, color=MOON, label="Moon")
    a2.bar(x + .2, [R["space"]["mars_by_decade"][d] for d in decs], .38, color=MARS, label="Mars")
    a2.set_xticks(x); a2.set_xticklabels(["to 1979", "1980s", "1990s", "2000s", "2010s", "2020s"], fontsize=11.5 * k)
    style_axes(a2, "y"); a2.tick_params(labelsize=12 * k); a2.legend(frameon=False, fontsize=12 * k)
    a2.set_title("Moon and Mars, by release decade", fontsize=13 * k, color=MUTED, loc="left")
    save(fig, "space", paper)


def fig_uk(paper=False, w=15.2):
    k = 0.62 if paper else 1
    a, b = R["uk"]["top_places"][:8][::-1], R["uk"]["made_set_where"][:8][::-1]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(w, w * 0.38)); fig.subplots_adjust(left=.14, right=.97, top=.9, bottom=.06, wspace=.45)
    a1.barh([x[0] for x in a], [x[1] for x in a], color=SET, height=.68)
    a2.barh([sh(x[0]) for x in b], [x[1] for x in b], color=MADE, height=.68)
    for ax, rows in ((a1, a), (a2, b)):
        for i, r in enumerate(rows):
            ax.text(r[1] + 3, i, str(r[1]), va="center", fontsize=12 * k, color=MUTED)
        style_axes(ax); ax.tick_params(labelsize=13 * k)
    a1.set_title("British places used as settings", fontsize=13 * k, color=MUTED, loc="left")
    a2.set_title("where British-made games are set", fontsize=13 * k, color=MUTED, loc="left")
    save(fig, "uk", paper)


def header():
    fig = plt.figure(figsize=(12, 6.3), dpi=100)
    ax = fig.add_axes([0.36, 0.01, 0.64, 0.6])
    draw_world(ax, default="#E6DED0", edge="#FBF8F2", lw=0.3)
    pc, sc = place_counts(), studio_counts()
    mx = max(pc.n.max(), sc.n.max())
    x, y = proj(lonfix(sc.made_lon), sc.made_lat); ax.scatter(x, y, s=3 + 300 * sc.n / mx, c=MADE, alpha=.75, lw=.4, edgecolors="white", zorder=3)
    x, y = proj(lonfix(pc.lon), pc.lat); ax.scatter(x, y, s=3 + 300 * pc.n / mx, c=SET, alpha=.75, lw=.4, edgecolors="white", zorder=4)
    for a, b in [("Japan", "United States of America"), ("United Kingdom", "United States of America"), ("United States of America", "United Kingdom")]:
        (x1, y1), (x2, y2) = CPT[a], CPT[b]
        xy = arc_xy(x1, y1, x2, y2, k=.22); ax.plot(xy[:, 0], xy[:, 1], color=FLOW, lw=2.2, alpha=.8, zorder=5)
    fig.text(.053, .9, "DATA STUDY", fontsize=12.5, family=MONO, color="white", va="center", bbox=dict(boxstyle="square,pad=.45", fc=FG, ec="none"))
    fig.text(.165, .9, "VIDEO GAMES · WIKIDATA AND WIKIPEDIA", fontsize=12.5, family=MONO, color=MUTED, va="center")
    fig.text(.05, .83, "Where games are set,", fontproperties=DISP, fontsize=50, va="top", color=FG)
    fig.text(.05, .7, "and where they are made", fontproperties=DISP, fontsize=50, va="top", color=FG)
    fig.text(.05, .55, f"{R['meta']['games_total']:,} games tied to\nreal places. New York leads\nwith {R['city']['New York City']}; Japan to the US\nis the busiest route ({R['flow']['Japan>United States of America']}).\n{R['space']['by_body']['Moon']} games on the Moon,\n{R['space']['by_body']['Mars']} on Mars.",
             fontsize=17, family=SER, va="top", color=FG, linespacing=1.38)
    fig.text(.05, .05, "DR TRISTAN HOTHAM · INDEPENDENT RESEARCHER", fontsize=12, family=MONO, color=MUTED)
    fig.savefig(os.path.join(ROOT, "header.png"), dpi=100); plt.close(fig)


if __name__ == "__main__":
    for paper in (False, True):
        w = 7.6 if paper else 15.2
        for f in (fig_map, fig_cities, fig_flows, fig_home, fig_trend, fig_space, fig_uk):
            f(paper, w)
    header()
    print("figures written")
