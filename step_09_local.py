"""
================================================================================
EGMS Check - KROK 9: OBLICZENIA NA WŁASNYM KOMPUTERZE (BEZ COLAB)
================================================================================
Układ jak w AgriScreen 1.1 (agriscreen/local.py): kod w klonie repozytorium (np. Pulpit\\GeoWorldLook\\projects\\
egms-check), dane w osobnym katalogu danych - zwykle zsynchronizowany Dysk Google (Mój dysk\\GeoWorldLook\\egmscheck,
ten sam układ data/... co w Colab, więc Colab dalej działa jako zapas). Klucze tylko w katalogu secrets na Dysku.

Polecenia (środowisko conda `egmscheck`, environment.yml):
    python step_09_local.py run [--region R] [--stage-b] [--confirm NAZWA=WARTOŚĆ] [--data-dir DIR] [--dry-run]
    python step_09_local.py settings        ustawienia po scaleniu (plik, zmienne środowiskowe, argumenty)
    python step_09_local.py approvals       stan zatwierdzeń CHECK_CONFIG
    python step_09_local.py selftest        testy bez sieci wszystkich modułów step_0N (--selftest)
    python step_09_local.py test [--work DIR] [--keep]
                                            pełny test: atrapy serwerów, dane o znanej odpowiedzi, trzy przebiegi
                                            (tests/local_harness/run_local_test.py)

Przebieg `run` = ta sama kolejność zadań co notatnik notebooks/EGMS_Monitoring.ipynb (build_colab_monitoring.py):
  dla każdego regionu: wyszukanie EGMS -> pobranie (po potwierdzeniu MB) -> stacje GNSS -> szeregi GNSS -> (niwelacja)
  -> ponowne wyszukanie i pobranie dla punktów spoza obszaru -> wycinki -> kontrole -> porównanie z GNSS
  -> (porównanie z niwelacją, drugie wydanie do niwelacji); potem monitoring archiwalny i ryciny dla każdego regionu;
  z --stage-b etap B (ASF HyP3 + MintPy, po potwierdzeniu liczby zleceń); na końcu run_summary.md.
Każde zadanie idzie przez step_05_colab_run.run_task (zapis w gwl_runs); pierwszy błąd zatrzymuje przebieg
(CLAUDE.md, zasada 3), tak jak w notatniku.

Potwierdzenia (ochrona przed przypadkowym pobraniem wielu GB i płatnymi zleceniami): komunikat zadania mówi, co
ustawić, np. "ustaw CONFIRM_MB_GRONINGEN = 4321" albo "ustaw CONFIRM_JOBS['37'] = 54". Lokalnie wpisuje się to samo:
    python step_09_local.py run --confirm CONFIRM_MB_GRONINGEN=4321 --confirm "CONFIRM_JOBS['37']=54"
albo trwale w local_settings.json, klucz "confirm". Bez tokenu CLMS przebieg czyta istniejące wycinki z data/03_Extracts/.

Ustawienia: DEFAULTS <- local_settings.json (katalog kodu, poza git) <- EGMSCHECK_DATA_DIR / EGMSCHECK_SECRETS_DIR
<- argumenty. Przykład local_settings.json:
    {"data_dir": "G:\\\\Mój dysk\\\\GeoWorldLook\\\\egmscheck", "secrets_dir": "G:\\\\Mój dysk\\\\GeoWorldLook\\\\secrets",
     "regions": ["groningen", "nrw_west"], "stage_b": false, "confirm": {}}
Blokada (drugi przebieg lokalny w tym samym czasie kończy się od razu), log w <dane>/data/logs/run_<czas>.log,
podsumowanie w <dane>/data/logs/last_run.json.

Brak nowej metody ani parametrów eksperymentu: wszystkie wartości pochodzą z CHECK_CONFIG (step_05_colab_run.py);
ten moduł zmienia tylko ścieżki tokenów (secrets_dir) i katalog danych.
================================================================================
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("EGMSCheck_Local")

CODE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = "local_settings.json"
DEFAULTS: Dict[str, Any] = {"data_dir": None, "secrets_dir": None, "regions": None, "stage_b": False, "confirm": {}}
TOKEN_FILES = {"token_path": "clms_token.json", "earthdata_path": "earthdata.json"}   # nazwy jak w CHECK_CONFIG
SELFTEST_MODULES = ["step_01_ingest", "step_04_egms_aoi", "step_05_colab_run", "step_06_ground", "step_07_monitoring",
                    "step_08_hyp3_mintpy"]
LOCK_NAME = ".egmscheck_local.lock"
LOCK_MAX_HOURS = 24
_CONFIRM_RE = re.compile(r"^\s*(CONFIRM_MB_[A-Z0-9_]+|CONFIRM_JOBS\[['\"]?(\w+)['\"]?\])\s*=\s*(\S+)\s*$")


# ==============================================================================
# Ustawienia
# ==============================================================================
def load_settings(code_dir: Path = CODE_DIR, **overrides: Any) -> Dict[str, Any]:
    """Ustawienia: DEFAULTS <- local_settings.json <- EGMSCHECK_DATA_DIR / EGMSCHECK_SECRETS_DIR <- argumenty."""
    s = copy.deepcopy(DEFAULTS)
    path = Path(code_dir) / SETTINGS_FILE
    if path.exists():
        s.update(json.loads(path.read_text(encoding="utf-8-sig")))     # utf-8-sig: plik z Windows może mieć BOM
    for key, var in (("data_dir", "EGMSCHECK_DATA_DIR"), ("secrets_dir", "EGMSCHECK_SECRETS_DIR")):
        if os.environ.get(var):
            s[key] = os.environ[var]
    confirm = merge_confirm(s.get("confirm") or {}, overrides.pop("confirm", None) or {})
    s.update({k: v for k, v in overrides.items() if v is not None})
    s["confirm"] = confirm
    if not s["data_dir"]:
        raise ValueError(f"Brak katalogu danych: ustaw data_dir w {path} albo EGMSCHECK_DATA_DIR albo --data-dir")
    s["data_dir"] = str(Path(s["data_dir"]).resolve())
    s["secrets_dir"] = str(Path(s["secrets_dir"]).resolve()) if s["secrets_dir"] else None
    return s


def parse_confirm(items: List[str]) -> Dict[str, Any]:
    """['CONFIRM_MB_GRONINGEN=4321', "CONFIRM_JOBS['37']=54"] -> {'CONFIRM_MB_GRONINGEN': 4321, 'CONFIRM_JOBS': {'37': 54}}."""
    out: Dict[str, Any] = {}
    for item in items:
        m = _CONFIRM_RE.match(item)
        if not m:
            raise ValueError(f"--confirm {item!r}: oczekiwano CONFIRM_MB_<REGION>=<MB> albo CONFIRM_JOBS['<ścieżka>']=<liczba>")
        value = int(m.group(3))
        if m.group(2) is not None:
            out.setdefault("CONFIRM_JOBS", {})[m.group(2)] = value
        else:
            out[m.group(1)] = value
    return out


def merge_confirm(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in extra.items():
        if k == "CONFIRM_JOBS":
            out["CONFIRM_JOBS"] = {**(out.get("CONFIRM_JOBS") or {}), **v}
        else:
            out[k] = v
    return out


def make_config(settings: Dict[str, Any], base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Kopia CHECK_CONFIG (albo `base`) z lokalnymi ścieżkami tokenów; parametry eksperymentu bez zmian."""
    from step_05_colab_run import CHECK_CONFIG
    cfg = copy.deepcopy(CHECK_CONFIG if base is None else base)
    cfg["project"]["project_dir"] = str(CODE_DIR)
    if settings.get("secrets_dir"):
        for key, name in TOKEN_FILES.items():
            cfg["project"][key] = str(Path(settings["secrets_dir"]) / name)
    return cfg


