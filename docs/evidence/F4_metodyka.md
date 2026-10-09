# F4 — Metodyka

> **Data:** 2026-10-09 · **Status:** `Draft`
> **Powiązane:** `docs/evidence/F1_przeglad_literatury_EGMS.md`, `docs/plans/Plan_v1_kryteria_akceptacji.md`

Wszystkie wzory i konwencje potrzebne w pipeline. Przy każdym podane jest źródło i status.

## 1. Produkty EGMS i który do czego

| Produkt | Co zawiera | Układ | Użycie w walidacji |
|---|---|---|---|
| Basic (L2a) | LOS, względem wirtualnego punktu odniesienia | lokalny | ocena dokładności InSAR; tylko w różnicach między stacjami |
| Calibrated (L2b) | LOS, dowiązany do modelu GNSS (A-EPND, siatka 50 km) | ETRF2000 | prędkości bezwzględne; test tego, co widzi użytkownik |
| Ortho (L3) | pion i E-W, siatka 100 m | ETRF2000 | porównanie z niwelacją; pomocniczo |

Model GNSS powstał z ok. 3770 stacji, głównie z sieci zagęszczającej EUREF. Stacja EPN w buforze
nie jest więc w pełni niezależna od L2b i L3. White Paper dopuszcza takie stacje do walidacji;
my dodatkowo wykonujemy test na L2a.

## 2. Konwencje do sprawdzenia na danych (testy obowiązkowe)

Status: **niezweryfikowane w dokumentacji**, dlatego sprawdzamy na danych przed jakimkolwiek porównaniem.

1. `los_east² + los_north² + los_up² ≈ 1`.
2. `los_up > 0` oraz `los_up ≈ cos(incidence_angle)` (tolerancja do ustalenia, np. 0,01).
3. Znak `los_east` jest przeciwny dla orbity wstępującej i zstępującej.
4. W znanym obszarze osiadania `mean_velocity < 0` na obu orbitach (ujemny = oddalanie od satelity).
   Fabris i Nazari stosują tę konwencję: wartości ujemne oznaczają osiadanie.
5. Kolumny dat mają format `yyyymmdd`, przemieszczenia są w mm.

Jeśli którykolwiek test nie przechodzi, zatrzymaj się i ustal konwencję w Product User Manual.

## 3. Rzut GNSS na LOS

**Pełny (domyślny, obowiązkowy w Lorce):**

```
d_LOS = E · los_east + N · los_north + U · los_up
```

E, N, U w mm; kosinusy kierunkowe z punktu EGMS najbliższego stacji (lub średnia z bufora).
Źródło: Even i in. 2024 (wektor LOS dostarczony z punktem); Koudogbo 2025, krok 3.

**Uproszczony (tylko gdy ruch poziomy jest pomijalny, jak w delcie Padu):**

```
V_LOS = V_V · cos θ
```

θ = `incidence_angle` najbliższego punktu. Źródło: Fabris i Nazari 2026, wzór 1.

Kierunek jest zawsze GNSS → LOS. Z jednej liczby w LOS nie da się odtworzyć trzech składowych.

**Wrażliwość Sentinel-1 (orientacyjnie, dla kątów padania ok. 29–46°):** pion ok. 0,7–0,9;
wschód ok. 0,5–0,7 ze znakiem zależnym od orbity; północ ok. 0,1. Ruch N-S jest prawie niewidoczny.

## 4. Dekompozycja dwóch orbit (tylko do zrozumienia produktu L3)

Fernández i in. 2018, wzór 1: pion i E-W wyznacza się z LOS wstępującego i zstępującego,
z kątami padania θ i kierunkami lotu α dla obu orbit, zaniedbując N-S. Wymaga interpolacji,
bo punkty obu orbit się nie pokrywają. Dokładny zapis macierzy: PDF, str. 5
(w ekstrakcie tekstowym wzór jest zniekształcony). W pipeline tego nie liczymy; korzystamy z L3.

## 5. Dopasowanie przestrzenne

