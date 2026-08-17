# Raport końcowy — budowa Dzik OS MVP

Data: 2026-08-17 · Gałąź: `claude/dzik-os-personal-trainer-app-d3q7fx`

## 1. Co zostało stworzone

Kompletna aplikacja „Dzik OS — Panel Podopiecznego": backend FastAPI
zintegrowany z `hos_engine`, mobile-first PWA po polsku (aplikacja
klienta + panel trenera + panel admina), dane demonstracyjne, testy
(jednostkowe/API/uprawnień/E2E), Docker Compose, CI i pełna dokumentacja.
Repozytorium `human-os2` (puste na starcie) otrzymało jako bazę verbatim
snapshot `dudsi101-svg/human-os@68fe1e4` (ADR-DZIK-003).

## 2. Struktura

```
apps/dzik-os/
├── backend/           # FastAPI + SQLAlchemy (dzik_os), 14 routerów, seed
│   └── tests/         # 50 testów pytest
├── frontend/          # React+TS+Vite PWA (18 widoków/komponentów)
├── e2e/               # 3 testy Playwright (Chromium)
├── docs/              # 13 dokumentów (brief, mapy, instrukcje, raporty)
├── Dockerfile / docker-compose.yml / .env.example
docs/adr/ADR-DZIK-001..003   # decyzje architektoniczne
.github/workflows/dzik-os-ci.yml
```

## 3. Wykorzystane fundamenty Human OS

* `hos_engine.sqlite_store.SQLiteEventStore` — niemutowalny, hash-chained
  łańcuch audytu (+ wielowątkowa podklasa, Core bez zmian);
* `hos_engine.consent.ConsentRegistry` — autoryzacja zgód (trwała warstwa
  w DB, decyzja w Core);
* wzorce `authority.RoleGrant` (role jawne, zakresowe, odwoływalne),
  format ID `HOS-<PREFIX>-<HEX12>` (DD-010), typy zdarzeń w stylu
  `event.types.json`, pokwitowania w duchu `ActionReceipt`;
* kontrakt ADR-ARCH-003: `UI → Request → Core/Policy → Receipt → UI`;
* zasady konstytucyjne: własność danych, zgoda cofalna, brak cichego
  nadpisywania, proweniencja, brak oceny „wartości" człowieka.

## 4. Czego świadomie NIE wykorzystano (moduł istnieje ≠ moduł potrzebny)

DecisionEngine, ExperimentEngine, SelfModelService, RecoveryKernel,
EmergencyRoot, KnowledgeGraph, AgentRuntime, simulation — uzasadnienie w
ADR-DZIK-002 §5 (m.in. znany bug emisji zdarzeń ExperimentEngine).
Formalna ontologia 25 typów encji istnieje w repo tylko w prozie — 
mapowanie potraktowano koncepcyjnie, podzbiór oznaczono
`MVP_IMPLEMENTED_SUBSET` (ADR-DZIK-003).

## 5. Wyniki testów (lokalnie, 2026-08-17)

| Pakiet | Wynik |
|---|---|
| Regresja Core `tests/` | **275 passed** (bez zmian względem bazy) |
| Backend `apps/dzik-os/backend/tests` | **50 passed** |
| E2E przeglądarkowe `apps/dzik-os/e2e` | **3 passed** (Chromium, telefon+desktop) |
| `ruff check apps/dzik-os` | clean |
| `tsc -b && vite build` | clean (typecheck + build) |
| `pip-audit` (zależności backendu) | 0 znanych podatności |
| `npm audit --omit=dev` | 0 podatności (po podbiciu react-router do v7) |

## 6. Stan bezpieczeństwa

Zaimplementowane: izolacja klientów (testowana, 404 dla cudzych zasobów),
dostęp trenera = relacja+zgoda, admin bez danych zdrowotnych, bcrypt,
sesje z hashowanym tokenem i TTL, rate limiting logowania, walidacja
uploadów (typ/rozmiar/pusty plik, losowe nazwy, nosniff), brak sekretów w
repo (.env.example), brak danych kart, audyt operacji wysokiej wagi,
eksport i anonimizacja danych. Świadomie otwarte ryzyka (z planem):
RISK_REGISTER.md — najważniejsze przed produkcją: przegląd prawny RODO
(R-01), szyfrowanie at-rest (R-02), backupy (R-12), wymuszenie zmiany
hasła startowego (R-06).

## 7. Stan deploymentu

Lokalne uruchomienie jednym poleceniem (Compose z PostgreSQL) —
udokumentowane i zweryfikowane komponentowo; CI dodane
(`dzik-os-ci.yml`). **Deployment zdalny nie był możliwy z tej sesji**
(brak serwera docelowego i sekretów) — dokładna instrukcja ostatniego
kroku: docs/DEPLOYMENT.md §3–4. Stary deployment Pages dotyczy tylko
prototypu `apps/user-demo` i nie koliduje (DEPLOYMENT.md §6).

## 8. Dane demonstracyjne (wyłącznie lokalnie/staging)

`python -m dzik_os.seed` — trener **dzik@example.com / DzikTrener#2026**,
klienci **klient.a@example.com / KlientA#2026!x** i
**klient.b@example.com / KlientB#2026!x**, admin
**admin@example.com / DzikAdmin#2026**. Seed zawiera: profil, cele, plan
z 2 wersjami + szablon, dietę, harmonogram (w tym suplementy z autorem),
8 tyg. pomiarów, oceniony raport, wiadomości, dokument PDF, płatność
opłaconą/oczekującą/zaległą.

## 9. Znane ograniczenia

docs/DEFERRED_FEATURES.md (m.in. kopiowanie szablonów jednym kliknięciem,
reset hasła e-mailem, push notifications, webhook operatora płatności,
paginacja) oraz rejestr ryzyk R-01…R-12.

## 10. Następne kroki (propozycja kolejności)

1. Staging z HTTPS + test instalacji PWA na fizycznym telefonie.
2. R-06 (wymuszona zmiana hasła) i R-12 (backupy).
3. Przegląd prawny (R-01) przed pierwszym prawdziwym klientem.
4. Ekran potwierdzenia zgody przy pierwszym logowaniu (R-05).
5. Kopiowanie szablonu do klienta; powiadomienia push.

## 11. Polecenia uruchomienia

Patrz README aplikacji (sekcja „Szybki start") i docs/DEPLOYMENT.md —
wszystkie polecenia zostały wykonane i zweryfikowane w tej sesji.

## 12. Staging

Brak działającego stagingu (wymaga infrastruktury i sekretów właściciela
repo — patrz §7).

## 13. Commity

Praca w logicznych commitach na gałęzi
`claude/dzik-os-personal-trainer-app-d3q7fx` (import bazy → backend →
testy → frontend+E2E → infra+dokumentacja). PR nie został utworzony
(brak wyraźnego polecenia w briefie; gałąź jest wypchnięta i gotowa do PR).
