"""
================================================================================
EGMS Check - KROK 5: STEROWANIE Z NOTATNIKA, REJESTR NA DYSKU I ZADANIA
================================================================================
Architektura (jak AgriWatch, 1_geoworldlook-agriscreen/step_05_colab_run.py): kod na GitHub -> klon repozytorium
na Dysku Google (MyDrive/GeoWorldLook/egmscheck) -> obliczenia w Colab -> tabele rejestru gwl_* na Dysku.
Interfejs według docs/plans/Plan_v2_implementacja.md (sekcje 3 i 4.5); cel: docs/plans/Plan_v2_pokaz_EGMS_monitoring.md.

  I.   Środowisko i rejestr (przeniesione z AgriWatch): setup_runtime (bez GEE; instalacja brakujących pakietów
       tylko w Colab), ensure_packages (etap B: hyp3_sdk, asf_search, mintpy, rasterio, h5py + kontrola GDAL/osgeo),
       REGISTRY_SCHEMA (gwl_runs jak w AgriWatch; gwl_sites i gwl_validation_metrics dla EGMS), registry_read,
       registry_upsert (upsert po kluczu głównym), run_task, run_history, registry_summary.
       ZMIANA względem AgriWatch: run_task zapisuje błąd zadania w gwl_runs i ZGŁASZA GO DALEJ (CLAUDE.md, zasada 3:
       błąd głośny; wynik zadania, które się nie powiodło, nie może wyglądać jak prawdziwy).
  II.  CHECK_CONFIG (jedno miejsce konfiguracji, Plan_v2 sekcja 3) z kluczem 'approved' w każdej sekcji
       eksperymentu; require_approved zatrzymuje zadanie, gdy sekcja nie jest zatwierdzona (decyzje autora,
       CLAUDE.md zasady 2, 4 i 9); approvals_table pokazuje stan zatwierdzeń i otwarte decyzje (wartości None).
  III. Zadania etapu A (pokaz EGMS 2020-2024, Groningen i zachodnia NRW), każde przez run_task:
         task_select_gnss       stacje GNSS: reguła E1 (step_01.select_stations) albo 'all_quality' (step_06)
         task_gnss_download     dobowe szeregi NGL tenv3 (step_01.download_file, manifest)
         task_levelling         niwelacja NRW: pobranie (step_01.download_file) i czytniki step_06
         task_egms_search       wyszukanie L2B + L3 (step_04.search_plan) i plan pobrania z kontrolą miejsca
         task_egms_download     pobranie po potwierdzeniu rozmiaru (confirm_mb) przez step_04.sync_files
         task_extract           wycinki L2b (step_04.extract_points_l2b), komórki L3 przy punktach i mapa L3 (step_04)
         task_checks            kontrole A1-A3, A5 (step_02) i siatka L3 (step_04.l3_grid_offsets); błąd = stop
         task_compare_gnss      EGMS L2b (LOS) i L3 (U) kontra GNSS (step_03), werdykt K1-K4
         task_compare_levelling EGMS L3 (U) kontra niwelacja (step_06), kryteria N1-N4
         task_levelling_egms_search / task_levelling_egms_download / task_levelling_extract /
         task_compare_levelling_check
                                drugie wydanie EGMS tylko do porównania z niwelacją (regions.<r>.levelling.egms_check,
                                np. 2019-2023, tylko L3 pion): to samo wyszukanie, plan, potwierdzenie i pobranie co dla
                                wydania głównego, komórki L3 przy reperach, kryteria N1-N4 i podział informacyjny
                                (niecki według niwelacji, odległość do najbliższej stacji GNSS NGL), rycina Δh
         task_monitoring_archive format długi, próbkowanie 6/12 dni, krzywe wykrycia (step_07)
         task_figures           ryciny pokazu (step_07) i wykres rozrzutu prędkości (step_03)
  IV.  Zadania etapu B (ASF HyP3 + MintPy, step_08): task_hyp3_plan, task_hyp3_submit (po potwierdzeniu liczby
       zleceń), task_hyp3_download, task_mintpy, task_hyp3_compare.
  V.   task_summary: run_summary.md i run_summary.json (wersje bibliotek, konfiguracja, wydanie EGMS, commit,
       zatwierdzenia, tabele werdyktów, ostatnie uruchomienia; CLAUDE.md, zasada 7).
  VI.  --selftest bez sieci: rejestr (nowe / zmienione / bez zmian), run_task zapisuje błąd i zgłasza go dalej,
       require_approved, blokady confirm_mb i confirm_jobs; zapis wyłącznie do katalogu tymczasowego.

Decyzje integracji (do akceptacji autora; wartości nowych kluczy CHECK_CONFIG oznaczone [p] albo None):
  - obszar wyszukania EGMS: egms.search_area 'aoi_plus_sites' = prostokąt obszaru rozszerzony o punkty
    naziemne (reguła E1 bierze stacje stabilne z okolicy, poza obszarem; bez rozszerzenia nie miałyby danych EGMS);
  - porównanie L2b z GNSS i szeregi L2b: daty jednej ścieżki = kolumny dat z wartościami dla punktów tej ścieżki
    (E1 podawał sumę dat wszystkich ścieżek; daty innych ścieżek i tak były NaN);
  - L3 przy punkcie: promień = cell_m * sqrt(2) / 2 (każda komórka zawierająca punkt), min_points = l3_min_points;
  - werdykt L3: zdefiniowane są tylko progi K1 (thresholds.gnss_l3u); pozostałe wiersze step_03.verdict są
    informacyjne (bez progu, 'spełnione' = None), wniosek tylko z K1;
  - K3 'abs_dv' (thresholds.gnss_l2b.k3_definition) = max |dv| na stacjach stabilnych (step_03.verdict liczy
    wariant E1 'abs_v_egms'); None = decyzja nieustalona = wyjątek;
  - werdykt L2b bez wiersza K1 (brak par stacja osiadająca x ścieżka 'ok' z A6) = 'NIEROZSTRZYGNIĘTE' zamiast
    step_03.overall (które bez K1 zwraca 'NIE POTWIERDZONE ... różni się ponad progi');
  - MIDAS: najnowsza migawka midas_*.IGS.txt z Dysku zamiast pobierania przy każdym uruchomieniu (wybór stacji
    nie zmienia się między przebiegami); nowszy stan MIDAS = decyzja autora;
  - niwelacja: okno epok = rzeczywisty zakres dat szeregów EGMS L3 (pierwsza i ostatnia data), nie daty z nazwy
    wydania; format długi niwelacji (LEVELLING_NRW) budowany tutaj (step_06 go nie tworzy);
  - GNSS w formacie długim: poziom odniesienia = mediana dób +-gnss_half_window_days wokół daty odniesienia szeregu
    EGMS (jak step_03.gnss_at_dates), ref_date = data EGMS (step_07.gnss_to_long odnosi do jednej, pierwszej doby);
  - ryciny rozrzutu (step_03.plot_velocity_scatter) tylko dla grup 'osiadająca' i 'stabilna' (grupa 'inna' z reguły
    'all_quality' jest pomijana z komunikatem, bo step_03 nie ma dla niej opisu);
  - przykłady szeregów (monitoring.example_rule [p] 'max_subsidence_median_stable', Plan_v2 sekcja 7 pkt 5):
    stacja o największym osiadaniu, stacja o medianie osiadania, stacja stabilna o najmniejszym |vu| (reguła E1),
    a dla niwelacji to samo według v_lev.

Konwencje: przemieszczenia w mm, prędkości w mm/rok, ujemne = osiadanie / oddalanie od satelity; EGMS EPSG:3035,
GNSS stopnie WGS84, niwelacja NRW w crs_epsg z konfiguracji. Ścieżki w CHECK_CONFIG są względne wobec PROJECT_DIR.
Parametry eksperymentu pochodzą wyłącznie z CHECK_CONFIG; sygnatury zadań nie mają wartości domyślnych.

Literatura i źródła: docs/evidence/F4_metodyka.md, docs/evidence/F5_zrodla_danych.md,
docs/plans/Plan_v1_kryteria_akceptacji.md, docs/migracja/09_audyt_po_migracji.md (cicho pominięte pary N3b);
Koudogbo i in. 2025 (walidacja EGMS), Even i in. 2024 (EGMS kontra niwelacja NRW).
================================================================================
"""

import argparse
import copy
import importlib
import importlib.util
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("EGMSCheck_Run")

HTTP_TIMEOUT_S = 300                     # limit oczekiwania na serwer (jak step_01.download_file)
HYP3_JOB_PREFIX = "egmscheck"            # nazwy zleceń HyP3 są publiczne: bez danych osobowych (hyp3_sdk)
NRW_LICENCE = "Datenlizenz Deutschland - Zero - Version 2.0 (Geobasis NRW; F5, sekcja 5)"
STAGE_A_PACKAGES = ["pyjwt", "pyproj", "matplotlib", "requests", "cryptography"]
STAGE_B_PACKAGES = ["hyp3_sdk", "asf_search", "mintpy", "rasterio", "h5py", "shapely"]
PIP_TO_MODULE = {"pyjwt": "jwt", "pyproj": "pyproj", "matplotlib": "matplotlib", "requests": "requests",
                 "cryptography": "cryptography", "hyp3_sdk": "hyp3_sdk", "asf_search": "asf_search",
                 "mintpy": "mintpy", "rasterio": "rasterio", "h5py": "h5py", "shapely": "shapely"}
VERSION_PACKAGES = ["numpy", "pandas", "matplotlib", "pyproj", "requests", "PyJWT", "shapely", "rasterio", "h5py",
                    "asf_search", "hyp3_sdk", "mintpy"]
SITES_COLUMNS = ["site", "site_type", "group", "lat_deg", "lon_deg", "x_3035", "y_3035", "source", "vu_mm_yr",
                 "svu_mm_yr", "t_first", "t_last", "n_steps", "dist_km"]
L2B_EXTRA = ["site", "distance_m", "source_file", "track", "direction"]
GNSS_REFERENCE = "GNSS_NGL"
LEVELLING_REFERENCE = "LEVELLING_NRW"
LEVELLING_REFERENCE_REL = "LEVELLING_NRW_STABLE_GROUP"     # wariant względny (oba zbiory względem grupy stabilnej)
GNSS_METRICS = ["v_egms", "v_gnss_los", "dv", "sigma_v_egms", "sigma_v_gnss", "series_diff_std", "corr",
                "frac_release", "frac_dates"]
LEVELLING_METRICS = ["dh_lev_mm", "dh_egms_mm", "diff_mm", "v_lev_mm_yr", "v_egms_dh_mm_yr"]

# ==============================================================================
# I. ŚRODOWISKO I REJESTR NA DYSKU GOOGLE (przeniesione z AgriWatch step_05_colab_run.py)
# ==============================================================================
# Rejestr = pliki CSV w data/registry/ (w Colab: na Dysku Google). Nazwy tabel i kolumn są nazwami w przyszłej
# bazie danych, "keys" to klucz główny. gwl_runs bez zmian względem AgriWatch.
REGISTRY_SCHEMA: Dict[str, Dict[str, List[str]]] = {
    "gwl_sites": {
        "keys": ["region", "site"],
        "columns": ["region", "site", "site_type", "group", "lat_deg", "lon_deg", "x_3035", "y_3035", "source",
                    "run_id", "updated_at"],
    },
    "gwl_validation_metrics": {
        # Bez run_id w kluczu: metryka policzona ponownie zastępuje wiersz, run_id wskazuje uruchomienie.
        "keys": ["region", "product", "reference", "site", "track", "radius_m", "metric"],
        "columns": ["region", "product", "reference", "site", "track", "radius_m", "metric", "value", "n", "status",
                    "run_id"],
    },
    "gwl_runs": {
        "keys": ["run_id"],
        "columns": ["run_id", "task", "started_at", "finished_at", "duration_s", "status", "git_commit",
                    "pipeline_version", "params_json", "n_new_rows", "message"],
    },
}

# Kolumny techniczne: ich zmiana nie oznacza zmiany danych (wiersz z tą samą wartością nie jest nadpisywany)
_META_COLUMNS = {"run_id", "ingested_at", "updated_at"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(project_dir: str, *args: str) -> str:
    """
    Wynik polecenia git albo jawny napis 'git-unavailable: <powód>' (brak programu git, przekroczony czas,
    kod błędu). Łapiemy wyłącznie OSError i TimeoutExpired; żadnego except Exception.
    """
    try:
        out = subprocess.run(["git", "-C", project_dir, *args], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"git-unavailable: {type(e).__name__}: {e}"
    if out.returncode != 0:
        return f"git-unavailable: git {' '.join(args)} -> kod {out.returncode}: {(out.stderr or out.stdout).strip()}"
    return out.stdout.strip()


def _git_commit(project_dir: str) -> str:
    """Skrót commita + '+dirty', jeśli w repozytorium są niezatwierdzone zmiany w śledzonych plikach."""
    if not os.path.exists(os.path.join(project_dir, ".git")):
        return "no-git"
    commit = _git(project_dir, "rev-parse", "--short", "HEAD")
    if commit.startswith("git-unavailable"):
        return commit
    dirty = _git(project_dir, "status", "--porcelain", "--untracked-files=no")
    if dirty.startswith("git-unavailable"):
        return f"{commit}+{dirty}"
    return commit + ("+dirty" if dirty else "")


def _install_missing(packages: List[str], in_colab: bool) -> List[str]:
    """
    Brakujące pakiety (nazwy pip, moduł z PIP_TO_MODULE): w Colab pip install, poza Colab ImportError z poleceniem
    (środowisko lokalne przygotowuje użytkownik; nic nie instalujemy po cichu). Zwraca listę zainstalowanych.
    """
    def missing_now():
        return [p for p in packages if importlib.util.find_spec(PIP_TO_MODULE.get(p, p.replace("-", "_"))) is None]
    missing = missing_now()
    if not missing:
        return []
    if not in_colab:
        raise ImportError(f"Brak pakietów {missing}; poza Colab zainstaluj je ręcznie: pip install {' '.join(missing)}")
    logger.info(f"Instalacja: {' '.join(missing)}")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *missing], check=True)
    importlib.invalidate_caches()
    still = missing_now()
    if still:
        raise ImportError(f"Po pip install nadal brak modułów dla {still}")
    return missing


def setup_runtime(project_dir: str, packages: List[str]) -> Dict[str, Any]:
    """
    Przygotowuje środowisko i zwraca słownik `rt` przekazywany do zadań. Dysk Google montuje, a repozytorium
    klonuje / aktualizuje komórka notatnika przed importem tego modułu (kod leży na Dysku), więc tu nie ma git pull.
    Kroki: logowanie -> pakiety (instalacja brakujących tylko w Colab; poza Colab brak = ImportError) -> katalog
    rejestru -> commit kodu. Bez GEE (AgriWatch inicjalizował Earth Engine; EGMS Check go nie używa).
    """
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    project_dir = os.path.abspath(project_dir)
    if not os.path.isdir(project_dir):
        raise FileNotFoundError(f"Brak katalogu projektu {project_dir}")
    in_colab = "google.colab" in sys.modules
    installed = _install_missing(list(packages), in_colab)
    rt = {
        "PROJECT_DIR": project_dir,
        "DATA_DIR": os.path.join(project_dir, "data"),
        "REGISTRY_DIR": os.path.join(project_dir, "data", "registry"),
        "IN_COLAB": in_colab,
        "GIT_COMMIT": _git_commit(project_dir),
        "INSTALLED": installed,
    }
    os.makedirs(rt["REGISTRY_DIR"], exist_ok=True)
    logger.info(f"Środowisko gotowe: {project_dir} (commit {rt['GIT_COMMIT']}, Colab={in_colab})")
    return rt


def _check_gdal() -> None:
    """MintPy prep_hyp3 wymaga GDAL dla Pythona (moduł osgeo), którego pip install mintpy nie instaluje."""
    if importlib.util.find_spec("osgeo") is None:
        raise ImportError("Brak modułu osgeo (GDAL dla Pythona), wymaganego przez MintPy (prep_hyp3, wczytanie "
                          "GeoTIFF HyP3). Colab: !apt-get -qq install -y python3-gdal albo "
                          "!pip install GDAL==$(gdal-config --version); lokalnie: conda install -c conda-forge gdal. "
                          "Potem uruchom ponownie środowisko wykonawcze.")


def ensure_packages(names: List[str]) -> Dict[str, Any]:
    """
    Pakiety etapu B (np. STAGE_B_PACKAGES): w Colab instalacja brakujących, poza Colab brak = ImportError.
    Gdy na liście jest mintpy: kontrola GDAL (osgeo) i programu smallbaselineApp.py na PATH, z instrukcją.
    """
    in_colab = "google.colab" in sys.modules
    installed = _install_missing(list(names), in_colab)
    if "mintpy" in names:
        _check_gdal()
        if shutil.which("smallbaselineApp.py") is None:
            raise FileNotFoundError("smallbaselineApp.py nie ma na PATH mimo modułu mintpy: sprawdź instalację MintPy "
                                    "(pip install mintpy instaluje skrypty w katalogu bin środowiska).")
    print(f"Pakiety etapu B gotowe: {list(names)}; zainstalowane teraz: {installed or 'brak'}")
    return {"installed": installed}


def _registry_path(rt: Dict[str, Any], table: str) -> str:
    if table not in REGISTRY_SCHEMA:
        raise KeyError(f"Nieznana tabela rejestru: {table}. Dostępne: {sorted(REGISTRY_SCHEMA)}")
    return os.path.join(rt["REGISTRY_DIR"], f"{table}.csv")


def registry_read(rt: Dict[str, Any], table: str) -> pd.DataFrame:
    """
    Czyta tabelę rejestru; brak pliku = pusta tabela z kolumnami ze schematu. Identyfikatory punktów i ścieżek
    (site, track) jako tekst: numery reperów z zerem wiodącym (np. 0450600001) przeczytane jako liczby traciłyby zero,
    a klucz nie zgadzałby się z nowym wierszem (duplikaty przy każdym uruchomieniu).
    """
    path = _registry_path(rt, table)
    cols = REGISTRY_SCHEMA[table]["columns"]
    if not os.path.exists(path):
        return pd.DataFrame(columns=cols)
    df = pd.read_csv(path, low_memory=False, dtype={c: str for c in ("site", "track") if c in cols})
    return df.reindex(columns=cols)


def _canon(df: pd.DataFrame) -> pd.DataFrame:
    """Tekstowa postać kanoniczna (porównanie kluczy i wartości niezależne od typu po odczycie CSV)."""
    def one(v: Any) -> str:
        if v is None or v is pd.NA or v is pd.NaT or (isinstance(v, float) and not np.isfinite(v)):
            return ""
        if isinstance(v, (float, np.floating)):
            return str(int(v)) if float(v).is_integer() else f"{float(v):.10g}"
        if isinstance(v, (int, np.integer, bool, np.bool_)):
            return str(int(v))
        if isinstance(v, str):
            return "" if v.lower() == "nan" else v
        return str(v)
    return df.apply(lambda col: col.map(one))


def registry_upsert(rt: Dict[str, Any], table: str, df: pd.DataFrame) -> Dict[str, int]:
    """
    Dopisuje wiersze do tabeli rejestru według klucza głównego:
      - nowy klucz -> wiersz dopisany,
      - istniejący klucz ze zmienioną wartością -> wiersz zastąpiony,
      - istniejący klucz bez zmian -> zostaje stary wiersz (z pierwotnym run_id i updated_at).
    Zapis atomowy (plik tymczasowy + zamiana). Zwraca liczniki {"new", "changed", "unchanged"}.
    """
    keys = REGISTRY_SCHEMA[table]["keys"]
    cols = REGISTRY_SCHEMA[table]["columns"]
    missing = [k for k in keys if k not in df.columns]
    if missing:
        raise ValueError(f"{table}: brak kolumn klucza {missing}")
    extra = [c for c in df.columns if c not in cols]
    if extra:
        logger.warning(f"{table}: kolumny spoza schematu pominięte: {extra}")
    new = df.reindex(columns=cols)
    new_c = _canon(new)
    new_key = new_c[keys].agg("\x1f".join, axis=1)
    dup = new_key.duplicated(keep="last")
    if dup.any():
        logger.warning(f"{table}: {int(dup.sum())} zduplikowanych kluczy w nowych danych — zostaje ostatni.")
        new, new_c, new_key = new[~dup.values], new_c[~dup.values], new_key[~dup.values]

    old = registry_read(rt, table)
    old_c = _canon(old)
    old_key = old_c[keys].agg("\x1f".join, axis=1) if len(old) else pd.Series([], dtype=str)

    in_old = new_key.isin(set(old_key))
    value_cols = [c for c in cols if c not in keys and c not in _META_COLUMNS]
    changed_keys = set()
    if in_old.any():
        a = new_c[in_old.values].set_index(new_key[in_old].to_numpy())[value_cols]
        b = old_c.set_index(old_key.to_numpy())[value_cols].loc[a.index]
        changed_keys = set(a.index[(a != b).any(axis=1).values])

    write_mask = (~in_old.values) | new_key.isin(changed_keys).values
    keep_old = ~old_key.isin(changed_keys).values if len(old) else np.array([], bool)
    kept = [x for x in (old[keep_old], new[write_mask]) if len(x)]     # bez pustych ramek (ostrzeżenie pandas)
    out = pd.concat(kept, ignore_index=True) if kept else new.iloc[:0]
    out_key = _canon(out[keys]).agg("\x1f".join, axis=1) if len(out) else pd.Series([], dtype=str)
    out = out.iloc[np.argsort(out_key.to_numpy(), kind="stable")]

    path = _registry_path(rt, table)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    out.to_csv(tmp, index=False)
    os.replace(tmp, path)
    counts = {"new": int((~in_old).sum()), "changed": len(changed_keys),
              "unchanged": int(in_old.sum()) - len(changed_keys)}
    logger.info(f"Rejestr {table}: +{counts['new']} nowych, {counts['changed']} zmienionych, "
                f"{counts['unchanged']} bez zmian (razem {len(out)}).")
    return counts


def _short_repr(v: Any, limit: int = 300) -> str:
    s = repr(v)
    return s if len(s) <= limit else s[:limit] + "..."


