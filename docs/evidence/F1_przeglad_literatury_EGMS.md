# F1 — Przegląd literatury: walidacja EGMS względem GNSS i niwelacji

> **Data:** 2026-10-09 · **Status:** `Draft`
> **Powiązane:** `docs/plans/Plan_v1_walidacja_EGMS.md`, `docs/evidence/F4_metodyka.md`

**Poziomy weryfikacji źródeł:**
- `pełny tekst` — przeczytane w całości (pozycje 1–6; teksty w `docs/evidence/literatura_txt/`).
- `raport` — pozycja 7: przeczytany tekst raportu, załącznik z tabelą reperów nieodczytany.
- `abstrakt / fragment` — pozycje uzupełniające na końcu, oznaczone w tabeli.

Zakres: walidacja produktów EGMS (Sentinel-1 InSAR) względem GNSS i niwelacji.
Sześć pozycji przeczytanych w całości (pełne teksty w `docs/evidence/literatura_txt/`), potem pozycje
uzupełniające znane tylko z abstraktu lub fragmentów.

## Wniosek zbiorczy

- Prędkości EGMS zgadzają się ze stacjami GNSS typowo na poziomie ok. 1 mm/rok, a szeregi
  czasowe na poziomie kilku mm.
- Zgodność spada dla ruchów szybkich i nieliniowych, dla składowej pionowej produktu Ortho
  i dla sygnałów sezonowych.
- Produkty Calibrated (L2b) i Ortho (L3) nie są niezależne od GNSS, bo są dowiązane do modelu
  prędkości GNSS. Dokładność InSAR ocenia się na produkcie Basic (L2a) metodą różnic między stacjami.
- Przegląd Crosetto i in. 2025 ostrzega przed uogólnianiem: obok różnic 1–2 mm/rok zdarzają się 5–10 mm/rok.

---

## 1. Koudogbo i in. 2025 — EGMS Validation Report, Third Update (wydanie 2019–2023)

- **Plik:** `docs/evidence/literatura_txt/koudogbo2025_egms_validation_report_2019-2023.txt`
- **Typ:** oficjalny raport EEA, dokument D7.3, wersja 3.0, 02.06.2025. Konsorcjum: Sixense, NGI, TNO, BRGM, GeoSphere, Terrasigna.
- **Co robi:** porównuje wszystkie trzy produkty EGMS z GNSS, danymi in-situ (niwelacja, piezometry, tachimetry) i reflektorami kątowymi.

**Metodyka porównania z GNSS (rozdz. 2.3.1.1)** — siedem kroków:
1. interpolacja czasowa GNSS do dat akwizycji EGMS, okno 12 dni,
2. wspólna data odniesienia,
3. rzut szeregu GNSS na LOS (dla L2a i L2b),
4. odniesienie przestrzenne: dla L2a różnice względem stacji referencyjnej; dla L2b i L3 odjęcie różnicy między układem GNSS a modelem A-EPND,
5. wybór punktów EGMS w promieniu **100 m** od stacji plus kryterium wysokości; stacje z mniej niż 3 punktami są odrzucane,
6. interpolacja przestrzenna do położenia stacji; podwójne różnice tylko dla L2a,
7. korelacja szeregów, odchylenie różnic, test modelu (OMT), test t dla prędkości.

**Wyniki liczbowe** (zebrane w `data/04_Reference/koudogbo2025_values.csv`):

