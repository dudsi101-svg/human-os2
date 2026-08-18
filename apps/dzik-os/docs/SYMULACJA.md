# Głęboka symulacja obciążeniowa

Narzędzie diagnostyczne: generuje realistyczny wolumen danych w **każdej**
sekcji aplikacji, żeby sprawdzić zachowanie systemu, gdy wszystkie moduły
pracują naraz — a nie na szkielecie danych demo.

```bash
python -m dzik_os.simulate                    # 10 podopiecznych, 12 tygodni
python -m dzik_os.simulate --clients 4 --weeks 6
python -m dzik_os.simulate --reset            # czyści bazę przed przebiegiem
```

Moduł jest **odrębny od `seed.py`**: seed to minimalny zestaw demonstracyjny,
na którym opierają się testy; symulacja to narzędzie o dużej objętości.
Wszystkie dane są syntetyczne i deterministyczne (stałe ziarno) — kolejne
przebiegi dają identyczny obraz. Powtórny przebieg na tej samej bazie pomija
istniejące konta zamiast je duplikować.

**Hasło wszystkich kont symulacji:** `SymKlient#2026!x` (wyłącznie
lokalnie/staging — nigdy na produkcji z prawdziwymi klientami).

## Co powstaje (10 podopiecznych × 12 tygodni ≈ 6000 rekordów)

Dziesięć zróżnicowanych person (staż, cel, sprzęt, dostępność, ograniczenia
zdrowotne, adherencja 55–99%, różne stany płatności), a dla każdej:
profil z proweniencją i historią wersji, cele, plan treningowy w trzech
wersjach, sesje treningowe z dziennikiem serii (RPE, ciężar, powtórzenia),
dieta w dwóch wersjach, dziennik kaloryczny, harmonogram z suplementami
(zawsze z zapisanym autorem) i adherencją, raporty tygodniowe z ocenami,
pomiary, obserwacje (w tym niepokojące), wiadomości, dokumenty, zdjęcia
progresu, płatności, komplet zgód, konsultacje i subskrypcja push.
Do tego zasoby trenera (baza wiedzy, ćwiczenia, produkty) i wspólne wyzwanie.

## Wyniki przebiegu z 2026-08-18

| Miara | Wynik |
|---|---|
| Wygenerowane rekordy | 6 028 w 3,2 s |
| Ekrany sprawdzone przez API | ~450 wywołań, **0 błędów** |
| Izolacja danych (próby IDOR) | 6/6 odrzuconych |
| Łańcuch audytu | 286 zdarzeń, `verify_chain()` OK w 4,3 ms |
| Najwolniejszy ekran | dashboard trenera — 76 ms |
| Eksport danych klienta | 102 ms (JSON) / 110 ms (XLSX, 65 KB) |

### Znaleziony problem: N+1 w widokach zbiorczych trenera

Pomiar liczby zapytań SQL przy rosnącej liczbie podopiecznych:

| Aktywni klienci | `/api/coach/dashboard` | `/api/coach/clients` |
|---|---|---|
| 2 | 24 zapytania | 145 zapytań |
| 6 | 56 zapytań | 164 zapytania |
| 10 | 88 zapytań | 184 zapytania |

Dashboard rośnie liniowo (**+8 zapytań na każdego podopiecznego**), lista
klientów ma wysoką stałą bazę (~135) plus ~5 na podopiecznego. Na SQLite
lokalnie to nadal dziesiątki milisekund, ale na PostgreSQL — gdzie każde
zapytanie kosztuje round-trip — przy 50 podopiecznych dashboard oznaczałby
ponad 400 zapytań na jedno wejście do panelu. Do naprawy agregacją
(jedno zapytanie zbiorcze zamiast pętli po klientach) zanim trener urośnie
ponad kilkunastu podopiecznych.

### Zachowania potwierdzone jako poprawne

* poprawka raportu tworzy **nową rewizję**, historia nie jest nadpisywana;
* raport już oceniony przez trenera odrzuca kolejną edycję (409) — ocena
  zamyka tydzień;
* nieudane powiadomienie push (martwy endpoint) tylko loguje ostrzeżenie
  i **nie przerywa** operacji użytkownika;
* wszystkie zapisy (raport, ocena, wersja planu, wiadomość, pomiar)
  wykonują się w 8–41 ms przy pełnej bazie.
