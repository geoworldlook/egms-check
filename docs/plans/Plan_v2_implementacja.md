# Plan v2 — implementacja: EGMS 2020–2024 (Groningen, zachodnia NRW) + monitoring HyP3/MintPy

> **Status:** ZAIMPLEMENTOWANE I PRZETESTOWANE OFFLINE, 2026-10-11 (commity `8ad90c9`…). Specyfikacja interfejsów dla modułów `step_04`–`step_08`.
> Stan: każdy moduł po niezależnej recenzji; `step_0N --selftest` (N = 1, 4–8) przechodzi; `tests/monitoring_harness/run_harness.sh`
> — 3 przebiegi zgodne z oczekiwaniem. **Na prawdziwych danych nieuruchomione** (serwery niedostępne ze środowiska Claude). Sekcja 6: decyzje.
> Decyzje autora z 2026-10-11: wydanie **2020–2024**; produkty **L2b i L3 pion**; NRW **bez Epe**;
> pomiar naziemny: **niwelacja, GNSS (jeśli są) i EGMS**; etap B: **ASF HyP3 + MintPy**, skrypt modułowy i automatyczny;
> wszystkie dane na Dysku Google konta GeoWorldLook, w projekcie `MyDrive/GeoWorldLook/egmscheck`.
> Kontekst: `Plan_v2_pokaz_EGMS_monitoring.md`.

## 0. Zasada: kontynuacja działającego kodu

- `step_01_ingest.py`, `step_02_checks_extract.py`, `step_03_compare_gnss.py`, `build_colab_master.py`
  i `notebooks/EGMS_Check.ipynb` (E1) **nie zmieniają zachowania**. Nowe moduły je importują.
- Wolno **dodać** funkcję do istniejącego modułu tylko wtedy, gdy nie da się jej umieścić w nowym; nie wolno zmienić
  sygnatury ani wyniku istniejącej funkcji.
- Przeniesione: `run_task`, `registry_*`, `setup_runtime`, `_git_commit` z AgriWatch (`step_05_colab_run.py`);
  `cell_containing`, `read_at_epochs`, `run_e2`, `summarize_e2`, `robust_stats`, `transform_xy`, `to_years`
  z `prototypes/egms_simple_check.py`.
- Zasady `CLAUDE.md`: błąd głośny (bez `except Exception`, bez wartości zastępczych, jawny `NaN` z powodem);
  brak wartości domyślnych parametrów eksperymentu w sygnaturach; mm i mm/rok; ujemne = osiadanie / oddalanie od
  satelity; EPSG:3035 dla EGMS; dokumentacja i komentarze po polsku, nazwy w kodzie i osie wykresów po angielsku.

## 1. Moduły

| Plik | KROK | Zawartość |
|---|---|---|
| `step_04_egms_aoi.py` | 4 | EGMS dla obszaru: wyszukanie L2B i L3 w prostokącie, plan pobrania z kontrolą miejsca na Dysku, czytnik L3, komórka L3 przy punkcie, mapa prędkości L3 (i opcjonalnie L2b) |
| `step_05_colab_run.py` | 5 | sterowanie: `CHECK_CONFIG`, `setup_runtime`, `run_task`, rejestr `gwl_*`, bramki zatwierdzeń, zadania `task_*`, `run_summary.md`, `--selftest` |
| `step_06_ground.py` | 6 | pomiary naziemne: reguła wyboru stacji GNSS dla obszaru bez warunku prędkości; niwelacja NRW (czytnik, epoki, porównanie z L3 i z L2b po rozkładzie asc/desc) |
| `step_07_monitoring.py` | 7 | wspólny format szeregów, próbkowanie 6/12 dni, „ile czasu do wykrycia”, wykresy pokazu |
| `step_08_hyp3_mintpy.py` | 8 | etap B: wyszukanie burstów (asf_search), pary SBAS, zlecenia HyP3 bez duplikatów, pobranie, przycięcie, szablon i uruchomienie MintPy, szeregi w punktach, dowiązanie do EGMS |
| `build_colab_monitoring.py` → `notebooks/EGMS_Monitoring.ipynb` | — | notatnik etapu A i B wywołujący `run_task`; generowany |

Notatnik E1 zostaje osobno jako zapis wyniku zarejestrowanego przed obliczeniami (odstępstwo od „jednego notatnika”
w `CLAUDE.md`, do akceptacji autora).

## 2. Wspólne struktury danych

### 2.1 Punkty naziemne (`sites`)

