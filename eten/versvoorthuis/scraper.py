import requests
from bs4 import BeautifulSoup
import csv
import time
import random

# ===============================
# Configuratie
# ===============================
BASE_URL = "https://versvoorthuis.nl"
MAALTIJDEN_URL = f"{BASE_URL}/nl/maaltijden/"
CSV_FILE = "meals.csv"
OFFSET_STEP = 12  # aantal maaltijden per pagina
MAX_OFFSET = 100  # optioneel, kan hoger

# ===============================
# Vraag gebruiker om cookiesessie
# ===============================
print("⚠️ Ga naar https://versvoorthuis.nl/nl/maaltijden/, voer je postcode in en accepteer cookies.")
cookie_value = input("Plak hier de waarde van je sessie-cookie (bijv. PHPSESSID): ").strip()

# ===============================
# Setup requests session met cookie
# ===============================
session = requests.Session()
session.cookies.set("PHPSESSID", cookie_value, domain=".versvoorthuis.nl")

# ===============================
# Functie om maaltijd links op te halen
# ===============================
def get_maaltijd_links(offset=0):
    url = f"{MAALTIJDEN_URL}?offset={offset}&limit={OFFSET_STEP}"
    response = session.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    links = []
    for card in soup.select("div.productCard a.image"):
        href = card.get("href")
        if href:
            full_url = BASE_URL + href
            links.append(full_url)
    return links

# ===============================
# Functie om details per maaltijd op te halen
# ===============================
def get_maaltijd_details(url):
    resp = session.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Naam
    name_tag = soup.select_one("h1")
    name = name_tag.text.strip() if name_tag else ""

    # Categorieën
    categories = [a.text.strip() for a in soup.select("div.productInCategoriesRow a")]

    # Ingrediënten: eerste methode
    ingredients_tag = soup.select_one("#collapse_4 .panel-body")
    ingredients = ingredients_tag.text.strip() if ingredients_tag else ""

    # Tweede methode (fallback) als eerste leeg is
    if not ingredients:
        # Soms staan ingrediënten in de beschrijving
        desc_tag = soup.select_one("#productDescriptionText")
        if desc_tag:
            # Probeer lines te vinden die beginnen met ingrediënten of bevat veel komma's
            text = desc_tag.text.strip()
            if "ingrediënten" in text.lower():
                ingredients = text
            else:
                # fallback: pak alle tekst en probeer heuristisch
                lines = text.split(". ")
                for line in lines:
                    if any(word in line.lower() for word in ["water", "suiker", "olijfolie", "aardappel", "kruiden", "melk"]):
                        ingredients = line
                        break

    return {
        "name": name,
        "categories": ", ".join(categories),
        "ingredients": ingredients,
        "url": url
    }

# ===============================
# Scraper logica met random pauze
# ===============================
all_maaltijden = []

for offset in range(0, MAX_OFFSET, OFFSET_STEP):
    print(f"📄 Ophalen van maaltijden, offset={offset}...")
    links = get_maaltijd_links(offset)
    if not links:
        print("🔹 Geen meer maaltijden gevonden, stoppen.")
        break
    for link in links:
        details = get_maaltijd_details(link)
        all_maaltijden.append(details)
        print(f"✅ {details['name']} toegevoegd.")
        # Random pauze 2-10 seconden
        wait_time = random.uniform(2, 10)
        print(f"⏱ Wachten {wait_time:.1f} seconden...")
        time.sleep(wait_time)

# ===============================
# Opslaan in CSV
# ===============================
keys = ["name", "categories", "ingredients", "url"]
with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=keys)
    writer.writeheader()
    for item in all_maaltijden:
        writer.writerow(item)

print(f"✅ Scraping voltooid. Resultaat opgeslagen in {CSV_FILE}")
