# Plan v1 — otwarte pytania i rzeczy niezweryfikowane

Status: lista robocza, 2026-10-09. Część planu `Plan_v1_walidacja_EGMS.md`.

Stan na 2026-10-09. Kolumny: co ustalić, jak sprawdzić, co od tego zależy.

## A. Blokujące — sprawdzić przed pisaniem kodu (łącznie ok. 1–2 godziny)

| # | Przypadek | Pytanie | Jak sprawdzić | Co zależy |
|---|---|---|---|---|
| A1 | 1 | Czy `PTO1.txt` się pobiera i jaki ma zakres dat, przerwy, skoki? | pobrać i obejrzeć | cały przypadek 1 |
|  |  | **Stan 2026-10-09:** plik jest; zakres 2008-06-18 – 2021-04-13 (nie 09.2022), 4248 dób, przerwy 30 d (09–10.2015) i 52 d (12.2018–02.2019), wyraźnego skoku nie widać. Szczegóły: `Plan_v1_wdrozenie.md`, sekcja 2.1 |  |  |
| A2 | 1 | Czy wydanie EGMS 2018–2022 jest dostępne do pobrania? | zapytanie API `GET /releases` | okno ≥ 85%; przy braku: inne źródło GNSS lub jawne odstępstwo |
|  |  | **Stan 2026-10-09:** według CLMS 2018–2022 i 2015–2021 są w archiwum (na wniosek przez Helpdesk); Explorer ma 2019–2023 i 2020–2024. Przy końcu GNSS w 04.2021 wspólne okno z 2018–2022 to 69% (< 85%). Odpowiedź API niesprawdzona. Decyzje D-A, D-B, D-D: `Plan_v1_wdrozenie.md`, sekcje 2.2–2.3 i 4 |  |  |
|  |  | **Stan 2026-10-10 (API, uruchomienie w Colab):** `GET /releases` zwraca tylko `2019-2023` i `2020-2024` (zapis z łącznikiem); `levels`: L2A, L2B, L3; `product_types`: BASIC, CALIBRATED, ORTHO-UP, ORTHO-EAST; 76 ścieżek (zapis trzycyfrowy, np. `095`). Wydania 2015–2021 i 2018–2022 nie są dostępne przez API |  |  |
| A2b | 1 | Bursty nad PTO1 (wyszukanie punktowe L2B) | 2026-10-10: ścieżka 117 — bursty 0263 i 0264 (IW3); 44 — 0265 i 0266 (IW1); 95 — 0807 i 0808 (IW2). **Na każdej ścieżce stacja leży w zakładce dwóch burstów**, więc duplikaty punktów dotyczą bufora wprost (kontrola A5). Rozmiar: 455 MB (2019–2023), 314 MB (2020–2024). Artykuł podaje „sceny” 264–266, 265–267, 806–808: zgodne co do ścieżek, bursty 0263 (117) spoza listy artykułu | sesja 4 |
| A7 | 1 | Definicja pokrycia w kontroli A6 (wspólne okno / okres wydania czy doby z GNSS / wspólne okno) | decyzja autora przed pierwszym przebiegiem | wynik A6 i wybór wydania |
| A3 | 2 | Tabela reperów: współrzędne, wysokości w epokach, dokładne daty | załącznik 5 w PDF; przepisać ok. 50 wierszy | cały przypadek 2 |
| A4 | 2 | Czy istnieje epoka 12.2022? | tekst i załącznik 5 raportu | test prognozy |
| A5 | 2 | Ile punktów EGMS jest przy reperach i przy reperze 000A2890? | zapytanie API `search` dla punktu, potem pobranie i policzenie punktów; szybki podgląd w EGMS Explorer | wykonalność; wybór L3 kontra L2b |
| A6 | oba | Konwencja znaku LOS i kosinusów kierunkowych | kontrole A1–A4 z `Plan_v1_kryteria_akceptacji`; EGMS Product User Manual | poprawność rzutów |

## A2. Publikacja

| # | Pytanie | Kto rozstrzyga |
|---|---|---|
| S1 | Nazwa projektu i repozytorium (robocza: `2_geoworldlook-egmscheck`) | autor |
| S2 | Język wpisu na blog; jeden wpis czy dwa | autor |
| S3 | Formuła atrybucji danych Copernicus i warunki użycia danych z raportu NLOG | sprawdzić przed publikacją |

## B. Ważne — w trakcie przypadku 1