| Miejsce | Zjawisko | Wynik |
|---|---|---|
| Gran Canaria | ruch umiarkowany | średnia różnica prędkości < 0,8 mm/rok; najgorsza stacja 1,2 (L2a), 2,0–2,1 (L2b), 2,2 mm/rok (L3 pion) |
| La Palma | erupcja 2021 | L2a: średnio 0,8 mm/rok; przy ruchu nieliniowym L2a jest najbardziej wiarygodny |
| Lorca | pompowanie wód | stacje poza niecką < 0,6 mm/rok; ORCA 1,3 mm/rok (ścieżka 103) i 5 mm/rok (ścieżka 001) |
| Jutlandia | osiadanie wybrzeża | średnio 0,8 mm/rok; L3: 0,7 (E-W) i 1,1 mm/rok (pion); stacja GESR odstaje o 3,7–3,9 mm/rok; 70% stacji przechodzi test prędkości |
| Thyborøn | reflektory + niwelacja | błąd położenia średnio 10,77 m (wymóg 10 m); różnice prędkości do ok. 4 mm/rok na reflektorze RR13 |
| Lotaryngia | wypiętrzanie pogórnicze | MAE < 5 mm; EGMS nie oddaje lokalnej sezonowości na iłach |
| Turów (PL) | odkrywka, piezometry | zgodność dla trendów liniowych, słaba dla nieliniowych |
| Navis (AT) | osuwisko, stok południowy | orbita wstępująca i składowa E-W zaniżają ruch |

**Ograniczenia:**
- większość wyników jest na wykresach, w tekście jest mało liczb do dokładnego odtworzenia,
- notatniki Jupyter zapowiedziano na III kw. 2025; publikacji nie znalazłem (stan 2026-10-09),
- zestaw 17 stacji GNSS CNIG dla Lorki ma w katalogu Copernicus in-situ status „Restricted"; trzy stacje IGME (LORC, LRCA, ORCA) dokument EEA o danych walidacyjnych opisuje jako otwarte, bez adresu pobrania.

**Co czytać:** 2.3.1.1 (metodyka), 3.1.2 (Gran Canaria), 3.1.3 (Lorca), 3.1.4 (Jutlandia), 5 (wnioski).

---

## 2. Fabris i Nazari 2026 — delta Padu

- **Plik:** `docs/evidence/literatura_txt/fabris_nazari2026_po_delta.txt`
- **Cytowanie:** Fabris M., Nazari S. (2026), *Analysis of InSAR datasets from the EGMS and Veneto region using ground-based GNSS velocities for the monitoring of land subsidence in the Po river delta (Italy)*, Frontiers in Earth Science 14:1781404, doi:10.3389/feart.2026.1781404. Licencja CC BY.
- **Dane InSAR:** EGMS Calibrated, ścieżki 44 i 117 (wstępujące) oraz 95 (zstępująca), okno 06.2018–07.2022; dodatkowo regionalny zbiór Veneto.
- **Dane GNSS:** sieć PODELNET: 3 stacje ciągłe (PTO1, TGPO, CODI) i 46 punktów kampanijnych. Kampanie w czerwcu/lipcu 2016, 2018, 2020, 2022; 130 wektorów, sesje min. 3 h, próbkowanie 15 s. Układ: ETRF2014.
- **Metoda:** rzut samego pionu, `V_LOS = V_V · cos θ`, kąt θ z najbliższego punktu EGMS. Średnia prędkość punktów w buforach 50, 100, 150, 200 m oraz dla 1, 2, 3 najbliższych punktów. Próg zgodności ±1,5 mm/rok.

**Wyniki** (pełne tabele w `data/04_Reference/fabris2026_*.csv`):
- prędkości pionowe GNSS 2018–2022: PTO1 −5,2 ± 1,9; TGPO −6,0 ± 2,0; CODI −3,0 ± 1,7 mm/rok (CODI do 2020),
- różnice GNSS − EGMS w LOS przy buforze 200 m: od −0,8 do +1,6 mm/rok,
- wniosek autorów: EGMS w tym obszarze nie wymaga dodatkowej kalibracji, zbiór Veneto wymaga,
- punkty kampanijne: 82%, 81% i 60% różnic w progu ±1,5 mm/rok (ścieżki 44, 117, 95).

