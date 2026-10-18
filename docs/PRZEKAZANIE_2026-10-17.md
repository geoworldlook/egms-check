# Przekazanie kontekstu — stan na 2026-10-17

Notatka dla nowej sesji, która kontynuuje projekt EGMS Check w osobnym wątku. Najpierw przeczytaj `CLAUDE.md`
i `docs/MIGRACJA_stan_i_audyt.md`; ta notatka streszcza ustalenia z rozmowy, których nie ma w kodzie.

## Gałąź i sposób pracy

- Bieżąca gałąź robocza: `claude/dreamy-dirac-jd4vue` (zawiera wszystkie zmiany z 2026-10-15…17).
- Autor uruchamia notatniki w Colab (repozytorium sklonowane na Dysku), wyniki trafiają na Dysk,
  wykonane notatniki autor wysyła na GitHub (commity „Utworzono za pomocą Colab”). Przed pushem: `git pull`.
- Klon na Dysku ma `core.fileMode false` (Dysk gubi bity wykonywalności).
- Po każdej zmianie kodu: changelog; przy poprawkach tylko zmienione fragmenty.
- Preferencje autora: najpierw pytania doprecyzowujące, analogie przy nowych pojęciach, kod w Pythonie.
  Dokumenty dla autora: krótkie, proste, forma bezosobowa („zbadano, zrobiono”), bez założeń.

## Dwa przypadki i wyniki (informacyjnie; progi nie są zmieniane po wynikach)

**GNSS — Groningen, EGMS L2b Calibrated 2020–2024.** 35 stacji (27 osiadających, 8 stabilnych), 125 par.
K1 99% ✔, K2 4,7 ✔, K3 1,62 ✘ → werdykt CZĘŚCIOWO. Stacja AME1: sezonowość GNSS ±10 mm, w EGMS prawie niewidoczna.

**Niwelacja — zachodnia NRW, EGMS L3 Ortho 2019–2023.**
- Wariant główny (bezwzględny): N1 6,0 ✘, N2 77% ✘, N3 3,7 ✔, N4 −1,97 ✘.
- Wariant względny (odjęty wspólny ruch grupy 307 reperów stabilnych, −1,22 ± 0,05 mm/rok):
  N1 3,4 ✔, N2 94% ✔, N4 −1,00 ✔.
- Niecki: 54 repery, zgodność znaku 100%, nachylenie 0,98; całość nachylenie 0,96; MAD 1,04 vs Even 1,12.
- Pasy niepewności (bez progów): szum EGMS σ_dh = √2·rmse komórki, ±2σ → 12% (bezwzględnie) / 37% (względnie);
  pas empiryczny group_mad_dv 0,73 mm/rok × dt (±4,4 mm) → 32% / 67%.
- Reper stabilny 4804901107: −3,1 mm; wspólny ruch daje −3,8 mm; po odjęciu +0,8 mm — w pasie szumu (±1,1)
  i empirycznym (±4,6). Wyjaśnienie: to ruch całego regionu względem odniesienia, nie problem reperu.
- Największe rozbieżności w nieckach: 5104900368 (+23,5 mm, zaszumiona komórka EGMS ±8,5), 5104900601 (−14,4),
  5104900095 (−13,2).

## Pliki z tej rozmowy

- Kod: `step_05_colab_run.py` (konfiguracja `regions.nrw_west.levelling.uncertainty`, zadania niwelacji),
  `step_07_monitoring.py` (mapa L3, wykresy z pasami, rycina reperu stabilnego A/B/C).
- Notatniki pokazowe: `notebooks/Showcase_1_GNSS_Groningen.ipynb`, `notebooks/Showcase_2_Levelling_NRW.ipynb` (do 2026-10-17: Pokaz_1_*, Pokaz_2_*)
  (generator `build_colab_pokaz.py`; tylko czytają wyniki z Dysku). Testy: `tests/monitoring_harness/`.
- Raport na spotkanie: `docs/raport/EGMS_raport_spotkanie_2026-10-16.docx` (krótki, bezosobowy, 7 rycin).
- Tabela pilotaży i wdrożeń komercyjnych: `docs/raport/EGMS_pilotaze_i_komercyjne_2026-10-17.docx`.
- Decyzje: `docs/plans/Plan_v2_implementacja.md`, `docs/evidence/F10_NRW_niwelacja_EGMS.md`.

## Ustalenia merytoryczne spoza kodu

- Deutsche Bahn (DB InfraGO + GAF, pilotaż pod Monachium): EGMS w pasie 30 m wzdłuż toru + wilgotność gleby;
  dowód koncepcji, wymaga walidacji. Inne przykłady: HoSMoS (wały na Dunaju), Sensar (NL), Detektia (Genua,
  San Sebastián), BGS (iły pęczniejące), Aminjafari 2026 (Szwecja), EGU26-23130 (Irlandia), przegląd RSASE 37:101452.
- Polska: EGMS używa głównie PIG-PIB (InMoTeP) i środowisko górnicze (AGH, GIG); brak publicznego pilotażu
  u PKP PLK / GDDKiA. Przy szybkich osiadaniach górniczych EGMS zaniża ruch.
- Prawo UE nie wymaga EGMS; pośrednio: dyrektywa CER 2022/2557 (ocena ryzyka naturalnego), dyrektywa glebowa
  2025/2360, CCS 2009/31/WE. Obowiązek pomiaru osiadań jest krajowy (np. holenderskie prawo górnicze).
  Teksty dyrektyw nie zostały przeczytane w oryginale (EUR-Lex był niedostępny).

## Otwarte wątki (zaproponowane, niepotwierdzone przez autora)

- dopisać tabelę pilotaży do raportu,
- przeczytać w całości prace szwedzką i irlandzką,
- rycina |różnica| względem tempa ruchu dla niwelacji,
- sprawdzić art. 5 dyrektywy CER i przetargi PLK/GDDKiA na monitoring satelitarny.
