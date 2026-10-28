"""Step 1. Read the Wikidata tables (via QLever) from the bundle and write tidy intermediate tables.

Outputs (data/):
  wd_games.csv      every video game in Wikidata: qid, title, year, enwiki title, sitelinks
  wd_settings.csv   game -> narrative location (P840) links for real places, with the place id
  wd_places.json    the real places used as settings: label, lon, lat, globe, country (Natural Earth ADM0_A3), level
  wd_skipped.csv    narrative locations that are not real mappable places (fictional, abstract, no coordinates)
  wd_made.csv       for every game with a developer or a country of origin: where it was made, and how we know
Run: python3 code/01_wikidata.py
"""
import collections, csv, json, os, sys, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_bundle, tsv, qid, lit, wkt, Countries, DATA

B = load_bundle()
Q = B["qlever_tsv"]
NE = Countries()

# ---------- countries table: Wikidata QID -> ISO alpha 2 -> Natural Earth
_, rows = tsv(Q["countries"])
WD_ISO = {qid(r[0]): lit(r[2]) for r in rows if qid(r[0])}
WD_CLAB = {qid(r[0]): lit(r[1]) for r in rows if qid(r[0])}


def ne_of_country(q):
    if q in NE.by_wd:
        return NE.by_wd[q]
    iso = WD_ISO.get(q, "")
    return NE.by_iso.get(iso, "")


# ---------- games
_, rows = tsv(Q["meta"])
GAMES = {}
for g, lab, date, enwiki, sl in rows:
    k = qid(g)
    if not k:
        continue
    y = int(date[:4]) if date[:4].isdigit() and not date.startswith("-") else None
    title = lit(lab)
    ew = urllib.parse.unquote(enwiki.strip("<>").rsplit("/wiki/", 1)[-1]) if enwiki else ""
    old = GAMES.get(k)
    if old and old["year"] and y and old["year"] <= y:
        continue
    GAMES[k] = {"qid": k, "title": title, "year": y, "enwiki": ew, "sitelinks": int(sl) if sl.isdigit() else 0}
print("games in Wikidata", len(GAMES))

# ---------- places used as narrative locations
REAL_SPACE = {  # real bodies and regions of space (labels checked against the table below)
    "Q405": "Moon", "Q111": "Mars", "Q525": "Sun", "Q313": "Venus", "Q308": "Mercury", "Q319": "Jupiter", "Q193": "Saturn",
    "Q324": "Uranus", "Q332": "Neptune", "Q339": "Pluto", "Q2565": "Titan", "Q3303": "Europa", "Q3123": "Io", "Q3169": "Ganymede",
    "Q3134": "Callisto", "Q25271": "International Space Station", "Q4169": "outer space", "Q321": "Milky Way", "Q1": "universe",
    "Q544": "Solar System", "Q3863": "asteroid belt", "Q2": "Earth",
}
_, rows = tsv(Q["places"])
PL = {}
for p, lab, coord, country, body, cls in rows:
    k = qid(p)
    if not k:
        continue
    d = PL.setdefault(k, {"label": lit(lab), "coord": None, "country": set(), "body": set(), "cls": set()})
    c = wkt(coord)
    if c and not d["coord"]:
        d["coord"] = c
    if qid(country): d["country"].add(qid(country))
    if qid(body): d["body"].add(qid(body))
    if qid(cls): d["cls"].add(qid(cls))
for k, v in REAL_SPACE.items():
    if k in PL:
        assert PL[k]["label"].lower() == v.lower(), (k, PL[k]["label"], v)

FICTIONAL_CLS = {"Q3895768", "Q1964689", "Q15632617", "Q17198419", "Q21070568", "Q15707521", "Q24334685", "Q17166742",
                 "Q2239243", "Q15711870", "Q107538843", "Q106921111", "Q18572946", "Q1145276"}
COUNTRY_CLS = {"Q6256", "Q3624078", "Q7275", "Q112099"}
HIST_CLS = {"Q3024240", "Q28171280", "Q1250464", "Q417175", "Q48349", "Q1371288"}
BROAD_CLS = {"Q5107", "Q9430", "Q165"}  # continent, ocean, sea
# multi-country regions that are not a continent in Wikidata's classes (checked by hand against the table)
BROAD_LABELS = {"Europe", "Asia", "Africa", "South America", "North America", "Caribbean", "Arctic", "Antarctic", "North Africa",
                "Maghreb", "East Asia", "South Asia", "Southeast Asia", "Insular Oceania", "Oceania", "Scandinavia", "Central Africa",
                "Central America", "Central Asia", "Middle East", "Bermuda Triangle", "Korea", "Livonia", "Palestine", "Mediterranean Sea",
                "Pacific Ocean", "Atlantic Ocean", "South Pacific Ocean", "North Atlantic Ocean", "Western Europe", "Eastern Europe",
                "Balkans", "Latin America", "West Africa", "East Africa", "Southern Africa", "Near East", "Levant", "Indochina",
                "Mesoamerica", "Polynesia", "Melanesia", "Micronesia", "Sahara", "Amazon rainforest", "Himalayas", "Alps", "Persian Gulf"}

