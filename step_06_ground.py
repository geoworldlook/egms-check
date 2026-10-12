"""
================================================================================
EGMS Check - KROK 6: POMIARY NAZIEMNE: STACJE GNSS W OBSZARZE I NIWELACJA NRW
================================================================================
Pomiar naziemny dla pokazu EGMS 2020-2024 (docs/plans/Plan_v2_implementacja.md, sekcja 4.2):

  I.   Stacje GNSS w obszarze, reguła 'all_quality': wszystkie stacje NGL (prędkości MIDAS z
       step_01.read_ngl_midas) w prostokącie obszaru, spełniające warunki jakości identyczne z
       step_01.select_stations (dane w oknie, niepewność vu, liczba skoków), bez warunku prędkości.
       Grupy według vu: 'osiadająca' / 'stabilna' / 'inna'. Brak stacji nie jest błędem (GNSS „jeśli są").
  II.  Niwelacja NRW (Geobasis NRW, Höhenfestpunkte): czytniki „Punktliste" i „Punktliste mit Zeitfolge"
       (CSV, ';', przecinek dziesiętny, daty dd.mm.rrrr, wysokości DHHN2016 w m; F5, sekcja 5).
       Czytniki niczego nie zgadują: brak kolumny, zła liczba lub data, duplikat = wyjątek z przykładami.
  III. Format długi niwelacji (EPSG:3035 i WGS84, tylko repery w obszarze) i epoki w oknie wydania EGMS
       (reguła 'first_last_in_release': pierwsza i ostatnia epoka w oknie, odstęp >= minimum); reper bez
       pary epok zostaje w tabeli ze statusem, nie znika.
  IV.  Porównanie z EGMS pion (format długi, Plan_v2 sekcja 2.2): Δh niwelacji i EGMS między epokami reperu,
       bez odniesienia ('absolute') albo względem grupy stabilnej ('stable_group': średnia Δh grupy w tych
       samych epokach odjęta od obu zbiorów). Odczyt w epoce: interpolacja liniowa, bez ekstrapolacji.
       Logika przeniesiona z prototypu (read_at_epochs, run_e2, summarize_e2, robust_stats).
  V.   EGMS L2b -> pion: rozkład szeregów LOS z orbity wstępującej i zstępującej na (E, U) przy założeniu
       braku ruchu północ-południe (Wright i in. 2004; MintPy asc_desc2horz_vert, horz_az_angle = -90).
  VI.  Kryteria jak T2 (Plan_v1_kryteria_akceptacji.md, sekcja C) + bias prędkości; mediana i MAD x 1,4826.
       Informacyjnie (bez progów; autor 2026-10-12): podział reperów na niecki (|v_niw| >= próg z konfiguracji)
       i pozostałe oraz odległość reperu do najbliższej stacji GNSS (sieć NGL z pliku MIDAS) - czy zgodność EGMS
       z niwelacją zależy od bliskości stacji GNSS, którymi kalibrowany jest L2b/L3.
  VII. --selftest bez sieci, na danych syntetycznych o znanej odpowiedzi; --describe-nrw (opis plików NRW).

Literatura: Even, Westerhaus, Kutterer 2024 (EGMS kontra niwelacja NRW, rozdz. 4.3; mediana, MAD x 1,4826);
Koudogbo i in. 2025 (walidacja EGMS, MAE < 5 mm); Wright, Parsons, Lu 2004 (GRL 31, L01607: składowe ruchu
z kilku geometrii LOS); Blewitt i in. 2016 (MIDAS). Dane: docs/evidence/F5_zrodla_danych.md (sekcje 2 i 5),
docs/evidence/F6_przypadki_zapasowe/zapas_nrw_niwelacja.md.

Konwencje: przemieszczenia i Δh w mm, prędkości w mm/rok, ujemne = osiadanie / oddalanie od satelity.
Układy: EGMS EPSG:3035, GNSS stopnie WGS84, niwelacja NRW w crs_epsg z konfiguracji (prawdopodobnie
EPSG:25832, do potwierdzenia w Datenformatbeschreibung.pdf). Wysokości DHHN2016 i EGMS (ETRF2000)
porównujemy wyłącznie jako różnice między epokami. Parametry eksperymentu (obszar, okno wydania, reguła epok,
odniesienie, sposób odczytu, progi) pochodzą z CHECK_CONFIG; sygnatury nie mają wartości domyślnych.
================================================================================
"""

import argparse
import csv
import re
import io
import json
import tempfile
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from step_03_compare_gnss import DAYS_PER_YEAR, years_since

MM_PER_M = 1000.0
MAD_TO_SIGMA = 1.4826                   # MAD -> odchylenie przy rozkładzie normalnym (Even i in. 2024)
READ_METHODS = ("linear_interpolation",)
EPOCH_RULES = ("first_last_in_release",)
REFERENCE_TYPES = ("absolute", "stable_group")

MIDAS_NEED = ["site", "t_first", "t_last", "vu_mm_yr", "svu_mm_yr", "n_steps", "lat_deg", "lon_deg"]
SITE_COLUMNS = ["site", "site_type", "group", "lat_deg", "lon_deg", "x_3035", "y_3035", "t_first", "t_last",
                "vu_mm_yr", "svu_mm_yr", "n_steps", "source"]
GNSS_SITE_SOURCE = "GNSS_NGL"
LEVELLING_SOURCE = "LEVELLING_NRW"

# Format plików Geobasis NRW (F5, sekcja 5; zapas_nrw_niwelacja.md). Kodowanie znaków podaje konfiguracja.
NRW_SEP = ";"
NRW_DATE_FORMAT = "%d.%m.%Y"
NRW_NUMBER = r"[+-]?\d+(?:,\d*)?"       # przecinek dziesiętny, bez separatora tysięcy; "32428124," (sam przecinek)
                                         # występuje w przykładzie Datenformatbeschreibung HFP NRW (07/2023)
NRW_POINT_COLUMNS = ["Punktkennzeichen", "Name des Punktes", "Ostwert", "Nordwert", "Höhe", "Schwerewert"]
NRW_SERIES_COLUMNS = ["Punktkennzeichen", "Messungsdatum", "Höhe"]

LEV_COLUMNS = ["benchmark_id", "x_3035", "y_3035", "lat_deg", "lon_deg", "epoch_date", "height_m"]
EPOCH_COLUMNS = ["benchmark_id", "t1", "t2", "span_yr", "n_epochs_total", "n_epochs_in_release", "status"]
EGMS_U_NEED = ["site", "component", "date", "disp_mm"]
COMPARE_COLUMNS = ["benchmark_id", "t1", "t2", "dt_yr", "dh_lev_mm", "dh_egms_mm", "diff_mm", "v_lev_mm_yr",
                   "v_egms_dh_mm_yr", "ref_dh_lev_mm", "ref_dh_egms_mm", "reference", "status"]
SUMMARY_COLUMNS = ["kryterium", "wynik", "próg", "spełnione", "n"]
THRESHOLD_KEYS = ["median_abs_dh_mm", "sign_min_signal_mm", "sign_agreement", "stable_max_lev_mm",
                  "stable_abs_dh_mm", "velocity_bias_mm_yr"]


# ==============================================================================
# 0. POMOCNICZE: PARAMETRY, KOLUMNY, UKŁADY WSPÓŁRZĘDNYCH
# ==============================================================================
def _require(name: str, value):
    """Parametr eksperymentu musi mieć wartość; None = decyzja autora nieustalona (CLAUDE.md, zasada 2)."""
    if value is None:
        raise ValueError(f"Parametr '{name}' = None: decyzja autora nieustalona (CHECK_CONFIG).")
    return value


def _require_columns(df: pd.DataFrame, cols: list, what: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"{what}: brak kolumn {missing}; dostępne: {list(df.columns)}")


def _check_aoi(aoi_lonlat) -> tuple:
    """Prostokąt (lon_min, lat_min, lon_max, lat_max) w stopniach WGS84."""
    lo0, la0, lo1, la1 = (float(v) for v in _require("aoi_lonlat", aoi_lonlat))
    if not (lo0 < lo1 and la0 < la1):
        raise ValueError(f"aoi_lonlat {aoi_lonlat}: oczekiwano (lon_min, lat_min, lon_max, lat_max)")
    return lo0, la0, lo1, la1


def _inside(lon: pd.Series, lat: pd.Series, aoi: tuple) -> pd.Series:
    lo0, la0, lo1, la1 = aoi
    return lon.between(lo0, lo1) & lat.between(la0, la1)


def _require_valid(df: pd.DataFrame, date_col: str, num_cols: list, what: str) -> None:
    """Data bez braków i liczby skończone; inaczej ValueError (brak wartości nie może dać wyniku 'ok')."""
    if df[date_col].isna().any():
        raise ValueError(f"{what}: {int(df[date_col].isna().sum())} wierszy bez daty w kolumnie {date_col}")
    for c in num_cols:
        bad = ~np.isfinite(df[c].to_numpy(float))
        if bad.any():
            raise ValueError(f"{what}: {int(bad.sum())} wartości nieskończonych lub NaN w kolumnie {c}")


def _no_duplicates(df: pd.DataFrame, keys: list, what: str) -> None:
    dup = df.duplicated(keys, keep=False)
    if dup.any():
        ex = df.loc[dup, keys].drop_duplicates().head(5).astype(str).to_dict("records")
        raise ValueError(f"{what}: {int(dup.sum())} wierszy ze zdublowanym kluczem {keys}, np. {ex}")


# Przeniesione z prototypes/egms_simple_check.py (transform_xy), zachowanie bez zmian.
def transform_xy(x, y, epsg_from: int, epsg_to: int):
    """Przeliczenie współrzędnych (pyproj, kolejność x/y zawsze lon/lat lub easting/northing)."""
    from pyproj import Transformer
    tr = Transformer.from_crs(epsg_from, epsg_to, always_xy=True)
    return tr.transform(x, y)


# ==============================================================================
# I. STACJE GNSS W OBSZARZE (reguła 'all_quality')
# ==============================================================================
def _empty_sites() -> pd.DataFrame:
    num = {"lat_deg", "lon_deg", "x_3035", "y_3035", "t_first", "t_last", "vu_mm_yr", "svu_mm_yr", "n_steps"}
    return pd.DataFrame({c: pd.Series(dtype=float if c in num else object) for c in SITE_COLUMNS})


