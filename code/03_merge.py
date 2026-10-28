"""Step 3. Merge the Wikidata and Wikipedia links into the published tables.

Rules
- A game-place link is kept once, with its source: wikidata, wikipedia or both.
- Most specific place: a country-level or historical-state link is set aside when the same game also has a city, region
  or landmark in that country; a broad link (continent, ocean, multi-country region) is set aside when the game has any
  other place on Earth. Set-aside links stay in links.csv with used = 0 and the reason.
- Where made: developer headquarters coordinates first, else the developer's country, else the game's country of origin
  (P495). The method is recorded per game.
Outputs (data/): games.csv, places.csv, links.csv, space.csv, eras.csv
Run: python3 code/03_merge.py
"""
import collections, csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, Countries

NE = Countries()
OUTFILES = []


def out(n):
    f = open(os.path.join(DATA, n), "w", newline="", encoding="utf-8"); OUTFILES.append(f); return f


rd = lambda n: list(csv.DictReader(open(os.path.join(DATA, "interim", n), encoding="utf-8")))
GAMES = {r["qid"]: r for r in rd("wd_games.csv")}
MADE = {r["game_qid"]: r for r in rd("wd_made.csv")}
WDP = json.load(open(os.path.join(DATA, "interim", "wd_places.json"), encoding="utf-8"))
WPP = json.load(open(os.path.join(DATA, "interim", "wp_places.json"), encoding="utf-8"))

PLACES = {}
for k, v in WDP.items():
    PLACES[k] = dict(v, how="Wikidata coordinates (P625)" if v["kind"] != "space" else "Wikidata")
for k, v in WPP.items():
    PLACES.setdefault(k, v)

# the same place under two Wikidata items (e.g. two items labelled "Tokyo"): fold the pair into the one used more
import math
for k, v in PLACES.items():
    if v.get("label") == "Northern Quebec":
        v["kind"] = "region"   # a region, not a town (checked by hand)
raw = collections.Counter([r["place_qid"] for r in rd("wd_settings.csv")] + [r["place_id"] for r in rd("wp_links.csv")])
ALIAS = {}
bylab = collections.defaultdict(list)
for k, v in PLACES.items():
    if v["kind"] != "space" and k in raw:
        bylab[v["label"]].append(k)
for lab, ks in bylab.items():
    ks.sort(key=lambda k: -raw[k])
    for k in ks[1:]:
        a, b = PLACES[ks[0]], PLACES[k]
        d = math.hypot(a["lon"] - b["lon"], (a["lat"] - b["lat"])) if a["lon"] is not None and b["lon"] is not None else 99
        if d < 0.5:
            ALIAS[k] = ks[0]
print("folded duplicate places:", {k: (PLACES[k]["label"], v) for k, v in ALIAS.items()})

src = collections.defaultdict(set)
cats = collections.defaultdict(list)
for r in rd("wd_settings.csv"):
    src[(r["game_qid"], ALIAS.get(r["place_qid"], r["place_qid"]))].add("wikidata")
for r in rd("wp_links.csv"):
    pid = ALIAS.get(r["place_id"], r["place_id"])
    src[(r["game_qid"], pid)].add("wikipedia")
    cats[(r["game_qid"], pid)].append(r["category"])

# space: Wikidata narrative locations on real bodies, plus the Wikipedia space categories
BODY_GROUP = {"Moon": "Moon", "Mars": "Mars", "Venus": "Venus", "Titan": "Titan", "Io": "Jupiter's moons", "Callisto": "Jupiter's moons",
              "Europa": "Jupiter's moons", "Ganymede": "Jupiter's moons", "Sun": "Sun", "Mercury": "Mercury", "Jupiter": "Jupiter",
              "Saturn": "Saturn", "Pluto": "Pluto", "International Space Station": "Earth orbit",
              "outer space": "Outer space", "Milky Way": "Outer space", "universe": "Outer space", "Solar System": "Outer space",
              "spacecraft": "Outer space"}
space = collections.defaultdict(set)
space_src = collections.defaultdict(set)
for (g, p), s in list(src.items()):
    if PLACES.get(p, {}).get("kind") == "space":
        b = PLACES[p]["body"]
        space[(g, BODY_GROUP[b])].add(b); space_src[(g, BODY_GROUP[b])].add("wikidata")
        del src[(g, p)]
for r in rd("wp_space.csv"):
    space[(r["game_qid"], BODY_GROUP[r["body"]])].add(r["body"]); space_src[(r["game_qid"], BODY_GROUP[r["body"]])].add("wikipedia")

# A data problem found while checking: about two hundred North American league sports games (Madden, NHL, MLB and so on)
# carry Washington, D.C. as their only Wikidata narrative location, and no Wikipedia category agrees. These are set aside.
import re
SPORT = re.compile(r"NFL|NHL|NBA|MLB|Madden|Baseball|Football|Hockey|Basketball|Bowl|World Series|Triple Play|Quarterback|Golf|PGA|"
                   r"Tennis|Soccer|FIFA|Slugfest|Blitz|Hoops|Tecmo|NCAA|Jam|Hardball|RBI|Bases|Pennant|Bigs|Home Run|Bottom of the 9th|"
                   r"Roughness|Open Ice|Face Off|End 2 End|Winning Run", re.I)
DC = "Q61"
dc_sport = {g for (g, p), s in src.items() if p == DC and s == {"wikidata"} and SPORT.search(GAMES[g]["title"])}
print("Washington, D.C. sports links set aside:", len(dc_sport))

# most specific place per game
by_game = collections.defaultdict(list)
for (g, p) in src:
    by_game[g].append(p)