_, rows = tsv(Q["setting"])
links = [(qid(g), qid(p)) for g, p in rows if qid(g) and qid(p)]
use = collections.Counter(p for _, p in links)


# classes that make a place a city, town, village or city district (for the league table of cities)
CITY_CLS = {"Q515", "Q1549591", "Q1093829", "Q200250", "Q174844", "Q5119", "Q1637706", "Q486972", "Q3957", "Q532", "Q15284",
            "Q208511", "Q2264924", "Q1066984", "Q22865", "Q13218391", "Q13218382", "Q62049", "Q1187811", "Q108178728", "Q51929311",
            "Q22923920", "Q2074737", "Q1200957", "Q747074", "Q14762300", "Q123705", "Q1907114", "Q1115575", "Q3559093", "Q133442",
            "Q11422368", "Q494721", "Q2039348", "Q7930989", "Q116457956", "Q257391", "Q15127012", "Q1549591", "Q484170", "Q3184121",
            "Q15078955", "Q902814", "Q1500350", "Q1763214", "Q1093829", "Q707813", "Q42744322", "Q1956600", "Q2989398",
            "Q15974307", "Q1637706", "Q5153359", "Q1590990", "Q3191695", "Q4835091", "Q1074523", "Q2154459", "Q2983893"}
# checked by hand in the list of local places: fictional places that carry coordinates, and non-places
NOT_REAL = {"Skull Island": "fictional", "Starfleet Academy": "fictional", "Villa Villekulla": "fictional",
            "Mount Celeste": "fictional", "English": "a language, not a place", "the Blitz": "an event, not a place"}
BROAD_LABELS |= {"Eurasia", "Finland\u2013Russia border"}
HIST_LABELS = {"British Empire"}


def classify(k):
    d = PL.get(k)
    if not d:
        return "missing", None
    if d["label"] in NOT_REAL:
        return "fictional", NOT_REAL[d["label"]]
    if not d["label"]:
        return "nocoord", "no English label"
    if d["label"] in HIST_LABELS:
        return "historical", None
    if k in REAL_SPACE:
        return ("space", REAL_SPACE[k]) if k != "Q2" else ("abstract", "Earth as a whole")
    real_body = [b for b in d["body"] if b in REAL_SPACE and b != "Q2"]
    if real_body:
        return "space", REAL_SPACE[real_body[0]]
    if d["body"] - {"Q2"}:
        return "fictional", "on a fictional body"
    if d["cls"] & FICTIONAL_CLS:
        return "fictional", "fictional class"
    if not d["coord"] or d["coord"][0] != "Q2":
        return "nocoord", "no Earth coordinates"
    if k in WD_ISO or d["cls"] & COUNTRY_CLS and ne_of_country(k):
        return "country", None
    if d["cls"] & HIST_CLS:
        return "historical", None
    if d["cls"] & BROAD_CLS or d["label"] in BROAD_LABELS:
        return "broad", None
    return "local", None


places, skipped = {}, []
for k in use:
    kind, note = classify(k)
    d = PL.get(k, {"label": ""})
    if kind in ("missing", "fictional", "nocoord", "abstract"):
        skipped.append({"place_qid": k, "label": d["label"], "reason": note or kind, "games": use[k]})
        continue
    if kind == "space":
        places[k] = {"label": d["label"], "kind": "space", "body": note, "lon": None, "lat": None, "a3": ""}
        continue
    _, lon, lat = d["coord"]
    if kind == "country":
        a3 = ne_of_country(k) or NE.at(lon, lat)
    else:
        a3 = NE.at(lon, lat)
    if kind == "broad":
        a3 = ""
    if kind == "local" and not d["cls"] & CITY_CLS:
        kind = "region"   # states, counties, islands, landmarks: kept on the map, left out of the city league table
    places[k] = {"label": d["label"], "kind": kind, "body": "", "lon": round(lon, 5), "lat": round(lat, 5), "a3": a3,
                 "wd_country": sorted(d["country"])}
