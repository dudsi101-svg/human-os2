# Co robić, gdy coś zniknęło

Dokument operacyjny: **pięć warstw odzyskiwania**, od najszybszej do
najcięższej, plus uczciwa lista tego, czego odzyskać się NIE da.

Zasada, na której to stoi: **aplikacja nie kasuje danych**. Ćwiczenia się
archiwizuje, plany i diety mają niemutowalną historię wersji, import ma
punkt przywracania. Jedyne miejsca z realnym usuwaniem to świadome decyzje
(usunięcie konta na żądanie klienta — RODO) i one są opisane niżej.

---

## Warstwa 1 — Cofnij import (sekundy)

**Kiedy:** wgrałeś zły plik z bazą ćwiczeń albo szablonów.

Panel importu → sekcja **„Ostatnie importy"** → **Cofnij**. Dostępne także
zaraz po imporcie, w raporcie.

* pozycje **zmienione** wracają do wartości sprzed importu, pole po polu;
* pozycje **utworzone** przez import zostają **zarchiwizowane**, nie
  usunięte — widać je po włączeniu „Pokaż zarchiwizowane";
* szablon wraca przez **nową wersję** z dawną treścią, więc historia
  (łącznie z samym importem) zostaje w całości.

**Ograniczenia:** cofnięcie działa **raz** i tylko dla **20 ostatnich**
importów. Starsze nie — przywracałyby stan sprzed późniejszych, świadomych
zmian, o których migawka nic nie wie. Cofnięcie zostawia ślad w audycie
(`IMPORT_UNDONE`).

To jedyna warstwa, której trener używa sam, bez niczyjej pomocy.

---

## Warstwa 2 — Historia wersji (minuty)

**Kiedy:** zepsuty plan treningowy albo plan diety.

Wersje planów i diet są **niemutowalne**. Nowa wersja nigdy nie nadpisuje
starej — poprzednie są dostępne w widoku planu. Powrót do starszej treści
robi się przez utworzenie nowej wersji z dawną zawartością.

Dotyczy: plany treningowe, plany diety (razem z suplementacją), szablony.

---

## Warstwa 3 — Archiwum (minuty)

**Kiedy:** ćwiczenie, produkt albo wpis bazy wiedzy „zniknął" z listy.

Prawdopodobnie jest zarchiwizowany, a nie usunięty. W panelu trenera:
przełącznik **„Pokaż zarchiwizowane"** → pozycja → przywróć.

W aplikacji **nie ma endpointu kasującego ćwiczenie ani produkt**. Jeśli
czegoś nie widać, to jest zarchiwizowane albo należy do innego trenera.

---

## Warstwa 4 — Kopia zapasowa (godziny)

**Kiedy:** uszkodzona baza, zły masowy zapis, awaria maszyny.

