"""
Generator dwóch notatników na spotkanie (autor 2026-10-15: „proste i czytelne, pokazujące co mamy”):
  notebooks/Pokaz_1_GNSS_Groningen.ipynb  - EGMS L2b kontra GNSS w Groningen,
  notebooks/Pokaz_2_Niwelacja_NRW.ipynb   - EGMS L3 kontra niwelacja w zachodniej NRW (wydanie 2019-2023).
Notatniki niczego nie liczą i niczego nie pobierają - tylko czytają gotowe wyniki zapisane na Dysku przez
notebooks/EGMS_Monitoring.ipynb. Kod jest ukryty w formularzach Colab (#@title, cellView=form): widać tytuł komórki,
opis i wynik. Liczby w podsumowaniach są czytane z plików wyników, nie wpisane w tekst. Repery i stacje na rycinach
wybiera reguła z notatnika technicznego (monitoring.example_rule), nie wybór ręczny.
Notatników nie edytuj ręcznie: zmień komórki niżej i uruchom `python build_colab_pokaz.py`.
"""
import json
from pathlib import Path

JAK_URUCHOMIC = """
**Jak uruchomić:** menu *Środowisko wykonawcze → Uruchom wszystko* (kilka sekund). Notatnik tylko czyta wyniki z Dysku,
policzone wcześniej w `EGMS_Monitoring.ipynb`. Kod jest ukryty — kliknij tytuł komórki, żeby go zobaczyć."""

SETUP = """#@title Przygotowanie: połączenie z Dyskiem i wczytanie wyników
from google.colab import drive
drive.mount('/content/drive')
import json, subprocess, sys
from pathlib import Path
import pandas as pd
from IPython.display import display, Image, Markdown, HTML
PROJECT_DIR = '/content/drive/MyDrive/GeoWorldLook/egmscheck'
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)
for m in [m for m in sys.modules if m.startswith('step_0')]:
    del sys.modules[m]          # zawsze kod z Dysku: moduł zapamiętany w jądrze sprzed aktualizacji dawał KeyError
from step_05_colab_run import (CHECK_CONFIG, region_paths, levelling_check_paths, _levelling_check_examples,
                               _example_sites, _read_sites, _sources)
rt = {'PROJECT_DIR': PROJECT_DIR}
KOD = subprocess.run(['git', '-C', PROJECT_DIR, 'log', '-1', '--format=%h z %ci'], capture_output=True, text=True).stdout.strip()
print('Wyniki policzone kodem:', KOD)
KROK = ('W EGMS_Monitoring.ipynb uruchom komórki startowe (pobierają aktualny kod na Dysk) i komórki obliczeń tego '
        'przypadku, a potem ten notatnik jeszcze raz.')

def wymagaj(paths, klucze, kolumny=None):
    # Wyniki starsze niż notatnik = jasny komunikat, co uruchomić (zamiast KeyError albo pustej komórki).
    stare = [k for k in klucze if k not in paths]
    if stare:
        raise RuntimeError(f'Kod na Dysku ({KOD}) jest starszy niż ten notatnik (brak: {stare}). {KROK}')
    brak = [Path(paths[k]).name for k in klucze if not Path(paths[k]).exists()]
    if brak:
        raise FileNotFoundError(f'Brak wyników na Dysku: {brak}. {KROK}')
    for k, cols in (kolumny or {}).items():
        jest = pd.read_csv(paths[k], nrows=0).columns
        if [c for c in cols if c not in jest]:
            raise RuntimeError(f'{Path(paths[k]).name} policzony starszym kodem (brak kolumn {[c for c in cols if c not in jest]}). {KROK}')

def pokaz(path, width=850):
    # Brak pliku = błąd (wyniki liczy EGMS_Monitoring.ipynb), nie pusta komórka.
    if not Path(path).exists():
        raise FileNotFoundError(f'Brak {path}: uruchom najpierw notebooks/EGMS_Monitoring.ipynb')
    display(Image(str(path), width=width))

def tabela(df):
    display(HTML(df.to_html(index=False)))

def ocena(x):
    s = str(x)
    return '✔ tak' if s == 'True' else '✘ nie' if s == 'False' else '— nie liczone'

def kryteria(path, kody):
    t = pd.read_csv(path)
    t = t[t['kryterium'].str[:2].isin(kody)]
    return pd.DataFrame({'kod': t['kryterium'].str[:2].to_numpy(), 'Kryterium': t['kryterium'].to_numpy(),
                         'Wynik': t['wynik'].to_numpy(), 'Próg': t['próg'].to_numpy(),
                         'Spełnione': t['spełnione'].map(ocena).to_numpy()})"""

