# TEST LOKALNY: pełny test obliczeń na własnym komputerze (step_09_local.py), Windows / macOS / Linux, bez Colab.
# Atrapy serwerów i dane o znanej odpowiedzi z tests/monitoring_harness (te same co w teście notatnika), bez sieci.
#   0. selftesty wszystkich modułów (step_09_local.selftest_all);
#   1. dane testowe (make_fixtures.py), atrapa klucza CLMS i danych Earthdata w <work>/secrets, pusty katalog danych
#      <work>/data (kod i dane osobno, jak kod w projects/egms-check i dane na Dysku Google);
#   2. PRZEBIEG 1 (full): etap A + B od zera, kontrola znanej odpowiedzi (Windows bez długich ścieżek: bez etapu B,
#      z wyraźnym komunikatem; step_09_local.require_long_paths);
#   3. PRZEBIEG 2 (rerun): nic nie jest pobierane, liczone od nowa ani zlecane drugi raz;
#   4. PRZEBIEG 3 (author): konfiguracja autora; z etapem B stop na potwierdzeniu zleceń HyP3, bez niego etap A przechodzi;
#   5. katalog kodu bez zmian (git status jak przed testem).
# Użycie (środowisko egmscheck):  python tests/local_harness/run_local_test.py [--work DIR] [--keep] [--skip-selftest] [--no-stage-b]
# Notatniki pokazowe (Showcase_*.ipynb) i Colab sprawdza tylko tests/monitoring_harness/run_harness.sh (Linux).
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CODE = Path(__file__).resolve().parents[2]
H = CODE / "tests" / "monitoring_harness"
MARKER = ".egmscheck_local_test"


def step(title: str) -> None:
    print(f"\n=== {title} ===", flush=True)


