"""
================================================================================
EGMS Check - KROK 3: WALIDACJA EGMS L2b NA STACJACH GNSS
================================================================================
Metoda według oficjalnej walidacji EGMS (Koudogbo i in. 2025, rozdz. 2.3.1.1) i Even i in. 2024:
  1. punkty EGMS w promieniu R od stacji, co najmniej N punktów; szereg EGMS = mediana punktów w każdej dacie,
  2. GNSS (E, N, U, płyta euroazjatycka odjęta) rzutowany na kierunek satelity wektorem LOS punktów:
         d_LOS = E * los_east + N * los_north + U * los_up,
  3. GNSS w datach EGMS: mediana dób w oknie +-k dni; wspólne okno; wspólna data odniesienia (oba szeregi = 0),
  4. prędkość obu szeregów tym samym modelem (trend liniowy + sinusoida roczna) w tym samym oknie,
  5. metryki: dv = v_GNSS,LOS - v_EGMS (konwencja Fabris i Nazari 2026), odchylenie różnicy szeregów, korelacja.
Kryteria i progi: CONFIG w notatniku (docs/plans/Plan_v1_kryteria_akceptacji.md, sekcja B).

Jednostki: mm, mm/rok. Ujemne = osiadanie / oddalanie od satelity.
================================================================================
"""

import numpy as np
import pandas as pd

DAYS_PER_YEAR = 365.25


# ==============================================================================
# I. CZAS I PRĘDKOŚĆ
# ==============================================================================
def years_since(dates, t0) -> np.ndarray:
    return np.asarray((pd.DatetimeIndex(dates) - t0) / pd.Timedelta(days=1), dtype=float) / DAYS_PER_YEAR


def fit_velocity(dates, y_mm: np.ndarray, model: str) -> tuple[float, float]:
    """Prędkość MNK [mm/rok] i jej odchylenie formalne (szum biały; dla GNSS zaniżone)."""
    m = np.isfinite(y_mm)
    if m.sum() < 10:
        raise ValueError(f"Za mało obserwacji do prędkości: {int(m.sum())}")
    t = years_since(pd.DatetimeIndex(dates)[m], pd.DatetimeIndex(dates)[m][0])
    cols = [np.ones_like(t), t]
    if model == "linear_annual":
        cols += [np.sin(2 * np.pi * t), np.cos(2 * np.pi * t)]
    elif model != "linear":
        raise ValueError(f"Nieznany model prędkości: {model}")
    A = np.column_stack(cols)
    coef, *_ = np.linalg.lstsq(A, y_mm[m], rcond=None)
    resid = y_mm[m] - A @ coef
    s2 = float(resid @ resid) / (len(resid) - A.shape[1])
    return float(coef[1]), float(np.sqrt(s2 * np.linalg.inv(A.T @ A)[1, 1]))


def gnss_at_dates(gnss_los: pd.Series, dates: pd.DatetimeIndex, half_window_days: float) -> pd.Series:
    """Mediana dobowych wartości GNSS w oknie +-half_window_days wokół każdej daty EGMS; brak dób = NaN."""
    t = gnss_los.index.to_numpy()
    v = gnss_los.to_numpy()
    out = np.full(len(dates), np.nan)
    for k, d in enumerate(dates):
        m = np.abs((t - d.to_datetime64()) / np.timedelta64(1, "D")) <= half_window_days
        if m.any():
            out[k] = np.median(v[m])
    return pd.Series(out, index=dates)