def select_stations_aoi(midas: pd.DataFrame, aoi_lonlat: tuple, t_first_max: float, t_last_min: float,
                        svu_max_mm_yr: float, max_steps: int, vu_subsiding_max: float,
                        vu_stable_abs_max: float) -> pd.DataFrame:
    """
    Reguła 'all_quality' (Plan_v2, sekcja 4.2): wszystkie stacje w aoi_lonlat spełniające warunki jakości
    identyczne z step_01.select_stations: t_first <= t_first_max, t_last >= t_last_min, svu <= svu_max_mm_yr,
    n_steps <= max_steps. Bez warunku prędkości; grupa według vu (MIDAS, mm/rok):
      'osiadająca': vu <= vu_subsiding_max;  'stabilna': |vu| <= vu_stable_abs_max;  'inna': pozostałe.
    Progi, przy których grupy nachodzą na siebie, = ValueError. Wynik w formacie punktów naziemnych
    (Plan_v2, sekcja 2.1) + kolumny MIDAS. Zero stacji = pusta tabela z kolumnami i komunikat, nie wyjątek
    (autor: GNSS „jeśli są").
    """
    _require_columns(midas, MIDAS_NEED, "MIDAS")
    for name, v in (("t_first_max", t_first_max), ("t_last_min", t_last_min), ("svu_max_mm_yr", svu_max_mm_yr),
                    ("max_steps", max_steps), ("vu_subsiding_max", vu_subsiding_max),
                    ("vu_stable_abs_max", vu_stable_abs_max)):
        _require(name, v)
    aoi = _check_aoi(aoi_lonlat)
    if vu_subsiding_max >= -vu_stable_abs_max:
        raise ValueError(f"Grupy nachodzą na siebie: vu_subsiding_max {vu_subsiding_max} >= "
                         f"-vu_stable_abs_max {-vu_stable_abs_max} mm/rok")
    inside = _inside(midas["lon_deg"], midas["lat_deg"], aoi)
    c_first, c_last = midas["t_first"] <= t_first_max, midas["t_last"] >= t_last_min
    c_svu, c_steps = midas["svu_mm_yr"] <= svu_max_mm_yr, midas["n_steps"] <= max_steps
    q = c_first & c_last & c_svu & c_steps                       # jak step_01.select_stations
    print(f"Stacje GNSS w obszarze {aoi}: {int(inside.sum())}; od <= {t_first_max}: {int((inside & c_first).sum())}; "
          f"do >= {t_last_min}: {int((inside & c_last).sum())}; svu <= {svu_max_mm_yr} mm/rok: "
          f"{int((inside & c_svu).sum())}; skoki <= {max_steps}: {int((inside & c_steps).sum())}; "
          f"wszystkie warunki: {int((inside & q).sum())}")
    sel = midas[inside & q].copy()
    if sel.empty:
        print("Brak stacji GNSS spełniających regułę 'all_quality' w obszarze: porównanie z GNSS nie będzie "
              "liczone (GNSS „jeśli są\").")
        return _empty_sites()
    vu = sel["vu_mm_yr"]
    if not np.isfinite(vu.to_numpy(float)).all():                # NaN trafiłby po cichu do grupy 'inna'
        raise ValueError(f"MIDAS: vu bez wartości dla stacji {sel.loc[~np.isfinite(vu), 'site'].tolist()}")
    sel["group"] = np.select([vu <= vu_subsiding_max, vu.abs() <= vu_stable_abs_max], ["osiadająca", "stabilna"],
                             "inna")
    x, y = transform_xy(sel["lon_deg"].to_numpy(float), sel["lat_deg"].to_numpy(float), 4326, 3035)
    sel = sel.assign(x_3035=x, y_3035=y, site_type="gnss", source=GNSS_SITE_SOURCE)
    print("Grupy stacji GNSS:", sel["group"].value_counts().to_dict())
    return sel[SITE_COLUMNS].sort_values(["group", "vu_mm_yr"]).reset_index(drop=True)


# ==============================================================================
# II. NIWELACJA NRW: CZYTNIKI
# ==============================================================================
def _read_nrw_csv(path: Path, encoding: str, columns: list, what: str, free_text: str | None) -> pd.DataFrame:
    """
    CSV Geobasis NRW jako tekst (moduł csv, bez konwersji i bez zgadywania przez pandas). Zwraca tylko kolumny
    `columns` (inne kolumny pliku są pomijane), wartości bez spacji na brzegach.
    Nagłówki: bez spacji i cudzysłowów na brzegach, w normalizacji Unicode NFC (litera „o" + znak łączący U+0308
    = „ö", więc „Höhe" pasuje niezależnie od zapisu); BOM na początku pliku usuwany jawnie. Głośno: wiersz z inną
    liczbą pól niż nagłówek (np. średnik na końcu wierszy danych - pandas przesunąłby wtedy po cichu kolumny
    o jedną), błędne cudzysłowy, zdublowana nazwa kolumny, brak kolumny (KeyError z listą dostępnych), brak
    wierszy danych, pusty Punktkennzeichen. Puste linie są pomijane.
    `free_text`: nazwa jedynej kolumny tekstowej w cudzysłowach (Punktliste: "Name des Punktes"; Zeitfolge: None).
    Rekord, którego moduł csv nie przyjmie (cudzysłów wewnątrz nazwy, np. "Kirche "St. Marien"" - w pliku bez
    podwojenia), jest rozbierany wg Datenformatbeschreibung: pola przed i po `free_text` nie zawierają średnika,
    więc dzieli się je od lewej i od prawej, a środek (otoczony cudzysłowami) to nazwa z cudzysłowami w środku
    bez zmian. Każdy taki rekord jest wypisany (linia, nazwa); rekord, który nie pasuje do tej struktury = ValueError.
    """
    with open(path, newline="", encoding=_require("encoding", encoding)) as f:
        text = f.read().removeprefix("\ufeff")
    k_text = None if free_text is None else columns.index(free_text)
    rows, rebuilt = [], []
    for ln, line in enumerate(text.splitlines(), start=1):   # rekord = linia (format HFP nie ma pól wieloliniowych)
        if not line.strip():
            continue
        try:
            r = next(csv.reader([line], delimiter=NRW_SEP, quotechar='"', skipinitialspace=True, strict=True))
        except csv.Error as e:
            if k_text is None:
                raise ValueError(f"{path} ({what}): błędny CSV w linii {ln}: {e}: {line[:120]!r}") from e
            r = _split_around_text(line, k_text, len(columns))
            if r is None:
                raise ValueError(f"{path} ({what}): błędny CSV w linii {ln} ({e}) i rekord nie pasuje do struktury "
                                 f"{columns} z polem tekstowym '{free_text}': {line[:120]!r}") from e
            rebuilt.append((ln, r[k_text]))
        rows.append((ln, r))
    if rebuilt:
        print(f"{path.name} ({what}): {len(rebuilt)} rekordów z cudzysłowem wewnątrz pola '{free_text}' rozebranych "
              f"wg struktury formatu (nazwa bez zmian; kolumna nieużywana w obliczeniach), np. {rebuilt[:5]}")
    if not rows:
        raise ValueError(f"{path} ({what}): plik pusty")
    # Datenformatbeschreibung HFP NRW (07/2023): pliki BEZ wiersza nagłówka, kolumny opisane kolejnością (= columns).
    # Rozpoznanie jawne: pierwsze pole "Punktkennzeichen" -> nagłówek; pierwsze pole z samych cyfr i liczba pól równa
    # len(columns) -> bez nagłówka (nazwy kolumn z kolejności); inaczej ValueError (bez zgadywania).
    first = [unicodedata.normalize("NFC", c).strip().strip('"').strip() for c in rows[0][1]]
    if first and first[0] == "Punktkennzeichen":
        header, data = first, rows[1:]
    elif first and re.fullmatch(r"\d+", first[0]) and len(first) == len(columns):
        header, data = list(columns), rows
    else:
        raise ValueError(f"{path} ({what}): pierwszy wiersz nie jest ani nagłówkiem, ani rekordem w formacie HFP NRW "
                         f"({len(columns)} pól, Punktkennzeichen z cyfr): {rows[0][1][:6]}")
    dup = sorted({c for c in header if header.count(c) > 1})
    if dup:
        raise ValueError(f"{path} ({what}): zdublowane nazwy kolumn {dup} w nagłówku {header}")
    bad = [(ln, len(r)) for ln, r in data if len(r) != len(header)]
    if bad:
        raise ValueError(f"{path} ({what}): {len(bad)} wierszy z liczbą pól różną od nagłówka ({len(header)}), "
                         f"np. (linia, pola) {bad[:5]} - średnik na końcu wiersza albo pole bez cudzysłowu?")
    df = pd.DataFrame([r for _, r in data], columns=header, dtype=object)
    _require_columns(df, columns, f"{path} ({what})")
    if df.empty:
        raise ValueError(f"{path} ({what}): brak wierszy danych")
    df = df[columns].apply(lambda s: s.str.strip())
    empty_id = df["Punktkennzeichen"] == ""
    if empty_id.any():
        lines = [data[k][0] for k in np.flatnonzero(empty_id.to_numpy())[:5]]
        raise ValueError(f"{path} ({what}): {int(empty_id.sum())} wierszy bez Punktkennzeichen, np. linie {lines}")
    return df


def _split_around_text(line: str, k_text: int, n_fields: int) -> list | None:
    """
    Rekord HFP z jednym polem tekstowym na pozycji `k_text`: k_text pól przed nim i n_fields-k_text-1 po nim
    (liczby, daty, Punktkennzeichen - bez średnika; bez cudzysłowu albo całe w cudzysłowach). Zwraca listę pól albo None, gdy linia nie ma
    tej struktury (za mało średników, cudzysłów poza polem tekstowym, pole tekstowe bez cudzysłowów na brzegach).
    """
    n_after = n_fields - k_text - 1
    head = line.split(NRW_SEP, k_text) if k_text else [line]
    if len(head) != k_text + 1:
        return None
    tail = head[-1].rsplit(NRW_SEP, n_after) if n_after else [head[-1]]
    if len(tail) != n_after + 1:
        return None
    def plain(f: str) -> str | None:                 # pole bez cudzysłowu albo całe w cudzysłowach, bez nich w środku
        f = f.strip()
        if len(f) >= 2 and f[0] == f[-1] == '"':
            f = f[1:-1]
        return None if '"' in f else f
    before, mid = [plain(f) for f in head[:-1]], tail[0].strip()
    after = [plain(f) for f in tail[1:]]
    if None in before + after or len(mid) < 2 or not (mid.startswith('"') and mid.endswith('"')):
        return None
    return before + [mid[1:-1]] + after


def _parse_decimal_comma(s: pd.Series, what: str) -> pd.Series:
    """Liczba z przecinkiem dziesiętnym; pusta lub inna wartość = ValueError z przykładami (bez zamiany na NaN)."""
    bad = ~s.str.fullmatch(NRW_NUMBER)
    if bad.any():
        raise ValueError(f"{what}: {int(bad.sum())} wartości nie jest liczbą z przecinkiem dziesiętnym, "
                         f"np. {s[bad].head(5).tolist()!r}")
    return s.str.replace(",", ".", regex=False).astype(float)


def _parse_dates(s: pd.Series, what: str) -> pd.Series:
    """Data dd.mm.rrrr; pusta lub inna wartość = ValueError z przykładami."""
    d = pd.to_datetime(s, format=NRW_DATE_FORMAT, errors="coerce")
    bad = d.isna()
    if bad.any():
        raise ValueError(f"{what}: {int(bad.sum())} wartości nie jest datą dd.mm.rrrr, np. {s[bad].head(5).tolist()!r}")
    return d


def read_nrw_points(path: Path, encoding: str) -> pd.DataFrame:
    """
    Höhenfestpunkt - Punktliste: Punktkennzeichen; Name des Punktes; Ostwert; Nordwert; Höhe; Schwerewert.
    Kolumny NRW_POINT_COLUMNS (nazwy jak w pliku, inne kolumny pomijane); Punktkennzeichen jako tekst
    (zera wiodące zostają); Ostwert, Nordwert [m, crs_epsg]
    i Höhe [m, DHHN2016] jako liczby. Name des Punktes i Schwerewert zostają tekstem (nieużywane w obliczeniach).
    Brak kolumny = KeyError z listą dostępnych; zła liczba = ValueError; zdublowany reper = ValueError.
    """
    df = _read_nrw_csv(path, encoding, NRW_POINT_COLUMNS, "Punktliste", "Name des Punktes")
    for c in ("Ostwert", "Nordwert", "Höhe"):
        df[c] = _parse_decimal_comma(df[c], f"{path}: kolumna {c}")
    _no_duplicates(df, ["Punktkennzeichen"], f"{path} (Punktliste)")
    return df.reset_index(drop=True)


def read_nrw_timeseries(path: Path, encoding: str) -> pd.DataFrame:
    """
    Höhenfestpunkt - Punktliste mit Zeitfolge: Punktkennzeichen; Messungsdatum (dd.mm.rrrr); Höhe [m, DHHN2016].
    Jeden wiersz na reper i datę; zdublowana para (reper, data) = ValueError; zła data lub liczba = ValueError.
    """
    df = _read_nrw_csv(path, encoding, NRW_SERIES_COLUMNS, "Punktliste mit Zeitfolge", None)
    df["Messungsdatum"] = _parse_dates(df["Messungsdatum"], f"{path}: kolumna Messungsdatum")
    df["Höhe"] = _parse_decimal_comma(df["Höhe"], f"{path}: kolumna Höhe")
    _no_duplicates(df, ["Punktkennzeichen", "Messungsdatum"], f"{path} (Zeitfolge)")
    return df.sort_values(["Punktkennzeichen", "Messungsdatum"]).reset_index(drop=True)


