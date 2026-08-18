# Proces obsługi incydentów ochrony danych — Dzik OS (szkic)

> **STATUS: SZKIC DO PRZYJĘCIA PRZEZ ADMINISTRATORA DANYCH.** Procedura
> techniczno-organizacyjna dla naruszeń ochrony danych osobowych
> (art. 33–34 RODO). Nie jest poradą prawną.

## 1. Co jest incydentem

Naruszenie bezpieczeństwa prowadzące do przypadkowego lub niezgodnego z
prawem zniszczenia, utracenia, zmodyfikowania, nieuprawnionego
ujawnienia lub dostępu do danych osobowych, m.in.:

* dostęp do danych klienta przez osobę bez aktywnej zgody/relacji
  (w tym udany atak IDOR),
* wyciek bazy danych lub plików (zdjęcia, dokumenty),
* przejęcie konta (trenera, klienta lub admina),
* utrata danych bez możliwości odtworzenia (awaria + brak kopii),
* naruszenie u podmiotu przetwarzającego (np. hosting).

## 2. Wykrywanie — narzędzia wbudowane w aplikację

* **Łańcuch audytu** (hash-chained, append-only): panel admina →
  „Weryfikacja łańcucha audytu" (`verify_chain`) — nieprzerwany łańcuch
  wyklucza niezauważoną manipulację historią zdarzeń.
* **Zdarzenia `ACCESS_DENIED`** — każda odmowa zasobowa (próba IDOR)
  jest logowana z identyfikatorem aktora i endpointem.
* **`PUSH_ENDPOINT_REBOUND`** — zmiana właściciela endpointu push
  (wykrywalność nadużycia współdzielonej przeglądarki).
* **Ekran aktywnych sesji** — użytkownik sam widzi urządzenia i może
  unieważnić sesje; zmiana hasła unieważnia wszystkie.
* Zdarzenia zgód (`CONSENT_*`) — pełna historia decyzji podmiotu.

## 3. Postępowanie (kroki)

1. **Zabezpieczenie** (niezwłocznie): unieważnić sesje dotkniętych kont
   (zmiana hasła / revoke-others), w razie potrzeby zawiesić konto
   (`status=SUSPENDED`), w skrajności zatrzymać maszynę (Fly.io).
2. **Utrwalenie dowodów:** zrzut bazy audytu (plik `audit.db` jest
   append-only), eksport zdarzeń z okresu incydentu; nie modyfikować.
3. **Ocena skali:** kogo dotyczy, jakie kategorie danych (zdrowotne =
   wysokie ryzyko), czy dane opuściły system.
4. **Ocena ryzyka i zgłoszenie:** administrator danych ocenia ryzyko
   naruszenia praw i wolności osób. Jeżeli ryzyko jest
   prawdopodobne — **zgłoszenie do UODO w 72 h** od stwierdzenia
   naruszenia (art. 33). DECYZJA ADMINISTRATORA DANYCH: kto dokonuje
   oceny i zgłasza (dane kontaktowe w RODO_REJESTR_CZYNNOSCI.md §1).
5. **Zawiadomienie osób** (art. 34): przy wysokim ryzyku (np. wyciek
   danych zdrowotnych/zdjęć) — bez zbędnej zwłoki, prostym językiem:
   co się stało, jakie dane, co zrobiono, co osoba może zrobić.
6. **Usunięcie przyczyny:** poprawka, test regresyjny odtwarzający
   scenariusz, wpis w CHANGELOG.
7. **Rejestr naruszeń:** każdy incydent (także niezgłaszany) trafia do
   wewnętrznego rejestru naruszeń administratora — data, opis, ocena
   ryzyka, działania. DECYZJA ADMINISTRATORA DANYCH: miejsce
   prowadzenia rejestru (dokument poza repozytorium kodu).

## 4. Incydent u podmiotu przetwarzającego

Fly.io (lub przyszły dostawca poczty/AI) ma obowiązek zgłosić naruszenie
administratorowi; administrator prowadzi wtedy kroki 3–7. DECYZJA
ADMINISTRATORA DANYCH: zweryfikować kanał powiadomień o naruszeniach w
DPA dostawców.

## 5. Kontakt zgłoszeniowy

Użytkownicy i osoby trzecie zgłaszają podejrzenia naruszeń na adres
administratora danych (polityka prywatności §13). Zgłoszenia
bezpieczeństwa kodu: prywatnie, zgodnie z SECURITY.md repozytorium
(nigdy publiczne issue).
