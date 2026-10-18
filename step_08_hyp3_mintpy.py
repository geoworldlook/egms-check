"""
================================================================================
EGMS Check - KROK 8: ETAP B: WŁASNE PRZETWORZENIE SENTINEL-1 (ASF HyP3 + MintPy) CO 6/12 DNI I DOWIĄZANIE DO EGMS
================================================================================
Etap B pokazu (docs/plans/Plan_v2_pokaz_EGMS_monitoring.md, sekcja 4), interfejs według
docs/plans/Plan_v2_implementacja.md, sekcja 4.4. Kontynuacja kodu E1: manifest i SHA-256 z step_01_ingest,
prędkość (fit_velocity) i mediana w oknie wokół daty (gnss_at_dates) z step_03_compare_gnss, bez zmian.

  I.    Dane logowania NASA Earthdata (JSON: username+password albo token; nic nie drukujemy) i klient HyP3.
  II.   Bursty Sentinel-1 (asf_search, zbiór SLC-BURST) na ścieżce z EGMS L2b; bursty pokrywające punkty naziemne;
        ciągłość burstów w podpasie (nazwa produktu INSAR_ISCE_MULTI_BURST koduje dla każdego podpasa jeden ciąg:
        pierwszy burst + liczba, np. 136231s2n02, MintPy prep_hyp3); stos dat z kompletem burstów (daty niepełne
        usuwane z wypisaniem brakujących burstów).
  III.  Sieć par SBAS (Berardino i in. 2002): każda data z n_neighbors następnymi, odstęp <= max_dt_days.
        Kolejne daty muszą być połączone, inaczej sieć jest niespójna i odwrócenie MintPy nie wyznaczy szeregu
        (smallbaselineApp: "make sure it's fully connected without subsets") -> wyjątek z listą przerw.
  IV.   Zlecenia HyP3 (prepare_* z hyp3_sdk) bez duplikatów: tożsamość zlecenia = (typ, zbiór granul); istniejące
        zlecenia o tej samej nazwie są pomijane; limit kredytów sprawdzany PRZED wysłaniem. Pobranie tylko zleceń
        zakończonych sukcesem, rozpakowanie do <out_dir>/<produkt>/, SHA-256 zipa w MANIFEST.csv; ponowne
        uruchomienie niczego nie zleca ani nie pobiera drugi raz.
  V.    Przycięcie produktów do wspólnego obszaru (rasterio): ten sam układ, rozmiar i siatka pikseli, inaczej
        wyjątek; <produkt>_<warstwa>_clip.tif + kopia <produkt>.txt w katalogu produktu (prep_hyp3 czyta plik .txt
        z TEGO SAMEGO katalogu co plik danych).
  VI.   MintPy 1.6.4: szablon (mintpy.load.processor = hyp3, ścieżki warstw, punkt odniesienia, poprawki),
        nazwa szeregu końcowego (replika TimeSeriesAnalysis.get_timeseries_filename), uruchomienie
        smallbaselineApp.py <szablon> --work-dir <katalog> (mintpy/cli/smallbaselineApp.py).
  VII.  Geometria LOS w konwencji MintPy (utils/utils0.py, get_unit_vector4component_of_interest, comp='enu2los'):
            e = -sin(inc) sin(az),  n = sin(inc) cos(az),  u = cos(inc),
        inc = kąt padania od pionu [deg], az = azymut wektora OD ZIEMI DO SATELITY od północy, przeciwnie do
        ruchu wskazówek zegara [deg] (geometryGeo.h5: incidenceAngle, azimuthAngle; dla HyP3 MintPy przelicza
        lv_theta, lv_phi z radianów: inc = 90 - theta, az = phi - 90; objects/stackDict.py).
        Znak: MintPy ts = -lambda/(4 pi) * faza (ifgram_inversion.py), enu2los: "motion toward satellite as
        positive". EGMS: przyjęte ujemne = oddalanie od satelity i wektor LOS od ziemi do satelity (los_up > 0);
        w dokumentacji niezweryfikowane (CLAUDE.md), sprawdzane na danych kontrolami F4_metodyka, sekcja 2 (step_02).
        Przy tej konwencji ODWRACANIE ZNAKU NIE JEST POTRZEBNE. Kontrola na danych przed porównaniem:
        check_los_vs_egms (ta sama ścieżka: zgodne los_up i znak los_east) oraz corr w align_to_reference.
  VIII. Szeregi w punktach: mediana pikseli okna window_px x window_px, tylko piksele maski maskTempCoh.h5
        (MintPy zapisuje piksele nieodwrócone jako 0, nie NaN, i nie maskuje szeregu: ifgram_inversion.py);
        metry -> mm; format długi (Plan_v2, sekcja 2.2) ze źródłem S1_HYP3_MINTPY. Dowiązanie do EGMS:
        przesunięcie = mediana(własny - EGMS) w zakładce, EGMS w datach własnych = mediana wartości EGMS
        w oknie +-half_window_days (step_03.gnss_at_dates); mniej niż 10 dopasowań -> NaN z powodem.
  IX.   --selftest bez sieci: atrapy asf_search i HyP3, syntetyczne GeoTIFF (UTM) i pliki MintPy (h5py)
        o znanej odpowiedzi; --describe-product (opis pobranego produktu HyP3).

Odstępstwa od specyfikacji 4.4 (do akceptacji autora):
  - submit_missing ma parametr cost_per_job (koszt jednego zlecenia w kredytach HyP3; bez wartości domyślnej,
    z CHECK_CONFIG); max_credits None = RuntimeError (decyzja autora).
  - mintpy_series_at_points ma dodatkowe parametry mask_h5 (maskTempCoh.h5), region i track (kolumny formatu
    długiego, których plik MintPy nie zawiera); wynik ma dodatkową kolumnę status, a track jest tekstem (jak
    step_07._track_label). Wiersze bez szeregu mają los_* NaN, więc przed step_07.validate_long / write_long
    wywołujący rozdziela wynik funkcją split_long_status (szeregi 'ok' + tabela statusów, jak step_07).
  - write_mintpy_template / expected_timeseries_name wymagają w mcfg kluczy deramp i solid_earth_tides (oraz
    weather_model dla troposphere 'pyaps'), których nie ma w CHECK_CONFIG ze specyfikacji; poprawka jonosferyczna
    stale 'no' (jedyna metoda MintPy, split_spectrum, wymaga warstw jonosfery, których produkt HyP3 nie ma);
    mintpy.save.hdfEos5 = no, mintpy.plot = no (przebieg automatyczny; ryciny robi step_07).
  - INSAR_ISCE_BURST tylko dla jednego burstu (produkty różnych burstów nie mają wspólnego obszaru do przycięcia).
    INSAR_ISCE_MULTI_BURST: reguły grupy z asf_search/burst2safe (<= 15 burstów, ciągłość, zachodzenie podpasów)
    sprawdzane przed wysłaniem (check_burst_contiguity); looks tylko z listy hyp3_sdk.
  - clip_to_common_overlap: dwa produkty tej samej pary dat = ValueError (zdublowany DATE12 w stosie MintPy).
  - dodane: product_name_and_type (wzorce nazw z MintPy prep_hyp3), check_burst_contiguity, fill_burst_gaps,
    reference_lalo_from_rule, check_los_vs_egms, split_long_status, describe_product; transform_xy przeniesione
    z prototypu.

Literatura i źródła: Yunjun, Fattahi, Amelung 2019 (MintPy, Computers & Geosciences 133, 104331); Berardino,
Fornaro, Lanari, Sansosti 2002 (SBAS, IEEE TGRS 40(11)); dokumentacja ASF HyP3, burst InSAR product guide
(hyp3-docs.asf.alaska.edu, odnośniki w docstringu mintpy/prep_hyp3.py); kod źródłowy MintPy 1.6.4, hyp3_sdk 7.7.8
i asf_search 14.0.3 (funkcje cytowane przy miejscach użycia). Nic z tego nie było uruchamiane na prawdziwych
danych (serwery ASF/Earthdata niedostępne ze środowiska, w którym powstał kod).

Konwencje: przemieszczenia w mm, prędkości w mm/rok, ujemne = osiadanie / oddalanie od satelity; punkty naziemne
w stopniach WGS84 (lon_deg, lat_deg); produkty HyP3 i MintPy w układzie UTM pliku (EPSG z atrybutów); EGMS
EPSG:3035. Parametry eksperymentu (ścieżka, daty, sieć par, typ zlecenia, rozmiar okna, odniesienie, poprawki
MintPy, limit kredytów) pochodzą z CHECK_CONFIG; sygnatury nie mają wartości domyślnych.
================================================================================
"""

import argparse
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from step_01_ingest import manifest_path_of, sha256_file, update_manifest
from step_03_compare_gnss import DAYS_PER_YEAR, fit_velocity, gnss_at_dates, years_since

# Biblioteki ASF ładowane przy pierwszym użyciu przez _lib(); test (albo harness) może podstawić tu atrapę.
# Wywołania zawsze przez atrybut modułu (asf_search.search, hyp3_sdk.HyP3), nigdy "from x import y".
asf_search = None
hyp3_sdk = None

SOURCE = "S1_HYP3_MINTPY"
MM_PER_M = 1000.0
HYP3_LICENCE = "ASF HyP3 products: open, Copernicus Sentinel data (ESA) processed by ASF"
JOB_TYPES = ("INSAR_ISCE_MULTI_BURST", "INSAR_ISCE_BURST")
HYP3_LOOKS = ("20x4", "10x2", "5x1")    # hyp3_sdk 7.7.8, HyP3.prepare_insar_isce_*_job: looks: Literal[...]
MAX_MULTI_BURST = 15                    # asf_search 14.0.3, S1MultiBurstGroup.check_group_validity (z burst2safe)
JOB_STATUS_RANK = {"SUCCEEDED": 0, "RUNNING": 1, "PENDING": 2}     # wybór spośród zleceń o tej samej tożsamości
BURST_COLUMNS = ["scene_name", "full_burst_id", "start_time", "date", "platform", "flight_direction",
                 "relative_orbit", "footprint_wkt"]
STACK_COLUMNS = ["date", "scene_names", "burst_ids", "platform", "n_bursts"]
JOB_TABLE_COLUMNS = ["job_type", "reference_first", "secondary_first", "n_granules", "status", "job_id", "status_code"]
DOWNLOAD_COLUMNS = ["job_id", "job_type", "status_code", "product_name", "date1", "date2", "product_dir", "zip_path",
                    "sha256", "status"]
CLIP_COLUMNS = ["product", "layer", "clip_path", "width", "height", "left", "bottom", "right", "top", "status"]
LONG_COLUMNS = ["region", "source", "site", "track", "direction", "component", "los_east", "los_north", "los_up",
                "date", "disp_mm", "ref_date", "reference", "n_points", "status"]
SERIES_KEY = ["region", "source", "site", "track", "component"]
SERIES_STATUS_COLUMNS = SERIES_KEY + ["direction", "n_points", "ref_date", "reference", "status"]
ALIGN_COLUMNS = ["site", "track", "n_matched", "offset_mm", "std_diff_mm", "corr", "status"]
EGMS_ALIGN_NEED = ["source", "site", "track", "date", "disp_mm", "ref_date", "reference"]
MIN_ALIGN_MATCHES = 10                  # reguła specyfikacji 4.4 (jak minimum obserwacji w step_03.fit_velocity)
GRID_TOL_PX = 1e-6                      # tolerancja wyrównania siatek pikseli [ułamek piksela]

FULL_BURST_ID = re.compile(r"^(?P<track>\d{3})_(?P<burst>\d{6})_IW(?P<swath>[123])$")   # np. 064_136231_IW2

# Przeniesione z MintPy 1.6.4, mintpy/prep_hyp3.py, _get_product_name_and_type (wzorce bez zmian).
HYP3_NAME_PATTERNS = (
    (r"S1_\d{6}_IW[123](_\d{8}){2}_(VV|HH)_INT\d{2}_[0-9A-F]{4}", "INSAR_ISCE_BURST"),
    (r"S1_\d{3}_\d{6}s1n\d{2}-\d{6}s2n\d{2}-\d{6}s3n\d{2}_IW(_\d{8}){2}_(VV|HH)_INT\d{2}_[0-9A-F]{4}",
     "INSAR_ISCE_MULTI_BURST"),
    (r"S1[ABCD]{2}(_\d{8}T\d{6}){2}_(VV|HH)[PRO]\d{3,4}_INT\d{2}_G_[uw][ec][123F]_[0-9A-F]{4}", "INSAR_GAMMA"),
)

# Warstwy produktu HyP3 -> klucze szablonu MintPy (defaults/smallbaselineApp.cfg, sekcja load_data).
LAYER_TEMPLATE_KEYS = {"unw_phase": "mintpy.load.unwFile", "corr": "mintpy.load.corFile",
                       "conncomp": "mintpy.load.connCompFile", "dem": "mintpy.load.demFile",
                       "lv_theta": "mintpy.load.incAngleFile", "lv_phi": "mintpy.load.azAngleFile",
                       "water_mask": "mintpy.load.waterMaskFile"}
IFG_LAYERS = ("unw_phase", "corr", "conncomp")
TROPO_METHODS = ("no", "height_correlation", "pyaps")     # gacos / opera wymagają katalogów danych: nieobsługiwane
RAMP_LIST = ["linear", "linear_range", "linear_azimuth", "quadratic", "quadratic_range", "quadratic_azimuth"]  # objects/ramp.py
NAME_KEYS = ["mintpy.solidEarthTides", "mintpy.ionosphericDelay.method", "mintpy.troposphericDelay.method",
             "mintpy.deramp", "mintpy.topographicResidual"]
MINTPY_GEOMETRY = "inputs/geometryGeo.h5"     # load_data.py: dane geokodowane (HyP3)
MINTPY_MASK = "maskTempCoh.h5"                # smallbaselineApp.generate_temporal_coherence_mask
REFERENCE_RULES = ("stable_gnss_min_abs_vu",)


# ==============================================================================
# 0. POMOCNICZE
# ==============================================================================
def _lib(name: str):
    """Moduł asf_search / hyp3_sdk: atrapa podstawiona w tym module albo prawdziwy import (bez cichych zamienników)."""
    mod = globals()[name]
    return importlib.import_module(name) if mod is None else mod


def _require(name: str, value):
    """Parametr eksperymentu musi mieć wartość; None = decyzja autora nieustalona (CLAUDE.md, zasada 2)."""
    if value is None:
        raise ValueError(f"Parametr '{name}' = None: decyzja autora nieustalona (CHECK_CONFIG).")
    return value


def _require_columns(df: pd.DataFrame, cols: list, what: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"{what}: brak kolumn {missing}; dostępne: {list(df.columns)}")


