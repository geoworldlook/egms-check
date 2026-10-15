# F10 — Zachodnia NRW: EGMS L3 (pion) kontra niwelacja, wydanie 2019–2023

> **Data:** 2026-10-13 · **Status:** `Draft` — wariant główny i dodatkowy (względny) policzone; ryciny szeregów reperów czekają na przebieg w Colab.
> **Wyniki:** `notebooks/EGMS_Monitoring.ipynb`, zapis z Colab w commicie `ace4313` (kod `1afb1da`).
> **Źródło porównawcze:** Even i in. 2024 — pełny tekst przeczytany 2026-10-13 (PDF od autora projektu; tekst w
> `docs/evidence/literatura_txt/even2024_bbd_vs_egms.txt`, katalog poza gitem).
> **Decyzje autora:** 2026-10-12 (wydanie 2019–2023 tylko do niwelacji, wszystkie repery, kryteria N1–N4 bez zmian, podział
> informacyjny) i 2026-10-13 (wariant dodatkowy względem reperów stabilnych). Poziom weryfikacji każdej informacji: sekcja 5.

---

## 0. W skrócie

- **Pytanie:** czy ruch terenu widoczny w EGMS potwierdza pomiar całkowicie niezależny od GNSS, czyli niwelacja państwowa NRW?
- **Odpowiedź:** tak dla **ruchu względnego** (gdzie i jak bardzo teren się obniża), nie dla **poziomu bezwzględnego**.
  - Na 1216 reperach zmiana wysokości z EGMS rośnie razem z niwelacją z nachyleniem **0,96 ± 0,01** w zakresie od −140 do +25 mm
    (3 lata). W nieckach (54 repery, |v| ≥ 10 mm/rok według niwelacji) znak ruchu zgadza się w **100%**, nachylenie wynosi 0,98.
  - Oba zbiory dzieli **stałe przesunięcie** ok. **−2 mm/rok** (EGMS pokazuje więcej osiadania). Przez nie wariant główny
    nie spełnia 3 z 4 kryteriów (N1, N2, N4). Werdykt zostaje, bo kryteria i odniesienie ustalono przed obliczeniami.
- **Zdanie na slajd:** „Na 1216 reperach niwelacji NRW (05.2019–05.2022) pomiar naziemny potwierdza niecki osiadania widoczne
  w EGMS — ten sam znak i ta sama skala ruchu, do −140 mm w 3 lata. Poziom bezwzględny różni się o stałe ok. 2 mm/rok.”

---

## 1. Dane i metoda

| | |
|---|---|
| Obszar | zachodnia NRW, 5,9–7,0° E, 50,7–51,3° N (Epe poza obszarem) |
| Niwelacja | Geobasis NRW, Höhenfestpunkte (Punktliste i Punktliste mit Zeitfolge), wysokości w DHHN2016 |
| Epoki | pierwsza i ostatnia epoka reperu w oknie dat EGMS, odstęp ≥ 1 rok; w praktyce kampania 05.2019 → 05.2022 |
| EGMS | L3 Ortho, składowa pionowa, wydanie 2019–2023 (daty szeregów 2019-01-07 – 2023-12-18), komórka 100 m z reperem |
| Odczyt EGMS | interpolacja liniowa szeregu w dniach obu epok niwelacji, bez ekstrapolacji |
| Wybór reperów | wszystkie z parą epok (1491); 1216 z komórką L3 i szeregiem; bez wyboru według EGMS |
| Odniesienie, wariant główny | `absolute`: oba zbiory tak, jak podane (decyzja autora 2026-10-12) |
| Kryteria | N1–N4 z `thresholds.levelling_l3u` (zatwierdzone 2026-10-12, przed obliczeniami) |
| Informacyjnie | podział według niwelacji: niecki \|v\| ≥ 10 mm/rok i pozostałe; odległość do najbliższej stacji NGL |

---

## 2. Wynik wariantu głównego (`absolute`)

