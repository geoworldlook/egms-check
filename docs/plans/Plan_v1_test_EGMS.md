# Plan v1 — test: czy możemy użyć EGMS

Status: PROPOSED, 2026-10-09. Część planu `Plan_v1_walidacja_EGMS.md`.

## Zasada

Test, który z góry ma „potwierdzić", nie jest testem. Ten plan jest ułożony tak, żeby wynik mógł
wyjść na tak albo na nie, a reguła decyzji była zapisana przed obliczeniami. Tylko wtedy wynik
pozytywny coś znaczy i da się go obronić przed ekspertami.

## Co dokładnie sprawdzamy

„Możemy użyć EGMS" rozbijamy na trzy twierdzenia. Każde ma osobny test.

| # | Twierdzenie | Test | Dane naziemne |
|---|---|---|---|
| T1 | EGMS podaje to samo tempo osiadania co stacja GNSS | przypadek 1 (`docs/evidence/F2`) | szereg dobowy PTO1, PANGAEA |
| T2 | EGMS podaje tę samą wielkość osiadania co niwelacja, także w prognozie na okres po danych | przypadek 2 (`docs/evidence/F3`) | repery Hengelo, NLOG |
| T3 | Nad wybranym obiektem jest dość punktów EGMS, żeby pomiar miał sens | kontrola pokrycia (niżej), opcjonalna | geometria obiektu lub sieci z danych otwartych |

T1 i T2 mówią o dokładności tam, gdzie punkty są. T3 mówi, czy nad danym obiektem w ogóle są.
Bez T3 uczciwy wniosek brzmi „EGMS mierzy poprawnie", a nie „możemy go użyć".

## Zakres stosowania, którego dotyczy wynik

Wynik pozytywny uprawnia do stwierdzenia: EGMS nadaje się do śledzenia **powolnego osiadania
terenu i obiektów** (rzędu milimetrów do kilku centymetrów na rok), w miejscach z punktami pomiarowymi.

Wynik niczego nie mówi o:
- zdarzeniach nagłych (zapadnięcie, awaria); EGMS jest aktualizowany raz w roku,
- ruchu w kierunku północ–południe,
- ruchu silnie nieliniowym lub o dużym gradiencie na krótkim dystansie,
- terenach bez trwałych odbić radarowych (roślinność, pola).

## Przed obliczeniami (zamrożenie)

1. Autor zatwierdza progi z `docs/plans/Plan_v1_kryteria_akceptacji.md` i decyzje z `Plan_v1_otwarte_pytania`, sekcja D.
   Data zapisana w tym pliku, w sekcji „Protokół".
2. Lista reperów, ścieżek i buforów jest ustalona z góry. Niczego nie usuwamy po zobaczeniu wyniku.
3. Konfiguracje `data/00_Metadata/case_*.example.yaml` trafiają do repozytorium przed pierwszym przebiegiem.
4. Bramki wykonalności z `Plan_v1_otwarte_pytania`, sekcja A, są sprawdzone. Jeśli któraś nie przechodzi,
   test się nie odbywa w tej postaci i zapisujemy dlaczego.

## Test T1 — GNSS

Wielkości i progi (z `Plan_v1_kryteria_akceptacji`, sekcja B):

| Kryterium | Próg | Zalicza |
|---|---|---|
| \|v_GNSS,LOS − v_EGMS\| | ≤ 1,5 mm/rok | na każdej z trzech ścieżek |
| Odchylenie różnicy szeregów | ≤ 5 mm | na każdej z trzech ścieżek |
| Bufor 100 m kontra 200 m | różnica ≤ 0,5 mm/rok **[propozycja]** | na każdej ścieżce |

Wynik T1: **zaliczony**, gdy wszystkie trzy ścieżki spełniają dwa pierwsze kryteria.
**Częściowy**, gdy spełniają je dwie z trzech. **Niezaliczony** w pozostałych przypadkach.

## Test T2 — repery

Wszystko względem reperu odniesienia. Progi z `Plan_v1_kryteria_akceptacji`, sekcja C.

| Kryterium | Próg | Uwagi |
|---|---|---|
| Mediana \|Δh_EGMS − Δh_niw\|, okno 12.2020–12.2023 | ≤ 5 mm **[propozycja]** | wszystkie repery z punktami EGMS |
| Zgodność znaku dla reperów o osiadaniu ≥ 6 mm | ≥ 90% **[propozycja]** | repery niosące sygnał |
| Prognoza kontra pomiar, okno po końcu danych EGMS | mediana błędu ≤ 3 mm **[propozycja]** | wydanie 2018–2022 jako dane uczące |
| Kontrola negatywna: repery stabilne | \|Δh_EGMS\| ≤ 5 mm **[propozycja]** | EGMS nie „widzi" ruchu, którego nie ma |

