"""Step 5. Small files the interactive page loads.

data/page.json      games, places, studios and countries in compact arrays (see the keys at the end)
data/countries.json Natural Earth 1:50m countries, simplified, for the choropleth, the land and the borders
data/towns.json     GeoNames towns for the "place names" map layer, with a rank for how many to show
data/hills.png      shaded relief in Web Mercator (AWS Terrain Tiles, zoom 4, resampled to 2048 px), black with alpha
Run: python3 code/05_page_data.py
"""
import base64, collections, csv, gzip, io, json, math, os, sys, zipfile
import numpy as np
import pandas as pd
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, CITIES, D13, Countries

rd = lambda n: pd.read_csv(os.path.join(DATA, n), keep_default_na=False, na_values=[""])
G = rd("games.csv"); P = rd("places.csv"); L = rd("links.csv"); S = rd("space.csv"); E = rd("eras.csv")
C = Countries()

# ---------- countries (simplified polygons)
from shapely.geometry import mapping
feats = []
A3 = sorted(C.feat)
AIDX = {a: i for i, a in enumerate(A3)}
for a in A3:
    f = C.feat[a]
    g = f["geom"].simplify(0.04, preserve_topology=True)
    if g.is_empty:
        g = f["geom"]
    m = mapping(g)
    def rnd(c):
        if isinstance(c[0], (float, int)):
            return [round(c[0], 2), round(c[1], 2)]
        return [rnd(x) for x in c]
    feats.append({"type": "Feature", "properties": {"i": AIDX[a]}, "geometry": {"type": m["type"], "coordinates": rnd(m["coordinates"])}})
json.dump({"type": "FeatureCollection", "features": feats}, open(os.path.join(DATA, "countries.json"), "w"), separators=(",", ":"))

# ---------- places, studios, games
PL = P[P.kind != "space"].reset_index(drop=True)
PIDX = {p: i for i, p in enumerate(PL.place_id)}
KIND = {"local": 0, "region": 1, "historical": 2, "country": 3, "broad": 4}
places = [[r.label, round(r.lon, 3), round(r.lat, 3), KIND[r.kind], AIDX.get(r.country_a3, -1) if isinstance(r.country_a3, str) else -1,
           r.location_source] for r in PL.itertuples()]

stud = {}
studios = []
def studio_idx(r):
    if not isinstance(r.made_how, str):
        return -1
    if r.made_how == "developer HQ":
        key = (r.developer, round(r.made_lon, 3), round(r.made_lat, 3))
        lon, lat = r.made_lon, r.made_lat
    else:  # a country only: placed at the country's label point
        f = C.feat[r.made_country_a3]
        key = ("country:" + r.made_country_a3,)
        lon, lat = f["lx"], f["ly"]
    if key not in stud:
        stud[key] = len(studios)
        name = (r.developer if isinstance(r.developer, str) else "a developer with no English name in Wikidata") if r.made_how == "developer HQ" else f"{C.feat[r.made_country_a3]['name']} (country only)"
        studios.append([name, round(lon, 3), round(lat, 3), AIDX.get(r.made_country_a3, -1), r.made_town if isinstance(r.made_town, str) else "",
                        1 if r.made_how == "developer HQ" else 0])
    return stud[key]

HOW = {"developer HQ": 0, "developer country": 1, "country of origin": 2}
used = L[L.used == 1]
gl = used.groupby("game_qid")
SRC = {"wikidata": 1, "wikipedia": 2, "both": 3}
eras = E.groupby("game_qid").agg(lo=("from", "min"), hi=("to", "max"))
BODY = {"Moon": 0, "Mars": 1, "Venus": 2, "Titan": 3, "Jupiter's moons": 4, "Sun": 5, "Mercury": 6, "Outer space": 7, "Earth orbit": 8}
sp = S.groupby("game_qid").body_group.agg(list)
spb = S.groupby("game_qid").bodies.agg(lambda s: "; ".join(s))
games = []
for r in G.itertuples():
    si = studio_idx(r)
    pl, src = [], []
    if r.qid in gl.groups:
        for x in gl.get_group(r.qid).itertuples():
            if x.place_id in PIDX:
                pl.append(PIDX[x.place_id]); src.append(SRC[x.source])
    e = eras.loc[r.qid] if r.qid in eras.index else None
    games.append([
        r.title if isinstance(r.title, str) else "", int(r.year) if pd.notna(r.year) else 0, si, HOW.get(r.made_how, -1) if isinstance(r.made_how, str) else -1,
        pl, src, [int(e.lo), int(e.hi)] if e is not None else 0,
        [BODY[b] for b in sp.loc[r.qid]] if r.qid in sp.index else 0,
        r.qid, r.enwiki if isinstance(r.enwiki, str) else "",
    ])
