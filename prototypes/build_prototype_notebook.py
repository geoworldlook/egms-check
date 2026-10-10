"""
Generator notatnika prototypes/EGMS_prototyp.ipynb (prototyp E1/E2 do uruchomienia w Colab).
Notatnika nie edytuj ręcznie: zmień CELLS i uruchom `python prototypes/build_prototype_notebook.py`.
Docelowy notatnik projektu (notebooks/EGMS_Check.ipynb) powstanie w sesji 1 przez build_colab_master.py.
"""
import json
from pathlib import Path

REPO_URL = "https://github.com/geoworldlook/2_geoworldlook-egmscheck.git"
BRANCH = "claude/dreamy-dirac-jd4vue"

CELLS = [
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


def create_notebook(path: Path) -> None:
    cells = []
    for kind, src in CELLS:
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
    create_notebook(Path(__file__).resolve().parent / "EGMS_prototyp.ipynb")
