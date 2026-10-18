# F3 — Przypadek 2: osiadanie z reperów (Hengelo, pole solne Twenthe-Rijn)

> **Data:** 2026-10-09 · **Status:** `Draft` — tabela reperów (załącznik 5) nieodczytana
> **Powiązane:** `docs/plans/Plan_v1_test_EGMS.md` (T2), `docs/plans/Plan_v1_dane_do_pobrania.md`

**Cel:** pokazać, że obniżenie reperów zmierzone niwelacją precyzyjną zgadza się z osiadaniem
widocznym w EGMS, w tym z prognozą zrobioną z danych sprzed pomiaru.

**Teza do obrony:** tam, gdzie EGMS pokazuje osiadanie, późniejsza niwelacja urzędowo
raportowana potwierdza jego wielkość i zasięg.

## Źródło danych terenowych

| Element | Wartość | Status |
|---|---|---|
| Dokument | „Meetregister bij het meetplan Twenthe-Rijn. Rapportage van de nauwkeurigheidswaterpassing Strootbeekpark 2023" | zweryfikowane |
| Wykonawca | Antea Group, nr projektu 0487387.100, rewizja 00 z 24.04.2024 | zweryfikowane |
| Zleceniodawca | Nobian, Hengelo | zweryfikowane |
| Publikacja | portal NLOG, strona „Meetplannen en Meetregisters"; pobranie bezpośrednie, bezpłatne | zweryfikowane |
| Podstawa | obowiązek pomiarów ruchu terenu przy działalności górniczej; rejestry trafiają do nadzoru SodM | zweryfikowane na stronie NLOG |
| Adres | https://www.nlog.nl/sites/default/files/2025-10/20240327_487387_meetregister_strootbeekpark_jaarlijks_2023_00.pdf | zweryfikowane |

NLOG to holenderski portal informacji o podziemiu; według mojej wiedzy prowadzi go służba
geologiczna TNO na zlecenie ministerstwa. Potwierdź sformułowanie przed slajdem.

## Co zmierzono

- Sieć: 50 reperów (45 własnych i 5 państwowych NAP), ok. 10 zamkniętych pętli, ok. 20 km.
- Metoda: niwelacja precyzyjna, odchylenie 1,1 mm/√km, tolerancja zamknięć 3 mm/√km.
- Reper odniesienia: podziemny 000A2890, +19,388 m NAP, przyjęty jako stabilny.
- Epoki: grudzień 2020 (pomiar zerowy), czerwiec 2022, grudzień 2023 – styczeń 2024.
  Legenda mapy odwołuje się też do „grudnia 2022", a nazwa pliku mówi o pomiarze corocznym,
  więc najpewniej istnieje czwarta epoka (12.2022). **Do potwierdzenia w PDF.**
- Wynik: różnice względem 2020 r. od −42 do +2 mm; względem poprzedniej epoki od −13 do +2 mm.
- Największe osiadanie: rejon „Steenzoutweg – Zoutwinningsweg", reper 7008 (−42 mm; −13 mm od poprzedniej epoki).
- Cel sieci według raportu: śledzenie osiadania i **spadku jego tempa**. Ruch może więc nie być liniowy.
- Repery 300 i 301 wykazują niewyjaśniony wzrost (+11 i +14 mm); raport to odnotowuje.

Przeliczenie własne, nie z raportu: −42 mm w 3 lata to ok. 14 mm/rok na reperze 7008.

