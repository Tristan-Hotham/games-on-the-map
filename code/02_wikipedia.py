"""Step 2. Parse the English Wikipedia category tree under "Category:Video games by setting".

Each "... video games set in X" / "set on X" category is read as one of:
  era    (a year, decade, century or millennium: "set in 1985", "set in the 1940s", "set in the 22nd century")
  space  (outer space, the Moon, Mars, Titan, Venus, the Solar System, spacecraft)
  place  (a real place, geocoded offline; see the order below)
  other  (kinds of place such as castles or hotels, fictional places, periods without dates): ignored
Some names carry both an era and a place ("set in 16th-century Sengoku period", "12th-century Plantagenet England").

Geocoding order for the place part, all offline:
  1. the category's Wikidata main topic (P301) when it has coordinates
  2. a place with the same English label among the Wikidata narrative locations (step 1)
  3. a Natural Earth country with that name (or a Wikidata country label)
  4. the hand list in this file (each entry names the GeoNames town it is placed at, or the Wikidata place it is the same as)
  5. GeoNames cities15000, exact name, the most populous match
Anything else is written to data/wp_unplaced.csv.
Outputs: data/wp_links.csv (game, place id, category), data/wp_places.json, data/wp_eras.csv, data/wp_space.csv, data/wp_categories.csv
Run: python3 code/02_wikipedia.py
"""
import collections, csv, io, json, os, re, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_bundle, tsv, qid, lit, wkt, Countries, DATA, CITIES