def _track_label(x) -> str:
    """
    Etykieta ścieżki jako tekst, ta sama reguła co step_07_monitoring._track_label (format długi przechowuje track
    jako tekst; validate_long odrzuca liczby): 88, 88.0, "88" -> "88"; "L3" bez zmian; pusta, NaN, bool = wyjątek.
    """
    if isinstance(x, str):
        if not x.strip():
            raise ValueError("Pusta etykieta ścieżki")
        return x
    if isinstance(x, (bool, np.bool_)):
        raise TypeError(f"Etykieta ścieżki nie może być typu bool: {x!r}")
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    if isinstance(x, (float, np.floating)) and np.isfinite(x) and float(x).is_integer():
        return str(int(x))
    raise ValueError(f"Nieprawidłowa etykieta ścieżki: {x!r}")


# Przeniesione z prototypes/egms_simple_check.py (transform_xy), zachowanie bez zmian.
def transform_xy(x, y, epsg_from: int, epsg_to: int):
    """Przeliczenie współrzędnych (pyproj, kolejność x/y zawsze lon/lat lub easting/northing)."""
    from pyproj import Transformer
    tr = Transformer.from_crs(epsg_from, epsg_to, always_xy=True)
    return tr.transform(x, y)


# ==============================================================================
# I. DANE LOGOWANIA EARTHDATA I KLIENT HyP3
# ==============================================================================
def load_earthdata_credentials(path) -> dict:
    """
    Plik JSON poza repozytorium (np. MyDrive/GeoWorldLook/secrets/earthdata.json): {"username", "password"}
    albo {"token"} (Earthdata bearer token). Zwraca tylko te klucze. Wartości nigdy nie są drukowane; komunikaty
    błędów podają wyłącznie nazwy kluczy.
    """
    p = Path(_require("earthdata_path", path))
    if not p.is_file():
        raise FileNotFoundError(f"Brak pliku danych logowania Earthdata: {p}")
    d = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(d, dict):
        raise ValueError(f"{p}: oczekiwano obiektu JSON z kluczami username+password albo token")
    if "token" in d and ("username" in d or "password" in d):
        raise ValueError(f"{p}: podaj albo token, albo username+password, nie oba (obecne klucze: {sorted(d)})")
    keys = ("token",) if "token" in d else ("username", "password")
    missing = [k for k in keys if k not in d]
    if missing:
        raise KeyError(f"{p}: brak kluczy {missing}; obecne klucze: {sorted(d)}")
    empty = [k for k in keys if not isinstance(d[k], str) or not d[k].strip()]
    if empty:
        raise ValueError(f"{p}: puste lub nietekstowe wartości kluczy {empty}")
    return {k: d[k] for k in keys}


def hyp3_client(creds: dict):
    """
    hyp3_sdk.HyP3 na produkcyjnym API ASF (hyp3_sdk.PROD_API). Uwaga z hyp3_sdk: wszystkie zlecenia HyP3 są
    publicznie widoczne - nazwa zlecenia nie może zawierać danych osobowych.
    """
    lib = _lib("hyp3_sdk")
    if set(creds) == {"token"}:
        return lib.HyP3(api_url=lib.PROD_API, token=creds["token"])
    if set(creds) == {"username", "password"}:
        return lib.HyP3(api_url=lib.PROD_API, username=creds["username"], password=creds["password"])
    raise ValueError(f"Nieznany zestaw kluczy danych logowania: {sorted(creds)}")


# ==============================================================================
# II. BURSTY SENTINEL-1 I STOS DAT
# ==============================================================================
def _parse_burst_id(full_burst_id: str) -> tuple[int, int, int]:
    m = FULL_BURST_ID.match(str(full_burst_id))
    if m is None:
        raise ValueError(f"fullBurstID {full_burst_id!r} niezgodny ze wzorcem {FULL_BURST_ID.pattern}")
    return int(m["track"]), int(m["burst"]), int(m["swath"])


def search_bursts(aoi_wkt: str, relative_orbit: int, start, end, polarization: str) -> pd.DataFrame:
    """
    asf_search.search(dataset=SLC-BURST, intersectsWith=aoi_wkt, relativeOrbit, start, end, polarization).
    Właściwości produktu według asf_search/Products/S1BurstProduct.py: sceneName, startTime (UTC, ISO),
    platform, flightDirection, pathNumber, polarization, burst.fullBurstID; geometry = GeoJSON [lon, lat].
    Wynik: BURST_COLUMNS; start_time bez strefy, w UTC; date = dzień UTC. Pusty wynik, inna ścieżka, inna
    polaryzacja, kilka kierunków orbity, zdublowana scena lub para (burst, dzień) = wyjątek.
    """
    for n, v in (("aoi_wkt", aoi_wkt), ("relative_orbit", relative_orbit), ("start", start), ("end", end),
                 ("polarization", polarization)):
        _require(f"hyp3.{n}", v)
    from shapely.geometry import shape
    lib = _lib("asf_search")
    res = lib.search(dataset=lib.DATASET.SLC_BURST, intersectsWith=aoi_wkt, relativeOrbit=int(relative_orbit),
                     start=start, end=end, polarization=polarization)
    rows = []
    for p in res:
        pr = p.properties
        rows.append({"scene_name": pr["sceneName"], "full_burst_id": pr["burst"]["fullBurstID"],
                     "start_time": pr["startTime"], "platform": pr["platform"],
                     "flight_direction": pr["flightDirection"], "relative_orbit": pr["pathNumber"],
                     "polarization": pr["polarization"], "footprint_wkt": shape(p.geometry).wkt})
    if not rows:
        raise RuntimeError(f"asf_search: brak burstów SLC dla ścieżki {relative_orbit}, {start} - {end}, {polarization}")
    df = pd.DataFrame(rows)
    # ISO8601: CMR podaje czas z częścią ułamkową sekundy albo bez; pandas 2.x bez tego formatu zgaduje wzorzec
    # z pierwszego wiersza i odrzuca wiersze o innej precyzji (ValueError na prawdziwym wyniku wyszukania).
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True, format="ISO8601").dt.tz_convert(None)
    df["date"] = df["start_time"].dt.normalize()
    df["flight_direction"] = df["flight_direction"].str.lower()
    df["relative_orbit"] = df["relative_orbit"].astype(int)
    bad = df[df["relative_orbit"] != int(relative_orbit)]
    if len(bad):
        raise ValueError(f"asf_search zwrócił inne ścieżki: {sorted(bad['relative_orbit'].unique())}")
    bad = df[df["polarization"] != polarization]
    if len(bad):
        raise ValueError(f"asf_search zwrócił inne polaryzacje: {sorted(bad['polarization'].unique())}")
    tracks = {_parse_burst_id(b)[0] for b in df["full_burst_id"]}
    if tracks != {int(relative_orbit)}:
        raise ValueError(f"fullBurstID ze ścieżek {sorted(tracks)}, oczekiwano {relative_orbit}")
    if df["flight_direction"].nunique() != 1:
        raise ValueError(f"Kilka kierunków orbity na jednej ścieżce: {sorted(df['flight_direction'].unique())}")
    for keys in (["scene_name"], ["full_burst_id", "date"]):
        dup = df.duplicated(keys, keep=False)
        if dup.any():
            raise ValueError(f"Zdublowany klucz {keys} w wyniku asf_search, np. "
                             f"{df.loc[dup, keys].head(4).astype(str).to_dict('records')}")
    print(f"Bursty ścieżki {relative_orbit}: {len(df)} scen, {df['full_burst_id'].nunique()} identyfikatorów, "
          f"{df['date'].nunique()} dat ({df['date'].min().date()} - {df['date'].max().date()}).")
    return df[BURST_COLUMNS].sort_values(["date", "full_burst_id"]).reset_index(drop=True)


def bursts_covering_points(bursts: pd.DataFrame, points_lonlat: pd.DataFrame) -> list[str]:
    """
    Posortowane fullBurstID, których obrys (w dowolnej dacie) zawiera co najmniej jeden punkt (lon_deg, lat_deg).
    Punkty poza wszystkimi burstami są wypisywane; żaden pokryty punkt = RuntimeError.
    """
    from shapely import wkt
    from shapely.geometry import Point
    _require_columns(bursts, ["full_burst_id", "footprint_wkt"], "bursts")
    _require_columns(points_lonlat, ["lon_deg", "lat_deg"], "points_lonlat")
    ll = points_lonlat[["lon_deg", "lat_deg"]].to_numpy(float)
    if len(ll) == 0 or not np.isfinite(ll).all():
        raise ValueError(f"points_lonlat: pusta tabela albo współrzędne NaN (wiersze {np.where(~np.isfinite(ll).all(axis=1))[0].tolist()})")
    pts = [Point(lo, la) for lo, la in ll]
    labels = list(points_lonlat["site"]) if "site" in points_lonlat.columns else list(range(len(pts)))
    hit, covered = set(), np.zeros(len(pts), bool)
    for bid, g in bursts.groupby("full_burst_id"):
        polys = [wkt.loads(w) for w in g["footprint_wkt"].unique()]
        inside = np.array([any(poly.covers(pt) for poly in polys) for pt in pts])
        if inside.any():
            hit.add(bid)
            covered |= inside
    if not covered.any():
        raise RuntimeError("Żaden punkt nie leży w burstach z wyszukania (zła ścieżka albo obszar?).")
    if not covered.all():
        print(f"UWAGA: punkty poza burstami tej ścieżki: {[labels[i] for i in np.where(~covered)[0]]}")
    return sorted(hit)


def check_burst_contiguity(burst_ids: list) -> None:
    """
    Grupa burstów jednego zlecenia INSAR_ISCE_MULTI_BURST. Reguły:
      - jedna ścieżka; w każdym podpasie numery burstów bez przerw (nazwa produktu, MintPy prep_hyp3, koduje dla
        podpasa tylko pierwszy burst i ich liczbę; burst2safe wymaga kolejnych numerów);
      - co najwyżej MAX_MULTI_BURST par burst/podpas, a w sąsiednich (kolejnych użytych) podpasach pierwszy i ostatni
        numer różnią się najwyżej o 1 - przeniesione z asf_search 14.0.3, S1MultiBurstProduct.py,
        S1MultiBurstGroup.check_group_validity (zapożyczone tam z burst2safe, którego używa HyP3). Grupa łamiąca te
        reguły kończy się zleceniem FAILED po pobraniu kredytów, więc sprawdzamy przed wysłaniem.
    """
    parsed = [_parse_burst_id(b) for b in burst_ids]
    if not parsed or len(set(burst_ids)) != len(burst_ids):
        raise ValueError(f"Pusta albo zdublowana lista burstów: {burst_ids}")
    if len({t for t, _, _ in parsed}) != 1:
        raise ValueError(f"Bursty z kilku ścieżek: {sorted(burst_ids)}")
    if len(parsed) > MAX_MULTI_BURST:
        raise ValueError(f"{len(parsed)} burstów > {MAX_MULTI_BURST} (limit grupy INSAR_ISCE_MULTI_BURST); podziel obszar")
    gaps, ranges = [], {}
    for sw in sorted({s for _, _, s in parsed}):
        nums = sorted(n for _, n, s in parsed if s == sw)
        gaps += [f"IW{sw}: {a:06d} -> {b:06d}" for a, b in zip(nums[:-1], nums[1:]) if b - a != 1]
        ranges[sw] = (nums[0], nums[-1])
    if gaps:
        raise ValueError(f"Bursty nieciągłe w podpasie ({gaps}); uzupełnij fill_burst_gaps albo podziel obszar.")
    sws = sorted(ranges)
    bad = [f"IW{a} {ranges[a]} / IW{b} {ranges[b]}" for a, b in zip(sws[:-1], sws[1:])
           if abs(ranges[a][0] - ranges[b][0]) > 1 or abs(ranges[a][1] - ranges[b][1]) > 1]
    if bad:
        raise ValueError(f"Podpasy nie zachodzą na siebie (pierwszy/ostatni burst różni się o > 1): {bad}")


def fill_burst_gaps(burst_ids: list) -> list[str]:
    """Uzupełnia przerwy w numeracji burstów w każdym podpasie (min..max); dodane identyfikatory są wypisywane."""
    parsed = [_parse_burst_id(b) for b in burst_ids]
    tracks = {t for t, _, _ in parsed}
    if len(tracks) != 1:
        raise ValueError(f"Bursty z kilku ścieżek: {sorted(burst_ids)}")
    track = tracks.pop()
    out = set()
    for sw in {s for _, _, s in parsed}:
        nums = [n for _, n, s in parsed if s == sw]
        out |= {f"{track:03d}_{n:06d}_IW{sw}" for n in range(min(nums), max(nums) + 1)}
    added = sorted(out - set(burst_ids))
    if added:
        print(f"Dodane bursty dla ciągłości: {added}")
    return sorted(out)


def acquisition_stack(bursts: pd.DataFrame, burst_ids: list) -> pd.DataFrame:
    """
    Daty, w których istnieją WSZYSTKIE bursty burst_ids; scene_names w kolejności burst_ids (ta sama kolejność
    dla każdej daty). Daty niepełne są usuwane z wypisaniem brakujących burstów.
    """
    _require_columns(bursts, BURST_COLUMNS, "bursts")
    burst_ids = list(burst_ids)
    if not burst_ids or len(set(burst_ids)) != len(burst_ids):
        raise ValueError(f"burst_ids puste albo zdublowane: {burst_ids}")
    unknown = sorted(set(burst_ids) - set(bursts["full_burst_id"]))
    if unknown:
        raise ValueError(f"Bursty spoza wyniku wyszukania: {unknown}")
    b = bursts[bursts["full_burst_id"].isin(burst_ids)]
    dup = b.duplicated(["full_burst_id", "date"], keep=False)
    if dup.any():                        # by_id.at[...] zwróciłby wtedy serię zamiast nazwy sceny
        raise ValueError(f"Zdublowane (burst, data): {b.loc[dup, ['full_burst_id', 'date']].astype(str).head(4).to_dict('records')}")
    rows, dropped = [], []
    for date, g in b.groupby("date"):
        by_id = g.set_index("full_burst_id")
        miss = [i for i in burst_ids if i not in by_id.index]
        if miss:
            dropped.append((str(date.date()), miss))
            continue
        if g["platform"].nunique() != 1:
            raise ValueError(f"{date.date()}: bursty z kilku platform {sorted(g['platform'].unique())}")
        rows.append({"date": date, "scene_names": [by_id.at[i, "scene_name"] for i in burst_ids],
                     "burst_ids": tuple(burst_ids), "platform": g["platform"].iat[0], "n_bursts": len(burst_ids)})
    if dropped:
        print(f"Usunięte daty bez kompletu burstów ({len(dropped)}): {dropped}")
    if not rows:
        raise RuntimeError(f"Brak dat z kompletem burstów {burst_ids}")
    return pd.DataFrame(rows, columns=STACK_COLUMNS).reset_index(drop=True)


