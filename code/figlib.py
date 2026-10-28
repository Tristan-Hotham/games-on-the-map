"""Shared drawing helpers for the static figures, header and collage: fonts, palette, a Robinson world map."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.collections import PolyCollection, LineCollection
from pyproj import Transformer
from shapely.geometry import shape
from common import DATA, NE

FONT_DIR = os.environ.get("FONT_DIR", "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts")
for f in ["FrauncesVar.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "SourceSerif4-Regular.ttf", "SourceSerif4-Semibold.ttf", "SourceSerif4-It.ttf"]:
    p = os.path.join(FONT_DIR, f)
    if os.path.exists(p):
        fm.fontManager.addfont(p)
DISP = fm.FontProperties(fname=os.path.join(FONT_DIR, "FrauncesVar.ttf")) if os.path.exists(os.path.join(FONT_DIR, "FrauncesVar.ttf")) else fm.FontProperties(family="serif", weight="bold")
SER = "Source Serif 4"
MONO = "IBM Plex Mono"

BG = "#F6F1E7"; FG = "#1F1B24"; MUTED = "#675F6B"; RULE = "#DDD3C3"; LAND = "#E9E1D3"; SEA = "#F6F1E7"
SET = "#CF3F35"; MADE = "#156B87"; FLOW = "#7B3F8C"; SPACE = "#2F2F7A"; MOON = "#8E8A99"; MARS = "#C0582F"

plt.rcParams.update({"font.family": MONO, "font.size": 12, "text.color": FG, "axes.labelcolor": FG, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.edgecolor": RULE, "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG})

ROB = Transformer.from_crs("EPSG:4326", "+proj=robin +lon_0=11 +datum=WGS84", always_xy=True)


def proj(lon, lat):
    return ROB.transform(np.asarray(lon, float), np.asarray(lat, float))


_POLYS = None


def world_polys(simplify=0.08):
    """Natural Earth 1:50m countries projected to Robinson, as (a3, [arrays of x,y]) pairs."""
    global _POLYS
    if _POLYS is not None:
        return _POLYS
    g = json.load(open(os.path.join(NE, "ne_50m_admin_0_countries.geojson"), encoding="utf-8"))
    out = []
    for f in g["features"]:
        a3 = f["properties"]["ADM0_A3"]
        if a3 == "ATA":
            continue
        geom = shape(f["geometry"]).simplify(simplify, preserve_topology=True)
        polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
        rings = []
        for p in polys:
            x, y = np.asarray(p.exterior.coords).T
            # split rings that cross the edge of the projection (lon_0 = 11 puts the seam at -169)
            px, py = proj(np.where(x < -169, x + 360, x) - 0, y)
            if np.ptp(px) > 3e7:
                continue
            rings.append(np.column_stack([px, py]))
        out.append((a3, rings))
    _POLYS = out
    return out


def draw_world(ax, fill=None, edge="#FFFFFF", lw=0.3, default=LAND, zorder=1):
    polys, cols = [], []
    for a3, rings in world_polys():
        c = (fill or {}).get(a3, default)
        for r in rings:
            polys.append(r); cols.append(c)
    ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors=edge, linewidths=lw, zorder=zorder))
    # outline of the projected globe
    lat = np.linspace(-90, 90, 181)
    x1, y1 = proj(np.full_like(lat, -169 + 1e-6), lat); x2, y2 = proj(np.full_like(lat, 191 - 1e-6), lat)
    ax.plot(np.r_[x1, x2[::-1], x1[:1]], np.r_[y1, y2[::-1], y1[:1]], color=RULE, lw=0.8, zorder=0)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_xlim(x1.min() * 1.01, x2.max() * 1.01); ax.set_ylim(proj(0, -58)[1], proj(0, 84)[1])


def arc_xy(lon1, lat1, lon2, lat2, k=0.22, n=40):
    """Curved line in projected space between two lon/lat points (no wrapping: the projection's seam is in the Pacific)."""
    x1, y1 = proj(lon1 if lon1 >= -169 else lon1 + 360, lat1); x2, y2 = proj(lon2 if lon2 >= -169 else lon2 + 360, lat2)
    mx, my, dx, dy = (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1
    cx, cy = mx - dy * k, my + dx * k
    t = np.linspace(0, 1, n)[:, None]
    P0, P1, P2 = np.array([x1, y1]), np.array([cx, cy]), np.array([x2, y2])
    return (1 - t) ** 2 * P0 + 2 * (1 - t) * t * P1 + t ** 2 * P2


def lonfix(lon):
    lon = np.asarray(lon, float)
    return np.where(lon < -169, lon + 360, lon)


def style_axes(ax, grid="x"):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(length=0, labelsize=12)
    if grid:
        ax.grid(axis=grid, color=RULE, lw=0.8); ax.set_axisbelow(True)
