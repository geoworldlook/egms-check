# Karta wyników EGMS Check

Stan na 2026-11-02 (wersja 1.0.0). Jedna tabela na eksperyment; wynik niespełniony wpisujemy tak samo jak spełniony.
Progi zapisano w kodzie **przed** obliczeniami i nie zmieniano ich po wynikach: E1 w konfiguracji notatnika
`notebooks/EGMS_Check.ipynb` (2026-10-10), wydanie 2020–2024 i niwelacja w `CHECK_CONFIG` (`step_05_colab_run.py`,
sekcja `thresholds`, zatwierdzona 2026-10-12). Pierwsze propozycje progów: `docs/archive/plans/Plan_v1_kryteria_akceptacji.md`.

Źródła liczb: E1 — `docs/evidence/F9_E1_interpretacja_wynikow.md` (przeliczone niezależnie z tabeli wyników,
`docs/archive/migracja/09_audyt_po_migracji.md`); wydanie 2020–2024 i niwelacja — pliki wynikowe przebiegu z 2026-10-15
(kod `06eeefc`), opublikowane w `docs/showcase/` razem z `egmscheck_results.json`; opis E2 —
`docs/evidence/F10_NRW_niwelacja_EGMS.md`.

Znak: ujemne = osiadanie / oddalanie od satelity. dv = v_GNSS − v_EGMS (mm/rok). „Para” = stacja × ścieżka satelity.

## E1 — EGMS L2b kontra GNSS, Groningen, wydanie 2019–2023 (główny test zarejestrowany przed obliczeniami)

35 stacji z reguły bez wyboru ręcznego (27 osiadających, 8 stabilnych); wynik ma 24 osiadające i 8 stabilnych.

| Kryterium | Wynik | Próg | Spełnione |
|---|---|---|---|
| K1 zgodność tempa: odsetek par z \|dv\| ≤ 1,5 mm/rok | 91% (n = 95 par) | ≥ 80% | tak |
| K2 zgodność szeregów: mediana odchylenia std różnicy | 4,7 mm (10–90%: 4,3–5,3) | ≤ 5 mm | tak, na granicy |
| K3 stacje stabilne: max \|v_EGMS\| | 2,22 mm/rok (n = 31 par) | ≤ 1,5 mm/rok | **nie** |
| K4 nachylenie v_EGMS względem v_GNSS (informacyjnie) | 0,96 (wyraz wolny +0,05) | ≈ 1 | — |
| Bias i rozrzut dv (informacyjnie) | mediana −0,18; MAD·1,48 = 0,86 mm/rok | — | — |

**Werdykt: CZĘŚCIOWO.** Tempo osiadania zgodne; sezonowość w EGMS stłumiona (kalibracja L2b do modelu GNSS).
K3 nie przeszło, bo stacje „stabilne” według MIDAS ruszają się w kierunku satelity także w GNSS; różnica
EGMS − GNSS przekracza próg tylko w 3 z 31 par. Werdykt zostaje, bo definicję K3 zapisano przed obliczeniami.

## E1b — to samo na wydaniu 2020–2024, Groningen (powtórka z regułą E1)

Kryteria jak E1; K3 jako max \|dv\| na stacjach stabilnych (decyzja autora 2026-10-12, po wnioskach z E1, przed
obliczeniami na tym wydaniu). Plik: `docs/showcase/verdict_gnss_l2b_groningen.csv`.

| Kryterium | Wynik | Próg | Spełnione |
|---|---|---|---|
| K1 zgodność tempa | 99% par (n = 93) | ≥ 80% | tak |
| K2 zgodność szeregów | mediana std różnicy 4,7 mm (n = 93) | ≤ 5 mm | tak |
| K3 stacje stabilne: max \|dv\| | 1,62 mm/rok (n = 32 pary) | ≤ 1,5 mm/rok | **nie** |
| K4 nachylenie (informacyjnie) | 0,94 (wyraz wolny −0,14; n = 125) | ≈ 1 | — |
| Bias i rozrzut dv (informacyjnie) | mediana −0,00; MAD·1,48 = 0,81 mm/rok | — | — |

**Werdykt: CZĘŚCIOWO** (K3 niespełnione o 0,12 mm/rok).

EGMS L3 pion kontra składowa pionowa GNSS (próg tylko dla K1): 96% par w progu 1,5 mm/rok (n = 24), nachylenie 0,96;
**K1 spełnione**. Plik: `docs/showcase/verdict_gnss_l3u_groningen.csv`.

## E2 — EGMS L3 pion kontra niwelacja państwowa, zachodnia NRW, wydanie 2019–2023 (test w pełni niezależny od GNSS)

Wszystkie repery z dwiema epokami w oknie wydania (głównie 05.2019 → 05.2022): 1491, z komórką EGMS 1216; bez wyboru
według EGMS. Pliki: `docs/showcase/levelling_summary_nrw_west_2019_2023*.csv`, `levelling_groups_*`.