# ==============================================================================
# III. SIEĆ PAR SBAS I ZLECENIA HyP3
# ==============================================================================
def sbas_pairs(dates, n_neighbors: int, max_dt_days: float) -> list[tuple]:
    """
    Każda data z n_neighbors następnymi datami, jeśli odstęp <= max_dt_days. Para kolejnych dat dalej niż
    max_dt_days rozcina sieć -> ValueError z listą przerw (niespójnej sieci SBAS MintPy nie odwróci).
    """
    n = int(_require("hyp3.n_neighbors", n_neighbors))
    max_dt = float(_require("hyp3.max_dt_days", max_dt_days))
    if n < 1 or max_dt <= 0:
        raise ValueError(f"n_neighbors={n_neighbors} (>= 1), max_dt_days={max_dt_days} (> 0)")
    d = pd.DatetimeIndex(pd.to_datetime(list(dates))).unique().sort_values()
    if len(d) < 2:
        raise ValueError(f"Za mało dat do sieci par: {len(d)}")
    dt = np.diff(d.to_numpy()) / np.timedelta64(1, "D")
    gaps = [f"{d[i].date()} -> {d[i + 1].date()} ({dt[i]:.0f} dni)" for i in np.where(dt > max_dt)[0]]
    if gaps:
        raise ValueError(f"Sieć par niespójna, przerwy > {max_dt:g} dni: {gaps}")
    pairs = []
    for i in range(len(d)):
        for j in range(i + 1, min(i + n, len(d) - 1) + 1):
            if (d[j] - d[i]) / pd.Timedelta(days=1) <= max_dt:
                pairs.append((d[i], d[j]))
    return pairs


def prepare_jobs(stack: pd.DataFrame, pairs: list, job_type: str, looks: str, apply_water_mask: bool,
                 name: str) -> list[dict]:
    """
    Jedno zlecenie na parę dat (hyp3_sdk.HyP3.prepare_* - metody klasy, bez sieci).
    INSAR_ISCE_MULTI_BURST: reference = sceny z d1, secondary = sceny z d2, ta sama kolejność burstów;
    bursty muszą być ciągłe (check_burst_contiguity). INSAR_ISCE_BURST: tylko dla jednego burstu.
    """
    for n, v in (("job_type", job_type), ("looks", looks), ("apply_water_mask", apply_water_mask), ("name", name)):
        _require(f"hyp3.{n}", v)
    if job_type not in JOB_TYPES:
        raise ValueError(f"Nieobsługiwany typ zlecenia {job_type!r}; dozwolone {JOB_TYPES}")
    if looks not in HYP3_LOOKS:
        raise ValueError(f"looks {looks!r}: dozwolone {HYP3_LOOKS} (hyp3_sdk)")
    if not isinstance(apply_water_mask, bool):
        raise ValueError(f"apply_water_mask musi być True/False, jest {apply_water_mask!r}")
    _require_columns(stack, STACK_COLUMNS, "stack")
    if not pairs:
        raise ValueError("Pusta lista par")
    ids = stack["burst_ids"].iat[0]
    if job_type == "INSAR_ISCE_MULTI_BURST":
        check_burst_contiguity(list(ids))
    elif len(ids) != 1:
        raise ValueError(f"INSAR_ISCE_BURST wymaga jednego burstu, jest {len(ids)}: {list(ids)}")
    scenes = stack.set_index("date")["scene_names"]
    missing = sorted({str(pd.Timestamp(x).date()) for p in pairs for x in p if pd.Timestamp(x) not in scenes.index})
    if missing:
        raise KeyError(f"Daty par spoza stosu: {missing}")
    lib = _lib("hyp3_sdk")
    jobs = []
    for d1, d2 in sorted((pd.Timestamp(a), pd.Timestamp(b)) for a, b in pairs):
        if d2 <= d1:
            raise ValueError(f"Para {d1.date()} -> {d2.date()}: druga data nie jest późniejsza")
        if job_type == "INSAR_ISCE_MULTI_BURST":
            jobs.append(lib.HyP3.prepare_insar_isce_multi_burst_job(
                reference=list(scenes[d1]), secondary=list(scenes[d2]), name=name,
                apply_water_mask=apply_water_mask, looks=looks))
        else:
            jobs.append(lib.HyP3.prepare_insar_isce_burst_job(
                scenes[d1][0], scenes[d2][0], name=name, apply_water_mask=apply_water_mask, looks=looks))
    return jobs


def _granules(job_type: str, params: dict) -> list:
    if job_type == "INSAR_ISCE_MULTI_BURST":
        return list(params["reference"]) + list(params["secondary"])
    if job_type == "INSAR_ISCE_BURST":
        return list(params["granules"])
    raise ValueError(f"Zlecenie typu {job_type!r} pod tą nazwą: nieobsługiwane (dozwolone {JOB_TYPES})")


def _job_key(job_type: str, params: dict) -> tuple:
    """Tożsamość zlecenia: (typ, zbiór granul referencyjnych i wtórnych)."""
    return job_type, frozenset(_granules(job_type, params))


def _first_granules(job_type: str, params: dict) -> tuple:
    if job_type == "INSAR_ISCE_MULTI_BURST":
        return params["reference"][0], params["secondary"][0]
    return params["granules"][0], params["granules"][1]


def submit_missing(hyp3, jobs: list, name: str, max_credits: float, cost_per_job: float) -> pd.DataFrame:
    """
    Wysyła tylko zlecenia, których jeszcze nie ma (hyp3.find_jobs(name=name); tożsamość = typ + zbiór granul).
    Ta sama tożsamość z innym looks / apply_water_mask = ValueError (produkty o różnych parametrach w jednym stosie).
    Koszt = liczba nowych zleceń x cost_per_job [kredyty HyP3]; przekroczenie max_credits albo pozostałych kredytów
    konta (hyp3.check_credits(); None = konto bez limitu) = RuntimeError PRZED wysłaniem.
    Zlecenia istniejące, także nieudane (FAILED), nie są wysyłane ponownie; ich liczba jest wypisywana.
    """
    _require("hyp3.name", name)
    if max_credits is None:
        raise RuntimeError("CHECK_CONFIG['hyp3']['max_credits'] = None: limit kredytów HyP3 to decyzja autora.")
    cost = float(_require("hyp3.cost_per_job", cost_per_job))
    if cost <= 0:
        raise ValueError(f"cost_per_job = {cost_per_job}: oczekiwano > 0")
    if not jobs:
        raise ValueError("Pusta lista zleceń")
    wrong = sorted({j.get("name") for j in jobs if j.get("name") != name}, key=str)
    if wrong:
        raise ValueError(f"Zlecenia z inną nazwą niż {name!r}: {wrong}")
    keys = [_job_key(j["job_type"], j["job_parameters"]) for j in jobs]
    if len(set(keys)) != len(keys):
        raise ValueError("Zdublowane zlecenia na liście jobs")
    # Kilka zleceń o tej samej tożsamości (np. FAILED i ponowione ręcznie): raportujemy najlepsze
    # (SUCCEEDED > RUNNING > PENDING > FAILED / inne), niezależnie od kolejności zwróconej przez API.
    existing, n_same = {}, Counter()
    for job in hyp3.find_jobs(name=name):
        k = _job_key(job.job_type, job.job_parameters)
        n_same[k] += 1
        if k not in existing or JOB_STATUS_RANK.get(job.status_code, 3) < JOB_STATUS_RANK.get(existing[k].status_code, 3):
            existing[k] = job
    multi = sum(1 for v in n_same.values() if v > 1)
    if multi:
        print(f"UWAGA: {multi} par granul ma kilka zleceń pod nazwą {name!r} (sprawdź duplikaty produktów przed MintPy).")
    conflicts = []
    for k, j in zip(keys, jobs):
        if k in existing:
            old = existing[k].job_parameters
            conflicts += [f"{_first_granules(k[0], j['job_parameters'])[0]}: {p} {old[p]!r} != {j['job_parameters'][p]!r}"
                          for p in ("looks", "apply_water_mask") if p in old and old[p] != j["job_parameters"][p]]
    if conflicts:
        raise ValueError(f"Istniejące zlecenia o tych samych granulach mają inne parametry: {conflicts[:5]}")
    new = [j for k, j in zip(keys, jobs) if k not in existing]
    failed = [k for k in keys if k in existing and existing[k].status_code == "FAILED"]
    if failed:
        print(f"UWAGA: {len(failed)} istniejących zleceń ma status FAILED; nie są wysyłane ponownie.")
    if new:
        need = len(new) * cost
        if need > float(max_credits):
            raise RuntimeError(f"{len(new)} nowych zleceń x {cost:g} = {need:g} kredytów > max_credits {max_credits}")
        remaining = hyp3.check_credits()
        if remaining is not None and need > float(remaining):
            raise RuntimeError(f"{len(new)} nowych zleceń x {cost:g} = {need:g} kredytów > pozostałe {remaining}")
    submitted = {}
    for i in range(0, len(new), 200):       # porcje jak domyślne n w hyp3_sdk.util.chunk
        for job in hyp3.submit_prepared_jobs(new[i:i + 200]):
            submitted[_job_key(job.job_type, job.job_parameters)] = job
    rows = []
    for k, j in zip(keys, jobs):
        job = existing.get(k) or submitted.get(k)
        if job is None:
            raise RuntimeError(f"HyP3 nie potwierdził zlecenia {_first_granules(k[0], j['job_parameters'])}")
        ref, sec = _first_granules(k[0], j["job_parameters"])
        rows.append({"job_type": k[0], "reference_first": ref, "secondary_first": sec, "n_granules": len(k[1]),
                     "status": "existing" if k in existing else "submitted", "job_id": job.job_id,
                     "status_code": job.status_code})
    out = pd.DataFrame(rows, columns=JOB_TABLE_COLUMNS)
    print(f"Zlecenia HyP3 '{name}': wysłane {int((out['status'] == 'submitted').sum())}, "
          f"istniejące {int((out['status'] == 'existing').sum())}.")
    return out


# ==============================================================================
# IV. POBRANIE I ROZPAKOWANIE PRODUKTÓW
# ==============================================================================
def product_name_and_type(filename: str) -> tuple[str, str]:
    """Nazwa produktu i typ zlecenia z nazwy pliku (wzorce MintPy prep_hyp3); nazwa nierozpoznana = ValueError."""
    for pattern, job_type in HYP3_NAME_PATTERNS:
        m = re.match(pattern, filename)
        if m:
            return m.group(), job_type
    raise ValueError(f"Nazwa {filename!r} niezgodna z wzorcami produktów HyP3 czytanych przez MintPy")


