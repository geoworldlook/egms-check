"""
EGMS Check — czy EGMS (Sentinel-1 InSAR, Copernicus) zgadza się z pomiarem naziemnym: GNSS i niwelacja.

Pakiet to wspólne polecenia projektu (standard GeoWorldLook, D-095):

    python -m egmscheck run        wszystkie zadania etapu A (opcjonalnie B) na danych z katalogu danych
    python -m egmscheck publish    wybrane wyniki do docs/showcase/ i na GitHub
    python -m egmscheck selftest   testy bez sieci wszystkich modułów
    python -m egmscheck settings   ustawienia po scaleniu

Obliczenia są w modułach step_00 … step_09 w katalogu głównym repozytorium (ten sam kod co w notatnikach Colab);
pakiet ich nie kopiuje, tylko wywołuje. Opis: docs/ARCHITEKTURA.md.
"""

__version__ = "1.0.0"
