# Plan v2 — pokaz EGMS (Groningen, zachodnia NRW) i droga do monitoringu co 6/12 dni

> **Status:** PROPOSED, 2026-10-11. Decyzje w sekcji 7 czekają na autora; bez nich nie ma kodu ani pobierania.
> **Powiązane:** `docs/migracja/09_audyt_po_migracji.md` (wynik E1), `docs/evidence/F8_przeglad_przypadkow.md`,
> `docs/evidence/F6_przypadki_zapasowe/zapas_nrw_niwelacja.md`.

## 1. Cel i pytanie

1. **Etap A (teraz): prosty skrypt, który pokazuje EGMS** dla dwóch regionów: Groningen (wydobycie gazu)
   i zachodnia NRW (odkrywki węgla brunatnego, wypiętrzanie po zatopieniu kopalń). Mapa prędkości + szeregi
   czasowe w wybranych punktach + porównanie z pomiarem naziemnym tam, gdzie jest.
2. **Etap B (później, ręcznie): własne przetworzenie Sentinel-1** dla okresu **po** końcu wydania EGMS,
   z próbkowaniem co 6/12 dni, żeby pokazać, że **monitoring** (nowe dane co kilka dni, nie raz w roku) zadziałałby.

Pytanie etapu B, które ma odpowiedź liczbową:
> Po jakim czasie od nowych akwizycji Sentinel-1 osiadanie o tempie 2–7 mm/rok jest widoczne ponad szumem
> i zgodne z GNSS?

## 2. Fakty, na których opiera się plan

| Fakt | Konsekwencja | Weryfikacja |
|---|---|---|
| EGMS L2a/L2b mają szeregi w **natywnych datach akwizycji**: co 6 dni (Sentinel-1A + 1B) do 23.12.2021, potem co 12 dni (sama 1A). | Próbkowanie 6/12 dni **już jest** w EGMS dla okresu archiwalnego. Etap A może je pokazać bez własnego przetwarzania. | E1 Groningen: 220–239 dat na parę w wydaniu 2019–2023 — zgodne z 6 dni × 3 lata + 12 dni × 2 lata. Data końca 1B: wiedza ogólna, potwierdzić. |
| EGMS to produkt **archiwalny**, aktualizowany raz w roku (okno 5 lat). | Monitoringu bieżącego EGMS nie daje — to jest powód etapu B. | `CLAUDE.md`, White Paper. |
| API zwraca wydania **2019–2023 i 2020–2024**. | Etap A: wydanie 2020–2024 (najnowsze). Etap B zaczyna się po 31.12.2024. | prawdziwe zapytanie, 2026-10-10. |
| Sentinel-1C działa od 2025 r. | W 2025–2026 w Europie znów może być 6 dni (1A + 1C). | **niezweryfikowane** dla tych ścieżek — sprawdzić listę akwizycji w CDSE. |
| Rozrzut szeregu EGMS względem GNSS ≈ 4,7 mm (E1, K2). | Pojedyncza akwizycja nie pokaże osiadania 3 mm/rok; widać je dopiero po wielu miesiącach. Monitoring wykrywa **trend i jego zmianę**, nie skok co 12 dni. | E1, wynik z 2026-10-10. |

Rachunek orientacyjny (szum biały, 4,7 mm na akwizycję, co 12 dni): niepewność prędkości ≈ 3,0 mm/rok po
roku i ≈ 1,0 mm/rok po dwóch latach (sam trend; z sinusoidą roczną więcej); co 6 dni ≈ 2,1 i 0,7 mm/rok. Szum atmosferyczny jest skorelowany,
więc w praktyce dłużej. To trzeba pokazać na danych (wykres 4), nie na wzorze.

## 3. Etap A — prosty skrypt `step_06_show_egms.py`

Jeden skrypt, dwie konfiguracje (`CHECK_CONFIG['show']['groningen']`, `...['nrw_west']`), uruchamiany z notatnika
lub z linii poleceń. Wykorzystuje istniejący kod: `step_01_ingest` (API, pobranie, manifest), `step_02_checks_extract`
(wycinek, kontrole A1–A5), `step_03_compare_gnss` (`fit_velocity`, `gnss_at_dates`).

