# 9. Audyt po migracji (nowe konto, 2026-10-10)

Sprawdzone w nowej sesji Claude Code, na świeżym klonie gałęzi `claude/dreamy-dirac-jd4vue` (commit `f60d52b`).

## 9.1 Co sprawdzono i z jakim wynikiem

| Sprawdzenie | Wynik |
|---|---|
| `python step_00_reference_check.py` | przechodzi |
| `python step_01_ingest.py --selftest` | przechodzi |
| `prototypes/egms_simple_check.py --selftest` | przechodzi (wymaga `pyproj`) |
| `python build_colab_master.py` | notatnik w repozytorium zgodny z generatorem (brak różnic) |
| `tests/colab_harness/` (środowisko jak Colab: Python 3.13, pandas 2.2.3, numpy 2.0.2) | `STATUS: OK`; wartości identyczne z oczekiwanymi w README (K1 100%, K2 1,6 mm, K3 0,78 mm/rok, nachylenie 1,00, 5 duplikatów) |
| Klucze w historii gita (wszystkie gałęzie) | brak kluczy prywatnych i sekretów; `access_token` występuje tylko jako nazwa funkcji w kodzie notatnika |
| `except Exception` / gołe `except:` | brak |
| Parametry domyślne w sygnaturach `step_0*.py` | tylko w atrapie sesji HTTP selftestu (`step_01_ingest.py:390–426`) — dopuszczalne |
| Dysk Google nowego konta | nie zawiera plików projektu (wyszukanie puste) — wyniki i GNSS są tylko na starym Dysku |

## 9.2 Nowe ustalenia

