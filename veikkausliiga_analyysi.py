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

def lataa_data():
    data_path = Path('veikkausliiga_tilastot.json')
    if not data_path.exists():
        raise FileNotFoundError(f"Virhe: Tiedostoa 'veikkausliiga_tilastot.json' ei löydy!")
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Virhe JSON-datassa: {str(e)}")

def normalisoi_joukkueet(data, aliases_file='utils/team_aliases.json'):
    aliases = {}
    try:
        aliases_path = Path(aliases_file)
        if aliases_path.exists() and aliases_path.stat().st_size > 0:
            with open(aliases_path, 'r') as f:
                aliases = json.load(f)
        else:
            print("Huomio: Aliaksetiedostoa ei löydy tai se on tyhjä")
    except Exception as e:
        print(f"Virhe aliaksien latauksessa: {str(e)}")

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
        except (ValueError, TypeError):
            vuoden_ottelut.sort(key=lambda x: str(x['date']))
        
        elo = defaultdict(lambda: INITIAL_ELO)
        
        for ottelu in vuoden_ottelut:
            try:
                home = ottelu['home_team']
                away = ottelu['away_team']
                score = str(ottelu['score']).replace("–", "-").replace("—", "-").strip()
                home_goals, away_goals = map(int, score.split("-"))
                
                expected_home = 1 / (1 + 10 ** ((elo[away] - (elo[home] + HOME_ADVANTAGE)) / 400))
                actual = 0.5 if home_goals == away_goals else (1 if home_goals > away_goals else 0)
                
                elo[home] += K_FACTOR * (actual - expected_home)
                elo[away] += K_FACTOR * ((1 - actual) - (1 - expected_home))
                
                elo_historia[vuosi].append({
                    'date': ottelu['date'],
                    'home_team': home,
                    'away_team': away,
                    'home_elo': round(elo[home], 1),
                    'away_elo': round(elo[away], 1)
                })
            except Exception as e:
                print(f"Virhe ottelussa {ottelu.get('date')} {vuosi}: {str(e)}")
                continue
    
    return elo_historia

def laske_yleisomaarat(data):
    yleisot = {
        'vuosittain': defaultdict(lambda: {'total': 0, 'avg': 0, 'max': 0, 'min': np.inf, 'ottelut': 0}),
        'top10': []
    }

    for ottelu in data:
        try:
            vuosi = int(ottelu['year'])
            yleiso = int(ottelu['audience'])
            koti = ottelu['home_team']
            
            # Vuosittaiset tilastot
            yleisot['vuosittain'][vuosi]['total'] += yleiso
            yleisot['vuosittain'][vuosi]['max'] = max(yleisot['vuosittain'][vuosi]['max'], yleiso)
            yleisot['vuosittain'][vuosi]['min'] = min(yleisot['vuosittain'][vuosi]['min'], yleiso)
            yleisot['vuosittain'][vuosi]['ottelut'] += 1
            
            # Ennätykset
            yleisot['top10'].append((vuosi, koti, yleiso))
        except (KeyError, ValueError) as e:
            print(f"Virhe yleisödatassa: {str(e)}")
            continue

    # Laske keskiarvot
    for vuosi in yleisot['vuosittain']:
        tiedot = yleisot['vuosittain'][vuosi]
        tiedot['avg'] = tiedot['total'] / tiedot['ottelut'] if tiedot['ottelut'] > 0 else 0
    
    # Järjestä ennätykset
    yleisot['top10'] = sorted(yleisot['top10'], key=lambda x: x[2], reverse=True)[:10]

    return yleisot

def generoi_raportit(elo_historia, yleisot):
    Path('reports').mkdir(parents=True, exist_ok=True)
    
    # Elo-data
    with open('reports/elo_historia.json', 'w', encoding='utf-8') as f:
        json.dump(elo_historia, f, ensure_ascii=False, indent=2)
    
    # Yleisöraportit
    plt.switch_backend('Agg')
    
    # Vuosittainen kehitys
    vuodet = sorted(yleisot['vuosittain'].keys())
    avg_yleisot = [yleisot['vuosittain'][v]['avg'] for v in vuodet]
    
    plt.figure(figsize=(12,6))
    plt.bar(vuodet, avg_yleisot, color='#2ecc71')
    plt.title('Keskimääräinen yleisömäärä vuosittain')
    plt.xlabel('Vuosi')
    plt.ylabel('Yleisömäärä')
    plt.xticks(vuodet, rotation=45)
    plt.tight_layout()
    plt.savefig('reports/vuosittainen_yleiso.png')
    plt.close()
    
    # TOP 10 -ennätykset
    with open('reports/top10_yleisot.md', 'w', encoding='utf-8') as f:
        f.write("# TOP 10 Yleisöennätykset\n\n")
        f.write("| Sija | Vuosi | Joukkue | Yleisömäärä |\n")
        f.write("|------|-------|---------|-------------|\n")
        for i, (vuosi, joukkue, maara) in enumerate(yleisot['top10'], 1):
            f.write(f"| {i} | {vuosi} | {joukkue} | {maara:,} |\n")

def paa():
    print("Aloitetaan analyysi...")
    try:
        data = lataa_data()
        data = normalisoi_joukkueet(data)
        
        elo_historia = laske_elo_arvot(data)
        yleisot = laske_yleisomaarat(data)
        
        generoi_raportit(elo_historia, yleisot)
        print("Analyytti valmis! Tulokset kansiossa 'reports'")
    except Exception as e:
        print(f"Kriittinen virhe: {str(e)}")
        exit(1)

if __name__ == "__main__":
    paa()