# ==============================================================================
# Plan zadań (kolejność z notebooks/EGMS_Monitoring.ipynb)
# ==============================================================================
def plan_tasks(cfg: Dict[str, Any], regions: List[str], stage_b: bool) -> List[Tuple[str, str, Tuple[str, ...]]]:
    """
    Lista (nazwa w gwl_runs, funkcja task_* ze step_05, dodatkowe argumenty po rt, cfg). Argument 'CONFIRM:<nazwa>'
    zastępuje wartość potwierdzenia z ustawień; etap B ma krok 'TRACKS:' (pętla po ścieżkach z planu HyP3).
    """
    unknown = [r for r in regions if r not in cfg["regions"]]
    if unknown:
        raise KeyError(f"Nieznane regiony {unknown}; w CHECK_CONFIG: {sorted(cfg['regions'])}")
    steps: List[Tuple[str, str, Tuple[str, ...]]] = []
    for r in regions:
        lev = cfg["regions"][r].get("levelling") is not None
        mb = f"CONFIRM:CONFIRM_MB_{r.upper()}"
        steps += [(f"egms_search_{r}", "task_egms_search", (r,)),
                  (f"egms_download_{r}", "task_egms_download", (r, mb)),
                  (f"select_gnss_{r}", "task_select_gnss", (r,)),
                  (f"gnss_download_{r}", "task_gnss_download", (r,))]
        if lev:
            steps.append((f"levelling_{r}", "task_levelling", (r,)))
        steps += [(f"egms_search_sites_{r}", "task_egms_search", (r,)),
                  (f"egms_download_sites_{r}", "task_egms_download", (r, mb)),
                  (f"extract_{r}", "task_extract", (r,)),
                  (f"checks_{r}", "task_checks", (r,)),
                  (f"compare_gnss_{r}", "task_compare_gnss", (r,))]
        if lev:
            steps += [(f"compare_levelling_{r}", "task_compare_levelling", (r,)),
                      (f"levelling_egms_search_{r}", "task_levelling_egms_search", (r,)),
                      (f"levelling_egms_download_{r}", "task_levelling_egms_download",
                       (r, f"CONFIRM:CONFIRM_MB_{r.upper()}_LEVELLING")),
                      (f"levelling_extract_{r}", "task_levelling_extract", (r,)),
                      (f"compare_levelling_check_{r}", "task_compare_levelling_check", (r,))]
    for r in regions:
        steps += [(f"monitoring_archive_{r}", "task_monitoring_archive", (r,)),
                  (f"figures_{r}", "task_figures", (r,))]
    if stage_b:
        r = cfg["hyp3"]["region"]
        steps += [(f"hyp3_plan_{r}", "task_hyp3_plan", (r,)), (f"TRACKS:{r}", "", ())]
    steps.append(("summary", "task_summary", ()))
    return steps


