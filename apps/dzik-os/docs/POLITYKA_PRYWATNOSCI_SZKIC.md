# Polityka prywatności Dzik OS — SZKIC v0.2 (2026-08-18)

> **STATUS: SZKIC DO KONSULTACJI PRAWNEJ.** Ten dokument jest punktem
> wyjścia przygotowanym technicznie na podstawie faktycznego działania
> aplikacji (wersja 0.11.0). **Nie jest poradą prawną.** Przed użyciem
> wobec prawdziwych klientów wymaga weryfikacji przez prawnika (dane
> zdrowotne = szczególna kategoria danych, art. 9 RODO) oraz uzupełnienia
> pól oznaczonych „DECYZJA ADMINISTRATORA DANYCH".
>
> Wersje polityki są numerowane; wersje archiwalne pozostają w historii
> repozytorium. Poprzednia wersja: v0.1 (2026-08-17).
>
> **Wersja publiczna (od 0.53.5):** skrócona, opisowa wersja tej treści
> — z wypełnionym administratorem (LUBELSKI DZIK sp. z o.o.) — żyje w
> `frontend/src/pages/Privacy.tsx` i jest dostępna pod `/prywatnosc`.
> Zmiany merytoryczne wprowadzaj w obu miejscach; ten szkic pozostaje
> pełniejszym dokumentem roboczym do konsultacji prawnej.

## 1. Administrator danych

Administratorem Twoich danych osobowych jest trener prowadzący usługę
„Dzik OS — Panel Podopiecznego":

- DECYZJA ADMINISTRATORA DANYCH: `[imię i nazwisko / nazwa firmy]`
- DECYZJA ADMINISTRATORA DANYCH: `[adres prowadzenia działalności, NIP]`
- kontakt: DECYZJA ADMINISTRATORA DANYCH: `[e-mail kontaktowy]`

## 2. Jakie dane przetwarzamy

| Kategoria | Przykłady | Skąd pochodzą |
|---|---|---|
| Dane konta | e-mail, imię i nazwisko, hasło (wyłącznie w postaci skrótu bcrypt) | od Ciebie / od trenera przy założeniu konta |
| Dane współpracy | profil współpracy, dokumenty, ewidencja płatności | od Ciebie i od trenera |
| Dane treningowe | plany, wyniki treningów, harmonogram, cele | od trenera i od Ciebie |
| **Dane zdrowotne (art. 9 RODO)** | masa ciała, obwody, raporty samopoczucia (sen, stres, energia, ból), urazy i ograniczenia, obserwacje | wyłącznie od Ciebie, dobrowolnie, za odrębną zgodą |
| **Żywienie i alergie (art. 9 RODO)** | alergie i nietolerancje, preferencje, plany żywieniowe, dziennik kaloryczny | jw., za odrębną zgodą |
| **Zdjęcia progresu (wizerunek)** | zdjęcia sylwetki (metadane EXIF, w tym GPS, usuwane przy zapisie) | jw., za odrębną zgodą |
| Wiadomości i pliki | treść rozmów z trenerem, załączniki | od obu stron |
| Ewidencja płatności | pakiet, kwota, termin, status (opłacona/oczekująca) | od trenera |
| Subskrypcje push | techniczny adres subskrypcji Twojej przeglądarki | od Ciebie, po włączeniu powiadomień |
| Zdjęcia do przepisania i przepisany tekst | zdjęcie etykiety produktu, kartki z planem lub dietą, skanu dokumentu — oraz tekst z niego odczytany (skan wyniku badań może zawierać dane zdrowotne) | od Ciebie i od trenera, tylko wtedy gdy ktoś świadomie zrobi zdjęcie |
| Dziennik zdarzeń (audyt) | kto i kiedy zmienił plan, zgodę, płatność (identyfikatory, bez treści zdrowotnych) | generowane przez aplikację |

**Czego NIE przetwarzamy:** danych kart płatniczych (aplikacja tylko
ewidencjonuje statusy płatności — nie ma płatności online), danych z
urządzeń typu wearables, danych osób trzecich, danych o lokalizacji
(GPS ze zdjęć jest usuwany). Aplikacja nie zawiera reklam, analityki ani
śledzenia. Nie zapisujemy adresów IP przy zgodach ani innych zbędnych
danych technicznych.