| # | Pytanie | Jak sprawdzić |
|---|---|---|
| B1 | Instytucja i opis przetwarzania zbioru PANGAEA (do slajdu o źródle) | strona zbioru i artykuł powiązany, doi:10.3389/feart.2022.907897 |
| B2 | Dziennik stacji PTO1: wymiany anteny, operator | strona operatora sieci |
| B3 | Czy PTO1 weszła do modelu GNSS użytego w EGMS? | EGMS GNSS Calibration Report, lista stacji |
| B4 | Czy potrzebne jest kryterium wysokości punktów? | rozkład `height` w buforze |
| B5 | Czy są szeregi po 09.2022 (np. w Nevada Geodetic Laboratory)? | http://geodesy.unr.edu, strona stacji |
|  | **Stan 2026-10-10:** NGL ma PTO1 (IGS20, plik `PTO1.tenv3` i `PTO1.EU.tenv3`), ale szereg obejmuje tylko **2010-07-22 – 2019-07-04** (3065 dób; przerwa 2018-12-16 → 2019-02-06). Jest krótszy niż PANGAEA (do 2021-04-13). NGL nie rozwiązuje problemu pokrycia dla PTO1 |  |

## C. Ważne — w trakcie przypadku 2

| # | Pytanie | Jak sprawdzić |
|---|---|---|
| C1 | Przyczyna osiadania i opis obszaru (do slajdu) | plan pomiarów Twenthe-Rijn na NLOG; raporty Nobian |
| C2 | Czy są wcześniejsze i późniejsze rejestry tej sieci (2022, 2024)? | strona NLOG „Meetplannen en Meetregisters" |
| C3 | Położenie reperów względem budynków (grunt czy konstrukcja) | załącznik 1 (mapa), opis reperów |
| C4 | Czy wydanie EGMS 2020–2024 jest już dostępne? | strona produktu CLMS |
| C5 | Status prawny sformułowania „dane urzędowe" | strona NLOG; rola SodM |

## D. Decyzje autora (nie dla Claude Code)

1. Model prędkości: trend liniowy czy trend + sinusoida roczna (EGMS stosuje drugi).
2. Agregacja GNSS: średnia czy mediana miesięczna; okno wokół dat EGMS.
3. Statystyka w buforze: średnia czy mediana.
4. Sposób odczytu EGMS w dacie epoki niwelacji.
5. Odniesienie w Hengelo, gdy przy reperze 000A2890 brak punktów EGMS.
6. Repery 300 i 301: włączać czy nie (decyzja przed obliczeniami).
7. Progi oznaczone **[propozycja]** w `docs/plans/Plan_v1_kryteria_akceptacji.md`.

## E. Czego nie udało mi się sprawdzić i dlaczego

- Serwery danych (PANGAEA, NLOG, EGMS, opengeodata.nrw.de) były niedostępne z mojego środowiska
  do pobierania plików. Treść stron i raportów czytałem przez narzędzie, które zwraca tekst.
- Załącznik 5 raportu z Hengelo nie ma czytelnej warstwy tekstowej w tym, co otrzymałem.
- Etykiety na mapie raportu odczytały się nieuporządkowane; stąd plik `..._UNVERIFIED.csv`.
- Pliku niwelacji NRW widziałem tylko początek (najnowsze daty tam to 2019 r.); to nie rozstrzyga o całości.
- Nie znalazłem opublikowanych notatników walidacyjnych EEA zapowiedzianych na III kw. 2025.

## F. Decyzje zapisane 2026-10-10 (walidacja GNSS, Groningen)

| Decyzja | Wartość | Kto |
|---|---|---|
| Przypadek GNSS | stacje NGL w regionie Groningen zamiast samej PTO1 (PTO1: GNSS kończy się 2021-04, NGL 2019-07) | autor |
| Reguła wyboru stacji | region 5.8–7.3° E, 52.9–53.6° N; dane od ≤ 2019.0 do ≥ 2024.25; niepewność vu ≤ 1,0 mm/rok; ≤ 2 skoki; osiadające vu ≤ −2 mm/rok (wszystkie w regionie); stabilne \|vu\| ≤ 1,0 mm/rok z regionu kontrolnego 4,8–8,3° E, 52,4–54,0° N, 8 najbliższych stacji osiadającej (min. 3, inaczej błąd) | autor (zatwierdzona; stabilne z okolicy dodane 2026-10-10 przed pobraniem EGMS, bo w regionie była tylko 1) |
| Wydanie EGMS | 2019–2023, L2B (dane NGL IGS20 sięgają ok. 2024.65) | autor |
| Metoda | bufor 100 m (200 m jako test wrażliwości), min. 3 punkty, mediana w buforze, GNSS 3D → LOS (pliki NGL „EU”), mediana ±6 dni, trend + sinusoida roczna dla obu szeregów | według Koudogbo i in. 2025; wpisane w notatniku przed obliczeniami |
| Kryteria | K1 ≥ 80% par \|dv\| ≤ 1,5 mm/rok; K2 mediana std różnicy szeregów ≤ 5 mm; K3 stabilne \|v_EGMS\| ≤ 1,5 mm/rok; K4 nachylenie (informacyjnie) | progi 1,5 i 5 z literatury; 80% i K3 — propozycje do potwierdzenia |
