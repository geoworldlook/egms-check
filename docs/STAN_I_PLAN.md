# EGMS Check — stan i plan

Stan na 2026-11-02, wersja 1.0.0. Jedna strona do orientacji; szczegóły w dokumentach z §6.

**Najważniejszy wynik:** na 1216 reperach niwelacji państwowej w zachodniej NRW (pomiar niezależny od GNSS) EGMS
pokazuje tę samą zmianę wysokości co niwelacja: nachylenie 0,96, do −140 mm w 3 lata, w nieckach znak zgodny w 100%.
Zostaje stałe przesunięcie ok. −2 mm/rok, więc wariant główny nie spełnia 3 z 4 kryteriów zapisanych przed
obliczeniami — i tak to raportujemy. W Groningen tempo osiadania z EGMS zgadza się z GNSS w granicach 1,5 mm/rok
dla 91% par (wydanie 2019–2023) i 99% par (2020–2024); werdykt CZĘŚCIOWO, bo kontrola na stacjach stabilnych (K3)
nie przeszła.

**Przepływ danych (jedno zdanie):** dane otwarte (EGMS przez API Copernicus, GNSS z NGL, niwelacja Geobasis NRW)
→ obliczenia na tym komputerze na żądanie (`python -m egmscheck run`; Colab jako zapas) → dane i wyniki na Dysku
Google (`data/egms-check`) → `python -m egmscheck publish` kopiuje wybrane wyniki do `docs/showcase/` → README,
profil GitHub i strona geoworldlook.vercel.app.

**Cel:** użytkownik EGMS wie, na ile może ufać liczbom EGMS w danym obszarze, sprawdzonym wobec niezależnego pomiaru
naziemnego. Nie mówimy „EGMS wykrył”; mówimy „pomiar naziemny potwierdza ruch widoczny w EGMS”.

## 1. Wersja 1.0.0 — produkt

- **Etap A (działa na prawdziwych danych):** EGMS L2b i L3 dla obszaru, wybór stacji GNSS regułą, niwelacja NRW,
  kontrole konwencji danych, porównania z kryteriami K1–K4 i N1–N4, ryciny, rejestr `gwl_*`. Regiony: Groningen
  (gaz) i zachodnia NRW (węgiel brunatny).
- **Polecenia:** `python -m egmscheck run | publish | selftest | settings` (oraz `approvals`, `test`) — pakiet
  `egmscheck` wywołuje te same moduły `step_0N` co notatniki Colab (D-095). Na komputerze: `scripts\gwl.cmd egms-check …`.
- **Publikacja:** `docs/showcase/` (werdykty, tabele niwelacji, 7 rycin, `egmscheck_results.json` ze źródłem każdej
  liczby). Bez zadania w Harmonogramie: EGMS wychodzi raz w roku.
- **CI:** ruff i testy bez sieci wszystkich modułów przy każdej zmianie (GitHub Actions).
- **Etap B (ASF HyP3 + MintPy):** zbudowany i sprawdzony na danych syntetycznych; na prawdziwych danych nieuruchomiony
  (konfiguracja zatwierdzona 2026-10-12: Groningen, ścieżki 37 i 88, 2024-01 … 2026-09).
- **Notatniki:** `EGMS_Check` (E1, zapis wyniku), `EGMS_Monitoring` (całość w Colab), dwa krótkie notatniki pokazowe
  po angielsku (`Showcase_1_GNSS_Groningen`, `Showcase_2_Levelling_NRW`).

## 2. Co jest sprawdzone