`data/03_Extracts/<region>/sites.csv`: `site` (identyfikator: kod stacji GNSS albo numer reperu), `site_type`
(`gnss` / `benchmark`), `group` (`osiadająca` / `stabilna` / `inna` dla GNSS; `benchmark` dla reperów),
`lat_deg`, `lon_deg`, `x_3035`, `y_3035`, `source`. Kolumny `site`, `x_3035`, `y_3035` pozwalają użyć
`step_02.extract_points` bez zmian.

### 2.2 Format długi szeregów (`timeseries_long`)

`data/03_Extracts/<region>/timeseries_long.csv.gz` — jedno źródło na wiersz:

| kolumna | opis |
|---|---|
| `region`, `source` | `groningen` / `nrw_west`; `EGMS_L2b_2020_2024`, `EGMS_L3U_2020_2024`, `GNSS_NGL_LOS`, `GNSS_NGL_U`, `LEVELLING_NRW`, `S1_HYP3_MINTPY` |
| `site`, `track`, `direction` | punkt naziemny; ścieżka i kierunek (puste dla pionu) |
| `component` | `LOS` / `U` |
| `los_east`, `los_north`, `los_up` | wektor LOS użyty do rzutu (dla `U`: 0, 0, 1) |
| `date`, `disp_mm` | data (UTC, dzień), przemieszczenie [mm] względem `ref_date` |
| `ref_date`, `reference` | data i punkt/obszar odniesienia (`absolute` albo identyfikator) |
| `n_points` | liczba punktów EGMS / pikseli w medianie; NaN dla GNSS i niwelacji |

Wszystkie wykresy i analizy `step_07` czytają tylko ten format.

## 3. `CHECK_CONFIG` (w `step_05_colab_run.py`)

Sekcje z kluczem `approved` (data zatwierdzenia albo `None`). Zadanie korzystające z sekcji wywołuje
`require_approved(cfg, section)` — `None` = `RuntimeError` z nazwą decyzji. Wartość `None` parametru = decyzja
nieustalona = wyjątek przy użyciu. **[p]** = propozycja do zatwierdzenia.

```text
project:    project_dir (Drive), token_path (CLMS), earthdata_path (secrets/earthdata.json), downloaded_by
egms:       release '2020-2024', levels ['L2B','L3'], l3_product_types ['ORTHO-UP'], raw_dir
            'data/01_Raw_EGMS/2020_2024', download_pause_s 15, drive_margin_gb [p] 1.0, chunksize 200000,
            l2b_aoi_map [p] False                                   approved '2026-10-11'
regions.groningen: cause, aoi_lonlat (5.8, 52.9, 7.3, 53.6) (jak E1), control_lonlat (4.8, 52.4, 8.3, 54.0),
            gnss_rule 'subsiding_and_stable' (reguła E1), levelling None          approved [p]
regions.nrw_west: cause, aoi_lonlat [p] (5.9, 50.7, 7.0, 51.3) (do potwierdzenia z ryc. 14–15 Even 2024; Epe
            leży poza obszarem), gnss_rule [p] 'all_quality', levelling {urls (do potwierdzenia), crs_epsg [p] 25832,
            epoch_rule [p] 'first_last_in_release', min_epoch_span_yr [p] 1.0, reference [p] None (decyzja)}
                                                                                   approved None
gnss:       midas_url, frame 'EU', t_first_max 2020.0, t_last_min 2024.25, svu_max_mm_yr 1.0, max_steps 2,
            vu_subsiding_max -2.0, vu_stable_abs_max 1.0, n_stable 8, n_stable_min 3       approved [p]
method:     jak E1: extract_radius_m 200, radius_main_m 100, radii_m [100, 200], min_points 3,
            gnss_half_window_days 6, velocity_model 'linear_annual', min_overlap 0.85, conv_tol 0.01,
            duplicate_dist_m 1.0; L3: l3_cell_m 100, l3_min_points 1                     approved [p]
thresholds: gnss_l2b {abs_dv_mm_yr 1.5, share_within 0.80, series_std_mm 5.0, stable_abs_v_mm_yr 1.5,
            k3_definition [p] None ('abs_v_egms' jak E1 albo 'abs_dv')}; gnss_l3u {abs_dv_mm_yr [p] 1.5,
            share_within [p] 0.80}; levelling_l3u {median_abs_dh_mm [p] 5.0, sign_min_signal_mm [p] 6.0,
            sign_agreement [p] 0.90, stable_max_lev_mm [p] 2.0, stable_abs_dh_mm [p] 5.0,
            velocity_bias_mm_yr [p] 1.5}                                                   approved None
monitoring: window_starts [p] ['2020-01-01', '2022-01-01'], windows_months [p] [3, 6, 9, 12, 18, 24, 36, 48, 60],
            model_short [p] 'linear' (< 12 mies.), model_long 'linear_annual', detect_k_sigma [p] 2.0,
            sigma_method [p] 'ar1', s1b_end_date '2021-12-23' (do potwierdzenia)          approved None
hyp3:       job_type [p] 'INSAR_ISCE_MULTI_BURST', looks [p] '20x4', apply_water_mask [p] True, polarization 'VV',
            start [p] '2024-01-01', overlap_end '2024-12-31', end None (podać jawnie), n_neighbors [p] 3,
            max_dt_days [p] 48, tracks 'from_egms_l2b', max_credits [p] None, raw_dir 'data/01_Raw_InSAR/hyp3',
            mintpy {troposphere [p] 'no', min_temp_coh [p] 0.7, topographic_residual [p] True,
                    reference_rule [p] 'stable_gnss_min_abs_vu', window_px [p] 3}           approved None
```

