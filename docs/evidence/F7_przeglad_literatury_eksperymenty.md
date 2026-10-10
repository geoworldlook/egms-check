# F7 — Przegląd literatury pod dwa eksperymenty (GNSS i osiadanie zmierzone naziemnie)

> **Data:** 2026-10-10 · **Status:** `Draft`
> **Powiązane:** `docs/plans/Plan_v1_eksperymenty.md`, `docs/evidence/F1_przeglad_literatury_EGMS.md`, `docs/evidence/F4_metodyka.md`

**Poziomy weryfikacji:**
- `pełny tekst (PDF)` — przeczytane w całości z PDF z Dysku Google (`/drive/EGMS`, 6 plików, stan 2026-10-10),
- `abstrakt` — znane tylko ze streszczenia lub wyniku wyszukiwania; liczby z takich źródeł nie trafiają do progów.

Uwaga o źródle tekstu: raport Koudogbo 2025 odczytany z Dysku urywa się na stronie 80 ze 109; strony 80–109
(Śląsk, Thyborøn, delta Padu, Oslo, Tagus, Lorca, Etna, wnioski) przeczytałem z pełnego tekstu w
`docs/evidence/literatura_txt/`. Pozostałe pięć tekstów z Dysku jest kompletnych.

---

## 1. Przeczytane w całości

| # | Pozycja | Co daje eksperymentom |
|---|---|---|
| 1 | Fabris i Nazari 2026, Front. Earth Sci. 14:1781404 (CC BY) | wzorzec E1: PTO1, EGMS L2b 2018–2022, ścieżki 44/117/95, bufory 50–200 m, próg 1,5 mm/rok |
| 2 | Koudogbo i in. 2025, EGMS Validation Report 2019–2023 (EEA) | oficjalna metodyka EGMS–GNSS (7 kroków) i EGMS–niwelacja; wyniki referencyjne |
| 3 | Even, Westerhaus, Kutterer 2024, PFG 92:253–270 (CC BY) | wzorzec E2: EGMS kontra niwelacja (Saara, zachodnia NRW), metryki, porażka w Epe |
| 4 | Crosetto i in. 2025, Validation White Paper v3.0 (EEA) | wymagania: 85% pokrycia, wskaźniki dokładności i precyzji, notatniki |
| 5 | Hrysiewicz i in. 2024, Earth Sci. Inform. 17:3825 (CC BY) | duplikaty w zakładkach burstów; pobieranie |
| 6 | Fernández i in. 2018, Sci. Rep. 8:14782 (CC BY) | rzut GNSS → LOS lepszy niż dekompozycja; niestabilne znaki pomiarowe |

## 2. Jak walidować EGMS względem GNSS (E1)

### 2.1 Metody w literaturze

| Krok | Koudogbo 2025 (rozdz. 2.3.1.1) | Fabris i Nazari 2026 | Even i in. 2024 |
|---|---|---|---|
| Dane GNSS | szeregi stacji ciągłych | **prędkość z 3 kampanii (2018, 2020, 2022)**, także dla stacji ciągłych | szeregi SAPOS, skoki poprawione tylko przy zdarzeniach (wymiana anteny) |
| Czas | interpolacja GNSS do dat EGMS, okno 12 dni; wspólna data odniesienia | brak porównania szeregów | wygładzenie InSAR RLOESS (7 punktów), interpolacja kształtozachowawcza, wspólny okres |
| Kierunek | GNSS rzutowany na LOS | tylko pion: `V_LOS = V_V · cos θ`, θ z najbliższego punktu | GNSS rzutowany wektorem LOS z punktu |
| Układ | dla L2b/L3: odjęcie różnicy między układem GNSS a modelem A-EPND | GNSS w ETRF2014; brak korekty | ETRS89/DREF91 i ETRF2000 uznane za praktycznie te same |
| Punkty EGMS | promień **100 m** + kryterium wysokości; < 3 punkty = stacja odrzucona | 1, 2, 3 najbliższe; bufory 50, 100, 150, **200 m**; średnia | wspólna komórka siatki |
| Metryki | korelacja, std różnic, test OMT, test t prędkości, sezonowość po usunięciu trendu | różnica prędkości `CGNSS − InSAR`, próg ±1,5 mm/rok | różnica prędkości: mediana, MAD × 1,4826; łączne σ (wzór 1) |

