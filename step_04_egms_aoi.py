"""
================================================================================
EGMS Check - KROK 4: EGMS DLA OBSZARU: WYSZUKANIE L2B I L3, PLAN POBRANIA, CZYTNIK L3, MAPA PRĘDKOŚCI
================================================================================
Pokaz EGMS dla obszaru (Groningen, zachodnia NRW; docs/plans/Plan_v2_pokaz_EGMS_monitoring.md),
interfejs według docs/plans/Plan_v2_implementacja.md, sekcja 4.1. Kontynuacja kodu E1: wyszukanie, manifest
i SHA-256 z step_01_ingest, wycinek i kolumny dat z step_02_checks_extract; wynik komórki L3 przechodzi
bez zmian przez step_03_compare_gnss.compare_station_track.

  I.   Obszar: prostokąt lon/lat (WGS84) -> prostokąt obejmujący w EPSG:3035 (narożniki i zagęszczone krawędzie,
       pyproj); transform_xy przeniesione z prototypu.
  II.  Wyszukanie (POST /search) w prostokącie: L2B (bursty) i L3 Ortho (kafle 100 km, productType ORTHO-UP / -EAST).
       Prostokąt maks. 5 x 5 stopni (limit API). Nazwy L3 sprawdzane wzorcem; plik innej składowej niż zamówiona
       (API mogłoby zignorować productType) jest pomijany jawnie, z liczbą i nazwami w logu; nazwa niezgodna
       ze wzorcem = wyjątek.
  III. Plan pobrania: stan plików lokalnych (existing / missing / partial), potrzebne bajty, kontrola wolnego
       miejsca z marginesem; pobranie przyrostowe sync_files (jak step_01.sync_egms) z wpisem w MANIFEST.csv.
  IV.  Czytnik L3 (zip z CSV, czytany fragmentami): komórki w prostokącie (mapa) i komórka 100 m zawierająca
       punkt naziemny (semantyka cell_containing z prototypu). Komórka dostaje wektor LOS (0, 0, 1), ścieżkę 'L3'
       i kierunek 'vertical', więc rzut GNSS w step_03 daje składową pionową U.
  V.   Mapa prędkości L2b (opcjonalnie, l2b_aoi_map): pid, easting, northing, mean_velocity (LOS) w prostokącie.
  VI.  --selftest bez sieci: atrapa /search i /download, syntetyczne zipy L2B i L3 o znanych komórkach.

Odstępstwa od specyfikacji 4.1 (do akceptacji autora):
  - step_01.hits_table wymaga pól relativeOrbit, direction, burstId; trafienia L3 mogą ich nie mieć
    (niezweryfikowane), więc dla L3 jest własna tabela hits_table_l3; L2B nadal idzie przez step_01.hits_table.
  - step_01.sync_egms buduje opis manifestu z burstId; dla L3 jest ogólne sync_files (ta sama logika: plik .part,
    kontrola rozmiaru, adres bez ?id=, SHA-256), opis z dostępnych pól; przerwa przed każdym pobraniem,
    także pierwszym w wywołaniu (wywołujący pobiera w pętli po zapytaniach).
  - dodane: search_plan (wszystkie poziomy naraz + wyniki zapytań do pobrania), hits_table_aoi, hits_table_l3,
    sync_files, l3_grid_offsets (kontrola konwencji: czy easting/northing L3 to środki komórek).
  - search_aoi zwraca wynik z trafieniami ograniczonymi do tabeli: plik odrzucony filtrem składowej nie może zostać
    pobrany przez sync_files z pominięciem planu miejsca.
  - sync_files nie nadpisuje pliku zarejestrowanego w manifeście treścią o innym SHA-256 (wyjątek przed podmianą)
    i ma limit oczekiwania HTTP_TIMEOUT_S; step_01.sync_egms nadpisuje plik i dopiero potem zgłasza różnicę sumy.
  - l3_cells_at_sites przyjmuje tylko kafle składowej U (nazwa pliku; wektor (0, 0, 1) jest poprawny tylko dla pionu);
    czytniki L3 odrzucają plik z kolumnami LOS (L2 ma wszystkie kolumny L3_REQUIRED); kolumny dat muszą rosnąć
    ściśle, a wynik dla kafli o różnych datach ma sumę dat w porządku chronologicznym (NaN poza kaflem, ostrzeżenie).

Konwencje: EPSG:3035 (easting, northing) dla EGMS, stopnie WGS84 dla prostokąta obszaru; L3 pion w mm, w górę
dodatni; prędkości mm/rok; ujemne = osiadanie / oddalanie od satelity. Parametry (prostokąt, wydanie, poziomy,
produkty, rozmiar komórki, margines miejsca, przerwa) pochodzą z CHECK_CONFIG, nie z sygnatur.

Literatura i źródła: docs/evidence/F5_zrodla_danych.md, sekcja 1 (EGMS Product Description: nazwy plików
i kolumny L3; oficjalny notatnik copernicus-land/egms-api: /search, bbox, productType, /download);
docs/evidence/F4_metodyka.md (komórka L3 100 m zawierająca reper; Even i in. 2024; Koudogbo i in. 2025);
Hrysiewicz i in. 2024 (EGMS-toolkit: przerwy między zapytaniami do serwera).
================================================================================
"""

import argparse
import io
import json
import logging
import re
import shutil
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from step_01_ingest import (EGMS_LICENCE, MANIFEST_COLUMNS, hits_table, manifest_path_of, search_egms, sha256_file,
                            update_manifest)
from step_02_checks_extract import DATE_COL, L2_REQUIRED, date_columns, extract_points

logger = logging.getLogger("EGMSCheck_AOI")

BBOX_MAX_DEG = 5.0                      # limit API EGMS dla bbox (F5, sekcja 1); nie parametr eksperymentu
SUPPORTED_LEVELS = ("L2B", "L3")        # zapis poziomów jak w przykładach API (F5)
L3_PRODUCT_COMPONENT = {"ORTHO-UP": "U", "ORTHO-EAST": "E"}   # productType -> litera składowej w nazwie pliku
L3_NAME = re.compile(r"^EGMS_L3_(?P<tile>E\d{2}N\d{2})_100km_(?P<component>[UE])_(?P<year1>\d{4})_(?P<year2>\d{4})"
                     r"_(?P<version>\d+)\.zip$")
RELEASE_NAME = re.compile(r"^(?P<year1>\d{4})-(?P<year2>\d{4})$")
HIT_REQUIRED = ["filename", "filesize", "release", "productLevel"]
HIT_OPTIONAL = ["productType", "relativeOrbit", "direction", "burstId", "tileId", "bbox", "poly"]
L3_REQUIRED = ["pid", "easting", "northing", "mean_velocity", "mean_velocity_std"]
L2_LOS_COLUMNS = ["los_east", "los_north", "los_up"]   # tylko L2 (F5: L3 nie ma wektora LOS) -> plik L2 podany omyłkowo
L3_MAP_COLUMNS = list(L3_REQUIRED)
L2B_MAP_COLUMNS = ["pid", "easting", "northing", "mean_velocity"]
L3_SITE_EXTRA = ["site", "distance_m", "source_file", "los_east", "los_north", "los_up", "track", "direction"]
AOI_DENSIFY = 101                       # punktów na krawędź prostokąta przy przeliczeniu (dokładność numeryczna)
HTTP_TIMEOUT_S = 300                    # limit oczekiwania na serwer (jak step_01.download_file); zawieszenie = wyjątek


# ==============================================================================
# I. OBSZAR: LON/LAT -> EPSG:3035
# ==============================================================================
def _check_aoi(aoi_lonlat) -> tuple:
    """Prostokąt (lon0, lat0, lon1, lat1) w stopniach WGS84; lon0 < lon1, lat0 < lat1, wartości skończone."""
    if len(aoi_lonlat) != 4:
        raise ValueError(f"Prostokąt obszaru musi mieć 4 wartości (lon0, lat0, lon1, lat1), jest {aoi_lonlat}")
    lon0, lat0, lon1, lat1 = (float(v) for v in aoi_lonlat)
    if not np.isfinite([lon0, lat0, lon1, lat1]).all():
        raise ValueError(f"Prostokąt obszaru z wartością nieskończoną lub NaN: {aoi_lonlat}")
    if not (-180.0 <= lon0 < lon1 <= 180.0 and -90.0 <= lat0 < lat1 <= 90.0):
        raise ValueError(f"Prostokąt obszaru poza zakresem lub odwrócony (lon0 < lon1, lat0 < lat1): {aoi_lonlat}")
    return lon0, lat0, lon1, lat1


