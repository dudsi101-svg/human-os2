# Plan sesji: przypięcie łańcucha dostaw + pip-audit (audyt Sprint B, pozycja B2)

**Gałąź:** `agent/przypiecie-lancucha` (od `main` = c3ce965)
**Rola:** aktywny piszący
**Cel:** to, co uruchamia CI i buduje obraz produkcyjny, przestaje być
ruchomym celem: akcje po pełnym SHA commita, obrazy bazowe po digeście,
`npm ci` zamiast `npm install`, znane podatności zależności blokują CI.

## Zamiar

1. **Przypięcie akcji po SHA** (z komentarzem `# vX.Y.Z` dla czytelności)
   w workflow aplikacji: `dzik-os-ci.yml` i wszystkich `fly-*.yml`.
   SHA rozwiązane dziś przez `git ls-remote` z oficjalnych repo:
   checkout v4.4.0, setup-python v5.6.0, setup-node v4.4.0,
   upload-artifact v4.6.2, flyctl-actions master (=tag 1.6).
2. **Obrazy bazowe po digeście** w `apps/dzik-os/Dockerfile`
   (`node:22-alpine@sha256:…`, `python:3.12-slim@sha256:…` — digesty
   z rejestru Docker Hub z dziś).
3. **`npm ci`** zamiast `npm install` w CI i Dockerfile (lockfile jest
   w repo — build przestaje móc cicho podnieść zależność).
4. **`pip-audit` jako blokujący krok** w jobie `quality` `dzik-os-ci`
   (audyt zainstalowanego środowiska backendu; znana podatność =
   czerwony build; wyjątki tylko jawne w workflow z komentarzem).
5. **`spojnosc.py` — 13. kontrola `sprawdz_przypiecie`:** każdy `uses:`
   w `dzik-os-ci.yml`/`fly-*.yml` musi wskazywać pełny 40-znakowy SHA —
   regres pinowania czerwieni bramkę (TDD: czerwona przed zmianą).

## Świadomie nie robię

- nie dotykam `ci.yml` (Core) ani `pages.yml` — poza zakresem pracy
  aplikacyjnej; odnotowane jako rekomendacja dla sesji Core;
- nie podnoszę wersji major akcji (checkout zostaje w linii v4 itd.) —
  pinowanie i upgrade to osobne decyzje;
- automatycznej aktualizacji pinów (dependabot itp.) nie konfiguruję —
  decyzja właściciela (wpis w STAN_PRZEKAZANIA).

## Rezerwacje

- **Wersja: 0.53.8.** **Migracja: brak.**

## Weryfikacja (do wypełnienia)

- bramki + nowa kontrola czerwona→zielona; lokalny `npm ci` przechodzi;
  docker build nie jest możliwy w tym środowisku — smoke po deployu
  zweryfikuje obraz (health/build), odnotować w weryfikacji rundy.

## Weryfikacja (wykonana)

- Nowa kontrola „przypięcie akcji" najpierw CZERWONA (23 nieprzypięte
  `uses:` w 10 plikach), po przypięciu — czysto (**13 kontroli**).
- `ruff` — czysto; backend **850 passed, 1 skipped** (jedyna czerwień
  po drodze: strażnik wersji z B1 złapał niezaktualizowany README przy
  bumpie 0.53.8 — dokładnie po to istnieje; poprawione); Core **275**.
- Uruchomienie na żywo: `npm ci --no-audit --no-fund` w frontend/ —
  „added 78 packages"; `pip-audit --skip-editable` po aktualizacji
  toolchainu — kod 0 (przed aktualizacją: znane podatności
  setuptools/urllib3/wheel z systemowego Pythona kontenera — stąd
  krok aktualizacji w CI przed audytem).
- Budowa obrazu Dockera niemożliwa w tym środowisku — digesty
  zweryfikowane nagłówkiem `Docker-Content-Digest` z rejestru;
  faktyczny build zweryfikuje deploy po scaleniu (smoke health/build).
