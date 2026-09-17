import json
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://analyst-assessment-production.up.railway.app"

def scrape_locations():
    response = requests.get(BASE_URL)
    soup = BeautifulSoup(response.text, "html.parser")
    locations = []
    
    # Locate all facility cards on the page
    cards = soup.find_all("div", class_="location-card") or soup.find_all("article") or soup.find_all("div", class_="card")
    
    for card in cards:
        name_el = card.find(["h2", "h3", "h4", "a"])
        name = name_el.get_text(strip=True) if name_el else ""
        
        text = card.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        address = lines[1] if len(lines) > 1 else ""
        city_state_zip = lines[2] if len(lines) > 2 else ""
        offerings = lines[3:] if len(lines) > 3 else []

        locations.append({
            "facility_name": name,
            "address": address,
            "city_state_zip": city_state_zip,
            "care_offerings": offerings,
            "raw_text": text
        })

    with open("scraped_facilities.json", "w") as f:
        json.dump(locations, f, indent=2)
    print(f"Scraped {len(locations)} locations.")

if __name__ == "__main__":
    scrape_locations()