| Kryterium | Wynik | Próg | Spełnione | n |
|---|---|---|---|---|
| N1 mediana \|Δh_EGMS − Δh_niw\| | 6,0 mm | ≤ 5,0 mm | nie | 1216 |
| N2 zgodność znaku (\|Δh_niw\| ≥ 6 mm) | 77% | ≥ 90% | nie | 559 |
| N3 repery stabilne (\|Δh_niw\| ≤ 2 mm) | mediana \|Δh_EGMS\| 3,7 mm | ≤ 5,0 mm | tak | 307 |
| N4 bias prędkości v_EGMS − v_niw | −1,97 mm/rok | \|bias\| ≤ 1,5 | nie | 1216 |
| Rozrzut różnic prędkości (informacyjnie) | MAD·1,4826 = 1,04 mm/rok | — | — | 1216 |
| Nachylenie Δh_EGMS(Δh_niw) (informacyjnie) | 0,96, błąd std. 0,01, wyraz wolny −6,0 mm | ≈ 1 | — | 1216 |

| Grupa (według niwelacji) | n | Mediana \|różnicy\| | Zgodność znaku (n) | Bias | MAD | Nachylenie | Najbliższa stacja NGL: mediana / min |
|---|---|---|---|---|---|---|---|
| wszystkie | 1216 | 6,0 mm | 77% (559) | −1,97 mm/rok | 1,04 | 0,96 | 10,7 / 1,0 km |
| niecki, \|v_niw\| ≥ 10 mm/rok | 54 | 5,1 mm | **100%** (54) | −1,54 mm/rok | 1,05 | **0,98** | 8,5 / 3,7 km |
| pozostałe | 1162 | 6,0 mm | 75% (505) | −1,98 mm/rok | 1,04 | 0,89 | 10,8 / 1,0 km |

Rycina: `data/05_Final_Outputs/egmscheck/nrw_west/figures/nrw_west_levelling_scatter_2019_2023.png`.

---

## 3. Interpretacja: co jest potwierdzone, a co nie

**Potwierdzone (z liczb powyżej):**
1. Znak i skala ruchu: punkty leżą wzdłuż linii 1:1 od −140 do +25 mm; w nieckach 100% zgodności znaku, nachylenie 0,98.
2. Rozrzut różnic jest mały: 1,04 mm/rok, czyli ok. 3 mm na 3 lata.
3. Niepowodzenie N1, N2 i N4 wynika z jednego zjawiska. Wyraz wolny −6,0 mm i bias −1,97 mm/rok × ok. 3 lata to ta sama
   wielkość. Przesunięcie podnosi medianę różnicy (N1) i odwraca znak reperów o małym wypiętrzeniu (+6 do +10 mm), stąd 77% w N2.

**Niepotwierdzone (hipotezy; sekcja 5):**
- przyczyna przesunięcia (różnica układów odniesienia),
- to, że niecki to odkrywki węgla brunatnego (z mapy prędkości L3 i wiedzy ogólnej, bez mapy odkrywek).

**Dlaczego to dowód niezależny od GNSS — sformułowanie ostrożne:**
- niwelacja nie korzysta z GNSS;
- EGMS L3 jest kalibrowany modelem prędkości GNSS w siatce ok. 50 km (F4, za Koudogbo i in. 2025 i White Paper). Taki model
  może przesunąć cały obszar, ale nie odtworzy niecki o szerokości kilku km i głębokości do 140 mm; zgodność kształtu
  i głębokości niecek pochodzi więc z pomiaru satelitarnego;
- argument opiera się na **skali przestrzennej**, nie na tym, że „stacje GNSS nie osiadają” (sekcja 5, punkt 3).

---

## 4. Wariant dodatkowy: względem reperów stabilnych (decyzja autora 2026-10-13)

- **Metoda (F4, sekcja 10, zapisana 2026-10-09, przed obliczeniami; metodyka projektu, nie metoda Even i in. 2024):** oba zbiory względem wspólnego odniesienia,
  `d_rel = d_P − d_ref`. Odniesienie = grupa reperów stabilnych **według niwelacji** (\|Δh_niw\| ≤ 2 mm, próg N3 z konfiguracji).
  Mediana prędkości grupy jest odejmowana osobno od niwelacji i od EGMS (`step_06.relative_to_stable_group`).
  Repery grupy nie biorą udziału w ocenie.
