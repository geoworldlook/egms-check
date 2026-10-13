"""
================================================================================
EGMS Check - KROK 7: MONITORING: WSPÓLNY FORMAT SZEREGÓW, PRÓBKOWANIE 6/12 DNI, CZAS DO WYKRYCIA OSIADANIA, WYKRESY POKAZU
================================================================================
Interfejs według docs/plans/Plan_v2_implementacja.md (sekcje 2.2 i 4.3); cel: docs/plans/Plan_v2_pokaz_EGMS_monitoring.md
(etap A, ryciny 1-4, i pomost do etapu B). Kontynuacja kodu E1: prędkość i jej odchylenie formalne liczy
step_03_compare_gnss.fit_velocity (bez zmian), mediana punktów w dacie jak w step_03.compare_station_track,
wzorzec kolumn dat z step_02_checks_extract.

  I.   Format długi szeregów (sekcja 2.2): jedno źródło na wiersz; validate_long sprawdza kolumny, typy, puste klucze
       i duplikaty (source, site, track, component, date). Zapis/odczyt csv.gz z etykietami jako tekst
       (ścieżka "37" i punkt "0042" przechodzą przez plik bez zmiany typu).
  II.  Szeregi w formacie długim:
         EGMS: dla pary (punkt, ścieżka) mediana punktów w promieniu R w każdej dacie, co najmniej N punktów
         (Koudogbo i in. 2025, rozdz. 2.3.1.1; jak E1); wektor LOS = średnia punktów; odniesienie = pierwsza data
         z wartością (zapisana w ref_date). Odniesienie 'absolute' tylko dla produktów kalibrowanych (L2b, L3 U).
         Para z oczekiwanej listy (punkt x ścieżka) z mniej niż N punktami NIE daje szeregu, ale ma wiersz w tabeli
         statusów z liczbą punktów i powodem (poprawka cichego pominięcia N3b, docs/migracja/09_audyt_po_migracji.md).
         GNSS: dobowe E, N, U [mm] rzutowane na LOS: d_LOS = E * los_east + N * los_north + U * los_up (F4, sekcja 3),
         albo sama składowa U (wektor 0, 0, 1).
  III. Próbkowanie: odstęp do poprzedniej akwizycji; liczba odstępów 6 dni (Sentinel-1A + 1B), 12 dni (jeden satelita)
       i innych, osobno przed i po dacie końca Sentinel-1B (parametr z CHECK_CONFIG, do potwierdzenia).
       subsample: co k-ta akwizycja (symulacja 12 dni z 6 dni).
  IV.  Prędkość z realistyczną niepewnością i "ile czasu do wykrycia":
         v i sigma_formal: step_03.fit_velocity (MNK, szum biały). Reszty modelu mają autokorelację, więc
         sigma_formal jest zaniżone (F4, sekcja 8). Poprawka AR(1): rho1 = autokorelacja reszt z opóźnieniem 1,
         n_eff = n (1 - rho1) / (1 + rho1),  sigma_real = sigma_formal * sqrt(n / n_eff)
         (efektywna liczba obserwacji dla trendu: Santer i in. 2000, JGR 105(D6), 7337-7356; cytowane z wiedzy
         ogólnej, tekstu nie ma w docs/evidence/literatura_txt; Santer i in. liczą też wariancję reszt z n_eff - 2
         stopniami swobody - tu postać uproszczona ze specyfikacji, przy małym n_eff mniej zachowawcza).
         n_eff nie większe od liczby parametrów modelu = brak stopni swobody: NaN i status. Przybliżenia, jawnie:
           - opóźnienie 1 = kolejna akwizycja, nie stały odstęp czasu; przy próbkowaniu 6/12 dni i przerwach
             rho1 jest przybliżeniem autokorelacji procesu;
           - rho1 < 0 traktujemy jak 0 (sigma_real = sigma_formal): ujemna autokorelacja nie może zmniejszyć
             niepewności poniżej formalnej w tej uproszczonej poprawce;
           - rho1 liczone z reszt krótkiego szeregu jest obciążone w dół (model zjada część wolnej zmienności),
             więc w krótkich oknach sigma_real bywa nadal zaniżone; w oknie 12 mies. z modelem 'linear_annual'
             trend i sinusoida są silnie skorelowane i v bywa niestabilne (widać to w teście syntetycznym);
           - kryterium |v| > k * sigma_real używa k z konfiguracji, bez poprawki liczby stopni swobody t-Studenta.
         Szum potęgowy GNSS (flicker, błądzenie losowe; F4, sekcja 8) poprawka AR(1) opisuje tylko częściowo.
         Krzywa wykrycia: okna [start, start + L miesięcy); dla L < 12 model krótki (np. 'linear'), dla L >= 12
         model długi (np. 'linear_annual'; sinusoidy rocznej nie da się oddzielić od trendu w krótszym oknie).
         Okno jest pełne, gdy ma obserwacje w pierwszym i w ostatnim miesiącu (rozdzielczość długości okna);
         okno niepełne, za krótkie albo bez obserwacji = status z powodem i NaN, nie wynik.
         Czas do wykrycia: najkrótsze okno, od którego wszystkie dłuższe okna ze statusem 'ok' wykrywają ruch.
  V.   Wykresy pokazu (osie po angielsku; zwracają Figure, bez plt.show): mapa prędkości L3, szeregi w punkcie,
       próbkowanie na ścieżkach, krzywa wykrycia, Δh EGMS względem Δh niwelacji (niecki wyróżnione). Paleta: kategorie w stałej kolejności (niebieski, pomarańczowy,
       turkusowy, żółty), skala rozbieżna czerwony - szary - niebieski z zerem pośrodku.
  VI.  --selftest bez sieci: dane syntetyczne o znanej odpowiedzi (próbkowanie 6 -> 12 dni, prędkość -4 i 0 mm/rok,
       sinusoida roczna, szum AR(1)), zapis tylko do katalogu tymczasowego.

Odstępstwa od specyfikacji 4.3 (do akceptacji autora):
  - egms_points_to_long ma dodatkowy wymagany argument expected_pairs (site, track, direction: lista par z wyszukania
    plików) i zwraca krotkę (szeregi, statusy); bez listy oczekiwanych par para bez punktów w wycinku znika (N3b).
    source musi mieć prefiks EGMS_L2b (kierunki asc/desc) albo EGMS_L3U (kierunek 'vertical'); ref_date = pierwsza
    data z wartością mediany (gdy kafel L3 nie ma pierwszej daty sumy kafli), a nie bezwarunkowo pierwsza kolumna.
  - sampling_table(dates, s1b_end) zwraca (tabela, podsumowanie); data końca 1B jest parametrem.
  - velocity_realistic i detection_curve mają wymagany argument min_obs (w CHECK_CONFIG['monitoring'] go nie ma);
    min_obs < 10 = ValueError, bo step_03.fit_velocity i tak wymaga co najmniej 10 obserwacji.
  - plot_l3_map(cells, sites, title, vlim_percentile), plot_sampling(table_by_track, title, s1b_end): dodane parametry.
  - dodane: LONG_KEY, write_long, read_long; kolumna k_sigma w krzywej wykrycia (plot_detection czyta z niej k).
  - pion: track nie może być pusty (część klucza; puste pole nie przetrwa zapisu CSV); EGMS L3 ma track 'L3',
    direction 'vertical' (jak step_04.l3_cells_at_sites), GNSS U dostaje etykiety od wywołującego. Wiersze LOS
    muszą mieć direction 'ascending' albo 'descending'; dla U direction jest dowolne (może być puste).

Konwencje: przemieszczenia w mm, prędkości w mm/rok; ujemne = osiadanie / oddalanie od satelity. EGMS w EPSG:3035,
GNSS w stopniach WGS84 (tu już jako E, N, U). Daty: dzień UTC bez godziny. Parametry eksperymentu (promień, liczba
punktów, okna, modele, k, metoda sigma, min_obs, data końca 1B) pochodzą z CHECK_CONFIG, nie z sygnatur.
================================================================================
"""

import argparse
import logging
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from step_02_checks_extract import DATE_COL
from step_03_compare_gnss import fit_velocity, years_since

logger = logging.getLogger("EGMSCheck_Monitoring")

LONG_COLUMNS = ["region", "source", "site", "track", "direction", "component", "los_east", "los_north", "los_up",
                "date", "disp_mm", "ref_date", "reference", "n_points"]
LONG_KEY = ["source", "site", "track", "component", "date"]
LONG_REQUIRED_VALUES = LONG_KEY + ["region", "ref_date", "reference", "los_east", "los_north", "los_up"]
LONG_TEXT = ["region", "source", "site", "track", "component", "reference"]
COMPONENTS = ("LOS", "U")
VERTICAL_LOS = (0.0, 0.0, 1.0)
DIRECTION_COMPONENT = {"ascending": "LOS", "descending": "LOS", "vertical": "U"}   # step_04: L3 = 'vertical'
GNSS_SOURCE = {"LOS": "GNSS_NGL_LOS", "U": "GNSS_NGL_U"}                          # nazwy źródeł z sekcji 2.2
# Produkty EGMS kalibrowane (odniesienie 'absolute') i ich składowa; L2a (względny) nie jest tu dozwolony.
EGMS_SOURCE_COMPONENT = {"EGMS_L2b": "LOS", "EGMS_L3U": "U"}                     # prefiksy nazw z sekcji 2.2
REFERENCE_ABSOLUTE = "absolute"     # EGMS L2b/L3 kalibrowane modelem GNSS, GNSS w układzie EU: brak punktu odniesienia

VELOCITY_MODELS = ("linear", "linear_annual")   # jak step_03.fit_velocity
FIT_VELOCITY_MIN_OBS = 10                       # próg wbudowany w step_03.fit_velocity (nie zmieniamy go)
SIGMA_METHODS = ("ar1",)
ANNUAL_MODEL_MIN_MONTHS = 12                    # sinusoida roczna wymaga co najmniej jednego pełnego cyklu
GAP_TWO_SATELLITES_DAYS = 6                     # Sentinel-1A + 1B: cykl powtórzeń 12 dni / 2 satelity
GAP_ONE_SATELLITE_DAYS = 12                     # jeden satelita
PERIOD_BEFORE, PERIOD_AFTER = "before_s1b_end", "after_s1b_end"
S1B_LABEL = "Sentinel-1B end (6 -> 12 days)"

# Paleta (skill dataviz, paleta referencyjna): kolory kategorii w stałej kolejności, tusz tekstu, siatka.
SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SERIES_COLORS = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")          # niebieski, pomarańczowy, turkusowy, żółty
SOURCE_FAMILIES = (("EGMS", 0), ("GNSS", 1), ("S1_", 2), ("LEVELLING", 3))   # kolor idzie za rodziną źródła
DIVERGING = ("#e34948", "#f0efec", "#2a78d6")                        # osiadanie (czerwony) - 0 (szary) - wypiętrzanie


# ==============================================================================
# I. FORMAT DŁUGI
# ==============================================================================
def _track_label(x) -> str:
    """Etykieta ścieżki jako tekst: 37, 37.0, "37" -> "37"; "L3" bez zmian. Pusta lub NaN = wyjątek."""
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


