# Mapa przetwarzania danych — Dzik OS

Charakter danych: dane zdrowotne i wizerunkowe (szczególne kategorie).
Administratorem danych klientów jest trener; aplikacja jest narzędziem.
Dokument opisuje stan MVP; przed produkcyjnym wdrożeniem wymagany
przegląd prawny (patrz RISK_REGISTER R-01).

> **Od 0.11.0** zgody są granularne per kategoria danych (osobno dane
> zdrowotne, żywienie/alergie, zdjęcia, komunikacja, przypomnienia,
> funkcje AI, marketing…) — kolumna „Podstawa" poniżej odnosi się do
> właściwej kategorii z `consent_catalog.py`. Dokumenty towarzyszące:
> `ZGODY_MODEL.md` (model zgód), `RODO_REJESTR_CZYNNOSCI.md` (rejestr
> czynności, procesorzy, retencja), `RODO_INCYDENTY.md` (incydenty),
> `RODO_DPIA.md` (ocena konieczności DPIA),
> `POLITYKA_PRYWATNOSCI_SZKIC.md` v0.2.

| Kategoria danych | Przykłady | Cel | Podstawa | Kto widzi | Retencja |
|---|---|---|---|---|---|
| Identyfikacyjne | imię, e-mail | konto, kontakt | umowa o prowadzenie | klient, trener; admin (bez zdrowotnych) | do usunięcia konta |
| Profil treningowy | cel, doświadczenie, sprzęt, dni | dobór planu | umowa | klient, trener (za zgodą) | do usunięcia |
| Wrażliwe deklarowane | urazy, alergie, preferencje żywieniowe | bezpieczny plan | **zgoda** (health_data, sensitive) | klient, trener (za zgodą) | do usunięcia |
| Pomiary i raporty | masa, obwody, skale samopoczucia | monitorowanie postępów | zgoda | klient, trener (za zgodą) | do usunięcia |
| Zdjęcia sylwetki / filmy | progres, technika | ocena postępów/techniki | zgoda | klient, trener (za zgodą) | fizycznie usuwane przy anonimizacji; nowe uploady zdjęć mają usuwane metadane EXIF (w tym geolokalizację GPS) i ograniczaną rozdzielczość już przy zapisie |
| Harmonogram (w tym suplementy) | nazwa, dawka wpisana przez człowieka, autor | przypomnienia | zgoda | klient, trener | do usunięcia |
| Adherencja harmonogramu | odhaczenie wykonania per dzień, notatka | monitorowanie realizacji | zgoda | klient, trener (za zgodą) | notatka usuwana przy anonimizacji |
| Dziennik obserwacji | samopoczucie/reakcja, waga (informacja/niepokojące) | wychwycenie niekorzystnych reakcji do przeglądu przez trenera — **nigdy diagnoza** | zgoda | klient, trener (za zgodą) | fizycznie usuwane przy anonimizacji |
| Dziennik kaloryczny | kcal/makro/woda dzienne | monitorowanie realizacji diety | zgoda | klient, trener (za zgodą) | fizycznie usuwane przy anonimizacji |
| Wiadomości i dokumenty | treść, załączniki | komunikacja | umowa | strony wątku | anonimizowane przy usunięciu |
| Płatności | pakiet, kwota, termin, status | rozliczenia | umowa | klient, trener | metadane mogą pozostać w księgowości trenera |
| Zdarzenia audytu | identyfikatory, typ akcji, hash | bezpieczeństwo, rozliczalność | uzasadniony interes | admin (weryfikacja), trener (pokwitowania swoich klientów) | trwałe (łańcuch niemutowalny; bez danych zdrowotnych w payloadach jawnych pól profilu — payload zawiera klucze pól, nie wartości wrażliwe) |

## Retencja plików (uzupełnienie)

* **Minimalizacja u źródła**: nowe uploady zdjęć są pozbawiane EXIF
  (w tym GPS) i rekompresowane (maks. 2560 px dłuższy bok) — aplikacja
  nigdy nie przechowuje geolokalizacji zdjęć. Pliki wgrane przed tą
  zmianą pozostają na dysku w oryginalnej postaci (bez retroaktywnego
  przetwarzania); są objęte tym samym reżimem dostępu i usuwania.
* **Pliki-sieroty**: upload nie podpięty do żadnego zasobu (raport,
  wiadomość, dokument, baza wiedzy, trening) jest po 24 h oznaczany
  `deleted_at` i usuwany z dysku (metadane zostają dla rozliczalności).
* **Odpowiedzi plikowe** mają `Cache-Control: no-store` — dane
  zdrowotne/wizerunkowe nie trafiają do cache przeglądarki ani
  pośredników.
* **Usunięcie konta** (poniżej) fizycznie usuwa pliki z dysku;
  **eksport** (`/api/me/export`) wymienia pliki z identyfikatorami do
  pobrania przez uwierzytelnione `/api/files/{id}`.

## Prawa użytkownika (wbudowane w aplikację)

* **Wgląd/eksport**: `GET /api/me/export` — pełny JSON wszystkich danych
  (przycisk w Profilu).
* **Poprawianie**: profil i raporty edytowalne z zachowaniem historii wersji.
* **Cofnięcie zgody**: Profil → Zgody → „Cofnij" — natychmiast odbiera
  trenerowi dostęp do danych zdrowotnych.
* **Usunięcie**: Profil → „Usuń konto i dane" (hasło + fraza
  `USUŃ MOJE DANE`): anonimizacja konta, wyczyszczenie pól profilu,
  usunięcie pomiarów i zdjęć **fizycznie z dysku**, anonimizacja
  wiadomości. Łańcuch audytu zachowuje wyłącznie identyfikatory
  i typy operacji.

## Przepływy poza aplikację

* **AI**: domyślnie żaden dostawca nie jest skonfigurowany
  (`ai_provider.NullAIProvider` — nic nie wysyła, zawsze zwraca „wymaga
  konfiguracji"). Jedyny podpięty, propose-only use case: podsumowanie
  raportu tygodniowego + szkic odpowiedzi dla trenera — wynik nigdy nie
  trafia do klienta bez edycji/zatwierdzenia przez trenera. Podłączenie
  realnego dostawcy wymaga osobnej decyzji, minimalizacji wysyłanego
  zakresu i — jeśli dane klienta miałyby opuszczać system — osobnej
  zgody — patrz ADR-DZIK-001 §AI.
* **E-mail**: domyślnie żaden dostawca nie jest skonfigurowany
  (`notifications_provider.NullNotificationProvider` — nic nie wysyła,
  loguje wyłącznie temat, bez adresu i treści). Jedyny podpięty trigger:
  niepokojąca obserwacja → próba powiadomienia trenera. Podłączenie
  realnego dostawcy to decyzja operatora (klucze API poza repozytorium).
* **Płatności**: brak danych kart; opcjonalny zewnętrzny link płatności
  prowadzi bezpośrednio do operatora trenera.
* **Logi**: aplikacja nie loguje treści danych wrażliwych; audyt
  przechowuje identyfikatory i podsumowania operacyjne.
