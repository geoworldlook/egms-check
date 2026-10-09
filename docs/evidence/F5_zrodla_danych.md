# F5 — Źródła danych

> **Data:** 2026-10-09 · **Status:** `Draft` — pliki danych niepobrane; sprawdzone strony źródłowe
> **Powiązane:** `docs/plans/Plan_v1_dane_do_pobrania.md`

Status weryfikacji na **2026-10-09**. „Zweryfikowane" = sprawdzone na stronie źródłowej lub
w publikacji. Plików danych nie pobierałem (brak tokenu EGMS; serwery danych niedostępne
z mojego środowiska), więc zawartość plików trzeba sprawdzić przy pierwszym pobraniu.

## 1. EGMS

| Element | Wartość | Status |
|---|---|---|
| Portal | EGMS Explorer, https://egms.land.copernicus.eu | zweryfikowane |
| Dokumentacja | https://land.copernicus.eu/en/products/european-ground-motion-service | zweryfikowane |
| Dostęp | bezpłatny, wymaga konta; pobieranie przez token | zweryfikowane |
| Wydania | 2015–2021, 2018–2022, 2019–2023; 2020–2024 jako czwarta aktualizacja | 2018–2022 oznaczone w katalogu EEA jako „Superseded"; dostępność starszych wydań i wydania 2020–2024 niezweryfikowana |
| Układ współrzędnych | ETRS89-LAEA, EPSG:3035; L2 dodatkowo szerokość i długość WGS84 | zweryfikowane |
| Układ odniesienia L2b/L3 | ETRF2000 przez model A-EPND | zweryfikowane (Even 2024; Koudogbo 2025) |

### Nazewnictwo plików (Product Description)

- L2a/L2b: `EGMS_L2b_<ścieżka>_<burst>_IW<pas>_VV_<rok1>_<rok2>_<wersja>.zip`, w środku CSV.
  Przykład: `EGMS_L2b_088_0282_IW2_VV_2018_2022_1.zip`.
- L3: `EGMS_L3_E<XX>N<YY>_100km_<U|E>_<rok1>_<rok2>_<wersja>` (`.tif` i `.csv`), kafle 100 km.

### Kolumny CSV L2a/L2b (zweryfikowane w Product Description, tabela 5)

| Kolumna | Jednostka | Opis |
|---|---|---|
| `pid` | — | identyfikator punktu |
| `cluster_label` | — | tylko L2a |
| `mp_type` | m² | 0 = rozpraszacz trwały; >0 = powierzchnia rozpraszacza rozproszonego |
| `latitude`, `longitude` | ° | WGS84 |
| `easting`, `northing` | m | EPSG:3035 |
| `height` | m | wysokość ortometryczna (EGM2008) |
| `height_wgs84` | m | wysokość elipsoidalna |
| `line`, `pixel` | piksel | położenie w burście |
| `rmse` | mm | reszty szeregu względem modelu „wielomian 3. stopnia + sezonowość" |
| `temporal_coherence` | — | koherencja czasowa |
| `amplitude_dispersion` | — | wskaźnik dyspersji amplitudy |
| `incidence_angle` | ° | kąt padania |
| `track_angle` | ° | kąt ścieżki |
| `los_east`, `los_north`, `los_up` | — | kosinusy kierunkowe LOS |
| `mean_velocity` | mm/rok | z modelu „wielomian 1. stopnia + sezonowość" |
| `mean_velocity_std` | mm/rok | odchylenie prędkości |
| `acceleration`, `acceleration_std` | mm/rok² | przyspieszenie |
| `seasonality`, `seasonality_std` | mm | amplituda sezonowa |
| kolumny dat `yyyymmdd` | mm | przemieszczenie w dacie akwizycji |

L3 nie ma kolumn kątów ani wektora LOS; ma `pid`, `easting`, `northing`, `height`, `rmse`,
`mean_velocity`, `mean_velocity_std`, `acceleration`, `acceleration_std`, `seasonality`,
`seasonality_std` i kolumny dat.

**Niezweryfikowane:** konwencja znaku przemieszczenia LOS (dokument jej nie podaje).
Patrz testy w `docs/evidence/F4_metodyka.md`, sekcja 2.

### Oficjalne API (zalecane)

Źródło: notatnik `EGMS-API.ipynb` w repozytorium `copernicus-land/egms-api` (przeczytany w całości; ostatnia
zmiana 2026-04-29). **Kodu nie uruchamiałem**: nie mam tokenu, a serwer jest niedostępny z mojego środowiska.

