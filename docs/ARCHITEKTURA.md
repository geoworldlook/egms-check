# EGMS Check — architektura (docelowa)

> Status: PROPOSED, 2026-10-09. Kodu jeszcze nie ma (poza `step_00_reference_check.py`).
> Układ jest przeniesiony z AgriWatch (`1_geoworldlook-agriscreen`, `docs/ARCHITEKTURA.md`):
> te same nazwy plików, ten sam mechanizm `run_task` i ten sam rejestr `gwl_*`.
> Po napisaniu kodu ten dokument ma opisywać stan faktyczny, a plany zostają w `docs/plans/`.

## 1. Przepływ

```text
GitHub (kod) ──git pull──▶ Dysk Google: MyDrive/GeoWorldLook/egmscheck ◀──── Colab
                                     │
notebooks/EGMS_Check.ipynb ──▶ step_05.setup_runtime ──▶ run_task(...) dla każdego zadania
                                                                   │
 ingest_egms ─▶ ingest_ground ─▶ checks ─▶ extract ─▶ compare_gnss ─▶ compare_levelling ─▶ forecast ─▶ bulletin
 (step_01)      (step_01)       (step_02)  (step_02)  (step_03)       (step_04)            (step_04)   (step_06)
                                                                   │
                                     data/registry/gwl_*.csv  +  data/05_Final_Outputs/egmscheck/
```

Pliki EGMS pobiera zadanie `ingest_egms` przez oficjalne API (`https://egms.land.copernicus.eu/insar-api/archive`):
zapytanie `search` dla punktu lub prostokąta, potem `download` do `data/01_Raw_EGMS/` na Dysku, przyrostowo
(plik już pobrany nie jest pobierany ponownie; każdy trafia do manifestu). Token CLMS API leży na Dysku poza
katalogiem repozytorium (`MyDrive/GeoWorldLook/secrets/clms_token.json`). Bez tokenu zadanie kończy się statusem
„pominięte: brak tokenu" zapisanym w `gwl_runs`, a dalsze zadania czytają wycinki z `data/03_Extracts/` w repozytorium.
Dzięki temu czytelnik wpisu odtwarza wykresy bez konta w CLMS.

## 2. Moduły (plan)

| Moduł | Odpowiedzialność | Główne funkcje (propozycja) |
|---|---|---|
| `step_00_reference_check.py` | spójność tabel przepisanych z publikacji | istnieje; uruchamiany także z `--selftest` |
| `step_01_ingest.py` | pobranie EGMS przez API, wczytanie danych, manifest | `get_access_token`, `search_egms`, `sync_egms` (przyrostowo), `read_egms_l2`, `read_egms_l3`, `read_pangaea_gnss`, `read_levelling_table`, `update_manifest` |
| `step_02_checks_extract.py` | kontrole konwencji, duplikaty, wycinki | `check_los_vector`, `check_sign`, `drop_overlap_duplicates`, `extract_buffer`, `extract_cells` |
| `step_03_compare_gnss.py` | przypadek 1 | `project_to_los`, `aggregate_gnss`, `common_window`, `fit_velocity`, `compare_series` |
| `step_04_compare_levelling.py` | przypadek 2 | `relative_to_reference`, `read_at_epochs`, `compare_height_changes`, `forecast_test` |
| `step_05_colab_run.py` | sterowanie i rejestr | `setup_runtime`, `run_task`, `registry_read/upsert`, `CHECK_CONFIG`, zadania `task_*`, `--selftest` |
| `step_06_figures_bulletin.py` | wykresy i raport | `plot_gnss_overlay`, `plot_levelling_overlay`, `plot_scatter`, `build_bulletin`, `run_summary` |
| `build_colab_master.py` | generator `notebooks/EGMS_Check.ipynb` | `create_check_notebook` |

Nagłówek każdego modułu jak w AgriWatch: blok opisowy „EGMS Check - KROK N: …" po polsku, z metodą
i literaturą; `logger`; sekcje numerowane rzymsko.

## 3. Zadania (`step_05`)