### 2.2 Wyniki referencyjne (do tabeli „literatura kontra my”)

| Miejsce | Produkt | Wynik | Źródło |
|---|---|---|---|
| PTO1, 3 ścieżki, bufor 200 m | L2b 2018–2022 | różnica +0,1 / +0,7 / −0,5 mm/rok (ścieżki 44 / 117 / 95) | Fabris 2026, tab. 4 |
| PTO1, wszystkie bufory 50–200 m | L2b | średnie prędkości stabilne w zakresie 0,1–0,2 mm/rok | Fabris 2026, tab. 3 |
| TGPO, CODI (walidacja) | L2b | od −0,8 do +1,6 mm/rok | Fabris 2026, tab. 4 |
| Gran Canaria | L2a/L2b/L3 | średnio < 0,8 mm/rok; najgorzej 2,0–2,2 mm/rok (L2b, L3 pion) | Koudogbo 2025, 3.1.2 |
| Lorca, stacje poza niecką | L2b | < 0,6 mm/rok | Koudogbo 2025, 3.1.3 |
| Jutlandia | L2a/L2b/L3 | średnio 0,8 mm/rok; L3 pion 1,1 mm/rok; GESR 3,7–3,9 mm/rok | Koudogbo 2025, 3.1.4 |
| Badenia-Wirtembergia (SAPOS) | EGMS 2015–2021 | zgodność najlepsza w E-W, najsłabsza w pionie; bias nieco większy niż BBD | Even 2024, 4.1.1 |

### 2.3 Wnioski dla E1

1. **Nasz test jest mocniejszy niż w artykule.** Fabris i Nazari porównują prędkość EGMS z prędkością GNSS
   z trzech kampanii (niepewność ok. ±2 mm/rok, większa niż próg 1,5 mm/rok). My mamy dobowy szereg PTO1,
   więc możemy porównać i prędkości, i szeregi czasowe, tak jak Koudogbo.
2. **Bufor 100 m (EEA) i 200 m (artykuł) liczymy oba.** W artykule wynik praktycznie nie zależy od promienia
   50–200 m (tab. 3), co jest dobrym testem wrażliwości.
3. **Rzut samego pionu jest uzasadniony w delcie Padu** (składowe poziome ok. 1 mm/rok, głównie N-S, na które
   Sentinel-1 jest prawie ślepy; Fabris 2026, 3.1). Fernández 2018 pokazuje, że przy dużym ruchu poziomym
   tak robić nie wolno; w Lorce potrzebny byłby pełny rzut 3D.
4. **Sezonowość w L2b interpretujemy ostrożnie** (Koudogbo 2025, 3.1.2: „seasonal effects should be carefully
   interpreted for Calibrated/L2b and Ortho/L3”). Ocena T1 na trendzie.
5. **L3 pion słabiej zgadza się z GNSS niż L2b** (Jutlandia: test prędkości przechodzi 22% stacji dla L3 wobec
   wszystkich dla L2b). E1 robimy na L2b; L3 tylko pomocniczo.
6. **Układ odniesienia.** EGMS L2b/L3 są w ETRF2000 przez model A-EPND; szereg PANGAEA jest w układzie związanym
   z Eurazją. Dla składowej pionowej różnica układów jest rzędu ułamków mm/rok (F4, sekcja 7); Koudogbo odejmuje
   ją jawnie. Do decyzji: korekta czy opis jako składnik niepewności.
7. **Niezależność.** EGMS kalibruje model GNSS głównie na EPND i pomocniczo na NGL (Even 2024, rozdz. 2).
   Jeśli PTO1 jest w NGL, mogła wejść do modelu (pytanie B3). White Paper dopuszcza takie stacje do walidacji.

## 3. Jak walidować EGMS na osiadaniu zmierzonym niwelacją (E2)

### 3.1 Metody w literaturze

