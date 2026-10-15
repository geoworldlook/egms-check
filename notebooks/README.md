# Notatniki

Wszystkie notatniki są generowane skryptami w katalogu głównym i nie są edytowane ręcznie.

| Notatnik | Generator | Do czego |
| --- | --- | --- |
| `EGMS_Monitoring.ipynb` | `build_colab_monitoring.py` | obliczenia: pobranie EGMS, GNSS i niwelacji, porównania, ryciny (Groningen, zachodnia NRW) |
| `Pokaz_1_GNSS_Groningen.ipynb` | `build_colab_pokaz.py` | pokaz na spotkanie: EGMS L2b kontra GNSS w Groningen |
| `Pokaz_2_Niwelacja_NRW.ipynb` | `build_colab_pokaz.py` | pokaz na spotkanie: EGMS L3 kontra niwelacja w NRW (wydanie 2019–2023) |
| `EGMS_Check.ipynb` | `build_colab_master.py` | pierwszy etap projektu (E1) |

Notatniki pokazowe tylko czytają wyniki zapisane na Dysku przez `EGMS_Monitoring.ipynb`; kod jest ukryty w formularzach
Colab, a liczby w podsumowaniach są czytane z plików wyników.

Zasady: wykonanie od góry do dołu; obliczenia w modułach `step_NN`, ryciny w `data/05_Final_Outputs/egmscheck/`.
