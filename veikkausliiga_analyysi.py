import json
import os
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
from pathlib import Path
import numpy as np

# Alustusparametrit
INITIAL_ELO = 1500
K_FACTOR = 30
HOME_ADVANTAGE = 100
REPORT_YEAR = 2015
YLEISO_REPORT_YEAR = 2015

def lataa_data():
    data_path = Path('veikkausliiga_tilastot.json')
    if not data_path.exists():
        raise FileNotFoundError(f"JSON-tiedostoa ei löydy: {data_path.absolute()}")
    
    with open(data_path, 'r', encoding='utf-8') as f:
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
            vuoden_ottelut.sort(key=lambda x: datetime.strptime(x['date'], "%d.%m.%Y"))
        except ValueError:
            vuoden_ottelut.sort(key=lambda x: x['date'])
        
        elo = defaultdict(lambda: INITIAL_ELO)
        
        for ottelu in vuoden_ottelut:
            home = ottelu['home_team']
            away = ottelu['away_team']
            
            try:
                score = ottelu['score'].replace("–", "-").replace("—", "-")
                home_goals, away_goals = map(int, score.split("-"))
            except (ValueError, AttributeError):
                continue
            
            expected_home = 1 / (1 + 10 ** ((elo[away] - (elo[home] + HOME_ADVANTAGE)) / 400))
            actual = 0.5 if home_goals == away_goals else (1 if home_goals > away_goals else 0)
            
            elo[home] += K_FACTOR * (actual - expected_home)
            elo[away] += K_FACTOR * ((1 - actual) - (1 - expected_home))
            
            elo_historia[vuosi].append({
                'date': f"{vuosi}-{ottelu['date']}",
                'home_team': home,
                'away_team': away,
                'home_elo': round(elo[home], 1),
                'away_elo': round(elo[away], 1)
            })
    
    return elo_historia

def laske_yleisomaarat(data):
    yleisotilastot = {
        'vuosittain': defaultdict(lambda: {'total': 0, 'avg': 0, 'max': 0, 'min': np.inf, 'ottelut': 0}),
        'joukkueittain': defaultdict(lambda: {'kotiyo': [], 'trendi': []}),
        'ennatykset': []
    }

    for ottelu in data:
        vuosi = ottelu['year']
        yleiso = ottelu['audience']
        koti = ottelu['home_team']
        
        # Vuosittaiset tilastot
        y_v = yleisotilastot['vuosittain'][vuosi]
        y_v['total'] += yleiso
        y_v['max'] = max(y_v['max'], yleiso)
        y_v['min'] = min(y_v['min'], yleiso)
        y_v['ottelut'] += 1
        
        # Joukkuekohtaiset tilastot
        yleisotilastot['joukkueittain'][koti]['kotiyo'].append(yleiso)
        yleisotilastot['joukkueittain'][koti]['trendi'].append((vuosi, yleiso))
        
        # Ennätykset
        yleisotilastot['ennatykset'].append((vuosi, koti, yleiso))

    # Laske keskiarvot
    for vuosi, tiedot in yleisotilastot['vuosittain'].items():
        tiedot['avg'] = tiedot['total'] / tiedot['ottelut'] if tiedot['ottelut'] else 0
    
    # Järjestä ennätykset
    yleisotilastot['ennatykset'] = sorted(
        yleisotilastot['ennatykset'], 
        key=lambda x: x[2], 
        reverse=True
    )[:10]

    return yleisotilastot

def generoi_raportit(elo_historia, yleisotilastot):
    Path('reports').mkdir(parents=True, exist_ok=True)
    
    # Elo-raportit
    with open('veikkausliiga_elo_historia.json', 'w', encoding='utf-8') as f:
        json.dump(elo_historia, f, ensure_ascii=False, indent=2)
    
    # Yleisöraportit
    plt.switch_backend('Agg')
    
    # Vuosittainen kehitys
    vuodet = sorted(yleisotilastot['vuosittain'].keys())
    avg_yleisot = [yleisotilastot['vuosittain'][v]['avg'] for v in vuodet]
    
    plt.figure(figsize=(12,6))
    plt.plot(vuodet, avg_yleisot, marker='o', color='#2ecc71')
    plt.title('Keskimääräinen yleisömäärä vuosittain')
    plt.xlabel('Vuosi')
    plt.ylabel('Yleisömäärä')
    plt.grid(True)
    plt.savefig('reports/yleiso_vuosittain.png')
    plt.close()
    
    # Ennätysyleisöt
    with open('reports/top10_yleisot.md', 'w', encoding='utf-8') as f:
        f.write("# TOP 10 Yleisöennätykset\n\n")
        f.write("| Vuosi | Joukkue | Yleisömäärä |\n")
        f.write("|-------|---------|-------------|\n")
        for e in yleisotilastot['ennatykset']:
            f.write(f"| {e[0]} | {e[1]} | {e[2]:,} |\n")

def paa():
    print("Aloitetaan analyysi...")
    try:
        data = lataa_data()
        data = normalisoi_joukkueet(data)
        
        elo_historia = laske_elo_arvot(data)
        yleisotilastot = laske_yleisomaarat(data)
        
        generoi_raportit(elo_historia, yleisotilastot)
        print("Analyytti valmis! Tulokset kansiossa /reports")
    except Exception as e:
        print(f"Virhe: {str(e)}")
        raise

if __name__ == "__main__":
    paa()
