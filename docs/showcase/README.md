# EGMS Check — opublikowane wyniki

Pliki w tym folderze tworzy polecenie `python -m egmscheck publish` (moduł `egmscheck/publish.py`). Kopiuje ono stały
wybór plików wynikowych z katalogu danych (`data/05_Final_Outputs/egmscheck/` na Dysku Google) i zapisuje
`egmscheck_results.json`. Nazwy plików są takie same jak w katalogu wyników. Plików nie zmienia się ręcznie.

Obecna publikacja: przebieg z 2026-10-15 (kod `06eeefc` w obecnej historii repozytorium; w rejestrze zapisany
jako `2a326ec`, sprzed przepisania historii D-094). Szczegóły w `egmscheck_results.json`, klucz `runs`.

| Plik | Co to jest |
|---|---|
| `egmscheck_results.json` | wszystkie tabele kryteriów w jednym pliku (kod K1…K4 / N1…N4, wynik, próg, spełnione, n), werdykty, podział na grupy, przesunięcie, pasy niepewności, skąd jest każdy wynik, spis plików |
| `verdict_gnss_l2b_<region>.csv` / `.txt` | EGMS L2b (kierunek satelity) kontra GNSS, wydanie 2020–2024: kryteria K1–K4 i werdykt |
| `verdict_gnss_l3u_<region>.csv` / `.txt` | EGMS L3 pion kontra składowa pionowa GNSS (próg tylko dla K1) |
| `levelling_summary_nrw_west_2019_2023.csv` | EGMS L3 pion kontra niwelacja, wariant główny (bezwzględny): N1–N4 |
| `levelling_summary_nrw_west_2019_2023_relative.csv` | wariant dodatkowy względem reperów stabilnych (policzony po wariancie głównym) |
| `levelling_groups_nrw_west_2019_2023*.csv` | to samo w podziale: wszystkie repery, niecki (\|v_niw\| ≥ 10 mm/rok), pozostałe |
| `levelling_offset_nrw_west_2019_2023_relative.json` | przesunięcie EGMS − niwelacja na grupie reperów stabilnych |
| `levelling_uncertainty_nrw_west_2019_2023.json` | odsetek reperów w pasach niepewności EGMS (informacyjnie) |
| `levelling_summary_nrw_west.csv` | niwelacja na wydaniu głównym 2020–2024 (tylko 13 reperów; za mało do wniosków) |
| `<region>_velocity_scatter.png` | prędkość EGMS kontra GNSS (para stacja × ścieżka) |
| `<region>_l3_velocity_map.png`, `nrw_west_l3_velocity_map_2019_2023.png` | mapa prędkości pionowej EGMS L3 |
| `nrw_west_levelling_scatter_2019_2023*.png` | zmiana wysokości EGMS kontra niwelacja (wariant główny i względny) |

Teksty kryteriów i werdyktów w plikach CSV są po polsku (tak zapisuje je kod). Omówienie po angielsku: `README.md`
w katalogu głównym; zestawienie po polsku: `docs/evidence/karta_wynikow.md`.

**Dane i licencje:** *Generated using European Union's Copernicus Land Monitoring Service information* (EGMS;
wyniki są zmodyfikowane: wycinki, porównania, ryciny; DOI produktów w `README.md`, sekcja „Data and attribution”);
GNSS: Nevada Geodetic Laboratory (Blewitt i in. 2018); niwelacja: Geobasis NRW, Datenlizenz Deutschland – Zero –
Version 2.0.
