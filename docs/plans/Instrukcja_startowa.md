# Instrukcja startowa — co zrobić przed pierwszą sesją i jak prowadzić pracę w Claude Code

Status: PROPOSED, 2026-10-09. Część planu `Plan_v1_walidacja_EGMS.md`.

## A. Przygotowanie (robisz sam, raz)

| # | Krok | Wynik |
|---|---|---|
| 1 | Rozpakuj paczkę do katalogu `2_geoworldlook-egmscheck` i wykonaj `git init` | lokalne repozytorium |
| 2 | Sklonuj obok AgriWatch: `git clone https://github.com/geoworldlook/1_geoworldlook-agriscreen.git` | wzorzec struktury i mechanizmu `run_task` w sąsiednim katalogu |
| 3 | Załóż konto w Copernicus Land Monitoring Service i wygeneruj token API (instrukcja: https://eea.github.io/clms-api-docs/authentication.html) | plik JSON z kluczem prywatnym |
| 4 | Zapisz token **poza repozytorium**, np. `~/GeoWorldLook/secrets/clms_token.jwt` (w Colab: `MyDrive/GeoWorldLook/secrets/clms_token.jwt`) | ścieżka do podania w konfiguracji |
| 5 | Pobierz `https://download.pangaea.de/dataset/958598/files/PTO1.txt` | `data/02_Raw_Ground/1_gnss_pangaea/PTO1.txt` |
| 6 | Pobierz raport Strootbeekpark 2023 (adres w `Plan_v1_dane_do_pobrania.md`, pozycja 4) | `docs/evidence/literatura_pdf/` |
| 7 | Opcjonalnie wgraj PDF-y sześciu publikacji | `docs/evidence/literatura_pdf/` |
| 8 | Uruchom `python step_00_reference_check.py` | komunikat „All reference consistency checks passed." |

Kroki 3–4 można odłożyć do sesji 2. Krok 6 jest potrzebny dopiero w sesji 8.

## B. Praca w Claude Code

1. Otwórz katalog `2_geoworldlook-egmscheck` w Claude Code. Plik `CLAUDE.md` wczyta się sam.
2. Wklejaj prompty z `docs/plans/Prompty_Claude_Code.md` po kolei, jeden na sesję lub etap.
3. Nie przechodź do następnego promptu, dopóki nie jest spełniony warunek „Gotowe, gdy" z poprzedniego.
4. Gdy Claude Code zada pytanie o decyzję metodyczną, odpowiedz i dopisz decyzję z datą do
   `docs/plans/Plan_v1_otwarte_pytania.md`.
5. Progi z `docs/plans/Plan_v1_kryteria_akceptacji.md` zatwierdź **przed** sesją 5 (pierwsze porównanie).

## C. Kolejność sesji

| Sesja | Co powstaje | Potrzebne od Ciebie |
|---|---|---|
| 0 | orientacja, lista pytań | nic |
| 1 | szkielet z AgriWatch: `step_05`, `build_colab_master.py`, `--selftest` | sklonowany AgriWatch |
| 2 | dostęp do API EGMS, lista wydań | token CLMS |
| 3 | pobranie danych przypadku 1, manifest | `PTO1.txt`; zgoda na rozmiar pobrania |
| 4 | kontrole konwencji, duplikaty, wycinki | decyzje o buforze i filtrze wysokości |
| 5 | porównanie z GNSS, pierwszy wykres | zatwierdzone progi; decyzje o modelu prędkości i agregacji |
| 6 | wykresy, biuletyn, `run_summary.md`, notatnik | nic |
| 7 | szkic wpisu na blog (przypadek 1) | język wpisu |
| 8 | tabela reperów z PDF | PDF raportu; sprawdzenie przepisanych wartości |
| 9 | porównanie z niwelacją i test prognozy | decyzje o odniesieniu i reperach 300, 301 |
| 10 | domknięcie: architektura według stanu kodu, statusy planów | nic |

## D. Czego Claude Code nie zrobi za Ciebie

- nie założy konta i nie wygeneruje tokenu,
- nie zatwierdzi progów ani decyzji metodycznych,
- nie potwierdzi poprawności ręcznie przepisanej tabeli reperów (może ją przepisać i sprawdzić sumy, ale ostatnie słowo jest Twoje),
- nie sprawdzi warunków licencyjnych raportu NLOG i formuły atrybucji Copernicus.
