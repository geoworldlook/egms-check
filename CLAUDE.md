# CLAUDE.md — EGMS Check (GeoWorldLook)

> **Stan bieżący (2026-10-10), migracja i audyt: `docs/MIGRACJA_stan_i_audyt.md` — czytaj najpierw.**
> Sekcja „Dwa przypadki” niżej opisuje plan z 2026-10-09; przypadek GNSS to obecnie region Groningen.

## Cel projektu

Własny projekt w ramach GeoWorldLook: sprawdzić, czy dane InSAR z European Ground Motion Service (EGMS)
zgadzają się z pomiarami naziemnymi z zaufanych, otwartych źródeł, i opisać to jako przykład
zastosowania na blogu GeoWorldLook. Wszystko na danych otwartych.

## Dwa przypadki

1. **GNSS — stacja PTO1 (delta Padu).** Dobowy szereg wysokości z otwartego zbioru PANGAEA nałożony
   na szereg EGMS Calibrated z bufora wokół stacji.
   Specyfikacja: `docs/evidence/F2_przypadek_GNSS_PTO1.md`. Liczby z publikacji: `data/04_Reference/fabris2026_*.csv`.
2. **Repery — Hengelo (pole solne Twenthe-Rijn).** Niwelacja precyzyjna 2020–2023 z rejestru na portalu NLOG
   porównana z EGMS Ortho (pion); dodatkowo prognoza z wcześniejszego wydania.
   Specyfikacja: `docs/evidence/F3_przypadek_repery_Hengelo.md`. Fakty z raportu: `data/04_Reference/hengelo_*.csv`.

Oba są częścią testu z `docs/plans/Plan_v1_test_EGMS.md`. Kolejność: najpierw 1, potem 2.
Przypadki zapasowe (`docs/evidence/F6_przypadki_zapasowe/`) tylko na wyraźną prośbę.

## Struktura: jak w AgriWatch

Repozytorium ma ten sam układ co `1_geoworldlook-agriscreen`. Trzymaj się go:

- skrypty w katalogu głównym: `step_NN_<cel>.py`; generator notatnika `build_colab_master.py`;
- jeden notatnik `notebooks/EGMS_Check.ipynb`, generowany, nie edytowany ręcznie;
- sterowanie przez `step_05_colab_run.py`: `setup_runtime`, `run_task`, zadania `task_*`, `--selftest`;
- konfiguracja w jednym miejscu: `CHECK_CONFIG` w `step_05_colab_run.py`;
- wyniki tabelaryczne w rejestrze `data/registry/gwl_*.csv` (schemat z AgriWatch), pliki w
  `data/05_Final_Outputs/egmscheck/`, na końcu `run_summary.md`;
- katalogi danych z prefiksem liczbowym (`00_Metadata` … `05_Final_Outputs`);
- dokumenty: `docs/ARCHITEKTURA.md` (stan kodu), `docs/plans/Plan_v*.md` (ze statusem i datą),
  `docs/evidence/F*_*.md` (przeglądy i analizy, z poziomem weryfikacji źródeł);
- nagłówek modułu: blok „EGMS Check - KROK N: …" po polsku z metodą i literaturą;
- dokumentacja, docstringi i komentarze po polsku; nazwy w kodzie i opisy osi wykresów po angielsku;
  komunikaty commitów po angielsku w stylu `feat(...)`, `fix(...)`.

Szczegóły: `docs/ARCHITEKTURA.md`. Zanim skopiujesz mechanizm `run_task` i rejestru, przeczytaj
`step_05_colab_run.py` w AgriWatch i przenieś go, zamiast pisać od nowa.

## Wynik końcowy

- wykresy „EGMS kontra pomiar naziemny" dla obu przypadków,
- `bulletin.md`, `egmscheck_latest.json` i ryciny PNG dla strony,
- notatnik wykonujący się od góry do dołu; EGMS pobiera przez API, gdy jest token, a bez tokenu czyta `data/03_Extracts/`,
- wpis na blog: `docs/plans/Plan_v1_wpis_na_blog.md`.

Lista danych do pobrania: `docs/plans/Plan_v1_dane_do_pobrania.md`.

## Zasady pracy (obowiązują zawsze)

1. **Najpierw zrozum eksperyment.** Przed kodem przeczytaj specyfikację przypadku i `docs/evidence/F4_metodyka.md`.
   Jeśli metoda z publikacji jest niejasna, przeczytaj publikację w `docs/evidence/literatura_txt/`, nie zgaduj.
