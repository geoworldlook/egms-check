"""
Generator notatnika notebooks/EGMS_Monitoring.ipynb (pokaz EGMS 2020-2024 dla Groningen i zachodniej NRW,
monitoring na danych archiwalnych i etap B: ASF HyP3 + MintPy). Notatnika nie edytuj ręcznie: zmień CELLS
i uruchom `python build_colab_monitoring.py`. Logika obliczeń jest w modułach step_01..step_08; każde zadanie
idzie przez step_05_colab_run.run_task (zapis w gwl_runs; błąd zatrzymuje notatnik).
Notatnik E1 (notebooks/EGMS_Check.ipynb, build_colab_master.py) zostaje bez zmian.
"""
import json
from pathlib import Path

REPO_URL = "https://github.com/geoworldlook/2_geoworldlook-egmscheck.git"
BRANCH = "claude/dreamy-dirac-jd4vue"


def _region_cells(region: str, title: str, levelling: bool) -> list:
    """Komórki jednego regionu: GNSS, (niwelacja), wyszukanie EGMS, potwierdzenie, pobranie, wycinki, kontrole, porównania."""
    var = f"CONFIRM_MB_{region.upper()}"
    name = title.split(" ", 1)[1].split(" (")[0]          # "2. Groningen (wydobycie gazu)" -> "Groningen"
    lev_task = (f"\nrun_task(rt, 'levelling_{region}', task_levelling, rt, cfg, '{region}')" if levelling else "")
    cells = [
        ("md", f"""## {title}
Kolejność: wyszukanie plików EGMS L2b i L3 (bez pobierania) z planem miejsca na Dysku → potwierdzenie rozmiaru →
pobranie → stacje GNSS według reguły z konfiguracji → dobowe szeregi GNSS{' → niwelacja (repery w obszarze)' if levelling else ''} →
ponowne wyszukanie i pobranie plików dla punktów spoza obszaru → wycinki i kontrole. Pobranie EGMS wymaga tylko
zatwierdzonego wydania i obszaru, więc może ruszyć przed decyzjami o GNSS{', niwelacji' if levelling else ''} i progach.
Pobranie wymaga wpisania liczby MB z planu w komórce poniżej (ochrona przed przypadkowym pobraniem wielu GB)."""),
        ("code", f"""P_{region.upper()} = region_paths(rt, cfg, '{region}')
run_task(rt, 'egms_search_{region}', task_egms_search, rt, cfg, '{region}')
if P_{region.upper()}['plan'].exists():
    plan = pd.read_csv(P_{region.upper()}['plan'])
    display(plan.groupby(['query_key', 'status']).agg(files=('filename', 'size'), MB=('filesize', lambda s: round(s.sum() / 1e6, 1))))"""),
        ("md", f"""### Potwierdzenie rozmiaru pobrania: {name}
Wpisz liczbę MB z komunikatu `egms_search_{region}` (suma plików brakujących, zaokrąglona). Inna liczba albo `None`
zatrzymuje notatnik z komunikatem, jaką wartość wpisać. Gdy po wyborze stacji ponowne wyszukanie znajdzie pliki dla
punktów spoza obszaru, notatnik zatrzyma się z nową liczbą MB do wpisania tutaj; pobrane pliki zostają na Dysku.
Bez tokenu CLMS notatnik czyta istniejące wycinki z `data/03_Extracts/`."""),
        ("code", f"""{var} = None   # np. 4321 - liczba MB z planu"""),
        ("code", f"""run_task(rt, 'egms_download_{region}', task_egms_download, rt, cfg, '{region}', {var})
run_task(rt, 'select_gnss_{region}', task_select_gnss, rt, cfg, '{region}')
run_task(rt, 'gnss_download_{region}', task_gnss_download, rt, cfg, '{region}'){lev_task}
display(pd.read_csv(P_{region.upper()}['sites'], dtype={{'site': str}}).head(30))
# Punkty spoza obszaru (np. stacje stabilne z okolicy): ponowne wyszukanie dobiera ich pliki. Gdy potrzeba nowych plików,
# pobranie zatrzymuje się z liczbą MB do wpisania w {var}; po wpisaniu uruchom notatnik ponownie (pobrane pliki zostają).
run_task(rt, 'egms_search_sites_{region}', task_egms_search, rt, cfg, '{region}')
run_task(rt, 'egms_download_sites_{region}', task_egms_download, rt, cfg, '{region}', {var})
run_task(rt, 'extract_{region}', task_extract, rt, cfg, '{region}')
run_task(rt, 'checks_{region}', task_checks, rt, cfg, '{region}')
display(pd.read_csv(P_{region.upper()}['checks']))"""),
        ("md", """### Porównanie z GNSS
Każda para stacja × ścieżka L2b (LOS, bufory 100 i 200 m) i stacja × komórka L3 (pion). Para bez punktów EGMS ma wiersz
ze statusem — nie znika z tabeli. Werdykt L2b według kryteriów K1–K4 (jak E1); dla L3 zdefiniowany jest tylko próg K1."""),
        ("code", f"""run_task(rt, 'compare_gnss_{region}', task_compare_gnss, rt, cfg, '{region}')
if P_{region.upper()}['gnss_compare'].exists():
    res = pd.read_csv(P_{region.upper()}['gnss_compare'], dtype={{'site': str}})
    cols = ['product', 'site', 'group', 'track', 'radius_m', 'n_points', 'v_gnss_los', 'v_egms', 'dv', 'series_diff_std', 'meets_A6', 'status']
    display(res[[c for c in cols if c in res]].round(2))
    for key in ('verdict_l2b', 'verdict_l3u'):
        if P_{region.upper()}[key].exists():
            display(pd.read_csv(P_{region.upper()}[key]))
            print('WNIOSEK:', P_{region.upper()}[key].with_suffix('.txt').read_text())"""),
    ]
    if levelling:
        cells += [
            ("md", """### Porównanie z niwelacją
Δh niwelacji i EGMS L3 (pion) między pierwszą i ostatnią epoką reperu w oknie dat EGMS; kryteria N1–N4
(mediana |różnicy|, zgodność znaku, kontrola negatywna na reperach stabilnych, bias prędkości)."""),
            ("code", f"""run_task(rt, 'compare_levelling_{region}', task_compare_levelling, rt, cfg, '{region}')
display(pd.read_csv(P_{region.upper()}['levelling_summary']))"""),
        ]
    return cells


