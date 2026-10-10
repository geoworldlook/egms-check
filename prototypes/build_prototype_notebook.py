"""
Generator notatników prototypowych do uruchomienia w Colab:
  prototypes/EGMS_prototyp.ipynb      - test metody E1/E2 i opis szeregu PTO1 (bez tokenu),
  prototypes/EGMS_pobranie_PTO1.ipynb - API EGMS: listy wartości, wyszukanie L2B dla PTO1, pobranie po potwierdzeniu.
Notatnika nie edytuj ręcznie: zmień CELLS i uruchom `python prototypes/build_prototype_notebook.py`.
Docelowy notatnik projektu (notebooks/EGMS_Check.ipynb) powstanie w sesji 1 przez build_colab_master.py.
"""
import json
from pathlib import Path

REPO_URL = "https://github.com/geoworldlook/2_geoworldlook-egmscheck.git"
BRANCH = "claude/dreamy-dirac-jd4vue"

CELLS_PROTOTYP = [
    ("md", """# EGMS Check — prototyp eksperymentów E1 (GNSS) i E2 (niwelacja)
Uruchom: `Środowisko wykonawcze → Uruchom wszystko`. GPU niepotrzebne, token CLMS niepotrzebny.

Co robi ten notatnik:
1. pobiera kod z GitHub (gałąź z prototypem),
2. uruchamia **test na danych syntetycznych o znanej odpowiedzi** (E1 i E2, z kontrolą negatywną),
3. opisuje **prawdziwy szereg GNSS stacji PTO1** (PANGAEA, CC BY 4.0) i rysuje go.

Czego jeszcze nie robi: porównania z prawdziwymi danymi EGMS. Wymaga to pobrania plików EGMS
i zatwierdzenia progów (`docs/plans/Plan_v1_eksperymenty.md`, sekcja 6)."""),
    ("md", "## 1. Kod z GitHub"),
    ("code", f"""import os, sys
REPO_URL = '{REPO_URL}'
BRANCH = '{BRANCH}'
if 'google.colab' in sys.modules:
    PROJECT_DIR = '/content/egmscheck'
else:
    # Lokalnie: katalog projektu = pierwszy katalog w górę, który zawiera prototyp.
    PROJECT_DIR = os.getcwd()
    while not os.path.exists(os.path.join(PROJECT_DIR, 'prototypes', 'egms_simple_check.py')):
        if os.path.dirname(PROJECT_DIR) == PROJECT_DIR:
            raise FileNotFoundError('Nie znaleziono katalogu projektu: uruchom notatnik z wnętrza repozytorium.')
        PROJECT_DIR = os.path.dirname(PROJECT_DIR)
if 'google.colab' in sys.modules:
    if not os.path.exists(os.path.join(PROJECT_DIR, '.git')):
        !git clone --depth 1 -b "{{BRANCH}}" "{{REPO_URL}}" "{{PROJECT_DIR}}"
    else:
        !git -C "{{PROJECT_DIR}}" pull --ff-only
    !git -C "{{PROJECT_DIR}}" log -1 --format="Kod: %h %ci %s"
    !pip install -q pyproj
os.chdir(PROJECT_DIR)
sys.path.insert(0, os.path.join(PROJECT_DIR, 'prototypes'))
print('Projekt:', PROJECT_DIR)"""),
    ("md", """## 2. Test metody na danych syntetycznych
Prawda jest znana: pion −5 mm/rok, kąt padania ok. 41°, szum dobowy GNSS 8 mm; w E2 niecka −14 mm/rok
i niwelacja z szumem 1 mm. Test ma odtworzyć te wartości i **nie przejść** przy celowo błędnej prędkości GNSS.
Wynik mówi o poprawności kodu, nie o EGMS."""),
    ("code", "!python prototypes/egms_simple_check.py --selftest"),
    ("md", "## 3. Prawdziwy szereg GNSS PTO1: zakres, przerwy, położenie w EPSG:3035"),
    ("code", "!python prototypes/egms_simple_check.py --describe-gnss data/02_Raw_Ground/1_gnss_pangaea/PTO1.txt"),
    ("md", """## 4. Wykres szeregu PTO1
Doby blado, mediana 30-dniowa wyraźnie. Pion w mm względem odniesienia zbioru PANGAEA.
To opis danych wejściowych, nie porównanie z EGMS."""),
    ("code", """import matplotlib.pyplot as plt
from egms_simple_check import read_pangaea_gnss

gnss, lon, lat = read_pangaea_gnss('data/02_Raw_Ground/1_gnss_pangaea/PTO1.txt')
median_30d = gnss.set_index('date')['up_mm'].rolling('30D', center=True).median()

fig, ax = plt.subplots(figsize=(11, 4))
ax.plot(gnss['date'], gnss['up_mm'], '.', ms=2, color='0.75', label='GNSS daily (PANGAEA)')
ax.plot(median_30d.index, median_30d.values, color='tab:blue', lw=1.5, label='30-day median')
ax.axvspan('2018-06-12', '2022-07-15', color='tab:orange', alpha=0.12, label='EGMS release 2018-2022')
ax.set_xlabel('Date')
ax.set_ylabel('Vertical displacement [mm]')
ax.set_title(f'PTO1 ({lon:.4f} E, {lat:.4f} N): GNSS series ends {gnss["date"].iat[-1].date()}')
ax.legend(loc='lower left')
ax.grid(alpha=0.3)
plt.show()"""),
    ("md", """## 5. Co dalej
- Decyzje autora: `docs/plans/Plan_v1_eksperymenty.md`, sekcja 6 (wydanie EGMS, definicja pokrycia 85%, przypadek 2: NRW czy Hengelo).
- Dane EGMS: token CLMS (API) albo wniosek do CLMS Helpdesk o wydania archiwalne.
- Źródła: Pintori i Serpelloni (2023), PANGAEA, doi:10.1594/PANGAEA.958598 (CC BY 4.0);
  Fabris i Nazari (2026), Front. Earth Sci. 14:1781404; Even i in. (2024), PFG 92:253–270."""),
]


