# Model zgód Dzik OS (od 0.11.0) — kategorie, dane, migracja, plan wycofania

> Dokument techniczny opisujący przebudowę systemu zgód (RODO).
> **Nie jest poradą prawną.** Miejsca wymagające decyzji administratora
> danych oznaczono „DECYZJA ADMINISTRATORA DANYCH".

## 1. Kategorie zgód (jedno źródło prawdy: `backend/dzik_os/consent_catalog.py`)

Zgody są rozdzielone na odrębne, jednoznaczne kategorie. Kategorie
**wymagane** (podstawa umowna — potwierdzenie warunków, nie zgoda opt-in)
i **opcjonalne** (właściwe zgody, art. 6 ust. 1 lit. a / art. 9 ust. 2
lit. a) nigdy nie są łączone w jedną decyzję.

| Klucz | Nazwa | purpose/domain | Odbiorca | Wymagana | Wrażliwa (art. 9) | Podstawa |
|---|---|---|---|---|---|---|
| `prowadzenie_konta` | Prowadzenie konta | account/account_data | SYSTEM | tak | nie | 6(1)(b) |
| `udostepnianie_trenerowi` | Dane współpracy dla trenera | coaching/collaboration | trener | tak | nie | 6(1)(b) |
| `dane_treningowe` | Dane treningowe | coaching/training_data | trener | tak | nie | 6(1)(b) |
| `komunikacja` | Komunikacja z trenerem | communication/messages | trener | tak | nie | 6(1)(b) |
| `dane_zdrowotne` | Dane zdrowotne | coaching/health_data | trener | nie | tak | 9(2)(a) |
| `zywienie_alergie` | Żywienie i alergie | coaching/nutrition_data | trener | nie | tak | 9(2)(a) |
| `zdjecia_progresu` | Zdjęcia progresu | coaching/progress_photos | trener | nie | tak | 9(2)(a) |
| `przypomnienia` | Push/przypomnienia | reminders/push_notifications | SYSTEM | nie | nie | 6(1)(a) |
| `funkcje_ai` | Funkcje AI (podsumowania i dokładniejsze przepisywanie tekstu ze zdjęcia) | ai_features/checkin_summaries | SYSTEM | nie | tak | 9(2)(a) |
| `marketing` | Marketing | marketing/contact_data | trener | nie | nie | 6(1)(a) |

Każda kategoria niesie pełny opis prezentowany klientowi przed decyzją:
**cel, zakres danych, odbiorców, okres przechowywania, informację o
dobrowolności, sposób wycofania i wersję dokumentu**
(`CONSENT_DOC_VERSION`, obecnie `2.2` — wersja podbita w 0.27.0 wraz
z rozszerzeniem opisu kategorii `funkcje_ai` o trzeci cel przetwarzania:
dokładniejsze przepisywanie tekstu ze zdjęcia, `docs/OCR.md`; wcześniej
`2.1` w 0.22.0 — wersja robocza podsumowania rozmowy startowej,
`docs/ONBOARDING_AI.md`).

Mapowanie kategorii na endpointy (egzekwowane w
`authz.resolve_client_access(domain=...)`):

* `collaboration` — profil współpracy (pola niewrażliwe), dokumenty,
  ewidencja płatności, historia zmian, pliki bez referencji;
* `training_data` — plany treningowe, wyniki, harmonogram + adherencja,
  cele, rekordy/siła w czasie, załączniki wpisów treningowych;
* `health_data` — pomiary, raporty tygodniowe (sen/stres/ból…),
  obserwacje, agregat monitoringu, pole profilu `urazy`, podsumowania AI
  (dodatkowo bramka `funkcje_ai`);
* `nutrition_data` — plany żywieniowe, dziennik kaloryczny, pola profilu
  `alergie`, `preferencje_zywieniowe` i `suplementacja_deklaracja`,
  dokumenty kategorii DIETA;
* `progress_photos` — lista zdjęć i pliki zdjęć progresu;
* `messages` — wątki wiadomości i załączniki wiadomości. (Terminarz
  konsultacji działa na samej aktywnej relacji — rezerwacja jest akcją
  klienta i nie niesie danych zdrowotnych.)

Pola wrażliwe profilu są filtrowane per pole: cofnięcie zgody
„żywienie i alergie" ukrywa przed trenerem `alergie` i
`preferencje_zywieniowe`, nie cały profil.

Od 0.22.0 zgody `dane_zdrowotne` i `zywienie_alergie` sterują dodatkowo
**samym zadawaniem pytań** w konwersacyjnym onboardingu: bez aktywnej
zgody krok wrażliwy w ogóle nie powstaje (nie zbieramy danych, których
nie wolno nam przechowywać), a przy zatwierdzeniu podsumowania pola
z tych kategorii nie trafiają do profilu. Zgoda `funkcje_ai` jest
osobną, niezależną bramką wysyłki do dostawcy modelu — jej brak nie
blokuje rozmowy, tylko przełącza podsumowanie w tryb deterministyczny
z jawnym komunikatem (`docs/ONBOARDING_AI.md`).

