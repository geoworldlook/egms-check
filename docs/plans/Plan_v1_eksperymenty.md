# Plan v1 — dwa proste eksperymenty: czy EGMS jest użyteczny

Status: PROPOSED, 2026-10-10. Część planu `Plan_v1_walidacja_EGMS.md`.
Podstawa: `docs/evidence/F7_przeglad_literatury_eksperymenty.md` (6 publikacji w pełnym tekście + literatura dodatkowa).
Kod: `prototypes/egms_simple_check.py` (prototyp; w sesjach 1–5 i 9 przechodzi do `step_02`–`step_04`).

## 1. Pytanie i warunki

Czy darmowe dane EGMS podają to samo tempo i tę samą wielkość osiadania co zaufany pomiar naziemny?

Warunki od autora (2026-10-10):
1. walidacja na stacji GNSS,
2. walidacja na rzeczywistym osiadaniu lub przemieszczeniu, **dla którego walidacja EGMS była już wykonana**,
3. dane otwarte i rzetelne,
4. prosty eksperyment w Pythonie,
5. literatura dodatkowa, jeśli potrzebna.

| Eksperyment | Miejsce | Pomiar naziemny | Opublikowana walidacja | Dane otwarte | Warunki 1–3 |
|---|---|---|---|---|---|
| **E1** | PTO1, delta Padu | dobowy pion GNSS (PANGAEA, CC BY 4.0) | Fabris i Nazari 2026 | tak | spełnia |
| **E2 (rekomendacja)** | zachodnia NRW, odkrywki węgla brunatnego i zatapiane kopalnie | niwelacja państwowa (Geoportal NRW) | Even i in. 2024 (279 reperów, bias 0,93 mm/rok, σ 1,76 mm) | tak (licencję potwierdzić) | spełnia |
| E2′ (dotychczasowy przypadek 2) | Hengelo, kawerny solne | niwelacja precyzyjna 2020–2023 (NLOG, PDF) | **brak** | do pobrania, licencja niepodana | nie spełnia warunku 2 |

**Rekomendacja:** E2 na danych z NRW jako eksperyment główny (odtworzenie opublikowanej walidacji),
Hengelo jako rozszerzenie „nasz własny test i prognoza”. To zmienia przypadek 2 w `CLAUDE.md`,
więc wymaga Twojej decyzji (D-E2 w sekcji 6).

## 2. E1 — EGMS kontra stacja GNSS PTO1

**Hipoteza H1:** w buforze wokół PTO1 prędkość EGMS L2b w LOS różni się od prędkości GNSS rzutowanej na LOS
o nie więcej niż 1,5 mm/rok na każdej z trzech ścieżek, a odchylenie różnicy szeregów jest ≤ 5 mm.

**Hipoteza zerowa w praktyce:** jeśli pipeline ma błąd znaku, układu lub okna, różnice wyjdą rzędu kilku mm/rok
(kontrola negatywna w teście syntetycznym daje 2,4 mm/rok przy prędkości zmienionej o 3 mm/rok w pionie).

### 2.1 Dane

| Element | Wybór | Uwagi |
|---|---|---|
| GNSS | `PTO1.txt`, 2008-06-18 – 2021-04-13, 4248 dób | jedna przerwa > 30 dni: 2018-12-16 → 2019-02-06 |
| Stacja w EPSG:3035 | E 4 505 481,6 m, N 2 429 535,0 m | przeliczone z pliku (pyproj) |
| EGMS | L2b, ścieżki 117 i 44 (wstępujące), 95 (zstępująca) | wydanie: decyzja D-A |
| Wartości do porównania | `data/04_Reference/fabris2026_tab3_egms_buffers.csv`, `..._tab4_differences.csv` | |

### 2.2 Dwa poziomy