# ==============================================================================
# III. FORMAT DŁUGI NIWELACJI I EPOKI W OKNIE WYDANIA
# ==============================================================================
def levelling_long(points: pd.DataFrame, series: pd.DataFrame, crs_epsg: int, aoi_lonlat: tuple) -> pd.DataFrame:
    """
    Szereg wysokości + współrzędne reperu -> format długi: benchmark_id, x_3035, y_3035, lat_deg, lon_deg,
    epoch_date, height_m. Ostwert/Nordwert z crs_epsg do EPSG:3035 i WGS84 (pyproj, always_xy).
    Tylko repery w aoi_lonlat. Głośno: reper z szeregu bez współrzędnych w Punktliste, współrzędne
    nieprzeliczalne (np. Ostwert z prefiksem strefy UTM „32") albo zero reperów w obszarze = ValueError.
    """
    _require_columns(points, ["Punktkennzeichen", "Ostwert", "Nordwert"], "Punktliste")
    _require_columns(series, ["Punktkennzeichen", "Messungsdatum", "Höhe"], "Punktliste mit Zeitfolge")
    crs = int(_require("crs_epsg", crs_epsg))
    aoi = _check_aoi(aoi_lonlat)
    _no_duplicates(points, ["Punktkennzeichen"], "Punktliste")
    _no_duplicates(series, ["Punktkennzeichen", "Messungsdatum"], "Punktliste mit Zeitfolge")
    _require_valid(series, "Messungsdatum", ["Höhe"], "Punktliste mit Zeitfolge")
    ids = pd.Index(series["Punktkennzeichen"].unique())
    no_xy = ids.difference(pd.Index(points["Punktkennzeichen"]))
    if len(no_xy):
        raise ValueError(f"{len(no_xy)} reperów z szeregu nie ma w Punktliste (brak współrzędnych), "
                         f"np. {list(no_xy[:5])}")
    xy = points.set_index("Punktkennzeichen").loc[ids, ["Ostwert", "Nordwert"]]
    e, n = xy["Ostwert"].to_numpy(float), xy["Nordwert"].to_numpy(float)
    x3, y3 = transform_xy(e, n, crs, 3035)
    lon, lat = transform_xy(e, n, crs, 4326)
    bad = ~(np.isfinite(x3) & np.isfinite(y3) & np.isfinite(lon) & np.isfinite(lat))
    if bad.any():
        raise ValueError(f"{int(bad.sum())} reperów ma współrzędne nieprzeliczalne z EPSG:{crs}, np. "
                         f"{xy[bad].head(5).reset_index().to_dict('records')} (prefiks strefy UTM? zły crs_epsg?)")
    pts = pd.DataFrame({"benchmark_id": ids.astype(str), "x_3035": x3, "y_3035": y3, "lat_deg": lat, "lon_deg": lon})
    keep = _inside(pts["lon_deg"], pts["lat_deg"], aoi)
    if not keep.any():
        raise ValueError(f"Żaden z {len(pts)} reperów nie leży w obszarze {aoi}; zakres lon "
                         f"{pts['lon_deg'].min():.4f}-{pts['lon_deg'].max():.4f}, lat {pts['lat_deg'].min():.4f}-"
                         f"{pts['lat_deg'].max():.4f} (sprawdź crs_epsg i aoi_lonlat)")
    out = (series.rename(columns={"Punktkennzeichen": "benchmark_id", "Messungsdatum": "epoch_date", "Höhe": "height_m"})
           .astype({"benchmark_id": str}).merge(pts[keep], on="benchmark_id", how="inner"))
    print(f"Niwelacja: {len(pts)} reperów w szeregu, {int(keep.sum())} w obszarze, {len(out)} epok, "
          f"daty {out['epoch_date'].min().date()} - {out['epoch_date'].max().date()}")
    return out[LEV_COLUMNS].sort_values(["benchmark_id", "epoch_date"]).reset_index(drop=True)


def benchmark_sites(lev: pd.DataFrame) -> pd.DataFrame:
    """Repery w formacie punktów naziemnych (Plan_v2, sekcja 2.1): wejście step_02.extract_points / L3 przy punkcie."""
    _require_columns(lev, ["benchmark_id", "x_3035", "y_3035", "lat_deg", "lon_deg"], "niwelacja (format długi)")
    one = lev.groupby("benchmark_id", sort=True)[["lat_deg", "lon_deg", "x_3035", "y_3035"]]
    if (one.nunique() > 1).any(axis=None):
        raise ValueError("Reper ma różne współrzędne w różnych epokach")
    s = one.first().reset_index().rename(columns={"benchmark_id": "site"})
    return s.assign(site_type="benchmark", group="benchmark", source=LEVELLING_SOURCE)[
        ["site", "site_type", "group", "lat_deg", "lon_deg", "x_3035", "y_3035", "source"]]


def epochs_in_release(lev: pd.DataFrame, release_start, release_end, rule: str, min_span_yr: float) -> pd.DataFrame:
    """
    Para epok na reper. rule 'first_last_in_release': pierwsza i ostatnia epoka w [release_start, release_end]
    (obie granice włącznie); status 'ok', gdy odstęp >= min_span_yr [lata]. Reper z < 2 epokami w oknie albo
    ze zbyt krótkim odstępem zostaje w wyniku ze statusem (powód), t1/t2 = znalezione epoki (NaT, gdy brak).
    """
    _require_columns(lev, ["benchmark_id", "epoch_date"], "niwelacja (format długi)")
    if rule not in EPOCH_RULES:
        raise ValueError(f"Nieznana reguła epok {rule!r}; dostępne {EPOCH_RULES} (decyzja autora)")
    t0, t1 = pd.Timestamp(_require("release_start", release_start)), pd.Timestamp(_require("release_end", release_end))
    if not t0 < t1:
        raise ValueError(f"Okno wydania {t0.date()} - {t1.date()}: początek musi być przed końcem")
    min_span = float(_require("min_span_yr", min_span_yr))
    _no_duplicates(lev, ["benchmark_id", "epoch_date"], "niwelacja (format długi)")
    _require_valid(lev, "epoch_date", [], "niwelacja (format długi)")
    rows = []
    for bid, g in lev.groupby("benchmark_id", sort=True):
        d = pd.DatetimeIndex(g["epoch_date"]).sort_values()
        win = d[(d >= t0) & (d <= t1)]
        row = {"benchmark_id": bid, "t1": pd.NaT, "t2": pd.NaT, "span_yr": np.nan, "n_epochs_total": len(d),
               "n_epochs_in_release": len(win)}
        if len(win) < 2:
            row["status"] = f"NaN: {len(win)} epok w oknie wydania {t0.date()} - {t1.date()} (potrzebne 2)"
            if len(win) == 1:
                row["t1"] = win[0]
        else:
            span = float(years_since([win[-1]], win[0])[0])
            row.update(t1=win[0], t2=win[-1], span_yr=span,
                       status="ok" if span >= min_span else f"NaN: odstęp epok {span:.2f} roku < min_span_yr {min_span}")
        rows.append(row)
    out = pd.DataFrame(rows, columns=EPOCH_COLUMNS)
    print(f"Epoki w oknie {t0.date()} - {t1.date()}: {int((out['status'] == 'ok').sum())} z {len(out)} reperów ze "
          f"statusem 'ok'; pozostałe (do 5): {out.loc[out['status'] != 'ok', 'status'].value_counts().head(5).to_dict()}")
    return out


# ==============================================================================
# IV. PORÓWNANIE Z EGMS (PION)
# ==============================================================================
# Przeniesione z prototypes/egms_simple_check.py (read_at_epochs). to_years zastąpione identycznym
# step_03_compare_gnss.years_since; dodane jawne błędy dla pustego i nieuporządkowanego szeregu.
def read_at_epochs(series: pd.Series, epochs, method: str) -> pd.Series:
    """Odczyt szeregu w datach epok; tylko interpolacja wewnątrz danych (bez ekstrapolacji)."""
    if method not in READ_METHODS:
        raise ValueError(f"Nieznany sposób odczytu w epoce: {method}")
    s = series.dropna()
    if s.empty:
        raise ValueError("Szereg bez wartości - odczyt w epoce niemożliwy")
    if not (s.index.is_monotonic_increasing and s.index.is_unique):
        raise ValueError("Daty szeregu nie rosną ściśle")
    t0 = s.index[0]
    t = years_since(s.index, t0)            # jednostka niezależna od rozdzielczości dat w pandas
    out = {}
    for ep in epochs:
        ep = pd.Timestamp(ep)
        if ep < s.index[0] or ep > s.index[-1]:
            raise ValueError(f"Epoka {ep.date()} poza zakresem szeregu {s.index[0].date()}-{s.index[-1].date()}")
        out[ep] = float(np.interp(years_since(pd.DatetimeIndex([ep]), t0)[0], t, s.to_numpy(float)))
    return pd.Series(out, dtype=float)


def _reference(reference) -> tuple[str, list]:
    """{"type": "absolute"} albo {"type": "stable_group", "ids": [...]}; cokolwiek innego = ValueError."""
    if not isinstance(reference, dict) or reference.get("type") not in REFERENCE_TYPES:
        raise ValueError(f"reference={reference!r}: odniesienie to decyzja autora; dozwolone {{'type': 'absolute'}} "
                         f"albo {{'type': 'stable_group', 'ids': [...]}}")
    if reference["type"] == "absolute":
        if set(reference) != {"type"}:
            raise ValueError(f"reference 'absolute' nie przyjmuje innych kluczy: {sorted(set(reference) - {'type'})}")
        return "absolute", []
    ids = reference.get("ids")
    if not ids or isinstance(ids, str):
        raise ValueError(f"reference 'stable_group' wymaga niepustej listy 'ids' (decyzja autora), jest {ids!r}")
    ids = [str(b) for b in ids]
    if len(set(ids)) != len(ids):
        raise ValueError(f"reference 'stable_group': zdublowane identyfikatory {ids}")
    return "stable_group", ids


def _egms_u_series(egms_long_u: pd.DataFrame, ref_type: str) -> dict:
    """
    Format długi (Plan_v2, sekcja 2.2), tylko składowa 'U' jednego źródła o wspólnym odniesieniu
    (kolumna reference, jeśli jest: jedna wartość; dla 'absolute' równa 'absolute') -> {site: szereg [mm]}.
    """
    _require_columns(egms_long_u, EGMS_U_NEED, "EGMS pion (format długi)")
    if egms_long_u.empty:
        raise ValueError("EGMS pion (format długi): brak wierszy")
    comp = sorted(egms_long_u["component"].astype(str).unique())
    if comp != ["U"]:
        raise ValueError(f"EGMS pion: oczekiwano tylko component 'U', jest {comp}")
    if "source" in egms_long_u.columns and egms_long_u["source"].nunique() > 1:
        raise ValueError(f"EGMS pion: więcej niż jedno źródło {sorted(egms_long_u['source'].unique())}; podaj jedno")
    if "reference" in egms_long_u.columns:
        refs = sorted(egms_long_u["reference"].astype(str).unique())
        if ref_type == "absolute" and refs != ["absolute"]:
            raise ValueError(f"reference 'absolute', a szeregi EGMS mają odniesienie {refs}: zbiory niespójne")
        if len(refs) > 1:     # 'stable_group': różnica z grupą ma sens tylko przy wspólnym odniesieniu szeregów
            raise ValueError(f"Szeregi EGMS mają różne odniesienia {refs}: zbiory niespójne")
    d = egms_long_u.assign(site=egms_long_u["site"].astype(str), date=pd.to_datetime(egms_long_u["date"]))
    _require_valid(d, "date", [], "EGMS pion (format długi)")      # disp_mm NaN dozwolone (pomijane w odczycie)
    _no_duplicates(d, ["site", "date"], "EGMS pion (format długi)")
    return {s: pd.Series(g["disp_mm"].to_numpy(float), index=pd.DatetimeIndex(g["date"])).sort_index()
            for s, g in d.groupby("site")}