GNSS = [
    ("md", """# EGMS kontra GNSS — Groningen (Holandia)

**Pytanie:** czy EGMS (ruch terenu z radaru satelitarnego Sentinel-1) pokazuje takie samo tempo osiadania jak stacje
GNSS na ziemi?

**Dane:**
- EGMS L2b Calibrated, wydanie 2020–2024: ruch punktów w kierunku satelity, osobno dla każdej ścieżki,
- stacje GNSS z Nevada Geodetic Laboratory: dobowe pozycje anten, nad polem gazowym Groningen.

**Jak porównujemy:** dla każdej stacji bierzemy punkty EGMS w promieniu 100 m, ruch GNSS przeliczamy na kierunek patrzenia
satelity i porównujemy tempo ruchu [mm/rok]. Progi oceny ustaliliśmy przed obliczeniami.
""" + JAK_URUCHOMIC),
    ("code", SETUP + """
G = region_paths(rt, CHECK_CONFIG, 'groningen')
wymagaj(G, ['sites', 'gnss_compare', 'verdict_l2b'])"""),
    ("md", """## 1. Ile mamy danych"""),
    ("code", """#@title Liczba stacji i par stacja–ścieżka
sites = _read_sites(G)
gn = sites[sites['site_type'] == 'gnss']
gc = pd.read_csv(G['gnss_compare'], dtype={'site': str, 'track': str})
par = gc[(gc['product'] == _sources(CHECK_CONFIG)['L2B']) & (gc['status'] == 'ok')
         & (gc['radius_m'] == CHECK_CONFIG['method']['radius_main_m'])]
display(Markdown(f"- **{len(gn)} stacji GNSS**: {int((gn['group'] == 'osiadająca').sum())} osiadających "
                 f"i {int((gn['group'] == 'stabilna').sum())} stabilnych\\n"
                 f"- **{len(par)} par stacja–ścieżka** z kompletem danych (promień {CHECK_CONFIG['method']['radius_main_m']} m)"))"""),
    ("md", """## 2. Czy tempo osiadania się zgadza?"""),
    ("code", """#@title Wykres: tempo ruchu z EGMS kontra z GNSS
pokaz(G['figures'] / 'groningen_velocity_scatter.png', 620)"""),
    ("md", """**Jak czytać:** każdy punkt to jedna stacja widziana z jednej ścieżki satelity. Oś pozioma to GNSS, pionowa EGMS,
obie w mm/rok. Ukośna linia oznacza idealną zgodność, a szary pas ±1,5 mm/rok to dopuszczalna różnica. Punkty pełne to
stacje osiadające, puste to stacje stabilne.

Prawie wszystkie punkty leżą w szarym pasie. Punkty ze ścieżek wznoszących (niebieskie) są nieco nad linią, a ze
zstępujących (pomarańczowe) nieco pod nią. To mała różnica ruchu poziomego wschód–zachód między GNSS a EGMS, w granicach
progu; nie badaliśmy jej osobno."""),
    ("md", """## 3. Ocena według kryteriów ustalonych przed obliczeniami"""),
    ("code", """#@title Tabela kryteriów K1–K3
t = kryteria(G['verdict_l2b'], ['K1', 'K2', 'K3'])
pytania = {'K1': 'Czy tempo osiadania się zgadza?', 'K2': 'Czy szeregi w czasie się zgadzają?',
           'K3': 'Czy na stacjach stabilnych EGMS nie pokazuje ruchu, którego nie ma?'}
t['Kryterium'] = t['kod'] + ': ' + t['kod'].map(pytania)
tabela(t[['Kryterium', 'Wynik', 'Próg', 'Spełnione']])
display(Markdown('**Wniosek według reguły ustalonej z góry:** ' + G['verdict_l2b'].with_suffix('.txt').read_text().strip()))"""),
    ("md", """**Jak czytać:** K1 i K2 są spełnione, czyli tempo osiadania i przebieg w czasie się zgadzają. K3 nie przeszło o włos
na jednej stacji stabilnej, dlatego wniosek formalny to zgodność częściowa."""),
    ("md", """## 4. Przykładowa stacja w czasie"""),
    ("code", """#@title Stacja osiadająca najszybciej według GNSS (wybrana regułą, nie ręcznie)
stacja = _example_sites(sites, None, CHECK_CONFIG['monitoring']['example_rule'])[0]
display(Markdown(f'Stacja **{stacja}**'))
pokaz(G['figures'] / f'groningen_series_{stacja}.png', 900)"""),
    ("md", """**Jak czytać:** każdy panel to jedna ścieżka satelity (ruch w kierunku satelity, LOS) albo ruch pionowy (U).
Linia to EGMS, kropki to dobowe pozycje GNSS przeliczone na ten sam kierunek. Oba szeregi opadają w tym samym tempie."""),
    ("md", """## Wniosek

- EGMS dobrze oddaje tempo osiadania nad polem gazowym Groningen. To samo pokazują stacje GNSS na ziemi.
- Wniosek formalny to **zgodność częściowa**, bo kontrola na stacjach stabilnych (K3) nie przeszła o włos.
- **Ograniczenie:** EGMS jest kalibrowany modelem z sieci GNSS, więc to porównanie nie jest w pełni niezależne. Dlatego
  drugi notatnik sprawdza EGMS niwelacją, która nie korzysta z GNSS.

**Źródła:** EGMS (Copernicus Land Monitoring Service); GNSS: Nevada Geodetic Laboratory (Blewitt i in. 2016, 2018);
metoda i progi: Koudogbo i in. (2025) EGMS Validation Report, Fabris i Nazari (2026)."""),
]

