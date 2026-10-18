#!/usr/bin/env bash
# TEST: pełny przebieg notebooks/EGMS_Monitoring.ipynb na atrapach (bez sieci do EGMS, NGL, NRW, ASF, Earthdata).
# Użycie: tests/monitoring_harness/run_harness.sh <python środowiska colab313> <katalog roboczy (usuwany)>
# Uwaga: usuwa i tworzy od nowa /content/drive/MyDrive/GeoWorldLook/egmscheck (atrapa Dysku, jak tests/colab_harness).
set -euo pipefail
PY="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; WORK=$2   # bez readlink: symlink pythona venv musi zostać
VENV=$(cd "$(dirname "$PY")/.." && pwd)
REPO=$(cd "$(dirname "$0")/../.." && pwd); H=$REPO/tests/monitoring_harness
BRANCH=main
URL=https://github.com/geoworldlook/egms-check.git
rm -rf "$WORK"; mkdir -p "$WORK"
chmod +x "$H/bin/smallbaselineApp.py"

# 1. Dane testowe, atrapa klucza CLMS i danych logowania Earthdata (fałszywe, nie dają dostępu do żadnej usługi).
"$PY" "$H/make_fixtures.py" "$WORK/fx"
SECRETS=/content/drive/MyDrive/GeoWorldLook/secrets
"$PY" "$REPO/tests/colab_harness/make_test_key.py" "$SECRETS/clms_token.json" "$WORK/pub.pem"
printf '{"username": "TEST", "password": "TEST"}\n' > "$SECRETS/earthdata.json"

# 2. Migawka bieżącego drzewa roboczego jako lokalne repozytorium na gałęzi notatnika; git w jądrze pobiera z niej
#    zamiast z GitHuba (url.insteadOf w osobnym GIT_CONFIG_GLOBAL). Repozytorium projektu nie jest zmieniane.
git clone -q --no-hardlinks "$REPO" "$WORK/snapshot"
(cd "$REPO" && git ls-files -co --exclude-standard -z | xargs -0 -I{} cp --parents {} "$WORK/snapshot/")
git -C "$WORK/snapshot" checkout -q -B "$BRANCH"
git -C "$WORK/snapshot" add -A
git -C "$WORK/snapshot" -c user.name=harness -c user.email=harness@invalid commit -q -m "harness snapshot" || true
printf '[url "%s"]\n\tinsteadOf = %s\n' "$WORK/snapshot" "$URL" > "$WORK/gitconfig"
rm -rf /content/drive/MyDrive/GeoWorldLook/egmscheck

# 3. Kopia testowa notatnika (zatwierdzenia "TEST", CONFIRM_*, kontrola znanej odpowiedzi) i trzy przebiegi.
"$PY" "$H/prepare_notebook.py" "$REPO/notebooks/EGMS_Monitoring.ipynb" "$WORK/test.ipynb" "$WORK/fx"
run_nb() {
  PATH="$VENV/bin:$H/bin:$PATH" PYTHONPATH="$H/fake" NBTEST_FX="$WORK/fx" NBTEST_PUBKEY="$WORK/pub.pem" \
    JUPYTER_PATH="$VENV/share/jupyter" MPLBACKEND=Agg GIT_CONFIG_GLOBAL="$WORK/gitconfig" \
    "$PY" "$H/run_nb.py" "$1" "$2" "$WORK"
}
echo "=== PRZEBIEG 1: pełny notatnik od zera ==="
run_nb "$WORK/test.ipynb" "$WORK/out1.ipynb" | tee "$WORK/pass1.log"
echo "=== PRZEBIEG 2: ponowne uruchomienie na tym samym Dysku (nic nie pobiera ani nie zleca drugi raz) ==="
run_nb "$WORK/test.ipynb" "$WORK/out2.ipynb" | tee "$WORK/pass2.log"
grep -q "\[SKIPPED\] egms_download_groningen" "$WORK/out2.ipynb.txt"
grep -q "\[SKIPPED\] extract_groningen" "$WORK/out2.ipynb.txt"
grep -q "\[SKIPPED\] extract_nrw_west" "$WORK/out2.ipynb.txt" || { echo "PRZEBIEG 2: sites.csv zapisany ponownie (GNSS + repery) i wycinki NRW liczone od nowa?"; exit 1; }
grep -q "MIDAS: migawka z Dysku" "$WORK/out2.ipynb.txt" || { echo "PRZEBIEG 2: MIDAS bez migawki z Dysku?"; exit 1; }
grep -q "wysłane 0, istniejące 93" "$WORK/out2.ipynb.txt" || { echo "PRZEBIEG 2: zlecenia HyP3 wysłane ponownie?"; exit 1; }
echo "=== PRZEBIEG 3: notatnik z repozytorium (konfiguracja autora): EGMS już na Dysku (przebiegi 1-2), etap A przechodzi, oczekiwany stop na potwierdzeniu zleceń HyP3 (CONFIRM_JOBS) ==="
if run_nb "$REPO/notebooks/EGMS_Monitoring.ipynb" "$WORK/out3.ipynb" > "$WORK/pass3.log"; then
  echo "PRZEBIEG 3: notatnik bez zatwierdzeń nie może przejść"; exit 1