def _group_dh(series_by_id: dict, ids: list, t1: pd.Timestamp, t2: pd.Timestamp, method: str, what: str):
    """Średnia zmiana (t1 -> t2) szeregów grupy odniesienia; każdy członek musi obejmować obie epoki."""
    dh = []
    for g in ids:
        s = series_by_id[g].dropna()
        if s.empty or t1 < s.index[0] or t2 > s.index[-1]:
            span = f"{s.index[0].date()} - {s.index[-1].date()}" if len(s) else "pusty"
            return np.nan, f"NaN: {what} reperu odniesienia {g} ({span}) nie obejmuje epok {t1.date()} - {t2.date()}"
        at = read_at_epochs(s, [t1, t2], method)
        dh.append(at[t2] - at[t1])
    return float(np.mean(dh)), None


def compare_levelling(lev: pd.DataFrame, epoch_pairs: pd.DataFrame, egms_long_u: pd.DataFrame, reference: dict,
                      method: str) -> pd.DataFrame:
    """
    Δh niwelacji i EGMS (pion) między epokami t1, t2 reperu (logika prototypu run_e2, format długi).
      lev: levelling_long; epoch_pairs: epochs_in_release; egms_long_u: szeregi pionowe EGMS w formacie długim
      z site = benchmark_id i component 'U' (jedno źródło, np. EGMS_L3U_2020_2024).
      reference {"type": "absolute"}: bez odniesienia, oba zbiory jak podane (szeregi EGMS muszą mieć
        reference 'absolute', jeśli kolumna istnieje);
      reference {"type": "stable_group", "ids": [...]}: od Δh reperu odejmujemy średnią Δh grupy w tych samych
        epokach t1, t2 - osobno dla niwelacji i dla EGMS (d_rel(t) = d_P(t) - średnia_g d_g(t)). Wysokości
        członka grupy między jego epokami interpolowane liniowo (method), bez ekstrapolacji. Każdy członek musi
        mieć niwelację i szereg EGMS (inaczej ValueError: zmiana grupy to decyzja autora); członek, który nie
        obejmuje epok reperu = NaN z powodem. Repery grupy dostają wiersz ze statusem, bez wartości.
    Wiersz na reper: dh_lev_mm, dh_egms_mm, diff_mm = dh_egms - dh_lev, v_lev_mm_yr = dh_lev / dt,
    v_egms_dh_mm_yr = dh_egms / dt, ref_dh_* (odjęta poprawka grupy; NaN dla 'absolute' - nic nie odjęto),
    status 'ok' albo powód NaN (brak szeregu EGMS, epoka poza szeregiem, para epok bez statusu 'ok').
    Data odniesienia szeregu EGMS nie wpływa na Δh (różnica dwóch odczytów tego samego szeregu).
    """
    if method not in READ_METHODS:
        raise ValueError(f"Nieznany sposób odczytu w epoce: {method}")
    ref_type, ref_ids = _reference(reference)
    _require_columns(lev, ["benchmark_id", "epoch_date", "height_m"], "niwelacja (format długi)")
    _require_columns(epoch_pairs, ["benchmark_id", "t1", "t2", "status"], "pary epok")
    _no_duplicates(lev, ["benchmark_id", "epoch_date"], "niwelacja (format długi)")
    _require_valid(lev, "epoch_date", ["height_m"], "niwelacja (format długi)")
    egms = _egms_u_series(egms_long_u, ref_type)
    h = {str(b): pd.Series(g["height_m"].to_numpy(float) * MM_PER_M, index=pd.DatetimeIndex(g["epoch_date"])).sort_index()
         for b, g in lev.groupby("benchmark_id")}
    if ref_type == "stable_group":
        miss_lev, miss_egms = [b for b in ref_ids if b not in h], [b for b in ref_ids if b not in egms]
        if miss_lev or miss_egms:
            raise ValueError(f"Grupa odniesienia: brak niwelacji {miss_lev}, brak szeregu EGMS {miss_egms} "
                             f"(zmiana grupy to decyzja autora)")
    cand = {str(b) for b, s in zip(epoch_pairs["benchmark_id"], epoch_pairs["status"]) if s == "ok"} - set(ref_ids)
    if cand and not cand & set(egms):          # pojedynczy brak = status; zero trafień = błąd złączenia
        raise ValueError(f"Żaden z {len(cand)} reperów z parą epok 'ok' nie ma szeregu EGMS: identyfikatory niwelacji "
                         f"np. {sorted(cand)[:5]}, EGMS np. {sorted(egms)[:5]} (format identyfikatorów, zera wiodące?)")
    label = "absolute" if ref_type == "absolute" else "stable_group:" + "|".join(ref_ids)
    rows = []
    for p in epoch_pairs.itertuples(index=False):
        bid = str(p.benchmark_id)
        row = {"benchmark_id": bid, "t1": p.t1, "t2": p.t2, "reference": label}
        if p.status != "ok":
            rows.append({**row, "status": p.status})
            continue
        if bid in ref_ids:
            rows.append({**row, "status": "NaN: reper należy do grupy odniesienia"})
            continue
        if bid not in h:
            raise KeyError(f"Reper {bid} z par epok nie występuje w niwelacji")
        t1, t2 = pd.Timestamp(p.t1), pd.Timestamp(p.t2)
        dt = float(years_since([t2], t1)[0])
        if not dt > 0:
            raise ValueError(f"Reper {bid}: t2 {t2.date()} nie jest po t1 {t1.date()}")
        miss = [t.date() for t in (t1, t2) if t not in h[bid].index]
        if miss:
            raise KeyError(f"Reper {bid}: epok {miss} nie ma w niwelacji (pary epok z innej tabeli?)")
        reasons = []
        dh_lev, dh_egms = h[bid][t2] - h[bid][t1], np.nan
        ref_lev = ref_egms = np.nan
        if ref_type == "stable_group":
            ref_lev, why = _group_dh(h, ref_ids, t1, t2, method, "niwelacja")
            reasons += [why] if why else []
            dh_lev -= ref_lev
        s = egms.get(bid)
        if s is None or s.dropna().empty:
            reasons.append("NaN: brak szeregu EGMS (pion) przy reperze")
        elif t1 < s.dropna().index[0] or t2 > s.dropna().index[-1]:
            reasons.append(f"NaN: epoka poza zakresem szeregu EGMS {s.dropna().index[0].date()} - "
                           f"{s.dropna().index[-1].date()}")
        else:
            at = read_at_epochs(s, [t1, t2], method)
            dh_egms = at[t2] - at[t1]
            if ref_type == "stable_group":
                ref_egms, why = _group_dh(egms, ref_ids, t1, t2, method, "szereg EGMS")
                reasons += [why] if why else []
                dh_egms -= ref_egms
        rows.append({**row, "dt_yr": dt, "dh_lev_mm": float(dh_lev), "dh_egms_mm": float(dh_egms),
                     "ref_dh_lev_mm": ref_lev, "ref_dh_egms_mm": ref_egms,
                     "status": "; ".join(reasons) if reasons else "ok"})
    out = pd.DataFrame(rows).reindex(columns=COMPARE_COLUMNS)
    num = ["dt_yr", "dh_lev_mm", "dh_egms_mm", "ref_dh_lev_mm", "ref_dh_egms_mm"]
    out[num] = out[num].astype(float)
    out["diff_mm"] = out["dh_egms_mm"] - out["dh_lev_mm"]
    out["v_lev_mm_yr"] = out["dh_lev_mm"] / out["dt_yr"]
    out["v_egms_dh_mm_yr"] = out["dh_egms_mm"] / out["dt_yr"]
    if not np.isfinite(out.loc[out["status"] == "ok", ["dt_yr", "diff_mm"]].to_numpy(float)).all():
        raise RuntimeError("compare_levelling: wiersz ze statusem 'ok' ma wartość NaN (niespójność wewnętrzna)")
    print(f"Porównanie z niwelacją ({label}): {int((out['status'] == 'ok').sum())} z {len(out)} reperów ze statusem 'ok'")
    return out


# ==============================================================================
# V. EGMS L2b -> PION (ORBITA WSTĘPUJĄCA + ZSTĘPUJĄCA)
# ==============================================================================
def vertical_from_asc_desc(los_asc: pd.Series, vec_asc: tuple, los_desc: pd.Series, vec_desc: tuple, epochs,
                           method: str, max_cond: float) -> pd.DataFrame:
    """
    Pion i wschód z dwóch szeregów LOS [mm] w epokach. vec_* = (los_east, los_north, los_up): kosinusy
    kierunkowe ziemia -> satelita jak w EGMS L2b (kontrole A1-A3 robi step_02.check_conventions).
    ZAŁOŻENIE: brak ruchu północ-południe (N = 0). Wtedy d = e*E + n*N + u*U = e*E + u*U i rozwiązujemy
        [[e_a, u_a], [e_d, u_d]] @ [E, U] = [d_a, d_d].
    Składowa los_north nie wchodzi do układu; ruch N != 0 przenosi się na błąd E i U (czułość LOS na N jest
    mała przy orbicie prawie biegunowej, ale nie zerowa). Założenie zapisane w kolumnie assumption = 'north=0'.
    Szeregi odczytywane w epokach read_at_epochs (method, bez ekstrapolacji: epoka poza szeregiem = ValueError).
    Oba szeregi powinny mieć wspólną datę odniesienia; inaczej sens mają tylko różnice między epokami.
    Uwarunkowanie układu cond > max_cond (wektory LOS prawie równoległe) albo układ osobliwy = ValueError.
    """
    max_cond = float(_require("max_cond", max_cond))
    va, vd = (np.asarray(v, float) for v in (vec_asc, vec_desc))
    if va.shape != (3,) or vd.shape != (3,) or not (np.isfinite(va).all() and np.isfinite(vd).all()):
        raise ValueError(f"Wektory LOS muszą mieć 3 skończone składowe (east, north, up): {vec_asc}, {vec_desc}")
    A = np.array([[va[0], va[2]], [vd[0], vd[2]]])
    cond = float(np.linalg.cond(A))
    if not np.isfinite(cond) or cond > max_cond:
        raise ValueError(f"Układ asc/desc źle uwarunkowany: cond = {cond:.3g} > max_cond = {max_cond} "
                         f"(wektory LOS prawie równoległe)")
    ep = pd.DatetimeIndex(pd.to_datetime(list(epochs)))
    if ep.empty:
        raise ValueError("Brak epok do rozkładu asc/desc")
    da = read_at_epochs(los_asc, ep, method).reindex(ep).to_numpy(float)
    dd = read_at_epochs(los_desc, ep, method).reindex(ep).to_numpy(float)
    east, up = np.linalg.solve(A, np.vstack([da, dd]))
    return pd.DataFrame({"date": ep, "los_asc_mm": da, "los_desc_mm": dd, "east_mm": east, "up_mm": up,
                         "cond": cond, "assumption": "north=0"})