Wynik T2: **zaliczony**, gdy spełnione są wszystkie cztery. **Częściowy**, gdy zgodne są nałożenie
i kontrola negatywna, a prognoza nie. **Niezaliczony**, gdy nie przechodzi pierwsze lub czwarte kryterium.

## Test T3 — pokrycie nad wybranym obiektem (opcjonalny)

Metoda wzięta z Even i in. 2024 (rozdz. 4.1.2), gdzie liczono pokrycie dróg i torów:

1. Geometrię sieci lub obiektu podziel na odcinki (w artykule 25, 50 i 100 m).
2. Dla każdego odcinka sprawdź, czy w odległości prostopadłej do 10 m jest punkt EGMS.
3. Policz odsetek odcinków z punktem, osobno dla produktu L2b (obie orbity) i L3.
4. Dodatkowo: liczba punktów na obiekt kubaturowy i ich `rmse` oraz `temporal_coherence`.

W artykule pokrycie w LOS było kilkukrotnie wyższe niż w produkcie pionowym, więc licz oba.

Próg zaliczenia wymaga decyzji autora, najlepiej po konsultacji z osobą z branży **[do decyzji]**: jaki odsetek
długości sieci lub ile punktów na obiekt uznajemy za wystarczające. Ja tej wartości nie znam.

T3 da się wykonać w kilka godzin na jednym obszarze pilotażowym i nie wymaga danych naziemnych.

## Reguła decyzji

| T1 | T2 | T3 | Wniosek |
|---|---|---|---|
| zaliczony | zaliczony | zaliczony | możemy użyć EGMS do śledzenia powolnego osiadania nad tym obiektem |
| zaliczony | zaliczony | niezaliczony | EGMS mierzy poprawnie, ale nad tym obiektem jest za mało punktów; rozważyć reflektory lub inne dane |
| zaliczony | częściowy | dowolny | użyteczny do oceny stanu i trendu; prognozy z EGMS traktować ostrożnie |
| zaliczony | niezaliczony | dowolny | zgodny ze stacją GNSS, niezgodny z niwelacją; wyjaśnić przyczynę (nieliniowość, gradient, repery na budowlach) przed użyciem |
| niezaliczony | dowolny | dowolny | zatrzymać się; najpierw błąd pipeline'u lub danych, dopiero potem wniosek o EGMS |

Wynik niezaliczony w T1 przy trzech ścieżkach i jednej stacji najczęściej oznacza błąd po naszej
stronie (znak, układ, okno), bo oficjalna walidacja EEA na wielu stacjach daje różnice ok. 1 mm/rok.
Dlatego w tym wierszu najpierw szukamy błędu.

Bez T3 wniosek kończy się na „EGMS mierzy poprawnie w dwóch sprawdzonych miejscach".

## Siła dowodu — co powiedzieć wprost

- T1 to jedna stacja i trzy ścieżki. T2 to jedna sieć ok. 50 reperów. To sprawdzenie, a nie dowód statystyczny.
- Szerokość dowodu daje literatura: oficjalna walidacja EEA w kilkunastu miejscach Europy i prace niezależne.
  Nasze testy pokazują, że **nasz pipeline** odtwarza ten poziom zgodności na danych, które każdy może pobrać.
- Produkt Calibrated jest dowiązany do modelu GNSS w skali 50 km. Sygnał lokalny pochodzi z radaru.
- Dla T2 nie ma wcześniejszej publikacji porównującej te repery z EGMS. To nasz własny wynik.

## Kolejność i nakład (szacunek)

| Krok | Co | Nakład |
|---|---|---|
| 1 | Bramki wykonalności (`Plan_v1_otwarte_pytania`, sekcja A) | 1–2 godziny |
| 2 | Zamrożenie progów i decyzji | ok. godziny |
| 3 | T1 | ok. 1 dnia |
| 4 | T2, w tym przepisanie tabeli reperów | 1–2 dni |
| 5 | T3 na obszarze pilotażowym | kilka godzin |
| 6 | Raport z regułą decyzji | pół dnia |

Szacunki zakładają, że dane da się pobrać bez przeszkód; to moje przybliżenie, nie pomiar.

## Protokół (wypełnia autor)

| Pozycja | Wartość |
|---|---|
| Data zatwierdzenia progów | |
| Zmiany względem `Plan_v1_kryteria_akceptacji` | |
| Próg T3 i jego uzasadnienie | |
| Commit repozytorium w chwili zamrożenia | |