def validate_long(df: pd.DataFrame) -> pd.DataFrame:
    """
    Kontrola formatu długiego (sekcja 2.2). Błąd przy: braku kolumny (KeyError), dacie innej niż datetime64 bez strefy
    albo z godziną (TypeError / ValueError), pustym kluczu lub wartości wymaganej (ValueError), etykiecie nie-tekstowej
    (TypeError), nieznanej składowej, wektorze innym niż (0, 0, 1) dla U, niejednoznacznym ref_date, wektorze, kierunku
    lub regionie w szeregu, duplikacie (source, site, track, component, date). disp_mm może być NaN (jawny brak),
    n_points też (GNSS, niwelacja). Zwraca kopię z kolumnami LONG_COLUMNS, posortowaną po kluczu; kolumny spoza
    LONG_COLUMNS (np. 'status' z step_08) są pomijane z ostrzeżeniem w logu - powody NaN trzeba zapisać osobno.
    """
    missing = [c for c in LONG_COLUMNS if c not in df.columns]
    if missing:
        raise KeyError(f"Format długi: brak kolumn {missing}; dostępne: {list(df.columns)}")
    extra = [c for c in df.columns if c not in LONG_COLUMNS]
    if extra:
        logger.warning(f"Format długi: pomijam kolumny spoza sekcji 2.2: {extra}")
    out = df[LONG_COLUMNS].copy()
    for c in ("date", "ref_date"):
        if not pd.api.types.is_datetime64_dtype(out[c]):
            raise TypeError(f"Kolumna {c}: oczekiwano datetime64 bez strefy (dzień UTC), jest {out[c].dtype}")
        if (out[c].notna() & (out[c] != out[c].dt.normalize())).any():
            raise ValueError(f"Kolumna {c}: daty z godziną; format długi przechowuje dzień")
    na = out[LONG_REQUIRED_VALUES].isna().sum()
    if na.any():
        raise ValueError(f"Format długi: puste wartości w kolumnach wymaganych {na[na > 0].to_dict()}")
    for c in LONG_TEXT:
        bad = ~out[c].map(lambda v: isinstance(v, str)).astype(bool)
        if bad.any():
            raise TypeError(f"Kolumna {c}: oczekiwano tekstu, są typy {sorted({type(v).__name__ for v in out.loc[bad, c]})}")
        if (out[c].str.strip() == "").any():
            raise ValueError(f"Kolumna {c}: puste etykiety")
    for c in ("disp_mm", "los_east", "los_north", "los_up", "n_points"):
        if not pd.api.types.is_numeric_dtype(out[c]):
            raise TypeError(f"Kolumna {c}: oczekiwano liczb, jest {out[c].dtype}")
    comp = set(out["component"]) - set(COMPONENTS)
    if comp:
        raise ValueError(f"Nieznane składowe {sorted(comp)}; dozwolone {COMPONENTS}")
    u = out["component"] == "U"
    if (out.loc[u, ["los_east", "los_north", "los_up"]].to_numpy() != np.array(VERTICAL_LOS)).any():
        raise ValueError("Składowa U wymaga wektora (0, 0, 1)")
    bad_dir = ~u & ~out["direction"].isin(["ascending", "descending"])
    if bad_dir.any():
        raise ValueError(f"Wiersze LOS bez kierunku ascending/descending: {sorted(out.loc[bad_dir, 'direction'].astype(str).unique())}")
    per = out.groupby(LONG_KEY[:-1])[["ref_date", "los_east", "los_north", "los_up", "direction", "region"]].nunique()
    if (per > 1).any().any():
        raise ValueError(f"Szeregi z więcej niż jedną datą odniesienia, wektorem LOS, kierunkiem lub regionem: "
                         f"{per[(per > 1).any(axis=1)].index.tolist()[:5]}")
    dup = out.duplicated(LONG_KEY, keep=False)
    if dup.any():
        raise ValueError(f"Duplikaty klucza {LONG_KEY}: {dup.sum()} wierszy, np. "
                         f"{out.loc[dup, LONG_KEY].head(3).to_dict('records')}")
    return out.sort_values(LONG_KEY).reset_index(drop=True)


def write_long(df: pd.DataFrame, path: Path) -> Path:
    """Zapis formatu długiego (csv.gz, kompresja z rozszerzenia) po kontroli validate_long; daty jako RRRR-MM-DD."""
    out = validate_long(df)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False, date_format="%Y-%m-%d")
    return path


def read_long(path: Path) -> pd.DataFrame:
    """Odczyt formatu długiego: etykiety jako tekst (bez zamiany "NA" na brak), daty jako datetime64; validate_long."""
    df = pd.read_csv(path, dtype={c: str for c in LONG_TEXT + ["direction"]}, keep_default_na=False, na_values=[""],
                     parse_dates=["date", "ref_date"], date_format="%Y-%m-%d")
    return validate_long(df)


