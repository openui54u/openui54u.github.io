import requests
from bs4 import BeautifulSoup
import csv
import time

# --- Config ---
BASE_URL = "https://versvoorthuis.nl/nl/maaltijden/"
CSV_FILENAME = "versvoorthuis.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- Instructie ---
print("=== START CHROME, LOGIN EN KIES POSTCODE ===")
input("Druk op Enter wanneer je ingelogd bent en op de maaltijdenpagina bent...")

cookie_value = input("Plak hier je sessie-cookie (PHPSESSID of versvth_sess): ").strip()
COOKIES = {"PHPSESSID": cookie_value}

# --- Functie om pagina te scrapen ---
def scrape_page(offset=0):
    params = {"limit": 18, "offset": offset} if offset > 0 else {}
    r = requests.get(BASE_URL, headers=HEADERS, cookies=COOKIES, params=params)
    if r.status_code != 200:
        print(f"Fout bij ophalen pagina offset {offset}: {r.status_code}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    products = soup.find_all("div", class_="productCard")
    scraped = []

    for p in products:
        # link naar gerecht
        link_tag = p.find("a", class_="image")
        link = "https://versvoorthuis.nl" + link_tag['href'] if link_tag else ""

        # haal productpagina op voor ingrediënten en categorie
        r_prod = requests.get(link, headers=HEADERS, cookies=COOKIES)
        if r_prod.status_code != 200:
            continue
        soup_prod = BeautifulSoup(r_prod.text, "html.parser")

        # Ingrediënten
        ing_div = soup_prod.find("div", id="collapse_4")
        ingredients = ing_div.get_text(strip=True) if ing_div else ""

        # Categorieën
        cat_div = soup_prod.find("div", class_="productInCategoriesRow")
        categories = ""
        if cat_div:
            categories = ", ".join([a.get_text(strip=True) for a in cat_div.find_all("a")])

        scraped.append({
            "Categorie": categories,
            "Ingrediënten": ingredients,
            "Link": link
        })

    return scraped

# --- Pagina loop ---
all_data = []
offset = 0
while True:
    print(f"Scrapen pagina offset {offset}...")
    page_data = scrape_page(offset)
    if not page_data:
        break
    all_data.extend(page_data)
    offset += 18
    time.sleep(1)  # korte pauze tussen requests

# --- Schrijf CSV ---
with open(CSV_FILENAME, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["Categorie", "Ingrediënten", "Link"])
    writer.writeheader()
    for row in all_data:
        writer.writerow(row)

print(f"Scraping klaar! Data opgeslagen in {CSV_FILENAME}")