| Podejście | Parametry | Źródło |
|---|---|---|
| Bufor wokół stacji | 100 m + kryterium wysokości; min. 3 punkty | Koudogbo 2025 |
| Bufory wielokrotne | 50, 100, 150, 200 m; oraz 1, 2, 3 najbliższe punkty | Fabris i Nazari 2026 |
| Wspólna komórka siatki | 50 m (LOS) lub komórka produktu (100 m dla L3) | Even i in. 2024 |
| Bufor 300 m, mediana | — | Naumowicz i Kowalczyk (tylko streszczenie) |

Zasady:
- odległości licz w EPSG:3035 (kolumny `easting`, `northing`), nie w stopniach,
- raportuj wyniki dla wszystkich buforów jednocześnie, jako test wrażliwości,
- pusty bufor lub mniej punktów niż minimum to `NaN` z powodem, nie zero,
- usuń zdublowane punkty z zakładek burstów przed liczeniem statystyk,
- kryterium wysokości odsiewa punkty na dachach i masztach; próg wymaga decyzji autora.

## 6. Dopasowanie czasowe

1. Przytnij oba szeregi do wspólnego okna; wymagaj co najmniej 85% pokrycia (White Paper).
2. Interpoluj GNSS do dat akwizycji EGMS. Warianty z literatury: okno 12 dni (Koudogbo);
   interpolacja kształtozachowawcza kawałkami sześcienna (Even). Wybór wymaga decyzji.
3. Ustal wspólną datę odniesienia i wyzeruj na niej oba szeregi.
4. Nie interpoluj przez przerwy w danych GNSS dłuższe niż okno; zostaw `NaN`.
5. Skoki w szeregach GNSS (wymiana anteny) koryguj tylko na podstawie dziennika stacji.

Even i in. dodatkowo wygładzają szereg InSAR regresją RLOESS w oknie 7 punktów, żeby szum
własny InSAR nie zdominował statystyk. Jeśli to stosujesz, raportuj wynik z wygładzaniem i bez.

## 7. Odniesienie i układy

**L2a — podwójne różnice:**

```
DD(t) = [EGMS_A(t) − EGMS_ref(t)] − [GNSS_A,LOS(t) − GNSS_ref,LOS(t)]
```

Usuwa wirtualny punkt odniesienia EGMS i wspólne błędy układu GNSS. Stację referencyjną
wybiera się w strefie stabilnej (CARG w Lorce, MAS1 na Gran Canarii, FYHA w Jutlandii).

**L2b i L3 — różnice pojedyncze:** EGMS jest w ETRF2000. Rozwiązanie GNSS w innym układzie
(ITRF2014, IGS14, IGS20, ETRF2014) ma inne prędkości, zwłaszcza poziome. Dwie drogi:
- przeliczyć prędkości GNSS do układu EGMS (jak Koudogbo: odjąć różnicę względem modelu A-EPND),
- albo pracować w różnicach między stacjami i podawać to wprost.

Thiéblemont i in. 2024 pokazują, że wybór układu zmienia prędkości pionowe na poziomie
ułamków mm/rok. Przy progu 1,5 mm/rok to nie jest pomijalne.

## 8. Prędkość

- Atrybut `mean_velocity` EGMS pochodzi z modelu „wielomian 1. stopnia + składowa sezonowa"
  dla całego wydania.
- Przy oknie węższym niż wydanie prędkość trzeba policzyć z szeregu tym samym modelem
  (trend liniowy + sinusoida roczna) i opisać to w raporcie.
- Dla GNSS stosuj ten sam model w tym samym oknie.
- Niepewność prędkości GNSS z prostej regresji jest zaniżona (szum skorelowany). Sposób
  szacowania wymaga decyzji autora; kandydaci: MIDAS, modele szumu potęgowego (HECTOR).

## 9. Metryki

Konwencja znaku różnicy jak w Fabris i Nazari: **Δv = v_GNSS,LOS − v_EGMS**.

Prędkości (na stację, ścieżkę, bufor; potem zbiorczo):
- Δv, bias = średnia i mediana Δv,
- rozrzut = odchylenie standardowe oraz MAD × 1,4826,
- odsetek |Δv| ≤ próg.