def _stage_b_tracks(rt: Dict[str, Any], cfg: Dict[str, Any], region: str,
                    confirm: Dict[str, Any]) -> List[Tuple[str, str, Tuple[Any, ...]]]:
    """Etap B po planie: wszystkie zlecenia, potem pobranie, MintPy i dowiązanie dla każdej ścieżki (jak notatnik)."""
    import step_05_colab_run as s5
    jobs = confirm.get("CONFIRM_JOBS") or {}
    tracks = s5.hyp3_planned_tracks(rt, cfg, region)
    steps = [(f"hyp3_submit_{region}_{t}", "task_hyp3_submit", (region, t, jobs.get(t))) for t in tracks]
    for t in tracks:
        steps += [(f"hyp3_download_{region}_{t}", "task_hyp3_download", (region, t)),
                  (f"mintpy_{region}_{t}", "task_mintpy", (region, t)),
                  (f"hyp3_compare_{region}_{t}", "task_hyp3_compare", (region, t))]
    return steps


def long_paths_enabled() -> bool:
    """Windows: czy system przyjmuje ścieżki dłuższe niż 260 znaków (LongPathsEnabled = 1). Inne systemy: True."""
    if os.name != "nt":
        return True
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem") as k:
            return winreg.QueryValueEx(k, "LongPathsEnabled")[0] == 1
    except OSError:
        return False


