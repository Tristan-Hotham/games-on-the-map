"""Step 6. Build index.html from code/page_template.html.

Every number in the text is a {{path|format}} token filled from data/results.json, so the page cannot drift from the analysis.
Facts the template states in words are checked against the data below. The page fetches data/page.json, data/countries.json,
data/towns.json and data/hills.png.
Run: python3 code/06_build_site.py
"""
import json, os, re, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, DATA, HERE

R = json.load(open(os.path.join(DATA, "results.json"), encoding="utf-8"))


def get(path, obj=None):
    """Walk a dotted path; keys may themselves contain dots (e.g. 'city.Washington, D.C.')."""
    v = R if obj is None else obj
    parts = path.split(".")
    i = 0
    while i < len(parts):
        for j in range(len(parts), i, -1):
            k = ".".join(parts[i:j])
            if isinstance(v, list) and k.isdigit():
                v = v[int(k)]; i = j; break
            if isinstance(v, dict) and k in v:
                v = v[k]; i = j; break
        else:
            raise KeyError(path)
    return v


def fmt(v, f):
    if f is None or f == "raw": return str(v)
    if f == "int": return f"{round(v):,}"
    if f == "pct": return f"{round(v * 100)}%"
    if f == "pct1": return f"{v * 100:.1f}%"
    if f == "f1": return f"{v:.1f}"
    raise ValueError(f)


def fill(tpl):
    return re.sub(r"\{\{([^}|]+)(\|(\w+))?\}\}", lambda m: fmt(get(m.group(1)), m.group(3)), tpl)


