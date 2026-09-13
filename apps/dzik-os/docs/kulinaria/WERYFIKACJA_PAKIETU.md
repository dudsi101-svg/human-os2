# Wyniki weryfikacji

27 testów automatycznych: wynik pozytywny. Testy bilansu używają danych syntetycznych, nie stanowią sprawdzenia odżywczego biblioteki.

Biblioteka: 300 kart wariantów, 30 rodzin dań, 73 produkty. Opublikowane receptury: 0. Zweryfikowane wartości odżywcze produktów: 0.

Poniżej liczba kart / rodzin po filtrach, przed oceną bilansu odżywczego. Ten sam przepis może obsługiwać kilka typów posiłków. Limit powtórzeń: 2 użycia rodziny na blok 7 dni.

| Konfiguracja | Śniadanie | Obiad | Kolacja | Przekąska | Wynik 28 dni |
|---|---|---|---|---|---|
| Wegańska, 3 posiłki | 60 / 6 | 110 / 11 | 120 / 12 | — | draft_preview |
| Mieszana, 3 posiłki | 120 / 12 | 180 / 18 | 230 / 23 | — | draft_preview |
| Wegetariańska | 120 / 12 | 120 / 12 | 170 / 17 | — | draft_preview |
| Pescetariańska | 120 / 12 | 160 / 16 | 210 / 21 | — | draft_preview |
| Paleo | 37 / 4 | 47 / 5 | 74 / 8 | — | search_exhausted |
| Wegańska do 15 min | 40 / 4 | 20 / 2 | 30 / 3 | — | search_exhausted |
| Wegańska, 4 posiłki | 60 / 6 | 110 / 11 | 120 / 12 | 20 / 2 | search_exhausted |
| Wegańska, 6 posiłków | 60 / 6 | 110 / 11 | 120 / 12 | 20 / 2 | search_exhausted |
| Wegańska, alergia na soję | 0 / 0 | 0 / 0 | 0 / 0 | — | insufficient_catalog |

`draft_preview`: utworzono podgląd, bez walidacji żywieniowej. `search_exhausted`: ograniczony algorytm nie znalazł całego planu; nie zwraca częściowego wyniku. `insufficient_catalog`: brak dań spełniających warunki dla co najmniej jednego typu posiłku. Przy alergii niezweryfikowany skład produktu jest powodem wykluczenia.

Wniosek: liczba 300 nie gwarantuje obsługi wszystkich konfiguracji. Rozbudowę należy kierować na brakujące rodziny, zwłaszcza przekąski i profile restrykcyjne, a następnie powtarzać ten audyt. Nie wolno obchodzić wykluczeń zdrowotnych ani publikować szkiców dla poprawy wyniku.