Wysokości reperów w każdej epoce oraz ich współrzędne są w załączniku 5 („differentiestaat").
Tego załącznika nie udało mi się odczytać maszynowo.

## Dane w folderze

- `data/04_Reference/hengelo_strootbeekpark_report_facts.csv` — fakty z tekstu raportu.
- `data/04_Reference/hengelo_strootbeekpark_2023_map_labels_UNVERIFIED.csv` — różnice dla ok. 45 reperów
  odczytane maszynowo z warstwy tekstowej mapy (załącznik 1). **Niezweryfikowane:** pary
  reper–wartość mogły zostać pomylone. Zgadzają się z tekstem tylko skrajne wartości.
  Traktuj plik jako podgląd; do obliczeń przepisz załącznik 5 z PDF.

## Pierwszy krok (blokujący)

Otwórz PDF i przepisz załącznik 5 do `data/02_Raw_Ground/2_levelling_hengelo/differentiestaat_2023.csv`:
numer reperu, X i Y (układ RD, EPSG:28992), wysokość NAP w każdej epoce. Zapisz dokładne daty epok.
To ok. 50 wierszy. Drugi sprawdzian: porównaj z etykietami na mapie.

## Dane EGMS

| Element | Wybór | Uzasadnienie |
|---|---|---|
| Produkt główny | Ortho (L3), składowa pionowa | niwelacja mierzy pion; brak założeń o ruchu poziomym |
| Produkt pomocniczy | Calibrated (L2b), obie orbity | gęstsze punkty (L3 to siatka 100 m i uśrednia lokalną nieckę) |
| Wydanie do nałożenia szeregów | 2019–2023 | obejmuje epoki 12.2020, 06.2022, 12.2022; ostatnia epoka (12.2023–01.2024) jest na samym końcu |
| Wydanie do prognozy | 2018–2022 | kończy się przed ostatnią epoką niwelacji |
| Wydanie 2020–2024 | jeśli jest dostępne, lepsze do nałożenia | obejmuje wszystkie epoki z zapasem |

Gęstości punktów EGMS w tym rejonie nie sprawdzałem. Teren przemysłowy sprzyja, ale to trzeba zobaczyć.

## Metoda

Niwelacja daje różnice wysokości względem reperu 000A2890. EGMS trzeba sprowadzić do tego samego odniesienia.

1. Dla każdego reperu wybierz komórkę L3 zawierającą reper (lub punkty L2b w promieniu 50–100 m).
2. Szereg EGMS przy reperze minus szereg EGMS przy reperze odniesienia: `d_rel(t) = d_P(t) − d_A2890(t)`.
3. Odczytaj `d_rel` w datach epok niwelacji (interpolacja między sąsiednimi akwizycjami).
4. Porównaj `Δd_rel` między epokami z różnicą wysokości z niwelacji.

**Poziom 1 — nałożenie:** szereg EGMS i punkty niwelacji na jednym wykresie, wyzerowane w epoce 12.2020.

**Poziom 2 — prognoza i potwierdzenie:**
1. Z wydania 2018–2022 policz prędkość względną każdego reperu (dane tylko do 12.2022).
2. Prognoza obniżenia między epoką 12.2022 a 12.2023: `v_rel × Δt`.
3. Porównaj z różnicą z niwelacji (kolumna „względem poprzedniej epoki": od −13 do +2 mm).

Jeśli epoka 12.2022 nie istnieje, prognozuj od 06.2022 i zaznacz, że pół roku okna leży w danych uczących.

Dla L2b: z jednej orbity pionu nie da się odtworzyć bez założenia. W niecce osiadania występuje ruch
poziomy ku środkowi, więc przelicz pion z obu orbit albo pokaż obie orbity osobno w LOS i opisz ograniczenie.

## Wykresy do prezentacji i wpisu

1. **Szeregi dla 3–4 reperów o największym osiadaniu** (np. 7008, 7009, 5410): linia EGMS i punkty niwelacji.
2. **To samo dla 2–3 reperów stabilnych** (np. 7006, 7007): kontrola negatywna.
3. **Wykres rozrzutu:** obniżenie z niwelacji kontra z EGMS dla wszystkich reperów, z linią 1:1.
4. **Mapa:** prędkość EGMS w tle, repery pokolorowane wynikiem niwelacji.
5. **Prognoza kontra pomiar** dla okna 12.2022–12.2023.

## Ryzyka

- **Ruch nieliniowy.** Nad kawernami w Epe EGMS zawiódł (Even i in. 2024). Tu raport sam mówi o zmianie tempa.
  Rozbieżność jest możliwym wynikiem i trzeba go pokazać tak samo jak zgodność.
- **Silny gradient.** Niecka jest lokalna; komórka 100 m może uśrednić maksimum. Dlatego wariant L2b.
- **Stabilność odniesienia.** Jeśli przy reperze 000A2890 nie ma punktów EGMS, potrzebna jest grupa
  reperów stabilnych jako odniesienie zastępcze; decyzja autora.
- **Repery a punkty radarowe.** Reper to znak w gruncie lub na budowli, punkt EGMS to zwykle dach lub
  konstrukcja. Osiadanie własne budynku może różnić się od osiadania gruntu.
- **Mała liczba epok.** Trzy lub cztery epoki; porównujemy różnice wysokości, nie gęsty szereg.
- **Precyzja.** Niwelacja ok. 1–2 mm; prędkość EGMS ok. 1 mm/rok. Repery o zmianie poniżej kilku mm
  nie rozstrzygają niczego; wynik niosą repery o osiadaniu od kilku do kilkudziesięciu mm.

## Kontrola negatywna poza Hengelo (opcjonalnie)

Rejestr NAM dla Schiermonnikoog: 59 reperów, epoki co 3 lata 2006–2024, wysokości w załączniku CSV,
brak istotnego ruchu. Adres: https://www.nlog.nl/sites/default/files/2025-10/meetregister_schiermonnikoog_2024.pdf
