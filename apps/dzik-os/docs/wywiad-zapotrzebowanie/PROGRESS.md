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
* Karta w zakładce Dieta klienta pokazuje zaproszenie do wywiadu także
  wtedy, gdy klient nie ma trenera — poprawne (wywiad działa bez trenera),
  ale komunikat mógłby o tym wspominać.
* Historia wersji szacunku u trenera to jedna linia tekstu — tabela
  z datami, gdy pojawi się >3 wersji.
* Dokument właściciela `wywiad_zapotrzebowanie_kaloryczne.md` nadal
  niedostarczony — różnice do wyrównania po otrzymaniu (PAL-e, progi
  tempa, treść komunikatu przy fladze zdrowotnej).