## 3. Cele, podstawy prawne i odrębne zgody

Zgody są podzielone na **odrębne kategorie** — każdą widzisz z pełnym
opisem (cel, zakres, odbiorcy, okres, dobrowolność, sposób wycofania,
wersja dokumentu) i o każdej decydujesz osobno. Zgody wymagane
(wynikające z umowy) i opcjonalne nigdy nie są łączone.

| Cel | Podstawa prawna | Charakter |
|---|---|---|
| Prowadzenie konta, bezpieczeństwo, dziennik zdarzeń | art. 6 ust. 1 lit. b i f RODO | wymagane (umowa) |
| Współpraca trenerska: profil, dokumenty, plany, wyniki, komunikacja | art. 6 ust. 1 lit. b RODO | wymagane (umowa) |
| Dane zdrowotne dla trenera | art. 9 ust. 2 lit. a RODO — **odrębna wyraźna zgoda** | opcjonalne |
| Żywienie i alergie dla trenera | art. 9 ust. 2 lit. a RODO — **odrębna wyraźna zgoda** | opcjonalne |
| Zdjęcia progresu dla trenera | art. 9 ust. 2 lit. a RODO — **odrębna wyraźna zgoda** | opcjonalne |
| Powiadomienia push / przypomnienia | art. 6 ust. 1 lit. a RODO — zgoda | opcjonalne |
| Funkcje AI (podsumowania raportów dla trenera, wersja robocza podsumowania rozmowy startowej, dokładniejsze przepisywanie tekstu ze zdjęcia) | art. 9 ust. 2 lit. a RODO — zgoda | opcjonalne; obecnie żaden dostawca AI nie jest skonfigurowany |
| Przepisywanie tekstu ze zdjęcia (tryb lokalny, na naszym serwerze) | art. 6 ust. 1 lit. b RODO; art. 9 ust. 2 lit. a, gdy zdjęcie dotyczy danych zdrowotnych | wymagane w zakresie umowy — **bez zgody `funkcje_ai` nic nie opuszcza aplikacji**; wynik jest zawsze propozycją do zatwierdzenia przez człowieka |
| Marketing trenera | art. 6 ust. 1 lit. a RODO — zgoda | opcjonalne; nigdy nie jest rejestrowana przy zakładaniu konta |
| Ewidencja płatności i rozliczenia | art. 6 ust. 1 lit. b i c RODO | wymagane (umowa + przepisy podatkowe) |

## 4. Zgoda i jej cofnięcie

- To **Ty** potwierdzasz zgody dotyczące swoich danych — przy pierwszym
  logowaniu widzisz każdą kategorię osobno i decydujesz o każdej z
  osobna. Deklaracja zebrana przez trenera przy zakładaniu konta nie
  zastępuje Twojej decyzji; przy podpinaniu istniejącego konta trener
  nie ma dostępu do danych, dopóki sam nie udzielisz zgód.
- Każdą zgodę możesz **cofnąć w każdej chwili** w aplikacji (Profil →
  Prywatność i zgody) — równie łatwo, jak ją wyrazić. Cofnięcie działa
  natychmiast i dotyczy tylko tej kategorii (np. cofnięcie zgody na
  zdjęcia nie wyłącza planu treningowego). Cofnięcie zgody na
  przypomnienia usuwa też wszystkie subskrypcje push.
- Cofnięcie zgody nie wpływa na zgodność z prawem przetwarzania sprzed
  cofnięcia. Historia zgód (udzielenie, potwierdzenie, cofnięcie,
  odmowa, wersja dokumentu, podstawa prawna) jest zapisywana w
  niezmiennym dzienniku zdarzeń.

## 5. Odbiorcy danych i podmioty przetwarzające

Korzystamy z zewnętrznych dostawców w minimalnym, opisanym niżej
zakresie:

- **Hosting:** aplikacja, baza danych i pliki działają na serwerach
  Fly.io w regionie Frankfurt (UE). Fly.io, Inc. jest podmiotem
  przetwarzającym. DECYZJA ADMINISTRATORA DANYCH: `[umowa powierzenia /
  DPA Fly.io]`.