def _check_rect(rect, what: str) -> tuple:
    """Prostokąt (x0, y0, x1, y1) w metrach; x0 < x1, y0 < y1."""
    if len(rect) != 4:
        raise ValueError(f"{what}: oczekiwano (x0, y0, x1, y1), jest {rect}")
    x0, y0, x1, y1 = (float(v) for v in rect)
    if not (np.isfinite([x0, y0, x1, y1]).all() and x0 < x1 and y0 < y1):
        raise ValueError(f"{what}: prostokąt odwrócony albo z NaN: {rect}")
    return x0, y0, x1, y1


def transform_xy(x, y, epsg_from: int, epsg_to: int):
    """
    Przeliczenie współrzędnych (pyproj, kolejność x/y zawsze lon/lat lub easting/northing).
    Przeniesione z prototypes/egms_simple_check.py (transform_xy), bez zmian.
    """
    from pyproj import Transformer
    tr = Transformer.from_crs(epsg_from, epsg_to, always_xy=True)
    return tr.transform(x, y)


def aoi_lonlat_to_3035(aoi_lonlat) -> tuple:
    """
    Prostokąt lon/lat -> najmniejszy prostokąt EPSG:3035 (x0, y0, x1, y1), który go obejmuje.
    Krawędzie są zagęszczone (AOI_DENSIFY punktów), bo w odwzorowaniu LAEA równoleżniki są łukami:
    skrajna wartość może leżeć wewnątrz krawędzi (np. obszar przecinający południk 10° E), nie w narożniku.
    """
    lon0, lat0, lon1, lat1 = _check_aoi(aoi_lonlat)
    lon, lat = np.linspace(lon0, lon1, AOI_DENSIFY), np.linspace(lat0, lat1, AOI_DENSIFY)
    edge_lon = np.concatenate([lon, np.full_like(lat, lon1), lon[::-1], np.full_like(lat, lon0)])
    edge_lat = np.concatenate([np.full_like(lon, lat0), lat, np.full_like(lon, lat1), lat[::-1]])
    x, y = (np.asarray(v, float) for v in transform_xy(edge_lon, edge_lat, 4326, 3035))
    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        raise ValueError(f"Przeliczenie {aoi_lonlat} do EPSG:3035 dało wartości nieskończone")
    return float(x.min()), float(y.min()), float(x.max()), float(y.max())


# ==============================================================================
# II. WYSZUKANIE L2B I L3 W PROSTOKĄCIE
# ==============================================================================
def bbox_query(aoi_lonlat: tuple, level: str, release: str, product_type: str | None) -> dict:
    """
    Zapytanie POST /search dla prostokąta: {"id": None, "bbox": [[lon0, lat0], [lon1, lat1]], "levels": [level],
    "releases": [release]} (+ "productType" dla L3). Prostokąt większy niż 5 x 5 stopni = ValueError (limit API).
    L3 wymaga productType (ORTHO-UP / ORTHO-EAST); L2B nie przyjmuje productType.
    """
    lon0, lat0, lon1, lat1 = _check_aoi(aoi_lonlat)
    if lon1 - lon0 > BBOX_MAX_DEG or lat1 - lat0 > BBOX_MAX_DEG:
        raise ValueError(f"Prostokąt {aoi_lonlat} ma {lon1 - lon0:.2f} x {lat1 - lat0:.2f} stopni; "
                         f"API EGMS przyjmuje maks. {BBOX_MAX_DEG} x {BBOX_MAX_DEG} (F5). Podziel obszar.")
    if level not in SUPPORTED_LEVELS:
        raise ValueError(f"Nieobsługiwany poziom {level!r}; dozwolone {SUPPORTED_LEVELS}")
    if not RELEASE_NAME.match(str(release)):
        raise ValueError(f"Wydanie {release!r} nie ma postaci 'RRRR-RRRR' (zapis jak w API, F5)")
    query = {"id": None, "bbox": [[lon0, lat0], [lon1, lat1]], "levels": [level], "releases": [release]}
    if level == "L3":
        if product_type not in L3_PRODUCT_COMPONENT:
            raise ValueError(f"L3 wymaga productType z {sorted(L3_PRODUCT_COMPONENT)}, jest {product_type!r} "
                             f"(CHECK_CONFIG['egms']['l3_product_types'])")
        query["productType"] = product_type
    elif product_type is not None:
        raise ValueError(f"productType dotyczy tylko L3, a podano {product_type!r} dla {level}")
    return query


def hits_table_l3(result: dict, product_type: str) -> pd.DataFrame:
    """
    Trafienia L3 jako tabela. Wymagane pola: filename, filesize, release, productLevel; pola L2B (relativeOrbit,
    direction, burstId) zostają, jeśli są. Nazwa rozbita wzorcem EGMS_L3_E<XX>N<YY>_100km_<U|E>_<r1>_<r2>_<wersja>.zip
    na tile, component, year1, year2, version. Nazwa niezgodna = ValueError. Pliki innej składowej niż productType
    są pomijane z ostrzeżeniem (liczba i nazwy), nigdy po cichu.
    """
    if product_type not in L3_PRODUCT_COMPONENT:
        raise ValueError(f"Nieznany productType L3 {product_type!r}; dozwolone {sorted(L3_PRODUCT_COMPONENT)}")
    df = pd.DataFrame(result["hits"])
    missing = [c for c in HIT_REQUIRED if c not in df.columns]
    if missing:
        raise KeyError(f"Trafienia L3 bez pól {missing}; dostępne: {list(df.columns)}")
    parsed = df["filename"].str.extract(L3_NAME)
    bad = df.loc[parsed["tile"].isna(), "filename"].tolist()
    if bad:
        raise ValueError(f"Nazwy plików L3 niezgodne ze wzorcem {L3_NAME.pattern}: {bad}")
    df = pd.concat([df[HIT_REQUIRED + [c for c in HIT_OPTIONAL if c in df.columns]], parsed], axis=1)
    comp = L3_PRODUCT_COMPONENT[product_type]
    other = df["component"] != comp
    if other.any():
        logger.warning(f"L3 {product_type}: pominięto {int(other.sum())} plików innej składowej niż '{comp}' "
                       f"(API zwróciło je mimo productType): {df.loc[other, 'filename'].tolist()}")
    df = df[~other].reset_index(drop=True)
    df["filesize_mb"] = df["filesize"] / 1e6
    return df


def hits_table_aoi(result: dict, level: str, product_type: str | None) -> pd.DataFrame:
    """Tabela trafień zależna od poziomu: L2B -> step_01.hits_table (bez zmian), L3 -> hits_table_l3."""
    if level == "L2B":
        if product_type is not None:
            raise ValueError(f"productType dotyczy tylko L3, a podano {product_type!r} dla L2B")
        return hits_table(result)
    if level == "L3":
        return hits_table_l3(result, product_type)
    raise ValueError(f"Nieobsługiwany poziom {level!r}; dozwolone {SUPPORTED_LEVELS}")


def _check_release(tab: pd.DataFrame, release: str) -> None:
    """Pole release trafień = zamówione wydanie; dla L3 także lata w nazwie pliku. Inaczej ValueError."""
    other = sorted(set(tab["release"].astype(str)) - {release})
    if other:
        raise ValueError(f"Trafienia z wydaniem {other}, zamówiono {release!r} - API zignorowało filtr "
                         f"albo zapisuje wydanie inaczej (sprawdź GET /releases)")
    if "year1" in tab.columns:
        y = RELEASE_NAME.match(release)
        bad = tab.loc[(tab["year1"] != y["year1"]) | (tab["year2"] != y["year2"]), "filename"].tolist()
        if bad:
            raise ValueError(f"Lata w nazwach plików L3 niezgodne z wydaniem {release}: {bad}")