fi
grep -q "Zlecenia HyP3 wstrzymane: po obejrzeniu planu ustaw CONFIRM_JOBS\['37'\]" "$WORK/out3.ipynb.txt"
tail -3 "$WORK/pass3.log"
echo "=== PRZEBIEG 4: notatniki pokazowe (notebooks/Pokaz_*.ipynb) na wynikach z przebiegów 1-3: tylko odczyt ==="
run_nb "$REPO/notebooks/Pokaz_1_GNSS_Groningen.ipynb" "$WORK/out4a.ipynb" > "$WORK/pass4a.log" || { tail -20 "$WORK/pass4a.log"; exit 1; }
grep -q "Wniosek według reguły ustalonej z góry" "$WORK/out4a.ipynb.txt" || { echo "PRZEBIEG 4: brak werdyktu GNSS"; exit 1; }
grep -q "stacji GNSS" "$WORK/out4a.ipynb.txt" || { echo "PRZEBIEG 4: brak liczby stacji GNSS"; exit 1; }
run_nb "$REPO/notebooks/Pokaz_2_Niwelacja_NRW.ipynb" "$WORK/out4b.ipynb" > "$WORK/pass4b.log" || { tail -20 "$WORK/pass4b.log"; exit 1; }
grep -q "Przesunięcie EGMS względem niwelacji na" "$WORK/out4b.ipynb.txt" || { echo "PRZEBIEG 4: brak wyniku wariantu względnego"; exit 1; }
grep -q "Najszybciej osiadający reper" "$WORK/out4b.ipynb.txt" || { echo "PRZEBIEG 4: brak podsumowania liczbowego"; exit 1; }
grep -q "EGMS − niwelacja \[mm\]" "$WORK/out4b.ipynb.txt" || { echo "PRZEBIEG 4: brak tabeli rozbieżności"; exit 1; }
grep -q "Typowa niezgodność EGMS–niwelacja jest około" "$WORK/out4b.ipynb.txt" || { echo "PRZEBIEG 4: brak niepewności (dwa pasy)"; exit 1; }
grep -q "typowa niezgodność EGMS–niwelacja (repery stabilne)" "$WORK/out4b.ipynb.txt" || { echo "PRZEBIEG 4: brak tabeli pasów"; exit 1; }
grep -q "Po odjęciu wspólnego przesunięcia różnica EGMS − niwelacja" "$WORK/out4b.ipynb.txt" || { echo "PRZEBIEG 4: brak sekcji reperu stabilnego"; exit 1; }
"$PY" - "$WORK/out4a.ipynb" "$WORK/out4b.ipynb" <<'PYEOF'
import sys, nbformat
need = {"out4a": 2, "out4b": 5}             # GNSS: rozrzut + stacja; niwelacja: mapa + rozrzut + >= 2 repery + reper stabilny
for path in sys.argv[1:]:
    nb = nbformat.read(path, as_version=4)
    imgs = sum(1 for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []) if "image/png" in o.get("data", {}))
    key = path.rsplit("/", 1)[-1].split(".")[0]
    assert imgs >= need[key], f"PRZEBIEG 4 {key}: za mało rycin ({imgs})"
    assert all(c.metadata.get("cellView") == "form" for c in nb.cells if c.cell_type == "code"), f"{key}: kod nieukryty"
    print(f"PRZEBIEG 4 {key}: {imgs} rycin")
PYEOF
echo "HARNESS: 4 przebiegi zgodne z oczekiwaniem"