## 4. Interfejsy

### 4.1 `step_04_egms_aoi.py`

```python
def bbox_query(aoi_lonlat: tuple, level: str, release: str, product_type: str | None) -> dict
    # {"id": None, "bbox": [[lon0, lat0], [lon1, lat1]], "levels": [level], "releases": [release]} (+ "productType")
    # aoi > 5° x 5° -> ValueError (limit API, F5)
def search_aoi(session, headers, endpoint, aoi_lonlat, level, release, product_type) -> tuple[dict, pd.DataFrame]
    # step_01.search_egms + step_01.hits_table; pusty wynik -> RuntimeError
def plan_download(hits: pd.DataFrame, out_dir: Path, free_bytes: int, margin_bytes: int) -> pd.DataFrame
    # kolumny hits + status ('existing' rozmiar zgodny / 'missing' / 'partial') + need_bytes;
    # suma brakujących > free_bytes - margin_bytes -> RuntimeError z liczbami (GB)
def drive_free_bytes(path: Path) -> int            # shutil.disk_usage
def l3_csv_name(zip_path: Path) -> str             # jedyny CSV w zipie L3; inny stan -> ValueError
def read_l3_aoi(zip_path, aoi_3035: tuple, chunksize: int, with_dates: bool) -> pd.DataFrame
    # komórki L3 w prostokącie EPSG:3035 (x0, y0, x1, y1); wymagane kolumny L3_REQUIRED; with_dates=False -> tylko
    # pid, easting, northing, mean_velocity, mean_velocity_std (mapa); True -> + kolumny dat
def l3_cells_at_sites(zip_paths: list, sites: pd.DataFrame, cell_m: float, chunksize: int) -> pd.DataFrame
    # komórka zawierająca każdy punkt (|dx|, |dy| <= cell_m/2); kolumny komórki + site, distance_m, source_file,
    # los_east=0, los_north=0, los_up=1, track='L3', direction='vertical'; >1 komórka -> ValueError;
    # brak komórki -> brak wiersza (raportowane przez wywołującego jako status)
def extract_l2b_velocity_map(zip_path, aoi_3035, chunksize) -> pd.DataFrame   # pid, easting, northing, mean_velocity
def aoi_lonlat_to_3035(aoi_lonlat) -> tuple        # prostokąt obejmujący (pyproj)
def _selftest() -> None                            # bez sieci: atrapa search, zip L2B i L3, plan z brakiem miejsca
```

### 4.2 `step_06_ground.py`