| Zadanie | Wejście | Wyjście |
|---|---|---|
| `task_ingest_egms` | token CLMS, położenia stacji i reperów, wydania i produkty z `CHECK_CONFIG` | pliki w `data/01_Raw_EGMS/`, wpisy w manifeście (nazwa, rozmiar, wydanie, data) |
| `task_ingest_ground` | `PTO1.txt`, tabela reperów | `gwl_sites`, `gwl_observations` (produkty naziemne) |
| `task_checks` | punkty EGMS | raport kontroli A1–A7; błąd zatrzymuje dalsze zadania tego przypadku |
| `task_extract` | punkty EGMS, położenia stacji i reperów | `data/03_Extracts/*.csv`, `gwl_observations` (produkty EGMS) |
| `task_compare_gnss` | wycinki, szereg GNSS | `gwl_validation_metrics` (przypadek 1) |
| `task_compare_levelling` | wycinki, tabela reperów | `gwl_validation_metrics` (przypadek 2, poziom 1) |
| `task_forecast` | wydanie EGMS sprzed epoki, tabela reperów | `gwl_validation_metrics` (przypadek 2, poziom 2) |
| `task_bulletin` | metryki, szeregi | `bulletin.md`, wykresy PNG, `egmscheck_latest.json` |
| `task_summary` | wszystko | `run_summary.md`: wersje, konfiguracja, kontrole, wynik progów, błędy |

## 4. Metoda

Opis i wzory: `docs/evidence/F4_metodyka.md`. Progi: `docs/plans/Plan_v1_kryteria_akceptacji.md`.

## 5. Rejestr `gwl_*` (Dysk Google, `data/registry/`)

Te same tabele i klucze co w AgriWatch, żeby oba projekty miały jeden schemat bazy.

| Tabela | Klucz | Użycie w EGMS Check |
|---|---|---|
| `gwl_sites` | `site_id` | `PTO1` (`site_type = gnss_station`), repery `HENGELO_<nr>` (`levelling_benchmark`) |
| `gwl_observations` | `site_id, product, variable, time_utc, orbit` | `product`: `EGMS_L2b_<wydanie>`, `EGMS_L3_<wydanie>`, `GNSS_PANGAEA`, `LEVELLING_NLOG`; `variable`: `los_displacement`, `up_displacement`, `height_nap`; `orbit`: numer ścieżki; `n_pixels`: liczba punktów w buforze |
| `gwl_validation_metrics` | `site_id, product, reference, segment, period, subset, metric` | `reference`: `GNSS_PANGAEA` lub `LEVELLING_NLOG`; `segment`: `overlay`, `forecast`; `subset`: bufor lub ścieżka; `metric`: `velocity_diff`, `series_diff_std`, `height_change_diff`, `corr` |
| `gwl_runs` | `run_id` | jak w AgriWatch: czas, status, commit, parametry |

`gwl_anomalies`, `gwl_status` i `gwl_calibrations` nie są używane.
Schemat tabel trzeba skopiować z `REGISTRY_SCHEMA` w AgriWatch, nie odtwarzać z pamięci.

## 6. Konfiguracja

Jak w AgriWatch: jedno miejsce, słownik `CHECK_CONFIG` w `step_05_colab_run.py`. Zawartość do przeniesienia
z szablonów `data/00_Metadata/case_1_gnss_pto1.example.yaml` i `case_2_reper_hengelo.example.yaml`.
Parametry eksperymentu (wydanie EGMS, ścieżki, bufory, okno, model prędkości, progi) nie mają wartości
domyślnych w sygnaturach funkcji; brak klucza w konfiguracji zatrzymuje zadanie.

## 7. Testy offline

```bash
python step_00_reference_check.py        # już działa
python step_05_colab_run.py --selftest   # [plan] dane syntetyczne EGMS + prawdziwe tabele referencyjne
```

## 8. Dokumenty

| Dokument | Status |
|---|---|
| `docs/plans/Plan_v1_walidacja_EGMS.md` | `PROPOSED` (2026-10-09) — plan główny |
| `docs/plans/Plan_v1_test_EGMS.md` | `PROPOSED` — trzy twierdzenia, progi, reguła decyzji |
| `docs/plans/Plan_v1_potok.md` | `PROPOSED` — etapy, testy, kolejność |
| `docs/plans/Plan_v1_dane_do_pobrania.md` | `PROPOSED` — zamknięta lista plików |
| `docs/plans/Plan_v1_kryteria_akceptacji.md` | `PROPOSED` — do zatwierdzenia przed pierwszym przebiegiem |
| `docs/plans/Plan_v1_otwarte_pytania.md` | lista robocza |
| `docs/plans/Plan_v1_wpis_na_blog.md` | `PROPOSED` |
| `docs/plans/Instrukcja_startowa.md`, `Prompty_Claude_Code.md` | instrukcje pracy w Claude Code |
| `docs/evidence/F1_przeglad_literatury_EGMS.md` | `Draft` — sześć publikacji w pełnym tekście |
| `docs/evidence/F2…`, `F3…` | `Draft` — specyfikacje przypadków |
| `docs/evidence/F4_metodyka.md`, `F5_zrodla_danych.md` | `Draft` |
| `docs/evidence/F6_przypadki_zapasowe/` | archiwum rozważanych wariantów (NRW, Lorca, odtworzenie tabel artykułu) |
