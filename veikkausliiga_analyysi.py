import json
import os
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
from pathlib import Path

# Alustusparametrit
INITIAL_ELO = 1500
K_FACTOR = 30
HOME_ADVANTAGE = 100  # Kotiedun lisäys
REPORT_YEAR = 2015    # Valittu esittelyvuosi

def lataa_data():
    data_path = Path('veikkausliiga_tilastot.json')
    if not data_path.exists():
        raise FileNotFoundError("JSON-tiedostoa ei löydy polusta: {}".format(data_path.absolute()))
    
    with open(data_path, 'r', encoding='utf-8') as f:  # KORJATTU: Lisätty 'as'
        return json.load(f)

def normalisoi_joukkueet(data, aliases_file='utils/team_aliases.json'):
    try:
        with open(aliases_file, 'r') as f:
            aliases = json.load(f)
    except FileNotFoundError:
        print("Varoitus: Aliaksia ei löydy, käytetään raakadataa")
        return data
    
    for ottelu in data:
        ottelu['home_team'] = aliases.get(ottelu['home_team'], ottelu['home_team'])
        ottelu['away_team'] = aliases.get(ottelu['away_team'], ottelu['away_team'])
    return data

def laske_elo_arvot(data):
    elo_historia = defaultdict(list)
    vuodet = sorted({ottelu['year'] for ottelu in data})
    
    for vuosi in vuodet:
        vuoden_ottelut = [o for o in data if o['year'] == vuosi]
        try:
            # Yritetään järjestää päivämäärän mukaan
            vuoden_ottelut.sort(key=lambda x: datetime.strptime(x['date'], "%d.%m.%Y"))
        except ValueError:
            # Jos päivämääräformaatti on virheellinen
            vuoden_ottelut.sort(key=lambda x: x['date'])
        
        elo = defaultdict(lambda: INITIAL_ELO)
        
        for ottelu in vuoden_ottelut:
            home = ottelu['home_team']
            away = ottelu['away_team']
            
            try:
                # Käsitellään eri erotinmerkit
                score = ottelu['score'].replace("–", "-").replace("—", "-")
                home_goals, away_goals = map(int, score.split("-"))
            except ValueError:
                print(f"Virheellinen tulos: {ottelu['score']}, ottelu {ottelu['date']} {vuosi}")
                continue
            
            # Laske Elo-odotukset
            expected_home = 1 / (1 + 10 ** ((elo[away] - (elo[home] + HOME_ADVANTAGE)) / 400))
            expected_away = 1 - expected_home
            
            # Päivitä Elo-arvot
            actual = 0.5 if home_goals == away_goals else (1 if home_goals > away_goals else 0)
            elo[home] += K_FACTOR * (actual - expected_home)
            elo[away] += K_FACTOR * ((1 - actual) - expected_away)
            
            # Tallenna historia
            elo_historia[vuosi].append({
                'date': f"{vuosi}-{ottelu['date']}",
                'home_team': home,
                'away_team': away,
                'home_elo': round(elo[home], 1),
                'away_elo': round(elo[away], 1)
            })
    
    return elo_historia

def generoi_raportit(elo_historia):
    # Varmista kansioiden olemassaolo
    Path('reports').mkdir(parents=True, exist_ok=True)
    
    # Tallenna koko historia
    with open('veikkausliiga_elo_historia.json', 'w', encoding='utf-8') as f:
        json.dump(elo_historia, f, ensure_ascii=False, indent=2)
    
    # Vuosiraportti CSV-muodossa
    for vuosi, data in elo_historia.items():
        df = pd.DataFrame(data)
        df.to_csv(f'reports/elo_{vuosi}.csv', index=False)
    
    # Esimerkkikuvaaja
    plt.switch_backend('Agg')  # Tärkeä GitHub Actionsia varten
    try:
        vuosi_data = [d for d in elo_historia[REPORT_YEAR] if d['home_team'] == 'HJK']
        if vuosi_data:
            df = pd.DataFrame(vuosi_data)
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df.dropna(subset=['date'])
            df.plot(x='date', y='home_elo', title=f'HJK:n Elo-kehitys {REPORT_YEAR}')
            plt.tight_layout()
            plt.savefig(f'reports/elo_kehitys_{REPORT_YEAR}.png')
            plt.close()
    except KeyError:
        print(f"Ei dataa vuodelle {REPORT_YEAR}")

def paa():
    print("Aloitetaan analyysi...")
    try:
        data = lataa_data()
        data = normalisoi_joukkueet(data)
        elo_historia = laske_elo_arvot(data)
        generoi_raportit(elo_historia)
        print("Analyytti valmis!")
    except Exception as e:
        print(f"Virhe analyysissa: {str(e)}")
        raise

if __name__ == "__main__":
    paa()