- **Powiadomienia push:** jeżeli je włączysz, doręcza je dostawca push
  Twojej przeglądarki (np. Mozilla, Google, Apple). Treść powiadomień
  jest szyfrowana do Twojego urządzenia i **nigdy nie zawiera danych
  zdrowotnych** — wyłącznie neutralne wezwanie do wejścia do aplikacji.
- **E-mail:** obecnie żaden dostawca poczty nie jest skonfigurowany —
  aplikacja nie wysyła e-maili. Jeżeli administrator uruchomi
  powiadomienia e-mail, wskaże tu dostawcę i zakres danych.
- **AI:** obecnie żaden dostawca AI nie jest skonfigurowany — dane nie
  są nigdzie wysyłane. Funkcje AI (propozycja streszczenia raportu dla
  trenera, wersja robocza podsumowania rozmowy startowej oraz
  dokładniejsze przepisywanie tekstu ze zdjęcia) działają wyłącznie za
  Twoją odrębną zgodą; jeżeli administrator skonfiguruje dostawcę,
  wskaże go w tej polityce **jako podmiot przetwarzający** przed
  uruchomieniem (nazwa, region, mechanizm transferu, umowa powierzenia).
  W trybie rozszerzonym przepisywania tekstu do dostawcy trafia
  **wyłącznie samo zdjęcie i rodzaj zadania** — bez identyfikatorów,
  adresu e-mail, imienia i nazwiska.
- **Przepisywanie tekstu ze zdjęcia bez zgody na funkcje AI:** działa
  silnik uruchomiony na naszym serwerze — zdjęcie ani odczytany tekst
  **nie opuszczają aplikacji**. Wynik jest zawsze propozycją: pokazujemy
  go obok zdjęcia, poprawiasz go Ty (albo trener) i dopiero
  zatwierdzenie cokolwiek zapisuje.
- **Płatności:** aplikacja prowadzi wyłącznie ewidencję statusów — nie
  ma płatności online i żaden operator płatności nie otrzymuje danych.
- **Czcionki i zasoby:** wszystkie zasoby (w tym czcionki Unbounded i
  Inter, self-hosting @fontsource) są serwowane z własnej domeny — Twój
  adres IP **nie jest** przekazywany do Google Fonts ani żadnej sieci
  CDN podczas korzystania z aplikacji.
- Dane **nie są sprzedawane** ani udostępniane podmiotom trzecim w
  celach marketingowych. Poza wymienionymi podmiotami przetwarzającymi
  dane nie są przekazywane dalej.
- Dostęp do Twoich danych ma wyłącznie Twój trener — w zakresie
  kategorii, na które wyraziłeś(-aś) zgodę; administrator techniczny
  systemu **nie ma** dostępu do danych zdrowotnych.

## 6. Przekazywanie poza EOG

Serwery aplikacji znajdują się w UE (Frankfurt). Dostawca infrastruktury
(Fly.io, Inc.) ma siedzibę w USA — DECYZJA ADMINISTRATORA DANYCH:
`[zweryfikować aktualny mechanizm transferu (SCC/DPF) i DPA dostawcy]`.
Dostawcy push (zależni od Twojej przeglądarki) mogą przetwarzać
techniczny adres subskrypcji poza EOG; treść jest zaszyfrowana.

## 7. Jak długo przechowujemy dane

- Dane współpracy: przez czas trwania współpracy trenerskiej.
- Po zakończeniu współpracy: DECYZJA ADMINISTRATORA DANYCH:
  `[np. 12 miesięcy]`, chyba że wcześniej skorzystasz z prawa do
  usunięcia.
- Dokumenty rozliczeniowe (kwoty, terminy, statusy): zgodnie z
  przepisami podatkowymi (5 lat od końca roku).
- Dziennik zdarzeń (bez treści zdrowotnych): trwale — służy Twojej
  własnej rozliczalności (możesz sprawdzić, kto i kiedy zmieniał Twoje
  dane).
- Kopie zapasowe: dane usunięte z aplikacji mogą pozostawać w kopiach
  zapasowych do wygaśnięcia ich rotacji — DECYZJA ADMINISTRATORA DANYCH:
  `[skonfigurować backupy i podać maksymalny okres, np. 30 dni]`.

## 8. Twoje prawa i jak z nich skorzystać

Masz prawo do:

- **dostępu** do danych i informacji o ich przetwarzaniu — wszystkie
  swoje dane widzisz w aplikacji;