## 2. Model danych

`ConsentRecord` (tabela `consents`) — nowe kolumny (migracja nr 10):

* `category` — klucz kategorii z katalogu; `NULL` = **historyczna zgoda
  parasolowa** sprzed podziału (patrz §4);
* `legal_basis` — podstawa prawna zapisana w chwili udzielenia (historia
  nie zmienia się razem z katalogiem);
* `source` — `SUBJECT` (podmiot osobiście) / `ONBOARDING_DECLARATION`
  (deklaracja z onboardingu oczekująca potwierdzenia) / `SEED` (demo);
* `denied_at` — jawna odmowa zgody opcjonalnej (wiersz z `denied_at`
  nigdy nie autoryzuje; historia decyzji negatywnych).

Pozostałe pola bez zmian: `confirmed_at` (potwierdzenie podmiotu),
`revoked_at` (cofnięcie — wiersz nigdy nie jest usuwany),
`consent_text_version` (wersja dokumentu, na którą wyrażono zgodę).

Zdarzenia audytowe (łańcuch hash-chained Human OS): `CONSENT_GRANTED`
(z kategorią, podstawą, źródłem, wersją), `CONSENT_CONFIRMED`,
`CONSENT_REVOKED`, `CONSENT_DECLINED`. Payloady zawierają wyłącznie
identyfikatory i metadane — nigdy treść danych zdrowotnych.

**Minimalizacja danych technicznych:** nie zapisujemy adresów IP,
fingerprintów przeglądarki ani innych danych technicznych przy zgodach —
tożsamość decyzji gwarantuje uwierzytelniona sesja + łańcuch audytu.

## 3. API

* `GET /api/me/consents` — historia zgód podmiotu + pełny katalog
  kategorii + `document_version`; każdy wiersz ma
  `document_version_current` (czy wersja dokumentu z chwili zgody jest
  nadal bieżąca).
* `POST /api/me/consents` `{category, grantee_id?}` — udzielenie JEDNEJ
  kategorii (cel/zakres/wrażliwość/podstawa z katalogu, nie z żądania).
* `POST /api/me/consents/decline` `{category, grantee_id?}` — jawna
  odmowa zgody opcjonalnej (422 dla kategorii wymaganych).
* `POST /api/me/consents/{id}/confirm` — potwierdzenie deklaracji z
  onboardingu (per kategoria).
* `POST /api/me/consents/{id}/revoke` — cofnięcie; dla kategorii
  `przypomnienia` usuwa też wszystkie subskrypcje push użytkownika.

Nie istnieje żaden endpoint „zaakceptuj wszystko". W UI jedyna decyzja
grupowa to potwierdzenie **kategorii wymaganych** — wszystkie wynikają z
jednej umowy o prowadzenie trenerskie (cele rzeczywiście łączliwe);
każda zgoda opcjonalna ma osobne przyciski „Wyrażam zgodę"/„Odmawiam".

## 4. Zgody historyczne (parasolowe) i kompatybilność

Wiersze sprzed migracji (`category IS NULL`, `coaching/health_data`,
`allow_sensitive=1`) były udzielane jako **pełny dostęp trenerski**.
`ConsentService._hydrate` hydratuje je na wszystkie domeny trenerskie —
migracja **nie zawęża po cichu** zakresu udzielonej zgody ani jej nie
unieważnia. Klient widzi taki wiersz w Profilu jako „zgodę parasolową"
i może ją cofnąć; nowe zgody są zawsze granularne.

DECYZJA ADMINISTRATORA DANYCH: czy poprosić istniejących klientów o
ponowne, granularne wyrażenie zgód (rekomendowane — pełna zgodność z
nowym wzorcem), czy honorować zgody parasolowe do naturalnej rotacji.
Techniczna ścieżka: klient cofa parasolową i udziela granularnych w
Profilu.

## 5. Onboarding i pierwszeństwo decyzji klienta

* NOWE konto zakładane przez trenera: rejestrowane są WYŁĄCZNIE
  deklaracje kategorii z `ONBOARDING_CATEGORIES` (konto, współpraca,
  trening, komunikacja + trzy wrażliwe), każda jako osobny wiersz
  `source=ONBOARDING_DECLARATION`, `confirmed_at=NULL`. Kategorie czysto
  opcjonalne (przypomnienia, AI, marketing) NIGDY nie są rejestrowane
  przez trenera.
* Przy pierwszym logowaniu klient na ekranie „Twoje dane, Twoja zgoda"
  potwierdza warunki wymagane (razem — jedna umowa) i decyduje o każdej
  zgodzie wrażliwej OSOBNO (Wyrażam zgodę / Odmawiam). Odmowa jest
  zapisywana w historii (`denied_at`).