| # | Waga | Ustalenie | Zalecenie |
|---|---|---|---|
| N1 | **WYSOKI** | **Istnieje prawdziwy wynik E1, nieopisany w tym dokumencie.** Gałąź `main` ma commit `2e781c9` („Utworzono za pomocą Colab”, 21:08 UTC) z notatnikiem zapisanym razem z wyjściami, pod ścieżką `dreamy-dirac-jd4vue/notebooks/EGMS_Check.ipynb`. Przebieg użył kodu `fe368e8`. Wynik: 31 plików pobranych, wycinek 10,3 MB; kontrole A1–A3 i A5 zaliczone (206 duplikatów usuniętych); 127 wierszy stacja × ścieżka, 95 par osiadających; **K1 91% (≥ 80%) ✔, K2 4,7 mm (≤ 5) ✔, bias −0,18 mm/rok, MAD 0,86 mm/rok, K3 max \|v_EGMS\| 2,22 mm/rok (≤ 1,5) ✘ (31 par), K4 nachylenie 0,96 (wyraz wolny +0,05)**. Wniosek: **CZĘŚCIOWO**. | Przyjąć ten wynik jako pierwszy przebieg główny. Zapisać go w `Plan_v1_otwarte_pytania.md` (sekcja F) z datą i commitem. Skopiować tabele z `data/05_Final_Outputs/` starego Dysku (w zapisie notatnika tabela par jest obcięta do 10 wierszy — nie widać, która stacja stabilna dała 2,22 mm/rok). |
| N2 | **WYSOKI** | **Zasada 9 (uczciwość statystyczna) po wyniku.** Progi K1 = 80% i K3 = 1,5 mm/rok oraz definicja K3 jako \|v_EGMS\| były zapisane w kodzie (`fe368e8`, 18:13 UTC, komentarz „propozycja zatwierdzona razem z regułą”) **przed** przebiegiem (21:08 UTC) — to jest rejestracja przed obliczeniami. `03_metoda_i_decyzje.md` (3.3) i decyzje 1–2 z `06_otwarte_decyzje.md` traktowały je jako otwarte, ale po wyniku **nie wolno ich już zmieniać**. Zamiana K3 na \|dv\| (M3) albo dodanie testu różnicowego (M1) teraz byłyby analizą dodatkową, a nie głównym kryterium. | Wniosek główny pozostaje CZĘŚCIOWO. M3 i M1 można policzyć i pokazać obok, jawnie oznaczone jako „analiza dodatkowa po wyniku głównym”. Autor potwierdza tę interpretację. |
| N3 | ŚREDNI | **Przyczyna niespełnienia K3 (z pełnej tabeli `groningen_results.csv` na starym Dysku, 100 m, pary `ok` z A6).** To nie jedna odstająca para: 8 z 31 par stabilnych ma \|v_EGMS\| > 1,5 mm/rok. Przekroczenia dotyczą głównie **mareografów TGBF (Borkum) i TGEM (Emden)** (6 z 8; mediana po ścieżkach v_EGMS −1,64 i −1,53 mm/rok, 34–46 punktów), do tego SCHI/110 i NORG/139. GNSS w LOS też nie pokazuje zera: mediana v_gnss_los dla stacji stabilnych to −0,79 mm/rok, a dla TGEM −1,16. **\|dv\| > 1,5 mm/rok mają tylko 3 z 31 par** (TGBF/37 1,94; SCHI/88 −1,76; TGBF/139 1,54). Czyli EGMS w większości zgadza się z GNSS także na stacjach stabilnych, a K3 nie przechodzi, bo stacje „stabilne” według MIDAS (vu z całego okresu, w pionie) nie są stabilne w LOS w latach 2019–2023. Przewidywały to M3 i M5. | Werdykt główny bez zmian (CZĘŚCIOWO). W raporcie pokazać obok K3 kolumny v_gnss_los i dv (analiza pomocnicza). |
| N3a | ŚREDNI | **Ścieżka 88 (wstępująca) zaniża osiadanie.** 6 z 9 par osiadających poza progiem K1 to ścieżka 88; mediana dv = −1,08 mm/rok (na pozostałych ścieżkach od −0,67 do +0,43). Na poziomie stacji (mediana dv po ścieżkach) **wszystkie 24 stacje osiadające mieszczą się w 1,5 mm/rok** (M2). | Opisać jako obserwację; sprawdzić, czy różnica jest stała w czasie (wykres szeregów dla ścieżki 88). Promień 200 m: K1 92%, K2 4,7 mm, K3 2,13 mm/rok — wynik stabilny względem promienia. |
| N3b | **WYSOKI (zasada 3)** | **Ciche pominięcie stacji.** Wybrano 27 stacji osiadających, ale w wynikach są tylko 24. **AME2, AWG1 i KNOC nie mają ani jednego wiersza**, choć mają szeregi GNSS i przypisane pliki EGMS. Przyczyna: pętla porównania (`build_colab_master.py:164`) iteruje po `points.groupby(['site','track','direction'])`, więc para stacja × ścieżka bez punktów w wycinku 200 m znika bez śladu. Status „za mało punktów” dostaje tylko para, która ma 1–2 punkty (MODD/37). Werdykt się nie zmienia (pary bez punktów i tak nie wchodzą do K1), ale raport zawyża wrażenie pokrycia i łamie zasadę „błąd głośny, nigdy cichy”. | Poprawić: iterować po iloczynie stacje × ścieżki z sekcji 4 i dla braku punktów zapisywać jawny status „brak punktów EGMS w 200 m”. Podać w raporcie: 27 wybranych, 24 z wynikiem, 3 bez punktów EGMS (AME2, AWG1 — Ameland; KNOC — nabrzeże Ems). |
| N4 | ŚREDNI | **Gałąź `main` jest rozbieżna z gałęzią roboczą** (tylko „Initial commit” + zapis z Colab w nietypowym katalogu `dreamy-dirac-jd4vue/`). Scalenie PR wymaga decyzji, co zrobić z tym plikiem. | Przy scalaniu przenieść zapis z wynikami do `docs/evidence/` (np. `E1_przebieg_2026-10-10.ipynb`) albo usunąć z `main` i zachować tabele z Dysku. Decyzja autora. |
| N5 | NISKI | `tests/colab_harness/README.md`: `PYTHONPATH=$H/fake` ze ścieżką względną nie dociera do jądra (`ModuleNotFoundError: google`). | Poprawione w tym commicie: `H=$PWD/tests/colab_harness`. |
| N6 | NISKI | Brak `run_summary.md` (C2) dotyczy teraz realnego przebiegu: wersje bibliotek z Colab z 2026-10-10 nie zostały zapisane. Commit kodu (`fe368e8`) jest znany z wyjścia sekcji 0. | Przy następnym przebiegu zapisać wersje; dla przebiegu z 2026-10-10 podać commit i datę. |

## 9.3 Zaktualizowane otwarte decyzje (zastępują `06_otwarte_decyzje.md`, punkty 1–3)

1. **Potwierdzić interpretację N2**: wynik główny = CZĘŚCIOWO; progi i definicja K3 zamrożone.
2. **Analizy dodatkowe po wyniku** (oznaczone jako takie): K3 jako \|dv\|, K1 na poziomie stacji (M2), test
   różnicowy osiadająca − stabilna (M1). Które z nich robimy?
3. ~~Skąd wziąć pełne tabele~~ — rozwiązane: stary Dysk (geo.world.look@gmail.com) udostępniony nowemu kontu;
   `05_Final_Outputs/egmscheck/groningen_results.csv` (254 wiersze, 100 i 200 m) przeczytany. Do zrobienia: kopia
   folderu na nowy Dysk (`04_migracja_kroki.md`, krok 4).
3a. Poprawka cichego pominięcia stacji (N3b) — przed kolejnym przebiegiem.
4. Bez zmian: E2 (NRW czy Hengelo), scalenie z `main` (z uwzględnieniem N4), przypadki dodatkowe.
