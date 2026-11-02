"""
================================================================================
EGMS Check - PUBLIKACJA: WYBRANE WYNIKI DO docs/showcase/ (README, strona, blog)
================================================================================
Wzór: AgriScreen (agriscreen/local.py, publish). `run` liczy wyniki w katalogu danych (Dysk Google,
data/05_Final_Outputs/egmscheck/); do repozytorium trafia tylko ich mały, czytelny wybór (D-095):

  I.   Lista plików: werdykty EGMS kontra GNSS (L2b w kierunku satelity i L3 pion) dla każdego regionu; dla regionu
       z niwelacją porównanie EGMS L3 z niwelacją na drugim wydaniu (wariant główny i względny, podział na niecki,
       przesunięcie grupy stabilnej, pasy niepewności) i porównanie na wydaniu głównym; ryciny rozrzutu i mapy L3.
       Brak pliku wymaganego = wyjątek z pełną listą braków (CLAUDE.md, zasada 3). Pliki opcjonalne (rycina
       rozrzutu GNSS powstaje tylko wtedy, gdy są pary stacja x ścieżka; mapy; run_summary) są kopiowane, gdy
       istnieją, a ich brak jest zapisany w egmscheck_results.json i wypisany na ekranie.
  II.  egmscheck_results.json: te same tabele kryteriów w jednym pliku (kod K1…K4 / N1…N4, wynik, próg, spełnione, n),
       werdykt słowny, wydanie EGMS, podział na grupy, przesunięcie i pasy niepewności; skąd jest każdy wynik
       (zadanie, czas, commit kodu z rejestru gwl_runs, a dla commitów sprzed 2026-11-02 także odpowiednik w obecnej
       historii z docs/evidence/historia_git_mapa.csv). Liczby tylko z plików wynikowych, nic nie jest wpisywane ręcznie.
       Lista "files" w JSON to spis zarządzanych plików docs/showcase/: plik z poprzedniej publikacji, którego teraz
       nie ma w wynikach, jest usuwany (żeby stary wynik nie udawał nowego).
  III. git: commit wyłącznie zmian w docs/showcase/ i push na bieżącą gałąź main. Bez okien logowania
       (GIT_TERMINAL_PROMPT=0, GCM_INTERACTIVE=never); na Windows systemowy Git for Windows, nie git ze środowiska
       conda (ten otwiera okno wyboru menedżera logowania; AgriScreen 1.3.1). --no-git: tylko kopiowanie.
  IV.  _selftest: syntetyczny katalog danych, kopiowanie, JSON, usunięcie nieaktualnego pliku, brak pliku wymaganego
       = wyjątek; bez sieci i bez git.

EGMS wychodzi raz w roku, więc publikacja jest na żądanie (po nowym przebiegu), bez zadania w Harmonogramie.
================================================================================
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("EGMSCheck_Publish")

CODE_DIR = Path(__file__).resolve().parents[1]
SHOWCASE = Path("docs") / "showcase"
RESULTS_JSON = "egmscheck_results.json"
HISTORY_MAP = Path("docs") / "evidence" / "historia_git_mapa.csv"
NOTICE = ("Generated using European Union's Copernicus Land Monitoring Service information (European Ground Motion "
          "Service; modified: extracts, comparisons, figures). GNSS: Nevada Geodetic Laboratory (Blewitt et al. 2018, "
          "doi:10.1029/2018EO104623). Levelling: Geobasis NRW, Datenlizenz Deutschland - Zero - Version 2.0.")


# ==============================================================================
# I. Lista plików
# ==============================================================================
def showcase_items(rt: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Pliki do publikacji: [{'src': Path, 'name': nazwa w docs/showcase, 'required': bool, 'task': zadanie}].
    Nazwa pliku w docs/showcase = nazwa w katalogu wyników (łatwo znaleźć źródło).
    """
    import step_05_colab_run as s5
    items: List[Dict[str, Any]] = []

    def add(src: Path, required: bool, task: str) -> None:
        items.append({"src": Path(src), "name": Path(src).name, "required": required, "task": task})

    for region, rcfg in cfg["regions"].items():
        P = s5.region_paths(rt, cfg, region)
        for key in ("verdict_l2b", "verdict_l3u"):
            add(P[key], True, f"compare_gnss_{region}")
            add(P[key].with_suffix(".txt"), True, f"compare_gnss_{region}")
        add(P["figures"] / f"{region}_velocity_scatter.png", False, f"figures_{region}")
        add(P["figures"] / f"{region}_l3_velocity_map.png", False, f"figures_{region}")
        if rcfg.get("levelling") is None:
            continue
        add(P["levelling_summary"], True, f"compare_levelling_{region}")
        if rcfg["levelling"].get("egms_check") is None:
            continue
        C = s5.levelling_check_paths(rt, cfg, region)
        task = f"compare_levelling_check_{region}"
        for key in ("summary", "groups", "summary_rel", "groups_rel", "offset_rel", "uncertainty", "figure",
                    "figure_rel"):
            add(C[key], True, task)
        add(C["map"], False, task)
    out = s5._abs(rt, cfg["project"]["outputs_dir"])
    for name in ("run_summary.md", "run_summary.json"):
        add(out / name, False, "summary")
    names = [i["name"] for i in items]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        raise ValueError(f"Dwa pliki o tej samej nazwie w docs/showcase: {dup}")
    return items