# ==============================================================================
# II. PORÓWNANIE STACJA x ŚCIEŻKA
# ==============================================================================
def compare_station_track(points: pd.DataFrame, date_cols: list, gnss: pd.DataFrame, radius_m: float,
                          cfg: dict) -> dict:
    """
    points: punkty EGMS jednej ścieżki przy jednej stacji (kolumny distance_m, los_*, daty).
    gnss: dobowe e_mm, n_mm, u_mm z kolumną date. Zwraca wiersz wyników (status 'ok' albo powód NaN).
    """
    sel = points[points["distance_m"] <= radius_m]
    row = {"radius_m": radius_m, "n_points": len(sel), "meets_A6": False}
    if len(sel) < cfg["min_points"]:
        return {**row, "status": f"za mało punktów EGMS (< {cfg['min_points']})"}
    dates = pd.to_datetime(pd.Index(date_cols), format="%Y%m%d")
    egms = pd.Series(np.median(sel[date_cols].to_numpy(float), axis=0), index=dates)
    le, ln, lu = (float(sel[c].mean()) for c in ("los_east", "los_north", "los_up"))
    g = gnss.set_index("date")
    g_los = g["e_mm"] * le + g["n_mm"] * ln + g["u_mm"] * lu
    g_at = gnss_at_dates(g_los, dates, cfg["gnss_half_window_days"])

    # Pokrycie A6: (a) wspólne okno / okres wydania, (b) daty EGMS w oknie z wartością GNSS.
    o0, o1 = max(dates[0], g.index[0]), min(dates[-1], g.index[-1])
    frac_release = max((o1 - o0).days, 0) / (dates[-1] - dates[0]).days
    in_win = (dates >= o0) & (dates <= o1)
    frac_dates = float(g_at[in_win].notna().mean()) if in_win.any() else 0.0
    row.update(frac_release=frac_release, frac_dates=frac_dates)
    common = egms.notna() & g_at.notna() & in_win
    if common.sum() < 10:
        return {**row, "status": "za mało wspólnych dat"}
    ref = egms.index[common][0]
    e = (egms - egms[ref])[common]
    gg = (g_at - g_at[ref])[common]
    v_e, sv_e = fit_velocity(e.index, e.to_numpy(), cfg["velocity_model"])
    v_g, sv_g = fit_velocity(gg.index, gg.to_numpy(), cfg["velocity_model"])
    d = (e - gg) - (e - gg).mean()
    row.update(los_up=lu, v_egms=v_e, v_gnss_los=v_g, dv=v_g - v_e, sigma_v_egms=sv_e, sigma_v_gnss=sv_g,
               series_diff_std=float(d.std(ddof=1)), corr=float(np.corrcoef(e, gg)[0, 1]),
               n_dates=int(common.sum()), status="ok")
    row["meets_A6"] = min(frac_release, frac_dates) >= cfg["min_overlap"]
    return row


def series_for_plot(points: pd.DataFrame, date_cols: list, gnss: pd.DataFrame, radius_m: float, cfg: dict) -> pd.DataFrame:
    """Szeregi EGMS (mediana, kwartyle) i GNSS w LOS w datach EGMS, wyzerowane we wspólnej dacie odniesienia."""
    sel = points[points["distance_m"] <= radius_m]
    dates = pd.to_datetime(pd.Index(date_cols), format="%Y%m%d")
    vals = sel[date_cols].to_numpy(float)
    g = gnss.set_index("date")
    g_los = g["e_mm"] * sel["los_east"].mean() + g["n_mm"] * sel["los_north"].mean() + g["u_mm"] * sel["los_up"].mean()
    out = pd.DataFrame({"egms": np.median(vals, axis=0), "egms_q25": np.percentile(vals, 25, axis=0),
                        "egms_q75": np.percentile(vals, 75, axis=0),
                        "gnss": gnss_at_dates(g_los, dates, cfg["gnss_half_window_days"]).to_numpy()}, index=dates)
    ref = out.dropna().index[0]
    return out - out.loc[ref, ["egms", "egms", "egms", "gnss"]].to_numpy()