# ==============================================================================
# II. SZEREGI EGMS I GNSS W FORMACIE DŁUGIM
# ==============================================================================
def egms_points_to_long(points: pd.DataFrame, date_cols: list, region: str, source: str, radius_m: float,
                        min_points: int, expected_pairs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Punkty EGMS (wynik step_02.extract_points po usunięciu duplikatów step_02.drop_cross_file_duplicates, z kolumnami
    track, direction; albo komórki step_04.l3_cells_at_sites) -> format długi.
    Dla każdej oczekiwanej pary (site, track) z expected_pairs: punkty z distance_m <= radius_m; co najmniej min_points
    -> szereg = mediana punktów w każdej dacie (np.median jak step_03.compare_station_track; NaN punktu daje NaN daty),
    los_* = średnia punktów, n_points, ref_date = pierwsza data z wartością mediany (zwykle pierwsza kolumna dat;
    późniejsza tylko, gdy kafel L3 nie ma pierwszych dat sumy kafli, step_04.l3_cells_at_sites), disp_mm względem
    ref_date (daty wcześniejsze = NaN), reference 'absolute' (tylko produkty kalibrowane: source z prefiksem
    EGMS_L2b albo EGMS_L3U; inny prefiks = ValueError).
    Składowa z kierunku: ascending/descending -> LOS, vertical -> U (wektor musi być 0, 0, 1); musi zgadzać się
    ze składową źródła (EGMS_L2b -> LOS, EGMS_L3U -> U).
    Zwraca (szeregi, statusy). Statusy: wiersz na KAŻDĄ oczekiwaną parę (region, source, site, track, direction,
    radius_m, min_points, n_points, ref_date, status): 'ok', 'brak punktów EGMS w promieniu R m', 'za mało punktów EGMS
    (n < N) w promieniu R m' albo 'mediana punktów bez wartości we wszystkich datach'. Para obecna w punktach,
    a nieobecna w expected_pairs = ValueError (niespójna konfiguracja); puste expected_pairs i distance_m = NaN też.
    """
    date_cols = list(date_cols)
    need = ["site", "track", "direction", "distance_m", "los_east", "los_north", "los_up"] + date_cols
    src_comp = [c for p, c in EGMS_SOURCE_COMPONENT.items() if str(source).startswith(p)]
    if len(src_comp) != 1:
        raise ValueError(f"source {source!r}: oczekiwano prefiksu {sorted(EGMS_SOURCE_COMPONENT)} (produkt kalibrowany, "
                         f"odniesienie 'absolute'); EGMS L2a jest względny i nie może dostać 'absolute'")
    if len(expected_pairs) == 0:
        raise ValueError(f"{source}: puste expected_pairs - nie ma czego raportować (lista par z wyszukania plików)")
    if len(points) == 0:
        # step_02.extract_points zwraca pd.DataFrame() bez kolumn, gdy nic nie leży w promieniu: każda para dostaje status.
        logger.info(f"{source}: brak punktów EGMS dla wszystkich {len(expected_pairs)} oczekiwanych par")
        points = pd.DataFrame({c: pd.Series(dtype=float if c not in ("site", "track", "direction") else object) for c in need})
    missing = [c for c in need if c not in points.columns]
    if missing:
        raise KeyError(f"Punkty EGMS: brak kolumn {missing}")
    bad = [c for c in date_cols if not DATE_COL.match(str(c))]
    if bad or len(date_cols) < 2:
        raise ValueError(f"Kolumny dat muszą mieć postać yyyymmdd (co najmniej 2); złe: {bad}")
    dates = pd.to_datetime(pd.Index(date_cols), format="%Y%m%d")
    if dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError("Kolumny dat muszą rosnąć ściśle")
    if not (np.isfinite(radius_m) and radius_m > 0):
        raise ValueError(f"radius_m musi być dodatni, jest {radius_m}")
    if isinstance(min_points, bool) or not isinstance(min_points, (int, np.integer)) or min_points < 1:
        raise ValueError(f"min_points musi być liczbą całkowitą >= 1, jest {min_points!r}")
    missing = [c for c in ("site", "track", "direction") if c not in expected_pairs.columns]
    if missing:
        raise KeyError(f"expected_pairs: brak kolumn {missing}")
    exp = expected_pairs[["site", "track", "direction"]].assign(track=expected_pairs["track"].map(_track_label))
    if exp.duplicated(["site", "track"]).any():
        raise ValueError(f"expected_pairs: powtórzone pary {exp.loc[exp.duplicated(['site', 'track']), ['site', 'track']].values.tolist()}")
    unknown_dir = set(exp["direction"]) - set(DIRECTION_COMPONENT)
    if unknown_dir:
        raise ValueError(f"Nieznane kierunki {sorted(map(str, unknown_dir))}; dozwolone {sorted(DIRECTION_COMPONENT)}")
    wrong_comp = sorted({d for d in exp["direction"] if DIRECTION_COMPONENT[d] != src_comp[0]})
    if wrong_comp:
        raise ValueError(f"source {source!r} ma składową {src_comp[0]}, a expected_pairs ma kierunki {wrong_comp}")
    if points["distance_m"].isna().any():
        raise ValueError(f"Punkty EGMS: {int(points['distance_m'].isna().sum())} punktów bez distance_m (NaN); "
                         f"nie wiadomo, czy leżą w promieniu")
    pts = points.assign(track=points["track"].map(_track_label))
    pair_dir = pts.groupby(["site", "track"])["direction"].agg(lambda s: set(s))
    multi = pair_dir[pair_dir.map(len) > 1]
    if len(multi):
        raise ValueError(f"Para (site, track) z kilkoma kierunkami: {multi.to_dict()}")
    exp_dir = dict(zip(zip(exp["site"], exp["track"]), exp["direction"]))
    extra = [k for k in pair_dir.index if k not in exp_dir]
    if extra:
        raise ValueError(f"Pary w punktach spoza expected_pairs: {extra}")
    clash = {k: (next(iter(v)), exp_dir[k]) for k, v in pair_dir.items() if next(iter(v)) != exp_dir[k]}
    if clash:
        raise ValueError(f"Kierunek w punktach różny od expected_pairs (punkty, oczekiwany): {clash}")

    groups = dict(tuple(pts[pts["distance_m"] <= radius_m].groupby(["site", "track"])))
    series, status = [], []
    for site, track, direction in exp.itertuples(index=False):
        p = groups.get((site, track), pts.iloc[:0])
        n = len(p)
        row = {"region": region, "source": source, "site": site, "track": track, "direction": direction,
               "radius_m": radius_m, "min_points": int(min_points), "n_points": n, "ref_date": pd.NaT}
        if n == 0:
            status.append({**row, "status": f"brak punktów EGMS w promieniu {radius_m:g} m"})
            continue
        if n < min_points:
            status.append({**row, "status": f"za mało punktów EGMS ({n} < {min_points}) w promieniu {radius_m:g} m"})
            continue
        med = np.median(p[date_cols].to_numpy(float), axis=0)
        fin = np.flatnonzero(np.isfinite(med))
        if len(fin) == 0:
            status.append({**row, "status": "mediana punktów bez wartości we wszystkich datach"})
            continue
        i_ref = int(fin[0])
        if i_ref > 0:
            logger.info(f"{source} {site}/{track}: data odniesienia {date_cols[i_ref]} (brak wartości w {i_ref} "
                        f"pierwszych datach, disp_mm = NaN)")
        le, ln, lu = (float(p[c].mean()) for c in ("los_east", "los_north", "los_up"))
        component = DIRECTION_COMPONENT[direction]
        if component == "U" and (le, ln, lu) != VERTICAL_LOS:
            raise ValueError(f"{site}/{track}: kierunek 'vertical' wymaga wektora (0, 0, 1), jest ({le}, {ln}, {lu})")
        series.append(pd.DataFrame({"region": region, "source": source, "site": site, "track": track,
                                    "direction": direction, "component": component, "los_east": le, "los_north": ln,
                                    "los_up": lu, "date": dates, "disp_mm": med - med[i_ref], "ref_date": dates[i_ref],
                                    "reference": REFERENCE_ABSOLUTE, "n_points": float(n)}))
        status.append({**row, "ref_date": dates[i_ref], "status": "ok"})
    st = pd.DataFrame(status)
    n_bad = int((st["status"] != "ok").sum())
    if n_bad:
        logger.info(f"{source}: {n_bad} z {len(st)} par bez szeregu (statusy w tabeli)")
    long = validate_long(pd.concat(series, ignore_index=True)) if series else \
        validate_long(pd.DataFrame({c: pd.Series(dtype="datetime64[ns]" if c in ("date", "ref_date") else
                                                 float if c in ("los_east", "los_north", "los_up", "disp_mm", "n_points")
                                                 else object) for c in LONG_COLUMNS}))
    return long, st


def gnss_to_long(gnss: pd.DataFrame, site: str, region: str, los_vec: tuple, component: str, track: str,
                 direction: str) -> pd.DataFrame:
    """
    Dobowe e_mm, n_mm, u_mm (step_01.read_ngl_tenv3) -> format długi. component 'LOS': d = E*le + N*ln + U*lu
    (los_vec = średni wektor punktów EGMS tej pary); 'U': d = U, los_vec musi być (0, 0, 1).
    source: GNSS_NGL_LOS / GNSS_NGL_U; ref_date = pierwsza doba wejścia, disp_mm względem niej; reference 'absolute';
    n_points NaN. Dla porównania z EGMS na wykresie wywołujący przycina GNSS do okna EGMS przed wywołaniem
    (wtedy pierwsza doba GNSS leży przy dacie odniesienia EGMS; pojedyncza doba niesie szum dobowy jako stałe przesunięcie).
    """
    missing = [c for c in ("date", "e_mm", "n_mm", "u_mm") if c not in gnss.columns]
    if missing:
        raise KeyError(f"GNSS {site}: brak kolumn {missing}")
    if component not in COMPONENTS:
        raise ValueError(f"Nieznana składowa {component!r}; dozwolone {COMPONENTS}")
    vec = tuple(float(v) for v in los_vec)
    if len(vec) != 3 or not np.isfinite(vec).all():
        raise ValueError(f"los_vec musi mieć 3 skończone składowe, jest {los_vec!r}")
    if component == "U" and vec != VERTICAL_LOS:
        raise ValueError(f"Składowa U wymaga wektora (0, 0, 1), jest {vec}")
    if gnss.empty:
        raise ValueError(f"GNSS {site}: pusty szereg")
    if not pd.api.types.is_datetime64_dtype(gnss["date"]):
        raise TypeError(f"GNSS {site}: kolumna date musi być datetime64, jest {gnss['date'].dtype}")
    dates = pd.DatetimeIndex(gnss["date"])
    if dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError(f"GNSS {site}: daty muszą rosnąć ściśle")
    le, ln, lu = vec
    proj = (gnss["e_mm"].to_numpy(float) * le + gnss["n_mm"].to_numpy(float) * ln + gnss["u_mm"].to_numpy(float) * lu)
    if not np.isfinite(proj[0]):
        raise ValueError(f"GNSS {site}: brak wartości w pierwszej dobie (data odniesienia)")
    out = pd.DataFrame({"region": region, "source": GNSS_SOURCE[component], "site": site, "track": _track_label(track),
                        "direction": direction, "component": component, "los_east": le, "los_north": ln, "los_up": lu,
                        "date": dates, "disp_mm": proj - proj[0], "ref_date": dates[0], "reference": REFERENCE_ABSOLUTE,
                        "n_points": np.nan})
    return validate_long(out)


# ==============================================================================
# III. PRÓBKOWANIE
# ==============================================================================
def _check_dates(dates, what: str) -> pd.DatetimeIndex:
    d = pd.DatetimeIndex(dates)
    if d.has_duplicates or not d.is_monotonic_increasing:
        raise ValueError(f"{what}: daty muszą rosnąć ściśle")
    return d


def sampling_table(dates: pd.DatetimeIndex, s1b_end) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Odstępy między akwizycjami. Tabela: date, gap_days (do poprzedniej akwizycji; NaN dla pierwszej), period
    ('before_s1b_end' gdy date <= s1b_end, inaczej 'after_s1b_end'; odstęp należy do okresu późniejszej akwizycji).
    Podsumowanie: wiersz na okres i 'all': n_dates, n_gaps, n_gap_6_days, n_gap_12_days, n_gap_other (dokładnie 6 / 12
    dni / reszta), median_gap_days (NaN bez odstępów), first_date, last_date. s1b_end z CHECK_CONFIG (do potwierdzenia).
    Daty muszą być dniami (północ): godzina akwizycji dałaby odstęp 6,0001 dnia liczony jako 'inny'.
    """
    d = _check_dates(dates, "sampling_table")
    if len(d) < 2:
        raise ValueError(f"sampling_table: za mało dat ({len(d)})")
    if (d != d.normalize()).any():
        raise ValueError("sampling_table: daty z godziną; podaj dzień akwizycji (np. DatetimeIndex.normalize())")
    if s1b_end is None or pd.isna(s1b_end):
        raise ValueError("sampling_table: brak daty końca Sentinel-1B (decyzja w CHECK_CONFIG['monitoring'])")
    s1b = pd.Timestamp(s1b_end)
    gap = np.r_[np.nan, np.diff(d.to_numpy()) / np.timedelta64(1, "D")]
    table = pd.DataFrame({"date": d, "gap_days": gap, "period": np.where(d <= s1b, PERIOD_BEFORE, PERIOD_AFTER)})
    rows = []
    for period in (PERIOD_BEFORE, PERIOD_AFTER, "all"):
        t = table if period == "all" else table[table["period"] == period]
        g = t["gap_days"].dropna()
        n6, n12 = int((g == GAP_TWO_SATELLITES_DAYS).sum()), int((g == GAP_ONE_SATELLITE_DAYS).sum())
        rows.append({"period": period, "n_dates": len(t), "n_gaps": len(g), "n_gap_6_days": n6, "n_gap_12_days": n12,
                     "n_gap_other": len(g) - n6 - n12, "median_gap_days": float(g.median()) if len(g) else np.nan,
                     "first_date": t["date"].min(), "last_date": t["date"].max()})
    return table, pd.DataFrame(rows)


def subsample(series: pd.Series, every_k: int) -> pd.Series:
    """
    Co k-ta akwizycja, od pierwszej (symulacja rzadszych przelotów: k = 2 na odcinku 6-dniowym daje 12 dni;
    na odcinku 12-dniowym dałoby 24 dni, więc wywołujący wybiera odcinek). Akwizycja z NaN też jest akwizycją.
    """
    if isinstance(every_k, bool) or not isinstance(every_k, (int, np.integer)) or every_k < 1:
        raise ValueError(f"every_k musi być liczbą całkowitą >= 1, jest {every_k!r}")
    _check_dates(series.index, "subsample")
    return series.iloc[::every_k]


# ==============================================================================
# IV. PRĘDKOŚĆ Z REALISTYCZNĄ NIEPEWNOŚCIĄ I CZAS DO WYKRYCIA
# ==============================================================================
def _design_matrix(dates: pd.DatetimeIndex, model: str) -> np.ndarray:
    """Ta sama macierz co w step_03.fit_velocity (czas w latach od pierwszej daty) - do reszt modelu."""
    t = years_since(dates, dates[0])
    cols = [np.ones_like(t), t]
    if model == "linear_annual":
        cols += [np.sin(2 * np.pi * t), np.cos(2 * np.pi * t)]
    return np.column_stack(cols)


def _check_min_obs(min_obs) -> None:
    if isinstance(min_obs, bool) or not isinstance(min_obs, (int, np.integer)):
        raise ValueError(f"min_obs musi być liczbą całkowitą, jest {min_obs!r}")
    if min_obs < FIT_VELOCITY_MIN_OBS:
        raise ValueError(f"min_obs = {min_obs} < {FIT_VELOCITY_MIN_OBS}: step_03.fit_velocity wymaga co najmniej "
                         f"{FIT_VELOCITY_MIN_OBS} obserwacji")


def velocity_realistic(dates, y_mm, model: str, sigma_method: str, min_obs: int) -> dict:
    """
    Prędkość [mm/rok] i niepewność z poprawką na autokorelację reszt.
    v, sigma_formal: step_03.fit_velocity (MNK, szum biały). rho1_raw = sum(e_i e_{i+1}) / sum(e_i^2) reszt modelu
    w kolejności akwizycji (przybliżenie przy nieregularnym próbkowaniu); rho1 = max(rho1_raw, 0);
    n_eff = n (1 - rho1) / (1 + rho1) (Santer i in. 2000); sigma_real = sigma_formal * sqrt(n / n_eff) - postać
    uproszczona ze specyfikacji (Santer i in. liczą wariancję reszt z n_eff - 2 stopniami swobody, co przy małym n_eff
    daje większe sigma; tu tego nie ma). n_eff <= liczba parametrów modelu (2 albo 4) = brak efektywnych stopni
    swobody: sigma_real NaN i status z powodem (v i sigma_formal zostają do wglądu).
    sigma_method inny niż 'ar1' -> ValueError. Mniej niż min_obs skończonych obserwacji -> NaN i status z powodem
    (fit_velocity nie jest wołane). Reszty dokładnie zerowe -> rho1 nieokreślone: NaN i status.
    """
    if sigma_method not in SIGMA_METHODS:
        raise ValueError(f"Nieznana metoda niepewności {sigma_method!r}; zaimplementowane {SIGMA_METHODS}")
    if model not in VELOCITY_MODELS:
        raise ValueError(f"Nieznany model prędkości {model!r}; dozwolone {VELOCITY_MODELS}")
    _check_min_obs(min_obs)
    d = _check_dates(dates, "velocity_realistic")
    if d.hasnans:
        raise ValueError("velocity_realistic: puste daty (NaT)")
    y = np.asarray(y_mm, dtype=float)
    if len(d) != len(y):
        raise ValueError(f"Liczba dat ({len(d)}) różna od liczby wartości ({len(y)})")
    m = np.isfinite(y)
    n = int(m.sum())
    out = {"model": model, "sigma_method": sigma_method, "n": n, "v_mm_yr": np.nan, "sigma_formal": np.nan,
           "rho1_raw": np.nan, "rho1": np.nan, "n_eff": np.nan, "sigma_real": np.nan}
    if n < min_obs:
        return {**out, "status": f"za mało obserwacji ({n} < {min_obs})"}
    v, s_formal = fit_velocity(d, y, model)
    A = _design_matrix(d[m], model)
    coef, *_ = np.linalg.lstsq(A, y[m], rcond=None)
    if not np.isclose(coef[1], v, rtol=1e-9, atol=1e-9):
        raise RuntimeError(f"Model reszt niezgodny z step_03.fit_velocity: {coef[1]} != {v}")
    e = y[m] - A @ coef
    ss = float(e @ e)
    out.update(v_mm_yr=v, sigma_formal=s_formal)
    if ss == 0.0:
        return {**out, "status": "reszty zerowe: autokorelacja nieokreślona"}
    r_raw = float(e[:-1] @ e[1:]) / ss
    r = max(r_raw, 0.0)
    if r >= 1.0:
        return {**out, "rho1_raw": r_raw, "rho1": r, "status": f"rho1 = {r:.3f} >= 1: n_eff nieokreślone"}
    n_eff = n * (1.0 - r) / (1.0 + r)
    out.update(rho1_raw=r_raw, rho1=r, n_eff=n_eff)
    if n_eff <= A.shape[1]:
        return {**out, "status": f"n_eff = {n_eff:.1f} <= liczba parametrów modelu ({A.shape[1]}): niepewność nieokreślona"}
    return {**out, "sigma_real": float(s_formal * np.sqrt(n / n_eff)), "status": "ok"}


def detection_curve(series: pd.Series, start, windows_months: list, model_short: str, model_long: str,
                    sigma_method: str, k: float, min_obs: int) -> pd.DataFrame:
    """
    Prędkość w rosnących oknach [start, start + L miesięcy) dla L z windows_months; model_short dla L < 12,
    model_long dla L >= 12. Okno pełne = obserwacja w pierwszym miesiącu okna i w ostatnim (od start + L - 1 mies.);
    okno niepełne / bez obserwacji / z małą liczbą obserwacji -> NaN i status z powodem.
    Kolumny: window_months, start_date, end_date (koniec okna, wyłączny), model, n, first_date, last_date, v_mm_yr,
    sigma_formal, rho1, n_eff, sigma_real, k_sigma, detected (|v| > k * sigma_real; <NA> gdy status != 'ok'), status.
    """
    if not isinstance(series, pd.Series):
        raise TypeError("series musi być pd.Series z indeksem dat")
    if not pd.api.types.is_datetime64_dtype(series.index):
        raise TypeError(f"Indeks szeregu musi być datetime64, jest {series.index.dtype}")
    _check_dates(series.index, "detection_curve")
    if sigma_method not in SIGMA_METHODS:
        raise ValueError(f"Nieznana metoda niepewności {sigma_method!r}; zaimplementowane {SIGMA_METHODS}")
    for mdl in (model_short, model_long):
        if mdl not in VELOCITY_MODELS:
            raise ValueError(f"Nieznany model prędkości {mdl!r}; dozwolone {VELOCITY_MODELS}")
    _check_min_obs(min_obs)
    if not (np.isfinite(k) and k > 0):
        raise ValueError(f"k musi być dodatnie, jest {k}")
    wins = list(windows_months)
    if not wins or any(isinstance(L, bool) or not isinstance(L, (int, np.integer)) or L < 1 for L in wins):
        raise ValueError(f"windows_months: niepusta lista liczb całkowitych >= 1, jest {wins}")
    if len(set(wins)) != len(wins):
        raise ValueError(f"windows_months: powtórzone długości {wins}")
    if start is None:
        raise ValueError("detection_curve: brak początku okna (CHECK_CONFIG['monitoring']['window_starts'])")
    t0 = pd.Timestamp(start)
    fin = series[np.isfinite(series.to_numpy(dtype=float))]
    rows = []
    for L in sorted(int(x) for x in wins):
        end = t0 + pd.DateOffset(months=L)
        w = fin[(fin.index >= t0) & (fin.index < end)]
        model = model_short if L < ANNUAL_MODEL_MIN_MONTHS else model_long
        row = {"window_months": L, "start_date": t0, "end_date": end, "model": model, "n": len(w),
               "first_date": w.index.min() if len(w) else pd.NaT, "last_date": w.index.max() if len(w) else pd.NaT,
               "v_mm_yr": np.nan, "sigma_formal": np.nan, "rho1": np.nan, "n_eff": np.nan, "sigma_real": np.nan,
               "k_sigma": float(k), "detected": pd.NA}
        if w.empty:
            rows.append({**row, "status": "brak obserwacji w oknie"})
            continue
        if w.index[0] >= t0 + pd.DateOffset(months=1):
            rows.append({**row, "status": f"okno niepełne: pierwsza obserwacja {w.index[0].date()} poza pierwszym miesiącem"})
            continue
        if w.index[-1] < t0 + pd.DateOffset(months=L - 1):
            rows.append({**row, "status": f"okno niepełne: ostatnia obserwacja {w.index[-1].date()} przed ostatnim miesiącem"})
            continue
        res = velocity_realistic(w.index, w.to_numpy(dtype=float), model, sigma_method, min_obs)
        row.update({c: res[c] for c in ("v_mm_yr", "sigma_formal", "rho1", "n_eff", "sigma_real")})
        if res["status"] == "ok":
            row["detected"] = bool(abs(res["v_mm_yr"]) > k * res["sigma_real"])
        rows.append({**row, "status": res["status"]})
    out = pd.DataFrame(rows)
    out["detected"] = out["detected"].astype("boolean")
    return out


def time_to_detection(curve: pd.DataFrame) -> float | None:
    """
    Najkrótsze okno [mies.] ze statusem 'ok', od którego to i wszystkie dłuższe okna ze statusem 'ok' wykrywają ruch.
    Okna bez wyniku są pomijane (nie potwierdzają i nie przeczą). None, gdy najdłuższe okno 'ok' nie wykrywa
    albo nie ma okien 'ok'.
    """
    missing = [c for c in ("window_months", "status", "detected") if c not in curve.columns]
    if missing:
        raise KeyError(f"Krzywa wykrycia: brak kolumn {missing}")
    ok = curve[curve["status"] == "ok"].sort_values("window_months")
    if ok.empty:
        return None
    if ok["detected"].isna().any():
        raise ValueError("Okno ze statusem 'ok' bez wartości detected")
    det = ok["detected"].astype(bool).to_numpy()
    if not det[-1]:
        return None
    i = len(det) - 1
    while i > 0 and det[i - 1]:
        i -= 1
    return float(ok["window_months"].iat[i])


# ==============================================================================
# V. WYKRESY (osie po angielsku)
# ==============================================================================
def _style(ax) -> None:
    """Wspólny wygląd: tło, siatka cienka i ciągła, osie stonowane, tekst w kolorach tuszu."""
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, lw=0.6, ls="-")
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_color(AXIS)
        s.set_linewidth(0.8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=MUTED, labelcolor=INK_2, labelsize=8)
    ax.xaxis.label.set_color(INK_2)
    ax.yaxis.label.set_color(INK_2)
    ax.title.set_color(INK)


