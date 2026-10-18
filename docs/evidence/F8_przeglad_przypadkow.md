# F8 — Przegląd przypadków: przyczyna osiadania, dane, stan

> **Data:** 2026-10-10 · **Status:** `Draft` — zestawienie przypadków rozważanych w projekcie (stare konto),
> z przyczyną osiadania i stanem prac. Źródła: `F2`, `F3`, `F6_przypadki_zapasowe/`, `Plan_v1_eksperymenty.md`,
> `docs/migracja/`. Poziom weryfikacji w kolumnie „Źródło”.

## 1. Zestawienie

| # | Przypadek | Przyczyna osiadania | Tempo | Pomiar naziemny | Opublikowana walidacja EGMS | Niezależny od kalibracji EGMS? | Stan |
|---|---|---|---|---|---|---|---|
| 1 | **Groningen (NL)** — E1 | wydobycie gazu ziemnego (pole Groningen) ¹ | GNSS vu −2,3 do −6,8 mm/rok (27 stacji) | 35 stacji GNSS NGL (otwarte) | metoda: Koudogbo i in. 2025 | częściowo — L2b kalibrowany GNSS, niecka w skali siatki kalibracji (~50 km) | **wykonany: CZĘŚCIOWO** (K1 91%, K2 4,7 mm, K3 ✘) |
| 2 | **Delta Padu (IT)** — PTO1, TGPO, CODI | kompakcja młodych osadów deltowych, wzmocniona dawnym wydobyciem wód metanonośnych ¹ | PTO1 −5,2; TGPO −6,0; CODI −3,0 mm/rok (2018–2022) | GNSS PANGAEA (CC BY 4.0), NGL | Fabris i Nazari 2026 (tabele 3–4: liczby punktów i średnie w buforach) | częściowo (GNSS) | **wstrzymany**: GNSS kończy się 2021-04 (PANGAEA) / 2019-07 (NGL); pokrycie wydań z API 46% i 26% < 85%; wydania 2018–2022 nie ma w API |
| 3 | **Hengelo (NL)** — pole solne Twenthe-Rijn | eksploatacja soli przez ługowanie (kawerny solne, Nobian) | do −42 mm w 3 lata, ok. 14 mm/rok (reper 7008; przeliczenie własne) | niwelacja precyzyjna, 50 reperów, epoki 12.2020, 06.2022, (12.2022?), 12.2023 (NLOG, PDF) | **brak** | **tak** — niwelacja względem reperu odniesienia | plan; blokada: przepisanie załącznika 5 z PDF (~50 wierszy); licencja niepodana |
| 4 | **Zachodnia NRW (DE)** | obniżanie wód podziemnych wokół odkrywek węgla brunatnego; na zachodzie **wypiętrzanie** po zatopieniu kopalń węgla kamiennego; kawerny w Epe (ruch nieliniowy) | strefy ruchu > ±3 mm/rok | niwelacja państwowa NRW (`hfp_plzf.csv`, otwarte) | Even i in. 2024: 279 reperów, bias 0,93 mm/rok, σ 1,76 mm | **tak** (różnice względem reperu) | plan; blokada: epoki niwelacji po 2019 niezweryfikowane; publikacja użyła EGMS 2015–2021 (poza API) |
| 5 | **Lorca (ES)** | nadmierny pobór wód podziemnych (wyczerpywanie warstwy wodonośnej) | najszybsze w Europie: do 9 cm/rok (Fernández 2018); NGL: LOR1 −64, LRC1 −22,4 mm/rok | GNSS: LOR1, LRC1 w NGL (otwarte) ²; sieć IGN „Lorca GNSS” zastrzeżona | Koudogbo i in. 2025 (ORCA: dv 1,3 i 5 mm/rok na ścieżkach 103 i 001) | **praktycznie tak** dla niecki — lokalna niecka (kilka km, dziesiątki mm/rok) jest za mała i za szybka, by wytworzyła ją kalibracja 50 km | plan; ten sam kod co E1 (zmiana `CFG`); ok. 7,4 GB EGMS; ryzyko: ruch poziomy (~28% pionu) i błędy rozwinięcia fazy przy szybkim ruchu |
| 6 | **Schiermonnikoog (NL)** — kontrola negatywna | brak istotnego ruchu (rejestr NAM) | ≈ 0 | niwelacja, 59 reperów, epoki co 3 lata 2006–2024, CSV w załączniku (NLOG) | brak | tak | pomysł; dobry do pokazania „EGMS nie widzi ruchu tam, gdzie go nie ma” |

¹ Przyczyna z wiedzy ogólnej (Groningen, delta Padu) — powszechnie opisana, ale w repozytorium nie ma cytatu;
potwierdzić źródłem przed slajdem. Przyczyny dla 3–6 pochodzą z dokumentów w `docs/evidence/`.
² Prędkości LOR1 i LRC1 z listy MIDAS NGL (sesja 2026-10-10, `docs/migracja/06_otwarte_decyzje.md`); dostępność
szeregów w oknie 2019–2023 sprawdzić regułą z E1 przed decyzją.

## 2. Ocena na spotkanie

| Przypadek | Siła sygnału | Niezależność | Gotowość | Komentarz |
|---|---|---|---|---|
| Groningen | średnia (2–7 mm/rok) | częściowa | **gotowy** | wynik jest; pokazać z zastrzeżeniem kalibracji i K3 |
| Lorca | **bardzo duża** (20–70 mm/rok) | praktycznie pełna dla niecki | szybki: ten sam notatnik, nowy region i pobranie | najmniej nowego kodu; opublikowany punkt odniesienia (Koudogbo 2025) |
| Hengelo | duża (do 14 mm/rok) | **pełna** | wolniejszy: ręczne przepisanie PDF, nowy kod E2 | najlepsza historia „operator mierzy niwelacją, EGMS widzi to samo” |
| NRW | średnia | pełna | niepewny (epoki) | najlepszy naukowo, ryzyko braku epok |
| Schiermonnikoog | brak (kontrola) | pełna | wolniejszy (PDF/CSV, kod E2) | uzupełnienie do Hengelo |
| Delta Padu | średnia | częściowa | zablokowany danymi | nie wraca bez wydania 2018–2022 |

## 3. Decyzje potrzebne przed wyborem (zasada 2 `CLAUDE.md`)

- Który przypadek jako drugi: Lorca (szybko, GNSS) czy Hengelo (niezależna niwelacja, wolniej).
- Dla Lorki: region i reguła wyboru stacji, wydanie (2019–2023 jak E1), progi — te same co E1 czy inne
  (1,5 mm/rok przy osiadaniu 60 mm/rok jest bardzo surowe); ustalić **przed** pobraniem.
- Dla Hengelo: wydanie (2020–2024), produkt (L3 pion / L2b), promień, reper odniesienia, progi T2.