# ==============================================================================
# VI. KRYTERIA
# ==============================================================================
# Przeniesione z prototypes/egms_simple_check.py (robust_stats); dodany jawny błąd dla pustego zbioru.
def robust_stats(x: np.ndarray) -> dict:
    """Mediana i MAD x 1,4826 (Even i in. 2024) oraz średnia i odchylenie."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        raise ValueError("robust_stats: brak skończonych wartości")
    med = float(np.median(x))
    return {"n": int(x.size), "median": med, "mad_sigma": float(MAD_TO_SIGMA * np.median(np.abs(x - med))),
            "mean": float(x.mean()), "std": float(x.std(ddof=1)) if x.size > 1 else np.nan}


def summarize_levelling(res: pd.DataFrame, th: dict) -> pd.DataFrame:
    """
    Kryteria jak T2 (Plan_v1_kryteria_akceptacji.md, sekcja C; prototyp summarize_e2) na wierszach 'ok':
      N1 mediana |diff| <= median_abs_dh_mm;
      N2 zgodność znaku dla |dh_lev| >= sign_min_signal_mm: odsetek >= sign_agreement;
      N3 kontrola negatywna: repery stabilne (|dh_lev| <= stable_max_lev_mm), mediana |dh_egms| <= stable_abs_dh_mm;
      N4 bias prędkości: |mediana(v_egms_dh - v_lev)| <= velocity_bias_mm_yr;
      informacyjnie: MAD x 1,4826 różnic prędkości; nachylenie dh_egms względem dh_lev (z błędem standardowym).
    Kryterium bez reperów = wiersz z powodem i spełnione None. Zero wierszy 'ok' = ValueError.
    """
    _require_columns(res, ["dh_lev_mm", "dh_egms_mm", "diff_mm", "v_lev_mm_yr", "v_egms_dh_mm_yr", "status"],
                     "wynik compare_levelling")
    missing = [k for k in THRESHOLD_KEYS if th.get(k) is None]
    if missing:
        raise ValueError(f"Progi bez wartości {missing}: decyzja autora (Plan_v1_kryteria_akceptacji.md)")
    ok = res[res["status"] == "ok"]
    if ok.empty:
        raise ValueError(f"Brak reperów ze statusem 'ok' (z {len(res)}): kryteriów nie da się policzyć")
    vals = ["dh_lev_mm", "dh_egms_mm", "diff_mm", "v_lev_mm_yr", "v_egms_dh_mm_yr"]
    nonfinite = ~np.isfinite(ok[vals].to_numpy(float)).all(axis=1)
    if nonfinite.any():                        # robust_stats pominąłby je po cichu, a n w tabeli byłoby zawyżone
        raise ValueError(f"{int(nonfinite.sum())} wierszy ze statusem 'ok' ma NaN w {vals}: wynik niespójny")
    rows = []
    med = robust_stats(ok["diff_mm"].abs().to_numpy())["median"]
    rows.append(("N1 mediana |Δh_EGMS - Δh_niw|", f"{med:.1f} mm", f"<= {th['median_abs_dh_mm']} mm",
                 med <= th["median_abs_dh_mm"], len(ok)))
    sig = ok[ok["dh_lev_mm"].abs() >= th["sign_min_signal_mm"]]
    name = f"N2 zgodność znaku (|Δh_niw| >= {th['sign_min_signal_mm']} mm)"
    if len(sig):
        share = float((np.sign(sig["dh_egms_mm"]) == np.sign(sig["dh_lev_mm"])).mean())
        rows.append((name, f"{share:.0%} reperów", f">= {th['sign_agreement']:.0%}", share >= th["sign_agreement"], len(sig)))
    else:
        rows.append((name, f"brak reperów z |Δh_niw| >= {th['sign_min_signal_mm']} mm", f">= {th['sign_agreement']:.0%}",
                     None, 0))
    stab = ok[ok["dh_lev_mm"].abs() <= th["stable_max_lev_mm"]]
    name = f"N3 kontrola negatywna: repery stabilne (|Δh_niw| <= {th['stable_max_lev_mm']} mm)"
    if len(stab):
        sm = float(stab["dh_egms_mm"].abs().median())
        rows.append((name, f"mediana |Δh_EGMS| {sm:.1f} mm", f"<= {th['stable_abs_dh_mm']} mm",
                     sm <= th["stable_abs_dh_mm"], len(stab)))
    else:
        rows.append((name, f"brak reperów z |Δh_niw| <= {th['stable_max_lev_mm']} mm", f"<= {th['stable_abs_dh_mm']} mm",
                     None, 0))
    dv = robust_stats((ok["v_egms_dh_mm_yr"] - ok["v_lev_mm_yr"]).to_numpy())
    rows.append(("N4 bias prędkości v_EGMS(Δh) - v_niw", f"mediana {dv['median']:+.2f} mm/rok",
                 f"|bias| <= {th['velocity_bias_mm_yr']} mm/rok", abs(dv["median"]) <= th["velocity_bias_mm_yr"], dv["n"]))
    rows.append(("Rozrzut różnic prędkości (informacyjnie)", f"MAD*1.4826 {dv['mad_sigma']:.2f} mm/rok", "-", None, dv["n"]))
    name = "Nachylenie Δh_EGMS względem Δh_niw (informacyjnie)"
    x, y = ok["dh_lev_mm"].to_numpy(float), ok["dh_egms_mm"].to_numpy(float)
    sxx = float(((x - x.mean()) ** 2).sum())
    if len(ok) >= 3 and sxx > 0:
        slope, intercept = np.polyfit(x, y, 1)
        se = float(np.sqrt(((y - (slope * x + intercept)) ** 2).sum() / (len(x) - 2) / sxx))
        rows.append((name, f"{slope:.2f}, błąd standardowy {se:.2f} (wyraz wolny {intercept:+.1f} mm)", "bliskie 1",
                     None, len(ok)))
    else:
        rows.append((name, "za mało reperów lub brak zróżnicowania Δh_niw", "bliskie 1", None, len(ok)))
    return pd.DataFrame(rows, columns=SUMMARY_COLUMNS)


STATION_BOX_MARGIN_DEG = 3.0            # stacje dalej niż 3 stopnie od prostokąta punktów nie mogą być najbliższe
STATION_CHUNK = 500                      # punkty na paczkę przy liczeniu odległości (pamięć: punkty x stacje)
GROUP_COLUMNS = ["grupa", "n", "median_abs_diff_mm", "sign_agreement", "n_sign", "bias_v_mm_yr", "mad_v_mm_yr",
                 "slope", "dist_station_km_median", "dist_station_km_min"]


def nearest_station_km(points: pd.DataFrame, stations: pd.DataFrame) -> pd.DataFrame:
    """
    Najbliższa stacja dla każdego punktu: points (id, x_3035, y_3035), stations (site, lat_deg, lon_deg; np. plik MIDAS
    NGL). Odległość pozioma w EPSG:3035 [km]. Do obliczeń brane są stacje w prostokącie punktów powiększonym
    o STATION_BOX_MARGIN_DEG (stacje z drugiej półkuli nie trafiają do odwzorowania LAEA). Brak stacji w tym
    prostokącie, punkt albo stacja bez współrzędnych, puste tabele = ValueError.
    Wynik: id, nearest_station, dist_station_km.
    """
    _require_columns(points, ["id", "x_3035", "y_3035"], "punkty")
    _require_columns(stations, ["site", "lat_deg", "lon_deg"], "stacje")
    if points.empty or stations.empty:
        raise ValueError(f"Puste tabele: punkty {len(points)}, stacje {len(stations)}")
    px, py = points["x_3035"].to_numpy(float), points["y_3035"].to_numpy(float)
    if not (np.isfinite(px).all() and np.isfinite(py).all()):
        raise ValueError(f"Punkty bez współrzędnych EPSG:3035: {points.loc[~(np.isfinite(px) & np.isfinite(py)), 'id'].tolist()[:5]}")
    slat, slon = stations["lat_deg"].to_numpy(float), stations["lon_deg"].to_numpy(float)
    if not (np.isfinite(slat).all() and np.isfinite(slon).all()):
        raise ValueError(f"Stacje bez współrzędnych: {stations.loc[~(np.isfinite(slat) & np.isfinite(slon)), 'site'].tolist()[:5]}")
    plon, plat = transform_xy(px, py, 3035, 4326)
    m = STATION_BOX_MARGIN_DEG
    box = ((slon >= plon.min() - m) & (slon <= plon.max() + m) & (slat >= plat.min() - m) & (slat <= plat.max() + m))
    if not box.any():
        raise ValueError(f"Żadnej stacji w prostokącie punktów +- {m} stopni ({plon.min():.2f}-{plon.max():.2f} E, "
                         f"{plat.min():.2f}-{plat.max():.2f} N)")
    near = stations[box]
    sx, sy = transform_xy(near["lon_deg"].to_numpy(float), near["lat_deg"].to_numpy(float), 4326, 3035)
    names = near["site"].astype(str).to_numpy()
    idx, dist = np.empty(len(px), int), np.empty(len(px), float)
    for a in range(0, len(px), STATION_CHUNK):
        d = np.hypot(px[a:a + STATION_CHUNK, None] - sx[None, :], py[a:a + STATION_CHUNK, None] - sy[None, :])
        idx[a:a + STATION_CHUNK] = d.argmin(axis=1)
        dist[a:a + STATION_CHUNK] = d.min(axis=1)
    return pd.DataFrame({"id": points["id"].astype(str).to_numpy(), "nearest_station": names[idx],
                         "dist_station_km": dist / 1000.0})


def levelling_groups(res: pd.DataFrame, strong_mm_yr: float, sign_min_mm: float) -> pd.DataFrame:
    """
    Podział informacyjny wierszy 'ok' compare_levelling (bez progów i bez werdyktu; autor 2026-10-12): wszystkie,
    niecki |v_lev| >= strong_mm_yr, pozostałe |v_lev| < strong_mm_yr (podział według NIWELACJI, nie według EGMS -
    wybór według testowanej wielkości obciążyłby wynik). Na grupę: n, mediana |diff| [mm], zgodność znaku dla
    |dh_lev| >= sign_min_mm (próg N2) i jej n, mediana i MAD x 1,4826 różnicy prędkości v_egms_dh - v_lev [mm/rok],
    nachylenie dh_egms względem dh_lev (n >= 3 i zróżnicowane dh_lev, inaczej NaN), mediana i minimum odległości
    do najbliższej stacji GNSS [km] (gdy jest kolumna dist_station_km, inaczej NaN). Grupa bez reperów = n 0 i NaN.
    Zero wierszy 'ok' = ValueError.
    """
    _require_columns(res, ["dh_lev_mm", "dh_egms_mm", "diff_mm", "v_lev_mm_yr", "v_egms_dh_mm_yr", "status"],
                     "wynik compare_levelling")
    strong, sign_min = float(_require("strong_mm_yr", strong_mm_yr)), float(_require("sign_min_mm", sign_min_mm))
    if not strong > 0:
        raise ValueError(f"strong_mm_yr musi być dodatnie, jest {strong}")
    ok = res[res["status"] == "ok"]
    if ok.empty:
        raise ValueError(f"Brak reperów ze statusem 'ok' (z {len(res)}): podziału nie da się policzyć")
    has_dist = "dist_station_km" in ok.columns
    groups = [("wszystkie", ok), (f"niecki: |v_niw| >= {strong:g} mm/rok", ok[ok["v_lev_mm_yr"].abs() >= strong]),
              (f"pozostałe: |v_niw| < {strong:g} mm/rok", ok[ok["v_lev_mm_yr"].abs() < strong])]
    rows = []
    for name, g in groups:
        row = dict.fromkeys(GROUP_COLUMNS, np.nan)
        row.update(grupa=name, n=len(g), n_sign=0)
        if len(g):
            row["median_abs_diff_mm"] = float(g["diff_mm"].abs().median())
            sig = g[g["dh_lev_mm"].abs() >= sign_min]
            row["n_sign"] = len(sig)
            if len(sig):
                row["sign_agreement"] = float((np.sign(sig["dh_egms_mm"]) == np.sign(sig["dh_lev_mm"])).mean())
            dv = robust_stats((g["v_egms_dh_mm_yr"] - g["v_lev_mm_yr"]).to_numpy())
            row["bias_v_mm_yr"], row["mad_v_mm_yr"] = dv["median"], dv["mad_sigma"]
            x, y = g["dh_lev_mm"].to_numpy(float), g["dh_egms_mm"].to_numpy(float)
            if len(g) >= 3 and float(((x - x.mean()) ** 2).sum()) > 0:
                row["slope"] = float(np.polyfit(x, y, 1)[0])
            if has_dist:
                d = g["dist_station_km"].to_numpy(float)
                if not np.isfinite(d).all():
                    raise ValueError(f"Grupa {name!r}: brak odległości do stacji GNSS w {int((~np.isfinite(d)).sum())} wierszach")
                row["dist_station_km_median"], row["dist_station_km_min"] = float(np.median(d)), float(d.min())
        rows.append(row)
    return pd.DataFrame(rows, columns=GROUP_COLUMNS)


# ==============================================================================
# VII. TEST OFFLINE I OPIS PLIKÓW NRW
# ==============================================================================
def _midas_line(site, t_first, t_last, vu_m_yr, svu_m_yr, n_steps, lat, lon) -> str:
    """Syntetyczny wiersz MIDAS (27 kolumn, układ step_01.MIDAS_COLUMNS); wartości testowe, nie stacje."""
    return (f"{site} MIDAS5 {t_first} {t_last} 10.0 3000 2900 2500 0.0001 0.0010 {vu_m_yr} 0.0001 0.0001 "
            f"{svu_m_yr} 0 0 0 0.01 0.01 0.02 0.001 0.001 0.003 {n_steps} {lat} {lon} 100.0")


def _expect_raises(exc, fn, *args, match: str = ""):
    try:
        fn(*args)
    except exc as e:
        assert match in str(e), f"komunikat bez '{match}': {e}"
        return e
    raise AssertionError(f"Oczekiwano {exc.__name__} z {getattr(fn, '__name__', fn)}")


def _num(v: float, nd: int) -> str:
    return f"{v:.{nd}f}".replace(".", ",")


def _selftest() -> None:
    from step_01_ingest import read_ngl_midas
    rng = np.random.default_rng(20261011)
    with tempfile.TemporaryDirectory(prefix="egmscheck_ground_") as tmpd:
        tmp = Path(tmpd)

        # 1. Stacje GNSS: reguła 'all_quality' i grupy; współrzędne syntetyczne.
        lines = [_midas_line("SUBA", 2015.0, 2026.5, -0.0045, 0.0004, 1, 51.00, 6.40),
                 _midas_line("SUBB", 2015.0, 2026.5, -0.0020, 0.0004, 0, 51.05, 6.45),   # vu = -2,0: granica
                 _midas_line("STBA", 2015.0, 2026.5, 0.0002, 0.0003, 0, 50.95, 6.30),
                 _midas_line("OTHA", 2015.0, 2026.5, -0.0015, 0.0004, 0, 50.90, 6.50),
                 _midas_line("UPLA", 2015.0, 2026.5, 0.0030, 0.0004, 2, 51.10, 6.20),
                 _midas_line("NOIS", 2015.0, 2026.5, -0.0050, 0.0015, 0, 51.00, 6.60),   # svu 1,5 > 1,0
                 _midas_line("STEP", 2015.0, 2026.5, -0.0050, 0.0004, 3, 51.00, 6.61),   # 3 skoki > 2
                 _midas_line("LATE", 2021.0, 2026.5, -0.0050, 0.0004, 0, 51.00, 6.62),   # dane od 2021
                 _midas_line("OUTA", 2015.0, 2026.5, -0.0050, 0.0004, 0, 51.00, 8.00)]   # poza obszarem
        mid = read_ngl_midas("\n".join(lines))
        gargs = (2020.0, 2024.25, 1.0, 2, -2.0, 1.0)
        st = select_stations_aoi(mid, (6.0, 50.8, 6.8, 51.2), *gargs)
        assert list(st.columns) == SITE_COLUMNS
        assert dict(zip(st["site"], st["group"])) == {"SUBA": "osiadająca", "SUBB": "osiadająca", "STBA": "stabilna",
                                                       "OTHA": "inna", "UPLA": "inna"}, st
        assert (st["site_type"] == "gnss").all() and (st["source"] == GNSS_SITE_SOURCE).all()
        lon_b, lat_b = transform_xy(st["x_3035"].to_numpy(), st["y_3035"].to_numpy(), 3035, 4326)
        assert np.allclose(lon_b, st["lon_deg"], atol=1e-9) and np.allclose(lat_b, st["lat_deg"], atol=1e-9)
        empty = select_stations_aoi(mid, (20.0, 60.0, 21.0, 61.0), *gargs)
        assert empty.empty and list(empty.columns) == SITE_COLUMNS
        _expect_raises(ValueError, select_stations_aoi, mid, (6.0, 50.8, 6.8, 51.2), 2020.0, 2024.25, 1.0, 2, -0.5, 1.0,
                       match="nachodzą")
        _expect_raises(ValueError, select_stations_aoi, mid, None, *gargs, match="decyzja autora")
        _expect_raises(KeyError, select_stations_aoi, mid.drop(columns="svu_mm_yr"), (6.0, 50.8, 6.8, 51.2), *gargs,
                       match="svu_mm_yr")
        _expect_raises(ValueError, select_stations_aoi, mid.assign(vu_mm_yr=mid["vu_mm_yr"].where(mid["site"] != "STBA")),
                       (6.0, 50.8, 6.8, 51.2), *gargs, match="STBA")

        # 2. Syntetyczna niecka osiadania (EPSG:3035) i repery; wartości testowe, nie dane.
        x0, y0 = transform_xy(6.40, 50.95, 4326, 3035)
        rate_peak, sigma_m, common_mm_yr = -12.0, 400.0, 3.0      # common: ruch wspólny tylko w EGMS (układ)
        offsets = {"B01": (0, 0), "B02": (200, 0), "B03": (0, -400), "B04": (-500, 300), "B05": (800, 800),
                   "T01": (3000, -3000), "T02": (-3000, 3000), "S01": (4000, 0), "S02": (0, 4000),
                   "S03": (-4000, -1000), "B06": (100, 100), "B07": (-100, 100), "B08": (150, -150),
                   "B09": (-200, -200), "B10": (300, 300), "X01": (40000, 0)}
        rate = {b: rate_peak * np.exp(-(dx ** 2 + dy ** 2) / (2 * sigma_m ** 2)) for b, (dx, dy) in offsets.items()}
        regular = ["2019-05-10", "2020-06-15", "2022-06-15", "2024-06-20", "2025-04-01"]
        epochs = {b: [pd.Timestamp(d) + pd.Timedelta(days=3 * k) for d in regular]
                  for k, b in enumerate(["B01", "B02", "B03", "B04", "B05", "T01", "T02", "B08", "B09", "X01"])}
        epochs.update({s: [pd.Timestamp(d) + pd.Timedelta(days=k) for d in ("2020-03-02", "2022-06-10", "2024-11-15")]
                       for k, s in enumerate(["S01", "S02", "S03"])})
        epochs["B06"] = [pd.Timestamp(d) for d in ("2019-05-10", "2021-03-01", "2021-09-01", "2025-04-01")]  # 0,5 roku
        epochs["B07"] = [pd.Timestamp(d) for d in ("2019-05-10", "2023-05-05", "2025-04-01")]                # 1 epoka
        epochs["B10"] = [pd.Timestamp(d) for d in ("2020-02-01", "2022-06-15", "2024-06-20")]  # przed grupą
        t_egms0 = pd.Timestamp("2020-01-03")
        egms_dates = pd.date_range(t_egms0, "2024-12-27", freq="6D")
        noise = {b: rng.normal(0.0, 1.0, len(e)) for b, e in epochs.items()}           # niwelacja: szum 1 mm
        pt_rows, ser_rows, h_mm = [], [], {}
        for b, (dx, dy) in offsets.items():
            e25, n25 = transform_xy(x0 + dx, y0 + dy, 3035, 25832)
            pt_rows.append(f'"{b}";"Punkt {b}; Kirchturm";{_num(e25, 3)};{_num(n25, 3)};{_num(100.0, 4)};"981123,4"')
            truth = rate[b] * years_since(epochs[b], t_egms0)
            h = np.round(100.0 + (truth + noise[b]) / MM_PER_M, 5)
            h_mm[b] = pd.Series(h * MM_PER_M, index=pd.DatetimeIndex(epochs[b]))
            ser_rows += [f"{b};{d.strftime('%d.%m.%Y')};{_num(v, 5)}" for d, v in zip(epochs[b], h)]
        p_pts, p_ser = tmp / "hfp_pl.csv", tmp / "hfp_plzf.csv"
        p_pts.write_text(" Punktkennzeichen ; Name des Punktes;Ostwert;Nordwert ;Höhe;Schwerewert\n"
                         + "\n".join(pt_rows) + "\n", encoding="cp1252")
        p_ser.write_text("Punktkennzeichen;Messungsdatum;Höhe\n" + "\n".join(ser_rows) + "\n", encoding="utf-8")

        # 3. Czytniki: nagłówki ze spacjami, cudzysłowy ze średnikiem, przecinek dziesiętny, kodowanie.
        pts = read_nrw_points(p_pts, "cp1252")
        ser = read_nrw_timeseries(p_ser, "utf-8")
        assert list(pts.columns) == NRW_POINT_COLUMNS and len(pts) == len(offsets)
        assert pts.loc[0, "Name des Punktes"] == "Punkt B01; Kirchturm" and pts["Ostwert"].dtype == float
        assert pts.loc[0, "Schwerewert"] == "981123,4" and np.isclose(pts.loc[0, "Höhe"], 100.0)
        assert len(ser) == sum(len(e) for e in epochs.values()) and ser["Messungsdatum"].dtype.kind == "M"
        _expect_raises(UnicodeDecodeError, read_nrw_points, p_pts, "utf-8")
        bad = tmp / "bad.csv"
        bad.write_text("Punktkennzeichen;Name des Punktes;Ostwert;Höhe;Schwerewert\n1;a;1,0;2,0;3,0\n", encoding="utf-8")
        e = _expect_raises(KeyError, read_nrw_points, bad, "utf-8", match="Nordwert")
        assert "dostępne" in str(e) and "Ostwert" in str(e)
        bad.write_text("Punktkennzeichen;Messungsdatum;Höhe\nB01;01.03.2021;100,1\nB01;01.03.2021;100,2\n", encoding="utf-8")
        _expect_raises(ValueError, read_nrw_timeseries, bad, "utf-8", match="zdublowanym")
        bad.write_text("Punktkennzeichen;Messungsdatum;Höhe\nB01;01.03.2021;100,1\nB02;01.03.2021;1.234,5\n", encoding="utf-8")
        _expect_raises(ValueError, read_nrw_timeseries, bad, "utf-8", match="1.234,5")
        bad.write_text("Punktkennzeichen;Messungsdatum;Höhe\nB01;2021-03-01;100,1\n", encoding="utf-8")
        _expect_raises(ValueError, read_nrw_timeseries, bad, "utf-8", match="2021-03-01")
        bad.write_text("Punktkennzeichen;Name des Punktes;Ostwert;Nordwert;Höhe;Schwerewert\n1;a;;5650000,0;2,0;\n",
                       encoding="utf-8")
        _expect_raises(ValueError, read_nrw_points, bad, "utf-8", match="Ostwert")
        head = "Punktkennzeichen;Name des Punktes;Ostwert;Nordwert;Höhe;Schwerewert\n"
        row = '"B01";"a";350000,5;5650000,25;100,1234;"981123,4"'
        for body in (row + ";\n" + row.replace("B01", "B02") + ";\n",          # średnik na końcu wierszy danych
                     row + ';"x"\n' + row.replace("B01", "B02") + "\n",         # pole nadmiarowe w jednym wierszu
                     row + "\n" + '"B02";"b";350100,5\n'):                       # wiersz za krótki
            bad.write_text(head + body, encoding="utf-8")                        # pandas: ciche przesunięcie kolumn
            _expect_raises(ValueError, read_nrw_points, bad, "utf-8", match="liczbą pól")
        bad.write_text(head + row.replace('"a"', '"a"x') + "\n", encoding="utf-8")
        _expect_raises(ValueError, read_nrw_points, bad, "utf-8", match="błędny CSV w linii 2")
        # Cudzysłów wewnątrz nazwy bez podwojenia (Colab, hfp_pl.csv linia 2944): rozbiór wg struktury formatu,
        # nazwa bez zmian, liczby jak zwykle; średnik w takiej nazwie też; Zeitfolge (bez pola tekstowego) głośno.
        bad.write_text(head + row.replace('"a"', '"Kirche "St. Marien""') + "\n"
                       + row.replace("B01", "B02").replace('"a"', '"Haus "Alt;Neu" 3"') + "\n", encoding="utf-8")
        p_q = read_nrw_points(bad, "utf-8")
        assert list(p_q["Name des Punktes"]) == ['Kirche "St. Marien"', 'Haus "Alt;Neu" 3'], p_q
        assert list(p_q["Punktkennzeichen"]) == ["B01", "B02"] and p_q["Ostwert"].tolist() == [350000.5, 350000.5]
        bad.write_text(head + row.replace('"a"', '"Kirche "St. Marien""').replace("350000,5", '"350"000,5"') + "\n",
                       encoding="utf-8")
        _expect_raises(ValueError, read_nrw_points, bad, "utf-8", match="nie pasuje do struktury")
        bad.write_text('B01;01.06.1977;"54,5"x\n', encoding="utf-8")
        _expect_raises(ValueError, read_nrw_timeseries, bad, "utf-8", match="błędny CSV w linii 1")
        bad.write_text(head.replace("Schwerewert", "Höhe") + row + "\n", encoding="utf-8")
        _expect_raises(ValueError, read_nrw_points, bad, "utf-8", match="zdublowane nazwy")
        bad.write_text("\ufeff" + head.replace("Punktkennzeichen", '"Punktkennzeichen"').replace("Höhe", "Ho\u0308he")
                       + row + "\n\n" + row.replace("B01", "B02") + "\n", encoding="utf-8")  # BOM, NFD, pusta linia
        p_bom = read_nrw_points(bad, "utf-8")
        assert p_bom["Punktkennzeichen"].tolist() == ["B01", "B02"] and p_bom["Ostwert"].tolist() == [350000.5] * 2
        assert p_bom["Nordwert"].tolist() == [5650000.25] * 2 and p_bom["Höhe"].tolist() == [100.1234] * 2

        # 4. Format długi: przeliczenie 25832 -> 3035/WGS84 (powrót do położenia), filtr obszaru, błędy głośne.
        aoi = (6.30, 50.90, 6.50, 51.00)
        lev = levelling_long(pts, ser, 25832, aoi)
        assert list(lev.columns) == LEV_COLUMNS and "X01" not in set(lev["benchmark_id"])
        one = lev.drop_duplicates("benchmark_id").set_index("benchmark_id")
        for b, (dx, dy) in offsets.items():
            if b == "X01":
                continue
            assert abs(one.at[b, "x_3035"] - (x0 + dx)) < 5e-3 and abs(one.at[b, "y_3035"] - (y0 + dy)) < 5e-3, b
            lo, la = transform_xy(x0 + dx, y0 + dy, 3035, 4326)
            assert abs(one.at[b, "lon_deg"] - lo) < 1e-7 and abs(one.at[b, "lat_deg"] - la) < 1e-7, b
        _expect_raises(ValueError, levelling_long, pts[pts["Punktkennzeichen"] != "B01"], ser, 25832, aoi,
                       match="Punktliste")
        _expect_raises(ValueError, levelling_long, pts.assign(Ostwert=pts["Ostwert"] + 32e6), ser, 25832, aoi,
                       match="nieprzeliczalne")
        _expect_raises(ValueError, levelling_long, pts, ser, 25832, (20.0, 60.0, 21.0, 61.0), match="Żaden")
        _expect_raises(ValueError, levelling_long, pts, ser, None, aoi, match="crs_epsg")
        sites = benchmark_sites(lev)
        assert len(sites) == len(offsets) - 1 and (sites["site_type"] == "benchmark").all()

        # 5. Epoki w oknie wydania: repery z zbyt krótkim odstępem i jedną epoką zostają ze statusem.
        ep = epochs_in_release(lev, "2020-01-01", "2024-12-31", "first_last_in_release", 1.0)
        epi = ep.set_index("benchmark_id")
        assert len(ep) == len(offsets) - 1
        assert epi.at["B01", "t1"] == pd.Timestamp("2020-06-15") and epi.at["B01", "t2"] == pd.Timestamp("2024-06-20")
        assert epi.at["B02", "t1"] == pd.Timestamp("2020-06-18") and epi.at["B01", "n_epochs_in_release"] == 3
        assert epi.at["B06", "status"].startswith("NaN: odstęp") and abs(epi.at["B06", "span_yr"] - 184 / DAYS_PER_YEAR) < 1e-9
        assert epi.at["B07", "status"].startswith("NaN: 1 epok") and pd.isna(epi.at["B07", "t2"])
        _expect_raises(ValueError, epochs_in_release, lev, "2020-01-01", "2024-12-31", "all_pairs", 1.0, match="reguła")
        _expect_raises(ValueError, epochs_in_release, lev, "2020-01-01", "2024-12-31", "first_last_in_release", None,
                       match="min_span_yr")
        edge = pd.DataFrame({"benchmark_id": "Z", "epoch_date": pd.to_datetime(
            ["2019-12-31", "2020-01-01", "2022-01-01", "2024-12-31", "2025-01-01"])})        # obie granice włącznie
        ez = epochs_in_release(edge, "2020-01-01", "2024-12-31", "first_last_in_release", 1.0).iloc[0]
        assert (ez["t1"], ez["t2"], ez["n_epochs_in_release"], ez["status"]) == (
            pd.Timestamp("2020-01-01"), pd.Timestamp("2024-12-31"), 3, "ok"), ez

        # 6. EGMS pion w formacie długim: niecka + ruch wspólny; B08 bez szeregu, B09 szereg do 2023-06-30.
        yrs = years_since(egms_dates, t_egms0)
        long_rows = []
        for b in offsets:
            if b in ("B08", "X01"):
                continue
            d = egms_dates[egms_dates <= "2023-06-30"] if b == "B09" else egms_dates
            long_rows.append(pd.DataFrame({
                "region": "selftest", "source": "EGMS_L3U_2020_2024", "site": b, "track": "", "direction": "",
                "component": "U", "los_east": 0.0, "los_north": 0.0, "los_up": 1.0, "date": d,
                "disp_mm": (rate[b] + common_mm_yr) * yrs[:len(d)], "ref_date": t_egms0, "reference": "absolute",
                "n_points": 1}))
        egms_long = pd.concat(long_rows, ignore_index=True)
        method = "linear_interpolation"
        res_a = compare_levelling(lev, ep, egms_long, {"type": "absolute"}, method).set_index("benchmark_id")
        ok_a = res_a[res_a["status"] == "ok"]
        assert set(ok_a.index) == {"B01", "B02", "B03", "B04", "B05", "T01", "T02", "S01", "S02", "S03", "B10"}, ok_a
        for b, r in ok_a.iterrows():
            dt = years_since([r["t2"]], r["t1"])[0]
            k1, k2 = epochs[b].index(r["t1"]), epochs[b].index(r["t2"])
            assert abs(r["dh_egms_mm"] - (rate[b] + common_mm_yr) * dt) < 1e-6, b
            assert abs(r["dh_lev_mm"] - (rate[b] * dt + noise[b][k2] - noise[b][k1])) < 0.02, b
            assert abs(r["diff_mm"] - (common_mm_yr * dt - (noise[b][k2] - noise[b][k1]))) < 0.02, b
            assert abs(r["v_egms_dh_mm_yr"] - (rate[b] + common_mm_yr)) < 1e-6 and pd.isna(r["ref_dh_lev_mm"]), b
        assert res_a.at["B08", "status"].startswith("NaN: brak szeregu EGMS") and pd.isna(res_a.at["B08", "diff_mm"])
        assert np.isfinite(res_a.at["B08", "dh_lev_mm"])
        assert res_a.at["B09", "status"].startswith("NaN: epoka poza zakresem") and pd.isna(res_a.at["B09", "dh_egms_mm"])
        assert res_a.at["B06", "status"] == epi.at["B06", "status"] and pd.isna(res_a.at["B06", "dh_lev_mm"])

        ids = ["S01", "S02", "S03"]
        res_g = compare_levelling(lev, ep, egms_long, {"type": "stable_group", "ids": ids}, method).set_index("benchmark_id")
        ok_g = res_g[res_g["status"] == "ok"]
        assert set(ok_g.index) == {"B01", "B02", "B03", "B04", "B05", "T01", "T02"}, res_g["status"]
        for b, r in ok_g.iterrows():
            dt = years_since([r["t2"]], r["t1"])[0]
            k1, k2 = epochs[b].index(r["t1"]), epochs[b].index(r["t2"])
            day = lambda s, t: float(np.interp((t - t_egms0).days, (s.index - t_egms0).days.to_numpy(float), s.to_numpy()))
            ref_lev = np.mean([day(h_mm[g], r["t2"]) - day(h_mm[g], r["t1"]) for g in ids])  # niezależnie: np.interp po dniach
            assert abs(r["ref_dh_egms_mm"] - common_mm_yr * dt) < 1e-6 and abs(r["dh_egms_mm"] - rate[b] * dt) < 1e-6, b
            assert abs(r["ref_dh_lev_mm"] - ref_lev) < 1e-6, b
            assert abs(r["diff_mm"] - (rate[b] * dt - (h_mm[b].iloc[k2] - h_mm[b].iloc[k1] - ref_lev))) < 1e-6, b
        assert (ok_g["diff_mm"].abs() < 5.0).all() and ok_g["diff_mm"].abs().median() < 2.5, ok_g["diff_mm"]
        assert res_g.loc[ids, "status"].eq("NaN: reper należy do grupy odniesienia").all()
        assert "reperu odniesienia S01" in res_g.at["B10", "status"] and pd.isna(res_g.at["B10", "dh_lev_mm"])
        for bad_ref in (None, {"type": "benchmark", "id": "S01"}, {"type": "stable_group", "ids": []},
                        {"type": "absolute", "ids": ids}):
            _expect_raises(ValueError, compare_levelling, lev, ep, egms_long, bad_ref, method, match="")
        _expect_raises(ValueError, compare_levelling, lev, ep, egms_long, None, method, match="decyzja autora")
        _expect_raises(ValueError, compare_levelling, lev, ep, egms_long, {"type": "stable_group", "ids": ["S01", "B08"]},
                       method, match="B08")
        _expect_raises(ValueError, compare_levelling, lev, ep, egms_long.assign(reference="S01"), {"type": "absolute"},
                       method, match="niespójne")
        _expect_raises(ValueError, compare_levelling, lev, ep, egms_long, {"type": "absolute"}, "nearest",
                       match="sposób odczytu")
        mixed = egms_long.assign(reference=np.where(egms_long["site"] == "S01", "B05", "absolute"))
        _expect_raises(ValueError, compare_levelling, lev, ep, mixed, {"type": "stable_group", "ids": ids}, method,
                       match="różne odniesienia")
        _expect_raises(ValueError, compare_levelling, lev, ep, egms_long.assign(site="E" + egms_long["site"]),
                       {"type": "absolute"}, method, match="Żaden z")                  # identyfikatory niezgodne
        _expect_raises(ValueError, compare_levelling, lev.assign(height_m=lev["height_m"].where(lev.index != 3)), ep,
                       egms_long, {"type": "absolute"}, method, match="height_m")
        _expect_raises(ValueError, compare_levelling, lev, ep, egms_long.assign(component="LOS"), {"type": "absolute"},
                       method, match="component")

        # 7. Kryteria: odniesienie do grupy stabilnej spełnia progi, ruch wspólny EGMS bez odniesienia - nie.
        th = {"median_abs_dh_mm": 5.0, "sign_min_signal_mm": 6.0, "sign_agreement": 0.90, "stable_max_lev_mm": 2.0,
              "stable_abs_dh_mm": 5.0, "velocity_bias_mm_yr": 1.5}                  # wartości testowe
        sg = summarize_levelling(res_g.reset_index(), th)
        assert list(sg.columns) == SUMMARY_COLUMNS and len(sg) == 6
        assert sg["spełnione"].iloc[:4].tolist() == [True, True, True, True], sg
        assert sg.at[1, "n"] == 4 and sg.at[1, "wynik"].startswith("100%")             # B01-B04: |Δh| >= 6 mm
        assert sg.at[0, "wynik"] == f"{ok_g['diff_mm'].abs().median():.1f} mm" and sg.at[0, "n"] == len(ok_g)
        n_stab = int((ok_g["dh_lev_mm"].abs() <= 2.0).sum())                         # wybór po niwelacji, nie po EGMS
        assert sg.at[2, "n"] == n_stab != int((ok_g["dh_egms_mm"].abs() <= 2.0).sum()), sg
        dv_g = (ok_g["v_egms_dh_mm_yr"] - ok_g["v_lev_mm_yr"]).median()
        assert sg.at[3, "wynik"] == f"mediana {dv_g:+.2f} mm/rok" and abs(float(sg.at[5, "wynik"].split(",")[0]) - 1) < 0.05
        neg = summarize_levelling(res_g.reset_index().assign(v_egms_dh_mm_yr=res_g["v_egms_dh_mm_yr"].to_numpy() - 3.0), th)
        assert neg.at[3, "spełnione"] is False and neg.at[3, "wynik"] == f"mediana {dv_g - 3.0:+.2f} mm/rok", neg  # |bias|
        nan_ok = res_g.reset_index()
        nan_ok.loc[nan_ok["benchmark_id"] == "B01", "dh_egms_mm"] = np.nan
        _expect_raises(ValueError, summarize_levelling, nan_ok, th, match="NaN")
        sa = summarize_levelling(res_a.reset_index(), th)
        bias_a = float((ok_a["v_egms_dh_mm_yr"] - ok_a["v_lev_mm_yr"]).median())
        assert abs(bias_a - common_mm_yr) < 1.0 and sa.at[0, "spełnione"] is False and sa.at[3, "spełnione"] is False, sa
        _expect_raises(ValueError, summarize_levelling, res_g.reset_index(), {**th, "sign_agreement": None},
                       match="sign_agreement")
        _expect_raises(ValueError, summarize_levelling, res_g.reset_index().assign(status="NaN: x"), th, match="'ok'")

        # 8. L2b -> pion: znane E i U odtworzone z orbity wstępującej i zstępującej (N = 0).
        def los_vec(inc_deg, heading_deg):           # kosinusy ziemia -> satelita, patrzenie w prawo (jak prototyp)
            inc, az = np.deg2rad(inc_deg), np.deg2rad(heading_deg + 90.0)
            return (-np.sin(inc) * np.sin(az), -np.sin(inc) * np.cos(az), np.cos(inc))
        va, vd = los_vec(39.0, -10.0), los_vec(41.0, 190.0)
        assert va[0] < 0 < vd[0]                     # A3: przeciwne znaki los_east
        t_ref = pd.Timestamp("2020-01-01")
        da_dates, dd_dates = pd.date_range("2020-01-05", "2024-12-30", freq="12D"), pd.date_range("2020-01-09", "2024-12-30", freq="12D")
        E = lambda d: 2.0 * years_since(d, t_ref)
        U = lambda d: -8.0 * years_since(d, t_ref)
        los_a = pd.Series(va[0] * E(da_dates) + va[2] * U(da_dates), index=da_dates)
        los_d = pd.Series(vd[0] * E(dd_dates) + vd[2] * U(dd_dates), index=dd_dates)
        eps = pd.DatetimeIndex(["2020-06-15", "2022-06-15", "2024-06-20"])
        vert = vertical_from_asc_desc(los_a, va, los_d, vd, eps, method, 10.0)
        assert np.allclose(vert["east_mm"], E(eps), atol=1e-9) and np.allclose(vert["up_mm"], U(eps), atol=1e-9), vert
        assert (vert["assumption"] == "north=0").all() and vert["cond"].iat[0] < 2.0
        _expect_raises(ValueError, vertical_from_asc_desc, los_a, va, los_d, los_vec(39.5, -10.0), eps, method, 10.0,
                       match="prawie równoległe")
        _expect_raises(ValueError, vertical_from_asc_desc, los_a, va, los_d, vd, ["2025-03-01"], method, 10.0,
                       match="poza zakresem")

        # 9. Przeniesione funkcje: odczyt bez ekstrapolacji, statystyki odporne.
        _expect_raises(ValueError, read_at_epochs, los_a, ["2019-12-01"], method, match="poza zakresem")
        _expect_raises(ValueError, read_at_epochs, los_a, ["2021-01-01"], "nearest", match="sposób odczytu")
        rs = robust_stats(np.array([1.0, 2.0, 3.0, 4.0, 100.0, np.nan]))
        assert rs["n"] == 5 and rs["median"] == 3.0 and abs(rs["mad_sigma"] - MAD_TO_SIGMA) < 1e-12

        print(json.dumps({"gnss_groups": dict(zip(st["site"], st["group"])),
                          "absolute_median_abs_diff_mm": float(ok_a["diff_mm"].abs().median()),
                          "absolute_velocity_bias_mm_yr": bias_a,
                          "stable_group_median_abs_diff_mm": float(ok_g["diff_mm"].abs().median()),
                          "asc_desc_cond": float(vert["cond"].iat[0])}, ensure_ascii=False, indent=1))
        print(sg.to_string(index=False))
    # Podział informacyjny i najbliższa stacja (wartości testowe o znanej odpowiedzi).
    rg = pd.DataFrame({"benchmark_id": ["a", "b", "c", "d", "e"], "status": ["ok", "ok", "ok", "ok", "NaN: x"],
                       "dh_lev_mm": [-60.0, -40.0, 3.0, -1.0, np.nan], "dh_egms_mm": [-57.0, -42.0, 1.0, 0.5, np.nan],
                       "dt_yr": [3.0, 2.0, 3.0, 1.0, np.nan]})
    rg["diff_mm"] = rg["dh_egms_mm"] - rg["dh_lev_mm"]
    rg["v_lev_mm_yr"], rg["v_egms_dh_mm_yr"] = rg["dh_lev_mm"] / rg["dt_yr"], rg["dh_egms_mm"] / rg["dt_yr"]
    gr = levelling_groups(rg, 10.0, 6.0).set_index("grupa")
    assert list(gr["n"]) == [4, 2, 2] and gr["n_sign"].iat[1] == 2 and gr["sign_agreement"].iat[1] == 1.0, gr
    assert gr["median_abs_diff_mm"].iat[1] == 2.5 and np.isnan(gr["sign_agreement"].iat[2]) and np.isnan(gr["slope"].iat[1]), gr
    assert abs(gr["slope"].iat[0] - np.polyfit([-60, -40, 3, -1], [-57, -42, 1, 0.5], 1)[0]) < 1e-12
    assert gr["dist_station_km_min"].isna().all()                    # bez kolumny odległości: NaN, nie zero
    _expect_raises(ValueError, levelling_groups, rg.assign(status="NaN: x"), 10.0, 6.0, match="Brak reperów")
    _expect_raises(ValueError, levelling_groups, rg, 0.0, 6.0, match="dodatnie")
    _expect_raises(ValueError, levelling_groups, rg, None, 6.0, match="strong_mm_yr")
    x0, y0 = transform_xy(np.array([6.5]), np.array([51.0]), 4326, 3035)
    pts = pd.DataFrame({"id": ["p1", "p2"], "x_3035": [x0[0], x0[0] + 30000.0], "y_3035": [y0[0], y0[0]]})
    sx, sy = transform_xy(np.array([x0[0] + 5000.0, x0[0] + 31000.0]), np.array([y0[0], y0[0]]), 3035, 4326)
    st_ = pd.DataFrame({"site": ["NEAR", "FAR", "SYDN"], "lon_deg": [sx[0], sx[1], 151.2], "lat_deg": [sy[0], sy[1], -33.9]})
    ns = nearest_station_km(pts, st_)
    assert list(ns["nearest_station"]) == ["NEAR", "FAR"] and np.allclose(ns["dist_station_km"], [5.0, 1.0], atol=1e-6), ns
    _expect_raises(ValueError, nearest_station_km, pts, st_.iloc[2:], match="Żadnej stacji")
    _expect_raises(ValueError, nearest_station_km, pts, st_.assign(lat_deg=np.nan), match="bez współrzędnych")
    gd = levelling_groups(rg.assign(dist_station_km=[12.0, 8.0, 30.0, 20.0, np.nan]), 10.0, 6.0)
    assert (gd["dist_station_km_min"] == [8.0, 8.0, 20.0]).all() and gd["dist_station_km_median"].iat[1] == 10.0, gd
    _expect_raises(ValueError, levelling_groups, rg.assign(dist_station_km=[12.0, np.nan, 30.0, 20.0, 1.0]), 10.0, 6.0,
                   match="brak odległości")
    # Format oficjalny (Datenformatbeschreibung HFP NRW, 07/2023): przykład z dokumentu, bez nagłówka, UTF-8,
    # średnik w nazwie w cudzysłowie, Ostwert z prefiksem strefy 32 i samym przecinkiem; EPSG:4647 -> okolice Lotte.
    with tempfile.TemporaryDirectory() as td_doc:
        pd_ = Path(td_doc) / "hfp_pl.csv"
        pd_.write_text('3613900015;"Halen,Everskamp 20";32428124,;5799122,;54,542;981290,8\n'
                       '3613900118;"Westerbeck;Tegelstr.4";32421085,300;5798465,200;57,486;981288,7\n', encoding="utf-8")
        sd_ = Path(td_doc) / "hfp_plzf.csv"
        sd_.write_text("3613900015;01.06.1977;54,541\n3613900015;30.08.1983;54,542\n3613900015;19.08.2010;54,542\n"
                       "3613900118;01.06.1968;57,491\n3613900118;08.09.2015;57,486\n", encoding="utf-8")
        pts_doc = read_nrw_points(pd_, "utf-8")
        assert list(pts_doc["Punktkennzeichen"]) == ["3613900015", "3613900118"]
        assert pts_doc.loc[1, "Name des Punktes"] == "Westerbeck;Tegelstr.4" and pts_doc.loc[0, "Ostwert"] == 32428124.0
        ser_doc = read_nrw_timeseries(sd_, "utf-8")
        assert len(ser_doc) == 5 and np.isclose(ser_doc["Höhe"].iloc[0], 54.541)
        from pyproj import Transformer
        lon_d, lat_d = Transformer.from_crs(4647, 4326, always_xy=True).transform(32428124.0, 5799122.0)
        assert abs(lon_d - 7.945) < 0.01 and abs(lat_d - 52.338) < 0.01, (lon_d, lat_d)
    print("SELFTEST step_06_ground OK")


def describe_nrw(points_path: Path, series_path: Path, encoding: str) -> None:
    """Opis prawdziwych plików NRW bez obliczeń: liczby reperów, zakres dat, epoki w latach, zakres Ostwert/Nordwert."""
    pts, ser = read_nrw_points(points_path, encoding), read_nrw_timeseries(series_path, encoding)
    print(json.dumps({"n_points": len(pts), "n_benchmarks_in_series": int(ser["Punktkennzeichen"].nunique()),
                      "n_rows_series": len(ser), "first_date": str(ser["Messungsdatum"].min().date()),
                      "last_date": str(ser["Messungsdatum"].max().date()),
                      "rows_per_year": {int(k): int(v) for k, v in ser["Messungsdatum"].dt.year.value_counts().sort_index().items()},
                      "ostwert_range_m": [float(pts["Ostwert"].min()), float(pts["Ostwert"].max())],
                      "nordwert_range_m": [float(pts["Nordwert"].min()), float(pts["Nordwert"].max())]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="EGMS Check - KROK 6")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--describe-nrw", nargs=3, metavar=("PUNKTLISTE", "ZEITFOLGE", "ENCODING"),
                    help="opis plików niwelacji NRW (bez obliczeń)")
    a = ap.parse_args()
    if a.selftest:
        _selftest()
    elif a.describe_nrw:
        describe_nrw(Path(a.describe_nrw[0]), Path(a.describe_nrw[1]), a.describe_nrw[2])
    else:
        ap.print_help()
