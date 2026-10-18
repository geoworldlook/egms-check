# TEST: wspólne definicje syntetycznego świata dla tests/monitoring_harness (fixtures, atrapy serwerów, atrapa MintPy).
# Wartości są testowe (znana odpowiedź), nie są danymi ani wynikiem. Współrzędne stacji i reperów są wymyślone.
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

RELEASE = "2020-2024"
RELEASE_CHECK = "2019-2023"                     # drugie wydanie (tylko L3 NRW) do porównania z niwelacją
L3_CHECK = {"region": "nrw_west", "tile": "EGMS_L3_E41N31_100km_U_2019_2023_1.zip", "first": "2019-01-05",
            "end": "2023-12-31"}
S1B_END = pd.Timestamp("2021-12-23")
T_ORIGIN = pd.Timestamp("2016-01-01")          # początek prawdy ruchu (t = 0) dla GNSS, EGMS i MintPy
VE, VN = 0.3, 0.2                               # ruch poziomy stacji [mm/rok] (płyta odjęta, mały resztkowy)
INC_DEG = 40.0                                  # kąt padania atrapy MintPy

# Stacje GNSS: (lon, lat, vu [mm/rok], svu [mm/rok], liczba skoków, amplituda roczna U [mm])
GNSS = {
    # Groningen: osiadające w obszarze, stabilne w okolicy (T003 poza obszarem), odrzucane przez regułę E1
    "S001": (6.80, 53.33, -6.0, 0.6, 0, 2.0), "S002": (6.70, 53.25, -4.5, 0.6, 0, 2.0),
    "S003": (6.90, 53.20, -3.0, 0.6, 0, 2.0), "S004": (6.55, 53.40, -2.5, 0.6, 0, 2.0),
    "T001": (6.30, 53.10, 0.2, 0.6, 0, 2.0), "T002": (7.00, 53.50, -0.3, 0.6, 0, 2.0),
    "T003": (5.60, 52.80, 0.8, 0.6, 0, 2.0),
    "X001": (6.60, 53.15, -5.0, 1.6, 0, 2.0), "Y001": (4.90, 52.30, -4.0, 0.5, 0, 2.0),
    "Z001": (6.40, 53.22, -1.5, 0.5, 0, 2.0), "Z002": (4.20, 52.00, 0.1, 0.5, 0, 2.0),
    # Zachodnia NRW: 'all_quality' -> osiadająca, stabilna, inna; odrzucane (svu, poza obszarem)
    "N001": (6.55, 51.02, -4.0, 0.6, 0, 2.0), "N002": (6.20, 50.85, 0.3, 0.6, 0, 2.0),
    "N003": (6.05, 51.15, 2.5, 0.6, 1, 2.0), "N004": (6.70, 51.10, -5.0, 1.5, 0, 2.0),
    "N005": (7.50, 51.00, -3.0, 0.6, 0, 2.0),
}
SELECTED = {"groningen": ["S001", "S002", "S003", "S004", "T001", "T002", "T003"], "nrw_west": ["N001", "N002", "N003"]}
EXPECTED_GROUPS = {"S001": "osiadająca", "S002": "osiadająca", "S003": "osiadająca", "S004": "osiadająca",
                   "T001": "stabilna", "T002": "stabilna", "T003": "stabilna",
                   "N001": "osiadająca", "N002": "stabilna", "N003": "inna"}

# Repery NRW: (lon, lat, prędkość pionowa [mm/rok]); B013 ma jedną epokę w oknie EGMS, B014 leży poza obszarem.
BENCH = {"B001": (6.480, 51.000, -10.0), "B002": (6.510, 51.010, -8.0), "B003": (6.450, 50.990, -6.0),
         "B004": (6.530, 50.980, -5.0), "B005": (6.420, 51.030, -3.0), "B006": (6.300, 50.900, 0.0),
         "B007": (6.250, 50.950, 0.3), "B008": (6.350, 51.200, -0.2), "B009": (6.000, 51.100, 3.0),
         "B010": (6.080, 51.050, 2.0), "B011": (6.800, 51.250, -1.0), "B012": (6.900, 50.800, -0.5),
         "B013": (6.700, 50.750, -2.0), "B014": (7.300, 51.000, -4.0)}
BENCH_ANNUAL_MM = 1.0
BENCH_EPOCHS = ["2019-05-10", "2020-06-15", "2022-06-15", "2024-06-20", "2025-04-01"]
BENCH_EPOCHS_B013 = ["2019-05-10", "2022-06-15", "2025-04-01"]


def bench_id(name: str) -> str:
    """Punktkennzeichen z zerem wiodącym (sprawdza zachowanie tekstu)."""
    return f"04506{int(name[1:]):05d}"