| Kryterium | Wariant główny (bezwzględny) | Wariant dodatkowy (względem reperów stabilnych) | Próg |
|---|---|---|---|
| N1 mediana \|Δh_EGMS − Δh_niw\| | 6,0 mm (n = 1216) — **nie** | 3,4 mm (n = 909) — tak | ≤ 5 mm |
| N2 zgodność znaku (\|Δh_niw\| ≥ 6 mm) | 77% (n = 559) — **nie** | 94% (n = 559) — tak | ≥ 90% |
| N3 repery stabilne: mediana \|Δh_EGMS\| | 3,7 mm (n = 307) — tak | nie dotyczy (tworzą grupę odniesienia) | ≤ 5 mm |
| N4 bias prędkości v_EGMS − v_niw | −1,97 mm/rok (n = 1216) — **nie** | −1,00 mm/rok (n = 909) — tak | \|bias\| ≤ 1,5 mm/rok |
| Rozrzut różnic prędkości (informacyjnie) | MAD·1,48 = 1,04 mm/rok | 1,05 mm/rok | — |
| Nachylenie Δh_EGMS względem Δh_niw (informacyjnie) | 0,96 ± 0,01 (zakres −140 … +25 mm) | 0,96 ± 0,01 | ≈ 1 |

- **Niecki** (54 repery z \|v_niw\| ≥ 10 mm/rok): zgodność znaku 100%, nachylenie 0,98; w wariancie względnym mediana
  różnicy 2,6 mm przy ruchu 30–140 mm.
- **Przesunięcie** grupy 307 reperów stabilnych według niwelacji: EGMS − niwelacja = −1,22 ± 0,05 mm/rok.
- **Werdykt wariantu głównego: niespełnione N1, N2, N4.** Przyczyną jest jedno zjawisko: stałe przesunięcie ok.
  −2 mm/rok między EGMS a układem niwelacji. Wariant względny policzono **po** obejrzeniu wariantu głównego, dlatego
  jest raportowany obok niego i nie zmienia werdyktu. Przyczyna przesunięcia (różnica układów odniesienia) to hipoteza.

Porównanie na wydaniu głównym 2020–2024: tylko 13 reperów ma dwie epoki w oknie wydania (N1 1,0 mm, N4 −0,91 mm/rok,
N2 niepoliczalne) — za mało, żeby z tego wnioskować; dlatego drugie wydanie (2019–2023) do niwelacji.

## GNSS w zachodniej NRW (wydanie 2020–2024)

**NIEROZSTRZYGNIĘTE:** w obszarze nie ma stacji GNSS osiadających, które spełniają regułę jakości, więc K1 jest
niepoliczalne. Na 3 parach stacji stabilnych K3 spełnione (informacyjnie). Plik: `docs/showcase/verdict_gnss_l2b_nrw_west.csv`.

## Obserwacje bez progu (opisowo; nie są dowodem)

| Co | Wynik | Uwagi |
|---|---|---|
| Pasy niepewności EGMS na niwelacji NRW (±2σ, σ_Δh = √2 · rmse komórki L3) | w pasie 12% reperów (37% po odjęciu przesunięcia) | `rmse` z EGMS opisuje tylko szum wokół modelu EGMS; jest zbyt optymistyczny wobec pomiaru naziemnego |
| Pas empiryczny (rozrzut różnic tempa na reperach stabilnych, 0,73 mm/rok × Δt) | w pasie 32% (67% po odjęciu przesunięcia) | drugi pas dodany po obejrzeniu pierwszego; informacyjnie |
| Czas do wykrycia trendu 2σ (AR(1)), Groningen, stacje osiadające | EGMS L2b: mediana 9 mies. (start 2020-01) i 12 mies. (start 2022-01, po końcu Sentinel-1B); GNSS w LOS: 18 mies. | ten sam test zaznacza też 69–94% par **stacji stabilnych** w EGMS (GNSS 56–72%), więc nie odróżnia ruchu od stabilności; do zmiany metody przed użyciem |
| Próbkowanie EGMS L2b po 23.12.2021 | co 12 dni zamiast 6 (mediana odstępu) | koniec Sentinel-1B; większy szum pojedynczej daty |

## Kolejne wiersze

| Krok | Co porównamy |
|---|---|
| Następne wydanie EGMS | te same reguły (K1–K4, N1–N4) na nowym wydaniu, bez zmiany progów |
| Etap B (ASF HyP3 + MintPy) | własne szeregi Sentinel-1 2024–2026 dla Groningen (ścieżki 37 i 88) wobec EGMS (zakładka 2024) i GNSS |
| Przesunięcie −2 mm/rok w NRW | hipoteza układów odniesienia: ruch punktów nawiązania sieci niwelacyjnej, porównanie z wydaniem 2020–2024 |
