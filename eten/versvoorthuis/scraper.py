import time
import csv
import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# -----------------------
# CONFIG
# -----------------------
BASE_URL = "https://versvoorthuis.nl/nl/maaltijden/"
CSV_FILE = "versvoorthuis.csv"

# Chrome driver opties
chrome_options = Options()
chrome_options.add_argument("--user-data-dir=chrome_data")  # bewaart sessie/cookies
chrome_options.add_argument("--profile-directory=Default")   # standaard profiel
chrome_options.add_argument("--headless")                   # comment uit om browser zichtbaar te maken
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

driver_path = "/path/to/chromedriver"  # <--- Pas dit aan

# -----------------------
# START CHROME EN LOGIN
# -----------------------
print("Start Chrome, log in en kies postcode. Druk daarna op Enter om verder te gaan...")
driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
driver.get(BASE_URL)
input("Druk op Enter als je bent ingelogd en postcode gekozen hebt...")

# -----------------------
# DATA OPSLAAN
# -----------------------
all_data = []

offset = 0
while True:
    if offset == 0:
        url = BASE_URL
    else:
        url = f"{BASE_URL}?limit=18&offset={offset}"
    print("Scraping:", url)
    driver.get(url)
    time.sleep(3)  # even wachten tot pagina geladen

    soup = BeautifulSoup(driver.page_source, "html.parser")
    products = soup.select(".productCard")
    if not products:
        break  # geen producten meer, stop

    for p in products:
        link_tag = p.select_one("a.image")
        title_tag = p.select_one(".title")
        if not link_tag or not title_tag:
            continue
        link = "https://versvoorthuis.nl" + link_tag['href']
        title = title_tag.get_text(strip=True)

        # Ga naar detailpagina
        driver.get(link)
        time.sleep(2)
        detail_soup = BeautifulSoup(driver.page_source, "html.parser")
        # Ingrediënten
        ing_tag = detail_soup.select_one("#collapse_4 .panel-body")
        ingredients = ing_tag.get_text(strip=True) if ing_tag else ""
        # Categorie
        cat_tag = detail_soup.select_one(".productInCategoriesRow")
        categories = [a.get_text(strip=True) for a in cat_tag.select("a")] if cat_tag else []
        all_data.append({
            "Categorie": ", ".join(categories),
            "Ingrediënten": ingredients,
            "Link": link
        })

    offset += 18

driver.quit()

# -----------------------
# CSV OPSLAAN
# -----------------------
print("Opslaan naar CSV:", CSV_FILE)
with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["Categorie", "Ingrediënten", "Link"])
    writer.writeheader()
    for row in all_data:
        writer.writerow(row)

print("Klaar! Aantal maaltijden:", len(all_data))