def search_aoi(session, headers: dict, endpoint: str, aoi_lonlat: tuple, level: str, release: str,
               product_type: str | None) -> tuple[dict, pd.DataFrame]:
    """
    Wyszukanie plików jednego poziomu (i dla L3 jednego productType) w prostokącie: bbox_query
    -> step_01.search_egms -> tabela trafień (hits_table_aoi) z kolumną level.
    Pusty wynik (także po odrzuceniu plików innej składowej L3) = RuntimeError. Zwraca (wynik, tabela): wynik ma
    identyfikator zapytania (id, potrzebny do pobrania) i trafienia OGRANICZONE do plików z tabeli, więc plik
    odrzucony filtrem składowej (zapisany w logu) nie przejdzie przez sync_files i nie ominie planu miejsca.
    """
    query = bbox_query(aoi_lonlat, level, release, product_type)
    result = search_egms(session, headers, endpoint, query)
    if not result["hits"]:
        raise RuntimeError(f"Brak plików EGMS {level} {release} {product_type or ''} w prostokącie {aoi_lonlat}")
    tab = hits_table_aoi(result, level, product_type)
    if tab.empty:
        raise RuntimeError(f"Po odrzuceniu plików innej składowej nie został żaden plik {level} {product_type}")
    _check_release(tab, release)
    kept = set(tab["filename"])
    result = {**result, "hits": [h for h in result["hits"] if h["filename"] in kept]}
    tab.insert(0, "level", level)
    logger.info(f"{level}{' ' + product_type if product_type else ''} {release}: {len(tab)} plików, "
                f"{tab['filesize_mb'].sum():.1f} MB")
    return result, tab


def search_plan(session, headers: dict, endpoint: str, aoi_lonlat: tuple, release: str, levels: list,
                l3_product_types: list) -> tuple[pd.DataFrame, dict]:
    """
    Wyszukanie wszystkich poziomów z CHECK_CONFIG['egms'] (levels, l3_product_types) dla jednego prostokąta.
    Zwraca (jedna tabela trafień z kolumnami level, product_type, query_key; słownik query_key -> wynik search_aoi,
    tj. id i trafienia z tabeli).
    query_key = 'L2B' albo 'L3:<productType>'; wynik zapytania jest potrzebny przy pobraniu (identyfikator id;
    wygasa, więc przed pobraniem warto wyszukać ponownie). Ten sam plik w dwóch zapytaniach = ValueError.
    """
    if not levels:
        raise ValueError("Pusta lista poziomów EGMS (CHECK_CONFIG['egms']['levels'])")
    tabs, results = [], {}
    for level in levels:
        if level == "L3" and not l3_product_types:
            raise ValueError("L3 bez listy produktów (CHECK_CONFIG['egms']['l3_product_types'])")
        for pt in (list(l3_product_types) if level == "L3" else [None]):
            key = level if pt is None else f"{level}:{pt}"
            if key in results:
                raise ValueError(f"Zapytanie {key} powtórzone w konfiguracji")
            results[key], tab = search_aoi(session, headers, endpoint, aoi_lonlat, level, release, pt)
            tabs.append(tab.assign(product_type=pt, query_key=key))
    table = pd.concat(tabs, ignore_index=True)
    dup = table.loc[table["filename"].duplicated(), "filename"].tolist()
    if dup:
        raise ValueError(f"Te same pliki w różnych zapytaniach: {dup}")
    logger.info(f"Razem {len(table)} plików, {table['filesize_mb'].sum():.1f} MB "
                f"({table.groupby('query_key').size().to_dict()})")
    return table, results


# ==============================================================================
# III. PLAN POBRANIA I POBRANIE
# ==============================================================================
def drive_free_bytes(path: Path) -> int:
    """Wolne miejsce [B] w systemie plików zawierającym path (shutil.disk_usage); brak ścieżki = wyjątek."""
    return int(shutil.disk_usage(Path(path)).free)


def plan_download(hits: pd.DataFrame, out_dir: Path, free_bytes: int, margin_bytes: int) -> pd.DataFrame:
    """
    Stan plików z tabeli trafień w out_dir (jeden katalog dla wszystkich poziomów; nazwy L2b i L3 się nie
    pokrywają) i potrzebne miejsce. Kolumny trafień + local_bytes (NaN = brak pliku), status, need_bytes:
      'existing' - plik o rozmiarze równym filesize (sync_files go pominie), need_bytes = 0;
      'partial'  - jest plik .part albo plik o innym rozmiarze; pobranie od początku, need_bytes = filesize;
      'missing'  - brak pliku, need_bytes = filesize.
    need_bytes jest szacunkiem ostrożnym (bez wznawiania; zwalniane miejsce po .part nie jest odejmowane).
    Suma need_bytes > free_bytes - margin_bytes = RuntimeError z liczbami w GB.
    """
    missing = [c for c in ("filename", "filesize") if c not in hits.columns]
    if missing:
        raise KeyError(f"Tabela trafień bez kolumn {missing}")
    if hits.empty:
        raise ValueError("Pusta tabela trafień: nie ma czego planować (wynik search_aoi / search_plan)")
    dup = hits.loc[hits["filename"].duplicated(), "filename"].tolist()
    if dup:
        raise ValueError(f"Powtórzone pliki w tabeli trafień: {dup}")
    if free_bytes < 0 or margin_bytes < 0:
        raise ValueError(f"free_bytes ({free_bytes}) i margin_bytes ({margin_bytes}) muszą być >= 0")
    size = hits["filesize"].astype("int64").to_numpy()
    if (size <= 0).any():
        raise ValueError(f"filesize <= 0 dla {hits.loc[size <= 0, 'filename'].tolist()}")
    out_dir = Path(out_dir)
    local, status = [], []
    for fname, fsize in zip(hits["filename"], size):
        dest = out_dir / fname
        part = dest.with_suffix(dest.suffix + ".part")
        n = dest.stat().st_size if dest.exists() else None
        local.append(np.nan if n is None else float(n))
        status.append("existing" if n == fsize else "partial" if (part.exists() or n is not None) else "missing")
    plan = hits.copy()
    plan["local_bytes"], plan["status"] = local, status
    plan["need_bytes"] = np.where(plan["status"] == "existing", 0, size).astype("int64")
    need, avail = int(plan["need_bytes"].sum()), int(free_bytes) - int(margin_bytes)
    counts = plan["status"].value_counts().to_dict()
    logger.info(f"Plan pobrania {out_dir}: {counts}; potrzeba {need / 1e9:.2f} GB, wolne {free_bytes / 1e9:.2f} GB, "
                f"margines {margin_bytes / 1e9:.2f} GB")
    if need > avail:
        raise RuntimeError(f"Za mało miejsca w {out_dir}: do pobrania {need / 1e9:.2f} GB ({counts}), wolne "
                           f"{free_bytes / 1e9:.2f} GB, margines {margin_bytes / 1e9:.2f} GB, dostępne "
                           f"{avail / 1e9:.2f} GB. Zwolnij miejsce albo zmniejsz obszar (decyzja autora).")
    return plan


def _manifest_what(hit: dict) -> str:
    """Opis pliku do manifestu z dostępnych pól trafienia (L2B: jak step_01.sync_egms; L3: kafel i składowa)."""
    parts = [f"EGMS {hit['productLevel']}"]
    m = L3_NAME.match(hit["filename"])
    if m:
        parts += [f"tile {m['tile']}", f"component {m['component']}"]
    for key, label in (("productType", "product"), ("relativeOrbit", "track"), ("direction", None),
                       ("burstId", "burst")):
        if hit.get(key) is not None:
            parts.append(str(hit[key]) if label is None else f"{label} {hit[key]}")
    return " ".join(parts)


def _manifest_sha(manifest_path: Path, file_path: str) -> str | None:
    """SHA-256 pliku zapisane w manifeście albo None, gdy pliku w manifeście nie ma (jeszcze nie zarejestrowany)."""
    if not Path(manifest_path).exists():
        return None
    m = pd.read_csv(manifest_path, dtype=str)
    _require(m.columns, ["file_path", "sha256"], str(manifest_path))
    s = m.loc[m["file_path"] == file_path, "sha256"]
    return None if s.empty else str(s.iloc[0])


