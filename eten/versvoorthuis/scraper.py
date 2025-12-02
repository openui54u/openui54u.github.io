import requests
from bs4 import BeautifulSoup
import csv
import time

# ==== CONFIG ====
BASE_URL = "https://versvoorthuis.nl/nl/maaltijden/"
PAGE_LIMIT = 18  # per pagina
OUTPUT_CSV = "versvoorthuis.csv"

# ==== COOKIE ====
# Handmatig: login via Chrome, kies postcode, kopieer cookie waarde
SESSION_COOKIE = input("Start Chrome, login en kies postcode. Voer de waarde van 'PHPSESSID' in: ").strip()
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": f"PHPSESSID={SESSION_COOKIE}"
}

# ==== FUNCTIES ====
def fetch_page(url):
    """Haalt HTML van een pagina op."""
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        print(f"Fout bij ophalen pagina: {url} ({resp.status_code})")
        return None
    return resp.text

def parse_meals(html):
    """Haalt alle maaltijden en detail-URLs van een overzichtspagina."""
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".productCard.card")
    meals = []
    for card in cards:
        info = card.select_one(".info .title")
        link = card.select_one("a.image")
        if info and link:
            meals.append({
                "name": info.text.strip(),
                "url": "https://versvoorthuis.nl" + link.get("href")
            })
    return meals

def parse_meal_details(url):
    """Haalt details van een maaltijdpagina."""
    html = fetch_page(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    data = {}

    # Naam
    title = soup.select_one("h1")
    data["name"] = title.text.strip() if title else ""

    # Gewicht en prijs (selecteer eerste optie)
    variation = soup.select_one("select.variationsSelectBox option")
    if variation:
        var_text = variation.text.strip()
        if " - €" in var_text:
            weight, price = var_text.split(" - €")
            data["weight"] = weight.strip()
            data["price"] = price.strip()
        else:
            data["weight"] = var_text.strip()
            data["price"] = ""
    else:
        data["weight"] = ""
        data["price"] = ""

    # Ingrediënten
    ingredients = soup.select_one("#collapse_4 .panel-body")
    data["ingredients"] = ingredients.text.strip() if ingredients else ""

    # Allergenen
    allergens = soup.select_one("#collapse_5 .panel-body")
    data["allergens"] = allergens.text.strip() if allergens else ""

    # Categorieën
    cats = soup.select(".productInCategoriesRow a")
    data["categories"] = ", ".join([c.text.strip() for c in cats]) if cats else ""

    # Voedingswaarden
    nutrients = {}
    for row in soup.select("#specsTable tbody tr"):
        tds = row.find_all("td")
        if len(tds) == 2:
            nutrients[tds[0].text.strip()] = tds[1].text.strip()
    data.update(nutrients)

    return data

# ==== MAIN ====
all_meals = []

# Eerste pagina (zonder offset)
print("Ophalen eerste pagina...")
html = fetch_page(BASE_URL)
meals = parse_meals(html)
all_meals.extend(meals)

# Bepaal aantal pagina's door te checken aantal maaltijden op eerste pagina
num_found = len(meals)
offset = PAGE_LIMIT
while True:
    print(f"Ophalen pagina met offset {offset}...")
    page_url = f"{BASE_URL}?limit={PAGE_LIMIT}&offset={offset}"
    html = fetch_page(page_url)
    next_meals = parse_meals(html)
    if not next_meals:
        break
    all_meals.extend(next_meals)
    offset += PAGE_LIMIT
    time.sleep(1)  # beleefd zijn naar de server

print(f"Totaal maaltijden gevonden: {len(all_meals)}")

# Haal details van iedere maaltijd
detailed_meals = []
for i, meal in enumerate(all_meals, 1):
    print(f"[{i}/{len(all_meals)}] Ophalen details: {meal['name']}")
    details = parse_meal_details(meal["url"])
    if details:
        detailed_meals.append(details)
    time.sleep(0.5)  # beleefd

# Sla op in CSV
if detailed_meals:
    keys = detailed_meals[0].keys()
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        dict_writer = csv.DictWriter(f, keys)
        dict_writer.writeheader()
        dict_writer.writerows(detailed_meals)

    print(f"Scrapen klaar! CSV opgeslagen als {OUTPUT_CSV}")
else:
    print("Geen maaltijden gedetailleerd opgehaald.")
