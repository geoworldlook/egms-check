# Plan v1 — wdrożenie (EGMS Check)

Status: PROPOSED, 2026-10-09. Część planu `Plan_v1_walidacja_EGMS.md`.
Podstawa: komplet dokumentów z paczki (plany, F1–F6, tabele referencyjne), plik `PTO1.txt`, kod AgriWatch
(`1_geoworldlook-agriscreen`, gałąź `main`, stan z 2026-10-09) oraz uzupełniający przegląd źródeł w sieci (sekcja 9).

Ten dokument nie zastępuje `Prompty_Claude_Code.md`, tylko go koryguje: mówi, co trzeba rozstrzygnąć i
uruchomić **przed** sesjami 1–10, i co w nich zmienić po tym, czego dowiedziałem się z danych i ze źródeł.

---

## 1. Najważniejsze w pięciu punktach

1. **`PTO1.txt` kończy się 13.04.2021, a nie we wrześniu 2022**, jak zakładają F2, F5, CLAUDE.md i konfiguracja.
   Szereg zaczyna się 18.06.2008, ma 4248 dób, dwie przerwy ≥ 30 dni i nie widać w nim wyraźnego skoku (sekcja 2.1).
2. **Wydanie EGMS 2018–2022 zostało przeniesione do archiwum.** Według CLMS EGMS Explorer udostępnia teraz tylko
   wydania 2019–2023 i 2020–2024; 2015–2021 i 2018–2022 są dostępne na wniosek przez CLMS Helpdesk
   (sekcja 2.2; potwierdzi to dopiero `GET /releases` z tokenem).
3. Skutek punktów 1 i 2: **przy wydaniu 2018–2022 wspólne okno z GNSS to 69% okresu wydania, czyli poniżej progu
   85% (kontrola A6).** Próg spełnia tylko wydanie 2015–2021 (88%). Wydania dostępne w API dają 46% i 26%.
   To blokuje T1 w obecnej postaci i wymaga Twojej decyzji (D-A, sekcja 4).
4. **Test prognozy w przypadku 2 też potrzebuje wydania 2018–2022** (dane uczące przed ostatnią epoką).
   Wniosek do Helpdesku warto złożyć od razu, bo jego czas obsługi jest nieznany i leży na ścieżce krytycznej.
5. **Artykuł Fernández i in. 2018 (PDF) używa odwrotnej konwencji znaku LOS** (dodatni = oddalanie od satelity)
   i pokazuje, że pomiar naziemny też bywa obciążony (niestabilne znaki). Wzoru dekompozycji nie wolno przepisać
   bez zmiany znaku; repery 300 i 301 w Hengelo warto czytać w tym świetle (sekcja 2.6).

---

## 2. Ustalenia z danych i źródeł

### 2.1 Plik GNSS `PTO1.txt` (pytanie A1, rozstrzygnięte)

Sprawdzone 2026-10-09 skryptem roboczym (bez zmian w pliku). SHA-256 w `data/00_Metadata/MANIFEST.csv`.

| Cecha | Wartość |
|---|---|
| Nagłówek | `* time U Su site long lati` |
| Kolumny | czas (rok dziesiętny), Up [mm], sigma Up [mm], `PTO1.up_GPS`, długość, szerokość |
| Współrzędne stacji | 12,3341° E, 44,9515° N (stałe w całym pliku; 4 miejsca po przecinku ≈ 8–11 m) |
| Zakres | 2008-06-18 – 2021-04-13 |
| Liczba dób | 4248, czas rośnie monotonicznie |
| Przerwy ≥ 30 dni | 2015-09-16 → 2015-10-16 (30 d); 2018-12-16 → 2019-02-06 (52 d) |
| Sigma Up | mediana 8,2 mm (zakres 4,4–22,8 mm) |
| Skoki | przegląd median 60-dniowych przed i po każdej dobie: największe zmiany 4,5–6,4 mm, wszystkie w kierunku trendu i porównywalne z szumem; **wyraźnego skoku nie widać**. To przegląd wstępny, nie test; dziennik stacji (B2) nadal potrzebny |
| Prędkość pionowa (orientacyjnie, MNK bez modelu szumu) | cały szereg −4,3 mm/rok; 06.2018–04.2021 −4,5 mm/rok; amplituda roczna ok. 0,3–0,5 mm |

