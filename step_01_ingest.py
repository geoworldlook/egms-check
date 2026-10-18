"""
================================================================================
EGMS Check - KROK 1: DOSTĘP DO API EGMS, WYSZUKANIE I POBRANIE PLIKÓW, MANIFEST
================================================================================
Pobieranie gotowych produktów EGMS (Copernicus Land Monitoring Service) przez oficjalne API:
https://egms.land.copernicus.eu/insar-api/archive

  I.   Token: klucz serwisowy CLMS (JSON) -> JWT RS256 -> token dostępu (1 h).
       Według oficjalnego notatnika copernicus-land/egms-api (EGMS-API.ipynb).
  II.  Listy dozwolonych wartości (levels, releases, relative_orbits, directions, product_types).
  III. Wyszukanie (POST /search) dla punktu lub prostokąta; tabela trafień z rozmiarami.
  IV.  Pobranie przyrostowe tylko plików potwierdzonych przez autora; SHA-256 i wpis w MANIFEST.csv.
  IVb. Przegląd stacji GNSS NGL (prędkości MIDAS) według kryteriów podanych przez autora.
  V.   --selftest bez sieci: podpis JWT, wyszukanie, pobranie i manifest na atrapie serwera.

Status: kod napisany według oficjalnego notatnika, NIE był uruchamiany z prawdziwym tokenem
(serwer EGMS niedostępny ze środowiska, w którym powstał). Pierwsze uruchomienie: Colab.
Token jest kluczem prywatnym: nie drukujemy go, nie zapisujemy w repozytorium ani w logach.

Literatura i źródła: docs/evidence/F5_zrodla_danych.md (sekcja 1), docs/plans/Plan_v1_wdrozenie.md.
================================================================================
"""

import argparse
import hashlib
import json
import logging
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger("EGMSCheck_Ingest")

API_ENDPOINT = "https://egms.land.copernicus.eu/insar-api/archive"
GRANT_TYPE = "urn:ietf:params:oauth:grant-type:jwt-bearer"
TOKEN_LIFETIME_S = 3600          # jak w oficjalnym notatniku
LIST_NAMES = ("levels", "releases", "relative_orbits", "directions", "product_types")
MANIFEST_COLUMNS = ["file_path", "what", "source_url", "downloaded_on", "downloaded_by", "sha256",
                    "licence", "egms_release", "notes"]
EGMS_LICENCE = "Copernicus Land Monitoring Service data policy (full, open and free; attribution required)"


# ==============================================================================
# I. TOKEN
# ==============================================================================
def load_service_key(source: str) -> dict:
    """
    Klucz serwisowy CLMS z pliku (ścieżka) albo ze zmiennej środowiskowej ("env:NAZWA", cały JSON w zmiennej).
    Brak pliku lub zmiennej = wyjątek. Zawartości nie drukujemy.
    """
    import os
    if source.startswith("env:"):
        return json.loads(os.environ[source[4:]])
    return json.loads(Path(source).read_text(encoding="utf-8"))


def get_access_token(service_key_path, session) -> str:
    """
    Klucz serwisowy CLMS (plik JSON z client_id, user_id, token_uri, private_key) -> token dostępu.
    service_key_path: ścieżka do pliku albo "env:NAZWA_ZMIENNEJ".
    Wyjątek przy każdym błędzie; token nigdy nie trafia do logów.
    """
    import jwt  # pyjwt
    key = load_service_key(str(service_key_path))
    now = int(time.time())
    claim_set = {"iss": key["client_id"], "sub": key["user_id"], "aud": key["token_uri"],
                 "iat": now, "exp": now + TOKEN_LIFETIME_S}
    grant = jwt.encode(claim_set, key["private_key"], algorithm="RS256")
    r = session.post(key["token_uri"],
                     headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
                     data={"grant_type": GRANT_TYPE, "assertion": grant})
    r.raise_for_status()
    token = r.json()["access_token"]
    logger.info("Token dostępu CLMS uzyskany (ważny ok. 1 h).")
    return token