B = load_bundle()
NE = Countries()
CATS = B["wiki_cats"]
PAGE_QID = B["wiki_page_qid"]
CAT_QID = B["wiki_cat_qid"]
GAMES = {}
with open(os.path.join(DATA, "interim", "wd_games.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        GAMES[r["qid"]] = r
WDP = json.load(open(os.path.join(DATA, "interim", "wd_places.json"), encoding="utf-8"))
WD_BY_LABEL = {}
for k, v in WDP.items():
    if v["kind"] != "space":
        WD_BY_LABEL.setdefault(v["label"], k)

_, rows = tsv(B["qlever_tsv"]["countries"])
WD_COUNTRY_BY_LABEL = {lit(r[1]): qid(r[0]) for r in rows}
WD_ISO = {qid(r[0]): lit(r[2]) for r in rows}

# category main topics with coordinates
_, rows = tsv(B["cat_topics_tsv"])
TOPIC = {}
for cat, top, tl, coord, country, body, cls in rows:
    c = wkt(coord)
    if qid(cat) and c and c[0] == "Q2":
        TOPIC[qid(cat)] = (qid(top), lit(tl), c[1], c[2])

# GeoNames cities15000
GN = collections.defaultdict(list)
with zipfile.ZipFile(CITIES) as z:
    name = [n for n in z.namelist() if n.endswith(".txt")][0]
    for line in io.TextIOWrapper(z.open(name), encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        GN[p[1]].append({"gid": p[0], "name": p[1], "lat": float(p[4]), "lon": float(p[5]), "cc": p[8], "pop": int(p[14] or 0)})


def gn(name, cc=None):
    c = [x for x in GN.get(name, []) if not cc or x["cc"] == cc]
    return max(c, key=lambda x: x["pop"]) if c else None


# ---------- the hand list: name -> ("gn", town, ISO2) placed at that GeoNames town, ("wd", label) same as a Wikidata place,
# ("ne", Natural Earth name), ("skip", reason). Kinds: region (state, county, prefecture, island), historical, broad.
HAND = {
    # US states and regions, placed at the state capital (GeoNames)
    "Alabama": ("gn", "Montgomery", "US", "region"), "Arkansas": ("gn", "Little Rock", "US", "region"),
    "Connecticut": ("gn", "Hartford", "US", "region"), "Delaware": ("gn", "Dover", "US", "region"),
    "Georgia (U.S. state)": ("gn", "Atlanta", "US", "region"), "Idaho": ("gn", "Boise", "US", "region"),
    "Illinois": ("gn", "Springfield", "US", "region"), "Indiana": ("gn", "Indianapolis", "US", "region"),
    "Iowa": ("gn", "Des Moines", "US", "region"), "Kansas": ("gn", "Topeka", "US", "region"),
    "Mississippi": ("gn", "Jackson", "US", "region"), "Missouri": ("gn", "Jefferson City", "US", "region"),
    "Montana": ("gn", "Helena", "US", "region"), "Nebraska": ("gn", "Lincoln", "US", "region"),
    "New Hampshire": ("gn", "Concord", "US", "region"), "New York (state)": ("gn", "Albany", "US", "region"),
    "North Dakota": ("gn", "Bismarck", "US", "region"), "Pennsylvania": ("gn", "Harrisburg", "US", "region"),
    "South Carolina": ("gn", "Columbia", "US", "region"), "Tennessee": ("gn", "Nashville", "US", "region"),
    "Virginia": ("gn", "Richmond", "US", "region"), "Washington (state)": ("gn", "Olympia", "US", "region"),
    "Wyoming": ("gn", "Cheyenne", "US", "region"), "the Western United States": ("gn", "Salt Lake City", "US", "region"),
    "the Las Vegas Valley": ("wd", "Las Vegas Valley"), "Daytona Beach, Florida": ("gn", "Daytona Beach", "US", "local"),
    "Orlando, Florida": ("gn", "Orlando", "US", "local"), "Georgia (country)": ("ne", "Georgia"),
    "Puerto Rico": ("gn", "San Juan", "PR", "region"), "Guam": ("gn", "Hagåtña", "GU", "region"),
    "the Northern Mariana Islands": ("gn", "Saipan", "MP", "region"), "the United States Virgin Islands": ("gn", "Charlotte Amalie", "VI", "region"),
    "the American frontier": ("gn", "Denver", "US", "region"), "St. Louis": ("gn", "St. Louis", "US", "local"),
    "Portland": ("gn", "Portland", "US", "local"),
    # Canada
    "Calgary": ("gn", "Calgary", "CA", "local"),
    # UK counties and places, placed at the county town (GeoNames)
    "Cheshire": ("gn", "Chester", "GB", "region"), "Cornwall": ("gn", "Truro", "GB", "region"), "Cumbria": ("gn", "Carlisle", "GB", "region"),
    "Devon": ("gn", "Exeter", "GB", "region"), "East Sussex": ("gn", "Lewes", "GB", "region"), "Gloucestershire": ("gn", "Gloucester", "GB", "region"),
    "Hampshire": ("gn", "Winchester", "GB", "region"), "Kent": ("gn", "Maidstone", "GB", "region"), "Lancashire": ("gn", "Preston", "GB", "region"),
    "Leicestershire": ("gn", "Leicester", "GB", "region"), "Lincolnshire": ("gn", "Lincoln", "GB", "region"),
    "Norfolk": ("gn", "Norwich", "GB", "region"), "Northamptonshire": ("gn", "Northampton", "GB", "region"),
    "Nottinghamshire": ("gn", "Nottingham", "GB", "region"),
    "Surrey": ("gn", "Guildford", "GB", "region"), "Wiltshire": ("gn", "Salisbury", "GB", "region"),
    "Yorkshire": ("gn", "York", "GB", "region"), "Northern Ireland": ("gn", "Belfast", "GB", "region"),
    "Cambridge": ("gn", "Cambridge", "GB", "local"), "Oxford": ("gn", "Oxford", "GB", "local"), "Bristol": ("gn", "Bristol", "GB", "local"),
    "Gloucester": ("gn", "Gloucester", "GB", "local"), "Plymouth": ("gn", "Plymouth", "GB", "local"), "Portsmouth": ("gn", "Portsmouth", "GB", "local"),
    "Southampton": ("gn", "Southampton", "GB", "local"), "Salisbury": ("gn", "Salisbury", "GB", "local"), "Winchester": ("gn", "Winchester", "GB", "local"),
    "York": ("gn", "York", "GB", "local"), "Newcastle upon Tyne": ("gn", "Newcastle upon Tyne", "GB", "local"), "Glasgow": ("gn", "Glasgow", "GB", "local"),
    "Manchester": ("wd", "Manchester"), "Birmingham": ("wd", "Birmingham"),
    "the Isle of Wight": ("wd", "Isle of Wight"), "the Isle of Man": ("gn", "Douglas", "IM", "region"), "Guernsey": ("gn", "Saint Peter Port", "GG", "region"),
    "medieval England": ("ne", "United Kingdom", "historical", "England"), "Plantagenet England": ("ne", "United Kingdom", "historical", "England"),
    "Anglo-Saxon England": ("ne", "United Kingdom", "historical", "England"), "medieval Scotland": ("wd", "Scotland"),
    "the Victorian era": ("skip", "period without dates"), "the British Empire": ("wd", "British Empire"),
    # Japan
    "Aichi Prefecture": ("gn", "Nagoya", "JP", "region"), "Chiba Prefecture": ("gn", "Chiba", "JP", "region"),
    "Fukuoka Prefecture": ("gn", "Fukuoka", "JP", "region"), "Fukuoka": ("gn", "Fukuoka", "JP", "local"),
    "Hiroshima Prefecture": ("gn", "Hiroshima", "JP", "region"), "Hiroshima": ("gn", "Hiroshima", "JP", "local"),
    "Hyōgo Prefecture": ("gn", "Kobe", "JP", "region"), "Kanagawa Prefecture": ("gn", "Yokohama", "JP", "region"),
    "Miyagi Prefecture": ("gn", "Sendai", "JP", "region"), "Osaka Prefecture": ("wd", "Osaka"), "Saitama Prefecture": ("gn", "Saitama", "JP", "region"),
    "Okinawa Prefecture": ("wd", "Okinawa Prefecture"), "Hokkaido": ("wd", "Hokkaidō"), "Nagano (city)": ("gn", "Nagano", "JP", "local"),
    "Sapporo": ("gn", "Sapporo", "JP", "local"), "Nagoya": ("gn", "Nagoya", "JP", "local"),
    "feudal Japan": ("ne", "Japan", "historical", "Japan"), "Sengoku period": ("ne", "Japan", "historical", "Japan"),
    "Edo period": ("ne", "Japan", "historical", "Japan"), "the Edo period": ("ne", "Japan", "historical", "Japan"),
    "the Kamakura period": ("ne", "Japan", "historical", "Japan"), "the Muromachi period": ("ne", "Japan", "historical", "Japan"),
    # historical states and periods with a clear home, placed at their capital or core country
    "Abbasid Caliphate": ("gn", "Baghdad", "IQ", "historical"), "the Abbasid Caliphate": ("gn", "Baghdad", "IQ", "historical"),
    "the Byzantine Empire": ("wd", "Byzantine Empire"), "the Roman Empire": ("wd", "Roman Empire"), "Roman Empire": ("wd", "Roman Empire"),
    "ancient Rome": ("wd", "Ancient Rome"), "ancient Greece": ("wd", "Ancient Greece"), "ancient Egypt": ("wd", "Ancient Egypt"),
    "ancient China": ("ne", "China", "historical", "China"), "Imperial China": ("ne", "China", "historical", "China"),
    "historical China": ("ne", "China", "historical", "China"), "the Han dynasty": ("ne", "China", "historical", "China"),
    "the Ming dynasty": ("wd", "Ming dynasty"), "the Qing dynasty": ("ne", "China", "historical", "China"),
    "the Song dynasty": ("ne", "China", "historical", "China"), "the Tang dynasty": ("ne", "China", "historical", "China"),
    "the Sui dynasty": ("ne", "China", "historical", "China"), "the Jin dynasty (1115–1234)": ("ne", "China", "historical", "China"),
    "the Yuan dynasty": ("ne", "China", "historical", "China"), "Yuan dynasty": ("ne", "China", "historical", "China"),
    "the Zhou dynasty": ("ne", "China", "historical", "China"), "the Three Kingdoms": ("ne", "China", "historical", "China"),
    "the Five Dynasties and Ten Kingdoms period": ("ne", "China", "historical", "China"),
    "the Mongol Empire": ("ne", "Mongolia", "historical", "Mongolia"), "the Ottoman Empire": ("wd", "Ottoman Empire"),
    "Ottoman Empire": ("wd", "Ottoman Empire"), "the Russian Empire": ("wd", "Russian Empire"), "the Soviet Union": ("wd", "Soviet Union"),
    "the Holy Roman Empire": ("ne", "Germany", "historical", "Holy Roman Empire"), "Holy Roman Empire": ("ne", "Germany", "historical", "Holy Roman Empire"),
    "the Sasanian Empire": ("ne", "Iran", "historical", "Sasanian Empire"), "the Ptolemaic Kingdom": ("wd", "Ancient Egypt"),
    "the Eighteenth Dynasty of Egypt": ("wd", "Ancient Egypt"), "the Nineteenth Dynasty of Egypt": ("wd", "Ancient Egypt"),
    "the Sikh Empire": ("gn", "Lahore", "PK", "historical"), "Sikh Empire": ("gn", "Lahore", "PK", "historical"),
    "East Germany": ("wd", "East Berlin"), "Yugoslavia": ("gn", "Belgrade", "RS", "historical"),
    "British Hong Kong": ("ne", "Hong Kong", "historical", "British Hong Kong"),
    "Thirteen Colonies": ("gn", "Philadelphia", "US", "historical"), "the Thirteen Colonies": ("gn", "Philadelphia", "US", "historical"),
    "the Italian Renaissance": ("wd", "Florence"), "medieval France": ("ne", "France", "historical", "France"),
    "medieval Scandinavia": ("wd", "Scandinavia"), "the Viking Age": ("wd", "Scandinavia"),
    # regions
    "Siberia": ("wd", "Siberia"), "Tibet": ("wd", "Tibet"), "Transylvania": ("wd", "Transylvania"), "Scandinavia": ("wd", "Scandinavia"),
    "New England": ("wd", "New England"), "the Middle East": ("wd", "Middle East"), "the Caribbean": ("wd", "Caribbean"),
    "the Arctic": ("wd", "Arctic"), "Antarctica": ("ne", "Antarctica"), "the Amazon": ("wd", "Amazon rainforest"),
    "Central America": ("broad", -86.0, 14.0), "Central Asia": ("broad", 66.0, 43.0), "South Asia": ("wd", "South Asia"),
    "Africa": ("wd", "Africa"), "Asia": ("wd", "Asia"), "Europe": ("wd", "Europe"), "North America": ("wd", "North America"),
    "South America": ("wd", "South America"), "Oceania": ("wd", "Insular Oceania"), "Korea": ("wd", "Korea"),
    "the Bermuda Triangle": ("wd", "Bermuda Triangle"), 
    "Corsica": ("gn", "Ajaccio", "FR", "region"), "Brittany": ("gn", "Rennes", "FR", "region"), "Île-de-France": ("wd", "Paris"),
    "Sicily": ("wd", "Sicily"), "Chechnya": ("gn", "Grozny", "RU", "region"), "Akihabara": ("wd", "Akihabara"),
    "Acre, Israel": ("wd", "Acre"), "Okinawa": ("wd", "Okinawa"), "Hawaii": ("wd", "Hawaii"), "Alaska": ("wd", "Alaska"),
    "Washington, D.C.": ("wd", "Washington, D.C."), "Palestine": ("wd", "Palestine"), 
    "the Falkland Islands": ("ne", "Falkland Is."), "Saba": ("ne", "Netherlands", "region", "Saba"),
    "Sint Eustatius": ("ne", "Netherlands", "region", "Sint Eustatius"), "Curaçao": ("ne", "Curaçao"),
    "Martinique": ("ne", "France", "region", "Martinique"), "Guadeloupe": ("ne", "France", "region", "Guadeloupe"),
    "French Polynesia": ("ne", "Fr. Polynesia"), "the Bahamas": ("ne", "Bahamas"), "the Cayman Islands": ("ne", "Cayman Is."),
    "the Marshall Islands": ("ne", "Marshall Is."), "the Solomon Islands": ("ne", "Solomon Is."),
    "the Federated States of Micronesia": ("ne", "Micronesia"), "Bermuda": ("ne", "Bermuda"), "Gibraltar": ("gn", "Gibraltar", "GI", "local"),
    "Macau": ("ne", "Macao"), "the Maldives": ("ne", "Maldives"), "Timor-Leste": ("ne", "Timor-Leste"),
    "the Democratic Republic of the Congo": ("ne", "Dem. Rep. Congo"), "the Republic of the Congo": ("ne", "Congo"),
    "the Dominican Republic": ("ne", "Dominican Rep."), "Bosnia and Herzegovina": ("ne", "Bosnia and Herz."),
    "the Czech Republic": ("ne", "Czechia"), "Saint Kitts and Nevis": ("ne", "St. Kitts and Nevis"),
    "Saint Vincent and the Grenadines": ("ne", "St. Vin. and Gren."), "São Tomé and Príncipe": ("ne", "São Tomé and Principe"),
    "Equatorial Guinea": ("ne", "Eq. Guinea"), "Antigua and Barbuda": ("ne", "Antigua and Barb."),
    "the United Arab Emirates": ("ne", "United Arab Emirates"), "Abu Dhabi": ("gn", "Abu Dhabi", "AE", "local"),
    "Saint Helena, Ascension and Tristan da Cunha": ("ne", "Saint Helena"), "Kolkata": ("gn", "Kolkata", "IN", "local"),
    "Karachi": ("gn", "Karachi", "PK", "local"), "Damascus": ("gn", "Damascus", "SY", "local"), "Baku": ("gn", "Baku", "AZ", "local"),
    "Caracas": ("gn", "Caracas", "VE", "local"), "Havana": ("gn", "Havana", "CU", "local"), "Lagos": ("wd", "Lagos"),
    "Vatican City": ("ne", "Vatican"), "Kosovo": ("ne", "Kosovo"), "Cape Verde": ("ne", "Cabo Verde"),
    "the Philippines": ("ne", "Philippines"), "the Netherlands": ("ne", "Netherlands"),
    "the United Kingdom": ("ne", "United Kingdom"), "the United States": ("ne", "United States of America"),
    "the Golden Age of Piracy": ("wd", "Caribbean"),
    # not real places, or no single place
    "Atlantis": ("skip", "mythical"), "the future": ("skip", "a time, not a place"), "a former country": ("skip", "container category"),
    "the Solar System": ("space", "Solar System"),
}
SPACE = {"outer space": "outer space", "Mars": "Mars", "the Moon": "Moon", "Titan (moon)": "Titan", "Venus": "Venus",
         "the Solar System": "Solar System", "spacecraft": "spacecraft"}
OTHER = {"abandoned buildings and structures", "amusement parks", "castles", "cemeteries", "circuses", "cities", "computers",
         "country houses", "factories", "forests", "heaven", "hell", "hotels", "islands", "jungles", "laboratories", "monasteries",
         "mountains", "museums", "national parks", "parks", "prison", "psychiatric hospitals", "schools", "secondary schools",
         "ships", "summer camps", "swamps", "towns", "trains", "uninhabited islands", "villages", "zoos", "the Colosseum",
         "the Crusades", "the Mesozoic", "the Middle Ages", "antiquity", "prehistory", "the Pleistocene", "the Stone Age",
         "the Renaissance", "dependent territories of the United Kingdom", "insular areas of the United States", "Overseas France",
         "underwater", "the future", "Atlantis"}
ORD = r"(\d+)(?:st|nd|rd|th)"


def era_of(s):
    """(from, to) years for a date-like phrase, or None."""
    m = re.fullmatch(r"(\d{4})", s)
    if m: y = int(m.group(1)); return (y, y)
    m = re.fullmatch(r"the (\d{3,4})0s", s)
    if m: y = int(m.group(1)) * 10; return (y, y + 9)
    m = re.fullmatch(r"the " + ORD + r" century( BC)?", s)
    if m:
        c = int(m.group(1))
        return (-(c * 100), -(c - 1) * 100 - 1) if m.group(2) else ((c - 1) * 100, c * 100 - 1)
    m = re.fullmatch(r"the " + ORD + r" millennium( BC)?", s)
    if m:
        c = int(m.group(1))
        return (-(c * 1000), -(c - 1) * 1000 - 1) if m.group(2) else ((c - 1) * 1000, c * 1000 - 1)
    return None


places = {}     # place id -> record
unplaced = collections.Counter()


def add_place(pid, rec):
    places.setdefault(pid, rec)
    return pid


def geocode(name, cat):
    """Return a place id, or None."""
    h = HAND.get(name)
    if h:
        if h[0] == "skip":
            return None
        if h[0] == "wd":
            k = WD_BY_LABEL.get(h[1])
            assert k, ("hand wd label not found", h[1])
            return k
        if h[0] == "gn":
            g = gn(h[1], h[2])
            if not g:
                print("hand list town not in cities15000:", h); return None
            return add_place("gn:" + name, {"label": name.replace("the ", "", 1) if name.startswith("the ") else name, "kind": h[3],
                                            "lon": g["lon"], "lat": g["lat"], "a3": NE.at(g["lon"], g["lat"]), "how": f"hand list: placed at {g['name']} (GeoNames)"})
        if h[0] == "ne":
            a3 = NE.by_name.get(h[1].lower()); assert a3, ("hand ne not found", h)
            if len(h) == 2:
                return country_place(a3)
            f = NE.feat[a3]
            return add_place("ne:" + a3 + ":" + h[3], {"label": h[3], "kind": h[2], "lon": f["lx"], "lat": f["ly"], "a3": a3,
                                                       "how": f"hand list: placed at the Natural Earth label point of {f['name']}"})
        if h[0] == "broad":
            return add_place("hand:" + name, {"label": name, "kind": "broad", "lon": h[1], "lat": h[2], "a3": "", "how": "hand list: rough centre"})
    cq = CAT_QID.get(cat)
    if cq in TOPIC:
        tq, tl, lon, lat = TOPIC[cq]
        if tq in WDP:
            return tq
    if name in WD_BY_LABEL:
        return WD_BY_LABEL[name]
    nm = name[4:] if name.startswith("the ") else name
    if nm in WD_COUNTRY_BY_LABEL:
        q = WD_COUNTRY_BY_LABEL[nm]
        if q in WDP:
            return q
        a3 = NE.by_wd.get(q) or NE.by_iso.get(WD_ISO.get(q, ""))
        if a3:
            return country_place(a3, q)
    if nm.lower() in NE.by_name:
        return country_place(NE.by_name[nm.lower()])
    g = gn(name)
    if g and g["pop"] >= 100000:
        return add_place("gn:" + name, {"label": name, "kind": "local", "lon": g["lon"], "lat": g["lat"], "a3": NE.at(g["lon"], g["lat"]),
                                        "how": f"GeoNames cities15000 exact name match (geonameid {g['gid']}, population {g['pop']:,})"})
    return None


def country_place(a3, q=None):
    # the same id as the Wikidata country place where one exists, so that the two sources merge
    for k, v in WDP.items():
        if v["kind"] == "country" and v["a3"] == a3:
            return k
    f = NE.feat[a3]
    return add_place(q or ("ne:" + a3), {"label": f["long"], "kind": "country", "lon": f["lx"], "lat": f["ly"], "a3": a3,
                                         "how": "Natural Earth country, label point"})


CONTAINER = re.compile(r".* by (country|city|region|prefecture|county|state or territory)$")
RX = re.compile(r"^Category:(?:(.+?) )?[Vv]ideo games set (in|on) (.+)$")
links, eras, space, catlog = [], [], [], []
for cat, members in CATS.items():
    m = RX.match(cat)
    if not m:
        continue
    prefix, prep, rest = m.groups()
    titles = [t for t in members if not t.startswith("C:")]
    games = sorted({PAGE_QID[t] for t in titles if t in PAGE_QID and PAGE_QID[t] in GAMES})
    era = era_of(rest)
    kind, pid, body, era2 = None, None, None, None
    if era:
        kind = "era"
    elif rest in SPACE:
        kind, body = "space", SPACE[rest]
    elif rest in OTHER or CONTAINER.match(rest):
        kind = "other"
    else:
        m2 = re.fullmatch(ORD + r"-century (.+)", rest)
        if m2:
            c = int(m2.group(1)); era2 = ((c - 1) * 100, c * 100 - 1); rest2 = m2.group(2)
        else:
            rest2 = rest
        pid = geocode(rest2, cat)
        if pid:
            kind = "place"
        elif rest2 in HAND and HAND[rest2][0] == "skip":
            kind = "other"
        else:
            kind = "unplaced"; unplaced[rest2] += len(games)
    catlog.append({"category": cat[9:], "kind": kind, "place_id": pid or "", "body": body or "",
                   "era": (f"{era[0]} to {era[1]}" if era else (f"{era2[0]} to {era2[1]}" if era2 else "")),
                   "members": len(titles), "games": len(games)})
    for g in games:
        if kind == "place":
            links.append((g, pid, cat[9:]))
        if era or era2:
            e = era or era2; eras.append((g, e[0], e[1], cat[9:]))
        if kind == "space":
            space.append((g, body, cat[9:]))

print("set-in categories", len(catlog), collections.Counter(c["kind"] for c in catlog))
print("unplaced:", unplaced.most_common())
print("links", len(links), "games", len({g for g, _, _ in links}), "eras", len({e[0] for e in eras}), "space", len({s[0] for s in space}))
json.dump(places, open(os.path.join(DATA, "interim", "wp_places.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
with open(os.path.join(DATA, "interim", "wp_links.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["game_qid", "place_id", "category"]); w.writerows(sorted(set(links)))
with open(os.path.join(DATA, "interim", "wp_eras.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["game_qid", "from", "to", "category"]); w.writerows(sorted(set(eras)))
with open(os.path.join(DATA, "interim", "wp_space.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["game_qid", "body", "category"]); w.writerows(sorted(set(space)))
with open(os.path.join(DATA, "interim", "wp_categories.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(catlog[0])); w.writeheader()
    for r in sorted(catlog, key=lambda r: r["category"]):
        w.writerow(r)
with open(os.path.join(DATA, "interim", "wp_unplaced.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["place_text", "games"]); w.writerows(unplaced.most_common())