# ==============================================================================
# II. egmscheck_results.json
# ==============================================================================
def _bool(value: str) -> Optional[bool]:
    v = str(value).strip()
    if v == "True":
        return True
    if v == "False":
        return False
    if v in ("", "nan", "None"):
        return None
    raise ValueError(f"Kolumna 'spełnione': nieoczekiwana wartość {value!r} (True / False / puste)")


def _int_or_none(value: str) -> Optional[int]:
    v = str(value).strip()
    return int(float(v)) if v not in ("", "nan") else None


def read_criteria(path: Path) -> List[Dict[str, Any]]:
    """Tabela kryteriów (kryterium, wynik, próg, spełnione, n / n_par) -> lista wierszy z kodem K1…/N1… albo None."""
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    need = {"kryterium", "wynik", "próg", "spełnione"}
    if not rows or not need <= set(rows[0]):
        raise ValueError(f"{path.name}: brak wierszy albo kolumn {sorted(need)}")
    n_col = "n" if "n" in rows[0] else "n_par"
    out = []
    for r in rows:
        head = r["kryterium"].split(" ", 1)[0]
        code = head if len(head) == 2 and head[0] in "KN" and head[1].isdigit() else None
        out.append({"code": code, "criterion": r["kryterium"], "result": r["wynik"], "threshold": r["próg"],
                    "passed": _bool(r["spełnione"]), "n": _int_or_none(r.get(n_col, ""))})
    return out


def read_table(path: Path) -> List[Dict[str, Any]]:
    """Mała tabela CSV (np. podział na grupy) -> lista słowników; liczby jako float, tekst bez zmian."""
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"{path.name}: pusta tabela")

    def conv(v: str) -> Any:
        try:
            return float(v)
        except ValueError:
            return v
    return [{k: conv(v) for k, v in r.items()} for r in rows]


def _history_map(code_dir: Path) -> Dict[str, str]:
    """Skrót starego commita -> skrót commita w obecnej historii (przepisanej 2026-11-02, D-094); ostatnia kolumna."""
    path = code_dir / HISTORY_MAP
    if not path.exists():
        return {}
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    hexcols = [i for i, v in enumerate(rows[1]) if len(v) == 40 and all(c in "0123456789abcdef" for c in v)]
    first, last = hexcols[0], hexcols[-1]
    return {r[first][:7]: r[last][:7] for r in rows[1:] if len(r) > last}


