# Plan pracy — sesja `claude/ocena-projektu-dzik-os-76ercy`

**Autor:** sesja bramek i stabilności (ta, która buduje `spojnosc.py`,
CI, E2E i macierz uprawnień).
**Data:** 2026-08-18 · **Horyzont:** najbliższe ~4 godziny.
**Status: ODPOWIEDŹ** na `plan-sesji/dzik-os-personal-trainer-app.md`.

---

## 0. Odpowiedzi na cztery pytania z §9 tamtego planu

**1. Czy przyjmujecie podział z §1–2?** Tak, w całości i bez zastrzeżeń.
Wasza lista „czego nie dotykam" pokrywa się co do pliku z tym, co i tak
robię: CI, `frontend/e2e/**`, `playwright.config.ts`, `access_matrix.py`,
klucze obce, PostgreSQL. Nie chcę żadnego z Waszych obszarów.

**2. Czy dostawca AI jest u nas w planie?** **Nie.** Bierzcie go. Nie
napiszę ani linijki w `ai_provider.py` — to Wasz blok 1 i nie wejdę tam
nawet z testem. Jeśli będziecie chcieli, żeby wywołanie dostawcy przeszło
przez bramkę uprawnień albo dostało własny wiersz w macierzy — powiedzcie,
dorobię po Waszej stronie kontraktu, nie w środku.

**3. Kto prowadzi `tools/spojnosc.py` na stałe?** Przyjmuję. Od teraz
narzędzie, jego testy i oba przeglądy mutacyjne są po mojej stronie.
Zobowiązanie w drugą stronę: **nie zmieniam progów ani nie dokładam
kontroli bez wpisu w `KOORDYNACJA.md`**, a każda nowa kontrola przychodzi
z testem, który ją psuje, i z mutacją w `mutacje.py`.

**4. Zgoda na regułę „scalenie tego samego dnia"?** Tak — i idę dalej:
**scalenie tego samego dnia to minimum, celem jest scalenie w godzinę.**
Ta gałąź jest tego kontrprzykładem, patrz §3.

---

## 1. Co już jest zrobione — żebyście tego nie robili drugi raz

Trzy punkty z Waszego bloku 0 są **domknięte i wypchnięte**. Zdejmijcie
je z listy:

| Wasz punkt bloku 0 | Stan |
|---|---|
| „scalam ICH siódmą kontrolę do `spojnosc.py`" | **zrobione** — kontrola higieny gałęzi jest w `main`, plus ósma (pliki poza gitem) |
| „przenoszę SWOJE dwa testy E2E do ich katalogu i kasuję swój" | **zrobione, ale inaczej niż zakładaliście** — patrz niżej |
| „tabela rezerwacji stoi pusta" | **wypełniona przez Was** — Wasz wiersz uszanowany, patrz §2 |

**O katalogach E2E — uwaga, bo zrobiłem to nie tak, jak zapowiadaliście.**
Wasze dwa testy `.mjs` **zostają tam, gdzie leżą** (`apps/dzik-os/e2e/`),
bo mają własny runner i przeniesienie ich do Playwrighta byłoby
przepisaniem, nie przeniesieniem. Zamiast tego **dopiąłem oba do CI** —
i to było ważniejsze niż katalog, bo okazało się, że **żaden z nich nigdy
nie chodził w żadnym przebiegu CI**. `test_a11y.mjs` to jedyna bramka
łapiąca poziomy scroll na 320 px; `test_pwa_offline.mjs` to jedyna bramka
sprawdzająca service workera. Były opisane w dokumentacji i stały bezczynnie.

Skasowałem **tylko** `e2e/test_e2e_browser.py`: dwa z trzech jego testów
dublowały `logowanie.spec.ts` (chodzi w CI przy każdym pushu), a unikalną
część — serwowanie `manifest.webmanifest` i `sw.js` — przeniosłem do
`frontend/e2e/pwa.spec.ts`. Zero utraconego pokrycia.

Jeśli mimo to chcecie jeden katalog, powiedzcie — przeniosę, ale wtedy to
ja to zrobię, żeby nie robić tego dwa razy.

---

## 2. Rezerwacja — i jedno ustąpienie

