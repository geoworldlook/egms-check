# F2 — Przypadek 1: GNSS (stacja PTO1, delta Padu)

> **Data:** 2026-10-09 · **Status:** `Draft` — pliku danych GNSS jeszcze nie otwierano
> **Powiązane:** `docs/plans/Plan_v1_test_EGMS.md` (T1), `docs/plans/Plan_v1_dane_do_pobrania.md`

**Cel:** na jednym wykresie nałożyć szereg czasowy stacji GNSS i szereg EGMS z jej otoczenia
i pokazać, że oba pomiary dają to samo tempo osiadania.

**Teza do obrony:** niezależny pomiar naziemny potwierdza tempo osiadania widoczne w EGMS.
Nie twierdzimy, że EGMS „wykrył" coś nieznanego; osiadanie delty Padu było znane wcześniej.

## Dlaczego ta stacja

- Dobowy szereg jest w opublikowanym, otwartym zbiorze danych (CC BY 4.0).
- Stacja leży w obszarze stałego osiadania ok. 5 mm/rok.
- Wokół niej jest kilkaset punktów EGMS na każdej ścieżce (artykuł: 531–753 w promieniu 200 m).
- Istnieje recenzowana publikacja z liczbami do porównania (Fabris i Nazari 2026).

## Dane

| Element | Wartość | Status |
|---|---|---|
| Stacja | PTO1, Porto Tolle (Włochy) | zweryfikowane w artykule |
| Szereg GNSS | PANGAEA, Pintori i Serpelloni 2023, doi:10.1594/PANGAEA.958598; plik `https://download.pangaea.de/dataset/958598/files/PTO1.txt` | PTO1 jest na liście stacji; samego pliku nie otwierałem |
| Zawartość pliku | czas (lata dziesiętne), Up [mm], sigma Up [mm], stacja, długość, szerokość | wg opisu zbioru |
| Zakres | 01.2010–09.2022 wg opisu (metadane podają też 11.2022) | do sprawdzenia w pliku |
| Przetwarzanie GNSS | GAMIT/GLOBK 10.71, układ związany z Eurazją | wg opisu zbioru |
| Instytucja | autorzy z INGV (włoski instytut geofizyki) według mojej wiedzy | potwierdź na stronie zbioru |
| EGMS | Calibrated (L2b), ścieżki 117 i 44 (wstępujące), 95 (zstępująca) | zweryfikowane w artykule |
| Wydanie EGMS | 2018–2022 | wybór uzasadniony niżej; dostępność do sprawdzenia |

Współrzędne stacji weź z pliku PANGAEA (kolumny długość i szerokość).

**Dlaczego wydanie 2018–2022:** szereg GNSS kończy się we wrześniu 2022 r. Z tym wydaniem
wspólne okno to ok. 4,7 z 5 lat (ponad 90%). Z wydaniem 2019–2023 byłoby to ok. 3,7 z 5 lat,
czyli poniżej progu 85% z White Paper.

## Czego się spodziewać (z artykułu)

| Wielkość | Wartość |
|---|---|
| Prędkość pionowa GNSS 2018–2022 | −5,2 ± 1,9 mm/rok |
| GNSS w LOS, ścieżki 117 i 95 | −3,9 ± 0,4 mm/rok |
| GNSS w LOS, ścieżka 44 | −4,3 ± 0,4 mm/rok |
| EGMS, ścieżka 117, bufor 200 m | 753 punkty, −4,6 ± 0,6 mm/rok |
| EGMS, ścieżka 44, bufor 200 m | 531 punktów, −4,4 ± 0,4 mm/rok |
| EGMS, ścieżka 95, bufor 200 m | 544 punkty, −3,4 ± 0,7 mm/rok |
| Różnica GNSS − EGMS | +0,7 / +0,1 / −0,5 mm/rok (ścieżki 117 / 44 / 95) |

Prędkości GNSS w artykule pochodzą z trzech kampanii, a nie z szeregu dobowego. Nasza prędkość
z szeregu PANGAEA może się od nich różnić; to nie błąd, tylko inne dane wejściowe.

Pełne tabele: `data/04_Reference/fabris2026_*.csv`.

## Kroki