def product_dates(product: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Daty pary z nazwy produktu (indeksy pól jak w MintPy prep_hyp3.add_hyp3_metadata)."""
    name, job_type = product_name_and_type(product)
    if name != product:
        raise ValueError(f"{product!r}: po nazwie produktu są dodatkowe znaki")
    parts = name.split("_")
    if job_type == "INSAR_ISCE_BURST":
        d = parts[3:5]
    elif job_type == "INSAR_ISCE_MULTI_BURST":
        d = parts[4:6]
    else:
        d = [x[:8] for x in parts[1:3]]
    return pd.Timestamp(d[0]), pd.Timestamp(d[1])


def _extract_product(zip_path: Path, product: str, out_dir: Path) -> None:
    """Rozpakowanie przez katalog tymczasowy; każdy element zipa musi leżeć w <produkt>/ (bez '..')."""
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        bad = [n for n in names if not n.startswith(f"{product}/") or ".." in Path(n).parts]
        if bad:
            raise ValueError(f"{zip_path.name}: elementy poza katalogiem {product}/: {bad[:5]}")
        if f"{product}/{product}.txt" not in names:
            raise ValueError(f"{zip_path.name}: brak pliku metadanych {product}.txt")
        tmp = out_dir / "_partial" / f"extract_{product}"
        if tmp.exists():
            shutil.rmtree(tmp)
        zf.extractall(tmp)
    dest = out_dir / product
    if dest.exists():
        raise FileExistsError(f"{dest} istnieje bez {product}.txt: sprawdź ręcznie (nie nadpisuję danych surowych)")
    (tmp / product).replace(dest)
    tmp.rmdir()


def download_succeeded(hyp3, name: str, out_dir, manifest_path, project_dir, downloaded_by: str) -> pd.DataFrame:
    """
    Zlecenia name: pobranie tylko SUCCEEDED (Job.download_files) do <out_dir>/_partial/<job_id>/, przeniesienie zipa
    do <out_dir>/<produkt>.zip, rozpakowanie do <out_dir>/<produkt>/, wiersz MANIFEST.csv z SHA-256 zipa.
    Produkt już rozpakowany jest pomijany (status 'existing'); zip bez katalogu jest tylko rozpakowany.
    Zlecenia nieudane, w toku i wygasłe: wiersz ze statusem i komunikat UWAGA (nie ma ich w stosie).
    """
    for n, v in (("name", name), ("out_dir", out_dir), ("manifest_path", manifest_path),
                 ("project_dir", project_dir), ("downloaded_by", downloaded_by)):
        _require(n, v)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    batch = list(hyp3.find_jobs(name=name))
    if not batch:
        raise RuntimeError(f"Brak zleceń HyP3 o nazwie {name!r}")
    counts = Counter(j.status_code for j in batch)
    print(f"Zlecenia '{name}': {dict(counts)}")
    not_ok = {k: v for k, v in counts.items() if k != "SUCCEEDED"}
    if not_ok:
        print(f"UWAGA: zlecenia bez produktu: {not_ok} (FAILED nie wróci; RUNNING/PENDING - uruchom ponownie później).")
    in_manifest = set()
    if Path(manifest_path).exists():
        in_manifest = set(pd.read_csv(manifest_path, dtype=str)["file_path"])
    rows = []
    for job in batch:
        row = {"job_id": job.job_id, "job_type": job.job_type, "status_code": job.status_code}
        if not job.succeeded():
            rows.append({**row, "status": f"brak produktu: zlecenie {job.status_code}"})
            continue
        zips = [f for f in (job.files or []) if f["filename"].endswith(".zip")]
        if len(zips) != 1:
            raise ValueError(f"Zlecenie {job.job_id}: oczekiwano jednego zipa, pliki: {[f['filename'] for f in job.files or []]}")
        f = zips[0]
        product = f["filename"][:-4]
        d1, d2 = product_dates(product)
        zip_path, dest = out_dir / f["filename"], out_dir / product
        row.update(product_name=product, date1=d1, date2=d2, product_dir=str(dest), zip_path=str(zip_path))
        if (dest / f"{product}.txt").exists():
            status = "existing"
        else:
            if not zip_path.exists():
                if job.expired():
                    print(f"UWAGA: zlecenie {job.job_id} ({product}) wygasło przed pobraniem.")
                    rows.append({**row, "product_dir": None, "status": "brak produktu: zlecenie wygasło"})
                    continue
                part = out_dir / "_partial" / job.job_id
                if part.exists():
                    shutil.rmtree(part)            # pozostałość przerwanego pobrania (nasz katalog tymczasowy)
                got = [Path(p) for p in job.download_files(part, True)]
                src = part / f["filename"]
                if src not in got:
                    raise FileNotFoundError(f"Zlecenie {job.job_id}: pobrano {[p.name for p in got]}, brak {f['filename']}")
                if f.get("size") is not None and src.stat().st_size != int(f["size"]):
                    raise IOError(f"{f['filename']}: pobrano {src.stat().st_size} B, oczekiwano {f['size']} B")
                src.replace(zip_path)
                shutil.rmtree(part)
                status = "downloaded"
            else:
                status = "extracted_existing_zip"
            _extract_product(zip_path, product, out_dir)
        mpath = manifest_path_of(zip_path, project_dir)
        digest = None
        if status != "existing" or mpath not in in_manifest:
            if not zip_path.exists():
                raise FileNotFoundError(f"{product}: katalog jest, a zipa {zip_path} i wpisu w manifeście nie ma")
            digest = sha256_file(zip_path)
            update_manifest(Path(manifest_path), {
                "file_path": mpath, "what": f"ASF HyP3 {job.job_type} {product} (job {job.job_id})",
                "source_url": f.get("url", ""), "downloaded_on": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "downloaded_by": downloaded_by, "sha256": digest, "licence": HYP3_LICENCE, "egms_release": "",
                "notes": status})
            in_manifest.add(mpath)
        rows.append({**row, "sha256": digest, "status": status})
    out = pd.DataFrame(rows, columns=DOWNLOAD_COLUMNS)
    print(f"Produkty: {out['status'].value_counts().to_dict()}")
    return out


# ==============================================================================
# V. PRZYCIĘCIE DO WSPÓLNEGO OBSZARU
# ==============================================================================
def clip_to_common_overlap(product_dirs: list, layers: list, out_dir) -> pd.DataFrame:
    """
    Wszystkie warstwy wszystkich produktów przycięte do przecięcia ich zasięgów (rasterio).
    Wymagane: ten sam CRS, ten sam rozmiar piksela, siatki wyrównane (przesunięcia o całe piksele); inaczej
    ValueError. Wynik: <out_dir>/<produkt>/<produkt>_<warstwa>_clip.tif + kopia <produkt>.txt (prep_hyp3 czyta .txt
    z katalogu pliku danych). Katalog w out_dir spoza listy produktów = ValueError (MintPy wczytałby go wzorcem *).
    Plik przycięty o zgodnym zasięgu i rozmiarze jest pomijany ('existing'); niezgodny jest zapisywany od nowa.
    """
    import rasterio
    from rasterio.windows import Window
    from rasterio.windows import transform as window_transform
    if not product_dirs:
        raise ValueError("Pusta lista produktów")
    if not layers:
        raise ValueError("Pusta lista warstw")
    dirs = [Path(p) for p in product_dirs]
    names = [d.name for d in dirs]
    if len(set(names)) != len(names):
        raise ValueError("Zdublowane nazwy produktów")
    for n in names:
        if product_name_and_type(n)[0] != n:
            raise ValueError(f"Katalog {n!r}: nazwa nie jest nazwą produktu HyP3")
    # Ta sama para dat dwa razy (np. dwa udane zlecenia tej samej pary) dałaby w stosie MintPy zdublowany DATE12.
    by_pair = {}
    for n in names:
        by_pair.setdefault(product_dates(n), []).append(n)
    dup = {f"{a.date()}_{b.date()}": v for (a, b), v in by_pair.items() if len(v) > 1}
    if dup:
        raise ValueError(f"Kilka produktów tej samej pary dat (wybierz jeden świadomie): {dup}")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stale = sorted(d.name for d in out_dir.iterdir() if d.is_dir() and d.name not in names)
    if stale:
        raise ValueError(f"{out_dir}: katalogi spoza bieżącej listy produktów {stale}; usuń je świadomie")
    src = {}
    for d in dirs:
        if not (d / f"{d.name}.txt").is_file():
            raise FileNotFoundError(f"{d}: brak {d.name}.txt")
        for layer in layers:
            f = d / f"{d.name}_{layer}.tif"
            if not f.is_file():
                present = sorted(x.name for x in d.iterdir())
                raise ValueError(f"{d.name}: brak warstwy {layer!r}; obecne pliki: {present}")
            src[(d.name, layer)] = f
    meta = {}
    for key, f in src.items():
        with rasterio.open(f) as ds:
            meta[key] = (ds.crs, ds.transform, ds.bounds)
    crs = {str(m[0]) for m in meta.values()}
    if len(crs) != 1:
        raise ValueError(f"Produkty w różnych układach: {sorted(crs)}")
    res = {(m[1].a, m[1].e, m[1].b, m[1].d) for m in meta.values()}
    if len(res) != 1 or next(iter(res))[2:] != (0.0, 0.0):
        raise ValueError(f"Różny rozmiar piksela albo obrót siatki: {sorted(res)}")
    xres, yres = meta[next(iter(meta))][1].a, -meta[next(iter(meta))][1].e
    left = max(m[2].left for m in meta.values())
    bottom = max(m[2].bottom for m in meta.values())
    right = min(m[2].right for m in meta.values())
    top = min(m[2].top for m in meta.values())
    if left >= right or bottom >= top:
        raise ValueError("Produkty nie mają wspólnego obszaru")
    ncols, nrows = (right - left) / xres, (top - bottom) / yres

    def whole(v, what):
        if abs(v - round(v)) > GRID_TOL_PX:
            raise ValueError(f"Siatki pikseli nie są wyrównane ({what} = {v:.6f} piksela)")
        return int(round(v))

    ncols, nrows = whole(ncols, "szerokość"), whole(nrows, "wysokość")
    target = (left, bottom, right, top)
    rows = []
    for (name, layer), f in src.items():
        tr = meta[(name, layer)][1]
        win = Window(whole((left - tr.c) / xres, f"{name}_{layer} kolumna"),
                     whole((tr.f - top) / yres, f"{name}_{layer} wiersz"), ncols, nrows)
        dst = out_dir / name / f"{name}_{layer}_clip.tif"
        status = "written"
        if dst.exists():
            with rasterio.open(dst) as ds:
                same = ((ds.width, ds.height) == (ncols, nrows) and str(ds.crs) == next(iter(crs))
                        and np.allclose(tuple(ds.bounds), target, atol=GRID_TOL_PX * xres))
            status = "existing" if same else "rewritten"
        if status != "existing":
            with rasterio.open(f) as ds:
                data = ds.read(window=win)
                prof = {"driver": "GTiff", "dtype": ds.dtypes[0], "count": ds.count, "width": ncols,
                        "height": nrows, "crs": ds.crs, "transform": window_transform(win, ds.transform),
                        "nodata": ds.nodata}
            dst.parent.mkdir(parents=True, exist_ok=True)
            part = dst.with_name(dst.name + ".part")
            with rasterio.open(part, "w", **prof) as out:
                out.write(data)
            part.replace(dst)
        rows.append({"product": name, "layer": layer, "clip_path": str(dst), "width": ncols, "height": nrows,
                     "left": left, "bottom": bottom, "right": right, "top": top, "status": status})
    for d in dirs:
        txt, dst = d / f"{d.name}.txt", out_dir / d.name / f"{d.name}.txt"
        if not dst.exists() or dst.read_bytes() != txt.read_bytes():
            shutil.copy2(txt, dst)
    out = pd.DataFrame(rows, columns=CLIP_COLUMNS)
    print(f"Przycięcie: {len(dirs)} produktów x {len(layers)} warstw, {ncols} x {nrows} pikseli; "
          f"{out['status'].value_counts().to_dict()}")
    return out


# ==============================================================================
# VI. MintPy: SZABLON, NAZWA SZEREGU KOŃCOWEGO, URUCHOMIENIE
# ==============================================================================
def _yes_no(value, name: str) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    raise ValueError(f"{name} musi być True/False, jest {value!r}")


def _mintpy_options(mcfg: dict) -> dict:
    """mcfg (CHECK_CONFIG['hyp3']['mintpy']) -> klucze szablonu MintPy, które wpływają na wynik i nazwę pliku."""
    need = ["troposphere", "deramp", "solid_earth_tides", "topographic_residual", "min_temp_coh"]
    missing = [k for k in need if k not in mcfg]
    if missing:
        raise KeyError(f"CHECK_CONFIG['hyp3']['mintpy']: brak kluczy {missing} (decyzja autora)")
    for k in need:
        _require(f"hyp3.mintpy.{k}", mcfg[k])
    tropo = str(mcfg["troposphere"]).lower().replace("-", "_")      # jak TimeSeriesAnalysis._read_template
    if tropo not in TROPO_METHODS:
        raise ValueError(f"troposphere {mcfg['troposphere']!r}: obsługiwane {TROPO_METHODS}")
    deramp = str(mcfg["deramp"]).lower()
    if deramp != "no" and deramp not in RAMP_LIST:
        raise ValueError(f"deramp {mcfg['deramp']!r}: dozwolone 'no' albo {RAMP_LIST}")
    tc = float(mcfg["min_temp_coh"])
    if not 0.0 <= tc <= 1.0:
        raise ValueError(f"min_temp_coh {tc} poza [0, 1]")
    opts = {"mintpy.networkInversion.minTempCoh": f"{tc:g}",
            "mintpy.solidEarthTides": _yes_no(mcfg["solid_earth_tides"], "solid_earth_tides"),
            "mintpy.ionosphericDelay.method": "no",     # split_spectrum wymaga warstw jonosfery (brak w HyP3)
            "mintpy.troposphericDelay.method": tropo}
    if tropo == "pyaps":
        opts["mintpy.troposphericDelay.weatherModel"] = _require("hyp3.mintpy.weather_model", mcfg.get("weather_model"))
    opts["mintpy.deramp"] = deramp
    opts["mintpy.topographicResidual"] = _yes_no(mcfg["topographic_residual"], "topographic_residual")
    return opts


def _mintpy_value(v: str):
    """Jak utils1.check_template_auto_value: yes/true -> True, no/false -> False, none -> None (bez rozróżniania wielkości liter)."""
    return {"yes": True, "true": True, "no": False, "false": False, "none": None}.get(str(v).lower(), v)


def _timeseries_name(t: dict) -> str:
    """
    Replika TimeSeriesAnalysis.get_timeseries_filename (MintPy 1.6.4, smallbaselineApp.py) dla Sentinel-1:
    łańcuch timeseries.h5 -> _LOD (tylko Envisat, pomijane) -> _SET -> _ion -> troposfera -> _ramp -> _demErr;
    plik końcowy = ostatni alfabetycznie ze zbioru wejść i wyjść (wejście kroków 'velocity' i 'geocode').
    """
    v = {k: _mintpy_value(t[k]) for k in NAME_KEYS}
    tropo_suffix = {"height_correlation": "_tropHgt", "gacos": "_GACOS", "opera": "_OPERA"}
    fname1, names = "timeseries.h5", []
    for step in ("correct_SET", "correct_ionosphere", "correct_troposphere", "deramp", "correct_topography"):
        fname0, stem = fname1, fname1[:-3]
        if step == "correct_SET" and v["mintpy.solidEarthTides"]:
            fname1 = f"{stem}_SET.h5"
        elif step == "correct_ionosphere" and v["mintpy.ionosphericDelay.method"]:
            if v["mintpy.ionosphericDelay.method"] != "split_spectrum":
                raise ValueError(f"Nieznana metoda jonosfery: {v['mintpy.ionosphericDelay.method']}")
            fname1 = f"{stem}_ion.h5"
        elif step == "correct_troposphere" and v["mintpy.troposphericDelay.method"]:
            m = v["mintpy.troposphericDelay.method"]
            if m == "pyaps":
                fname1 = f"{stem}_{t['mintpy.troposphericDelay.weatherModel']}.h5"
            elif m in tropo_suffix:
                fname1 = f"{stem}{tropo_suffix[m]}.h5"
            else:
                raise ValueError(f"Nieznana metoda troposfery: {m}")
        elif step == "deramp" and v["mintpy.deramp"]:
            if v["mintpy.deramp"] not in RAMP_LIST:
                raise ValueError(f"Nieznany typ rampy: {v['mintpy.deramp']}")
            fname1 = f"{stem}_ramp.h5"
        elif step == "correct_topography" and v["mintpy.topographicResidual"]:
            fname1 = f"{stem}_demErr.h5"
        names += [fname0, fname1]
    return sorted(set(names))[-1]


def expected_timeseries_name(mcfg: dict) -> str:
    """Nazwa końcowego szeregu w katalogu roboczym MintPy dla ustawień mcfg (np. 'timeseries_demErr.h5')."""
    return _timeseries_name(_mintpy_options(mcfg))


def _read_template(path) -> dict:
    """Szablon 'klucz = wartość' (jak readfile.read_template: komentarze '#', '%', '!'; '#' kończy wartość)."""
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        c = [x.strip() for x in line.split("=", 1)]
        if len(c) == 2 and not line.startswith(("%", "#", "!")):
            value = c[1].split("#")[0].strip()
            if value:
                out[c[0]] = value
    return out


def write_mintpy_template(path, clip_dir, reference_lalo, mcfg: dict) -> Path:
    """
    Szablon MintPy dla przyciętych produktów HyP3 (clip_to_common_overlap). Sprawdza: nazwa pliku inna niż
    smallbaselineApp.cfg (MintPy ignoruje taki szablon własny, cli/smallbaselineApp.py); ścieżka clip_dir bez
    'unw_phase' i 'corr' (prep_hyp3 rozpoznaje interferogram po podciągu całej ścieżki) oraz bez '#' i '$'
    (komentarz i zmienne w read_template); pliki każdej warstwy istnieją, warstw interferogramu tyle samo;
    punkt odniesienia (lat, lon) leży w zasięgu przyciętych plików.
    """
    path, clip_dir = Path(path), Path(_require("clip_dir", clip_dir)).resolve()
    if path.name == "smallbaselineApp.cfg":
        raise ValueError("Szablon nie może nazywać się smallbaselineApp.cfg (MintPy go zignoruje)")
    s = clip_dir.as_posix()
    bad = [x for x in ("unw_phase", "corr", "#", "$") if x in s]
    if bad:
        raise ValueError(f"Ścieżka {s} zawiera {bad}: prep_hyp3 / read_template źle ją zinterpretują")
    patterns = {layer: f"{s}/*/*_{layer}_clip.tif" for layer in LAYER_TEMPLATE_KEYS}
    found = {layer: sorted(clip_dir.glob(f"*/*_{layer}_clip.tif")) for layer in LAYER_TEMPLATE_KEYS}
    empty = [layer for layer, f in found.items() if not f]
    if empty:
        raise FileNotFoundError(f"{clip_dir}: brak przyciętych warstw {empty}")
    n_ifg = {layer: len(found[layer]) for layer in IFG_LAYERS}
    if len(set(n_ifg.values())) != 1:
        raise ValueError(f"Różna liczba plików warstw interferogramu: {n_ifg}")
    lat, lon = (float(v) for v in _require("reference_lalo", reference_lalo))
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError(f"reference_lalo ({lat}, {lon}) poza zakresem (lat, lon)")
    import rasterio
    with rasterio.open(found["unw_phase"][0]) as ds:
        epsg, b = ds.crs.to_epsg(), ds.bounds
    if epsg is None:
        raise ValueError(f"{found['unw_phase'][0].name}: układ bez kodu EPSG")
    x, y = transform_xy(lon, lat, 4326, epsg)
    if not (b.left <= x <= b.right and b.bottom <= y <= b.top):
        raise ValueError(f"Punkt odniesienia ({lat}, {lon}) poza zasięgiem przyciętych produktów")
    opts = _mintpy_options(mcfg)
    lines = ["## EGMS Check - KROK 8: szablon MintPy dla produktów ASF HyP3 (step_08_hyp3_mintpy.write_mintpy_template)",
             f"## wygenerowany {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
             "mintpy.load.processor = hyp3"]
    lines += [f"{LAYER_TEMPLATE_KEYS[layer]} = {patterns[layer]}" for layer in LAYER_TEMPLATE_KEYS]
    lines += [f"mintpy.reference.lalo = {lat:.6f},{lon:.6f}"]
    lines += [f"{k} = {v}" for k, v in opts.items()]
    lines += ["mintpy.save.hdfEos5 = no", "mintpy.plot = no"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_mintpy(template, work_dir) -> Path:
    """
    smallbaselineApp.py <szablon> --work-dir <work_dir> (subprocess, check=True). Zwraca ścieżkę szeregu końcowego
    (nazwa z ustawień zapisanych w szablonie); brak pliku szeregu, geometrii (inputs/geometryGeo.h5) lub maski
    maskTempCoh.h5 po przebiegu = FileNotFoundError. MintPy sam pomija kroki aktualne (updateMode).
    """
    template, work_dir = Path(template).resolve(), Path(_require("work_dir", work_dir)).resolve()
    if not template.is_file():
        raise FileNotFoundError(template)
    tpl = _read_template(template)
    missing = [k for k in NAME_KEYS if k not in tpl]
    if missing:
        raise KeyError(f"{template.name}: brak kluczy {missing} - szablon nie z write_mintpy_template")
    name = _timeseries_name(tpl)
    exe = shutil.which("smallbaselineApp.py")
    if exe is None:
        raise FileNotFoundError("smallbaselineApp.py nie ma na PATH: zainstaluj MintPy (pip install mintpy).")
    work_dir.mkdir(parents=True, exist_ok=True)
    cmd = [exe, str(template), "--work-dir", str(work_dir)]
    print("Uruchamiam:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    for f in (work_dir / name, work_dir / MINTPY_GEOMETRY, work_dir / MINTPY_MASK):
        if not f.is_file():
            raise FileNotFoundError(f"Po przebiegu MintPy brak {f}; szeregi w katalogu: "
                                    f"{sorted(p.name for p in work_dir.glob('timeseries*.h5'))}")
    return work_dir / name


def reference_lalo_from_rule(sites: pd.DataFrame, rule: str) -> dict:
    """
    Punkt odniesienia MintPy z reguły (CHECK_CONFIG hyp3.mintpy.reference_rule):
    'stable_gnss_min_abs_vu' = stacja GNSS z grupy 'stabilna' o najmniejszym |vu| (remis: kod stacji alfabetycznie).
    """
    if _require("hyp3.mintpy.reference_rule", rule) not in REFERENCE_RULES:
        raise ValueError(f"Nieznana reguła odniesienia {rule!r}; dozwolone {REFERENCE_RULES}")
    _require_columns(sites, ["site", "site_type", "group", "lat_deg", "lon_deg", "vu_mm_yr"], "sites")
    st = sites[(sites["site_type"] == "gnss") & (sites["group"] == "stabilna") & sites["vu_mm_yr"].notna()]
    if st.empty:
        raise RuntimeError("Brak stabilnej stacji GNSS do punktu odniesienia MintPy")
    best = st.assign(abs_vu=st["vu_mm_yr"].abs()).sort_values(["abs_vu", "site"]).iloc[0]
    return {"site": best["site"], "lat_deg": float(best["lat_deg"]), "lon_deg": float(best["lon_deg"]),
            "vu_mm_yr": float(best["vu_mm_yr"])}


# ==============================================================================
# VII. GEOMETRIA LOS
# ==============================================================================
def los_unit_vector(inc_deg, az_deg) -> tuple:
    """
    Wektor jednostkowy (E, N, U) od ziemi do satelity - dokładnie MintPy utils0.get_unit_vector4component_of_interest
    (comp='enu2los'); inc od pionu, az od północy przeciwnie do wskazówek zegara, w stopniach (geometryGeo.h5).
    d_LOS = E*e + N*n + U*u, dodatnie = ruch do satelity (jak EGMS). Działa dla liczb i tablic.
    """
    inc, az = np.deg2rad(inc_deg), np.deg2rad(az_deg)
    return (np.sin(inc) * np.sin(az) * -1, np.sin(inc) * np.cos(az), np.cos(inc))


def check_los_vs_egms(vec_own, vec_egms, tol: float) -> dict:
    """
    Kontrola konwencji przed porównaniem (ta sama ścieżka): |los_up_own - los_up_EGMS| <= tol i ten sam niezerowy
    znak los_east. Zwraca wartości i 'pass'; wywołujący zatrzymuje obliczenia, gdy pass = False.
    """
    tol = float(_require("tol", tol))
    e0, n0, u0 = (float(v) for v in vec_own)
    e1, n1, u1 = (float(v) for v in vec_egms)
    if not np.isfinite([e0, n0, u0, e1, n1, u1]).all():
        raise ValueError(f"Wektor LOS z NaN: własny {vec_own}, EGMS {vec_egms}")
    d_up = abs(u0 - u1)
    cosang = (e0 * e1 + n0 * n1 + u0 * u1) / (np.hypot(np.hypot(e0, n0), u0) * np.hypot(np.hypot(e1, n1), u1))
    sign_ok = np.sign(e0) == np.sign(e1) != 0
    return {"d_los_up": d_up, "sign_east_own": float(np.sign(e0)), "sign_east_egms": float(np.sign(e1)),
            "angle_deg": float(np.rad2deg(np.arccos(np.clip(cosang, -1.0, 1.0)))), "threshold": tol,
            "pass": bool(d_up <= tol and sign_ok)}


# ==============================================================================
# VIII. SZEREGI W PUNKTACH I DOWIĄZANIE DO EGMS
# ==============================================================================
def _h5_attrs(f) -> dict:
    return {k: (v.decode() if isinstance(v, bytes) else str(v)) for k, v in f.attrs.items()}


def _file_epsg(atr: dict) -> int:
    """EPSG pliku MintPy: atrybut EPSG (readfile.read_gdal_vrt), inaczej UTM_ZONE (jak utils0.utm_zone2epsg_code)."""
    if atr.get("EPSG") not in (None, "", "None"):
        return int(atr["EPSG"])
    if atr.get("UTM_ZONE"):
        from pyproj import CRS
        z = atr["UTM_ZONE"]
        return int(CRS.from_dict({"proj": "utm", "zone": int(z[:-1]), "south": z[-1].upper() == "S"}).to_authority()[1])
    if atr.get("X_UNIT", "").startswith("deg"):
        return 4326
    raise ValueError(f"Plik MintPy bez EPSG, UTM_ZONE i współrzędnych w stopniach: {sorted(atr)}")


def _grid(atr: dict, what: str) -> tuple:
    need = ["X_FIRST", "Y_FIRST", "X_STEP", "Y_STEP", "WIDTH", "LENGTH"]
    missing = [k for k in need if k not in atr]
    if missing:
        raise KeyError(f"{what}: brak atrybutów {missing} (plik nie jest geokodowany?)")
    return tuple(float(atr[k]) for k in need)


def mintpy_series_at_points(ts_h5, geom_h5, mask_h5, points: pd.DataFrame, window_px: int, region: str,
                            track) -> pd.DataFrame:
    """
    Szereg MintPy w punktach (site, lon_deg, lat_deg): piksel jak coord.lalo2yx (floor((y - Y_FIRST)/Y_STEP + 0.01)),
    mediana pikseli okna window_px x window_px (nieparzyste; okno przycięte do rastra) spośród pikseli maski
    maskTempCoh.h5 i skończonych we wszystkich datach; metry -> mm. los_* z mediany incidenceAngle/azimuthAngle
    tych pikseli (los_unit_vector). Punkt poza rastrem albo bez ważnych pikseli = wiersze z disp_mm i los_* NaN
    i powodem w status. ref_date = REF_DATE (szereg MintPy jest tam zerem - sprawdzane), reference = punkt
    odniesienia MintPy; track jako tekst (_track_label). Przed zapisem formatu długiego (step_07.validate_long wymaga
    los_*) wiersze bez szeregu oddziela split_long_status.
    """
    import h5py
    w = int(_require("hyp3.mintpy.window_px", window_px))
    if w < 1 or w % 2 == 0:
        raise ValueError(f"window_px = {window_px}: oczekiwano nieparzystej liczby >= 1")
    _require("region", region)
    track = _track_label(_require("track", track))          # tekst, jak w formacie długim step_07
    _require_columns(points, ["site", "lon_deg", "lat_deg"], "points")
    if points["site"].duplicated().any():
        raise ValueError(f"Zdublowane punkty: {sorted(points.loc[points['site'].duplicated(), 'site'])}")
    with h5py.File(ts_h5, "r") as f:
        atr = _h5_attrs(f)
        for k in ("timeseries", "date"):
            if k not in f:
                raise KeyError(f"{ts_h5}: brak zbioru {k!r}; są {list(f.keys())}")
        dates = pd.to_datetime([d.decode() if isinstance(d, bytes) else str(d) for d in f["date"][:]], format="%Y%m%d")
    if atr.get("FILE_TYPE") != "timeseries" or atr.get("UNIT") != "m":
        raise ValueError(f"{ts_h5}: FILE_TYPE={atr.get('FILE_TYPE')}, UNIT={atr.get('UNIT')}; oczekiwano timeseries, m")
    grid = _grid(atr, str(ts_h5))
    for other in (geom_h5, mask_h5):
        with h5py.File(other, "r") as f:
            if not np.allclose(_grid(_h5_attrs(f), str(other)), grid, rtol=0, atol=1e-6):
                raise ValueError(f"{other}: siatka inna niż w {ts_h5}")
    x0, y0, dx, dy, width, length = grid
    width, length = int(width), int(length)
    epsg = _file_epsg(atr)
    ref_date = pd.Timestamp(atr["REF_DATE"])
    if ref_date not in dates:
        raise ValueError(f"REF_DATE {ref_date.date()} nie jest datą szeregu")
    reference = f"MintPy REF_Y/X {atr['REF_Y']},{atr['REF_X']}" + (
        f"; REF_LAT/LON {atr['REF_LAT']},{atr['REF_LON']}" if "REF_LAT" in atr else "")
    direction = atr["ORBIT_DIRECTION"].lower()
    if direction not in ("ascending", "descending"):
        raise ValueError(f"ORBIT_DIRECTION {atr['ORBIT_DIRECTION']!r}")
    xs, ys = transform_xy(points["lon_deg"].to_numpy(float), points["lat_deg"].to_numpy(float), 4326, epsg)
    h = w // 2
    base = {"region": region, "source": SOURCE, "track": track, "direction": direction, "component": "LOS",
            "ref_date": ref_date, "reference": reference}
    parts = []
    with h5py.File(ts_h5, "r") as fts, h5py.File(geom_h5, "r") as fg, h5py.File(mask_h5, "r") as fm:
        for k, ds in ((("incidenceAngle", "azimuthAngle"), fg), (("mask",), fm)):
            miss = [x for x in k if x not in ds]
            if miss:
                raise KeyError(f"{ds.filename}: brak zbiorów {miss}; są {list(ds.keys())}")
        for site, x, y in zip(points["site"], np.atleast_1d(xs), np.atleast_1d(ys)):
            row = int(np.floor((y - y0) / dy + 0.01))
            col = int(np.floor((x - x0) / dx + 0.01))
            nan = pd.DataFrame({**base, "site": site, "los_east": np.nan, "los_north": np.nan, "los_up": np.nan,
                                "date": dates, "disp_mm": np.nan, "n_points": 0}, index=range(len(dates)))
            if not (0 <= row < length and 0 <= col < width):
                parts.append(nan.assign(status="NaN: punkt poza zasięgiem pliku MintPy"))
                continue
            r0, r1, c0, c1 = max(row - h, 0), min(row + h + 1, length), max(col - h, 0), min(col + h + 1, width)
            block = fts["timeseries"][:, r0:r1, c0:c1].astype(float)
            valid = fm["mask"][r0:r1, c0:c1].astype(bool) & np.all(np.isfinite(block), axis=0)
            if not valid.any():
                parts.append(nan.assign(status=f"NaN: brak ważnych pikseli ({MINTPY_MASK}) w oknie {w}x{w}"))
                continue
            inc = float(np.median(fg["incidenceAngle"][r0:r1, c0:c1][valid]))
            az = float(np.median(fg["azimuthAngle"][r0:r1, c0:c1][valid]))
            if not (np.isfinite(inc) and np.isfinite(az)):
                parts.append(nan.assign(status=f"NaN: brak kąta padania/azymutu ({MINTPY_GEOMETRY}) w pikselach okna"))
                continue
            le, ln, lu = los_unit_vector(inc, az)
            disp = np.median(block[:, valid], axis=1) * MM_PER_M
            parts.append(pd.DataFrame({**base, "site": site, "los_east": le, "los_north": ln, "los_up": lu,
                                       "date": dates, "disp_mm": disp, "n_points": int(valid.sum()),
                                       "status": "ok"}))
    out = pd.concat(parts, ignore_index=True)[LONG_COLUMNS]
    at_ref = out[(out["date"] == ref_date) & (out["status"] == "ok")]["disp_mm"]
    if (at_ref.abs() > 1e-3).any():
        raise ValueError(f"Szereg MintPy nie jest zerem w REF_DATE {ref_date.date()} (max {at_ref.abs().max():.4f} mm)")
    return out


def align_to_reference(own_long: pd.DataFrame, egms_long: pd.DataFrame, overlap_start, overlap_end,
                       half_window_days: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Dowiązanie własnego szeregu do EGMS dla każdej pary (site, track): w zakładce [overlap_start, overlap_end]
    EGMS w datach własnych = mediana wartości EGMS w oknie +-half_window_days (step_03.gnss_at_dates);
    offset = mediana(własny - EGMS); szereg przesunięty = własny - offset, w odniesieniu EGMS (ref_date, reference).
    Mniej niż MIN_ALIGN_MATCHES dopasowań, brak szeregu EGMS albo brak wartości własnych = offset NaN z powodem,
    a szereg przesunięty ma disp_mm NaN. Tabela: ALIGN_COLUMNS (corr - korelacja w zakładce, informacyjnie:
    ujemna wskazywałaby odwrócony znak).
    """
    _require_columns(own_long, LONG_COLUMNS, "own_long")
    _require_columns(egms_long, EGMS_ALIGN_NEED, "egms_long")
    t0, t1 = pd.Timestamp(_require("overlap_start", overlap_start)), pd.Timestamp(_require("hyp3.overlap_end", overlap_end))
    hw = float(_require("half_window_days", half_window_days))
    for what, df in (("egms_long", egms_long), ("own_long", own_long)):
        if df["source"].nunique() != 1:
            raise ValueError(f"{what} z kilku źródeł albo pusty: {sorted(df['source'].unique())}")
    # Klucz ścieżki przez _track_label: 88, 88.0 (CSV z pustymi polami) i "88" to ta sama ścieżka; samo astype(str)
    # dałoby "88.0" != "88" i po cichu status "brak szeregu EGMS" dla wszystkich punktów.
    egms = egms_long.assign(track=egms_long["track"].map(_track_label), date=pd.to_datetime(egms_long["date"]))
    own = own_long.assign(track=own_long["track"].map(_track_label), date=pd.to_datetime(own_long["date"]))
    for what, df in (("egms_long", egms), ("own_long", own)):
        if df.duplicated(["site", "track", "date"]).any():
            raise ValueError(f"{what}: zdublowane (site, track, date)")
    rows, shifted = [], []
    for (site, tk), g in own.groupby(["site", "track"], sort=True):
        g = g.sort_values("date")
        e = egms[(egms["site"] == site) & (egms["track"] == tk)].sort_values("date")
        row = {"site": site, "track": tk, "n_matched": 0, "offset_mm": np.nan, "std_diff_mm": np.nan, "corr": np.nan}
        win = g[(g["date"] >= t0) & (g["date"] <= t1) & g["disp_mm"].notna()]
        if e.empty:
            status = "NaN: brak szeregu EGMS dla (site, track)"
        elif win.empty:
            status = "NaN: brak wartości własnych w zakładce"
        else:
            if e["reference"].nunique() != 1 or e["ref_date"].nunique() != 1:
                raise ValueError(f"{site}/{tk}: EGMS z kilkoma odniesieniami")
            # Mediana tylko z dat EGMS z wartością: NaN w oknie (np. daty przed ref_date, step_07) dałby NaN mediany
            # i zgubił dopasowanie mimo innych wartości w oknie; liczba dopasowań trafia do n_matched.
            e_at = gnss_at_dates(e[e["disp_mm"].notna()].set_index("date")["disp_mm"], pd.DatetimeIndex(win["date"]), hw)
            d = win["disp_mm"].to_numpy() - e_at.to_numpy()
            m = np.isfinite(d)
            row["n_matched"] = int(m.sum())
            if m.sum() < MIN_ALIGN_MATCHES:
                status = f"NaN: za mało dopasowanych dat ({int(m.sum())} < {MIN_ALIGN_MATCHES})"
            else:
                off = float(np.median(d[m]))
                row.update(offset_mm=off, std_diff_mm=float(np.std(d[m] - off, ddof=1)),
                           corr=float(np.corrcoef(win["disp_mm"].to_numpy()[m], e_at.to_numpy()[m])[0, 1]))
                status = "ok"
        rows.append({**row, "status": status})
        s = g.copy()
        s["disp_mm"] = s["disp_mm"] - row["offset_mm"]          # NaN, gdy dowiązanie się nie udało
        if status == "ok":
            s["reference"], s["ref_date"] = e["reference"].iat[0], pd.Timestamp(e["ref_date"].iat[0])
        s["status"] = np.where(s["status"] == "ok", status, s["status"])   # wiersz z własnym powodem NaN go zachowuje
        shifted.append(s)
    table = pd.DataFrame(rows, columns=ALIGN_COLUMNS)
    print(f"Dowiązanie do EGMS ({egms_long['source'].iat[0]}): {table['status'].value_counts().to_dict()}")
    return pd.concat(shifted, ignore_index=True)[LONG_COLUMNS], table


def split_long_status(long_with_status: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Wynik mintpy_series_at_points / align_to_reference -> (szeregi, statusy), jak step_07.egms_points_to_long:
    szeregi = wiersze serii ze statusem 'ok', bez kolumny status (format długi sekcji 2.2; step_07.validate_long
    wymaga los_* i odrzuca puste); statusy = wiersz na KAŻDY szereg (SERIES_STATUS_COLUMNS), także bez wartości,
    z powodem NaN. Status niejednolity w obrębie szeregu = ValueError (oba źródła nadają go całemu szeregowi).
    """
    _require_columns(long_with_status, LONG_COLUMNS, "long_with_status")
    df = long_with_status.assign(track=long_with_status["track"].map(_track_label))
    per = df.groupby(SERIES_KEY)["status"].nunique()
    if (per > 1).any():
        raise ValueError(f"Szeregi z kilkoma statusami: {per[per > 1].index.tolist()[:5]}")
    status = (df.groupby(SERIES_KEY, sort=True)
              .agg(direction=("direction", "first"), n_points=("n_points", "first"), ref_date=("ref_date", "first"),
                   reference=("reference", "first"), status=("status", "first")).reset_index()[SERIES_STATUS_COLUMNS])
    series = df[df["status"] == "ok"].drop(columns="status").reset_index(drop=True)
    if series[["los_east", "los_north", "los_up"]].isna().any().any():
        raise ValueError("Szereg ze statusem 'ok' bez wektora LOS")
    return series, status


# ==============================================================================
# IX. TEST OFFLINE (dane syntetyczne o znanej odpowiedzi; wartości testowe nie są wynikiem) I OPIS PRODUKTU
# ==============================================================================
_T_TRACK = 88                          # numer ścieżki testowej (dowolny)
_T_EPSG = 32631                        # układ syntetycznych GeoTIFF (dowolna strefa UTM)
_T_X0, _T_Y0, _T_PX = 600000.0, 5800000.0, 80.0
_T_LAYERS = list(LAYER_TEMPLATE_KEYS)


def _expect_raises(exc, fn, *args, match: str = ""):
    try:
        fn(*args)
    except exc as e:
        assert match in str(e), f"komunikat bez '{match}': {e}"
        return e
    raise AssertionError(f"Oczekiwano {exc.__name__} z {getattr(fn, '__name__', fn)}")


class _FakeProduct:
    def __init__(self, properties, geometry):
        self.properties, self.geometry = properties, geometry


class _FakeAsf:
    """Atrapa modułu asf_search: search() zwraca ustalone produkty i zapisuje argumenty wywołania."""

    class DATASET:
        SLC_BURST = "SLC-BURST"

    def __init__(self, products):
        self.products, self.calls = products, []

    def search(self, **kw):
        self.calls.append(kw)
        return list(self.products)


def _synthetic_bursts(dates, burst_nums, drop: set) -> list:
    """
    Bursty IW1 ścieżki testowej; obrys burstu k: lon 5-6, lat 52.0 + 0.2 (k - k0) .. + 0.25 (zakładki 0.05).
    startTime na przemian bez i z częścią ułamkową sekundy (oba warianty ISO 8601 występują w CMR).
    """
    out = []
    for n_d, d in enumerate(dates):
        for i, b in enumerate(burst_nums):
            if (d, b) in drop:
                continue
            la = 52.0 + 0.2 * i
            ring = [[5.0, la], [6.0, la], [6.0, la + 0.25], [5.0, la + 0.25], [5.0, la]]
            out.append(_FakeProduct(
                {"sceneName": f"S1_{b:06d}_IW1_{d:%Y%m%d}T054312_VV_{b % 65536:04X}-BURST",
                 "startTime": f"{d:%Y-%m-%d}T05:43:12{'.654321' if n_d % 2 else ''}Z", "platform": "Sentinel-1A",
                 "flightDirection": "ASCENDING",
                 "pathNumber": _T_TRACK, "polarization": "VV", "burst": {"fullBurstID": f"{_T_TRACK:03d}_{b:06d}_IW1"}},
                {"type": "Polygon", "coordinates": [ring]}))
    return out


def _product_txt() -> str:
    """Metadane w formacie pliku .txt HyP3 (klucze czytane przez prep_hyp3.add_hyp3_metadata); wartości testowe."""
    return ("Reference Granule: TEST\nSecondary Granule: TEST\nBaseline: 50.0\nUTC time: 20000.0\nHeading: -12.0\n"
            "Spacecraft height: 693000.0\nEarth radius at nadir: 6370000.0\nSlant range near: 800000.0\n"
            "Range looks: 20\nAzimuth looks: 4\nUnwrapping type: snaphu_mcf\n")


def _tif_bytes(dx_px: int, dy_px: int, layer_index: int, epsg: int, x_shift_m: float) -> bytes:
    """GeoTIFF 30 x 40 w siatce testowej przesunięty o (dx, dy) pikseli; wartość = kol. + 1000 wiersz globalny + 1e5 warstwa."""
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.transform import from_origin
    r, c = np.mgrid[0:30, 0:40]
    data = ((c + dx_px) + 1000.0 * (r + dy_px) + 1e5 * layer_index).astype("float32")[None]
    tr = from_origin(_T_X0 + dx_px * _T_PX + x_shift_m, _T_Y0 - dy_px * _T_PX, _T_PX, _T_PX)
    with MemoryFile() as mem:
        with mem.open(driver="GTiff", width=40, height=30, count=1, dtype="float32",
                      crs=rasterio.crs.CRS.from_epsg(epsg), transform=tr, nodata=0.0) as ds:
            ds.write(data)
        return mem.read()


def _write_product(where: Path, product: str, k: int, epsg: int, x_shift_m: float, layers: list) -> None:
    """Rozpakowany produkt testowy (katalog) - do kontroli błędów przycięcia."""
    d = where / product
    d.mkdir(parents=True)
    (d / f"{product}.txt").write_text(_product_txt())
    for i, layer in enumerate(layers):
        (d / f"{product}_{layer}.tif").write_bytes(_tif_bytes(k % 3, k % 2, i, epsg, x_shift_m))


def _fake_hyp3_classes(real):
    """Atrapy HyP3 i Job jako podklasy prawdziwych z hyp3_sdk: metody prepare_* i Batch są prawdziwe, sieci nie ma."""

    class FakeJob(real.Job):
        downloads = 0

        def download_files(self, location, create):
            location = Path(location)
            location.mkdir(parents=True, exist_ok=create)
            out = []
            for f in self.files:
                product = f["filename"][:-4]
                with zipfile.ZipFile(location / f["filename"], "w") as zf:
                    zf.writestr(f"{product}/{product}.txt", _product_txt())
                    for i, layer in enumerate(_T_LAYERS):
                        zf.writestr(f"{product}/{product}_{layer}.tif", _tif_bytes(self.k % 3, self.k % 2, i, _T_EPSG, 0.0))
                out.append(location / f["filename"])
            FakeJob.downloads += 1
            return out

    class FakeHyP3(real.HyP3):
        def __init__(self, credits):              # bez super().__init__: brak logowania i sieci
            self.jobs, self.n_submit_calls, self.credits = [], 0, credits

        def find_jobs(self, name=None, **kw):
            return real.Batch([j for j in self.jobs if j.name == name])

        def check_credits(self):
            return self.credits

        def submit_prepared_jobs(self, prepared_jobs):
            self.n_submit_calls += 1
            new = []
            for p in prepared_jobs:
                k = len(self.jobs)
                par = p["job_parameters"]
                if p["job_type"] == "INSAR_ISCE_MULTI_BURST":
                    nums = sorted(int(s.split("_")[1]) for s in par["reference"])
                    d1, d2 = par["reference"][0].split("_")[3][:8], par["secondary"][0].split("_")[3][:8]
                    product = (f"S1_{_T_TRACK:03d}_{nums[0]:06d}s1n{len(nums):02d}-000000s2n00-000000s3n00_IW_"
                               f"{d1}_{d2}_VV_INT80_{k:04X}")
                else:
                    g1, g2 = par["granules"]
                    product = f"S1_{g1.split('_')[1]}_IW1_{g1.split('_')[3][:8]}_{g2.split('_')[3][:8]}_VV_INT80_{k:04X}"
                job = FakeJob(job_type=p["job_type"], job_id=f"job-{k:03d}", request_time=datetime.now(timezone.utc),
                              status_code="SUCCEEDED", user_id="selftest", name=p.get("name"),
                              job_parameters=dict(par), files=[{"filename": f"{product}.zip",
                                                                "url": f"https://hyp3.invalid/{product}.zip"}])
                job.k = k
                self.jobs.append(job)
                new.append(job)
            return real.Batch(new)

    return FakeHyP3, FakeJob


class _RecordingHyP3:
    """Atrapa konstruktora HyP3 do testu hyp3_client: zapisuje argumenty (bez sieci)."""
    PROD_API = "https://hyp3.invalid"

    def __init__(self, **kw):
        self.kw = kw


def _write_synthetic_mintpy(tmp: Path, dates: pd.DatetimeIndex, rng) -> dict:
    """
    Pliki jak z MintPy (układ HDF5 z objects/stack.py, atrybuty z readfile.read_gdal_vrt): 60 x 50 pikseli UTM,
    prędkość LOS v(r, c) = -6 + 0.5 (c - 20) + 0.25 (r - 30) mm/rok, REF_DATE = pierwsza data (zero), szum 0,3 mm;
    incidenceAngle 40, azimuthAngle 102 (MintPy: typowe Sentinel-1 wstępująca). Maska: dwa piksele przy (30, 20)
    wyłączone i wypełnione śmieciem +1000 mm; całe okno przy (10, 40) wyłączone.
    """
    import h5py
    L, W = 60, 50
    t = years_since(dates, dates[0])
    r, c = np.mgrid[0:L, 0:W]
    v = -6.0 + 0.5 * (c - 20) + 0.25 * (r - 30)
    ts = (v[None] * t[:, None, None] + rng.normal(0.0, 0.3, (len(dates), L, W))) / MM_PER_M
    ts[0] = 0.0
    mask = np.ones((L, W), bool)
    for rr, cc in ((29, 19), (31, 21)):
        mask[rr, cc] = False
        ts[1:, rr, cc] = 1.0
    mask[9:12, 39:42] = False
    atr = {"FILE_TYPE": "timeseries", "UNIT": "m", "X_FIRST": _T_X0, "Y_FIRST": _T_Y0, "X_STEP": _T_PX,
           "Y_STEP": -_T_PX, "WIDTH": W, "LENGTH": L, "EPSG": _T_EPSG, "UTM_ZONE": "31N", "X_UNIT": "meters",
           "REF_DATE": dates[0].strftime("%Y%m%d"), "REF_Y": 0, "REF_X": 0, "ORBIT_DIRECTION": "ASCENDING"}
    paths = {"ts": tmp / "timeseries_demErr.h5", "geom": tmp / "geometryGeo.h5", "mask": tmp / "maskTempCoh.h5"}
    with h5py.File(paths["ts"], "w") as f:
        f.create_dataset("timeseries", data=ts.astype("float32"))
        f.create_dataset("date", data=np.array([d.strftime("%Y%m%d") for d in dates], dtype=np.bytes_))
        f.create_dataset("bperp", data=np.zeros(len(dates), "float32"))
        f.attrs.update({k: str(x) for k, x in atr.items()})
    with h5py.File(paths["geom"], "w") as f:
        f.create_dataset("incidenceAngle", data=np.full((L, W), 40.0, "float32"))
        f.create_dataset("azimuthAngle", data=np.full((L, W), 102.0, "float32"))
        f.attrs.update({k: str(x) for k, x in {**atr, "FILE_TYPE": "geometry"}.items()})
    with h5py.File(paths["mask"], "w") as f:
        f.create_dataset("mask", data=mask)
        f.attrs.update({k: str(x) for k, x in {**atr, "FILE_TYPE": "mask"}.items()})
    return paths


def _pixel_lonlat(row: int, col: int) -> tuple:
    return transform_xy(_T_X0 + (col + 0.5) * _T_PX, _T_Y0 - (row + 0.5) * _T_PX, _T_EPSG, 4326)


def _selftest() -> None:
    import contextlib
    import io
    import rasterio
    real = importlib.import_module("hyp3_sdk")
    rng = np.random.default_rng(20261011)
    saved = {k: globals()[k] for k in ("asf_search", "hyp3_sdk")}
    old_path = os.environ.get("PATH", "")
    try:
        with tempfile.TemporaryDirectory(prefix="egmscheck_hyp3_") as tmpd:
            tmp = Path(tmpd)

            # 1. Dane logowania: dwie poprawne postacie, błędy, żadna wartość nie trafia na ekran.
            secret = "S3CRET-TOKEN-value"
            (tmp / "tok.json").write_text(json.dumps({"token": secret}))
            (tmp / "up.json").write_text(json.dumps({"username": "u", "password": secret}))
            (tmp / "both.json").write_text(json.dumps({"token": secret, "username": "u", "password": "p"}))
            (tmp / "bad.json").write_text(json.dumps({"user": "u", "pass": secret}))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                c_tok = load_earthdata_credentials(tmp / "tok.json")
                c_up = load_earthdata_credentials(tmp / "up.json")
                e1 = _expect_raises(ValueError, load_earthdata_credentials, tmp / "both.json")
                e2 = _expect_raises(KeyError, load_earthdata_credentials, tmp / "bad.json", match="brak kluczy")
                _expect_raises(FileNotFoundError, load_earthdata_credentials, tmp / "nie_ma.json")
            assert c_tok == {"token": secret} and c_up == {"username": "u", "password": secret}
            assert secret not in buf.getvalue() + str(e1) + str(e2), "sekret w komunikacie"
            globals()["hyp3_sdk"] = type("M", (), {"HyP3": _RecordingHyP3, "PROD_API": _RecordingHyP3.PROD_API})
            assert hyp3_client(c_tok).kw == {"api_url": "https://hyp3.invalid", "token": secret}
            assert hyp3_client(c_up).kw == {"api_url": "https://hyp3.invalid", "username": "u", "password": secret}

            # 2. Bursty, pokrycie punktów, ciągłość, stos dat (data nr 5 bez burstu 100002 -> usunięta).
            dates = pd.date_range("2024-01-05", periods=30, freq="12D")
            nums = [100001, 100002, 100003]
            fake_asf = _FakeAsf(_synthetic_bursts(dates, nums, drop={(dates[5], 100002)}))
            globals()["asf_search"] = fake_asf
            aoi = "POLYGON((5 52, 6 52, 6 53, 5 53, 5 52))"
            b = search_bursts(aoi, _T_TRACK, "2024-01-01", "2024-12-31", "VV")
            kw = fake_asf.calls[-1]
            assert kw["dataset"] == "SLC-BURST" and kw["relativeOrbit"] == _T_TRACK and kw["polarization"] == "VV"
            assert list(b.columns) == BURST_COLUMNS and len(b) == 89 and (b["flight_direction"] == "ascending").all()
            assert b["start_time"].dt.tz is None and set(b["start_time"].dt.strftime("%H:%M:%S")) == {"05:43:12"}
            assert (b["date"] == b["start_time"].dt.normalize()).all() and set(b["date"]) == set(dates)
            _expect_raises(ValueError, search_bursts, aoi, 15, "2024-01-01", "2024-12-31", "VV", match="inne ścieżki")
            _expect_raises(ValueError, search_bursts, aoi, _T_TRACK, "2024-01-01", None, "VV", match="None")
            pts = pd.DataFrame({"site": ["P1", "P2", "FAR"], "lon_deg": [5.5, 5.5, 8.0], "lat_deg": [52.30, 52.50, 50.0]})
            cov = bursts_covering_points(b, pts)
            assert cov == ["088_100002_IW1", "088_100003_IW1"], cov
            _expect_raises(ValueError, check_burst_contiguity, ["088_100001_IW1", "088_100003_IW1"], match="nieciągłe")
            assert fill_burst_gaps(["088_100001_IW1", "088_100003_IW1"]) == [f"088_{n}_IW1" for n in nums]
            # Reguły grupy asf_search/burst2safe: podpasy zachodzą (+-1) - tak; przesunięte o 2 - nie; > 15 - nie.
            check_burst_contiguity(["088_100001_IW1", "088_100002_IW1", "088_100002_IW2", "088_100003_IW2"])
            _expect_raises(ValueError, check_burst_contiguity, ["088_100001_IW1", "088_100003_IW2"], match="nie zachodzą")
            _expect_raises(ValueError, check_burst_contiguity, [f"088_{100001 + i}_IW1" for i in range(16)],
                           match=f"> {MAX_MULTI_BURST}")
            stack = acquisition_stack(b, cov)
            assert len(stack) == 29 and dates[5] not in set(stack["date"])
            assert stack["scene_names"].iat[0] == [f"S1_{n:06d}_IW1_20240105T054312_VV_{n % 65536:04X}-BURST"
                                                    for n in (100002, 100003)]

            # 3. Sieć SBAS: znany wynik na małym przykładzie; przerwa -> wyjątek; spójność stosu.
            d0 = pd.Timestamp("2024-01-01")
            small = [d0 + pd.Timedelta(days=x) for x in (0, 12, 24, 36, 60)]
            got = [((a - d0).days, (c - d0).days) for a, c in sbas_pairs(small, 2, 30)]
            assert got == [(0, 12), (0, 24), (12, 24), (12, 36), (24, 36), (36, 60)], got
            _expect_raises(ValueError, sbas_pairs, [small[0], small[1], small[4]], 2, 30, match="niespójna")
            pairs = sbas_pairs(stack["date"], 3, 48)
            sd = list(stack["date"])
            assert all((sd[i], sd[i + 1]) in pairs for i in range(len(sd) - 1))
            assert all((c - a).days <= 48 for a, c in pairs) and len(pairs) == 3 * len(sd) - 6

            # 4. Zlecenia: payload hyp3_sdk, brak duplikatów przy ponownym wysłaniu, ochrona kredytów.
            FakeHyP3, FakeJob = _fake_hyp3_classes(real)
            globals()["hyp3_sdk"] = type("M", (), {"HyP3": FakeHyP3, "PROD_API": real.PROD_API})
            name = "egmscheck_selftest"
            jobs = prepare_jobs(stack, pairs[:6], "INSAR_ISCE_MULTI_BURST", "20x4", True, name)
            j0 = jobs[0]
            assert j0["job_type"] == "INSAR_ISCE_MULTI_BURST" and j0["name"] == name
            assert j0["job_parameters"] == {"reference": stack["scene_names"].iat[0], "secondary": stack["scene_names"].iat[1],
                                            "apply_water_mask": True, "looks": "20x4"}, j0
            _expect_raises(ValueError, prepare_jobs, stack, pairs[:2], "INSAR_ISCE_BURST", "20x4", True, name)
            _expect_raises(ValueError, prepare_jobs, stack, pairs[:2], "INSAR_ISCE_MULTI_BURST", "20x5", True, name,
                           match="looks")
            one = prepare_jobs(acquisition_stack(b, ["088_100002_IW1"]), pairs[:1], "INSAR_ISCE_BURST", "20x4", False, name)
            assert one[0]["job_parameters"]["granules"][0].startswith("S1_100002_IW1_20240105")
            hy = FakeHyP3(credits=5)
            _expect_raises(RuntimeError, submit_missing, hy, jobs, name, None, 1.0, match="max_credits")
            _expect_raises(RuntimeError, submit_missing, hy, jobs, name, 100, 1.0, match="pozostałe")
            _expect_raises(RuntimeError, submit_missing, hy, jobs, name, 3, 1.0, match="max_credits")
            assert hy.n_submit_calls == 0, "ochrona kredytów musi działać przed wysłaniem"
            hy.credits = 100
            r1 = submit_missing(hy, jobs[:4], name, 100, 1.0)
            r2 = submit_missing(hy, jobs, name, 100, 1.0)
            assert (r1["status"] == "submitted").all() and list(r2["status"]) == ["existing"] * 4 + ["submitted"] * 2
            r3 = submit_missing(hy, jobs, name, 100, 1.0)
            assert (r3["status"] == "existing").all() and hy.n_submit_calls == 2 and len(hy.jobs) == 6
            other = prepare_jobs(stack, pairs[:6], "INSAR_ISCE_MULTI_BURST", "10x2", True, name)
            _expect_raises(ValueError, submit_missing, hy, other, name, 100, 1.0, match="inne parametry")
            _expect_raises(ValueError, submit_missing, hy, jobs + jobs[:1], name, 100, 1.0, match="Zdublowane")
            # Dwa zlecenia tej samej tożsamości (FAILED zwrócone przez API pierwsze, potem SUCCEEDED): raport SUCCEEDED.
            hy2 = FakeHyP3(credits=100)
            submit_missing(hy2, jobs[:1], name, 100, 1.0)
            ok_job = hy2.jobs[0]
            hy2.jobs.insert(0, FakeJob(job_type=ok_job.job_type, job_id="job-failed", request_time=ok_job.request_time,
                                       status_code="FAILED", user_id="selftest", name=name,
                                       job_parameters=dict(ok_job.job_parameters), files=[]))
            r4 = submit_missing(hy2, jobs[:1], name, 100, 1.0)
            assert list(r4["status_code"]) == ["SUCCEEDED"] and list(r4["job_id"]) == [ok_job.job_id], r4

            # 5. Pobranie: tylko SUCCEEDED, manifest z SHA-256, drugie uruchomienie bez pobierania.
            hy.jobs[0].status_code, hy.jobs[1].status_code = "FAILED", "RUNNING"
            proj = tmp / "proj"
            raw = proj / "data" / "01_Raw_InSAR" / "hyp3"
            man = proj / "data" / "00_Metadata" / "MANIFEST.csv"
            man.parent.mkdir(parents=True)
            dl = download_succeeded(hy, name, raw, man, proj, "selftest")
            assert sorted(dl["status"]) == ["brak produktu: zlecenie FAILED", "brak produktu: zlecenie RUNNING"] + ["downloaded"] * 4
            m = pd.read_csv(man)
            assert len(m) == 4 and (m["licence"] == HYP3_LICENCE).all()
            ok = dl[dl["status"] == "downloaded"]
            assert all(sha256_file(Path(z)) == s for z, s in zip(ok["zip_path"], ok["sha256"]))
            assert all((Path(p) / f"{Path(p).name}_unw_phase.tif").is_file() for p in ok["product_dir"])
            n_dl = FakeJob.downloads
            dl2 = download_succeeded(hy, name, raw, man, proj, "selftest")
            assert FakeJob.downloads == n_dl == 4 and (dl2.dropna(subset=["product_name"])["status"] == "existing").all()
            assert len(pd.read_csv(man)) == 4

            # 6. Przycięcie: wspólny obszar, identyczny kształt i wartości (wartość = położenie w siatce globalnej).
            prods = list(ok["product_dir"])                 # zlecenia k = 2..5: przesunięcia dx 2,0,1,2; dy 0,1,0,1
            clip = raw.parent / "hyp3_clip"
            cl = clip_to_common_overlap(prods, _T_LAYERS, clip)
            assert (cl["status"] == "written").all() and set(zip(cl["height"], cl["width"])) == {(29, 38)}
            arrs = []
            for p in cl[cl["layer"] == "unw_phase"]["clip_path"]:
                with rasterio.open(p) as ds:
                    arrs.append(ds.read(1))
                    assert ds.bounds.left == _T_X0 + 2 * _T_PX and ds.bounds.top == _T_Y0 - _T_PX
            assert all(np.array_equal(a, arrs[0]) for a in arrs) and arrs[0][0, 0] == 2 + 1000 * 1
            assert all((clip / Path(p).name / f"{Path(p).name}.txt").is_file() for p in prods)
            assert (clip_to_common_overlap(prods, _T_LAYERS, clip)["status"] == "existing").all()
            bad = tmp / "bad"
            pn = [f"S1_{_T_TRACK:03d}_100002s1n02-000000s2n00-000000s3n00_IW_20240105_2024011{i}_VV_INT80_00A{i}"
                  for i in range(4)]
            _write_product(bad / "crs", pn[0], 0, _T_EPSG, 0.0, _T_LAYERS)
            _write_product(bad / "crs", pn[1], 1, 32632, 0.0, _T_LAYERS)
            _expect_raises(ValueError, clip_to_common_overlap, [bad / "crs" / pn[0], bad / "crs" / pn[1]], _T_LAYERS,
                           bad / "o1", match="różnych układach")
            _write_product(bad / "half", pn[2], 0, _T_EPSG, 0.0, _T_LAYERS)
            _write_product(bad / "half", pn[3], 1, _T_EPSG, 0.5 * _T_PX, _T_LAYERS)
            _expect_raises(ValueError, clip_to_common_overlap, [bad / "half" / pn[2], bad / "half" / pn[3]], _T_LAYERS,
                           bad / "o2", match="nie są wyrównane")
            (bad / "crs" / pn[0] / f"{pn[0]}_dem.tif").unlink()
            _expect_raises(ValueError, clip_to_common_overlap, [bad / "crs" / pn[0]], _T_LAYERS, bad / "o3",
                           match="brak warstwy 'dem'")
            _expect_raises(ValueError, clip_to_common_overlap, prods[:2], _T_LAYERS, clip, match="spoza bieżącej")
            p0 = Path(prods[0])
            twin = p0.parent / (p0.name[:-4] + "FFFF")      # ta sama para dat, inny produkt (kompletny, poprawne nazwy)
            twin.mkdir()
            for f in p0.iterdir():
                shutil.copy2(f, twin / f.name.replace(p0.name, twin.name))
            _expect_raises(ValueError, clip_to_common_overlap, prods + [twin], _T_LAYERS, bad / "o4",
                           match="tej samej pary dat")
            shutil.rmtree(twin)

            # 7. Szablon MintPy, nazwa szeregu końcowego, uruchomienie (atrapa smallbaselineApp.py na PATH).
            mcfg = {"troposphere": "no", "deramp": "no", "solid_earth_tides": False, "topographic_residual": True,
                    "min_temp_coh": 0.7, "reference_rule": "stable_gnss_min_abs_vu", "window_px": 3}
            with rasterio.open(cl["clip_path"].iat[0]) as ds:
                bb = ds.bounds
            lon_c, lat_c = transform_xy((bb.left + bb.right) / 2, (bb.bottom + bb.top) / 2, _T_EPSG, 4326)
            tpl = write_mintpy_template(tmp / "mintpy" / "EGMSCheckSenAT088.txt", clip, (lat_c, lon_c), mcfg)
            t = _read_template(tpl)
            assert t["mintpy.load.processor"] == "hyp3" and t["mintpy.reference.lalo"] == f"{lat_c:.6f},{lon_c:.6f}"
            assert t["mintpy.load.unwFile"] == f"{clip.resolve().as_posix()}/*/*_unw_phase_clip.tif"
            assert t["mintpy.load.incAngleFile"].endswith("*_lv_theta_clip.tif") and t["mintpy.load.azAngleFile"].endswith("*_lv_phi_clip.tif")
            assert (t["mintpy.troposphericDelay.method"], t["mintpy.networkInversion.minTempCoh"], t["mintpy.topographicResidual"],
                    t["mintpy.deramp"], t["mintpy.solidEarthTides"], t["mintpy.ionosphericDelay.method"]) == \
                ("no", "0.7", "yes", "no", "no", "no")
            _expect_raises(ValueError, write_mintpy_template, tmp / "x.txt", clip, (10.0, 10.0), mcfg, match="poza zasięgiem")
            _expect_raises(ValueError, write_mintpy_template, tmp / "smallbaselineApp.cfg", clip, (lat_c, lon_c), mcfg)
            _expect_raises(KeyError, write_mintpy_template, tmp / "x.txt", clip, (lat_c, lon_c),
                           {k: v for k, v in mcfg.items() if k != "deramp"}, match="deramp")
            assert expected_timeseries_name(mcfg) == "timeseries_demErr.h5"
            assert expected_timeseries_name({**mcfg, "troposphere": "height_correlation", "deramp": "quadratic",
                                             "solid_earth_tides": True}) == "timeseries_SET_tropHgt_ramp_demErr.h5"
            assert expected_timeseries_name({**mcfg, "troposphere": "pyaps", "weather_model": "ERA5",
                                             "topographic_residual": False}) == "timeseries_ERA5.h5"
            assert expected_timeseries_name({**mcfg, "topographic_residual": False}) == "timeseries.h5"
            _expect_raises(ValueError, expected_timeseries_name, {**mcfg, "troposphere": "gacos"})
            _expect_raises(ValueError, expected_timeseries_name, {**mcfg, "troposphere": "pyaps"}, match="weather_model")
            bindir = tmp / "bin"
            bindir.mkdir()
            fake_sba = bindir / "smallbaselineApp.py"
            fake_sba.write_text(
                f"#!{sys.executable}\nimport json, sys, pathlib\na = sys.argv[1:]\n"
                "wd = pathlib.Path(a[a.index('--work-dir') + 1])\n(wd / 'inputs').mkdir(parents=True, exist_ok=True)\n"
                "for n in ('timeseries.h5', 'timeseries_demErr.h5', 'inputs/geometryGeo.h5', 'maskTempCoh.h5'):\n"
                "    (wd / n).write_bytes(b'')\n(wd / 'argv.json').write_text(json.dumps(a))\n")
            fake_sba.chmod(0o755)
            os.environ["PATH"] = str(tmp / "empty")
            _expect_raises(FileNotFoundError, run_mintpy, tpl, tmp / "mintpy" / "work", match="PATH")
            os.environ["PATH"] = str(bindir) + os.pathsep + old_path
            ts_path = run_mintpy(tpl, tmp / "mintpy" / "work")
            assert ts_path == (tmp / "mintpy" / "work" / "timeseries_demErr.h5").resolve()
            assert json.loads((ts_path.parent / "argv.json").read_text()) == [str(tpl.resolve()), "--work-dir",
                                                                              str(ts_path.parent)]
            os.environ["PATH"] = old_path
            sites = pd.DataFrame({"site": ["SA", "SB", "SC"], "site_type": ["gnss"] * 3,
                                  "group": ["stabilna", "stabilna", "osiadająca"], "lat_deg": [52.1, 52.2, 52.3],
                                  "lon_deg": [5.1, 5.2, 5.3], "vu_mm_yr": [0.6, -0.2, -4.0]})
            assert reference_lalo_from_rule(sites, "stable_gnss_min_abs_vu")["site"] == "SB"

            # 8. Wektor LOS: norma 1, przypadek liczony ręcznie (inc 40, az 102), kontrola z wektorem EGMS.
            inc = np.array([30.0, 40.0, 45.0])
            az = np.array([102.0, -102.0, 78.0])
            assert np.allclose(np.sqrt(sum(x ** 2 for x in los_unit_vector(inc, az))), 1.0)
            # sin 40 = 0.6427876, sin 102 = 0.9781476, cos 102 = -0.2079117, cos 40 = 0.7660444
            assert np.allclose(los_unit_vector(40.0, 102.0), (-0.6287414, -0.1336424, 0.7660444), atol=1e-6)
            asc, desc = los_unit_vector(40.0, 102.0), los_unit_vector(40.0, -102.0)
            assert check_los_vs_egms(asc, los_unit_vector(41.0, 101.0), 0.05)["pass"]
            assert not check_los_vs_egms(asc, desc, 0.05)["pass"]
            _expect_raises(ValueError, check_los_vs_egms, asc, asc, None, match="None")

            # 9. Szeregi w punktach: znana prędkość odzyskana przez step_03.fit_velocity; maska; NaN z powodem.
            mdates = pd.date_range("2024-01-05", periods=46, freq="12D")
            mp = _write_synthetic_mintpy(tmp, mdates, rng)
            loc = {"A": (30, 20), "D": (35, 24), "B": (10, 40)}
            pts = pd.DataFrame([{"site": s, "lon_deg": _pixel_lonlat(*rc)[0], "lat_deg": _pixel_lonlat(*rc)[1]}
                                for s, rc in loc.items()] + [{"site": "C", "lon_deg": 20.0, "lat_deg": 40.0}])
            own = mintpy_series_at_points(mp["ts"], mp["geom"], mp["mask"], pts, 3, "testregion", _T_TRACK)
            assert list(own.columns) == LONG_COLUMNS and (own["source"] == SOURCE).all()
            v_true = {"A": -6.0, "D": -6.0 + 0.5 * 4 + 0.25 * 5}
            for s, vt in v_true.items():
                g = own[own["site"] == s]
                v, _ = fit_velocity(pd.DatetimeIndex(g["date"]), g["disp_mm"].to_numpy(), "linear")
                assert abs(v - vt) < 0.1, (s, v, vt)
                assert (g["status"] == "ok").all() and g["disp_mm"].iat[0] == 0.0
                assert np.allclose(g[["los_east", "los_north", "los_up"]].iloc[0].to_numpy(float), asc)
            assert own[own["site"] == "A"]["n_points"].iat[0] == 7 and own[own["site"] == "D"]["n_points"].iat[0] == 9
            assert own[own["site"] == "B"]["disp_mm"].isna().all() and own[own["site"] == "B"]["status"].iat[0].startswith("NaN: brak ważnych")
            assert own[own["site"] == "C"]["disp_mm"].isna().all() and "poza zasięgiem" in own[own["site"] == "C"]["status"].iat[0]
            assert (own["direction"] == "ascending").all() and (own["ref_date"] == mdates[0]).all()
            assert (own["track"] == str(_T_TRACK)).all(), "track jako tekst (format długi step_07)"
            # Kontrakt z step_07: szeregi 'ok' przechodzą validate_long; punkty bez szeregu tylko w tabeli statusów.
            from step_07_monitoring import validate_long
            ser, st = split_long_status(own)
            assert sorted(ser["site"].unique()) == ["A", "D"] and len(validate_long(ser)) == 2 * len(mdates)
            assert list(st["site"]) == ["A", "B", "C", "D"] and list(st["status"] == "ok") == [True, False, False, True]

            # 10. Dowiązanie do EGMS: offset = v (t0_EGMS - t_ref własny) w latach; za mało dat -> NaN z powodem.
            edates = pd.date_range("2020-01-03", "2024-12-31", freq="6D")
            te = years_since(edates, edates[0])
            egms = pd.concat([pd.DataFrame({"source": "EGMS_L2b_2020_2024", "site": s, "track": _T_TRACK, "date": edates,
                                            "disp_mm": vt * te + rng.normal(0, 0.3, len(edates)), "ref_date": edates[0],
                                            "reference": "absolute"}) for s, vt in v_true.items()], ignore_index=True)
            shifted, tab = align_to_reference(own, egms, "2024-01-01", "2024-12-31", 6)
            years = (mdates[0] - edates[0]).days / DAYS_PER_YEAR
            for s, vt in v_true.items():
                r = tab[tab["site"] == s].iloc[0]
                assert r["status"] == "ok" and r["n_matched"] == 31 and abs(r["offset_mm"] - (-vt * years)) < 0.3, r
                assert r["std_diff_mm"] < 1.0 and r["corr"] > 0.9
                sh = shifted[(shifted["site"] == s) & (shifted["date"] <= "2024-12-31")].set_index("date")["disp_mm"]
                e_at = gnss_at_dates(egms[egms["site"] == s].set_index("date")["disp_mm"], sh.index, 6)
                assert float(np.median(np.abs(sh - e_at))) < 0.3
                assert (shifted[shifted["site"] == s]["reference"] == "absolute").all()
            assert tab.set_index("site").loc["B", "status"] == "NaN: brak szeregu EGMS dla (site, track)"
            assert shifted[shifted["site"].isin(["B", "C"])]["disp_mm"].isna().all()
            ser_s, st_s = split_long_status(shifted)
            assert len(validate_long(ser_s)) == 2 * len(mdates) and (ser_s["reference"] == "absolute").all()
            # Ścieżka EGMS jako float (CSV z pustymi polami) i NaN w EGMS co trzecią datę: ten sam wynik dowiązania
            # (mediana okna +-6 dni z dat z wartością; bez pominięcia NaN część dat straciłaby dopasowanie).
            egms_nan = egms.assign(track=float(_T_TRACK),
                                   disp_mm=egms["disp_mm"].where(np.arange(len(egms)) % 3 != 1))
            _, tab_nan = align_to_reference(own, egms_nan, "2024-01-01", "2024-12-31", 6)
            assert (tab_nan.set_index("site").loc[["A", "D"], "n_matched"] == 31).all(), tab_nan
            assert np.allclose(tab_nan.set_index("site").loc[["A", "D"], "offset_mm"],
                               tab.set_index("site").loc[["A", "D"], "offset_mm"], atol=0.3)
            _, few = align_to_reference(own, egms, "2024-12-01", "2024-12-31", 6)
            ra = few.set_index("site").loc["A"]
            assert np.isnan(ra["offset_mm"]) and ra["status"].startswith("NaN: za mało dopasowanych dat"), ra
            print(json.dumps({"bursts": len(b), "stack_dates": len(stack), "pairs": len(pairs),
                              "jobs_after_rerun": len(hy.jobs), "clip_shape": [29, 38],
                              "v_A_mm_yr": float(fit_velocity(pd.DatetimeIndex(own[own["site"] == "A"]["date"]),
                                                              own[own["site"] == "A"]["disp_mm"].to_numpy(), "linear")[0]),
                              "offset_A_mm": float(tab.set_index("site").loc["A", "offset_mm"]),
                              "offset_A_expected_mm": 6.0 * years}, indent=1))
    finally:
        globals().update(saved)
        os.environ["PATH"] = old_path
    print("SELFTEST step_08_hyp3_mintpy OK")


def describe_product(product_dir) -> None:
    """Opis rozpakowanego produktu HyP3 bez obliczeń: nazwa i typ, pliki .tif (CRS, rozmiar, piksel, zasięg), klucze .txt."""
    import rasterio
    d = Path(product_dir)
    name, job_type = product_name_and_type(d.name)
    out = {"product": name, "job_type": job_type, "dates": [str(x.date()) for x in product_dates(name)], "layers": {}}
    for f in sorted(d.glob("*.tif")):
        with rasterio.open(f) as ds:
            out["layers"][f.name] = {"crs": str(ds.crs), "width": ds.width, "height": ds.height,
                                     "pixel": [ds.transform.a, ds.transform.e], "bounds": list(ds.bounds),
                                     "dtype": ds.dtypes[0], "nodata": ds.nodata}
    txt = d / f"{name}.txt"
    out["txt_keys"] = [ln.split(":")[0].strip() for ln in txt.read_text().splitlines() if ":" in ln] if txt.exists() else None
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="EGMS Check - KROK 8")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--describe-product", metavar="KATALOG", help="opis rozpakowanego produktu HyP3 (bez obliczeń)")
    a = ap.parse_args()
    if a.selftest:
        _selftest()
    elif a.describe_product:
        describe_product(a.describe_product)
    else:
        ap.print_help()