| Element | Even i in. 2024 | Koudogbo 2025 (in situ) |
|---|---|---|
| Produkt | L3 pion (i BBD) | L2a, L2b, L3 pion |
| Dopasowanie | reper i punkt InSAR w tej samej komórce siatki (Saara: komórka produktu 100 m; NRW: siatka 50 m) | bufor 50 lub 100 m wokół punktu in situ; średnia prędkość punktów |
| Czas | InSAR wygładzony RLOESS (7 punktów) i interpolowany do epok niwelacji; wspólny okres | agregacja do 6 dni, miesięcy, lat |
| Odniesienie | średnia różnica między zbiorami bez znaczenia (różne odniesienia) | brak wspólnego reperu; ocena trendów |
| Metryki | różnica prędkości: mediana i MAD × 1,4826; łączne σ różnic przemieszczeń | MAE, R², wskaźnik zgodności d |

### 3.2 Wyniki referencyjne

| Miejsce | Dane naziemne | Liczba punktów | Wynik EGMS | Dostęp do danych | Źródło |
|---|---|---|---|---|---|
| Saara, Primsmulde (pogórnicze) | niwelacja RAG, 10 kampanii 04.2016–04.2021 | 1095 | różnice głównie w ±3 mm/rok, praktycznie bez biasu, σ = 2,80 mm | **niedostępne** | Even 2024, 4.2.1 |
| **Zachodnia NRW** (odkrywki, zatapianie kopalń) | niwelacja państwowa, kampanie 2017 i 2019 | 279 | bias 0,93 mm/rok, σ = 1,76 mm (ostrożnie: 2 kampanie) | **otwarte** (Geoportal NRW) | Even 2024, 4.3.1 |
| Epe (kawerny) | niwelacja roczna 2016–2021, 3 GNSS | 447 | porażka: błąd rozwinięcia fazy, ruch nieliniowy | niedostępne | Even 2024, 4.4 |
| Lotaryngia (wypiętrzanie pogórnicze) | ok. 850 rocznych pomiarów niwelacyjnych | — | MAE < 5 mm; dokładność niwelacji podana jako ±20 mm/rok; EGMS nie oddaje sezonowości na iłach | licencji nie podano | Koudogbo 2025, 3.2.1 |
| Thyborøn | niwelacja reflektorów, 3 epoki 2021–2023 | 9 reflektorów | wysoka korelacja; RR13 ok. 4 mm/rok różnicy | na prośbę | Koudogbo 2025, 3.3.1 |

### 3.3 Wnioski dla E2

1. **Jedyny znaleziony przypadek spełniający wszystkie trzy warunki** (rzeczywiste osiadanie, opublikowana
   walidacja EGMS, otwarte dane naziemne) to **zachodnia NRW** z Even i in. 2024. Hengelo ma otwarte dane
   i rzeczywiste osiadanie, ale **nie ma opublikowanej walidacji EGMS** (F3); spełnia warunki 1 i 3, nie 2.
2. **L3 pion jest właściwym produktem do niwelacji** (Even; Koudogbo w Lotaryngii: zgodność stref ruchu 70% dla L3
   wobec 56–63% dla L2b). Jego słabość to siatka 100 m i uśrednianie silnych gradientów.
3. **Dwie kampanie dają słabą prędkość.** Even sami zastrzegają ostrożność dla NRW. To ograniczenie trzeba
   powtórzyć we wpisie; nie da się go usunąć bez późniejszych epok.
4. **Granice metody są znane i trzeba je pokazać:** ruch nieliniowy (Epe), lokalna sezonowość gruntów
   ekspansywnych (Lotaryngia), niestabilne znaki pomiarowe (Fernández 2018, stacje 23 i 28).

## 4. Otwarte i rzetelne dane naziemne — przegląd

