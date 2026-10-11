# TEST: pliki w formatach EGMS L2b/L3, NGL MIDAS/tenv3, Geobasis NRW i HyP3 o ZNANEJ odpowiedzi, wyłącznie do
# sprawdzenia notebooks/EGMS_Monitoring.ipynb poza Colab. Wartości są wymyślone, nie są danymi ani wynikiem.
# Użycie: python make_fixtures.py <katalog_fx>
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent / "fake"))
import egms_harness_lib as L  # noqa: E402

FX = Path(sys.argv[1])
for d in ("egms", "tenv3", "nrw", "hyp3"):
    (FX / d).mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(20261011)
TO3035 = Transformer.from_crs(4326, 3035, always_xy=True)
TO25832 = Transformer.from_crs(4326, 25832, always_xy=True)
DCOLS = ["pid", "easting", "northing", "height", "mean_velocity", "mean_velocity_std", "los_east", "los_north", "los_up",
         "incidence_angle"]


def zip_bytes(members: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:      # bez kompresji: rozmiary rzędu MB (plan)
        for n, b in members.items():
            zf.writestr(n, b)
    return buf.getvalue()


def site_truth_u(name: str, dates) -> np.ndarray:
    return L.bench_truth(name, dates) if name in L.BENCH else L.gnss_truth(name, dates)[2]


def site_truth_enu(name: str, dates) -> tuple:
    if name in L.BENCH:
        return np.zeros(len(dates)), np.zeros(len(dates)), L.bench_truth(name, dates)
    return L.gnss_truth(name, dates)


def region_sites(region: str) -> list:
    return L.SELECTED[region] + ([b for b in L.BENCH if b != "B014"] if region == "nrw_west" else [])


def lonlat(name: str) -> tuple:
    return (L.BENCH[name][0], L.BENCH[name][1]) if name in L.BENCH else (L.GNSS[name][0], L.GNSS[name][1])


# 1. MIDAS (27 kolumn, układ step_01.MIDAS_COLUMNS) i dobowe tenv3 (2016-01-01 .. 2025-08-01).
lines = []
for s, (lon, lat, vu, svu, ns, amp) in L.GNSS.items():
    lines.append(f"{s} MIDAS5 2012.0000 2025.6000 13.6 4500 4400 4000 {L.VE / 1000:.6f} {L.VN / 1000:.6f} {vu / 1000:.6f} "
                 f"0.000100 0.000100 {svu / 1000:.6f} 0 0 0 0.01 0.01 0.01 0.002 0.002 0.006 {ns} {lat:.6f} {lon:.6f} 10.0")
(FX / "midas.txt").write_text("\n".join(lines) + "\n")
hdr = ("site YYMMMDD yyyy.yyyy __MJD week d reflon _e0(m) __east(m) ____n0(m) _north(m) u0(m) ____up(m) _ant(m) sig_e(m) "
       "sig_n(m) sig_u(m) __corr_en __corr_eu __corr_nu _latitude(deg) _longitude(deg) __height(m)")
days = pd.date_range("2016-01-01", "2025-08-01", freq="D")
for s in sum(L.SELECTED.values(), []):
    lon, lat = L.GNSS[s][:2]
    E, N, U = L.gnss_truth(s, days)
    e = 12.1234 + (E + rng.normal(0, 1.5, len(days))) / 1000
    n = 34.5678 + (N + rng.normal(0, 1.5, len(days))) / 1000
    u = 0.0042 + (U + rng.normal(0, 5.0, len(days))) / 1000
    rows = [hdr] + [f"{s} {d.strftime('%y%b%d').upper()} {2016 + ti:.4f} 57388 1878 5 {lon:.4f} {int(np.floor(ei))} "
                    f"{ei - np.floor(ei):.6f} {int(np.floor(ni))} {ni - np.floor(ni):.6f} {int(np.floor(ui))} "
                    f"{ui - np.floor(ui):.6f} 0.0 0.001 0.001 0.005 0 0 0 {lat:.6f} {lon:.6f} 10.0"
                    for d, ti, ei, ni, ui in zip(days, L.years(days), e, n, u)]
    (FX / "tenv3" / f"{s}.EU.tenv3").write_text("\n".join(rows) + "\n")

# 2. EGMS L2b: punkty przy każdym punkcie naziemnym regionu (12 w 100 m, 8 w 100-200 m) + punkty dalekie;
#    drugi burst ścieżki 88 Groningen: 5 duplikatów (0,3 m) punktów pierwszego burstu -> A5 usuwa dokładnie 5.
index = {}
for region, R in L.REGIONS.items():
    names = region_sites(region)
    for trk, (direction, heading, first, bursts) in R["tracks"].items():
        dates = L.egms_dates(region, trk)
        dcols = [d.strftime("%Y%m%d") for d in dates]
        t_rel = (dates - dates[0]).days.to_numpy() / 365.25
        first_df = None
        for b_i, burst in enumerate(bursts):
            rows = []
            if b_i == 0:
                for s in names:
                    x0, y0 = TO3035.transform(*lonlat(s))
                    E, N, U = site_truth_enu(s, dates)
                    for k in range(20):
                        r = (100 * np.sqrt(rng.uniform())) if k < 12 else rng.uniform(105, 195)
                        a = rng.uniform(0, 2 * np.pi)
                        inc = rng.uniform(38.0, 42.0)
                        le, ln, lu = L.los_egms(inc, heading)
                        los = E * le + N * ln + U * lu + rng.normal(0, 2.0, len(dates))
                        los = np.round(los - los[0], 2)
                        rows.append([f"{trk}{b_i}{s}{k}", x0 + r * np.cos(a), y0 + r * np.sin(a), 5.0,
                                     float(np.polyfit(t_rel, los, 1)[0]), 0.3, le, ln, lu, inc] + list(los))
                df = pd.DataFrame(rows, columns=DCOLS + dcols)
                first_df = df
            else:
                dup = first_df.iloc[:5].copy()
                dup["pid"] = dup["pid"] + "_dup"
                dup["easting"] += 0.3
                df = dup
            far = first_df.iloc[:60].copy()
            far["pid"] = far["pid"] + f"_far{b_i}"
            far["northing"] += 100000.0                       # daleko od wszystkich punktów naziemnych
            df = pd.concat([df, far], ignore_index=True)
            fn = f"EGMS_L2b_{trk:03d}_{burst}_IW2_VV_2020_2024_1.zip"
            content = zip_bytes({fn.replace(".zip", ".csv"): df.to_csv(index=False)})
            (FX / "egms" / fn).write_bytes(content)
            index[fn] = {"size": len(content), "level": "L2B", "region": region, "track": trk, "direction": direction,
                         "burstId": int(burst)}

# 3. EGMS L3 (U): blok 3 x 3 komórek 100 m przy każdym punkcie (prędkość punktu, pełny szereg) + tło co ok. 1,5 km
#    w obszarze (tylko prędkość do mapy; szereg pusty, żeby plik był mały).
for region, R in L.REGIONS.items():
    dates = L.acq_dates(L.L3_FIRST, "2024-12-31")
    dcols = [d.strftime("%Y%m%d") for d in dates]
    t_rel = (dates - dates[0]).days.to_numpy() / 365.25
    cells = {}
    lo0, la0, lo1, la1 = R["aoi"]
    for lon in np.arange(lo0, lo1 + 1e-9, 0.0225):
        for lat in np.arange(la0, la1 + 1e-9, 0.0135):
            x, y = TO3035.transform(lon, lat)
            cells[(int(x // 100), int(y // 100))] = ("bg", -0.5 + 0.1 * np.sin(lon * 7) + 0.1 * np.cos(lat * 11), None)
    for s in region_sites(region):
        x, y = TO3035.transform(*lonlat(s))
        ix, iy = int(x // 100), int(y // 100)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cells[(ix + dx, iy + dy)] = (s, None, s)
    rows = []
    for (ix, iy), (tag, v_bg, s) in cells.items():
        if s is not None:
            u = site_truth_u(s, dates)
            series = u - u[0] + rng.normal(0, 0.5, len(dates))
            series = np.round(series - series[0], 2)
            v = float(np.polyfit(t_rel, series, 1)[0])
        else:
            series, v = np.full(len(dates), np.nan), float(v_bg)
        rows.append([f"L3_{ix}_{iy}", ix * 100 + 50.0, iy * 100 + 50.0, 5.0, 1.0, v, 0.2, 0.0, 0.0, 0.0, 0.0] + list(series))
    df = pd.DataFrame(rows, columns=["pid", "easting", "northing", "height", "rmse", "mean_velocity", "mean_velocity_std",
                                     "acceleration", "acceleration_std", "seasonality", "seasonality_std"] + dcols)
    fn = R["tile"]
    content = zip_bytes({fn[:-4] + ".tif": b"II*\x00fake", fn[:-4] + ".csv": df.to_csv(index=False)})
    (FX / "egms" / fn).write_bytes(content)
    index[fn] = {"size": len(content), "level": "L3", "region": region, "track": None, "direction": None,
                 "burstId": None}
(FX / "egms" / "index.json").write_text(json.dumps(index, indent=1))

# 4. Geobasis NRW: Punktliste (cp1252, przecinek dziesiętny, EPSG:25832) i Punktliste mit Zeitfolge.
pt_rows, ser_rows = [], []
for k, (b, (lon, lat, rate)) in enumerate(L.BENCH.items()):
    e, n = TO25832.transform(lon, lat)
    bid = L.bench_id(b)
    pt_rows.append(f'"{bid}";"Höhenfestpunkt {b}; Kirche";{e:.3f};{n:.3f};{100.0:.4f};"981123,4"'.replace(".", ","))
    ep = pd.DatetimeIndex(L.BENCH_EPOCHS_B013 if b == "B013" else L.BENCH_EPOCHS) + pd.Timedelta(days=k)
    h = 100.0 + (L.bench_truth(b, ep) + rng.normal(0, 0.5, len(ep))) / 1000.0
    ser_rows += [f"{bid};{d:%d.%m.%Y};" + f"{v:.5f}".replace(".", ",") for d, v in zip(ep, h)]
(FX / "nrw" / "hfp_pl.csv").write_text("Punktkennzeichen;Name des Punktes;Ostwert;Nordwert;Höhe;Schwerewert\n"
                                       + "\n".join(pt_rows) + "\n", encoding="cp1252")
(FX / "nrw" / "hfp_plzf.csv").write_text("Punktkennzeichen;Messungsdatum;Höhe\n" + "\n".join(ser_rows) + "\n",
                                         encoding="cp1252")

# 5. Przykładowy produkt HyP3 (atrapa serwera tworzy takie zipy dla każdego zlecenia).
example = "S1_088_088000s1n03-000000s2n00-000000s3n00_IW_20240107_20240119_VV_INT80_0000"
(FX / "hyp3" / f"{example}.zip").write_bytes(L.hyp3_product_zip(example))

total = {r: sum(v["size"] for v in index.values() if v["region"] == r) for r in L.REGIONS}
print("fixtures:", len(index), "plików EGMS,", {r: f"{b / 1e6:.2f} MB" for r, b in total.items()},
      len(sum(L.SELECTED.values(), [])), "stacji GNSS,", len(L.BENCH), "reperów")
