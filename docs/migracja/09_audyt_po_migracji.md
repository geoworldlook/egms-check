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
| N3 | ŚREDNI | **K3 niespełnione: przyczyna nieznana.** Możliwe: stacja stabilna według MIDAS (cały okres) porusza się w oknie 2019–2023 (M3); mało punktów lądowych przy mareografach TG\* (M5); szum pojedynczej ścieżki. | Z pełnej tabeli par: wskazać stację i ścieżkę, podać `v_gnss_los` i `dv`. Jeśli GNSS też pokazuje ruch w LOS, to rozbieżność dotyczy reguły wyboru stabilnych, nie EGMS — opisać to w raporcie, nie zmieniając werdyktu. |
| N4 | ŚREDNI | **Gałąź `main` jest rozbieżna z gałęzią roboczą** (tylko „Initial commit” + zapis z Colab w nietypowym katalogu `dreamy-dirac-jd4vue/`). Scalenie PR wymaga decyzji, co zrobić z tym plikiem. | Przy scalaniu przenieść zapis z wynikami do `docs/evidence/` (np. `E1_przebieg_2026-10-10.ipynb`) albo usunąć z `main` i zachować tabele z Dysku. Decyzja autora. |
| N5 | NISKI | `tests/colab_harness/README.md`: `PYTHONPATH=$H/fake` ze ścieżką względną nie dociera do jądra (`ModuleNotFoundError: google`). | Poprawione w tym commicie: `H=$PWD/tests/colab_harness`. |
| N6 | NISKI | Brak `run_summary.md` (C2) dotyczy teraz realnego przebiegu: wersje bibliotek z Colab z 2026-10-10 nie zostały zapisane. Commit kodu (`fe368e8`) jest znany z wyjścia sekcji 0. | Przy następnym przebiegu zapisać wersje; dla przebiegu z 2026-10-10 podać commit i datę. |

## 9.3 Zaktualizowane otwarte decyzje (zastępują `06_otwarte_decyzje.md`, punkty 1–3)

1. **Potwierdzić interpretację N2**: wynik główny = CZĘŚCIOWO; progi i definicja K3 zamrożone.
2. **Analizy dodatkowe po wyniku** (oznaczone jako takie): K3 jako \|dv\|, K1 na poziomie stacji (M2), test
   różnicowy osiadająca − stabilna (M1). Które z nich robimy?
3. **Skąd wziąć pełne tabele**: skopiować `data/05_Final_Outputs/` ze starego Dysku czy ponownie uruchomić notatnik
   na nowym koncie (wymaga nowego klucza CLMS i ok. 4,4 GB pobierania, chyba że skopiujemy wycinek
   `data/03_Extracts/groningen/egms_l2b_points.csv.gz`, 10,3 MB).
4. Bez zmian: E2 (NRW czy Hengelo), scalenie z `main` (z uwzględnieniem N4), przypadki dodatkowe.
