#!/usr/bin/env python3
"""Build the static, crawlable SnowSignal ski-resort directory.

The source catalogue remains the app's reviewed CSV. This creates one HTML page
per active resort, a country-filterable directory, and a sitemap suitable for
GitHub Pages. Run from this repository after a reviewed catalogue update:

    python tools/build_resort_pages.py ../ski-snow-forecast/data/resorts_v1.csv
"""

from __future__ import annotations

import csv
import html
import json
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote


SITE_URL = "https://snowsignalapp.github.io"
APP_STORE_URL = "https://apps.apple.com/app/id6819308659"
ROOT = Path(__file__).resolve().parents[1]


def text(value: str | None) -> str:
    return html.escape((value or "").strip(), quote=True)


def number(value: str | None, suffix: str = "") -> str:
    if not value:
        return "Not published"
    try:
        rendered = f"{float(value):,.0f}" if float(value).is_integer() else f"{float(value):,.1f}"
    except ValueError:
        rendered = value
    return f"{rendered}{suffix}"


def directory_page(resorts: list[dict[str, str]]) -> str:
    countries = sorted({row["country"] for row in resorts})
    country_options = "\n".join(f'<option value="{text(country)}">{text(country)}</option>' for country in countries)
    entries = "\n".join(
        f'''<li class="resort-directory-item" data-country="{text(row['country'])}" data-search="{text(' '.join((row['name'], row['country'], row['region'], row['locality'])).lower())}">
          <a href="{text(row['slug'])}.html"><strong>{text(row['name'])}</strong><span>{text(row['country'])}{' · ' + text(row['region']) if row['region'] else ''}</span></a>
        </li>'''
        for row in resorts
    )
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Browse {len(resorts):,} ski resorts by country. Open a resort for mapped terrain, elevation, official links and SnowSignal forecast guidance.">
  <link rel="canonical" href="{SITE_URL}/resorts/">
  <meta property="og:type" content="website"><meta property="og:title" content="Ski resort directory | SnowSignal"><meta property="og:description" content="Browse worldwide ski resorts by country and plan with SnowSignal."><meta property="og:url" content="{SITE_URL}/resorts/"><meta property="og:image" content="{SITE_URL}/snow-signal-logo.png">
  <meta name="twitter:card" content="summary">
  <title>Ski Resort Directory by Country | SnowSignal</title>
  <link rel="icon" type="image/png" href="../snow-signal-logo.png"><link rel="stylesheet" href="../site.css?v=20261101-resorts">
</head>
<body>
  <header class="site-header"><nav class="nav shell" aria-label="Main navigation"><a class="brand" href="../index.html"><img src="../snow-signal-logo.png" alt="">SnowSignal</a><div class="nav-links"><a href="{APP_STORE_URL}">Explore in SnowSignal</a><a href="{APP_STORE_URL}">Download for iPhone</a></div></nav></header>
  <main class="resort-directory shell">
    <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../index.html">Home</a><span aria-hidden="true">/</span><span>Ski resorts</span></nav>
    <h1>Find a ski resort.</h1>
    <p class="lead">Browse our published worldwide catalogue by country, then open a resort for mountain facts, mapped terrain and forecast guidance in SnowSignal.</p>
    <div class="directory-controls" aria-label="Filter ski resorts"><label>Search resorts<input id="resort-search" type="search" placeholder="e.g. Val Thorens or Japan" autocomplete="off"></label><label>Country<select id="country-filter"><option value="">All countries</option>{country_options}</select></label></div>
    <p id="directory-count" class="directory-count" aria-live="polite">Showing {len(resorts):,} resorts</p>
    <ul id="resort-list" class="resort-directory-list">{entries}</ul>
    <noscript><p class="directory-note">Use your browser’s find feature to search this complete alphabetical list.</p></noscript>
  </main>
  <footer><div class="footer-row shell"><span>© 2026 SnowSignal</span><div class="footer-links"><a href="../data.html">Data and sources</a><a href="../privacy.html">Privacy</a><a href="../terms.html">Terms</a></div></div></footer>
  <script>
    const search = document.querySelector('#resort-search'), country = document.querySelector('#country-filter'), items = [...document.querySelectorAll('.resort-directory-item')], count = document.querySelector('#directory-count');
    function filterResorts() {{ const term = search.value.trim().toLowerCase(); let visible = 0; items.forEach((item) => {{ const match = (!term || item.dataset.search.includes(term)) && (!country.value || item.dataset.country === country.value); item.hidden = !match; if (match) visible += 1; }}); count.textContent = `Showing ${{visible.toLocaleString()}} resort${{visible === 1 ? '' : 's'}}`; }}
    search.addEventListener('input', filterResorts); country.addEventListener('change', filterResorts);
  </script>
