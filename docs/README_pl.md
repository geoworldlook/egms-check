> English version: [README.md](../README.md)

# EGMS Check — czy radarowe dane o ruchu gruntu zgadzają się z pomiarem naziemnym

> Nazwa robocza. Kod jeszcze nie istnieje: repozytorium zawiera plan, przegląd literatury,
> wartości referencyjne i strukturę wzorowaną na `1_geoworldlook-agriscreen` (AgriWatch).
> Odznaka „Open in Colab" pojawi się, gdy powstanie `notebooks/EGMS_Check.ipynb`.

Sprawdzenie danych European Ground Motion Service (EGMS, Copernicus, InSAR z Sentinel-1) na dwóch
otwartych zbiorach pomiarów naziemnych. Każdy przypadek kończy się wykresem „EGMS kontra pomiar naziemny".

| Przypadek | Miejsce | Pomiar naziemny | Sygnał | Co porównujemy |
|---|---|---|---|---|
| 1. GNSS | stacja PTO1, delta Padu (Włochy) | dobowy szereg wysokości, PANGAEA (CC BY 4.0) | ok. 5 mm/rok | szereg GNSS w kierunku patrzenia radaru i szereg EGMS z bufora wokół stacji |
| 2. Repery | Hengelo, pole solne Twenthe-Rijn (Holandia) | niwelacja precyzyjna 2020–2023, rejestr na portalu NLOG | do −42 mm w 3 lata | obniżenie reperów i EGMS (pion), także prognoza sprzed pomiaru |

Test i reguła decyzji: [`docs/plans/Plan_v1_test_EGMS.md`](plans/Plan_v1_test_EGMS.md).
Wynik trafi na blog GeoWorldLook: [`docs/plans/Plan_v1_wpis_na_blog.md`](plans/Plan_v1_wpis_na_blog.md).

**Architektura (jak w AgriWatch):** kod na GitHub → obliczenia w Google Colab → Dysk Google jako baza danych
(`MyDrive/GeoWorldLook/egmscheck`, tabele CSV `data/registry/gwl_*`). Szczegóły: [`docs/ARCHITEKTURA.md`](ARCHITEKTURA.md).

## Struktura repozytorium

```text
├── step_00_reference_check.py    # kontrola spójności tabel przepisanych z publikacji (działa już teraz)
├── step_01_ingest.py             # [częściowo] EGMS przez oficjalne API (wyszukanie i pobranie), szereg GNSS, tabela reperów, manifest
├── step_02_checks_extract.py     # [plan] kontrole konwencji EGMS, duplikaty z zakładek burstów, wycinki do notatnika
├── step_03_compare_gnss.py       # [plan] przypadek 1: rzut na LOS, wspólne okno, prędkości, różnice
├── step_04_compare_levelling.py  # [plan] przypadek 2: odniesienie do reperu, różnice wysokości, prognoza
├── step_05_colab_run.py          # [plan] sterowanie z notatnika: setup_runtime, run_task, rejestr gwl_*, zadania, --selftest
├── step_06_figures_bulletin.py   # [plan] wykresy, biuletyn, JSON dla strony, run_summary.md
├── build_colab_master.py         # [plan] generator notatnika
├── notebooks/EGMS_Check.ipynb    # [plan] notatnik = podstawa wpisu na blog
├── data/
│   ├── 00_Metadata/              # manifest plików, szablony, konfiguracje przypadków
│   ├── 01_Raw_EGMS/              # pliki pobrane przez API EGMS (poza repozytorium)
│   ├── 02_Raw_Ground/            # 1_gnss_pangaea/PTO1.txt, 2_levelling_hengelo/differentiestaat_2023.csv
│   ├── 03_Extracts/              # małe wycinki EGMS wokół stacji i reperów (w repozytorium; czyta je notatnik)
│   ├── 04_Reference/             # liczby z publikacji i z raportu niwelacyjnego
│   └── 05_Final_Outputs/         # wykresy, biuletyn, run_summary.md (poza repozytorium)
├── docs/
│   ├── ARCHITEKTURA.md           # architektura docelowa
│   ├── plans/                    # plan v1: test, potok, dane, kryteria, pytania, wpis na blog
│   └── evidence/                 # F1 przegląd literatury, F2–F3 przypadki, F4 metodyka, F5 źródła danych, F6 zapas
└── CLAUDE.md                     # zasady pracy dla Claude Code
```

