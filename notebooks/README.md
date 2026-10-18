# Notebooks

All notebooks are created by scripts in the main folder. Do not edit them by hand.

| Notebook | Created by | What it is for |
| --- | --- | --- |
| `Showcase_1_GNSS_Groningen.ipynb` | `build_colab_pokaz.py` | short summary: EGMS L2b compared with GNSS stations in Groningen |
| `Showcase_2_Levelling_NRW.ipynb` | `build_colab_pokaz.py` | short summary: EGMS L3 compared with levelling in North Rhine-Westphalia (release 2019–2023) |
| `EGMS_Monitoring.ipynb` | `build_colab_monitoring.py` | calculations: download of EGMS, GNSS and levelling data, comparisons, figures (Groningen, western NRW) |
| `EGMS_Check.ipynb` | `build_colab_master.py` | first stage of the project (experiment E1) |

The showcase notebooks only read results that `EGMS_Monitoring.ipynb` saved on Google Drive. Their code is hidden in
Colab forms, and every number in their summaries is read from the result files.

The two technical notebooks (`EGMS_Monitoring`, `EGMS_Check`) are in Polish.

Rules: run notebooks from top to bottom; the calculations live in the `step_NN` modules, and the figures are saved in
`data/05_Final_Outputs/egmscheck/`.