def _source_color(source: str) -> str:
    """Kolor rodziny źródła (EGMS, GNSS, S1_*, LEVELLING); nieznana rodzina = KeyError."""
    for prefix, slot in SOURCE_FAMILIES:
        if source.startswith(prefix):
            return SERIES_COLORS[slot]
    raise KeyError(f"Nieznana rodzina źródła {source!r}; znane prefiksy {[p for p, _ in SOURCE_FAMILIES]}")


def _source_label(src: str) -> str:
    """Czytelna nazwa źródła do legendy: EGMS_L3U_2019_2023 -> 'EGMS L3 vertical, release 2019-2023', LEVELLING_* ->
    'levelling'; inne (GNSS, S1_*) bez zmian."""
    import re
    m = re.fullmatch(r"EGMS_(L3U|L2b)_(\d{4})_(\d{4})", src)
    if m:
        kind = "L3 vertical" if m.group(1) == "L3U" else "L2b calibrated (LOS)"
        return f"EGMS {kind}, release {m.group(2)}-{m.group(3)}"
    if src.startswith("LEVELLING"):
        return "levelling"
    return src


def _label_offsets(ax, xs, ys, names, fontsize: float) -> list:
    """
    Przesunięcia podpisów punktów [pt] bez nachodzenia: dla każdego punktu pierwsze z czterech położeń (prawo-góra,
    prawo-dół, lewo-góra, lewo-dół), którego prostokąt (szerokość ~0,6 * fontsize na znak) nie nachodzi na już
    postawione. Gdy żadne nie jest wolne - prawo-góra (nachodzenie widoczne, nie ukryte).
    """
    pts = ax.transData.transform(np.column_stack([xs, ys])) * 72.0 / ax.figure.dpi
    cands = [((5, 4), "left", "bottom"), ((5, -4), "left", "top"), ((-5, 4), "right", "bottom"), ((-5, -4), "right", "top")]
    placed, out = [], []
    for (px, py), name in zip(pts, names):
        wd, ht = 0.6 * fontsize * len(str(name)), 1.2 * fontsize
        choice = cands[0]
        for c in cands:
            (dx, dy), ha, va = c
            x0 = px + dx - (wd if ha == "right" else 0.0)
            y0 = py + dy - (ht if va == "top" else 0.0)
            box = (x0, y0, x0 + wd, y0 + ht)
            if all(box[2] <= b[0] or box[0] >= b[2] or box[3] <= b[1] or box[1] >= b[3] for b in placed):
                choice = c
                break
        (dx, dy), ha, va = choice
        x0, y0 = px + dx - (wd if ha == "right" else 0.0), py + dy - (ht if va == "top" else 0.0)
        placed.append((x0, y0, x0 + wd, y0 + ht))
        out.append(choice)
    return out