def run_task(rt: Dict[str, Any], name: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Dict[str, Any]:
    """
    Uruchamia jedno zadanie i zapisuje je w gwl_runs.

    Kontrakt zadania: fn(*args, **kwargs) zwraca słownik z kluczami (wszystkie opcjonalne):
      "registry": {tabela: DataFrame} -> wiersze trafiają do rejestru (z run_id tego uruchomienia),
      "skipped": True                 -> zadanie nie miało nic do zrobienia (status "skipped"),
      "message": str                  -> komunikat zapisany w gwl_runs i wypisany,
      "pipeline_version": str         -> wersja modułu zapisana w gwl_runs.
    Zmiana względem AgriWatch: błąd jest zapisany w gwl_runs (status "error") i ZGŁOSZONY DALEJ - "Uruchom wszystko"
    zatrzymuje się na pierwszym błędzie (CLAUDE.md, zasada 3). Wynik inny niż słownik = TypeError (też zapisany).
    """
    started = _utc_now()
    run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}_{name}"
    t0 = time.time()
    status, message, n_new, result = "ok", "", 0, None
    logger.info(f"=== ZADANIE {name} (run_id={run_id}) ===")

    def record() -> None:
        params = {"args": [_short_repr(a) for a in args], "kwargs": {k: _short_repr(v) for k, v in kwargs.items()}}
        run_row = pd.DataFrame([{
            "run_id": run_id, "task": name, "started_at": started, "finished_at": _utc_now(),
            "duration_s": round(time.time() - t0, 1), "status": status, "git_commit": rt.get("GIT_COMMIT", ""),
            "pipeline_version": result.get("pipeline_version", "") if isinstance(result, dict) else "",
            "params_json": json.dumps(params, ensure_ascii=False), "n_new_rows": n_new, "message": message[:2000],
        }])
        registry_upsert(rt, "gwl_runs", run_row)
        print(f"[{status.upper()}] {name} ({run_row['duration_s'].iat[0]} s) {message}")

    # Jedyny szeroki except w module: BaseException (także KeyboardInterrupt przerwanej komórki) jest tylko zapisywany
    # w gwl_runs i zawsze zgłaszany dalej instrukcją `raise` - niczego nie połyka, nie podstawia wyniku.
    try:
        result = fn(*args, **kwargs)
        if not isinstance(result, dict):
            raise TypeError(f"Zadanie {name} zwróciło {type(result).__name__}; kontrakt run_task wymaga słownika")
        if result.get("skipped"):
            status = "skipped"
        message = str(result.get("message", ""))
        parts = []
        for table, df in (result.get("registry") or {}).items():
            df = df.copy()
            if "run_id" in REGISTRY_SCHEMA[table]["columns"]:
                df["run_id"] = run_id
            c = registry_upsert(rt, table, df)
            n_new += c["new"]
            parts.append(f"{table}: +{c['new']}/~{c['changed']}")
        if parts:
            message = (message + "; " if message else "") + ", ".join(parts)
    except BaseException as e:
        status, message = "error", f"{type(e).__name__}: {e}"
        logger.error(f"Zadanie {name} zakończone błędem: {message}")
        record()
        raise
    record()
    return result


def run_history(rt: Dict[str, Any], n: int) -> pd.DataFrame:
    """Ostatnie n uruchomień (najnowsze na górze)."""
    runs = registry_read(rt, "gwl_runs")
    cols = ["run_id", "task", "status", "duration_s", "n_new_rows", "git_commit", "message"]
    return runs.sort_values(["started_at", "run_id"], ascending=False).head(n)[cols].reset_index(drop=True)


def registry_summary(rt: Dict[str, Any]) -> pd.DataFrame:
    """Liczba wierszy i rozmiar każdej tabeli rejestru."""
    rows = []
    for table in REGISTRY_SCHEMA:
        path = _registry_path(rt, table)
        exists = os.path.exists(path)
        rows.append({"table": table, "rows": len(registry_read(rt, table)) if exists else 0,
                     "size_kb": round(os.path.getsize(path) / 1024, 1) if exists else 0.0})
    return pd.DataFrame(rows)


# ==============================================================================
# II. KONFIGURACJA I ZATWIERDZENIA (Plan_v2_implementacja.md, sekcja 3)
# ==============================================================================
# [p] = propozycja do zatwierdzenia; None = decyzja nieustalona (wyjątek przy użyciu). Sekcja z approved = None
# zatrzymuje każde zadanie, które jej używa (require_approved). Ścieżki względne liczone od PROJECT_DIR.
# Klucze oznaczone "dodane" nie występują w specyfikacji: wymagają ich moduły step_04-step_08.
CHECK_CONFIG: Dict[str, Any] = {
    "project": {
        "project_dir": "/content/drive/MyDrive/GeoWorldLook/egmscheck",   # klon repozytorium na Dysku (Plan_v2)
        "token_path": "/content/drive/MyDrive/GeoWorldLook/secrets/clms_token.json",   # poza repozytorium (CLAUDE.md)
        "earthdata_path": "/content/drive/MyDrive/GeoWorldLook/secrets/earthdata.json",  # NASA Earthdata (etap B)
        "downloaded_by": "GeoWorldLook",
        "manifest": "data/00_Metadata/MANIFEST.csv",
        "extracts_dir": "data/03_Extracts",
        "outputs_dir": "data/05_Final_Outputs/egmscheck",
        "gnss_dir": "data/02_Raw_Ground/3_gnss_ngl",                      # jak E1
        "levelling_dir": "data/02_Raw_Ground/4_levelling_nrw",
    },
    "egms": {
        "release": "2020-2024",                  # decyzja autora 2026-10-11 (API zwraca 2019-2023 i 2020-2024)
        "levels": ["L2B", "L3"],                 # decyzja autora 2026-10-11: L2b i L3 pion
        "l3_product_types": ["ORTHO-UP"],
        "raw_dir": "data/01_Raw_EGMS/2020_2024",  # Dysk (decyzja 2026-10-11: wszystkie dane na Dysku)
        "download_pause_s": 15,                  # Hrysiewicz i in. 2024 (EGMS-toolkit), jak E1
        "drive_margin_gb": 1.0,                  # [p] zapas wolnego miejsca na Dysku
        "chunksize": 200000,                     # jak E1
        "l2b_aoi_map": False,                    # [p] mapa L2b całego obszaru (duże pliki) - wyłączona
        # Prostokąt wyszukania: obszar regionu + punkty naziemne, gdy już wybrane (decyzja autora 2026-10-11: wszystkie dane
        # projektu na Dysku). Bez sites.csv wyszukanie obejmuje sam obszar; po wyborze stacji ponowne task_egms_search
        # dobiera pliki dla punktów spoza obszaru (pobranie przyrostowe, istniejące pliki pominięte).
        "search_area": "aoi_plus_sites",
        "approved": "2026-10-11",                # decyzje autora z 2026-10-11 (Plan_v2_implementacja.md, nagłówek)
    },
    "regions": {
        "groningen": {
            "cause": "wydobycie gazu (pole Groningen)",
            "aoi_lonlat": (5.8, 52.9, 7.3, 53.6),        # jak E1 (stacje osiadające)
            "control_lonlat": (4.8, 52.4, 8.3, 54.0),    # jak E1 (stacje stabilne: region + ok. 60 km okolicy)
            "gnss_rule": "subsiding_and_stable",         # reguła E1 (step_01.select_stations, zatwierdzona 2026-10-10)
            "levelling": None,                           # brak niwelacji w tym regionie (None = nie dotyczy)
            "approved": "2026-10-10",                    # obszar E1, reguła zatwierdzona 2026-10-10
        },
        "nrw_west": {
            "cause": "odkrywki węgla brunatnego (obniżanie wód); wypiętrzanie po zatopieniu kopalń",
            "aoi_lonlat": (5.9, 50.7, 7.0, 51.3),        # [p] do potwierdzenia z ryc. 14-15 Even 2024; Epe poza obszarem
            "gnss_rule": "all_quality",                  # [p] step_06.select_stations_aoi
            "levelling": {
                # Geobasis NRW, Höhenfestpunkte (adresy od autora 2026-10-12; licencja dl-de/zero-2-0, F5 sekcja 5).
                "urls": {"points": "https://www.opengeodata.nrw.de/produkte/geobasis/rb/fd/hfp_pl_csv/hfp_pl.csv",
                         "series": "https://www.opengeodata.nrw.de/produkte/geobasis/rb/fd/hfp_plzf_csv/hfp_plzf.csv"},
                "encoding": "utf-8",                     # Datenformatbeschreibung HFP NRW (07/2023): UTF-8
                # Ostwert z przedrostkiem strefy "32" (np. 32428124): EPSG:4647 = ETRS89 / UTM 32N (zE-N). Sprawdzone na
                # przykładzie z Datenformatbeschreibung: 3613900015 "Halen" -> 7,945 E, 52,338 N (Lotte, NRW).
                # Opis kolumny podaje "DHDN2016" (najpewniej literówka; 8-cyfrowy Ostwert z prefiksem 32 to UTM 32).
                "crs_epsg": 4647,
                "epoch_rule": "first_last_in_release",   # [p]
                "min_epoch_span_yr": 1.0,                # [p]
                "reference": {"type": "absolute"},       # autor 2026-10-12: wariant główny bez wspólnego reperu; jak Even i in. 2024 (rozdz. 3, 4.3.1: różnice prędkości wprost, bias raportowany; pełny tekst sprawdzony 2026-10-13)
                "read_method": "linear_interpolation",   # dodane [p] (prototyp read_at_epochs; bez ekstrapolacji)
                # Autor 2026-10-12, po diagnostyce epok (kampania niwelacji 05.2019 -> 05.2022: 1491 reperów z dwiema
                # epokami w oknie 2019-2023, 13 w oknie 2020-2024): porównanie z niwelacją DODATKOWO z wydaniem
                # 2019-2023, tylko L3 pion (4 kafle). Wydanie główne egms.release i wynik 2020-2024 bez zmian.
                # Repery: wszystkie z parą epok w oknie wydania (bez wyboru według EGMS); kryteria N1-N4 z progami
                # thresholds.levelling_l3u bez zmian.
                "egms_check": {"release": "2019-2023", "levels": ["L3"], "l3_product_types": ["ORTHO-UP"],
                               "raw_dir": "data/01_Raw_EGMS/2019_2023"},
                # Autor 2026-10-12: podział INFORMACYJNY (bez progu i bez werdyktu) na niecki |v_niw| >= 10 mm/rok
                # i pozostałe, według niwelacji; z odległością reperu do najbliższej stacji GNSS (NGL, plik MIDAS).
                "strong_motion_mm_yr": 10.0,
                # Autor 2026-10-13: wariant DODATKOWY (wariant główny 'absolute' i jego werdykt bez zmian) - oba zbiory
                # względem grupy reperów stabilnych według niwelacji (|Δh_niw| <= thresholds.levelling_l3u.
                # stable_max_lev_mm), mediana prędkości grupy; metodyka projektu F4 sekcja 10 (zapisana przed obliczeniami;
                # to NIE jest metoda Even i in. 2024, którzy porównują prędkości wprost - sprostowanie w F4),
                # policzony po obejrzeniu wyniku 'absolute' (stałe przesunięcie ok. -2 mm/rok) - tak opisywać w raporcie.
                "relative_variant": "stable_group_median",
                # Autor 2026-10-15: niepewność EGMS na rycinach, INFORMACYJNIE (bez progu, werdykty bez zmian):
                # sigma pojedynczego odczytu = kolumna 'rmse' komórki L3 (reszty szeregu względem modelu EGMS, mm);
                # Δh to różnica dwóch odczytów -> sigma_Δh = sqrt(2) * rmse; pas +-k_sigma * sigma_Δh (2 = ok. 95%).
                # Niwelacja bez niepewności: rejestr NRW jej nie podaje (kolumny: punkt, data, wysokość).
                "uncertainty": {"egms_sigma_column": "rmse", "k_sigma": 2.0},
            },
            "approved": "2026-10-12",                # autor 2026-10-12: obszar 5,9-7,0 E, 50,7-51,3 N; egms_check 2019-2023
        },
    },
    "gnss": {
        "midas_url": "https://geodesy.unr.edu/velocities/midas.IGS.txt",   # jak E1 (NGL, Blewitt i in. 2016)
        "frame": "EU",                           # płyta euroazjatycka odjęta, jak EGMS L2b/L3 (E1)
        "t_first_max": 2020.0,                   # [p] GNSS pokrywa wydanie 2020-2024
        "t_last_min": 2024.25,                   # [p]
        "svu_max_mm_yr": 1.0,                    # [p] jak E1
        "max_steps": 2,                          # [p] jak E1
        "vu_subsiding_max": -2.0,                # [p] jak E1
        "vu_stable_abs_max": 1.0,                # [p] jak E1
        "n_stable": 8,                           # [p] jak E1
        "n_stable_min": 3,                       # [p] jak E1
        "approved": "2026-10-12",                # autor 2026-10-12: reguła E1, okno 2020.0-2024.25
    },
    "method": {
        # Jak E1 (Koudogbo i in. 2025: 100 m, min. 3 punkty, okno 12 dni; model EGMS: trend + sinusoida roczna)
        "extract_radius_m": 200,                 # [p]
        "radius_main_m": 100,                    # [p]
        "radii_m": [100, 200],                   # [p]
        "min_points": 3,                         # [p]
        "gnss_half_window_days": 6,              # [p]
        "velocity_model": "linear_annual",       # [p]
        "min_overlap": 0.85,                     # [p] White Paper 2025
        "conv_tol": 0.01,                        # [p]
        "duplicate_dist_m": 1.0,                 # [p]
        "l3_cell_m": 100,                        # [p] siatka L3 (F5)
        "l3_min_points": 1,                      # [p] jedna komórka
        "approved": "2026-10-12",                # autor 2026-10-12: parametry E1
    },
    "thresholds": {
        "gnss_l2b": {"abs_dv_mm_yr": 1.5,        # Fabris i Nazari 2026 za Fiaschi i in. 2018 (E1)
                     "share_within": 0.80,       # jak E1
                     "series_std_mm": 5.0,       # Crosetto i in. 2025 (E1)
                     "stable_abs_v_mm_yr": 1.5,  # jak E1
                     "k3_definition": "abs_dv"},  # autor 2026-10-12: max |dv| na stacjach stabilnych (wybór po wnioskach E1, przed obliczeniami)
        "gnss_l3u": {"abs_dv_mm_yr": 1.5,        # [p]
                     "share_within": 0.80},      # [p]
        "levelling_l3u": {"median_abs_dh_mm": 5.0,      # [p] Koudogbo i in. 2025 (MAE < 5 mm)
                          "sign_min_signal_mm": 6.0,    # [p] Plan_v1_kryteria_akceptacji, sekcja C
                          "sign_agreement": 0.90,       # [p]
                          "stable_max_lev_mm": 2.0,     # [p]
                          "stable_abs_dh_mm": 5.0,      # [p]
                          "velocity_bias_mm_yr": 1.5},  # [p]
        "approved": "2026-10-12",                # autor 2026-10-12: progi [p] jak wyżej; k3_definition nadal do decyzji
    },
    "monitoring": {
        "window_starts": ["2020-01-01", "2022-01-01"],          # [p]
        "windows_months": [3, 6, 9, 12, 18, 24, 36, 48, 60],    # [p]
        "model_short": "linear",                 # [p] okna < 12 mies.
        "model_long": "linear_annual",           # jak E1
        "detect_k_sigma": 2.0,                   # [p]
        "sigma_method": "ar1",                   # [p]
        "s1b_end_date": "2021-12-23",            # do potwierdzenia (koniec Sentinel-1B)
        "min_obs": 10,                           # dodane [p] (step_07; próg step_03.fit_velocity)
        "map_vlim_percentile": 98.0,             # dodane [p] (step_07.plot_l3_map: granice skali kolorów)
        "example_rule": "max_subsidence_median_stable",   # dodane [p] (Plan_v2 sekcja 7 pkt 5; reguła E1)
        "approved": "2026-10-12",                # autor 2026-10-12: wszystkie wartości [p] tej sekcji
    },
    "hyp3": {
        "region": "groningen",                   # dodane [p]: region etapu B (Plan_v2 sekcja 4.2: ścieżki Groningen)
        "job_type": "INSAR_ISCE_MULTI_BURST",    # [p]
        "looks": "20x4",                         # [p]
        "apply_water_mask": True,                # [p]
        "polarization": "VV",
        "start": "2024-01-01",                   # [p] zakładka z EGMS (Plan_v2 sekcja 4.1)
        "overlap_end": "2024-12-31",             # koniec wydania EGMS 2020-2024
        "end": "2026-09-30",                     # autor 2026-10-12: ostatni pełny miesiąc przed uruchomieniem
        "n_neighbors": 3,                        # [p]
        "max_dt_days": 48,                       # [p]
        "tracks": ["37", "88"],                  # autor 2026-10-12: 2 ścieżki (zst. 37, wst. 88; najwięcej stacji GNSS w E1)
        "max_credits": 10000,                    # autor 2026-10-12: miesięczny przydział kredytów ASF HyP3 (do sprawdzenia w check_credits)
        "cost_per_job": 10,                      # autor 2026-10-12: górne oszacowanie kosztu zlecenia; ASF i tak odrzuca przekroczenie
        "los_check_tol": 0.05,                   # autor 2026-10-12: |los_up własny - EGMS| (ok. 3 stopnie kąta padania)
        "raw_dir": "data/01_Raw_InSAR/hyp3",
        "mintpy": {"troposphere": "no",          # [p]
                   "min_temp_coh": 0.7,          # [p]
                   "topographic_residual": True,  # [p]
                   "reference_rule": "stable_gnss_min_abs_vu",  # [p]
                   "window_px": 3,               # [p]
                   "deramp": "no",               # autor 2026-10-12: bez usuwania rampy (nie tłumić sygnału niecki)
                   "solid_earth_tides": False},  # autor 2026-10-12: pomijalne dla trendu na małym obszarze
        "approved": "2026-10-12",                # autor 2026-10-12: region Groningen, 2 ścieżki, wartości [p] i powyższe
    },
}


def _section(cfg: Dict[str, Any], section_path: str) -> Dict[str, Any]:
    node: Any = cfg
    for part in section_path.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(f"Brak sekcji CHECK_CONFIG['{section_path}'] (część '{part}')")
        node = node[part]
    if not isinstance(node, dict):
        raise KeyError(f"CHECK_CONFIG['{section_path}'] nie jest sekcją (słownikiem)")
    return node


def _open_decisions(section: Dict[str, Any], prefix: str = "") -> List[str]:
    """Klucze sekcji z wartością None (decyzje nieustalone); region.levelling = None oznacza 'nie dotyczy'."""
    out = []
    for k, v in section.items():
        if k == "approved" or (k == "levelling" and v is None and not prefix):
            continue
        if v is None:
            out.append(prefix + k)
        elif isinstance(v, dict):
            out += _open_decisions(v, prefix + k + ".")
    return out


def require_approved(cfg: Dict[str, Any], section_path: str) -> Dict[str, Any]:
    """
    Sekcja CHECK_CONFIG (ścieżka z kropkami, np. 'regions.groningen') zatwierdzona przez autora -> sekcja.
    approved = None -> RuntimeError z nazwą decyzji i listą otwartych parametrów (CLAUDE.md, zasady 2 i 9).
    Brak sekcji albo klucza 'approved' -> KeyError.
    """
    sec = _section(cfg, section_path)
    if "approved" not in sec:
        raise KeyError(f"CHECK_CONFIG['{section_path}'] nie ma klucza 'approved'")
    if sec["approved"] is None:
        open_ = _open_decisions(sec)
        raise RuntimeError(f"Sekcja CHECK_CONFIG['{section_path}'] nie jest zatwierdzona (approved = None): decyzja "
                           f"autora przed obliczeniami (wartości [p] i None w step_05_colab_run.py)"
                           + (f"; otwarte parametry: {open_}" if open_ else ""))
    return sec


def approvals_table(cfg: Dict[str, Any]) -> pd.DataFrame:
    """Stan zatwierdzeń: sekcja, approved, status, otwarte decyzje (klucze o wartości None)."""
    rows = []

    def walk(node: Dict[str, Any], path: str) -> None:
        for k, v in node.items():
            if not isinstance(v, dict):
                continue
            p = f"{path}.{k}" if path else k
            if "approved" in v:
                rows.append({"section": p, "approved": v["approved"],
                             "status": "zatwierdzone" if v["approved"] is not None else "czeka na decyzję autora",
                             "open_decisions": ", ".join(_open_decisions(v)) or "-"})
            else:
                walk(v, p)
    walk(cfg, "")
    return pd.DataFrame(rows, columns=["section", "approved", "status", "open_decisions"])


def _decided(section: Dict[str, Any], key: str, path: str) -> Any:
    """Wartość parametru; brak klucza = KeyError, None = RuntimeError (decyzja autora nieustalona)."""
    if key not in section:
        raise KeyError(f"CHECK_CONFIG['{path}'] nie ma klucza '{key}'")
    if section[key] is None:
        raise RuntimeError(f"CHECK_CONFIG['{path}']['{key}'] = None: decyzja autora nieustalona (CLAUDE.md, zasada 2)")
    return section[key]