NIWELACJA = [
    ("md", """# EGMS kontra niwelacja — zachodnia Nadrenia Północna-Westfalia (Niemcy)

**Pytanie:** czy EGMS pokazuje to samo osiadanie co niwelacja precyzyjna, czyli pomiar wysokości reperów wykonany na ziemi?

**Dane:**
- EGMS L3 Ortho (ruch pionowy w komórkach 100 × 100 m), wydanie 2019–2023,
- niwelacja: rejestr punktów wysokościowych Geobasis NRW; repery z dwoma pomiarami w oknie EGMS (najczęściej maj 2019
  i maj 2022).

**Dlaczego to ważne:** niwelacja nie korzysta z GNSS, a EGMS jest kalibrowany modelem GNSS. To sprawdzenie jest więc
niezależne od kalibracji.

**Jak porównujemy:** dla każdego reperu bierzemy komórkę EGMS, w której leży, i porównujemy zmianę wysokości między
tymi samymi dniami [mm]. Bierzemy wszystkie repery z dwoma pomiarami, bez wybierania według EGMS. Progi oceny
ustaliliśmy przed obliczeniami.
""" + JAK_URUCHOMIC),
    ("code", SETUP + """
C = levelling_check_paths(rt, CHECK_CONFIG, 'nrw_west')
wymagaj(C, ['compare', 'summary', 'summary_rel', 'offset_rel', 'groups', 'groups_rel', 'figure', 'map', 'uncertainty'],
        kolumny={'compare': ['sigma_dh_mm']})
strong = CHECK_CONFIG['regions']['nrw_west']['levelling']['strong_motion_mm_yr']
res = pd.read_csv(C['compare'], dtype={'benchmark_id': str})
ok = res[res['status'] == 'ok']
unc = json.loads(C['uncertainty'].read_text())
off = json.loads(C['offset_rel'].read_text())
k = unc['k_sigma']"""),
    ("md", """## 1. Gdzie EGMS widzi ruch"""),
    ("code", """#@title Mapa tempa ruchu pionowego EGMS 2019–2023
pokaz(C['map'], 720)"""),
    ("md", """**Jak czytać:** czerwone plamy to niecki osiadania przy odkrywkach węgla brunatnego (do kilkudziesięciu mm/rok),
niebieskie to wypiętrzanie. Trójkąty to stacje GNSS, kółka to repery pokazane niżej w czasie."""),
    ("md", """## 2. Czy niwelacja potwierdza ruch z EGMS?"""),
    ("code", """#@title Wykres: zmiana wysokości z niwelacji kontra z EGMS (wszystkie repery)
display(Markdown(f'**{len(ok)} reperów** z dwoma pomiarami niwelacyjnymi i komórką EGMS. '
                 f'Niepewność EGMS (mediana, ±{k:g}σ): **±{k * unc["median_sigma_dh_mm"]:.1f} mm**; '
                 f'w granicach niepewności: **{unc["share_within_absolute"]:.0%}** reperów, a po odjęciu wspólnego '
                 f'przesunięcia (wariant względny) **{unc["share_within_relative"]:.0%}**.'))
pokaz(C['figure'], 640)"""),
    ("md", """**Jak czytać:** każdy punkt to jeden reper. Oś pozioma to zmiana wysokości z niwelacji, pionowa z EGMS, obie w mm
między tymi samymi dniami. Ukośna linia oznacza idealną zgodność. Pomarańczowe punkty to repery w nieckach osiadania.

Szary pas wokół linii to niepewność EGMS (±2σ). Reper w pasie oznacza, że różnica EGMS − niwelacja mieści się w tym,
jak dokładny jest sam EGMS. Niepewność bierzemy z kolumny `rmse` w plikach EGMS (typowy szum pojedynczego pomiaru);
zmiana wysokości to różnica dwóch odczytów, więc σ = √2 · rmse. Niepewności niwelacji nie rysujemy, bo rejestr NRW jej
nie podaje.

Punkty leżą wzdłuż linii od 0 do około −140 mm. Cała chmura jest lekko przesunięta w dół: EGMS pokazuje wszędzie
trochę więcej osiadania niż niwelacja. Dlatego po odjęciu tego wspólnego przesunięcia w pasie jest więcej reperów."""),
    ("md", """## 3. Trzy repery w czasie"""),
    ("code", """#@title Repery wybrane regułą: najszybsze osiadanie, mediana niecek, reper stabilny
przyklady = dict((lab, bid) for bid, lab in _levelling_check_examples(res, CHECK_CONFIG['monitoring']['example_rule'], strong))
for lab in ('fastest subsidence by levelling', f'median rate in bowls (|v| >= {strong:g} mm/yr)', 'smallest |rate|, stable'):
    if lab not in przyklady:
        print(f'Reguła „{lab}”: ten sam reper co na rycinie wyżej albo brak reperów w tej grupie')
        continue
    pokaz(C['figure'].parent / f"nrw_west_levelling_series_2019_2023_{przyklady[lab]}.png", 900)"""),
    ("md", """**Jak czytać:** niebieska linia to EGMS co 6–12 dni, a jasnoniebieski pas wokół niej to niepewność EGMS (±2σ). Duże
żółte punkty to dwa pomiary niwelacyjne; przerywana linia tylko je łączy, między nimi niwelacji nie ma. Oba szeregi
zaczynają się od zera w dniu pierwszego pomiaru. Jeśli żółty punkt leży w pasie, EGMS i niwelacja zgadzają się
w granicach dokładności EGMS.

Na dwóch pierwszych reperach EGMS i niwelacja kończą się prawie w tym samym miejscu. Trzeci reper się nie rusza, a EGMS
pokazuje na nim kilka mm osiadania — wyjaśnia to następna sekcja."""),
    ("md", """## 4. Reper stabilny: czy różnica kilku mm to powód do niepokoju?

Niwelacja mówi, że reper się nie rusza, a EGMS pokazuje kilka mm osiadania w 3 lata. Rozkładamy to na dwie części:
**szum** (losowe skoki pomiaru, szary pas) i **wspólne przesunięcie** (to samo dla wszystkich reperów stabilnych)."""),
    ("code", """#@title Reper stabilny wybrany regułą: trzy panele i liczby
bid = przyklady.get('smallest |rate|, stable')
if bid is None:
    raise ValueError('Reguła nie wskazała reperu stabilnego (brak reperów o |v| bliskim zera)')
r = ok[ok['benchmark_id'] == bid].iloc[0]
wspolne = off['median_v_egms_group_mm_yr'] * r['dt_yr'] - off['median_v_lev_group_mm_yr'] * r['dt_yr']
po = r['diff_mm'] - wspolne
display(Markdown(
    f"- Reper **{bid}**: niwelacja **{r['dh_lev_mm']:+.1f} mm**, EGMS **{r['dh_egms_mm']:+.1f} ± {k * r['sigma_dh_mm']:.1f} mm** "
    f"(±{k:g}σ) w {r['dt_yr']:.2f} roku.\\n"
    f"- Wszystkie **{off['n_group']} reperów stabilnych** mają w EGMS wspólne tempo **{off['offset_egms_minus_lev_mm_yr']:+.2f} mm/rok**; "
    f"przez ten czas daje to **{wspolne:+.1f} mm**.\\n"
    f"- Po odjęciu wspólnego przesunięcia różnica EGMS − niwelacja wynosi **{po:+.1f} mm** — "
    + ('**w granicach niepewności EGMS**.' if abs(po) <= k * r['sigma_dh_mm'] else '**poza pasem niepewności EGMS**.')))
pokaz(C['figure'].parent / f"nrw_west_levelling_stable_2019_2023_{bid}.png", 1000)"""),
    ("md", """**Jak czytać:**
- **Panel A (tak jak jest):** EGMS (niebieski) idzie wzdłuż kropkowanej linii, czyli wspólnego tempa wszystkich reperów
  stabilnych. Nie odjeżdża od niej, więc to nie jest ruch tego reperu.
- **Panel B (po odjęciu wspólnego tempa):** EGMS skacze wokół zera w pasie szumu, a pomiary niwelacyjne leżą w pasie.
  Po wyrównaniu „zera” obie metody pokazują to samo: reper się nie rusza.
- **Panel C (wszystkie repery stabilne):** zmiany EGMS na wszystkich reperach stabilnych skupiają się wokół kilku mm
  poniżej zera. Ten reper jest typowy. Kryterium N3, ustalone przed obliczeniami, dopuszcza medianę do 5 mm — jest
  spełnione.
- **Skala:** kilka mm wobec −140 mm w nieckach to kilka procent sygnału.

**Analogia:** mierzymy wzrost ludzi na promie. Miarka liczona od pokładu pokazuje, że nikt się nie zmienia. GPS liczony od
poziomu morza pokazuje, że wszyscy obniżają się o 1 mm na rok, bo cały prom powoli osiada. Obie miary są dobre, tylko mają
inne „zero”. Niwelacja liczy od reperów nawiązania sieci, a EGMS od układu ETRF2000 przez GNSS.

**Co jest pewne, a co jest hipotezą:** że przesunięcie jest wspólne dla wszystkich reperów stabilnych i mieści się
w progu — to zmierzyliśmy. Że jego przyczyną jest różne „zero” układów odniesienia — to najbardziej prawdopodobne
wyjaśnienie, ale go nie sprawdzaliśmy (Even i in. 2024 też go nie podają)."""),
    ("md", """## 5. Ocena według kryteriów ustalonych przed obliczeniami"""),
    ("code", """#@title Tabela kryteriów N1–N4: wariant główny i wariant względny
kody = ['N1', 'N2', 'N3', 'N4']
pytania = {'N1': 'N1: typowa różnica EGMS − niwelacja', 'N2': 'N2: zgodność kierunku ruchu',
           'N3': 'N3: repery stabilne bez fałszywego ruchu', 'N4': 'N4: przesunięcie tempa EGMS'}
g, w = kryteria(C['summary'], kody), kryteria(C['summary_rel'], kody)
# N3 w wariancie względnym nie jest liczone: repery stabilne są tam grupą odniesienia.
w.loc[(w['kod'] == 'N3') & (w['Spełnione'] == '— nie liczone'), 'Wynik'] = 'nie dotyczy (grupa odniesienia)'
t = g[['kod', 'Próg']].assign(Kryterium=g['kod'].map(pytania), **{
    'Wariant główny': g['Wynik'] + ' ' + g['Spełnione'].str[:1],
    'Względem reperów stabilnych': g['kod'].map(dict(zip(w['kod'], w['Wynik'] + ' ' + w['Spełnione'].str[:1])))})
tabela(t[['Kryterium', 'Próg', 'Wariant główny', 'Względem reperów stabilnych']])
display(Markdown(f"Przesunięcie EGMS względem niwelacji na {off['n_group']} reperach stabilnych: "
                 f"**{off['offset_egms_minus_lev_mm_yr']:+.2f} ± {off['offset_se_mm_yr']:.2f} mm/rok**"))"""),
    ("md", """**Jak czytać:** ✔ = kryterium spełnione, ✘ = niespełnione, — = nie liczone.
- **Wariant główny** porównuje wartości wprost, tak jak Even i in. (2024). Nie spełnia progów N1, N2 i N4 przez stałe
  przesunięcie EGMS, a nie przez rozrzut.
- **Wariant względny** (dodatkowy) najpierw wyznacza wspólne „zero” na reperach, które według niwelacji się nie ruszają.
  Wtedy wszystkie liczone kryteria są spełnione. N3 nie jest tu liczone, bo te repery służą jako odniesienie.
- Wariant względny dodaliśmy po obejrzeniu wyniku głównego, więc werdykt główny się nie zmienia."""),
    ("md", """## 6. Niecki osiadania"""),
    ("code", """#@title Repery w nieckach (tempo według niwelacji co najmniej 10 mm/rok) i pozostałe
gr, grw = pd.read_csv(C['groups']), pd.read_csv(C['groups_rel'])
for x in (gr, grw):     # kolejność wierszy z step_06.levelling_groups: wszystkie, niecki, pozostałe
    assert list(x['grupa'].str[:5]) == ['wszys', 'nieck', 'pozos'], list(x['grupa'])
tabela(pd.DataFrame({'Grupa': ['wszystkie', f'niecki (≥ {strong:g} mm/rok)', 'pozostałe'],
                     'Repery': gr['n'].astype(int),
                     'Typowa różnica [mm]': gr['median_abs_diff_mm'].round(1),
                     'Zgodność kierunku': (gr['sign_agreement'] * 100).round(0).astype('Int64').astype(str) + '%',
                     'Nachylenie (1 = ta sama skala)': gr['slope'].round(2),
                     'Najbliższa stacja GNSS [km, mediana]': gr['dist_station_km_median'].round(1)}))
display(Markdown(f"Po odniesieniu do reperów stabilnych typowa różnica w nieckach spada z "
                 f"**{gr['median_abs_diff_mm'].iat[1]:.1f} mm** do **{grw['median_abs_diff_mm'].iat[1]:.1f} mm**."))"""),
    ("md", """**Jak czytać:** w nieckach EGMS i niwelacja zgadzają się co do kierunku ruchu na każdym reperze, a skala ruchu jest
prawie 1:1. Niecki mają kilka kilometrów szerokości, a model GNSS do kalibracji EGMS ma siatkę około 50 km. Kalibracja
nie mogła ich więc „dorysować” — EGMS zmierzył je sam."""),
    ("md", """## 7. Największe rozbieżności"""),
    ("code", """#@title Trzy największe różnice w nieckach (pokazujemy też to, co nie pasuje)
nie = ok[ok['v_lev_mm_yr'].abs() >= strong]
top = nie.reindex(nie['diff_mm'].abs().sort_values(ascending=False).index).head(3)
tabela(pd.DataFrame({'Reper': top['benchmark_id'], 'Niwelacja [mm]': top['dh_lev_mm'].round(1),
                     'EGMS [mm]': top['dh_egms_mm'].round(1), 'EGMS − niwelacja [mm]': top['diff_mm'].round(1),
                     f'Niepewność EGMS ±{k:g}σ [mm]': (k * top['sigma_dh_mm']).round(1),
                     'Co to znaczy': top['diff_mm'].map(lambda d: 'EGMS: mniej osiadania' if d > 0 else 'EGMS: więcej osiadania')}))"""),
    ("md", """**Jak czytać:** we wszystkich trzech kierunek ruchu się zgadza. Część różnic „więcej osiadania” to ogólne przesunięcie
EGMS (kilka mm w 3 lata). Reper z dużą dodatnią różnicą odstaje naprawdę; prawdopodobna przyczyna (niesprawdzona) to
reper na brzegu niecki, gdzie komórka 100 × 100 m uśrednia teren osiadający szybciej i wolniej."""),
    ("md", """## Najważniejsze liczby"""),
    ("code", """#@title Podsumowanie liczbowe (czytane z plików wyników)
sm = pd.read_csv(C['summary'])
nach = sm.loc[sm['kryterium'].str.startswith('Nachylenie'), 'wynik'].iat[0].split(',')[0]
szyb = ok.sort_values('v_lev_mm_yr').iloc[0]
display(Markdown(
    f"- **{len(ok)} reperów** porównanych; zmiana wysokości z EGMS idzie prawie 1:1 z niwelacją (nachylenie {nach}).\\n"
    f"- **Niecki ({int(gr['n'].iat[1])} reperów):** kierunek ruchu zgodny w {gr['sign_agreement'].iat[1]:.0%}, "
    f"nachylenie {gr['slope'].iat[1]:.2f}.\\n"
    f"- **Najszybciej osiadający reper {szyb['benchmark_id']}:** niwelacja {szyb['dh_lev_mm']:+.0f} mm, "
    f"EGMS {szyb['dh_egms_mm']:+.0f} mm.\\n"
    f"- **Przesunięcie EGMS:** {off['offset_egms_minus_lev_mm_yr']:+.2f} mm/rok względem reperów stabilnych.\\n"
    f"- **Niepewność EGMS** (mediana, ±{k:g}σ): ±{k * unc['median_sigma_dh_mm']:.1f} mm; w granicach niepewności "
    f"{unc['share_within_absolute']:.0%} reperów (po odjęciu wspólnego przesunięcia {unc['share_within_relative']:.0%})."))"""),
    ("md", """## Wniosek

- **Niwelacja, pomiar niezależny od GNSS, potwierdza osiadanie widoczne w EGMS:** to samo położenie niecek, ten sam
  kierunek ruchu i prawie ta sama skala.
- **EGMS mierzy ruch sam,** nie tylko powtarza kalibrację GNSS: niecki są dużo mniejsze niż siatka modelu kalibracji.
- **Poziom bezwzględny wymaga ostrożności:** EGMS ma przesunięcie około 1–2 mm/rok. Przy ruchu poniżej ~2 mm/rok i przy
  wysokościach bezwzględnych potrzebny jest punkt odniesienia z pomiaru naziemnego.
- EGMS jest produktem archiwalnym, aktualizowanym raz w roku; nie wykrywa zdarzeń nagłych.

**Czego tu nie ma:** porównania z GNSS w NRW (w obszarze nie ma osiadającej stacji — wynik nierozstrzygnięty),
krzywych „czasu do wykrycia” (metoda wymaga poprawki) i własnego przetwarzania Sentinel-1 (nieuruchomione). Szczegóły:
`EGMS_Monitoring.ipynb` i `docs/evidence/F10_NRW_niwelacja_EGMS.md`.

**Źródła:** EGMS (Copernicus Land Monitoring Service); niwelacja: Geobasis NRW; porównanie z niwelacją w NRW: Even,
Westerhaus, Kutterer (2024), PFG 92:253–270; progi: Koudogbo i in. (2025) EGMS Validation Report."""),
]

