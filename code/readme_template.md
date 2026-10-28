# Where games are set, and where they are made

A world map of video games tied to real places: where each game is set, where the studio that made it is based, and the games set on the Moon, Mars and elsewhere in space. Built from Wikidata and English Wikipedia's "video games set in" categories.

Interactive version: https://maps.tristanhotham.com/games-on-the-map/
Paper: https://doi.org/10.5281/zenodo.23735822
Blog post: https://blog.tristanhotham.com/2026/10/28/games-on-the-map/

## Headline results

- {{meta.games_total|int}} games tied to a real place ({{meta.games_earth|int}} on Earth, {{meta.games_space|int}} in space), {{meta.share_of_wikidata|pct1}} of the {{meta.wikidata_games|int}} video games in Wikidata.
- New York City is the most used setting ({{city.New York City|int}} games), then London ({{city.London|int}}), Tokyo ({{city.Tokyo|int}}), Los Angeles ({{city.Los Angeles|int}}), Paris and San Francisco ({{city.Paris|int}} each).
- The United States is a setting for {{top_set_countries.0.share|pct}} of Earth-set games; Japan ({{set_count.Japan|int}}) and the United Kingdom ({{set_count.United Kingdom|int}}) follow.
- The United States, Japan and the United Kingdom made {{made_share3|pct}} of the {{made_cov.known|int}} games with a known maker.
- Busiest route from studio country to setting country: Japan to the United States ({{flow.Japan>United States of America|int}} games), then the UK to the US ({{flow.United Kingdom>United States of America|int}}) and the US to the UK ({{flow.United States of America>United Kingdom|int}}).
- American studios set {{home.usa.share_home|pct}} of their games at home, Japanese {{home.japan.share_home|pct}}, British {{home.uk.share_home|pct}}. None of the {{spot.egypt.games|int}} games set in Egypt with a known maker was made in Egypt.
- The US share of settings falls from {{trend.us_share_1990|pct}} of 1990s releases to {{trend.us_share_2020|pct}} of 2020s releases so far; Tokyo's share nearly doubled from the 1990s to the 2010s.
- Space: the Moon {{space.by_body.Moon|int}} games, Mars {{space.by_body.Mars|int}}, Titan {{space.by_body.Titan|int}}, Venus {{space.by_body.Venus|int}}; {{space.by_body.Outer space|int}} in outer space generally.
- Data problem found and handled: {{meta.links_dc_sport|int}} Wikidata links tie league sports games to Washington, D.C.; they are set aside (kept in links.csv with the reason).

## Files

- `index.html`: the interactive page (Leaflet; loads `data/page.json`, `data/countries.json`, `data/towns.json`, `data/hills.png`).
- `data/games.csv`: every game in the study, with release year, developer, where made and how that is known.
- `data/places.csv`: every place used as a setting, with level, coordinates, country and where the location came from.
- `data/links.csv`: every game and place link, its source (wikidata, wikipedia, both), whether it is used, and if not why.
- `data/space.csv`: games set in space, by body. `data/eras.csv`: setting periods from Wikipedia category names.
- `data/results.json`: every number used in the page, paper, blog and collage.
- `code/`: the pipeline (see below). `release/`: paper, blog post and figures, Zenodo files. `reddit/`: collage and post text.

## How to rerun

Python 3 with pandas, numpy, shapely, pyproj, Pillow and matplotlib; xelatex for the paper. The source bundle (Wikidata via QLever and the Wikipedia category tree, retrieved 28 October 2026) is read from `GAMES_BUNDLE`; Natural Earth from `NE`; GeoNames cities15000 from `CITIES`; AWS terrain tiles from `D13`.

```
python3 code/01_wikidata.py     # Wikidata tables -> data/interim/
python3 code/02_wikipedia.py    # parse and geocode the Wikipedia categories
python3 code/03_merge.py        # merge, most specific place, where made -> data/*.csv
python3 code/04_analyse.py      # data/results.json
python3 code/05_page_data.py    # page data, countries, towns, hill shading
python3 code/06_build_site.py   # index.html (with checks of every fact stated in words)
python3 code/07_figures.py      # blog and paper figures, header.png
python3 code/08_paper.py        # paper PDF
python3 code/09_release.py      # blog post, Zenodo files
python3 reddit/collage.py       # Reddit collage
```

## Caveats

Coverage is partial and uneven: most games have no setting recorded, and the data favour well-known games and English Wikipedia's interests. Sports games carry many links. Regions are shown as points. "Where made" is the developer's headquarters as recorded today. Fictional stand-ins for real places are not counted.

## Sources and licences

- Wikidata (CC0), queried through QLever (University of Freiburg), 28 October 2026.
- English Wikipedia, Category:Video games by setting: category names and page titles, English Wikipedia contributors, CC BY-SA 4.0.
- Natural Earth 1:50m admin 0 countries (public domain). GeoNames cities15000 (CC BY 4.0).
- Hill shading computed from AWS Terrain Tiles (Mapzen terrarium). Optional base maps on the page: Tiles © Esri.

Text, figures and derived data: CC BY-SA 4.0. Code: MIT. See LICENSE.

## Citation

Hotham, T. (2026) Where games are set, and where they are made: real places in video games from Wikidata and English Wikipedia. Zenodo. https://doi.org/10.5281/zenodo.23735822

Dr Tristan Hotham, Independent researcher, ORCID 0000-0003-4931-9349.

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
