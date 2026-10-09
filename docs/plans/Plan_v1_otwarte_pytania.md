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
