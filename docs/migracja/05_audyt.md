# 5. Audyt dotychczasowych wyników

> EGMS Check (GeoWorldLook) — przekazanie projektu, stan 2026-10-10, gałąź `claude/dreamy-dirac-jd4vue`.
> Indeks: [`../MIGRACJA_stan_i_audyt.md`](../MIGRACJA_stan_i_audyt.md)

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