```python
def select_stations_aoi(midas, aoi_lonlat, t_first_max, t_last_min, svu_max_mm_yr, max_steps,
                        vu_subsiding_max, vu_stable_abs_max) -> pd.DataFrame
    # reguła 'all_quality': wszystkie stacje w obszarze spełniające jakość; group wg vu: 'osiadająca' (vu <= max),
    # 'stabilna' (|vu| <= abs_max), 'inna'; 0 stacji -> pusta tabela + komunikat (GNSS "jeśli są"), nie wyjątek
def read_nrw_points(path) -> pd.DataFrame          # Punktliste: ';', przecinek dziesiętny; Punktkennzeichen, Ostwert, Nordwert, Höhe
def read_nrw_timeseries(path) -> pd.DataFrame      # Punktliste mit Zeitfolge: Punktkennzeichen; Messungsdatum (dd.mm.rrrr); Höhe
    # nazwy kolumn sprawdzane; brak -> KeyError z listą dostępnych
def levelling_long(points, series, crs_epsg, aoi_lonlat) -> pd.DataFrame
    # benchmark_id, x_3035, y_3035, lat_deg, lon_deg, epoch_date, height_m; tylko repery w obszarze
def epochs_in_release(lev, release_start, release_end, rule, min_span_yr) -> pd.DataFrame
    # benchmark_id, t1, t2 (rule 'first_last_in_release': pierwsza i ostatnia epoka w oknie wydania, odstęp >= min)
def read_at_epochs(series: pd.Series, epochs, method: str) -> pd.Series     # z prototypu; bez ekstrapolacji
def compare_levelling(lev, epoch_pairs, egms_long_u: pd.DataFrame, reference: dict, method: str) -> pd.DataFrame
    # Δh niwelacji i EGMS (pion) względem odniesienia: {"type": "absolute"} albo {"type": "stable_group", "ids": [...]};
    # wiersz na reper: dh_lev_mm, dh_egms_mm, diff_mm, v_lev_mm_yr, v_egms_mm_yr, status ('ok' / powód NaN)
def vertical_from_asc_desc(los_asc: pd.Series, vec_asc: tuple, los_desc: pd.Series, vec_desc: tuple,
                           epochs) -> pd.DataFrame
    # L2b -> pion w epokach: interpolacja obu szeregów do epok, układ 2x2 dla (E, U) przy założeniu N = 0
    # (założenie jawnie w docstringu i w wyniku); osobliwy układ -> ValueError
def summarize_levelling(res, th: dict) -> pd.DataFrame          # kryteria jak T2 + bias prędkości; tabela kryteriów
def _selftest() -> None
```

### 4.3 `step_07_monitoring.py`

```python
LONG_COLUMNS = [...]                               # sekcja 2.2
def validate_long(df) -> pd.DataFrame              # kolumny, typy, duplikaty (source, site, track, component, date) -> błąd
def egms_points_to_long(points, date_cols, region, source, radius_m, min_points) -> pd.DataFrame
    # mediana punktów w dacie dla (site, track); los_* = średnia punktów; ref_date = pierwsza data
def gnss_to_long(gnss: pd.DataFrame, site, region, los_vec: tuple, component, track, direction) -> pd.DataFrame
def sampling_table(dates: pd.DatetimeIndex) -> pd.DataFrame       # date, gap_days; podsumowanie 6/12/inne
def subsample(series: pd.Series, every_k: int) -> pd.Series       # symulacja rzadszych przelotów
def velocity_realistic(dates, y_mm, model, sigma_method) -> dict  # v, sigma_formal, rho1, n_eff, sigma_real
def detection_curve(series: pd.Series, start, windows_months, model_short, model_long, sigma_method, k) -> pd.DataFrame
    # window_months, end_date, n, v_mm_yr, sigma_real, detected (|v| > k*sigma_real)
def time_to_detection(curve) -> float | None       # pierwsze okno stale wykrywające (wszystkie dłuższe też), None
def plot_l3_map(cells, sites, title) -> Figure
def plot_series_long(long_df, site, title, s1b_end) -> Figure
def plot_sampling(table_by_track) -> Figure
def plot_detection(curves: dict[str, pd.DataFrame], title) -> Figure
def _selftest() -> None                            # syntetyczne szeregi o znanej prędkości i szumie AR(1)
```

### 4.4 `step_08_hyp3_mintpy.py`