- **Status:** wariant **dodatkowy**. Policzony po obejrzeniu wyniku `absolute`, więc raportowany obok niego, bez zmiany werdyktu.
  N4 w tym wariancie sprawdza, czy przesunięcie jest jednakowe w całym obszarze (grupa stabilna kontra pozostałe repery).
  N3 jest tu mało informatywne, bo repery stabilne tworzą grupę odniesienia.
- **Wynik** (Colab, kod `da72a77`, zapis `0fc76cf`):
  - grupa odniesienia: 307 reperów stabilnych według niwelacji; ich mediana prędkości: niwelacja +0,00, EGMS −1,22 mm/rok;
    **przesunięcie EGMS − niwelacja w strefie stabilnej: −1,22 ± 0,05 mm/rok** (błąd standardowy mediany; rozrzut w grupie
    MAD·1,48 = 0,73 mm/rok);
  - ocenianych reperów: 909 (repery grupy nie biorą udziału).

| Kryterium | Wynik | Próg | Spełnione | n |
|---|---|---|---|---|
| N1 mediana \|Δh_EGMS − Δh_niw\| | 3,4 mm | ≤ 5,0 mm | tak | 909 |
| N2 zgodność znaku (\|Δh_niw\| ≥ 6 mm) | 94% | ≥ 90% | tak | 559 |
| N3 repery stabilne | brak (tworzą grupę odniesienia) | — | — | 0 |
| N4 bias prędkości | −1,00 mm/rok | \|bias\| ≤ 1,5 | tak | 909 |
| Rozrzut (MAD·1,48) | 1,05 mm/rok | — | — | 909 |
| Nachylenie | 0,96 ± 0,01, wyraz wolny −2,8 mm | ≈ 1 | — | 909 |

| Grupa (według niwelacji) | n | Mediana \|różnicy\| | Zgodność znaku | Bias | Nachylenie |
|---|---|---|---|---|---|
| wszystkie oceniane | 909 | 3,4 mm | 94% | −1,00 mm/rok | 0,96 |
| niecki, \|v_niw\| ≥ 10 mm/rok | 54 | **2,6 mm** | **100%** | **−0,33 mm/rok** | 0,98 |
| pozostałe | 855 | 3,4 mm | 93% | −1,02 mm/rok | 0,90 |

  **Interpretacja:**
  - po usunięciu przesunięcia ze strefy stabilnej wszystkie trzy policzalne kryteria są spełnione; w nieckach różnica
    wynosi 2,6 mm przy ruchu 30–140 mm;
  - przesunięcie **nie jest jednakowe**: po odjęciu −1,22 mm/rok pozostaje −1,0 mm/rok na reperach poza grupą stabilną
    (w nieckach tylko −0,3). Jednorodna różnica układów odniesienia tego nie tłumaczy w całości — część przesunięcia
    zależy od miejsca albo od rodzaju reperu (hipoteza, nie badana);
  - wynik dodatkowy, policzony po obejrzeniu wariantu głównego; werdykt wariantu głównego bez zmian.

- **Ryciny:** rozrzut `nrw_west_levelling_scatter_2019_2023_relative.png`; szeregi w czasie przy reperach z reguły przykładów
  (najszybsze osiadanie, mediana, najmniejszy ruch, mediana niecek) `nrw_west_levelling_series_2019_2023_<reper>.png`
  — dodane 2026-10-13, do przebiegu w Colab.
