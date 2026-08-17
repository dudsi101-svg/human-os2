# Mapa przetwarzania danych — Dzik OS

Charakter danych: dane zdrowotne i wizerunkowe (szczególne kategorie).
Administratorem danych klientów jest trener; aplikacja jest narzędziem.
Dokument opisuje stan MVP; przed produkcyjnym wdrożeniem wymagany
przegląd prawny (patrz RISK_REGISTER R-01).

| Kategoria danych | Przykłady | Cel | Podstawa | Kto widzi | Retencja |
|---|---|---|---|---|---|
| Identyfikacyjne | imię, e-mail | konto, kontakt | umowa o prowadzenie | klient, trener; admin (bez zdrowotnych) | do usunięcia konta |
| Profil treningowy | cel, doświadczenie, sprzęt, dni | dobór planu | umowa | klient, trener (za zgodą) | do usunięcia |
| Wrażliwe deklarowane | urazy, alergie, preferencje żywieniowe | bezpieczny plan | **zgoda** (health_data, sensitive) | klient, trener (za zgodą) | do usunięcia |
| Pomiary i raporty | masa, obwody, skale samopoczucia | monitorowanie postępów | zgoda | klient, trener (za zgodą) | do usunięcia |
| Zdjęcia sylwetki / filmy | progres, technika | ocena postępów/techniki | zgoda | klient, trener (za zgodą) | fizycznie usuwane przy anonimizacji |
| Harmonogram (w tym suplementy) | nazwa, dawka wpisana przez człowieka, autor | przypomnienia | zgoda | klient, trener | do usunięcia |
| Adherencja harmonogramu | odhaczenie wykonania per dzień, notatka | monitorowanie realizacji | zgoda | klient, trener (za zgodą) | notatka usuwana przy anonimizacji |
| Dziennik obserwacji | samopoczucie/reakcja, waga (informacja/niepokojące) | wychwycenie niekorzystnych reakcji do przeglądu przez trenera — **nigdy diagnoza** | zgoda | klient, trener (za zgodą) | fizycznie usuwane przy anonimizacji |
| Dziennik kaloryczny | kcal/makro/woda dzienne | monitorowanie realizacji diety | zgoda | klient, trener (za zgodą) | fizycznie usuwane przy anonimizacji |
| Wiadomości i dokumenty | treść, załączniki | komunikacja | umowa | strony wątku | anonimizowane przy usunięciu |
| Płatności | pakiet, kwota, termin, status | rozliczenia | umowa | klient, trener | metadane mogą pozostać w księgowości trenera |
| Zdarzenia audytu | identyfikatory, typ akcji, hash | bezpieczeństwo, rozliczalność | uzasadniony interes | admin (weryfikacja), trener (pokwitowania swoich klientów) | trwałe (łańcuch niemutowalny; bez danych zdrowotnych w payloadach jawnych pól profilu — payload zawiera klucze pól, nie wartości wrażliwe) |

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

* **AI**: w MVP żadne dane nie są wysyłane do zewnętrznych modeli AI
  (`DZIK_AI_ENABLED=false`; brak kodu wysyłającego). Ewentualne włączenie
  wymaga osobnej zgody i minimalizacji zakresu — patrz ADR-DZIK-001 §AI.
* **E-mail**: domyślnie żaden dostawca nie jest skonfigurowany
  (`notifications_provider.NullNotificationProvider` — nic nie wysyła,
  loguje wyłącznie temat, bez adresu i treści). Jedyny podpięty trigger:
  niepokojąca obserwacja → próba powiadomienia trenera. Podłączenie
  realnego dostawcy to decyzja operatora (klucze API poza repozytorium).
* **Płatności**: brak danych kart; opcjonalny zewnętrzny link płatności
  prowadzi bezpośrednio do operatora trenera.
* **Logi**: aplikacja nie loguje treści danych wrażliwych; audyt
  przechowuje identyfikatory i podsumowania operacyjne.