### 3.1 Dane

| | Groningen | Zachodnia NRW |
|---|---|---|
| Przyczyna | wydobycie gazu | obniżanie wód przy odkrywkach; wypiętrzanie po zatopieniu kopalń |
| Mapa | EGMS L3 Ortho, pion (siatka 100 m), wydanie 2020–2024 | to samo |
| Szeregi | EGMS L2b w promieniu 100 m od punktów (jak E1) | EGMS L2b lub L3 pion w punktach |
| Pomiar naziemny | GNSS NGL (dobowy) — te same stacje co E1 | do ustalenia: GNSS NGL (reguła E1 na obszarze NRW), niwelacja `hfp_plzf.csv` |
| Obszar | prostokąt E1: 5,8–7,3° E, 52,9–53,6° N | **do decyzji** (sekcja 7) |

L3 do mapy, bo kafle są małe (siatka 100 m), a L2b z całego obszaru to wiele GB. L2b do szeregów, bo ma natywne daty.

### 3.2 Wyniki (ryciny po angielsku, opisy po polsku)

1. **Mapa prędkości pionowej** (L3) z zaznaczonymi stacjami/reperami i punktami szeregów.
2. **Szeregi EGMS w 3–4 punktach** (wybór regułą: największe osiadanie, mediana, punkt stabilny) z GNSS w tle;
   pionowa linia 23.12.2021 (zmiana 6 → 12 dni).
3. **Próbkowanie**: odstępy między akwizycjami w czasie (6 / 12 dni, przerwy) dla każdej ścieżki.
4. **„Ile czasu do wykrycia”**: prędkość liczona z rosnącego okna (3, 6, 12, 18, 24… mies.) z przedziałem
   niepewności, EGMS i GNSS na jednym wykresie. To jest pomost do etapu B: pokazuje na danych archiwalnych,
   co dałby monitoring co 6/12 dni.

### 3.3 Format danych wspólny dla etapów A i B

Każde źródło (EGMS, własne przetworzenie, GNSS) zapisuje szereg w jednym formacie długim
`data/03_Extracts/<region>/timeseries_long.csv.gz`:

| kolumna | opis |
|---|---|
| `region`, `source` | np. `groningen`, `EGMS_L2b_2020_2024` / `S1_own_<narzędzie>` / `GNSS_NGL` |
| `point_id`, `x_3035`, `y_3035` | punkt lub komórka; EPSG:3035 |
| `track`, `direction`, `los_east`, `los_north`, `los_up` | geometria (puste dla GNSS) |
| `component` | `LOS` / `vertical` / `E`, `N`, `U` |
| `date`, `disp_mm` | data akwizycji, przemieszczenie w mm (ujemne = osiadanie / oddalanie od satelity) |
| `reference` | punkt lub obszar odniesienia |

Wszystkie wykresy czytają tylko ten format. Etap B dopisuje wiersze z innym `source` — **bez zmian w kodzie wykresów**.

## 4. Etap B — własne przetworzenie co 6/12 dni (przygotowanie już teraz)

### 4.1 Zasada

Własne przetworzenie ma **zakładkę z EGMS** (co najmniej rok, np. 2024), żeby:
1. sprawdzić je względem EGMS i GNSS na okresie, w którym znamy odpowiedź,
2. dowiązać przesunięcie szeregu do EGMS,
3. dopiero potem przedłużyć na 2025–2026 (okres, którego EGMS jeszcze nie ma) — to jest „monitoring”.

### 4.2 Co etap A ustala na stałe dla etapu B

- te same ścieżki i kierunki (lista z etapu A, np. Groningen 15, 37, 88, 110, 139),
- ten sam punkt / obszar odniesienia,
- te same punkty szeregów i stacje GNSS,
- ten sam model prędkości i te same metryki (`fit_velocity`, rozrzut różnicy szeregów).

### 4.3 Możliwe narzędzia (wybór autora; żadne nie było tu uruchamiane)

