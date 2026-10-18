# Plan v1 — potok obliczeń

Status: PROPOSED, 2026-10-09. Część planu `Plan_v1_walidacja_EGMS.md`. Układ plików jak w AgriWatch.

## Zasada

Jeden kod, dwa przypadki w jednym `CHECK_CONFIG`. Wspólne: wczytanie EGMS, kontrole, wybór przestrzenny,
dopasowanie czasowe, metryki, wykresy. Różne: czytnik danych naziemnych i sposób odniesienia.

## Etapy

| # | Etap | Przypadek | Wyjście | Kontrole |
|---|---|---|---|---|
| 0 | Manifest danych | oba | `data/00_Metadata/MANIFEST.csv` | każdy plik ma adres, datę, SHA-256, licencję |
| 1 | Wczytanie EGMS | oba | tabela punktów + tabela szeregów | kolumny wg `docs/evidence/F5`; daty `yyyymmdd`; mm |
| 2 | Scalenie burstów, duplikaty | oba (L2b) | punkty bez duplikatów; ile usunięto | A5 |
| 3 | Kontrole konwencji | oba | raport kontroli | A1–A4; błąd zatrzymuje przebieg |
| 4a | Wczytanie GNSS | 1 | szereg Up [mm] z datami | zakres, przerwy, skoki opisane |
| 4b | Wczytanie niwelacji | 2 | repery: X, Y, wysokości w epokach | suma kontrolna z etykietami mapy; RD → EPSG:3035 |
| 5 | Wybór przestrzenny | oba | punkty EGMS na stację/reper, liczby, odległości | pusty wybór → `NaN` z powodem |
| 6 | Szereg EGMS w miejscu pomiaru | oba | średnia/mediana i rozrzut na datę | min. liczba punktów z konfiguracji |
| 7a | Rzut GNSS na LOS, agregacja, wspólne okno | 1 | dwa szeregi w LOS, wyzerowane | A6 (≥ 85%) |
| 7b | Odniesienie do reperu, odczyt w epokach | 2 | Δh z EGMS i z niwelacji na reper | odniesienie jawne |
| 8 | Prędkości i różnice | oba | Δv, różnice szeregów, Δh | ten sam model i okno dla obu źródeł |
| 9 | Test prognozy | 2 | prognoza kontra pomiar | dane uczące kończą się przed epoką |
| 10 | Kryteria | oba | status każdego progu z `Plan_v1_kryteria_akceptacji` | progi zatwierdzone przed przebiegiem |
| 11 | Wykresy i raport | oba | `data/05_Final_Outputs/egmscheck/` | komplet z `Plan_v1_kryteria_akceptacji`, sekcja D |
| 12 | Wycinki do notatnika | oba | małe pliki w `data/03_Extracts/` (punkty z buforów, szeregi, tabela reperów) | czytelnik bez tokenu odtwarza wyniki z wycinków |
| 13 | Notatnik na blog | oba | `notebooks/EGMS_Check.ipynb` (generowany) | wykonuje się od góry do dołu; ryciny PNG w `data/05_Final_Outputs/egmscheck/figures/` |

## Dwa tryby pracy (jak w AgriWatch)

- **Zadania `task_*`** uruchamiane z notatnika przez `run_task`: wczytanie plików z Dysku, kontrole, wycinki, porównania, raport.
- **Notatnik `notebooks/EGMS_Check.ipynb`** generowany przez `build_colab_master.py`. To on trafia na blog
  (`docs/plans/Plan_v1_wpis_na_blog.md`).

Logika obliczeń jest w modułach `step_NN`, importowanych z notatnika; notatnik nie zawiera własnych obliczeń.

## Moduły