**E1a — odtworzenie artykułu (test pipeline'u).** Wymaga wydania 2018–2022 (archiwum, wniosek do CLMS Helpdesk).
Dla każdej ścieżki: liczba punktów i średnia `mean_velocity` dla 1, 2, 3 najbliższych punktów i buforów
50/100/150/200 m. Porównanie z tabelą 3 artykułu. Oczekiwanie: te same liczby punktów (±2% **[propozycja]**)
i średnie co do ok. 0,1–0,2 mm/rok. Rozbieżność oznacza najpewniej inną obsługę duplikatów, filtr wysokości
albo inne wydanie i wymaga wyjaśnienia przed E1b.

**E1b — porównanie szeregów (właściwy test H1).** Wymaga wydania z D-A.

| Krok | Funkcja w prototypie | Parametr z konfiguracji |
|---|---|---|
| 1. Wczytaj EGMS, kontrole A1–A3 | `read_egms_csv`, `check_los_vector`, `check_east_sign` | tolerancje A1/A2 |
| 2. Duplikaty między plikami burstów | `find_cross_file_duplicates` | `duplicate_distance_m`, `duplicate_rule` |
| 3. Bufor 100 i 200 m, filtr wysokości | `select_buffer` | `buffer_radii_m`, `height_filter_m`, `min_points` |
| 4. Szereg EGMS bufora (średnia/mediana na datę) | `buffer_series` | `buffer_statistic` |
| 5. GNSS → LOS: `U · los_up` (średnie `los_up` z bufora) | `run_e1_track` | — (uzasadnienie: F7, 2.3 p. 3) |
| 6. GNSS w datach EGMS: agregacja dób w oknie ±k dni | `gnss_at_dates` | `gnss_window_half_days`, `gnss_aggregation` |
| 7. Pokrycie A6 w obu definicjach | `coverage` | `min_overlap_fraction`, definicja D-B |
| 8. Wspólne okno, wspólna data odniesienia, wyzerowanie | `run_e1_track` | `window`, `reference` |
| 9. Prędkość tym samym modelem dla obu szeregów | `fit_velocity` | `velocity_model` |
| 10. Δv = v_GNSS,LOS − v_EGMS; std, RMS, korelacja różnic | `compare_series` | progi T1 |

### 2.3 Wydanie i okno (najważniejsze ograniczenie)

| Wydanie | Dostęp | Wspólne okno z PTO1 | A6 (a) |
|---|---|---|---|
| 2015–2021 | archiwum | ok. 01.2016–04.2021 | 88% |
| 2018–2022 | archiwum | 06.2018–04.2021 | 69% |
| 2019–2023 | API | 01.2019–04.2021 | 46% |

Bez dłuższego szeregu GNSS (NGL lub INGV RING, do sprawdzenia) czysty test E1b spełniający A6 daje tylko
wydanie 2015–2021. Rekomendacja bez zmian względem `Plan_v1_wdrozenie.md`, D-A: sprawdzić NGL; jeśli PTO1 tam
nie ma, wniosek do Helpdesku o 2015–2021 i 2018–2022.

## 3. E2 — EGMS kontra niwelacja w zachodniej NRW (rekomendowany)

**Hipoteza H2:** dla reperów niwelacji państwowej w zachodniej NRW, które mają komórkę EGMS L3 (pion), różnice
prędkości EGMS − niwelacja mają bias ≤ 1,5 mm/rok **[propozycja]**, a łączne σ różnic przemieszczeń ≤ 3 mm
**[propozycja]**. Even i in. 2024 podają 0,93 mm/rok i 1,76 mm; nasz wynik ma być tego samego rzędu, nie identyczny
(inny zasięg obszaru, inna siatka dopasowania).

### 3.1 Dane

| Element | Wybór | Status |
|---|---|---|
| Niwelacja | „Höhenfestpunkte – Punktliste mit Zeitfolge” (`hfp_plzf.csv`, ok. 7,7 MB) + „Punktliste” (współrzędne) | format zweryfikowany (F5, sekcja 5); **zakres epok i licencja do potwierdzenia przy pobraniu** |
| Układ reperów | EPSG:25832 (do potwierdzenia w `Datenformatbeschreibung.pdf`) | przeliczenie do EPSG:3035 bez zmiany datum (oba ETRS89) |
| EGMS | L3 pion | wydanie: do odtworzenia Even — 2015–2021 (archiwum); do rozszerzenia — 2019–2023 lub 2020–2024 (API), jeśli są epoki niwelacji w tym okresie |
| Obszar | zasięg z ryc. 14–15 artykułu Even (wyłącznie z PDF; tekst nie podaje granic) | do odczytania z PDF; **bez Epe** (znana porażka, opisana osobno) |

### 3.2 Kroki

| Krok | Funkcja w prototypie | Parametr |
|---|---|---|
| 1. Wczytaj niwelację (format długi), przelicz do EPSG:3035 | `read_levelling_long`, `transform_xy` | `levelling_crs_epsg` |
| 2. Komórka L3 zawierająca reper | `cell_containing` | rozmiar komórki 100 m |
| 3. Odniesienie: reper lub grupa stabilna | `run_e2` | `reference` (decyzja przed obliczeniami) |
| 4. `d_rel(t) = d_P(t) − d_ref(t)`; odczyt w datach epok (interpolacja, bez ekstrapolacji) | `read_at_epochs` | `epoch_reading` |
| 5. Δh_EGMS i Δh_niw dla par epok; różnice; kryteria T2 | `run_e2`, `summarize_e2` | `epoch_pairs`, progi |
| 6. Statystyki jak w Even: mediana i MAD × 1,4826 różnic prędkości; łączne σ | `robust_stats`, `pooled_sigma` | — |

Różnice względem Even (zapisane z góry, żeby nie dopasowywać po wyniku):
- dopasowanie: komórka L3 zawierająca reper (100 m) zamiast siatki 50 m,
- bez wygładzania RLOESS w wariancie głównym; z RLOESS jako wariant porównawczy (jeśli autor zgodzi się na zależność od `statsmodels`),
- jawne odniesienie do reperu lub grupy stabilnej (Even porównują prędkości bez wspólnego reperu).

### 3.3 Poziom 2 — „prognoza → potwierdzenie” (tylko jeśli są późniejsze epoki)

Jeśli plik NRW ma epoki po 2021 r.: prędkość z wydania kończącego się przed epoką t1, prognoza `v · (t2 − t1)`,
porównanie z niwelacją. Jeśli ich nie ma, poziom 2 odpada i zostaje Hengelo (E2′) jako jedyny test prognozy.

### 3.4 E2′ — Hengelo jako rozszerzenie

Bez zmian względem `docs/evidence/F3_przypadek_repery_Hengelo.md`. Ten sam kod (`run_e2`). W raporcie wprost:
„brak wcześniejszej walidacji EGMS w tym miejscu; to nasz własny wynik”.

## 4. Kryteria i reguła decyzji

E1 korzysta z progów T1 (`Plan_v1_kryteria_akceptacji.md`, sekcja B). E2 na NRW potrzebuje nowych progów
(sekcja 3 wyżej, **[propozycja]**); E2′ korzysta z progów T2 (sekcja C).

| E1 | E2 (NRW) | Wniosek |
|---|---|---|
| zaliczony | zaliczony | EGMS potwierdzony na dwóch otwartych rodzajach pomiaru naziemnego; nasz pipeline odtwarza opublikowane walidacje |
| zaliczony | niezaliczony | sprawdzić odniesienie i stabilność reperów (przykład z Polski: stałe przesunięcie −7 mm/rok od „stałych” punktów) zanim cokolwiek powiemy o EGMS |
| niezaliczony | dowolny | najpierw szukać błędu po naszej stronie (znak, układ, okno); oficjalne walidacje dają ok. 1 mm/rok |

## 5. Prosty eksperyment w Pythonie — co działa już dziś

```bash
pip install numpy pandas pyproj            # przetestowano: numpy 2.5.3, pandas 3.0.5, pyproj 3.8.0, Python 3.13
python prototypes/egms_simple_check.py --selftest
python prototypes/egms_simple_check.py --describe-gnss data/02_Raw_Ground/1_gnss_pangaea/PTO1.txt
python prototypes/egms_simple_check.py --run e1    # zatrzyma się: CONFIG["status"] != "APPROVED"
```

Wynik `--selftest` (2026-10-10, dane syntetyczne o znanej odpowiedzi, ziarno 20261010):

| Test | Prawda | Wynik |
|---|---|---|
| E1: prędkość EGMS w LOS (pion −5 mm/rok, θ ≈ 41°) | −3,77 mm/rok (−5 · cos θ) | −3,78 mm/rok |
| E1: Δv przy GNSS o tej samej prędkości (szum dobowy 8 mm) | 0 | +0,16 mm/rok; std różnic 1,8 mm |
| E1: kontrola negatywna (GNSS wolniejszy o 3 mm/rok w pionie) | \|Δv\| > 1,5 | 2,42 mm/rok, próg niezaliczony |
| A6 przy GNSS do 2021-04-13 i wydaniu 2018–2022 | ok. 69% | 69,3% |
| E2: niecka −14 mm/rok, niwelacja z szumem 1 mm | mediana \|różnicy\| ≈ 1 mm, znak zgodny | 1,3 mm; zgodność znaku 100%; nachylenie 0,94 |
| A3, duplikaty, brak ekstrapolacji, RD → 3035 → RD, odjęcie odniesienia od siebie | — | przechodzą |

Test syntetyczny sprawdza, że kod odtwarza znaną odpowiedź i wykrywa błąd. Nie mówi nic o EGMS;
to robią dopiero E1b i E2 na prawdziwych danych.

## 6. Decyzje autora przed pierwszym przebiegiem

| # | Decyzja | Rekomendacja |
|---|---|---|
| D-E2 | E2 na NRW (odtworzenie Even 2024) zamiast Hengelo jako przypadku głównego | tak; Hengelo jako rozszerzenie |
| D-A | wydanie i okno E1 | NGL → jeśli brak, 2015–2021 (test) + 2018–2022 (porównanie z artykułem) |
| D-B | definicja A6 | oba warunki (a) i (b) |
| D-E2-ref | odniesienie w NRW | do decyzji po obejrzeniu mapy reperów, **przed** policzeniem różnic |
| D-E2-th | progi E2 na NRW (bias ≤ 1,5 mm/rok, σ ≤ 3 mm) | do zatwierdzenia |
| D2–D4 | statystyka bufora, agregacja GNSS, model prędkości, odczyt w epoce | bez zmian (`Plan_v1_otwarte_pytania.md`, sekcja D) |

## 7. Dane do pobrania (dopisek do `Plan_v1_dane_do_pobrania.md`)

| # | Co | Skąd | Uwagi |
|---|---|---|---|
| 10 | `hfp_plzf.csv`, `hfp_pl.csv`, `Datenformatbeschreibung.pdf`, `Nutzerinformation.pdf` | https://www.opengeodata.nrw.de/produkte/geobasis/rb/fd/ | zapisać datę pobrania i licencję ze strony |
| 11 | EGMS L3 pion dla zachodniej NRW, 2015–2021 | CLMS Helpdesk (archiwum) | dołączyć do wniosku z D-D |
| 12 | EGMS L3 pion dla zachodniej NRW, 2019–2023 / 2020–2024 | API EGMS | jeśli niwelacja ma epoki w tym okresie |
| 13 | PDF Even i in. 2024 (ryc. 14–15: zasięg obszaru) | jest na Dysku (`/drive/EGMS`) | odczytać granice obszaru |