| Narzędzie | Co daje | Uwagi |
|---|---|---|
| ASF HyP3 (interferogramy na żądanie) + MintPy (szereg czasowy, Python) | rozproszone przetwarzanie, szereg co 6/12 dni | darmowe konto Earthdata; najmniej ręcznej pracy |
| COMET LiCSAR / LiCSBAS | gotowe interferogramy dla ramek, szereg w Pythonie | pokrycie ramek dla NL/NRW do sprawdzenia |
| ESA SNAP + StaMPS | pełne przetwarzanie PS | najwięcej pracy ręcznej, najbliżej metody EGMS |

Dane Sentinel-1: Copernicus Data Space Ecosystem (CDSE). **Sekret CDSE z poprzedniego konta trzeba unieważnić** (audyt S1).

## 5. Zasady uczciwości (przed obliczeniami)

- Obszary, punkty szeregów i reguła ich wyboru — ustalone przed pobraniem, nie po obejrzeniu mapy.
- Etap A to **pokaz**, nie nowa walidacja: werdykt E1 (CZĘŚCIOWO) zostaje bez zmian.
- Kryterium „monitoring zadziałałby” dla etapu B — propozycje **[p]** do zatwierdzenia przed etapem B:
  - [p] na okresie zakładki: \|v_own − v_EGMS\| ≤ 1,5 mm/rok i rozrzut różnicy szeregów ≤ 5 mm (jak E1),
  - [p] czas do wykrycia: pierwsze okno, w którym \|v\| > 2σ (σ z szumu rzeczywistego, np. bootstrap blokowy),
    raportowany dla każdej stacji osiadającej i stabilnej (stabilna nie powinna „wykryć” osiadania).
- Rozbieżność raportujemy tak samo jak zgodność.

## 6. Kolejność i nakład

| # | Krok | Wymaga |
|---|---|---|
| 1 | Decyzje z sekcji 7 | autor |
| 2 | Groningen: wycinek L2b z E1 (już jest, 10,3 MB) → wykresy 2–4 bez nowego pobierania | kopia `egmscheck` na nowy Dysk |
| 3 | Groningen + NRW: kafle L3 2020–2024 (wyszukanie API → rozmiar → zgoda → pobranie) | nowy klucz CLMS |
| 4 | NRW: reguła wyboru stacji GNSS (jak E1) lub niwelacja; L2b w punktach | decyzja 3 |
| 5 | `step_06_show_egms.py` + sekcja w notatniku + test offline (atrapy jak `tests/colab_harness`) | — |
| 6 | Etap B: zakładka 2024 → przedłużenie 2025–2026 | decyzja 6, konto CDSE / Earthdata |

Krok 2 daje wykresy na spotkanie najszybciej: dane już są, potrzebny jest tylko nowy kod rysowania.
Uwaga: wycinek E1 jest z wydania **2019–2023**; przejście na 2020–2024 wymaga ponownego pobrania L2b (ok. 4–5 GB).

## 7. Decyzje autora (zasada 2 `CLAUDE.md`)

1. **Wydanie EGMS:** 2020–2024 dla obu regionów (rekomendacja), czy 2019–2023 w Groningen (spójność z E1, bez pobierania)?
2. **Obszar NRW:** odkrywki (Garzweiler / Hambach / Inden), strefa wypiętrzania na zachodzie, czy oba?
   Epe (kawerny, ruch nieliniowy) — wykluczyć (rekomendacja) czy pokazać jako ograniczenie?
3. **Pomiar naziemny w NRW:** GNSS NGL (najlepszy do pokazu co 6/12 dni), niwelacja, czy sam EGMS bez porównania?
4. **Produkt do szeregów:** L2b (LOS, natywne daty, wymaga rzutu GNSS) czy L3 pion (prostszy opis na slajdzie)?
   Do sprawdzenia na danych: czy L3 ma natywne daty, czy próbkowanie przeliczone.
5. **Reguła wyboru punktów szeregów** (proponowana: największe osiadanie, mediana, stabilny — wewnątrz obszaru).
6. **Etap B — narzędzie:** HyP3 + MintPy (rekomendacja: najmniej pracy ręcznej, Python), LiCSBAS czy SNAP + StaMPS?
7. **Kryteria etapu B** z sekcji 5 — zatwierdzić przed etapem B.