REGIONS = {
    "groningen": {"aoi": (5.8, 52.9, 7.3, 53.6), "tile": "EGMS_L3_E41N33_100km_U_2020_2024_1.zip",
                  "tracks": {88: ("ascending", -12.0, "2020-01-03", ["0290", "0291"]),
                             37: ("descending", 192.0, "2020-01-05", ["0400"])}},
    "nrw_west": {"aoi": (5.9, 50.7, 7.0, 51.3), "tile": "EGMS_L3_E41N31_100km_U_2020_2024_1.zip",
                 "tracks": {15: ("ascending", -12.0, "2020-01-02", ["0300"]),
                            139: ("descending", 192.0, "2020-01-04", ["0410"])}},
}
L3_FIRST = "2020-01-06"
# Etap B (Groningen): siatka produktów HyP3 w UTM 32N obejmująca region z okolicą; piksel 1 km.
HYP3_GRID = {"epsg": 32632, "x0": 200000.0, "y0": 6000000.0, "nx": 280, "ny": 210, "px": 1000.0}
HYP3_END_TEST = "2025-01-31"


def acq_dates(first: str, end: str) -> pd.DatetimeIndex:
    """Daty akwizycji: co 6 dni do końca Sentinel-1B, potem co 12 dni (jak EGMS L2b)."""
    d6 = pd.date_range(first, S1B_END, freq="6D")
    d12 = pd.date_range(d6[-1] + pd.Timedelta(days=12), end, freq="12D")
    return d6.append(d12)


def egms_dates(region: str, track: int) -> pd.DatetimeIndex:
    return acq_dates(REGIONS[region]["tracks"][track][2], "2024-12-31")


def burst_dates(region: str, track: int) -> pd.DatetimeIndex:
    """Daty burstów Sentinel-1 ścieżki (2024-2026): ta sama sekwencja 12-dniowa co EGMS."""
    d = acq_dates(REGIONS[region]["tracks"][track][2], "2026-12-31")
    return d[d >= "2024-01-01"]


def track_region(track: int) -> str:
    for r, v in REGIONS.items():
        if track in v["tracks"]:
            return r
    raise KeyError(track)


def years(dates) -> np.ndarray:
    return np.asarray((pd.DatetimeIndex(dates) - T_ORIGIN) / pd.Timedelta(days=1), float) / 365.25


def gnss_truth(site: str, dates) -> tuple:
    """Prawda E, N, U [mm] w datach (t od T_ORIGIN)."""
    lon, lat, vu, svu, ns, amp = GNSS[site]
    t = years(dates)
    return VE * t, VN * t, vu * t + amp * np.sin(2 * np.pi * t)


def bench_truth(name: str, dates) -> np.ndarray:
    t = years(dates)
    return BENCH[name][2] * t + BENCH_ANNUAL_MM * np.sin(2 * np.pi * t)


def los_egms(inc_deg, heading_deg) -> tuple:
    """Kosinusy ziemia -> satelita jak w fixtures E1 (az = heading + 90, patrzenie w prawo)."""
    inc, az = np.deg2rad(inc_deg), np.deg2rad(heading_deg + 90.0)
    return -np.sin(inc) * np.sin(az), -np.sin(inc) * np.cos(az), np.cos(inc)


def los_mintpy(inc_deg, heading_deg) -> tuple:
    """Ten sam wektor w konwencji MintPy (az = 90 - heading): e = -sin(inc) sin(az), n = sin(inc) cos(az)."""
    inc, az = np.deg2rad(inc_deg), np.deg2rad(90.0 - heading_deg)
    return -np.sin(inc) * np.sin(az), np.sin(inc) * np.cos(az), np.cos(inc)


def hyp3_product_zip(product: str) -> bytes:
    """Zip produktu HyP3: <produkt>/<produkt>.txt i 7 warstw GeoTIFF w siatce HYP3_GRID (wartości stałe)."""
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.transform import from_origin
    g = HYP3_GRID
    tr = from_origin(g["x0"], g["y0"], g["px"], g["px"])
    values = {"unw_phase": 0.0, "corr": 0.9, "conncomp": 1.0, "dem": 10.0, "lv_theta": np.deg2rad(90.0 - INC_DEG),
              "lv_phi": 0.0, "water_mask": 1.0}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{product}/{product}.txt",
                    "Reference Granule: TEST\nSecondary Granule: TEST\nBaseline: 50.0\nUTC time: 20000.0\nHeading: -12.0\n"
                    "Spacecraft height: 693000.0\nEarth radius at nadir: 6370000.0\nSlant range near: 800000.0\n"
                    "Range looks: 20\nAzimuth looks: 4\nUnwrapping type: snaphu_mcf\n")
        for layer, val in values.items():
            with MemoryFile() as mem:
                with mem.open(driver="GTiff", width=g["nx"], height=g["ny"], count=1, dtype="float32",
                              crs=rasterio.crs.CRS.from_epsg(g["epsg"]), transform=tr, compress="deflate") as ds:
                    ds.write(np.full((1, g["ny"], g["nx"]), val, "float32"))
                zf.writestr(f"{product}/{product}_{layer}.tif", mem.read())
    return buf.getvalue()


def load_json(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