def _s1b_line(ax, s1b_end, label: bool) -> None:
    import matplotlib.transforms as mtransforms
    if s1b_end is None or pd.isna(s1b_end):
        raise ValueError("Brak daty końca Sentinel-1B (CHECK_CONFIG['monitoring']['s1b_end_date'])")
    x = pd.Timestamp(s1b_end)
    ax.axvline(x, color=MUTED, lw=1.0, zorder=1)
    if label:
        ax.text(x, 0.98, " " + S1B_LABEL, transform=mtransforms.blended_transform_factory(ax.transData, ax.transAxes),
                ha="left", va="top", fontsize=8, color=INK_2)


def plot_l3_map(cells: pd.DataFrame, sites: pd.DataFrame, title: str, vlim_percentile: float):
    """
    Mapa prędkości L3 (kolumny easting, northing, mean_velocity [mm/rok]) w km EPSG:3035; skala rozbieżna z zerem
    pośrodku, granice symetryczne +-percentyl |v| (vlim_percentile z CHECK_CONFIG), wartości poza zakresem w kolorze
    końca skali (strzałki paska). Punkty naziemnych (site, x_3035, y_3035) zaznaczone i podpisane bez nachodzenia
    podpisów; z kolumną site_type stacje GNSS to trójkąty, repery kółka (legenda).
    Komórki bez prędkości nie są rysowane; ich liczba jest w podpisie.
    """
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as pe
    from matplotlib.colors import LinearSegmentedColormap
    for name, df, cols in (("cells", cells, ["easting", "northing", "mean_velocity"]), ("sites", sites, ["site", "x_3035", "y_3035"])):
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise KeyError(f"{name}: brak kolumn {missing}")
    if not (np.isfinite(vlim_percentile) and 0 < vlim_percentile <= 100):
        raise ValueError(f"vlim_percentile musi być w (0, 100], jest {vlim_percentile}")
    v = cells["mean_velocity"].to_numpy(float)
    ok = np.isfinite(v)
    if not ok.any():
        raise ValueError("Brak komórek z prędkością")
    lim = float(np.percentile(np.abs(v[ok]), vlim_percentile))
    if lim == 0.0:
        raise ValueError("Zakres skali zerowy (wszystkie |v| w percentylu = 0)")
    x, y = cells["easting"].to_numpy(float)[ok] / 1000.0, cells["northing"].to_numpy(float)[ok] / 1000.0
    # Rozstaw siatki: mediana odstępów unikalnych eastingów zaokrąglonych do 1 m (minimum dałoby ułamek metra przy
    # szumie zmiennoprzecinkowym współrzędnych i niewidoczne komórki); jedna kolumna komórek -> 100 m (siatka L3).
    ux = np.unique(np.round(x * 1000.0)) / 1000.0
    spacing = float(np.median(np.diff(ux))) if len(ux) > 1 else 0.1
    w, h = max(np.ptp(x), spacing), max(np.ptp(y), spacing)
    ax_w = 5.6                                                        # szerokość osi [cal] przy figurze 8"
    fig, ax = plt.subplots(figsize=(8, float(np.clip(ax_w * h / w + 1.6, 4.0, 10.0))), facecolor=SURFACE)
    _style(ax)
    ax.grid(False)
    size = max((ax_w * 72 * spacing / max(w, h)) ** 2, 0.5)          # kwadrat ~ rozmiar komórki [pt^2]
    cmap = LinearSegmentedColormap.from_list("egms_diverging", DIVERGING)
    sc = ax.scatter(x, y, c=v[ok], cmap=cmap, vmin=-lim, vmax=lim, s=size, marker="s", linewidths=0, rasterized=True)
    cb = fig.colorbar(sc, ax=ax, shrink=0.8, extend="both")
    cb.set_label("Vertical velocity [mm/yr]", color=INK_2, fontsize=8)
    cb.ax.tick_params(colors=MUTED, labelcolor=INK_2, labelsize=8)
    cb.outline.set_edgecolor(AXIS)
    sx, sy = sites["x_3035"].to_numpy(float) / 1000.0, sites["y_3035"].to_numpy(float) / 1000.0
    kind = sites["site_type"].to_numpy(str) if "site_type" in sites.columns else np.full(len(sites), "site")
    for k, mk, lab in (("gnss", "^", "GNSS station"), ("benchmark", "o", "levelling benchmark"), ("site", "^", None)):
        sel = kind == k
        if sel.any():
            ax.scatter(sx[sel], sy[sel], marker=mk, s=64 if mk == "^" else 48, facecolor=INK, edgecolor=SURFACE,
                       linewidths=1.5, zorder=3, label=lab)
    if "site_type" in sites.columns:
        ax.legend(fontsize=7, loc="upper right", frameon=True, facecolor=SURFACE, edgecolor=AXIS, labelcolor=INK_2)
    ax.set_aspect("equal")
    fig.canvas.draw()                                                 # układ osi ustalony przed liczeniem podpisów
    halo = [pe.withStroke(linewidth=2.5, foreground=SURFACE)]
    for name, xs, ys, ((dx, dy), ha, va) in zip(sites["site"], sx, sy, _label_offsets(ax, sx, sy, sites["site"], 8)):
        ax.annotate(str(name), (xs, ys), xytext=(dx, dy), textcoords="offset points", fontsize=8, color=INK,
                    ha=ha, va=va, path_effects=halo, zorder=4)
    ax.set_xlabel("Easting, EPSG:3035 [km]")
    ax.set_ylabel("Northing, EPSG:3035 [km]")
    n_nan = int((~ok).sum())
    ax.set_title(f"{title}\n{int(ok.sum())} cells" + (f", {n_nan} without velocity (not drawn)" if n_nan else "")
                 + f"; colour limits ±{lim:.1f} mm/yr ({vlim_percentile:g}th percentile of |v|)", fontsize=9, color=INK)
    fig.tight_layout()
    return fig


def plot_series_long(long_df: pd.DataFrame, site: str, title: str, s1b_end):
    """
    Szeregi jednego punktu z formatu długiego: panel na ścieżkę LOS i jeden panel pionu (U); w panelu każde źródło
    w kolorze swojej rodziny (EGMS linia z punktami akwizycji, GNSS kropki dobowe, niwelacja duże punkty epok połączone
    cienką linią przerywaną - linia tylko łączy epoki, nie jest pomiarem). Legenda z czytelną nazwą źródła.
    W legendzie data odniesienia szeregu. Pionowa linia: koniec Sentinel-1B (s1b_end z CHECK_CONFIG).
    Dwa źródła tej samej rodziny w jednym panelu = ValueError.
    """
    import matplotlib.pyplot as plt
    d = validate_long(long_df)
    d = d[d["site"] == site]
    if d.empty:
        raise ValueError(f"Brak szeregów dla punktu {site!r}")
    d = d.assign(panel=np.where(d["component"] == "U", "U", "LOS " + d["track"]))
    keys = sorted(d["panel"].unique(), key=lambda p: (p == "U", p))
    fig, axes = plt.subplots(len(keys), 1, figsize=(9, 2.9 * len(keys) + 0.6), sharex=True, squeeze=False,
                             facecolor=SURFACE)
    for i, (ax, key) in enumerate(zip(axes[:, 0], keys)):
        _style(ax)
        g = d[d["panel"] == key]
        colors = {}
        for src, gs in g.groupby("source"):
            c = _source_color(src)
            if c in colors.values():
                raise ValueError(f"{site}, panel {key}: dwa źródła tej samej rodziny ({sorted(g['source'].unique())})")
            colors[src] = c
            gs = gs.sort_values("date")
            ref = gs["ref_date"].iat[0].date()
            name = _source_label(src)
            if src.startswith("GNSS"):
                ax.plot(gs["date"], gs["disp_mm"], ".", ms=2.5, color=c, alpha=0.6, label=f"{name} (daily, ref {ref})")
            elif src.startswith("LEVELLING"):
                n = len(gs)
                ax.plot(gs["date"], gs["disp_mm"], "--", lw=1.0, color=c, zorder=4)
                ax.plot(gs["date"], gs["disp_mm"], "o", ms=8, color=c, mec=INK, mew=1.0, zorder=5,
                        label=f"{name}, {n} survey{'s' if n != 1 else ''} (ref {ref}; dashed line only joins them)")
            else:
                npts = gs["n_points"].iat[0]
                unit = "cell" if src.startswith("EGMS_L3") else "point"
                extra = (f"median of {int(npts)} {unit}{'s' if npts != 1 else ''}, " if np.isfinite(npts) else "")
                ax.plot(gs["date"], gs["disp_mm"], "-o", lw=1.5, ms=3, color=c, mec=SURFACE, mew=0.5,
                        label=f"{name} ({extra}ref {ref})", zorder=3)
        _s1b_line(ax, s1b_end, label=(i == 0))
        if key == "U":
            ax.set_ylabel("Vertical displacement [mm]")
            head = "Vertical (U)"
        else:
            ax.set_ylabel("LOS displacement [mm]")
            head = f"Track {g['track'].iat[0]}, {g['direction'].iat[0]} (LOS)"
        if len(colors) > 1:
            ax.legend(fontsize=7, loc="lower left", frameon=False, labelcolor=INK_2)
            ax.set_title(head, loc="left", fontsize=9)
        else:
            ax.set_title(f"{head}: {_source_label(next(iter(colors)))}", loc="left", fontsize=9)
    axes[-1, 0].set_xlabel("Date")
    fig.suptitle(title, fontsize=11, color=INK)
    fig.tight_layout()
    return fig


def plot_sampling(table_by_track: dict, title: str, s1b_end):
    """
    Odstęp do poprzedniej akwizycji w czasie, panel na ścieżkę (tabele z sampling_table; wspólne osie);
    w panelu liczby odstępów 6 / 12 dni / innych; pionowa linia końca Sentinel-1B.
    """
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MultipleLocator
    if not table_by_track:
        raise ValueError("plot_sampling: brak tabel")
    fig, axes = plt.subplots(len(table_by_track), 1, figsize=(9, 1.7 * len(table_by_track) + 0.9), sharex=True,
                             sharey=True, squeeze=False, facecolor=SURFACE)
    gmax = 0.0
    for i, (ax, (track, t)) in enumerate(zip(axes[:, 0], sorted(table_by_track.items(), key=lambda kv: str(kv[0])))):
        missing = [c for c in ("date", "gap_days") if c not in t.columns]
        if missing:
            raise KeyError(f"Tabela próbkowania ścieżki {track}: brak kolumn {missing}")
        _style(ax)
        ax.plot(t["date"], t["gap_days"], "o", ms=3.5, color=SERIES_COLORS[0], mec=SURFACE, mew=0.5)
        _s1b_line(ax, s1b_end, label=(i == 0))
        g = t["gap_days"].dropna()
        gmax = max(gmax, float(g.max()))
        n6, n12 = int((g == GAP_TWO_SATELLITES_DAYS).sum()), int((g == GAP_ONE_SATELLITE_DAYS).sum())
        ax.set_title(f"Track {track}", loc="left", fontsize=9)
        ax.set_title(f"gaps: 6 d {n6} · 12 d {n12} · other {len(g) - n6 - n12}", loc="right", fontsize=8, color=INK_2)
    ax0 = axes[0, 0]
    ax0.yaxis.set_major_locator(MultipleLocator(6 if gmax <= 48 else 12 if gmax <= 120 else 30))
    ax0.set_ylim(0, gmax * 1.4)                                       # miejsce na podpis linii końca 1B
    axes[-1, 0].set_xlabel("Acquisition date")
    fig.supylabel("Gap to previous acquisition [days]", fontsize=9, color=INK_2)
    fig.suptitle(title, fontsize=11, color=INK)
    fig.tight_layout()
    return fig


