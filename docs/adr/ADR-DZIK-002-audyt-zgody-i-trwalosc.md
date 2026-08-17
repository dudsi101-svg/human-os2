# ADR-DZIK-002: Audyt, zgody i trwałość — integracja z hos_engine

Status: Accepted · Data: 2026-08-17 · Dotyczy: `apps/dzik-os/backend`

## Kontekst

`hos_engine` dostarcza sprawdzone prymitywy (275 testów), ale większość
rejestrów jest in-memory (audyt repozytorium, §8 „Nothing is persisted
unless you wire it"). Aplikacja domenowa potrzebuje trwałości bez
reimplementowania reguł Core.

## Decyzje

1. **Łańcuch audytu = `hos_engine.sqlite_store.SQLiteEventStore`**
   (hash chain, `verify_chain()`), zawsze w dedykowanym pliku SQLite
   (`DZIK_AUDIT_DB`), również przy głównej bazie PostgreSQL. Wielowątkowość
   serwera HTTP obsługuje podklasa `ThreadSafeEventStore` (wymiana
   połączenia + blokada wokół `append`) — **Core pozostaje niezmieniony**;
   pełna regresja Core wykonana (275 pass).
2. **Pokwitowania**: tabela `receipts` w bazie głównej wiąże odpowiedź API
   z `event_id`/`event_hash` łańcucha (wzorzec ActionReceipt/ADR-ARCH-003).
3. **Zgody**: wiersze `consents` w DB są źródłem trwałości; autoryzacja
   deleguje do `hos_engine.consent.ConsentRegistry.authorize` na rejestrze
   hydratowanym z aktywnych wierszy (ConsentService). Reguły zgód mają
   jedno źródło prawdy — Core. Kontrakt „cofa wyłącznie podmiot" zachowany.
4. **Identyfikatory** w formacie kanonicznym `HOS-<PREFIX>-<HEX12>`
   (zgodne z DD-010).
5. **Świadomie NIE podłączono** (moduł istnieje ≠ moduł potrzebny):
   DecisionEngine, ExperimentEngine, SelfModelService, RecoveryKernel,
   EmergencyRoot, KnowledgeGraph, AgentRuntime, simulation. Uzasadnienie:
   MVP nie podejmuje decyzji algorytmicznych, nie prowadzi eksperymentów
   N-of-1 i nie ma agentów AI; podłączanie tych modułów „bo istnieją"
   zwiększałoby powierzchnię błędu. Znany bug Core (emisja zdarzeń
   ExperimentEngine niezgodna ze schematem EventStore) dodatkowo
   potwierdza decyzję o niepodłączaniu go w MVP.

## Znane ograniczenie

Audyt w osobnym pliku ⇒ zdarzenie może powstać mimo rollbacku transakcji
głównej DB (nadmiarowy wpis; nigdy brakujący). Akceptowane w MVP —
rejestr ryzyk R-04; docelowo outbox lub `state_checkpoint` z Core.