def checks():
    """Facts stated in words in the page, paper, blog and collage."""
    c, s, m, f = R["city"], R["set_count"], R["made_count"], R["flow"]
    tc = [r["name"] for r in R["top_cities"]]
    assert tc[:6] == ["New York City", "London", "Tokyo", "Los Angeles", "Paris", "San Francisco"] or tc[:4] == ["New York City", "London", "Tokyo", "Los Angeles"], tc
    assert 1.7 < c["New York City"] / c["London"] < 2.0 and 1.7 < c["New York City"] / c["Tokyo"] < 2.0      # nearly twice
    assert c["Washington, D.C."] + R["meta"]["links_dc_sport"] > c["Tokyo"]                                  # would sit third
    assert 150 < R["meta"]["links_dc_sport"] < 250                                                          # about two hundred
    ts = [r["name"] for r in R["top_set_countries"]]
    assert ts[:8] == ["United States of America", "Japan", "United Kingdom", "France", "Italy", "Russia", "Germany", "China"], ts
    africa_me = {"Egypt", "Iraq", "Saudi Arabia", "Iran", "Israel", "Morocco", "South Africa", "Turkey", "Kenya", "Libya", "Afghanistan", "Syria"}
    assert next(n for n in ts if n in africa_me) == "Egypt"
    tm = [r["name"] for r in R["top_made_countries"]]
    assert tm[:5] == ["United States of America", "Japan", "United Kingdom", "France", "Canada"] and R["top_made_countries"][5]["games"] < 150
    assert (m["United States of America"] + m["Japan"] + m["United Kingdom"]) / R["made_cov"]["known"] > .6     # "most of the games"
    fl = [(r["made"], r["set"]) for r in R["flows_top"]]
    assert fl[0] == ("Japan", "United States of America") and fl[1] == ("United Kingdom", "United States of America")
    assert fl[2] == ("United States of America", "United Kingdom") and fl[3] == ("United States of America", "Russia")
    assert f["United Kingdom>United States of America"] > f["United Kingdom>United Kingdom"]
    h = R["home"]; assert h["usa"]["share_home"] > .5 and h["japan"]["share_home"] > .5 and all(h[k]["share_home"] < .4 for k in ("uk", "france", "canada", "sweden"))
    sp = R["spot"]
    assert sp["egypt"]["made_at_home"] == 0 and sp["monaco"]["made_at_home"] == 0
    assert all(sp[k]["share_local"] < .05 for k in ("mexico", "greece", "hk")) and all(sp[k]["share_local"] < .1 for k in ("italy", "germany", "russia", "china"))
    big = sorted(R["set_made_locally"], key=lambda r: -r["share_local"])
    assert [r["country"] for r in big[:2]] == ["Japan", "United States of America"] and big[0]["share_local"] > .4 and big[1]["share_local"] > .4
    assert {r["country"] for r in big[2:4]} == {"United Kingdom", "Poland"}
    t = R["trend"]; ss = R["share_series"]
    assert t["us_share_1990"] > t["us_share_2010"] > t["us_share_2020"]
    assert 1.75 < t["tokyo_2010"] / t["tokyo_1990"] < 2.0                                       # nearly doubled
    decs = ["1980", "1990", "2000", "2010", "2020"]
    assert max(decs, key=lambda d: ss["Los Angeles"][d]) == "1990"
    assert all(ss["Egypt"][a] > ss["Egypt"][b] for a, b in zip(decs[:3], decs[1:4]))                  # faded steadily, 1980s to 2010s
    assert max(decs, key=lambda d: ss["Moscow and the Soviet Union"][d]) == "1980"
    assert R["space"]["by_body"]["Moon"] > R["space"]["by_body"]["Mars"] and "Earth orbit" not in R["space"]["by_body"]
    assert R["space"]["by_body"]["Sun"] == 1 and R["space"]["by_body"]["Mercury"] == 1
    assert R["meta"]["earth_by_source"]["wikipedia"] > R["meta"]["earth_by_source"]["wikidata"]
    uk = R["uk"]
    assert [x[0] for x in uk["made_towns"][:5]] == ["London", "Coventry", "Derby", "Manchester", "Liverpool"], uk["made_towns"]
    assert uk["studios"][0][0] == "Codemasters"
    assert [x[0] for x in uk["top_places"][:4]] == ["London", "England", "Scotland", "Wales"]
    # Formula One games carry many places (the claim in the caveats)
    G = pd.read_csv(os.path.join(DATA, "games.csv"), keep_default_na=False); L = pd.read_csv(os.path.join(DATA, "links.csv"), keep_default_na=False)
    f1 = G[G.title.str.match(r"^(F1 20\d\d|F1 Manager|Formula One 0)")].qid
    n = L[(L.used == 1) & L.game_qid.isin(f1)].groupby("game_qid").place_id.nunique()
    assert len(n) >= 10 and n.median() >= 15, n.describe()
    R.setdefault("checks", {})["f1_median_places"] = float(n.median()); R["checks"]["f1_games"] = int(len(n))
    # Codemasters near Coventry; Core Design near Derby (the studio towns quoted)
    assert set(G[G.made_town == "Coventry"].developer.value_counts().index[:1]) == {"Codemasters"}
    assert G[G.made_town == "Derby"].developer.value_counts().index[0] == "Core Design"
    print("checks passed")


def dashfree(html):
    vis = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "", html, flags=re.S)
    vis = re.sub(r"<[^>]+>", " ", vis)
    for bad in ("—", "–", "--"):
        assert bad not in vis, (bad, vis[max(0, vis.find(bad) - 80):vis.find(bad) + 80])
    for scr in re.findall(r"<script>(.*?)</script>", html, flags=re.S):
        scr = re.sub(r"var\(--[\w-]+|\"--[\w-]+\"|i--|--\w", "", scr)
        for bad in ("—", "–", "--"):
            assert bad not in scr, (bad, scr[max(0, scr.find(bad) - 80):scr.find(bad) + 80])


if __name__ == "__main__":
    checks()
    json.dump(R, open(os.path.join(DATA, "results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tpl = open(os.path.join(HERE, "page_template.html"), encoding="utf-8").read()
    html = fill(tpl).replace("/*RESULTS*/", json.dumps(R, ensure_ascii=False, separators=(",", ":")))
    assert "{{" not in html
    dashfree(html)
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)
    print("index.html", len(html.encode()) // 1024, "KB")
