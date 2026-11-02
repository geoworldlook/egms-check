# Dokumenty źródłowe innych wydawców

Dokumentów innych wydawców nie przechowujemy w repozytorium: podajemy odnośnik, wersję i sumę SHA-256, żeby każdy
mógł pobrać ten sam plik i sprawdzić, że jest identyczny (D-095).

## Opis formatu reperów NRW (Höhenfestpunkte)

| | |
|---|---|
| Dokument | *Datenformatbeschreibung Höhenfestpunkte (HFP) NRW*, Stand: 07/2023, 2 strony |
| Wydawca | Bezirksregierung Köln, Geobasis NRW |
| Odnośnik | https://www.opengeodata.nrw.de/produkte/geobasis/rb/fd/hfp_plzf_csv/Datenformatbeschreibung.pdf (ten sam plik w `…/hfp_pl_csv/`) |
| SHA-256 | `b73ce0c64aa0cb26720cc277423cc453b46206131ef2b50879ea5aeeee76e955` (285 673 bajty, plik z 17.07.2023) |
| Sprawdzone | 2026-11-02: plik na stronie identyczny z kopią używaną od 2026-10-12 (kopia była w repozytorium do wersji 1.0.0) |
| Licencja | strona produktu: dane Geobasis NRW na licencji Datenlizenz Deutschland – Zero – Version 2.0; sam dokument nie podaje licencji, dlatego tylko odnośnik |

Co z niego bierze kod (`step_06_ground.py`, czytniki niwelacji; `step_05_colab_run.py`, konfiguracja `nrw_west`):

- pliki `hfp_pl.csv` (Punktliste) i `hfp_plzf.csv` (Punktliste-Zeitfolge) **bez wiersza nagłówka**, kolumny opisane
  kolejnością; kodowanie UTF-8; separator `;`; tekst w cudzysłowie; przecinek dziesiętny;
- Punktliste: numer punktu, nazwa, Ostwert i Nordwert, wysokość w **DHHN2016**, wartość grawimetryczna;
- Punktliste-Zeitfolge: numer punktu, data pomiaru, wysokość w DHHN2016;
- przykład z dokumentu (punkt 3613900015 „Halen”) służy w teście czytnika (`step_06_ground.py --selftest`).

Druga informacja wydawcy, `Nutzerinformation.pdf` (ten sam katalog na stronie), też nie jest w repozytorium;
jej uwaga o ograniczonej porównywalności wartości jest streszczona w `docs/evidence/F5_zrodla_danych.md` (sekcja 5).