NOTEBOOKS = {"Pokaz_1_GNSS_Groningen.ipynb": GNSS, "Pokaz_2_Niwelacja_NRW.ipynb": NIWELACJA}


def create_notebook(path: Path, cells_spec: list) -> None:
    cells = []
    for i, (kind, src) in enumerate(cells_spec):
        if kind == "code" and not src.startswith("#@title "):
            raise ValueError(f"{path.name}, komórka {i}: komórka kodu bez '#@title' (kod ma być ukryty w formularzu)")
        if kind == "code":
            compile(src, f"{path.name}, komórka {i}", "exec")     # błąd składni = wyjątek przy generowaniu, nie w Colab
        cell = {"cell_type": "markdown" if kind == "md" else "code", "id": f"{path.stem.lower()}-{i:02d}",
                "metadata": {"cellView": "form"} if kind == "code" else {}, "source": src.splitlines(keepends=True)}
        if kind == "code":
            cell.update(execution_count=None, outputs=[])
        cells.append(cell)
    nb = {"nbformat": 4, "nbformat_minor": 5, "cells": cells,
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                       "language_info": {"name": "python"}, "colab": {"provenance": []}}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Zapisano {path}")


if __name__ == "__main__":
    for name, spec in NOTEBOOKS.items():
        create_notebook(Path(__file__).resolve().parent / "notebooks" / name, spec)