1. Pobierz `PTO1.txt`. Zapisz w manifeście adres, datę i sumę SHA-256. Sprawdź zakres dat i przerwy.
2. Pobierz EGMS L2b dla burstów pokrywających stację na trzech ścieżkach.
3. Kontrole konwencji na danych EGMS (`docs/evidence/F4_metodyka.md`, sekcja 2).
4. Wybierz punkty EGMS w promieniu 100 m i 200 m od stacji; usuń duplikaty z zakładek burstów.
5. Szereg EGMS: średnia (i mediana) przemieszczeń punktów w buforze dla każdej daty.
6. Szereg GNSS: pion × `los_up` (średnie z bufora). Uzasadnienie pominięcia poziomu:
   Fabris i Nazari podają, że składowe poziome są pomijalne (ok. 1 mm/rok w kierunku N-S).
7. Agregacja GNSS do średnich miesięcznych lub median w oknie wokół dat EGMS.
8. Wspólne okno, wspólna data odniesienia, wyzerowanie obu szeregów.
9. Prędkości z obu szeregów tym samym modelem w tym samym oknie; różnica prędkości.
10. Różnica szeregów: odchylenie standardowe, korelacja.
11. Wykresy i tabela (niżej).

## Wykresy do prezentacji i wpisu

1. **Główny:** szereg GNSS w LOS (punkty dobowe blado, średnie miesięczne wyraźnie) i szereg
   EGMS (średnia z bufora z pasmem rozrzutu punktów), ścieżka 117. Linie trendu i prędkości w legendzie.
2. **Różnica:** EGMS − GNSS w czasie, z zaznaczonym progiem.
3. **Trzy ścieżki obok siebie:** to samo dla 44 i 95, jako dowód, że wynik nie zależy od orbity.
4. **Mapa:** stacja, bufory, punkty EGMS pokolorowane prędkością.
5. **Tabela:** nasze prędkości obok wartości z artykułu.

Wariant pomocniczy, bardziej intuicyjny dla odbiorcy: produkt Ortho (L3, pion) w komórce
ze stacją nałożony wprost na pion GNSS, oba w mm. Mniej rygorystyczny (siatka 100 m).

## Pułapki

- **Szum GNSS.** Dobowy pion ma rozrzut rzędu kilku mm, a sygnał w oknie to ok. 2 cm.
  Bez agregacji trend ginie w szumie.
- **Sezonowość.** Uśrednianie punktów EGMS wygładza amplitudę sezonową (Koudogbo 2025).
  Oceniaj trend; korelację sezonową raportuj osobno.
- **Skoki w szeregu GNSS.** Koryguj tylko na podstawie dziennika stacji; inaczej pokaż je i opisz.
- **Zależność od modelu GNSS.** L2b jest dowiązany do modelu prędkości GNSS w siatce 50 km.
  Lokalny sygnał pochodzi z InSAR, ale trzeba to powiedzieć wprost. Nie wiem, czy PTO1 weszła do modelu.
- **Układy odniesienia.** Szereg GNSS jest w układzie związanym z Eurazją, EGMS w ETRF2000.
  Różnica prędkości pionowych między układami jest rzędu ułamków mm/rok; opisz to jako składnik niepewności.
- **Kąt padania.** Z tabel artykułu wynika 39,9–42,8° dla ścieżek 117 i 95 oraz 32,4–36,0° dla 44.
  `incidence_angle` punktów przy stacji powinien wpaść w te przedziały.

## Rozszerzenia, jeśli starczy czasu

- **Stacja CODI** (Codigoro): też jest w zbiorze PANGAEA; dane GNSS kończą się w 2020 r.
- **Odtworzenie tabel 3 i 4 artykułu** dla trzech stacji i wszystkich buforów:
  `docs/evidence/F6_przypadki_zapasowe/odtworzenie_tabel_fabris2026.md`.
- **Test na L2a** w różnicy między stacjami, niezależny od modelu GNSS.
- **Mocniejszy sygnał:** stacje LORC, LRCA, ORCA w Lorce. Dokument EEA o danych walidacyjnych
  opisuje szeregi IGME jako otwarte i wolne do redystrybucji, ale nie podaje adresu pobrania.