def api_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}


# ==============================================================================
# II. LISTY DOZWOLONYCH WARTOŚCI
# ==============================================================================
def get_api_lists(session, headers: dict, endpoint: str) -> dict:
    """GET /levels, /releases, ... -> słownik surowych odpowiedzi JSON (zapisujemy je jako dowód, pytanie A2)."""
    out = {}
    for name in LIST_NAMES:
        r = session.get(f"{endpoint}/{name}", headers=headers)
        r.raise_for_status()
        out[name] = r.json()
    return out


# ==============================================================================
# III. WYSZUKANIE
# ==============================================================================
def search_egms(session, headers: dict, endpoint: str, query: dict) -> dict:
    """POST /search. Wymagane w zapytaniu: levels, releases. Zwraca {"id": ..., "hits": [...]}."""
    missing = [k for k in ("levels", "releases") if k not in query]
    if missing:
        raise KeyError(f"Zapytanie bez wymaganych pól: {missing}")
    r = session.post(f"{endpoint}/search", headers=headers, data=json.dumps(query))
    r.raise_for_status()
    result = r.json()
    if "hits" not in result or "id" not in result:
        raise KeyError(f"Nieoczekiwana odpowiedź /search, klucze: {sorted(result)}")
    return result


def point_query(lon_deg: float, lat_deg: float, level: str, release: str) -> dict:
    """Zapytanie dla jednego punktu (bbox może być jednym punktem; F5, sekcja 1)."""
    return {"id": None, "bbox": [[lon_deg, lat_deg]], "levels": [level], "releases": [release]}


def hits_table(result: dict) -> pd.DataFrame:
    """Trafienia jako tabela; filesize w bajtach (plik skompresowany) -> MB."""
    cols = ["filename", "filesize", "release", "productLevel", "relativeOrbit", "direction", "burstId"]
    df = pd.DataFrame(result["hits"])
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"Trafienia bez pól {missing}; dostępne: {list(df.columns)}")
    df = df[cols + [c for c in ("bbox", "poly") if c in df.columns]].copy()
    df["filesize_mb"] = df["filesize"] / 1e6
    return df


# ==============================================================================
# IV. POBRANIE I MANIFEST
# ==============================================================================
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def update_manifest(manifest_path: Path, row: dict) -> None:
    """Dopisuje wiersz; ta sama ścieżka pliku z inną sumą SHA-256 = błąd (dane surowe są niezmienne)."""
    missing = [c for c in MANIFEST_COLUMNS if c not in row]
    if missing:
        raise KeyError(f"Wiersz manifestu bez pól {missing}")
    m = pd.read_csv(manifest_path, dtype=str) if Path(manifest_path).exists() else pd.DataFrame(columns=MANIFEST_COLUMNS)
    same = m[m["file_path"] == row["file_path"]]
    if len(same):
        if (same["sha256"] != row["sha256"]).any():
            raise ValueError(f"{row['file_path']}: plik w manifeście ma inną sumę SHA-256")
        return
    m = pd.concat([m, pd.DataFrame([row])], ignore_index=True)
    m.to_csv(manifest_path, index=False)


