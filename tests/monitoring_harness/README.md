# Test notatnika `notebooks/EGMS_Monitoring.ipynb` poza Colab

Atrapy: CLMS (token), EGMS API (wyszukanie L2B/L3 w prostokącie, pobranie), NGL (MIDAS, tenv3), pliki niwelacji NRW,
`asf_search`, `hyp3_sdk.HyP3`, `smallbaselineApp.py` (MintPy) i Dysk Google. Dane testowe mają **znaną odpowiedź**
(`make_fixtures.py`); służą wyłącznie do sprawdzenia kodu, nigdy jako wynik.

```bash
# środowisko jak Colab: zob. tests/colab_harness/README.md (venv colab313 z jądrem colab313)
# dodatkowo: colab313/bin/pip install rasterio h5py hyp3_sdk asf_search
tests/monitoring_harness/run_harness.sh <ścieżka do colab313/bin/python> <katalog roboczy, usuwany>
```

Cztery przebiegi:
1. pełny notatnik od zera na kopii z zatwierdzeniami `TEST` i wartościami `CONFIRM_*` → `HARNESS: znana odpowiedź OK`;
2. ponowne uruchomienie na tym samym Dysku → nic nie jest pobierane ani zlecane drugi raz (MIDAS z migawki na Dysku),
   wycinki obu regionów nie są liczone od nowa;
3. notatnik z repozytorium (konfiguracja autora, bez `CONFIRM_JOBS`) → etap A przechodzi, stop na potwierdzeniu zleceń HyP3.
4. notatniki pokazowe `notebooks/Showcase_1_GNSS_Groningen.ipynb` i `notebooks/Showcase_2_Levelling_NRW.ipynb` (tylko odczyt wyników z przebiegów 1–3) → werdykt, tabele, podsumowanie liczbowe, ryciny, kod ukryty w formularzach.

Uwaga: skrypt usuwa i tworzy od nowa `/content/drive/MyDrive/GeoWorldLook/egmscheck` (atrapa Dysku).