| Co | Wynik | Status |
|---|---|---|
| E1: EGMS L2b 2019–2023 wobec 24 stacji GNSS osiadających i 8 stabilnych (Groningen) | K1 91% par, K2 4,7 mm, K3 2,22 mm/rok, nachylenie 0,96 | **CZĘŚCIOWO** (K3 nie) |
| E1b: to samo na wydaniu 2020–2024 | K1 99%, K2 4,7 mm, K3 1,62 mm/rok, nachylenie 0,94; L3 pion: K1 96% | **CZĘŚCIOWO** (K3 nie) |
| E2: EGMS L3 pion 2019–2023 wobec niwelacji, 1216 reperów (zachodnia NRW) | N1 6,0 mm, N2 77%, N3 3,7 mm, N4 −1,97 mm/rok; nachylenie 0,96; niecki: znak 100% | **3 z 4 kryteriów niespełnione** (stałe przesunięcie) |
| E2, wariant względny (policzony po wariancie głównym) | N1 3,4 mm, N2 94%, N4 −1,00 mm/rok | spełnione, informacyjnie |
| GNSS w zachodniej NRW | brak stacji osiadających | **nierozstrzygnięte** |
| Pasy niepewności EGMS (rmse) | w pasie tylko 12% reperów | rmse zbyt optymistyczny (opisowo) |

Pełna tabela: `docs/evidence/karta_wynikow.md`.

## 3. Czego nie mówimy (granice)

- Dwa regiony, płaski teren, powolny ruch (do kilkunastu mm/rok). Nie uogólniamy na szybkie osiadania górnicze,
  osuwiska, ruch nagły ani pojedyncze budynki.
- EGMS jest archiwum aktualizowanym raz w roku, a nie wczesnym ostrzeganiem.
- EGMS L2b/L3 jest kalibrowany modelem GNSS, więc porównanie z GNSS nie jest w pełni niezależne; niwelacja jest.
- Przyczyna przesunięcia −2 mm/rok w NRW (układy odniesienia) i różnica orbit w Groningen to hipotezy, niesprawdzone.

## 4. Decyzje

- **D-095 (2026-11-02):** EGMS Check w standardzie projektu GeoWorldLook, wersja 1.0.0 — pakiet `egmscheck` jako
  cienka warstwa nad modułami `step_0N` (bez przenoszenia kodu), publikacja na żądanie, CI, archiwum dokumentów.
  Opis: `docs/plans/Plan_v3_produkt.md`.
- D-094 (2026-11-02): historia repozytorium przepisana (`docs/evidence/historia_git.md`).
- Wcześniejsze decyzje autora (2026-10-10 … 10-15): w `CHECK_CONFIG` (klucze `approved`) i w
  `docs/archive/plans/Plan_v2_implementacja.md`, sekcja 6.

## 5. Dalej (propozycje do decyzji autora)

| Co | Po czym | Uwagi |
|---|---|---|
| Te same reguły na następnym wydaniu EGMS | po publikacji wydania | `run`, potem `publish`; progi bez zmian |
| Etap B na prawdziwych danych (HyP3 + MintPy, Groningen) | konto NASA Earthdata, kredyty HyP3 | własne przetwarzanie Sentinel-1 poza wydaniem EGMS |
| Sprawdzenie hipotezy przesunięcia w NRW | — | punkty nawiązania niwelacji, układy ETRF2000 / DHHN2016 |
| Moduły `step_0N` przeniesione do pakietu (jak AgriScreen 1.0) | gdy Colab przestanie być zapasem | z testem regresji na tych samych danych |

## 6. Gdzie co jest

| Temat | Dokument |
|---|---|
| Kod, moduły i zadania | `docs/ARCHITEKTURA.md` |
| Uruchomienie na tym komputerze | `docs/URUCHOMIENIE_LOKALNE.md` |
| Zmiany wersji | `CHANGELOG.md` |
| Wszystkie wyniki w jednej tabeli | `docs/evidence/karta_wynikow.md` |
| Wyniki i ich omówienie | `docs/evidence/F9_E1_interpretacja_wynikow.md`, `F10_NRW_niwelacja_EGMS.md` |
| Metodyka, źródła, literatura | `docs/evidence/F4_metodyka.md`, `F5_zrodla_danych.md`, `F1_…`, `F7_…` |
| Opublikowane wyniki | `docs/showcase/` |
| Plan aktywny | `docs/plans/Plan_v3_produkt.md` |
| Historia (plany v1–v2, migracja, przekazania) | `docs/archive/` |
| Historia repozytorium (przepisana 2026-11-02, D-094) | `docs/evidence/historia_git.md` |