Kopie robi się **codziennie o 02:30 UTC** (workflow „Kopia zapasowa
(Fly.io)"), można też uruchomić ręcznie z zakładki Actions. Archiwum
`dzik-backup-<data>.tar.gz` obejmuje spójnie: bazę główną (przez sqlite3
backup API, nie kopiowanie pliku na żywo), łańcuch audytu i katalog
uploadów. Trzymamy **14 najnowszych** w `/data/backups`.

### Procedura odtworzenia

```bash
flyctl ssh console -a dzik-os-panel
ls -la /data/backups                       # wybierz archiwum
# Odtwarzanie wykonuj przy ZATRZYMANEJ aplikacji.
python -m dzik_os.backup --restore /data/backups/dzik-backup-<data>.tar.gz --force
```

Bez `--force` narzędzie **odmawia nadpisania** istniejących danych — to
zabezpieczenie, nie usterka. Po odtworzeniu narzędzie samo weryfikuje
łańcuch audytu i wypisuje wynik.

### Sprawdzone, nie zadeklarowane

Procedura została przećwiczona **2026-08-18** na pełnej bazie (7 kont, 256
ćwiczeń, 4 plany, pliki uploadów): baza, audyt i uploady skasowane, potem
odtworzone z archiwum. Wynik: komplet danych zgodny ze stanem sprzed
skasowania, skasowany plik uploadu z powrotem na dysku,
`verify_chain() = True`. To była **realna próba**, nie test jednostkowy.

Powtarzaj tę próbę po każdej zmianie w `backup.py` albo w strukturze
`/data`. Kopia, której nigdy nie odtworzono, nie jest kopią zapasową —
jest przypuszczeniem.

---

## Warstwa 5 — Snapshot wolumenu Fly (dni)

**Kiedy:** utracony cały wolumen `dzik_data` — czyli razem z archiwami z
warstwy 4.

Fly robi automatyczne snapshoty wolumenów. Odtworzenie tworzy **nowy
wolumen** ze snapshotu; trzeba go podmontować i przepiąć maszynę.

```bash
flyctl volumes list -a dzik-os-panel
flyctl volumes snapshots list <volume_id>
flyctl volumes fork <volume_id> --snapshot-id <snapshot_id> -a dzik-os-panel
```

**Znana słabość, wypisana wprost:** archiwa z warstwy 4 leżą **na tym samym
wolumenie**, który mają chronić. Przy utracie wolumenu warstwy 4 i 5 padają
razem, a jedyną obroną zostaje snapshot Fly — którego odtworzenia jeszcze
nie ćwiczyliśmy. Kopiowanie archiwów poza maszynę jest **świadomie**
wyłączone: dane zdrowotne nie mają trafiać do artefaktów GitHub Actions.
Docelowe rozwiązanie to własny magazyn poza Fly (S3/B2) z osobnym kluczem —
nierobione, bo wymaga Twojej decyzji o dostawcy.

---

## Czego odzyskać się NIE da

Uczciwa lista — te rzeczy są bezpowrotne z założenia albo z konieczności.

1. **Usunięcie konta klienta na jego żądanie (RODO).** Kasuje dane
   osobowe, pomiary, zdjęcia, wiadomości i odpowiedzi. Tak ma działać —
   „prawo do bycia zapomnianym" nie może mieć furtki. Zostaje wyłącznie
   ślad w audycie (fakt usunięcia, bez treści).
2. **Utrata klucza `DZIK_FILE_KEY`.** Pliki uploadów są szyfrowane at-rest
   (AES-256-GCM). Bez klucza archiwum jest **nie do odczytania**. Klucz
   trzymaj **osobno** od kopii zapasowych — kopia i klucz w jednym miejscu
   znoszą sens szyfrowania i jednocześnie ryzykują utratą obu naraz.
3. **Import starszy niż 20 ostatnich.** Patrz warstwa 1.
4. **Dane zapisane po ostatniej kopii.** Przy codziennym backupie okno
   utraty to **do 24 godzin** pracy. Skrócenie = częstszy harmonogram w
   `.github/workflows/fly-backup.yml`.

---

## Zanim zrobisz coś ryzykownego

* **Import w trybie „Zastąp"** — najpierw „Pokaż, co się zmieni". Zapis
  tworzy punkt przywracania automatycznie, ale podgląd i tak pokaże, czy
  plik jest tym, czym myślisz.
* **Masowa zmiana bazy ćwiczeń** — kliknij „Pobierz to, co mam teraz".
  Eksport jest w formacie importu, więc jest zarazem kopią i drogą powrotu.
* **Zmiana w `backup.py` albo w układzie `/data`** — powtórz próbę
  odtworzenia z warstwy 4 i dopisz datę w tym dokumencie.

---

## Automatyczna próba odtworzenia (od 0.53.9)

Co poniedziałek 05:00 UTC workflow **„Próba odtworzenia backupu
(Fly.io)"** wykonuje na maszynie produkcyjnej pełny, nieniszczący cykl:
świeże archiwum → odtworzenie do katalogu tymczasowego (dane produkcyjne
strukturalnie nietykane — proces odtwarzający dostaje inne ścieżki przez
env) → liczności kluczowych tabel + liczba plików uploadów + niezależna
weryfikacja łańcucha audytu → sprzątanie. Raport w logu Actions zawiera
wyłącznie nazwy tabel i liczby (zero PII).

**Czerwony przebieg tego workflow to alarm**: kopia zapasowa nie
dowiodła odtwarzalności. Obejrzyj log, powtórz ręcznie
(`python -m dzik_os.proba_odtworzenia` przez `flyctl ssh console`)
i nie odkładaj — do czasu wyjaśnienia realny backup może być bezwartościowy.
Ręczne odtworzenie NA ŻYWE dane pozostaje procedurą z warstwy 4 tego
dokumentu (przy zatrzymanej aplikacji).
