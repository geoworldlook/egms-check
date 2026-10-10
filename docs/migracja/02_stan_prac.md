# 2. Stan prac (2026-10-10)

> EGMS Check (GeoWorldLook) — przekazanie projektu, stan 2026-10-10, gałąź `claude/dreamy-dirac-jd4vue`.
> Indeks: [`../MIGRACJA_stan_i_audyt.md`](../MIGRACJA_stan_i_audyt.md)

### 2.1 Podsumowanie w jednym akapicie

E1 ma gotowy, przetestowany notatnik (`notebooks/EGMS_Check.ipynb`). Na **prawdziwych danych** wykonano
sekcje 1–4: wybór stacji, pobranie szeregów GNSS i listę plików EGMS. **Porównania EGMS z GNSS na prawdziwych
danych jeszcze nie ma.** Następny krok to pobranie 4,4 GB EGMS (sekcja 5) po potwierdzeniu progów. E2 jest
na etapie planu: brak kodu, decyzja o miejscu (NRW czy Hengelo) otwarta.

### 2.2 Tabela stanu

| Element | Stan | Dowód |
|---|---|---|
| Przegląd literatury | gotowy | `docs/evidence/F1`, `F4`, `F7`; pełne teksty 6 publikacji w `docs/evidence/literatura_txt/` (poza gitem) |
| Plan wdrożenia i eksperymentów | gotowy, częściowo nieaktualny (przypadek PTO1 zastąpiony przez Groningen) | `docs/plans/Plan_v1_wdrozenie.md`, `Plan_v1_eksperymenty.md` |
| Dostęp do API EGMS | **działa z prawdziwym kluczem** (Colab, 2026-10-10) | wyszukania i rozmiary plików z API; `Plan_v1_otwarte_pytania.md` A2 |
| Przypadek PTO1 (delta Padu) | **wstrzymany**: GNSS (PANGAEA) kończy się 2021-04, NGL 2019-07; wspólne okno z wydaniami dostępnymi w API to 46% (2019–2023) i 26% (2020–2024), poniżej progu 85% | `Plan_v1_otwarte_pytania.md` A1, A2, B5 |
| E1 Groningen — wybór stacji | **wykonany na prawdziwych danych**: 27 osiadających (−2,3 do −6,8 mm/rok) + 8 stabilnych z okolicy (8–28 km) | wynik sekcji 2 w Colab (`03_metoda_i_decyzje.md`, 3.2) |
| E1 — szeregi GNSS | **pobrane** (35 stacji, NGL IGS20, płyta euroazjatycka odjęta) | sekcja 3 w Colab; manifest na Dysku |
| E1 — pliki EGMS | **zidentyfikowane**: 31 plików L2B 2019–2023, 4443 MB, ścieżki 15, 88 (wst.), 37, 110, 139 (zst.) | sekcja 4 w Colab |
| E1 — pobranie, kontrole, porównanie, werdykt | **kod gotowy i przetestowany na danych testowych; na prawdziwych danych nieuruchomiony** | `tests/colab_harness/` |
| E2 | plan; brak kodu | `docs/evidence/F6_przypadki_zapasowe/zapas_nrw_niwelacja.md`, `F3_przypadek_repery_Hengelo.md` |
| Wpis na blog | plan | `docs/plans/Plan_v1_wpis_na_blog.md` |

### 2.3 Co jest gdzie

| Zasób | Miejsce | Uwagi przy migracji |
|---|---|---|
| Kod i dokumenty | GitHub `geoworldlook/2_geoworldlook-egmscheck`, gałąź **`claude/dreamy-dirac-jd4vue`** (nie połączona z `main`, brak PR) | nowe konto potrzebuje dostępu do repozytorium albo jego przeniesienia (`04_migracja_kroki.md`) |
| Notatnik Colab | `https://colab.research.google.com/github/geoworldlook/2_geoworldlook-egmscheck/blob/claude/dreamy-dirac-jd4vue/notebooks/EGMS_Check.ipynb` | po zmianie właściciela lub gałęzi zmienia się adres i `BRANCH` w sekcji 0 |
| Kopia robocza na Dysku | `MyDrive/GeoWorldLook/egmscheck` (klon repozytorium; tu trafiają GNSS, manifest, wycinek EGMS, wyniki) | skopiować na nowy Dysk albo pozwolić notatnikowi sklonować od nowa |
| Klucz CLMS API | `MyDrive/GeoWorldLook/secrets/clms_token.json` | **nie kopiować**; na nowym koncie wygenerować nowy klucz (`04_migracja_kroki.md`, krok 3) |
| Surowe pliki EGMS | dysk sesji Colab `/content/egms_raw` (ulotny) | nie migrują; pobiorą się ponownie |
| PDF publikacji | Dysk: `/drive/EGMS` | prawa wydawców; udostępnić nowemu kontu lub pobrać ponownie |
| Pełne teksty publikacji | `docs/evidence/literatura_txt/*.txt` (ignorowane przez git) | **istnieją tylko lokalnie w starej sesji**; w nowej odtworzyć z PDF |
| Kontekst rozmów z Claude | nie migruje | ten dokument + `CLAUDE.md` + `Plan_v1_otwarte_pytania.md` (sekcja F) |

### 2.4 Kod

| Plik | Rola | Test |
|---|---|---|
| `step_00_reference_check.py` | spójność tabel przepisanych z Fabris i Nazari 2026 | `python step_00_reference_check.py` — przechodzi |
| `step_01_ingest.py` | klucz CLMS → token; wyszukanie i pobranie EGMS z manifestem SHA-256; NGL: MIDAS, tenv3; reguła wyboru stacji | `--selftest` — przechodzi (atrapa serwera) |
| `step_02_checks_extract.py` | wycinek punktów EGMS wokół stacji; kontrole A1–A3, A5 (duplikaty) | tylko przez test notatnika |
| `step_03_compare_gnss.py` | GNSS → LOS, dopasowanie dat, prędkości, metryki, werdykt K1–K4, wykresy | tylko przez test notatnika |
| `build_colab_master.py` → `notebooks/EGMS_Check.ipynb` | notatnik E1 (sekcje 0–10); generowany, nie edytować ręcznie | `tests/colab_harness/` — przechodzi (commit `fe368e8`) |
| `prototypes/` | wcześniejsze notatniki PTO1 i prototyp E1/E2 | `egms_simple_check.py --selftest` — przechodzi |