# ==============================================================================
# III. WERDYKT
# ==============================================================================
def verdict(results: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Kryteria na promieniu głównym, tylko pary stacja x ścieżka ze statusem 'ok' i spełnionym A6.
    K1: odsetek |dv| <= próg (stacje osiadające);  K2: mediana odchylenia różnicy szeregów;
    K3: kontrola negatywna - |v_EGMS| na stacjach stabilnych;  K4: nachylenie v_EGMS(v_GNSS) (raportowane).
    """
    th = cfg["thresholds"]
    r = results[(results["radius_m"] == cfg["radius_main_m"]) & (results["status"] == "ok") & results["meets_A6"].fillna(False).astype(bool)]
    sub, stab = r[r["group"] == "osiadająca"], r[r["group"] == "stabilna"]
    rows = []
    if len(sub):
        share = float((sub["dv"].abs() <= th["abs_dv_mm_yr"]).mean())
        rows.append(("K1 zgodność tempa osiadania", f"{share:.0%} par z |dv| <= {th['abs_dv_mm_yr']} mm/rok",
                     f">= {th['share_within']:.0%}", share >= th["share_within"], len(sub)))
        med = float(sub["series_diff_std"].median())
        rows.append(("K2 zgodność szeregów czasowych", f"mediana std różnicy {med:.1f} mm",
                     f"<= {th['series_std_mm']} mm", med <= th["series_std_mm"], len(sub)))
        bias, mad = float(sub["dv"].median()), float(1.4826 * (sub["dv"] - sub["dv"].median()).abs().median())
        rows.append(("Bias i rozrzut dv (informacyjnie)", f"mediana {bias:+.2f}, MAD*1.4826 {mad:.2f} mm/rok", "-", None, len(sub)))
    if len(stab):
        worst = float(stab["v_egms"].abs().max())
        rows.append(("K3 kontrola negatywna (stacje stabilne)", f"max |v_EGMS| {worst:.2f} mm/rok",
                     f"<= {th['stable_abs_v_mm_yr']} mm/rok", worst <= th["stable_abs_v_mm_yr"], len(stab)))
    if len(r) >= 3:
        slope, intercept = np.polyfit(r["v_gnss_los"], r["v_egms"], 1)
        rows.append(("K4 nachylenie v_EGMS względem v_GNSS (informacyjnie)", f"{slope:.2f} (wyraz wolny {intercept:+.2f})",
                     "bliskie 1", None, len(r)))
    return pd.DataFrame(rows, columns=["kryterium", "wynik", "próg", "spełnione", "n_par"])


def overall(verdict_table: pd.DataFrame) -> str:
    """Wniosek z kryteriów K1-K3 (reguła zapisana przed obliczeniami)."""
    p = dict(zip(verdict_table["kryterium"].str[:2], verdict_table["spełnione"]))
    if p.get("K1") and p.get("K2") and p.get("K3", True):
        return "POTWIERDZONE: EGMS odtwarza tempo osiadania mierzone przez GNSS w granicach przyjętych progów."
    if p.get("K1"):
        return "CZĘŚCIOWO: tempo osiadania zgodne, ale szeregi czasowe lub kontrola negatywna poza progiem."
    return "NIE POTWIERDZONE: tempo osiadania z EGMS różni się od GNSS ponad przyjęte progi; najpierw sprawdzić znak, układ i okno."


# ==============================================================================
# IV. WYKRESY (osie po angielsku)
# ==============================================================================
def plot_velocity_scatter(results: pd.DataFrame, cfg: dict):
    """Główny wykres walidacji: prędkość EGMS kontra GNSS w LOS, linia 1:1 i pas +-próg."""
    import matplotlib.pyplot as plt
    r = results[(results["radius_m"] == cfg["radius_main_m"]) & (results["status"] == "ok")]
    th = cfg["thresholds"]["abs_dv_mm_yr"]
    fig, ax = plt.subplots(figsize=(6.5, 6))
    lim = [min(r["v_gnss_los"].min(), r["v_egms"].min()) - 1, max(r["v_gnss_los"].max(), r["v_egms"].max()) + 1]
    ax.fill_between(lim, [lim[0] - th, lim[1] - th], [lim[0] + th, lim[1] + th], color="0.9", label=f"±{th} mm/yr")
    ax.plot(lim, lim, color="0.4", lw=1, label="1:1")
    for (grp, direction), g in r.groupby(["group", "direction"]):
        ax.scatter(g["v_gnss_los"], g["v_egms"], s=36, marker="o" if direction == "ascending" else "s",
                   facecolors="none" if grp == "stabilna" else None,
                   label=f"{'subsiding' if grp == 'osiadająca' else 'stable'} station, {direction}")
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("GNSS velocity projected to LOS [mm/yr]")
    ax.set_ylabel("EGMS L2b velocity, median within buffer [mm/yr]")
    ax.set_title(f"EGMS vs GNSS, buffer {cfg['radius_main_m']} m, {len(r)} station-track pairs")
    ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="upper left")
    return fig


def plot_series(series: pd.DataFrame, title: str):
    """Szereg EGMS (mediana, pas kwartyli) i GNSS w LOS w datach EGMS."""
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.fill_between(series.index, series["egms_q25"], series["egms_q75"], color="tab:orange", alpha=0.25,
                    label="EGMS interquartile range")
    ax.plot(series.index, series["egms"], color="tab:orange", lw=1.5, label="EGMS L2b (median)")
    ax.plot(series.index, series["gnss"], ".", ms=3, color="tab:blue", label="GNSS in LOS (median ±6 days)")
    ax.set_xlabel("Date"); ax.set_ylabel("LOS displacement [mm]")
    ax.set_title(title); ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="lower left")
    return fig