| Plik | Etapy z tabeli | Zadania |
|---|---|---|
| `step_01_ingest.py` | 0, 1, 4a, 4b | `ingest_egms`, `ingest_ground` |
| `step_02_checks_extract.py` | 2, 3, 5, 6, 12 | `checks`, `extract` |
| `step_03_compare_gnss.py` | 7a, 8 | `compare_gnss` |
| `step_04_compare_levelling.py` | 7b, 8, 9 | `compare_levelling`, `forecast` |
| `step_05_colab_run.py` | 10 + sterowanie | `setup_runtime`, `run_task`, rejestr `gwl_*`, `CHECK_CONFIG`, `--selftest` |
| `step_06_figures_bulletin.py` | 11 | `bulletin`, `summary` |
| `build_colab_master.py` | 13 | generator notatnika |

Opis architektury i mapowanie na tabele rejestru: `docs/ARCHITEKTURA.md`.

## Testy, które mają sens naukowy

Bez danych:
- ruch czysto pionowy U przy wektorze LOS (0, 0, 1) daje d_LOS = U,
- rzut pionu `U · los_up` równa się `U · cos θ` dla spójnego punktu,
- ruch wschodni daje przeciwne znaki d_LOS na orbicie wstępującej i zstępującej,
- prędkość z syntetycznego szeregu „trend + sinusoida + szum" odtwarza zadany trend w granicach niepewności,
- odjęcie szeregu odniesienia od samego siebie daje zero,
- przeliczenie RD → EPSG:3035 → RD wraca do punktu wyjścia w granicach mm.

Na danych:
- `incidence_angle` przy PTO1 mieści się w przedziałach z `Plan_v1_kryteria_akceptacji`,
- prędkości w buforze przy PTO1 mają znak ujemny na trzech ścieżkach,
- suma kontrolna przepisanej tabeli reperów: różnice wyliczone z wysokości zgadzają się z etykietami mapy
  i z zakresem z tekstu raportu (od −42 do +2 mm; od −13 do +2 mm).

## Kolejność realizacji

**Przypadek 1 (GNSS):**
1. Pytania A1, A2, A6 z `Plan_v1_otwarte_pytania`.
2. Etapy 0–3 dla ścieżki 117.
3. Etapy 4a–8 dla ścieżki 117; pierwszy wykres.
4. Ścieżki 44 i 95; bufor 100 m i 200 m.
5. Kryteria, tabela porównawcza z artykułem, komplet wykresów.

**Przypadek 2 (repery):**
1. Pytania A3, A4, A5 z `Plan_v1_otwarte_pytania`; przepisanie tabeli reperów.
2. Etapy 0, 1, 3, 4b, 5 dla L3; mapa reperów na tle prędkości EGMS.
3. Etapy 6, 7b, 8: nałożenie szeregów i wykres rozrzutu.
4. Etap 9: test prognozy z wydania 2018–2022.
5. Wariant L2b, jeśli L3 ma za mało komórek z danymi przy reperach.

Przy każdej decyzji z `Plan_v1_otwarte_pytania`, sekcja D, zatrzymaj się i zapytaj.

## Układ prezentacji

1. Pytanie i projekt: dwa miejsca, dwa rodzaje pomiaru naziemnego, progi ustalone z góry.
2. Skąd dane: źródła, instytucje, licencje, wydania EGMS.
3. Metoda na jednym schemacie: punkty EGMS wokół stacji lub reperu → ten sam kierunek i odniesienie → nałożenie.
4. Przypadek 1: wykres główny, różnica, trzy ścieżki, tabela z artykułem.
5. Przypadek 2: mapa, szeregi wybranych reperów, wykres rozrzutu, prognoza kontra pomiar.
6. Kontrole negatywne i znane granice metody.
7. Czego to nie dowodzi; następny etap (pokrycie nad konkretnym obiektem, np. siecią wodociągową).

## Środowisko

- Python ≥ 3.10; `numpy pandas scipy geopandas pyproj shapely matplotlib`.
- Pobranie EGMS: oficjalne API (`requests`, `pyjwt`), opis w `docs/evidence/F5_zrodla_danych.md`, sekcja 1.
  EGMS-toolkit zostaje jako zapas (wymaga GDAL ≥ 3.8 i GMT z GSHHG).
- Wersje bibliotek zapisuje `run_summary.md`, jak w AgriWatch.
