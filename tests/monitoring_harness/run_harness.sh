#!/usr/bin/env bash
# TEST: pełny przebieg notebooks/EGMS_Monitoring.ipynb na atrapach (bez sieci do EGMS, NGL, NRW, ASF, Earthdata).
# Użycie: tests/monitoring_harness/run_harness.sh <python środowiska colab313> <katalog roboczy (usuwany)>
# Uwaga: usuwa i tworzy od nowa /content/drive/MyDrive/GeoWorldLook/egmscheck (atrapa Dysku, jak tests/colab_harness).
set -euo pipefail
PY="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; WORK=$2   # bez readlink: symlink pythona venv musi zostać
VENV=$(cd "$(dirname "$PY")/.." && pwd)
REPO=$(cd "$(dirname "$0")/../.." && pwd); H=$REPO/tests/monitoring_harness
BRANCH=claude/dreamy-dirac-jd4vue
URL=https://github.com/geoworldlook/2_geoworldlook-egmscheck.git
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
echo "=== PRZEBIEG 3: notatnik z repozytorium bez zatwierdzeń: pobranie EGMS już jest na Dysku (przebiegi 1-2), sekcje 2-3 przechodzą, oczekiwany głośny stop na pierwszej niezatwierdzonej sekcji (monitoring) ==="
if run_nb "$REPO/notebooks/EGMS_Monitoring.ipynb" "$WORK/out3.ipynb" > "$WORK/pass3.log"; then
  echo "PRZEBIEG 3: notatnik bez zatwierdzeń nie może przejść"; exit 1
fi
grep -q "Sekcja CHECK_CONFIG\['monitoring'\] nie jest zatwierdzona" "$WORK/out3.ipynb.txt"
tail -3 "$WORK/pass3.log"
echo "HARNESS: 3 przebiegi zgodne z oczekiwaniem"