</body></html>'''


def resort_page(row: dict[str, str]) -> str:
    name, country, slug = (text(row[key]) for key in ("name", "country", "slug"))
    place = ", ".join(part for part in (row["locality"], row["region"], row["country"]) if part)
    elevation = f"{number(row['base_elevation_m'], ' m')} base · {number(row['mid_elevation_m'], ' m')} mid · {number(row['top_elevation_m'], ' m')} top"
    vertical = "Not published"
    if row["base_elevation_m"] and row["top_elevation_m"]:
        vertical = f"{number(str(float(row['top_elevation_m']) - float(row['base_elevation_m'])), ' m')}"
    map_url = f"https://www.google.com/maps/search/?api=1&query={quote(row['latitude'] + ',' + row['longitude'])}"
    official = f'<a class="button" href="{text(row["official_website"])}" rel="noopener">Official resort website</a>' if row["official_website"] else ""
    openskimap = f'<a class="text-link" href="{text(row["openskimap_url"])}" rel="noopener">Open mapped terrain on OpenSkiMap</a>' if row["openskimap_url"] else ""
    schema = {"@context": "https://schema.org", "@type": "TouristAttraction", "name": row["name"], "url": f"{SITE_URL}/resorts/{row['slug']}.html", "geo": {"@type": "GeoCoordinates", "latitude": float(row["latitude"]), "longitude": float(row["longitude"])}, "address": {"@type": "PostalAddress", "addressCountry": row["country"]}}
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{name} ski resort snow forecast guidance, elevation, mapped terrain, lifts, location and official links. Compare mountain conditions in SnowSignal.">
  <link rel="canonical" href="{SITE_URL}/resorts/{slug}.html"><meta property="og:type" content="website"><meta property="og:title" content="{name} ski resort snow forecast &amp; terrain | SnowSignal"><meta property="og:description" content="Mountain facts and SnowSignal forecast guidance for {name}, {country}."><meta property="og:url" content="{SITE_URL}/resorts/{slug}.html"><meta property="og:image" content="{SITE_URL}/snow-signal-logo.png"><meta name="twitter:card" content="summary">
  <title>{name} Ski Resort Snow Forecast &amp; Terrain | SnowSignal</title><link rel="icon" type="image/png" href="../snow-signal-logo.png"><link rel="stylesheet" href="../site.css?v=20261101-resorts"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}</script>
</head>
<body>
  <header class="site-header"><nav class="nav shell" aria-label="Main navigation"><a class="brand" href="../index.html"><img src="../snow-signal-logo.png" alt="">SnowSignal</a><div class="nav-links"><a href="index.html">Resort directory</a><a href="{APP_STORE_URL}">Explore in SnowSignal</a><a href="{APP_STORE_URL}">Download for iPhone</a></div></nav></header>
  <main class="resort-page shell">
    <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../index.html">Home</a><span aria-hidden="true">/</span><a href="index.html">Ski resorts</a><span aria-hidden="true">/</span><span>{name}</span></nav>
    <section class="resort-hero"><div><p class="resort-location">{text(place)}</p><h1>{name} ski resort</h1><p class="lead">Explore mapped mountain facts for {name}, then see the latest snow and weather forecast at base, middle and top in SnowSignal.</p><div class="actions"><a class="button primary" href="{APP_STORE_URL}">Explore {name} in SnowSignal</a><a class="button" href="{map_url}" rel="noopener">Open in Google Maps</a>{official}</div></div><aside class="resort-fact-panel"><span>Elevation</span><strong>{elevation}</strong><span>Mapped terrain and forecast context</span></aside></section>
    <section class="resort-facts" aria-label="{name} ski resort facts"><div><span>Mapped skiable terrain</span><strong>{number(row['ski_area_size_km'], ' km')}</strong></div><div><span>Skiable lifts</span><strong>{number(row['number_of_lifts'])}</strong></div><div><span>Vertical range</span><strong>{vertical}</strong></div></section>
    <section class="resort-content"><div><h2>Explore {name} in SnowSignal</h2><p>See the latest elevation-aware snowfall, temperature, rain and wind forecast for the mountain. Recheck conditions close to travel and use the resort’s official information for current lift operations, closures and safety guidance.</p><a class="text-link" href="{APP_STORE_URL}">Explore in SnowSignal</a></div><div><h2>See more in SnowSignal</h2><p>Keep {name} with your ski shortlist, compare mountain forecasts and use the app’s terrain and historical context to plan your next snow day.</p><a class="text-link" href="{APP_STORE_URL}">See more in SnowSignal</a></div></section>
    <section class="resort-links"><h2>Maps and official information</h2><div class="actions"><a class="button" href="{map_url}" rel="noopener">Find {name} on Google Maps</a>{official}</div>{openskimap}<p class="directory-note">Terrain and lift figures are mapped catalogue data and may differ from official resort totals. This page does not show a live snow report or operating status.</p></section>
  </main>
  <footer><div class="footer-row shell"><span>© 2026 SnowSignal</span><div class="footer-links"><a href="index.html">Resort directory</a><a href="../data.html">Data and sources</a><a href="../support.html">Support</a><a href="../privacy.html">Privacy</a></div></div></footer>
</body></html>'''


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "ski-snow-forecast" / "data" / "resorts_v1.csv"
    with source.open(encoding="utf-8", newline="") as file:
        resorts = [row for row in csv.DictReader(file) if row["is_active"].lower() == "true"]
    resorts.sort(key=lambda row: (row["country"], row["name"].casefold(), row["slug"]))
    destination = ROOT / "resorts"
    destination.mkdir(exist_ok=True)
    (destination / "index.html").write_text(directory_page(resorts), encoding="utf-8")
    for row in resorts:
        (destination / f"{row['slug']}.html").write_text(resort_page(row), encoding="utf-8")
    static_urls = ["/", "/resorts/", "/data.html", "/support.html", "/privacy.html", "/terms.html"]
    resort_urls = [f"/resorts/{row['slug']}.html" for row in resorts]
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap.extend(f"  <url><loc>{SITE_URL}{url}</loc></url>" for url in static_urls + resort_urls)
    sitemap.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")
    print(f"Built {len(resorts):,} resort pages in {destination}")


if __name__ == "__main__":
    main()
