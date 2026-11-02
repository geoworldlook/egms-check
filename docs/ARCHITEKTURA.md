# EGMS Check — architektura

Stan: 2026-11-02, wersja 1.0.0 (D-095). Opis kodu, który jest w repozytorium; plany i historia w `docs/plans/`
i `docs/archive/`. Wzór układu: AgriScreen (mechanizm `run_task`, rejestr `gwl_*`, kod i dane w osobnych katalogach).

## 1. Przepływ

```text
dane otwarte: API EGMS (Copernicus, klucz CLMS) · NGL (GNSS) · Geobasis NRW (niwelacja)
        │
        ▼
python -m egmscheck run  (albo notatnik notebooks/EGMS_Monitoring.ipynb w Colab)
        │   step_09_local.run → step_05.setup_runtime(kod, dane) → run_task(...) dla każdego zadania
        ▼
katalog danych na Dysku Google (Pulpit\GeoWorldLook\data\egms-check = Mój dysk\GeoWorldLook\egmscheck)
        data/01_Raw_EGMS, 02_Raw_Ground   surowe pliki (tylko do odczytu, wpis w data/00_Metadata/MANIFEST.csv)
        data/03_Extracts/<region>/        wycinki wokół punktów naziemnych, szeregi w formacie długim
        data/05_Final_Outputs/egmscheck/  tabele kryteriów, werdykty, ryciny, run_summary.md
        data/registry/gwl_*.csv           rejestr uruchomień, punktów i metryk
        │
        ▼
python -m egmscheck publish → docs/showcase/ (stały wybór plików + egmscheck_results.json) → README, strona
```

Kod i dane są rozdzielone: kod w klonie repozytorium (`projects/egms-check`), dane w katalogu z ustawień
(`local_settings.json`, `EGMSCHECK_DATA_DIR` albo `--data-dir`). W Colab dane leżą w klonie na Dysku
(`DATA_ROOT` = katalog projektu). Klucze tylko w katalogu `secrets` na Dysku, nigdy w repozytorium ani w logach.

## 2. Moduły

| Moduł | Odpowiedzialność |
|---|---|
| `step_00_reference_check.py` | spójność tabel przepisanych z publikacji (`data/04_Reference/`); bez sieci |
| `step_01_ingest.py` | API EGMS: token z klucza CLMS (JWT RS256), wyszukanie, pobranie przyrostowe z SHA-256 i manifestem; NGL: MIDAS, szeregi `tenv3`, reguła wyboru stacji E1 |
| `step_02_checks_extract.py` | wycinek punktów L2b wokół stacji (plik czytany fragmentami); kontrole konwencji A1–A3, A5 (duplikaty z zakładek burstów) |
| `step_03_compare_gnss.py` | E1: rzut GNSS na kierunek satelity, wspólne daty (±6 dni), prędkość tym samym modelem, dv, kryteria K1–K4, ryciny |
| `step_04_egms_aoi.py` | EGMS dla obszaru: wyszukanie L2b i L3, plan pobrania z kontrolą miejsca, czytnik L3, komórka L3 przy punkcie, mapa prędkości |
| `step_05_colab_run.py` | sterowanie: `CHECK_CONFIG` (jedyne miejsce parametrów, klucze `approved`), `setup_runtime`, `run_task`, rejestr `gwl_*`, zadania `task_*`, `run_summary` |
| `step_06_ground.py` | pomiar naziemny: stacje GNSS w obszarze, czytniki niwelacji NRW, epoki w oknie wydania, porównanie z EGMS pion (N1–N4), wariant względem grupy stabilnej |
| `step_07_monitoring.py` | wspólny format długi szeregów, próbkowanie 6/12 dni, czas do wykrycia trendu, ryciny pokazu i pasy niepewności |
| `step_08_hyp3_mintpy.py` | etap B: bursty Sentinel-1 (asf_search), sieć par SBAS, zlecenia ASF HyP3, przycięcie, MintPy, szeregi w punktach i dowiązanie do EGMS |
| `step_09_local.py` | obliczenia na własnym komputerze: ustawienia, plan zadań w kolejności notatnika, blokada, log, `last_run.json`; parser poleceń |
| `egmscheck/` | pakiet: `python -m egmscheck …` (ten sam parser co `step_09_local.py`), `publish.py` (publikacja do `docs/showcase/`), `__version__` |
| `build_colab_*.py` | generatory notatników (`EGMS_Check`, `EGMS_Monitoring`, `Showcase_*`); notatników nie edytuje się ręcznie |

Moduły `step_0N` leżą w katalogu głównym, bo importują je notatniki Colab (zapas) i klon repozytorium na Dysku;
pakiet ich nie kopiuje, tylko wywołuje (D-095). Nagłówek każdego modułu opisuje metodę i literaturę.

## 3. Zadania (kolejność z `step_09_local.plan_tasks`, taka sama jak w `notebooks/EGMS_Monitoring.ipynb`)

Dla każdego regionu (`groningen`, `nrw_west`):

1. `egms_search_<r>` → `egms_download_<r>` (po potwierdzeniu rozmiaru `CONFIRM_MB_<R>`);
2. `select_gnss_<r>` → `gnss_download_<r>`; w regionie z niwelacją `levelling_<r>`;
3. `egms_search_sites_<r>` → `egms_download_sites_<r>` (pliki dla punktów spoza obszaru);
4. `extract_<r>` → `checks_<r>` (błąd kontroli zatrzymuje przebieg) → `compare_gnss_<r>` (werdykty L2b i L3);
5. w regionie z niwelacją: `compare_levelling_<r>`, potem drugie wydanie tylko do niwelacji (`levelling_egms_search`,
   `levelling_egms_download`, `levelling_extract`, `compare_levelling_check`).

