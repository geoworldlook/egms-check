> **Przypadek zapasowy.** Nie jest częścią dwóch głównych przypadków (`docs/evidence/F2`, `docs/evidence/F3`).
> Odwołania do „przypadku A/B/C" pochodzą z wcześniejszej wersji pakietu. Indeks: `docs/evidence/F6_przypadki_zapasowe/README.md`.

# 02 — Przypadek A: delta Padu (EGMS vs GNSS)

**Cel:** pokazać na danych otwartych, że prędkości EGMS zgadzają się z GNSS, odtwarzając
tabele 3 i 4 z Fabris i Nazari 2026.

**Dlaczego ten przypadek:** artykuł podaje liczby punktów i średnie prędkości dla każdej
stacji, ścieżki i bufora. To pozwala sprawdzić pipeline co do liczby, a nie „na oko".

## Zakres

| Element | Wartość | Status |
|---|---|---|
| Produkt | EGMS Calibrated (L2b) | zweryfikowane |
| Ścieżki | 44 i 117 (wstępujące), 95 (zstępująca) | zweryfikowane |
| „Sceny" z tabeli 1 | 44: 265–266–267; 117: 264–265–266; 95: 806–807–808 | zweryfikowane w tekście; interpretacja jako indeksy burstów niezweryfikowana |
| Okno czasowe | 44: 13.06.2018–12.07.2022; 117: 12.06.2018–15.07.2022; 95: 11.06.2018–14.07.2022 | zweryfikowane |
| Wydanie EGMS | najpewniej 2018–2022 | niezweryfikowane (artykuł nie podaje wprost) |
| Stacje ciągłe | PTO1 (Porto Tolle), TGPO (Taglio di Po), CODI (Codigoro, do 2020) | zweryfikowane |
| Bufory | 50, 100, 150, 200 m oraz 1, 2, 3 najbliższe punkty | zweryfikowane |
| Obszar | delta Padu, ok. 400 km²; orientacyjnie 11,95–12,65°E, 44,75–45,15°N | orientacyjne, do potwierdzenia |

Współrzędnych stacji **nie ma w artykule**. Trzeba je wziąć z dziennika stacji lub z nagłówka
pliku szeregu czasowego. Nie wpisuj ich z pamięci.

## Dwa poziomy odtworzenia

### Poziom 1 — strona EGMS (wymaga tylko danych EGMS)

Dla każdej stacji, ścieżki i bufora policz liczbę punktów oraz średnią i odchylenie
`mean_velocity`. Porównaj z `data/04_Reference/fabris2026_tab3_egms_buffers.csv`.

Przykład docelowy: PTO1, ścieżka 117, bufor 200 m → 753 punkty, −4,6 ± 0,6 mm/rok.

To jest najtwardszy test pipeline'u: sprawdza pobranie, scalenie burstów, usuwanie duplikatów,
układ współrzędnych i wybór przestrzenny.

### Poziom 2 — strona GNSS

Dwa warianty, raportowane osobno:

- **2a. GNSS z artykułu.** Prędkości pionowe z tabeli 2 rzutowane na LOS wzorem
  `V_LOS = V_V · cos θ`, θ = `incidence_angle` najbliższego punktu EGMS. Wynik porównaj
  z kolumną „CGNSS vel." tabeli 3 i z tabelą 4.
- **2b. GNSS z niezależnych szeregów dobowych.** Prędkość policzona z szeregu w tym samym oknie.
  To wzmacnia wynik, bo prędkości w artykule pochodzą z trzech epok i mają niepewność ok. ±2 mm/rok.

## Kąty padania wynikające z tabel (kontrola pomocnicza)

Wyliczone przeze mnie z `V_LOS / V_V` z uwzględnieniem zaokrągleń do 0,1 mm/rok; w artykule ich nie ma.
Kąt `incidence_angle` najbliższego punktu EGMS powinien wpaść w podany przedział.

| Stacja | Ścieżka 44 | Ścieżka 117 | Ścieżka 95 |
|---|---|---|---|
| PTO1 | 32,4–36,0° | 39,9–42,8° | 39,9–42,8° |
| TGPO | 33,7–36,7° | 40,1–42,6° | 40,1–42,6° |
| CODI | 26,1–33,3° | 33,8–39,6° | 33,8–39,6° |

Źródło obliczenia: `step_00_reference_check.py`, kontrola 5.

## Dane GNSS do wariantu 2b

| Źródło | Stacje | Status |
|---|---|---|
| PANGAEA, Pintori i Serpelloni 2023, doi:10.1594/PANGAEA.958598, CC BY 4.0 | PTO1 i CODI są na liście; TGPO i VCCL nie ma | lista stacji zweryfikowana; zawartości plików nie otwierałem |
| Nevada Geodetic Laboratory (NGL) | nieznane | niezweryfikowane (brak dostępu z mojego środowiska) |

Zbiór PANGAEA zawiera tylko składową pionową (mm), w układzie związanym z Eurazją, dobowo,
01.2010–09.2022 według opisu. Kolumny: czas (lata dziesiętne), Up, sigma Up, stacja, długość, szerokość.

## Kroki

1. Pobierz L2b dla trzech ścieżek i obszaru delty (`docs/evidence/F5_zrodla_danych.md`).
2. Scal bursty **z usuwaniem zdublowanych punktów** w zakładkach.
3. Sprawdź konwencje: `los_up ≈ cos(incidence_angle)`, znak `los_east` przeciwny dla orbit, prędkości ujemne w delcie.
4. Ustal współrzędne stacji i przelicz do EPSG:3035.
5. Wybierz punkty w buforach; policz liczbę, średnią, odchylenie.
6. Poziom 1: porównaj z tabelą 3.
7. Poziom 2a i 2b: rzut GNSS na LOS, różnice GNSS − EGMS, porównanie z tabelą 4.
8. Test wrażliwości: te same liczby dla wariantu prędkości (atrybut vs przeliczona w oknie).
9. Raport: tabela „artykuł vs my", wykresy, lista rozbieżności z wyjaśnieniem.

## Znane pułapki

- **Wariant prędkości.** Atrybut `mean_velocity` dotyczy całego wydania (01.2018–12.2022).
  Tabela 1 podaje okno 06.2018–07.2022. Licz oba warianty i sprawdź, który odtwarza tabelę 3.
- **Duplikaty.** Bez ich usunięcia liczba punktów będzie zawyżona o kilka procent.
- **Wydanie.** Inne wydanie EGMS to inne punkty; liczby punktów się nie zgodzą.
- **CODI.** Dane GNSS do 07.2020, więc porównanie trzeba ograniczyć czasowo, jak w artykule.
  Na ścieżce 44 przy CODI nie ma punktów EGMS.
- **Ta sama prędkość LOS dla ścieżek 117 i 95.** Autorzy podają, że kąty padania różnią się o mniej niż 1°.
- **Rozbieżność w artykule.** CODI, ścieżka 117: różnica 1,6 mm/rok przekracza próg 1,5.

## Czego ten przypadek nie pokaże

- Zgodności szeregów czasowych w artykule nie ma, są tylko prędkości. Wariant 2b pozwala ją dodać.
- Sygnał jest umiarkowany (3–6 mm/rok na stacjach), a ruch poziomy pomijalny. Przypadek
  nie testuje pełnego rzutu 3D; od tego jest przypadek C.
- L2b jest dowiązany do modelu GNSS. Dla niezależności dodaj test na L2a w różnicach
  między stacjami (PTO1 jako referencja, TGPO i CODI jako kontrolne).
