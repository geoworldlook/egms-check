> **Przypadek zapasowy.** Nie jest częścią dwóch głównych przypadków (`docs/evidence/F2`, `docs/evidence/F3`).
> Odwołania do „przypadku A/B/C" pochodzą z wcześniejszej wersji pakietu. Indeks: `docs/evidence/F6_przypadki_zapasowe/README.md`.

# 04 — Przypadek C: Lorca (rozszerzenie ekstremalne, opcjonalne)

**Cel:** sprawdzić pipeline na najszybszym osiadaniu w Europie i na przypadku, w którym
ruch poziomy nie jest pomijalny. Tematycznie najbliżej wod-kan: przyczyną jest pompowanie wód podziemnych.

**Status:** opcjonalny. Uruchamiaj dopiero po A i dopiero gdy znajdą się otwarte szeregi GNSS.

## Dlaczego nie jest przypadkiem głównym

- Zestaw „Lorca GNSS" użyty przez EEA (17 stacji, dostawca IGN Hiszpania) ma w katalogu
  Copernicus in-situ politykę danych **Restricted**.
- Stacja ORCA należy do IGME, a jej dane w raporcie kończą się na 2020 r.
- Dane kampanijne z Fernández i in. 2018 są dostępne tylko na prośbę.
- Raport EEA podaje wyniki głównie na wykresach.

## Wartości referencyjne

| Źródło | Wielkość | Wartość |
|---|---|---|
| Koudogbo 2025 | różnica prędkości, stacje poza niecką (CARG, HUOV, MAZA, ACAL, CRTG) | < 0,6 mm/rok |
| Koudogbo 2025 | ORCA, L2b, ścieżka 103 | 1,3 mm/rok |
| Koudogbo 2025 | ORCA, L2b, ścieżka 001 | 5 mm/rok |
| Koudogbo 2025 | dokładność prędkości w tym zastosowaniu | poniżej 1 mm/rok |
| Fernández 2018 | maks. osiadanie (11.2015–02.2017) | 9,0 ± 0,5 cm/rok |
| Fernández 2018 | maks. ruch poziomy | 2,5 ± 0,3 cm/rok (ok. 28% pionu) |
| Portela 2025 | prędkość pionowa ORCA | −74,8 ± 0,5 mm/rok |

Konfiguracja EEA: ścieżki wstępujące 103 i 001, zstępująca 008 (w jednym podpisie ryciny
występuje 088), stacja referencyjna CARG, stacje w niecce LRCA, ORCA, LORC.

## Czym różni się od A

- **Pełny rzut 3D.** `d_LOS = E·los_east + N·los_north + U·los_up`. Rzut samego pionu
  wprowadziłby w strefie maksymalnego osiadania błąd do ok. 1,5 cm/rok w LOS
  (2,5 cm/rok ruchu poziomego × współczynnik ok. 0,6).
- **L2a w podwójnych różnicach** względem stacji stabilnej (CARG), jak w raporcie.
- **Ruch nieliniowy.** Możliwe przyspieszenia i sezonowość; porównuj szeregi, nie tylko prędkości.
- **Układ odniesienia GNSS** ma znaczenie dla składowych poziomych; pracuj w różnicach między stacjami.

## Warunek uruchomienia

Znajdź otwarte dobowe szeregi 3D dla co najmniej: jednej stacji w niecce (LORC lub LRCA)
i jednej stabilnej (np. CARG). Kandydaci do sprawdzenia: Nevada Geodetic Laboratory,
produkty szeregów czasowych EPN / EPN Densification, hiszpańska sieć ERGNSS (IGN).
Żadnego z nich nie zweryfikowałem dla tych stacji.

## Wątek „radar pokazał, pomiar potwierdził" (do slajdu, nie do przeliczenia)

- InSAR wcześniej wykrył i zmapował nieckę (maks. 16 cm/rok w latach 2006–2011 według prac cytowanych przez Fernández 2018).
- Sieć GNSS z 2015 r. zaprojektowano na podstawie map InSAR; pomiary potwierdziły tempo i wzór osiadań.
- Sentinel-1 pokazał rozszerzenie niecki na południowy zachód, poza sieć GNSS.
- Lotniczy LiDAR 2009–2016 pokazał osiadania do −12 cm/rok (Hu i in. 2022; znam tylko abstrakt).
