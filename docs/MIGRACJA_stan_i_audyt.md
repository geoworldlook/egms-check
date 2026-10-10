# EGMS Check — przekazanie projektu: cel, stan prac, audyt

> Status: AKTUALNY, 2026-10-10. Gałąź `claude/dreamy-dirac-jd4vue`.
> Dokument startowy dla nowego konta (GitHub, Google, Claude). Czytaj go przed `CLAUDE.md`:
> część zapisów w `CLAUDE.md` i `docs/ARCHITEKTURA.md` opisuje stan planowany z 2026-10-09, a nie obecny
> (sekcja 5.4).

---

## 1. Cel projektu

Sprawdzić na otwartych danych, czy EGMS (European Ground Motion Service, Copernicus) wiarygodnie pokazuje
**powolne osiadanie terenu**, czyli czy nadaje się do jego monitorowania z kosmosu. Wynik ma posłużyć jako
przykład zastosowania na blogu GeoWorldLook i do prezentacji na spotkaniu.

Dwa eksperymenty:

| | Eksperyment | Dane naziemne | Pytanie |
|---|---|---|---|
| **E1** | walidacja na GNSS | stacje GNSS z Nevada Geodetic Laboratory (NGL) w rejonie pola gazowego Groningen | czy EGMS podaje to samo tempo osiadania co GNSS i nie pokazuje osiadania tam, gdzie GNSS go nie widzi? |
| **E2** | walidacja na osiadaniu zmierzonym niwelacją | rekomendacja: niwelacja NRW (otwarte dane); alternatywa: Hengelo (NLOG) | czy EGMS zgadza się z niezależnym pomiarem wysokości reperów? |

Zasady stałe (szczegóły: `CLAUDE.md`): dane otwarte z manifestem i SHA-256; progi zatwierdzone przed
obliczeniami i niezmieniane po wynikach; błąd głośny zamiast wartości zastępczych; brak danych wymyślonych;
sformułowanie „pomiar naziemny potwierdza tempo osiadania widoczne w EGMS”.

---

## 2. Stan prac (2026-10-10)

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
| E1 Groningen — wybór stacji | **wykonany na prawdziwych danych**: 27 osiadających (−2,3 do −6,8 mm/rok) + 8 stabilnych z okolicy (8–28 km) | wynik sekcji 2 w Colab (sekcja 3.2 niżej) |
| E1 — szeregi GNSS | **pobrane** (35 stacji, NGL IGS20, płyta euroazjatycka odjęta) | sekcja 3 w Colab; manifest na Dysku |
| E1 — pliki EGMS | **zidentyfikowane**: 31 plików L2B 2019–2023, 4443 MB, ścieżki 15, 88 (wst.), 37, 110, 139 (zst.) | sekcja 4 w Colab |
| E1 — pobranie, kontrole, porównanie, werdykt | **kod gotowy i przetestowany na danych testowych; na prawdziwych danych nieuruchomiony** | `tests/colab_harness/` |
| E2 | plan; brak kodu | `docs/evidence/F6_przypadki_zapasowe/zapas_nrw_niwelacja.md`, `F3_przypadek_repery_Hengelo.md` |
| Wpis na blog | plan | `docs/plans/Plan_v1_wpis_na_blog.md` |

### 2.3 Co jest gdzie

| Zasób | Miejsce | Uwagi przy migracji |
|---|---|---|
| Kod i dokumenty | GitHub `geoworldlook/2_geoworldlook-egmscheck`, gałąź **`claude/dreamy-dirac-jd4vue`** (nie połączona z `main`, brak PR) | nowe konto potrzebuje dostępu do repozytorium albo jego przeniesienia (sekcja 4) |
| Notatnik Colab | `https://colab.research.google.com/github/geoworldlook/2_geoworldlook-egmscheck/blob/claude/dreamy-dirac-jd4vue/notebooks/EGMS_Check.ipynb` | po zmianie właściciela lub gałęzi zmienia się adres i `BRANCH` w sekcji 0 |
| Kopia robocza na Dysku | `MyDrive/GeoWorldLook/egmscheck` (klon repozytorium; tu trafiają GNSS, manifest, wycinek EGMS, wyniki) | skopiować na nowy Dysk albo pozwolić notatnikowi sklonować od nowa |
| Klucz CLMS API | `MyDrive/GeoWorldLook/secrets/clms_token.json` | **nie kopiować**; na nowym koncie wygenerować nowy klucz (sekcja 4, krok 3) |
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

