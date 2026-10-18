# Prompty do Claude Code — po jednym na sesję

Status: PROPOSED, 2026-10-09. Kolejność i warunki przejścia: `Instrukcja_startowa.md`.
Każdy prompt wklej w całości. Zasady stałe są w `CLAUDE.md`, więc prompty ich nie powtarzają.

---

## Sesja 0 — orientacja

```text
Przeczytaj CLAUDE.md, README.md, docs/ARCHITEKTURA.md i docs/plans/Plan_v1_walidacja_EGMS.md.
Potem docs/plans/Plan_v1_test_EGMS.md, Plan_v1_kryteria_akceptacji.md i Plan_v1_otwarte_pytania.md.
Uruchom: python step_00_reference_check.py

Nie pisz jeszcze kodu. Odpowiedz:
1. Co ma wykazać każdy z dwóch przypadków i jakie są progi (w 5-8 zdaniach).
2. Które pytania z Plan_v1_otwarte_pytania.md (sekcje A, A2, D) wymagają mojej odpowiedzi,
   a które możesz rozstrzygnąć sam, i jak.
3. Jakie widzisz ryzyka lub niespójności w planie.
```

Gotowe, gdy: kontrola tabel przechodzi, a lista pytań jest u Ciebie.

---

## Sesja 1 — szkielet z AgriWatch

```text
Obok tego repozytorium jest sklonowane ../agriscreen. Przeczytaj w nim:
step_05_colab_run.py (setup_runtime, run_task, run_history, registry_read/upsert, REGISTRY_SCHEMA, _selftest),
build_colab_master.py i docs/ARCHITEKTURA.md.

Zadanie: przenieś mechanizm sterowania i rejestru do tego repozytorium.
- step_05_colab_run.py: setup_runtime, run_task, rejestr gwl_* (tylko tabele z docs/ARCHITEKTURA.md, sekcja 5),
  słownik CHECK_CONFIG zbudowany z data/00_Metadata/case_1_gnss_pto1.example.yaml i case_2_reper_hengelo.example.yaml
  (pola TODO zostają jako wymagane klucze bez wartości domyślnych), puste zadania task_* z docs/ARCHITEKTURA.md, sekcja 3,
  oraz --selftest, który uruchamia step_00 i sprawdza zapis/odczyt rejestru na katalogu tymczasowym.
- build_colab_master.py: generator notebooks/EGMS_Check.ipynb z komórkami dla zadań w kolejności z architektury.
- Nagłówki modułów w stylu AgriWatch ("EGMS Check - KROK N: ...").

Zanim zaczniesz, powiedz mi, które fragmenty step_05 z AgriWatch przenosisz bez zmian, które upraszczasz
i co pomijasz (GEE, GPU, SR). Części specyficznych dla AgriWatch nie kopiuj.
Na końcu: python step_05_colab_run.py --selftest oraz changelog.
```

Gotowe, gdy: `--selftest` przechodzi, a notatnik się generuje.

---

## Sesja 2 — dostęp do API EGMS

```text
Przeczytaj docs/evidence/F5_zrodla_danych.md, sekcja 1 ("Oficjalne API"), oraz oficjalny notatnik
https://github.com/copernicus-land/egms-api (EGMS-API.ipynb). Kod z F5 jest nietestowany.

Token CLMS API jest w pliku: <PODAJ ŚCIEŻKĘ POZA REPOZYTORIUM>. Nie kopiuj go, nie drukuj, nie zapisuj w logach.

Zadanie w step_01_ingest.py:
1. get_access_token(token_path) według oficjalnego notatnika.
2. Funkcja pobierająca listy: levels, releases, relative_orbits, directions, product_types.
3. search_egms(query) zwracająca hits i id; bez pobierania plików.

Uruchom i pokaż mi: listę wydań (czy jest 2018-2022, 2019-2023, 2020-2024 i w jakim zapisie),
listę poziomów i typów produktów. Zapisz odpowiedź w docs/plans/Plan_v1_otwarte_pytania.md (pytanie A2).
Jeśli wydania 2018-2022 nie ma, zatrzymaj się i zapytaj, co dalej.
```

Gotowe, gdy: znamy listę wydań i poprawny zapis filtrów.

---

## Sesja 3 — pobranie danych przypadku 1

```text
Przeczytaj docs/evidence/F2_przypadek_GNSS_PTO1.md i docs/plans/Plan_v1_dane_do_pobrania.md.
Plik data/02_Raw_Ground/1_gnss_pangaea/PTO1.txt jest na miejscu.

1. read_pangaea_gnss: wczytaj plik, pokaż nagłówek, zakres dat, liczbę dni, przerwy dłuższe niż 30 dni,
   współrzędne stacji. Nie koryguj niczego. Jeśli widzisz skok w szeregu, pokaż go i zapytaj.
2. Dla współrzędnych stacji wykonaj search_egms: poziom L2B, wydanie z sesji 2, osobno ścieżki 117, 44, 95.
   Pokaż dla każdej: nazwy plików, burstId, kierunek, rozmiar. Porównaj numery burstów ze "scenami"
   z data/04_Reference/fabris2026_tab1_insar_datasets.csv.
3. Podaj łączny rozmiar i poczekaj na moją zgodę. Dopiero potem sync_egms: pobranie do data/01_Raw_EGMS/,
   przyrostowo, z wpisem do data/00_Metadata/MANIFEST.csv (adres bez identyfikatora zapytania, data, SHA-256, wydanie).
4. Wpisz współrzędne stacji do CHECK_CONFIG ze wskazaniem źródła (plik PANGAEA).
```

