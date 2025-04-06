import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime

def fetch_year(year):
    base_url = f"https://www.veikkausliiga.com/tilastot/{year}/veikkausliiga/ottelut/"
    try:
        response = requests.get(base_url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        return parse_games(response.text, year)
    except Exception as e:
        print(f"Error fetching {year}: {str(e)}")
        return []

def parse_games(html, year):
    soup = BeautifulSoup(html, 'html.parser')
    games = []
    
    table = soup.find('table', {'id': 'games'})
    if not table:
        return games
        
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) >= 8:
            try:
                date = cols[0].get_text(strip=True)
                home_team = cols[4].get_text(strip=True).split(' - ')[0]
                away_team = cols[4].get_text(strip=True).split(' - ')[1]
                score = cols[6].get_text(strip=True).replace("–", "-")
                audience = cols[7].get_text(strip=True).replace(" ", "")
                
                game = {
                    "year": year,
                    "date": date,
                    "home_team": home_team,
                    "away_team": away_team,
                    "score": score,
                    "audience": int(audience) if audience.isdigit() else 0
                }
                games.append(game)
            except Exception as e:
                print(f"Parsing error in {year}: {str(e)}")
    return games

def main():
    all_games = []
    start_year = 1990
    end_year = datetime.now().year
    
    for year in range(start_year, end_year + 1):
        print(f"Processing year {year}...")
        games = fetch_year(year)
        all_games.extend(games)
        time.sleep(1.5)  # Avoid overwhelming the server
    
    with open('veikkausliiga_tilastot.json', 'w', encoding='utf-8') as f:
        json.dump(all_games, f, ensure_ascii=False, indent=2, sort_keys=True)
    
    print(f"Saved {len(all_games)} games to veikkausliiga_tilastot.json")

if __name__ == "__main__":
    main()
