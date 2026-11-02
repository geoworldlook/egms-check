# 3. Metoda E1 i zapisane decyzje

> EGMS Check (GeoWorldLook) — przekazanie projektu, stan 2026-10-10, gałąź `claude/dreamy-dirac-jd4vue`.
> Indeks: [`../MIGRACJA_stan_i_audyt.md`](../MIGRACJA_stan_i_audyt.md)

### 3.1 Metoda (według Koudogbo i in. 2025, oficjalny raport walidacji EGMS 2019–2023)

1. Punkty EGMS L2b w promieniu 100 m od stacji (200 m jako test wrażliwości), co najmniej 3 punkty; szereg
   EGMS = mediana punktów w każdej dacie.
2. GNSS E, N, U rzutowane na kierunek satelity: `d = E·los_east + N·los_north + U·los_up` (średni wektor LOS
   punktów w buforze).
3. GNSS w datach EGMS: mediana dób w oknie ±6 dni; wspólne okno; wspólna data odniesienia.
4. Prędkość obu szeregów tym samym modelem: trend liniowy + sinusoida roczna.
5. `dv = v_GNSS,LOS − v_EGMS`; odchylenie standardowe różnicy szeregów; korelacja.
6. Kontrole blokujące przed porównaniem: A1 (norma LOS = 1), A2 (`los_up` = cos kąta padania), A3 (przeciwny
   znak `los_east` na orbitach wst./zst.), A5 (duplikaty z zakładek burstów < 1 m). A6 (pokrycie ≥ 85%
   w obu definicjach: wspólne okno / okres wydania oraz daty z GNSS / wspólne okno) filtruje pary.

### 3.2 Reguła wyboru stacji (zatwierdzona 2026-10-10)

- Wspólne warunki: dane GNSS od ≤ 2019.0 do ≥ 2024.25; niepewność vu (MIDAS) ≤ 1,0 mm/rok; ≤ 2 skoki.
- **Osiadające:** wszystkie stacje w prostokącie 5,8–7,3° E, 52,9–53,6° N z vu ≤ −2 mm/rok → 27 stacji.
- **Stabilne (kontrola negatywna):** |vu| ≤ 1,0 mm/rok w prostokącie 4,8–8,3° E, 52,4–54,0° N; 8 najbliższych
  stacji osiadającej → SCHI, NORG, BLLM, TGEM, TGBF, AMEL, TGWE, RDN1 (vu od −0,90 do +0,07 mm/rok).
- Źródło: `https://geodesy.unr.edu/velocities/midas.IGS.txt` (IGS20; dane do 2024.646).

### 3.3 Kryteria (stan: K1 i K3 **czekają na potwierdzenie autora**)

| | Kryterium | Próg | Źródło progu |
|---|---|---|---|
| K1 | odsetek par stacja × ścieżka (osiadające) z \|dv\| ≤ 1,5 mm/rok | ≥ 80% | 1,5 mm/rok: Fabris i Nazari 2026 za Fiaschi i in. 2018; **80%: propozycja** |
| K2 | mediana odchylenia standardowego różnicy szeregów | ≤ 5 mm | Crosetto i in. 2025 (White Paper) |
| K3 | stacje stabilne: max \|v_EGMS\| | ≤ 1,5 mm/rok | **propozycja** |
| K4 | nachylenie v_EGMS względem v_GNSS | raportowane | — |

Wniosek: POTWIERDZONE (K1, K2, K3) / CZĘŚCIOWO (tylko K1) / NIE POTWIERDZONE.