| Element | Wartość |
|---|---|
| Adres bazowy | `https://egms.land.copernicus.eu/insar-api/archive` |
| Uwierzytelnienie | token CLMS API (plik JSON z `client_id`, `user_id`, `token_uri`, `private_key`) → JWT podpisany RS256 → token dostępu ważny 1 godzinę → nagłówek `Authorization: Bearer …` |
| Skąd token | konto na stronie CLMS, zakładka z tokenami API; instrukcja: https://eea.github.io/clms-api-docs/authentication.html |
| Listy dozwolonych wartości | `GET /levels`, `/releases`, `/swaths`, `/relative_orbits`, `/bursts`, `/directions`, `/tile_ids`, `/product_types` |
| Wyszukiwanie | `POST /search` z JSON; wymagane `levels` i `releases` |
| Filtry | `bbox` (lista par lon, lat; maks. 5° × 5°; **może być jeden punkt**), `relativeOrbit`, `direction`, `swath`, `burstCycle`, `tileId`, `productType` (`ORTHO-UP`, `ORTHO-EAST`) |
| Wynik | `hits` z `filename`, `filesize` (bajty, plik skompresowany), `bbox`, `poly`, `productLevel`, `release`, `burstId`, `relativeOrbit`, `direction`; oraz `id` zapytania |
| Pobranie | `GET {adres}/download/{filename}?id={id}`; identyfikator wygasa, gdy nie jest używany |
| Zapis poziomów i wydań w przykładach | `"L2B"`, `"L3"`, `"2019-2023"` (z łącznikiem) |

Co to rozwiązuje w naszym planie:
- zapytanie dla jednego punktu (współrzędne stacji) zwraca dokładnie te bursty, które ją pokrywają,
- `GET /releases` odpowiada, czy wydania 2018–2022 i 2020–2024 są dostępne,
- `filesize` podaje rozmiar przed pobraniem,
- `poly` pozwala sprawdzić, czy stacja leży w zakładce dwóch burstów.

Szkic zapytań (na podstawie oficjalnego notatnika; **nietestowany**, do sprawdzenia przy pierwszym uruchomieniu):

```python
# Przypadek 1: bursty L2B pokrywające stację, jedna ścieżka
query = {"id": None,
         "bbox": [[station_lon_deg, station_lat_deg]],   # jeden punkt
         "levels": ["L2B"],
         "releases": [egms_release],                      # zapis jak w GET /releases
         "relativeOrbit": relative_orbit}                 # typ wartości sprawdzić w GET /relative_orbits
# Przypadek 2: kafel L3 z pionem nad siecią reperów
query = {"id": None,
         "bbox": [[lon_min, lat_min], [lon_max, lat_max]],
         "levels": ["L3"],
         "releases": [egms_release],
         "productType": "ORTHO-UP"}
result = requests.post(f"{api_endpoint}/search", headers=headers, data=json.dumps(query)).json()
links = [f"{api_endpoint}/download/{hit['filename']}?id={result['id']}" for hit in result["hits"]]
```

Niezweryfikowane: dokładny zapis wydań i ścieżek w filtrach, limity pobierania, czas ważności identyfikatora zapytania.
Token to klucz prywatny: trzymaj go poza repozytorium i nie drukuj w notatniku.

### Pozostałe narzędzia pobierania

| Narzędzie | Uwagi | Status |
|---|---|---|
| EGMS-toolkit, https://github.com/alexisInSAR/EGMStoolkit | GPL-3.0; wersja 0.3.0 Beta (10.2025); Python 3, GDAL ≥ 3.8, GMT + GSHHG; usuwa duplikaty; korzysta z tokenu z EGMS Explorer, nie z tokenu CLMS API | zweryfikowane w kodzie: obsługuje wydania 2015_2021, 2018_2022, 2019_2023 |
| Ręcznie z EGMS Explorer | wybór burstów na mapie | zweryfikowane |

Przykład z dokumentacji EGMS-toolkit (opcje sprawdź poleceniem `EGMStoolkit -h`):

```
EGMStoolkit -l L2a,L2b -r 2018_2022 -t <token> -b <lon_min,lat_min,lon_max,lat_max> \
  -o ./data/01_Raw_EGMS --track 117 --pass Ascending --nomerging --noclipping --quiet --clean
```

Kolejność współrzędnych w `-b` wynika z przykładów w artykule (zachód, południe, wschód, północ);
dokumentacja nie podaje jej wprost. Token to 32-znakowy ciąg z końca dowolnego linku pobierania
w EGMS Explorer, ważny czasowo. **Nie zapisuj tokenu w repozytorium.**

## 2. GNSS