def require_long_paths() -> None:
    """
    Etap B na Windows wymaga długich ścieżek: nazwa produktu HyP3 (INSAR_ISCE_MULTI_BURST) ma ok. 80 znaków i występuje
    w ścieżce pliku dwa razy (<produkt>/<produkt>_<warstwa>.tif), przy rozpakowaniu trzy razy - razem ponad 260 znaków.
    Bez tego przebieg zatrzymałby się w połowie pobierania; zatrzymujemy go przed etapem B, z instrukcją.
    """
    if not long_paths_enabled():
        raise RuntimeError(
            "Etap B na Windows wymaga długich ścieżek (limit 260 znaków; nazwy produktów HyP3 mają ok. 80 znaków). "
            "Jednorazowo w PowerShell uruchomionym jako administrator: New-ItemProperty -Path "
            "'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\FileSystem' -Name LongPathsEnabled -Value 1 -PropertyType DWORD "
            "-Force; potem otwórz nową konsolę. Etap A działa bez tej zmiany.")


def run_all(rt: Dict[str, Any], cfg: Dict[str, Any], regions: List[str], stage_b: bool,
            confirm: Dict[str, Any]) -> List[str]:
    """Uruchamia plan zadań przez run_task; pierwszy błąd idzie dalej (bez przechwytywania). Zwraca nazwy zadań."""
    import step_05_colab_run as s5
    done: List[str] = []
    queue = list(plan_tasks(cfg, regions, stage_b))
    if stage_b:
        require_long_paths()                  # przed etapem A: nie liczymy godzinami, żeby stanąć na etapie B
        s5.ensure_packages(s5.STAGE_B_PACKAGES)
    while queue:
        name, fn_name, args = queue.pop(0)
        if name.startswith("TRACKS:"):
            queue = _stage_b_tracks(rt, cfg, name.split(":", 1)[1], confirm) + queue
            continue
        real = [confirm.get(a.split(":", 1)[1]) if isinstance(a, str) and a.startswith("CONFIRM:") else a for a in args]
        s5.run_task(rt, name, getattr(s5, fn_name), rt, cfg, *real)
        done.append(name)
    return done


# ==============================================================================
# Blokada, log, przebieg
# ==============================================================================
class Lock:
    """Blokada w katalogu danych: drugi przebieg lokalny w tym samym czasie kończy się od razu."""

    def __init__(self, data_dir: str):
        self.path = Path(data_dir) / "data" / "registry" / LOCK_NAME

    def __enter__(self) -> "Lock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and time.time() - self.path.stat().st_mtime < LOCK_MAX_HOURS * 3600:
            raise RuntimeError(f"Inny przebieg trwa (blokada {self.path}); usuń plik, jeśli to pozostałość")
        self.path.write_text(f"{os.getpid()} {dt.datetime.now():%Y-%m-%d %H:%M}\n", encoding="utf-8")
        return self

    def __exit__(self, *exc: Any) -> None:
        self.path.unlink(missing_ok=True)