Szeregi czasowe (po odjęciu średniego przesunięcia, bo zbiory mają różne odniesienia):
- odchylenie standardowe różnic σ_P w punkcie P,
- łączne `σ = sqrt( Σ_P (N_P − 1) · σ_P² / (N − 1) )`, N = Σ N_P (Even i in. 2024, wzór 1),
- korelacja szeregów; osobno po odjęciu trendu (sezonowość),
- RMS różnic.

White Paper wymaga czterech wskaźników zbiorczych: dokładność i precyzja prędkości (mm/rok)
oraz dokładność i precyzja szeregów (mm). Przyjmij: dokładność = bias, precyzja = rozrzut.

## 10. Porównanie z niwelacją (przypadek 2)

Niwelacja daje różnice wysokości względem reperu odniesienia, w pionie. Żeby porównanie było
uczciwe, EGMS trzeba sprowadzić do tego samego kierunku i tego samego odniesienia.

**Kierunek.** Produkt Ortho (L3) podaje pion wprost. Z L2b pionu z jednej orbity nie da się odtworzyć
bez założenia o ruchu poziomym; w niecce osiadania ruch poziomy ku środkowi istnieje
(w Lorce do 28% pionu, Fernández i in. 2018). Dlatego L3 jest produktem głównym, a L2b pomocniczym.

**Odniesienie.**

```
d_rel(t) = d_P(t) − d_ref(t)
```

`d_P` to szereg EGMS przy reperze P, `d_ref` przy reperze odniesienia. Tak samo postępują
Even i in. 2024: średnia różnica między zbiorami nie ma znaczenia, bo mają różne odniesienia.

**Porównywana wielkość.** Dla epok t1 < t2:

```
Δh_EGMS = d_rel(t2) − d_rel(t1)        Δh_niw = H_P(t2) − H_P(t1)   (wysokości już względem odniesienia)
```

**Odczyt EGMS w dacie epoki.** Kampania niwelacyjna trwa dni lub tygodnie, akwizycje są co 6–12 dni.
Sposób odczytu (interpolacja liniowa między sąsiednimi akwizycjami, średnia z okna, wartość z dopasowanego
modelu) wymaga decyzji autora. Even i in. wygładzają szereg InSAR (RLOESS, okno 7 punktów),
a potem interpolują kształtozachowawczo do epok niwelacji.

**Dopasowanie przestrzenne.** L3: komórka 100 m zawierająca reper. L2b: punkty w promieniu 50–100 m.
Even i in. łączyli repery z punktami w tej samej komórce siatki 50 m.

**Test prognozy.** Prędkość względną `v_rel` liczy się wyłącznie z danych sprzed epoki t1,
a potem porównuje `v_rel · (t2 − t1)` z `Δh_niw`. Dane uczące i sprawdzające nie mogą się nakładać;
jeśli się nakładają, trzeba to napisać.

**Budżet niepewności (orientacyjnie).** Niwelacja 1,1 mm/√km w raporcie z Hengelo, czyli ok. 1–2 mm
na różnicę wysokości w sieci o długości ok. 20 km. Szereg EGMS: rozrzut pojedynczego punktu rzędu
kilku mm; średnia z wielu punktów mniej. Repery o zmianie poniżej kilku mm nie rozstrzygają o zgodności.

## 11. Znane granice metody (do raportu)

| Granica | Przykład | Źródło |
|---|---|---|
| Ruch nieliniowy, silne gradienty | kawerny Epe, erupcja La Palma, piezometr H-3 w Turowie | Even 2024; Koudogbo 2025 |
| Ruch N-S | osuwisko Navis | Koudogbo 2025 |
| Sezonowość wygładzana przez uśrednianie w buforze | Jutlandia, Gran Canaria | Koudogbo 2025 |
| Mała gęstość punktów w roślinności | punkty kampanijne w delcie Padu, La Palma | Fabris 2026; Koudogbo 2025 |
| Produkt L3: siatka 100 m, uśrednianie | słabsza zgodność pionu | Koudogbo 2025; Even 2024 |
| Zdarzenia bardzo szybkie | zapadliska, obrywy | White Paper |
