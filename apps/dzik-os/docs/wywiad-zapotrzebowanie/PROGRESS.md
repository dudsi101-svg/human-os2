# Postęp — wywiad „Zapotrzebowanie kaloryczne” (0.62.0)

| Etap | Stan | Dowód |
|---|---|---|
| 0 rozpoznanie | ✅ | `00_rozpoznanie.md` |
| 1 silnik | ✅ | `dzik_os/wywiad/zapotrzebowanie.py`, 9 testów |
| 2 definicja wywiadu (typ + NUMBER) | ✅ | `definicje.py`, 47 testów modułu wywiadu zielone |
| 3 model + migracja 33 | ✅ | `CalorieEstimate`, `db.py` |
| 4 API + serwis | ✅ | `routers/zapotrzebowanie.py`, `wywiad/zapotrzebowanie_serwis.py`, 7 testów |
| 5 UI | ✅ | `pages/wywiad/Zapotrzebowanie.tsx`, E2E `zapotrzebowanie.spec.ts` |
| 6 zamknięcie | ✅ | CHANGELOG 0.62.0, WYWIAD.md §8, RELEASE_STATUS, plan-sesji |

## P2 / do rozważenia (bez osobnej weryfikacji, zasady v2 §3)

* Przeliczenie po nowym pomiarze masy bez nowej wersji wywiadu — dziś
  wynik zmienia się tylko przez wywiad (świadomie; patrz WYWIAD.md §8).
* Klient bez trenera: zaproszenie do wywiadu w Diecie jest poprawne (wywiad
  działa bez trenera); komunikat ukrycia ma osobne brzmienie bez trenera.
* Historia wersji szacunku u trenera to jedna linia tekstu — tabela
  z datami, gdy pojawi się >3 wersji.
* Dokument właściciela `wywiad_zapotrzebowanie_kaloryczne.md` nadal
  niedostarczony — różnice do wyrównania po otrzymaniu (PAL-e, progi
  tempa, treść komunikatu przy fladze zdrowotnej).

## Przegląd kodu (3 recenzentów wsadowo, zasady v2 §3)

**P1 naprawione:** dowiązanie `frontend/node_modules` dodane przez pomyłkę
z worktree (usunięte z indeksu, `.gitignore` bez ukośnika); eksport RODO
przy ukrytym wyniku — udokumentowany jako świadoma decyzja + test.
**P2 naprawione:** `typy_aktywne()` także w `GET /wywiady/zgloszenia/{id}`
i `GET /coach/wywiady/do-przegladu`; PUT/POST zapotrzebowania przez
`_dostep_pelny` (404 + audyt, spójnie z resztą wywiadu); neutralne
`summary` audytu odsłonięcia; NUMBER przyjmuje wyłącznie zwykły zapis
dziesiętny (bez `1e2`, `1_0`, cyfr spoza ASCII) i zapisuje znormalizowany.
**P2 odnotowane (bez zmiany):** `hidden_for_client`/`safety_flag` widoczne
dla trenera także po cofnięciu zgody zdrowotnej przez klienta — ten sam
wzorzec co istniejący `safety_flag` z 0.59.0; do rozstrzygnięcia razem.

**Z przeglądu testów/UX naprawione:** komunikat ukrycia dla klienta bez
trenera; nota o wygasłym ustaleniu przy nowej wersji (+ `override_kcal`
w historii, test); brzmienie dla trenera bez przypisywania diagnozy; testy:
404 przed przesłaniem, odblokowanie no-op, cofnięcie bez nadpisania
no-op, eksport z nadpisaniem, usuwanie konta, `features.calorie_interview`
= true; „Wróć do wzoru” bez otwierania formularza; przycisk poza
`role="status"`; podpowiedź zakresu 800–8000; słowniczek PPM/PAL/CPM;
ostrzeżenie o PPM po ludzku; „Zaproponuj kcal” mówi, że nie przypisuje
(+ asercja E2E). **P2 odnotowane:** asercja „żaden string bez cyfr” w teście
flagi; test `oblicz` z PAL ograniczonym do 1,9 i krokami; test `BrakDanych →
None` na poziomie serwisu; asercje audytu; selektory E2E po `id`
radiogroup; `_rows` nie dekoduje `*_json` (spójne z dietą).