countries = [[a, C.feat[a]["name"], round(C.feat[a]["lx"], 2), round(C.feat[a]["ly"], 2)] for a in A3]
spacebodies = {r.game_qid: r for r in S.itertuples()}
page = {"keys": {"game": ["title", "year", "studio", "made_how", "places", "place_sources", "era", "space", "qid", "enwiki"],
                 "place": ["label", "lon", "lat", "kind", "country", "location_source"],
                 "studio": ["name", "lon", "lat", "country", "town", "has_hq"], "country": ["a3", "name", "lon", "lat"]},
        "kinds": list(KIND), "how": list(HOW), "bodies": list(BODY), "space_detail": {g: spb.loc[g] for g in spb.index},
        "games": games, "places": places, "studios": studios, "countries": countries}
s = json.dumps(page, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
s = s.replace(" \u2014 ", " - ").replace("\u2014", "-").replace("\u2013", "-")   # plain hyphens in names
open(os.path.join(DATA, "page.json"), "w", encoding="utf-8").write(s)
print("page.json", len(s.encode()) // 1024, "KB;", len(games), "games,", len(places), "places,", len(studios), "studio points")

# ---------- towns for labels
rows = []
with zipfile.ZipFile(CITIES) as z:
    nm = [n for n in z.namelist() if n.endswith(".txt")][0]
    for line in io.TextIOWrapper(z.open(nm), encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        rows.append((p[1], float(p[4]), float(p[5]), int(p[14] or 0), p[7]))
rows.sort(key=lambda r: -r[3])
towns = []
for i, (n, la, lo, pop, fc) in enumerate(rows[:7000]):
    rank = 3 if (i < 70 or fc == "PPLC" and pop > 1e6) else 2 if (i < 450 or fc == "PPLC") else 1 if i < 2000 else 0
    towns.append([n.replace("\u2013", "-").replace("\u2014", "-"), round(lo, 3), round(la, 3), rank])
json.dump(towns, open(os.path.join(DATA, "towns.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("towns", len(towns))

# ---------- hills (Web Mercator, matches Leaflet's world at zoom 3)
T = json.load(gzip.open(os.path.join(D13, "terrarium_tiles.json.gz")))["tiles"]
z = 4
el = np.zeros((16 * 256, 16 * 256), np.float32)
for x in range(16):
    for y in range(16):
        a = np.asarray(Image.open(io.BytesIO(base64.b64decode(T[f"{z}/{x}/{y}"]))).convert("RGB")).astype(np.float32)
        el[y * 256:(y + 1) * 256, x * 256:(x + 1) * 256] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
del T
el = el.reshape(2048, 2, 2048, 2).mean(axis=(1, 3))
land = el > 0
# ground distance per pixel shrinks towards the poles in Mercator: scale the gradient by cos(lat)
n = 2048
yy = (np.arange(n) + .5) / n
lat = np.degrees(np.arctan(np.sinh(math.pi * (1 - 2 * yy))))
cell = 2 * math.pi * 6371000 / n * np.cos(np.radians(lat))[:, None]
e = np.maximum(el, 0) * 12.0
gy, gx = np.gradient(e)
dzdx, dzdy = gx / cell, -gy / cell
slope = np.arctan(np.hypot(dzdx, dzdy))
aspect = np.arctan2(-dzdx, -dzdy)
alt = np.radians(40)
sh = np.zeros_like(e)
for az, w in ((315, .65), (270, .2), (0, .15)):
    sh += w * (np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(np.radians(az) - aspect))
v = np.clip(sh / np.sin(alt), 0, 1.4)
dark = np.clip(1 - v, 0, 1) ** 0.9                    # 0 flat or lit, up to 1 in deep shadow
light = np.clip(v - 1, 0, .4) / .4                    # sunlit slopes
A = np.where(land, np.clip(dark * 255 * 1.15, 0, 255), 0).astype(np.uint8)
L2 = np.where(land, np.clip(light * 120, 0, 120), 0).astype(np.uint8)
# two-channel PNG: R = shade (darkening), G = highlight; the page turns them into colour and alpha on a canvas
img = np.dstack([A, L2, np.zeros_like(A)])
Image.fromarray(img, "RGB").save(os.path.join(DATA, "hills.png"), optimize=True)
print("hills.png", os.path.getsize(os.path.join(DATA, "hills.png")) // 1024, "KB")