---

## 3. Metoda E1 i zapisane decyzje

### 3.1 Metoda (według Koudogbo i in. 2025, oficjalny raport walidacji EGMS 2019–2023)

1. Punkty EGMS L2b w promieniu 100 m od stacji (200 m jako test wrażliwości), co najmniej 3 punkty; szereg
   EGMS = mediana punktów w każdej dacie.
2. GNSS E, N, U rzutowane na kierunek satelity: `d = E·los_east + N·los_north + U·los_up` (średni wektor LOS
   punktów w buforze).
3. GNSS w datach EGMS: mediana dób w oknie ±6 dni; wspólne okno; wspólna data odniesienia.
4. Prędkość obu szeregów tym samym modelem: trend liniowy + sinusoida roczna.
5. `dv = v_GNSS,LOS − v_EGMS`; odchylenie standardowe różnicy szeregów; korelacja.
6. Kontrole blokujące przed porównaniem: A1 (norma LOS = 1), A2 (`los_up` = cos kąta padania), A3 (przeciwny
   znak `los_east` na orbitach wst./zst.), A5 (duplikaty z zakładek burstów < 1 m). A6 (pokrycie ≥ 85%
   w obu definicjach: wspólne okno / okres wydania oraz daty z GNSS / wspólne okno) filtruje pary.

### 3.2 Reguła wyboru stacji (zatwierdzona 2026-10-10)

- Wspólne warunki: dane GNSS od ≤ 2019.0 do ≥ 2024.25; niepewność vu (MIDAS) ≤ 1,0 mm/rok; ≤ 2 skoki.
- **Osiadające:** wszystkie stacje w prostokącie 5,8–7,3° E, 52,9–53,6° N z vu ≤ −2 mm/rok → 27 stacji.
- **Stabilne (kontrola negatywna):** |vu| ≤ 1,0 mm/rok w prostokącie 4,8–8,3° E, 52,4–54,0° N; 8 najbliższych
  stacji osiadającej → SCHI, NORG, BLLM, TGEM, TGBF, AMEL, TGWE, RDN1 (vu od −0,90 do +0,07 mm/rok).
- Źródło: `https://geodesy.unr.edu/velocities/midas.IGS.txt` (IGS20; dane do 2024.646).

### 3.3 Kryteria (stan: K1 i K3 **czekają na potwierdzenie autora**)

| | Kryterium | Próg | Źródło progu |
|---|---|---|---|
| K1 | odsetek par stacja × ścieżka (osiadające) z \|dv\| ≤ 1,5 mm/rok | ≥ 80% | 1,5 mm/rok: Fabris i Nazari 2026 za Fiaschi i in. 2018; **80%: propozycja** |
| K2 | mediana odchylenia standardowego różnicy szeregów | ≤ 5 mm | Crosetto i in. 2025 (White Paper) |
| K3 | stacje stabilne: max \|v_EGMS\| | ≤ 1,5 mm/rok | **propozycja** |
| K4 | nachylenie v_EGMS względem v_GNSS | raportowane | — |

Wniosek: POTWIERDZONE (K1, K2, K3) / CZĘŚCIOWO (tylko K1) / NIE POTWIERDZONE.

---

## 4. Migracja na nowe konto — lista kroków

1. **GitHub.** Właściciel `geoworldlook` dodaje nowe konto jako współpracownika z prawem zapisu albo przenosi
   repozytorium. Jeśli zmieni się właściciel lub nazwa: poprawić adres w `build_colab_master.py` (sekcja 0,
   `git clone`), w README i w linku Colab, potem `python build_colab_master.py`.
   Rozważyć scalenie gałęzi `claude/dreamy-dirac-jd4vue` z `main` przez PR (decyzja otwarta).
2. **Claude Code na nowym koncie.** Zainstalować aplikację GitHub Claude dla repozytorium i podłączyć GitHub
   w ustawieniach claude.ai. Pierwsza wiadomość w nowej sesji: sekcja 8 tego dokumentu.
