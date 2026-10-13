"""
Generator notatnika notebooks/EGMS_Pokaz.ipynb: krótki pokaz na spotkanie. Notatnik niczego nie liczy i niczego nie
pobiera - tylko czyta gotowe wyniki zapisane na Dysku przez notebooks/EGMS_Monitoring.ipynb (tabele i ryciny).
Wybór treści (autor 2026-10-13): dwa najmocniejsze, niezależne wyniki - EGMS kontra GNSS w Groningen i EGMS kontra
niwelacja w zachodniej NRW (wydanie 2019-2023). Repery na rycinach szeregów wybiera ta sama reguła co w notatniku
technicznym (monitoring.example_rule + mediana niecek), nie wybór ręczny. Notatnika nie edytuj ręcznie: zmień CELLS
i uruchom `python build_colab_pokaz.py`.
"""
import json
from pathlib import Path

CELLS = [
    ("md", """# EGMS kontra pomiar naziemny — pokaz

**Pytanie.** Czy European Ground Motion Service (EGMS, radar satelitarny Sentinel-1) pokazuje ten sam ruch terenu
co pomiar naziemny?

**Dwa niezależne sprawdzenia:**
1. **GNSS — Groningen (NL):** osiadanie nad polem gazowym; 35 stacji GNSS, EGMS 2020–2024.
2. **Niwelacja — zachodnia NRW (DE):** niecki osiadania przy odkrywkach węgla brunatnego; 1216 reperów,
   pomiary 05.2019 i 05.2022, EGMS 2019–2023. Niwelacja nie korzysta z GNSS, więc to sprawdzenie jest w pełni niezależne.

Progi oceny ustalono przed obliczeniami. Ten notatnik tylko pokazuje gotowe wyniki z `EGMS_Monitoring.ipynb`."""),
    ("code", """from google.colab import drive
drive.mount('/content/drive')
import json, subprocess, sys
from pathlib import Path
import pandas as pd
from IPython.display import display, Image, Markdown
PROJECT_DIR = '/content/drive/MyDrive/GeoWorldLook/egmscheck'
sys.path.insert(0, PROJECT_DIR)
from step_05_colab_run import CHECK_CONFIG, region_paths, levelling_check_paths, _levelling_check_examples
rt = {'PROJECT_DIR': PROJECT_DIR}
G, N = region_paths(rt, CHECK_CONFIG, 'groningen'), region_paths(rt, CHECK_CONFIG, 'nrw_west')
C = levelling_check_paths(rt, CHECK_CONFIG, 'nrw_west')
print('Kod na Dysku:', subprocess.run(['git', '-C', PROJECT_DIR, 'log', '-1', '--format=%h %ci'],
                                      capture_output=True, text=True).stdout.strip())

def pokaz(path, width=850):
    # Brak pliku = błąd (wyniki liczy EGMS_Monitoring.ipynb), nie pusta komórka.
    if not Path(path).exists():
        raise FileNotFoundError(f'Brak {path}: uruchom najpierw notebooks/EGMS_Monitoring.ipynb')
    display(Image(str(path), width=width))

def kryteria(path, kody):
    t = pd.read_csv(path)
    return t[t['kryterium'].str[:2].isin(kody)][['kryterium', 'wynik', 'próg', 'spełnione']].reset_index(drop=True)"""),
    ("md", """## 1. GNSS — Groningen

Każda stacja GNSS jest porównana z punktami EGMS w promieniu 100 m, osobno dla każdej ścieżki satelity.
Ruch GNSS przeliczono na kierunek patrzenia satelity. **K1** to odsetek par stacja–ścieżka, w których tempo ruchu
z EGMS i GNSS różni się najwyżej o 1,5 mm/rok."""),
    ("code", """display(kryteria(G['verdict_l2b'], ['K1', 'K2', 'K3']))
print('Wniosek (reguła ustalona przed obliczeniami):', G['verdict_l2b'].with_suffix('.txt').read_text().strip())
pokaz(G['figures'] / 'groningen_velocity_scatter.png', 650)"""),
    ("md", """**Jak czytać:** każdy punkt to stacja × ścieżka; linia to zgodność idealna, szary pas ±1,5 mm/rok.
Tempo osiadania się zgadza. Kontrola na stacjach „stabilnych” (K3) nie przeszła o włos, dlatego wniosek formalny to
zgodność częściowa. Punkty ze ścieżek wznoszących (niebieskie) leżą nieco nad linią, a z zstępujących (pomarańczowe) nieco
pod nią (ok. 0,5–1 mm/rok, w granicach progu). Taki układ wskazuje na niewielką różnicę ruchu poziomego wschód–zachód
między GNSS a EGMS; nie badaliśmy jej osobno. Ograniczenie: EGMS jest kalibrowany modelem GNSS, więc to porównanie nie jest w pełni niezależne —
stąd drugie sprawdzenie niwelacją."""),
    ("md", """## 2. Niwelacja — zachodnia NRW

Mapa pokazuje, gdzie EGMS widzi ruch: czerwone plamy to niecki osiadania (do kilkudziesięciu mm/rok). Mapa jest z tego
samego wydania EGMS (2019–2023) co porównanie z niwelacją; trójkąty to stacje GNSS, kółka to repery z rycin w czasie niżej."""),
    ("code", """pokaz(C['map'], 700)"""),
    ("md", """Każdy reper ma dwa pomiary niwelacyjne (maj 2019 i maj 2022). Dla tych samych dni odczytujemy EGMS w komórce 100 m
z reperem i porównujemy zmianę wysokości. Wybór reperów: wszystkie z dwoma pomiarami, bez wyboru według EGMS."""),
    ("code", """pokaz(C['figure'], 620)"""),
    ("md", """**Jak czytać:** oś pozioma — niwelacja, pionowa — EGMS, ta sama zmiana wysokości w mm. Pomarańczowe punkty to
repery w nieckach (|v| ≥ 10 mm/rok według niwelacji). Punkty leżą wzdłuż linii 1:1 aż do −140 mm.
Widać też, że cała chmura jest lekko przesunięta w dół: EGMS pokazuje wszędzie trochę więcej osiadania."""),
    ("code", """t1 = kryteria(C['summary'], ['N1', 'N2', 'N4']).rename(columns={'wynik': 'główny (bez odniesienia)', 'spełnione': 'spełnione (główny)'})
t2 = kryteria(C['summary_rel'], ['N1', 'N2', 'N4'])[['wynik', 'spełnione']].rename(columns={'wynik': 'względem reperów stabilnych', 'spełnione': 'spełnione (względny)'})
display(pd.concat([t1, t2], axis=1))
off = json.loads(C['offset_rel'].read_text())
print(f"Przesunięcie EGMS względem niwelacji na {off['n_group']} reperach stabilnych: "
      f"{off['offset_egms_minus_lev_mm_yr']:+.2f} ± {off['offset_se_mm_yr']:.2f} mm/rok")
g1, g2 = pd.read_csv(C['groups']), pd.read_csv(C['groups_rel'])
nie = pd.DataFrame({'wariant': ['główny', 'względny'], 'repery w nieckach': [g1['n'].iat[1], g2['n'].iat[1]],
                    'mediana |EGMS − niwelacja| [mm]': [g1['median_abs_diff_mm'].iat[1], g2['median_abs_diff_mm'].iat[1]],
                    'zgodność znaku': [g1['sign_agreement'].iat[1], g2['sign_agreement'].iat[1]],
                    'nachylenie': [g1['slope'].iat[1], g2['slope'].iat[1]],
                    'najbliższa stacja GNSS (mediana) [km]': [g1['dist_station_km_median'].iat[1], g2['dist_station_km_median'].iat[1]]})
display(nie.round(2))"""),
    ("md", """**Jak czytać:**
- wariant **główny** (zatwierdzony przed obliczeniami) porównuje wartości wprost, jak Even i in. (2024); nie spełnia progów
  przez stałe przesunięcie ok. 1–2 mm/rok, a nie przez rozrzut;
- wariant **względny** (dodatkowy, policzony po obejrzeniu głównego) odnosi oba pomiary do reperów, które według niwelacji
  się nie ruszają, czyli usuwa wspólne „zero”; wtedy wszystkie policzalne kryteria są spełnione;
- w nieckach EGMS i niwelacja zgadzają się co do znaku zawsze, a skala ruchu jest prawie 1:1.

Największe rozbieżności w nieckach (tabela niżej) pokazujemy wprost. W żadnej nie zmienia się znak ruchu — EGMS pokazuje
mniej osiadania niż niwelacja. Prawdopodobna przyczyna (nie sprawdzona): reper na brzegu niecki, gdzie komórka EGMS
100 × 100 m uśrednia teren osiadający szybciej i wolniej."""),
    ("code", """res = pd.read_csv(C['compare'], dtype={'benchmark_id': str})
strong = CHECK_CONFIG['regions']['nrw_west']['levelling']['strong_motion_mm_yr']
nie_ok = res[(res['status'] == 'ok') & (res['v_lev_mm_yr'].abs() >= strong)]
top = nie_ok.reindex(nie_ok['diff_mm'].abs().sort_values(ascending=False).index).head(3)
display(top[['benchmark_id', 'dh_lev_mm', 'dh_egms_mm', 'diff_mm']].rename(columns={
    'benchmark_id': 'reper', 'dh_lev_mm': 'niwelacja [mm]', 'dh_egms_mm': 'EGMS [mm]', 'diff_mm': 'EGMS − niwelacja [mm]'}).round(1))"""),
    ("md", """Te repery stanowią niewielką część z 54 reperów w nieckach; mediana różnicy w nieckach jest w tabeli wyżej.

Niecki mają kilka kilometrów szerokości, a model GNSS do kalibracji EGMS ma siatkę ok. 50 km. Takiej niecki kalibracja
nie mogła „dorysować” — EGMS zmierzył ją sam."""),
    ("md", """### Przykładowe repery w czasie

Niebieska linia: EGMS co 6–12 dni. Duże żółte punkty: dwa pomiary niwelacyjne; przerywana linia tylko je łączy,
między nimi niwelacji nie ma. Oba szeregi od zera w dniu pierwszego pomiaru. Repery wybrane regułą:
najszybsze osiadanie według niwelacji, mediana niecek i reper, który najmniej się rusza (kontrola)."""),
    ("code", """przyklady = dict((lab, bid) for bid, lab in _levelling_check_examples(res, CHECK_CONFIG['monitoring']['example_rule'], strong))
for lab in ('fastest subsidence by levelling', f'median rate in bowls (|v| >= {strong:g} mm/yr)', 'smallest |rate|, stable'):
    if lab not in przyklady:
        print(f'Reguła „{lab}”: ten sam reper co na rycinie wyżej albo brak reperów w tej grupie')
        continue
    pokaz(C['figure'].parent / f"nrw_west_levelling_series_2019_2023_{przyklady[lab]}.png", 900)"""),
    ("md", """## Podsumowanie

- **GNSS (Groningen):** tempo osiadania z EGMS zgodne z GNSS; wniosek formalny: zgodność częściowa.
- **Niwelacja (NRW):** pomiar niezależny od GNSS potwierdza niecki osiadania widoczne w EGMS — ten sam znak i ta sama skala
  ruchu, do −140 mm w 3 lata. Poziom bezwzględny różni się o stałe ok. 1–2 mm/rok; po odniesieniu do reperów stabilnych
  zgodność mieści się w progach.
- **Czego tu nie pokazujemy:** porównania z GNSS w NRW (w obszarze nie ma osiadającej stacji — wynik nierozstrzygnięty),
  krzywych „czasu do wykrycia” (wymagają poprawki metody) i etapu B (własne przetwarzanie Sentinel-1, nieuruchomione).
  Wszystko jest w `EGMS_Monitoring.ipynb` i w `docs/evidence/F10_NRW_niwelacja_EGMS.md`.

**Źródła:** EGMS (Copernicus Land Monitoring Service); GNSS: Nevada Geodetic Laboratory (Blewitt i in. 2016, 2018);
niwelacja: Geobasis NRW. Metoda: Koudogbo i in. (2025), EGMS Validation Report; porównanie z niwelacją NRW:
Even, Westerhaus, Kutterer (2024), PFG 92:253–270."""),
]


def create_notebook(path: Path) -> None:
    cells = []
    for i, (kind, src) in enumerate(CELLS):
        cell = {"cell_type": "markdown" if kind == "md" else "code", "id": f"pokaz-{i:02d}", "metadata": {},
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
    create_notebook(Path(__file__).resolve().parent / "notebooks" / "EGMS_Pokaz.ipynb")