**Ograniczenia istotne dla nas:**
- prędkości GNSS policzono z trzech epok kampanijnych, także dla stacji ciągłych; niepewność ok. ±2 mm/rok jest większa niż badane różnice,
- CODI wyłączono w 2021 r. i zastąpiono stacją VCCL,
- wartość 1,6 mm/rok (CODI, ścieżka 117) przekracza próg 1,5, choć tekst mówi o różnicach poniżej progu,
- tekst podaje odsetki po rekalibracji 76%, 66%, 56%, a opis ryciny 6 sugeruje inną kolejność (66% dla ścieżki 44, 76% dla 117); do sprawdzenia w PDF,
- nie jest jasne, czy użyto atrybutu `mean_velocity`, czy prędkości przeliczonej w oknie kampanii.

**Co czytać:** 2.2–2.4 (dane i metoda), tabele 1–4, 3.2.1, 4.1.

---

## 3. Even, Westerhaus, Kutterer 2024 — BBD vs EGMS

- **Plik:** `docs/evidence/literatura_txt/even2024_bbd_vs_egms.txt`
- **Cytowanie:** Even M., Westerhaus M., Kutterer H. (2024), *German and European Ground Motion Service: a Comparison*, PFG 92:253–270, doi:10.1007/s41064-024-00273-3. Licencja CC BY.
- **Co robi:** porównuje niemiecki BBD i EGMS (dane 01.2016–12.2021) ze sobą, z GNSS i z niwelacją w czterech miejscach.

**Metoda (rozdz. 3)** — najlepszy opisany przepis w całym zestawie:
1. wygładzenie szeregu InSAR regresją RLOESS w oknie 7 punktów,
2. interpolacja do epok drugiego zbioru (kształtozachowawcza, kawałkami sześcienna),
3. przycięcie do wspólnego okresu,
4. różnice prędkości: mediana i MAD × 1,4826,
5. łączne odchylenie różnic przemieszczeń: `σ = sqrt( Σ_P (N_P − 1)·σ_P² / (N − 1) )`,
6. GNSS rzutowany na LOS wektorem LOS dostarczonym z punktem.

**Wyniki dla EGMS:**

| Miejsce | Referencja | Punkty | Wynik EGMS |
|---|---|---|---|
| Badenia-Wirtembergia | 36 stacji SAPOS | — | zgodność najlepsza w E-W, najsłabsza w pionie; bias nieco większy niż BBD |
| Saara, niecka Prims | niwelacja RAG, 10 kampanii 04.2016–04.2021 | 1095 | różnice głównie w ±3 mm/rok, praktycznie bez biasu, σ = 2,80 mm |
| **Zachodnia NRW** | **niwelacja z Geoportal NRW, kampanie 2017 i 2019** | **279** | **bias 0,93 mm/rok, σ = 1,76 mm** |
| Epe (kawerny) | niwelacja roczna 2016–2021, 3 stacje GNSS | 447 | porażka: EGMS nie odtwarza silnego osiadania zimą 2017–2018, błąd rozwijania fazy |

**Ograniczenia:** dane geodezyjne z Saary, Epe i SAPOS nie są udostępniane. Otwarta jest tylko
niwelacja NRW. Wynik dla NRW opiera się na dwóch kampaniach i autorzy zalecają ostrożność.
Kod dostępny częściowo, na prośbę.

**Co czytać:** 3 (metody), 4.1.1 (SAPOS), 4.3 (NRW), 4.4 (Epe jako przykład porażki), 5.

---

## 4. Fernández i in. 2018 — Lorca 2D/3D

- **Plik:** `docs/evidence/literatura_txt/fernandez2018_lorca_2d3d.txt`
- **Cytowanie:** Fernández J. i in. (2018), *Modeling the two- and three-dimensional displacement field in Lorca, Spain, subsidence and the global implications*, Scientific Reports 8:14782, doi:10.1038/s41598-018-33128-0. Licencja CC BY.
- **Dane:** sieć 33 punktów GNSS mierzona kampanijnie (11.2015, 06–07.2016, 02.2017) plus 2 stacje ciągłe; Sentinel-1A, ścieżki 103 (wstępująca) i 8 (zstępująca), własne przetwarzanie CPT, piksel ok. 60 m.

