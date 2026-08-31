# Plan sesji: konto podopiecznego z zaplecza (0.54.2, potrzeba właściciela na żywo)

**Gałąź:** `agent/dodaj-klienta` (od `main` = 8e31c15)
**Rola:** aktywny piszący
**Cel:** właściciel chce DZIŚ konto podopiecznego przypisane do
trenera, a trener jest niedostępny (normalna ścieżka to zaproszenie
z panelu trenera). Powstaje operatorskie narzędzie tworzące konto
CLIENT z aktywną relacją do wskazanego trenera — lustrzane do
`dodaj_trenera`.

## Zamiar

1. **`dzik_os/dodaj_klienta.py`**: konto CLIENT (ACTIVE) + aktywna
   `CoachClientRelationship` do trenera wskazanego e-mailem. Zasady jak
   w dodaj_trenera: hasło wyłącznie z env `DZIK_KLIENT_PASSWORD`
   (nigdy argv), `must_change_password=True` (hasło startowe
   jednorazowe — właściciel ustawi własne przy pierwszym logowaniu),
   odmowa dla zajętego e-maila i nieistniejącego/nie-trenerskiego
   konta trenera, limit `DZIK_MAX_CLIENTS` honorowany, zdarzenia
   audytowe (rejestracja + relacja).
2. **`.github/workflows/fly-dodaj-klienta.yml`** — wzorzec
   fly-dodaj-trenera: inputy email + coach_email (walidowane, przez
   env), hasło z sekretu repo albo wygenerowane (maskowane, artefakt
   `haslo-klienta` 1 dzień), chwilowy sekret Fly kasowany po użyciu,
   akcje po SHA.
3. Testy: sukces (konto+relacja, login działa, must_change),
   odmowy (zajęty e-mail / zły trener / limit), audyt bez hasła.

## Świadomie nie robię

- nie przepuszczam hasła z czatu przez workflow — właściciel ustawi
  wybrane hasło samodzielnie na ekranie wymuszonej zmiany;
- normalną ścieżką pozostaje zaproszenie z panelu trenera (klient sam
  ustawia hasło) — narzędzie jest dla przypadków operatorskich.

## Rezerwacje

- **Wersja: 0.54.2.** **Migracja: brak.**

## Weryfikacja (do wypełnienia)

- bramki pełne; moduł na żywo w izolowanym środowisku; po scaleniu
  uruchomienie workflow na produkcji dla konta właściciela.
