"""Step 4. Every number used in the page, paper, blog and collage, written to data/results.json.
Run: python3 code/04_analyse.py
"""
import collections, csv, json, os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA

rd = lambda n: pd.read_csv(os.path.join(DATA, n), keep_default_na=False, na_values=[""], dtype={"place_id": str})
G = rd("games.csv"); P = rd("places.csv"); L = rd("links.csv"); S = rd("space.csv"); E = rd("eras.csv")
WG = pd.read_csv(os.path.join(DATA, "interim", "wd_games.csv"), keep_default_na=False, usecols=["qid", "year", "enwiki"])
SK = rd(os.path.join("interim", "wd_skipped.csv"))
CATS = rd(os.path.join("interim", "wp_categories.csv"))
UNP = rd(os.path.join("interim", "wp_unplaced.csv"))

R = {}
G["dec"] = (G.year // 10 * 10).astype("Int64")
LU = L[L.used == 1].merge(P, on="place_id", how="left")
earth = G[G.set_on_earth == 1]
n_earth, n_space = len(earth), int((G.set_in_space == 1).sum())

# ---------- coverage
gsrc = L[L.used == 1].groupby("game_qid").source.agg(lambda s: set(s))
def src_kind(s):
    has_wd = bool(s & {"wikidata", "both"}); has_wp = bool(s & {"wikipedia", "both"})
    return "both" if has_wd and has_wp else ("wikidata" if has_wd else "wikipedia")
gk = gsrc.map(src_kind).value_counts()
R["meta"] = {
    "retrieved": "28 October 2026",
    "wikidata_games": len(WG),
    "wikidata_games_enwiki": int((WG.enwiki != "").sum()),
    "games_total": len(G), "games_earth": n_earth, "games_space": n_space,
    "games_earth_and_space": int(((G.set_on_earth == 1) & (G.set_in_space == 1)).sum()),
    "share_of_wikidata": len(G) / len(WG),
    "earth_by_source": {k: int(v) for k, v in gk.items()},
    "links_used": int((L.used == 1).sum()), "links_dc_sport": int(L.set_aside_because.str.startswith("probable Wikidata error").sum()), "links_set_aside": int((L.used == 0).sum()),
    "links_used_by_source": {k: int(v) for k, v in L[L.used == 1].source.value_counts().items()},
    "places": int(P[P.kind != "space"].shape[0]),
    "places_dots": int(P.kind.isin(["local", "region", "historical"]).sum()),
    "places_cities": int((P.kind == "local").sum()),
    "countries_set": int(LU[LU.country_a3.notna()].country_a3.nunique()),
    "countries_made": int(G[G.made_country_a3.notna()].made_country_a3.nunique()),
    "wd_fictional_places": int(len(SK)), "wd_fictional_links": int(SK.games.sum()),
    "wd_fictional_top": SK.sort_values("games", ascending=False).head(8)[["label", "games"]].to_dict("records"),
    "wp_categories": int(len(CATS)), "wp_categories_place": int((CATS.kind == "place").sum()),
    "wp_categories_era": int((CATS.kind == "era").sum()), "wp_categories_space": int((CATS.kind == "space").sum()),
    "wp_categories_other": int((CATS.kind == "other").sum()), "wp_unplaced": UNP.to_dict("records"),
    "with_year": int(G.year.notna().sum()), "year_min": int(G.year.min()), "year_max": int(G.year.max()),
    "earth_with_enwiki": int((earth.enwiki.notna()).sum()),
}
mh = earth.made_how.value_counts()
R["made_cov"] = {"known": int(earth.made_how.notna().sum()), "share": float(earth.made_how.notna().mean()),
                 "hq": int(mh.get("developer HQ", 0)), "dev_country": int(mh.get("developer country", 0)),
                 "origin": int(mh.get("country of origin", 0)), "unknown": int(earth.made_how.isna().sum())}

# ---------- where set
def games_by(df, col):
    return df.groupby(col).game_qid.nunique().sort_values(ascending=False)
cities = games_by(LU[LU.kind == "local"], "label")
R["top_cities"] = [{"name": k, "games": int(v), "country": LU[LU.label == k].country.iloc[0]} for k, v in cities.head(20).items()]
places_all = games_by(LU[LU.kind.isin(["local", "region"])], "label")
R["top_places"] = [{"name": k, "games": int(v)} for k, v in places_all.head(20).items()]
cset = games_by(LU[LU.country.notna()], "country")
R["top_set_countries"] = [{"name": k, "games": int(v), "share": v / n_earth} for k, v in cset.head(20).items()]
cmade = earth[earth.made_country.notna()].groupby("made_country").qid.nunique().sort_values(ascending=False)
R["top_made_countries"] = [{"name": k, "games": int(v), "share": v / R["made_cov"]["known"]} for k, v in cmade.head(20).items()]
towns = earth[earth.made_town.notna()].groupby(["made_town", "made_country"]).qid.nunique().sort_values(ascending=False)
R["top_made_towns"] = [{"name": a, "country": b, "games": int(v)} for (a, b), v in towns.head(15).items()]
studios = earth[earth.developer.notna()].groupby("developer").qid.nunique().sort_values(ascending=False)
R["top_studios"] = [{"name": k, "games": int(v)} for k, v in studios.head(15).items()]
broad_only = set(LU.groupby("game_qid").kind.agg(lambda s: set(s) == {"broad"}).pipe(lambda s: s[s].index))
R["meta"]["games_broad_only"] = len(broad_only)

# ---------- made to set
F = LU[LU.country.notna()][["game_qid", "country", "country_a3"]].drop_duplicates()
F = F.merge(G[["qid", "made_country", "made_country_a3", "year", "dec"]], left_on="game_qid", right_on="qid")
F = F[F.made_country.notna()]
pairs = F.groupby(["made_country", "country"]).game_qid.nunique().sort_values(ascending=False)
cross = pairs[[a != b for a, b in pairs.index]]
R["flows_top"] = [{"made": a, "set": b, "games": int(v)} for (a, b), v in cross.head(20).items()]
R["flows_home_top"] = [{"made": a, "set": b, "games": int(v)} for (a, b), v in pairs[[a == b for a, b in pairs.index]].head(10).items()]
R["n_games_with_both_ends"] = int(F.game_qid.nunique())
home = []
for c, grp in F.groupby("made_country"):
    n = grp.game_qid.nunique()
    if n < 40:
        continue
    h = grp[grp.country == c].game_qid.nunique()
    home.append({"country": c, "games": int(n), "home": int(h), "share_home": h / n,
                 "top_abroad": (grp[grp.country != c].groupby("country").game_qid.nunique().sort_values(ascending=False).head(3).index.tolist())})
home.sort(key=lambda r: -r["share_home"])
R["home_share"] = home
# set there, made elsewhere: countries that are often a setting but rarely make the games set in them
setters = []
for c, grp in F.groupby("country"):
    n = grp.game_qid.nunique()
    if n < 60:
        continue
    local = grp[grp.made_country == c].game_qid.nunique()
    setters.append({"country": c, "games": int(n), "made_at_home": int(local), "share_local": local / n,
                    "top_makers": grp[grp.made_country != c].groupby("made_country").game_qid.nunique().sort_values(ascending=False).head(3).index.tolist()})
setters.sort(key=lambda r: r["share_local"])
R["set_made_locally"] = setters
MAKERS = ["United States of America", "Japan", "United Kingdom", "France", "Canada", "Sweden"]
SETS = ["United States of America", "Japan", "United Kingdom", "France", "Italy", "Russia", "Germany", "China", "Egypt"]
R["matrix"] = {"makers": MAKERS, "sets": SETS, "n": [[int(pairs.get((m, c), 0)) for c in SETS] for m in MAKERS]}
# the US share of settings, by maker
R["us_share_by_maker"] = {c: float(F[F.made_country == c].groupby("game_qid").country.agg(lambda s: "United States of America" in set(s)).mean())
                          for c in ["Japan", "United Kingdom", "France", "Canada", "United States of America", "Germany", "Sweden"]}

# ---------- by release decade
decs = [1970, 1980, 1990, 2000, 2010, 2020]
bydec = {}
for d in decs:
    eg = earth[earth.dec == d].qid
    sub = LU[LU.game_qid.isin(eg)]
    c = games_by(sub[sub.kind == "local"], "label")
    k = games_by(sub[sub.country.notna()], "country")
    bydec[str(d)] = {"games": int(len(eg)), "top_cities": [[a, int(b)] for a, b in c.head(5).items()],
                     "top_countries": [[a, int(b)] for a, b in k.head(5).items()],
                     "us_share": float(sub[sub.country == "United States of America"].game_qid.nunique() / max(1, len(eg))),
                     "space": int(G[(G.dec == d) & (G.set_in_space == 1)].shape[0])}
R["by_decade"] = bydec
R["earth_no_year"] = int(earth.year.isna().sum())

def series(label=None, labels=None, country=None):
    sub = LU
    if labels: sub = sub[sub.label.isin(labels)]
    if country: sub = sub[sub.country == country]
    s = sub[["game_qid"]].drop_duplicates().merge(G[["qid", "dec"]], left_on="game_qid", right_on="qid")
    return {str(d): int((s.dec == d).sum()) for d in decs}
R["series"] = {
    "Moscow and the Soviet Union": series(labels=["Moscow", "Soviet Union", "Russian Soviet Federative Socialist Republic"]),
    "Los Angeles": series(labels=["Los Angeles"]),
    "New York City": series(labels=["New York City", "Manhattan", "Brooklyn", "Queens"]),
    "Tokyo": series(labels=["Tokyo", "Shinjuku", "Shibuya", "Akihabara", "Sumida", "Machida", "Higashi-Nakano"]),
    "London": series(labels=["London", "Whitechapel"]),
    "Egypt": series(country="Egypt"),
}
R["share_series"] = {k: {d: v[d] / bydec[d]["games"] for d in v} for k, v in R["series"].items()}

# ---------- setting era (Wikipedia period categories)
E["mid"] = (E["from"] + E["to"]) / 2
eg = E.groupby("game_qid").agg(lo=("from", "min"), hi=("to", "max")).reset_index()
eg = eg.merge(G[["qid", "year"]], left_on="game_qid", right_on="qid", how="left")
R["era"] = {
    "games": int(len(eg)),
    "ww2": int(E[(E["from"] >= 1939) & (E["to"] <= 1945)].game_qid.nunique()),
    "ww1": int(E[(E["from"] >= 1914) & (E["to"] <= 1918)].game_qid.nunique()),
    "cold_war": int(E[(E["from"] >= 1947) & (E["to"] <= 1991)].game_qid.nunique()),
    "future_2027": int(E[E["from"] >= 2027].game_qid.nunique()),
    "before_1500": int(E[E["to"] < 1500].game_qid.nunique()),
    "year_1944": int(E[(E["from"] == 1944) & (E["to"] == 1944)].game_qid.nunique()),
}
cw = E[(E["from"] >= 1947) & (E["to"] <= 1991)].game_qid.unique()
sub = LU[LU.game_qid.isin(cw) & LU.country.notna()]
R["era"]["cold_war_top_countries"] = [[a, int(b)] for a, b in games_by(sub, "country").head(5).items()]
yr = E[(E["from"] == E["to"])]
R["era"]["year_top"] = [[int(a), int(b)] for a, b in yr.groupby("from").game_qid.nunique().sort_values(ascending=False).head(6).items()]
ER = [(-100000, 499, "Before 500"), (500, 1499, "500 to 1499"), (1500, 1799, "1500 to 1799"), (1800, 1913, "1800 to 1913"),
      (1914, 1945, "1914 to 1945"), (1946, 1991, "1946 to 1991"), (1992, 2026, "1992 to 2026"), (2027, 100000, "2027 and later")]
R["era_bins"] = [{"label": lab, "from": a, "to": b, "games": int(E[(E["to"] >= a) & (E["from"] <= b)].game_qid.nunique())} for a, b, lab in ER]

# ---------- the UK
uk = LU[LU.country == "United Kingdom"]
R["uk"] = {
    "set": int(uk.game_qid.nunique()),
    "set_share": uk.game_qid.nunique() / n_earth,
    "top_places": [[a, int(b)] for a, b in games_by(uk[uk.kind.isin(["local", "region"])], "label").head(10).items()],
    "made": int(cmade.get("United Kingdom", 0)),
    "made_towns": [[a, int(b)] for (a, c), b in towns.items() if c == "United Kingdom"][:8],
    "studios": [[a, int(b)] for a, b in earth[earth.made_country == "United Kingdom"].groupby("developer").qid.nunique().sort_values(ascending=False).head(8).items()],
}
ukm = F[F.made_country == "United Kingdom"]
R["uk"]["made_set_where"] = [[a, int(b)] for a, b in ukm.groupby("country").game_qid.nunique().sort_values(ascending=False).head(8).items()]
R["uk"]["made_home_share"] = next(r["share_home"] for r in home if r["country"] == "United Kingdom")
ukset = F[F.country == "United Kingdom"]
R["uk"]["set_made_by"] = [[a, int(b)] for a, b in ukset.groupby("made_country").game_qid.nunique().sort_values(ascending=False).head(6).items()]
R["uk"]["set_made_at_home_share"] = ukset[ukset.made_country == "United Kingdom"].game_qid.nunique() / max(1, ukset.game_qid.nunique())
R["uk"]["nations"] = {n: int(LU[LU.label == n].game_qid.nunique()) for n in ["England", "Scotland", "Wales", "Northern Ireland"]}

# ---------- space
sp = S.merge(G[["qid", "title", "year", "dec"]], left_on="game_qid", right_on="qid")
R["space"] = {
    "games": n_space,
    "by_body": {k: int(v) for k, v in sp.groupby("body_group").game_qid.nunique().sort_values(ascending=False).items()},
    "moon_by_decade": {str(d): int(sp[(sp.body_group == "Moon") & (sp.dec == d)].game_qid.nunique()) for d in decs},
    "mars_by_decade": {str(d): int(sp[(sp.body_group == "Mars") & (sp.dec == d)].game_qid.nunique()) for d in decs},
    "moon_first": sp[sp.body_group == "Moon"].sort_values("year").head(3)[["title", "year"]].to_dict("records"),
    "mars_first": sp[sp.body_group == "Mars"].sort_values("year").head(3)[["title", "year"]].to_dict("records"),
    "small_bodies": sp[sp.body_group.isin(["Venus", "Jupiter's moons", "Mercury", "Sun", "Titan"])].sort_values(["body_group", "year"])[["body_group", "bodies", "title", "year"]].to_dict("records"),
    "by_source": {k: int(v) for k, v in S.source.value_counts().items()},
}
R["space"]["moon_vs_mars"] = R["space"]["by_body"]["Moon"] / R["space"]["by_body"]["Mars"]
for k in ("moon_first", "mars_first", "small_bodies"):
    for r in R["space"][k]:
        r["year"] = int(r["year"]) if pd.notna(r["year"]) else None

# ---------- named spots used in the text (looked up by name so the wording cannot drift)
SM = {r["country"]: r for r in setters}
HM = {r["country"]: r for r in home}
R["spot"] = {k: SM[v] for k, v in {"egypt": "Egypt", "monaco": "Monaco", "belgium": "Belgium", "mexico": "Mexico", "japan": "Japan",
                                     "uk": "United Kingdom", "usa": "United States of America", "russia": "Russia", "italy": "Italy",
                                     "germany": "Germany", "china": "China", "france": "France", "canada": "Canada", "greece": "Greece",
                                     "hk": "Hong Kong", "antarctica": "Antarctica"}.items()}
R["home"] = {k: HM[v] for k, v in {"usa": "United States of America", "japan": "Japan", "uk": "United Kingdom", "france": "France",
                                    "canada": "Canada", "sweden": "Sweden", "germany": "Germany", "poland": "Poland", "australia": "Australia"}.items()}
R["set_count"] = {k: int(v) for k, v in cset.items()}
R["made_count"] = {k: int(v) for k, v in cmade.items()}
R["city"] = {r["name"]: r["games"] for r in R["top_cities"]}
R["place"] = {k: int(v) for k, v in places_all.head(80).items()}
R["flow"] = {f'{r["made"]}>{r["set"]}': r["games"] for r in R["flows_top"]}
R["flow"].update({f'{r["made"]}>{r["set"]}': r["games"] for r in R["flows_home_top"]})
d = R["by_decade"]
R["trend"] = {"us_share_1990": d["1990"]["us_share"], "us_share_2020": d["2020"]["us_share"], "us_share_2000": d["2000"]["us_share"],
              "us_share_2010": d["2010"]["us_share"], "tokyo_1990": R["share_series"]["Tokyo"]["1990"], "tokyo_2010": R["share_series"]["Tokyo"]["2010"],
              "la_1990": R["share_series"]["Los Angeles"]["1990"], "la_2010": R["share_series"]["Los Angeles"]["2010"],
              "moscow_2000": R["series"]["Moscow and the Soviet Union"]["2000"], "moscow_1980": R["share_series"]["Moscow and the Soviet Union"]["1980"],
              "moscow_2020": R["share_series"]["Moscow and the Soviet Union"]["2020"], "egypt_1980": R["share_series"]["Egypt"]["1980"], "egypt_1990": R["share_series"]["Egypt"]["1990"],
              "egypt_2010": R["share_series"]["Egypt"]["2010"]}

# ---------- headline checks used in words
R["checks"] = {
    "nyc_top": R["top_cities"][0]["name"] == "New York City",
    "japan_to_us_top_flow": R["flows_top"][0]["made"] == "Japan" and R["flows_top"][0]["set"] == "United States of America",
}
json.dump(R, open(os.path.join(DATA, "results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: int(o) if hasattr(o, "__int__") else str(o))
print(json.dumps({k: R[k] for k in ("meta", "made_cov")}, indent=0, default=str)[:3000])
print("cities", [(r["name"], r["games"]) for r in R["top_cities"][:12]])
print("set", [(r["name"], r["games"]) for r in R["top_set_countries"][:12]])
print("made", [(r["name"], r["games"]) for r in R["top_made_countries"][:12]])
print("flows", [(r["made"], r["set"], r["games"]) for r in R["flows_top"][:12]])
print("home", [(r["country"], r["games"], round(r["share_home"], 2)) for r in home])
print("setters", [(r["country"], r["games"], round(r["share_local"], 2), r["top_makers"]) for r in setters])
print("us share by maker", R["us_share_by_maker"])
print("decades", json.dumps(bydec)[:2500])
print("series", R["series"])
print("era", R["era"], R["era_bins"])
print("uk", R["uk"])
print("space", R["space"])