Gotowe, gdy: pliki trzech ścieżek są pobrane i wpisane do manifestu.

---

## Sesja 4 — kontrole konwencji i wycinki

```text
Przeczytaj docs/evidence/F4_metodyka.md (sekcje 2 i 5) i Plan_v1_kryteria_akceptacji.md (sekcja A).

W step_02_checks_extract.py:
1. Wczytaj pliki L2B; rozdziel atrybuty punktów i szeregi czasowe. Sprawdź nazwy kolumn z F5.
2. Kontrole A1-A4 na punktach w promieniu 1 km od stacji; pokaż wyniki liczbowo. Jeśli któraś nie przechodzi,
   zatrzymaj się: konwencję trzeba ustalić w dokumentacji EGMS, nie zgadywać.
3. Duplikaty w zakładkach burstów: policz, ile par punktów leży bliżej niż 1 m; pokaż przykłady;
   zaproponuj regułę usuwania i zapytaj o zgodę.
4. Zapytaj mnie o: minimalną liczbę punktów w buforze, filtr wysokości, statystykę w buforze (średnia czy mediana).
5. Wycinki: punkty w promieniu 200 m od stacji (z odległością, żeby bufor 100 m dało się odtworzyć),
   dla trzech ścieżek, do data/03_Extracts/. Pliki mają być małe i czytelne bez surowych danych.
6. Porównaj liczbę punktów w buforze 200 m z artykułem (753 / 531 / 544) i incidence_angle z przedziałami
   z Plan_v1_kryteria_akceptacji.md. Różnice opisz, nie dopasowuj.
```

Gotowe, gdy: kontrole przechodzą, wycinki są w repozytorium, a różnice względem artykułu są opisane.

---

## Sesja 5 — porównanie z GNSS

```text
Progi w docs/plans/Plan_v1_kryteria_akceptacji.md są zatwierdzone (data w protokole w Plan_v1_test_EGMS.md).
Nie zmieniaj ich.

Zanim napiszesz kod, zapytaj mnie o: model prędkości (liniowy czy liniowy + sinusoida roczna),
agregację GNSS (średnia czy mediana miesięczna), datę odniesienia, wspólne okno.

W step_03_compare_gnss.py, dla każdej ścieżki i bufora 100 m oraz 200 m:
1. Szereg EGMS: statystyka przemieszczeń punktów w buforze dla każdej daty, z rozrzutem.
2. GNSS w LOS: Up * los_up (uzasadnienie w F2); agregacja; wspólne okno; pokrycie >= 85%.
3. Prędkości obu szeregów tym samym modelem; różnica v_GNSS,LOS - v_EGMS.
4. Różnica szeregów: odchylenie standardowe, korelacja.
5. Zapis do gwl_validation_metrics; tabela "artykuł kontra my" z data/04_Reference/fabris2026_*.csv.

Pokaż wynik dla ścieżki 117 jako pierwszy wykres (osie po angielsku) i tabelę kryteriów T1.
Wynik niezgodny z progiem raportuj tak samo jak zgodny; najpierw sprawdź znak, układ i okno.
```

Gotowe, gdy: jest tabela kryteriów T1 dla trzech ścieżek i wykres główny.

---

## Sesja 6 — wykresy, biuletyn, notatnik

```text
Przeczytaj docs/plans/Plan_v1_wpis_na_blog.md i docs/evidence/F2 (sekcja o wykresach).

1. step_06_figures_bulletin.py: wykres główny, wykres różnicy, trzy ścieżki obok siebie, mapa punktów wokół stacji;
   bulletin.md, egmscheck_latest.json, run_summary.md (wersje bibliotek, konfiguracja, wydanie EGMS, commit,
   wynik kontroli, wynik progów, błędy) w data/05_Final_Outputs/egmscheck/.
2. Uzupełnij build_colab_master.py i wygeneruj notatnik. Notatnik ma przejść od góry do dołu w dwóch trybach:
   z tokenem (pobiera) i bez tokenu (ingest_egms kończy się statusem "pominięte: brak tokenu" w gwl_runs,
   reszta czyta data/03_Extracts/). Sprawdź oba tryby.
3. Uzupełnij --selftest o przebieg na danych syntetycznych EGMS i prawdziwym pliku GNSS.
```

Gotowe, gdy: notatnik przechodzi bez tokenu na świeżym klonie repozytorium.

---

## Sesja 7 — szkic wpisu na blog (przypadek 1)