**Wyniki:**
- maksymalne osiadanie 9,0 ± 0,5 cm/rok,
- maksymalny ruch poziomy 2,5 ± 0,3 cm/rok, czyli ok. 28% pionu, skierowany dośrodkowo,
- zgodność A-DInSAR z GNSS ok. 0,7 cm/rok w LOS (po rzucie 3D), ok. 1,0 cm/rok w E-W,
- przyjęcie, że LOS = pion, zawyża objętość o ok. 24%,
- Sentinel-1 pokazał rozszerzenie niecki na południowy zachód, poza zasięg sieci GNSS.

**Znaczenie dla nas:** w Lorce nie wolno rzutować samego pionu, potrzebny pełny rzut 3D.
Zawiera też wzór dekompozycji orbit na pion i E-W.

**Uzupełnienia z PDF (przeczytany w całości 2026-10-09; plik lokalnie w `docs/evidence/literatura_pdf/`):**
- znak LOS w artykule: dodatni = oddalanie od satelity, czyli odwrotnie niż przyjmujemy dla EGMS (F4, sekcja 4),
- zgodność liczona dla punktów A-DInSAR w promieniu **100 m** od stacji GNSS (tab. S5 i S6 w suplemencie):
  ok. 0,7 cm/rok w pionie, ok. 1,0 cm/rok w E-W, ok. 0,7 cm/rok w LOS po rzucie 3D GNSS na obu orbitach,
- dekompozycja na pion i E-W dała tu słabe wyniki (E-W na poziomie niepewności), rzut GNSS → LOS lepsze,
- duże ruchy poziome przy stacjach 23 i 28 autorzy przypisali **niestabilności znaków pomiarowych** po porównaniu
  z A-DInSAR i wizji w terenie; pomiar naziemny też bywa obciążony,
- GNSS: GAMIT/GLOBK 10.6, ITRF2008, potem obrót do lokalnego układu przez minimalizację prędkości stacji ALAC, ALBA,
  ALME; odrzucano dni z niepewnością > 20 mm lub odchyleniem > 10 mm od trendu; błądzenie losowe 1,5 / 2,5 mm/√rok,
- A-DInSAR: 37 obrazów (19 wstępujących, 18 zstępujących), 185 interferogramów, okno 10.2015–02.2017, CPT,
  wieloodczyt 3 × 15 (ok. 60 × 60 m), próg koherencji 0,4.

**Ograniczenia:** to nie jest EGMS, tylko własne przetwarzanie. Dane dostępne na prośbę.

---

## 5. Hrysiewicz, Khoshlahjeh Azar, Holohan 2024 — EGMS-toolkit

- **Plik:** `docs/evidence/literatura_txt/hrysiewicz2024_egms_toolkit.txt`
- **Cytowanie:** Earth Science Informatics 17:3825–3837, doi:10.1007/s12145-024-01356-w. Kod: github.com/alexisInSAR/EGMStoolkit (GPL-3.0).
- **Co daje:** wyszukanie burstów i kafli dla obszaru, pobranie, scalenie, przycięcie, konwersję.
- **Kluczowa uwaga:** w zakładkach burstów i pasów punkty są zdublowane (2–4% punktów w przykładzie Dublina). Bez ich usunięcia średnie i liczby punktów w buforze są zafałszowane.
- **Wymagania:** Python 3, GDAL ≥ 3.8, GMT z GSHHG. Token z EGMS Explorer (końcówka dowolnego linku pobierania, ważny czasowo).
- **Ograniczenie:** artykuł opisuje wydania 2015–2021 i 2018–2022. Obsługa nowszych jest niezweryfikowana (repozytorium: wersja 0.3.0 Beta, 10.2025).

---

## 6. Crosetto i in. 2025 — Validation White Paper

