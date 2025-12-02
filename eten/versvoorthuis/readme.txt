# VersVoorThuis Scraper

Dit script scrapt maaltijden van https://versvoorthuis.nl.

## Vereisten
- Python 3.9+
- pip install requests beautifulsoup4

## Belangrijk
1. De website vereist een **ingelogde sessie en postcode**.
2. Open je browser, log in, voer je postcode in.
3. Kopieer de cookies van de sessie (`PHPSESSID` etc.).
4. Plak de cookies in de `COOKIES` dict in scraper.py
5. Start de scraper: `python scraper.py`
6. Output wordt weggeschreven naar `versvoorthuis_maaltijden.csv`