CELLS_PTO1 = [
    ("md", """# EGMS Check — pobranie danych EGMS dla stacji PTO1 (przypadek 1)
Produkt: **EGMS Calibrated (L2B)**, ścieżki 117 i 44 (wstępujące) oraz 95 (zstępująca), pobierany przez oficjalne API.

Kolejność (nie pomijaj kroków):
1. Dysk Google i kod; dane trafiają na Dysk: `MyDrive/GeoWorldLook/egmscheck/data/01_Raw_EGMS/`.
2. Token: klucz serwisowy CLMS na Dysku **poza repozytorium** (`MyDrive/GeoWorldLook/secrets/clms_token.jwt`).
   Token nie jest drukowany ani zapisywany.
3. Listy wartości API: które wydania są dostępne (pytanie A2) — zapis do `data/00_Metadata/`.
4. Wyszukanie plików dla punktu PTO1 we wszystkich wydaniach: nazwy, bursty, rozmiary. **Nic się nie pobiera.**
5. **Stop:** decyzja o wydaniu (D-A) i zgoda na rozmiar. Dopiero potem krok 6 z listą plików.
6. Pobranie przyrostowe z SHA-256 i wpisem w `MANIFEST.csv`.
7. Sprawdzenie, czy Nevada Geodetic Laboratory ma stację PTO1 (dłuższy szereg GNSS)."""),
    ("md", "## 1. Dysk Google i kod"),
    ("code", f"""import os, sys
from google.colab import drive
drive.mount('/content/drive')

REPO_URL = '{REPO_URL}'
BRANCH = '{BRANCH}'
PROJECT_DIR = '/content/drive/MyDrive/GeoWorldLook/egmscheck'
if not os.path.exists(os.path.join(PROJECT_DIR, '.git')):
    os.makedirs(os.path.dirname(PROJECT_DIR), exist_ok=True)
    !git clone -b "{{BRANCH}}" "{{REPO_URL}}" "{{PROJECT_DIR}}"
else:
    !git -C "{{PROJECT_DIR}}" fetch origin "{{BRANCH}}"
    !git -C "{{PROJECT_DIR}}" checkout "{{BRANCH}}"
    !git -C "{{PROJECT_DIR}}" pull --ff-only origin "{{BRANCH}}"
!git -C "{{PROJECT_DIR}}" log -1 --format="Kod: %h %ci %s"
!pip install -q pyjwt pyproj
os.chdir(PROJECT_DIR)
for p in (PROJECT_DIR, os.path.join(PROJECT_DIR, 'prototypes')):
    if p not in sys.path:
        sys.path.insert(0, p)
print('Projekt:', PROJECT_DIR)"""),
    ("md", "## 2. Stacja i token"),
    ("code", """from pathlib import Path
import requests
from step_01_ingest import API_ENDPOINT, get_access_token, api_headers, get_api_lists, search_egms, point_query, hits_table
from egms_simple_check import read_pangaea_gnss

TOKEN_PATH = Path('/content/drive/MyDrive/GeoWorldLook/secrets/clms_token.jwt')   # klucz serwisowy CLMS (JSON)
gnss, STATION_LON, STATION_LAT = read_pangaea_gnss('data/02_Raw_Ground/1_gnss_pangaea/PTO1.txt')
print(f'PTO1 z pliku PANGAEA: lon {STATION_LON}, lat {STATION_LAT}')

session = requests.Session()
headers = api_headers(get_access_token(TOKEN_PATH, session))   # token nie jest drukowany"""),
    ("md", "## 3. Listy wartości API (które wydania są dostępne?)"),
    ("code", """import json, datetime
TODAY = datetime.date.today().strftime('%Y%m%d')
lists = get_api_lists(session, headers, API_ENDPOINT)
out = Path(f'data/00_Metadata/egms_api_lists_{TODAY}.json')
out.write_text(json.dumps(lists, indent=1, ensure_ascii=False))
for name, values in lists.items():
    shown = values if name != 'relative_orbits' else f'{len(values)} wartości, np. {values[:10]}'
    print(f'{name}: {shown}')
print('Zapisano', out)"""),
    ("md", """## 4. Wyszukanie plików L2B dla punktu PTO1 we wszystkich wydaniach (bez pobierania)
Artykuł Fabris i Nazari 2026 podaje „sceny” 264–266 (ścieżka 117), 265–267 (44) i 806–808 (95);
porównaj je z kolumną `burstId`. Dwa trafienia na jednej ścieżce = stacja w zakładce burstów (duplikaty punktów)."""),
    ("code", """import pandas as pd
TRACKS = {117: 'ascending', 44: 'ascending', 95: 'descending'}     # Fabris i Nazari 2026, tab. 1
releases = lists['releases']
if not all(isinstance(r, str) for r in releases):
    raise TypeError(f'Nieoczekiwany format listy wydań: {releases}')
tables = []
for rel in releases:
    res = search_egms(session, headers, API_ENDPOINT, point_query(STATION_LON, STATION_LAT, 'L2B', rel))
    t = hits_table(res)
    t['query_release'] = rel
    tables.append(t)
hits = pd.concat(tables, ignore_index=True)
hits['relativeOrbit'] = hits['relativeOrbit'].astype(int)
hits_pto1 = hits[hits['relativeOrbit'].isin(TRACKS)]
cols = ['query_release', 'release', 'relativeOrbit', 'direction', 'burstId', 'filename', 'filesize_mb']
print(hits_pto1[cols].sort_values(['query_release', 'relativeOrbit', 'burstId']).to_string(index=False))
print()
print(hits_pto1.groupby('query_release')['filesize_mb'].agg(['count', 'sum']).rename(columns={'sum': 'total_MB'}))
other = sorted(set(hits['relativeOrbit']) - set(TRACKS))
print('Inne ścieżki nad stacją (nieużywane w artykule):', other)
csv = Path(f'data/00_Metadata/egms_search_PTO1_{TODAY}.csv')
hits.drop(columns=[c for c in ('poly', 'bbox') if c in hits.columns]).to_csv(csv, index=False)
print('Zapisano', csv)"""),
    ("md", """## 5. STOP — decyzja przed pobraniem
Prześlij do Claude Code wynik kroków 3 i 4 (lista wydań, tabela, łączny rozmiar). Rozstrzygamy:
- wydanie (D-A, `docs/plans/Plan_v1_wdrozenie.md`): 2018–2022 i 2015–2021 są w archiwum CLMS; jeśli API ich nie zwraca,
  zostaje wniosek do CLMS Helpdesk albo wydanie 2019–2023 z jawnym odstępstwem od progu 85%,
- lista plików do pobrania (trzy ścieżki, bursty pokrywające stację)."""),
    ("md", "## 6. Pobranie (po decyzji): wpisz wydanie i nazwy plików z tabeli wyżej"),
    ("code", """from step_01_ingest import sync_egms
RELEASE = None              # np. '2019-2023' - zapis dokładnie jak w liście z kroku 3
CONFIRMED_FILES = []        # nazwy plików z kolumny filename, zaakceptowane po obejrzeniu rozmiarów
DOWNLOADED_BY = None        # kto pobiera (do manifestu)
PAUSE_S = 15                # przerwa między plikami; serwer odrzuca zbyt częste zapytania

if not CONFIRMED_FILES:
    print('Pominięte: brak potwierdzonej listy plików (krok 5).')
else:
    if RELEASE is None or DOWNLOADED_BY is None:
        raise ValueError('Uzupełnij RELEASE i DOWNLOADED_BY.')
    res = search_egms(session, headers, API_ENDPOINT, point_query(STATION_LON, STATION_LAT, 'L2B', RELEASE))
    report = sync_egms(session, headers, API_ENDPOINT, res, CONFIRMED_FILES,
                       Path('data/01_Raw_EGMS') / RELEASE / 'L2b', Path('data/00_Metadata/MANIFEST.csv'),
                       Path(PROJECT_DIR), PAUSE_S, DOWNLOADED_BY)
    print(report.to_string(index=False))"""),
    ("md", """## 7. Czy Nevada Geodetic Laboratory ma stację PTO1?
Szereg PANGAEA kończy się 2021-04-13. Dłuższy szereg (E, N, U) z NGL rozwiązałby problem pokrycia 85% (D-A).
Ta komórka tylko sprawdza, czy strona stacji istnieje; niczego nie pobiera."""),
    ("code", """url = 'https://geodesy.unr.edu/NGLStationPages/stations/PTO1.sta'
r = requests.get(url, timeout=60)
print(url, '->', r.status_code)
if r.ok:
    print(r.text[:1500])"""),
]


def create_notebook(path: Path, cells_spec: list) -> None:
    cells = []
    for kind, src in cells_spec:
        cell = {"cell_type": "markdown" if kind == "md" else "code", "metadata": {},
                "source": src.splitlines(keepends=True)}
        if kind == "code":
            cell.update(execution_count=None, outputs=[])
        cells.append(cell)
    nb = {"nbformat": 4, "nbformat_minor": 5, "cells": cells,
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                       "language_info": {"name": "python"}, "colab": {"provenance": []}}}
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Zapisano {path}")


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    create_notebook(here / "EGMS_prototyp.ipynb", CELLS_PROTOTYP)
    create_notebook(here / "EGMS_pobranie_PTO1.ipynb", CELLS_PTO1)
