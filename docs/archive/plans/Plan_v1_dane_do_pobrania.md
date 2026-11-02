# Plan v1 — dane do pobrania i dostarczenia

Status: PROPOSED, 2026-10-09. Część planu `Plan_v1_walidacja_EGMS.md`.

Lista zamknięta. Każda pozycja ma: co, skąd, co dokładnie wybrać, gdzie zapisać.
Po pobraniu dopisz wiersz do `data/00_Metadata/MANIFEST.csv` (szablon: `data/00_Metadata/MANIFEST.template.csv`).

**Ręcznie robisz trzy rzeczy: token CLMS (raz), plik GNSS (jeden plik) i tabelę reperów (z PDF).
Dane EGMS pobiera zadanie `ingest_egms` przez oficjalne API.**

## Jednorazowo — dostęp do API EGMS

| # | Co | Skąd | Gdzie zapisać |
|---|---|---|---|
| 0 | Token CLMS API (plik JSON z kluczem prywatnym) | konto na stronie CLMS (https://land.copernicus.eu), zakładka z tokenami API; instrukcja: https://eea.github.io/clms-api-docs/authentication.html | `MyDrive/GeoWorldLook/secrets/clms_token.json`, poza repozytorium |

Opis API: `docs/evidence/F5_zrodla_danych.md`, sekcja 1. Kod z oficjalnego notatnika nie był przeze mnie uruchamiany.

## Przypadek 1 — GNSS (stacja PTO1)

| # | Co | Skąd | Jak | Gdzie trafia |
|---|---|---|---|---|
| 1 | Szereg GNSS stacji PTO1 | https://download.pangaea.de/dataset/958598/files/PTO1.txt (strona zbioru: https://doi.org/10.1594/PANGAEA.958598) | ręcznie albo skryptem (zwykłe pobranie pliku) | `data/02_Raw_Ground/1_gnss_pangaea/PTO1.txt` |
| 2 | EGMS Calibrated (L2B), ścieżki 117, 44 i 95 | API EGMS | zapytanie dla punktu = współrzędne stacji; wydanie **2018–2022** | `data/01_Raw_EGMS/2018_2022/L2b/` |
| 3 | EGMS Ortho pion (L3), opcjonalnie | API EGMS | zapytanie dla punktu, `productType = ORTHO-UP`; wydanie 2018–2022 | `data/01_Raw_EGMS/2018_2022/L3/` |

Uwagi do pozycji 2:
- Współrzędne stacji pochodzą z pliku z pozycji 1, więc najpierw pozycja 1.
- Artykuł podaje „sceny" 264–266 (ścieżka 117), 265–267 (44), 806–808 (95). Wynik zapytania pokaże, czy to numery burstów.
- Jeśli `GET /releases` nie zwraca wydania 2018–2022, zatrzymaj się: zmienia to okno czasowe testu.

Po pobraniu pozycji 1 sprawdź od razu: pierwszą i ostatnią datę oraz współrzędne stacji w pliku.

## Przypadek 2 — repery (Hengelo)

| # | Co | Skąd | Jak | Gdzie trafia |
|---|---|---|---|---|
| 4 | Raport niwelacyjny Strootbeekpark 2023 | https://www.nlog.nl/sites/default/files/2025-10/20240327_487387_meetregister_strootbeekpark_jaarlijks_2023_00.pdf | ręcznie, jeden PDF | `docs/evidence/literatura_pdf/` |
| 5 | Tabela reperów z załącznika 5 („differentiestaat") | pozycja 4 | **ręcznie**: numer, X, Y (układ RD), wysokość NAP w każdej epoce; osobno dokładne daty epok | `data/02_Raw_Ground/2_levelling_hengelo/differentiestaat_2023.csv` (szablon: `data/00_Metadata/hengelo_differentiestaat.template.csv`) |
| 6a | EGMS Ortho pion (L3) do nałożenia | API EGMS | prostokąt obejmujący sieć reperów, `ORTHO-UP`; wydanie **2019–2023** (albo 2020–2024, jeśli jest) | `data/01_Raw_EGMS/<wydanie>/L3/` |
| 6b | EGMS Ortho pion (L3) do prognozy | API EGMS | ten sam prostokąt; wydanie **2018–2022** | `data/01_Raw_EGMS/2018_2022/L3/` |
| 7 | EGMS Calibrated (L2B), obie orbity, pomocniczo | API EGMS | ten sam prostokąt; wydanie jak w 6a | `data/01_Raw_EGMS/<wydanie>/L2b/` |

Wskazówki:
- Pozycja 5 to praca ręczna, ok. 50 reperów. Przepisane wartości powinna sprawdzić druga osoba albo drugi przebieg.
  Kontrola: różnice wyliczone z wysokości muszą dać zakres od −42 do +2 mm względem 2020 r.
- Prostokąt dla pozycji 6 i 7 wynika ze współrzędnych reperów, więc najpierw pozycja 5.
  Wstępnie można użyć prostokąta wokół Hengelo i sprawdzić, czy przy reperach są punkty.
- Pozycja 7 jest potrzebna tylko wtedy, gdy L3 ma za mało komórek z danymi przy reperach.

## Test pokrycia T3 (opcjonalny)

| # | Co | Skąd | Gdzie zapisać |
|---|---|---|---|
| 8 | Geometria sieci lub obiektu pilotażowego (linie, poligony) | dane otwarte, np. OpenStreetMap | `data/02_Raw_Ground/3_pilot_area/` |
| 9 | EGMS L2b (obie orbity) i L3 dla obszaru pilotażowego | API EGMS | `data/01_Raw_EGMS/<wydanie>/` |

## Czego nie musisz pobierać

- Tabele z artykułu Fabris i Nazari są już w `data/04_Reference/`.
- Pełne teksty publikacji są w `docs/evidence/literatura_txt/`; PDF-y przydadzą się tylko do rycin i wzorów.
- Danych GNSS dla TGPO, CODI i Lorki oraz niwelacji NRW nie potrzebujesz do dwóch głównych przypadków.

## Jak dostarczyć

- **Do Claude Code lub na Dysk Google** (`MyDrive/GeoWorldLook/egmscheck`): pozycje 1, 4 i 5 w podanych ścieżkach;
  token (pozycja 0) na Dysku poza katalogiem repozytorium.
- **Do mnie w tej rozmowie:** wgraj `PTO1.txt` oraz pliki EGMS pobrane przez API dla ścieżki 117; policzę pierwszy wykres.
  Dla przypadku 2 wgraj PDF (pozycja 4); spróbuję odczytać załącznik 5 ze stron PDF. Tokenu mi nie wysyłaj.

## Rozmiary

Zapytanie `search` zwraca `filesize` każdego pliku przed pobraniem. Zadanie `ingest_egms` powinno wypisać
łączny rozmiar i poprosić o potwierdzenie, zanim zacznie pobierać.
