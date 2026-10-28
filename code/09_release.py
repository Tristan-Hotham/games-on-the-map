"""Step 9. Blog post (release/blog/post.html, meta.json) and Zenodo files (release/zenodo/).
Run after steps 1 to 8: python3 code/09_release.py
"""
import json, os, re, shutil, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, DATA, HERE
import importlib
site = importlib.import_module("06_build_site")
R = site.R
mc = R["made_count"]
R["made_share3"] = (mc["United States of America"] + mc["Japan"] + mc["United Kingdom"]) / R["made_cov"]["known"]
SLUG = "games-on-the-map"; DOI = "10.5281/zenodo.23735822"
PAGE = f"https://maps.tristanhotham.com/{SLUG}/"; REPO = f"https://github.com/Tristan-Hotham/{SLUG}"
PDF = "Hotham_Games_on_the_Map.pdf"

# facts stated in words in the blog only
tc = [r["name"] for r in R["top_cities"]]
assert R["city"]["Paris"] == R["city"]["San Francisco"] and tc.index("Washington, D.C.") == 7
assert R["space"]["by_body"]["Jupiter's moons"] == 2
site.checks()

# ---------- README
rd = open(os.path.join(HERE, "readme_template.md"), encoding="utf-8").read()
rd = re.sub(r"\{\{([^}|]+)(\|(\w+))?\}\}", lambda m: site.fmt(site.get(m.group(1)), m.group(3)), rd)
assert "{{" not in rd
open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8").write(rd)

# ---------- blog
t = open(os.path.join(HERE, "blog_template.html"), encoding="utf-8").read()
t = re.sub(r"\{\{(?!IMG\|)([^}|]+)(\|(\w+))?\}\}", lambda m: site.fmt(site.get(m.group(1)), m.group(3)), t)
BLOG = os.path.join(ROOT, "release", "blog")
for img in re.findall(r"\{\{IMG\|([^|]+)\|", t):
    assert os.path.exists(os.path.join(BLOG, img)), img
vis = re.sub(r"<!--.*?-->|<[^>]+>", " ", t, flags=re.S)
for bad in ("\u2014", "\u2013", "--"):
    assert bad not in vis, bad
open(os.path.join(BLOG, "post.html"), "w", encoding="utf-8").write(t)
words = len(re.sub(r"\{\{IMG\|[^}]*\}\}", " ", vis).split())
meta = {
    "title": "Where games are set, and where they are made",
    "slug": SLUG,
    "excerpt": f"A world map of {R['meta']['games_total']:,} video games tied to real places: where each is set and where its studio is based. New York leads, Japan to the United States is the busiest route, and the Moon beats Mars.",
    "seo_description": f"Where {R['meta']['games_total']:,} video games are set and where they were made, from Wikidata and Wikipedia, plus the games set in space.",
    "tags": ["video games", "maps", "Wikidata", "Wikipedia", "game development", "data visualisation", "space", "data"],
    "header_alt": f"Title card reading 'Where games are set, and where they are made' on warm paper, beside a world map with red dots where games are set and blue dots where their studios are based, and purple arcs from Japan and the UK to the United States. Text: {R['meta']['games_total']:,} games tied to real places; New York leads with {R['city']['New York City']}; Japan to the US is the busiest route ({R['flow']['Japan>United States of America']}); {R['space']['by_body']['Moon']} games on the Moon, {R['space']['by_body']['Mars']} on Mars.",
}
assert len(meta["seo_description"]) < 160
json.dump(meta, open(os.path.join(BLOG, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("post.html words", words)

# ---------- Zenodo
Z = os.path.join(ROOT, "release", "zenodo"); os.makedirs(Z, exist_ok=True)
shutil.copy(os.path.join(ROOT, "release", PDF), os.path.join(Z, PDF))
for f in ("games.csv", "places.csv", "links.csv", "space.csv", "eras.csv", "results.json"):
    shutil.copy(os.path.join(DATA, f), os.path.join(Z, f))
zp = os.path.join(Z, f"{SLUG}_code_and_data.zip")
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for base in ("code", "data"):
        for dp, dn, fn in os.walk(os.path.join(ROOT, base)):
            dn[:] = [d for d in dn if d not in ("__pycache__", "interim")]
            for f in fn:
                p = os.path.join(dp, f); z.write(p, os.path.relpath(p, ROOT))
    for f in ("README.md", "LICENSE"):
        z.write(os.path.join(ROOT, f), f)
abstract = open(os.path.join(ROOT, "release", "paper", PDF.replace(".pdf", ".tex")), encoding="utf-8").read()
ab = re.search(r"\\textbf\{Abstract\}\\end\{center\}\s*(.*?)\n\n", abstract, flags=re.S).group(1)
ab = ab.replace("\\%", "%").replace("``", "\u201c").replace("''", "\u201d").replace("\\&", "&")
zmeta = {
    "title": "Where Games Are Set, and Where They Are Made: Real Places in Video Games from Wikidata and English Wikipedia",
    "description_html": f"<p>{ab}</p><p>Interactive version: <a href=\"{PAGE}\">{PAGE}</a>. Data and code: <a href=\"{REPO}\">{REPO}</a>. Blog post: to follow.</p>",
    "keywords": ["video games", "setting", "game development", "cultural geography", "Wikidata", "Wikipedia categories", "geocoding", "data visualisation", "outer space", "maps"],
    "licence": "cc-by-sa-4.0",
    "related": [
        {"identifier": REPO, "relation": "issupplementedby", "resource_type": "software"},
        {"identifier": PAGE, "relation": "issupplementedby", "resource_type": "other"},
        {"identifier": "https://www.wikidata.org", "relation": "isderivedfrom", "resource_type": "dataset"},
        {"identifier": "https://en.wikipedia.org/wiki/Category:Video_games_by_setting", "relation": "isderivedfrom", "resource_type": "dataset"},
        {"identifier": "https://www.naturalearthdata.com", "relation": "isderivedfrom", "resource_type": "dataset"},
        {"identifier": "https://download.geonames.org/export/dump/", "relation": "isderivedfrom", "resource_type": "dataset"},
    ],
}
json.dump(zmeta, open(os.path.join(Z, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("zenodo files:", sorted(os.listdir(Z)), os.path.getsize(zp) // 1024, "KB zip")