def run_provenance(rt: Dict[str, Any], tasks: List[str], code_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Ostatnie udane uruchomienie każdego zadania z gwl_runs: czas, commit kodu (i jego odpowiednik po D-094)."""
    import step_05_colab_run as s5
    runs = s5.registry_read(rt, "gwl_runs")
    ok = runs[runs["status"] == "ok"].sort_values("finished_at")
    hmap = _history_map(code_dir)
    out: Dict[str, Dict[str, Any]] = {}
    for task in tasks:
        t = ok[ok["task"] == task]
        if t.empty:
            out[task] = {"status": "brak udanego uruchomienia w gwl_runs"}
            continue
        last = t.iloc[-1]
        commit = str(last["git_commit"])
        base, plus, rest = commit.partition("+")
        entry = {"finished_at": str(last["finished_at"]), "git_commit": commit}
        if base[:7] in hmap:
            entry["git_commit_current_history"] = hmap[base[:7]] + (plus + rest if plus else "")
        out[task] = entry
    return out


def build_results(rt: Dict[str, Any], cfg: Dict[str, Any], items: List[Dict[str, Any]],
                  code_dir: Path) -> Dict[str, Any]:
    """Zawartość egmscheck_results.json: wyniki z plików wynikowych, skąd pochodzą i spis plików."""
    import step_05_colab_run as s5
    from egmscheck import __version__
    release = cfg["egms"]["release"]
    results: List[Dict[str, Any]] = []
    for region, rcfg in cfg["regions"].items():
        P = s5.region_paths(rt, cfg, region)
        for key, product in (("verdict_l2b", "EGMS L2b Calibrated (line of sight) vs GNSS"),
                             ("verdict_l3u", "EGMS L3 Ortho (vertical) vs GNSS (up)")):
            results.append({"id": f"{region}_{key}", "region": region, "comparison": product, "release": release,
                            "verdict": P[key].with_suffix(".txt").read_text(encoding="utf-8").strip(),
                            "criteria": read_criteria(P[key]), "file": P[key].name,
                            "task": f"compare_gnss_{region}"})
        if rcfg.get("levelling") is None:
            continue
        results.append({"id": f"{region}_levelling_{release.replace('-', '_')}", "region": region,
                        "comparison": "EGMS L3 Ortho (vertical) vs levelling", "release": release,
                        "criteria": read_criteria(P["levelling_summary"]), "file": P["levelling_summary"].name,
                        "task": f"compare_levelling_{region}"})
        if rcfg["levelling"].get("egms_check") is None:
            continue
        C = s5.levelling_check_paths(rt, cfg, region)
        rel2 = str(rcfg["levelling"]["egms_check"]["release"])
        tag = rel2.replace("-", "_")
        task = f"compare_levelling_check_{region}"
        results.append({"id": f"{region}_levelling_{tag}", "region": region, "release": rel2,
                        "comparison": "EGMS L3 Ortho (vertical) vs levelling, main variant (absolute)",
                        "criteria": read_criteria(C["summary"]), "groups": read_table(C["groups"]),
                        "file": C["summary"].name, "task": task})
        results.append({"id": f"{region}_levelling_{tag}_relative", "region": region, "release": rel2,
                        "comparison": "EGMS L3 Ortho (vertical) vs levelling, additional variant relative to "
                                      "levelling-stable benchmarks (computed after the main variant)",
                        "criteria": read_criteria(C["summary_rel"]), "groups": read_table(C["groups_rel"]),
                        "offset": json.loads(C["offset_rel"].read_text(encoding="utf-8")),
                        "file": C["summary_rel"].name, "task": task})
        results.append({"id": f"{region}_levelling_{tag}_uncertainty", "region": region, "release": rel2,
                        "comparison": "share of benchmarks inside the EGMS uncertainty bands (informative, no threshold)",
                        "uncertainty": json.loads(C["uncertainty"].read_text(encoding="utf-8")),
                        "file": C["uncertainty"].name, "task": task})
    tasks = sorted({r["task"] for r in results})
    present = [i for i in items if i["src"].exists()]
    return {
        "project": "EGMS Check",
        "version": __version__,
        "published": f"{dt.date.today():%Y-%m-%d}",
        "language_note": "criterion and verdict texts are copied from the result files (Polish); codes K1-K4 and "
                         "N1-N4 are explained in README.md and docs/evidence/karta_wynikow.md",
        "notice": NOTICE,
        "results": results,
        "runs": run_provenance(rt, tasks + ["figures_" + r for r in cfg["regions"]], code_dir),
        "files": sorted(i["name"] for i in present),
        "missing_optional": sorted(i["name"] for i in items if not i["required"] and not i["src"].exists()),
    }


# ==============================================================================
# III. Kopiowanie i git
# ==============================================================================
def copy_showcase(items: List[Dict[str, Any]], dest: Path) -> Tuple[List[str], List[str]]:
    """
    Kopiuje pliki do dest; brak pliku wymaganego = FileNotFoundError z listą wszystkich braków. Usuwa pliki
    z poprzedniej publikacji (spis 'files' w starym JSON), których teraz nie ma. Zwraca (skopiowane, usunięte).
    """
    missing = [str(i["src"]) for i in items if i["required"] and not i["src"].exists()]
    if missing:
        raise FileNotFoundError("Brak wyników do publikacji (najpierw `python -m egmscheck run`):\n  "
                                + "\n  ".join(missing))
    dest.mkdir(parents=True, exist_ok=True)
    old_json = dest / RESULTS_JSON
    old = json.loads(old_json.read_text(encoding="utf-8")).get("files", []) if old_json.exists() else []
    copied = []
    for i in items:
        if i["src"].exists():
            shutil.copyfile(i["src"], dest / i["name"])
            copied.append(i["name"])
    removed = []
    for name in sorted(set(old) - set(copied)):
        if (dest / name).exists():
            (dest / name).unlink()
            removed.append(name)
    return copied, removed


def git_exe() -> str:
    """Systemowy Git (Windows: Git for Windows w Program Files), inaczej git z PATH."""
    if os.name == "nt":
        for base in (os.environ.get("ProgramW6432"), os.environ.get("ProgramFiles")):
            if base and (Path(base) / "Git" / "cmd" / "git.exe").exists():
                return str(Path(base) / "Git" / "cmd" / "git.exe")
    exe = shutil.which("git")
    if exe is None:
        raise FileNotFoundError("Brak programu git (Windows: zainstaluj Git for Windows)")
    return exe


def git(code_dir: Path, *args: str) -> str:
    """Polecenie git bez okien i pytań o logowanie; błąd = RuntimeError z komunikatem gita."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}
    r = subprocess.run([git_exe(), "-C", str(code_dir), *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {(r.stderr or r.stdout).strip()}")
    return r.stdout.strip()


def git_publish(code_dir: Path, message: str, branch: str = "main") -> str:
    """Commit wyłącznie zmian w docs/showcase/ (także usunięć) i push na `branch`. Zwraca opis wyniku."""
    if git(code_dir, "rev-parse", "--abbrev-ref", "HEAD") != branch:
        raise RuntimeError(f"Publikacja tylko z gałęzi {branch}; bieżąca: {git(code_dir, 'rev-parse', '--abbrev-ref', 'HEAD')}")
    path = SHOWCASE.as_posix()
    git(code_dir, "add", "-A", "--", path)
    if subprocess.run([git_exe(), "-C", str(code_dir), "diff", "--cached", "--quiet", "--", path]).returncode == 0:
        return "bez zmian do publikacji"
    git(code_dir, "commit", "-m", message, "--", path)
    commit = git(code_dir, "rev-parse", "--short", "HEAD")
    git(code_dir, "push", "origin", f"HEAD:{branch}")
    return f"opublikowano {commit} na origin/{branch}"


def publish(settings: Dict[str, Any], cfg: Dict[str, Any], do_git: bool = True, message: Optional[str] = None,
            code_dir: Path = CODE_DIR) -> Dict[str, Any]:
    """Wyniki z katalogu danych -> docs/showcase/ + egmscheck_results.json; opcjonalnie commit i push."""
    data_dir = Path(settings["data_dir"])
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Brak katalogu danych {data_dir} (Dysk Google zalogowany?)")
    rt = {"PROJECT_DIR": str(code_dir), "DATA_ROOT": str(data_dir),
          "REGISTRY_DIR": str(data_dir / "data" / "registry")}
    items = showcase_items(rt, cfg)
    dest = code_dir / SHOWCASE
    copied, removed = copy_showcase(items, dest)
    results = build_results(rt, cfg, items, code_dir)
    (dest / RESULTS_JSON).write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for name in results["missing_optional"]:
        print(f"[BRAK, opcjonalny] {name}")
    summary = {"showcase": str(dest), "copied": copied, "removed": removed,
               "missing_optional": results["missing_optional"]}
    if do_git:
        msg = message or f"auto: EGMS Check results published {dt.date.today():%Y-%m-%d}"
        summary["git"] = git_publish(code_dir, msg)
    else:
        summary["git"] = "pominięte (--no-git)"
    return summary


# ==============================================================================
# IV. Test bez sieci
# ==============================================================================
def _selftest() -> None:
    import step_05_colab_run as s5
    import pandas as pd
    cfg = s5.CHECK_CONFIG
    with tempfile.TemporaryDirectory(prefix="egmscheck_publish_") as tmpd:
        tmp = Path(tmpd)
        data, code = tmp / "dane", tmp / "kod"
        (code / "docs" / "evidence").mkdir(parents=True)
        (code / HISTORY_MAP).write_text("old,mid,new,date,message\n" + "a" * 40 + "," + "b" * 40 + "," + "c" * 40
                                        + ",2026-10-15,x\n", encoding="utf-8")
        rt = {"PROJECT_DIR": str(code), "DATA_ROOT": str(data), "REGISTRY_DIR": str(data / "data" / "registry")}
        items = showcase_items(rt, cfg)
        assert {i["name"] for i in items if i["required"]} >= {"verdict_gnss_l2b_groningen.csv",
                                                                 "levelling_summary_nrw_west_2019_2023.csv"}
        crit = ("kryterium,wynik,próg,spełnione,n_par\nK1 zgodność tempa osiadania,99% par,>= 80%,True,93\n"
                "Bias i rozrzut dv (informacyjnie),\"mediana -0.00, MAD 0.81\",-,,93\n"
                "K3 kontrola negatywna,max |dv| 1.62 mm/rok,<= 1.5 mm/rok,False,32\n")
        lev = "kryterium,wynik,próg,spełnione,n\nN1 mediana,6.0 mm,<= 5.0 mm,False,1216\n"
        groups = "grupa,n,bias_v_mm_yr\nwszystkie,1216,-1.97\n"
        for i in items:
            if not i["required"] and i["name"].startswith("run_summary"):
                continue                              # brak opcjonalnego pliku: ma trafić do missing_optional
            i["src"].parent.mkdir(parents=True, exist_ok=True)
            n = i["name"]
            body = (crit if n.startswith("verdict") and n.endswith(".csv") else
                    "CZĘŚCIOWO: tempo zgodne." if n.endswith(".txt") else
                    lev if n.startswith("levelling_summary") else
                    groups if n.startswith("levelling_groups") else
                    json.dumps({"offset_egms_minus_lev_mm_yr": -1.2}) if n.endswith(".json") else "PNG")
            i["src"].write_text(body, encoding="utf-8")
        s5.registry_upsert(rt, "gwl_runs", pd.DataFrame([{
            "run_id": "r1", "task": "compare_gnss_groningen", "started_at": "2026-10-15T12:50:00Z",
            "finished_at": "2026-10-15T12:51:52Z", "duration_s": 1.0, "status": "ok", "git_commit": "aaaaaaa+dirty",
            "message": "ok"}]))
        dest = code / SHOWCASE
        dest.mkdir(parents=True)
        (dest / "stary_wynik.png").write_text("x", encoding="utf-8")
        (dest / RESULTS_JSON).write_text(json.dumps({"files": ["stary_wynik.png"]}), encoding="utf-8")
        (dest / "README.md").write_text("opis", encoding="utf-8")
        res = publish({"data_dir": str(data)}, cfg, do_git=False, code_dir=code)
        assert res["removed"] == ["stary_wynik.png"] and (dest / "README.md").exists(), res
        assert set(res["missing_optional"]) == {"run_summary.md", "run_summary.json"}, res
        js = json.loads((dest / RESULTS_JSON).read_text(encoding="utf-8"))
        assert js["files"] == sorted(res["copied"]) and "stary_wynik.png" not in js["files"]
        g = next(r for r in js["results"] if r["id"] == "groningen_verdict_l2b")
        assert [c["code"] for c in g["criteria"]] == ["K1", None, "K3"], g["criteria"]
        assert [c["passed"] for c in g["criteria"]] == [True, None, False] and g["criteria"][0]["n"] == 93
        assert g["verdict"].startswith("CZĘŚCIOWO") and g["release"] == cfg["egms"]["release"]
        r = js["runs"]["compare_gnss_groningen"]
        assert r["git_commit"] == "aaaaaaa+dirty" and r["git_commit_current_history"] == "ccccccc+dirty", r
        assert "status" in js["runs"]["figures_groningen"]
        lv = next(r for r in js["results"] if r["id"] == "nrw_west_levelling_2019_2023_relative")
        assert lv["offset"]["offset_egms_minus_lev_mm_yr"] == -1.2 and lv["groups"][0]["n"] == 1216.0
        # Brak pliku wymaganego: wyjątek z nazwą, nic nie jest kopiowane po cichu.
        (data / "data" / "05_Final_Outputs" / "egmscheck" / "groningen" / "verdict_gnss_l3u_groningen.csv").unlink()
        try:
            publish({"data_dir": str(data)}, cfg, do_git=False, code_dir=code)
            raise AssertionError("brak wymaganego pliku musi zatrzymać publikację")
        except FileNotFoundError as e:
            assert "verdict_gnss_l3u_groningen.csv" in str(e)
        try:
            read_criteria(dest / "levelling_groups_nrw_west_2019_2023.csv")
            raise AssertionError("tabela bez kolumn kryteriów")
        except ValueError:
            pass
    print("SELFTEST egmscheck.publish OK")
