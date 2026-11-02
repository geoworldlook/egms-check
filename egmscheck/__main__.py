"""
Polecenia EGMS Check z wiersza poleceń (komputer lokalny, bez Colab):

    python -m egmscheck run        [--region R] [--stage-b] [--confirm NAZWA=WARTOŚĆ] [--data-dir DIR] [--dry-run]
    python -m egmscheck publish    [--data-dir DIR] [--no-git] [--message TEKST]
    python -m egmscheck selftest                                   testy bez sieci (tak samo w CI)
    python -m egmscheck settings                                   ustawienia po scaleniu
    python -m egmscheck approvals                                  stan zatwierdzeń CHECK_CONFIG
    python -m egmscheck test       [--work DIR] [--keep]           pełny test na atrapach serwerów

Ten sam parser co `python step_09_local.py …` (step_09_local.main), więc oba wejścia robią to samo.
Katalog danych: --data-dir, zmienna EGMSCHECK_DATA_DIR albo local_settings.json (docs/URUCHOMIENIE_LOKALNE.md).
"""

import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    sys.path.insert(0, str(CODE_DIR))          # moduły step_0N leżą w katalogu głównym repozytorium
    import step_09_local
    return step_09_local.main(argv, prog="python -m egmscheck")


if __name__ == "__main__":
    sys.exit(main())