3. **Klucz CLMS (Copernicus Land).** Na nowym koncie CLMS wygenerować nowy klucz serwisowy (JSON z `client_id`,
   `user_id`, `token_uri`, `private_key`) i zapisać jako `MyDrive/GeoWorldLook/secrets/clms_token.json`
   na nowym Dysku. **Stary klucz unieważnić** w profilu CLMS. Uwaga bezpieczeństwa: sekcja 5.5.
4. **Dysk Google.** Skopiować `MyDrive/GeoWorldLook/egmscheck/data/02_Raw_Ground/3_gnss_ngl/` i
   `data/00_Metadata/MANIFEST.csv` (oszczędza pobierania; niekonieczne). Jeśli wycinek
   `data/03_Extracts/groningen/egms_l2b_points.csv.gz` już powstał, skopiować go — notatnik wtedy nie pobiera
   4,4 GB. Udostępnić folder `/drive/EGMS` z PDF publikacji.
5. **Pełne teksty publikacji.** W nowej sesji Claude odtworzyć `docs/evidence/literatura_txt/` z PDF
   (lista plików w README tego katalogu; poziomy weryfikacji źródeł w plikach `F*`).
6. **Sprawdzenie.** W Colab: `Uruchom wszystko`. Sekcje 0–4 muszą dać 35 stacji (27 + 8) i 31 plików,
   4443 MB. Inny wynik oznacza zmianę danych NGL — zapisać datę i nie zmieniać reguły.

---

## 5. Audyt dotychczasowych wyników

Skala: **WYSOKI** — może zmienić wniosek; **ŚREDNI** — osłabia wniosek lub prezentację; **NISKI** — porządek.

### 5.1 Co faktycznie wiemy, a co tylko przetestowaliśmy

| Wynik | Poziom dowodu |
|---|---|
| API EGMS: wydania przez API tylko 2019–2023 i 2020–2024; L2A/L2B/L3 | prawdziwe zapytanie, Colab 2026-10-10 |
| PTO1 nie spełnia warunku pokrycia 85% z żadnym wydaniem z API | prawdziwe dane (PANGAEA, NGL, API) |
| 27 + 8 stacji w Groningen, 31 plików EGMS, 4,4 GB | prawdziwe dane (NGL, API) |
| Notatnik E1 liczy poprawnie (odtwarza zadane prędkości, nachylenie 1,00) | **tylko dane testowe** o znanej odpowiedzi |
| Zgodność EGMS z GNSS w Groningen | **brak wyniku** — nie wolno jej jeszcze ogłaszać |
| Konwencja znaku i wektora LOS w plikach EGMS | niezweryfikowana; sprawdzi ją sekcja 6 na prawdziwych danych |

### 5.2 Metodyka