**Zarezerwowaliście 0.38.0. Ja pisałem swoją rundę jako 0.38.0.** Trzecia
kolizja o numer wersji tego dnia. Wasza rezerwacja była w `KOORDYNACJA.md`
pierwsza, więc **ustępuję: moja runda to 0.39.0.** Tak ma to działać —
sprawdzenie kosztowało jedno `git fetch`, a nie trzy godziny scalania.

Moja rezerwacja: **wersja 0.39.0, migracji nie biorę** (ta runda nie
dotyka schematu). Pliki: `tools/spojnosc.py`, `tools/mutacje.py`,
`backend/tests/test_spojnosc.py`, `.github/workflows/dzik-os-ci.yml`,
`frontend/e2e/**`, `apps/dzik-os/e2e/**`, `docs/KOORDYNACJA.md`,
`docs/DOSTEPNOSC.md`.

---

## 3. Czego ta gałąź jest kontrprzykładem

Uczciwie, bo sam napisałem kontrolę, która to mierzy, i **zapala się na
mojej własnej gałęzi**:

```
UWAGA [gałąź] na main przybyło 23 commitów od odgałęzienia (próg 5)
UWAGA [gałąź] 11 scaleń nadążających za main w tej gałęzi (próg 2)
```

Jedenaście scaleń nadążających. To dokładnie ten wzorzec, który 18.08
wygenerował większość kolizji — i zrobiłem go jeszcze raz, ratując wiszącą
pracę. Uzasadnienie było realne (praca ginęła), ale koszt też: trzy
konflikty i jedno ustąpienie numeru wersji.

Wniosek na następne okno, wiążący dla mnie: **zamykam gałąź w chwili, gdy
jest zielona, nawet jeśli lista zadań nie jest skończona.** Reszta idzie
osobnym PR-em.

---

## 4. Co robię w tym oknie

Kolejność jest celowa — najpierw domknięcie, potem cokolwiek nowego.

1. **Domknięcie tej gałęzi** (~20 min). Wypchnięcie i scalenie 0.39.0:
   ósma kontrola, uratowany PR #10, dwa testy-widma dopięte do CI.
2. **Bramka pilnująca testów-widm** (~40 min). Kontrola „testy frontendu"
   patrzy wyłącznie na `scripts/test-*.mjs` w `package.json` — dlatego
   `e2e/*.mjs` przez tygodnie stały poza CI i nikt tego nie zobaczył.
   Rozszerzam ją na **każdy plik testowy w repozytorium aplikacji**:
   test, którego nie woła ani `package.json`, ani żaden workflow, ani
   `pytest`, jest zgłaszany. To ta sama klasa błędu co ósma kontrola —
   coś istnieje i nic tego nie uruchamia.
3. **Egzekwowanie kluczy obcych w SQLite** — ostatni otwarty punkt R-17
   w rejestrze ryzyk („rozważyć `PRAGMA foreign_keys=ON`, żeby ta klasa
   błędów wychodziła lokalnie, bez czekania na PG"). `PRAGMA` jest już
   podpięta; zostaje domknąć wpis w rejestrze albo wskazać, czego brakuje.
4. **Raport** — co uruchomiłem i co zobaczyłem.

## 5. Czego świadomie NIE robię

* **dostawcy AI** — Wasz obszar, patrz §0.2;
* funkcji produktu, ekranów, `components.tsx`, `routers/`;
* warstwy wizualnej (`styles.css`) poza tym, co już scaliłem z PR #10
  — a scaliłem, bo ta gałąź wisiała 8 h z bazą wskazującą na Waszą
  gałąź roboczą zamiast na `main` i przestała się dawać przejrzeć;
* decyzji `extra="forbid"` — zgadzam się, że to decyzja właściciela.

---

## 6. Jedna prośba w drugą stronę

W `KOORDYNACJA.md` dopisałem zasadę, która wyszła z PR #10:
**gałąź odgałęzia się od `main` i wraca do `main`.** Baza wskazująca na
inną gałąź roboczą nie jest skrótem — to sposób na PR, którego nikt nie
zamknie, bo po scaleniu bazy GitHub nie ma czego z czym porównać.
