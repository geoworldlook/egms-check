# Pełny test obliczeń lokalnych (`step_09_local.py`)

Windows, macOS i Linux, bez Colab i bez `/content`. Atrapy serwerów i dane o **znanej odpowiedzi** pochodzą
z `tests/monitoring_harness` (te same co w teście notatnika); służą wyłącznie do sprawdzenia kodu, nigdy jako wynik.

```bat
conda activate egmscheck
python step_09_local.py test            :: albo: python tests\local_harness\run_local_test.py --keep
```

Kroki:

0. selftesty wszystkich modułów (`step_0N --selftest`, `step_09_local`);
1. dane testowe (`make_fixtures.py`), atrapa klucza CLMS i danych Earthdata, pusty katalog danych osobno od kodu;
2. **przebieg 1:** etap A i B od zera z konfiguracją testową i potwierdzeniami z plików atrapy, potem kontrola znanej
   odpowiedzi (`prepare_notebook.check_code`: grupy stacji, kontrole, werdykty K1–K3 i N1–N4, wariant względny,
   niepewność, czas do wykrycia, dowiązanie HyP3, `run_summary.md`);
3. **przebieg 2:** ponownie na tych samych danych: nic nie jest pobierane, wycinki nie są liczone od nowa, zlecenia
   HyP3 nie są wysyłane drugi raz, MIDAS z migawki;
4. **przebieg 3:** konfiguracja autora (`CHECK_CONFIG`) bez potwierdzeń: etap A przechodzi, stop na zleceniach HyP3;
5. katalog kodu bez zmian (wyniki tylko w katalogu danych).

Wynik: `TEST LOKALNY: wszystkie przebiegi zgodne z oczekiwaniem`. Logi przebiegów: `<katalog roboczy>/pass_*.log`
(katalog zostaje po błędzie albo z `--keep`).

Uwaga: proces przebiegu wczytuje `tests/monitoring_harness/fake/sitecustomize.py` (atrapy sieci, `mintpy`, `osgeo`
i moduł `google.colab`), więc wewnątrz testu `IN_COLAB` = True; wszystkie pakiety są w środowisku, więc nic nie jest
instalowane. MintPy zastępuje atrapa `bin/smallbaselineApp.py` (na Windows przez plik `.cmd` w katalogu roboczym).
