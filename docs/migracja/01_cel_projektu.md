# 1. Cel projektu

> EGMS Check (GeoWorldLook) — przekazanie projektu, stan 2026-10-10, gałąź `claude/dreamy-dirac-jd4vue`.
> Indeks: [`../MIGRACJA_stan_i_audyt.md`](../MIGRACJA_stan_i_audyt.md)

Sprawdzić na otwartych danych, czy EGMS (European Ground Motion Service, Copernicus) wiarygodnie pokazuje
**powolne osiadanie terenu**, czyli czy nadaje się do jego monitorowania z kosmosu. Wynik ma posłużyć jako
przykład zastosowania na blogu GeoWorldLook i do prezentacji na spotkaniu.

Dwa eksperymenty:

| | Eksperyment | Dane naziemne | Pytanie |
|---|---|---|---|
| **E1** | walidacja na GNSS | stacje GNSS z Nevada Geodetic Laboratory (NGL) w rejonie pola gazowego Groningen | czy EGMS podaje to samo tempo osiadania co GNSS i nie pokazuje osiadania tam, gdzie GNSS go nie widzi? |
| **E2** | walidacja na osiadaniu zmierzonym niwelacją | rekomendacja: niwelacja NRW (otwarte dane); alternatywa: Hengelo (NLOG) | czy EGMS zgadza się z niezależnym pomiarem wysokości reperów? |

Zasady stałe (szczegóły: `CLAUDE.md`): dane otwarte z manifestem i SHA-256; progi zatwierdzone przed
obliczeniami i niezmieniane po wynikach; błąd głośny zamiast wartości zastępczych; brak danych wymyślonych;
sformułowanie „pomiar naziemny potwierdza tempo osiadania widoczne w EGMS”.
