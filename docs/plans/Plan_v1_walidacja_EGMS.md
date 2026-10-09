# Plan v1 — walidacja EGMS na stacji GNSS i reperach (EGMS Check v1.0)

Status: PROPOSED, 2026-10-09. Zakres: dwa miejsca (PTO1 w delcie Padu, repery w Hengelo), produkty EGMS
Calibrated i Ortho, dane wyłącznie otwarte. Architektura przeniesiona z AgriWatch v1.0
(Colab, rejestr na Dysku, notatnik generowany).

Podstawa: przegląd sześciu publikacji w pełnym tekście (`docs/evidence/F1_przeglad_literatury_EGMS.md`)
i raport niwelacyjny z portalu NLOG. Kodu jeszcze nie ma.

## 1. Pytanie

Czy darmowe dane EGMS podają to samo osiadanie co pomiar naziemny, i czy da się to pokazać na danych,
które każdy może pobrać?

## 2. Części planu

| Dokument | Co rozstrzyga |
|---|---|
| `Plan_v1_test_EGMS.md` | trzy twierdzenia (T1 GNSS, T2 repery, T3 pokrycie), progi, reguła decyzji |
| `Plan_v1_dane_do_pobrania.md` | zamknięta lista plików z adresami i ścieżkami |
| `Plan_v1_potok.md` | etapy, moduły `step_NN`, testy, kolejność |
| `Plan_v1_kryteria_akceptacji.md` | progi do zatwierdzenia przed pierwszym przebiegiem |
| `Plan_v1_otwarte_pytania.md` | rzeczy niezweryfikowane i decyzje autora |
| `Plan_v1_wpis_na_blog.md` | wymagania i układ wpisu na blog GeoWorldLook |
| `Plan_v1_wdrozenie.md` | plan wdrożenia: ustalenia z danych i źródeł, decyzje blokujące, poprawki sesji |
| `Instrukcja_startowa.md` | przygotowanie i kolejność sesji |
| `Prompty_Claude_Code.md` | gotowe prompty, po jednym na sesję |

## 3. Kolejność

1. Bramki wykonalności (`Plan_v1_otwarte_pytania.md`, sekcja A) i pobranie danych.
2. Zatwierdzenie progów (`Plan_v1_kryteria_akceptacji.md`); wpis w protokole w `Plan_v1_test_EGMS.md`.
3. Przeniesienie szkieletu z AgriWatch: `step_05` (`setup_runtime`, `run_task`, rejestr), `build_colab_master.py`.
4. Przypadek 1 (GNSS): `step_01` → `step_02` → `step_03` → wykres.
5. Wpis na blog z przypadkiem 1.
6. Przypadek 2 (repery): przepisanie tabeli → `step_04` → wykresy → prognoza.
7. `step_06`: biuletyn, JSON dla strony, `run_summary.md`. Aktualizacja `docs/ARCHITEKTURA.md` do stanu kodu.

## 4. Czego nie robimy (i dlaczego)

- Własnego przetwarzania InSAR: sprawdzamy gotowy produkt, nie budujemy konkurencyjnego.
- Lorki i NRW w wersji 1.0: brak potwierdzonych otwartych danych naziemnych o wymaganych cechach
  (`docs/evidence/F6_przypadki_zapasowe/`).
- Wniosków o zdarzeniach nagłych: EGMS jest aktualizowany raz w roku.

## 5. Decyzje do zatwierdzenia

Progi oznaczone **[propozycja]**, model prędkości, agregacja GNSS, odniesienie w Hengelo, nazwa projektu,
język wpisu. Lista: `Plan_v1_otwarte_pytania.md`, sekcje A2 i D.
