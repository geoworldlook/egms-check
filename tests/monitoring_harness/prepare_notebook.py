# TEST: kopia testowa notebooks/EGMS_Monitoring.ipynb dla atrap (nie zmienia notatnika ani CHECK_CONFIG w repozytorium).
#  1. po komórce konfiguracji: komórka, która w KOPII cfg ustawia approved = "TEST" w każdej sekcji i wartości testowe
#     decyzji None (adresy NRW atrapy, kodowanie, odniesienie, koniec etapu B, kredyty, tolerancja LOS, opcje MintPy);
#  2. CONFIRM_MB_<REGION> = suma rozmiarów plików EGMS atrapy dla regionu (MB, zaokrąglone) - niezależnie od kodu planu;
#  3. CONFIRM_JOBS = {ścieżka: 3 n - 6} (n dat burstów w [hyp3.start, koniec testu], sąsiedzi 3, odstęp 12 dni <= 48);
#  4. na końcu komórka kontroli znanej odpowiedzi (asserty).
# Użycie: python prepare_notebook.py <notatnik wejściowy> <notatnik wyjściowy> <katalog_fx>
import json
import sys
from pathlib import Path

import nbformat

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "fake"))
sys.path.insert(0, str(HERE.parents[1]))
import egms_harness_lib as L  # noqa: E402
from step_05_colab_run import CHECK_CONFIG  # noqa: E402

src, dst, fx = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
nb = nbformat.read(src, as_version=4)
index = json.loads((fx / "egms" / "index.json").read_text())
mb = {r: int(round(sum(v["size"] for v in index.values() if v["region"] == r) / 1e6)) for r in L.REGIONS}
start = CHECK_CONFIG["hyp3"]["start"]
jobs = {}
for track in L.REGIONS[CHECK_CONFIG["hyp3"]["region"]]["tracks"]:
    d = L.burst_dates(CHECK_CONFIG["hyp3"]["region"], track)
    n = int(((d >= start) & (d <= L.HYP3_END_TEST)).sum())
    jobs[str(track)] = 3 * n - 6

APPROVE = f'''# HARNESS (test): zatwierdzenia i decyzje w KOPII cfg; wartości testowe, nie decyzje autora.
def _approve(node):
    for k, v in node.items():
        if isinstance(v, dict):
            if 'approved' in v:
                v['approved'] = 'TEST'
            else:
                _approve(v)
_approve(cfg)
cfg['thresholds']['gnss_l2b']['k3_definition'] = 'abs_v_egms'
_lv = cfg['regions']['nrw_west']['levelling']
_lv['urls'] = {{'points': 'https://www.opengeodata.nrw.de/produkte/geobasis/rb/fd/hfp_pl_csv/hfp_pl.csv',
               'series': 'https://www.opengeodata.nrw.de/produkte/geobasis/rb/fd/hfp_plzf_csv/hfp_plzf.csv'}}
_lv['encoding'] = 'cp1252'
_lv['reference'] = {{'type': 'absolute'}}
cfg['hyp3'].update(end='{L.HYP3_END_TEST}', max_credits=10000, cost_per_job=1, los_check_tol=0.05)
cfg['hyp3']['mintpy'].update(deramp='no', solid_earth_tides=False)
assert CHECK_CONFIG['monitoring']['approved'] is None, 'kopia testowa nie może zmieniać CHECK_CONFIG'
display(approvals_table(cfg))'''

