"""Kreator diety oparty na spójnych daniach (0.57.0, P0).

Pakiet właściciela „DIETA_KULINARNA” 1.0 (13.09): zamiast doboru
produktów z grup makro — wybór zatwierdzonych receptur, dopasowanie
porcji w dozwolonych granicach, walidacja dnia i tygodnia, ślad decyzji
zgodny z kontraktem Wiedzy. Deterministycznie, bez modelu językowego.

Moduły:
* `dane`      — profile (osie), receptury startowe, mapowanie składników
                na wbudowaną bazę produktów, reguły strukturalne, źródła;
* `receptury` — składniki z wartościami z bazy, warianty porcji,
                obliczanie wartości, gramatyka rodzin, kontrola publikacji;
* `silnik`    — kolejność z pliku 03: walidacja i skierowanie zdrowotne,
                przecięcie profili, konflikty celów, filtry twarde,
                warianty, wartości, solver dnia, ranking, tydzień, raport;
* `zamiana`   — podgląd i zatwierdzenie zamiany dania.
"""
