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

### Znaleziony problem: N+1 w widokach zbiorczych — NAPRAWIONY

Pierwszy przebieg pokazał, że koszt zapytań rósł liniowo z liczbą
podopiecznych (a przy treningach — z długością historii). Naprawą jest
warstwa agregacji `dzik_os/aggregates.py`: każda metryka liczona jest
jednym zapytaniem grupującym zamiast pętli po rekordach.

| Ekran | Zapytania SQL przed | po | Zmiana |
|---|---|---|---|
| Lista klientów (10 podopiecznych) | 184 | **13** | −93% |
| Dashboard trenera (10 podopiecznych) | 88 | **15** | −83% |
| Lista treningów (12 tyg. historii) | 40 | **7** | −82% |
| Lista wątków wiadomości | 54 | **9** | −83% |

Kluczowe: liczba zapytań jest teraz **stała** — nie rośnie z liczbą
podopiecznych ani z historią. Pomiar skalowania po naprawie:

| Aktywni klienci | dashboard | lista klientów |
|---|---|---|
| 2 | 14 zapytań | 14 zapytań |
| 6 | 14 zapytań | 13 zapytań |
| 10 | 14 zapytań | 13 zapytań |

Reguły zgód pozostały w Core: rejestr `hos_engine.ConsentRegistry` jest
hydratowany raz dla wszystkich podopiecznych (`ConsentService.hydrate_many`)
i to on nadal odpowiada „czy wolno" — warstwa aplikacji nie reimplementuje
reguł. Testy `test_aggregates.py` pilnują jednego i drugiego: zgodności
wyników z wyliczeniem pojedynczym (w tym natychmiastowego skutku cofnięcia
zgody) oraz stałego budżetu zapytań, żeby N+1 nie wróciło niezauważone.

### Zachowania potwierdzone jako poprawne

* poprawka raportu tworzy **nową rewizję**, historia nie jest nadpisywana;
* raport już oceniony przez trenera odrzuca kolejną edycję (409) — ocena
  zamyka tydzień;
* nieudane powiadomienie push (martwy endpoint) tylko loguje ostrzeżenie
  i **nie przerywa** operacji użytkownika;
* wszystkie zapisy (raport, ocena, wersja planu, wiadomość, pomiar)
  wykonują się w 8–41 ms przy pełnej bazie.