| Źródło | Co daje | Licencja / dostęp | Status |
|---|---|---|---|
| PANGAEA, Pintori i Serpelloni 2023, https://doi.org/10.1594/PANGAEA.958598 | dobowe szeregi pionowe stacji ciągłych w dorzeczu Padu, GAMIT/GLOBK, układ związany z Eurazją | CC BY 4.0; pliki `https://download.pangaea.de/dataset/958598/files/<ID>.txt`; paczka zbiorcza wymaga konta | lista stacji zweryfikowana: **PTO1 i CODI są, TGPO i VCCL nie ma**; okres wg opisu 01.2010–09.2022 (metadane podają też 1997–11.2022) |
| Fabris i Nazari 2026, tabela 2 | prędkości pionowe PTO1, TGPO, CODI | CC BY | zweryfikowane; `data/04_Reference/fabris2026_tab2_gnss_vertical.csv` |
| Nevada Geodetic Laboratory, https://geodesy.unr.edu | dobowe szeregi E, N, U tysięcy stacji, prędkości MIDAS | otwarte | obecność PTO1, TGPO, LORC, LRCA, CARG **niezweryfikowana** |
| EPN / EPN Densification, https://epncb.eu/_productsservices/timeseries | szeregi stacji EPN | otwarte | niezweryfikowane dla naszych stacji |
| „Lorca GNSS", katalog Copernicus in-situ, https://cis2.eea.europa.eu/data/825 | 17 stacji, IGN Hiszpania, dobowo od 2015 | **Restricted** | zweryfikowane |
| SAPOS Badenia-Wirtembergia, stacje SGW w Epe | użyte w Even 2024 | nieudostępniane | zweryfikowane |

Współrzędne stacji bierz z nagłówka pliku szeregu lub dziennika stacji.

Format NGL `tenv3` (z pamięci, do potwierdzenia przy pobraniu): jeden wiersz na dobę, kolumny
m.in. stacja, data, rok dziesiętny, wschód, północ, wysokość w metrach względem pozycji odniesienia
oraz ich niepewności.

## 3. Niwelacja — Holandia, portal NLOG (przypadek 2)

| Element | Wartość | Status |
|---|---|---|
| Strona | https://www.nlog.nl/meetplannen-en-meetregisters | zweryfikowane |
| Co zawiera | plany pomiarów i rejestry pomiarowe ruchu terenu przy wydobyciu gazu, ropy i soli; operatorzy mają obowiązek prawny pomiarów, rejestry trafiają do nadzoru SodM | zweryfikowane na stronie |
| Dostęp | bezpośrednie pobranie PDF, bezpłatnie; licencji strona nie podaje | zweryfikowane |
| Rejestr Strootbeekpark 2023 (Hengelo, Twenthe-Rijn) | https://www.nlog.nl/sites/default/files/2025-10/20240327_487387_meetregister_strootbeekpark_jaarlijks_2023_00.pdf | treść zweryfikowana; załącznik 5 nieodczytany |
| Rejestr Ganzebos – Marssteden – Usseler Es 2022 (ten sam obszar koncesji) | https://www.nlog.nl/sites/default/files/2025-10/20230302_480645_meetregister_ganzebos_-_marssteden_usseler_es_-_2022_00.pdf | istnienie zweryfikowane; nieczytany |
| Rejestr Schiermonnikoog 2024 (NAM) | https://www.nlog.nl/sites/default/files/2025-10/meetregister_schiermonnikoog_2024.pdf | zweryfikowane: 59 reperów, epoki 2006–2024, załącznik CSV, brak istotnego ruchu |
| Sieć Twenthe-Rijn (opis sieci niwelacyjnej) | https://www.nlog.nl/field-web/rest/field/document/3953470385 | odnośnik ze strony; nieotwierany |

