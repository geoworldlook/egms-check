# Test notatnika `notebooks/EGMS_Check.ipynb` poza Colab

Atrapy serwerów CLMS (token), EGMS (wyszukanie, pobranie) i NGL (MIDAS, tenv3) oraz Dysku Google.
Pliki EGMS i GNSS są sztuczne, o **znanej odpowiedzi** (zadane prędkości, szum, duplikaty z zakładek
burstów, stacje odrzucane przez regułę). Służą wyłącznie do sprawdzenia, że kod liczy to, co powinien —
nigdy jako wynik walidacji.

Prawdziwe w teście: `git clone/pull` z GitHuba, `pip install`, całe obliczenia, tabele i wykresy.

## Uruchomienie (Linux, katalog `/content` zapisywalny, jak w Colab)

```bash
# 1. Środowisko jak Colab: Python 3.13, IPython 7.34, ipykernel 6.17, pandas 2.2.3, numpy 2.0.2
python3.13 -m venv colab313 && colab313/bin/pip install "ipython==7.34.0" "ipykernel==6.17.1" \
    "pandas==2.2.3" "numpy==2.0.2" matplotlib pyproj pyjwt cryptography requests nbclient nbformat
colab313/bin/python -m ipykernel install --prefix colab313 --name colab313

# 2. Atrapa klucza CLMS (jednorazowy klucz RSA) i dane testowe
H=tests/colab_harness
colab313/bin/python $H/make_test_key.py /content/drive/MyDrive/GeoWorldLook/secrets/clms_token.json /tmp/pub.pem
mkdir -p /tmp/fx/egms /tmp/fx/tenv3 && colab313/bin/python $H/make_fixtures.py /tmp/fx

# 3. Notatnik z DOWNLOAD = True
sed 's/DOWNLOAD = False /DOWNLOAD = True  /' notebooks/EGMS_Check.ipynb > /tmp/main_dl.ipynb
PATH=$PWD/colab313/bin:$PATH PYTHONPATH=$H/fake NBTEST_FX=/tmp/fx NBTEST_PUBKEY=/tmp/pub.pem \
  JUPYTER_PATH=$PWD/colab313/share/jupyter MPLBACKEND=Agg \
  colab313/bin/python $H/run_nb.py /tmp/main_dl.ipynb /tmp/main_out.ipynb /tmp
```

Oczekiwany wynik (stan 2026-10-10, commit `fe368e8`): 4 stacje osiadające i 3 stabilne (jedna spoza
regionu, 92 km), 5 punktów usuniętych jako duplikaty, K1 100%, K2 1,6 mm, K3 0,78 mm/rok, nachylenie 1,00,
wniosek POTWIERDZONE, `STATUS: OK`.

Uwaga: atrapa nie sprawdza zachowania prawdziwych serwerów (limity, czasy, format odpowiedzi poza polami
używanymi w kodzie). Tego dowodzi dopiero przebieg w Colab.
