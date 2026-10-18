# 4. Migracja na nowe konto — lista kroków

> EGMS Check (GeoWorldLook) — przekazanie projektu, stan 2026-10-10, gałąź `claude/dreamy-dirac-jd4vue`.
> Indeks: [`../MIGRACJA_stan_i_audyt.md`](../MIGRACJA_stan_i_audyt.md)

1. **GitHub.** Właściciel `geoworldlook` dodaje nowe konto jako współpracownika z prawem zapisu albo przenosi
   repozytorium. Jeśli zmieni się właściciel lub nazwa: poprawić adres w `build_colab_master.py` (sekcja 0,
   `git clone`), w README i w linku Colab, potem `python build_colab_master.py`.
   Rozważyć scalenie gałęzi `claude/dreamy-dirac-jd4vue` z `main` przez PR (decyzja otwarta).
2. **Claude Code na nowym koncie.** Zainstalować aplikację GitHub Claude dla repozytorium i podłączyć GitHub
   w ustawieniach claude.ai. Pierwsza wiadomość w nowej sesji: `08_prompt_nowa_sesja.md`.
3. **Klucz CLMS (Copernicus Land).** Na nowym koncie CLMS wygenerować nowy klucz serwisowy (JSON z `client_id`,
   `user_id`, `token_uri`, `private_key`) i zapisać jako `MyDrive/GeoWorldLook/secrets/clms_token.json`
   na nowym Dysku. **Stary klucz unieważnić** w profilu CLMS. Uwaga bezpieczeństwa: `05_audyt.md`, 5.5.
4. **Dysk Google.** Skopiować `MyDrive/GeoWorldLook/egmscheck/data/02_Raw_Ground/3_gnss_ngl/` i
   `data/00_Metadata/MANIFEST.csv` (oszczędza pobierania; niekonieczne). Jeśli wycinek
   `data/03_Extracts/groningen/egms_l2b_points.csv.gz` już powstał, skopiować go — notatnik wtedy nie pobiera
   4,4 GB. Udostępnić folder `/drive/EGMS` z PDF publikacji.
5. **Pełne teksty publikacji.** W nowej sesji Claude odtworzyć `docs/evidence/literatura_txt/` z PDF
   (lista plików w README tego katalogu; poziomy weryfikacji źródeł w plikach `F*`).
6. **Sprawdzenie.** W Colab: `Uruchom wszystko`. Sekcje 0–4 muszą dać 35 stacji (27 + 8) i 31 plików,
   4443 MB. Inny wynik oznacza zmianę danych NGL — zapisać datę i nie zmieniać reguły.
