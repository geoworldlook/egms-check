# Plan v1 — wpis na blog GeoWorldLook

Status: PROPOSED, 2026-10-09. Część planu `Plan_v1_walidacja_EGMS.md`.

Wynik ma później trafić na blog jako przykład zastosowania, w formie takiej jak wpis
https://geoworldlook.vercel.app/blog/1_wpis_testowy_test-sar-colab

## Format istniejącego wpisu (stan z 2026-10-09)

- Nagłówek z polami: `title`, `date`, `tags`, `summary`, `readTime`.
- Treść jak notatnik: krótkie akapity, komórki kodu w Pythonie, pod każdą wydruk lub rycina PNG.
- Sekcje jako nagłówki drugiego poziomu. Tekst po polsku, nawigacja strony po angielsku.
- Brak odnośnika do Colab i do repozytorium, brak podsumowania; dane są symulowane.

Wpis o EGMS powinien zachować ten format, ale pracować na prawdziwych danych, mieć źródła,
odnośnik do notatnika i wnioski.

## Wymagania, które zmieniają plan pipeline'u

1. **Wynik w formie notatnika.** Jeden notatnik `notebooks/EGMS_Check.ipynb`, generowany przez
   `build_colab_master.py` jak w AgriWatch; wykonuje się od góry do dołu i zostawia wydruki oraz ryciny.
2. **Notatnik działa także bez tokenu.** Z tokenem CLMS zadanie `ingest_egms` pobiera pliki przez API; bez tokenu
   zadanie zgłasza to wprost w `gwl_runs`, a kolejne zadania korzystają z wycinków w repozytorium.
   Notatnik czyta małe wycinki z `data/03_Extracts/` (punkty z bufora wokół stacji, punkty przy reperach).
3. **Małe pliki w repozytorium.** Wycinki mają mieścić się w repozytorium publicznym i ładować
   w Colab z adresu repozytorium.
4. **Powtarzalność.** Brak losowości; wersje bibliotek przypięte w pierwszej komórce.
5. **Ryciny jako PNG** o stałych nazwach w `data/05_Final_Outputs/egmscheck/figures/`, z podpisami po angielsku w osiach.

## Proponowany układ wpisu

| Sekcja | Zawartość | Kod |
|---|---|---|
| Pytanie | czy darmowe dane radarowe mierzą osiadanie tak samo jak pomiar naziemny | — |
| Dane | tabela: źródło, instytucja, licencja, okres | — |
| Metoda | trzy kroki: punkty wokół miejsca pomiaru → ten sam kierunek i odniesienie → nałożenie | — |
| Przypadek 1: stacja GNSS | wczytanie wycinków, rzut na LOS, wykres główny, różnica, prędkości | 3–4 komórki |
| Przypadek 2: repery | wczytanie tabeli reperów, szeregi wybranych reperów, wykres rozrzutu, prognoza kontra pomiar | 4–5 komórek |
| Co się nie zgadza | rozbieżności i znane granice metody | — |
| Wnioski | co wynik pokazuje, czego nie pokazuje | — |
| Jak odtworzyć | odnośnik do notatnika i repozytorium, lista danych | — |
| Źródła | publikacje i wymagane atrybucje | — |

Przykładowy nagłówek:

```
title: "Czy EGMS mierzy osiadanie? Test na stacji GNSS i reperach"
date: <data publikacji>
tags: [InSAR, EGMS, Sentinel-1, GNSS, Python, Colab]
summary: "Dwa otwarte zbiory pomiarów naziemnych nałożone na dane European Ground Motion Service."
readTime: <po napisaniu>
```

## Atrybucje i licencje

| Dane | Warunek | Status |
|---|---|---|
| EGMS (Copernicus Land Monitoring Service) | dane bezpłatne i otwarte; wymagane podanie źródła | brzmienie formuły sprawdź na stronie CLMS przed publikacją |
| PANGAEA, Pintori i Serpelloni 2023 | CC BY 4.0: cytowanie z DOI | zweryfikowane na stronie zbioru |
| Fabris i Nazari 2026 (liczby do porównania) | CC BY: cytowanie | zweryfikowane |
| Raport Strootbeekpark (NLOG) | licencja niepodana | cytuj i linkuj; pokazuj własne wykresy z przepisanych wartości, nie wklejaj mapy ani stron raportu; przed publikacją wycinka z wartościami reperów rozważ zapytanie do NLOG |

## Co trafia do repozytorium publicznego

Projekt jest własny i w całości na danych otwartych, więc repozytorium i wpis mogą zawierać komplet:
kod, wycinki danych, wykresy i progi. Poza repozytorium zostają tylko surowe pliki EGMS (rozmiar)
i token.

Wzorem AgriWatch zadanie `bulletin` zapisuje dla strony: `bulletin.md`, ryciny PNG i
`egmscheck_latest.json` w `data/05_Final_Outputs/egmscheck/`.

## Decyzje do podjęcia

1. Język tekstu wpisu (istniejący wpis testowy jest po polsku). Jak w AgriWatch: opisy i komentarze po polsku, opisy osi wykresów po angielsku.
2. Jeden wpis z dwoma przypadkami czy dwa osobne wpisy. Proponuję zacząć od przypadku 1 jako
   samodzielnego wpisu; przypadek 2 dołączyć, gdy tabela reperów będzie gotowa.
3. Nazwa projektu i repozytorium (robocza: `2_geoworldlook-egmscheck`, „EGMS Check").