Pozycje `[plan]` jeszcze nie istnieją. Numeracja i nazwy plików idą śladem AgriWatch (`step_NN_<cel>.py`,
katalogi danych z prefiksem liczbowym, `docs/plans`, `docs/evidence/F*`).

## Uruchomienie (stan obecny)

**Stan projektu, migracja i audyt:** [`docs/MIGRACJA_stan_i_audyt.md`](MIGRACJA_stan_i_audyt.md)

**Walidacja EGMS na stacjach GNSS, region Groningen (2026-10-10):** [`notebooks/EGMS_Check.ipynb`](../notebooks/EGMS_Check.ipynb) —
[Otwórz w Colab](https://colab.research.google.com/github/geoworldlook/2_geoworldlook-egmscheck/blob/claude/dreamy-dirac-jd4vue/notebooks/EGMS_Check.ipynb)
(wymaga tokenu CLMS na Dysku; pobranie EGMS po akceptacji rozmiaru w sekcji 5).

**Prototyp w Colab (2026-10-10):** [`prototypes/EGMS_prototyp.ipynb`](../prototypes/EGMS_prototyp.ipynb) —
test metody na danych syntetycznych i opis szeregu GNSS PTO1, bez tokenu.
[Otwórz w Colab](https://colab.research.google.com/github/geoworldlook/2_geoworldlook-egmscheck/blob/claude/dreamy-dirac-jd4vue/prototypes/EGMS_prototyp.ipynb),
potem `Środowisko wykonawcze → Uruchom wszystko`.
Pobranie EGMS L2B dla PTO1 (wymaga tokenu CLMS na Dysku; pobiera dopiero po potwierdzeniu listy plików):
[Otwórz w Colab](https://colab.research.google.com/github/geoworldlook/2_geoworldlook-egmscheck/blob/claude/dreamy-dirac-jd4vue/prototypes/EGMS_pobranie_PTO1.ipynb).
Plan eksperymentów: [`docs/plans/Plan_v1_eksperymenty.md`](plans/Plan_v1_eksperymenty.md).

1. Przygotowanie krok po kroku: [`docs/plans/Instrukcja_startowa.md`](plans/Instrukcja_startowa.md).
2. Otwórz folder w Claude Code i wklejaj prompty z [`docs/plans/Prompty_Claude_Code.md`](plans/Prompty_Claude_Code.md), po jednym na sesję.
3. Kontrola tabel referencyjnych (bez danych, bez sieci):

```bash
python step_00_reference_check.py
```

Docelowo, jak w AgriWatch: otwarcie `notebooks/EGMS_Check.ipynb` w Colab, `Uruchom wszystko`, zadania
`ingest_egms → ingest_ground → checks → extract → compare_gnss → compare_levelling → forecast → bulletin → summary`,
wyniki w `data/05_Final_Outputs/egmscheck/` i tabelach `data/registry/gwl_*.csv`, na końcu `run_summary.md`.

## Zakres wersji 1.0 (propozycja, 2026-10-09)

Dwa miejsca, dwa rodzaje pomiaru naziemnego, produkty EGMS Calibrated i Ortho, progi ustalone przed obliczeniami.
Poza zakresem: wykrywanie zdarzeń nagłych, ruch północ–południe, ocena pokrycia nad konkretną siecią
(test T3 jest opcjonalny). Przypadki zapasowe (NRW, Lorca): `docs/evidence/F6_przypadki_zapasowe/`.

## Zależności (plan)

`numpy pandas scipy geopandas pyproj shapely matplotlib`; pobieranie EGMS dodatkowo `requests pyjwt`.
Czytelnik notatnika nie potrzebuje tokenu: gdy go brak, notatnik korzysta z wycinków w `data/03_Extracts/`.

## Źródła danych i atrybucje

EGMS: Copernicus Land Monitoring Service (formułę atrybucji sprawdź przed publikacją).
GNSS: Pintori F., Serpelloni E. (2023), PANGAEA, doi:10.1594/PANGAEA.958598, CC BY 4.0.
Niwelacja: Antea Group dla Nobian (2024), rejestr pomiarowy Twenthe-Rijn, sieć Strootbeekpark, portal NLOG.
Liczby do porównania: Fabris M., Nazari S. (2026), Front. Earth Sci. 14:1781404, CC BY.