| # | Waga | Ustalenie | Zalecenie |
|---|---|---|---|
| M1 | **WYSOKI** | **Niezależność.** EGMS L2b jest dowiązany do modelu prędkości GNSS (siatka 50 km), budowanego głównie z sieci EUREF i pomocniczo z NGL (Even i in. 2024; F4, F7 pkt 7). Wszystkie nasze stacje pochodzą z NGL. Część zgodności, zwłaszcza K3 (prędkości bezwzględne stacji stabilnych), może wynikać z kalibracji, a nie z pomiaru InSAR. Wcześniejszy plan zakładał test na L2a — **nie jest zaimplementowany**. | Przed publikacją: (a) sprawdzić, czy stacje z Groningen weszły do modelu GNSS EGMS (raport kalibracji); (b) dodać test różnicowy na L2a lub L2b: `v(osiadająca) − v(stabilna)` na tej samej ścieżce, EGMS kontra GNSS. Różnica kasuje wpływ kalibracji i jest najmocniejszym argumentem (np. Ameland: AME1 kontra AMEL). |
| M2 | ŚREDNI | **Pary nie są niezależne.** K1 liczy pary stacja × ścieżka; każda stacja daje 4–5 par; DZYL/DZY1 i AME1/AME2 stoją obok siebie. Rzeczywista liczba niezależnych obserwacji jest mniejsza niż `n_par`. | Raportować także K1 na poziomie stacji (mediana dv po ścieżkach); w opisie podać liczbę stacji, nie tylko par. |
| M3 | ŚREDNI | **K3 mierzy \|v_EGMS\|, nie zgodność z GNSS.** Stacja „stabilna” według MIDAS (cały okres pomiarów, nawet od 2002 r.) może poruszać się w oknie 2019–2023. | Pokazywać obok K3 także `v_gnss_los` i `dv` dla stacji stabilnych (są w tabeli sekcji 7); rozważyć K3 jako \|dv\| — decyzja **przed** pobraniem. |
| M4 | ŚREDNI | Progi K1 (80%) i K3 (1,5 mm/rok) są propozycjami, nie wartościami z literatury, i **nie zostały jeszcze potwierdzone**. | Potwierdzić przed sekcją 5; zapisać datę w `Plan_v1_otwarte_pytania.md`, sekcja F. |
| M5 | ŚREDNI | **Stacje TG\* (mareografy) i wyspy.** Stacje przy nabrzeżu (TGBF Borkum, TGEM Emden) mogą mieć mało punktów lądowych w 100 m. | Bez zmian w regule; status „za mało punktów” jest raportowany jawnie, nie usuwany. |
| M6 | NISKI | Niepewność prędkości liczona dla szumu białego — dla GNSS i InSAR zaniżona (szum skorelowany). | W raporcie nazywać ją „formalną”; nie używać do testów istotności. |
| M7 | NISKI | Reguła duplikatów (< 1 m między plikami) w teście usunęła raz punkt prawdziwy (0,41 m od innego). | Liczba usuniętych punktów i mediana odległości są drukowane w sekcji 6; ocenić na prawdziwych danych. |
| M8 | NISKI | Zmiana reguły stacji stabilnych (0,5 → 1,0 mm/rok, region rozszerzony) nastąpiła po obejrzeniu listy stacji, ale **przed** pobraniem jakichkolwiek danych EGMS. | Zgodne z zasadą 9 `CLAUDE.md`; chronologia zapisana w sekcji F. Przy publikacji podać ją jawnie. |
| M9 | NISKI | Układ odniesienia: NGL „EU” (IGS20, płyta odjęta) kontra EGMS ETRF2000. Różnica w pionie: ułamki mm/rok (F4, sekcja 7). | Opisać jako składnik niepewności; ewentualnie wartość bias w tabeli kryteriów ją pokaże. |

### 5.3 Kod i zgodność z `CLAUDE.md`

| # | Waga | Ustalenie | Zalecenie |
|---|---|---|---|
| C1 | ŚREDNI | Architektura z `CLAUDE.md` (jak AgriWatch: `step_05_colab_run.py`, `run_task`, `CHECK_CONFIG`, rejestr `gwl_*.csv`, `run_summary.md`, `bulletin.md`, `egmscheck_latest.json`) **nie jest zaimplementowana**. Konfiguracja jest w słowniku `CFG` w notatniku. | Świadome uproszczenie na rzecz czytelnego notatnika na spotkanie. Po pierwszym wyniku: przenieść `CFG` do `CHECK_CONFIG` i dodać `run_summary.md` (wersje bibliotek, commit, konfiguracja) — wymóg odtwarzalności (zasada 7). |
| C2 | ŚREDNI | **Brak `run_summary.md`.** Notatnik drukuje commit kodu, ale nie zapisuje wersji bibliotek ani konfiguracji obok wyników. | Dodać zapis w sekcji 8 przed pierwszym prawdziwym przebiegiem lub tuż po nim. |
| C3 | ŚREDNI | `step_02` i `step_03` nie mają własnych `--selftest`; sprawdza je tylko test notatnika. | Test notatnika jest teraz w repozytorium (`tests/colab_harness/`); dodać testy jednostkowe `fit_velocity`, `gnss_at_dates`, `check_conventions`. |
| C4 | NISKI | Pobieranie (sekcja 5) zapisuje wycinek dopiero po wszystkich 31 plikach. Przerwanie sesji Colab po kilkunastu plikach wymaga ponownego pobrania, jeśli dysk sesji został wyczyszczony. | Akceptowalne przy 4,4 GB; przy większych regionach zapisywać wycinek po każdym pliku. |
| C5 | NISKI | Zasady „brak wartości domyślnych” i „błąd głośny”: spełnione (brak domyślnych parametrów w sygnaturach; brak `except Exception`; braki → `RuntimeError` lub jawny status). | — |

### 5.4 Dokumentacja

