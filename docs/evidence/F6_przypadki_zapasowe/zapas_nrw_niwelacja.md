> **Przypadek zapasowy.** Nie jest częścią dwóch głównych przypadków (`docs/evidence/F2`, `docs/evidence/F3`).
> Odwołania do „przypadku A/B/C" pochodzą z wcześniejszej wersji pakietu. Indeks: `docs/evidence/F6_przypadki_zapasowe/README.md`.

# 03 — Przypadek B: zachodnia NRW (EGMS vs niwelacja)

**Cel:** pokazać na danych otwartych, że osiadanie widoczne w danych radarowych potwierdza
niezależny pomiar terenowy, w tym pomiar wykonany później.

**Wzorzec:** Even, Westerhaus, Kutterer 2024, rozdz. 4.3.

## Zjawisko

Zachodnia Nadrenia Północna-Westfalia (zagłębie reńskie):
- osiadanie liniowe od obniżania zwierciadła wód wokół odkrywek węgla brunatnego,
- wypiętrzanie na zachodzie po zatopieniu dawnych kopalń węgla kamiennego.

Dokładnego zasięgu obszaru artykuł nie podaje w tekście; jest na ryc. 14 i 15 w PDF.

## Wynik referencyjny (Even i in. 2024)

| Wielkość | EGMS | BBD |
|---|---|---|
| Liczba reperów z punktem InSAR w tej samej komórce | 279 | 584 |
| Bias różnic prędkości pionowych | 0,93 mm/rok | 1,42 mm/rok |
| Łączne odchylenie różnic | 1,76 mm | 2,68 mm |

- Produkt: EGMS Ortho, składowa pionowa, siatka 100 m, dane 01.2016–12.2021.
- Niwelacja: kampanie 2017 i 2019, pobrane z Geoportal NRW.
- Łączenie: siatka 50 m; reper jest porównywany z punktem InSAR w tej samej komórce.
- Autorzy zastrzegają ostrożność: prędkość z dwóch kampanii jest słabo wyznaczona.

Wartości: `data/04_Reference/even2024_values.csv`.

## Dane otwarte

| Zbiór | Zawartość | Status |
|---|---|---|
| Höhenfestpunkt – Punktliste mit Zeitfolge (`hfp_plzf.csv`, ok. 7,7 MB) | wysokości reperów w kolejnych datach pomiaru, cała NRW | format zweryfikowany; zakres dat niezweryfikowany |
| Höhenfestpunkt – Punktliste (`hfp_pl_csv`) | współrzędne reperów | format zweryfikowany |
| Höhenänderungen aus Sentinel-1 (GeoPackage, 2020–2024, kafle 16 km) | niezależne przetwarzanie S-1 przez Geobasis NRW | istnienie zweryfikowane |
| Bodenbewegungsgebiete (WMS/WFS, kafle 250 m) | strefy ruchu > ±3 mm/rok | zweryfikowane |

Format plików niwelacji: CSV, UTF-8, separator `;`, przecinek dziesiętny, daty `dd.mm.rrrr`.
- Lista punktów: `Punktkennzeichen; Name des Punktes; Ostwert; Nordwert; Höhe; Schwerewert`.
- Szereg: `Punktkennzeichen; Messungsdatum; Höhe` — jeden wiersz na punkt i datę, wysokość w DHHN2016.

Układ współrzędnych `Ostwert/Nordwert` trzeba potwierdzić w `Datenformatbeschreibung.pdf`
(strona produktu podaje ETRS89/UTM32, EPSG:25832).

## Dwa poziomy

### Poziom 1 — odtworzenie Even i in. 2024

1. Pobierz EGMS L3 pion dla obszaru, wydanie obejmujące 2016–2021.
2. Wczytaj niwelację, wybierz repery z pomiarami w 2017 i 2019.
3. Połącz repery z punktami EGMS w siatce 50 m.
4. Szereg EGMS: wygładzenie RLOESS (okno 7), interpolacja do dat niwelacji, wspólny okres.
5. Policz różnice prędkości (mediana, MAD × 1,4826) i łączne σ.
6. Porównaj z: 279 punktów, bias 0,93 mm/rok, σ 1,76 mm.

### Poziom 2 — „prognoza → potwierdzenie"

Warunek: w pliku niwelacji są epoki **po** końcu użytego wydania EGMS. To pierwsza rzecz do sprawdzenia.

1. Z wydania EGMS kończącego się w roku R policz prędkość pionową w każdej komórce.
2. Wybierz repery z dwiema epokami niwelacji t1 < t2, obie po roku R (lub t1 tuż przy jego końcu).
3. Prognoza: `Δh_prog = v · (t2 − t1)`. Pomiar: `Δh_niw = H(t2) − H(t1)`.
4. Oba zbiory odnieś do tego samego stabilnego reperu lub grupy reperów.
5. Raportuj bias, odchylenie, odsetek reperów w progu i mapę różnic.

Jeśli późniejszych epok nie ma, poziom 2 odpada i zostaje poziom 1. Wtedy „późniejszy pomiar"
można pokazać tylko słabiej: nowszym wydaniem EGMS lub zbiorem Sentinel-1 Geobasis NRW,
które nie są pomiarem terenowym. Napisz to wprost w raporcie.

## Pułapki

- **Porównywalność epok.** Wydawca zaznacza, że wartości z różnych punktów i dat są „tylko
  warunkowo porównywalne" (różne metody, wpływ stabilizacji znaku). Dlatego różnice względem
  reperu stabilnego, nie wysokości bezwzględne.
- **Zastrzeżenie wydawcy co do skali.** Nakładanie na budynki i działki uznaje za nieuzasadnione
  fachowo. Analiza obszarowa, nie pojedyncze obiekty.
- **Liczba reperów.** Zależy od zasięgu obszaru i wydania EGMS; 279 odtworzymy tylko przy tym samym zasięgu.
- **Układy.** EGMS L3 jest w ETRF2000 przez model GNSS, niwelacja w DHHN2016. Porównujemy
  różnice, nie wartości bezwzględne.
- **Ruch nieliniowy.** W Epe (kawerny) EGMS zawodzi. Nie włączaj Epe do obszaru i opisz to jako znane ograniczenie.

## Ograniczenie interpretacyjne

EGMS jest produktem archiwalnym, aktualizowanym raz w roku. Pokazuje powolne trendy.
Nie wykrywa nagłych zapadnięć; White Paper wyłącza zdarzenia bardzo szybkie.
