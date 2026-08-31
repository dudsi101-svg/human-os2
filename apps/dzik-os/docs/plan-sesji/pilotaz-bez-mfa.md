# Plan sesji: pilotaż na loginie i haśle — MFA opcjonalne (0.54.1)

**Gałąź:** `agent/pilotaz-bez-mfa` (od `main` = 683c66b)
**Rola:** aktywny piszący
**Decyzja właściciela (2026-08-29, na żywo):** logowanie jest zbyt
skomplikowane i czasochłonne na pilotaż — „na razie wystarczy login
i hasło dla trenera i opiekuna". Wymuszanie MFA schodzi na czas
pilotażu; MFA pozostaje dostępne opcjonalnie, a przywrócenie przymusu
to jedna zmienna środowiskowa.

## Zamiar

1. **fly.toml:** `DZIK_MFA_REQUIRED_ROLES = ""` z komentarzem
   (decyzja właściciela + jak przywrócić: `"COACH,ADMIN"`).
   Mechanizm w kodzie już jest konfigurowalny — zmiana czysto
   konfiguracyjna. Wymuszona zmiana hasła startowego ZOSTAJE
   (hasło z artefaktu jest jednorazowe; po zmianie logowanie to
   już tylko login+hasło).
2. **`resetuj_haslo`:** reset operatorski czyści też TOTP i kody
   zapasowe (konto wraca do logowania hasłem) — bez tego konto
   z już skonfigurowanym authenticatorem nie da się sprowadzić do
   nowego trybu ani odzyskać po utracie telefonu. Fakt wyczyszczenia
   w zdarzeniu audytowym.
3. **Uczciwość dokumentów:** `/prywatnosc` (Privacy.tsx) przestaje
   twierdzić, że MFA trenera jest obowiązkowe — „dostępna weryfikacja
   dwuetapowa (na czas pilotażu nieobowiązkowa)"; RISK_REGISTER R-07
   z datowaną decyzją właściciela; RELEASE_STATUS (konta + jak
   przywrócić przymus).
4. Testy: pusta lista ról → brak wymuszenia dla COACH i działa
   `mfa/disable`; reset czyści TOTP (login po resecie bez wyzwania).
   Domyślne środowisko (COACH,ADMIN) bez zmian — istniejące testy
   egzekwowania dalej obowiązują.

## Świadomie nie robię

- nie usuwam mechanizmu MFA ani jego wymuszania z kodu — wraca jedną
  zmienną, gdy pilotaż okrzepnie (rekomendacja: przy >1 prawdziwym
  kliencie).

## Rezerwacje

- **Wersja: 0.54.1.** **Migracja: brak.**

## Weryfikacja (do wypełnienia)

- bramki pełne; test resetu z TOTP na żywo w izolowanym środowisku.
