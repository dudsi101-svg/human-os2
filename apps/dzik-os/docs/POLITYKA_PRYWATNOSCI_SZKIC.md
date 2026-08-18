# Polityka prywatności Dzik OS — SZKIC v0.1 (2026-08-17)

> **STATUS: SZKIC DO KONSULTACJI PRAWNEJ.** Ten dokument jest punktem
> wyjścia przygotowanym technicznie na podstawie faktycznego działania
> aplikacji. **Nie jest poradą prawną.** Przed użyciem wobec prawdziwych
> klientów wymaga weryfikacji przez prawnika (dane zdrowotne = szczególna
> kategoria danych, art. 9 RODO) oraz uzupełnienia pól oznaczonych
> `[DO UZUPEŁNIENIA]`.

## 1. Administrator danych

Administratorem Twoich danych osobowych jest trener prowadzący usługę
„Dzik OS — Panel Podopiecznego":

- `[DO UZUPEŁNIENIA: imię i nazwisko / nazwa firmy]`
- `[DO UZUPEŁNIENIA: adres prowadzenia działalności, NIP]`
- kontakt: `[DO UZUPEŁNIENIA: e-mail kontaktowy]`

## 2. Jakie dane przetwarzamy

| Kategoria | Przykłady | Skąd pochodzą |
|---|---|---|
| Dane konta | e-mail, imię i nazwisko, hasło (wyłącznie w postaci skrótu bcrypt) | od Ciebie / od trenera przy założeniu konta |
| Profil współpracy | cele, doświadczenie, sprzęt, dostępność, preferencje żywieniowe | od Ciebie |
| **Dane zdrowotne (szczególna kategoria, art. 9 RODO)** | alergie, kontuzje i ograniczenia, masa ciała, obwody, raporty samopoczucia (sen, stres, energia, ból), zdjęcia sylwetki | wyłącznie od Ciebie, dobrowolnie |
| Treningi i dieta | plany, wyniki treningów, komentarze, realizacja diety | od trenera i od Ciebie |
| Wiadomości i pliki | treść rozmów z trenerem, załączniki, dokumenty PDF | od obu stron |
| Ewidencja płatności | pakiet, kwota, termin, status (opłacona/oczekująca) | od trenera |
| Dziennik zdarzeń (audyt) | kto i kiedy zmienił plan, zgodę, płatność (identyfikatory, bez treści zdrowotnych) | generowane przez aplikację |

**Czego NIE przetwarzamy:** danych kart płatniczych (aplikacja tylko
ewidencjonuje statusy płatności), danych z urządzeń typu wearables,
danych osób trzecich. Aplikacja nie zawiera reklam ani śledzenia.
Funkcje AI są w tej wersji **wyłączone**.

## 3. Cele i podstawy prawne

| Cel | Podstawa prawna |
|---|---|
| Prowadzenie współpracy trenerskiej (plany, raporty, wiadomości) | art. 6 ust. 1 lit. b RODO — wykonanie umowy |
| Przetwarzanie danych zdrowotnych na potrzeby prowadzenia trenerskiego | art. 9 ust. 2 lit. a RODO — **Twoja wyraźna zgoda** |
| Ewidencja płatności i rozliczenia | art. 6 ust. 1 lit. b i c RODO |
| Bezpieczeństwo, dziennik zdarzeń, zapobieganie nadużyciom | art. 6 ust. 1 lit. f RODO — uzasadniony interes |

## 4. Zgoda i jej cofnięcie