print("narrative locations", len(use), "real", len(places), "skipped", len(skipped))
print(collections.Counter(v["kind"] for v in places.values()))
print("sample local:", [places[k]["label"] for k, _ in use.most_common() if places.get(k, {}).get("kind") == "local"][:30])
print("no country:", [(places[k]["label"], places[k]["kind"]) for k in places if not places[k]["a3"] and places[k]["kind"] != "space"])
print("historical:", [places[k]["label"] for k in places if places[k]["kind"] == "historical"][:40])
print("broad:", [places[k]["label"] for k in places if places[k]["kind"] == "broad"][:40])

os.makedirs(os.path.join(DATA, "interim"), exist_ok=True)
with open(os.path.join(DATA, "interim", "wd_settings.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["game_qid", "place_qid"])
    for g, p in sorted(set(links)):
        if p in places and g in GAMES:
            w.writerow([g, p])
json.dump(places, open(os.path.join(DATA, "interim", "wd_places.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
with open(os.path.join(DATA, "interim", "wd_skipped.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, ["place_qid", "label", "reason", "games"]); w.writeheader()
    for r in sorted(skipped, key=lambda r: -r["games"]):
        w.writerow(r)

# ---------- where made
_, rows = tsv(Q["companies"])
CO = {}
for d, lab, hq, hqc, country, coord in rows:
    k = qid(d)
    if not k:
        continue
    c = CO.setdefault(k, {"label": lit(lab), "hq": "", "hqlab": "", "pt": None, "how": "", "country": set()})
    p1, p2 = wkt(hqc), wkt(coord)
    if p1 and p1[0] == "Q2" and not c["pt"]:
        c["pt"], c["how"], c["hq"] = (p1[1], p1[2]), "headquarters", qid(hq)
    elif p2 and p2[0] == "Q2" and not c["pt"]:
        c["pt"], c["how"] = (p2[1], p2[2]), "company coordinates"
    if qid(country): c["country"].add(qid(country))
_, rows = tsv(Q["dev"])
DEV = collections.defaultdict(list)
for g, d in rows:
    if qid(g) and qid(d) and qid(d) not in DEV[qid(g)]:
        DEV[qid(g)].append(qid(d))
devcount = collections.Counter(d for ds in DEV.values() for d in ds)
_, rows = tsv(Q["origin"])
ORIG = collections.defaultdict(list)
for g, c in rows:
    if qid(g) and qid(c) and qid(c) not in ORIG[qid(g)]:
        ORIG[qid(g)].append(qid(c))
_, rows = tsv(Q["pub"])
PUB = collections.defaultdict(list)
for g, d in rows:
    if qid(g) and qid(d) and qid(d) not in PUB[qid(g)]:
        PUB[qid(g)].append(qid(d))

n_how = collections.Counter()
with open(os.path.join(DATA, "interim", "wd_made.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["game_qid", "made_how", "dev_qid", "dev_label", "lon", "lat", "made_a3", "n_devs", "origin_a3"])
    for g in GAMES:
        devs = DEV.get(g, [])
        org = [ne_of_country(c) for c in ORIG.get(g, [])]
        org = [o for o in org if o]
        org_a3 = org[0] if len(set(org)) == 1 else ("+".join(sorted(set(org))) if org else "")
        located = sorted([d for d in devs if CO.get(d, {}).get("pt")], key=lambda d: (-devcount[d], d))
        if located:
            d = located[0]; lon, lat = CO[d]["pt"]
            a3 = NE.at(lon, lat)
            row = [g, "developer HQ", d, CO[d]["label"], round(lon, 5), round(lat, 5), a3, len(devs), org_a3]
        else:
            withc = sorted([d for d in devs if any(ne_of_country(c) for c in CO.get(d, {}).get("country", ()))], key=lambda d: (-devcount[d], d))
            if withc:
                d = withc[0]; a3 = [ne_of_country(c) for c in sorted(CO[d]["country"]) if ne_of_country(c)][0]
                row = [g, "developer country", d, CO[d]["label"], "", "", a3, len(devs), org_a3]
            elif org and len(set(org)) == 1:
                row = [g, "country of origin", "", "", "", "", org[0], len(devs), org_a3]
            else:
                n_how["none"] += 1
                continue
        n_how[row[1]] += 1
        w.writerow(row)
print("made:", dict(n_how))

with open(os.path.join(DATA, "interim", "wd_games.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["qid", "title", "year", "enwiki", "sitelinks"])
    for g in sorted(GAMES, key=lambda k: int(k[1:])):
        v = GAMES[g]; w.writerow([g, v["title"], v["year"] or "", v["enwiki"], v["sitelinks"]])
print("done")