class _Tee:
    """Wypisy run_task (print) trafiają na ekran i do pliku logu."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, s: str) -> int:
        for st in self.streams:
            st.write(s)
        return len(s)

    def flush(self) -> None:
        for st in self.streams:
            st.flush()


def run(settings: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None, dry_run: bool = False) -> Dict[str, Any]:
    """
    Przebieg lokalny: blokada -> setup_runtime(kod, dane) -> zadania -> last_run.json. Błąd zadania jest zapisany
    w gwl_runs (run_task) i w last_run.json, a potem zgłoszony dalej.
    """
    import step_05_colab_run as s5
    cfg = make_config(settings) if cfg is None else cfg
    regions = list(settings.get("regions") or cfg["regions"])
    steps = plan_tasks(cfg, regions, bool(settings["stage_b"]))
    if dry_run:
        return {"dry_run": True, "data_dir": settings["data_dir"], "regions": regions,
                "tasks": [n for n, _, _ in steps]}
    data_dir = Path(settings["data_dir"])
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Brak katalogu danych {data_dir} (Dysk Google zalogowany? ścieżka w {SETTINGS_FILE})")
    logs = data_dir / "data" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log_path = logs / f"run_{dt.datetime.now():%Y%m%d_%H%M%S}.log"
    summary: Dict[str, Any] = {"started": f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}", "log": str(log_path),
                               "data_dir": str(data_dir), "regions": regions, "stage_b": bool(settings["stage_b"])}
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    out_stream = open(log_path, "a", encoding="utf-8")
    old_stdout = sys.stdout
    sys.stdout = _Tee(old_stdout, out_stream)
    try:
        with Lock(str(data_dir)):
            rt = s5.setup_runtime(str(CODE_DIR), s5.STAGE_A_PACKAGES, str(data_dir))
            summary["git_commit"] = rt["GIT_COMMIT"]
            seen = set(s5.registry_read(rt, "gwl_runs")["run_id"])
            # Jak run_task: BaseException tylko zapisana w podsumowaniu i zawsze zgłoszona dalej.
            try:
                summary["tasks"] = run_all(rt, cfg, regions, bool(settings["stage_b"]), settings.get("confirm") or {})
                summary["status"] = "ok"
            except BaseException as e:
                summary["status"], summary["error"] = "error", f"{type(e).__name__}: {e}"
                raise
            finally:
                summary["finished"] = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}"
                runs = s5.registry_read(rt, "gwl_runs")
                mine = runs[~runs["run_id"].isin(seen)].sort_values("started_at")
                summary["task_status"] = dict(zip(mine["task"], mine["status"]))
                (logs / "last_run.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    finally:
        sys.stdout = old_stdout
        out_stream.close()
        root.removeHandler(handler)
        handler.close()
    return summary


def selftest_all(python: str = sys.executable) -> Dict[str, str]:
    """`python step_0N.py --selftest` dla każdego modułu z testem offline i test tego modułu. Zwraca {moduł: ok/błąd}."""
    res = {}
    for mod in SELFTEST_MODULES:
        if mod == "step_08_hyp3_mintpy" and not long_paths_enabled():
            res[mod] = "pominięty: Windows bez długich ścieżek (ścieżki produktów HyP3 > 260 znaków; require_long_paths)"
            print(f"[POMINIĘTY] {mod} --selftest: {res[mod]}")
            continue
        r = subprocess.run([python, str(CODE_DIR / f"{mod}.py"), "--selftest"], cwd=CODE_DIR, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env={**os.environ, "MPLBACKEND": "Agg"})
        res[mod] = "ok" if r.returncode == 0 else f"BŁĄD (kod {r.returncode}): {(r.stderr or r.stdout).strip()[-1500:]}"
        print(f"[{'OK' if r.returncode == 0 else 'BŁĄD'}] {mod} --selftest")
    _selftest()
    res["step_09_local"] = "ok"
    print("[OK] step_09_local selftest")
    return res


# ==============================================================================
# Test offline tego modułu
# ==============================================================================
def _selftest() -> None:
    from step_05_colab_run import CHECK_CONFIG
    import step_05_colab_run as s5
    with tempfile.TemporaryDirectory(prefix="egmscheck_local_") as tmpd:
        tmp = Path(tmpd)
        # 1. Ustawienia: plik (z BOM), zmienna środowiskowa, argumenty; brak katalogu danych = wyjątek.
        code = tmp / "kod"
        code.mkdir()
        try:
            load_settings(code)
            raise AssertionError("brak data_dir powinien zatrzymać")
        except ValueError as e:
            assert "data_dir" in str(e)
        (code / SETTINGS_FILE).write_text(json.dumps({"data_dir": str(tmp / "d1"), "secrets_dir": str(tmp / "sek"),
                                                      "confirm": {"CONFIRM_MB_GRONINGEN": 5}}), encoding="utf-8-sig")
        s = load_settings(code)
        assert s["data_dir"] == str((tmp / "d1").resolve()) and s["stage_b"] is False
        old = os.environ.get("EGMSCHECK_DATA_DIR")
        os.environ["EGMSCHECK_DATA_DIR"] = str(tmp / "d2")
        try:
            s = load_settings(code, stage_b=True, confirm={"CONFIRM_MB_NRW_WEST": 7})
        finally:
            if old is None:
                os.environ.pop("EGMSCHECK_DATA_DIR")
            else:
                os.environ["EGMSCHECK_DATA_DIR"] = old
        assert s["data_dir"] == str((tmp / "d2").resolve()) and s["stage_b"] is True
        assert s["confirm"] == {"CONFIRM_MB_GRONINGEN": 5, "CONFIRM_MB_NRW_WEST": 7}
        # 2. Potwierdzenia w postaci z komunikatów zadań.
        c = parse_confirm(["CONFIRM_MB_GRONINGEN=4321", "CONFIRM_JOBS['37'] = 54", 'CONFIRM_JOBS["88"]=12',
                           "CONFIRM_MB_NRW_WEST_LEVELLING=377"])
        assert c == {"CONFIRM_MB_GRONINGEN": 4321, "CONFIRM_JOBS": {"37": 54, "88": 12},
                     "CONFIRM_MB_NRW_WEST_LEVELLING": 377}, c
        for bad in ("GRONINGEN=4", "CONFIRM_MB_GRONINGEN=", "CONFIRM_MB_GRONINGEN=4.5"):
            try:
                parse_confirm([bad])
                raise AssertionError(bad)
            except ValueError:
                pass
        assert merge_confirm({"CONFIRM_JOBS": {"37": 1}}, {"CONFIRM_JOBS": {"88": 2}})["CONFIRM_JOBS"] == {"37": 1, "88": 2}
        # 3. Konfiguracja: tylko ścieżki tokenów; CHECK_CONFIG repozytorium bez zmian.
        cfg = make_config(s)
        assert cfg["project"]["token_path"] == str(tmp / "sek" / "clms_token.json")
        assert cfg["project"]["earthdata_path"] == str(tmp / "sek" / "earthdata.json")
        assert CHECK_CONFIG["project"]["token_path"].startswith("/content/drive"), "CHECK_CONFIG zmieniony"
        strip = ("project",)
        assert {k: v for k, v in cfg.items() if k not in strip} == {k: v for k, v in CHECK_CONFIG.items() if k not in strip}
        # 4. Plan zadań: kolejność z notatnika; każde zadanie task_* z notatnika EGMS_Monitoring jest w planie.
        names = [n for n, _, _ in plan_tasks(cfg, ["groningen", "nrw_west"], True)]
        assert names[:4] == ["egms_search_groningen", "egms_download_groningen", "select_gnss_groningen",
                             "gnss_download_groningen"], names
        assert names.index("compare_levelling_check_nrw_west") < names.index("monitoring_archive_groningen")
        assert names[-3:] == ["hyp3_plan_groningen", "TRACKS:groningen", "summary"] and "levelling_groningen" not in names
        nb = (CODE_DIR / "notebooks" / "EGMS_Monitoring.ipynb")
        if nb.exists():
            src = "".join("".join(c["source"]) for c in json.loads(nb.read_text(encoding="utf-8"))["cells"])
            used_nb = set(re.findall(r"run_task\(rt, [^,]+, (task_\w+)", src))
            used_here = {f for _, f, _ in plan_tasks(cfg, list(cfg["regions"]), True) if f} | \
                        {"task_hyp3_submit", "task_hyp3_download", "task_mintpy", "task_hyp3_compare"}
            assert used_nb == used_here, f"notatnik {sorted(used_nb - used_here)}, tutaj {sorted(used_here - used_nb)}"
        try:
            plan_tasks(cfg, ["berlin"], False)
            raise AssertionError("nieznany region")
        except KeyError as e:
            assert "berlin" in str(e)
        dry = run(dict(s, regions=["groningen"], stage_b=False), cfg, dry_run=True)
        assert dry["tasks"][-1] == "summary" and len(dry["tasks"]) == 12, dry
        # 5. Blokada i przebieg na pustym katalogu danych: pierwsze zadanie bez tokenu i bez wycinków = błąd zapisany.
        d = tmp / "dane"
        d.mkdir()
        with Lock(str(d)):
            try:
                with Lock(str(d)):
                    raise AssertionError("druga blokada")
            except RuntimeError as e:
                assert "Inny przebieg" in str(e)
        assert not (d / "data" / "registry" / LOCK_NAME).exists()
        sd = dict(s, data_dir=str(d), regions=["groningen"], stage_b=False, confirm={})
        cfg_t = make_config(sd)
        try:
            run(sd, cfg_t)
            raise AssertionError("przebieg bez danych i tokenu nie może przejść")
        except FileNotFoundError:
            pass
        last = json.loads((d / "data" / "logs" / "last_run.json").read_text(encoding="utf-8"))
        assert last["status"] == "error" and "FileNotFoundError" in last["error"], last
        assert last["task_status"] == {"egms_search_groningen": "error"}, last["task_status"]
        assert not (d / "data" / "registry" / LOCK_NAME).exists(), "blokada po błędzie"
        assert Path(last["log"]).read_text(encoding="utf-8").count("[ERROR] egms_search_groningen") == 1
        runs = s5.registry_read({"REGISTRY_DIR": str(d / "data" / "registry")}, "gwl_runs")
        assert list(runs["status"]) == ["error"] and not (CODE_DIR / "data" / "registry" / LOCK_NAME).exists()
        # 6. Etap B na Windows bez długich ścieżek: stop przed pierwszym zadaniem, z poleceniem dla administratora.
        if not long_paths_enabled():
            try:
                run(dict(sd, stage_b=True), cfg_t)
                raise AssertionError("etap B bez długich ścieżek nie może ruszyć")
            except RuntimeError as e:
                assert "LongPathsEnabled" in str(e), e
            last = json.loads((d / "data" / "logs" / "last_run.json").read_text(encoding="utf-8"))
            assert last["task_status"] == {} and "LongPathsEnabled" in last["error"], last
    print("SELFTEST step_09_local OK")


# ==============================================================================
# Wiersz poleceń
# ==============================================================================
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python step_09_local.py", description="EGMS Check - KROK 9: obliczenia lokalne")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "settings"):
        p = sub.add_parser(name)
        p.add_argument("--data-dir", default=None, help="katalog danych (z podkatalogiem data/)")
        p.add_argument("--secrets-dir", default=None, help="katalog z clms_token.json i earthdata.json")
        p.add_argument("--region", action="append", default=None, help="region z CHECK_CONFIG (można powtórzyć)")
        p.add_argument("--stage-b", action="store_true", default=None, help="także etap B (ASF HyP3 + MintPy)")
        p.add_argument("--confirm", action="append", default=[], help="np. CONFIRM_MB_GRONINGEN=4321")
        if name == "run":
            p.add_argument("--dry-run", action="store_true", help="tylko lista zadań")
    sub.add_parser("approvals")
    sub.add_parser("selftest")
    sub.add_parser("test", help="pełny test; opcje (--work, --keep, --skip-selftest, --no-stage-b) idą do "
                                "tests/local_harness/run_local_test.py")
    a, extra = ap.parse_known_args(argv)
    if extra and a.cmd != "test":
        ap.error(f"nieznane argumenty: {' '.join(extra)}")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for noisy in ("matplotlib", "PIL", "urllib3", "fiona", "rasterio", "h5py"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    sys.path.insert(0, str(CODE_DIR))

    if a.cmd == "approvals":
        from step_05_colab_run import CHECK_CONFIG, approvals_table
        print(approvals_table(CHECK_CONFIG).to_string(index=False))
        return 0
    if a.cmd == "selftest":
        res = selftest_all()
        bad = {k: v for k, v in res.items() if v != "ok" and not v.startswith("pominięty")}
        skipped = {k: v for k, v in res.items() if v.startswith("pominięty")}
        for k, v in {**bad, **skipped}.items():
            print(f"\n{k}: {v}")
        print(f"\nSELFTEST: {len(res) - len(bad) - len(skipped)}/{len(res)} modułów OK"
              + (f", pominięte {len(skipped)}" if skipped else ""))
        return 1 if bad else 0
    if a.cmd == "test":
        cmd = [sys.executable, str(CODE_DIR / "tests" / "local_harness" / "run_local_test.py"), *extra]
        return subprocess.run(cmd, cwd=CODE_DIR).returncode
    s = load_settings(data_dir=a.data_dir, secrets_dir=a.secrets_dir, regions=a.region, stage_b=a.stage_b,
                      confirm=parse_confirm(a.confirm))
    if a.cmd == "settings":
        print(json.dumps(dict(s, code_dir=str(CODE_DIR)), ensure_ascii=False, indent=1))
        return 0
    summ = run(s, dry_run=a.dry_run)
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