```text
Na podstawie notatnika i bulletin.md przygotuj szkic wpisu według docs/plans/Plan_v1_wpis_na_blog.md:
nagłówek (title, date, tags, summary, readTime), sekcje z tabeli "Proponowany układ wpisu" dla przypadku 1,
komórki kodu z notatnika, ryciny PNG, źródła i atrybucje.
Język tekstu: <POLSKI / ANGIELSKI>.

Trzymaj się sformułowań z CLAUDE.md ("pomiar naziemny potwierdza...", "osiadanie"). Każda liczba we wpisie
ma pochodzić z run_summary.md lub z tabel w data/04_Reference/, z podanym źródłem. Sekcja "Co się nie zgadza"
jest obowiązkowa. Zapisz szkic w docs/evidence/ jako plik Markdown; nie publikuj.
```

Gotowe, gdy: szkic przeczytałeś i poprawiłeś sam.

---

## Sesja 8 — tabela reperów z PDF (przypadek 2)

```text
Przeczytaj docs/evidence/F3_przypadek_repery_Hengelo.md. PDF raportu jest w docs/evidence/literatura_pdf/.

1. Znajdź w PDF załącznik 5 ("differentiestaat") i mapę (załącznik 1). Powiedz, na których stronach są
   i czy tabela ma warstwę tekstową, czy jest obrazem.
2. Odczytaj tabelę do data/02_Raw_Ground/2_levelling_hengelo/differentiestaat_2023.csv według szablonu
   data/00_Metadata/hengelo_differentiestaat.template.csv, z numerem strony w każdym wierszu.
   Wartości nieczytelne zostaw puste i wypisz osobno; nie zgaduj.
3. Ustal dokładne daty epok i rozstrzygnij, czy istnieje epoka z grudnia 2022 (pytanie A4).
4. Kontrole: różnice wyliczone z wysokości mają dać zakres od -42 do +2 mm względem 2020 i od -13 do +2 mm
   względem poprzedniej epoki; reper 7008 ma -42 i -13. Porównaj też z
   data/04_Reference/hengelo_strootbeekpark_2023_map_labels_UNVERIFIED.csv i wypisz rozbieżności.
5. Daj mi listę wierszy do ręcznego sprawdzenia w PDF. Dopiero po moim potwierdzeniu oznacz tabelę jako sprawdzoną.
```

Gotowe, gdy: tabela przechodzi kontrole i jest przez Ciebie potwierdzona.

---

## Sesja 9 — porównanie z niwelacją i test prognozy

```text
Przeczytaj docs/evidence/F4_metodyka.md, sekcja 10, i Plan_v1_kryteria_akceptacji.md, sekcja C.

Zanim zaczniesz, zapytaj mnie o: odniesienie (reper 000A2890 czy grupa stabilna), repery 300 i 301
(włączać czy nie), minimalną liczbę punktów EGMS przy reperze, sposób odczytu EGMS w dacie epoki.

1. Przelicz współrzędne reperów z RD (EPSG:28992) do EPSG:3035; sprawdź przeliczenie w obie strony.
2. search_egms dla prostokąta obejmującego repery: L3, ORTHO-UP, wydanie do nałożenia i wydanie 2018-2022.
   Podaj rozmiary i poczekaj na zgodę przed pobraniem.
3. Pokaż mapę: ile reperów ma komórkę L3 z danymi, czy ma ją reper odniesienia. Jeśli pokrycie jest
   za małe, zatrzymaj się i zaproponuj wariant L2B.
4. step_04_compare_levelling.py: szeregi względem odniesienia, odczyt w epokach, różnice wysokości
   EGMS kontra niwelacja; wykres rozrzutu z linią 1:1; szeregi dla reperów o największym osiadaniu i dla stabilnych.
5. Test prognozy: prędkość z wydania 2018-2022, prognoza na okno między epokami po końcu tych danych,
   porównanie z niwelacją. Dane uczące i sprawdzające nie mogą się nakładać; jeśli muszą, napisz to wprost.
6. Tabela kryteriów T2. Rozbieżność raportuj tak samo jak zgodność i podaj możliwe przyczyny z F3 (sekcja o ryzykach).
```

Gotowe, gdy: jest tabela kryteriów T2, wykres rozrzutu i wynik testu prognozy.

---

## Sesja 10 — domknięcie

```text
1. Zaktualizuj docs/ARCHITEKTURA.md tak, żeby opisywała stan faktyczny kodu (moduły, funkcje, zadania, rejestr),
   a nie plan. Usuń oznaczenia [plan] z README dla plików, które istnieją; dodaj odznakę "Open in Colab".
2. W docs/plans/ ustaw statusy: co wykonane, co odłożone. W Plan_v1_test_EGMS.md wypełnij regułę decyzji
   wynikami T1 i T2 (T3 tylko jeśli był liczony).
3. Uzupełnij wpis na blog o przypadek 2 albo przygotuj drugi wpis, według mojej decyzji.
4. Wypisz, co pozostaje niezweryfikowane (licencja danych NLOG, formuła atrybucji Copernicus, inne).
5. Uruchom --selftest i notatnik bez tokenu na świeżym klonie; podaj changelog całości.
```

Gotowe, gdy: świeży klon repozytorium odtwarza wykresy bez tokenu.