Format danych w rejestrze Strootbeekpark: PDF. Wysokości NAP w epokach i współrzędne reperów są
w załączniku 5 („differentiestaat"); trzeba je przepisać. Układ współrzędnych holenderskich
pomiarów to zwykle RD (EPSG:28992); potwierdź w załączniku.

W rejestrze Schiermonnikoog kolumny załącznika CSV to: `Puntnr`, `X` (RD), `Y` (RD), `TYPE`,
`H_DD_MM_YYYY` (wysokość w epoce względem reperu odniesienia, w metrach).

## 4. Dane walidacyjne użyte przez EEA

Dokument „Validation Data Collection and Description" (CLMS) opisuje zbiory użyte w oficjalnej walidacji:
https://land.copernicus.eu/en/technical-library/validation-data-collection-and-description-document/@@download/file

| Zbiór | Dostęp wg dokumentu |
|---|---|
| Lorca, GNSS IGME: LORC (2011–2022), LRCA (2012–2022), ORCA (2016–2022), dobowe, 3 składowe | otwarte, wolne do redystrybucji; adresu pobrania brak |
| Lorca, GNSS CNIG (17 stacji) | na prośbę |
| Lorca, niwelacja: kampanie 2005, 2016, 2017 | licencji nie podano |
| Jutlandia, GNSS (DTU) | na prośbę |
| Wyspy Kanaryjskie, GNSS (CNIG) | na prośbę; część stacji otwarta |
| Thyborøn, reflektory i niwelacja co 3 lata od 2003 | na prośbę |
| Freyming-Merlebach, niwelacja coroczna od 2006 (ok. 1500 punktów, BRGM) | otwartej licencji nie podano |
| Navis, tachimetr automatyczny (Tyrol) | podgląd publiczny na portalu Tyrolu; licencji pobrania nie podano |

Czytałem streszczenie tego dokumentu zwrócone przez narzędzie, nie cały plik; przed powołaniem się
na warunki dostępu sprawdź odpowiedni rozdział.

## 5. Niwelacja NRW (przypadek zapasowy)

| Zbiór | Adres | Status |
|---|---|---|
| Punktliste mit Zeitfolge | https://www.opengeodata.nrw.de/produkte/geobasis/rb/fd/hfp_plzf_csv/ | zweryfikowane: `hfp_plzf.csv` (ok. 7,7 MB, plik z 21.08.2023), `Datenformatbeschreibung.pdf`, `Nutzerinformation.pdf` |
| Punktliste | https://www.opengeodata.nrw.de/produkte/geobasis/rb/fd/hfp_pl_csv/ | istnienie zweryfikowane |
| Höhenänderungen aus Sentinel-1 (2020–2024) | https://www.opengeodata.nrw.de/produkte/geobasis/bb/bbk_nrw/hoeae_s1/ | zweryfikowane: 155 kafli GeoPackage, EPSG:25832 |
| Bodenbewegungsgebiete | WMS `https://www.wms.nrw.de/geobasis/wms_nw_bodenbewegungsgebiete_kacheln`, WFS `https://www.wfs.nrw.de/geobasis/wfs_nw_bodenbewegungsgebiete_kacheln` | zweryfikowane |

Format CSV: UTF-8, separator `;`, tekst w cudzysłowach, przecinek dziesiętny, daty `dd.mm.rrrr`.

- Lista: `Punktkennzeichen; Name des Punktes; Ostwert [m]; Nordwert [m]; Höhe [m, DHHN2016]; Schwerewert [mgal]`.
- Szereg: `Punktkennzeichen; Messungsdatum; Höhe [m, DHHN2016]`, jeden wiersz na punkt i datę.

Niezweryfikowane: obecność wiersza nagłówka, układ współrzędnych `Ostwert/Nordwert`, najnowsza
data pomiaru (przykłady w opisie formatu sięgają 2015 r.), licencja wprost na stronie katalogu.
Strona Geobasis NRW podaje dla swoich danych licencję Datenlizenz Deutschland – Zero 2.0.

Uwaga wydawcy (`Nutzerinformation.pdf`, stan 07.2023): wartości z różnych punktów i dat są
tylko warunkowo porównywalne; do wiarygodnych wniosków potrzebna jest wiedza o specyfice
pomiarów i górnictwa. Kontakt: raumbezug@bezreg-koeln.nrw.de.

## 6. Czego nie ma w otwartym dostępie

- niwelacja RAG w niecce Prims (Saara) i niwelacja oraz GNSS w Epe,
- zestaw 17 stacji GNSS CNIG użyty przez EEA w Lorce (trzy stacje IGME są opisane jako otwarte, patrz sekcja 4),
- dane kampanijne PODELNET poza tym, co jest w artykule (ryc. 4 pokazuje prędkości 46 punktów, bez tabeli),
- dane kampanijne z Fernández i in. 2018.

## 7. Zasady przechowywania

```
data/01_Raw_EGMS/<wydanie>/<produkt>/...        # bez modyfikacji
data/02_Raw_Ground/1_gnss_pangaea/<stacja>.txt
data/02_Raw_Ground/2_levelling_hengelo/differentiestaat_2023.csv   # przepisane z PDF: strona, kto, kiedy
data/00_Metadata/MANIFEST.csv                         # plik, źródło (URL), data pobrania, SHA-256, licencja
data/03_Extracts/...                       # wyniki pośrednie z metadanymi
```