LEVEL = {"local": 3, "region": 3, "historical": 1, "country": 1, "broad": 0}
links = []
for g, ps in by_game.items():
    ok = [p for p in ps if not (p == DC and g in dc_sport)]
    fine_a3 = {PLACES[p]["a3"] for p in ok if LEVEL[PLACES[p]["kind"]] == 3}
    nonbroad = [p for p in ok if PLACES[p]["kind"] != "broad"]
    for p in ps:
        k = PLACES[p]["kind"]; used, why = 1, ""
        if p == DC and g in dc_sport:
            used, why = 0, "probable Wikidata error: league sports game tagged with Washington, D.C."
        elif k in ("country", "historical") and PLACES[p]["a3"] in fine_a3:
            used, why = 0, "a more specific place in the same country"
        elif k == "broad" and nonbroad:
            used, why = 0, "a more specific place"
        s = src[(g, p)]
        links.append({"game_qid": g, "place_id": p, "source": "both" if len(s) == 2 else next(iter(s)), "used": used,
                      "set_aside_because": why, "wikipedia_categories": "; ".join(sorted(cats.get((g, p), [])))})

# eras (setting periods from Wikipedia category names)
eras = rd("wp_eras.csv")

used_places = {l["place_id"] for l in links}
pgames = collections.Counter(l["place_id"] for l in links if l["used"])
placed = {l["game_qid"] for l in links if l["used"]}
in_space = {g for g, _ in space}
print("games with an Earth setting", len(placed), "in space", len(in_space), "both", len(placed & in_space))

w = csv.writer(out("places.csv"))
w.writerow(["place_id", "label", "kind", "lon", "lat", "country_a3", "country", "location_source", "games"])
for p in sorted(used_places, key=lambda p: (-pgames[p], p)):
    v = PLACES[p]
    w.writerow([p, v["label"], v["kind"], v["lon"], v["lat"], v["a3"], NE.feat[v["a3"]]["name"] if v["a3"] else "", v["how"], pgames[p]])

w = csv.DictWriter(out("links.csv"), list(links[0]))
w.writeheader()
for l in sorted(links, key=lambda l: (int(l["game_qid"][1:]), l["place_id"])):
    w.writerow(l)

w = csv.writer(out("space.csv"))
w.writerow(["game_qid", "body_group", "bodies", "source"])
for (g, b) in sorted(space, key=lambda x: (x[1], int(x[0][1:]))):
    s = space_src[(g, b)]
    w.writerow([g, b, "; ".join(sorted(space[(g, b)])), "both" if len(s) == 2 else next(iter(s))])

w = csv.writer(out("eras.csv"))
w.writerow(["game_qid", "from", "to", "category"])
for e in eras:
    w.writerow([e["game_qid"], e["from"], e["to"], e["category"]])

# nearest GeoNames town (population 15,000 or more) to each studio point, as a readable "made in" label
import io, zipfile
import numpy as np
from common import CITIES
gn = []
with zipfile.ZipFile(CITIES) as z:
    nm = [n for n in z.namelist() if n.endswith(".txt")][0]
    for line in io.TextIOWrapper(z.open(nm), encoding="utf-8"):
        p = line.split("\t")
        gn.append((p[1], float(p[4]), float(p[5]), int(p[14] or 0)))
GLAT = np.radians([g[1] for g in gn]); GLON = np.radians([g[2] for g in gn]); GPOP = np.array([g[3] for g in gn])


def near_town(lon, lat):
    la, lo = math.radians(lat), math.radians(lon)
    d = 6371 * np.arccos(np.clip(np.sin(la) * np.sin(GLAT) + np.cos(la) * np.cos(GLAT) * np.cos(GLON - lo), -1, 1))
    # the biggest town within 15 km, else the nearest within 60 km
    near = np.where(d <= 15)[0]
    if len(near):
        return gn[near[np.argmax(GPOP[near])]][0]
    i = int(np.argmin(d))
    return gn[i][0] if d[i] <= 60 else ""


keep = placed | in_space
w = csv.writer(out("games.csv"))
w.writerow(["qid", "title", "year", "enwiki", "sitelinks", "made_how", "developer_qid", "developer", "made_lon", "made_lat",
            "made_town", "made_country_a3", "made_country", "origin_country_a3", "set_on_earth", "set_in_space"])
for g in sorted(keep, key=lambda k: int(k[1:])):
    G, M = GAMES[g], MADE.get(g, {})
    a3 = M.get("made_a3", "")
    title = G["title"] or G["enwiki"].replace("_", " ")     # no English label in Wikidata: use the English Wikipedia title
    w.writerow([g, title, G["year"], G["enwiki"], G["sitelinks"], M.get("made_how", ""), M.get("dev_qid", ""), M.get("dev_label", ""),
                M.get("lon", ""), M.get("lat", ""), near_town(float(M["lon"]), float(M["lat"])) if M.get("lon") else "", a3, NE.feat[a3]["name"] if a3 in NE.feat else "", M.get("origin_a3", ""),
                int(g in placed), int(g in in_space)])
print("games.csv", len(keep))

for f in OUTFILES:   # flush and close the tables before tidying them
    f.close()

# Names from the sources sometimes contain en or em dashes (e.g. "Tomb Raider I–III"); the published tables use plain hyphens.
for n in ("games.csv", "places.csv", "links.csv", "space.csv", "eras.csv"):
    p = os.path.join(DATA, n)
    t = open(p, encoding="utf-8").read().replace(" — ", " - ").replace("—", "-").replace("–", "-")
    open(p, "w", encoding="utf-8").write(t)