| # | Waga | Ustalenie | Zalecenie |
|---|---|---|---|
| D1 | ŚREDNI | `CLAUDE.md` opisuje przypadek 1 jako PTO1 i przypadek 2 jako Hengelo; obecny stan: Groningen, a E2 nierozstrzygnięty (rekomendacja NRW). | Zaktualizować `CLAUDE.md` po decyzji o E2. Do tego czasu obowiązuje ten dokument (odnośnik dodany na górze `CLAUDE.md`). |
| D2 | NISKI | `docs/ARCHITEKTURA.md` ma status PROPOSED i mówi „kodu jeszcze nie ma”. | Zaktualizować razem z C1. |
| D3 | NISKI | „Najważniejsze rzeczy niezweryfikowane” w `CLAUDE.md`: punkty o API (lista wydań, działanie z tokenem) są już zweryfikowane. | Przenieść do sekcji „zweryfikowane” przy aktualizacji D1. |

### 5.5 Bezpieczeństwo

| # | Waga | Ustalenie | Zalecenie |
|---|---|---|---|
| S1 | **WYSOKI** | Wcześniej w rozmowie wklejono klucz CLMS i sekret CDSE (Copernicus Data Space). Należy je uznać za ujawnione. | **Unieważnić oba** i wygenerować nowe na nowym koncie. Nigdy nie wklejać kluczy do czatu. |
| S2 | — | Repozytorium sprawdzone: w historii gita brak kluczy prywatnych; `.gitignore` wyklucza `secrets*`, `*.key`, `.env`. Klucz testowy w `tests/colab_harness` jest generowany przy każdym uruchomieniu i nie jest zapisywany w repozytorium. | — |

---

## 6. Otwarte decyzje (w kolejności blokowania)

1. **Progi K1 (80%) i K3 (1,5 mm/rok)** — potwierdzić przed sekcją 5 (M4).
2. **K3 jako \|v_EGMS\| czy \|dv\|** — przed sekcją 5 (M3).
3. **Test różnicowy niezależny od kalibracji** (M1) — czy dodać przed pierwszym przebiegiem, czy jako drugi etap.
4. **E2: NRW czy Hengelo** — NRW ma otwarte dane i powtarzalne epoki; Hengelo wymaga ręcznego przepisania
   tabeli z PDF (`hengelo_*_UNVERIFIED.csv` nie nadaje się do obliczeń).
5. Scalenie gałęzi z `main`; czy wersjonować wycinki `data/03_Extracts` w repozytorium.
6. Przypadki dodatkowe (później, na wyraźną prośbę): Lorca (LOR1 −64 mm/rok, LRC1 −22,4 mm/rok, ok. 7,4 GB),
   delta Padu.

## 7. Następne kroki

1. Potwierdzić decyzje 1–3 z sekcji 6.
2. Colab: sekcja 5 `DOWNLOAD = True` → sekcje 5–9. Zachować tabelę kontroli (sekcja 6), statusy par
   (sekcja 7), tabelę kryteriów i wniosek (sekcja 8), wykresy.
3. Ocena wyniku zgodnie z regułą zapisaną przed obliczeniami; rozbieżność raportować tak samo jak zgodność.
4. Uzupełnić C1/C2 (`run_summary.md`) i D1–D3.
5. E2 według decyzji 4.
6. Wpis na blog (`docs/plans/Plan_v1_wpis_na_blog.md`).

## 8. Pierwsza wiadomość do Claude na nowym koncie (do skopiowania)

```
Projekt EGMS Check (GeoWorldLook), repozytorium geoworldlook/2_geoworldlook-egmscheck,
gałąź claude/dreamy-dirac-jd4vue. Przeczytaj najpierw docs/MIGRACJA_stan_i_audyt.md,
potem CLAUDE.md i docs/plans/Plan_v1_otwarte_pytania.md (sekcja F).
Pracujemy w Colab (notebooks/EGMS_Check.ipynb, generowany przez build_colab_master.py).
Klucz CLMS jest na moim Dysku w MyDrive/GeoWorldLook/secrets/clms_token.json —
nie proś o jego treść i nie kopiuj go nigdzie.
Następny krok: sekcja 6 dokumentu migracyjnego (otwarte decyzje), potem pierwszy przebieg E1.
```