Potem dla każdego regionu `monitoring_archive_<r>` i `figures_<r>`; z `--stage-b` etap B (`hyp3_plan`, zlecenia,
pobranie, `mintpy`, `hyp3_compare` dla każdej ścieżki, po potwierdzeniu liczby zleceń `CONFIRM_JOBS`); na końcu
`summary` (`run_summary.md` i `.json`: wersje bibliotek, commit, konfiguracja, zatwierdzenia, werdykty).

Każde zadanie idzie przez `run_task`: zapis w `gwl_runs` (czas, status, commit, parametry). Błąd zadania jest zapisany
i zgłoszony dalej — pierwszy błąd zatrzymuje przebieg; wynik zadania, które się nie powiodło, nie może wyglądać jak
prawdziwy (`CLAUDE.md`, zasada 3). Bez klucza CLMS przebieg czyta istniejące wycinki z `data/03_Extracts/`.

## 4. Konfiguracja i decyzje

`CHECK_CONFIG` w `step_05_colab_run.py`: `project` (ścieżki), `egms` (wydanie 2020–2024, L2b i L3 pion), `regions`
(obszary, reguła stacji, niwelacja NRW i drugie wydanie 2019–2023), `gnss`, `method`, `thresholds` (K1–K4, N1–N4),
`monitoring`, `hyp3`. Każda sekcja eksperymentu ma klucz `approved` (data decyzji autora); `require_approved`
zatrzymuje zadanie, gdy sekcja nie jest zatwierdzona. Funkcje nie mają wartości domyślnych dla parametrów
eksperymentu. Lokalnie zmieniają się tylko ścieżki kluczy (`step_09_local.make_config`). Stan zatwierdzeń:
`python -m egmscheck approvals`.

## 5. Rejestr `gwl_*` (katalog danych, `data/registry/`)

| Tabela | Klucz | Zawartość |
|---|---|---|
| `gwl_runs` | `run_id` | uruchomienia zadań: czas, status (`ok` / `skipped` / `error`), commit kodu, parametry, komunikat |
| `gwl_sites` | `region, site` | punkty naziemne: stacje GNSS (grupa osiadająca / stabilna), repery |
| `gwl_validation_metrics` | `region, product, reference, site, track, radius_m, metric` | metryki porównań (prędkości, różnice, liczby punktów) |

Upsert po kluczu (nowe / zmienione / bez zmian), zapis atomowy. Schemat `gwl_runs` jak w AgriScreen.

## 6. Publikacja (`egmscheck/publish.py`)

Stały wybór plików z `data/05_Final_Outputs/egmscheck/` → `docs/showcase/` (te same nazwy) i `egmscheck_results.json`:
tabele kryteriów z kodami K1…/N1…, werdykty, podział na grupy, przesunięcie, pasy niepewności oraz zadanie, czas
i commit kodu każdego wyniku z `gwl_runs` (z odpowiednikiem w historii po D-094 z `docs/evidence/historia_git_mapa.csv`).
Brak pliku wymaganego = wyjątek; pliki opcjonalne (rycina rozrzutu, mapy, `run_summary`) są kopiowane, gdy istnieją,
a ich brak trafia do JSON. Commit tylko `docs/showcase/`; push systemowym Gitem bez okien logowania; `--no-git`
= samo kopiowanie.

## 7. Testy

| Polecenie | Co sprawdza |
|---|---|
| `python -m egmscheck selftest` | testy bez sieci wszystkich modułów (`step_00`, `step_0N --selftest`, `step_09_local`, publikacja); tak samo w CI |
| `python -m egmscheck test` | pełny test lokalny: atrapy serwerów, dane o znanej odpowiedzi, trzy przebiegi (`tests/local_harness/`) |
| `tests/colab_harness/`, `tests/monitoring_harness/` | notatniki Colab na atrapach (Linux, uruchamiane ręcznie) |
| CI (`.github/workflows/selftest.yml`) | ruff i selftest przy każdej zmianie kodu (Linux, Python 3.12) |

Na Windows bez długich ścieżek test etapu B (`step_08`) jest pomijany z komunikatem (nazwy produktów HyP3 mają
ok. 80 znaków); w CI na Linuksie działa.

## 8. Dokumenty

| Dokument | Treść |
|---|---|
| `docs/STAN_I_PLAN.md` | stan i plan na jednej stronie |
| `docs/URUCHOMIENIE_LOKALNE.md` | uruchomienie na własnym komputerze |
| `docs/evidence/karta_wynikow.md` | wszystkie wyniki w jednej tabeli |
| `docs/evidence/F1`–`F10` | literatura, metodyka (F4), źródła danych (F5), przypadki, wyniki E1 (F9) i E2 (F10) |
| `docs/evidence/zrodla/README.md` | dokumenty innych wydawców: odnośniki i sumy SHA-256 |
| `docs/plans/Plan_v3_produkt.md` | plan aktywny (D-095) |
| `docs/archive/` | plany v1–v2, przekazanie z migracji, notatki |