def plot_detection(curves: dict, title: str):
    """
    Krzywe wykrycia (detection_curve) dla kilku szeregów: v z pasem +-k*sigma_real w funkcji długości okna,
    linia na szereg (kolory w kolejności słownika, maks. 4: podawaj EGMS, GNSS, własne przetworzenie, niwelacja
    w tej kolejności, jak w plot_series_long), punkt pełny = wykrycie, pusty = brak; linia zera.
    Okna bez wyniku nie są rysowane; ich liczba jest w legendzie. k czytane z kolumny k_sigma (jedno dla wszystkich).
    """
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    if not curves:
        raise ValueError("plot_detection: brak krzywych")
    if len(curves) > len(SERIES_COLORS):
        raise ValueError(f"plot_detection: maks. {len(SERIES_COLORS)} krzywe na wykresie (paleta), jest {len(curves)}")
    need = ["window_months", "v_mm_yr", "sigma_real", "detected", "status", "k_sigma"]
    for label, c in curves.items():
        missing = [x for x in need if x not in c.columns]
        if missing:
            raise KeyError(f"Krzywa {label!r}: brak kolumn {missing}")
    ks = {float(x) for c in curves.values() for x in c["k_sigma"].unique()}
    if len(ks) != 1:
        raise ValueError(f"Krzywe z różnym k: {sorted(ks)}")
    k = ks.pop()
    fig, ax = plt.subplots(figsize=(8.5, 4.8), facecolor=SURFACE)
    _style(ax)
    ax.axhline(0.0, color=AXIS, lw=1.0, zorder=1)
    handles, xticks = [], set()
    for (label, c), color in zip(curves.items(), SERIES_COLORS):
        ok = c[c["status"] == "ok"].sort_values("window_months")
        n_bad = len(c) - len(ok)
        x, v, band = ok["window_months"].to_numpy(float), ok["v_mm_yr"].to_numpy(float), k * ok["sigma_real"].to_numpy(float)
        det = ok["detected"].astype(bool).to_numpy()
        xticks.update(x.tolist())
        ax.fill_between(x, v - band, v + band, color=color, alpha=0.12, lw=0)
        ax.plot(x, v, "-", lw=1.5, color=color, zorder=2)
        ax.plot(x[det], v[det], "o", ms=7, color=color, mec=SURFACE, mew=1.5, zorder=3)
        ax.plot(x[~det], v[~det], "o", ms=7, mfc=SURFACE, mec=color, mew=1.5, zorder=3)
        ttd = time_to_detection(c)
        txt = f"detected from {ttd:g} months" if ttd is not None else "not detected"
        handles.append(Line2D([], [], color=color, lw=1.5, label=f"{label}: {txt}"
                              + (f" ({n_bad} window{'s' if n_bad != 1 else ''} without result)" if n_bad else "")))
    handles += [Patch(color=INK_2, alpha=0.15, lw=0, label=f"±{k:g} σ (AR(1)-adjusted)"),
                Line2D([], [], marker="o", ls="none", ms=7, color=INK_2, mec=SURFACE, label=f"detected: |v| > {k:g} σ"),
                Line2D([], [], marker="o", ls="none", ms=7, mfc=SURFACE, mec=INK_2, mew=1.5, label="not detected")]
    ax.set_xticks(sorted(xticks))
    ax.set_xlabel("Window length from start [months]")
    ax.set_ylabel("Velocity [mm/yr]")
    ax.set_title(title, fontsize=10, color=INK)
    ax.legend(handles=handles, fontsize=7, loc="best", frameon=False, labelcolor=INK_2)
    fig.tight_layout()
    return fig


def plot_levelling_scatter(res: pd.DataFrame, strong_mm_yr: float, title: str):
    """
    Δh EGMS (pion) względem Δh niwelacji między epokami reperu (wynik step_06.compare_levelling, wiersze 'ok'):
    kolor = grupa według NIWELACJI (|v_lev| >= strong_mm_yr: niecki; pozostałe), linia 1:1, osie w mm, równa skala.
    W legendzie liczba reperów w grupie; w tytule n i mediana |Δh_EGMS - Δh_niw|. Zero wierszy 'ok' = ValueError.
    """
    import matplotlib.pyplot as plt
    need = ["dh_lev_mm", "dh_egms_mm", "diff_mm", "v_lev_mm_yr", "status"]
    missing = [c for c in need if c not in res.columns]
    if missing:
        raise KeyError(f"plot_levelling_scatter: brak kolumn {missing}")
    if not (strong_mm_yr is not None and np.isfinite(strong_mm_yr) and strong_mm_yr > 0):
        raise ValueError(f"strong_mm_yr musi być dodatnie, jest {strong_mm_yr}")
    ok = res[res["status"] == "ok"]
    if ok.empty:
        raise ValueError("plot_levelling_scatter: brak reperów ze statusem 'ok'")
    strong = ok["v_lev_mm_yr"].abs() >= strong_mm_yr
    x, y = ok["dh_lev_mm"].to_numpy(float), ok["dh_egms_mm"].to_numpy(float)
    lo, hi = float(min(x.min(), y.min())), float(max(x.max(), y.max()))
    pad = 0.05 * max(hi - lo, 1.0)
    lo, hi = lo - pad, hi + pad
    fig, ax = plt.subplots(figsize=(6.4, 6.0), facecolor=SURFACE)
    _style(ax)
    ax.plot([lo, hi], [lo, hi], color=INK_2, lw=1.0, zorder=1, label="1:1")
    for mask, color, label in ((~strong, SERIES_COLORS[0], f"|v_levelling| < {strong_mm_yr:g} mm/yr"),
                               (strong, SERIES_COLORS[1], f"|v_levelling| >= {strong_mm_yr:g} mm/yr (subsidence bowls)")):
        m = mask.to_numpy()
        ax.plot(x[m], y[m], "o", ms=4.5, color=color, mec=SURFACE, mew=0.6, alpha=0.85, zorder=2,
                label=f"{label}, n = {int(m.sum())}")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    ax.set_xlabel("Levelling height change between epochs [mm]")
    ax.set_ylabel("EGMS vertical change between the same epochs [mm]")
    med = float(ok["diff_mm"].abs().median())
    ax.set_title(f"{title}\nn = {len(ok)} benchmarks; median |EGMS - levelling| = {med:.1f} mm", fontsize=9, color=INK)
    ax.legend(fontsize=7, loc="upper left", frameon=False, labelcolor=INK_2)
    fig.tight_layout()
    return fig


# ==============================================================================
# VI. TEST OFFLINE
# ==============================================================================
def _expect(exc, fn, *args, **kwargs):
    """Wywołanie musi zgłosić wyjątek exc (błąd głośny)."""
    try:
        fn(*args, **kwargs)
    except exc:
        return
    raise AssertionError(f"Oczekiwano {exc.__name__} z {fn.__name__}")


def _ar1(rng, n: int, phi: float, sigma: float) -> np.ndarray:
    """Szum AR(1) o odchyleniu brzegowym sigma (start ze stanu stacjonarnego)."""
    e = rng.normal(0.0, sigma * np.sqrt(1.0 - phi ** 2), n)
    x = np.empty(n)
    x[0] = rng.normal(0.0, sigma)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