- **Niepewność EGMS (autor 2026-10-15, informacyjnie, bez progu):** σ_Δh = √2 · `rmse` komórki L3, pas ±2σ na rycinach
  reperów i wokół 1:1 na rozrzucie; odsetek reperów w pasie w `levelling_uncertainty_nrw_west_2019_2023.json`. Rycina
  reperu stabilnego `nrw_west_levelling_stable_2019_2023_<reper>.png` rozdziela szum (pas) i wspólne tempo grupy
  stabilnej (linia), pokazuje szereg po odjęciu tego tempa i rozkład Δh EGMS całej grupy z progiem N3. Że przesunięcie
  jest wspólne dla grupy — zmierzone; że wynika z różnych układów odniesienia — hipoteza (sekcja 5, wiersz 6).

---

## 5. Weryfikacja informacji

| # | Informacja | Stan | Źródło / uwaga |
|---|---|---|---|
| 1 | Liczby z sekcji 2 (1216, 559, 307, 54, 6,0 mm, 77%, −1,97, 0,96 ± 0,01, 8,5 km) | **zweryfikowane** | wyjścia notatnika, commit `ace4313` |
| 2 | 1491 reperów z parą epok 2019–2023; 13 w 2020–2024; epoki głównie 05.2019 → 05.2022 | **zweryfikowane** | komórka diagnostyczna i log `epochs_in_release` (`ace4313`) |
| 3 | „Stacje GNSS w obszarze nie osiadają” | **poprawione** | W obszarze jest 17 stacji NGL; regułę jakości spełnia 6, z vu od −1,28 do +1,98 mm/rok (MIDAS, cały szereg). O pozostałych 11 nie wiemy nic; nie wiemy też, które stacje wchodzą do modelu kalibracji EGMS. Zdanie wycofane; argument niezależności = skala przestrzenna (sekcja 3). |
| 4 | Kalibracja L2b/L3 modelem GNSS (A-EPND) w siatce ok. 50 km | zweryfikowane w dokumentach projektu | F4 (tabela produktów), F1 (Koudogbo i in. 2025, krok 4); pełne teksty nie są w repozytorium |
| 5 | „Najbliższa stacja GNSS 8,5 km” | **doprecyzowane** | liczone do wszystkich stacji NGL z migawki MIDAS (`midas_20261012.IGS.txt`), także tych spoza modelu EGMS; poprawnie: „najbliższa stacja NGL” |
| 6 | Przesunięcie wynika z różnicy układów odniesienia | **hipoteza** | Fakty: EGMS L3 jest w ETRF2000 przez kalibrację GNSS (EPND) — potwierdzone w Even i in. 2024, rozdz. 2 i 2.2; niwelacja w DHHN2016 (Datenformatbeschreibung 07/2023). Wydawca niwelacji: wartości z różnych punktów i dat „tylko warunkowo porównywalne” (cytowane w F6; Nutzerinformation.pdf nie jest w repozytorium). Even i in. **nie podają przyczyny** biasu w NRW. Nie sprawdzaliśmy ruchu punktów nawiązania sieci niwelacyjnej. |
| 7 | Even i in. 2024: NRW, 279 reperów, bias 0,93 mm/rok, σ 1,76 mm, kampanie 2017 i 2019, EGMS 01.2016–12.2021 | **zweryfikowane w pełnym tekście** (2026-10-13) | rozdz. 4.3 i 4.3.1, ryc. 17b: mediana różnic prędkości 0,93, MAD·1,48 = 1,12 mm/rok. **Znak**: histogram ma tytuł „Differences Rates EGMS and Levelling”, kolejności odejmowania tekst nie podaje — znaku nie da się porównać z naszym. Autorzy: bias „not negligible, but small compared to the magnitude of displacement rates”; ostrożność, bo tylko dwie kampanie. |
| 8 | Metoda Even i in.: konfiguracja „absolute (jak Even)” kontra F4 §10 „Even: średnia różnica nie ma znaczenia” | **rozstrzygnięte** (pełny tekst, rozdz. 3) | Even porównują **prędkości wprost** i raportują bias — to odpowiada naszemu wariantowi `absolute`. Zdanie o „średniej różnicy bez znaczenia” dotyczy tylko σ różnic szeregów przemieszczeń (wzór 1), nie prędkości. **F4 §10 było błędne** — poprawione 2026-10-13. Wariant względny jest metodyką projektu, nie metodą Even i in. |
| 9 | Niecki = odkrywki węgla brunatnego | **częściowo zweryfikowane** | Even i in. 2024, rozdz. 4.3: ruch w zachodniej NRW wynika z obniżania wód podziemnych wokół odkrywek węgla brunatnego, a na zachodzie z wypiętrzania po zatopieniu kopalń węgla kamiennego. Położenia konkretnych odkrywek względem naszych niecek nie sprawdzaliśmy (mapa odkrywek albo warstwa Bodenbewegungsgebiete NRW, F6). |
| 10 | „Do −140 mm w 3 lata” | **zweryfikowane** | reper 5104900560: −140 mm, 2019-05-13 → 2022-05-13 (komórka diagnostyczna) |
| 11 | Sformułowanie „EGMS wykrywa” | **poprawione** | CLAUDE.md: „pomiar naziemny potwierdza osiadanie widoczne w EGMS”; EGMS jest produktem archiwalnym |