- **eksportu / przenoszenia danych** — Profil → „Eksportuj wszystkie
  dane": komplet danych w otwartym formacie JSON (maszynowym) albo w
  arkuszu Excel (czytelnym); eksport obejmuje też historię zgód,
  pokwitowania audytu i ewidencję płatności;
- **sprostowania** — swoje deklaracje poprawiasz w aplikacji; historia
  zmian jest zachowywana, nic nie jest nadpisywane po cichu;
- **usunięcia** — Profil → „Usuń konto i dane" (hasło + fraza
  potwierdzająca): konto jest anonimizowane, zdjęcia i pliki **fizycznie
  usuwane z dysku**, pomiary/obserwacje/dziennik żywieniowy usuwane,
  treści wolnotekstowe (cele, wiadomości, komentarze, notatki)
  anonimizowane, subskrypcje push usuwane, a wszystkie sesje
  unieważniane. Pozostają: dane rozliczeniowe wymagane przepisami
  (kwoty/terminy/statusy, bez notatek) oraz dziennik zdarzeń
  (identyfikatory operacji, bez danych zdrowotnych);
- **cofnięcia każdej zgody** (pkt 4) oraz **sprzeciwu** wobec
  przetwarzania opartego na uzasadnionym interesie;
- **skargi do Prezesa Urzędu Ochrony Danych Osobowych** (uodo.gov.pl).

Realizacja praw: bezpośrednio w aplikacji (przyciski powyżej działają
natychmiast, bez rozpatrywania) albo wnioskiem na adres kontaktowy
administratora (pkt 1) — odpowiedź w terminie do miesiąca (art. 12
RODO).

## 9. Bezpieczeństwo

- transmisja wyłącznie szyfrowana (HTTPS); rygorystyczne nagłówki
  bezpieczeństwa i CSP;
- hasła przechowywane jako skróty bcrypt; wymuszona zmiana hasła
  startowego; limity prób; serwerowe unieważnianie sesji i ekran
  aktywnych sesji;
- ścisła izolacja kont — klient widzi wyłącznie swoje dane, trener
  wyłącznie dane aktywnie przypisanych klientów w zakresie udzielonych
  zgód; każda odmowa dostępu jest logowana;
- nowe zdjęcia są pozbawiane metadanych EXIF (w tym GPS) już przy
  zapisie; odpowiedzi z plikami nie trafiają do cache;
- operacje o wysokim znaczeniu zapisywane w niezmiennym, kryptograficznie
  łańcuchowanym dzienniku zdarzeń (możliwość wykrycia manipulacji);
- kopie zapasowe: DECYZJA ADMINISTRATORA DANYCH (pkt 7);
- szyfrowanie danych w spoczynku na poziomie aplikacji nie jest
  zaimplementowane — DECYZJA ADMINISTRATORA DANYCH: ocena środków po
  stronie platformy hostingowej.

## 10. Pliki cookie i pamięć przeglądarki

Aplikacja używa wyłącznie technicznego ciasteczka sesji (httpOnly)
oraz pamięci przeglądarki na potrzeby zalogowania i trybu offline
(PWA). Brak cookies reklamowych, analitycznych i śledzących.

## 11. Osoby niepełnoletnie

Usługa jest przeznaczona dla osób pełnoletnich. DECYZJA ADMINISTRATORA
DANYCH: `[czy osoby 16–18 lat mogą korzystać za zgodą opiekuna]`.

## 12. Zmiany polityki

Polityka jest wersjonowana (ta wersja: v0.2). O istotnych zmianach —
w tym o każdej zmianie wersji dokumentu zgód — informujemy w aplikacji
przed ich wejściem w życie; zgody wyrażone na wcześniejsze wersje
zachowują w historii numer wersji, na którą zostały udzielone. Wersje
archiwalne pozostają dostępne.

## 13. Kontakt

W sprawach danych osobowych: DECYZJA ADMINISTRATORA DANYCH: `[e-mail]`.

---

*Dokument przygotowany 2026-08-18 na podstawie rzeczywistego działania
aplikacji Dzik OS 0.11.0 (kategorie zgód, eksport, anonimizacja i audyt
opisane w docs/ZGODY_MODEL.md, docs/RODO_REJESTR_CZYNNOSCI.md i
docs/DATA_PROCESSING_MAP.md).*
