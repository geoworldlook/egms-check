# TEST: atrapy serwerów dla notebooks/EGMS_Monitoring.ipynb (pliki z make_fixtures.py; zmienne NBTEST_FX, NBTEST_PUBKEY).
#  - requests: token CLMS (podpis JWT sprawdzany kluczem publicznym), EGMS /search (bbox, L2B i L3 ORTHO-UP) i /download,
#    NGL (MIDAS, tenv3), Geobasis NRW (Punktliste, Zeitfolge);
#  - asf_search.search: bursty SLC ścieżki w prostokącie zapytania (daty jak EGMS, 12 dni);
#  - hyp3_sdk.HyP3: zlecenia bez sieci, zapisane w $NBTEST_FX/hyp3_jobs.json (wspólne dla kolejnych klientów),
#    od razu SUCCEEDED; Job.download_files tworzy zip produktu (egms_harness_lib.hyp3_product_zip).
# Żadne wywołanie nie wychodzi do sieci: nieznany adres = wyjątek.
import json
import os
from datetime import datetime, timezone
from pathlib import Path

if os.environ.get("NBTEST_FX"):
    import requests
    from requests.models import Response

    import egms_harness_lib as L

    FX = Path(os.environ["NBTEST_FX"])
    PUB = Path(os.environ["NBTEST_PUBKEY"]).read_text()
    IDX = json.loads((FX / "egms" / "index.json").read_text())

    def _resp(url, status=200, content=b"", js=None):
        r = Response()
        r.status_code, r.url = status, url
        r._content = json.dumps(js).encode() if js is not None else content
        r._content_consumed, r.encoding = True, "utf-8"
        return r

    def _intersects(a, b):
        return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])

    def _egms(method, url, kw):
        assert kw["headers"]["Authorization"] == "Bearer TEST", "brak tokenu w nagłówku"
        if url.endswith("/search"):
            q = json.loads(kw["data"])
            assert len(q["releases"]) == 1 and q["releases"][0] in (L.RELEASE, L.RELEASE_CHECK), q
            rel = q["releases"][0]
            (lo0, la0), (lo1, la1) = q["bbox"]
            level = q["levels"][0]
            if level == "L3":
                assert q.get("productType") == "ORTHO-UP", q
            hits = []
            for f, v in IDX.items():
                if (v["level"] != level or v["release"] != rel
                        or not _intersects((lo0, la0, lo1, la1), L.REGIONS[v["region"]]["aoi"])):
                    continue
                h = {"filename": f, "filesize": v["size"], "release": rel, "productLevel": level}
                if level == "L2B":
                    h.update(relativeOrbit=v["track"], direction=v["direction"], burstId=v["burstId"])
                else:
                    h.update(productType="ORTHO-UP")
                hits.append(h)
            return _resp(url, js={"id": f"Q-{level}-{len(hits)}", "hits": hits})
        if "/download/" in url:
            assert kw.get("params", {}).get("id", "").startswith("Q-"), kw.get("params")
            return _resp(url, content=(FX / "egms" / url.rsplit("/", 1)[-1]).read_bytes())
        raise AssertionError(f"Nieobsługiwany adres EGMS: {url}")

    _orig = requests.sessions.Session.request

    def request(self, method, url, **kw):
        if "land.copernicus.eu/@@oauth2-token" in url:
            import jwt
            jwt.decode(kw["data"]["assertion"], PUB, algorithms=["RS256"], audience=url)
            return _resp(url, js={"access_token": "TEST"})
        if "egms.land.copernicus.eu/insar-api/archive" in url:
            return _egms(method, url, kw)
        if "geodesy.unr.edu" in url:
            if url.endswith("midas.IGS.txt"):
                return _resp(url, content=(FX / "midas.txt").read_bytes())
            p = FX / "tenv3" / url.rsplit("/", 1)[-1]
            return _resp(url, content=p.read_bytes()) if url.endswith(".EU.tenv3") and p.exists() else _resp(url, 404)
        if "opengeodata.nrw.de" in url:
            p = FX / "nrw" / url.rsplit("/", 1)[-1]
            return _resp(url, content=p.read_bytes()) if p.exists() else _resp(url, 404)
        raise AssertionError(f"TEST: wywołanie sieci poza atrapą: {method} {url}")

    requests.sessions.Session.request = request

    # --- asf_search ---------------------------------------------------------------------------------------------
    import asf_search

    class _Product:
        def __init__(self, properties, geometry):
            self.properties, self.geometry = properties, geometry

    def _search(dataset=None, intersectsWith=None, relativeOrbit=None, start=None, end=None, polarization=None, **kw):
        from shapely import wkt
        assert dataset == asf_search.DATASET.SLC_BURST, dataset
        lo0, la0, lo1, la1 = wkt.loads(intersectsWith).bounds
        track = int(relativeOrbit)
        region = L.track_region(track)
        direction, heading = L.REGIONS[region]["tracks"][track][:2]
        d = L.burst_dates(region, track)
        d = d[(d >= pd_ts(start)) & (d <= pd_ts(end))]
        edges = [la0 - 0.05 + i * (la1 - la0 + 0.1) / 3 for i in range(4)]
        out = []
        for date in d:
            for i in range(3):
                b = track * 1000 + i
                ring = [[lo0 - 0.2, edges[i] - 0.02], [lo1 + 0.2, edges[i] - 0.02], [lo1 + 0.2, edges[i + 1] + 0.02],
                        [lo0 - 0.2, edges[i + 1] + 0.02], [lo0 - 0.2, edges[i] - 0.02]]
                out.append(_Product({"sceneName": f"S1_{b:06d}_IW1_{date:%Y%m%d}T054312_VV_{b % 65536:04X}-BURST",
                                     "startTime": f"{date:%Y-%m-%d}T05:43:12.000000Z", "platform": "Sentinel-1A",
                                     "flightDirection": direction.upper(), "pathNumber": track, "polarization": polarization,
                                     "burst": {"fullBurstID": f"{track:03d}_{b:06d}_IW1"}},
                                    {"type": "Polygon", "coordinates": [ring]}))
        return out

    def pd_ts(x):
        import pandas as pd
        return pd.Timestamp(x)

    asf_search.search = _search

    # --- hyp3_sdk -----------------------------------------------------------------------------------------------
    import hyp3_sdk

    _REAL_HYP3, _JOBS = hyp3_sdk.HyP3, FX / "hyp3_jobs.json"

    class _FakeJob(hyp3_sdk.Job):
        def download_files(self, location=".", create=True):
            location = Path(location)
            location.mkdir(parents=True, exist_ok=create)
            out = []
            for f in self.files:
                p = location / f["filename"]
                p.write_bytes(L.hyp3_product_zip(f["filename"][:-4]))
                out.append(p)
            return out

    def _load_jobs():
        if not _JOBS.exists():
            return []
        jobs = []
        for d in json.loads(_JOBS.read_text()):
            j = hyp3_sdk.Job.from_dict(d)
            j.__class__ = _FakeJob
            jobs.append(j)
        return jobs

    class _FakeHyP3(_REAL_HYP3):
        def __init__(self, api_url=None, username=None, password=None, token=None, prompt=None):
            assert token or (username and password), "atrapa HyP3: brak danych logowania"
            self.url = api_url

        def find_jobs(self, name=None, **kw):
            return hyp3_sdk.Batch([j for j in _load_jobs() if j.name == name])

        def check_credits(self):
            return 100000.0

        def submit_prepared_jobs(self, prepared_jobs):
            jobs = _load_jobs()
            new = []
            for p in prepared_jobs:
                k, par = len(jobs), p["job_parameters"]
                assert p["job_type"] == "INSAR_ISCE_MULTI_BURST", p["job_type"]
                nums = sorted(int(s.split("_")[1]) for s in par["reference"])
                d1, d2 = par["reference"][0].split("_")[3][:8], par["secondary"][0].split("_")[3][:8]
                track = nums[0] // 1000
                product = (f"S1_{track:03d}_{nums[0]:06d}s1n{len(nums):02d}-000000s2n00-000000s3n00_IW_{d1}_{d2}_VV_INT80_"
                           f"{k:04X}")
                job = _FakeJob(job_type=p["job_type"], job_id=f"job-{k:05d}", request_time=datetime.now(timezone.utc),
                               status_code="SUCCEEDED", user_id="TEST", name=p.get("name"), job_parameters=dict(par),
                               files=[{"filename": f"{product}.zip", "url": f"https://hyp3.invalid/{product}.zip"}])
                jobs.append(job)
                new.append(job)
            _JOBS.write_text(json.dumps([j.to_dict() for j in jobs]))
            return hyp3_sdk.Batch(new)

    hyp3_sdk.HyP3 = _FakeHyP3

    import google.colab  # noqa: F401,E402  (w Colab moduł jest wczytany od startu)
