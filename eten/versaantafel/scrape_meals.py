#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrape_meals.py
Simple site-agnostic scraper for meal pages that tries to extract:
 - meal name
 - ingredient list (as one string)
Outputs CSV: Maaltijdnaam,Ingrediënten

Usage examples:
  python scrape_meals.py --site versaantafel --start-url "https://www.versaantafel.nl/alle-maaltijden"
  python scrape_meals.py --start-url "https://example.com/path/to/list" --out mymeals.csv

Notes:
 - Some sites load ingredients with JS; this script uses requests + bs4.
 - If a site needs JS, consider running with Selenium (not included here).
 - Be polite: respect robots.txt and site terms.
"""
import argparse
import csv
import re
import sys
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
import json

USER_AGENT = "MealScraper/1.0 (+https://github.com/yourname) Python-requests"

HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8"}

# Basic helpers
def safe_get(url, session, retries=3, backoff=1.0):
    for attempt in range(retries):
        try:
            r = session.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return r
        except Exception as e:
            if attempt + 1 == retries:
                print(f"[ERROR] GET {url} -> {e}", file=sys.stderr)
                return None
            else:
                time.sleep(backoff * (attempt + 1))
    return None

def find_links_on_list_page(soup, base_url):
    """
    Heuristics: find links that likely point to meal detail pages.
    Looks for anchor tags, cards, items in lists.
    """
    links = set()
    # common: anchors inside elements with class containing 'meal', 'product', 'card', 'gerechten'
    candidates = soup.find_all("a", href=True)
    for a in candidates:
        href = a["href"].strip()
        if href.startswith("#"):
            continue
        full = urljoin(base_url, href)
        # heuristics: exclude external domains
        if urlparse(full).netloc != urlparse(base_url).netloc:
            continue
        text = (a.get_text(" ", strip=True) or "").lower()
        # filter out links that are clearly not meals (cart, login, category)
        if any(x in href.lower() for x in ["#", "cart", "login", "account", "category", "filter"]):
            continue
        # prefer anchors with some text or titles
        if len(text) >= 3:
            links.add(full)
    return list(links)

def extract_jsonld_ingredients(soup):
    """
    Parse application/ld+json blocks for recipeIngredient or ingredient fields.
    """
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:
            # sometimes it's multiple JSON objects glued together
            txt = tag.string or ""
            try:
                data = json.loads(txt.split("\n",1)[0])
            except Exception:
                continue
        # If data is a list, iterate
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            # recipeIngredient is common
            if "recipeIngredient" in item and isinstance(item["recipeIngredient"], list):
                return " ; ".join([str(i).strip() for i in item["recipeIngredient"]])
            # ingredients or ingredient might be present
            if "ingredients" in item:
                val = item["ingredients"]
                if isinstance(val, list):
                    return " ; ".join([str(i).strip() for i in val])
                elif isinstance(val, str):
                    return val.strip()
            # some sites include nutrition/description with ingredients
    return None

def extract_from_meta_desc(soup):
    """
    Some sites include a short ingredient summary in meta description.
    """
    md = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if md and md.get("content"):
        txt = md.get("content").strip()
        # Heuristic: if it contains commas and ingredient-like words (e.g. 'aardappel', 'kip', 'tomaat')
        if len(txt) > 20:
            return txt
    return None

def extract_by_label_search(soup):
    """
    Search for nodes that contain words like 'Ingrediënt', 'Ingrediënten', 'Ingredienten' (NL)
    - If found, try to extract sibling/next text or following <ul>/<p>.
    """
    patterns = re.compile(r"ingredien|ingredient", re.I)
    for tag in soup.find_all(text=patterns):
        parent = tag.parent
        # if parent contains the label and sibling list
        text_snippet = parent.get_text(" ", strip=True)
        # search nearby siblings for lists or paragraphs
        # check next sibling
        for sibling in list(parent.next_siblings)[:6]:
            if getattr(sibling, "get_text", None):
                stext = sibling.get_text(" ", strip=True)
                if len(stext) >= 3:
                    return stext
        # check children of parent
        for child in parent.find_all(["ul", "ol", "p", "div"], recursive=False):
            ctext = child.get_text(" ", strip=True)
            if len(ctext) >= 3:
                return ctext
        # as fallback return the parent's text minus the label itself
        cleaned = re.sub(patterns, "", text_snippet, flags=re.I).strip(" :\-")
        if len(cleaned) >= 3:
            return cleaned
    return None

def extract_meal_name(soup):
    # try common title tags
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
        # strip site name after dash or pipe
        title = re.split(r"[-|•\|]\s*", title)[0].strip()
        if len(title) > 1:
            return title
    # h1
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)
    # meta og:title
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        return og.get("content").strip()
    # fallback: first h2 or strong
    h2 = soup.find(["h2", "h3"])
    if h2:
        return h2.get_text(" ", strip=True)
    return "Onbekende maaltijd"

def extract_ingredients_from_page(url, session):
    r = safe_get(url, session)
    if not r:
        return None, None
    soup = BeautifulSoup(r.text, "html.parser")
    name = extract_meal_name(soup)
    # strategies (priority)
    strategies = [
        extract_jsonld_ingredients,
        extract_by_label_search,
        extract_from_meta_desc
    ]
    for strat in strategies:
        try:
            ing = strat(soup)
            if ing and len(ing.strip()) >= 2:
                # normalize whitespace and separators
                ing = re.sub(r"\s+", " ", ing).strip()
                ing = ing.replace("\n", " ; ")
                return name, ing
        except Exception as e:
            # continue trying other strategies
            continue
    # As last resort, try to extract list items present on page
    lis = soup.find_all("li")
    for li in lis:
        txt = li.get_text(" ", strip=True)
        if len(txt) > 3 and len(txt) < 200:
            # naive: if a list contains many short items, join some as ingredients
            maybe = " ; ".join([li.get_text(" ", strip=True) for li in lis[:20]])
            if len(maybe) > 10:
                return name, maybe
    return name, ""

def main():
    ap = argparse.ArgumentParser(description="Scrape meal pages and export CSV (Maaltijdnaam, Ingrediënten).")
    ap.add_argument("--start-url", "-u", help="Start/list page URL", required=True)
    ap.add_argument("--out", "-o", help="Output CSV filename", default="meals.csv")
    ap.add_argument("--max-pages", type=int, default=500, help="Max number of detail pages to fetch")
    ap.add_argument("--delay", type=float, default=0.6, help="Delay between requests (seconds)")
    ap.add_argument("--site", choices=["versaantafel", "versvoorthuis", "uitgekookt", "auto"], default="auto", help="Site hint (affects heuristics)")
    args = ap.parse_args()

    session = requests.Session()
    start_url = args.start_url
    r = safe_get(start_url, session)
    if not r:
        print("[ERROR] kon startpagina niet ophalen", file=sys.stderr)
        return
    base = "{scheme}://{netloc}".format(**urlparse(start_url)._asdict())
    soup = BeautifulSoup(r.text, "html.parser")

    # Find candidate detail links on the start page
    links = find_links_on_list_page(soup, start_url)
    print(f"[INFO] {len(links)} kandidaat links gevonden op startpagina (voor filtering).")

    # Heuristic: try to detect pagination and follow pages (simple)
    # find anchor tags with text 'volgende' or page numbers
    # naive approach: try to find more links by scanning the site root category pages (not exhaustive)
    # For now, keep initial set; user can provide a file or a start URL that lists all meals.

    # Optional: if links seem small, try to follow anchors inside cards
    # Limit to max_pages
    links = list(dict.fromkeys(links))[: args.max_pages]

    results = []
    for i, link in enumerate(links, start=1):
        print(f"[{i}/{len(links)}] ophalen: {link}")
        name, ing = extract_ingredients_from_page(link, session)
        if name is None:
            continue
        results.append((name, ing, link))
        time.sleep(args.delay)

    # Write CSV
    out_file = args.out
    with open(out_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Maaltijdnaam", "Ingrediënten", "BronURL"])
        for name, ing, link in results:
            writer.writerow([name, ing, link])
    print(f"[DONE] {len(results)} regels geschreven naar {out_file}")

if __name__ == "__main__":
    main()