| Zbiór | Zjawisko | Otwarty? | Opublikowana walidacja EGMS? | Uwagi |
|---|---|---|---|---|
| PANGAEA.958598, PTO1 (dobowy pion) | osiadanie delty, ok. 4–5 mm/rok | tak, CC BY 4.0 | tak (Fabris 2026, prędkość kampanijna) | szereg kończy się 2021-04-13 |
| NGL (Nevada Geodetic Laboratory), szeregi E/N/U | dowolne stacje | tak | pośrednio (NGL jest źródłem modelu GNSS EGMS) | obecność PTO1 niezweryfikowana; serwer niedostępny z mojego środowiska |
| Geoportal NRW, „Höhenfestpunkte – Punktliste mit Zeitfolge” | osiadanie i wypiętrzanie górnicze | tak (Datenlizenz Deutschland, do potwierdzenia dla tego zbioru) | tak (Even 2024) | zakres epok po 2019 r. niezweryfikowany |
| NLOG, Strootbeekpark 2023 (PDF) | osiadanie nad kawernami solnymi | do pobrania; licencji nie podano | nie | tabela do przepisania z PDF |
| NLOG, Schiermonnikoog 2024 (CSV) | brak ruchu | do pobrania | nie | kontrola negatywna |
| IGME: LORC, LRCA, ORCA (Lorca) | osiadanie do kilku cm/rok | deklarowane jako otwarte | tak (Koudogbo 2025) | brak adresu pobrania |
| CNIG Lorca (17 stacji), Saara (RAG), Epe (SGW), SAPOS, DTU | — | nie / na prośbę | tak | nie spełniają warunku otwartości |

## 5. Literatura dodatkowa (wyszukana 2026-10-10)

| Pozycja | Po co | Poziom |
|---|---|---|
| Martins i in. 2024, IGARSS, „Validation of the European Ground Motion Service with GNSS and Corner Reflectors Over Deforming Areas”, s. 7537–7541 | metoda TNO/DTU w notatnikach Python; wydanie 2015–2021; większość różnic prędkości < 2 mm/rok | abstrakt |
| Pintori i Serpelloni 2024, Earth Space Sci., doi:10.1029/2023EA003326 | wypiętrzenie stacji w dorzeczu Padu do 7 mm w 01.2021–08.2022 (susza); ryzyko dla okna E1 | abstrakt |
| Crosetto i in. 2025, RSASE 37:101452, „Applications based on EGMS products: a review” | przegląd: zgodność 1–2 mm/rok tam, gdzie badano, bez uogólnienia | fragmenty |
| Praca o terenach pogórniczych w Polsce, RSASE 2025 (ScienceDirect S2352938525001132) | EGMS kontra niwelacja precyzyjna w sieci kopalnianej: korelacja ok. 0,90–0,97 i stałe przesunięcie ok. −7 mm/rok, przypisane ruchowi punktów uznanych za stałe | abstrakt; dane prawdopodobnie nieotwarte |
| Cigna i in. 2021, Remote Sens. 13:4800, dokładność prędkości PSI i SBAS Sentinel-1 względem GNSS i niwelacji | metodyka porównań; cytowana przez Fabris 2026 | nieczytane |
| Fiaschi i in. 2018, Int. J. Remote Sens. 39:8724 | źródło progu 1,5 mm/rok dla delty Padu | nieczytane |
| Blewitt i in. 2016 (MIDAS) | odporna prędkość GNSS (mediana nachyleń rocznych), odporna na skoki | znane z opisu NGL |

Przykład z Polski (stałe przesunięcie ok. −7 mm/rok wobec „stałych” punktów sieci) dobrze ilustruje, że wynik
porównania z niwelacją zależy od stabilności odniesienia. To samo ryzyko dotyczy reperu 000A2890 w Hengelo
i wyboru reperów odniesienia w NRW.

## 6. Co z tego wynika dla progów

| Próg w planie | Wsparcie w literaturze |
|---|---|
| \|Δv\| ≤ 1,5 mm/rok (T1) | Fabris 2026 za Fiaschi 2018 i Huang 2024 (RMSE 1,5 mm/rok); EEA: średnio 0,8 mm/rok, pojedyncze stacje do 2–4 mm/rok |
| std różnicy szeregów ≤ 5 mm (T1) | Jutlandia: odchylenia w ±10 mm, ale średnie z bufora wygładzają sezonowość; Even: σ 1,76–2,80 mm względem niwelacji |
| mediana \|Δh_EGMS − Δh_niw\| ≤ 5 mm (T2) | Koudogbo 2025: MAE < 5 mm (Lotaryngia); Even 2024: σ 1,76–2,80 mm |
| bias różnic prędkości przy niwelacji | Even 2024: 0,93 mm/rok (NRW), ok. 0 (Saara) |