def _selftest() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rng = np.random.default_rng(20261011)
    s1b_end = pd.Timestamp("2021-12-23")       # wartość testowa; w przebiegu CHECK_CONFIG['monitoring']['s1b_end_date']

    # 1. Próbkowanie: 6 dni do końca 1B, potem 12 dni, jedna brakująca akwizycja (odstęp 24 dni).
    d6 = pd.date_range("2020-01-04", s1b_end, freq="6D")
    d12 = pd.date_range(d6[-1] + pd.Timedelta(days=12), "2024-12-31", freq="12D")
    dates = d6.append(d12.delete(10))
    table, summ = sampling_table(dates, s1b_end)
    sb, sa, sall = (summ.set_index("period").loc[p] for p in (PERIOD_BEFORE, PERIOD_AFTER, "all"))
    assert (sb["n_dates"], sb["n_gap_6_days"], sb["n_gap_12_days"], sb["n_gap_other"]) == (len(d6), len(d6) - 1, 0, 0), sb
    assert (sa["n_dates"], sa["n_gap_6_days"], sa["n_gap_12_days"], sa["n_gap_other"]) == (len(d12) - 1, 0, len(d12) - 2, 1), sa
    assert sall["n_gaps"] == len(dates) - 1 and np.isnan(table["gap_days"].iat[0])
    assert sb["median_gap_days"] == 6 and sa["median_gap_days"] == 12
    _expect(ValueError, sampling_table, dates[::-1], s1b_end)
    _expect(ValueError, sampling_table, dates, None)
    _expect(ValueError, sampling_table, dates + pd.Timedelta(hours=5, minutes=43), s1b_end)        # godzina akwizycji
    # Granica: akwizycja dokładnie w dniu końca 1B należy do okresu 'przed'; odstęp do następnej - do 'po'.
    tb, _ = sampling_table(pd.DatetimeIndex([s1b_end - pd.Timedelta(days=6), s1b_end, s1b_end + pd.Timedelta(days=12)]),
                           s1b_end)
    assert tb["period"].tolist() == [PERIOD_BEFORE, PERIOD_BEFORE, PERIOD_AFTER], tb
    s3 = sampling_table(pd.DatetimeIndex(["2020-01-01", "2020-01-04", "2020-01-10"]), s1b_end)[1].set_index("period").loc["all"]
    assert (s3["n_gap_6_days"], s3["n_gap_12_days"], s3["n_gap_other"]) == (1, 0, 1), s3              # odstęp 3 dni = inny
    # Podpróbkowanie odcinka 6-dniowego co 2 -> same odstępy 12 dni.
    s6 = pd.Series(np.arange(len(d6), dtype=float), index=d6)
    sub = subsample(s6, 2)
    assert len(sub) == (len(d6) + 1) // 2 and sub.index[0] == d6[0]
    assert sampling_table(sub.index, s1b_end)[1].set_index("period").loc["all", "n_gap_12_days"] == len(sub) - 1
    _expect(ValueError, subsample, s6, 0)

    # 2. Prędkość realistyczna na szumie o znanej autokorelacji.
    dd = pd.date_range("2010-01-01", periods=3000, freq="D")
    tt = years_since(dd, dd[0])
    r_pos = velocity_realistic(dd, 2.0 * tt + _ar1(rng, len(dd), 0.5, 1.0), "linear", "ar1", 10)
    assert r_pos["status"] == "ok" and abs(r_pos["rho1"] - 0.5) < 0.05, r_pos
    assert np.isclose(r_pos["n_eff"], r_pos["n"] * (1 - r_pos["rho1"]) / (1 + r_pos["rho1"]))
    assert np.isclose(r_pos["sigma_real"], r_pos["sigma_formal"] * np.sqrt(r_pos["n"] / r_pos["n_eff"]))
    assert r_pos["sigma_real"] > 1.5 * r_pos["sigma_formal"] and abs(r_pos["v_mm_yr"] - 2.0) < 4 * r_pos["sigma_real"], r_pos
    r_neg = velocity_realistic(dd, 2.0 * tt + _ar1(rng, len(dd), -0.5, 1.0), "linear", "ar1", 10)
    assert r_neg["rho1_raw"] < 0 and r_neg["rho1"] == 0.0 and r_neg["sigma_real"] == r_neg["sigma_formal"], r_neg
    r_few = velocity_realistic(dd[:12], np.r_[np.full(3, np.nan), np.arange(9.0)], "linear", "ar1", 10)
    assert r_few["n"] == 9 and np.isnan(r_few["v_mm_yr"]) and r_few["status"].startswith("za mało"), r_few
    # Silnie skorelowane reszty przy 12 obserwacjach: n_eff <= 2 parametry -> sigma_real NaN z powodem, nie wynik.
    d12s = pd.date_range("2020-01-01", periods=12, freq="12D")
    r_dof = velocity_realistic(d12s, np.cumsum(np.cumsum(np.random.default_rng(4).normal(0, 1, 12))), "linear", "ar1", 10)
    assert r_dof["n_eff"] <= 2 and np.isnan(r_dof["sigma_real"]) and r_dof["status"].startswith("n_eff"), r_dof
    _expect(ValueError, velocity_realistic, dd, tt, "linear", "bootstrap", 10)
    _expect(ValueError, velocity_realistic, dd, tt, "linear", "ar1", 5)
    _expect(ValueError, velocity_realistic, dd, tt, "quadratic", "ar1", 10)

    # 3. Szeregi o znanej prędkości: -4 mm/rok i 0 mm/rok, sinusoida roczna 3 mm, ten sam szum AR(1) (phi 0,7, 3 mm).
    t = years_since(dates, dates[0])
    noise = _ar1(rng, len(dates), 0.7, 3.0)
    y_sub = -4.0 * t + 3.0 * np.sin(2 * np.pi * t) + noise
    y_0 = y_sub + 4.0 * t
    full = velocity_realistic(dates, y_sub, "linear_annual", "ar1", 10)
    assert full["rho1"] > 0 and full["sigma_real"] > full["sigma_formal"], full
    assert abs(full["v_mm_yr"] + 4.0) < 3 * full["sigma_real"], full
    windows = [3, 6, 9, 12, 18, 24, 36, 48, 60, 72]
    curve_sub = detection_curve(pd.Series(y_sub, index=dates), "2020-01-01", windows, "linear", "linear_annual", "ar1", 2.0, 10)
    curve_0 = detection_curve(pd.Series(y_0, index=dates), "2020-01-01", windows, "linear", "linear_annual", "ar1", 2.0, 10)
    st = curve_sub.set_index("window_months")["status"]
    assert st[72].startswith("okno niepełne") and st[60] == "ok" and st[3] == "ok", st
    assert (curve_sub.set_index("window_months")["model"].loc[[3, 6, 9]] == "linear").all()
    assert (curve_sub.set_index("window_months")["model"].loc[[12, 24, 60]] == "linear_annual").all()
    ttd_sub, ttd_0 = time_to_detection(curve_sub), time_to_detection(curve_0)
    assert ttd_sub is not None and ttd_sub <= 60, curve_sub
    long_ok = curve_0[(curve_0["window_months"] >= 24) & (curve_0["status"] == "ok")]
    assert len(long_ok) == 4 and not long_ok["detected"].astype(bool).any(), curve_0
    assert ttd_0 is None
    # Seria 12-dniowa: okno 3-miesięczne ma < 10 obserwacji -> status, nie wynik.
    c12 = detection_curve(pd.Series(y_sub, index=dates), "2023-01-01", [3, 12], "linear", "linear_annual", "ar1", 2.0, 10)
    assert c12["status"].iat[0].startswith("za mało") and pd.isna(c12["detected"].iat[0]) and c12["status"].iat[1] == "ok", c12
    # Reguły okna: początek przed danymi (> 1 mies.) = niepełne; okno po danych = brak obserwacji; koniec wyłączny.
    c_early = detection_curve(pd.Series(y_sub, index=dates), "2019-10-01", [6], "linear", "linear_annual", "ar1", 2.0, 10)
    assert c_early["status"].iat[0].startswith("okno niepełne: pierwsza") and np.isnan(c_early["v_mm_yr"].iat[0]), c_early
    c_late = detection_curve(pd.Series(y_sub, index=dates), "2026-01-01", [3], "linear", "linear_annual", "ar1", 2.0, 10)
    assert c_late["status"].iat[0] == "brak obserwacji w oknie" and c_late["n"].iat[0] == 0, c_late
    dday = pd.date_range("2020-01-01", "2020-04-01", freq="D")                      # 2020-04-01 = start + 3 mies.
    c_end = detection_curve(pd.Series(np.random.default_rng(1).normal(0, 1, len(dday)), index=dday), "2020-01-01", [3], "linear",
                            "linear_annual", "ar1", 2.0, 10)
    assert c_end["n"].iat[0] == 31 + 29 + 31 and c_end["last_date"].iat[0] == pd.Timestamp("2020-03-31"), c_end
    # time_to_detection na krzywej o znanej odpowiedzi (okno bez wyniku pomijane).
    hand = pd.DataFrame({"window_months": [3, 6, 12, 24, 36], "status": ["ok", "ok", "okno niepełne", "ok", "ok"],
                         "detected": pd.array([True, False, pd.NA, True, True], dtype="boolean")})
    assert time_to_detection(hand) == 24.0
    assert time_to_detection(hand.assign(detected=pd.array([True, True, pd.NA, True, True], dtype="boolean"))) == 3.0
    assert time_to_detection(hand.assign(detected=pd.array([True, True, pd.NA, True, False], dtype="boolean"))) is None

    # 4. EGMS -> format długi: mediana, średni wektor LOS, statusy par bez szeregu (N3b).
    date_cols = [d.strftime("%Y%m%d") for d in dates]
    truth = -4.0 * t * 0.78
    x0, y0 = 4_100_000.0, 3_300_000.0
    off = np.array([-2.0, -1.0, 0.0, 1.0, 5.0])                     # niesymetryczne: mediana = truth, średnia != truth
    vals_a = truth[None, :] + off[:, None] * (1.0 + np.arange(len(dates)))[None, :]   # mediana = truth dokładnie
    # Punkt w odległości dokładnie 100 m należy do bufora (<=, jak step_03); wektor: średnia (-0.58, 0.80) != mediana.
    pts_a = pd.DataFrame({"site": "A", "track": 37, "direction": "ascending", "distance_m": [10, 30, 50, 70, 100],
                          "los_east": [-0.60, -0.62, -0.61, -0.59, -0.48], "los_north": -0.11,
                          "los_up": [0.78, 0.77, 0.79, 0.78, 0.88]})
    far = pts_a.iloc[:1].assign(distance_m=150.0)                                        # poza promieniem 100 m
    pts = pd.concat([
        pd.concat([pts_a, pd.DataFrame(vals_a, columns=date_cols)], axis=1),
        pd.concat([far.reset_index(drop=True), pd.DataFrame(np.full((1, len(dates)), 1000.0), columns=date_cols)], axis=1),
        pd.DataFrame({"site": "A", "track": 88, "direction": "descending", "distance_m": [20.0, 40.0], "los_east": 0.6,
                      "los_north": -0.1, "los_up": 0.79, **{c: 0.0 for c in date_cols}}),
        pd.DataFrame({"site": "B", "track": 37, "direction": "ascending", "distance_m": [150.0, 180.0],
                      "los_east": -0.6, "los_north": -0.1, "los_up": 0.79, **{c: 0.0 for c in date_cols}}),
    ], ignore_index=True)
    expected = pd.DataFrame({"site": ["A", "A", "B", "C"], "track": [37, 88, 37, 37],
                             "direction": ["ascending", "descending", "ascending", "ascending"]})
    long_e, status = egms_points_to_long(pts, date_cols, "synthetic", "EGMS_L2b_2020_2024", 100.0, 3, expected)
    assert set(zip(long_e["site"], long_e["track"])) == {("A", "37")}, long_e[["site", "track"]].drop_duplicates()
    assert np.allclose(long_e["disp_mm"].to_numpy(), truth - truth[0]) and (long_e["ref_date"] == dates[0]).all()
    assert np.isclose(long_e["los_east"].iat[0], -0.58) and np.isclose(long_e["los_up"].iat[0], 0.80), long_e.iloc[0]
    assert (long_e["n_points"] == 5).all() and (long_e["component"] == "LOS").all() and len(long_e) == len(dates)
    stt = status.set_index(["site", "track"])
    assert len(status) == 4 and stt.loc[("A", "37"), "status"] == "ok" and stt.loc[("A", "37"), "ref_date"] == dates[0]
    assert stt.loc[("A", "88"), "n_points"] == 2 and stt.loc[("A", "88"), "status"].startswith("za mało")
    assert stt.loc[("B", "37"), "n_points"] == 0 and stt.loc[("B", "37"), "status"].startswith("brak punktów")
    assert stt.loc[("C", "37"), "n_points"] == 0 and stt.loc[("C", "37"), "status"].startswith("brak punktów")
    # Granica min_points: 2 punkty przy min_points = 2 dają szereg.
    st2 = egms_points_to_long(pts, date_cols, "synthetic", "EGMS_L2b_2020_2024", 100.0, 2, expected)[1]
    assert st2.set_index(["site", "track"]).loc[("A", "88"), "status"] == "ok", st2
    _expect(ValueError, egms_points_to_long, pts, date_cols, "synthetic", "EGMS_L2b_2020_2024", 100.0, 3,
            expected[expected["site"] != "B"])                                          # para B/37 spoza listy
    _expect(KeyError, egms_points_to_long, pts.drop(columns="direction"), date_cols, "synthetic", "EGMS_L2b_2020_2024",
            100.0, 3, expected)
    _expect(ValueError, egms_points_to_long, pts, date_cols, "synthetic", "EGMS_L2a_2020_2024", 100.0, 3, expected)  # względny
    _expect(ValueError, egms_points_to_long, pts, date_cols, "synthetic", "EGMS_L3U_2020_2024", 100.0, 3, expected)  # LOS != U
    _expect(ValueError, egms_points_to_long, pts, date_cols, "synthetic", "EGMS_L2b_2020_2024", 100.0, 3, expected.iloc[:0])
    _expect(ValueError, egms_points_to_long, pts.assign(distance_m=np.where(np.arange(len(pts)) == 2, np.nan, pts["distance_m"])),
            date_cols, "synthetic", "EGMS_L2b_2020_2024", 100.0, 3, expected)
    # Brak wartości w pierwszej dacie (kafel L3 bez pierwszej daty sumy kafli): odniesienie = druga data, pierwsza NaN.
    long_r, st_r = egms_points_to_long(pts.assign(**{date_cols[0]: np.nan}), date_cols, "synthetic", "EGMS_L2b_2020_2024",
                                       100.0, 3, expected)
    lr = long_r.set_index("date")["disp_mm"]
    assert (long_r["ref_date"] == dates[1]).all() and np.isnan(lr.iat[0]) and lr.iat[1] == 0.0, long_r.head(3)
    assert np.allclose(lr.iloc[1:].to_numpy(), truth[1:] - truth[1]) and st_r["ref_date"].iat[0] == dates[1]
    # Pusty wycinek (step_02.extract_points -> pd.DataFrame()): brak szeregów, ale status dla każdej pary.
    long_none, status_none = egms_points_to_long(pd.DataFrame(), date_cols, "synthetic", "EGMS_L2b_2020_2024", 100.0, 3,
                                                 expected)
    assert long_none.empty and list(long_none.columns) == LONG_COLUMNS and len(status_none) == 4
    assert (status_none["n_points"] == 0).all() and status_none["status"].str.startswith("brak punktów").all()
    # Komórka L3 (wektor 0, 0, 1, kierunek 'vertical') -> składowa U.
    l3 = pd.DataFrame({"site": "A", "track": "L3", "direction": "vertical", "distance_m": [35.0], "los_east": 0.0,
                       "los_north": 0.0, "los_up": 1.0, **{c: v for c, v in zip(date_cols, -4.0 * t)}})
    long_u, status_u = egms_points_to_long(l3, date_cols, "synthetic", "EGMS_L3U_2020_2024", 71.0, 1,
                                           pd.DataFrame({"site": ["A"], "track": ["L3"], "direction": ["vertical"]}))
    assert (long_u["component"] == "U").all() and (status_u["status"] == "ok").all()
    _expect(ValueError, egms_points_to_long, l3.assign(los_up=0.9), date_cols, "synthetic", "EGMS_L3U_2020_2024", 71.0,
            1, pd.DataFrame({"site": ["A"], "track": ["L3"], "direction": ["vertical"]}))

    # 5. GNSS -> format długi: znany rzut i odniesienie do pierwszej doby.
    gd = pd.date_range("2020-01-01", "2024-12-31", freq="D")
    i = np.arange(len(gd), dtype=float)
    gnss = pd.DataFrame({"date": gd, "e_mm": 5.0 + 1.0 * i, "n_mm": 2.0 * i, "u_mm": -3.0 * i})
    g_los = gnss_to_long(gnss, "A", "synthetic", (0.6, -0.1, 0.79), "LOS", 37, "ascending")
    assert np.allclose(g_los["disp_mm"].to_numpy(), -1.97 * i) and (g_los["source"] == "GNSS_NGL_LOS").all()
    assert g_los["track"].iat[0] == "37" and g_los["n_points"].isna().all()
    tg = years_since(gd, gd[0])
    g_u = gnss_to_long(gnss.assign(u_mm=-4.0 * tg + _ar1(rng, len(gd), 0.9, 2.0)), "A", "synthetic", (0, 0, 1), "U",
                       "L3", "vertical")
    _expect(ValueError, gnss_to_long, gnss, "A", "synthetic", (0.6, -0.1, 0.79), "U", "L3", "vertical")
    _expect(KeyError, gnss_to_long, gnss.drop(columns="u_mm"), "A", "synthetic", (0, 0, 1), "U", "L3", "vertical")
    g_los_plot = gnss_to_long(gnss.assign(e_mm=0.0, n_mm=0.0, u_mm=-4.0 * tg + _ar1(rng, len(gd), 0.9, 2.0)), "A",
                              "synthetic", tuple(long_e[["los_east", "los_north", "los_up"]].iloc[0]), "LOS", 37,
                              "ascending")

    # 6. validate_long łapie błędy; zapis i odczyt csv.gz zachowują etykiety tekstowe.
    long_all = validate_long(pd.concat([long_e, long_u, g_los_plot, g_u], ignore_index=True))
    _expect(ValueError, validate_long, pd.concat([long_e, long_e.iloc[:3]], ignore_index=True))      # duplikaty
    _expect(KeyError, validate_long, long_e.drop(columns="ref_date"))
    _expect(TypeError, validate_long, long_e.assign(date=long_e["date"].dt.strftime("%Y-%m-%d")))
    _expect(ValueError, validate_long, long_e.assign(site=np.where(np.arange(len(long_e)) == 0, None, "A")))
    _expect(TypeError, validate_long, long_e.assign(track=37))
    _expect(ValueError, validate_long, long_u.assign(los_up=0.9))
    _expect(ValueError, validate_long, long_e.assign(direction="vertical"))                       # LOS bez asc/desc
    _expect(ValueError, validate_long, long_e.assign(direction=np.where(np.arange(len(long_e)) < 5, "descending",
                                                                        "ascending")))         # dwa kierunki w szeregu
    with tempfile.TemporaryDirectory(prefix="egmscheck_monitoring_") as tmp:
        tmp = Path(tmp)
        p = write_long(pd.concat([long_all, long_e.assign(site="0042")], ignore_index=True), tmp / "x" / "timeseries_long.csv.gz")
        back = read_long(p)
        assert len(back) == len(long_all) + len(long_e) and "0042" in set(back["site"]) and "37" in set(back["track"])
        assert np.allclose(back.loc[back["site"] == "0042", "disp_mm"].to_numpy(), long_e["disp_mm"].to_numpy())

        # 7. Wykresy: cztery ryciny do PNG w katalogu tymczasowym.
        gx, gy = np.meshgrid(np.arange(-20, 21) * 100.0 + 50.0, np.arange(-15, 16) * 100.0 + 50.0)
        rate = -12.0 * np.exp(-(gx ** 2 + gy ** 2) / (2 * 700.0 ** 2)) + rng.normal(0, 0.5, gx.shape)
        cells = pd.DataFrame({"easting": x0 + gx.ravel(), "northing": y0 + gy.ravel(), "mean_velocity": rate.ravel()})
        cells.loc[5, "mean_velocity"] = np.nan
        sites = pd.DataFrame({"site": ["A", "B"], "x_3035": [x0, x0 + 1500.0], "y_3035": [y0, y0 - 900.0]})
        table_88, _ = sampling_table(d6.append(d12)[::2], s1b_end)
        lev_res = pd.DataFrame({"dh_lev_mm": [-60.0, -30.0, 2.0, -1.0], "dh_egms_mm": [-57.0, -33.0, 1.0, 0.0],
                                "v_lev_mm_yr": [-20.0, -10.0, 0.7, -0.3], "status": ["ok", "ok", "ok", "NaN: x"]})
        lev_res["diff_mm"] = lev_res["dh_egms_mm"] - lev_res["dh_lev_mm"]
        _expect(ValueError, plot_levelling_scatter, lev_res.assign(status="NaN: x"), 10.0, "x")
        _expect(ValueError, plot_levelling_scatter, lev_res, 0.0, "x")
        _expect(KeyError, plot_levelling_scatter, lev_res.drop(columns="diff_mm"), 10.0, "x")
        figs = {"map": plot_l3_map(cells, sites, "Synthetic L3 velocity", 98.0),
                "series": plot_series_long(long_all, "A", "Site A (synthetic)", s1b_end),
                "sampling": plot_sampling({"37": table, "88": table_88}, "Acquisition sampling (synthetic)", s1b_end),
                "detection": plot_detection({"EGMS synthetic, -4 mm/yr": curve_sub, "Stable synthetic, 0 mm/yr": curve_0},
                                            "Velocity vs window length (synthetic)"),
                "levelling": plot_levelling_scatter(lev_res, 10.0, "Synthetic benchmarks")}
        for name, fig in figs.items():
            out = tmp / f"{name}.png"
            fig.savefig(out, dpi=80, facecolor=fig.get_facecolor())
            plt.close(fig)
            assert out.stat().st_size > 1000, name
        _expect(ValueError, plot_series_long, long_all, "Z", "none", s1b_end)
        _expect(ValueError, plot_l3_map, cells, sites, "x", 0.0)
        # Czytelne nazwy źródeł; podpisy dwóch bliskich punktów mapy nie nachodzą na siebie; typy punktów w legendzie.
        assert _source_label("EGMS_L3U_2019_2023") == "EGMS L3 vertical, release 2019-2023"
        assert _source_label("EGMS_L2b_2020_2024").startswith("EGMS L2b") and _source_label("LEVELLING_NRW") == "levelling"
        assert _source_label("GNSS_NGL") == "GNSS_NGL"
        close = pd.DataFrame({"site": ["5204900182", "5204900194", "G1"], "x_3035": [x0, x0 + 60.0, x0 - 1500.0],
                              "y_3035": [y0, y0 + 30.0, y0], "site_type": ["benchmark", "benchmark", "gnss"]})
        fig = plot_l3_map(cells, close, "x", 98.0)
        ax = fig.axes[0]
        fig.canvas.draw()
        boxes = [t.get_window_extent() for t in ax.texts]
        assert len(boxes) == 3 and not boxes[0].overlaps(boxes[1]), "podpisy bliskich punktów nachodzą na siebie"
        assert sorted(t.get_text() for t in ax.get_legend().get_texts()) == ["GNSS station", "levelling benchmark"]
        plt.close(fig)
        _expect(ValueError, plot_sampling, {"37": table}, "x", None)                     # data końca 1B nieustalona
        # Szum zmiennoprzecinkowy współrzędnych nie zmienia rozmiaru komórek na mapie.
        size_clean = plot_l3_map(cells, sites, "x", 98.0)
        noisy = plot_l3_map(cells.assign(easting=cells["easting"] + np.where(np.arange(len(cells)) % 7 == 0, 1e-6, 0.0)),
                            sites, "x", 98.0)
        s_c, s_n = (f.axes[0].collections[0].get_sizes()[0] for f in (size_clean, noisy))
        assert np.isclose(s_c, s_n) and s_c > 10, (s_c, s_n)
        plt.close("all")

    print({"sampling_before": sb[["n_dates", "n_gap_6_days", "n_gap_12_days", "n_gap_other"]].to_dict(),
           "sampling_after": sa[["n_dates", "n_gap_6_days", "n_gap_12_days", "n_gap_other"]].to_dict(),
           "ar1_rho1_true_0.5": round(r_pos["rho1"], 3), "full_series": {k: (round(v, 3) if isinstance(v, float) else v)
                                                                       for k, v in full.items()},
           "time_to_detection_minus4": ttd_sub, "time_to_detection_0": ttd_0,
           "status_pairs": status[["site", "track", "n_points", "status"]].values.tolist()})
    print(curve_sub[["window_months", "n", "v_mm_yr", "sigma_formal", "sigma_real", "rho1", "detected", "status"]]
          .round(3).to_string(index=False))
    print("SELFTEST step_07_monitoring OK")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    ap = argparse.ArgumentParser(description="EGMS Check - KROK 7: monitoring, próbkowanie, czas do wykrycia")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        _selftest()
    else:
        ap.print_help()
