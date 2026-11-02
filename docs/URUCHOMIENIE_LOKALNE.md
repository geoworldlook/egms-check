# EGMS Check na własnym komputerze (Windows) — bez Colab

Stan: 2026-11-02, wersja 1.0.0. Wzór: AgriScreen (ten sam układ i te same polecenia). Kod w klonie repozytorium,
dane na Dysku Google (synchronizowane, wspólne z Colab jako zapasem), obliczenia na komputerze.

## 1. Układ

```text
Pulpit\GeoWorldLook\
├── workspace.json                rejestr projektów (kod, dane, środowisko, polecenia)
├── projects\egms-check\          kod (git), local_settings.json (poza git)
├── data\egms-check  ──▶          łącze do Dysku Google: Mój dysk\GeoWorldLook\egmscheck
│                                  (ten sam układ data\... co w Colab: 00_Metadata … 05_Final_Outputs, registry, logs)
└── scripts\gwl.cmd               polecenia wszystkich projektów w jednym miejscu
```

Zasady jak w AgriScreen: kod tylko w `projects\` (GitHub), dane tylko na Dysku (`data\` to łącza), klucze tylko
w `Mój dysk\GeoWorldLook\secrets` (`clms_token.json`, `earthdata.json`); nie kopiuj ich do repozytorium.

## 2. Pierwsze uruchomienie

1. Środowisko conda `egmscheck` (etap A i B, z GDAL i MintPy):
   ```bat
   conda create -n egmscheck -y python=3.11 conda-launchers
   conda env update -n egmscheck -f environment.yml
   ```
   (dwa kroki z powodu błędu conda 26.9 na Windows: „Could not find 'share/conda-launchers/cli-64.exe'”).
2. Łącze do danych: `scripts\gwl.cmd egms-check link-data "G:\Mój dysk\GeoWorldLook\egmscheck"`.
3. `local_settings.json` w `projects\egms-check` (poza git; `<użytkownik>` = nazwa konta Windows, albo od razu
   ścieżka do folderu na Dysku, np. `G:\\Mój dysk\\GeoWorldLook\\egmscheck`):
   ```json
   {"data_dir": "C:\\Users\\<użytkownik>\\Desktop\\GeoWorldLook\\data\\egms-check",
    "secrets_dir": "G:\\Mój dysk\\GeoWorldLook\\secrets",
    "regions": ["groningen", "nrw_west"], "stage_b": false, "confirm": {}}
   ```
4. Test: `scripts\gwl.cmd egms-check test` (pełny test na atrapach, kilka minut; nic nie pobiera z sieci).
5. Tylko dla etapu B (HyP3 + MintPy): długie ścieżki w Windows. Nazwa produktu HyP3 ma ok. 80 znaków i występuje
   w ścieżce pliku dwa–trzy razy, a Windows domyślnie przyjmuje najwyżej 260 znaków. Jednorazowo, PowerShell
   uruchomiony jako administrator:
   ```powershell
   New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force
   ```
   Bez tego `run --stage-b` zatrzymuje się przed pierwszym zadaniem z tym poleceniem, a test pomija etap B
   (z komunikatem). Etap A działa bez tej zmiany.

MintPy na Windows wymaga Pythona 3.11 (pakiet `pysolid` w conda-forge nie ma wersji dla 3.12), dlatego
`environment.yml` ma `python=3.11`.

## 3. Polecenia

| Polecenie (`scripts\gwl.cmd egms-check …`) | To samo w konsoli projektu | Co robi |
|---|---|---|
| `run` | `python -m egmscheck run` | etap A dla regionów z ustawień, ryciny, `run_summary.md` |
| `run --region groningen` | `… run --region groningen` | jeden region |
| `run --stage-b` | `… run --stage-b` | także etap B (ASF HyP3 + MintPy) |
| `plan` | `… run --dry-run` | lista zadań w kolejności, bez liczenia |
| `publish` | `python -m egmscheck publish` | wybrane wyniki do `docs/showcase/`, commit i push (§6) |
| `test` | `python -m egmscheck test` | pełny test na atrapach (tests/local_harness) |
| `selftest` | `python -m egmscheck selftest` | testy offline wszystkich modułów i publikacji (to samo w CI) |
| `approvals` | `python -m egmscheck approvals` | stan zatwierdzeń `CHECK_CONFIG` |
| `settings` | `python -m egmscheck settings` | ustawienia po scaleniu |
| `console` | — | konsola z aktywnym środowiskiem w katalogu kodu |
| `open results` / `open logs` | — | `run_summary.md` / folder logów |

`python step_09_local.py …` działa tak samo (ten sam parser poleceń). Kolejność zadań jest taka sama jak w notatniku
`notebooks/EGMS_Monitoring.ipynb`; każde zadanie idzie przez `run_task` i trafia do `gwl_runs`. Pierwszy błąd
zatrzymuje przebieg (błąd głośny), jak w notatniku.

## 4. Potwierdzenia pobrań i zleceń

Pobranie EGMS i zlecenia HyP3 wymagają wpisania liczby z planu (ochrona przed przypadkowym pobraniem wielu GB
i płatnymi zleceniami). Komunikat zadania mówi, co ustawić, np. `ustaw CONFIRM_MB_GRONINGEN = 4321`. Lokalnie:

```bat
scripts\gwl.cmd egms-check run --confirm CONFIRM_MB_GRONINGEN=4321
scripts\gwl.cmd egms-check run --stage-b --confirm "CONFIRM_JOBS['37']=54" --confirm "CONFIRM_JOBS['88']=54"
```

albo trwale w `local_settings.json`: `"confirm": {"CONFIRM_MB_GRONINGEN": 4321, "CONFIRM_JOBS": {"37": 54}}`.
Bez tokenu CLMS przebieg czyta istniejące wycinki z `data\03_Extracts\` (pliki już na Dysku).

## 5. Log i stan

- log: `data\egms-check\data\logs\run_<czas>.log`, podsumowanie `last_run.json` (status, zadania, błąd);
- blokada `data\registry\.egmscheck_local.lock`: drugi przebieg lokalny w tym samym czasie kończy się od razu;
- `scripts\gwl.cmd list` pokazuje stan wszystkich projektów (gałąź, zmiany w kodzie, łącze danych, ostatni przebieg).

EGMS jest aktualizowany raz w roku, więc projekt nie ma zadania w Harmonogramie (inaczej niż AgriScreen).

## 6. Publikacja wyników

Po nowym przebiegu (np. nowe wydanie EGMS) `scripts\gwl.cmd egms-check publish`:

1. kopiuje stały wybór plików z `data\05_Final_Outputs\egmscheck\` do `docs\showcase\` (werdykty, tabele niwelacji,
   ryciny) i zapisuje `egmscheck_results.json` (wszystkie kryteria, skąd jest każdy wynik); brak pliku wymaganego
   zatrzymuje publikację z listą braków;
2. robi commit wyłącznie `docs\showcase\` i push na `main` (systemowy Git, bez okien logowania; brak zapisanego
   logowania = błąd w konsoli, commit zostaje lokalnie).

`publish --no-git` tylko kopiuje (do obejrzenia zmian przed commitem). Potem ręcznie: liczby w `README.md`, na stronie
(`content/projects/egms-check.yaml`) i w profilu GitHub, jeśli się zmieniły.

## 7. Czego test nie sprawdza

- prawdziwych serwerów (CLMS, EGMS, NGL, Geobasis NRW, ASF): to dowodzi dopiero przebieg z tokenem;
- prawdziwego MintPy i GDAL na Windows (test używa atrapy `smallbaselineApp.py`);
- notatników pokazowych `Showcase_*.ipynb` i Colab: `tests/monitoring_harness/run_harness.sh` (Linux).
