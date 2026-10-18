"""
================================================================================
EGMS Check - KROK 2: WYCINKI EGMS WOKÓŁ STACJI I KONTROLE KONWENCJI
================================================================================
  I.   Wycinek: z pliku EGMS L2b (zip z CSV, często > 1 GB po rozpakowaniu) czytamy fragmentami
       tylko punkty w promieniu od stacji; wynik jest mały i trafia do data/03_Extracts/.
  II.  Kontrole przed porównaniem (docs/evidence/F4_metodyka.md, sekcja 2;
       docs/plans/Plan_v1_kryteria_akceptacji.md, sekcja A):
         A1 norma wektora LOS = 1;  A2 los_up = cos(kąt padania);  A3 los_east ma przeciwny znak
         na orbicie wstępującej i zstępującej;  A5 duplikaty punktów z zakładek burstów.
       Niespełniona kontrola zatrzymuje dalsze obliczenia.
  III. Duplikaty: punkt obecny w dwóch burstach (bliżej niż próg) zostaje tylko z jednego pliku
       (pierwszego alfabetycznie). EGMS-toolkit robi to inaczej (Hrysiewicz i in. 2024); liczba
       usuniętych punktów jest raportowana.

Konwencje: EPSG:3035 (easting, northing), przemieszczenia w mm, ujemne = oddalanie od satelity.
================================================================================
"""

import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

DATE_COL = re.compile(r"^\d{8}$")
L2_REQUIRED = ["pid", "easting", "northing", "height", "mean_velocity", "los_east", "los_north", "los_up",
               "incidence_angle"]


# ==============================================================================
# I. WYCINEK
# ==============================================================================
def extract_points(zip_path: Path, stations: pd.DataFrame, radius_m: float, chunksize: int) -> pd.DataFrame:
    """
    Punkty pliku EGMS L2b w promieniu radius_m od stacji (kolumny stacji: site, x_3035, y_3035).
    Wynik: atrybuty punktu + kolumny dat + site, distance_m, source_file. Punkt blisko dwóch stacji
    pojawia się dwa razy (raz dla każdej stacji).
    """
    with zipfile.ZipFile(zip_path) as zf:
        csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(csvs) != 1:
            raise ValueError(f"{zip_path}: oczekiwano jednego pliku CSV, jest {csvs}")
        parts = []
        with zf.open(csvs[0]) as f:
            for chunk in pd.read_csv(f, chunksize=chunksize):
                missing = [c for c in L2_REQUIRED if c not in chunk.columns]
                if missing:
                    raise KeyError(f"{zip_path}: brak kolumn {missing}")
                for st in stations.itertuples():
                    d = np.hypot(chunk["easting"].to_numpy() - st.x_3035, chunk["northing"].to_numpy() - st.y_3035)
                    near = d <= radius_m
                    if near.any():
                        parts.append(chunk[near].assign(site=st.site, distance_m=d[near]))
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, ignore_index=True)
    out["source_file"] = Path(zip_path).name
    return out


def date_columns(df: pd.DataFrame) -> list:
    cols = [c for c in df.columns if DATE_COL.match(str(c))]
    if len(cols) < 2:
        raise ValueError("Za mało kolumn dat yyyymmdd w wycinku")
    return cols


# ==============================================================================
# II. KONTROLE KONWENCJI
# ==============================================================================
def check_conventions(points: pd.DataFrame, tol: float) -> pd.DataFrame:
    """
    A1, A2 dla każdej ścieżki; A3 dla par orbit (wstępująca kontra zstępująca).
    points musi mieć kolumny track i direction. Zwraca tabelę kontroli z kolumną 'pass'.
    """
    rows = []
    for (track, direction), p in points.groupby(["track", "direction"]):
        norm = np.sqrt(p["los_east"] ** 2 + p["los_north"] ** 2 + p["los_up"] ** 2)
        a1 = float(np.max(np.abs(norm - 1.0)))
        a2 = float(np.max(np.abs(p["los_up"] - np.cos(np.deg2rad(p["incidence_angle"])))))
        rows.append({"check": "A1 |norma LOS - 1|", "track": track, "value": a1, "threshold": tol, "pass": a1 <= tol})
        rows.append({"check": "A2 |los_up - cos(theta)|", "track": track, "value": a2, "threshold": tol, "pass": a2 <= tol})
    sign = points.groupby("direction")["los_east"].median().apply(np.sign)
    if set(sign.index) == {"ascending", "descending"}:
        ok = bool(sign["ascending"] == -sign["descending"] != 0)
        rows.append({"check": "A3 znak los_east: wstępująca = -zstępująca", "track": "all",
                     "value": f"asc {sign['ascending']:+.0f}, desc {sign['descending']:+.0f}", "threshold": "przeciwne",
                     "pass": ok})
    return pd.DataFrame(rows)


# ==============================================================================
# III. DUPLIKATY Z ZAKŁADEK BURSTÓW
# ==============================================================================
def drop_cross_file_duplicates(points: pd.DataFrame, max_dist_m: float) -> tuple[pd.DataFrame, int]:
    """
    W obrębie ścieżki i stacji: punkt z drugiego pliku bliżej niż max_dist_m od punktu z pierwszego
    (alfabetycznie) pliku jest usuwany. Zwraca (punkty bez duplikatów, liczba usuniętych).
    """
    keep = np.ones(len(points), bool)
    pts = points.reset_index(drop=True)
    for _, g in pts.groupby(["track", "site"]):
        files = sorted(g["source_file"].unique())
        for k, f in enumerate(files[1:], start=1):
            ref = g[g["source_file"].isin(files[:k])][["easting", "northing"]].to_numpy()
            cur = g[g["source_file"] == f]
            for idx, xy in zip(cur.index, cur[["easting", "northing"]].to_numpy()):
                if np.min(np.hypot(*(ref - xy).T)) < max_dist_m:
                    keep[idx] = False
    return pts[keep].reset_index(drop=True), int((~keep).sum())


def nearest_cross_file_distance(points: pd.DataFrame) -> pd.Series:
    """Dla raportu A5: odległość każdego punktu do najbliższego punktu z innego pliku tej samej ścieżki [m]."""
    out = pd.Series(np.nan, index=points.index)
    for _, g in points.groupby(["track", "site"]):
        for f in g["source_file"].unique():
            other = g[g["source_file"] != f][["easting", "northing"]].to_numpy()
            if len(other) == 0:
                continue
            cur = g[g["source_file"] == f]
            out[cur.index] = [float(np.min(np.hypot(*(other - xy).T))) for xy in cur[["easting", "northing"]].to_numpy()]
    return out