def sync_files(session, headers: dict, endpoint: str, result: dict, filenames: list, out_dir: Path,
               manifest_path: Path, project_dir: Path, pause_s: float, downloaded_by: str) -> pd.DataFrame:
    """
    Pobiera WYŁĄCZNIE pliki z listy `filenames` (potwierdzonej przez autora po obejrzeniu planu) z jednego wyniku
    wyszukania (jego id). Logika jak step_01.sync_egms: plik istniejący o rozmiarze filesize jest pomijany, zapis
    przez .part, kontrola rozmiaru, SHA-256 i wiersz manifestu z adresem bez ?id= (identyfikator wygasa).
    Różnice: opis manifestu z dostępnych pól (L3 może nie mieć burstId); przerwa pause_s przed każdym pobraniem,
    także pierwszym (wywołujący pobiera w pętli po zapytaniach; serwer odrzuca zbyt częste zapytania); limit
    oczekiwania HTTP_TIMEOUT_S; plik zarejestrowany w manifeście nie jest nadpisywany treścią o innym SHA-256
    (dane surowe są niezmienne: wyjątek przed podmianą, pobranie zostaje w .part).
    Wynik brać z search_aoi / search_plan (trafienia ograniczone do tabeli, bez plików odrzuconych filtrem składowej).
    """
    hits = {h["filename"]: h for h in result["hits"]}
    unknown = [f for f in filenames if f not in hits]
    if unknown:
        raise KeyError(f"Pliki spoza wyniku wyszukiwania: {unknown}")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for fname in filenames:
        hit = hits[fname]
        missing = [k for k in HIT_REQUIRED if k not in hit]
        if missing:
            raise KeyError(f"{fname}: trafienie bez pól {missing}")
        size, dest = int(hit["filesize"]), out_dir / fname
        file_path = manifest_path_of(dest, project_dir)
        status = "skipped_existing"
        if dest.exists() and dest.stat().st_size == size:
            digest = sha256_file(dest)
        else:
            time.sleep(pause_s)          # Hrysiewicz i in. 2024: przerwy między zapytaniami
            r = session.get(f"{endpoint}/download/{fname}", params={"id": result["id"]}, headers=headers, stream=True,
                            timeout=HTTP_TIMEOUT_S)
            r.raise_for_status()
            part = dest.with_suffix(dest.suffix + ".part")
            with open(part, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
            if part.stat().st_size != size:
                raise IOError(f"{fname}: pobrano {part.stat().st_size} B, oczekiwano {size} B")
            digest, known = sha256_file(part), _manifest_sha(manifest_path, file_path)
            if known is not None and known != digest:
                raise ValueError(f"{fname}: pobrana treść ma SHA-256 inne niż wpis w manifeście ({file_path}); dane "
                                 f"surowe są niezmienne - {dest.name} nie został nadpisany, pobranie zostało w {part.name}")
            part.replace(dest)
            status = "downloaded"
        update_manifest(manifest_path, {
            "file_path": file_path, "what": _manifest_what(hit),
            "source_url": f"{endpoint}/download/{fname}",
            "downloaded_on": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "downloaded_by": downloaded_by,
            "sha256": digest, "licence": EGMS_LICENCE, "egms_release": hit["release"], "notes": status})
        rows.append({"filename": fname, "status": status, "bytes": dest.stat().st_size, "sha256": digest})
        logger.info(f"{fname}: {status}")
    return pd.DataFrame(rows, columns=["filename", "status", "bytes", "sha256"])


# ==============================================================================
# IV. CZYTNIK L3 I KOMÓRKA PRZY PUNKCIE
# ==============================================================================
def l3_csv_name(zip_path: Path) -> str:
    """Nazwa jedynego pliku CSV w zipie (L3: obok .tif; działa też dla L2b). Zero lub więcej niż jeden = ValueError."""
    with zipfile.ZipFile(zip_path) as zf:
        csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if len(csvs) != 1:
        raise ValueError(f"{zip_path}: oczekiwano jednego pliku CSV, jest {csvs}")
    return csvs[0]


def _csv_header(zip_path: Path, name: str) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as zf, zf.open(name) as f:
        return pd.read_csv(f, nrows=0)


def _require(columns, required: list, what: str) -> None:
    missing = [c for c in required if c not in columns]
    if missing:
        raise KeyError(f"{what}: brak kolumn {missing}")


def _l3_header(zip_path: Path) -> tuple[str, pd.DataFrame]:
    """(nazwa CSV, nagłówek) pliku L3: kolumny L3_REQUIRED (brak = KeyError); kolumny LOS = plik L2 (ValueError)."""
    name = l3_csv_name(zip_path)
    header = _csv_header(zip_path, name)
    _require(header.columns, L3_REQUIRED, str(zip_path))
    los = [c for c in L2_LOS_COLUMNS if c in header.columns]
    if los:
        raise ValueError(f"{zip_path}: kolumny {los} oznaczają plik L2 (LOS), nie L3 (F5: L3 nie ma wektora LOS)")
    return name, header


def _checked_dates(header: pd.DataFrame, what: str) -> list:
    """Kolumny dat yyyymmdd (step_02.date_columns): poprawne daty kalendarzowe, ściśle rosnące; inaczej ValueError."""
    cols = date_columns(header)
    d = pd.to_datetime(pd.Index(cols), format="%Y%m%d")          # zła data (np. 20201345) = ValueError
    if d.has_duplicates or not d.is_monotonic_increasing:
        raise ValueError(f"{what}: kolumny dat nie rosną ściśle: {cols[:5]}...")
    return cols


def _read_rect(zip_path: Path, cols: list, aoi_3035: tuple, chunksize: int) -> pd.DataFrame:
    """Wiersze CSV z zipu w prostokącie EPSG:3035 (granice włącznie), tylko kolumny cols; pid jako tekst."""
    x0, y0, x1, y1 = _check_rect(aoi_3035, "aoi_3035")
    name, parts = l3_csv_name(zip_path), []
    with zipfile.ZipFile(zip_path) as zf, zf.open(name) as f:
        for chunk in pd.read_csv(f, chunksize=chunksize, usecols=cols, dtype={"pid": str}):
            m = chunk["easting"].between(x0, x1) & chunk["northing"].between(y0, y1)
            if m.any():
                parts.append(chunk.loc[m, cols])
    out = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)
    dup = out.loc[out["pid"].duplicated(), "pid"].tolist()
    if dup:
        raise ValueError(f"{zip_path}: zdublowane pid w jednym pliku: {dup[:10]}")
    logger.info(f"{Path(zip_path).name}: {len(out)} wierszy w prostokącie {aoi_3035}")
    return out


def read_l3_aoi(zip_path: Path, aoi_3035: tuple, chunksize: int, with_dates: bool) -> pd.DataFrame:
    """
    Komórki L3 w prostokącie EPSG:3035 (x0, y0, x1, y1). Wymagane kolumny L3_REQUIRED (brak = KeyError);
    plik z wektorem LOS (L2 podany omyłkowo) = ValueError.
    with_dates=False -> tylko pid, easting, northing, mean_velocity, mean_velocity_std (mapa);
    with_dates=True  -> te kolumny + kolumny dat yyyymmdd, ściśle rosnące (mm; składowa z nazwy pliku:
    U = pion, w górę dodatni; E = wschód dodatni).
    Brak komórek w prostokącie (np. kafel na morzu) = pusta tabela z kolumnami; ocenia wywołujący.
    """
    _, header = _l3_header(zip_path)
    cols = L3_MAP_COLUMNS + (_checked_dates(header, str(zip_path)) if with_dates else [])
    return _read_rect(zip_path, cols, aoi_3035, chunksize)