- Zgodę na dostęp trenera do Twoich danych zdrowotnych wyrażasz jawnie
  przy pierwszym logowaniu (ekran „Twoje dane, Twoja zgoda").
- Zgodę możesz **cofnąć w każdej chwili** w aplikacji (Profil → Zgody).
  Cofnięcie działa natychmiast — trener traci dostęp do Twoich danych.
- Cofnięcie zgody nie wpływa na zgodność z prawem przetwarzania sprzed
  cofnięcia. Historia zgód (nadanie, potwierdzenie, cofnięcie) jest
  zapisywana w niezmiennym dzienniku zdarzeń.

## 5. Odbiorcy danych

- **Hosting:** aplikacja działa na serwerach Fly.io w regionie
  Frankfurt (UE). Fly.io Inc. jest podmiotem przetwarzającym
  (`[DO UZUPEŁNIENIA: umowa powierzenia / DPA Fly.io]`).
- Dane **nie są sprzedawane** ani udostępniane podmiotom trzecim w
  celach marketingowych.
- Dostęp do Twoich danych ma wyłącznie Twój trener (w zakresie objętym
  zgodą) — administrator techniczny systemu **nie ma** dostępu do danych
  zdrowotnych.
- `[DO UZUPEŁNIENIA przy wdrożeniu płatności online: operator płatności]`
- **Zasoby zewnętrzne (czcionki, CDN):** aplikacja nie ładuje żadnych
  zasobów z serwerów podmiotów trzecich. Czcionki (Unbounded, Inter) są
  hostowane razem z aplikacją (self-hosting od 2026-08-18) — Twój adres IP
  **nie jest** przekazywany do Google (Google Fonts) ani do żadnej innej
  sieci CDN podczas korzystania z aplikacji.

## 6. Przekazywanie poza EOG

Serwery aplikacji znajdują się w UE (Frankfurt). Dostawca infrastruktury
(Fly.io Inc.) ma siedzibę w USA — podstawą przekazania są standardowe
klauzule umowne `[DO WERYFIKACJI PRAWNEJ: aktualny mechanizm transferu
i DPA dostawcy]`.

## 7. Jak długo przechowujemy dane

- Dane współpracy: przez czas trwania współpracy trenerskiej.
- Po zakończeniu współpracy: do `[DO UZUPEŁNIENIA: np. 12 miesięcy]`,
  chyba że wcześniej skorzystasz z prawa do usunięcia.
- Dokumenty rozliczeniowe: zgodnie z przepisami podatkowymi (5 lat).
- Dziennik zdarzeń (bez treści zdrowotnych): `[DO UZUPEŁNIENIA]`.

## 8. Twoje prawa

Masz prawo do:

- **dostępu** do danych i informacji o ich przetwarzaniu;
- **sprostowania** — swoje deklaracje możesz poprawiać w aplikacji
  (historia zmian jest zachowywana, nic nie jest nadpisywane po cichu);
- **usunięcia** — funkcja „Usuń konto i dane" w aplikacji anonimizuje
  konto i trwale usuwa pliki (zdjęcia, dokumenty);
- **przenoszenia danych** — funkcja „Eksportuj wszystkie dane" pobiera
  komplet Twoich danych w otwartym formacie JSON;
- **cofnięcia zgody** (pkt 4) oraz **sprzeciwu** wobec przetwarzania
  opartego na uzasadnionym interesie;
- **skargi do Prezesa Urzędu Ochrony Danych Osobowych** (uodo.gov.pl).

Realizacja praw: bezpośrednio w aplikacji albo kontaktowo (pkt 1).

## 9. Bezpieczeństwo

- transmisja wyłącznie szyfrowana (HTTPS);
- hasła przechowywane jako skróty bcrypt; wymuszona zmiana hasła
  startowego przy pierwszym logowaniu; limit prób logowania;
- ścisła izolacja kont — klient widzi wyłącznie swoje dane, trener
  wyłącznie dane aktywnie przypisanych klientów za ich zgodą;
- operacje o wysokim znaczeniu zapisywane w niezmiennym, kryptograficznie
  łańcuchowanym dzienniku zdarzeń (możliwość wykrycia manipulacji);
- kopie zapasowe: `[DO UZUPEŁNIENIA po konfiguracji backupów]`.

## 10. Pliki cookie i pamięć przeglądarki

Aplikacja używa wyłącznie technicznego ciasteczka sesji (httpOnly)
oraz pamięci przeglądarki na potrzeby zalogowania. Brak cookies
reklamowych, analitycznych i śledzących.

## 11. Osoby niepełnoletnie

Usługa jest przeznaczona dla osób pełnoletnich. Osoby w wieku
`[DO DECYZJI: 16–18 lat]` mogą korzystać wyłącznie za zgodą opiekuna
prawnego.

## 12. Zmiany polityki

Polityka jest wersjonowana. O istotnych zmianach poinformujemy w
aplikacji przed ich wejściem w życie. Wersje archiwalne pozostają
dostępne.

## 13. Kontakt

W sprawach danych osobowych: `[DO UZUPEŁNIENIA: e-mail]`.

---

*Dokument przygotowany 2026-08-17 na podstawie rzeczywistego działania
aplikacji Dzik OS 0.1.1 (funkcje zgód, eksportu, anonimizacji i audytu
opisane w docs/DATA_PROCESSING_MAP.md i docs/PERMISSIONS.md).*