CHECK = f'''# HARNESS (test): kontrola znanej odpowiedzi na danych syntetycznych (egms_harness_lib); wartości testowe, nie wynik.
import egms_harness_lib as Lh
from step_05_colab_run import registry_read
from step_07_monitoring import read_long
runs = registry_read(rt, 'gwl_runs')
assert (runs['status'] != 'error').all(), runs[runs['status'] == 'error'][['task', 'message']]
G, N = region_paths(rt, cfg, 'groningen'), region_paths(rt, cfg, 'nrw_west')
sg, sn = (pd.read_csv(p['sites'], dtype={{'site': str}}) for p in (G, N))
assert dict(zip(sg['site'], sg['group'])) == {{s: Lh.EXPECTED_GROUPS[s] for s in Lh.SELECTED['groningen']}}, sg
gn = sn[sn['site_type'] == 'gnss']
assert dict(zip(gn['site'], gn['group'])) == {{s: Lh.EXPECTED_GROUPS[s] for s in Lh.SELECTED['nrw_west']}}, gn
bn = sn[sn['site_type'] == 'benchmark']
assert sorted(bn['site']) == sorted(Lh.bench_id(b) for b in Lh.BENCH if b != 'B014'), bn['site'].tolist()
chk = pd.read_csv(G['checks'])
assert chk['pass'].all() and chk.loc[chk['check'].str.startswith('A5'), 'value'].iat[0].startswith('5 pkt'), chk
for P, n_pairs in ((G, 14), (N, 6)):
    res = pd.read_csv(P['gnss_compare'], dtype={{'site': str}})
    m = res[(res['product'] == 'EGMS_L2b_2020_2024') & (res['radius_m'] == 100)]
    assert len(m) == n_pairs and (m['status'] == 'ok').all() and (m['dv'].abs() < 1.0).all(), m
    l3 = res[res['product'] == 'EGMS_L3U_2020_2024']
    truth = l3['site'].map(lambda s: Lh.GNSS[s][2])
    assert (l3['status'] == 'ok').all() and ((l3['v_egms'] - truth).abs() < 0.3).all() and (l3['dv'].abs() < 0.6).all(), l3
    v2 = pd.read_csv(P['verdict_l2b'])
    assert v2.loc[v2['kryterium'].str[:2].isin(['K1', 'K2', 'K3']), 'spełnione'].astype(bool).all(), v2
    v3 = pd.read_csv(P['verdict_l3u'])
    assert bool(v3.loc[v3['kryterium'].str[:2] == 'K1', 'spełnione'].iat[0]), v3
summ = pd.read_csv(N['levelling_summary'])
nk = summ['kryterium'].str.match(r'N\\d')
assert nk.sum() == 4 and summ.loc[nk, 'spełnione'].astype(bool).all(), summ
lc = pd.read_csv(N['levelling_compare'], dtype={{'benchmark_id': str}}).set_index('benchmark_id')
assert lc.at[Lh.bench_id('B013'), 'status'].startswith('NaN: 1 epok') and (lc['status'] == 'ok').sum() == 12, lc['status']
assert (lc.loc[lc['status'] == 'ok', 'diff_mm'].abs() < 3.0).all(), lc['diff_mm']
lg, ln_ = read_long(G['long']), read_long(N['long'])
assert {{'EGMS_L2b_2020_2024', 'EGMS_L3U_2020_2024', 'GNSS_NGL_LOS', 'GNSS_NGL_U', 'S1_HYP3_MINTPY'}} <= set(lg['source']), set(lg['source'])
assert 'LEVELLING_NRW' in set(ln_['source']), set(ln_['source'])
tt = pd.read_csv(G['ttd'], dtype={{'site': str, 'track': str}})
s1 = tt[(tt['site'] == 'S001') & (tt['source'] == 'EGMS_L2b_2020_2024') & (tt['start'] == '2020-01-01')]
assert len(s1) == 2 and s1['ttd_months'].notna().all() and (s1['ttd_months'] <= 24).all(), s1
for f in sorted(G['outputs'].glob('hyp3_align_groningen_*.csv')):
    a = pd.read_csv(f)
    assert len(a) == 7 and (a['status'] == 'ok').all() and (a['std_diff_mm'] < 2.5).all(), (f.name, a)
assert len(list(G['outputs'].glob('hyp3_align_groningen_*.csv'))) == {len(jobs)}
assert len(list(G['figures'].glob('*.png'))) >= 6 and len(list(N['figures'].glob('*.png'))) >= 6
assert Path(PROJECT_DIR, cfg['project']['outputs_dir'], 'run_summary.md').stat().st_size > 2000
print('HARNESS: znana odpowiedź OK')'''

cells, done = [], {"cfg": False, "mb": set(), "jobs": False}
for c in nb.cells:
    if c.cell_type == "code":
        for region, v in mb.items():
            line = f"CONFIRM_MB_{region.upper()} = None"
            if line in c.source:
                c.source = c.source.replace(line, f"CONFIRM_MB_{region.upper()} = {v}  # HARNESS: suma plików atrapy")
                done["mb"].add(region)
        if "CONFIRM_JOBS = None" in c.source:
            c.source = c.source.replace("CONFIRM_JOBS = None", f"CONFIRM_JOBS = {jobs!r}  # HARNESS: 3 n - 6")
            done["jobs"] = True
    cells.append(c)
    if c.cell_type == "code" and "cfg = copy.deepcopy(CHECK_CONFIG)" in c.source:
        cells.append(nbformat.v4.new_code_cell(APPROVE))
        done["cfg"] = True
cells.append(nbformat.v4.new_code_cell(CHECK))
assert done["cfg"] and done["mb"] == set(mb) and done["jobs"], done
nb.cells = cells
nb.metadata["kernelspec"] = {"display_name": "colab313", "language": "python", "name": "colab313"}
nbformat.write(nb, dst)
print(f"Zapisano {dst}: CONFIRM_MB {mb}, CONFIRM_JOBS {jobs}")
