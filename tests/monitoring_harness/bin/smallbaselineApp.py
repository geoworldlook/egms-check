#!/usr/bin/env python3
# TEST: atrapa MintPy smallbaselineApp.py <szablon> --work-dir <katalog> dla tests/monitoring_harness.
# Czyta szablon zapisany przez step_08.write_mintpy_template (warstwy przycięte, punkt odniesienia, poprawki), daty par
# z nazw produktów i siatkę z przyciętego unw_phase; zapisuje pliki o układzie MintPy 1.6.4: <szereg końcowy>.h5
# (nazwa jak step_08._timeseries_name), timeseries.h5, inputs/geometryGeo.h5, maskTempCoh.h5.
# Szereg = prawda ruchu najbliższej stacji GNSS (egms_harness_lib) rzutowana na LOS (inc 40, az MintPy = 90 - heading),
# względem pierwszej daty i piksela odniesienia, w metrach. Wartości testowe, nie wynik.
import glob
import os
import sys
from pathlib import Path

import h5py
import numpy as np
import rasterio

sys.path.insert(0, os.getcwd())          # PROJECT_DIR (bieżący katalog jądra): ta sama logika nazw co step_08
from step_08_hyp3_mintpy import _read_template, _timeseries_name, product_dates, transform_xy  # noqa: E402

import egms_harness_lib as L  # noqa: E402

args = sys.argv[1:]
tpl, wd = Path(args[0]), Path(args[args.index("--work-dir") + 1])
t = _read_template(tpl)
assert t["mintpy.load.processor"] == "hyp3", t
files = sorted(glob.glob(t["mintpy.load.unwFile"]))
assert files, f"brak plików {t['mintpy.load.unwFile']}"
for key in ("mintpy.load.corFile", "mintpy.load.connCompFile", "mintpy.load.demFile", "mintpy.load.incAngleFile",
            "mintpy.load.azAngleFile", "mintpy.load.waterMaskFile"):
    assert len(glob.glob(t[key])) == len(files), key
products = [Path(f).parent.name for f in files]
dates = sorted({d for p in products for d in product_dates(p)})
track = int(products[0].split("_")[1])
region = L.track_region(track)
direction, heading = L.REGIONS[region]["tracks"][track][:2]
with rasterio.open(files[0]) as ds:
    tr, W, H, epsg = ds.transform, ds.width, ds.height, ds.crs.to_epsg()
x0, y0, px = tr.c, tr.f, tr.a
r, c = np.mgrid[0:H, 0:W]
xc, yc = x0 + (c + 0.5) * px, y0 - (r + 0.5) * px
sites = L.SELECTED[region]
sx, sy = transform_xy(np.array([L.GNSS[s][0] for s in sites]), np.array([L.GNSS[s][1] for s in sites]), 4326, epsg)
nearest = np.argmin((xc[None] - np.asarray(sx)[:, None, None]) ** 2 + (yc[None] - np.asarray(sy)[:, None, None]) ** 2, axis=0)
le, ln, lu = L.los_mintpy(L.INC_DEG, heading)
D = []
for s in sites:
    E, N, U = L.gnss_truth(s, dates)
    d = E * le + N * ln + U * lu
    D.append(d - d[0])
D = np.array(D)                                        # (stacje, daty) [mm]
lat, lon = (float(v) for v in t["mintpy.reference.lalo"].split(","))
rx, ry = transform_xy(lon, lat, 4326, epsg)
ref_r, ref_c = int(np.floor((ry - y0) / -px + 0.01)), int(np.floor((rx - x0) / px + 0.01))
ts = np.moveaxis(D[nearest], -1, 0)                    # (daty, wiersze, kolumny)
ts = (ts - ts[:, ref_r, ref_c][:, None, None]) / 1000.0
atr = {"FILE_TYPE": "timeseries", "UNIT": "m", "X_FIRST": x0, "Y_FIRST": y0, "X_STEP": px, "Y_STEP": -px, "WIDTH": W,
       "LENGTH": H, "EPSG": epsg, "X_UNIT": "meters", "REF_DATE": dates[0].strftime("%Y%m%d"), "REF_Y": ref_r,
       "REF_X": ref_c, "REF_LAT": lat, "REF_LON": lon, "ORBIT_DIRECTION": direction.upper()}
(wd / "inputs").mkdir(parents=True, exist_ok=True)
for name in {"timeseries.h5", _timeseries_name(t)}:
    with h5py.File(wd / name, "w") as f:
        f.create_dataset("timeseries", data=ts.astype("float32"))
        f.create_dataset("date", data=np.array([d.strftime("%Y%m%d") for d in dates], dtype=np.bytes_))
        f.create_dataset("bperp", data=np.zeros(len(dates), "float32"))
        f.attrs.update({k: str(v) for k, v in atr.items()})
with h5py.File(wd / "inputs" / "geometryGeo.h5", "w") as f:
    f.create_dataset("incidenceAngle", data=np.full((H, W), L.INC_DEG, "float32"))
    f.create_dataset("azimuthAngle", data=np.full((H, W), 90.0 - heading, "float32"))
    f.attrs.update({k: str(v) for k, v in {**atr, "FILE_TYPE": "geometry"}.items()})
with h5py.File(wd / "maskTempCoh.h5", "w") as f:
    f.create_dataset("mask", data=np.ones((H, W), bool))
    f.attrs.update({k: str(v) for k, v in {**atr, "FILE_TYPE": "mask"}.items()})
print(f"TEST smallbaselineApp: {len(products)} interferogramów, {len(dates)} dat, siatka {W} x {H}, ścieżka {track}, "
      f"szereg {_timeseries_name(t)}")
