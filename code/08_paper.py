"""Step 8. Build the paper PDF: fill code/paper_template.tex from data/results.json, write
release/paper/Hotham_Games_on_the_Map.tex and compile it with xelatex (figures from step 7).
Run: python3 code/08_paper.py
"""
import json, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, DATA, HERE
import importlib
site = importlib.import_module("06_build_site")

R = site.R
OUT = os.path.join(ROOT, "release", "paper"); NAME = "Hotham_Games_on_the_Map"
mc = R["made_count"]
R["made_share3"] = (mc["United States of America"] + mc["Japan"] + mc["United Kingdom"]) / R["made_cov"]["known"]
H = {r["country"]: r for r in R["home_share"]}
R["home_italy_games"] = H["Italy"]["games"]; R["home_china_games"] = H["China"]["games"]
# facts stated in words in the paper only
assert [r["name"] for r in R["top_made_towns"][:4]] == ["Tokyo", "Osaka", "Paris", "Seattle"], R["top_made_towns"][:5]
sb = {(r["bodies"], r["title"], r["year"]) for r in R["space"]["small_bodies"]}
assert ("Io", "Dropzone", 1984) in sb and ("Callisto", "The Callisto Protocol", 2022) in sb
assert H["Italy"]["games"] < 100 and H["China"]["games"] < 100
assert all(H[c]["top_abroad"][0] == "United States of America" for c in ("Japan", "United Kingdom", "Canada"))
site.checks()

tex = lambda s: str(s).replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#").replace("$", "\\$")


def fmt(v, f):
    if f == "int": return f"{int(round(v)):,}"
    if f == "pct": return f"{v * 100:.0f}\\%"
    if f == "pct1": return f"{v * 100:.1f}\\%"
    if f == "f1": return f"{v:.1f}"
    return tex(str(v))


def sub(m):
    path, _, f = m.group(1).partition("|")
    return fmt(site.get(path.strip()), f.strip() or "raw")


m = R["meta"]; lb = m["links_used_by_source"]; eb = m["earth_by_source"]; sb2 = R["space"]["by_source"]
TS = ("\\begin{table}[tbp]\\centering\\small\\caption{What each source contributes. Games are counted by the sources of their used Earth links; "
      "links are game and place pairs; space rows are game and body pairs.}\\label{tab:sources}"
      "\\begin{tabular}{lrrr}\\toprule & Wikidata only & Wikipedia only & Both\\\\\\midrule\n"
      f"Games set on Earth & {eb['wikidata']:,} & {eb['wikipedia']:,} & {eb['both']:,}\\\\\n"
      f"Game and place links used & {lb['wikidata']:,} & {lb['wikipedia']:,} & {lb['both']:,}\\\\\n"
      f"Game and space body pairs & {sb2['wikidata']:,} & {sb2['wikipedia']:,} & {sb2['both']:,}\\\\\n"
      "\\bottomrule\\end{tabular}\\end{table}")
SM = {r["country"]: r for r in R["set_made_locally"]}
short = lambda n: {"United States of America": "United States"}.get(n, n)
rows = ""
for r in R["top_set_countries"][:14]:
    n = r["name"]; s = SM.get(n)
    rows += (f"{tex(short(n))} & {r['games']:,} & {r['share'] * 100:.1f} & {mc.get(n, 0):,} & "
             + (f"{s['share_local'] * 100:.0f}" if s else "") + "\\\\\n")
TC = ("\\begin{table}[tbp]\\centering\\small\\caption{The fourteen most used setting countries: games set there, their share of all Earth-set games, "
      "placed games made there, and the share of the games set there (with a known maker) that were made there.}\\label{tab:countries}"
      "\\begin{tabular}{lrrrr}\\toprule Country & Set there & \\% of games & Made there & \\% made locally\\\\\\midrule\n" + rows +
      "\\bottomrule\\end{tabular}\\end{table}")
t = open(os.path.join(HERE, "paper_template.tex"), encoding="utf-8").read()
t = re.sub(r"\{\{(?!TABLE_)(.+?)\}\}", sub, t).replace("{{TABLE_SOURCES}}", TS).replace("{{TABLE_COUNTRIES}}", TC)
assert "{{" not in t and "--" not in t and "—" not in t and "–" not in t
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, NAME + ".tex"), "w", encoding="utf-8").write(t)
for _ in range(2):
    r = subprocess.run(["xelatex", "-interaction=nonstopmode", NAME + ".tex"], cwd=OUT, capture_output=True, text=True)
for ext in (".aux", ".log", ".out"):
    p = os.path.join(OUT, NAME + ext)
    if os.path.exists(p): os.remove(p)
shutil.copy(os.path.join(OUT, NAME + ".pdf"), os.path.join(ROOT, "release", NAME + ".pdf"))
txt = subprocess.run(["pdftotext", os.path.join(OUT, NAME + ".pdf"), "-"], capture_output=True, text=True).stdout
print("paper written", r.returncode, "words", len(txt.split()), "dashes", txt.count("—") + txt.count("–") + txt.count("--"))