def l3_cells_at_sites(zip_paths: list, sites: pd.DataFrame, cell_m: float, chunksize: int) -> pd.DataFrame:
    """
    Komórka L3 zawierająca każdy punkt naziemny: |easting - x| <= cell_m/2 i |northing - y| <= cell_m/2
    (semantyka cell_containing z prototypes/egms_simple_check.py; easting/northing = środek komórki).
    sites: kolumny site, x_3035, y_3035. Przeszukiwane są wszystkie podane zipy (punkt może leżeć przy granicy kafla).
    Tylko kafle składowej pionowej: nazwa EGMS_L3_..._U_...zip (wektor (0, 0, 1) jest poprawny wyłącznie dla U;
    kafel E albo plik L2 = ValueError).
    Wynik: kolumny komórki (bez dat) + kolumny dat ściśle rosnące + site, distance_m (do środka komórki), source_file,
    los_east=0, los_north=0, los_up=1, track='L3', direction='vertical' -> wejście step_03.compare_station_track
    bez zmian (rzut GNSS wektorem (0, 0, 1) = składowa U). Kafle o różnych zestawach dat: suma dat, NaN w datach
    nieobecnych w kaflu komórki (ostrzeżenie z liczbą brakujących dat na plik).
    Więcej niż jedna komórka przy punkcie = ValueError. Punkt bez komórki = brak wiersza (status nadaje wywołujący).
    """
    _require(sites.columns, ["site", "x_3035", "y_3035"], "sites")
    if sites.empty:
        raise ValueError("Pusta tabela punktów naziemnych (sites)")
    if sites["site"].duplicated().any():
        raise ValueError(f"Powtórzone identyfikatory punktów: {sites.loc[sites['site'].duplicated(), 'site'].tolist()}")
    if not np.isfinite(cell_m) or cell_m <= 0:
        raise ValueError(f"cell_m musi być dodatnie, jest {cell_m}")
    if not zip_paths:
        raise ValueError("Brak plików L3 do przeszukania")
    fnames = [Path(zp).name for zp in zip_paths]
    if len(set(fnames)) != len(fnames):
        raise ValueError(f"Powtórzone pliki L3: {sorted({f for f in fnames if fnames.count(f) > 1})}")
    not_up = [f for f in fnames if not (L3_NAME.match(f) and L3_NAME.match(f)["component"] == "U")]
    if not_up:
        raise ValueError(f"Oczekiwano kafli L3 składowej pionowej (EGMS_L3_E..N.._100km_U_..zip); wektor (0, 0, 1) "
                         f"jest poprawny tylko dla U, a podano {not_up}")
    sx, sy = sites["x_3035"].to_numpy(float), sites["y_3035"].to_numpy(float)
    if not (np.isfinite(sx).all() and np.isfinite(sy).all()):
        raise ValueError(f"Punkty bez współrzędnych EPSG:3035: {sites.loc[~(np.isfinite(sx) & np.isfinite(sy)), 'site'].tolist()}")
    half, names = cell_m / 2.0, sites["site"].to_numpy()
    parts, dates_by_file, first_header = [], {}, None
    for zp in zip_paths:
        name, header = _l3_header(zp)
        dates_by_file[Path(zp).name] = tuple(_checked_dates(header, str(zp)))
        first_header = list(header.columns) if first_header is None else first_header
        with zipfile.ZipFile(zp) as zf, zf.open(name) as f:
            for chunk in pd.read_csv(f, chunksize=chunksize, dtype={"pid": str}):
                x, y = chunk["easting"].to_numpy(float), chunk["northing"].to_numpy(float)
                order = np.argsort(x, kind="stable")
                xs = x[order]
                lo, hi = np.searchsorted(xs, sx - half, side="left"), np.searchsorted(xs, sx + half, side="right")
                for k in np.nonzero(hi > lo)[0]:
                    idx = order[lo[k]:hi[k]]
                    idx = np.sort(idx[np.abs(y[idx] - sy[k]) <= half])
                    if len(idx):
                        parts.append(chunk.iloc[idx].assign(site=names[k], distance_m=np.hypot(x[idx] - sx[k], y[idx] - sy[k]),
                                                            source_file=Path(zp).name))
    # pd.concat dokleja daty nieobecne w pierwszym kaflu na koniec (za site): kolejność dat ustalana jawnie.
    dcols = sorted(set().union(*dates_by_file.values()))               # yyyymmdd: porządek tekstowy = chronologiczny
    if len(set(dates_by_file.values())) > 1:
        logger.warning(f"Pliki L3 mają różne zestawy dat (suma {len(dcols)}); brakujące daty na plik (NaN w komórkach "
                       f"tego pliku): {({f: len(dcols) - len(d) for f, d in dates_by_file.items()})}")
    attrs = [c for c in first_header if c not in set(dcols)]
    if not parts:
        logger.info(f"Żaden z {len(sites)} punktów nie leży w komórce L3")
        return pd.DataFrame(columns=attrs + dcols + L3_SITE_EXTRA)
    out = pd.concat(parts, ignore_index=True)
    n = out.groupby("site").size()
    multi = n[n > 1].index.tolist()
    if multi:
        detail = {s: out.loc[out["site"] == s, ["pid", "source_file"]].values.tolist() for s in multi}
        raise ValueError(f"Więcej niż jedna komórka L3 zawiera punkt: {detail}")
    no_cell = [s for s in names if s not in set(out["site"])]
    if no_cell:
        logger.info(f"Punkty bez komórki L3 ({len(no_cell)}): {no_cell}")
    out = out.assign(los_east=0.0, los_north=0.0, los_up=1.0, track="L3", direction="vertical")
    attrs += [c for c in out.columns if c not in set(attrs) | set(dcols) | set(L3_SITE_EXTRA)]   # kolumny spoza 1. kafla
    out = out.reindex(columns=attrs + dcols + L3_SITE_EXTRA)   # data spoza kafli z komórkami = kolumna NaN (jawnie)
    order = {s: k for k, s in enumerate(names)}
    return out.sort_values("site", key=lambda s: s.map(order)).reset_index(drop=True)


def l3_grid_offsets(cells: pd.DataFrame, cell_m: float) -> pd.DataFrame:
    """
    Kontrola konwencji na danych: reszty easting i northing modulo cell_m z liczbą komórek.
    l3_cells_at_sites zakłada, że easting/northing to środki komórek (reszta cell_m/2 przy siatce wyrównanej
    do cell_m); reszta 0 oznaczałaby narożniki i przesunięcie dopasowania o pół komórki.
    """
    _require(cells.columns, ["easting", "northing"], "cells")
    if cells.empty:
        raise ValueError("Brak komórek do kontroli siatki")
    if not np.isfinite(cell_m) or cell_m <= 0:
        raise ValueError(f"cell_m musi być dodatnie, jest {cell_m}")

    def mod(v):   # zaokrąglenie przed drugim modulo: 4 149 999.9999 -> 0, nie 100
        return (v.astype(float) % cell_m).round(2) % cell_m
    off = pd.DataFrame({"easting_mod": mod(cells["easting"]), "northing_mod": mod(cells["northing"])})
    return off.value_counts().rename("n_cells").reset_index()


# ==============================================================================
# V. MAPA PRĘDKOŚCI L2B
# ==============================================================================
def extract_l2b_velocity_map(zip_path: Path, aoi_3035: tuple, chunksize: int) -> pd.DataFrame:
    """
    Punkty pliku L2b w prostokącie EPSG:3035: pid, easting, northing, mean_velocity (prędkość LOS [mm/rok],
    ujemna = oddalanie od satelity). Sprawdzane są wszystkie kolumny L2 z step_02 (plik L3 podany omyłkowo = KeyError).
    """
    header = _csv_header(zip_path, l3_csv_name(zip_path))
    _require(header.columns, L2_REQUIRED, str(zip_path))
    return _read_rect(zip_path, L2B_MAP_COLUMNS, aoi_3035, chunksize)