2. **Pytaj, nie zgaduj.** Zatrzymaj się i zapytaj przy każdej decyzji o: wydaniu EGMS, oknie czasowym,
   modelu prędkości, agregacji GNSS, obsłudze braków i skoków, promieniu bufora, punkcie odniesienia, progach.
   Lista znanych decyzji: `docs/plans/Plan_v1_otwarte_pytania.md`.
3. **Błąd głośny, nigdy cichy.** Bez `except Exception`, bez wartości zastępczych. Brak pliku, brak kolumny,
   pusty bufor, brak punktów przy reperze odniesienia — to wyjątek albo jawny `NaN` z powodem, nigdy zero.
   (`run_task` zapisuje błąd zadania w `gwl_runs`; wynik zadania, które się nie powiodło, nie może wyglądać jak prawdziwy.)
4. **Brak wartości domyślnych dla parametrów eksperymentu.** Promień, okno, wydanie, ścieżka, próg i model
   pochodzą z `CHECK_CONFIG`, nie z sygnatur funkcji.
5. **Jawne jednostki i konwencje.** Przemieszczenia w mm, prędkości w mm/rok. Znak: ujemny = osiadanie /
   oddalanie od satelity. Układy: EGMS w EPSG:3035, repery holenderskie w RD (EPSG:28992), GNSS w stopniach WGS84.
6. **Dane surowe są niezmienne.** `data/01_Raw_EGMS/` i `data/02_Raw_Ground/` tylko do odczytu. Każdy plik ma
   wpis w `data/00_Metadata/MANIFEST.csv`: adres, data pobrania, SHA-256, licencja. Dane przepisane z PDF
   mają numer strony oraz kto przepisał i kto sprawdził.
7. **Odtwarzalność.** `run_summary.md` zapisuje wersje bibliotek, konfigurację, wydanie EGMS, commit.
8. **Waliduj względem rzeczywistości.** Najpierw kontrole konwencji na danych (`docs/evidence/F4_metodyka.md`,
   sekcja 2), potem porównanie z liczbami z `data/04_Reference/`.
9. **Uczciwość statystyczna.** Progi z `docs/plans/Plan_v1_kryteria_akceptacji.md` autor zatwierdza przed pierwszym
   przebiegiem. Nie zmieniaj ich po zobaczeniu wyników. Rozbieżność raportuj tak samo jak zgodność;
   nie dobieraj reperów ani buforów pod wynik.
10. **Nie wymyślaj danych.** Współrzędnych stacji i reperów, dat epok i wartości referencyjnych nie uzupełniaj
    z pamięci. Plik `data/04_Reference/hengelo_*_UNVERIFIED.csv` jest podglądem, nie danymi do obliczeń.
11. **Jeden kod, dwie konfiguracje.** Wspólne wczytanie EGMS, wybór przestrzenny, dopasowanie czasowe i metryki.

## Najważniejsze rzeczy niezweryfikowane

- konwencja znaku przemieszczenia LOS i kosinusów kierunkowych w plikach EGMS,
- lista wydań zwracana przez API (`GET /releases`): czy są 2018–2022 i 2020–2024,
- działanie API z prawdziwym tokenem (kod z oficjalnego notatnika nie był tu uruchamiany),
- zawartość pliku `PTO1.txt` (zakres dat, przerwy, skoki),
- tabela reperów z załącznika 5 raportu z Hengelo (współrzędne, wysokości, dokładne daty epok),
- gęstość punktów EGMS wokół reperów w Hengelo i przy reperze odniesienia.

Pełna lista: `docs/plans/Plan_v1_otwarte_pytania.md`.

## Sformułowania do wpisu i raportu

- Mówimy „osiadanie", nie „osuwisko".
- Mówimy „pomiar naziemny potwierdza tempo osiadania widoczne w EGMS", nie „EGMS wykrył".
- EGMS jest produktem archiwalnym, aktualizowanym raz w roku; nie wykrywa zdarzeń nagłych.

## Konwencje pracy z użytkownikiem

- Po każdej zmianie kodu podaj changelog. Przy poprawkach pokazuj tylko zmienione fragmenty.
- Token CLMS API leży poza repozytorium (na Dysku: `MyDrive/GeoWorldLook/secrets/clms_token.json`); nie kopiuj go do repozytorium, notatnika ani logów.
