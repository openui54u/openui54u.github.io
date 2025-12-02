import requests
from bs4 import BeautifulSoup
import csv
import time

BASE_URL = "https://www.versaantafel.nl"
MAIN_URL = "https://www.versaantafel.nl/maaltijden-aan-huis/"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def get_soup(url):
    """Download pagina en maak BeautifulSoup object"""
    print(f"Fetching: {url}")
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def get_categories(main_url):
    """Haal alle categorieën op van de hoofdmaaltijdenpagina"""
    page = get_soup(main_url)
    categories = {}

    # Alle product-cards binnen de categorie-widget
    for card in page.select("div.product-widget-container.categories-widget div.product-card a"):
        href = card.get("href")
        h3 = card.select_one("h3.h1")
        name = h3.text.strip() if h3 else "Onbekend"
        if href:
            full_url = href if href.startswith("http") else BASE_URL + href
            categories[name] = full_url

    return categories

def get_number_of_pages(category_url):
    """Bepaal het aantal pagina's in de categorie"""
    page = get_soup(category_url)
    pagination = page.select("ul.pages-items li a.page")
    if not pagination:
        return 1
    pages = [int(a.text.strip()) for a in pagination if a.text.strip().isdigit()]
    return max(pages)

def get_meal_links_from_page(url):
    """Vind alle maaltijd-links op één categoriepagina"""
    page = get_soup(url)
    links = []

    # Zoek alle <a> binnen div.product-card (die maaltijd-links bevatten)
    for card in page.select("div.product-card a"):
        href = card.get("href")
        # Filter geen media/image links
        if href and "/media/" not in href and "?" not in href:
            full_url = href if href.startswith("http") else BASE_URL + href
            links.append(full_url)

    # Unieke links
    links = list(dict.fromkeys(links))
    return links

def scrape_meal(url):
    """Scrape detailpagina → naam + ingrediënten"""
    page = get_soup(url)

    # Naam van de maaltijd
    title_el = page.select_one("div.product-info h1")
    name = title_el.text.strip() if title_el else "Onbekend"

    # Ingrediënten
    ingredients = ""
    nutritional_div = page.select_one("div.product-nutritional")
    if nutritional_div:
        title_divs = nutritional_div.select("div.collapsible-product-field-title")
        for t in title_divs:
            span = t.find("span")
            if span and "Ingrediënten" in span.text:
                # Volgende sibling met de inhoud
                content_div = t.find_next_sibling("div", class_="collapsible-field")
                if content_div:
                    ingredient_div = content_div.find("div", attrs={"data-target-product-id": True})
                    if ingredient_div:
                        ingredients = ingredient_div.get_text(strip=True)
                break

    return {
        "name": name,
        "ingredients": ingredients,
        "url": url
    }

def main():
    # 1) Alle categorieën ophalen
    categories = get_categories(MAIN_URL)
    print(f"Totaal categorieën: {len(categories)}")

    all_rows = []

    # 2) Per categorie scrapen
    for cat_name, cat_url in categories.items():
        print(f"\n=== Categorie: {cat_name} ===")
        total_pages = get_number_of_pages(cat_url)
        print(f"Aantal pagina's: {total_pages}")

        # Alle pagina’s doorlopen
        for p in range(1, total_pages + 1):
            page_url = f"{cat_url}?p={p}"
            meal_links = get_meal_links_from_page(page_url)
            print(f"Pagina {p}: {len(meal_links)} maaltijden gevonden")

            # Scrape elke maaltijd
            for idx, link in enumerate(meal_links, start=1):
                try:
                    data = scrape_meal(link)
                    all_rows.append({
                        "Categorie": cat_name,
                        "Naam": data["name"],
                        "Ingrediënten": data["ingredients"],
                        "URL": data["url"]
                    })
                    print(f"[{idx}/{len(meal_links)}] {data['name']}")
                except Exception as e:
                    print(f"FOUT bij {link}: {e}")
                time.sleep(0.3)  # beleefd scrapen

            time.sleep(0.5)  # kleine pauze tussen pagina's

    # 3) Schrijf alles naar CSV
    with open("meals.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Categorie", "Naam", "Ingrediënten", "URL"])
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    print("\n🎉 CSV geschreven naar meals.csv")

if __name__ == "__main__":
    main()
