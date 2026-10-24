# TEST: jeden przebieg step_09_local.run na atrapach (proces uruchamiany przez run_local_test.py z PYTHONPATH =
# tests/monitoring_harness/fake, więc sitecustomize podmienia sieć: CLMS, EGMS, NGL, NRW, ASF, HyP3; MintPy = atrapa).
# Użycie: python driver.py <full|rerun|author> <katalog roboczy> <etap B: 1|0>
#   full   - konfiguracja testowa (APPROVE z prepare_notebook), potwierdzenia z plików atrapy, etap A (+ B),
#            na końcu kontrola znanej odpowiedzi (check_code z prepare_notebook);
#   rerun  - to samo drugi raz na tych samych danych (run_local_test.py sprawdza w logu, że nic nie poszło drugi raz);
#   author - konfiguracja autora (CHECK_CONFIG), bez potwierdzeń: z etapem B oczekiwany stop na potwierdzeniu zleceń
#            HyP3; bez etapu B etap A przechodzi (pliki EGMS już są na "Dysku" z przebiegów 1-2).
# Wartości testowe, nie wynik.
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CODE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CODE))
sys.path.insert(0, str(CODE / "tests" / "monitoring_harness"))
import prepare_notebook as pn  # noqa: E402
import step_05_colab_run as s5  # noqa: E402
import step_09_local as s9  # noqa: E402

mode, work, stage_b = sys.argv[1], Path(sys.argv[2]), sys.argv[3] == "1"
mb, mb_lev, jobs = pn.confirm_values(work / "fx")
settings = s9.load_settings(code_dir=work, data_dir=str(work / "data"), secrets_dir=str(work / "secrets"),
                            stage_b=stage_b, regions=None, confirm={})
cfg = s9.make_config(settings)

if mode in ("full", "rerun"):
    exec(pn.APPROVE, {"cfg": cfg, "CHECK_CONFIG": s5.CHECK_CONFIG, "approvals_table": s5.approvals_table,
                      "display": print})
    confirm = {f"CONFIRM_MB_{r.upper()}": v for r, v in mb.items()}
    confirm.update({f"CONFIRM_MB_{r.upper()}_LEVELLING": v for r, v in mb_lev.items()})
    confirm["CONFIRM_JOBS"] = jobs
    settings["confirm"] = confirm
    summ = s9.run(settings, cfg)
    assert summ["status"] == "ok" and set(summ["task_status"].values()) <= {"ok", "skipped"}, summ
    print(f"DRIVER {mode}: {len(summ['tasks'])} zadań, etap B {stage_b}, log {summ['log']}")
    if mode == "full":
        rt = s5.setup_runtime(str(CODE), [], str(work / "data"))
        exec(pn.check_code(jobs, stage_b=stage_b), {"rt": rt, "cfg": cfg, "pd": pd, "np": np, "Path": Path,
                                                    "region_paths": s5.region_paths, "PROJECT_DIR": str(work / "data")})
elif mode == "author" and stage_b:
    try:
        s9.run(settings, cfg)
    except RuntimeError as e:
        assert "Zlecenia HyP3 wstrzymane: po obejrzeniu planu ustaw CONFIRM_JOBS['37']" in str(e), e
        print(f"DRIVER author: oczekiwany stop: {e}")
    else:
        raise AssertionError("konfiguracja autora bez CONFIRM_JOBS nie może przejść etapu B")
elif mode == "author":
    summ = s9.run(settings, cfg)
    assert summ["status"] == "ok", summ
    print(f"DRIVER author: etap A z konfiguracją autora przeszedł ({len(summ['tasks'])} zadań)")
else:
    raise ValueError(f"nieznany tryb {mode}")
print(f"DRIVER {mode}: OK")
