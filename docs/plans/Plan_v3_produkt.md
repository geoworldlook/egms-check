# Plan v3 — EGMS Check jako produkt (standard projektu GeoWorldLook)

Status: decyzja D-095 zrealizowana 2026-11-02 (wersja 1.0.0); kroki z §3 czekają na decyzje autora.
Wzór: AgriScreen (układ repozytorium, polecenia pakietu, publikacja, CI). Metody, progi i wyniki bez zmian.

## 1. Decyzja D-095 (2026-11-02)

EGMS Check dostaje ten sam układ i przepływ danych co AgriScreen:
`dane otwarte → obliczenia na tym komputerze (na żądanie) → wyniki na Dysku → docs/showcase/ → README i strona`.

- **Pakiet `egmscheck` jako cienka warstwa** nad modułami `step_0N`: `python -m egmscheck run | publish | selftest |
  settings` (oraz `approvals`, `test`), ten sam parser co `python step_09_local.py …`. Moduły zostają w katalogu
  głównym, bo czytają je notatniki Colab (zapas) i klon repozytorium na Dysku. Przeniesienie ich do pakietu to osobny
  krok z testem regresji (jak AgriScreen 1.0).
- **Bez `weekly` i bez zadania w Harmonogramie:** EGMS wychodzi raz w roku; `run` i `publish` uruchamia się na żądanie.
- **`publish`:** stały wybór plików wynikowych → `docs/showcase/` i `egmscheck_results.json` (liczby tylko z plików;
  przy każdym wyniku zadanie, czas i commit kodu z rejestru `gwl_runs`, z odpowiednikiem w historii po D-094).
  Brak pliku wymaganego zatrzymuje publikację; plik z poprzedniej publikacji, którego już nie ma w wynikach, jest
  usuwany. Commit tylko `docs/showcase/`; push systemowym Gitem, bez okien logowania; `--no-git` = samo kopiowanie.
- **CI:** ruff i testy bez sieci wszystkich modułów (GitHub Actions, Python 3.12). Test etapu B (`step_08`) działa
  tylko na Linuksie: Windows bez długich ścieżek go pomija.
- **Dokumenty:** `docs/STAN_I_PLAN.md`, `docs/evidence/karta_wynikow.md`, ten plan; plany v1–v2, notatki z migracji
  i przekazania przeniesione do `docs/archive/` (`git mv`; treść bez zmian poza ścieżkami i drobnymi poprawkami
  brzmienia).
- **Dokument Geobasis NRW** (`Datenformatbeschreibung` HFP, 07/2023): zamiast kopii PDF w repozytorium — odnośnik
  i suma SHA-256 (`docs/evidence/zrodla/README.md`). Strona produktu podaje licencję dl-de/zero-2-0 dla danych,
  a sam dokument nie podaje licencji, więc nie rozpowszechniamy kopii. Plik na stronie jest identyczny z wcześniejszą
  kopią (ta sama suma SHA-256, sprawdzone 2026-11-02).
- **Wersje** według semver od 1.0.0; wcześniejsze etapy w `CHANGELOG.md` bez numerów.

## 2. Zrobione (2026-11-02)

| Element standardu | Gdzie |
|---|---|
| README (EN) jako karta produktu, „How it is built”, licencje danych | `README.md` |
| `LICENSE`, `CHANGELOG.md`, `pyproject.toml`, `environment.yml` | katalog główny |
| Polecenia pakietu, publikacja | `egmscheck/`, `step_09_local.py` |
| CI | `.github/workflows/selftest.yml` |
| Stan i plan, uruchomienie, architektura | `docs/STAN_I_PLAN.md`, `docs/URUCHOMIENIE_LOKALNE.md`, `docs/ARCHITEKTURA.md` |
| Karta wyników | `docs/evidence/karta_wynikow.md` |
| Wyniki do publikacji | `docs/showcase/` (pierwsza publikacja: przebieg z 2026-10-15, kod `06eeefc`) |
| Archiwum | `docs/archive/` |

## 3. Następne kroki (propozycje; każdy wymaga decyzji autora)

1. **Następne wydanie EGMS:** te same reguły (K1–K4, N1–N4) bez zmiany progów; `run`, potem `publish`.
   Przed pobraniem: potwierdzenie rozmiaru (`CONFIRM_MB_*`).
2. **Etap B na prawdziwych danych** (konfiguracja zatwierdzona 2026-10-12: Groningen, ścieżki 37 i 88,
   2024-01 … 2026-09): wymaga konta NASA Earthdata i kredytów ASF HyP3; na Windows także długich ścieżek.
3. **Hipoteza przesunięcia −2 mm/rok w NRW:** ruch punktów nawiązania sieci niwelacyjnej, układy ETRF2000 i DHHN2016.
   Protokół przed liczeniem.
4. **Czas do wykrycia ruchu:** obecna miara (trend 2σ, AR(1)) zaznacza też większość stacji stabilnych; przed użyciem
   nowa metoda i protokół (`docs/evidence/karta_wynikow.md`, obserwacje bez progu).
5. **Moduły `step_0N` w pakiecie** (jak AgriScreen 1.0): po decyzji, czy Colab zostaje zapasem; test regresji na
   tych samych danych syntetycznych.
