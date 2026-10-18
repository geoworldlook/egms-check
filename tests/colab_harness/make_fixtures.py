# TEST: pliki w formacie EGMS L2b i NGL tenv3/MIDAS o znanej odpowiedzi (tylko do sprawdzenia notatnika).
import json, zipfile, io, sys
import numpy as np, pandas as pd
from pyproj import Transformer
fx = sys.argv[1]; rng = np.random.default_rng(7)
ST = {"S001": (6.80, 53.33, -6.0), "S002": (6.70, 53.30, -4.5), "S003": (6.90, 53.20, -3.0), "S004": (6.55, 53.40, -2.5),
      "T001": (6.30, 53.10, 0.2), "T002": (7.00, 53.50, -0.3), "T003": (5.60, 52.80, 0.8)}   # T003: okolica, poza regionem
EXTRA = {"X001": (6.60, 53.25, -5.0, 1.6, 0), "Y001": (4.90, 52.30, -4.0, 0.5, 0), "Z001": (6.40, 53.20, -1.5, 0.5, 0),
         "Z002": (4.20, 52.00, 0.1, 0.5, 0)}   # odrzucone: svu > 1, poza regionem, vu pośrednie, stabilna poza okolicą
lines = []
for s, (lon, lat, vu) in ST.items():
    lines.append(f"{s} MIDAS5 2012.0000 2024.6461 12.6 4500 4400 4000 0.000300 0.000200 {vu/1000:.6f} 0.000100 0.000100 0.000600 0 0 0 0.01 0.01 0.01 0.002 0.002 0.006 0 {lat:.6f} {lon:.6f} 10.0")
for s, (lon, lat, vu, svu, ns) in EXTRA.items():
    lines.append(f"{s} MIDAS5 2012.0000 2024.6461 12.6 4500 4400 4000 0.000300 0.000200 {vu/1000:.6f} 0.000100 0.000100 {svu/1000:.6f} 0 0 0 0.01 0.01 0.01 0.002 0.002 0.006 {ns} {lat:.6f} {lon:.6f} 10.0")
open(f"{fx}/midas.txt", "w").write("\n".join(lines) + "\n")
hdr = "site YYMMMDD yyyy.yyyy __MJD week d reflon _e0(m) __east(m) ____n0(m) _north(m) u0(m) ____up(m) _ant(m) sig_e(m) sig_n(m) sig_u(m) __corr_en __corr_eu __corr_nu _latitude(deg) _longitude(deg) __height(m)"
days = pd.date_range("2016-01-01", "2024-08-24", freq="D")
t = ((days - days[0]) / pd.Timedelta(days=1)).to_numpy() / 365.25
truth = {}
for s, (lon, lat, vu) in ST.items():
    E, N = 0.3 * t, 0.2 * t
    U = vu * t + 2.0 * np.sin(2 * np.pi * t)
    truth[s] = (days, E, N, U)
    e, n, u = 12 + 0.1234 + (E + rng.normal(0, 1.5, t.size)) / 1000, 34 + 0.5678 + (N + rng.normal(0, 1.5, t.size)) / 1000, 0 + 0.0042 + (U + rng.normal(0, 5, t.size)) / 1000
    rows = [hdr] + [f"{s} {d.strftime('%y%b%d').upper()} {2016 + ti:.4f} 57388 1878 5 {lon:.4f} {int(np.floor(ei))} {ei - np.floor(ei):.6f} {int(np.floor(ni))} {ni - np.floor(ni):.6f} {int(np.floor(ui))} {ui - np.floor(ui):.6f} 0.0 0.001 0.001 0.005 0 0 0 {lat:.6f} {lon:.6f} 10.0"
                    for d, ti, ei, ni, ui in zip(days, t, e, n, u)]
    open(f"{fx}/tenv3/{s}.EU.tenv3", "w").write("\n".join(rows) + "\n")
dates = list(pd.date_range("2019-01-03", "2021-12-23", freq="6D")) + list(pd.date_range("2022-01-04", "2023-12-27", freq="12D"))
dcols = [d.strftime("%Y%m%d") for d in dates]
tr = Transformer.from_crs(4326, 3035, always_xy=True)
TRACKS = {"015": ("ascending", -12.0, ["015-0300-IW2-VV"]), "088": ("ascending", -12.0, ["088-0290-IW1-VV", "088-0291-IW1-VV"]),
          "037": ("descending", 192.0, ["037-0400-IW3-VV"]), "139": ("descending", 192.0, ["139-0410-IW2-VV"])}
index = {}
for trk, (direction, heading, bursts) in TRACKS.items():
    for b_i, burst in enumerate(bursts):
        rows = []
        for s, (lon, lat, vu) in ST.items():
            x0, y0 = tr.transform(lon, lat)
            d_days, E, N, U = truth[s]
            sel = np.searchsorted(d_days, pd.DatetimeIndex(dates))
            n_pts = 22 if b_i == 0 else 8                    # drugi burst: 5 duplikatów (0,3 m) + 3 nowe punkty
            for k in range(n_pts):
                r = 200 * np.sqrt(rng.uniform()) if k >= 12 else 100 * np.sqrt(rng.uniform())
                a = rng.uniform(0, 2 * np.pi); inc = np.deg2rad(rng.uniform(32, 44)); az = np.deg2rad(heading + 90)
                le, ln, lu = -np.sin(inc) * np.sin(az), -np.sin(inc) * np.cos(az), np.cos(inc)
                los = E[sel] * le + N[sel] * ln + U[sel] * lu + rng.normal(0, 2.5, len(dates))
                los -= los[0]
                rows.append([f"{trk}{b_i}{s}{k}", x0 + r * np.cos(a), y0 + r * np.sin(a), 5.0, float(np.polyfit(np.arange(len(dates)) * 0 + ((pd.DatetimeIndex(dates) - dates[0]).days / 365.25), los, 1)[0]),
                             le, ln, lu, np.rad2deg(inc)] + list(los))
            if b_i == 1:
                for k in range(5):                          # duplikaty punktów z pierwszego burstu tej ścieżki
                    pass
        df = pd.DataFrame(rows, columns=["pid", "easting", "northing", "height", "mean_velocity", "los_east", "los_north", "los_up", "incidence_angle"] + dcols)
        if b_i == 1:
            first = index[[k for k in index if k.startswith(f"EGMS_L2b_{trk}_{bursts[0].split('-')[1]}")][0]]["df"]
            dup = first.iloc[:5].copy(); dup["pid"] = dup["pid"] + "_dup"; dup["easting"] += 0.3
            df = pd.concat([df, dup], ignore_index=True)
        far = df.iloc[:200].copy(); far["pid"] = far["pid"] + "_far"; far["easting"] += 30000   # punkty daleko od stacji
        df = pd.concat([df, far], ignore_index=True)
        fn = f"EGMS_L2b_{burst.replace('-', '_')}_2019_2023_1.zip"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(fn.replace(".zip", ".csv"), df.to_csv(index=False))
        open(f"{fx}/egms/{fn}", "wb").write(buf.getvalue())
        index[fn] = {"df": df, "track": trk, "direction": direction, "burstId": burst, "size": len(buf.getvalue())}
json.dump({k: {kk: vv for kk, vv in v.items() if kk != "df"} for k, v in index.items()}, open(f"{fx}/egms/index.json", "w"))
print("fixtures:", len(index), "plików EGMS,", len(ST), "stacji")