def _region(cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    return require_approved(cfg, f"regions.{region}")


# ==============================================================================
# III. ZADANIA ETAPU A: ŚCIEŻKI, PUNKTY NAZIEMNE, WSPÓLNE POMOCNICZE
# ==============================================================================
def _abs(rt: Dict[str, Any], path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else Path(rt["PROJECT_DIR"]) / p


def region_paths(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Path]:
    """Pliki regionu: wycinki w data/03_Extracts/<region>/, wyniki w data/05_Final_Outputs/egmscheck/<region>/."""
    ex = _abs(rt, cfg["project"]["extracts_dir"]) / region
    out = _abs(rt, cfg["project"]["outputs_dir"]) / region
    return {"extracts": ex, "outputs": out, "figures": out / "figures",
            "sites": ex / "sites.csv", "plan": ex / f"egms_plan_{region}.csv",
            "l2b_points": ex / "egms_l2b_points.csv.gz", "l2b_dedup": ex / "egms_l2b_points_dedup.csv.gz",
            "l3_cells": ex / "egms_l3u_cells_at_sites.csv.gz", "l3_map": ex / "egms_l3u_map.csv.gz",
            "l2b_map": ex / "egms_l2b_map.csv.gz", "levelling": ex / "levelling_long.csv.gz",
            "long": ex / "timeseries_long.csv.gz", "long_status": ex / "timeseries_status.csv",
            "download_log": out / f"egms_download_{region}.csv", "checks": out / f"checks_{region}.csv",
            "l3_grid": out / f"l3_grid_offsets_{region}.csv", "gnss_compare": out / f"gnss_compare_{region}.csv",
            "verdict_l2b": out / f"verdict_gnss_l2b_{region}.csv", "verdict_l3u": out / f"verdict_gnss_l3u_{region}.csv",
            "levelling_compare": out / f"levelling_compare_{region}.csv",
            "levelling_summary": out / f"levelling_summary_{region}.csv",
            "levelling_status": out / f"levelling_egms_status_{region}.csv",
            "sampling": out / f"sampling_{region}.csv", "sampling_summary": out / f"sampling_summary_{region}.csv",
            "detection": out / f"detection_curves_{region}.csv", "ttd": out / f"time_to_detection_{region}.csv",
            "hyp3_plan": ex / f"hyp3_plan_{region}.csv"}


def levelling_check_paths(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Path]:
    """
    Pliki porównania z niwelacją na drugim wydaniu (regions.<region>.levelling.egms_check.release, np. 2019-2023):
    plan i dziennik pobrania, komórki L3 przy reperach, mapa prędkości L3 obszaru, parametry wycinka, wyniki N1-N4,
    podział, ryciny (rozrzut, mapa).
    Nazwy z rokiem wydania, więc nie mieszają się z plikami wydania głównego.
    """
    lv = _region(cfg, region).get("levelling")
    if lv is None:
        raise ValueError(f"Region {region} bez niwelacji (levelling = None): brak porównania z drugim wydaniem")
    rel = str(_decided(_decided(lv, "egms_check", f"regions.{region}.levelling"), "release",
                       f"regions.{region}.levelling.egms_check"))
    tag = rel.replace("-", "_")
    P = region_paths(rt, cfg, region)
    ex, out = P["extracts"], P["outputs"]
    return {"plan": ex / f"egms_plan_{region}_levelling_{tag}.csv",
            "download_log": out / f"egms_download_{region}_levelling_{tag}.csv",
            "l3_cells": ex / f"egms_l3u_{tag}_cells_at_benchmarks.csv.gz",
            "l3_map": ex / f"egms_l3u_{tag}_map.csv.gz",
            "map": P["figures"] / f"{region}_l3_velocity_map_{tag}.png",
            "params": ex / f"extract_params_levelling_{tag}.json",
            "compare": out / f"levelling_compare_{region}_{tag}.csv",
            "summary": out / f"levelling_summary_{region}_{tag}.csv",
            "status": out / f"levelling_egms_status_{region}_{tag}.csv",
            "groups": out / f"levelling_groups_{region}_{tag}.csv",
            "figure": P["figures"] / f"{region}_levelling_scatter_{tag}.png",
            "compare_rel": out / f"levelling_compare_{region}_{tag}_relative.csv",
            "summary_rel": out / f"levelling_summary_{region}_{tag}_relative.csv",
            "groups_rel": out / f"levelling_groups_{region}_{tag}_relative.csv",
            "offset_rel": out / f"levelling_offset_{region}_{tag}_relative.json",
            "uncertainty": out / f"levelling_uncertainty_{region}_{tag}.json",
            "figure_rel": P["figures"] / f"{region}_levelling_scatter_{tag}_relative.png"}


def hyp3_paths(rt: Dict[str, Any], cfg: Dict[str, Any], region: str, track: str) -> Dict[str, Path]:
    """Pliki etapu B jednej ścieżki: plan i zlecenia, produkty (raw_dir), katalog MintPy w wycinkach (poza git)."""
    P = region_paths(rt, cfg, region)
    mp = P["extracts"] / f"mintpy_{track}"
    return {"plan_json": P["extracts"] / f"hyp3_plan_{region}_{track}.json",
            "jobs": P["outputs"] / f"hyp3_jobs_{region}_{track}.csv",
            "download": P["outputs"] / f"hyp3_download_{region}_{track}.csv",
            "raw": _abs(rt, cfg["hyp3"]["raw_dir"]) / f"{region}_{track}",
            "mintpy": mp, "clip": mp / "clip", "work": mp / "work", "template": mp / f"EGMSCheck_{region}_{track}.txt",
            "align": P["outputs"] / f"hyp3_align_{region}_{track}.csv",
            "status": P["outputs"] / f"hyp3_series_status_{region}_{track}.csv"}


def _sources_of(release: str) -> Dict[str, str]:
    """Nazwy źródeł formatu długiego (Plan_v2 sekcja 2.2) z wydania '2020-2024': EGMS_L2b_2020_2024, EGMS_L3U_2020_2024."""
    y1, y2 = str(release).split("-")
    return {"L2B": f"EGMS_L2b_{y1}_{y2}", "L3": f"EGMS_L3U_{y1}_{y2}"}


def _sources(cfg: Dict[str, Any]) -> Dict[str, str]:
    """Źródła wydania głównego (egms.release)."""
    return _sources_of(cfg["egms"]["release"])


def _manifest(rt: Dict[str, Any], cfg: Dict[str, Any]) -> Path:
    m = _abs(rt, cfg["project"]["manifest"])
    m.parent.mkdir(parents=True, exist_ok=True)
    return m


def _read_csv(path: Path, what: str, **kw) -> pd.DataFrame:
    if not Path(path).exists():
        raise FileNotFoundError(f"Brak pliku {path} ({what})")
    return pd.read_csv(path, **kw)


def _sites_for_search(P: Dict[str, Path]) -> pd.DataFrame:
    """Punkty naziemne do prostokąta wyszukania EGMS; brak sites.csv = sam obszar (komunikat, nie cichy wybór)."""
    if P["sites"].exists():
        return _read_sites(P)
    print(f"Brak {P['sites']}: wyszukanie EGMS tylko dla obszaru regionu. Po wyborze stacji (task_select_gnss) uruchom "
          f"ponownie egms_search, aby dobrać pliki dla punktów spoza obszaru.")
    return pd.DataFrame(columns=["site", "lon_deg", "lat_deg"])


def _read_sites(P: Dict[str, Path]) -> pd.DataFrame:
    s = _read_csv(P["sites"], "punkty naziemne: task_select_gnss / task_levelling", dtype={"site": str})
    missing = [c for c in ["site", "site_type", "group", "lat_deg", "lon_deg", "x_3035", "y_3035"] if c not in s]
    if missing:
        raise KeyError(f"{P['sites']}: brak kolumn {missing}")
    return s


def _write_sites(P: Dict[str, Path], rows: pd.DataFrame, site_type: str) -> pd.DataFrame:
    """
    Zastępuje w sites.csv wiersze danego typu (gnss / benchmark); identyfikator w dwóch typach = ValueError.
    Plik o tej samej treści nie jest zapisywany ponownie (czas modyfikacji steruje aktualnością wycinków);
    porównanie niezależne od kolejności wierszy (wiersze zapisywanego typu trafiają na koniec, więc przy dwóch
    typach kolejność w pliku zmienia się co uruchomienie - bez tego ponowny przebieg wycinałby EGMS od nowa).
    """
    rows = rows.reindex(columns=SITES_COLUMNS).assign(site_type=site_type)
    rows["site"] = rows["site"].astype(str)
    old = _read_sites(P).reindex(columns=SITES_COLUMNS) if P["sites"].exists() else None
    keep = old[old["site_type"] != site_type] if old is not None else rows.iloc[:0]
    out = pd.concat([keep, rows], ignore_index=True) if len(keep) else rows.reset_index(drop=True)
    dup = out.loc[out["site"].duplicated(), "site"].tolist()
    if dup:
        raise ValueError(f"Te same identyfikatory punktów w różnych typach: {dup[:10]}")

    def by_site(df: pd.DataFrame) -> pd.DataFrame:
        return _canon(df.sort_values("site", kind="stable").reset_index(drop=True))
    if old is not None and len(old) == len(out) and by_site(old).equals(by_site(out)):
        return out
    P["sites"].parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(P["sites"], index=False)
    return out


def _sites_registry(sites: pd.DataFrame, region: str) -> pd.DataFrame:
    return sites.assign(region=region, updated_at=_utc_now())[
        ["region", "site", "site_type", "group", "lat_deg", "lon_deg", "x_3035", "y_3035", "source", "updated_at"]]


def _read_plan(P: Dict[str, Path]) -> pd.DataFrame:
    plan = _read_csv(P["plan"], "plan pobrania EGMS: task_egms_search")
    missing = [c for c in ("level", "filename", "filesize", "need_bytes", "status", "query_key") if c not in plan]
    if missing:
        raise KeyError(f"{P['plan']}: brak kolumn {missing}")
    return plan


def _l2b_tracks(plan: pd.DataFrame) -> Dict[int, str]:
    """Ścieżki L2B z planu -> kierunek; ścieżka z dwoma kierunkami = ValueError."""
    l2 = plan[plan["level"] == "L2B"]
    out = {}
    for t, d in zip(l2["relativeOrbit"], l2["direction"]):
        t = int(t)
        if out.setdefault(t, d) != d:
            raise ValueError(f"Ścieżka {t} z dwoma kierunkami w planie: {out[t]}, {d}")
    return dict(sorted(out.items()))


def _extracts_exist(P: Dict[str, Path], cfg: Dict[str, Any]) -> bool:
    need = ([P["l2b_points"]] if "L2B" in cfg["egms"]["levels"] else []) + \
           ([P["l3_cells"], P["l3_map"]] if "L3" in cfg["egms"]["levels"] else [])
    return bool(need) and all(p.exists() for p in need)


def _up_to_date(outputs: List[Path], inputs: List[Path]) -> bool:
    """Wszystkie wyniki istnieją i są nowsze niż każde wejście (czas modyfikacji)."""
    if not all(p.exists() for p in outputs):
        return False
    return min(p.stat().st_mtime for p in outputs) >= max(p.stat().st_mtime for p in inputs)


def _date_cols(df: pd.DataFrame) -> List[str]:
    from step_02_checks_extract import date_columns
    return sorted(date_columns(df))               # yyyymmdd: porządek tekstowy = chronologiczny


def _track_date_cols(points: pd.DataFrame) -> List[str]:
    """Daty jednej ścieżki: kolumny dat z co najmniej jedną wartością dla punktów tej ścieżki."""
    cols = [c for c in _date_cols(points) if points[c].notna().any()]
    if len(cols) < 2:
        raise ValueError(f"Za mało dat z wartościami w punktach ścieżki ({len(cols)})")
    return cols


def _order_columns(df: pd.DataFrame) -> pd.DataFrame:
    dates = _date_cols(df)
    extra = [c for c in L2B_EXTRA if c in df.columns]
    attrs = [c for c in df.columns if c not in set(dates) | set(extra)]
    return df[attrs + dates + extra]


def _read_points(path: Path, what: str) -> pd.DataFrame:
    return _read_csv(path, what, dtype={"pid": str, "site": str}, low_memory=False)


def _search_lonlat(reg: Dict[str, Any], sites: pd.DataFrame, rule: str) -> tuple:
    """Prostokąt wyszukania EGMS: 'aoi' albo 'aoi_plus_sites' (obszar rozszerzony o wszystkie punkty naziemne)."""
    lo0, la0, lo1, la1 = (float(v) for v in reg["aoi_lonlat"])
    if rule == "aoi":
        return lo0, la0, lo1, la1
    if rule != "aoi_plus_sites":
        raise ValueError(f"egms.search_area {rule!r}: dozwolone 'aoi', 'aoi_plus_sites'")
    if sites.empty:
        return lo0, la0, lo1, la1
    box = (min(lo0, float(sites["lon_deg"].min())), min(la0, float(sites["lat_deg"].min())),
           max(lo1, float(sites["lon_deg"].max())), max(la1, float(sites["lat_deg"].max())))
    if box != (lo0, la0, lo1, la1):
        logger.info(f"Prostokąt wyszukania EGMS rozszerzony o punkty naziemne: {reg['aoi_lonlat']} -> {box}")
    return tuple(float(v) for v in box)


def _gnss_path(rt: Dict[str, Any], cfg: Dict[str, Any], site: str) -> Path:
    frame = cfg["gnss"]["frame"]
    return _abs(rt, cfg["project"]["gnss_dir"]) / (f"{site}.EU.tenv3" if frame == "EU" else f"{site}.tenv3")


def _read_gnss(rt: Dict[str, Any], cfg: Dict[str, Any], sites: List[str]) -> Dict[str, pd.DataFrame]:
    """Szeregi tenv3 stacji (układ z gnss.frame: bramka sekcji gnss, gdy są stacje do wczytania)."""
    from step_01_ingest import read_ngl_tenv3
    if sites:
        require_approved(cfg, "gnss")
    out = {}
    for s in sites:
        p = _gnss_path(rt, cfg, s)
        if not p.exists():
            raise FileNotFoundError(f"Brak szeregu GNSS {p}: uruchom task_gnss_download")
        out[s] = read_ngl_tenv3(p)
    return out


def _metric_rows(df: pd.DataFrame, region: str, metrics: List[str], n_col: str, reference: str) -> pd.DataFrame:
    """
    Wyniki (kolumny product, site, track, radius_m, status + metryki) -> wiersze gwl_validation_metrics.
    Metryka bez kolumny przy wierszu 'ok' = KeyError (literówka nie może dać cichego NaN); przy wierszach z powodem
    NaN brak kolumny jest dozwolony (np. żadna para nie doszła do policzenia prędkości).
    """
    absent = [c for c in metrics + [n_col] if c not in df.columns]
    if absent and (df["status"] == "ok").any():
        raise KeyError(f"Brak kolumn metryk {absent} w wynikach ze statusem 'ok'; dostępne: {list(df.columns)}")
    rows = []
    for r in df.itertuples(index=False):
        d = r._asdict()
        for mname in metrics:
            v = d.get(mname, np.nan)
            n = d.get(n_col, np.nan)
            rows.append({"region": region, "product": d["product"], "reference": reference, "site": str(d["site"]),
                         "track": str(d["track"]), "radius_m": d.get("radius_m", np.nan), "metric": mname,
                         "value": float(v) if v is not None and pd.notna(v) else np.nan,
                         "n": float(n) if n is not None and pd.notna(n) else np.nan, "status": d["status"]})
    return pd.DataFrame(rows, columns=[c for c in REGISTRY_SCHEMA["gwl_validation_metrics"]["columns"] if c != "run_id"])


def task_select_gnss(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    Stacje GNSS regionu z pliku prędkości MIDAS (NGL): reguła E1 'subsiding_and_stable' (step_01.select_stations,
    okna z sekcji gnss) albo 'all_quality' (step_06.select_stations_aoi; zero stacji = pusta lista, nie błąd).
    Plik MIDAS zapisany z datą pobrania w data/02_Raw_Ground/3_gnss_ngl/ i w manifeście; gdy na Dysku jest już
    migawka midas_*.IGS.txt, używana jest najnowsza z nich bez ponownego pobrania (MIDAS zmienia się co tydzień:
    nowy plik przy każdym uruchomieniu zmieniałby wybór stacji między przebiegami). Wynik: sites.csv
    (wiersze GNSS zastąpione, repery zostają) i gwl_sites.
    """
    import step_01_ingest as s1
    import step_04_egms_aoi as s4
    import step_06_ground as s6
    reg = _region(cfg, region)
    g = require_approved(cfg, "gnss")
    P = region_paths(rt, cfg, region)
    gdir = _abs(rt, cfg["project"]["gnss_dir"])
    snapshots = sorted(gdir.glob("midas_*.IGS.txt"))      # midas_RRRRMMDD: porządek tekstowy = chronologiczny
    if snapshots:
        midas_path = snapshots[-1]
        print(f"MIDAS: migawka z Dysku {midas_path.name} (dostępne: {[p.name for p in snapshots]}); bez ponownego "
              f"pobrania - nowszy stan MIDAS zmienia wybór stacji (decyzja autora)")
    else:
        midas_path = gdir / f"midas_{datetime.now(timezone.utc):%Y%m%d}.IGS.txt"
    s1.download_file(g["midas_url"], midas_path, _manifest(rt, cfg), Path(rt["PROJECT_DIR"]),
                     "NGL MIDAS velocities (IGS20)", s1.NGL_LICENCE, cfg["project"]["downloaded_by"])
    midas = s1.read_ngl_midas(midas_path.read_text(encoding="utf-8"))
    rule = reg["gnss_rule"]
    if rule == "subsiding_and_stable":
        st = s1.select_stations(midas, reg["aoi_lonlat"], reg["control_lonlat"], g["t_first_max"], g["t_last_min"],
                                g["svu_max_mm_yr"], g["max_steps"], g["vu_subsiding_max"], g["vu_stable_abs_max"],
                                g["n_stable"], g["n_stable_min"])
        x, y = s4.transform_xy(st["lon_deg"].to_numpy(float), st["lat_deg"].to_numpy(float), 4326, 3035)
        st = st.assign(x_3035=x, y_3035=y, source=s6.GNSS_SITE_SOURCE)
    elif rule == "all_quality":
        st = s6.select_stations_aoi(midas, reg["aoi_lonlat"], g["t_first_max"], g["t_last_min"], g["svu_max_mm_yr"],
                                    g["max_steps"], g["vu_subsiding_max"], g["vu_stable_abs_max"])
    else:
        raise ValueError(f"regions.{region}.gnss_rule {rule!r}: dozwolone 'subsiding_and_stable', 'all_quality'")
    sites = _write_sites(P, st, "gnss")
    gn = sites[sites["site_type"] == "gnss"]
    msg = f"{len(gn)} stacji GNSS ({gn['group'].value_counts().to_dict()}), reguła {rule}"
    return {"message": msg, "registry": {"gwl_sites": _sites_registry(gn, region)} if len(gn) else {}}


def task_gnss_download(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    """Dobowe szeregi NGL (tenv3, układ z gnss.frame) stacji z sites.csv; plik istniejący nie jest pobierany ponownie."""
    import step_01_ingest as s1
    _region(cfg, region)
    g = require_approved(cfg, "gnss")
    P = region_paths(rt, cfg, region)
    gn = _read_sites(P)
    gn = gn[gn["site_type"] == "gnss"]
    if gn.empty:
        return {"skipped": True, "message": "brak stacji GNSS w regionie (GNSS „jeśli są”)"}
    rows = []
    for s in gn["site"]:
        path = _gnss_path(rt, cfg, s)
        s1.download_file(s1.ngl_tenv3_url(s, g["frame"]), path, _manifest(rt, cfg), Path(rt["PROJECT_DIR"]),
                         f"NGL IGS20 {g['frame']} daily series {s}", s1.NGL_LICENCE, cfg["project"]["downloaded_by"])
        t = s1.read_ngl_tenv3(path)
        rows.append({"site": s, "first": t["date"].min().date(), "last": t["date"].max().date(), "days": len(t)})
    tab = pd.DataFrame(rows)
    print(tab.to_string(index=False))
    return {"message": f"{len(tab)} szeregów GNSS ({tab['first'].min()} - {tab['last'].max()})"}


def task_levelling(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    Niwelacja NRW: pobranie Punktliste i Punktliste mit Zeitfolge z adresów regions.<region>.levelling.urls
    (None = decyzja, RuntimeError), czytniki i format długi step_06 (repery w obszarze), repery do sites.csv.
    """
    import step_01_ingest as s1
    import step_06_ground as s6
    reg = _region(cfg, region)
    lv = reg.get("levelling")
    if lv is None:
        return {"skipped": True, "message": f"region {region} bez niwelacji (levelling = None)"}
    path = f"regions.{region}.levelling"
    urls = _decided(lv, "urls", path)
    missing = [k for k in ("points", "series") if not urls.get(k)]
    if missing:
        raise KeyError(f"CHECK_CONFIG['{path}']['urls'] bez adresów {missing}")
    enc, crs = _decided(lv, "encoding", path), _decided(lv, "crs_epsg", path)
    P = region_paths(rt, cfg, region)
    d = _abs(rt, cfg["project"]["levelling_dir"])
    files = {}
    for key, what in (("points", "Höhenfestpunkte Punktliste"), ("series", "Höhenfestpunkte Punktliste mit Zeitfolge")):
        dest = d / urls[key].rstrip("/").rsplit("/", 1)[-1]
        s1.download_file(urls[key], dest, _manifest(rt, cfg), Path(rt["PROJECT_DIR"]), f"Geobasis NRW {what}",
                         NRW_LICENCE, cfg["project"]["downloaded_by"])
        files[key] = dest
    lev = s6.levelling_long(s6.read_nrw_points(files["points"], enc), s6.read_nrw_timeseries(files["series"], enc),
                            crs, reg["aoi_lonlat"])
    P["levelling"].parent.mkdir(parents=True, exist_ok=True)
    lev.to_csv(P["levelling"], index=False, date_format="%Y-%m-%d")
    bench = s6.benchmark_sites(lev)
    sites = _write_sites(P, bench, "benchmark")
    b = sites[sites["site_type"] == "benchmark"]
    return {"message": f"{len(b)} reperów w obszarze, {len(lev)} epok ({lev['epoch_date'].min().date()} - "
                       f"{lev['epoch_date'].max().date()})", "registry": {"gwl_sites": _sites_registry(b, region)}}


def _read_levelling(P: Dict[str, Path]) -> pd.DataFrame:
    return _read_csv(P["levelling"], "niwelacja: task_levelling", dtype={"benchmark_id": str},
                     parse_dates=["epoch_date"])


# ------------------------------------------------------------------------------
# EGMS: wyszukanie, plan, potwierdzenie, pobranie
# ------------------------------------------------------------------------------
# Serwery CLMS/EGMS bywają chwilowo niedostępne (503 z land.copernicus.eu/@@oauth2-token, Colab 2026-10-12).
# Ponawiamy WYŁĄCZNIE odpowiedzi 502/503/504, z jawnymi przerwami i komunikatem; po ostatniej próbie błąd idzie dalej
# (błąd głośny). Inne błędy HTTP (np. 401 przy złym kluczu) i wszystkie pozostałe wyjątki nie są ponawiane.
TRANSIENT_HTTP = (502, 503, 504)
L2B_SITE_TYPES = ("gnss",)                       # typy punktów, wokół których wycina się L2b (task_extract)
TRANSIENT_WAITS_S = (30, 90, 300)


def _retry_transient(fn: Callable[[], Any], what: str) -> Any:
    import requests
    for k, wait in enumerate(TRANSIENT_WAITS_S + (None,)):
        try:
            return fn()
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else None
            if code not in TRANSIENT_HTTP or wait is None:
                raise
            print(f"{what}: serwer odpowiedział {code} (chwilowa niedostępność); próba {k + 2} za {wait} s")
            time.sleep(wait)


def _clms_session(cfg: Dict[str, Any]):
    import requests
    import step_01_ingest as s1
    session = requests.Session()
    token = _retry_transient(lambda: s1.get_access_token(cfg["project"]["token_path"], session), "token CLMS")
    return session, s1.api_headers(token)


def _need_mb(plan: pd.DataFrame) -> int:
    return int(round(float(plan["need_bytes"].sum()) / 1e6))


def _check_confirm_mb(plan: pd.DataFrame, confirm_mb: Any, var: str, plan_name: str) -> int:
    """
    Ochrona przed przypadkowym pobraniem: confirm_mb musi być równe sumie need_bytes z planu w MB, zaokrąglonej
    do całości. None albo inna liczba = RuntimeError z wartością do wpisania (var: nazwa zmiennej w notatniku).
    """
    need = _need_mb(plan)
    if confirm_mb is None:
        raise RuntimeError(f"Pobranie EGMS wstrzymane: po obejrzeniu planu ustaw {var} = {need} (MB do pobrania według "
                           f"{plan_name}, {int((plan['need_bytes'] > 0).sum())} plików)")
    if isinstance(confirm_mb, bool) or not isinstance(confirm_mb, (int, np.integer, float)) or confirm_mb != need:
        raise RuntimeError(f"{var} = {confirm_mb!r}, a plan wymaga {need} MB: plan się zmienił albo wpisano inną liczbę; "
                           f"sprawdź plan i ustaw {var} = {need}")
    return need


def _in_manifest(manifest: Path, paths: List[str]) -> List[bool]:
    if not manifest.exists():
        return [False] * len(paths)
    known = set(pd.read_csv(manifest, dtype=str)["file_path"])
    return [p in known for p in paths]


def _query_main(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    """Zapytanie EGMS wydania głównego (sekcja egms): wydanie, poziomy, katalog, plan, zmienna potwierdzenia."""
    e = require_approved(cfg, "egms")
    _region(cfg, region)
    P = region_paths(rt, cfg, region)
    return {"release": e["release"], "levels": e["levels"], "l3_product_types": e["l3_product_types"],
            "raw": _abs(rt, e["raw_dir"]), "plan": P["plan"], "log": P["download_log"],
            "confirm_var": f"CONFIRM_MB_{region.upper()}", "ready": _extracts_exist(P, cfg),
            "ready_what": f"w {P['extracts']}"}


def _query_levelling(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    Zapytanie EGMS drugiego wydania do porównania z niwelacją (regions.<region>.levelling.egms_check). Tylko L3
    (porównanie z reperami czyta komórkę L3); inne poziomy, wydanie równe głównemu albo brak klucza = wyjątek.
    """
    require_approved(cfg, "egms")
    lv = _region(cfg, region).get("levelling")
    if lv is None:
        raise ValueError(f"Region {region} bez niwelacji (levelling = None)")
    path = f"regions.{region}.levelling.egms_check"
    q = _decided(lv, "egms_check", f"regions.{region}.levelling")
    rel, levels = _decided(q, "release", path), list(_decided(q, "levels", path))
    pts, raw_dir = _decided(q, "l3_product_types", path), _decided(q, "raw_dir", path)
    if levels != ["L3"]:
        raise ValueError(f"CHECK_CONFIG['{path}']['levels'] = {levels}: porównanie z niwelacją używa tylko ['L3']")
    if str(rel) == str(cfg["egms"]["release"]):
        raise ValueError(f"CHECK_CONFIG['{path}']['release'] = {rel} jest wydaniem głównym: to porównanie liczy "
                         f"task_compare_levelling")
    C = levelling_check_paths(rt, cfg, region)
    return {"release": rel, "levels": levels, "l3_product_types": pts, "raw": _abs(rt, raw_dir), "plan": C["plan"],
            "log": C["download_log"], "confirm_var": f"CONFIRM_MB_{region.upper()}_LEVELLING",
            "ready": C["l3_cells"].exists(), "ready_what": str(C["l3_cells"])}


def _egms_search_impl(rt: Dict[str, Any], cfg: Dict[str, Any], region: str, q: Dict[str, Any]) -> Dict[str, Any]:
    """Wyszukanie (step_04.search_plan) i plan pobrania (step_04.plan_download) dla zapytania q; zapis planu q['plan']."""
    import step_01_ingest as s1
    import step_04_egms_aoi as s4
    e = require_approved(cfg, "egms")
    reg = _region(cfg, region)
    P = region_paths(rt, cfg, region)
    token = Path(cfg["project"]["token_path"])
    if not token.is_file():
        if q["ready"]:
            return {"skipped": True, "message": f"brak tokenu CLMS ({token}): używam istniejących wycinków {q['ready_what']}"}
        raise FileNotFoundError(f"Brak tokenu CLMS {token} i brak wycinków {q['ready_what']}")
    area = _search_lonlat(reg, _sites_for_search(P), e["search_area"])
    session, headers = _clms_session(cfg)
    table, _ = _retry_transient(lambda: s4.search_plan(session, headers, s1.API_ENDPOINT, area, q["release"], q["levels"],
                                                       q["l3_product_types"]), "wyszukanie EGMS")
    raw = q["raw"]
    raw.mkdir(parents=True, exist_ok=True)
    plan = s4.plan_download(table, raw, s4.drive_free_bytes(raw), int(round(float(e["drive_margin_gb"]) * 1e9)))
    plan = plan.drop(columns=[c for c in ("bbox", "poly") if c in plan.columns]).assign(search_lonlat=str(area))
    q["plan"].parent.mkdir(parents=True, exist_ok=True)
    plan.to_csv(q["plan"], index=False)
    by = plan.groupby("query_key").agg(files=("filename", "size"), MB=("filesize", lambda s: round(s.sum() / 1e6, 1)))
    print(by.to_string())
    need = _need_mb(plan)
    return {"message": f"{len(plan)} plików, łącznie {plan['filesize'].sum() / 1e6:.1f} MB, do pobrania "
                       f"{plan['need_bytes'].sum() / 1e6:.1f} MB ({plan['status'].value_counts().to_dict()}); "
                       f"po akceptacji ustaw {q['confirm_var']} = {need}"}


def task_egms_search(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    Wyszukanie L2B i L3 (step_04.search_plan) w prostokącie wyszukania (egms.search_area) i plan pobrania
    (step_04.plan_download) względem wolnego miejsca w raw_dir z marginesem drive_margin_gb. Zapis
    egms_plan_<region>.csv; komunikat z liczbą MB do potwierdzenia (CONFIRM_MB_<REGION>).
    Bez tokenu CLMS: gdy wycinki istnieją -> pominięte (notatnik czyta data/03_Extracts/), inaczej FileNotFoundError.
    """
    return _egms_search_impl(rt, cfg, region, _query_main(rt, cfg, region))


def task_levelling_egms_search(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    Jak task_egms_search, dla drugiego wydania do porównania z niwelacją (regions.<region>.levelling.egms_check,
    tylko L3 pion); plan egms_plan_<region>_levelling_<wydanie>.csv, potwierdzenie CONFIRM_MB_<REGION>_LEVELLING.
    Region bez niwelacji = pominięte.
    """
    if _region(cfg, region).get("levelling") is None:
        return {"skipped": True, "message": f"region {region} bez niwelacji (levelling = None)"}
    return _egms_search_impl(rt, cfg, region, _query_levelling(rt, cfg, region))


def _egms_download_impl(rt: Dict[str, Any], cfg: Dict[str, Any], region: str, q: Dict[str, Any],
                        confirm_mb: Any) -> Dict[str, Any]:
    """Pobranie plików z planu q['plan'] po potwierdzeniu rozmiaru (opis kolejności: task_egms_download)."""
    import step_01_ingest as s1
    import step_04_egms_aoi as s4
    e = require_approved(cfg, "egms")
    reg = _region(cfg, region)
    P = region_paths(rt, cfg, region)
    token = Path(cfg["project"]["token_path"])
    if not token.is_file() and q["ready"]:
        return {"skipped": True, "message": f"brak tokenu CLMS ({token}): używam istniejących wycinków"}
    plan = _read_plan({"plan": q["plan"]})
    raw, man, proj = q["raw"], _manifest(rt, cfg), Path(rt["PROJECT_DIR"])
    registered = _in_manifest(man, [s1.manifest_path_of(raw / f, proj) for f in plan["filename"]])
    if (plan["need_bytes"] == 0).all() and all(registered) and all((raw / f).exists() for f in plan["filename"]):
        return {"skipped": True, "message": f"wszystkie {len(plan)} pliki z planu są na Dysku i w manifeście"}
    need = _check_confirm_mb(plan, confirm_mb, q["confirm_var"], q["plan"].name)
    if not token.is_file():
        raise FileNotFoundError(f"Brak tokenu CLMS {token}: pobranie niemożliwe")
    session, headers = _clms_session(cfg)
    area = _search_lonlat(reg, _sites_for_search(P), e["search_area"])
    table, results = _retry_transient(lambda: s4.search_plan(session, headers, s1.API_ENDPOINT, area, q["release"], q["levels"],
                                    q["l3_product_types"]), "wyszukanie EGMS")
    a = table.set_index("filename")["filesize"].astype("int64").sort_index()
    b = plan.set_index("filename")["filesize"].astype("int64").sort_index()
    if not a.equals(b):
        raise RuntimeError(f"Świeże wyszukanie różni się od planu (pliki: nowe {sorted(set(a.index) - set(b.index))[:5]}, "
                           f"brakujące {sorted(set(b.index) - set(a.index))[:5]}): uruchom ponownie wyszukanie "
                           f"i potwierdź nowy rozmiar")
    fresh = s4.plan_download(table, raw, s4.drive_free_bytes(raw), int(round(float(e["drive_margin_gb"]) * 1e9)))
    if _need_mb(fresh) > need:                 # potwierdzenie dotyczy planu z pliku; pobieramy według świeżego stanu Dysku
        raise RuntimeError(f"Do pobrania jest teraz {_need_mb(fresh)} MB, potwierdzono {need} MB (pliki zniknęły z Dysku "
                           f"po wyszukaniu?): uruchom ponownie task_egms_search i potwierdź nowy rozmiar")
    reg_now = _in_manifest(man, [s1.manifest_path_of(raw / f, proj) for f in fresh["filename"]])
    todo = fresh[(fresh["status"] != "existing") | ~np.array(reg_now)]
    logs = []
    for key, g in todo.groupby("query_key", sort=True):
        logs.append(s4.sync_files(session, headers, s1.API_ENDPOINT, results[key], list(g["filename"]), raw, man, proj,
                                  e["download_pause_s"], cfg["project"]["downloaded_by"]).assign(query_key=key))
    log = pd.concat(logs, ignore_index=True) if logs else pd.DataFrame(columns=["filename", "status", "bytes", "sha256"])
    q["log"].parent.mkdir(parents=True, exist_ok=True)
    log.to_csv(q["log"], index=False)
    return {"message": f"potwierdzone {need} MB; {log['status'].value_counts().to_dict()}"}


def task_egms_download(rt: Dict[str, Any], cfg: Dict[str, Any], region: str, confirm_mb: Any) -> Dict[str, Any]:
    """
    Pobranie plików z planu po potwierdzeniu rozmiaru (confirm_mb = MB z task_egms_search, zaokrąglone).
    Kolejność: plan -> (bez tokenu i z wycinkami: pominięte) -> blokada confirm_mb -> token -> świeże wyszukanie
    (identyfikator zapytania wygasa; wynik musi zgadzać się z planem) -> plan ponownie (miejsce) -> step_04.sync_files
    dla plików brakujących, niepełnych i istniejących bez wpisu w manifeście.
    """
    return _egms_download_impl(rt, cfg, region, _query_main(rt, cfg, region), confirm_mb)


def task_levelling_egms_download(rt: Dict[str, Any], cfg: Dict[str, Any], region: str, confirm_mb: Any) -> Dict[str, Any]:
    """Jak task_egms_download, dla drugiego wydania do porównania z niwelacją (CONFIRM_MB_<REGION>_LEVELLING)."""
    if _region(cfg, region).get("levelling") is None:
        return {"skipped": True, "message": f"region {region} bez niwelacji (levelling = None)"}
    return _egms_download_impl(rt, cfg, region, _query_levelling(rt, cfg, region), confirm_mb)


def task_extract(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    Wycinki z plików planu: L2b - step_02.extract_points wokół wszystkich punktów naziemnych (GNSS i repery)
    w promieniu extract_radius_m, plik po pliku (ścieżka i kierunek z planu); L3 U - step_04.l3_cells_at_sites
    (komórka przy punkcie, z datami) i step_04.read_l3_aoi (mapa obszaru, bez dat); opcjonalnie mapa L2b.
    Wycinki aktualne (nowsze niż pliki i sites.csv, te same parametry co w extract_params.json) = pominięte.
    Bez planu lub plików surowych: pominięte, gdy
    wycinki istnieją (tryb bez tokenu), inaczej FileNotFoundError. Zero punktów L2b / komórek L3 = RuntimeError.
    """
    import step_02_checks_extract as s2
    import step_04_egms_aoi as s4
    e = require_approved(cfg, "egms")
    reg = _region(cfg, region)
    m = require_approved(cfg, "method")
    P = region_paths(rt, cfg, region)
    raw = _abs(rt, e["raw_dir"])
    if not P["plan"].exists():
        if _extracts_exist(P, cfg):
            return {"skipped": True, "message": "brak planu EGMS (tryb bez tokenu): używam istniejących wycinków"}
        raise FileNotFoundError(f"Brak planu {P['plan']}: uruchom task_egms_search i task_egms_download")
    plan = _read_plan(P)
    absent = [f for f, n in zip(plan["filename"], plan["filesize"]) if not ((raw / f).exists()
                                                                          and (raw / f).stat().st_size == int(n))]
    if absent:
        if _extracts_exist(P, cfg) and not Path(cfg["project"]["token_path"]).is_file():
            return {"skipped": True, "message": f"{len(absent)} plików surowych brak (bez tokenu): używam wycinków"}
        raise FileNotFoundError(f"{len(absent)} plików z planu brak w {raw} (np. {absent[:3]}): uruchom task_egms_download")
    sites = _read_sites(P)
    pts_xy = sites[["site", "x_3035", "y_3035"]]
    # L2b przy punkcie czyta tylko porównanie z GNSS (task_compare_gnss); repery porównuje się z L3 (komórka przy
    # reperze). Wycinek L2b wokół wszystkich reperów NRW (13 476 x promień 200 m = ok. 1 mln punktów z pełnymi
    # szeregami na plik) przepełniał pamięć Colab (2026-10-12), dlatego L2b tylko wokół site_type z L2B_SITE_TYPES.
    pts_l2b = sites.loc[sites["site_type"].isin(L2B_SITE_TYPES), ["site", "x_3035", "y_3035"]]
    l2 = plan[plan["level"] == "L2B"]
    l3 = plan[(plan["level"] == "L3") & (plan["product_type"] == "ORTHO-UP")]
    outputs = ([P["l2b_points"]] if len(l2) else []) + ([P["l3_cells"], P["l3_map"]] if len(l3) else []) + \
              ([P["l2b_map"]] if e["l2b_aoi_map"] and len(l2) else [])
    if not outputs:
        raise ValueError(f"Plan bez plików L2B i L3 ORTHO-UP: nie ma czego wycinać ({plan['query_key'].unique()})")
    # Parametry wycinków zapisane obok nich: zmiana promienia, komórki L3, obszaru albo listy plików unieważnia wycinki
    # (sam czas modyfikacji tego nie wykrywa - stary wycinek byłby po cichu użyty z nową konfiguracją).
    params = {"extract_radius_m": m["extract_radius_m"], "l3_cell_m": m["l3_cell_m"],
              "aoi_lonlat": [float(v) for v in reg["aoi_lonlat"]], "l2b_aoi_map": bool(e["l2b_aoi_map"]),
              "l2b_site_types": list(L2B_SITE_TYPES),
              "files": sorted(str(f) for f in plan["filename"])}
    pfile = P["extracts"] / "extract_params.json"
    same = pfile.exists() and json.loads(pfile.read_text(encoding="utf-8")) == params
    if same and _up_to_date(outputs, [raw / f for f in plan["filename"]] + [P["sites"]]):
        return {"skipped": True, "message": "wycinki aktualne (nowsze niż pliki EGMS i sites.csv, te same parametry)"}
    if pfile.exists() and not same:
        print(f"Parametry wycinków różne od zapisanych w {pfile.name}: wycinam od nowa")
    msg = []
    aoi3035 = s4.aoi_lonlat_to_3035(reg["aoi_lonlat"])
    if len(l2):
        if pts_l2b.empty:
            raise RuntimeError(f"Plan zawiera pliki L2B, ale w sites.csv nie ma punktów typu {list(L2B_SITE_TYPES)} "
                               f"(L2b porównuje się tylko z GNSS): uruchom task_select_gnss albo usuń L2B z egms.levels")
        print(f"L2b: wycinek wokół {len(pts_l2b)} punktów typu {list(L2B_SITE_TYPES)} (z {len(sites)} w sites.csv)")
        parts, maps = [], []
        for r in l2.itertuples(index=False):
            p = s4.extract_points_l2b(raw / r.filename, pts_l2b, m["extract_radius_m"], e["chunksize"], s4.L2B_USED)
            print(f"{r.filename}: {len(p)} punktów w promieniu {m['extract_radius_m']} m")
            if len(p):
                parts.append(p.assign(track=int(r.relativeOrbit), direction=r.direction))
            if e["l2b_aoi_map"]:
                maps.append(s4.extract_l2b_velocity_map(raw / r.filename, aoi3035, e["chunksize"])
                            .assign(track=int(r.relativeOrbit), direction=r.direction, source_file=r.filename))
        if not parts:
            raise RuntimeError(f"Brak punktów L2b w promieniu {m['extract_radius_m']} m od żadnego punktu naziemnego")
        points = _order_columns(pd.concat(parts, ignore_index=True))
        P["l2b_points"].parent.mkdir(parents=True, exist_ok=True)
        points.to_csv(P["l2b_points"], index=False)
        cnt = points.groupby(["track", "direction"])["site"].nunique().to_dict()
        msg.append(f"L2b: {len(points)} wierszy, punkty naziemne z danymi na ścieżkę {cnt}")
        if e["l2b_aoi_map"]:
            mp = pd.concat(maps, ignore_index=True)
            if mp.empty:
                raise RuntimeError("Mapa L2b: brak punktów w obszarze")
            mp.to_csv(P["l2b_map"], index=False)
    if len(l3):
        zips = [raw / f for f in l3["filename"]]
        cells = s4.l3_cells_at_sites(zips, sites, m["l3_cell_m"], e["chunksize"])
        if cells.empty:
            raise RuntimeError("Żaden punkt naziemny nie leży w komórce L3")
        cells.to_csv(P["l3_cells"], index=False)
        maps = [s4.read_l3_aoi(z, aoi3035, e["chunksize"], False).assign(source_file=z.name) for z in zips]
        mp = pd.concat([x for x in maps if len(x)], ignore_index=True) if any(len(x) for x in maps) else pd.DataFrame()
        if mp.empty:
            raise RuntimeError(f"Mapa L3: brak komórek w obszarze {reg['aoi_lonlat']} we wszystkich kaflach")
        mp.to_csv(P["l3_map"], index=False)
        msg.append(f"L3: komórki przy {cells['site'].nunique()} z {len(sites)} punktów, mapa {len(mp)} komórek")
    pfile.write_text(json.dumps(params, indent=1), encoding="utf-8")
    return {"message": "; ".join(msg)}


def task_levelling_extract(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    Komórki L3 (U) drugiego wydania (regions.<region>.levelling.egms_check) przy wszystkich reperach z sites.csv
    (step_04.l3_cells_at_sites, jak w task_extract; bez wyboru według EGMS) i mapa prędkości L3 obszaru regionu
    (step_04.read_l3_aoi, jak mapa wydania głównego). Każdy z dwóch wycinków liczony tylko, gdy nieaktualny (komórki:
    nowsze niż pliki i sites.csv, te same parametry; mapa: nowsza niż pliki). Bez planu: pominięty, gdy wycinek
    istnieje i nie ma tokenu, inaczej FileNotFoundError. Zero reperów w komórkach albo pusta mapa = RuntimeError.
    """
    import step_04_egms_aoi as s4
    e = require_approved(cfg, "egms")
    if _region(cfg, region).get("levelling") is None:
        return {"skipped": True, "message": f"region {region} bez niwelacji (levelling = None)"}
    m = require_approved(cfg, "method")
    q = _query_levelling(rt, cfg, region)
    C, P = levelling_check_paths(rt, cfg, region), region_paths(rt, cfg, region)
    no_token = not Path(cfg["project"]["token_path"]).is_file()
    if not q["plan"].exists():
        if q["ready"] and no_token:
            return {"skipped": True, "message": f"brak planu (tryb bez tokenu): używam {C['l3_cells'].name}"}
        raise FileNotFoundError(f"Brak planu {q['plan']}: uruchom task_levelling_egms_search i task_levelling_egms_download")
    plan = _read_plan({"plan": q["plan"]})
    l3 = plan[(plan["level"] == "L3") & (plan["product_type"] == "ORTHO-UP")]
    if l3.empty:
        raise ValueError(f"Plan {q['plan'].name} bez plików L3 ORTHO-UP ({plan['query_key'].unique()})")
    zips = [q["raw"] / f for f in l3["filename"]]
    absent = [z.name for z, n in zip(zips, l3["filesize"]) if not (z.exists() and z.stat().st_size == int(n))]
    if absent:
        if q["ready"] and no_token:
            return {"skipped": True, "message": f"{len(absent)} plików surowych brak (bez tokenu): używam {C['l3_cells'].name}"}
        raise FileNotFoundError(f"{len(absent)} plików L3 z planu brak w {q['raw']} (np. {absent[:3]}): "
                                f"uruchom task_levelling_egms_download")
    sites = _read_sites(P)
    bench = sites.loc[sites["site_type"] == "benchmark", ["site", "x_3035", "y_3035"]]
    if bench.empty:
        raise RuntimeError(f"{P['sites']}: brak reperów - uruchom task_levelling")
    params = {"release": str(q["release"]), "l3_cell_m": m["l3_cell_m"], "files": sorted(str(f) for f in l3["filename"])}
    same = C["params"].exists() and json.loads(C["params"].read_text(encoding="utf-8")) == params
    cells_ok = same and _up_to_date([C["l3_cells"]], zips + [P["sites"]])
    map_ok = _up_to_date([C["l3_map"]], zips)
    if cells_ok and map_ok:
        return {"skipped": True, "message": f"wycinki aktualne ({C['l3_cells'].name}, {C['l3_map'].name}: nowsze niż pliki)"}
    msg = []
    C["l3_cells"].parent.mkdir(parents=True, exist_ok=True)
    if not cells_ok:
        cells = s4.l3_cells_at_sites(zips, bench, m["l3_cell_m"], e["chunksize"])
        if cells.empty:
            raise RuntimeError(f"Żaden z {len(bench)} reperów nie leży w komórce L3 wydania {q['release']}")
        cells.to_csv(C["l3_cells"], index=False)
        C["params"].write_text(json.dumps(params, indent=1), encoding="utf-8")
        d = _date_cols(cells)
        msg.append(f"L3 {q['release']}: komórki przy {cells['site'].nunique()} z {len(bench)} reperów; "
                   f"daty {d[0]} - {d[-1]} ({len(d)})")
    if not map_ok:
        aoi = _region(cfg, region)["aoi_lonlat"]
        maps = [x for x in (s4.read_l3_aoi(z, s4.aoi_lonlat_to_3035(aoi), e["chunksize"], False) for z in zips) if len(x)]
        if not maps:
            raise RuntimeError(f"Mapa L3 {q['release']}: brak komórek w obszarze {aoi} we wszystkich kaflach")
        mp = pd.concat(maps, ignore_index=True)
        mp.to_csv(C["l3_map"], index=False)
        msg.append(f"mapa L3 {q['release']}: {len(mp)} komórek")
    return {"message": "; ".join(msg)}


def task_checks(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    Kontrole przed porównaniem (F4_metodyka, sekcja 2): A1-A3 (step_02.check_conventions), A5 duplikaty z zakładek
    burstów (usunięte; wynik w egms_l2b_points_dedup.csv.gz) i siatka L3 (step_04.l3_grid_offsets: easting/northing
    = środki komórek, reszta cell_m/2). Tabela kontroli zapisana zawsze; niespełniona kontrola = RuntimeError.
    """
    import step_02_checks_extract as s2
    import step_04_egms_aoi as s4
    e = require_approved(cfg, "egms")
    _region(cfg, region)
    m = require_approved(cfg, "method")
    P = region_paths(rt, cfg, region)
    rows = []
    if "L2B" in e["levels"]:
        points = _read_points(P["l2b_points"], "wycinek L2b: task_extract")
        checks = s2.check_conventions(points, m["conv_tol"])
        d = s2.nearest_cross_file_distance(points)
        dedup, n_dup = s2.drop_cross_file_duplicates(points, m["duplicate_dist_m"])
        rows.append(checks)
        rows.append(pd.DataFrame([{"check": "A5 duplikaty z zakładek burstów (usunięte)", "track": "all",
                                   "value": f"{n_dup} pkt; odległość do najbliższego z innego pliku: mediana "
                                            f"{d.median():.2f} m" if d.notna().any() else f"{n_dup} pkt; jeden plik na ścieżkę",
                                   "threshold": f"< {m['duplicate_dist_m']} m = duplikat", "pass": True}]))
        dedup.to_csv(P["l2b_dedup"], index=False)
        if "A3 znak los_east: wstępująca = -zstępująca" not in set(checks["check"]):
            print("UWAGA: A3 nie sprawdzone - w wycinku jest tylko jeden kierunek orbity.")
    if "L3" in e["levels"]:
        mp = _read_points(P["l3_map"], "mapa L3: task_extract")
        off = s4.l3_grid_offsets(mp, m["l3_cell_m"])
        off.to_csv(P["l3_grid"], index=False)
        half = m["l3_cell_m"] / 2.0
        ok = bool(((off["easting_mod"] == half) & (off["northing_mod"] == half)).all())
        rows.append(pd.DataFrame([{"check": "L3 siatka: easting/northing = środki komórek", "track": "L3",
                                   "value": "; ".join(f"({r.easting_mod:g}, {r.northing_mod:g}): {r.n_cells}"
                                                      for r in off.head(5).itertuples()),
                                   "threshold": f"reszta modulo {m['l3_cell_m']} = ({half:g}, {half:g})", "pass": ok}]))
    tab = pd.concat(rows, ignore_index=True)
    tab["pass"] = tab["pass"].astype(bool)
    P["checks"].parent.mkdir(parents=True, exist_ok=True)
    tab.to_csv(P["checks"], index=False)
    print(tab.to_string(index=False))
    if not tab["pass"].all():
        raise RuntimeError(f"Kontrola konwencji nie przeszła (F4, sekcja 2): {tab.loc[~tab['pass'], 'check'].tolist()}; "
                           f"porównanie wstrzymane. Tabela: {P['checks']}")
    return {"message": f"{len(tab)} kontroli spełnionych"}


# ------------------------------------------------------------------------------
# Porównania: GNSS, niwelacja
# ------------------------------------------------------------------------------
def _check_radii(m: Dict[str, Any]) -> None:
    """
    Spójność promieni sekcji method: radius_main_m w radii_m (inaczej step_03.verdict nie ma par) i każdy promień
    <= extract_radius_m (wycinek L2b nie zawiera punktów dalszych - liczba punktów byłaby po cichu zaniżona).
    """
    if m["radius_main_m"] not in m["radii_m"]:
        raise ValueError(f"method.radius_main_m {m['radius_main_m']} spoza method.radii_m {m['radii_m']}")
    too_far = [r for r in m["radii_m"] if r > m["extract_radius_m"]]
    if too_far:
        raise ValueError(f"method.radii_m {too_far} > extract_radius_m {m['extract_radius_m']} (zasięg wycinka L2b)")


def _l3_radius(m: Dict[str, Any]) -> float:
    """Komórka L3 zawierająca punkt: odległość do środka <= cell_m * sqrt(2) / 2."""
    return float(m["l3_cell_m"]) * np.sqrt(2.0) / 2.0


def _verdict_l3(res_l3: pd.DataFrame, view: Dict[str, Any], th_l3: Dict[str, Any]) -> tuple:
    """
    step_03.verdict na wynikach L3: progi zdefiniowane tylko dla K1 (thresholds.gnss_l3u). Brakujące progi
    (series_std_mm, stable_abs_v_mm_yr) podane jako NaN tylko po to, by verdict policzył wartości; te wiersze
    dostają 'próg' = brak progu i 'spełnione' = None (informacyjnie). Wniosek tylko z K1.
    """
    import step_03_compare_gnss as s3
    th = {"abs_dv_mm_yr": th_l3["abs_dv_mm_yr"], "share_within": th_l3["share_within"],
          "series_std_mm": np.nan, "stable_abs_v_mm_yr": np.nan}
    v = s3.verdict(res_l3, {**view, "thresholds": th})
    undefined = v["kryterium"].str[:2].isin(["K2", "K3"])
    v.loc[undefined, "próg"] = "brak progu w CHECK_CONFIG['thresholds']['gnss_l3u'] (informacyjnie)"
    v.loc[undefined, "spełnione"] = None
    k1 = v.loc[v["kryterium"].str[:2] == "K1", "spełnione"]
    if k1.empty:
        concl = "L3: brak par stacja osiadająca x L3 ze statusem 'ok' i A6 - K1 niepoliczalne."
    elif bool(k1.iat[0]):
        concl = "L3 (pion): K1 spełnione - tempo osiadania z EGMS L3 zgodne z GNSS (U) w granicach progu."
    else:
        concl = "L3 (pion): K1 niespełnione - tempo osiadania z EGMS L3 różni się od GNSS (U) ponad próg."
    return v, concl


def _k3_abs_dv(v: pd.DataFrame, res: pd.DataFrame, view: Dict[str, Any]) -> pd.DataFrame:
    """
    K3 w wariancie 'abs_dv': max |dv| na stacjach stabilnych zamiast max |v_EGMS| (ten sam filtr par co
    step_03.verdict, więc wiersz K3 istnieje dokładnie wtedy, gdy są pary stabilne); wiersz zastąpiony na miejscu.
    """
    th = view["thresholds"]["stable_abs_v_mm_yr"]
    r = res[(res["radius_m"] == view["radius_main_m"]) & (res["status"] == "ok") & res["meets_A6"].fillna(False).astype(bool)]
    stab = r[r["group"] == "stabilna"]
    idx = v.index[v["kryterium"].str[:2] == "K3"]
    if len(idx) != (1 if len(stab) else 0):
        raise RuntimeError(f"K3: {len(idx)} wierszy w werdykcie, {len(stab)} par stabilnych - niespójny filtr")
    if len(stab):
        worst = float(stab["dv"].abs().max())
        v = v.copy()
        v.loc[idx[0], ["kryterium", "wynik", "próg", "spełnione", "n_par"]] = [
            "K3 kontrola negatywna (stacje stabilne, |dv|)", f"max |dv| {worst:.2f} mm/rok", f"<= {th} mm/rok",
            worst <= th, len(stab)]
    return v


def task_compare_gnss(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    EGMS kontra GNSS dla KAŻDEJ pary stacja x ścieżka L2B z planu (LOS, promienie radii_m) i stacja x L3 (U):
    step_03.compare_station_track bez zmian; para bez punktów w wycinku dostaje jawny wiersz statusu (nie znika;
    N3b). Werdykt step_03.verdict (L2b: progi gnss_l2b, K3 według k3_definition; L3: tylko K1, gnss_l3u).
    Wymaga zatwierdzenia sekcji thresholds.
    """
    import step_03_compare_gnss as s3
    e = require_approved(cfg, "egms")
    _region(cfg, region)
    m = require_approved(cfg, "method")
    th = require_approved(cfg, "thresholds")
    P = region_paths(rt, cfg, region)
    sites = _read_sites(P)
    gn = sites[sites["site_type"] == "gnss"]
    if gn.empty:
        return {"skipped": True, "message": f"region {region}: brak stacji GNSS - porównanie nie jest liczone"}
    k3 = _decided(th["gnss_l2b"], "k3_definition", "thresholds.gnss_l2b")
    if k3 not in ("abs_v_egms", "abs_dv"):
        raise ValueError(f"thresholds.gnss_l2b.k3_definition {k3!r}: dozwolone 'abs_v_egms', 'abs_dv'")
    _check_radii(m)
    gnss = _read_gnss(rt, cfg, list(gn["site"]))
    src = _sources(cfg)
    grp = dict(zip(gn["site"], gn["group"]))
    view = {"min_points": m["min_points"], "gnss_half_window_days": m["gnss_half_window_days"],
            "velocity_model": m["velocity_model"], "min_overlap": m["min_overlap"], "radius_main_m": m["radius_main_m"],
            "thresholds": {k: th["gnss_l2b"][k] for k in ("abs_dv_mm_yr", "share_within", "series_std_mm",
                                                          "stable_abs_v_mm_yr")}}
    rows = []
    if "L2B" in e["levels"]:
        tracks = _l2b_tracks(_read_plan(P))
        points = _read_points(P["l2b_dedup"], "wycinek L2b bez duplikatów: task_checks")
        for site in gn["site"]:
            for track, direction in tracks.items():
                p = points[(points["site"] == site) & (points["track"] == track)]
                for radius in m["radii_m"]:
                    if p.empty:
                        res = {"radius_m": radius, "n_points": 0, "meets_A6": False,
                               "status": f"brak punktów EGMS L2b w wycinku (promień {m['extract_radius_m']} m)"}
                    else:
                        res = s3.compare_station_track(p, _track_date_cols(p), gnss[site], radius, view)
                    rows.append({"product": src["L2B"], "site": site, "group": grp[site], "track": track,
                                 "direction": direction, **res})
    view_l3 = {**view, "min_points": m["l3_min_points"], "radius_main_m": _l3_radius(m)}
    if "L3" in e["levels"]:
        cells = _read_points(P["l3_cells"], "komórki L3: task_extract")
        dc = _date_cols(cells)
        for site in gn["site"]:
            c = cells[cells["site"] == site]
            if c.empty:
                res = {"radius_m": _l3_radius(m), "n_points": 0, "meets_A6": False,
                       "status": "brak komórki L3 zawierającej punkt"}
            else:
                res = s3.compare_station_track(c, dc, gnss[site], _l3_radius(m), view_l3)
            rows.append({"product": src["L3"], "site": site, "group": grp[site], "track": "L3", "direction": "vertical",
                         **res})
    results = pd.DataFrame(rows)
    results.insert(0, "region", region)
    P["gnss_compare"].parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(P["gnss_compare"], index=False)
    msg = []
    r2 = results[results["product"] == src["L2B"]]
    if len(r2):
        v2 = s3.verdict(r2, view)
        if k3 == "abs_dv":
            v2 = _k3_abs_dv(v2, r2, view)
        # Bez wiersza K1 step_03.overall zwraca "NIE POTWIERDZONE: ... różni się ponad progi" - fałszywy wniosek, gdy
        # K1 nie da się policzyć (np. reguła 'all_quality' bez stacji osiadających albo żadna para bez A6).
        if (v2["kryterium"].str[:2] == "K1").any():
            concl2 = s3.overall(v2)
        else:
            concl2 = ("NIEROZSTRZYGNIĘTE: brak par stacja osiadająca x ścieżka L2b ze statusem 'ok' i A6 na promieniu "
                      f"{m['radius_main_m']} m - K1 niepoliczalne, wniosek o tempie osiadania nie jest możliwy.")
        v2.to_csv(P["verdict_l2b"], index=False)
        print(v2.to_string(index=False))
        msg.append(f"L2b: {concl2}")
        with open(P["verdict_l2b"].with_suffix(".txt"), "w", encoding="utf-8") as f:
            f.write(concl2 + "\n")
    r3 = results[results["product"] == src["L3"]]
    if len(r3):
        v3, concl3 = _verdict_l3(r3, view_l3, th["gnss_l3u"])
        v3.to_csv(P["verdict_l3u"], index=False)
        print(v3.to_string(index=False))
        msg.append(concl3)
        with open(P["verdict_l3u"].with_suffix(".txt"), "w", encoding="utf-8") as f:
            f.write(concl3 + "\n")
    n_ok = int((results["status"] == "ok").sum())
    reg_rows = _metric_rows(results.assign(n=results.get("n_dates", np.nan)), region, GNSS_METRICS + ["n_points"], "n",
                            GNSS_REFERENCE)
    return {"message": f"{len(results)} wierszy (status ok: {n_ok}); " + " | ".join(msg),
            "registry": {"gwl_validation_metrics": reg_rows}}


def _levelling_l3_long(region: str, P: Dict[str, Path], cells_path: Path, source: str, m: Dict[str, Any]) -> tuple:
    """Szeregi EGMS L3 (U) przy reperach w formacie długim (step_07.egms_points_to_long) + statusy par."""
    import step_07_monitoring as s7
    sites = _read_sites(P)
    bench = sites.loc[sites["site_type"] == "benchmark", "site"].tolist()
    if not bench:
        raise RuntimeError(f"{P['sites']}: brak reperów - uruchom task_levelling")
    cells = _read_points(cells_path, f"komórki L3 przy reperach ({source})")
    c = cells[cells["site"].isin(bench)]
    expected = pd.DataFrame({"site": bench, "track": "L3", "direction": "vertical"})
    return s7.egms_points_to_long(c if len(c) else pd.DataFrame(), _date_cols(cells), region, source,
                                  _l3_radius(m), m["l3_min_points"], expected)


def _compare_levelling_core(rt: Dict[str, Any], cfg: Dict[str, Any], region: str, cells_path: Path, source: str,
                            out: Dict[str, Path]) -> tuple:
    """
    Wspólny rdzeń porównania z niwelacją (task_compare_levelling, task_compare_levelling_check): szeregi L3 przy
    reperach z cells_path, epoki w oknie dat tych szeregów, Δh (step_06.compare_levelling), N1-N4. Zapis statusów
    (out['status']) i podsumowania (out['summary']); wynik porównania zwracany (zapis robi wywołujący).
    Zwraca (lev, res, summ, t0, t1, wiersze rejestru, opis kryteriów, szeregi EGMS w formacie długim).
    """
    import step_06_ground as s6
    require_approved(cfg, "egms")
    lv = _region(cfg, region)["levelling"]
    path = f"regions.{region}.levelling"
    m = require_approved(cfg, "method")
    th = require_approved(cfg, "thresholds")
    ref = _decided(lv, "reference", path)
    method, rule = _decided(lv, "read_method", path), _decided(lv, "epoch_rule", path)
    span = _decided(lv, "min_epoch_span_yr", path)
    P = region_paths(rt, cfg, region)
    lev = _read_levelling(P)
    long_u, st_u = _levelling_l3_long(region, P, cells_path, source, m)
    out["status"].parent.mkdir(parents=True, exist_ok=True)
    st_u.to_csv(out["status"], index=False)
    if long_u.empty:
        raise RuntimeError(f"Żaden reper nie ma szeregu EGMS L3 {source} (statusy: {out['status']})")
    t0, t1 = long_u["date"].min(), long_u["date"].max()
    ep = s6.epochs_in_release(lev, t0, t1, rule, span)
    res = s6.compare_levelling(lev, ep, long_u, ref, method)
    summ = s6.summarize_levelling(res, th["levelling_l3u"])
    summ.to_csv(out["summary"], index=False)
    print(summ.to_string(index=False))
    reg_rows = _metric_rows(res.assign(product=source, site=res["benchmark_id"], track="L3",
                                       radius_m=_l3_radius(m), n=1.0), region, LEVELLING_METRICS, "n", LEVELLING_REFERENCE)
    crit = "; ".join(f"{k[:2]}: {v}" for k, v in zip(summ["kryterium"], summ["spełnione"])
                     if str(k)[:1] == "N" and str(k)[1:2].isdigit())
    return lev, res, summ, t0, t1, reg_rows, crit, long_u


def task_compare_levelling(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    EGMS L3 (pion) kontra niwelacja (step_06): szeregi L3 przy reperach (step_07.egms_points_to_long, reper bez
    komórki = status), epoki w oknie dat EGMS (step_06.epochs_in_release; okno = pierwsza i ostatnia data szeregów L3),
    Δh i prędkości (step_06.compare_levelling, odniesienie z konfiguracji), kryteria N1-N4 (summarize_levelling).
    """
    require_approved(cfg, "egms")
    if _region(cfg, region).get("levelling") is None:
        return {"skipped": True, "message": f"region {region} bez niwelacji (levelling = None)"}
    P = region_paths(rt, cfg, region)
    _, res, _, t0, t1, reg_rows, crit, _ = _compare_levelling_core(
        rt, cfg, region, P["l3_cells"], _sources(cfg)["L3"],
        {"status": P["levelling_status"], "summary": P["levelling_summary"]})
    res.to_csv(P["levelling_compare"], index=False, date_format="%Y-%m-%d")
    return {"message": f"{int((res['status'] == 'ok').sum())} z {len(res)} reperów 'ok' (okno {t0.date()} - "
                       f"{t1.date()}); {crit}", "registry": {"gwl_validation_metrics": reg_rows}}


def _latest_midas(rt: Dict[str, Any], cfg: Dict[str, Any]) -> pd.DataFrame:
    """Najnowsza migawka MIDAS z Dysku (task_select_gnss); brak migawki = FileNotFoundError."""
    import step_01_ingest as s1
    gdir = _abs(rt, cfg["project"]["gnss_dir"])
    snapshots = sorted(gdir.glob("midas_*.IGS.txt"))
    if not snapshots:
        raise FileNotFoundError(f"Brak migawki midas_*.IGS.txt w {gdir}: uruchom task_select_gnss")
    return s1.read_ngl_midas(snapshots[-1].read_text(encoding="utf-8"))


def _levelling_check_examples(res: pd.DataFrame, rule: str, strong_mm_yr: float) -> List[Tuple[str, str]]:
    """
    Repery do rycin szeregów, regułą bez wyboru ręcznego: monitoring.example_rule dla niwelacji (najszybsze osiadanie,
    mediana v_niw, najmniejsze |v_niw|) oraz reper o medianie v_niw w nieckach (|v_niw| >= strong_mm_yr; podział
    według niwelacji, autor 2026-10-12). Zwraca (benchmark_id, opis reguły) bez powtórzeń.
    """
    empty = pd.DataFrame(columns=["site", "site_type", "group", "vu_mm_yr"])
    base = _example_sites(empty, res, rule)
    labels = ["fastest subsidence by levelling", "median rate, all benchmarks", "smallest |rate|, stable"]
    out = list(zip(base, labels[:len(base)]))
    ok = res[res["status"] == "ok"]
    bowls = ok[ok["v_lev_mm_yr"].abs() >= strong_mm_yr].sort_values("v_lev_mm_yr")
    if len(bowls):
        out.append((str(bowls["benchmark_id"].iat[len(bowls) // 2]), f"median rate in bowls (|v| >= {strong_mm_yr:g} mm/yr)"))
    seen, uniq = set(), []
    for bid, lab in out:
        if bid not in seen:
            seen.add(bid)
            uniq.append((bid, lab))
    return uniq


def _egms_sigma_at_benchmarks(cells_path: Path, sigma_column: str) -> pd.DataFrame:
    """
    Niepewność EGMS przy reperze z komórki L3 (jedna komórka na reper, step_04.l3_cells_at_sites): egms_rmse_mm =
    kolumna sigma_column, sigma_dh_mm = sqrt(2) * rmse (Δh = różnica dwóch odczytów; interpolacja między sąsiednimi
    datami pominięta - zachowawczo). Brak kolumny = KeyError; komórka bez wartości = NaN (jawnie, liczone w raporcie).
    """
    cells = _read_points(cells_path, "komórki L3 przy reperach: task_levelling_extract")
    if sigma_column not in cells.columns:
        raise KeyError(f"{cells_path.name}: brak kolumny {sigma_column!r} (CHECK_CONFIG ...levelling.uncertainty."
                       f"egms_sigma_column); kolumny bez dat: {[c for c in cells.columns if not str(c).isdigit()]}")
    if cells["site"].duplicated().any():
        raise ValueError(f"{cells_path.name}: więcej niż jedna komórka przy reperze {cells.loc[cells['site'].duplicated(), 'site'].tolist()[:5]}")
    rmse = pd.to_numeric(cells[sigma_column], errors="raise").to_numpy(float)
    return pd.DataFrame({"benchmark_id": cells["site"].astype(str).to_numpy(), "egms_rmse_mm": rmse,
                         "sigma_dh_mm": np.sqrt(2.0) * rmse})


def _levelling_series_long(long_u: pd.DataFrame, lev: pd.DataFrame, row: pd.Series, region: str) -> pd.DataFrame:
    """
    Szereg EGMS (pion) i epoki niwelacji jednego reperu w formacie długim, oba wyzerowane w pierwszej epoce porównania
    t1 (EGMS: interpolacja liniowa w t1, jak w porównaniu; bez ekstrapolacji). Epoki niwelacji z okna szeregu EGMS.
    """
    bid, t1 = str(row["benchmark_id"]), pd.Timestamp(row["t1"])
    e = long_u[(long_u["site"].astype(str) == bid) & long_u["disp_mm"].notna()].sort_values("date")
    if e.empty:
        raise ValueError(f"Reper {bid}: brak szeregu EGMS")
    d = pd.DatetimeIndex(e["date"])
    if not d[0] <= t1 <= d[-1]:
        raise ValueError(f"Reper {bid}: epoka {t1.date()} poza szeregiem EGMS {d[0].date()} - {d[-1].date()}")
    # Jedna jednostka czasu po obu stronach: Timestamp.value jest zawsze w ns, a asi8 w jednostce indeksu (pandas 3: us).
    e0 = float(np.interp(t1.as_unit("ns").value, d.as_unit("ns").asi8, e["disp_mm"].to_numpy(float)))
    e = e.assign(disp_mm=e["disp_mm"] - e0, ref_date=t1)
    g = lev[(lev["benchmark_id"].astype(str) == bid) & (lev["epoch_date"] >= d[0]) & (lev["epoch_date"] <= d[-1])]
    g = g.sort_values("epoch_date")
    h1 = float(g.loc[g["epoch_date"] == t1, "height_m"].iat[0]) * 1000.0
    lv = pd.DataFrame({"region": region, "source": LEVELLING_REFERENCE, "site": bid, "track": "vertical",
                       "direction": "vertical", "component": "U", "los_east": 0.0, "los_north": 0.0, "los_up": 1.0,
                       "date": pd.DatetimeIndex(g["epoch_date"]).normalize(), "disp_mm": g["height_m"].to_numpy(float) * 1000.0 - h1,
                       "ref_date": t1, "reference": "absolute", "n_points": np.nan})
    return pd.concat([e.assign(reference="absolute"), lv], ignore_index=True)


def task_compare_levelling_check(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    EGMS L3 (pion) drugiego wydania (regions.<region>.levelling.egms_check) kontra niwelacja: ten sam rdzeń co
    task_compare_levelling (wszystkie repery z parą epok w oknie dat szeregów; N1-N4 z thresholds.levelling_l3u bez
    zmian), osobne pliki wyników z rokiem wydania. Dodatkowo, informacyjnie (bez progów; autor 2026-10-12):
    odległość reperu do najbliższej stacji GNSS NGL (wszystkie stacje z migawki MIDAS - przybliżenie sieci, którą
    kalibrowany jest EGMS; sama sieć kalibracji nie jest publikowana przy plikach), podział niecki / pozostałe według
    niwelacji (strong_motion_mm_yr) i rycina Δh EGMS względem Δh niwelacji.
    """
    import matplotlib.pyplot as plt
    import step_06_ground as s6
    import step_07_monitoring as s7
    require_approved(cfg, "egms")
    reg = _region(cfg, region)
    if reg.get("levelling") is None:
        return {"skipped": True, "message": f"region {region} bez niwelacji (levelling = None)"}
    path = f"regions.{region}.levelling"
    strong = _decided(reg["levelling"], "strong_motion_mm_yr", path)
    th = require_approved(cfg, "thresholds")["levelling_l3u"]
    q = _query_levelling(rt, cfg, region)
    C = levelling_check_paths(rt, cfg, region)
    source = _sources_of(q["release"])["L3"]
    lev, res, _, t0, t1, reg_rows, crit, long_u = _compare_levelling_core(rt, cfg, region, C["l3_cells"], source,
                                                                  {"status": C["status"], "summary": C["summary"]})
    xy = lev.drop_duplicates("benchmark_id").rename(columns={"benchmark_id": "id"})[["id", "x_3035", "y_3035"]]
    xy["id"] = xy["id"].astype(str)
    ok_ids = set(res.loc[res["status"] == "ok", "benchmark_id"].astype(str))
    near = s6.nearest_station_km(xy[xy["id"].isin(ok_ids)], _latest_midas(rt, cfg)).rename(columns={"id": "benchmark_id"})
    res = res.assign(benchmark_id=res["benchmark_id"].astype(str))

    # Niepewność EGMS przy reperze (autor 2026-10-15, informacyjnie): rmse komórki L3, sigma_Δh = sqrt(2) * rmse.
    unc = _decided(reg["levelling"], "uncertainty", path)
    sig_col = _decided(unc, "egms_sigma_column", f"{path}.uncertainty")
    k_sig = float(_decided(unc, "k_sigma", f"{path}.uncertainty"))
    sig = _egms_sigma_at_benchmarks(C["l3_cells"], sig_col)

    def with_dist(df: pd.DataFrame) -> pd.DataFrame:
        return (df.assign(benchmark_id=df["benchmark_id"].astype(str)).merge(near, on="benchmark_id", how="left")
                .merge(sig, on="benchmark_id", how="left"))

    def report(df: pd.DataFrame, compare_p: Path, groups_p: Path, fig_p: Path, title: str) -> pd.DataFrame:
        df.to_csv(compare_p, index=False, date_format="%Y-%m-%d")
        groups = s6.levelling_groups(df, strong, th["sign_min_signal_mm"])
        groups.to_csv(groups_p, index=False)
        print("Podział informacyjny (bez progów; niecki według niwelacji):")
        print(groups.to_string(index=False))
        fig = s7.plot_levelling_scatter(df, float(strong), title, k_sig)
        fig_p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(fig_p, dpi=150, facecolor=fig.get_facecolor())
        plt.close(fig)
        return groups

    print(f"=== Wariant główny 'absolute' ({source}) ===")
    res_x = with_dist(res)
    groups = report(res_x, C["compare"], C["groups"], C["figure"],
                    f"EGMS L3 vertical {q['release']} vs levelling, {region}")
    # Wariant dodatkowy (autor 2026-10-13): oba zbiory względem grupy stabilnej według niwelacji; werdykt główny bez zmian.
    variant = _decided(reg["levelling"], "relative_variant", path)
    if variant not in s6.RELATIVE_VARIANTS:
        raise ValueError(f"CHECK_CONFIG['{path}']['relative_variant'] = {variant!r}: dozwolone {s6.RELATIVE_VARIANTS}")
    print(f"=== Wariant dodatkowy '{variant}' (metodyka F4 sekcja 10; policzony po wyniku 'absolute') ===")
    rel, info = s6.relative_to_stable_group(res[s6.COMPARE_COLUMNS], th["stable_max_lev_mm"])
    summ_rel = s6.summarize_levelling(rel, th)
    summ_rel.to_csv(C["summary_rel"], index=False)
    print(summ_rel.to_string(index=False))
    C["offset_rel"].write_text(json.dumps({"variant": variant, "source": source, **info}, indent=1, ensure_ascii=False),
                               encoding="utf-8")
    rel_x = with_dist(rel)
    report(rel_x, C["compare_rel"], C["groups_rel"], C["figure_rel"],
           f"EGMS L3 vertical {q['release']} vs levelling, {region}, relative to stable benchmarks")
    w_abs, w_rel = s7.share_within_uncertainty(res_x, k_sig), s7.share_within_uncertainty(rel_x, k_sig)
    ok_x = res_x[res_x["status"] == "ok"]
    unc_info = {"sigma_column": sig_col, "k_sigma": k_sig, "sigma_dh_rule": "sqrt(2) * rmse (różnica dwóch odczytów EGMS)",
                "median_rmse_mm": float(ok_x["egms_rmse_mm"].median()), "median_sigma_dh_mm": w_abs["median_sigma_dh_mm"],
                "n_without_sigma": w_abs["n_without_sigma"], "n_absolute": w_abs["n"], "share_within_absolute": w_abs["share_within"],
                "n_relative": w_rel["n"], "share_within_relative": w_rel["share_within"],
                "note": "informacyjnie, bez progu; niwelacja bez niepewności (rejestr NRW jej nie podaje)"}
    C["uncertainty"].write_text(json.dumps(unc_info, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Niepewność EGMS (informacyjnie): mediana rmse {unc_info['median_rmse_mm']:.2f} mm, sigma_Δh "
          f"{unc_info['median_sigma_dh_mm']:.2f} mm; w granicach ±{k_sig:g}σ: wariant główny {w_abs['share_within']:.0%} "
          f"(n {w_abs['n']}), względny {w_rel['share_within']:.0%} (n {w_rel['n']}); bez rmse: {w_abs['n_without_sigma']}")
    # Ryciny szeregów: EGMS w czasie i epoki niwelacji przy reperach z reguły przykładów (bez wyboru ręcznego).
    mo = require_approved(cfg, "monitoring")
    examples = _levelling_check_examples(res, mo["example_rule"], float(strong))
    # Mapa prędkości L3 tego samego wydania co porównanie: stacje GNSS i repery z rycin szeregów.
    if C["l3_map"].exists():
        sites = _read_sites(region_paths(rt, cfg, region))
        shown = sites[(sites["site_type"] == "gnss") | sites["site"].astype(str).isin([b for b, _ in examples])]
        fig = s7.plot_l3_map(_read_points(C["l3_map"], "mapa L3: task_levelling_extract"), shown,
                             f"EGMS L3 vertical velocity {q['release']}, {region}", mo["map_vlim_percentile"])
        fig.savefig(C["map"], dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
    else:
        print(f"Brak {C['l3_map'].name} (tryb bez plików surowych): mapa {C['map'].name} nie powstała")
    figs, tag = [], str(q["release"]).replace("-", "_")

    def egms_txt(row) -> str:
        s_ = float(row["sigma_dh_mm"])
        return (f"EGMS {row['dh_egms_mm']:+.0f} ± {k_sig * s_:.0f} mm ({k_sig:g}σ)" if np.isfinite(s_)
                else f"EGMS {row['dh_egms_mm']:+.0f} mm (no EGMS rmse)")

    for bid, label in examples:
        row = res_x[(res_x["benchmark_id"] == bid) & (res_x["status"] == "ok")].iloc[0]
        one = _levelling_series_long(long_u, lev, row, region)
        title = (f"Benchmark {bid}: {label}\nlevelling {row['dh_lev_mm']:+.0f} mm, {egms_txt(row)} "
                 f"({pd.Timestamp(row['t1']):%Y-%m-%d} to {pd.Timestamp(row['t2']):%Y-%m-%d})")
        fig = s7.plot_levelling_series(one, bid, title, mo["s1b_end_date"], float(row["sigma_dh_mm"]), k_sig)
        out_png = C["figure"].parent / f"{region}_levelling_series_{tag}_{bid}.png"
        fig.savefig(out_png, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        figs.append(out_png.name)
        if label == "smallest |rate|, stable":
            # Reper stabilny (autor 2026-10-15): szum EGMS, wspólne tempo grupy stabilnej i rozkład całej grupy (N3).
            grp = res_x[(res_x["status"] == "ok") & (res_x["dh_lev_mm"].abs() <= th["stable_max_lev_mm"])]
            title = (f"Benchmark {bid}: stable by levelling ({row['dh_lev_mm']:+.0f} mm), {egms_txt(row)}\n"
                     f"EGMS difference explained: noise (band) + common rate of all {info['n_group']} stable benchmarks")
            fig = s7.plot_stable_benchmark(one, bid, float(row["dh_egms_mm"]), grp["dh_egms_mm"].to_numpy(float), info,
                                           float(row["sigma_dh_mm"]), k_sig, float(th["stable_abs_dh_mm"]), title,
                                           mo["s1b_end_date"])
            out_png = C["figure"].parent / f"{region}_levelling_stable_{tag}_{bid}.png"
            fig.savefig(out_png, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close(fig)
            figs.append(out_png.name)
    print(f"Ryciny reperów ({len(figs)}): {figs}")
    m = require_approved(cfg, "method")
    reg_rows = pd.concat([reg_rows, _metric_rows(rel.assign(product=source, site=rel["benchmark_id"], track="L3",
                                                            radius_m=_l3_radius(m), n=1.0),
                                                 region, LEVELLING_METRICS, "n", LEVELLING_REFERENCE_REL)],
                         ignore_index=True)
    crit_rel = "; ".join(f"{k[:2]}: {v}" for k, v in zip(summ_rel["kryterium"], summ_rel["spełnione"])
                         if str(k)[:1] == "N" and str(k)[1:2].isdigit())
    bowls = groups.iloc[1]
    btxt = (f"niecki: n {int(bowls['n'])}, mediana |diff| {bowls['median_abs_diff_mm']:.1f} mm, najbliższa stacja GNSS "
            f"(mediana) {bowls['dist_station_km_median']:.1f} km" if bowls["n"] else "niecki: brak reperów")
    return {"message": f"{source}: {int((res['status'] == 'ok').sum())} z {len(res)} reperów 'ok' (okno {t0.date()} - "
                       f"{t1.date()}); główny 'absolute': {crit}; {btxt}; dodatkowy względny (grupa {info['n_group']}, "
                       f"przesunięcie {info['offset_egms_minus_lev_mm_yr']:+.2f} ± {info['offset_se_mm_yr']:.2f} mm/rok): "
                       f"{crit_rel}; ryciny {C['figure'].name}, {C['figure_rel'].name} i {len(figs)} szeregów reperów",
            "registry": {"gwl_validation_metrics": reg_rows}}


# ------------------------------------------------------------------------------
# Monitoring archiwalny i ryciny
# ------------------------------------------------------------------------------
def _levelling_to_long(lev: pd.DataFrame, region: str, t0, t1) -> tuple:
    """
    Niwelacja -> format długi (Plan_v2 sekcja 2.2): source LEVELLING_NRW, component U, wektor (0, 0, 1), track
    i direction 'vertical', epoki w [t0, t1], disp_mm = (h - h(pierwsza epoka w oknie)) * 1000, n_points NaN.
    Reper bez epoki w oknie = status, bez szeregu.
    """
    rows, status = [], []
    for bid, g in lev.groupby("benchmark_id", sort=True):
        g = g[(g["epoch_date"] >= t0) & (g["epoch_date"] <= t1)].sort_values("epoch_date")
        if g.empty:
            status.append({"site": bid, "source": LEVELLING_REFERENCE, "status": "brak epok niwelacji w oknie EGMS"})
            continue
        h = g["height_m"].to_numpy(float) * 1000.0
        rows.append(pd.DataFrame({"region": region, "source": LEVELLING_REFERENCE, "site": str(bid), "track": "vertical",
                                  "direction": "vertical", "component": "U", "los_east": 0.0, "los_north": 0.0,
                                  "los_up": 1.0, "date": pd.DatetimeIndex(g["epoch_date"]).normalize(),
                                  "disp_mm": h - h[0], "ref_date": pd.Timestamp(g["epoch_date"].iat[0]).normalize(),
                                  "reference": "absolute", "n_points": np.nan}))
        status.append({"site": bid, "source": LEVELLING_REFERENCE, "status": "ok"})
    return (pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()), pd.DataFrame(status)


def _gnss_projected(g: pd.DataFrame, vec: tuple) -> pd.Series:
    le, ln, lu = vec
    return pd.Series(g["e_mm"].to_numpy(float) * le + g["n_mm"].to_numpy(float) * ln + g["u_mm"].to_numpy(float) * lu,
                     index=pd.DatetimeIndex(g["date"]))


def task_monitoring_archive(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    Monitoring na danych archiwalnych (Plan_v2 sekcja 3.2, ryciny 2-4):
      1. format długi (step_07): EGMS L2b na ścieżkę (oczekiwane pary = wszystkie punkty x ścieżki planu), EGMS L3 U,
         GNSS w LOS (wektor szeregu EGMS) i U, przycięty do okna szeregu EGMS, z poziomem odniesienia = mediana dób
         +-gnss_half_window_days wokół daty odniesienia EGMS, niwelacja; szeregi etapu B (S1_*) już zapisane w pliku
         zostają; timeseries_long.csv.gz + tabela statusów (każda para bez szeregu z powodem);
      2. próbkowanie 6/12 dni na ścieżkę (step_07.sampling_table, data końca Sentinel-1B z konfiguracji);
      3. krzywe wykrycia dla każdego szeregu EGMS i GNSS w tych samych datach (step_03.gnss_at_dates), od każdej
         daty startu, i czas do wykrycia (step_07.detection_curve, time_to_detection).
    """
    import step_03_compare_gnss as s3
    import step_07_monitoring as s7
    e = require_approved(cfg, "egms")
    _region(cfg, region)
    m = require_approved(cfg, "method")
    mo = require_approved(cfg, "monitoring")
    _check_radii(m)
    P = region_paths(rt, cfg, region)
    src = _sources(cfg)
    sites = _read_sites(P)
    gn = sites[sites["site_type"] == "gnss"]
    gnss = _read_gnss(rt, cfg, list(gn["site"]))
    longs, statuses = [], []
    if "L2B" in e["levels"]:
        tracks = _l2b_tracks(_read_plan(P))
        points = _read_points(P["l2b_dedup"], "wycinek L2b bez duplikatów: task_checks")
        union = _date_cols(points)
        for track, direction in tracks.items():
            p = points[points["track"] == track]
            exp = pd.DataFrame({"site": sites["site"], "track": track, "direction": direction})
            lg, st = s7.egms_points_to_long(p if len(p) else pd.DataFrame(), _track_date_cols(p) if len(p) else union,
                                            region, src["L2B"], m["radius_main_m"], m["min_points"], exp)
            longs.append(lg)
            statuses.append(st)
    if "L3" in e["levels"]:
        cells = _read_points(P["l3_cells"], "komórki L3: task_extract")
        exp = pd.DataFrame({"site": sites["site"], "track": "L3", "direction": "vertical"})
        lg, st = s7.egms_points_to_long(cells, _date_cols(cells), region, src["L3"], _l3_radius(m), m["l3_min_points"], exp)
        longs.append(lg)
        statuses.append(st)
    egms_long = pd.concat([x for x in longs if len(x)], ignore_index=True) if any(len(x) for x in longs) else pd.DataFrame()
    if egms_long.empty:
        raise RuntimeError("Brak szeregów EGMS w formacie długim (statusy par w tabeli)")
    # GNSS w oknie każdego szeregu EGMS tego punktu: LOS (wektor szeregu) i U. Poziom odniesienia GNSS = mediana dób
    # +-gnss_half_window_days wokół daty odniesienia szeregu EGMS (jak step_03.gnss_at_dates), ref_date = data EGMS:
    # pojedyncza pierwsza doba (step_07.gnss_to_long) niosłaby szum dobowy jako stałe przesunięcie na rycinie.
    hw = m["gnss_half_window_days"]
    for (source, site, track), g in egms_long.groupby(["source", "site", "track"], sort=True):
        if site not in gnss:
            continue
        lo, hi, ref = g["date"].min(), g["date"].max(), g["ref_date"].iat[0]
        gd = gnss[site][(gnss[site]["date"] >= lo - pd.Timedelta(days=hw)) & (gnss[site]["date"] <= hi)]
        comp = g["component"].iat[0]
        row = {"region": region, "source": s7.GNSS_SOURCE[comp], "site": site, "track": track,
               "direction": g["direction"].iat[0], "radius_m": np.nan, "min_points": np.nan, "n_points": np.nan,
               "ref_date": pd.NaT}
        near = (gd["date"] - ref).abs() <= pd.Timedelta(days=hw)
        if not near.any():
            statuses.append(pd.DataFrame([{**row, "status": f"GNSS bez dób w +-{hw} dni od daty odniesienia EGMS "
                                                            f"{ref.date()}"}]))
            continue
        vec = tuple(g[["los_east", "los_north", "los_up"]].iloc[0].astype(float))
        gl = s7.gnss_to_long(gd.reset_index(drop=True), site, region, vec, comp, track if comp == "LOS" else "vertical",
                             g["direction"].iat[0])
        level = float(np.median(gl.loc[near.to_numpy(), "disp_mm"]))
        gl = s7.validate_long(gl.assign(disp_mm=gl["disp_mm"] - level, ref_date=ref))
        longs.append(gl)
        statuses.append(pd.DataFrame([{**row, "track": gl["track"].iat[0], "ref_date": ref, "status": "ok"}]))
    if P["levelling"].exists():
        lv_long, lv_st = _levelling_to_long(_read_levelling(P), region, egms_long["date"].min(), egms_long["date"].max())
        if len(lv_long):
            longs.append(lv_long)
        statuses.append(lv_st.assign(region=region))
    if P["long"].exists():                    # szeregi etapu B (task_hyp3_compare) zostają w pliku
        own = s7.read_long(P["long"])
        own = own[own["source"].str.startswith("S1_")]
        if len(own):
            print(f"Zachowane szeregi etapu B: {own[['source', 'site', 'track']].drop_duplicates().shape[0]}")
            longs.append(own)
    long = pd.concat([x for x in longs if len(x)], ignore_index=True)
    s7.write_long(long, P["long"])
    status = pd.concat(statuses, ignore_index=True)
    status.to_csv(P["long_status"], index=False, date_format="%Y-%m-%d")

    # Próbkowanie: daty akwizycji każdej ścieżki (z szeregów EGMS).
    samp, summ = [], []
    for (source, track), g in egms_long.groupby(["source", "track"], sort=True):
        d = pd.DatetimeIndex(sorted(g["date"].unique()))
        t, s = s7.sampling_table(d, mo["s1b_end_date"])
        samp.append(t.assign(source=source, track=track))
        summ.append(s.assign(source=source, track=track))
    pd.concat(samp, ignore_index=True).to_csv(P["sampling"], index=False, date_format="%Y-%m-%d")
    pd.concat(summ, ignore_index=True).to_csv(P["sampling_summary"], index=False, date_format="%Y-%m-%d")

    # Krzywe wykrycia: EGMS i GNSS w datach EGMS.
    args = (mo["windows_months"], mo["model_short"], mo["model_long"], mo["sigma_method"], mo["detect_k_sigma"],
            mo["min_obs"])
    curves, ttd = [], []
    for (source, site, track), g in egms_long.groupby(["source", "site", "track"], sort=True):
        g = g.sort_values("date")
        ser = pd.Series(g["disp_mm"].to_numpy(float), index=pd.DatetimeIndex(g["date"]))
        cands = [(source, ser)]
        if site in gnss:
            vec = tuple(g[["los_east", "los_north", "los_up"]].iloc[0].astype(float))
            g_at = s3.gnss_at_dates(_gnss_projected(gnss[site], vec), ser.index, m["gnss_half_window_days"])
            cands.append((f"{s7.GNSS_SOURCE[g['component'].iat[0]]}@{source}", g_at))
        for name, s in cands:
            for start in mo["window_starts"]:
                c = s7.detection_curve(s, start, *args).assign(site=site, track=track, source=name, egms_source=source)
                curves.append(c)
                t = s7.time_to_detection(c)
                ttd.append({"site": site, "track": track, "source": name, "egms_source": source, "start": start,
                            "ttd_months": t, "n_ok_windows": int((c["status"] == "ok").sum()),
                            "status": "wykryte" if t is not None else ("brak okien 'ok'" if not (c["status"] == "ok").any()
                                                                       else "niewykryte")})
    cv = pd.concat(curves, ignore_index=True)
    cv.to_csv(P["detection"], index=False, date_format="%Y-%m-%d")
    tt = pd.DataFrame(ttd)
    tt.to_csv(P["ttd"], index=False)
    reg_rows = pd.DataFrame({"region": region, "product": tt["source"], "reference": "TIME_TO_DETECTION",
                             "site": tt["site"].astype(str), "track": tt["track"].astype(str), "radius_m": np.nan,
                             "metric": "ttd_months_from_" + tt["start"].astype(str), "value": tt["ttd_months"].astype(float),
                             "n": tt["n_ok_windows"].astype(float), "status": tt["status"]})
    n_series = long.drop_duplicates(["source", "site", "track"]).groupby("source").size().to_dict()
    return {"message": f"szeregi: {n_series}; pary bez szeregu: {int((status['status'] != 'ok').sum())}; "
                       f"krzywe wykrycia: {len(tt)}, wykryte {int((tt['status'] == 'wykryte').sum())}",
            "registry": {"gwl_validation_metrics": reg_rows}}


def _example_sites(sites: pd.DataFrame, lev_res: pd.DataFrame, rule: str) -> List[str]:
    """
    Reguła przykładów (monitoring.example_rule) 'max_subsidence_median_stable' (Plan_v2 sekcja 7 pkt 5, reguła E1):
    GNSS - stacja osiadająca o najmniejszym vu, stacja o medianie vu osiadających, stacja stabilna o najmniejszym |vu|;
    niwelacja - reper 'ok' o najmniejszym v_lev, reper o medianie v_lev, reper o najmniejszym |v_lev|.
    """
    if rule != "max_subsidence_median_stable":
        raise ValueError(f"monitoring.example_rule {rule!r}: zaimplementowana 'max_subsidence_median_stable'")
    out = []
    gn = sites[sites["site_type"] == "gnss"]
    sub = gn[gn["group"] == "osiadająca"].sort_values("vu_mm_yr")
    stab = gn[gn["group"] == "stabilna"].assign(a=lambda x: x["vu_mm_yr"].abs()).sort_values("a")
    if len(sub):
        out += [sub["site"].iat[0], sub["site"].iat[len(sub) // 2]]
    if len(stab):
        out.append(stab["site"].iat[0])
    if lev_res is not None and len(lev_res):
        ok = lev_res[lev_res["status"] == "ok"].sort_values("v_lev_mm_yr")
        if len(ok):
            out += [ok["benchmark_id"].iat[0], ok["benchmark_id"].iat[len(ok) // 2],
                    ok.assign(a=ok["v_lev_mm_yr"].abs()).sort_values("a")["benchmark_id"].iat[0]]
    return list(dict.fromkeys(str(s) for s in out))


def _read_curves(P: Dict[str, Path]) -> pd.DataFrame:
    cv = _read_csv(P["detection"], "krzywe wykrycia: task_monitoring_archive", dtype={"site": str, "track": str})
    cv["detected"] = cv["detected"].map({True: True, False: False, "True": True, "False": False}).astype("boolean")
    return cv


def task_figures(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    Ryciny PNG regionu (osie po angielsku) w data/05_Final_Outputs/egmscheck/<region>/figures/: mapa prędkości L3,
    próbkowanie ścieżek, szeregi i krzywe wykrycia dla punktów z reguły przykładów, rozrzut prędkości EGMS L2b
    kontra GNSS (step_03.plot_velocity_scatter; tylko grupy osiadająca/stabilna, które step_03 umie opisać).
    """
    import matplotlib.pyplot as plt
    import step_03_compare_gnss as s3
    import step_07_monitoring as s7
    e = require_approved(cfg, "egms")
    _region(cfg, region)
    m = require_approved(cfg, "method")
    mo = require_approved(cfg, "monitoring")
    P = region_paths(rt, cfg, region)
    P["figures"].mkdir(parents=True, exist_ok=True)
    src = _sources(cfg)
    sites = _read_sites(P)
    long = s7.read_long(P["long"])
    lev_res = _read_csv(P["levelling_compare"], "porównanie z niwelacją", dtype={"benchmark_id": str}) \
        if P["levelling_compare"].exists() else None
    examples = _example_sites(sites, lev_res, mo["example_rule"])
    saved = []

    def save(fig, name):
        out = P["figures"] / name
        fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        saved.append(out)

    if P["l3_map"].exists():
        mp = _read_points(P["l3_map"], "mapa L3")
        shown = sites[(sites["site_type"] == "gnss") | sites["site"].isin(examples)]
        save(s7.plot_l3_map(mp, shown, f"EGMS L3 vertical velocity {e['release']}, {region}",
                            mo["map_vlim_percentile"]), f"{region}_l3_velocity_map.png")
    samp = _read_csv(P["sampling"], "próbkowanie: task_monitoring_archive", dtype={"track": str}, parse_dates=["date"])
    tables = {f"{t}" if s == src["L2B"] else "L3": g for (s, t), g in samp.groupby(["source", "track"])}
    save(s7.plot_sampling(tables, f"EGMS acquisition sampling, {region}", mo["s1b_end_date"]), f"{region}_sampling.png")
    cv = _read_curves(P)
    for site in examples:
        if site not in set(long["site"]):
            print(f"{site}: brak szeregów w formacie długim - rycina pominięta (statusy: {P['long_status']})")
            continue
        save(s7.plot_series_long(long, site, f"{region}: {site}", mo["s1b_end_date"]), f"{region}_series_{site}.png")
        l2 = long[(long["site"] == site) & (long["source"] == src["L2B"])]
        best = l2.groupby("track")["n_points"].first().sort_values(ascending=False).index[:1].tolist() if len(l2) else []
        for start in mo["window_starts"]:
            for kind, egms_src, track in ([("LOS", src["L2B"], best[0])] if best else []) + [("U", src["L3"], "L3")]:
                c = cv[(cv["site"] == site) & (cv["track"] == str(track)) & (cv["egms_source"] == egms_src)
                       & (cv["start_date"].astype(str).str[:10] == str(start)[:10])]
                if c.empty:
                    continue
                curves = {f"{n} (track {track})" if n == egms_src else n: g for n, g in c.groupby("source", sort=False)}
                save(s7.plot_detection(curves, f"{region}: {site}, {kind}, windows from {start}"),
                     f"{region}_detection_{site}_{kind}_{str(start)[:10]}.png")
    if P["gnss_compare"].exists():
        th = require_approved(cfg, "thresholds")
        res = _read_csv(P["gnss_compare"], "porównanie GNSS", dtype={"site": str})
        r = res[(res["product"] == src["L2B"]) & res["group"].isin(list(s3.GROUP_EN))]
        dropped = int(((res["product"] == src["L2B"]) & ~res["group"].isin(list(s3.GROUP_EN))).sum())
        if dropped:
            print(f"Wykres rozrzutu: pominięto {dropped} wierszy grupy 'inna' (step_03.plot_velocity_scatter opisuje "
                  f"tylko grupy osiadająca/stabilna)")
        if (r["status"] == "ok").any():
            save(s3.plot_velocity_scatter(r, {"radius_main_m": m["radius_main_m"],
                                              "thresholds": {"abs_dv_mm_yr": th["gnss_l2b"]["abs_dv_mm_yr"]}}),
                 f"{region}_velocity_scatter.png")
    plt.close("all")
    return {"message": f"{len(saved)} rycin w {P['figures']} (przykłady: {examples})"}


# ==============================================================================
# IV. ZADANIA ETAPU B: ASF HyP3 + MintPy (step_08)
# ==============================================================================
def _hyp3_tracks(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, str]:
    """Ścieżki etapu B: 'from_egms_l2b' = wszystkie ścieżki L2B z planu EGMS; lista = jej podzbiór (z kierunkiem)."""
    h = cfg["hyp3"]
    l2 = {str(t): d for t, d in _l2b_tracks(_read_plan(region_paths(rt, cfg, region))).items()}
    if h["tracks"] == "from_egms_l2b":
        return l2
    want = [str(t) for t in h["tracks"]]
    missing = [t for t in want if t not in l2]
    if missing:
        raise ValueError(f"hyp3.tracks {missing} spoza ścieżek EGMS L2B {sorted(l2)} (dowiązanie wymaga EGMS)")
    return {t: l2[t] for t in want}


def _job_name(region: str, track: str) -> str:
    return f"{HYP3_JOB_PREFIX}_{region}_{track}"


def _aoi_wkt(box: tuple) -> str:
    lo0, la0, lo1, la1 = box
    return f"POLYGON(({lo0} {la0}, {lo1} {la0}, {lo1} {la1}, {lo0} {la1}, {lo0} {la0}))"


def hyp3_planned_tracks(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> List[str]:
    """Ścieżki z planu etapu B (task_hyp3_plan) - do pętli w notatniku."""
    p = region_paths(rt, cfg, region)["hyp3_plan"]
    return [str(t) for t in _read_csv(p, "plan HyP3: task_hyp3_plan", dtype={"track": str})["track"]]


def task_hyp3_plan(rt: Dict[str, Any], cfg: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    Plan zleceń HyP3 dla każdej ścieżki etapu B: bursty (step_08.search_bursts) w prostokącie wyszukania EGMS,
    bursty pokrywające punkty naziemne (+ uzupełnienie ciągłości dla INSAR_ISCE_MULTI_BURST), stos dat z kompletem
    burstów, pary SBAS, zlecenia prepare_* (bez sieci). Zapis hyp3_plan_<region>_<track>.json i tabeli planu;
    komunikat z liczbą zleceń do potwierdzenia (CONFIRM_JOBS). Kierunek orbity burstów = kierunek ścieżki EGMS.
    """
    import step_08_hyp3_mintpy as s8
    e = require_approved(cfg, "egms")
    reg = _region(cfg, region)
    h = require_approved(cfg, "hyp3")
    end = _decided(h, "end", "hyp3")
    P = region_paths(rt, cfg, region)
    sites = _read_sites(P)
    wkt = _aoi_wkt(_search_lonlat(reg, sites, e["search_area"]))
    rows = []
    for track, direction in _hyp3_tracks(rt, cfg, region).items():
        b = s8.search_bursts(wkt, int(track), h["start"], end, h["polarization"])
        if set(b["flight_direction"]) != {direction}:
            raise ValueError(f"Ścieżka {track}: bursty {sorted(set(b['flight_direction']))}, EGMS {direction}")
        ids = s8.bursts_covering_points(b, sites[["site", "lon_deg", "lat_deg"]])
        if h["job_type"] == "INSAR_ISCE_MULTI_BURST":
            ids = s8.fill_burst_gaps(ids)
        stack = s8.acquisition_stack(b, ids)
        pairs = s8.sbas_pairs(stack["date"], h["n_neighbors"], h["max_dt_days"])
        name = _job_name(region, track)
        jobs = s8.prepare_jobs(stack, pairs, h["job_type"], h["looks"], h["apply_water_mask"], name)
        plan = {"region": region, "track": track, "direction": direction, "name": name, "burst_ids": list(ids),
                "dates": [str(d.date()) for d in stack["date"]],
                "pairs": [[str(a.date()), str(c.date())] for a, c in pairs], "jobs": jobs}
        hp = hyp3_paths(rt, cfg, region, track)
        hp["plan_json"].parent.mkdir(parents=True, exist_ok=True)
        hp["plan_json"].write_text(json.dumps(plan, indent=1, default=str), encoding="utf-8")
        rows.append({"track": track, "direction": direction, "name": name, "n_bursts": len(ids), "n_dates": len(stack),
                     "first_date": plan["dates"][0], "last_date": plan["dates"][-1], "n_jobs": len(jobs),
                     "credits": len(jobs) * h["cost_per_job"] if h["cost_per_job"] is not None else np.nan})
    tab = pd.DataFrame(rows)
    tab.to_csv(P["hyp3_plan"], index=False)
    print(tab.to_string(index=False))
    confirm = {r.track: r.n_jobs for r in tab.itertuples()}
    return {"message": f"{int(tab['n_jobs'].sum())} zleceń na {len(tab)} ścieżkach; po akceptacji ustaw "
                       f"CONFIRM_JOBS = {confirm}"}


def _hyp3_plan_json(rt, cfg, region, track) -> Dict[str, Any]:
    p = hyp3_paths(rt, cfg, region, track)["plan_json"]
    if not p.exists():
        raise FileNotFoundError(f"Brak planu {p}: uruchom task_hyp3_plan")
    return json.loads(p.read_text(encoding="utf-8"))


def _check_confirm_jobs(plan: Dict[str, Any], confirm_jobs: Any, track: str) -> int:
    n = len(plan["jobs"])
    if confirm_jobs is None:
        raise RuntimeError(f"Zlecenia HyP3 wstrzymane: po obejrzeniu planu ustaw CONFIRM_JOBS['{track}'] = {n} "
                           f"(liczba zleceń w planie ścieżki {track})")
    if isinstance(confirm_jobs, bool) or not isinstance(confirm_jobs, (int, np.integer)) or confirm_jobs != n:
        raise RuntimeError(f"CONFIRM_JOBS['{track}'] = {confirm_jobs!r}, a plan ma {n} zleceń: sprawdź plan i ustaw {n}")
    return n


def task_hyp3_submit(rt: Dict[str, Any], cfg: Dict[str, Any], region: str, track: str, confirm_jobs: Any) -> Dict[str, Any]:
    """
    Wysłanie zleceń z planu ścieżki po potwierdzeniu ich liczby (confirm_jobs = liczba zleceń w planie). Zlecenia
    istniejące (ta sama nazwa i zbiór granul) nie są wysyłane ponownie; limit kredytów sprawdzany przed wysłaniem
    (step_08.submit_missing: max_credits, cost_per_job z konfiguracji).
    """
    import step_08_hyp3_mintpy as s8
    _region(cfg, region)
    h = require_approved(cfg, "hyp3")
    plan = _hyp3_plan_json(rt, cfg, region, track)
    n = _check_confirm_jobs(plan, confirm_jobs, track)
    for key in ("max_credits", "cost_per_job"):          # decyzje autora przed logowaniem Earthdata i wysłaniem
        _decided(h, key, "hyp3")
    hy = s8.hyp3_client(s8.load_earthdata_credentials(cfg["project"]["earthdata_path"]))
    tab = s8.submit_missing(hy, plan["jobs"], plan["name"], h["max_credits"], h["cost_per_job"])
    hp = hyp3_paths(rt, cfg, region, track)
    hp["jobs"].parent.mkdir(parents=True, exist_ok=True)
    tab.to_csv(hp["jobs"], index=False)
    return {"message": f"ścieżka {track}: {n} zleceń w planie; {tab['status'].value_counts().to_dict()}"}


def task_hyp3_download(rt: Dict[str, Any], cfg: Dict[str, Any], region: str, track: str) -> Dict[str, Any]:
    """Pobranie produktów zleceń zakończonych sukcesem (step_08.download_succeeded; manifest z SHA-256 zipa)."""
    import step_08_hyp3_mintpy as s8
    _region(cfg, region)
    require_approved(cfg, "hyp3")
    plan = _hyp3_plan_json(rt, cfg, region, track)
    hp = hyp3_paths(rt, cfg, region, track)
    hy = s8.hyp3_client(s8.load_earthdata_credentials(cfg["project"]["earthdata_path"]))
    dl = s8.download_succeeded(hy, plan["name"], hp["raw"], _manifest(rt, cfg), Path(rt["PROJECT_DIR"]),
                               cfg["project"]["downloaded_by"])
    hp["download"].parent.mkdir(parents=True, exist_ok=True)
    dl.to_csv(hp["download"], index=False, date_format="%Y-%m-%d")
    return {"message": f"ścieżka {track}: {dl['status'].value_counts().to_dict()}"}


def task_mintpy(rt: Dict[str, Any], cfg: Dict[str, Any], region: str, track: str) -> Dict[str, Any]:
    """
    MintPy dla ścieżki: produkty z pobrania -> przycięcie do wspólnego obszaru (step_08.clip_to_common_overlap)
    -> punkt odniesienia z reguły (stabilna stacja GNSS o najmniejszym |vu|) -> szablon -> smallbaselineApp.py.
    Wymaga GDAL (osgeo). Zero produktów = RuntimeError (zlecenia w toku: uruchom ponownie później).
    """
    import step_08_hyp3_mintpy as s8
    _region(cfg, region)
    h = require_approved(cfg, "hyp3")
    _check_gdal()
    P, hp = region_paths(rt, cfg, region), hyp3_paths(rt, cfg, region, track)
    dl = _read_csv(hp["download"], "pobranie HyP3: task_hyp3_download")
    ok = dl[dl["status"].isin(["downloaded", "existing", "extracted_existing_zip"])]
    if ok.empty:
        raise RuntimeError(f"Ścieżka {track}: brak pobranych produktów HyP3 ({dl['status'].value_counts().to_dict()}); "
                           f"zlecenia w toku - uruchom task_hyp3_download później")
    clip = s8.clip_to_common_overlap(list(ok["product_dir"]), list(s8.LAYER_TEMPLATE_KEYS), hp["clip"])
    ref = s8.reference_lalo_from_rule(_read_sites(P), h["mintpy"]["reference_rule"])
    tpl = s8.write_mintpy_template(hp["template"], hp["clip"], (ref["lat_deg"], ref["lon_deg"]), h["mintpy"])
    ts = s8.run_mintpy(tpl, hp["work"])
    return {"message": f"ścieżka {track}: {len(ok)} produktów, przycięcie {clip['width'].iat[0]} x {clip['height'].iat[0]} "
                       f"px, odniesienie {ref['site']} (vu {ref['vu_mm_yr']:+.2f} mm/rok), szereg {ts.name}"}


def task_hyp3_compare(rt: Dict[str, Any], cfg: Dict[str, Any], region: str, track: str) -> Dict[str, Any]:
    """
    Szeregi MintPy w punktach naziemnych (step_08.mintpy_series_at_points), kontrola wektora LOS względem EGMS
    tej ścieżki (check_los_vs_egms; niespełniona = RuntimeError), dowiązanie do EGMS w zakładce
    [hyp3.start, hyp3.overlap_end] (align_to_reference), dopisanie do timeseries_long (źródło S1_HYP3_MINTPY;
    poprzednie wiersze tej ścieżki zastąpione) i ryciny szeregów z trzema źródłami.
    """
    import matplotlib.pyplot as plt
    import step_07_monitoring as s7
    import step_08_hyp3_mintpy as s8
    require_approved(cfg, "egms")
    _region(cfg, region)
    m = require_approved(cfg, "method")
    mo = require_approved(cfg, "monitoring")
    h = require_approved(cfg, "hyp3")
    tol = _decided(h, "los_check_tol", "hyp3")
    P, hp = region_paths(rt, cfg, region), hyp3_paths(rt, cfg, region, track)
    direction = _hyp3_tracks(rt, cfg, region)[track]
    sites = _read_sites(P)
    work = hp["work"]
    own = s8.mintpy_series_at_points(work / s8.expected_timeseries_name(h["mintpy"]), work / s8.MINTPY_GEOMETRY,
                                     work / s8.MINTPY_MASK, sites[["site", "lon_deg", "lat_deg"]],
                                     h["mintpy"]["window_px"], region, track)
    if set(own["direction"]) != {direction}:
        raise ValueError(f"Ścieżka {track}: MintPy {sorted(set(own['direction']))}, EGMS {direction}")
    long = s7.read_long(P["long"])
    egms = long[(long["source"] == _sources(cfg)["L2B"]) & (long["track"] == str(track))]
    if egms.empty:
        raise RuntimeError(f"Brak szeregów EGMS L2b ścieżki {track} w {P['long']}: uruchom task_monitoring_archive")
    own_ok = own[own["status"] == "ok"]
    if own_ok.empty:
        raise RuntimeError(f"Ścieżka {track}: żaden punkt nie ma szeregu MintPy (statusy w wyniku)")
    vec_own = tuple(own_ok.groupby("site")[["los_east", "los_north", "los_up"]].first().mean())
    vec_egms = tuple(egms.groupby("site")[["los_east", "los_north", "los_up"]].first().mean())
    chk = s8.check_los_vs_egms(vec_own, vec_egms, tol)
    print(f"Kontrola wektora LOS (MintPy kontra EGMS, ścieżka {track}): {chk}")
    if not chk["pass"]:
        raise RuntimeError(f"Wektor LOS MintPy niezgodny z EGMS (ścieżka {track}): {chk}; porównanie wstrzymane")
    shifted, tab = s8.align_to_reference(own, egms, h["start"], h["overlap_end"], m["gnss_half_window_days"])
    ser, st = s8.split_long_status(shifted)
    tab.to_csv(hp["align"], index=False)
    st.to_csv(hp["status"], index=False, date_format="%Y-%m-%d")
    keep = long[~((long["source"] == s8.SOURCE) & (long["track"] == str(track)))]
    merged = pd.concat([keep, ser[s7.LONG_COLUMNS]], ignore_index=True) if len(ser) else keep
    s7.write_long(merged, P["long"])
    figs = []
    P["figures"].mkdir(parents=True, exist_ok=True)
    for site in tab.loc[tab["status"] == "ok", "site"].tolist()[:3]:
        fig = s7.plot_series_long(s7.read_long(P["long"]), site, f"{region}: {site}, EGMS + own processing (track {track})",
                                  mo["s1b_end_date"])
        out = P["figures"] / f"{region}_hyp3_series_{site}_{track}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        figs.append(out.name)
    reg_rows = pd.DataFrame([{"region": region, "product": s8.SOURCE, "reference": _sources(cfg)["L2B"],
                              "site": str(r.site), "track": str(track), "radius_m": np.nan, "metric": metric,
                              "value": float(getattr(r, metric)), "n": float(r.n_matched), "status": r.status}
                             for r in tab.itertuples() for metric in ("offset_mm", "std_diff_mm", "corr")])
    return {"message": f"ścieżka {track}: dowiązanie {tab['status'].value_counts().to_dict()}; mediana std różnicy "
                       f"{tab['std_diff_mm'].median():.2f} mm; ryciny {figs}",
            "registry": {"gwl_validation_metrics": reg_rows}}


# ==============================================================================
# V. RAPORT Z URUCHOMIENIA (CLAUDE.md, zasada 7)
# ==============================================================================
def _versions() -> Dict[str, Any]:
    import importlib.metadata as md
    out = {"python": sys.version.split()[0]}
    for p in VERSION_PACKAGES:
        try:
            out[p] = md.version(p)
        except md.PackageNotFoundError:
            out[p] = "not installed"
    return out


def _md_table(df: pd.DataFrame) -> str:
    if not len(df):
        return "(brak)"
    cols = [str(c) for c in df.columns]
    rows = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    rows += ["| " + " | ".join("" if (not isinstance(v, (list, dict)) and pd.isna(v)) else str(v) for v in r) + " |"
             for r in df.itertuples(index=False)]
    return "\n".join(rows)


def task_summary(rt: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    run_summary.md i run_summary.json w outputs_dir: wersje bibliotek, commit, wydanie EGMS, konfiguracja,
    zatwierdzenia, dla każdego regionu kontrole, werdykty GNSS (L2b, L3), kryteria niwelacji, czas do wykrycia,
    dowiązanie etapu B, ostatnie uruchomienia. Bez danych surowych.
    """
    out_dir = _abs(rt, cfg["project"]["outputs_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    approvals = approvals_table(cfg)
    regions = {}
    for region in cfg["regions"]:
        P = region_paths(rt, cfg, region)
        r = {}
        for key in ("checks", "verdict_l2b", "verdict_l3u", "levelling_summary", "ttd"):
            if P[key].exists():
                r[key] = pd.read_csv(P[key], dtype={"site": str, "track": str})   # numery reperów z zerem wiodącym
        for key in ("verdict_l2b", "verdict_l3u"):
            txt = P[key].with_suffix(".txt")
            if txt.exists():
                r[key + "_conclusion"] = txt.read_text(encoding="utf-8").strip()
        if P["plan"].exists():
            plan = pd.read_csv(P["plan"])
            r["egms_files"] = {"n": len(plan), "MB": round(plan["filesize"].sum() / 1e6, 1),
                               "by_query": plan["query_key"].value_counts().to_dict()}
        for f in sorted(P["outputs"].glob(f"hyp3_align_{region}_*.csv")) if P["outputs"].exists() else []:
            r[f.stem] = pd.read_csv(f, dtype={"site": str, "track": str})
        if cfg["regions"][region].get("levelling") is not None:
            C = levelling_check_paths(rt, cfg, region)
            rel = cfg["regions"][region]["levelling"]["egms_check"]["release"]
            for key in ("summary", "groups", "summary_rel", "groups_rel"):
                if C[key].exists():
                    r[f"levelling_check_{key}"] = pd.read_csv(C[key])
            if C["offset_rel"].exists():
                r["levelling_check_offset_rel"] = json.loads(C["offset_rel"].read_text(encoding="utf-8"))
            if "levelling_check_summary" in r:
                r["levelling_check_release"] = rel
        regions[region] = r
    runs = run_history(rt, 25)
    summary = {
        "generated_utc": _utc_now(), "git_commit": rt.get("GIT_COMMIT", ""), "project_dir": rt["PROJECT_DIR"],
        "egms_release": cfg["egms"]["release"], "versions": _versions(), "config": cfg,
        "approvals": approvals.to_dict(orient="records"),
        "regions": {k: {kk: (vv.to_dict(orient="records") if isinstance(vv, pd.DataFrame) else vv) for kk, vv in v.items()}
                    for k, v in regions.items()},
        "runs": runs.to_dict(orient="records"),
    }
    js = out_dir / "run_summary.json"
    js.write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    parts = [f"# EGMS Check — raport z uruchomienia {summary['generated_utc']}", "",
             f"Commit `{summary['git_commit']}` · wydanie EGMS {summary['egms_release']} · Python "
             f"{summary['versions']['python']}", "", "## Wersje bibliotek",
             _md_table(pd.DataFrame([summary["versions"]])), "", "## Zatwierdzenia (CHECK_CONFIG)", _md_table(approvals), ""]
    for region, r in regions.items():
        parts += [f"## Region {region}", ""]
        if "egms_files" in r:
            parts += [f"Pliki EGMS: {json.dumps(r['egms_files'], ensure_ascii=False)}", ""]
        for key, title in (("checks", "Kontrole konwencji"), ("verdict_l2b", "Werdykt EGMS L2b kontra GNSS"),
                           ("verdict_l3u", "Werdykt EGMS L3 (U) kontra GNSS"),
                           ("levelling_summary", "EGMS L3 kontra niwelacja: kryteria"), ("ttd", "Czas do wykrycia [mies.]")):
            if key in r:
                parts += [f"### {title}", _md_table(r[key])]
                if key + "_conclusion" in r:
                    parts += ["", f"**Wniosek:** {r[key + '_conclusion']}"]
                parts.append("")
        if "levelling_check_summary" in r:
            rel = r["levelling_check_release"]
            parts += [f"### EGMS L3 {rel} kontra niwelacja: kryteria (drugie wydanie, tylko do porównania z niwelacją)",
                      _md_table(r["levelling_check_summary"]), ""]
            if "levelling_check_groups" in r:
                parts += [f"### EGMS L3 {rel} kontra niwelacja: podział informacyjny (bez progów)",
                          _md_table(r["levelling_check_groups"]), ""]
            if "levelling_check_summary_rel" in r:
                off = r.get("levelling_check_offset_rel", {})
                parts += [f"### EGMS L3 {rel} kontra niwelacja: wariant DODATKOWY względem grupy stabilnej "
                          f"(policzony po wyniku 'absolute'; werdykt główny bez zmian)",
                          f"Grupa: {off.get('n_group')} reperów, {off.get('group_rule')}; przesunięcie EGMS - niwelacja "
                          f"{off.get('offset_egms_minus_lev_mm_yr', float('nan')):+.2f} ± "
                          f"{off.get('offset_se_mm_yr', float('nan')):.2f} mm/rok.", "",
                          _md_table(r["levelling_check_summary_rel"]), ""]
                if "levelling_check_groups_rel" in r:
                    parts += [_md_table(r["levelling_check_groups_rel"]), ""]
        for k, v in r.items():
            if k.startswith("hyp3_align_"):
                parts += [f"### Etap B: dowiązanie do EGMS ({k})", _md_table(v), ""]
        if not r:
            parts += ["(brak wyników)", ""]
    parts += ["## Konfiguracja", "```json", json.dumps(cfg, indent=1, ensure_ascii=False, default=str), "```", "",
              "## Ostatnie uruchomienia", _md_table(runs), ""]
    mdp = out_dir / "run_summary.md"
    mdp.write_text("\n".join(parts), encoding="utf-8")
    return {"message": f"{mdp} ({mdp.stat().st_size // 1024} kB), {js.name}"}


# ==============================================================================
# VI. TEST OFFLINE
# ==============================================================================
def _expect(exc, fn, *args, match: str = ""):
    try:
        fn(*args)
    except exc as e:
        assert match in str(e), f"komunikat bez '{match}': {e}"
        return e
    raise AssertionError(f"Oczekiwano {exc.__name__} z {getattr(fn, '__name__', fn)}")


def _selftest() -> None:
    with tempfile.TemporaryDirectory(prefix="egmscheck_run_") as tmpd:
        tmp = Path(tmpd)
        proj = tmp / "proj"
        proj.mkdir()
        rt = setup_runtime(str(proj), [])
        assert rt["GIT_COMMIT"] == "no-git" and Path(rt["REGISTRY_DIR"]).is_dir() and rt["INSTALLED"] == []
        _expect(ImportError, _install_missing, ["pakiet_ktorego_nie_ma_xyz"], False, match="pip install")
        old_path = os.environ.get("PATH", "")
        try:                                   # git niedostępny -> jawny napis, bez wyjątku
            os.environ["PATH"] = str(tmp / "pusty")
            assert _git(str(proj), "status").startswith("git-unavailable: FileNotFoundError")
        finally:
            os.environ["PATH"] = old_path
        assert _git(str(proj), "rev-parse", "HEAD").startswith("git-unavailable")    # nie repozytorium: kod błędu

        # 1. Rejestr: nowe / bez zmian / zmienione; klucze '37' i 37, 100 i 100.0 to ten sam klucz.
        base = pd.DataFrame({"region": "r", "product": "EGMS_L2b_2020_2024", "reference": "GNSS_NGL",
                             "site": ["S1", "S1", "S2"], "track": [37, 88, 37], "radius_m": [100, 100, 100.0],
                             "metric": "dv", "value": [0.5, -0.2, 1.0], "n": [100, 90, 80], "status": "ok",
                             "run_id": "r1"})
        assert registry_upsert(rt, "gwl_validation_metrics", base) == {"new": 3, "changed": 0, "unchanged": 0}
        again = base.assign(track=base["track"].astype(str), radius_m=100.0, run_id="r2")
        assert registry_upsert(rt, "gwl_validation_metrics", again) == {"new": 0, "changed": 0, "unchanged": 3}
        assert set(registry_read(rt, "gwl_validation_metrics")["run_id"]) == {"r1"}, "wiersz bez zmian zachowuje run_id"
        upd = base.iloc[[2]].assign(value=1.25, run_id="r3")
        new = base.iloc[[0]].assign(site="S3", run_id="r3")
        assert registry_upsert(rt, "gwl_validation_metrics", pd.concat([upd, new])) == {"new": 1, "changed": 1,
                                                                                        "unchanged": 0}
        reg = registry_read(rt, "gwl_validation_metrics")
        assert len(reg) == 4 and float(reg.loc[reg["site"] == "S2", "value"].iat[0]) == 1.25
        assert reg.loc[reg["site"] == "S2", "run_id"].iat[0] == "r3"
        _expect(ValueError, registry_upsert, rt, "gwl_validation_metrics", base.drop(columns="metric"), match="metric")
        # Numery reperów z zerem wiodącym (kolumna site tylko z cyfr): ten sam klucz przy ponownym zapisie, zero zostaje.
        rt_b = {"REGISTRY_DIR": str(tmp / "reg_bench")}
        bench = pd.DataFrame({"region": "nrw_west", "product": "EGMS_L3U_2020_2024", "reference": "LEVELLING_NRW",
                              "site": ["0450600001", "0450600002"], "track": "L3", "radius_m": 70.71067811865476,
                              "metric": "diff_mm", "value": [1.0, 2.0], "n": 1.0, "status": "ok", "run_id": "b1"})
        assert registry_upsert(rt_b, "gwl_validation_metrics", bench) == {"new": 2, "changed": 0, "unchanged": 0}
        assert registry_upsert(rt_b, "gwl_validation_metrics", bench.assign(run_id="b2")) == {"new": 0, "changed": 0,
                                                                                               "unchanged": 2}
        assert sorted(registry_read(rt_b, "gwl_validation_metrics")["site"]) == ["0450600001", "0450600002"]
        _expect(KeyError, registry_read, rt, "gwl_nie_ma", match="Nieznana tabela")

        # 2. run_task: wynik z rejestrem, pominięcie, błąd zapisany w gwl_runs i zgłoszony dalej, zły kontrakt.
        sites = pd.DataFrame({"region": "r", "site": ["A", "B"], "site_type": "gnss", "group": "stabilna",
                              "lat_deg": [53.0, 53.1], "lon_deg": [6.0, 6.1], "x_3035": 1.0, "y_3035": 2.0,
                              "source": "GNSS_NGL", "updated_at": "t"})
        res = run_task(rt, "ok_task", lambda: {"message": "zrobione", "registry": {"gwl_sites": sites}})
        assert res["message"] == "zrobione"
        run_task(rt, "skip_task", lambda: {"skipped": True, "message": "nic"})

        def boom(x):
            raise ValueError(f"awaria {x}")
        _expect(ValueError, run_task, rt, "boom_task", boom, 7, match="awaria 7")
        _expect(TypeError, run_task, rt, "bad_contract", lambda: 42, match="słownika")
        runs = registry_read(rt, "gwl_runs").set_index("task")
        assert runs.at["ok_task", "status"] == "ok" and "gwl_sites: +2/~0" in runs.at["ok_task", "message"]
        assert runs.at["skip_task", "status"] == "skipped"
        assert runs.at["boom_task", "status"] == "error" and runs.at["boom_task", "message"] == "ValueError: awaria 7"
        assert runs.at["bad_contract", "status"] == "error" and "TypeError" in runs.at["bad_contract", "message"]
        assert json.loads(runs.at["boom_task", "params_json"])["args"] == ["7"]
        reg_sites = registry_read(rt, "gwl_sites")
        assert len(reg_sites) == 2 and reg_sites["run_id"].str.endswith("_ok_task").all()
        hist = run_history(rt, 2)
        assert len(hist) == 2 and list(hist.columns)[:3] == ["run_id", "task", "status"]
        rs = registry_summary(rt).set_index("table")
        assert rs.at["gwl_runs", "rows"] == 4 and rs.at["gwl_validation_metrics", "rows"] == 4

        # 3. Zatwierdzenia: stan z CHECK_CONFIG repozytorium (wszystkie sekcje zatwierdzone przez autora), wyjątek z
        #    nazwą decyzji na kopii z cofniętym zatwierdzeniem albo parametrem None.
        cfg = copy.deepcopy(CHECK_CONFIG)
        ap = approvals_table(cfg).set_index("section")
        assert ap.at["egms", "approved"] == "2026-10-11" and ap.at["regions.groningen", "approved"] == "2026-10-10"
        assert (ap.loc[["regions.nrw_west", "gnss", "method", "thresholds", "monitoring", "hyp3"], "approved"]
                == "2026-10-12").all()
        assert (ap["open_decisions"] == "-").all(), ap[ap["open_decisions"] != "-"]
        assert require_approved(cfg, "egms")["release"] == "2020-2024"
        assert require_approved(cfg, "regions.groningen")["aoi_lonlat"] == (5.8, 52.9, 7.3, 53.6)
        cfg_u = copy.deepcopy(cfg)
        cfg_u["hyp3"]["approved"] = None
        cfg_u["hyp3"]["max_credits"] = None
        e = _expect(RuntimeError, require_approved, cfg_u, "hyp3", match="CHECK_CONFIG['hyp3']")
        assert "max_credits" in str(e)
        cfg_u["monitoring"]["approved"] = None
        _expect(RuntimeError, require_approved, cfg_u, "monitoring", match="nie jest zatwierdzona")
        # sekcja zatwierdzona, ale parametr nadal None (decyzja autora) -> głośny stop przy użyciu
        _expect(RuntimeError, _decided, cfg_u["hyp3"], "max_credits", "hyp3", match="max_credits")
        _expect(KeyError, require_approved, cfg, "regions.berlin", match="berlin")
        _expect(KeyError, require_approved, cfg, "project", match="approved")
        cfg_u["method"]["approved"] = None
        _expect(RuntimeError, task_compare_gnss, rt, cfg_u, "groningen", match="method")    # zadanie zatrzymane
        assert CHECK_CONFIG["hyp3"]["approved"] == "2026-10-12", "test nie może zmieniać konfiguracji repozytorium"

        # 4. Blokada confirm_mb: przed tokenem i siecią; None / inna liczba = RuntimeError z wartością do wpisania.
        cfg_t = copy.deepcopy(CHECK_CONFIG)
        for sec in ("method", "gnss", "thresholds", "monitoring", "hyp3"):
            cfg_t[sec]["approved"] = "SELFTEST"
        cfg_t["hyp3"].update(max_credits=None, cost_per_job=None)    # blokady decyzji sprawdzane niżej
        cfg_t["project"]["token_path"] = str(tmp / "brak_tokenu.json")
        P = region_paths(rt, cfg_t, "groningen")
        P["plan"].parent.mkdir(parents=True)
        plan = pd.DataFrame({"level": ["L2B", "L3"], "filename": ["a.zip", "b.zip"], "filesize": [2_400_000, 1_300_000],
                             "need_bytes": [2_400_000, 1_300_000], "status": ["missing", "missing"],
                             "query_key": ["L2B", "L3:ORTHO-UP"], "relativeOrbit": [37, np.nan],
                             "direction": ["ascending", np.nan], "product_type": [np.nan, "ORTHO-UP"]})
        plan.to_csv(P["plan"], index=False)
        pd.DataFrame({"site": ["A"], "site_type": ["gnss"], "group": ["stabilna"], "lat_deg": [53.0], "lon_deg": [6.0],
                      "x_3035": [1.0], "y_3035": [2.0]}).to_csv(P["sites"], index=False)
        assert _need_mb(plan) == 4
        _expect(RuntimeError, task_egms_download, rt, cfg_t, "groningen", None, match="CONFIRM_MB_GRONINGEN = 4")
        _expect(RuntimeError, task_egms_download, rt, cfg_t, "groningen", 3, match="plan wymaga 4 MB")
        _expect(RuntimeError, task_egms_download, rt, cfg_t, "groningen", True, match="plan wymaga 4 MB")
        _expect(FileNotFoundError, task_egms_download, rt, cfg_t, "groningen", 4, match="tokenu")   # blokada przepuszcza
        assert _check_confirm_mb(plan, 4.0, "CONFIRM_MB_GRONINGEN", "egms_plan_groningen.csv") == 4
        assert _l2b_tracks(plan) == {37: "ascending"}
        # Bez tokenu, z wycinkami: wyszukanie i pobranie pominięte (notatnik czyta data/03_Extracts/).
        for k in ("l2b_points", "l3_cells", "l3_map"):
            P[k].write_text("x\n")
        assert task_egms_search(rt, cfg_t, "groningen")["skipped"] and task_egms_download(rt, cfg_t, "groningen", None)["skipped"]
        # Drugie wydanie do porównania z niwelacją: osobne pliki, osobna zmienna potwierdzenia, tylko L3, inne wydanie.
        C = levelling_check_paths(rt, cfg_t, "nrw_west")
        assert C["plan"].name == "egms_plan_nrw_west_levelling_2019_2023.csv"
        assert C["l3_cells"].name == "egms_l3u_2019_2023_cells_at_benchmarks.csv.gz" and _sources_of("2019-2023")["L3"] == "EGMS_L3U_2019_2023"
        _expect(ValueError, levelling_check_paths, rt, cfg_t, "groningen", match="bez niwelacji")
        assert task_levelling_egms_search(rt, cfg_t, "groningen")["skipped"]          # region bez niwelacji
        _expect(FileNotFoundError, task_levelling_egms_search, rt, cfg_t, "nrw_west", match="brak wycinków")
        C["plan"].parent.mkdir(parents=True, exist_ok=True)
        plan.iloc[[1]].to_csv(C["plan"], index=False)
        _expect(RuntimeError, task_levelling_egms_download, rt, cfg_t, "nrw_west", None, match="CONFIRM_MB_NRW_WEST_LEVELLING = 1")
        _expect(RuntimeError, task_levelling_egms_download, rt, cfg_t, "nrw_west", 4, match="plan wymaga 1 MB")
        _expect(FileNotFoundError, task_levelling_extract, rt, cfg_t, "nrw_west", match="plików L3 z planu brak")
        for k, v, exc, msg in (("levels", ["L2B", "L3"], ValueError, "tylko ['L3']"),
                               ("release", "2020-2024", ValueError, "wydaniem głównym"),
                               ("raw_dir", None, RuntimeError, "raw_dir")):
            cfg_b = copy.deepcopy(cfg_t)
            cfg_b["regions"]["nrw_west"]["levelling"]["egms_check"][k] = v
            _expect(exc, task_levelling_egms_search, rt, cfg_b, "nrw_west", match=msg)
        cfg_b = copy.deepcopy(cfg_t)
        cfg_b["regions"]["nrw_west"]["levelling"]["strong_motion_mm_yr"] = None
        _expect(RuntimeError, task_compare_levelling_check, rt, cfg_b, "nrw_west", match="strong_motion_mm_yr")
        assert C["compare_rel"].name == "levelling_compare_nrw_west_2019_2023_relative.csv"
        assert CHECK_CONFIG["regions"]["nrw_west"]["levelling"]["relative_variant"] == "stable_group_median"
        assert CHECK_CONFIG["regions"]["nrw_west"]["levelling"]["egms_check"]["release"] == "2019-2023"

        # 5. Blokada confirm_jobs: liczba zleceń z planu ścieżki, przed danymi logowania Earthdata.
        hp = hyp3_paths(rt, cfg_t, "groningen", "37")
        hp["plan_json"].write_text(json.dumps({"name": "egmscheck_groningen_37", "jobs": [{"name": "x"}] * 5}))
        cfg_t["project"]["earthdata_path"] = str(tmp / "brak_earthdata.json")
        _expect(RuntimeError, task_hyp3_submit, rt, cfg_t, "groningen", "37", None, match="CONFIRM_JOBS['37'] = 5")
        _expect(RuntimeError, task_hyp3_submit, rt, cfg_t, "groningen", "37", 4, match="plan ma 5")
        # Limit kredytów i koszt zlecenia: decyzje sprawdzane przed logowaniem Earthdata (i przed wysłaniem).
        _expect(RuntimeError, task_hyp3_submit, rt, cfg_t, "groningen", "37", 5, match="max_credits")
        cfg_t["hyp3"]["max_credits"] = 10
        _expect(RuntimeError, task_hyp3_submit, rt, cfg_t, "groningen", "37", 5, match="cost_per_job")
        cfg_t["hyp3"]["cost_per_job"] = 1
        _expect(FileNotFoundError, task_hyp3_submit, rt, cfg_t, "groningen", "37", 5, match="Earthdata")

        # 5a. Bramki sekcji, których parametrów zadanie używa: egms (poziomy, wydanie), gnss (układ szeregów tenv3).
        cfg_e = copy.deepcopy(cfg_t)
        cfg_e["egms"]["approved"] = None
        for fn in (task_checks, task_compare_gnss, task_compare_levelling, task_monitoring_archive, task_figures,
                   task_hyp3_plan):
            _expect(RuntimeError, fn, rt, cfg_e, "groningen", match="CHECK_CONFIG['egms']")
        _expect(RuntimeError, task_hyp3_compare, rt, cfg_e, "groningen", "37", match="CHECK_CONFIG['egms']")
        cfg_g = copy.deepcopy(CHECK_CONFIG); cfg_g["gnss"]["approved"] = None
        _expect(RuntimeError, _read_gnss, rt, cfg_g, ["A"], match="CHECK_CONFIG['gnss']")
        assert _read_gnss(rt, cfg_g, []) == {}
        # Metryka bez kolumny: błąd przy wierszu 'ok', jawny NaN przy wierszu z powodem.
        mr = pd.DataFrame({"product": ["p"], "site": ["s"], "track": ["t"], "radius_m": [1.0], "status": ["ok"], "n": [1.0]})
        _expect(KeyError, _metric_rows, mr, "r", ["v_egms"], "n", "REF", match="v_egms")
        nan_row = _metric_rows(mr.assign(status="za mało punktów"), "r", ["v_egms"], "n", "REF")
        assert len(nan_row) == 1 and np.isnan(nan_row["value"].iat[0]) and nan_row["status"].iat[0] == "za mało punktów"
        mcfg = {"radius_main_m": 100, "radii_m": [100, 200], "extract_radius_m": 200}
        _check_radii(mcfg)
        _expect(ValueError, _check_radii, {**mcfg, "radius_main_m": 150}, match="radius_main_m")
        _expect(ValueError, _check_radii, {**mcfg, "radii_m": [100, 300]}, match="extract_radius_m")

        # 6. Pomocnicze: obszar wyszukania, przykłady, punkty naziemne w dwóch typach.
        reg = cfg_t["regions"]["groningen"]
        st = pd.DataFrame({"site": ["S", "T"], "lon_deg": [6.0, 4.9], "lat_deg": [53.0, 53.9]})
        assert _search_lonlat(reg, st, "aoi") == (5.8, 52.9, 7.3, 53.6)
        assert _search_lonlat(reg, st, "aoi_plus_sites") == (4.9, 52.9, 7.3, 53.9)
        _expect(ValueError, _search_lonlat, reg, st, "bbox", match="search_area")
        ex_sites = pd.DataFrame({"site": ["A", "B", "C", "D", "E"], "site_type": "gnss",
                                 "group": ["osiadająca"] * 3 + ["stabilna"] * 2, "vu_mm_yr": [-3.0, -6.0, -4.0, 0.8, -0.2]})
        lev_res = pd.DataFrame({"benchmark_id": ["b1", "b2", "b3", "b4"], "status": ["ok", "ok", "ok", "NaN: x"],
                                "v_lev_mm_yr": [-1.0, -9.0, 0.3, -20.0]})
        assert _example_sites(ex_sites, lev_res, "max_subsidence_median_stable") == ["B", "C", "E", "b2", "b1", "b3"]
        _expect(ValueError, _write_sites, P, pd.DataFrame({"site": ["A"], "group": ["benchmark"]}), "benchmark",
                match="różnych typach")
        # Dwa typy punktów: ponowny zapis tej samej treści (kolejność typów w pliku inna niż w nowym zapisie) nie zmienia
        # pliku - czas modyfikacji sites.csv steruje aktualnością wycinków (task_extract).
        g_rows = pd.DataFrame({"site": ["A"], "group": ["stabilna"], "lat_deg": [53.0], "lon_deg": [6.0],
                               "x_3035": [1.0], "y_3035": [2.0]})
        b_rows = pd.DataFrame({"site": ["0450600001"], "group": ["benchmark"], "lat_deg": [51.0], "lon_deg": [6.5],
                               "x_3035": [3.0], "y_3035": [4.0]})
        _write_sites(P, g_rows, "gnss")
        _write_sites(P, b_rows, "benchmark")
        before, t_before = P["sites"].read_bytes(), P["sites"].stat().st_mtime_ns
        _write_sites(P, g_rows, "gnss")
        _write_sites(P, b_rows, "benchmark")
        assert P["sites"].read_bytes() == before and P["sites"].stat().st_mtime_ns == t_before, "sites.csv zapisany ponownie"
        assert set(_read_sites(P)["site"]) == {"A", "0450600001"}
        print(approvals_table(CHECK_CONFIG).to_string(index=False))
    # Ponawianie chwilowych błędów serwera (503 z land.copernicus.eu, Colab 2026-10-12): 503 x2 -> sukces;
    # 401 i ostatnie 503 idą dalej bez zmian (błąd głośny). time.sleep podmieniony na czas testu.
    import requests
    def _http(code):
        r = requests.models.Response(); r.status_code = code
        return requests.HTTPError(f"{code} test", response=r)
    calls, real_sleep = [], time.sleep
    time.sleep = lambda s: calls.append(s)
    try:
        seq = iter([_http(503), _http(503), "TOKEN"])
        def flaky():
            v = next(seq)
            if isinstance(v, Exception):
                raise v
            return v
        assert _retry_transient(flaky, "test") == "TOKEN" and calls == list(TRANSIENT_WAITS_S[:2])
        calls.clear()
        def denied():
            raise _http(401)
        _expect(requests.HTTPError, _retry_transient, denied, "test", match="401")
        assert calls == [], "401 nie jest ponawiany"
        def down():
            raise _http(503)
        _expect(requests.HTTPError, _retry_transient, down, "test", match="503")
        assert calls == list(TRANSIENT_WAITS_S)
    finally:
        time.sleep = real_sleep
    # Szereg reperu na rycinie: EGMS wyzerowany w epoce t1 niezależnie od jednostki czasu indeksu (ns w pandas 2, us w 3).
    t1 = pd.Timestamp("2019-05-02")
    for unit in ("ns", "us"):
        de = pd.date_range("2019-01-07", "2020-12-31", freq="6D").as_unit(unit)
        lu = pd.DataFrame({"site": "B1", "date": de, "disp_mm": -2.0 * (de - t1).days.to_numpy(float) / 365.25 + 7.0})
        lv = pd.DataFrame({"benchmark_id": "B1", "epoch_date": pd.DatetimeIndex([t1, pd.Timestamp("2020-06-01")]).as_unit(unit),
                           "height_m": [100.0, 99.998]})
        one = _levelling_series_long(lu, lv, pd.Series({"benchmark_id": "B1", "t1": t1}), "r")
        eg = one[one["source"] != LEVELLING_REFERENCE].sort_values("date")
        at_t1 = float(np.interp(0.0, (pd.DatetimeIndex(eg["date"]) - t1).days.to_numpy(float), eg["disp_mm"].to_numpy(float)))
        assert abs(at_t1) < 1e-9, (unit, at_t1)
        assert np.allclose(one.loc[one["source"] == LEVELLING_REFERENCE, "disp_mm"], [0.0, -2.0]), unit
    print("SELFTEST step_05_colab_run OK")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    ap = argparse.ArgumentParser(description="EGMS Check - KROK 5: sterowanie, rejestr, zadania")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--approvals", action="store_true", help="stan zatwierdzeń CHECK_CONFIG")
    a = ap.parse_args()
    if a.selftest:
        _selftest()
    elif a.approvals:
        print(approvals_table(CHECK_CONFIG).to_string(index=False))
    else:
        ap.print_help()
