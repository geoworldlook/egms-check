# F10 — Zachodnia NRW: EGMS L3 (pion) kontra niwelacja, wydanie 2019–2023

> **Data:** 2026-10-13 · **Status:** `Draft` — wariant główny policzony; wariant dodatkowy (względny) czeka na przebieg w Colab.
> **Wyniki:** `notebooks/EGMS_Monitoring.ipynb`, zapis z Colab w commicie `ace4313` (kod `1afb1da`).
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

- **Metoda (F4, sekcja 10, zapisana 2026-10-09, przed obliczeniami):** oba zbiory względem wspólnego odniesienia,
  `d_rel = d_P − d_ref`. Odniesienie = grupa reperów stabilnych **według niwelacji** (\|Δh_niw\| ≤ 2 mm, próg N3 z konfiguracji).
  Mediana prędkości grupy jest odejmowana osobno od niwelacji i od EGMS (`step_06.relative_to_stable_group`).
  Repery grupy nie biorą udziału w ocenie.
- **Status:** wariant **dodatkowy**. Policzony po obejrzeniu wyniku `absolute`, więc raportowany obok niego, bez zmiany werdyktu.
  N4 w tym wariancie sprawdza, czy przesunięcie jest jednakowe w całym obszarze (grupa stabilna kontra pozostałe repery).
  N3 jest tu mało informatywne, bo repery stabilne tworzą grupę odniesienia.
- **Wynik:** do uzupełnienia po przebiegu komórki `compare_levelling_check_nrw_west` w Colab
  (`levelling_summary_nrw_west_2019_2023_relative.csv`, `levelling_offset_nrw_west_2019_2023_relative.json`).

---

## 5. Weryfikacja informacji

| # | Informacja | Stan | Źródło / uwaga |
|---|---|---|---|
| 1 | Liczby z sekcji 2 (1216, 559, 307, 54, 6,0 mm, 77%, −1,97, 0,96 ± 0,01, 8,5 km) | **zweryfikowane** | wyjścia notatnika, commit `ace4313` |
| 2 | 1491 reperów z parą epok 2019–2023; 13 w 2020–2024; epoki głównie 05.2019 → 05.2022 | **zweryfikowane** | komórka diagnostyczna i log `epochs_in_release` (`ace4313`) |
| 3 | „Stacje GNSS w obszarze nie osiadają” | **poprawione** | W obszarze jest 17 stacji NGL; regułę jakości spełnia 6, z vu od −1,28 do +1,98 mm/rok (MIDAS, cały szereg). O pozostałych 11 nie wiemy nic; nie wiemy też, które stacje wchodzą do modelu kalibracji EGMS. Zdanie wycofane; argument niezależności = skala przestrzenna (sekcja 3). |
| 4 | Kalibracja L2b/L3 modelem GNSS (A-EPND) w siatce ok. 50 km | zweryfikowane w dokumentach projektu | F4 (tabela produktów), F1 (Koudogbo i in. 2025, krok 4); pełne teksty nie są w repozytorium |
| 5 | „Najbliższa stacja GNSS 8,5 km” | **doprecyzowane** | liczone do wszystkich stacji NGL z migawki MIDAS (`midas_20261012.IGS.txt`), także tych spoza modelu EGMS; poprawnie: „najbliższa stacja NGL” |
| 6 | Przesunięcie wynika z różnicy układów odniesienia | **hipoteza** | Fakty: EGMS L3 dowiązany do GNSS w ETRF2000 (F4, F6); niwelacja w DHHN2016 (Datenformatbeschreibung 07/2023). Wydawca: wartości z różnych punktów i dat są „tylko warunkowo porównywalne” (cytowane w F6; źródło pierwotne, Nutzerinformation.pdf, nie jest w repozytorium). Nie sprawdzaliśmy ruchu punktów nawiązania sieci niwelacyjnej. |
| 7 | Even i in. 2024: NRW, 279 reperów, bias 0,93 mm/rok, σ 1,76 mm, kampanie 2017 i 2019, EGMS 2016–2021 | zweryfikowane w repozytorium | `data/04_Reference/even2024_values.csv` (sekcja 4.3.1). **Znak biasu i sposób odniesienia niezweryfikowane**: pełnego tekstu nie ma w repozytorium, serwer wydawcy niedostępny z sesji 2026-10-13. Nie mówić „ten sam kierunek przesunięcia”. |
| 8 | Sprzeczność: konfiguracja „absolute (jak Even i in. 2024)” kontra F4 §10 „tak samo postępują Even: średnia różnica nie ma znaczenia” | **wykryta, nierozstrzygnięta** | oba zdania o metodzie Even oznaczone jako niezweryfikowane (konfiguracja, F4, Plan_v2); rozstrzygnąć po lekturze PDF, rozdz. 3 i 4.3 |
| 9 | Niecki = odkrywki węgla brunatnego | **niezweryfikowane** | mapa L3 (silne osiadanie w środkowo-wschodniej części obszaru) i wiedza ogólna; sprawdzić z mapą odkrywek albo warstwą Bodenbewegungsgebiete NRW (F6) |
| 10 | „Do −140 mm w 3 lata” | **zweryfikowane** | reper 5104900560: −140 mm, 2019-05-13 → 2022-05-13 (komórka diagnostyczna) |
| 11 | Sformułowanie „EGMS wykrywa” | **poprawione** | CLAUDE.md: „pomiar naziemny potwierdza osiadanie widoczne w EGMS”; EGMS jest produktem archiwalnym |

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
  osiadają”; „Even i in. znaleźli przesunięcie w tym samym kierunku”; „odkrywki X i Y” bez sprawdzenia mapy.