CELLS = [
    ("md", """# EGMS 2020–2024: pokaz dla Groningen i zachodniej NRW oraz droga do monitoringu co 6/12 dni

**Pytanie.** Co pokazuje European Ground Motion Service (EGMS, Sentinel-1 InSAR) w dwóch obszarach osiadania i wypiętrzania,
jak zgadza się z pomiarem naziemnym (GNSS, niwelacja) i po jakim czasie od nowych akwizycji osiadanie byłoby widoczne
ponad szumem, gdyby EGMS aktualizować co 6/12 dni, a nie raz w roku?

**Dane (otwarte).** EGMS Calibrated L2b (LOS) i Ortho L3 (pion), wydanie 2020–2024, Copernicus Land Monitoring Service ·
dobowe szeregi GNSS z Nevada Geodetic Laboratory · niwelacja Geobasis NRW · etap B: Sentinel-1 przetworzony w ASF HyP3 i MintPy.

**Zasady.** Parametry i progi są w `CHECK_CONFIG` (`step_05_colab_run.py`); sekcja niezatwierdzona przez autora zatrzymuje
zadania, które jej używają. Każde zadanie zapisuje się w rejestrze `gwl_runs` na Dysku; błąd zatrzymuje notatnik.
Pomiar naziemny potwierdza tempo osiadania widoczne w EGMS — EGMS jest produktem archiwalnym i nie wykrywa zdarzeń nagłych.

Uruchom: `Środowisko wykonawcze → Uruchom wszystko`. Pobranie EGMS i zlecenia HyP3 wymagają potwierdzenia (sekcje 2, 3, 5)."""),
    ("md", "## 0. Środowisko\nMontowanie Dysku, klon lub aktualizacja repozytorium na Dysku, świeży import modułów, pakiety etapu A."),
    ("code", f"""import os, subprocess, sys
from google.colab import drive
drive.mount('/content/drive')
REPO_URL, BRANCH = '{REPO_URL}', '{BRANCH}'
PROJECT_DIR = '/content/drive/MyDrive/GeoWorldLook/egmscheck'

def git(*args):
    # Błąd gita zatrzymuje notatnik (polecenie '!git' nie zatrzymuje: po nieudanym pull liczyłby stary kod).
    r = subprocess.run(['git', *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {{' '.join(args)}} -> kod {{r.returncode}}: {{(r.stderr or r.stdout).strip()}}")
    return r.stdout.strip()

if not os.path.exists(os.path.join(PROJECT_DIR, '.git')):
    os.makedirs(os.path.dirname(PROJECT_DIR), exist_ok=True)
    git('clone', '-q', '-b', BRANCH, REPO_URL, PROJECT_DIR)
else:
    git('-C', PROJECT_DIR, 'fetch', '-q', 'origin', BRANCH)
    git('-C', PROJECT_DIR, 'checkout', '-q', BRANCH)
    git('-C', PROJECT_DIR, 'pull', '-q', '--ff-only', 'origin', BRANCH)
print(git('-C', PROJECT_DIR, 'log', '-1', '--format=Kod: %h %ci %s'))
os.chdir(PROJECT_DIR)
sys.path.insert(0, PROJECT_DIR)
for m in [m for m in sys.modules if m.startswith('step_0')]:
    del sys.modules[m]                      # po git pull importujemy świeży kod
import copy, json
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from pathlib import Path
from IPython.display import display, Image, Markdown
pd.set_option('display.width', 200); pd.set_option('display.max_columns', 30)
from step_05_colab_run import (setup_runtime, ensure_packages, run_task, run_history, registry_summary, region_paths,
                               hyp3_planned_tracks, STAGE_A_PACKAGES, STAGE_B_PACKAGES,
                               task_select_gnss, task_gnss_download, task_levelling, task_egms_search, task_egms_download,
                               task_extract, task_checks, task_compare_gnss, task_compare_levelling,
                               task_monitoring_archive, task_figures, task_hyp3_plan, task_hyp3_submit,
                               task_hyp3_download, task_mintpy, task_hyp3_compare, task_summary)
rt = setup_runtime(PROJECT_DIR, STAGE_A_PACKAGES)
print('Projekt:', rt['PROJECT_DIR'], '| commit:', rt['GIT_COMMIT'])"""),
    ("md", """## 1. Konfiguracja i zatwierdzenia
`cfg` to kopia `CHECK_CONFIG`. Tabela pokazuje, które sekcje autor zatwierdził (data) i jakie decyzje są otwarte
(wartości `None`). Wartości oznaczone w kodzie `[p]` to propozycje; zmienia się je w `step_05_colab_run.py` z datą zatwierdzenia,
nigdy po obejrzeniu wyników."""),
    ("code", """from step_05_colab_run import CHECK_CONFIG, approvals_table
cfg = copy.deepcopy(CHECK_CONFIG)
display(approvals_table(cfg))"""),
] + _region_cells("groningen", "2. Groningen (wydobycie gazu)", levelling=False) \
  + _region_cells("nrw_west", "3. Zachodnia NRW (odkrywki węgla brunatnego, wypiętrzanie)", levelling=True) + [
    ("md", """## 4. Monitoring na danych archiwalnych i ryciny
Wspólny format szeregów (`timeseries_long.csv.gz`): EGMS L2b (mediana punktów w buforze), EGMS L3 (komórka), GNSS w LOS
i w pionie, niwelacja. Próbkowanie akwizycji (6 dni do końca Sentinel-1B, potem 12 dni) i „ile czasu do wykrycia”:
prędkość z rosnącego okna z niepewnością poprawioną na autokorelację (AR(1)), dla EGMS i GNSS w tych samych datach."""),
    ("code", """for region in ('groningen', 'nrw_west'):
    run_task(rt, f'monitoring_archive_{region}', task_monitoring_archive, rt, cfg, region)
    run_task(rt, f'figures_{region}', task_figures, rt, cfg, region)
    P = region_paths(rt, cfg, region)
    display(pd.read_csv(P['ttd'], dtype={'site': str, 'track': str}).pivot_table(index=['site', 'track'], columns=['source', 'start'], values='ttd_months', aggfunc='first'))
    for png in sorted(P['figures'].glob(f'{region}_*.png'))[:12]:
        print(png.name); display(Image(filename=str(png), width=800))"""),
    ("md", """## 5. Etap B: własne przetworzenie Sentinel-1 (ASF HyP3 + MintPy)
Ścieżki z planu EGMS L2b regionu z `cfg['hyp3']['region']`. Bursty pokrywające punkty naziemne, sieć par SBAS i zlecenia
HyP3 (płatne kredytami): najpierw plan bez wysyłania, potem potwierdzenie liczby zleceń na ścieżkę. Zlecenia przetwarzają się
godzinami — pobranie i MintPy uruchom ponownie, gdy zlecenia mają status SUCCEEDED. Zakładka z EGMS (2024) służy
do sprawdzenia i dowiązania szeregu; dalsze daty to „monitoring”, którego EGMS jeszcze nie ma."""),
    ("code", """ensure_packages(STAGE_B_PACKAGES)
HYP3_REGION = cfg['hyp3']['region']
run_task(rt, f'hyp3_plan_{HYP3_REGION}', task_hyp3_plan, rt, cfg, HYP3_REGION)
display(pd.read_csv(region_paths(rt, cfg, HYP3_REGION)['hyp3_plan']))"""),
    ("md", """### Potwierdzenie zleceń HyP3
Wpisz słownik `{ścieżka: liczba zleceń}` z komunikatu `hyp3_plan_...`. `None` albo inna liczba zatrzymuje notatnik."""),
    ("code", """CONFIRM_JOBS = None   # np. {'37': 54, '88': 54}"""),
    ("code", """for track in hyp3_planned_tracks(rt, cfg, HYP3_REGION):
    run_task(rt, f'hyp3_submit_{HYP3_REGION}_{track}', task_hyp3_submit, rt, cfg, HYP3_REGION, track,
             None if CONFIRM_JOBS is None else CONFIRM_JOBS.get(track))
for track in hyp3_planned_tracks(rt, cfg, HYP3_REGION):
    run_task(rt, f'hyp3_download_{HYP3_REGION}_{track}', task_hyp3_download, rt, cfg, HYP3_REGION, track)
    run_task(rt, f'mintpy_{HYP3_REGION}_{track}', task_mintpy, rt, cfg, HYP3_REGION, track)
    run_task(rt, f'hyp3_compare_{HYP3_REGION}_{track}', task_hyp3_compare, rt, cfg, HYP3_REGION, track)
P = region_paths(rt, cfg, HYP3_REGION)
for f in sorted(P['outputs'].glob('hyp3_align_*.csv')):
    print(f.name); display(pd.read_csv(f).round(2))
for png in sorted(P['figures'].glob(f'{HYP3_REGION}_hyp3_series_*.png'))[:6]:
    print(png.name); display(Image(filename=str(png), width=800))"""),
    ("md", """## 6. Podsumowanie uruchomienia
`run_summary.md` i `run_summary.json` (wersje bibliotek, konfiguracja, wydanie EGMS, commit, zatwierdzenia, werdykty,
ostatnie uruchomienia) w `data/05_Final_Outputs/egmscheck/`."""),
    ("code", """run_task(rt, 'summary', task_summary, rt, cfg)
display(run_history(rt, 30))
display(registry_summary(rt))
display(Markdown(Path(PROJECT_DIR, cfg['project']['outputs_dir'], 'run_summary.md').read_text()[:6000]))"""),
    ("md", """## Jak czytać wynik
- Zgodność EGMS z GNSS i niwelacją dotyczy powolnego osiadania i wypiętrzania tam, gdzie są punkty pomiarowe; EGMS L2b/L3
  jest kalibrowany modelem GNSS, więc zgodność prędkości bezwzględnej nie jest w pełni niezależna.
- „Czas do wykrycia” mówi, po ilu miesiącach nowych akwizycji trend przekracza k × niepewność; nie dotyczy zdarzeń nagłych.
- Etap B pokazuje, że ten sam szereg można przedłużać poza wydanie EGMS (monitoring), po sprawdzeniu na zakładce z EGMS."""),
]


def create_notebook(path: Path) -> None:
    cells = []
    for i, (kind, src) in enumerate(CELLS):
        cell = {"cell_type": "markdown" if kind == "md" else "code", "id": f"cell-{i:02d}", "metadata": {},
                "source": src.splitlines(keepends=True)}
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
    create_notebook(Path(__file__).resolve().parent / "notebooks" / "EGMS_Monitoring.ipynb")