# ==============================================================================
# VI. TEST OFFLINE (dane syntetyczne o znanej odpowiedzi; wartości testowe nie są wynikiem)
# ==============================================================================
def _zip_bytes(members: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for n, b in members.items():
            zf.writestr(n, b)
    return buf.getvalue()


def _synthetic_l3(prefix: str, x0: float, y0: float, nx: int, ny: int, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Siatka 100 m: środki x0 + 100 i, y0 + 100 j; prędkość -1 - 0.5 i - 0.25 j mm/rok; szereg = v * t (bez szumu)."""
    t = np.asarray((dates - dates[0]) / pd.Timedelta(days=1), float) / 365.25
    rows = []
    for i in range(nx):
        for j in range(ny):
            v = -1.0 - 0.5 * i - 0.25 * j
            rows.append({"pid": f"{prefix}_{i}_{j}", "easting": x0 + 100.0 * i, "northing": y0 + 100.0 * j,
                         "height": 5.0, "rmse": 1.0, "mean_velocity": v, "mean_velocity_std": 0.1,
                         "acceleration": 0.0, "acceleration_std": 0.0, "seasonality": 0.0, "seasonality_std": 0.0,
                         **{d.strftime("%Y%m%d"): v * tk for d, tk in zip(dates, t)}})
    return pd.DataFrame(rows)


def _synthetic_l2b(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """30 punktów na linii y = 3 350 100, x = 4 149 900 + 20 k; L2_REQUIRED + mean_velocity_std (jak L2b, F5) + daty
    (LOS = -2 mm/rok * t)."""
    k = np.arange(30)
    t = np.asarray((dates - dates[0]) / pd.Timedelta(days=1), float) / 365.25
    df = pd.DataFrame({"pid": [f"P{i:03d}" for i in k], "easting": 4_149_900.0 + 20.0 * k, "northing": 3_350_100.0,
                       "height": 3.0, "mean_velocity": -2.0, "mean_velocity_std": 0.2,
                       "los_east": -0.6, "los_north": -0.1, "los_up": 0.79,
                       "incidence_angle": np.rad2deg(np.arccos(0.79))})
    series = pd.DataFrame(np.tile(-2.0 * t, (len(k), 1)), columns=dates.strftime("%Y%m%d"), index=df.index)
    return pd.concat([df, series], axis=1)


class _FakeAoiSession:
    """Atrapa serwera EGMS: /search dla prostokąta (L2B, L3 z plikiem ORTHO-EAST) i /download z kontrolą id
    i limitu czasu; pliki z self.truncate są wysyłane bez ostatniego bajtu (przerwane pobranie)."""

    def __init__(self, files: dict):
        self.files, self.queries, self.calls, self.qid_of = files, [], [], {}
        self.bad_name, self.release_override, self.truncate = False, None, set()

    def post(self, url, headers=None, data=None):
        from step_01_ingest import _FakeResponse
        assert url.endswith("/search"), url
        q = json.loads(data)
        self.queries.append(q)
        qid, rel = f"Q{len(self.queries)}", self.release_override or q["releases"][0]
        if q["bbox"][0][0] > 20.0:
            hits = []
        elif q["levels"] == ["L2B"]:
            hits = [{"filename": n, "filesize": len(c), "release": rel, "productLevel": "L2B", "relativeOrbit": 15,
                     "direction": "ascending", "burstId": 123} for n, c in self.files.items() if n.startswith("EGMS_L2b_")]
        else:   # L3: atrapa ignoruje productType i zwraca też składową E (sprawdzenie filtra po nazwie)
            hits = [{"filename": n, "filesize": len(c), "release": rel, "productLevel": "L3"}
                    for n, c in self.files.items() if n.startswith("EGMS_L3_")]
            if self.bad_name:
                hits.append({"filename": "EGMS_L3_tile_bad.zip", "filesize": 10, "release": rel, "productLevel": "L3"})
        for h in hits:
            self.qid_of[h["filename"]] = qid
        return _FakeResponse({"id": qid, "hits": hits})

    def get(self, url, headers=None, params=None, stream=False, timeout=None):
        from step_01_ingest import _FakeResponse
        name = url.rsplit("/", 1)[-1]
        assert "/download/" in url and params == {"id": self.qid_of[name]}, (url, params)
        assert stream and timeout == HTTP_TIMEOUT_S, (stream, timeout)
        self.calls.append(name)
        return _FakeResponse(content=self.files[name][:-1] if name in self.truncate else self.files[name])


def _expect(exc, fn, *args):
    try:
        fn(*args)
    except exc as e:
        return str(e)
    raise AssertionError(f"Oczekiwano {exc.__name__} z {fn.__name__}")


def _selftest() -> None:
    from step_03_compare_gnss import compare_station_track
    import hashlib
    rel, ep = "2020-2024", "https://fake/api"
    dates = pd.date_range("2020-01-06", periods=80, freq="6D")
    t1 = _synthetic_l3("T1", 4_150_050.0, 3_350_050.0, 5, 5, dates)
    t2 = _synthetic_l3("T2", 4_200_050.0, 3_350_050.0, 3, 3, dates)
    n1, n2 = "EGMS_L3_E41N33_100km_U_2020_2024_1.zip", "EGMS_L3_E42N33_100km_U_2020_2024_1.zip"
    ne, nb = "EGMS_L3_E41N33_100km_E_2020_2024_1.zip", "EGMS_L2b_015_0123_IW2_VV_2020_2024_1.zip"
    files = {n1: _zip_bytes({n1[:-4] + ".tif": b"II*\x00fake", n1[:-4] + ".csv": t1.to_csv(index=False).encode()}),
             n2: _zip_bytes({n2[:-4] + ".tif": b"II*\x00fake", n2[:-4] + ".csv": t2.to_csv(index=False).encode()}),
             ne: _zip_bytes({ne[:-4] + ".csv": t1.to_csv(index=False).encode()}),
             nb: _zip_bytes({nb[:-4] + ".csv": _synthetic_l2b(dates).to_csv(index=False).encode()})}
    aoi = (5.8, 52.9, 7.3, 53.6)

    # 1. Zapytanie: kształt JSON, limit 5 stopni, productType tylko dla L3.
    assert bbox_query(aoi, "L3", rel, "ORTHO-UP") == {"id": None, "bbox": [[5.8, 52.9], [7.3, 53.6]], "levels": ["L3"],
                                                     "releases": [rel], "productType": "ORTHO-UP"}
    assert bbox_query(aoi, "L2B", rel, None) == {"id": None, "bbox": [[5.8, 52.9], [7.3, 53.6]], "levels": ["L2B"],
                                                "releases": [rel]}
    assert bbox_query((1.0, 50.0, 6.0, 55.0), "L2B", rel, None)["bbox"] == [[1.0, 50.0], [6.0, 55.0]]   # równo 5 x 5
    _expect(ValueError, bbox_query, (1.0, 50.0, 6.5, 51.0), "L2B", rel, None)
    _expect(ValueError, bbox_query, (1.0, 50.0, 2.0, 55.5), "L3", rel, "ORTHO-UP")
    _expect(ValueError, bbox_query, (7.3, 52.9, 5.8, 53.6), "L2B", rel, None)
    _expect(ValueError, bbox_query, aoi, "L2B", rel, "ORTHO-UP")
    _expect(ValueError, bbox_query, aoi, "L3", rel, None)
    _expect(ValueError, bbox_query, aoi, "L2A", rel, None)
    _expect(ValueError, bbox_query, aoi, "L3", "2020_2024", "ORTHO-UP")

    # 2. Wyszukanie wszystkich poziomów; plik ORTHO-EAST odrzucony po nazwie; puste wyniki i złe nazwy = wyjątek.
    s = _FakeAoiSession(files)
    table, results = search_plan(s, {"Authorization": "Bearer X"}, ep, aoi, rel, ["L2B", "L3"], ["ORTHO-UP"])
    assert s.queries == [bbox_query(aoi, "L2B", rel, None), bbox_query(aoi, "L3", rel, "ORTHO-UP")]
    assert sorted(results) == ["L2B", "L3:ORTHO-UP"] and results["L3:ORTHO-UP"]["id"] == "Q2"
    assert sorted(table["filename"]) == sorted([nb, n1, n2]) and ne not in set(table["filename"])
    assert table.set_index("filename").loc[n1, ["level", "tile", "component", "query_key"]].tolist() == \
        ["L3", "E41N33", "U", "L3:ORTHO-UP"]
    assert table.set_index("filename").loc[nb, "relativeOrbit"] == 15 and pd.isna(table.set_index("filename").loc[n1, "burstId"])
    assert sorted(h["filename"] for h in results["L3:ORTHO-UP"]["hits"]) == [n1, n2], "wynik bez plików odrzuconych"
    _expect(RuntimeError, search_aoi, s, {}, ep, (21.0, 50.0, 22.0, 51.0), "L3", rel, "ORTHO-UP")
    s.bad_name = True
    assert "niezgodne ze wzorcem" in _expect(ValueError, search_aoi, s, {}, ep, aoi, "L3", rel, "ORTHO-UP")
    s.bad_name, s.release_override = False, "2019-2023"
    _expect(ValueError, search_aoi, s, {}, ep, aoi, "L2B", rel, None)
    s.release_override = None
    table, results = search_plan(s, {}, ep, aoi, rel, ["L2B", "L3"], ["ORTHO-UP"])   # świeże id przed pobraniem

    # 3. Prostokąt EPSG:3035: zagęszczenie krawędzi; definicja EPSG:3035: (10 E, 52 N) -> (4 321 000, 3 210 000).
    x0, y0, x1, y1 = aoi_lonlat_to_3035((9.0, 52.0, 11.0, 53.0))
    cx, cy = transform_xy(np.array([9.0, 11.0, 9.0, 11.0]), np.array([52.0, 52.0, 53.0, 53.0]), 4326, 3035)
    assert abs(y0 - 3_210_000.0) < 1e-3 and y0 < min(cy) - 100.0, "minimum northing leży wewnątrz dolnej krawędzi"
    assert x0 <= min(cx) and x1 >= max(cx) and y1 >= max(cy)
    _expect(ValueError, aoi_lonlat_to_3035, (11.0, 52.0, 9.0, 53.0))

    with tempfile.TemporaryDirectory(prefix="egmscheck_aoi_") as tmp:
        proj = Path(tmp) / "proj"
        raw, man = proj / "data" / "01_Raw_EGMS" / "2020_2024", proj / "data" / "00_Metadata" / "MANIFEST.csv"
        man.parent.mkdir(parents=True)
        size = {n: len(files[n]) for n in (n1, n2, nb)}

        # 4. Plan pobrania: missing -> existing / partial; brak miejsca = RuntimeError.
        p0 = plan_download(table, raw, 10 ** 12, 0)
        assert (p0["status"] == "missing").all() and p0["local_bytes"].isna().all()
        assert int(p0["need_bytes"].sum()) == sum(size.values())
        r = sync_files(s, {}, ep, results["L3:ORTHO-UP"], [n1], raw, man, proj, 0.0, "selftest")
        assert r["status"].tolist() == ["downloaded"]
        raw.joinpath(nb + ".part").write_bytes(files[nb][: size[nb] // 2])
        p1 = plan_download(table, raw, 10 ** 12, 0).set_index("filename")
        assert p1.loc[[n1, n2, nb], "status"].tolist() == ["existing", "missing", "partial"]
        assert p1.loc[[n1, n2, nb], "need_bytes"].tolist() == [0, size[n2], size[nb]]
        raw.joinpath(n2).write_bytes(files[n2][:7])
        assert plan_download(table, raw, 10 ** 12, 0).set_index("filename").loc[n2, "status"] == "partial"
        raw.joinpath(n2).unlink()
        need = size[n2] + size[nb]
        msg = _expect(RuntimeError, plan_download, table, raw, need + 1000 - 1, 1000)
        assert "GB" in msg and "Za mało miejsca" in msg
        assert len(plan_download(table, raw, need + 1000, 1000)) == 3        # równo na granicy: wystarcza
        _expect(ValueError, plan_download, table.iloc[:0], raw, 10 ** 12, 0)
        assert drive_free_bytes(Path(tmp)) > 0

        # 5. Pobranie przyrostowe; przerwane pobranie = IOError i .part; drugie uruchomienie nie pobiera;
        #    manifest z SHA-256, bez ?id=; plik odrzucony filtrem składowej nie do pobrania; plik w manifeście
        #    nie jest nadpisywany inną treścią.
        s.truncate = {n2}
        assert "oczekiwano" in _expect(IOError, sync_files, s, {}, ep, results["L3:ORTHO-UP"], [n2], raw, man, proj, 0.0,
                                       "selftest")
        assert raw.joinpath(n2 + ".part").exists() and not raw.joinpath(n2).exists()
        assert plan_download(table, raw, 10 ** 12, 0).set_index("filename").loc[n2, "status"] == "partial"
        s.truncate = set()
        r_b = sync_files(s, {}, ep, results["L2B"], [nb], raw, man, proj, 0.0, "selftest")
        r_3 = sync_files(s, {}, ep, results["L3:ORTHO-UP"], [n1, n2], raw, man, proj, 0.0, "selftest")
        assert r_b["status"].tolist() == ["downloaded"] and r_3["status"].tolist() == ["skipped_existing", "downloaded"]
        assert not raw.joinpath(nb + ".part").exists() and not raw.joinpath(n2 + ".part").exists()
        n_get = len(s.calls)
        sync_files(s, {}, ep, results["L2B"], [nb], raw, man, proj, 0.0, "selftest")
        sync_files(s, {}, ep, results["L3:ORTHO-UP"], [n1, n2], raw, man, proj, 0.0, "selftest")
        assert len(s.calls) == n_get == 4, "drugie uruchomienie nie może pobierać"
        _expect(KeyError, sync_files, s, {}, ep, results["L3:ORTHO-UP"], ["nie_ma.zip"], raw, man, proj, 0.0, "selftest")
        _expect(KeyError, sync_files, s, {}, ep, results["L3:ORTHO-UP"], [ne], raw, man, proj, 0.0, "selftest")
        assert not raw.joinpath(ne).exists() and len(s.calls) == 4
        orig = files[nb]
        raw.joinpath(nb).write_bytes(orig[:7])                                # uszkodzona kopia lokalna
        s.files = {**files, nb: bytes(255 - b for b in orig)}                 # serwer: ta sama nazwa i rozmiar, inna treść
        assert "nie został nadpisany" in _expect(ValueError, sync_files, s, {}, ep, results["L2B"], [nb], raw, man, proj,
                                                 0.0, "selftest")
        assert raw.joinpath(nb).read_bytes() == orig[:7]
        s.files = files
        assert sync_files(s, {}, ep, results["L2B"], [nb], raw, man, proj, 0.0, "selftest")["status"].tolist() == ["downloaded"]
        assert raw.joinpath(nb).read_bytes() == orig and not raw.joinpath(nb + ".part").exists()
        m = pd.read_csv(man, dtype=str).set_index("file_path")
        assert list(m.reset_index().columns) == MANIFEST_COLUMNS and len(m) == 3
        for n in (n1, n2, nb):
            row = m.loc[f"data/01_Raw_EGMS/2020_2024/{n}"]
            assert row["sha256"] == hashlib.sha256(files[n]).hexdigest() and row["egms_release"] == rel
            assert "?id=" not in row["source_url"] and row["source_url"] == f"{ep}/download/{n}"
        assert m.loc[f"data/01_Raw_EGMS/2020_2024/{nb}", "what"] == "EGMS L2B track 15 ascending burst 123"
        assert m.loc[f"data/01_Raw_EGMS/2020_2024/{n1}", "what"] == "EGMS L3 tile E41N33 component U"
        p3 = plan_download(table, raw, 0, 0)
        assert (p3["status"] == "existing").all() and int(p3["need_bytes"].sum()) == 0

        # 6. Czytnik L3: jedyny CSV obok .tif; mapa w prostokącie (granice włącznie); daty; brak kolumny = KeyError.
        z1, z2, zb = raw / n1, raw / n2, raw / nb
        assert l3_csv_name(z1) == n1[:-4] + ".csv"
        two = Path(tmp) / "two.zip"
        two.write_bytes(_zip_bytes({"a.csv": b"x", "b.csv": b"y"}))
        _expect(ValueError, l3_csv_name, two)
        two.write_bytes(_zip_bytes({"a.tif": b"x"}))
        _expect(ValueError, l3_csv_name, two)
        rect = (4_150_000.0, 3_350_000.0, 4_150_250.0, 3_350_150.0)          # i = 0..2 (250 włącznie), j = 0..1
        mp = read_l3_aoi(z1, rect, 4, False)
        assert list(mp.columns) == L3_MAP_COLUMNS and sorted(mp["pid"]) == sorted(f"T1_{i}_{j}" for i in range(3) for j in range(2))
        assert np.allclose(mp.set_index("pid").loc["T1_2_1", "mean_velocity"], -1.0 - 1.0 - 0.25)
        md = read_l3_aoi(z1, rect, 7, True)
        dcols = [c for c in md.columns if DATE_COL.match(c)]
        assert len(md) == 6 and list(md.columns[:5]) == L3_MAP_COLUMNS and len(dcols) == len(dates) == len(md.columns) - 5
        assert len(read_l3_aoi(z1, (0.0, 0.0, 10.0, 10.0), 4, False)) == 0
        off = l3_grid_offsets(read_l3_aoi(z1, (4e6, 3e6, 5e6, 4e6), 10, False), 100.0)
        assert off[["easting_mod", "northing_mod", "n_cells"]].values.tolist() == [[50.0, 50.0, 25]]
        wrap = l3_grid_offsets(pd.DataFrame({"easting": [4_149_999.9999], "northing": [3_350_050.0]}), 100.0)
        assert wrap[["easting_mod", "northing_mod"]].values.tolist() == [[0.0, 50.0]]
        bad = Path(tmp) / "bad_l3.zip"
        bad.write_bytes(_zip_bytes({"c.csv": t1.drop(columns="mean_velocity_std").to_csv(index=False).encode()}))
        assert "mean_velocity_std" in _expect(KeyError, read_l3_aoi, bad, rect, 4, False)
        assert "plik L2" in _expect(ValueError, read_l3_aoi, zb, rect, 4, False)          # L2b ma też L3_REQUIRED
        rev = t1[[c for c in t1.columns if not DATE_COL.match(c)] + [c for c in t1.columns if DATE_COL.match(c)][::-1]]
        bad.write_bytes(_zip_bytes({"c.csv": rev.to_csv(index=False).encode()}))
        assert "nie rosną" in _expect(ValueError, read_l3_aoi, bad, rect, 4, True)

        # 7. Komórka przy punkcie: dwa kafle, punkt spoza siatki bez wiersza, punkt na granicy dwóch komórek = ValueError.
        sites = pd.DataFrame({"site": ["SITE_A", "SITE_B", "SITE_OUT"],
                              "x_3035": [4_150_250.0 + 20.0, 4_200_150.0 - 45.0, 4_000_000.0],
                              "y_3035": [3_350_350.0 - 30.0, 3_350_050.0 + 10.0, 3_000_000.0]})
        cells = l3_cells_at_sites([z1, z2], sites, 100.0, 4)
        assert cells["site"].tolist() == ["SITE_A", "SITE_B"] and cells["pid"].tolist() == ["T1_2_3", "T2_1_0"]
        assert cells["source_file"].tolist() == [n1, n2]
        assert np.allclose(cells["distance_m"], [np.hypot(20, 30), np.hypot(45, 10)])
        assert (cells[["los_east", "los_north", "los_up"]].to_numpy() == [0.0, 0.0, 1.0]).all()
        assert set(cells["track"]) == {"L3"} and set(cells["direction"]) == {"vertical"}
        assert l3_cells_at_sites([z2], sites.iloc[[2]], 100.0, 4).empty
        edge = pd.DataFrame({"site": ["SITE_EDGE"], "x_3035": [4_150_100.0], "y_3035": [3_350_050.0]})
        assert "Więcej niż jedna komórka" in _expect(ValueError, l3_cells_at_sites, [z1], edge, 100.0, 3)
        _expect(ValueError, l3_cells_at_sites, [z1], sites.iloc[:0], 100.0, 4)
        assert "Powtórzone pliki" in _expect(ValueError, l3_cells_at_sites, [z1, z1], sites, 100.0, 4)
        ze = Path(tmp) / ne                                                    # kafel E: te same kolumny, inna składowa
        ze.write_bytes(files[ne])
        assert "tylko dla U" in _expect(ValueError, l3_cells_at_sites, [z1, ze], sites, 100.0, 4)
        assert "tylko dla U" in _expect(ValueError, l3_cells_at_sites, [zb], sites, 100.0, 4)
        # Kafel o rzadszych datach podany jako pierwszy: daty wyniku ściśle rosnące, NaN tylko w datach spoza kafla.
        n3 = "EGMS_L3_E42N34_100km_U_2020_2024_1.zip"
        t3 = _synthetic_l3("T3", 4_200_050.0, 3_400_050.0, 2, 2, dates)
        t3 = t3.drop(columns=dates[1::2].strftime("%Y%m%d"))
        z3 = Path(tmp) / n3
        z3.write_bytes(_zip_bytes({n3[:-4] + ".csv": t3.to_csv(index=False).encode()}))
        sc = pd.DataFrame({"site": ["SITE_C", "SITE_A"], "x_3035": [4_200_160.0, sites["x_3035"].iat[0]],
                           "y_3035": [3_400_040.0, sites["y_3035"].iat[0]]})
        mixed = l3_cells_at_sites([z3, z1], sc, 100.0, 4)
        dm = date_columns(mixed)
        assert dm == list(dates.strftime("%Y%m%d")) and list(mixed.columns[-len(L3_SITE_EXTRA):]) == L3_SITE_EXTRA
        mx = mixed.set_index("site")
        assert mx.loc["SITE_C", "pid"] == "T3_1_0" and mx.loc["SITE_A", "pid"] == "T1_2_3"
        assert mx.loc["SITE_C", dm].isna().tolist() == [k % 2 == 1 for k in range(len(dates))]
        assert mx.loc["SITE_A", dm].notna().all()
        only_c = l3_cells_at_sites([z3, z1], sc.iloc[[0]], 100.0, 4)          # komórka tylko z kafla o rzadszych datach
        assert date_columns(only_c) == dm and only_c[dm].iloc[0].isna().tolist() == [k % 2 == 1 for k in range(len(dates))]

        # 8. Komórka L3 przez step_03.compare_station_track bez zmian: GNSS z dużym E i N, U = v t -> dv = 0.
        v_a = -1.0 - 0.5 * 2 - 0.25 * 3
        days = pd.date_range(dates[0] - pd.Timedelta(days=30), dates[-1] + pd.Timedelta(days=30), freq="D")
        tg = np.asarray((days - dates[0]) / pd.Timedelta(days=1), float) / 365.25
        gnss = pd.DataFrame({"date": days, "e_mm": 30.0 * tg + 5.0, "n_mm": -20.0 * tg, "u_mm": v_a * tg})
        dc = date_columns(cells)
        res = compare_station_track(cells[cells["site"] == "SITE_A"], dc, gnss, 100.0 * np.sqrt(2) / 2,
                                    {"min_points": 1, "gnss_half_window_days": 6, "velocity_model": "linear",
                                     "min_overlap": 0.85})
        assert res["status"] == "ok" and res["n_points"] == 1 and res["los_up"] == 1.0 and res["meets_A6"]
        assert abs(res["v_egms"] - v_a) < 1e-9 and abs(res["dv"]) < 1e-9, res

        # 9. Mapa L2b i zgodność pobranego L2b z wycinkiem E1 (step_02.extract_points).
        lm = extract_l2b_velocity_map(zb, (4_150_000.0, 3_350_000.0, 4_150_220.0, 3_350_200.0), 7)
        assert list(lm.columns) == L2B_MAP_COLUMNS and lm["pid"].tolist() == [f"P{k:03d}" for k in range(5, 17)]
        assert "los_east" in _expect(KeyError, extract_l2b_velocity_map, z1, rect, 4)
        ex = extract_points(zb, pd.DataFrame({"site": ["S"], "x_3035": [4_150_100.0], "y_3035": [3_350_100.0]}), 50.0, 7)
        assert len(ex) == 5
    print("SELFTEST step_04_egms_aoi OK")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    ap = argparse.ArgumentParser(description="EGMS Check - KROK 4")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        _selftest()
    else:
        ap.print_help()