Prędkość orientacyjna −4,5 mm/rok jest bliska −5,2 ± 1,9 mm/rok z artykułu (kampanie 2018–2022). To liczba do
orientacji, nie wynik testu; progi nie były jeszcze zatwierdzone, więc nie porównuję jej z niczym formalnie.

Co trzeba poprawić w dokumentach: F2 (wiersz „Zakres"), F5 (sekcja 2), CLAUDE.md (lista niezweryfikowanych),
`case_1_gnss_pto1.example.yaml` (`window_end: ... wg opisu 2022-09`). Opis zbioru (01.2010–09.2022) dotyczy całego
zbioru, a nie stacji PTO1.

### 2.2 Wydania EGMS (pytania A2 i C4, rozstrzygnięte częściowo)

| Ustalenie | Źródło | Status |
|---|---|---|
| Wydanie 2020–2024 jest opublikowane (prezentowane na webinarze w XII 2025) | aktualności CLMS (sekcja 9) | zweryfikowane w źródle wtórnym; strona CLMS niedostępna z mojego środowiska |
| EGMS Explorer udostępnia bezpośrednio tylko 2019–2023 i 2020–2024 | jw. | jw. |
| 2015–2021 i 2018–2022 są w archiwum, dostępne na wniosek przez CLMS Helpdesk/Service Desk; wniosek ma zawierać poziom produktu (Basic, Calibrated, Ortho) i listę kafli lub burstów | aktualności i strona produktu CLMS | jw. |
| Czy API (`/releases`) zwraca wydania archiwalne | — | **niezweryfikowane**; sprawdzi sesja 2 |
| Oficjalny notatnik API: zapis `"L2B"`, `"L3"`, `"2019-2023"`, `"ORTHO-UP"`; token ważny 1 h; brak zapisanych wyników komórek | `copernicus-land/egms-api`, `EGMS-API.ipynb` | zweryfikowane w kodzie (nieuruchamiane) |
| Pion L3 2018–2022 był udostępniony także na platformie ESA GEP | ESA EO4Society, 06.2024 | tylko informacja o udostępnieniu; formatu i licencji nie sprawdzałem |

### 2.3 Wspólne okno GNSS–EGMS dla przypadku 1

Okno wydania 2018–2022 według tabeli 1 artykułu (ścieżka 117); dla pozostałych wydań przyjąłem pełne lata
kalendarzowe (dokładne daty pierwszej i ostatniej akwizycji pokażą pliki).

| Wydanie | Wspólne okno / okres wydania | Doby GNSS we wspólnym oknie | A6 (≥ 85%) |
|---|---|---|---|
| 2015–2021 | 5,28 / 6,00 roku = **88%** | 93% | spełnia (na granicy; zależy od daty pierwszej akwizycji) |
| 2018–2022 | 2,84 / 4,09 roku = **69%** | 90% | **nie spełnia** |
| 2019–2023 | 2,28 / 5,00 roku = 46% | 91% | nie spełnia |
| 2020–2024 | 1,28 / 5,00 roku = 26% | 97% | nie spełnia |

Kontrola A6 jest dziś zdefiniowana niejednoznacznie: „pokrycie czasowe EGMS–dane naziemne ≥ 85%" może znaczyć
(a) długość wspólnego okna względem okresu wydania albo (b) odsetek dat EGMS we wspólnym oknie, dla których jest
GNSS. Przy (b) każde wydanie przechodzi, ale wtedy test na 2020–2024 opierałby się na 15 miesiącach. Definicję
trzeba zapisać **przed** pierwszym przebiegiem (decyzja D-B).

### 2.4 Literatura uzupełniająca, istotna dla planu

- **Pintori i Serpelloni 2024** (Earth and Space Science, doi:10.1029/2023EA003326; artykuł powiązany ze zbiorem
  PANGAEA): stacje GNSS w dorzeczu Padu wypiętrzyły się o **do 7 mm między 01.2021 a 08.2022** wskutek suszy
  (ubytek wody ok. 70 Gt). Wniosek dla nas: koniec wydania 2018–2022 (do 07.2022) zawiera nieliniowy sygnał
  hydrologiczny. Trend liniowy liczony do 07.2022 jest nim obciążony; przy porównaniu w oknie kończącym się
  04.2021 problemu prawie nie ma. Trzeba to opisać w F2 jako ryzyko i jako argument przy wyborze okna.
  (Znane z abstraktu i opisu zbioru; pełnego tekstu nie czytałem.)
- **Konwencja znaku LOS w EGMS** nadal niepotwierdzona: nie znalazłem jej w dostępnych fragmentach Product User
  Manual. Zostają kontrole A1–A4 na danych; PUM (EGMS-D4-PUM-SC1-2.0-007) trzeba przeczytać w sesji 4, jeśli
  któraś kontrola nie przejdzie.
- **Nevada Geodetic Laboratory**: nie udało mi się potwierdzić, że ma stację PTO1 (strona niedostępna z mojego
  środowiska, wyszukiwarka nic nie zwraca). Jeśli ma, dałaby szereg E, N, U po 04.2021, co rozwiązuje punkt 2.3
  i pozwala na pełny rzut 3D. Sprawdzenie zajmuje 5 minut w przeglądarce (B5).

### 2.5 AgriWatch: co przenosimy

Przeczytałem `step_05_colab_run.py` (1221 linii) i `build_colab_master.py`.

| Element | Decyzja | Uwagi |
|---|---|---|
| `REGISTRY_SCHEMA` | przenieść bez zmian tabele `gwl_sites`, `gwl_observations`, `gwl_validation_metrics`, `gwl_runs` | `gwl_anomalies`, `gwl_status`, `gwl_calibrations` pominąć (ARCHITEKTURA, sekcja 5) |
| `_utc_now`, `_git_commit`, `_canon`, `registry_read`, `registry_upsert`, `run_history`, `registry_summary` | bez zmian | w `_git` zamienić `except Exception` na `except (OSError, subprocess.SubprocessError)` (CLAUDE.md, zasada 3) |
| `run_task` | bez zmian w kontrakcie (`registry`, `skipped`, `pipeline_version`) | `except Exception` w `run_task` zostaje: zapisuje błąd w `gwl_runs`, na co CLAUDE.md wprost pozwala |
| `setup_runtime` | uprościć: bez GEE, bez GPU i SR; lista pakietów z sekcji „Środowisko" w `Plan_v1_potok.md`; dodać `TOKEN_PATH` | ścieżka tokenu z konfiguracji, nie z sygnatury |
| `monitor_config` → `check_config(rt, case_id)` | nowe: wczytuje `CHECK_CONFIG`, zamienia ścieżki na bezwzględne i **zatrzymuje się na każdym kluczu z wartością `TODO`** | spełnia zasadę 4 (brak wartości domyślnych) |
| `run_monitoring` → `run_check` | nowe: kolejność zadań z ARCHITEKTURA, sekcja 3 | — |
| **Bramka po `task_checks`** | **nowe; w AgriWatch tego nie ma**: błąd jednego zadania nie zatrzymuje następnych | ARCHITEKTURA wymaga, żeby błąd kontroli zatrzymał dalsze zadania tego przypadku. Propozycja: `run_task(..., requires=["checks:case_1"])` sprawdza w `gwl_runs` status zadania-warunku z bieżącej serii i przy braku `ok` zapisuje `skipped` z powodem |
| `_selftest` | nowy, na wzór AgriWatch: katalog tymczasowy, dane syntetyczne EGMS (trend + sinusoida + szum, znany wektor LOS), prawdziwy `PTO1.txt` i tabele referencyjne | testy „z sensem naukowym" z `Plan_v1_potok.md` |
| `build_colab_master.py` | struktura `CELLS` bez zmian; komórka 1 (Dysk, klon, `pull --ff-only`, autostash) przeniesiona; GPU niepotrzebne | notatnik `notebooks/EGMS_Check.ipynb` |

### 2.6 Fernández i in. 2018 — lektura PDF (2026-10-09)

Szczegóły w F1 (pozycja 4) i F4 (sekcje 4 i 8). Co zmienia w planie:

| Ustalenie | Skutek |
|---|---|
| u_LOS dodatnie przy oddalaniu od satelity; wzór 1 w druku ma strony zamienione względem modelu wprost | F4, sekcja 4 poprawiona; w kodzie żadnych wzorów przepisanych z artykułu bez kontroli A1–A4 |
| Rzut GNSS → LOS dał lepszą zgodność (ok. 0,7 cm/rok) niż dekompozycja orbit na pion i E-W | potwierdza regułę „kierunek zawsze GNSS → LOS” i L3 zamiast własnej dekompozycji w Hengelo |
| Porównanie punktów InSAR w promieniu 100 m od stacji | ten sam promień co w metodyce EEA; spójne z buforem 100 m w przypadku 1 |
| Niestabilność znaków pomiarowych (stacje 23 i 28) wykryta dopiero przez porównanie z InSAR i wizję w terenie | w przypadku 2 rozbieżność na pojedynczym reperze może wynikać z reperu, nie z EGMS; dlatego decyzja o reperach 300 i 301 i o opisie reperów (C3) przed obliczeniami |
| Niepewność prędkości GNSS z błądzeniem losowym 1,5 / 2,5 mm/√rok | dodatkowy kandydat do decyzji o niepewności prędkości GNSS (F4, sekcja 8) |
| Odrzucanie dni GNSS: niepewność > 20 mm lub > 10 mm od trendu | możliwa reguła dla PTO1 (sigma do 22,8 mm); tylko jako decyzja autora przed obliczeniami, nie domyślnie |

---

## 3. Niespójności w dokumentach (do poprawy w sesji 0)

| # | Miejsce | Problem | Poprawka |
|---|---|---|---|
| N1 | F2, F5, CLAUDE.md, `case_1_*.yaml` | zakres GNSS do 09.2022 | 2008-06-18 – 2021-04-13 (sekcja 2.1) |
| N2 | `case_1_*.yaml`, `aggregation` | odsyła do „Plan_v1_otwarte_pytania, E" | powinno być D2 |
| N3 | `fabris2026_nps_agreement.csv`, `note` | odsyła do „B5" (to pytanie o NGL) | brak odpowiedniego pytania; dodać B6 „odsetki po rekalibracji: tekst kontra opis ryc. 6" |
| N4 | `Plan_v1_test_EGMS.md`, T1 | kryterium „bufor 100 m kontra 200 m" jest w tabeli, ale reguła wyniku go nie używa | zdecydować: kryterium wpływa na wynik czy jest tylko raportowane (D-C) |
| N5 | `Plan_v1_kryteria_akceptacji.md`, A6 | definicja pokrycia niejednoznaczna | D-B |
| N6 | ARCHITEKTURA, `task_checks` | „raport kontroli A1–A7", ale A6 wymaga danych naziemnych, a A7 dotyczy wszystkich plików wejściowych | A1–A5 w `task_checks`; A6 w `task_compare_*`; A7 w `task_ingest_*` |
| N7 | `Plan_v1_dane_do_pobrania.md`, poz. 2–3 i 6b | wydanie 2018–2022 przez API | dopisać drogę przez Helpdesk lub ESA GEP (sekcja 2.2) |
| N8 | `case_2_*.yaml`, `acceptance` | tylko 2 progi, a T2 ma 4 kryteria | dopisać próg prognozy i kontroli negatywnej oraz definicję reperu stabilnego (≤ 2 mm) |
| N9 | `Plan_v1_otwarte_pytania.md`, A2 | zakłada, że brak 2018–2022 w API zatrzymuje pracę | zmienione: brak w API → wniosek do Helpdesku, praca idzie dalej (sekcja 5) |

---

## 4. Decyzje, które musisz podjąć (w kolejności blokowania)

Dla każdej podaję rekomendację; decyzja jest Twoja (CLAUDE.md, zasada 2). Zapis z datą do `Plan_v1_otwarte_pytania.md`.

| # | Decyzja | Warianty | Rekomendacja | Blokuje |
|---|---|---|---|---|
| **D-A** | Wydanie EGMS i okno dla T1 | (1) 2015–2021, okno ok. 01.2016–04.2021; (2) 2018–2022, okno 06.2018–04.2021 i jawne odstępstwo od A6; (3) dłuższy szereg GNSS (NGL lub INGV), jeśli istnieje, z wydaniem 2018–2022; (4) 2019–2023 z API, okno 01.2019–04.2021 | **(3), jeśli NGL ma PTO1** (5 minut sprawdzenia); w przeciwnym razie **(1) jako test T1 i (2) jako tabela „artykuł kontra my"**: oba wydania z jednego wniosku do Helpdesku. Wariant (4) tylko awaryjnie: 46% i dodatkowo wpływ suszy | sesje 2–5 |
| **D-B** | Definicja A6 | (a) wspólne okno / okres wydania; (b) doby z GNSS / wspólne okno; (c) oba warunki | **(c)**: (a) ≥ 85% i (b) ≥ 85%; to wierne White Paper i odporne na krótkie okna | sesja 5 |
| **D-C** | Rola kryterium „100 m kontra 200 m" | wpływa na wynik T1 / tylko raport | tylko raport, bo reguła T1 już go nie używa; po prostu zostawić tabelę zgodną z regułą | sesja 5 |
| **D-D** | Złożenie wniosku do CLMS Helpdesk | teraz / po sesji 2 | **teraz**: L2b 2018–2022 i 2015–2021 dla burstów nad PTO1 na ścieżkach 117, 44 i 95 oraz L3 pion 2018–2022 dla kafla z Hengelo. Numery burstów pokaże dopiero `search`; jeśli formularz ich wymaga, podać obszar (punkt PTO1 i prostokąt Hengelo) | ścieżka krytyczna T1 i testu prognozy |
| D-E | Dostęp sieciowy dla sesji API | Colab / lokalnie / to środowisko w chmurze | w tym środowisku domeny `egms.land.copernicus.eu`, `download.pangaea.de`, `geodesy.unr.edu`, `www.nlog.nl` są zablokowane (proxy 403). Albo sesje 2, 3 i 9 w Colab lub lokalnie, albo dopisanie tych domen w ustawieniach sieci środowiska | sesje 2, 3, 9 |
| D-F | Pozostałe z sekcji D w `Plan_v1_otwarte_pytania.md` | model prędkości, agregacja GNSS, statystyka w buforze, odczyt w epoce, odniesienie, repery 300 i 301, progi | bez zmian względem planu; terminy w sekcji 5 | sesje 4, 5, 9 |

Uwaga do D-A, wariant (1): wydanie 2015–2021 było przetwarzane starszą wersją łańcucha EGMS. Wynik T1 na nim mówi
o tamtym wydaniu, nie o wydaniu, z którego korzysta dziś użytkownik. Trzeba to napisać we wpisie.

---

## 5. Kolejność wdrożenia

Sesje z `Prompty_Claude_Code.md` zostają; zmienia się ich zawartość i warunki przejścia. Etapy oznaczone ✱ robisz sam.

```text
Etap 0 ─▶ ✱ wnioski i dostęp ─────────────────────────────┐ (równolegle, czas obsługi Helpdesku nieznany)
   │                                                      │
Sesja 0 ─▶ Sesja 1 ─▶ Sesja 2 ─▶ Sesja 3 ─▶ Sesja 4 ─▶ ✱ zamrożenie progów ─▶ Sesja 5 ─▶ Sesja 6 ─▶ Sesja 7  ══▶ M2: wpis (przypadek 1)
                         │                                                            
                         └─▶ (2019–2023/2020–2024 dostępne od razu) ─▶ Sesja 8 ─▶ Sesja 9a (nałożenie) ─▶ Sesja 9b (prognoza, gdy jest 2018–2022) ─▶ Sesja 10
```

### Etap 0 — wykonane w tej sesji (2026-10-09)

- Paczka zaimportowana do repozytorium (z zachowaniem `.gitignore`: pełne teksty publikacji zostają lokalnie).
- `PTO1.txt` w `data/02_Raw_Ground/1_gnss_pangaea/`, wpis w `data/00_Metadata/MANIFEST.csv` z SHA-256.
- `python step_00_reference_check.py` przechodzi.
- Pytanie A1 rozstrzygnięte (sekcja 2.1); A2 i C4 rozstrzygnięte częściowo (sekcja 2.2).

### ✱ Etap 0b — Ty, równolegle

1. Sprawdź w przeglądarce, czy NGL ma stację PTO1 (`https://geodesy.unr.edu`, wyszukiwarka stacji) i do kiedy sięga szereg.
2. Podejmij D-A, D-B, D-C (pół godziny; od tego zależy treść wniosku).
3. Złóż wniosek do CLMS Helpdesk (D-D).
4. Token CLMS API (Instrukcja startowa, kroki 3–4) i decyzja D-E.
5. Pobierz PDF raportu ze Strootbeekpark (potrzebny w sesji 8).

### Sesja 0 — orientacja (zmieniona)

Jak w promptach, plus: wprowadzić poprawki N1–N9 z sekcji 3 (tylko dokumenty, bez kodu) i dopisać decyzje D-A…D-D
z datą do `Plan_v1_otwarte_pytania.md`. **Gotowe, gdy:** dokumenty są spójne z faktycznym zakresem `PTO1.txt`.

### Sesja 1 — szkielet z AgriWatch (uzupełniona)

Jak w promptach, plus elementy nowe z sekcji 2.5: `check_config` z zatrzymaniem na `TODO`, bramka `requires` w
`run_task`, zawężony wyjątek w `_git`, `update_manifest` (SHA-256 i wiersz manifestu) przeniesiony do `step_01`.
`--selftest` sprawdza też, że: (i) zadanie zależne od nieudanego `checks` kończy się `skipped` z powodem,
(ii) brak klucza w konfiguracji daje wyjątek, a nie wartość domyślną.
**Gotowe, gdy:** `--selftest` przechodzi, notatnik się generuje.

### Sesja 2 — API EGMS (zmieniona)

Jak w promptach, ale: brak wydania 2018–2022 w `GET /releases` **nie zatrzymuje projektu**, tylko jest zapisywany
w `Plan_v1_otwarte_pytania.md` (A2) i kieruje do wniosku z D-D. Dodatkowo: sprawdzić, czy `search` z `releases`
ustawionym na wydanie archiwalne zwraca `hits` (czasem archiwum jest widoczne w wyszukiwaniu, ale bez pobierania).
Wymaga D-E. **Gotowe, gdy:** znamy listę wydań, zapis filtrów i wiemy, które wydania są pobieralne przez API.

### Sesja 3 — dane przypadku 1 (zmieniona)

Punkt 1 promptu (`read_pangaea_gnss`) jest w dużej części wykonany (sekcja 2.1): funkcja ma odtworzyć te liczby
jako test. Punkt 2 (`search_egms` dla ścieżek 117, 44, 95) wykonać na wydaniu z D-A; jeśli to wydanie archiwalne,
to `search` na wydaniu 2019–2023 i tak warto zrobić, bo poda numery burstów do wniosku. Pliki z Helpdesku trafiają
do `data/01_Raw_EGMS/<wydanie>/L2b/` z wpisem w manifeście (adres: identyfikator zgłoszenia, nie URL z tokenem).
**Gotowe, gdy:** pliki trzech ścieżek wydania z D-A są w manifeście.

### Sesja 4 — kontrole i wycinki (bez zmian merytorycznych)

Kontrole A1–A5 (zgodnie z N6). Porównanie liczby punktów z artykułem (753 / 531 / 544) ma sens tylko na wydaniu
2018–2022; na innym wydaniu wypisać liczby bez oceny. Decyzje: minimalna liczba punktów, filtr wysokości,
statystyka w buforze.

### ✱ Zamrożenie (przed sesją 5)

Wypełnić protokół w `Plan_v1_test_EGMS.md`: data, progi T1 i T2, definicja A6 (D-B), wydanie i okno (D-A),
commit. Bez tego sesja 5 się nie zaczyna (CLAUDE.md, zasada 9).

### Sesja 5 — porównanie z GNSS (zmieniona)

Jak w promptach, plus: okno porównania z D-A; A6 według D-B; jeśli okno kończy się po 01.2021, wynik dodatkowo
w oknie kończącym się 12.2020 jako test wrażliwości na suszę 2021–2022 (raportowany, nie zmienia oceny). Niepewność
prędkości GNSS: decyzja przed obliczeniami (F4, sekcja 8; MIDAS albo model szumu potęgowego).

### Sesje 6–7 — wykresy, notatnik, wpis (bez zmian)

Do wpisu dochodzi akapit o wyborze wydania i okna (D-A) oraz o tym, że szereg GNSS kończy się w 04.2021.
**Kamień milowy M2:** szkic wpisu z przypadkiem 1.

### Sesja 8 — tabela reperów (bez zmian)

Niezależna od wydań EGMS; może iść równolegle z sesjami 5–7, jeśli PDF jest na miejscu.

### Sesja 9 — niwelacja (podzielona)

- **9a, nałożenie i T2 poziom 1:** wydanie 2020–2024 (obejmuje wszystkie epoki 12.2020–01.2024 z zapasem; dostępne w API).
- **9b, prognoza (T2 poziom 2):** wydanie 2018–2022 z Helpdesku albo pion L3 z ESA GEP. Jeśli żadne nie przyjdzie
  w rozsądnym czasie: wariant zastępczy — szereg z wydania 2019–2023 przycięty na epoce 12.2022 (albo 06.2022)
  i prognoza na kolejne okno. **Zastrzeżenie:** przetwarzanie wydania 2019–2023 korzystało z danych do 12.2023,
  więc dane uczące nie są w pełni niezależne od okna sprawdzającego; trzeba to napisać wprost (F4, sekcja 10).
  Wybór wariantu przed obliczeniami.

### Sesja 10 — domknięcie (bez zmian)

---

## 6. Ścieżka krytyczna i kamienie milowe

| Kamień | Warunek | Zależy od |
|---|---|---|
| M0 | dokumenty spójne, decyzje D-A…D-D zapisane | Ty (etap 0b), sesja 0 |
| M1 | szkielet, `--selftest`, notatnik pusty | sesja 1 (nie zależy od danych EGMS; można zacząć od razu) |
| M2 | T1: tabela kryteriów, wykres główny, szkic wpisu | token, D-E, **pliki wydania z D-A** (Helpdesk, jeśli archiwalne) |
| M3 | T2 poziom 1 | PDF, sesja 8, wydanie 2020–2024 |
| M4 | T2 poziom 2 (prognoza) | **wydanie 2018–2022** albo wariant zastępczy |
| M5 | domknięcie, świeży klon odtwarza wykresy bez tokenu | M2–M4 |

Najdłuższy nieznany czas to obsługa wniosku w Helpdesku. Dlatego: wniosek teraz, sesja 1 równolegle,
a przypadek 2 (poziom 1) można zrobić przed T1, jeśli Helpdesk się przeciąga. To zmienia kolejność „najpierw 1,
potem 2" z CLAUDE.md, więc wymaga Twojej zgody.

---

## 7. Ryzyka

| Ryzyko | Skutek | Co robimy |
|---|---|---|
| Helpdesk nie udostępni 2018–2022 / 2015–2021 albo zwleka | T1 tylko w wariancie (4); brak prognozy w T2 | wariant (4) z jawnym odstępstwem od A6; prognoza w wariancie zastępczym 9b; ESA GEP dla L3 |
| Format lub kolumny plików archiwalnych inne niż w F5 | błędy wczytania | kontrola kolumn w `read_egms_l2` z komunikatem; bez cichych mapowań |
| Susza 2021–2022 (wypiętrzenie do 7 mm) | obciążenie trendu, gdy okno sięga 2022 | okno do 04.2021 lub test wrażliwości (sesja 5) |
| PTO1 w modelu GNSS EGMS (B3) | T1 nie jest w pełni niezależny | napisać wprost; opcjonalny test na L2a (F2, rozszerzenia) |
| Kontrole A1–A4 nie przechodzą | stop przypadku | PUM, nie zgadywać (sesja 4) |
| Mała gęstość punktów przy reperze 000A2890 | brak odniesienia | grupa stabilna, decyzja przed obliczeniami |
| Brak sieci do serwerów danych w tym środowisku | sesje API niewykonalne tutaj | D-E |
| Licencja raportu NLOG | ograniczenia publikacji wycinka | sprawdzić przed wpisem z przypadkiem 2 (S3) |
| Niestabilny reper (osiadanie własne znaku lub budowli) | rozbieżność przypisana EGMS, choć źródłem jest reper | opis reperów (C3) i lista wyłączeń przed obliczeniami; rozbieżności raportować z możliwą przyczyną (Fernández i in. 2018: stacje 23 i 28) |

---

## 8. Co zostaje niezweryfikowane po tej sesji

- lista wydań z `GET /releases` i to, czy API obsługuje wydania archiwalne,
- czas i forma obsługi wniosku do Helpdesku,
- konwencja znaku LOS (PUM),
- dokładne daty pierwszej i ostatniej akwizycji wydań 2015–2021, 2019–2023, 2020–2024 przy PTO1 (tabela 2.3 przyjmuje pełne lata),
- obecność PTO1 w NGL i dziennik stacji (B2, B5),
- zawartość pracy Pintori i Serpelloni 2024 poza abstraktem.

---

## 9. Źródła sprawdzone w tej sesji

| Źródło | Co z niego wziąłem | Poziom |
|---|---|---|
| `data/02_Raw_Ground/1_gnss_pangaea/PTO1.txt` | sekcja 2.1 | plik danych, przeliczone |
| `copernicus-land/egms-api`, `EGMS-API.ipynb` (GitHub) | uwierzytelnienie, punkty końcowe, zapis filtrów | kod, nieuruchamiany |
| CLMS, „EGMS annual update brings new data, improvements to EGMS Explorer": https://land.copernicus.eu/en/news/egms-annual-update-brings-new-data-improvements-to-egms-explorer | wydania w Explorerze i archiwum | treść przez wyszukiwarkę; strona niedostępna bezpośrednio |
| CLMS, strona produktu EGMS: https://land.copernicus.eu/en/products/european-ground-motion-service | wniosek o dane archiwalne | jw. |
| CLMS FAQ, okres danych: https://land.copernicus.eu/en/faq/products/european-ground-motion-service/for-what-period-does-the-service-provide-data-and-products | sprzeczne terminy wydania 2020–2024 (IV kw. 2025 kontra IV kw. 2026; nowsze źródła potwierdzają 2025) | jw. |
| ESA EO4Society, 24.06.2024: https://eo4society.esa.int/2024/06/24/new-copernicus-ground-motion-data-available-on-gep/ | L3 pion 2018–2022 na GEP | jw. |
| B2FIND, opis zbioru PANGAEA.958598: https://b2find.eudat.eu/dataset/5475e4be-cd5f-5a1f-a69a-e09adc455deb | zakres zbioru, przetwarzanie | metadane |
| Pintori i Serpelloni 2024, doi:10.1029/2023EA003326 | wypiętrzenie do 7 mm w 01.2021–08.2022 | abstrakt |
| `1_geoworldlook-agriscreen`: `step_05_colab_run.py`, `build_colab_master.py` | sekcja 2.5 | kod |
| Fernández i in. 2018, Sci. Rep. 8:14782, doi:10.1038/s41598-018-33128-0 (PDF, 14 stron) | sekcja 2.6; F1, F4 | pełny tekst |
