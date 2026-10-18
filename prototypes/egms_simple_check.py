"""
================================================================================
EGMS Check - PROTOTYP: PROSTY EKSPERYMENT E1 (GNSS) I E2 (NIWELACJA)
================================================================================
Prototyp metody z docs/plans/Plan_v1_eksperymenty.md. Jeden kod dla obu eksperymentów
(CLAUDE.md, zasada 11): wczytanie EGMS, kontrole konwencji, wybór przestrzenny, dopasowanie
czasowe, prędkości i metryki są wspólne; różni się tylko czytnik pomiaru naziemnego
i sposób odniesienia (E1: rzut GNSS na LOS; E2: różnice względem reperu odniesienia).

  I.   Czytniki: EGMS CSV (L2a/L2b/L3), szereg GNSS PANGAEA, tabela niwelacji (format długi).
  II.  Kontrole konwencji A1-A3 i duplikaty z zakładek burstów (F4, sekcja 2; Hrysiewicz i in. 2024).
  III. Wybór przestrzenny w EPSG:3035 i szereg EGMS w miejscu pomiaru (Koudogbo 2025; Fabris i Nazari 2026).
  IV.  Dopasowanie czasowe, pokrycie A6, prędkość (liniowa lub liniowa + sinusoida roczna).
  V.   Metryki: różnica prędkości, odchylenie różnic szeregów, korelacja, łączne sigma (Even i in. 2024, wzór 1).
  VI.  E1: GNSS -> LOS -> porównanie. E2: odniesienie do reperu, odczyt w epokach, test prognozy.
  VII. --selftest (dane syntetyczne o znanej odpowiedzi) i --describe-gnss (opis prawdziwego PTO1.txt).

To jest PROTOTYP do przeniesienia w sesjach 1-5 do step_02/step_03/step_04 (układ AgriWatch).
Parametry eksperymentu nie mają wartości domyślnych w sygnaturach; pochodzą z CONFIG.
Przebieg na prawdziwych danych EGMS wymaga CONFIG["status"] == "APPROVED" (progi i decyzje
zatwierdzone przed obliczeniami, CLAUDE.md, zasada 9).

Konwencje: przemieszczenia w mm, prędkości w mm/rok, ujemne = osiadanie / oddalanie od satelity.
Układy: EGMS EPSG:3035 (easting, northing), GNSS stopnie WGS84, NRW EPSG:25832, RD EPSG:28992.
================================================================================
"""

import argparse
import json
import logging
import re
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger("EGMSCheck_Prototype")

MM_PER_M = 1000.0
DAYS_PER_YEAR = 365.25          # rok juliański; do czasu w latach dziesiętnych w modelu prędkości
MAD_TO_SIGMA = 1.4826           # MAD -> odchylenie przy rozkładzie normalnym (Even i in. 2024)

# ==============================================================================
# KONFIGURACJA (jedno miejsce; docelowo CHECK_CONFIG w step_05_colab_run.py)
# Wartości None = decyzja autora jeszcze niepodjęta (Plan_v1_otwarte_pytania.md, sekcja D).
# ==============================================================================
CONFIG = {
    "status": "PROPOSED",   # "APPROVED" dopiero po wpisie w protokole Plan_v1_test_EGMS.md
    "e1": {
        "gnss_file": "data/02_Raw_Ground/1_gnss_pangaea/PTO1.txt",
        "egms_files": {},                   # {"117": "data/01_Raw_EGMS/<wydanie>/L2b/...csv", ...}
        "egms_release": None,               # D-A
        "buffer_radii_m": [100, 200],       # Koudogbo 2025 (100 m); Fabris i Nazari 2026 (200 m)
        "min_points": None,                 # EEA: 3
        "height_filter_m": None,            # (min, max) albo "none"; decyzja autora
        "buffer_statistic": None,           # "mean" | "median"
        "gnss_window_half_days": None,      # Koudogbo 2025: okno 12 dni -> połowa 6 dni
        "gnss_aggregation": None,           # "mean" | "median" w oknie wokół daty EGMS
        "window": None,                     # ("YYYY-MM-DD", "YYYY-MM-DD")
        "reference": None,                  # "first_common_date" | "YYYY-MM-DD"
        "velocity_model": None,             # "linear" | "linear_annual"
        "min_overlap_fraction": 0.85,       # White Paper, rozdz. 4.1
        "duplicate_distance_m": 1.0,        # nasza heurystyka (Plan_v1_wdrozenie.md, N10)
        "duplicate_rule": None,             # "report_only" | "drop_later_file"
        "thresholds": {"abs_velocity_diff_mm_yr": 1.5, "series_diff_std_mm": 5.0},
    },
    "e2": {
        "levelling_file": None,             # format długi: benchmark_id, x, y, epoch_date, height_m
        "levelling_crs_epsg": None,         # 25832 (NRW) | 28992 (Hengelo)
        "egms_l3_file": None,
        "egms_release": None,
        "forecast_l3_file": None,           # wcześniejsze wydanie do testu prognozy (opcjonalnie)
        "reference": None,                  # {"benchmark": "<id>"} | {"stable_group": ["<id>", ...]}
        "epoch_pairs": None,                # [("t1", "t2"), ...] daty epok jako "YYYY-MM-DD"
        "epoch_reading": None,              # "linear_interpolation" (jedyny zaimplementowany)
        "velocity_model": None,
        "thresholds": {"median_abs_dh_mm": 5.0, "sign_agreement": 0.90, "min_signal_mm": 6.0,
                       "forecast_median_abs_mm": 3.0, "stable_abs_dh_mm": 5.0, "stable_max_lev_mm": 2.0},
    },
}