- **Plik:** `docs/evidence/literatura_txt/crosetto2025_validation_white_paper.txt`
- **Typ:** dokument EEA, wersja 3.0, 29.01.2025. Plan przyszłych walidacji, bez wyników.

**Ustalenia, na których opieramy projekt:**
- dokładność i precyzję ocenia się na produkcie **Basic (L2a)** oraz osobno na modelu GNSS,
- wymagane wskaźniki: dokładność i precyzja prędkości (mm/rok) oraz szeregów czasowych (mm),
- co najmniej **85% pokrycia czasowego** między EGMS a danymi referencyjnymi,
- stacja permanentna może służyć do walidacji, nawet jeśli weszła do modelu GNSS,
- oczekiwane produkty: mapa błędów prędkości, bias, odchylenie, wykresy szeregów i ich różnic, korelacja,
- kod i dane w notatnikach Jupyter; każdą rozbieżność trzeba omówić,
- zdarzeń bardzo szybkich InSAR nie uchwyci i trzeba to mówić wprost.

**Co czytać:** rozdz. 3, 4.1, 4.3.

---

## 7. Raport niwelacyjny Strootbeekpark 2023 (źródło danych przypadku 2)

- **Typ:** rejestr pomiarowy wymagany prawem górniczym, nie publikacja naukowa. Antea Group dla Nobian, 24.04.2024.
- **Dostęp:** portal NLOG; PDF do pobrania bezpośrednio.
- **Zawartość:** niwelacja precyzyjna 50 reperów; epoki 12.2020, 06.2022, (12.2022 do potwierdzenia), 12.2023.
- **Wynik:** różnice względem 2020 r. od −42 do +2 mm; względem poprzedniej epoki od −13 do +2 mm.
- **Znaczenie:** pomiar terenowy późniejszy niż wydanie EGMS 2018–2022, więc nadaje się do testu prognozy.
- **Ograniczenie:** nikt nie porównał jeszcze tych danych z EGMS w znanej mi publikacji. To będzie nasz
  własny wynik, bez wzorca do odtworzenia. Szczegóły: `docs/evidence/F3_przypadek_repery_Hengelo.md`.

---

## Pozycje uzupełniające (nie w folderze)

| Pozycja | Po co | Status |
|---|---|---|
| EGMS Product Description and Format Specification | nazwy kolumn CSV, nazewnictwo plików | sprawdzone: tabela atrybutów w `docs/evidence/F5` |
| EGMS Product User Manual | konwencja znaku LOS | nieczytane, potrzebne |
| EGMS GNSS Calibration Report (Larsen i in.) | model A-EPND, układ ETRF2000 | znany z fragmentów |
| Thiéblemont i in. 2024, Earth's Future, doi:10.1029/2024EF004523 | wpływ układu odniesienia na prędkości pionowe | tylko abstrakt |
| Crosetto i in. 2025, RSASE 37:101452 | przegląd zastosowań i walidacji EGMS | tylko fragmenty |
| Martins i in. 2024, IGARSS, doi:10.1109/IGARSS53475.2024.10641305 | metoda TNO dla GNSS i reflektorów; większość różnic < 2 mm/rok | tylko abstrakt |
| Portela i in. 2025, Tectonics, doi:10.1029/2024TC008381 | prędkości GNSS w dolinie Guadalentín (ORCA −74,8 ± 0,5 mm/rok) | tylko fragment |
| Hu i in. 2022, lotniczy LiDAR w Alto Guadalentín | niezależne potwierdzenie osiadań do −12 cm/rok (2009–2016) | tylko abstrakt |
| Cenni, Fiaschi, Fabris 2021, Remote Sensing 13:1488 | sieci geodezyjne w delcie Padu, ruch poziomy | nieczytane |
| Naumowicz i Kowalczyk | integracja EGMS, ASG-EUPOS i niwelacji w Polsce; bufor 0,3 km, mediana | tylko streszczenie |

Linki: `docs/evidence/literatura_txt/README.md`.