def sync_egms(session, headers: dict, endpoint: str, result: dict, filenames: list, out_dir: Path,
              manifest_path: Path, project_dir: Path, pause_s: float, downloaded_by: str) -> pd.DataFrame:
    """
    Pobiera WYŁĄCZNIE pliki z listy `filenames` (potwierdzonej przez autora po obejrzeniu rozmiarów).
    Przyrostowo: plik istniejący o rozmiarze zgodnym z `filesize` jest pomijany. Zapis przez plik .part.
    W manifeście adres bez identyfikatora zapytania (?id=... wygasa i nie jest częścią źródła).
    """
    hits = {h["filename"]: h for h in result["hits"]}
    unknown = [f for f in filenames if f not in hits]
    if unknown:
        raise KeyError(f"Pliki spoza wyniku wyszukiwania: {unknown}")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for k, fname in enumerate(filenames):
        hit = hits[fname]
        dest = out_dir / fname
        status = "skipped_existing"
        if not (dest.exists() and dest.stat().st_size == int(hit["filesize"])):
            if k > 0:
                time.sleep(pause_s)      # serwer odrzuca zbyt częste zapytania (Hrysiewicz i in. 2024)
            r = session.get(f"{endpoint}/download/{fname}", params={"id": result["id"]}, headers=headers, stream=True)
            r.raise_for_status()
            part = dest.with_suffix(dest.suffix + ".part")
            with open(part, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
            if part.stat().st_size != int(hit["filesize"]):
                raise IOError(f"{fname}: pobrano {part.stat().st_size} B, oczekiwano {hit['filesize']} B")
            part.replace(dest)
            status = "downloaded"
        digest = sha256_file(dest)
        update_manifest(manifest_path, {
            "file_path": manifest_path_of(dest, project_dir), "what": f"EGMS {hit['productLevel']} track "
            f"{hit['relativeOrbit']} {hit['direction']} burst {hit['burstId']}",
            "source_url": f"{endpoint}/download/{fname}",
            "downloaded_on": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "downloaded_by": downloaded_by,
            "sha256": digest, "licence": EGMS_LICENCE, "egms_release": hit["release"], "notes": status})
        rows.append({"filename": fname, "status": status, "bytes": dest.stat().st_size, "sha256": digest})
        logger.info(f"{fname}: {status}")
    return pd.DataFrame(rows)


def manifest_path_of(path: Path, project_dir: Path) -> str:
    """Ścieżka do manifestu: względna wobec projektu albo bezwzględna, gdy plik leży poza projektem (np. dysk Colab)."""
    p, root = Path(path).resolve(), Path(project_dir).resolve()
    return p.relative_to(root).as_posix() if p.is_relative_to(root) else p.as_posix()


# ------------------------------------------------------------------------------
# Szeregi GNSS z Nevada Geodetic Laboratory (format tenv3, układ IGS20)
# Pliki "EU" mają odjęty ruch płyty euroazjatyckiej, jak EGMS L2b/L3 (ETRF2000).
# Adresy według odnośników na stronach stacji NGL (sprawdzone dla PTO1, 2026-10-10).
# ------------------------------------------------------------------------------
NGL_LICENCE = "NGL products: free use with citation (Blewitt et al. 2018, Eos 99)"


def ngl_tenv3_url(site: str, frame: str) -> str:
    if frame == "EU":
        return f"https://geodesy.unr.edu/gps_timeseries/IGS20/tenv3/EU/{site}.EU.tenv3"
    if frame == "IGS20":
        return f"https://geodesy.unr.edu/gps_timeseries/IGS20/tenv3/IGS20/{site}.tenv3"
    raise ValueError(f"Nieznany układ NGL: {frame}")


def download_file(url: str, dest: Path, manifest_path: Path, project_dir: Path, what: str, licence: str,
                  downloaded_by: str) -> str:
    """Pobiera plik (jeśli go nie ma), liczy SHA-256 i dopisuje wiersz do manifestu. Zwraca SHA-256."""
    import requests
    dest = Path(dest)
    if not dest.exists():
        r = requests.get(url, timeout=300)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_suffix(dest.suffix + ".part")
        part.write_bytes(r.content)
        part.replace(dest)
    digest = sha256_file(dest)
    update_manifest(manifest_path, {"file_path": manifest_path_of(dest, project_dir), "what": what, "source_url": url,
                                    "downloaded_on": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                                    "downloaded_by": downloaded_by, "sha256": digest, "licence": licence,
                                    "egms_release": "", "notes": ""})
    return digest


def read_ngl_tenv3(path: Path) -> pd.DataFrame:
    """
    tenv3 -> dobowe przemieszczenia E, N, U [mm] względem pierwszej epoki szeregu.
    Pozycja = część całkowita (_e0, ____n0, u0) + część ułamkowa (__east, _north, ____up), w metrach.
    """
    t = pd.read_csv(path, sep=r"\s+")
    need = ["site", "YYMMMDD", "_e0(m)", "__east(m)", "____n0(m)", "_north(m)", "u0(m)", "____up(m)", "sig_u(m)"]
    missing = [c for c in need if c not in t.columns]
    if missing:
        raise KeyError(f"{path}: brak kolumn tenv3 {missing}")
    if t["site"].nunique() != 1:
        raise ValueError(f"{path}: więcej niż jedna stacja w pliku")
    out = pd.DataFrame({"date": pd.to_datetime(t["YYMMMDD"], format="%y%b%d")})
    for comp, (i, f) in {"e": ("_e0(m)", "__east(m)"), "n": ("____n0(m)", "_north(m)"), "u": ("u0(m)", "____up(m)")}.items():
        pos_m = t[i].astype(float) + t[f].astype(float)
        out[f"{comp}_mm"] = (pos_m - pos_m.iloc[0]) * 1000.0
    out["sig_u_mm"] = t["sig_u(m)"].astype(float) * 1000.0
    if not out["date"].is_monotonic_increasing:
        raise ValueError(f"{path}: daty nie rosną monotonicznie")
    return out


# ==============================================================================
# IVb. PRZEGLĄD STACJI GNSS (Nevada Geodetic Laboratory, prędkości MIDAS)
# ==============================================================================
# Plik prędkości MIDAS (Blewitt i in. 2016): jeden wiersz na stację, 27 kolumn. Układ kolumn spisany
# z opisu formatu NGL z pamięci; parser sprawdza liczbę kolumn i zakresy wartości, a notatnik
# drukuje kilka surowych wierszy do porównania z README formatu na stronie NGL.
MIDAS_COLUMNS = ["site", "midas_version", "t_first", "t_last", "duration_yr", "n_epochs", "n_epochs_good",
                 "n_pairs", "ve_m_yr", "vn_m_yr", "vu_m_yr", "sve_m_yr", "svn_m_yr", "svu_m_yr",
                 "e0_m", "n0_m", "u0_m", "out_e", "out_n", "out_u", "sd_e", "sd_n", "sd_u",
                 "n_steps", "lat_deg", "lon_deg", "height_m"]


def read_ngl_midas(text: str) -> pd.DataFrame:
    """Tekst pliku MIDAS -> tabela; prędkości przeliczone na mm/rok. Inna liczba kolumn = wyjątek."""
    rows = [ln.split() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    bad = [r[0] for r in rows if len(r) != len(MIDAS_COLUMNS)]
    if bad:
        raise ValueError(f"MIDAS: {len(bad)} wierszy z liczbą kolumn różną od {len(MIDAS_COLUMNS)}, np. {bad[:5]}")
    df = pd.DataFrame(rows, columns=MIDAS_COLUMNS)
    num = [c for c in MIDAS_COLUMNS if c not in ("site", "midas_version")]
    df[num] = df[num].astype(float)
    if not (df["lat_deg"].between(-90, 90).all() and df["lon_deg"].between(-360, 360).all()):
        raise ValueError("MIDAS: szerokość lub długość poza zakresem - zły układ kolumn")
    df["lon_deg"] = ((df["lon_deg"] + 180.0) % 360.0) - 180.0
    for c in ("ve", "vn", "vu"):
        df[f"{c}_mm_yr"] = df[f"{c}_m_yr"] * 1000.0
        df[f"s{c}_mm_yr"] = df[f"s{c}_m_yr"] * 1000.0
    return df


def screen_stations(midas: pd.DataFrame, bbox_lonlat: tuple, t_first_max: float, t_last_min: float,
                    vu_max_mm_yr: float) -> pd.DataFrame:
    """
    Stacje w prostokącie (lon_min, lat_min, lon_max, lat_max), z danymi od co najmniej t_first_max
    do co najmniej t_last_min (lata dziesiętne) i prędkością pionową <= vu_max_mm_yr (osiadanie).
    Kryteria podaje autor z góry; wynik to pełna lista spełniających je stacji, bez wyboru ręcznego.
    """
    lo0, la0, lo1, la1 = bbox_lonlat
    m = (midas["lon_deg"].between(lo0, lo1) & midas["lat_deg"].between(la0, la1)
         & (midas["t_first"] <= t_first_max) & (midas["t_last"] >= t_last_min)
         & (midas["vu_mm_yr"] <= vu_max_mm_yr))
    cols = ["site", "lat_deg", "lon_deg", "t_first", "t_last", "n_epochs_good", "vu_mm_yr", "svu_mm_yr", "n_steps"]
    return midas.loc[m, cols].sort_values("vu_mm_yr").reset_index(drop=True)


def select_stations(midas: pd.DataFrame, region_lonlat: tuple, control_region_lonlat: tuple, t_first_max: float,
                    t_last_min: float, svu_max_mm_yr: float, max_steps: int, vu_subsiding_max: float,
                    vu_stable_abs_max: float, n_stable: int, n_stable_min: int) -> pd.DataFrame:
    """
    Reguła wyboru stacji (2026-10-10). Wspólne warunki jakości: dane w oknie, niepewność vu <= svu_max,
    liczba skoków <= max_steps.
      'osiadająca': wszystkie stacje w region_lonlat z vu <= vu_subsiding_max;
      'stabilna'  : stacje w control_region_lonlat (region rozszerzony o okolicę) z |vu| <= vu_stable_abs_max,
                    n_stable najbliższych stacji osiadającej (kolumna dist_km). Kontrola negatywna:
                    ta sama metoda w okolicy musi pokazać brak ruchu.
    Bez wyboru ręcznego. Wyjątek, gdy stacji stabilnych jest mniej niż n_stable_min.
    """
    q = ((midas["t_first"] <= t_first_max) & (midas["t_last"] >= t_last_min)
         & (midas["svu_mm_yr"] <= svu_max_mm_yr) & (midas["n_steps"] <= max_steps))

    def inside(box):
        lo0, la0, lo1, la1 = box
        return midas["lon_deg"].between(lo0, lo1) & midas["lat_deg"].between(la0, la1)

    sub = midas[q & inside(region_lonlat) & (midas["vu_mm_yr"] <= vu_subsiding_max)].assign(group="osiadająca")
    if sub.empty:
        raise RuntimeError("Brak stacji osiadających spełniających regułę.")
    stab = midas[q & inside(control_region_lonlat) & (midas["vu_mm_yr"].abs() <= vu_stable_abs_max)].copy()
    lat0, lon0 = np.deg2rad(stab["lat_deg"].to_numpy())[:, None], np.deg2rad(stab["lon_deg"].to_numpy())[:, None]
    lat1, lon1 = np.deg2rad(sub["lat_deg"].to_numpy())[None, :], np.deg2rad(sub["lon_deg"].to_numpy())[None, :]
    hav = np.sin((lat1 - lat0) / 2) ** 2 + np.cos(lat0) * np.cos(lat1) * np.sin((lon1 - lon0) / 2) ** 2
    stab["dist_km"] = (2 * 6371.0 * np.arcsin(np.sqrt(hav))).min(axis=1) if len(stab) else []
    print(f"Stacje stabilne spełniające regułę w regionie kontrolnym: {len(stab)}; wybrano {min(n_stable, len(stab))} "
          f"najbliższych stacji osiadającej.")
    stab = stab.nsmallest(n_stable, "dist_km").assign(group="stabilna")
    if len(stab) < n_stable_min:
        raise RuntimeError(f"Stacji stabilnych {len(stab)} < {n_stable_min}: kontrola negatywna byłaby zbyt słaba. "
                           f"Rozszerz control_region_lonlat (decyzja przed pobraniem EGMS).")
    sub = sub.assign(dist_km=0.0)
    cols = ["site", "group", "lat_deg", "lon_deg", "t_first", "t_last", "vu_mm_yr", "svu_mm_yr", "n_steps", "dist_km"]
    return pd.concat([sub, stab])[cols].sort_values(["group", "vu_mm_yr"]).reset_index(drop=True)


def ngl_screening(session, headers: dict, endpoint: str, midas_url: str, bbox_lonlat: tuple,
                  t_first_max: float, t_last_min: float, vu_max_mm_yr: float, max_search: int,
                  release: str) -> pd.DataFrame:
    """
    Przegląd stacji NGL: plik MIDAS -> stacje spełniające kryteria -> pokrycie EGMS L2B (wyszukanie punktowe).
    Drukuje dane kontrolne (surowe wiersze, zakres dat w pliku, liczby stacji po każdym warunku).
    Wyjątek, gdy dane w pliku kończą się przed t_last_min albo żadna stacja nie spełnia kryteriów.
    """
    import requests
    r = requests.get(midas_url, timeout=300)
    r.raise_for_status()
    print("Trzy pierwsze surowe wiersze:")
    print("\n".join(r.text.splitlines()[:3]))
    midas = read_ngl_midas(r.text)
    t_end = midas["t_last"].max()
    print(f"{midas_url}: {len(midas)} stacji, najpóźniejszy koniec danych {t_end:.3f}")
    print("PTO1:", midas.loc[midas["site"] == "PTO1", ["t_first", "t_last", "vu_mm_yr", "svu_mm_yr"]].to_dict("records"))
    if t_end < t_last_min:
        raise RuntimeError(f"Dane w pliku MIDAS kończą się {t_end:.3f}, przed t_last_min={t_last_min}.")
    lo0, la0, lo1, la1 = bbox_lonlat
    eu = midas[midas["lon_deg"].between(lo0, lo1) & midas["lat_deg"].between(la0, la1)]
    ok_t = (eu["t_first"] <= t_first_max) & (eu["t_last"] >= t_last_min)
    print(f"Stacje w prostokącie: {len(eu)}; od <= {t_first_max}: {int((eu['t_first'] <= t_first_max).sum())}; "
          f"do >= {t_last_min}: {int((eu['t_last'] >= t_last_min).sum())}; oba warunki: {int(ok_t.sum())}; "
          f"oba + vu <= {vu_max_mm_yr} mm/rok: {int((ok_t & (eu['vu_mm_yr'] <= vu_max_mm_yr)).sum())}")
    cand = screen_stations(midas, bbox_lonlat, t_first_max, t_last_min, vu_max_mm_yr)
    if cand.empty:
        raise RuntimeError("Brak stacji spełniających kryteria.")
    cov = []
    for _, st in cand.head(max_search).iterrows():
        res = search_egms(session, headers, endpoint, point_query(st["lon_deg"], st["lat_deg"], "L2B", release))
        h = pd.DataFrame(res["hits"])
        cov.append({"site": st["site"], "n_files": len(h),
                    "tracks": sorted({int(x) for x in h["relativeOrbit"]}) if len(h) else [],
                    "total_MB": round(h["filesize"].sum() / 1e6, 1) if len(h) else 0.0})
    print(f"Pokrycie EGMS ({release}) sprawdzone dla {len(cov)} z {len(cand)} stacji (najszybsze osiadanie najpierw).")
    return cand.merge(pd.DataFrame(cov), on="site", how="left")


# ==============================================================================
# V. TEST OFFLINE
# ==============================================================================
class _FakeResponse:
    def __init__(self, payload=None, content=b""):
        self._payload, self._content = payload, content

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload

    def iter_content(self, chunk_size):
        for i in range(0, len(self._content), chunk_size):
            yield self._content[i:i + chunk_size]


class _FakeSession:
    """Atrapa serwera: sprawdza podpis JWT i zwraca ustalone odpowiedzi."""

    def __init__(self, public_key_pem, files):
        self.public_key_pem, self.files, self.calls = public_key_pem, files, []

    def post(self, url, headers=None, data=None):
        import jwt
        self.calls.append(("POST", url))
        if url.endswith("/token"):
            claims = jwt.decode(data["assertion"], self.public_key_pem, algorithms=["RS256"], audience=url)
            assert claims["iss"] == "client-1" and claims["sub"] == "user-1"
            assert data["grant_type"] == GRANT_TYPE
            return _FakeResponse({"access_token": "ACCESS"})
        if url.endswith("/search"):
            q = json.loads(data)
            assert headers["Authorization"] == "Bearer ACCESS" and q["levels"] == ["L2B"]
            hits = [{"filename": n, "filesize": len(c), "release": q["releases"][0], "productLevel": "L2B",
                     "relativeOrbit": 117, "direction": "ascending", "burstId": i} for i, (n, c) in enumerate(self.files.items())]
            return _FakeResponse({"id": "Q1", "hits": hits})
        raise AssertionError(url)

    def get(self, url, headers=None, params=None, stream=False):
        self.calls.append(("GET", url))
        name = url.rsplit("/", 1)[-1]
        if "/download/" in url:
            assert params == {"id": "Q1"}
            return _FakeResponse(content=self.files[name])
        return _FakeResponse([f"{name}-a", f"{name}-b"])


def _selftest() -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    tmp = Path(tempfile.mkdtemp(prefix="egmscheck_ingest_"))
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                  serialization.NoEncryption()).decode()
    pub_pem = priv.public_key().public_bytes(serialization.Encoding.PEM,
                                             serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    key_path = tmp / "service_key.json"
    key_path.write_text(json.dumps({"client_id": "client-1", "user_id": "user-1",
                                    "token_uri": "https://fake/token", "private_key": priv_pem}))
    files = {"EGMS_L2b_117_0265_IW2_VV_2018_2022_1.zip": b"x" * 3000, "EGMS_L2b_117_0266_IW2_VV_2018_2022_1.zip": b"y" * 10}
    s = _FakeSession(pub_pem, files)
    token = get_access_token(key_path, s)
    import os
    os.environ["EGMSCHECK_SELFTEST_KEY"] = key_path.read_text()
    assert get_access_token("env:EGMSCHECK_SELFTEST_KEY", s) == token
    h = api_headers(token)
    lists = get_api_lists(s, h, "https://fake/api")
    assert set(lists) == set(LIST_NAMES)
    res = search_egms(s, h, "https://fake/api", point_query(12.3341, 44.9515, "L2B", "2018-2022"))
    tab = hits_table(res)
    assert len(tab) == 2 and tab["filesize_mb"].sum() > 0
    proj = tmp / "proj"
    out = proj / "data" / "01_Raw_EGMS" / "2018-2022" / "L2b"
    man = proj / "data" / "00_Metadata" / "MANIFEST.csv"
    man.parent.mkdir(parents=True)
    r1 = sync_egms(s, h, "https://fake/api", res, list(files), out, man, proj, 0.0, "selftest")
    assert (r1["status"] == "downloaded").all()
    n_downloads = sum(1 for c in s.calls if "/download/" in c[1])
    r2 = sync_egms(s, h, "https://fake/api", res, list(files), out, man, proj, 0.0, "selftest")
    assert (r2["status"] == "skipped_existing").all()
    assert sum(1 for c in s.calls if "/download/" in c[1]) == n_downloads, "drugie uruchomienie nie może pobierać"
    m = pd.read_csv(man)
    assert len(m) == 2 and m["source_url"].str.contains(r"\?id=").sum() == 0
    assert m["sha256"].iat[0] == hashlib.sha256(files[m["file_path"].iat[0].rsplit("/", 1)[-1]]).hexdigest()
    try:
        sync_egms(s, h, "https://fake/api", res, ["nie_ma.zip"], out, man, proj, 0.0, "selftest")
        raise AssertionError("Oczekiwano wyjątku dla pliku spoza wyniku")
    except KeyError:
        pass
    # Przegląd stacji MIDAS na dwóch syntetycznych wierszach (27 kolumn).
    line = "PTO1 MIDAS5 2008.46 2026.70 18.2 6000 5900 5000 0.0001 0.0010 -0.0045 0.0001 0.0001 0.0004 " \
           "0 0 0 0.01 0.01 0.02 0.001 0.001 0.003 1 44.9515 12.3341 30.0"
    stable = line.replace("PTO1", "STBL").replace("-0.0045", "0.0002").replace("44.9515", "50.0")
    mid = read_ngl_midas(line + "\n" + stable)
    sel = screen_stations(mid, (-25.0, 34.0, 45.0, 72.0), 2019.9, 2025.0, -2.0)
    assert list(sel["site"]) == ["PTO1"] and abs(sel["vu_mm_yr"].iat[0] + 4.5) < 1e-9
    near = stable.replace("STBL", "NEAR").replace("50.0", "45.2")   # stabilna ~28 km od PTO1
    far = stable.replace("STBL", "FARS").replace("50.0", "47.0")    # stabilna ~230 km od PTO1
    mid3 = read_ngl_midas("\n".join([line, stable, near, far]))
    sel = select_stations(mid3, (12.0, 44.5, 12.6, 45.1), (10.0, 44.0, 14.0, 48.0), 2019.0, 2024.25, 1.0, 2,
                          -2.0, 1.0, 1, 1)
    assert list(sel["site"]) == ["PTO1", "NEAR"] and list(sel["group"]) == ["osiadająca", "stabilna"]
    assert 25 < sel["dist_km"].iat[1] < 32
    try:
        select_stations(mid3, (12.0, 44.5, 12.6, 45.1), (12.0, 44.5, 12.6, 45.1), 2019.0, 2024.25, 1.0, 2,
                        -2.0, 1.0, 3, 1)
        raise AssertionError("Oczekiwano wyjątku: brak stacji stabilnych")
    except RuntimeError:
        pass
    try:
        read_ngl_midas("XXXX MIDAS5 2008.0 2026.0")
        raise AssertionError("Oczekiwano wyjątku dla złej liczby kolumn")
    except ValueError:
        pass
    print("SELFTEST step_01_ingest OK")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    ap = argparse.ArgumentParser(description="EGMS Check - KROK 1")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--key", help="klucz CLMS: ścieżka do pliku JSON albo env:NAZWA_ZMIENNEJ")
    ap.add_argument("--api-lists", action="store_true", help="zapisz listy wartości API do data/00_Metadata")
    ap.add_argument("--search-point", nargs=4, metavar=("LON", "LAT", "LEVEL", "RELEASE"),
                    help="wyszukaj pliki dla punktu, bez pobierania")
    a = ap.parse_args()
    if a.selftest:
        _selftest()
    elif a.api_lists or a.search_point:
        import requests
        if not a.key:
            raise SystemExit("Podaj --key (plik JSON albo env:NAZWA).")
        session = requests.Session()
        headers = api_headers(get_access_token(a.key, session))
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        if a.api_lists:
            lists = get_api_lists(session, headers, API_ENDPOINT)
            out = Path(f"data/00_Metadata/egms_api_lists_{today}.json")
            out.write_text(json.dumps(lists, indent=1, ensure_ascii=False))
            print(json.dumps({k: (v if k != "relative_orbits" else f"{len(v)} wartości") for k, v in lists.items()},
                             ensure_ascii=False, indent=1))
        if a.search_point:
            lon, lat, level, release = a.search_point
            tab = hits_table(search_egms(session, headers, API_ENDPOINT, point_query(float(lon), float(lat), level, release)))
            print(tab.drop(columns=[c for c in ("poly", "bbox") if c in tab.columns]).to_string(index=False))
            print(f"Razem: {len(tab)} plików, {tab['filesize_mb'].sum():.1f} MB")
    else:
        ap.print_help()
