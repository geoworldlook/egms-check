# Wartości referencyjne

Liczby przepisane z publikacji, do testów regresyjnych i tabel „publikacja vs my".
Jednostki: prędkości w mm/rok, odchylenia szeregów w mm, promienie w m. Znak ujemny = osiadanie.

| Plik | Źródło | Jak sprawdzone |
|---|---|---|
| `fabris2026_tab1_insar_datasets.csv` | Fabris i Nazari 2026, tabela 1 | odczyt z tekstu |
| `fabris2026_tab2_gnss_vertical.csv` | tabela 2 | odczyt z tekstu |
| `fabris2026_tab3_egms_buffers.csv` | tabela 3 | wszystkie 21 wierszy porównane automatycznie z ekstraktem tekstowym: 0 rozbieżności |
| `fabris2026_tab4_differences.csv` | tabela 4 | `step_00_reference_check.py`: zgodne z tabelą 3 |
| `fabris2026_nps_agreement.csv` | tekst sekcji 3.2.1 | odczyt z tekstu; kolejność po rekalibracji do potwierdzenia na ryc. 6 |
| `even2024_values.csv` | Even i in. 2024, sekcje 4.1–4.4 | odczyt z tekstu; wartości z rycin 2–5 nie są ujęte |
| `koudogbo2025_values.csv` | Koudogbo i in. 2025, rozdz. 2.3 i 3 | odczyt z tekstu; większość wyników raportu jest tylko na wykresach |

## Pliki przypadku 2 (Hengelo)

| Plik | Źródło | Status |
|---|---|---|
| `hengelo_strootbeekpark_report_facts.csv` | tekst raportu Antea Group 2024 | odczyt z tekstu; jedna pozycja (epoka 12.2022) wywnioskowana z legendy mapy |
| `hengelo_strootbeekpark_2023_map_labels_UNVERIFIED.csv` | etykiety mapy, załącznik 1 | **niezweryfikowane**: odczyt maszynowy z nieuporządkowanej warstwy tekstowej; pary reper–wartość mogły zostać pomylone. Z tekstem raportu zgadzają się tylko wartości skrajne (−42/−13 dla reperu 7008, maksimum +2). Nie używać do obliczeń. |

Dane do obliczeń dla przypadku 2 to tabela przepisana z załącznika 5 raportu, zapisana w
`data/02_Raw_Ground/2_levelling_hengelo/`.

## Kolumny `fabris2026_tab3_egms_buffers.csv`

- `selection`: `nearest1`, `nearest2`, `nearest3` (średnia z 1, 2, 3 najbliższych punktów) lub `buffer`.
- `radius_m`: promień bufora; puste dla `nearest*`.
- `n_ps`: liczba punktów EGMS.
- `ps_vel_mm_yr`, `ps_vel_std_mm_yr`: średnia i odchylenie prędkości LOS punktów; odchylenie puste dla jednego punktu.
- `gnss_los_mm_yr`, `gnss_los_unc_mm_yr`: prędkość pionowa GNSS zrzutowana na LOS; jedna wartość na stację i ścieżkę.
- CODI, ścieżka 44: brak punktów EGMS; jest tylko wartość GNSS.

Nie poprawiaj tych plików „żeby pasowały". Jeśli znajdziesz błąd przepisania, popraw go
z odwołaniem do strony PDF i uruchom `python step_00_reference_check.py`.
