# TEST: atrapa serwerów CLMS / EGMS / NGL dla notebooks/EGMS_Check.ipynb (pliki z make_fixtures.py).
import json, os
import requests
from requests.models import Response
import google.colab   # w Colab moduł jest wczytany od startu
FX = os.environ["NBTEST_FX"]; PUB = open(os.environ["NBTEST_PUBKEY"]).read()
IDX = json.load(open(f"{FX}/egms/index.json"))
_orig = requests.sessions.Session.request
def _resp(url, status=200, content=b"", js=None):
    r = Response(); r.status_code = status; r.url = url
    r._content = json.dumps(js).encode() if js is not None else content
    r._content_consumed = True; r.encoding = "utf-8"
    return r
def request(self, method, url, **kw):
    if "land.copernicus.eu/@@oauth2-token" in url:
        import jwt
        jwt.decode(kw["data"]["assertion"], PUB, algorithms=["RS256"], audience=url)
        return _resp(url, js={"access_token": "TEST"})
    if "egms.land.copernicus.eu/insar-api/archive" in url:
        assert kw["headers"]["Authorization"] == "Bearer TEST"
        if url.endswith("/search"):
            q = json.loads(kw["data"]); assert q["releases"] == ["2019-2023"] and q["levels"] == ["L2B"]
            lon, lat = q["bbox"][0]
            hits = [] if lon < 5.5 else [{"filename": f, "filesize": v["size"], "release": "2019-2023", "productLevel": "L2B",
                                          "relativeOrbit": v["track"], "direction": v["direction"], "burstId": v["burstId"]} for f, v in IDX.items()]
            return _resp(url, js={"id": "Q", "hits": hits})
        if "/download/" in url:
            return _resp(url, content=open(f"{FX}/egms/{url.rsplit('/', 1)[-1]}", "rb").read())
    if "geodesy.unr.edu" in url:
        if url.endswith("midas.IGS.txt"):
            return _resp(url, content=open(f"{FX}/midas.txt", "rb").read())
        if url.endswith(".EU.tenv3"):
            p = f"{FX}/tenv3/{url.rsplit('/', 1)[-1]}"
            return _resp(url, content=open(p, "rb").read()) if os.path.exists(p) else _resp(url, status=404)
        return _resp(url, status=404)
    return _orig(self, method, url, **kw)
requests.sessions.Session.request = request
