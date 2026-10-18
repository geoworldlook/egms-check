# Plan v1 — kryteria akceptacji

Status: PROPOSED, 2026-10-09 — do zatwierdzenia przed pierwszym przebiegiem. Część planu `Plan_v1_walidacja_EGMS.md`.

Progi zapisuje się **przed** pierwszym przebiegiem. Po zobaczeniu wyników nie wolno ich zmieniać;
ewentualną zmianę zapisuje się tu z datą i uzasadnieniem.

Wiersze oznaczone **[propozycja]** to moje propozycje, nie wartości z literatury.
Autor zatwierdza je lub zmienia przed uruchomieniem.

## A. Kontrole poprawności danych (blokujące, oba przypadki)

| # | Kontrola | Próg | Źródło |
|---|---|---|---|
| A1 | Norma wektora LOS (L2a/L2b) | \|norma − 1\| ≤ 0,01 **[propozycja]** | definicja kosinusów kierunkowych |
| A2 | `los_up` względem `cos(incidence_angle)` | różnica ≤ 0,01 **[propozycja]** | geometria |
| A3 | Znak `los_east` przeciwny dla orbit | zawsze | geometria |
| A4 | Znak prędkości w znanej strefie osiadania | ujemny | Fabris i Nazari 2026; raport z Hengelo |
| A5 | Brak zdublowanych punktów po scaleniu burstów | 0 par bliżej niż 1 m **[propozycja]** | Hrysiewicz i in. 2024 |
| A6 | Pokrycie czasowe EGMS–dane naziemne | ≥ 85% | White Paper |
| A7 | Wpis w manifeście i suma kontrolna każdego pliku wejściowego | zawsze | odtwarzalność |

Niespełnienie którejkolwiek kontroli zatrzymuje przebieg.

## B. Przypadek 1 — GNSS (PTO1)

| Wielkość | Próg | Źródło |
|---|---|---|
| \|v_GNSS,LOS − v_EGMS\| na każdej ścieżce | ≤ 1,5 mm/rok | Fabris i Nazari 2026 (za Fiaschi i in. 2018) |
| Odchylenie standardowe różnicy szeregów (po agregacji GNSS) | ≤ 5 mm | Crosetto i in. 2025 (przegląd) |
| Zgodność między buforami 100 m i 200 m | różnica średnich prędkości ≤ 0,5 mm/rok **[propozycja]** | w tabeli 3 artykułu rozstęp między buforami nie przekracza 0,2 mm/rok |
| Zgodność między ścieżkami po przeliczeniu na pion | raportowana, bez progu | — |
| `incidence_angle` przy stacji | 39,9–42,8° (ścieżki 117, 95); 32,4–36,0° (ścieżka 44) | wyliczone z tabel artykułu (`step_00_reference_check.py`) |

Wartości z artykułu podajemy obok naszych w tabeli porównawczej. Nie są progiem: prędkość GNSS
w artykule pochodzi z kampanii, nasza z szeregu dobowego.

Kontrola opcjonalna, jeśli pobrane zostanie wydanie 2018–2022: liczba punktów w buforze 200 m
względem artykułu (753 / 531 / 544), tolerancja ±2% **[propozycja]**.

## C. Przypadek 2 — repery (Hengelo)

Wszystkie wielkości względem reperu odniesienia (lub zatwierdzonej grupy stabilnej).

| Wielkość | Próg | Źródło |
|---|---|---|
| Poziom 1: \|Δh_EGMS − Δh_niwelacja\| dla okna 12.2020–12.2023, mediana po reperach | ≤ 5 mm **[propozycja]** | Koudogbo 2025: MAE < 5 mm w Lotaryngii; Crosetto 2025: σ < 5 mm |
| Poziom 1: zgodność znaku dla reperów o osiadaniu ≥ 6 mm z niwelacji | ≥ 90% reperów **[propozycja]** | 6 mm to ok. 3× precyzja porównania |
| Poziom 1: nachylenie regresji EGMS względem niwelacji | raportowane z przedziałem ufności; oczekiwane bliskie 1 | — |
| Poziom 2: \|prognoza − pomiar\| dla okna 12.2022–12.2023, mediana | ≤ 3 mm **[propozycja]** | precyzja prędkości EGMS ok. 1 mm/rok + niwelacja 1–2 mm |
| Kontrola negatywna: repery stabilne (\|Δh\| ≤ 2 mm z niwelacji) | \|Δh_EGMS\| ≤ 5 mm **[propozycja]** | jw. |

Decyzje, które muszą zapaść przed przebiegiem, a nie po nim:
- czy repery 300 i 301 (niewyjaśniony wzrost wg raportu) wchodzą do statystyk,
- minimalna liczba punktów EGMS przy reperze,
- co jest odniesieniem, jeśli przy reperze 000A2890 nie ma punktów EGMS.

## D. Co musi być w prezentacji niezależnie od wyniku

1. Wszystkie ścieżki i bufory (przypadek 1) oraz wszystkie repery (przypadek 2), także te, które wypadły gorzej.
2. Progi i data ich zatwierdzenia.
3. Lista rozbieżności z prawdopodobną przyczyną.
4. Znane granice metody (`docs/evidence/F4_metodyka.md`, sekcja 11).
5. Źródła danych, licencje, wydania EGMS.
6. Zdanie o zakresie: wynik nie rozstrzyga o pokryciu nad konkretnym obiektem ani o zdarzeniach nagłych.