* ISTNIEJĄCE konto podpinane przez (innego) trenera: żadna zgoda nie
  jest rejestrowana — trener widzi `consent_active=false` do czasu, aż
  klient sam udzieli zgód (P3; zachowane i rozszerzone).

DECYZJA ADMINISTRATORA DANYCH: deklaracje z onboardingu autoryzują
dostęp trenera **prowizorycznie** do chwili decyzji klienta (trener może
przygotować plan przed pierwszym logowaniem). Jeżeli administrator uzna,
że dostęp ma być zablokowany do potwierdzenia — należy odfiltrować
wiersze `confirmed_at IS NULL AND source='ONBOARDING_DECLARATION'` w
`ConsentService._hydrate` (zmiana jednej metody; test
`test_onboarding_registers_separate_declarations_per_category` do
aktualizacji).

## 6. Wycofanie zgody

* Równie łatwe jak udzielenie: jeden przycisk w Profilu → Prywatność i
  zgody (klient) — bez formularzy, bez kontaktu z trenerem.
* Działa natychmiast: decyzja autoryzacyjna zapada przy każdym żądaniu
  (hydratacja rejestru z aktywnych wierszy), więc kolejne żądanie
  trenera dostaje 404; dotyczy także ISTNIEJĄCYCH plików.
* `przypomnienia`: cofnięcie usuwa wszystkie subskrypcje push (kanał
  doręczeń przestaje istnieć — nie tylko „nie wysyłamy").
* `funkcje_ai`: cofnięcie blokuje podsumowania AI raportów klienta
  niezależnie od woli trenera oraz przełącza przepisywanie tekstu ze
  zdjęcia w tryb lokalny — funkcja działa dalej, ale zdjęcie nie opuszcza
  aplikacji (`docs/OCR.md` §1). Reguła zgody żyje w JEDNYM miejscu:
  `authz.ai_features_consent_active`.

## 7. Migracja nr 10 i plan wycofania (rollback)

Migracja `10 — granular consent categories (RODO)`:

```sql
ALTER TABLE consents ADD COLUMN category VARCHAR(40);
ALTER TABLE consents ADD COLUMN legal_basis VARCHAR(120);
ALTER TABLE consents ADD COLUMN source VARCHAR(40);
ALTER TABLE consents ADD COLUMN denied_at VARCHAR(40);
```

Właściwości:

* **czysto addytywna** — żadne istniejące dane nie są modyfikowane ani
  usuwane; istniejące wiersze dostają `NULL` w nowych kolumnach i są
  interpretowane jako zgody parasolowe (§4);
* bezpieczna dla SQLite i PostgreSQL (proste `ALTER TABLE ADD COLUMN`).

**Plan wycofania:**

1. Wdrożyć poprzednią wersję aplikacji (kod sprzed 0.11.0 ignoruje nowe
   kolumny — ORM sprzed zmiany ich nie mapuje; stary `_hydrate` czyta
   `purpose/domain` wprost, więc historyczne wiersze parasolowe działają
   jak przed migracją).
2. Usunąć stempel migracji: `DELETE FROM schema_migrations WHERE
   version = 10;` (kolumny mogą zostać — są nieużywane; ewentualne
   `ALTER TABLE ... DROP COLUMN` jest możliwe na obu silnikach, ale
   niekonieczne).
3. Uwaga funkcjonalna: wiersze granularne utworzone w 0.11.0 będą przez
   stary kod interpretowane dosłownie (pojedynczy purpose/domain), więc
   klienci, którzy w 0.11.0 udzielili wyłącznie zgód granularnych, po
   rollbacku będą dla starego kodu (pytającego o `coaching/health_data`)
   mieli tylko zakres `dane_zdrowotne`. Rollback nie rozszerza niczyich
   uprawnień — może je co najwyżej zawęzić (bezpieczny kierunek).

## 8. Testy (backend/tests)

* `test_consents.py` — cofnięcie per kategoria odbiera dostęp tylko do
  tej kategorii (zdrowie/żywienie/zdjęcia), ponowne udzielenie, historia,
  izolacja cudzych zgód, kompletność katalogu.
* `test_consent_categories.py` — odmowa opcjonalnej (z historią i
  audytem), zakaz odmowy wymaganej, nieznana kategoria, wersjonowanie
  dokumentu, bramka AI, push↔zgoda `przypomnienia`, onboarding per
  kategoria, honorowanie zgody parasolowej sprzed migracji.
* `test_privacy.py` — eksport (nowe sekcje), usunięcie konta (push,
  wolne teksty, zachowanie danych rozliczeniowych).
* `test_password_and_confirmation.py` — migracja v1→v10 na istniejącej
  bazie (stuby tabel + asercje nowych kolumn).