---

## 5a. Porównanie z Even i in. 2024 (ten sam region, inny okres)

| | Even i in. 2024 | Ten projekt |
|---|---|---|
| Kampanie niwelacji | 2017 i 2019 | 05.2019 i 05.2022 |
| EGMS | Ortho, pion, dane 01.2016–12.2021 | L3 Ortho, pion, wydanie 2019–2023 |
| Łączenie | reper i punkt InSAR w tej samej komórce siatki 50 m | komórka L3 100 m zawierająca reper |
| Szereg InSAR | wygładzenie RLOESS (7 punktów), interpolacja kawałkami sześcienna | bez wygładzania, interpolacja liniowa |
| Repery | 279 | 1216 |
| Mediana różnicy prędkości | 0,93 mm/rok (kolejność odejmowania nieopisana) | −1,97 mm/rok (EGMS − niwelacja) |
| MAD·1,4826 | 1,12 mm/rok | 1,04 mm/rok |
| Ocena autorów / nasza | bias „nieznikomy, ale mały wobec prędkości ruchu” | kryteria N1, N2, N4 niespełnione; ruch względny zgodny |

Rozrzut (MAD) jest tego samego rzędu. Bias u nas jest około dwa razy większy co do wartości; przyczyny różnicy
(okres, wydanie, sposób łączenia, wygładzanie) nie były badane. Kierunku przesunięcia u Even i in. nie da się ustalić z tekstu.

---

## 6. Ograniczenia

- jedna kampania niwelacji: dwie epoki na reper; prędkość z dwóch epok jest słabo wyznaczona (to samo zastrzeżenie u Even i in. 2024);
- L3 to średnia komórki 100 m: na skraju niecki może zaniżać ruch punktu (np. reper 5104900599 w wydaniu 2020–2024);
- 275 z 1491 reperów bez komórki EGMS (teren odkrywek, roślinność);
- wariant główny `absolute` nie usuwa różnicy układów; wariant względny ją usuwa, ale został wybrany po obejrzeniu wyniku.

## 7. Sformułowania

- **Mówić:** „pomiar naziemny potwierdza niecki osiadania widoczne w EGMS”; „ruch względny zgodny, poziom bezwzględny przesunięty
  o ok. 2 mm/rok”; „najbliższa stacja NGL w medianie 8,5 km”.
- **Nie mówić:** „EGMS zgodny z niwelacją w granicach 5 mm” (N1 nie przeszło); „EGMS wykrył niecki”; „stacje GNSS w obszarze nie
  osiadają”; „Even i in. znaleźli przesunięcie w tym samym kierunku”; „Even i in. wyjaśniają przesunięcie układami”
  (nie wyjaśniają); „odkrywki X i Y” bez sprawdzenia mapy.
- **Można powołać się na Even i in. 2024** tak: „w tym samym regionie, dla kampanii 2017–2019, Even i in. (2024) również
  raportują nieznikomy bias różnic prędkości EGMS i niwelacji (0,93 mm/rok) przy rozrzucie podobnym do naszego (1,12 mm/rok)”.
