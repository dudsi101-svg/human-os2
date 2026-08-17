# ADR-DZIK-003: Import fundamentów do human-os2 i mapowanie na ontologię

Status: Accepted · Data: 2026-08-17 · Dotyczy: całe repozytorium `human-os2`

## 1. Import fundamentów (kontekst i decyzja)

Zadanie: zbudować Dzik OS na fundamentach repozytorium
`dudsi101-svg/human-os`, ale gałąź robocza wskazana do developmentu leży w
**pustym** repozytorium `dudsi101-svg/human-os2`. Aby aplikacja mogła
faktycznie importować `hos_engine` i aby repozytorium było samowystarczalne,
zawartość `human-os@68fe1e4e4d5e893512f6cce27679ad7d9cee321f` została
zaimportowana **verbatim** jako commit bazowy (oznaczony w opisie commita),
bez modyfikacji jakiegokolwiek pliku Human OS. To import z zachowaniem
pochodzenia, nie niezależna kopia: zmiany Dzik OS żyją wyłącznie w
`apps/dzik-os/`, `docs/adr/ADR-DZIK-*` i plikach rejestrów (adnotacje
addytywne). Licencje zachowane (kod Apache-2.0, dokumentacja CC BY 4.0);
nazwa produktu („Dzik OS") jest odrębna od znaku „Human OS", zgodnie z
LICENSE-DECISION.md.

## 2. Konflikt: ontologia formalna istnieje tylko w prozie

Brief mapuje encje Dzik OS na typy IDENTITY/PROFILE/GOAL/WORKFLOW/TASK/
DOCUMENT/METRIC/DECISION/CONSENT/COMMITMENT/EXPERIMENT/VERSION. Audyt
repozytorium wykazał, że ta lista („Formal Entity & Relation Model")
występuje **wyłącznie jako proza** (hub_entity_registry.py:13-20,
docs/HOS_ENTITY_RELATION_EVENT_SCHEMA_v0.1.md §4.3) — bez definicji pól,
bez walidacji — z wyraźnym zakazem wygodnego mapowania na zaimplementowaną
szóstkę typów Hub.

**Decyzja (najmniej ryzykowna):** Dzik OS traktuje mapowanie briefu jako
**konceptualne** i NIE implementuje encji względem niezaimplementowanej
ontologii. Runtime używa: konwencji ID, kontraktu zgód, typów zdarzeń w
stylu `event.types.json`, ról uprawnień (wzorzec authority.py) i łańcucha
zdarzeń. Zaimplementowany podzbiór jest oznaczony
**`MVP_IMPLEMENTED_SUBSET`** — częściowa implementacja nie jest
przedstawiana jako pełny Human OS. Mapowanie domena→ontologia pozostaje
udokumentowane w tabeli poniżej i może zostać zrealizowane, gdy formalna
ontologia otrzyma schematy.

| Encja Dzik OS | Docelowy typ (koncepcyjnie) | Implementacja MVP |
|---|---|---|
| users/identity | IDENTITY | tabela users + identity_id |
| profile_fields | PROFILE | wersjonowane pola z proweniencją |
| goals | GOAL | tabela goals |
| training/nutrition plan | WORKFLOW | plan + niemutowalne wersje |
| workout_session/entry | TASK/OUTCOME | tabele sesji i wpisów |
| documents/files | DOCUMENT/RESOURCE | tabele + storage |
| weekly_checkins | INTERACTION + EVENT | raporty + zdarzenia audytu |
| measurements | METRIC | tabela measurements |
| wersja planu z powodem | DECISION + VERSION | version_no + reason + zdarzenie |
| consents | CONSENT | trwała warstwa ConsentRegistry |
| payment_records | COMMITMENT | terminy i statusy płatności |

## 3. Inne odnotowane konflikty źródeł (bez cichego wyboru)

* **CLAUDE.md przestarzały** względem kodu (wersja, mypy w CI, recovery
  „zero code"). Przyjęto stan faktyczny kodu i README/manifest; CLAUDE.md
  nie poprawiano (poza zakresem zadania Dzik OS).
* **TEST_RESULTS.txt stale** (28 testów z ery 0.9.0 vs. 275 obecnie).
  Nie nadpisano; wyniki Dzik OS raportowane w apps/dzik-os/docs/FINAL_REPORT.md.
* **Dwa słowniki relacji i trzy słowniki statusów** — Dzik OS nie używa
  żadnego z nich bezpośrednio (statusy domenowe własne, nazwane jawnie),
  więc nie przesądza ich unifikacji.

## 4. Napięcie normatywne: suplementy

`docs/INTENDED_PURPOSE.md` (aplikacja osobista Human OS) wyklucza
funkcje dot. suplementów i dawek. Dzik OS jest **innym produktem**
(narzędzie trenera) i ma odrębny intended purpose; mimo to przejęto
najostrzejszą bezpieczną interpretację: system **wyłącznie przechowuje
i przypomina** harmonogram wprowadzony świadomie przez człowieka, z
obowiązkowym autorem zalecenia; nie zawiera żadnego kodu dobierającego,
zwiększającego ani sugerującego dawkowanie czegokolwiek. Granica
prawna (wyrób medyczny) do ponownej oceny przy rozwoju — rejestr ryzyk
R-10.
