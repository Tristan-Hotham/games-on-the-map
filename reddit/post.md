## Title

[OC] Where 6,691 video games tied to real places are set, and where they were made: New York is the top setting (529 games), Japan to the USA is the busiest studio-to-setting route (467), and the Moon beats Mars 119 to 85

## Body (optional)

I combined Wikidata's "narrative location" for video games with English Wikipedia's "Video games set in..." categories, geocoded the places, and matched each game to its developer's headquarters. New York City leads (529), then London (288) and Tokyo (276). The USA, Japan and the UK made 69% of the games with a known maker. American and Japanese studios mostly set games at home (63% and 55%); British studios set more games in the USA than in Britain. None of the 295 games set in Egypt with a known maker was made there.

Caveat: this only covers games someone has documented in Wikidata or English Wikipedia (3.5% of video games in Wikidata), so famous Western and Japanese games dominate. I also set aside 202 Wikidata links that wrongly tag sports games with Washington, D.C.

Interactive version (map with studio-to-setting lines, filters by decade, and a space tab): https://maps.tristanhotham.com/games-on-the-map/

## Source comment

Source: Wikidata (CC0), video game items with narrative location (P840), developer (P178), headquarters location (P159) and country of origin (P495), queried through QLever on 28 October 2026; English Wikipedia category tree "Category:Video games by setting" (category names and page titles, English Wikipedia contributors, CC BY-SA 4.0); country outlines from Natural Earth 1:50m (public domain); town names and some locations from GeoNames cities15000 (CC BY 4.0).

Tools: Python (pandas, NumPy, shapely, pyproj, matplotlib), Leaflet for the interactive map.

Interactive: https://maps.tristanhotham.com/games-on-the-map/
Blog post: https://blog.tristanhotham.com/2026/10/28/games-on-the-map/
Paper: https://doi.org/10.5281/zenodo.23735822