def require(cfg: dict, key: str):
    """Klucz konfiguracji musi istnieć i mieć wartość (bez wartości zastępczych)."""
    value = cfg[key]
    if value is None:
        raise ValueError(f"CONFIG: '{key}' nie ma wartości - decyzja autora (Plan_v1_otwarte_pytania.md, sekcja D).")
    return value


# ==============================================================================
# I. CZYTNIKI
# ==============================================================================
DATE_COL = re.compile(r"^\d{8}$")
L2_REQUIRED = ["pid", "easting", "northing", "height", "mean_velocity", "los_east", "los_north",
               "los_up", "incidence_angle"]
L3_REQUIRED = ["pid", "easting", "northing", "mean_velocity"]


def read_egms_csv(path: Path, level: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Plik CSV EGMS -> (atrybuty punktów, szeregi w mm: wiersze = daty, kolumny = pid).
    Kolumny wg Product Description (docs/evidence/F5, sekcja 1). Brak kolumny = wyjątek.
    """
    df = pd.read_csv(path)
    required = L2_REQUIRED if level in ("L2a", "L2b") else L3_REQUIRED
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"{path}: brak kolumn {missing} (poziom {level})")
    date_cols = [c for c in df.columns if DATE_COL.match(str(c))]
    if len(date_cols) < 2:
        raise ValueError(f"{path}: za mało kolumn dat yyyymmdd ({len(date_cols)})")
    if df["pid"].duplicated().any():
        raise ValueError(f"{path}: zdublowane pid w jednym pliku")
    points = df.drop(columns=date_cols).copy()
    points["source_file"] = Path(path).name
    series = df.set_index("pid")[date_cols].T
    series.index = pd.to_datetime(series.index, format="%Y%m%d")
    series.index.name = "date"
    return points, series.astype(float)


def read_pangaea_gnss(path: Path) -> tuple[pd.DataFrame, float, float]:
    """
    Szereg dobowy PANGAEA (Pintori i Serpelloni 2023): czas [rok dziesiętny], Up [mm], sigma [mm],
    nazwa, długość, szerokość. Zwraca (szereg, lon, lat); współrzędne muszą być stałe w pliku.
    """
    df = pd.read_csv(path, sep=r"\s+", comment="*", header=None,
                     names=["t_decyear", "up_mm", "sigma_mm", "site", "lon_deg", "lat_deg"])
    if df.empty:
        raise ValueError(f"{path}: pusty plik")
    if df["lon_deg"].nunique() != 1 or df["lat_deg"].nunique() != 1:
        raise ValueError(f"{path}: współrzędne stacji zmieniają się w pliku")
    if not df["t_decyear"].is_monotonic_increasing:
        raise ValueError(f"{path}: czas nie rośnie monotonicznie")
    df["date"] = decyear_to_datetime(df["t_decyear"].to_numpy())
    return df[["date", "t_decyear", "up_mm", "sigma_mm"]], float(df["lon_deg"].iat[0]), float(df["lat_deg"].iat[0])


def read_levelling_long(path: Path) -> pd.DataFrame:
    """Tabela niwelacji w formacie długim: benchmark_id, x, y, epoch_date, height_m (wysokość w m)."""
    df = pd.read_csv(path, dtype={"benchmark_id": str})
    missing = [c for c in ["benchmark_id", "x", "y", "epoch_date", "height_m"] if c not in df.columns]
    if missing:
        raise KeyError(f"{path}: brak kolumn {missing}")
    df["epoch_date"] = pd.to_datetime(df["epoch_date"])
    if df.duplicated(["benchmark_id", "epoch_date"]).any():
        raise ValueError(f"{path}: zdublowana para (reper, epoka)")
    return df


def decyear_to_datetime(t: np.ndarray) -> pd.DatetimeIndex:
    """Rok dziesiętny -> data (ułamek roku względem liczby dni w danym roku kalendarzowym)."""
    year = np.floor(t).astype(int)
    start = pd.to_datetime([f"{y}-01-01" for y in year])
    days_in_year = np.where(pd.DatetimeIndex(start).is_leap_year, 366.0, 365.0)
    return pd.DatetimeIndex(start + pd.to_timedelta((t - year) * days_in_year, unit="D"))


def to_years(dates: pd.DatetimeIndex, t0: pd.Timestamp) -> np.ndarray:
    """Czas w latach od t0 (rok juliański)."""
    return np.asarray((pd.DatetimeIndex(dates) - t0) / pd.Timedelta(days=1), dtype=float) / DAYS_PER_YEAR


def transform_xy(x, y, epsg_from: int, epsg_to: int):
    """Przeliczenie współrzędnych (pyproj, kolejność x/y zawsze lon/lat lub easting/northing)."""
    from pyproj import Transformer
    tr = Transformer.from_crs(epsg_from, epsg_to, always_xy=True)
    return tr.transform(x, y)


# ==============================================================================
# II. KONTROLE KONWENCJI I DUPLIKATY
# ==============================================================================
def check_los_vector(points: pd.DataFrame, tol_norm: float, tol_cos: float) -> dict:
    """A1: |norma - 1| <= tol; A2: |los_up - cos(incidence)| <= tol. Zwraca wyniki liczbowo."""
    norm = np.sqrt(points["los_east"] ** 2 + points["los_north"] ** 2 + points["los_up"] ** 2)
    cos_inc = np.cos(np.deg2rad(points["incidence_angle"]))
    a1 = float(np.max(np.abs(norm - 1.0)))
    a2 = float(np.max(np.abs(points["los_up"] - cos_inc)))
    return {"A1_max_abs_norm_minus_1": a1, "A1_pass": a1 <= tol_norm,
            "A2_max_abs_losup_minus_cosinc": a2, "A2_pass": a2 <= tol_cos,
            "los_up_positive": bool((points["los_up"] > 0).all())}


def check_east_sign(points_asc: pd.DataFrame, points_desc: pd.DataFrame) -> dict:
    """A3: znak los_east przeciwny dla orbity wstępującej i zstępującej (geometria Sentinel-1)."""
    s_asc = np.sign(points_asc["los_east"].median())
    s_desc = np.sign(points_desc["los_east"].median())
    return {"A3_sign_asc": float(s_asc), "A3_sign_desc": float(s_desc), "A3_pass": bool(s_asc == -s_desc != 0)}


def find_cross_file_duplicates(points: pd.DataFrame, max_dist_m: float) -> pd.DataFrame:
    """
    Pary punktów z RÓŻNYCH plików (burstów) bliżej niż max_dist_m. Heurystyka odległościowa;
    EGMS-toolkit robi to inaczej (otoczka wklęsła, przypisanie zakładki do jednego burstu).
    """
    xy = points[["easting", "northing"]].to_numpy()
    src = points["source_file"].to_numpy()
    rows = []
    order = np.argsort(xy[:, 0])            # przemiatanie po easting: O(n log n + par w pasie)
    for a_pos, i in enumerate(order):
        for j in order[a_pos + 1:]:
            if xy[j, 0] - xy[i, 0] > max_dist_m:
                break
            if src[i] != src[j] and np.hypot(*(xy[j] - xy[i])) < max_dist_m:
                rows.append((points["pid"].iat[i], src[i], points["pid"].iat[j], src[j]))
    return pd.DataFrame(rows, columns=["pid_a", "file_a", "pid_b", "file_b"])


# ==============================================================================
# III. WYBÓR PRZESTRZENNY I SZEREG EGMS W MIEJSCU POMIARU
# ==============================================================================
def select_buffer(points: pd.DataFrame, x0: float, y0: float, radius_m: float,
                  height_filter_m) -> pd.DataFrame:
    """Punkty w promieniu radius_m od (x0, y0) w EPSG:3035, z kolumną distance_m."""
    d = np.hypot(points["easting"] - x0, points["northing"] - y0)
    sel = points.assign(distance_m=d)[d <= radius_m]
    if height_filter_m != "none":
        lo, hi = height_filter_m
        sel = sel[(sel["height"] >= lo) & (sel["height"] <= hi)]
    return sel


def buffer_series(series: pd.DataFrame, pids, statistic: str, min_points: int) -> pd.DataFrame:
    """Statystyka przemieszczeń punktów bufora dla każdej daty + rozrzut i liczba punktów."""
    sub = series[list(pids)]
    n = sub.notna().sum(axis=1)
    if statistic == "mean":
        centre = sub.mean(axis=1)
    elif statistic == "median":
        centre = sub.median(axis=1)
    else:
        raise ValueError(f"Nieznana statystyka bufora: {statistic}")
    out = pd.DataFrame({"value_mm": centre, "spread_mm": sub.std(axis=1, ddof=1), "n": n})
    out.loc[out["n"] < min_points, ["value_mm", "spread_mm"]] = np.nan   # jawny NaN, nie zero
    return out


def cell_containing(points: pd.DataFrame, x0: float, y0: float, cell_m: float) -> pd.Series:
    """Komórka L3 (środek siatki) zawierająca punkt; brak komórki = None (bez szukania dalej)."""
    half = cell_m / 2.0
    hit = points[(np.abs(points["easting"] - x0) <= half) & (np.abs(points["northing"] - y0) <= half)]
    if len(hit) > 1:
        raise ValueError(f"Więcej niż jedna komórka L3 zawiera punkt ({x0:.1f}, {y0:.1f})")
    return None if hit.empty else hit.iloc[0]


# ==============================================================================
# IV. CZAS: AGREGACJA GNSS, POKRYCIE, PRĘDKOŚĆ
# ==============================================================================
def gnss_at_dates(gnss: pd.DataFrame, value_col: str, dates: pd.DatetimeIndex,
                  half_window_days: float, aggregation: str) -> pd.Series:
    """Wartość GNSS w dacie EGMS: średnia/mediana dób w oknie +-half_window_days; brak dób = NaN."""
    agg = {"mean": np.mean, "median": np.median}[aggregation]     # KeyError przy nieznanej agregacji
    t = gnss["date"].to_numpy()
    v = gnss[value_col].to_numpy()
    out = np.full(len(dates), np.nan)
    for k, d in enumerate(pd.DatetimeIndex(dates)):
        m = np.abs((t - d.to_datetime64()) / np.timedelta64(1, "D")) <= half_window_days
        if m.any():
            out[k] = agg(v[m])
    return pd.Series(out, index=pd.DatetimeIndex(dates))


def coverage(egms_dates: pd.DatetimeIndex, ground_dates: pd.DatetimeIndex,
             gnss_at_egms: pd.Series) -> dict:
    """
    A6 w dwóch definicjach (D-B): (a) długość wspólnego okna / okres wydania EGMS;
    (b) odsetek dat EGMS we wspólnym oknie, dla których jest wartość GNSS.
    """
    e0, e1 = egms_dates.min(), egms_dates.max()
    g0, g1 = ground_dates.min(), ground_dates.max()
    o0, o1 = max(e0, g0), min(e1, g1)
    span = max((o1 - o0) / pd.Timedelta(days=1), 0.0)
    frac_a = span / ((e1 - e0) / pd.Timedelta(days=1))
    in_win = (egms_dates >= o0) & (egms_dates <= o1)
    frac_b = float(gnss_at_egms[in_win].notna().mean()) if in_win.any() else 0.0
    return {"overlap_start": str(o0.date()), "overlap_end": str(o1.date()),
            "fraction_of_release": float(frac_a), "fraction_dates_with_ground": frac_b}


def fit_velocity(dates: pd.DatetimeIndex, y_mm: np.ndarray, model: str) -> dict:
    """
    Prędkość MNK. model: "linear" (a + v t) albo "linear_annual" (+ sin/cos 2 pi t).
    sigma_v formalna przy szumie białym; dla GNSS jest zaniżona (szum skorelowany, F4, sekcja 8).
    """
    m = np.isfinite(y_mm)
    if m.sum() < 3:
        raise ValueError(f"Za mało obserwacji do prędkości: {int(m.sum())}")
    t = to_years(pd.DatetimeIndex(dates)[m], pd.DatetimeIndex(dates)[m][0])
    cols = [np.ones_like(t), t]
    if model == "linear_annual":
        cols += [np.sin(2 * np.pi * t), np.cos(2 * np.pi * t)]
    elif model != "linear":
        raise ValueError(f"Nieznany model prędkości: {model}")
    A = np.column_stack(cols)
    coef, *_ = np.linalg.lstsq(A, y_mm[m], rcond=None)
    resid = y_mm[m] - A @ coef
    dof = len(resid) - A.shape[1]
    s2 = float(resid @ resid) / dof
    cov = s2 * np.linalg.inv(A.T @ A)
    out = {"v_mm_yr": float(coef[1]), "sigma_v_formal_mm_yr": float(np.sqrt(cov[1, 1])),
           "rms_resid_mm": float(np.sqrt(s2)), "n": int(m.sum())}
    if model == "linear_annual":
        out["annual_amp_mm"] = float(np.hypot(coef[2], coef[3]))
    return out


# ==============================================================================
# V. METRYKI
# ==============================================================================
def compare_series(egms_mm: pd.Series, ground_mm: pd.Series) -> dict:
    """Różnica szeregów po odjęciu średniego przesunięcia (różne odniesienia): std, RMS, korelacja."""
    both = pd.concat([egms_mm, ground_mm], axis=1, keys=["egms", "ground"]).dropna()
    if len(both) < 3:
        raise ValueError(f"Za mało wspólnych dat: {len(both)}")
    d = both["egms"] - both["ground"]
    d = d - d.mean()
    return {"series_diff_std_mm": float(d.std(ddof=1)), "series_diff_rms_mm": float(np.sqrt((d ** 2).mean())),
            "corr": float(np.corrcoef(both["egms"], both["ground"])[0, 1]), "n_dates": int(len(both))}


def robust_stats(x: np.ndarray) -> dict:
    """Mediana i MAD x 1,4826 (Even i in. 2024) oraz średnia i odchylenie."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    med = float(np.median(x))
    return {"n": int(x.size), "median": med, "mad_sigma": float(MAD_TO_SIGMA * np.median(np.abs(x - med))),
            "mean": float(x.mean()), "std": float(x.std(ddof=1)) if x.size > 1 else np.nan}


def pooled_sigma(diff_by_point: dict) -> float:
    """
    Łączne odchylenie różnic przemieszczeń (Even i in. 2024, wzór 1):
    sigma = sqrt( sum_P (N_P - 1) sigma_P^2 / (N - 1) ),  N = sum_P N_P, sigma_P z różnic w punkcie P
    po odjęciu średniej (zbiory mają różne odniesienia).
    """
    num, n_total = 0.0, 0
    for diffs in diff_by_point.values():
        d = np.asarray(diffs, float)
        d = d[np.isfinite(d)]
        if d.size < 2:
            continue
        num += (d.size - 1) * np.var(d, ddof=1)
        n_total += d.size
    if n_total < 2:
        raise ValueError("pooled_sigma: za mało obserwacji")
    return float(np.sqrt(num / (n_total - 1)))


# ==============================================================================
# VI. EKSPERYMENTY
# ==============================================================================
def run_e1_track(gnss: pd.DataFrame, x0: float, y0: float, points: pd.DataFrame, series: pd.DataFrame,
                 radius_m: float, c: dict) -> dict:
    """E1 dla jednej ścieżki i jednego bufora: GNSS (pion) -> LOS, porównanie z szeregiem EGMS."""
    sel = select_buffer(points, x0, y0, radius_m, c["height_filter_m"])
    if len(sel) < c["min_points"]:
        return {"radius_m": radius_m, "n_points": len(sel), "status": "NaN: za mało punktów w buforze"}
    los_up = float(sel["los_up"].mean())       # rzut samego pionu: d_LOS = U * los_up (Fabris i Nazari 2026, wzór 1)
    egms = buffer_series(series, sel["pid"], c["buffer_statistic"], c["min_points"])["value_mm"]
    g_los = gnss.assign(los_mm=gnss["up_mm"] * los_up)
    g_at = gnss_at_dates(g_los, "los_mm", egms.index, c["gnss_window_half_days"], c["gnss_aggregation"])
    cov = coverage(egms.index, pd.DatetimeIndex(gnss["date"]), g_at)

    w0, w1 = (pd.Timestamp(s) for s in c["window"])
    win = (egms.index >= w0) & (egms.index <= w1)
    e, g = egms[win], g_at[win]
    common = e.notna() & g.notna()
    if not common.any():
        return {"radius_m": radius_m, "status": "NaN: brak wspólnych dat w oknie", **cov}
    ref = e.index[common][0] if c["reference"] == "first_common_date" else pd.Timestamp(c["reference"])
    if not common.get(ref, False):
        raise ValueError(f"Data odniesienia {ref.date()} nie jest wspólną datą obu szeregów")
    e, g = e - e[ref], g - g[ref]
    ve = fit_velocity(e.index, e.to_numpy(), c["velocity_model"])
    vg = fit_velocity(g.index, g.to_numpy(), c["velocity_model"])
    out = {"radius_m": radius_m, "n_points": len(sel), "los_up_mean": los_up,
           "incidence_mean_deg": float(sel["incidence_angle"].mean()),
           "mean_velocity_attr_mm_yr": float(sel["mean_velocity"].mean()),
           "v_egms_mm_yr": ve["v_mm_yr"], "v_gnss_los_mm_yr": vg["v_mm_yr"],
           "dv_gnss_minus_egms_mm_yr": vg["v_mm_yr"] - ve["v_mm_yr"],   # konwencja Fabris i Nazari 2026
           **compare_series(e, g), **cov, "status": "ok"}
    th = c["thresholds"]
    out["pass_velocity"] = abs(out["dv_gnss_minus_egms_mm_yr"]) <= th["abs_velocity_diff_mm_yr"]
    out["pass_series"] = out["series_diff_std_mm"] <= th["series_diff_std_mm"]
    out["pass_A6"] = min(cov["fraction_of_release"], cov["fraction_dates_with_ground"]) >= c["min_overlap_fraction"]
    return out


def read_at_epochs(series_mm: pd.Series, epochs: list, method: str) -> pd.Series:
    """Odczyt szeregu w datach epok; tylko interpolacja wewnątrz danych (bez ekstrapolacji)."""
    if method != "linear_interpolation":
        raise ValueError(f"Nieznany sposób odczytu w epoce: {method}")
    s = series_mm.dropna()
    t0 = s.index[0]
    t = to_years(s.index, t0)               # jednostka niezależna od rozdzielczości dat w pandas
    out = {}
    for ep in epochs:
        ep = pd.Timestamp(ep)
        if ep < s.index[0] or ep > s.index[-1]:
            raise ValueError(f"Epoka {ep.date()} poza zakresem szeregu EGMS {s.index[0].date()}-{s.index[-1].date()}")
        out[ep] = float(np.interp(to_years(pd.DatetimeIndex([ep]), t0)[0], t, s.to_numpy()))
    return pd.Series(out)


def run_e2(lev: pd.DataFrame, l3_points: pd.DataFrame, l3_series: pd.DataFrame, c: dict, cell_m: float) -> pd.DataFrame:
    """
    E2: Delta h z niwelacji i z EGMS L3 (pion) względem reperu/grupy odniesienia, dla par epok.
    lev musi mieć kolumny x_3035, y_3035. Wynik: wiersz na (reper, para epok).
    """
    ref = c["reference"]
    ref_ids = [ref["benchmark"]] if "benchmark" in ref else list(ref["stable_group"])
    cells = {}
    for bid, g in lev.groupby("benchmark_id"):
        cell = cell_containing(l3_points, g["x_3035"].iat[0], g["y_3035"].iat[0], cell_m)
        cells[bid] = None if cell is None else cell["pid"]
    ref_cells = [cells[b] for b in ref_ids if cells.get(b) is not None]
    if not ref_cells:
        raise ValueError("Brak komórki EGMS przy reperze/grupie odniesienia - decyzja autora (D5)")
    d_ref = l3_series[ref_cells].mean(axis=1)
    h = lev.pivot(index="epoch_date", columns="benchmark_id", values="height_m") * MM_PER_M
    h_ref = h[ref_ids].mean(axis=1)
    rows = []
    for t1, t2 in c["epoch_pairs"]:
        t1, t2 = pd.Timestamp(t1), pd.Timestamp(t2)
        for bid in h.columns:
            if bid in ref_ids:
                continue
            row = {"benchmark_id": bid, "t1": t1.date(), "t2": t2.date(), "egms_pid": cells[bid]}
            dh_lev = (h.at[t2, bid] - h_ref[t2]) - (h.at[t1, bid] - h_ref[t1])
            row["dh_lev_mm"] = float(dh_lev)
            if cells[bid] is None:
                row.update(dh_egms_mm=np.nan, status="NaN: brak komórki L3 przy reperze")
            else:
                rel = l3_series[cells[bid]] - d_ref                     # d_rel(t) = d_P(t) - d_ref(t)
                at = read_at_epochs(rel, [t1, t2], c["epoch_reading"])
                row.update(dh_egms_mm=float(at[t2] - at[t1]), status="ok")
            rows.append(row)
    out = pd.DataFrame(rows)
    out["diff_egms_minus_lev_mm"] = out["dh_egms_mm"] - out["dh_lev_mm"]
    return out


def summarize_e2(res: pd.DataFrame, th: dict) -> dict:
    """Kryteria T2 poziomu 1 (Plan_v1_kryteria_akceptacji.md, sekcja C) na wynikach run_e2."""
    ok = res[res["status"] == "ok"]
    stats = robust_stats(ok["diff_egms_minus_lev_mm"].abs().to_numpy())
    signal = ok[ok["dh_lev_mm"].abs() >= th["min_signal_mm"]]
    sign_agree = float((np.sign(signal["dh_egms_mm"]) == np.sign(signal["dh_lev_mm"])).mean()) if len(signal) else np.nan
    stable = ok[ok["dh_lev_mm"].abs() <= th["stable_max_lev_mm"]]
    stable_med = float(stable["dh_egms_mm"].abs().median()) if len(stable) else np.nan
    slope = np.polyfit(ok["dh_lev_mm"], ok["dh_egms_mm"], 1)[0] if len(ok) >= 3 else np.nan
    return {"n_benchmarks_ok": len(ok), "n_without_egms": int((res["status"] != "ok").sum()),
            "median_abs_diff_mm": stats["median"], "pass_median": stats["median"] <= th["median_abs_dh_mm"],
            "n_signal": len(signal), "sign_agreement": sign_agree,
            "pass_sign": bool(sign_agree >= th["sign_agreement"]) if len(signal) else None,
            "n_stable": len(stable), "stable_median_abs_egms_mm": stable_med,
            "pass_stable": bool(stable_med <= th["stable_abs_dh_mm"]) if len(stable) else None,
            "slope_egms_vs_lev": float(slope)}


# ==============================================================================
# VII. TEST OFFLINE I OPIS DANYCH
# ==============================================================================
def _synthetic_l2(rng, n, x0, y0, radius, incidence_deg, heading_deg, ascending, v_up, amp, noise, dates, fname):
    """Syntetyczny plik L2b: ruch czysto pionowy v_up [mm/rok] + sezonowość + szum, znany wektor LOS."""
    r = radius * np.sqrt(rng.uniform(0, 1, n))
    a = rng.uniform(0, 2 * np.pi, n)
    inc = np.deg2rad(incidence_deg + rng.normal(0, 0.2, n))
    # Kosinusy kierunkowe ziemia -> satelita; satelita patrzy w prawo od kierunku lotu.
    look_az = np.deg2rad(heading_deg + 90.0)
    los_e = -np.sin(inc) * np.sin(look_az)
    los_n = -np.sin(inc) * np.cos(look_az)
    los_u = np.cos(inc)
    t = to_years(dates, dates[0])
    disp = (v_up * t + amp * np.sin(2 * np.pi * t))[None, :] * los_u[:, None] + rng.normal(0, noise, (n, len(dates)))
    disp -= disp[:, :1]
    df = pd.DataFrame({"pid": [f"{fname}_{i}" for i in range(n)], "easting": x0 + r * np.cos(a),
                       "northing": y0 + r * np.sin(a), "height": rng.uniform(1, 20, n),
                       "mean_velocity": v_up * los_u, "los_east": los_e, "los_north": los_n, "los_up": los_u,
                       "incidence_angle": np.rad2deg(inc)})
    ts = pd.DataFrame(disp, columns=[d.strftime("%Y%m%d") for d in dates])
    return pd.concat([df, ts], axis=1), ("asc" if ascending else "desc")


def _selftest() -> None:
    rng = np.random.default_rng(20261010)
    tmp = Path(tempfile.mkdtemp(prefix="egmscheck_selftest_"))
    dates = pd.date_range("2018-06-12", "2022-07-15", freq="6D")
    x0, y0 = 4_500_000.0, 2_500_000.0
    v_up_true = -5.0

    # 1. Rzut: ruch czysto pionowy i wektor (0,0,1) -> d_LOS = U; ruch wschodni -> przeciwne znaki orbit.
    assert np.isclose(np.dot([0, 0, 1], [0, 0, -7.0]), -7.0)
    l2a, _ = _synthetic_l2(rng, 50, x0, y0, 200, 41, -10, True, v_up_true, 2.0, 2.0, dates, "asc")
    l2d, _ = _synthetic_l2(rng, 50, x0, y0, 200, 41, 190, False, v_up_true, 2.0, 2.0, dates, "desc")
    a3 = check_east_sign(l2a, l2d)
    assert a3["A3_pass"], a3

    # 2. Czytnik + A1/A2 na pliku CSV.
    p = tmp / "EGMS_L2b_117_synth.csv"
    l2a.to_csv(p, index=False)
    pts, ser = read_egms_csv(p, "L2b")
    a12 = check_los_vector(pts, 0.01, 0.01)
    assert a12["A1_pass"] and a12["A2_pass"] and a12["los_up_positive"], a12

    # 3. Duplikaty: kopia 5 punktów w drugim pliku z przesunięciem 0,3 m musi dać 5 par.
    dup = pts.iloc[:5].copy()
    dup["pid"] = dup["pid"] + "_dup"
    dup["easting"] += 0.3
    dup["source_file"] = "other.csv"
    assert len(find_cross_file_duplicates(pd.concat([pts, dup]), 1.0)) == 5

    # 4. E1 na syntetycznym GNSS o tej samej prędkości: dv ~ 0, std różnic mała.
    gdates = pd.date_range("2017-01-01", "2023-01-01", freq="D")
    tg = to_years(gdates, dates[0])
    gnss = pd.DataFrame({"date": gdates, "up_mm": v_up_true * tg + 2.0 * np.sin(2 * np.pi * tg)
                         + rng.normal(0, 8.0, len(gdates))})
    c = {"height_filter_m": "none", "min_points": 3, "buffer_statistic": "median", "gnss_window_half_days": 6,
         "gnss_aggregation": "median", "window": ("2018-06-12", "2022-07-15"), "reference": "first_common_date",
         "velocity_model": "linear_annual", "min_overlap_fraction": 0.85,
         "thresholds": {"abs_velocity_diff_mm_yr": 1.5, "series_diff_std_mm": 5.0}}
    r = run_e1_track(gnss, x0, y0, pts, ser, 200, c)
    expected_v_los = v_up_true * r["los_up_mean"]
    assert abs(r["v_egms_mm_yr"] - expected_v_los) < 0.3, r
    assert abs(r["dv_gnss_minus_egms_mm_yr"]) < 1.0, r
    assert r["pass_A6"], r
    # Kontrola negatywna: GNSS z inną prędkością (-2 mm/rok) musi dać |dv| > 1,5 mm/rok.
    gnss_bad = gnss.assign(up_mm=gnss["up_mm"] - (v_up_true + 2.0) * tg)
    r_bad = run_e1_track(gnss_bad, x0, y0, pts, ser, 200, c)
    assert not r_bad["pass_velocity"], r_bad

    # 5. Pokrycie A6: GNSS kończący się 2021-04-13 przy wydaniu 2018-06..2022-07 -> ok. 69%.
    g_short = gnss[gnss["date"] <= "2021-04-13"]
    cv = coverage(ser.index, pd.DatetimeIndex(g_short["date"]),
                  gnss_at_dates(g_short.assign(los_mm=g_short["up_mm"]), "los_mm", ser.index, 6, "median"))
    assert 0.66 < cv["fraction_of_release"] < 0.72, cv

    # 6. E2: niecka z L3, repery w środkach komórek, niwelacja = prawda + szum 1 mm; odniesienie poza niecką.
    gx, gy = np.meshgrid(np.arange(-500, 501, 100.0), np.arange(-500, 501, 100.0))
    cx, cy = x0 + gx.ravel(), y0 + gy.ravel()
    rate = -14.0 * np.exp(-((gx.ravel() ** 2 + gy.ravel() ** 2) / (2 * 200.0 ** 2)))     # mm/rok
    l3dates = pd.date_range("2020-01-03", "2024-12-27", freq="6D")
    tl = to_years(l3dates, l3dates[0])
    l3 = pd.DataFrame(rate[:, None] * tl[None, :] + rng.normal(0, 1.0, (rate.size, tl.size)),
                      columns=[d.strftime("%Y%m%d") for d in l3dates])
    l3.insert(0, "pid", [f"c{i}" for i in range(rate.size)])
    l3.insert(1, "easting", cx)
    l3.insert(2, "northing", cy)
    l3.insert(3, "mean_velocity", rate)
    p3 = tmp / "EGMS_L3_synth_U.csv"
    l3.to_csv(p3, index=False)
    l3p, l3s = read_egms_csv(p3, "L3")
    epochs = [pd.Timestamp("2020-12-15"), pd.Timestamp("2022-06-15"), pd.Timestamp("2023-12-15")]
    lev_rows = []
    pick = [0, 5, 60, 61, 72, 120]           # komórka 0 = narożnik (odniesienie, ruch ~0)
    for k in pick:
        for ep in epochs:
            tt = to_years(pd.DatetimeIndex([ep]), l3dates[0])[0]
            lev_rows.append({"benchmark_id": f"B{k}", "x_3035": cx[k] + 12.0, "y_3035": cy[k] - 7.0,
                             "epoch_date": ep, "height_m": 10.0 + (rate[k] * tt + rng.normal(0, 1.0)) / MM_PER_M})
    lev = pd.DataFrame(lev_rows)
    c2 = {"reference": {"benchmark": "B0"}, "epoch_pairs": [(epochs[0], epochs[2])],
          "epoch_reading": "linear_interpolation"}
    res = run_e2(lev, l3p, l3s, c2, cell_m=100.0)
    th = CONFIG["e2"]["thresholds"]
    summ = summarize_e2(res, th)
    assert summ["median_abs_diff_mm"] < 3.0 and summ["pass_sign"], summ
    # Odjęcie szeregu odniesienia od samego siebie daje zero.
    assert np.allclose((l3s["c0"] - l3s["c0"]).to_numpy(), 0.0)
    # Brak ekstrapolacji: epoka po końcu danych -> wyjątek.
    try:
        read_at_epochs(l3s["c60"], [pd.Timestamp("2026-01-01")], "linear_interpolation")
        raise AssertionError("Oczekiwano wyjątku dla epoki poza zakresem")
    except ValueError:
        pass
    # Łączne sigma: dwa punkty o stałej różnicy -> 0.
    assert pooled_sigma({"a": [1, 1, 1], "b": [3, 3]}) == 0.0
    # Przeliczenie RD -> 3035 -> RD wraca do punktu w granicach mm (sprawdzane, jeśli jest pyproj).
    xr, yr = 254_000.0, 471_000.0
    x3, y3 = transform_xy(xr, yr, 28992, 3035)
    xb, yb = transform_xy(x3, y3, 3035, 28992)
    assert abs(xb - xr) < 1e-3 and abs(yb - yr) < 1e-3

    print(json.dumps({"E1_synthetic": {k: r[k] for k in ("n_points", "v_egms_mm_yr", "v_gnss_los_mm_yr",
                                                           "dv_gnss_minus_egms_mm_yr", "series_diff_std_mm")},
                      "E1_negative_control_dv": r_bad["dv_gnss_minus_egms_mm_yr"],
                      "A6_short_gnss": cv, "E2_synthetic": summ}, indent=2, default=str))
    print("SELFTEST OK")


def describe_gnss(path: Path) -> None:
    """Opis prawdziwego pliku GNSS: zakres, liczba dób, przerwy > 30 dni, współrzędne w EPSG:3035."""
    g, lon, lat = read_pangaea_gnss(path)
    gaps = g["date"].diff().dt.days
    x, y = transform_xy(lon, lat, 4326, 3035)
    print(json.dumps({"first": str(g["date"].iat[0].date()), "last": str(g["date"].iat[-1].date()),
                      "n_days": len(g), "lon_deg": lon, "lat_deg": lat, "easting_3035": round(x, 1),
                      "northing_3035": round(y, 1),
                      "gaps_over_30_days": [(str(g["date"].iat[i - 1].date()), str(g["date"].iat[i].date()), int(gaps.iat[i]))
                                            for i in np.where(gaps > 30)[0]],
                      "sigma_up_median_mm": float(g["sigma_mm"].median())}, indent=2))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    ap = argparse.ArgumentParser(description="EGMS Check - prototyp E1/E2")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--describe-gnss", type=Path)
    ap.add_argument("--run", choices=["e1", "e2"])
    a = ap.parse_args()
    if a.selftest:
        _selftest()
    elif a.describe_gnss:
        describe_gnss(a.describe_gnss)
    elif a.run:
        if CONFIG["status"] != "APPROVED":
            sys.exit("CONFIG['status'] != 'APPROVED': progi i decyzje nie są zatwierdzone (CLAUDE.md, zasada 9).")
        raise NotImplementedError("Przebieg na prawdziwych danych EGMS: po pobraniu plików (sesje 3-5, 9).")
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
