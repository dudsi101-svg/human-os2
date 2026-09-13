# Instrukcja dla Claude

Zintegruj ten działający moduł z moją aplikacją. Najpierw sprawdź repozytorium, technologię, bazę produktów, obecne cele żywieniowe, uprawnienia i moduł Wiedza. Jeśli kod aplikacji nie został udostępniony, poproś o repozytorium; nie deklaruj integracji wyłącznie na podstawie plików referencyjnych.

Uruchom testy, przejrzyj engine.py i przeczytaj ograniczenia. Możesz użyć modułu w Pythonie jako serwisu domenowego lub przenieść zachowanie do obecnego stosu, zachowując scenariusze testowe. Nie wdrażaj publicznego endpointu bez uwierzytelniania, limitu zasobów i sprawdzania właściciela planu. Serwer weryfikuje screening_status oraz targets_reference; nie przyjmuje ich jako niekontrolowanej deklaracji klienta.

Podłącz istniejącą bazę żywieniową i zatwierdzone cele. Stan surowy, suchy, ugotowany i odsączony musi być zgodny. Nie wpisuj fikcyjnych wartości, dat recenzji ani nazwisk. Dane testowe są syntetyczne i nie wolno używać ich do planów użytkowników.

Przepisy są 300 szkicami wariantów w 30 rodzinach. Włącz je w trybie demonstracyjnym, a produkcyjny import kieruj do kolejki redakcyjnej. Opublikuj tylko rzeczywiście zatwierdzone rekordy. Jeżeli po tym zabraknie kandydatów, pokaż brak pokrycia zamiast omijać filtr publikacji.

Zachowaj dobór całych dań i wyłącznie zatwierdzonych porcji. Nie dodawaj dowolnego oleju czy białka do każdego posiłku. W razie braku rozwiązania pokaż powód. `search_exhausted` oznacza brak rozwiązania w ograniczonym przeszukiwaniu, nie dowód niemożliwości; można zwiększyć budżet lub podłączyć bardziej kompletny solver.

Integrując ślad decyzji z Wiedzą, dopisz owner_id, plan_revision, właściwy target_type i trwałe identyfikatory. Obecny trace jest szkieletem domenowym, nie pełnym obiektem prywatnej warstwy API. Zapisz plan i trace atomowo. Zmiana dania wymaga ponownego sprawdzenia całego dnia i uprawnień; zachowaj stare rewizje.

P0 do wykonania w repozytorium: adapter żywieniowy, kontrola autoryzacji, formularz parametrów, podgląd menu, przejście do receptury i listy zakupów, wyjaśnienia, publikowanie treści oraz testy integracyjne. Nie dopisuj czatu AI jako warunku działania; ten silnik nie wymaga klucza AI.

Raport końcowy ma rozdzielać kod gotowy, dane zweryfikowane, dane robocze i brakujące moduły. Podaj wyniki testów oraz pokrycie każdej wspieranej diety. Nie nazywaj katalogu 300 rekordów bazą 300 przetestowanych dań.
