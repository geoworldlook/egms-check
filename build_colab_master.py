"""
Generator notatnika notebooks/EGMS_Check.ipynb (walidacja EGMS na stacjach GNSS, region Groningen).
Notatnika nie edytuj ręcznie: zmień CELLS i uruchom `python build_colab_master.py`.
Logika obliczeń jest w modułach step_01..step_03; notatnik zawiera parametry, wywołania, tabele i wykresy.
"""
import json
from pathlib import Path

REPO_URL = "https://github.com/geoworldlook/2_geoworldlook-egmscheck.git"
BRANCH = "claude/dreamy-dirac-jd4vue"

CELLS = [
    ("md", """# Czy EGMS nadaje się do obserwacji osiadania? Walidacja na stacjach GNSS (Groningen)

**Pytanie.** Czy prędkości i szeregi czasowe European Ground Motion Service (EGMS, Sentinel-1 InSAR)
zgadzają się z niezależnym pomiarem GNSS na tyle, by używać ich do obserwacji osiadania?

**Dane (otwarte).** EGMS Calibrated (L2b), wydanie 2019–2023, Copernicus Land Monitoring Service ·
dobowe szeregi GNSS z Nevada Geodetic Laboratory (IGS20, płyta euroazjatycka odjęta).

**Metoda** (jak w oficjalnej walidacji EGMS, Koudogbo i in. 2025):
punkty EGMS w promieniu 100 m od stacji → GNSS rzutowany na kierunek satelity → te same daty i odniesienie →
prędkość obu szeregów tym samym modelem → różnice.

**Kryteria ustalone przed obliczeniami** — sekcja 1. Werdykt — sekcja 8.

Uruchom: `Środowisko wykonawcze → Uruchom wszystko`. Pobieranie EGMS wymaga zgody w sekcji 5."""),
    ("md", "## 0. Środowisko"),
    ("code", f"""import os, sys
from google.colab import drive
drive.mount('/content/drive')
REPO_URL, BRANCH = '{REPO_URL}', '{BRANCH}'
PROJECT_DIR = '/content/drive/MyDrive/GeoWorldLook/egmscheck'
if not os.path.exists(os.path.join(PROJECT_DIR, '.git')):
    os.makedirs(os.path.dirname(PROJECT_DIR), exist_ok=True)
    !git clone -q -b "{{BRANCH}}" "{{REPO_URL}}" "{{PROJECT_DIR}}"
else:
    !git -C "{{PROJECT_DIR}}" fetch -q origin "{{BRANCH}}"
    !git -C "{{PROJECT_DIR}}" checkout -q "{{BRANCH}}"
    !git -C "{{PROJECT_DIR}}" pull -q --ff-only origin "{{BRANCH}}"
!git -C "{{PROJECT_DIR}}" log -1 --format="Kod: %h %ci %s"
!pip install -q pyjwt pyproj
os.chdir(PROJECT_DIR)
sys.path.insert(0, PROJECT_DIR)
for m in [m for m in sys.modules if m.startswith('step_0')]:
    del sys.modules[m]                      # po git pull importujemy świeży kod
import numpy as np, pandas as pd, matplotlib.pyplot as plt, requests
from pathlib import Path
pd.set_option('display.width', 200); pd.set_option('display.max_columns', 30)
print('Projekt:', PROJECT_DIR)"""),
    ("md", """## 1. Parametry i kryteria (ustalone przed obliczeniami, 2026-10-10)
Źródła wartości w komentarzach. Zmiana po zobaczeniu wyników jest niedozwolona; ewentualną zmianę zapisuje się z datą."""),
    ("code", """CFG = {
    # Wybór stacji (reguła zatwierdzona 2026-10-10)
    'region_lonlat': (5.8, 52.9, 7.3, 53.6),     # Groningen i okolice (pole gazowe)
    't_first_max': 2019.0, 't_last_min': 2024.25, # GNSS pokrywa wydanie 2019-2023
    'svu_max_mm_yr': 1.0,                         # niepewność prędkości GNSS
    'max_steps': 2,                               # skoki w szeregu GNSS
    'vu_subsiding_max': -2.0,                     # stacja osiadająca: vu <= -2 mm/rok
    'vu_stable_abs_max': 0.5,                     # stacja stabilna (kontrola negatywna)
    # EGMS
    'release': '2019-2023', 'level': 'L2B',
    'extract_radius_m': 200,
    # Metoda (Koudogbo i in. 2025: 100 m, min. 3 punkty, okno 12 dni; model EGMS: trend + sinusoida roczna)
    'radius_main_m': 100, 'radii_m': [100, 200], 'min_points': 3,
    'gnss_half_window_days': 6, 'velocity_model': 'linear_annual',
    'min_overlap': 0.85,                          # White Paper 2025
    'conv_tol': 0.01, 'duplicate_dist_m': 1.0,
    # Progi (Plan_v1_kryteria_akceptacji; [p] = propozycja zatwierdzona razem z regułą)
    'thresholds': {'abs_dv_mm_yr': 1.5,          # Fabris i Nazari 2026 za Fiaschi i in. 2018
                   'share_within': 0.80,         # [p] odsetek par stacja x ścieżka w progu
                   'series_std_mm': 5.0,         # Crosetto i in. 2025
                   'stable_abs_v_mm_yr': 1.5},   # [p] stacje stabilne: EGMS nie pokazuje ruchu
}
TOKEN_PATH = '/content/drive/MyDrive/GeoWorldLook/secrets/clms_token.json'
RAW_DIR = Path('/content/egms_raw')                       # surowe pliki EGMS: dysk sesji Colab (duże)
EXTRACT = Path('data/03_Extracts/groningen/egms_l2b_points.csv.gz')   # wycinek: Dysk / repozytorium
GNSS_DIR = Path('data/02_Raw_Ground/3_gnss_ngl')
FIG_DIR = Path('data/05_Final_Outputs/egmscheck/figures'); FIG_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = Path('data/00_Metadata/MANIFEST.csv')
DOWNLOADED_BY = 'GeoWorldLook'"""),
    ("md", "## 2. Stacje GNSS (wszystkie spełniające regułę, bez wyboru ręcznego)"),
    ("code", """from pyproj import Transformer
from step_01_ingest import read_ngl_midas, select_stations
MIDAS_URL = 'https://geodesy.unr.edu/velocities/midas.IGS.txt'
r = requests.get(MIDAS_URL, timeout=300); r.raise_for_status()
stations = select_stations(read_ngl_midas(r.text), CFG['region_lonlat'], CFG['t_first_max'], CFG['t_last_min'],
                           CFG['svu_max_mm_yr'], CFG['max_steps'], CFG['vu_subsiding_max'], CFG['vu_stable_abs_max'])
stations['x_3035'], stations['y_3035'] = Transformer.from_crs(4326, 3035, always_xy=True).transform(
    stations['lon_deg'].to_numpy(), stations['lat_deg'].to_numpy())
print(stations['group'].value_counts().to_string())
stations[['site', 'group', 'lat_deg', 'lon_deg', 't_first', 't_last', 'vu_mm_yr', 'svu_mm_yr', 'n_steps']].round(3)"""),
    ("md", "## 3. GNSS: dobowe szeregi NGL (E, N, U; płyta euroazjatycka odjęta, jak w EGMS)"),
    ("code", """from step_01_ingest import ngl_tenv3_url, download_file, read_ngl_tenv3, NGL_LICENCE
gnss = {}
for s in stations['site']:
    path = GNSS_DIR / f'{s}.EU.tenv3'
    download_file(ngl_tenv3_url(s, 'EU'), path, MANIFEST, Path('.'), f'NGL IGS20 EU-fixed daily series {s}',
                  NGL_LICENCE, DOWNLOADED_BY)
    gnss[s] = read_ngl_tenv3(path)
pd.DataFrame({s: {'od': g['date'].min().date(), 'do': g['date'].max().date(), 'doby': len(g)} for s, g in gnss.items()}).T"""),
    ("md", "## 4. EGMS: pliki pokrywające stacje (bez pobierania)"),
    ("code", """from step_01_ingest import API_ENDPOINT, get_access_token, api_headers, search_egms, point_query
session = requests.Session()
headers = api_headers(get_access_token(TOKEN_PATH, session))
hits = {}
for st in stations.itertuples():
    res = search_egms(session, headers, API_ENDPOINT, point_query(st.lon_deg, st.lat_deg, CFG['level'], CFG['release']))
    for h in res['hits']:
        hits.setdefault(h['filename'], {**h, 'stations': []})['stations'].append(st.site)
files = pd.DataFrame(hits.values())
files['track'] = files['relativeOrbit'].astype(int)
files['size_MB'] = files['filesize'] / 1e6
print(f"Plików: {len(files)}, łącznie {files['size_MB'].sum():.0f} MB (unikalne, wspólne dla wielu stacji)")
files[['filename', 'track', 'direction', 'size_MB', 'stations']].sort_values(['track', 'filename'])"""),
    ("md", """## 5. Pobranie i wycinek (wymaga zgody na rozmiar z sekcji 4)
Surowe pliki trafiają na dysk sesji Colab (`/content/egms_raw`), do manifestu z SHA-256.
Z każdego pliku zostają tylko punkty w promieniu 200 m od stacji: mały wycinek zapisany na Dysku.
Jeśli wycinek już istnieje, sekcja go wczytuje i niczego nie pobiera."""),
    ("code", """from step_01_ingest import sync_egms
from step_02_checks_extract import extract_points, date_columns
DOWNLOAD = False          # ustaw True po akceptacji rozmiaru z sekcji 4
if EXTRACT.exists():
    points = pd.read_csv(EXTRACT, dtype={'pid': str})
    print('Wczytano wycinek', EXTRACT, len(points), 'wierszy')
elif DOWNLOAD:
    res = {}                                  # świeże wyszukanie: identyfikator zapytania wygasa
    for st in stations.itertuples():
        q = search_egms(session, headers, API_ENDPOINT, point_query(st.lon_deg, st.lat_deg, CFG['level'], CFG['release']))
        for h in q['hits']:
            res.setdefault(h['filename'], q)
    parts = []
    for f, h in hits.items():
        sync_egms(session, headers, API_ENDPOINT, res[f], [f], RAW_DIR, MANIFEST, Path('.'), 15, DOWNLOADED_BY)
        p = extract_points(RAW_DIR / f, stations[stations['site'].isin(h['stations'])], CFG['extract_radius_m'], 200_000)
        if len(p):
            parts.append(p.assign(track=int(h['relativeOrbit']), direction=h['direction']))
        print(f, '->', len(p), 'punktów')
    points = pd.concat(parts, ignore_index=True)
    EXTRACT.parent.mkdir(parents=True, exist_ok=True)
    points.to_csv(EXTRACT, index=False)
    print('Zapisano wycinek', EXTRACT, f'{EXTRACT.stat().st_size / 1e6:.1f} MB')
else:
    raise RuntimeError('Zatrzymano celowo: ustaw DOWNLOAD = True po akceptacji rozmiaru z sekcji 4.')
DATE_COLS = date_columns(points)
points.groupby(['track', 'direction', 'site']).size().unstack(0).fillna(0).astype(int)"""),
    ("md", "## 6. Kontrole przed porównaniem (blokujące)"),
    ("code", """from step_02_checks_extract import check_conventions, drop_cross_file_duplicates, nearest_cross_file_distance
checks = check_conventions(points, CFG['conv_tol'])
d = nearest_cross_file_distance(points)
points, n_dup = drop_cross_file_duplicates(points, CFG['duplicate_dist_m'])
checks.loc[len(checks)] = ['A5 duplikaty z zakładek burstów (usunięte)', 'all', f'{n_dup} pkt; odległość do najbliższego z innego pliku: mediana {d.median():.2f} m',
                           f"< {CFG['duplicate_dist_m']} m = duplikat", True]
display(checks)
if not checks['pass'].all():
    raise RuntimeError('Kontrola konwencji nie przeszła: porównanie wstrzymane (F4, sekcja 2).')"""),
    ("md", "## 7. Porównanie: każda stacja × każda ścieżka × promień 100 i 200 m"),
    ("code", """from step_03_compare_gnss import compare_station_track
rows = []
for (site, track, direction), p in points.groupby(['site', 'track', 'direction']):
    for radius in CFG['radii_m']:
        rows.append({'site': site, 'group': stations.set_index('site').loc[site, 'group'], 'track': track,
                     'direction': direction, **compare_station_track(p, DATE_COLS, gnss[site], radius, CFG)})
results = pd.DataFrame(rows)
results.to_csv('data/05_Final_Outputs/egmscheck/groningen_results.csv', index=False)
cols = ['site', 'group', 'track', 'radius_m', 'n_points', 'v_gnss_los', 'v_egms', 'dv', 'series_diff_std', 'corr', 'meets_A6', 'status']
results[results['radius_m'] == CFG['radius_main_m']][cols].round(2)"""),
    ("md", """## 8. Wynik walidacji
Kryteria liczone dla promienia 100 m, na parach stacja × ścieżka ze spełnionym pokryciem czasowym (A6)."""),
    ("code", """from step_03_compare_gnss import verdict, overall, plot_velocity_scatter
v = verdict(results, CFG)
display(v)
print('\\nWNIOSEK:', overall(v))
fig = plot_velocity_scatter(results, CFG)
fig.savefig(FIG_DIR / 'groningen_velocity_scatter.png', dpi=200, bbox_inches='tight'); plt.show()"""),
    ("md", """## 9. Co widać w szeregach (przykłady wybrane regułą, nie ręcznie)
Stacja o największym osiadaniu, stacja o medianie osiadania i stacja stabilna o najmniejszym |vu|;
dla każdej ścieżka z największą liczbą punktów EGMS."""),
    ("code", """from step_03_compare_gnss import series_for_plot, plot_series, GROUP_EN
sub = stations[stations['group'] == 'osiadająca'].sort_values('vu_mm_yr')
stab = stations[stations['group'] == 'stabilna'].assign(a=lambda x: x['vu_mm_yr'].abs()).sort_values('a')
examples = [sub.iloc[0]['site'], sub.iloc[len(sub) // 2]['site']] + ([stab.iloc[0]['site']] if len(stab) else [])
for site in examples:
    ps = points[(points['site'] == site) & (points['distance_m'] <= CFG['radius_main_m'])]
    if ps.empty:
        print(site, ': brak punktów EGMS w promieniu', CFG['radius_main_m'], 'm'); continue
    track = ps.groupby('track').size().idxmax()
    s = series_for_plot(ps[ps['track'] == track], DATE_COLS, gnss[site], CFG['radius_main_m'], CFG)
    row = results[(results['site'] == site) & (results['track'] == track) & (results['radius_m'] == CFG['radius_main_m'])].iloc[0]
    fig = plot_series(s, f"{site} ({GROUP_EN[row['group']]}), track {track}: v_GNSS,LOS {row['v_gnss_los']:.1f}, "
                         f"v_EGMS {row['v_egms']:.1f} mm/yr")
    fig.savefig(FIG_DIR / f'groningen_series_{site}_{track}.png', dpi=200, bbox_inches='tight'); plt.show()"""),
    ("md", """## 10. Jak czytać wynik
- **Potwierdzone** znaczy: w tym regionie EGMS podaje to samo tempo powolnego osiadania co GNSS, w granicach progów —
  dane nadają się do obserwacji trendów osiadania tam, gdzie są punkty pomiarowe.
- Wynik **nie** mówi o zdarzeniach nagłych (EGMS: aktualizacja raz w roku, okno 5 lat), ruchu północ–południe
  ani o miejscach bez punktów EGMS.
- EGMS L2b jest kalibrowany modelem GNSS (m.in. stacje NGL): zgodność prędkości bezwzględnej nie jest w pełni
  niezależna; sygnał lokalny pochodzi z radaru.
- Pomiar naziemny potwierdza tempo osiadania widoczne w EGMS — nie odwrotnie."""),
]


def create_notebook(path: Path) -> None:
    cells = []
    for kind, src in CELLS:
        cell = {"cell_type": "markdown" if kind == "md" else "code", "metadata": {}, "source": src.splitlines(keepends=True)}
        if kind == "code":
            cell.update(execution_count=None, outputs=[])
        cells.append(cell)
    nb = {"nbformat": 4, "nbformat_minor": 5, "cells": cells,
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                       "language_info": {"name": "python"}, "colab": {"provenance": []}}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Zapisano {path}")


if __name__ == "__main__":
    create_notebook(Path(__file__).resolve().parent / "notebooks" / "EGMS_Check.ipynb")
