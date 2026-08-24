# Plan sesji: dostawca AI

**Gałąź:** `agent/dostawca-ai` (od `main` = `d1b3ed4`)
**Rola:** aktywny piszący i integrator (zgoda właściciela: „możesz ruszać
z AI"; obszar produktowy w całości — rozstrzygnięte w K-000)
**Cel:** prawdziwa implementacja kontraktu `AIProvider` — jedna zmiana
odblokowuje **cztery istniejące funkcje naraz**: OCR etykiet
(`ocr_ai.py`), odczyt opisów ćwiczeń (`exercise_parser_ai.py`),
onboarding wspierany AI (`onboarding_ai.py`) i asystenta trenera
(`coach_assistant.py`). Wszystkie cztery już wołają
`ai_provider.provider` i mają własne bramki zgód/limitów — brakuje
wyłącznie dostawcy.

## Stan zastany (zwiad)

* Kontrakt `AIProvider` (Protocol): `summarize_checkin`, `propose_json`
  (system_prompt / data_section rozdzielone — ochrona przed
  wstrzyknięciem), `propose_json_from_image` (vision; jedzie wyłącznie
  zdjęcie + rodzaj zadania, zero identyfikatorów).
* Konfiguracja gotowa: `DZIK_AI_ENABLED`, `DZIK_AI_TIMEOUT_S`, dzienne
  limity wywołań per użytkownik i globalnie, limit znaków wejścia.
* Wybór dostawcy: wzorzec `notifications_provider._zbuduj_provider()` —
  brak klucza = `Null`, zachowanie dokładnie dotychczasowe.

## Zamiar

**`AnthropicAIProvider`** przez oficjalny SDK `anthropic` (zgodnie
z referencją claude-api; nigdy surowe HTTP w projekcie z SDK):

* model domyślnie **`claude-opus-5`**, zmienialny przez `DZIK_AI_MODEL`;
  adaptacyjne myślenie (`thinking: {"type": "adaptive"}`);
* `propose_json`: system prompt aplikacji + dane użytkownika jako
  osobny blok user; odpowiedź to surowy tekst — walidacja schematem
  pozostaje po stronie wołających (tak jak dziś deklaruje kontrakt);
* `propose_json_from_image`: blok obrazu base64 + tekst zadania;
* `summarize_checkin`: jedno wywołanie z twardym schematem
  {summary, draft_response, flags}, parsowanie po stronie dostawcy,
  `None` przy niezgodnym JSON (UI ma tryb bez AI);
* **błędy nigdy nie wybuchają**: łańcuch wyjątków SDK (RateLimit →
  APIStatus → APIConnection) → `None` + log wyłącznie z klasą wyjątku
  i licznikami tokenów — **zero treści i zero PII w logach** (wzorzec
  SMTP z 0.42.0);
* liczniki `tokens_in/out` z `response.usage` (kontrola kosztów);
* klient wstrzykiwalny w konstruktorze — testy używają sztucznego
  klienta, żadnych prawdziwych wywołań w testach.

Builder: `DZIK_AI_ENABLED=true` **i** `DZIK_AI_API_KEY` ustawione →
Anthropic; inaczej Null. Sam klucz bez włącznika nie uruchamia niczego
(świadoma decyzja operatora ma być podwójna).

Zależność `anthropic` dochodzi do `backend/pyproject.toml`.

## Mój obszar

- `backend/dzik_os/ai_provider.py` (implementacja + builder);
- `backend/dzik_os/config.py` (`DZIK_AI_API_KEY`, `DZIK_AI_MODEL`,
  `DZIK_AI_MAX_TOKENS` — dopisanie pól);
- `backend/pyproject.toml` (zależność `anthropic`);
- `backend/tests/test_ai_provider.py` (nowy);
- `docs/DEPLOYMENT.md` (sekcja włączenia AI), `docs/CHANGELOG.md`,
  `docs/STAN_PRZEKAZANIA.md` (integrator); ten plan.

## Czego nie dotykam

- czterech modułów wołających (`ocr_ai`, `exercise_parser_ai`,
  `onboarding_ai`, `coach_assistant`) — kontrakt się nie zmienia,
  ich bramki zgód i limitów zostają jedynym wejściem;
- frontendu (UI już pokazuje oba stany: skonfigurowane/nie);
- migracji, seeda, Core.

## Rezerwacje

- **Wersja: 0.45.0** (ostatnia: 0.44.0). **Migracja: brak.**

## Świadomie nie robię

- nie wysyłam żadnego prawdziwego wywołania do API Anthropic — klucza
  nie ma w tym środowisku i nie powinno być; **tryb rozszerzony nigdy
  się nie wykonał** i mówię to wprost (ZASADA_URUCHOMIENIA: integracja
  zewnętrzna bez dostawcy = jawna deklaracja, nie markowanie);
- nie zmieniam zakresu danych wysyłanych do modelu — minimalizacja
  zdefiniowana w wołających (DATA_PROCESSING_MAP §AI) zostaje;
- nie dodaję streamingu ani cache — pierwsza wersja ma być prosta
  i poprawna; optymalizacje po pierwszych rachunkach za tokeny.

## Weryfikacja (do wypełnienia)

- pełne bramki §5 (frontend nietknięty — bez przebiegu, jawnie);
- uruchomienie na żywo BEZ klucza: aplikacja wstaje, cztery funkcje
  zgłaszają „wymaga konfiguracji" dokładnie jak dotąd;
- uruchomienie na żywo Z WSTRZYKNIĘTYM sztucznym klientem: pełna
  ścieżka propose_json → walidacja wołającego działa;
- instrukcja jednokomendowego włączenia dla właściciela
  (`flyctl secrets set DZIK_AI_API_KEY=... DZIK_AI_ENABLED=true`).
