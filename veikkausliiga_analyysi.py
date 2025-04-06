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
START_YEAR = 1990

def lataa_data():
    data_path = Path('veikkausliiga_tilastot.json')
    if not data_path.exists():
        raise FileNotFoundError("Virhe: Tiedostoa 'veikkausliiga_tilastot.json' ei löydy!")
    
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Varmista että data on kronologisessa järjestyksessä
    return sorted(data, key=lambda x: (x['year'], x['date']))

def normalisoi_joukkueet(data):
    # Lisää historiallisia joukkueiden nimiä tähän
    aliases = {
        "MyPa": "Myllykosken Pallo -47",
        "FC Jazz": "Jazz",
        "FC Jokerit": "Jokerit",
        # ... lisää tarvittaessa
    }
    
    for ottelu in data:
        ottelu['home_team'] = aliases.get(ottelu['home_team'], ottelu['home_team'])
        ottelu['away_team'] = aliases.get(ottelu['away_team'], ottelu['away_team'])
    return data

def laske_yleisomaarat(data):
    tilastot = {
        'kaikkien_aikojen': {
            'suurin': 0,
            'pienin': float('inf'),
            'suurin_vuosi': None,
            'suurin_joukkue': None,
            'keskiarvo': 0
        },
        'vuosittain': defaultdict(lambda: {
            'summa': 0,
            'maara': 0,
            'keskiarvo': 0,
            'suurin': 0,
            'suurin_ottelu': None
        }),
        'joukkueittain': defaultdict(lambda: {
            'kotiyo_summa': 0,
            'kotiyo_maara': 0,
            'keskiarvo': 0,
            'suurin': 0
        })
    }

    total_yleiso = 0
    total_ottelut = 0
    
    for ottelu in data:
        vuosi = ottelu['year']
        yleiso = ottelu['audience']
        koti = ottelu['home_team']
        vieras = ottelu['away_team']

        # Päivitä kaikkien aikojen tilastot
        if yleiso > tilastot['kaikkien_aikojen']['suurin']:
            tilastot['kaikkien_aikojen'].update({
                'suurin': yleiso,
                'suurin_vuosi': vuosi,
                'suurin_joukkue': koti
            })
        
        if yleiso < tilastot['kaikkien_aikojen']['pienin']:
            tilastot['kaikkien_aikojen']['pienin'] = yleiso
        
        total_yleiso += yleiso
        total_ottelut += 1

        # Vuosittaiset tilastot
        v_tilasto = tilastot['vuosittain'][vuosi]
        v_tilasto['summa'] += yleiso
        v_tilasto['maara'] += 1
        if yleiso > v_tilasto['suurin']:
            v_tilasto['suurin'] = yleiso
            v_tilasto['suurin_ottelu'] = f"{koti} vs {vieras}"

        # Joukkueittaiset tilastot
        j_tilasto = tilastot['joukkueittain'][koti]
        j_tilasto['kotiyo_summa'] += yleiso
        j_tilasto['kotiyo_maara'] += 1
        if yleiso > j_tilasto['suurin']:
            j_tilasto['suurin'] = yleiso

    # Laske keskiarvot
    tilastot['kaikkien_aikojen']['keskiarvo'] = total_yleiso / total_ottelut if total_ottelut else 0
    
    for vuosi in tilastot['vuosittain']:
        v = tilastot['vuosittain'][vuosi]
        v['keskiarvo'] = v['summa'] / v['maara'] if v['maara'] else 0
    
    for joukkue in tilastot['joukkueittain']:
        j = tilastot['joukkueittain'][joukkue]
        j['keskiarvo'] = j['kotiyo_summa'] / j['kotiyo_maara'] if j['kotiyo_maara'] else 0

    return tilastot

def generoi_historiallinen_yleisoraportti(tilastot):
    Path('reports').mkdir(exist_ok=True)
    
    # Kaikkien aikojen tilastot
    with open('reports/yleisohistoria.md', 'w', encoding='utf-8') as f:
        f.write("# Veikkausliigan yleisötilastot 1990-\n\n")
        f.write(f"**Kaikkien aikojen ennätys:**\n")
        f.write(f"- {tilastot['kaikkien_aikojen']['suurin']:,} katsojaa ({tilastot['kaikkien_aikojen']['suurin_vuosi']}, {tilastot['kaikkien_aikojen']['suurin_joukkue']})\n")
        f.write(f"- Keskimääräinen yleisömäärä: {tilastot['kaikkien_aikojen']['keskiarvo']:.0f}\n")
        f.write(f"- Pienin yleisömäärä: {tilastot['kaikkien_aikojen']['pienin']}\n\n")

        f.write("## Vuosittainen kehitys\n")
        f.write("| Vuosi | Keskimääräinen | Suurin yleisö | Ottelu |\n")
        f.write("|-------|-----------------|---------------|--------|\n")
        for vuosi in sorted(tilastot['vuosittain'].keys()):
            v = tilastot['vuosittain'][vuosi]
            f.write(f"| {vuosi} | {v['keskiarvo']:.0f | {v['suurin']:,} | {v['suurin_ottelu']} |\n")

    # Visuaalinen esitys
    plt.switch_backend('Agg')
    vuodet = sorted(tilastot['vuosittain'].keys())
    keskiarvo = [tilastot['vuosittain'][v]['keskiarvo'] for v in vuodet]
    maksimi = [tilastot['vuosittain'][v]['suurin'] for v in vuodet]

    plt.figure(figsize=(15, 7))
    plt.plot(vuodet, keskiarvo, label='Keskimääräinen', marker='o')
    plt.plot(vuodet, maksimi, label='Ennätys', linestyle='--', marker='x')
    plt.title('Veikkausliigan yleisömäärät 1990–2024')
    plt.xlabel('Vuosi')
    plt.ylabel('Yleisömäärä')
    plt.xticks(vuodet, rotation=45)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig('reports/yleisokehitys_historiallinen.png')
    plt.close()

def paa():
    print("Aloitetaan historiallinen analyysi...")
    try:
        data = lataa_data()
        data = normalisoi_joukkueet(data)
        tilastot = laske_yleisomaarat(data)
        generoi_historiallinen_yleisoraportti(tilastot)
        print("Raportti luotu: reports/yleisohistoria.md")
    except Exception as e:
        print(f"Virhe: {str(e)}")
        exit(1)

if __name__ == "__main__":
    paa()