```python
def load_earthdata_credentials(path) -> dict       # {"username","password"} albo {"token"}; nic nie drukuje
def hyp3_client(creds) -> "hyp3_sdk.HyP3"
def search_bursts(aoi_wkt, relative_orbit, start, end, polarization) -> pd.DataFrame
    # asf_search.search(dataset=SLC_BURST, ...): scene_name, full_burst_id, start_time, date, platform,
    # flight_direction, relative_orbit, footprint_wkt
def bursts_covering_points(bursts, points_lonlat: pd.DataFrame) -> list[str]
def acquisition_stack(bursts, burst_ids) -> pd.DataFrame          # date -> scene_names (lista); daty niepełne usunięte z logiem
def sbas_pairs(dates, n_neighbors, max_dt_days) -> list[tuple]
def prepare_jobs(stack, pairs, job_type, looks, apply_water_mask, name) -> list[dict]   # HyP3.prepare_* (classmethod)
def submit_missing(hyp3, jobs, name, max_credits) -> pd.DataFrame
    # find_jobs(name=name) -> pomija istniejące (te same granule); check_credits; submit_prepared_jobs
def download_succeeded(hyp3, name, out_dir, manifest_path, project_dir, downloaded_by) -> pd.DataFrame
    # Job.download_files -> rozpakowanie -> wpis w manifeście (SHA-256 zipa); istniejące pomijane
def clip_to_common_overlap(product_dirs, layers, out_dir) -> pd.DataFrame
    # rasterio; ten sam CRS i rozmiar piksela albo ValueError; *_<layer>_clip.tif + kopia <product>.txt
def write_mintpy_template(path, clip_dir, reference_lalo, mcfg) -> Path
def expected_timeseries_name(mcfg) -> str          # zgodnie z krokami MintPy (troposfera, deramp, demErr)
def run_mintpy(template, work_dir) -> Path         # subprocess smallbaselineApp.py, check=True
def los_unit_vector(inc_deg, az_deg) -> tuple      # konwencja MintPy (geometryGeo.h5); kontrola z wektorem EGMS
def mintpy_series_at_points(ts_h5, geom_h5, points, window_px) -> pd.DataFrame    # format długi, mm, LOS
def align_to_reference(own_long, egms_long, overlap_start, overlap_end, half_window_days) -> tuple[pd.DataFrame, pd.DataFrame]
def _selftest() -> None                            # atrapy asf_search i HyP3, syntetyczne GeoTIFF i h5
```

### 4.5 `step_05_colab_run.py` — zadania

`task_select_gnss`, `task_gnss_download`, `task_levelling`, `task_egms_search`, `task_egms_download(confirm_mb)`,
`task_extract`, `task_checks`, `task_compare_gnss`, `task_compare_levelling`, `task_monitoring_archive`,
`task_figures`, `task_hyp3_plan`, `task_hyp3_submit(confirm_jobs)`, `task_hyp3_download`, `task_mintpy`,
`task_hyp3_compare`, `task_summary`. Każde przyjmuje `(rt, cfg, region)` lub `(rt, cfg)` i zwraca słownik
kontraktu `run_task` (`registry`, `message`, `skipped`). Pobranie wymaga podania rozmiaru z planu
(`confirm_mb` = suma z `task_egms_search`, zaokrąglona) — ochrona przed przypadkowym pobraniem.
`run_task` zapisuje błąd w `gwl_runs` i **zgłasza go dalej** (błąd głośny).

## 5. Testy

Każdy moduł: `python step_0N_*.py --selftest` bez sieci. Notatnik: `tests/monitoring_harness/` (atrapy EGMS
bbox L2B/L3, NGL, NRW, asf_search, HyP3; atrapa `smallbaselineApp.py` na PATH). Wartości testowe nie są wynikiem.

## 6. Stan po implementacji: decyzje autora i znane luki (2026-10-11)

Zatwierdzone w `CHECK_CONFIG`: `egms` (wydanie 2020–2024, L2b + L3 pion, `search_area` = obszar + punkty naziemne) i
`regions.groningen` (obszar E1). Pozostałe sekcje mają `approved = None` — notatnik zatrzymuje się na pierwszej z nich.

Do decyzji autora:
1. `regions.nrw_west`: prostokąt obszaru (ryc. 14–15 Even 2024), adresy plików niwelacji, kodowanie, EPSG, odniesienie.
2. `gnss`: reguła E1 z oknem 2020.0–2024.25; `method`: parametry E1.
3. `thresholds`: w tym `gnss_l2b.k3_definition` (`abs_v_egms` jak E1 albo `abs_dv`; oba z progiem 1,5 mm/rok).
4. `monitoring`: okna, próg 2σ (bez znaku: istotne wypiętrzenie też liczy się jako „wykrycie”), AR(1).
5. `hyp3`: data końca, limit kredytów i koszt zlecenia, tolerancja kontroli LOS, deramp, pływy skorupy, troposfera.
6. Sformułowanie wniosku, gdy K1 niepoliczalne: „NIEROZSTRZYGNIĘTE” (E1 bez zmian).
7. `data/00_Metadata/MANIFEST.csv` jest w gicie i rośnie na klonie na Dysku: który manifest jest źródłem prawdy.
8. Migawka MIDAS: notatnik używa najnowszej migawki z Dysku; nowsza = świadoma decyzja (może zmienić wybór stacji).

Znane luki: porównanie niwelacji z L2b (rozkład asc/desc, `step_06.vertical_from_asc_desc`) nie jest podpięte do zadania;
w trybie bez tokenu trzeba skopiować `egms_plan_<region>.csv` razem z wycinkami; rejestr `gwl_*` tylko dopisuje.
