"""Shared helpers: paths, the TSV reader for the QLever tables, and Natural Earth country lookup."""
import gzip, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
BUNDLE = os.environ.get("GAMES_BUNDLE", "/home/claude/hist/_data15/games_bundle.json.gz")
NE = os.environ.get("NE", "/home/claude/hist/_data3/ne/geojson")
CITIES = os.environ.get("CITIES", "/home/claude/hist/_data13/cities15000.zip")
D13 = os.environ.get("D13", "/home/claude/hist/_data13")

WD = "http://www.wikidata.org/entity/"


def load_bundle():
    return json.load(gzip.open(BUNDLE))


def tsv(text):
    """QLever TSV: header row then rows. Returns (header, rows)."""
    lines = text.split("\n")
    head = [h.lstrip("?") for h in lines[0].split("\t")]
    return head, [l.split("\t") for l in lines[1:] if l]


def qid(x):
    """'<http://www.wikidata.org/entity/Q60>' -> 'Q60'; blank nodes and empty -> ''."""
    if not x or "genid" in x:
        return ""
    m = re.match(r"<http://www\.wikidata\.org/entity/(Q\d+)>", x)
    return m.group(1) if m else ""


def lit(x):
    """'"New York City"@en' -> 'New York City'; typed literals keep their value."""
    if not x:
        return ""
    m = re.match(r'^"(.*)"(?:@[\w-]+|\^\^<[^>]+>)?$', x, flags=re.S)
    s = m.group(1) if m else x
    return s.replace('\\"', '"').replace("\\\\", "\\")


def wkt(x):
    """Point coordinates. Earth: 'POINT(lon lat)'. Other globes: '"<...Q405> Point(lon lat)"^^...'.
    Returns (globe_qid or 'Q2', lon, lat) or None."""
    if not x:
        return None
    m = re.search(r"(?:<http://www\.wikidata\.org/entity/(Q\d+)>\s*)?Point\(([-\d.eE+]+)\s+([-\d.eE+]+)\)", x, flags=re.I)
    if not m:
        return None
    return (m.group(1) or "Q2", float(m.group(2)), float(m.group(3)))


class Countries:
    """Natural Earth 1:50m admin 0 polygons, keyed by ADM0_A3, with point-in-polygon lookup."""

    def __init__(self):
        from shapely.geometry import shape, Point
        from shapely.strtree import STRtree
        self.Point = Point
        g = json.load(open(os.path.join(NE, "ne_50m_admin_0_countries.geojson"), encoding="utf-8"))
        self.feat = {}
        geoms, keys = [], []
        for f in g["features"]:
            p = f["properties"]
            k = p["ADM0_A3"]
            self.feat[k] = {"a3": k, "name": p["NAME"], "long": p["NAME_LONG"], "admin": p["ADMIN"], "iso2": p["ISO_A2_EH"],
                            "wd": p.get("WIKIDATAID") or "", "lx": p["LABEL_X"], "ly": p["LABEL_Y"], "cont": p["CONTINENT"],
                            "sov": p["SOVEREIGNT"], "geom": shape(f["geometry"])}
            geoms.append(self.feat[k]["geom"]); keys.append(k)
        self.keys, self.geoms = keys, geoms
        self.tree = STRtree(geoms)
        self.by_wd = {v["wd"]: k for k, v in self.feat.items() if v["wd"]}
        self.by_iso = {}
        for k, v in self.feat.items():
            if v["iso2"] and v["iso2"] != "-99":
                # prefer the sovereign feature when a code repeats (e.g. AU for Indian Ocean Ter.)
                if v["iso2"] not in self.by_iso or v["admin"] == v["sov"]:
                    self.by_iso[v["iso2"]] = k
        self.by_name = {}
        for k, v in self.feat.items():
            for n in (v["name"], v["long"], v["admin"]):
                self.by_name.setdefault(n.lower(), k)

    def at(self, lon, lat, tol_deg=0.6):
        """Country containing the point; else the nearest within tol_deg (coasts, small islands)."""
        pt = self.Point(lon, lat)
        for i in self.tree.query(pt):
            if self.geoms[i].contains(pt):
                return self.keys[i]
        i = self.tree.nearest(pt)
        if self.geoms[i].distance(pt) <= tol_deg:
            return self.keys[i]
        return ""