def git_status() -> str:
    r = subprocess.run(["git", "-C", str(CODE), "status", "--porcelain", "--untracked-files=all"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else f"git niedostępny: {r.stderr}"


def prepare_work(work: Path) -> None:
    """Katalog roboczy: nowy albo wcześniejszy katalog tego testu (z plikiem-znacznikiem); inny niepusty = błąd."""
    if work.exists() and any(work.iterdir()):
        if not (work / MARKER).exists():
            raise RuntimeError(f"{work} nie jest pusty i nie jest katalogiem tego testu (brak {MARKER}): wybierz inny")
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    (work / MARKER).write_text("katalog roboczy tests/local_harness/run_local_test.py\n", encoding="utf-8")


def fake_mintpy(work: Path) -> Path:
    """Atrapa smallbaselineApp.py na PATH (Windows: plik .cmd; inne systemy: skrypt wykonywalny)."""
    b = work / "bin"
    b.mkdir()
    src = H / "bin" / "smallbaselineApp.py"
    if os.name == "nt":
        (b / "smallbaselineApp.py.cmd").write_text(f'@"{sys.executable}" "{src}" %*\r\n', encoding="utf-8")
    else:
        dst = b / "smallbaselineApp.py"
        dst.write_text(f"#!{sys.executable}\n" + src.read_text(encoding="utf-8"), encoding="utf-8")
        dst.chmod(0o755)
    return b


def run_driver(mode: str, work: Path, env: dict, stage_b: bool) -> str:
    log = work / f"pass_{mode}.log"
    t0 = time.time()
    with open(log, "w", encoding="utf-8") as f:
        r = subprocess.run([sys.executable, str(CODE / "tests" / "local_harness" / "driver.py"), mode, str(work),
                            "1" if stage_b else "0"],
                           cwd=CODE, env=env, stdout=f, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    text = log.read_text(encoding="utf-8", errors="replace")
    print("\n".join(line for line in text.splitlines() if re.match(r"^\[(OK|SKIPPED|ERROR)\]|^DRIVER|^HARNESS", line)))
    if r.returncode != 0:
        print(text[-4000:])
        raise RuntimeError(f"PRZEBIEG {mode}: kod {r.returncode}, pełny log {log}")
    print(f"({mode}: {time.time() - t0:.0f} s, log {log})")
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description="EGMS Check: pełny test obliczeń lokalnych na atrapach")
    ap.add_argument("--work", default=None, help="katalog roboczy (usuwany przy następnym teście)")
    ap.add_argument("--keep", action="store_true", help="zostaw katalog roboczy (wyniki, logi)")
    ap.add_argument("--skip-selftest", action="store_true")
    ap.add_argument("--no-stage-b", action="store_true", help="bez etapu B (ASF HyP3 + MintPy)")
    a = ap.parse_args()
    t0 = time.time()
    work = Path(a.work).resolve() if a.work else Path(tempfile.mkdtemp(prefix="egmscheck_local_test_"))
    prepare_work(work)
    print(f"Katalog roboczy: {work} (po błędzie zostaje do obejrzenia)")
    before = git_status()
    sys.path.insert(0, str(CODE))
    import step_09_local as s9
    stage_b = not a.no_stage_b and s9.long_paths_enabled()
    if not stage_b and not a.no_stage_b:
        print("UWAGA: Windows bez długich ścieżek (LongPathsEnabled = 0): test BEZ etapu B (HyP3 + MintPy).\n"
              "       Włączenie: step_09_local.require_long_paths (komunikat z poleceniem dla administratora).")

    if not a.skip_selftest:
        step("0. Selftesty modułów")
        res = s9.selftest_all()
        bad = {k: v for k, v in res.items() if v != "ok" and not v.startswith("pominięty")}
        if bad:
            raise RuntimeError(f"Selftesty z błędem: {bad}")

    step("1. Dane testowe, atrapy kluczy, katalog danych")
    subprocess.run([sys.executable, str(H / "make_fixtures.py"), str(work / "fx")], cwd=CODE, check=True)
    subprocess.run([sys.executable, str(CODE / "tests" / "colab_harness" / "make_test_key.py"),
                    str(work / "secrets" / "clms_token.json"), str(work / "pub.pem")], cwd=CODE, check=True)
    (work / "secrets" / "earthdata.json").write_text('{"username": "TEST", "password": "TEST"}\n', encoding="utf-8")
    (work / "data").mkdir()
    env = {**os.environ, "PYTHONPATH": str(H / "fake"), "NBTEST_FX": str(work / "fx"),
           "NBTEST_PUBKEY": str(work / "pub.pem"), "MPLBACKEND": "Agg", "PYTHONIOENCODING": "utf-8",
           "PATH": str(fake_mintpy(work)) + os.pathsep + os.environ.get("PATH", "")}
    for var in ("EGMSCHECK_DATA_DIR", "EGMSCHECK_SECRETS_DIR"):
        env.pop(var, None)                    # test nie może trafić w prawdziwy katalog danych

    step(f"2. PRZEBIEG 1: pełny przebieg od zera (etap A{' + B' if stage_b else ', BEZ etapu B'}) "
         f"i kontrola znanej odpowiedzi")
    out = run_driver("full", work, env, stage_b)
    assert "HARNESS: znana odpowiedź OK" in out

    step("3. PRZEBIEG 2: ponownie na tych samych danych (nic nie pobiera, nie liczy wycinków, nie zleca drugi raz)")
    out = run_driver("rerun", work, env, stage_b)
    for needle in ("[SKIPPED] egms_download_groningen", "[SKIPPED] extract_groningen", "[SKIPPED] extract_nrw_west",
                   "MIDAS: migawka z Dysku"):
        assert needle in out, f"PRZEBIEG 2: brak '{needle}'"
    if stage_b:
        sub = re.findall(r"wysłane (\d+), istniejące (\d+)", out)
        assert sub and all(s == "0" and int(e) > 0 for s, e in sub), f"PRZEBIEG 2: zlecenia HyP3 wysłane ponownie? {sub}"

    step("4. PRZEBIEG 3: konfiguracja autora bez potwierdzeń"
         + (" (stop na zleceniach HyP3)" if stage_b else " (etap A przechodzi)"))
    run_driver("author", work, env, stage_b)

    step("5. Katalog kodu bez zmian")
    after = git_status()
    assert after == before, f"Test zmienił katalog kodu:\nprzed:\n{before}\npo:\n{after}"
    # data/registry i data/logs są w .gitignore, więc git status ich nie pokaże: sprawdzenie wprost.
    leaked = [p for p in ("data/registry/gwl_runs.csv", "data/logs", "data/03_Extracts/groningen",
                          "data/05_Final_Outputs/egmscheck") if (CODE / p).exists()]
    assert not leaked, f"Wyniki testu w katalogu kodu: {leaked}"

    print(f"\nTEST LOKALNY: wszystkie przebiegi zgodne z oczekiwaniem ({time.time() - t0:.0f} s)"
          + ("" if stage_b else " - BEZ ETAPU B (HyP3 + MintPy nie sprawdzone)"))
    if a.keep:
        print(f"Katalog roboczy zostaje: {work}")
    else:
        shutil.rmtree(work)
    return 0


if __name__ == "__main__":
    sys.exit(main())
