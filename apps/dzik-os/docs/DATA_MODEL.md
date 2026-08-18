# Model danych — Dzik OS

Definicje: `backend/dzik_os/models.py` (SQLAlchemy). Identyfikatory w
konwencji Human OS: `HOS-<PREFIX>-<hex12>` (wzorzec
`schemas/common.schema.json` po DD-010). Daty jako ISO-8601 (UTC).
Migracje: `db.py` — rejestr `schema_migrations`, wersja 1 = schemat MVP.

## Konta i dostęp

| Tabela | Rola | Kluczowe pola |
|---|---|---|
| `users` | konto | email, password_hash (bcrypt; `"!"` dla PENDING = brak hasła), display_name, identity_id, status (PENDING/ACTIVE/SUSPENDED/DELETED), anonymized_at, totp_secret/totp_confirmed_at/totp_last_counter (MFA) |
| `role_grants` | rola uprawnień (oś B) | user_id, role, scope, issued_by, valid_from/to, revoked_at |
| `auth_sessions` | sesje | token_hash (SHA-256), expires_at, revoked_at |
| `client_invitations` | zaproszenie aktywacyjne (migracja 11) | coach_id, client_id, email, token_hash (SHA-256, jedyny ślad tokenu), expires_at (7 dni), used_at, cancelled_at — jednorazowe; nowe unieważnia poprzednie |
| `password_reset_tokens` | reset hasła (migracja 11) | user_id, token_hash (SHA-256), expires_at (60 min), used_at — jednorazowy; użycie unieważnia wszystkie sesje |
| `mfa_recovery_codes` | kody odzyskiwania MFA (migracja 11) | user_id, code_hash (SHA-256), used_at — jednorazowe; regeneracja unieważnia stare |
| `mfa_challenges` | wyzwanie drugiego kroku logowania (migracja 11) | user_id, token_hash (SHA-256), expires_at (5 min), used_at |
| `coach_client_relationships` | współpraca | coach_id, client_id, status, started_at/ended_at, created_by |
| `consents` | zgody (trwała warstwa ConsentRegistry) | subject_id, grantee_id, purpose, domain, actions, allow_sensitive, consent_text_version, granted_at, revoked_at |

## Profil i cele

| Tabela | Uwagi |
|---|---|
| `profile_fields` | **append-only, wersjonowanie per pole**: field_key, value, source, author_id, purpose, version, is_current, sensitive |
| `goals` | cel główny/dodatkowy, target_date, status, created_by, version |

## Trening

| Tabela | Uwagi |
|---|---|
| `training_plans` | client_id NULL ⇒ szablon trenera; current_version_no |
| `training_plan_versions` | **niemutowalne**; unique(plan_id, version_no); reason obowiązkowy; content_json = {days:[{name, weekday, exercises:[{name, sets, reps, weight, tempo, rest, comment, video_url}]}]} |
| `workout_sessions` | wykonanie dnia planu: performed_on, status, comment, pain_flag, pain_note |
| `workout_entries` | wynik per ćwiczenie: result, comment, file_id (film) |

## Dieta

| Tabela | Uwagi |
|---|---|
| `nutrition_plans` | jak training_plans |
| `nutrition_plan_versions` | niemutowalne; kcal/makro, sections, meals (z zamiennikami), document_id (PDF) |

## Harmonogram i raporty

| Tabela | Uwagi |
|---|---|
| `schedule_items` | kategoria (TRENING/POSILEK/NAWODNIENIE/REGENERACJA/SUPLEMENT/POMIAR/RAPORT/PLATNOSC/INNE), pora, dni tygodnia, autor_id + author_note (proweniencja zalecenia), status |
| `reminders` | jednorazowe przypomnienia trenera |
| `weekly_checkins` | payload_json (formularz), status SUBMITTED/REVIEWED, revision, coach_response, rating (1-5, opcjonalna ocena **raportu** przez trenera — nie ocena osoby), photos_expected (migracja 12, NULLable — deklarowana liczba zdjęć; mniej zapisanych = raport jawnie CZĘŚCIOWY, `photos_complete=false` w API; NULL = raport historyczny/bez deklaracji, traktowany jako kompletny) |
| `checkin_revisions` | poprzednie wersje poprawianych raportów (append-only); raport z revision > 1 ma w API flagę `corrected` |
| `idempotency_keys` | migracja 12: klucz idempotencji operacji zapisu — unique(user_id, operation, idem_key), request_hash (SHA-256 kanonicznego JSON-a żądania), response_json (zapisany wynik operacji: identyfikatory/liczniki, nigdy treść formularza). Powtórka z tym samym kluczem i treścią zwraca zapisany wynik; ten sam klucz z inną treścią = 409. Usuwane przy usunięciu konta. |

### Stany odpowiedzi skalowych raportu (`payload_json.scale_states`)

Subiektywne skale 1–5 (`diet_adherence`, `energy`, `sleep`, `hunger`,
`stress`, `recovery`) NIE mają wartości domyślnej. `scale_states` (mapa
klucz → stan, wewnątrz payload_json — bez zmiany schematu) rozróżnia:

| Stan | Wartość skali | Znaczenie |
|---|---|---|
| `ANSWERED` | 1–5 (wymagana) | świadomie wybrana wartość — **w tym neutralne 3/5** |
| `SKIPPED` | NULL (wymuszone) | świadome pominięcie pytania |
| `NOT_APPLICABLE` | NULL (wymuszone) | pytanie nie dotyczy tego tygodnia |
| brak klucza | NULL | brak odpowiedzi |

Raporty sprzed 0.15.0 nie mają `scale_states` — ich wartości NIE są
reinterpretowane (brak retroaktywnej migracji); API oznacza je
`scales_declared=false`, a punkty samopoczucia w monitoringu niosą
`declared=false` (UI: nota „wartość mogła zostać na domyślnym 3/5").
Walidacja spójności (wartość bez stanu, stan bez wartości itd.) w
`schemas.CheckinIn._validate_scale_states` — działa tylko przy podanym
`scale_states` (stare klienty API działają bez zmian).

## Pomiary i pliki

| Tabela | Uwagi |
|---|---|
| `metric_definitions` | własne mierniki trenera (nazwa, jednostka) |
| `measurements` | kind, value, unit, measured_at, source, created_by |
| `files` | filename, content_type (whitelist), size, sha256, storage_path (losowa nazwa), uploaded_by, deleted_at |
| `documents` | metadane dokumentu klienta (tytuł, kategoria) → files |
| `progress_photos` | zdjęcia sylwetki, opcjonalnie związane z raportem; pose (PRZOD/BOK/TYL/INNE) i position (kolejność wybrana przez klienta) — migracja 12, NULL = zdjęcie historyczne. Dopinanie: przy wysyłce raportu lub pojedynczo przez `POST /api/checkins/{id}/photos` (dedup po file_id; po ocenie trenera 409). Zdjęcia przechodzą kompresję i usunięcie EXIF/GPS po stronie klienta (canvas) ORAZ backendu (P4, Pillow) — dwie niezależne warstwy. Id i nazwy plików zdjęć nigdy nie trafiają do audytu/push/logów — wyłącznie liczniki. |

## Monitoring w czasie

| Tabela | Uwagi |
|---|---|
| `schedule_completions` | adherencja elementu harmonogramu per dzień: completed_on, status DONE/SKIPPED, note; unique(schedule_item_id, completed_on) — idempotentne odhaczenie |
| `observations` | dziennik obserwacji (samopoczucie/objaw/reakcja/inne), opcjonalnie powiązany ze schedule_item_id; severity INFO/NIEPOKOJACE — **wyłącznie flaga do przeglądu przez trenera, nigdy diagnoza ani automatyczna interpretacja** |
| `daily_nutrition_logs` | dzienny log kcal/makro/wody, osobny od statycznego celu w `nutrition_plan_versions`; unique(client_id, logged_on) |

Agregacja `/api/clients/{id}/monitoring` łączy powyższe z celem (`goals`),
pomiarami i raportami tygodniowymi w jeden przegląd trendów — nie jest
osobnym magazynem danych, tylko odczytem z istniejących tabel.

## Baza wiedzy

| Tabela | Uwagi |
|---|---|
| `knowledge_items` | materiał trenera (artykuł/link/plik): title, category, body, external_url, file_id, pinned, status ACTIVE/ARCHIVED. **Broadcast**, nie per-klient — widoczny dla wszystkich aktywnie prowadzonych klientów danego trenera (`coach_id`), nie przechodzi przez `resolve_client_access` bo to własność trenera, nie dane klienta. |
| `exercises` | know-how ćwiczeń: name, muscle_group (NOGI/PLECY/KLATKA/BARKI/RECE/BRZUCH/CALE_CIALO/MOBILNOSC/INNE), how_to, benefit, equipment, video_url, status. **Broadcast**, ten sam wzorzec co `knowledge_items`. |
| `food_products` | baza produktów: name, category, kcal_100g/protein_100g/fat_100g/carbs_100g, default_portion_g, status. **Broadcast**, ten sam wzorzec co `knowledge_items`. Przeliczenie na porcję (kcal/makro × gramatura/100) jest czystą arytmetyką po stronie frontendu — nie osobnym magazynem danych. |

**Kompozytor diety** (`POST /api/coach/diet-suggestion`, trener-only, nic
nie zapisuje) nie ma własnej tabeli — bierze `target_kcal/protein_g/
fat_g/carbs_g` i listę `product_ids` **wybranych przez trenera**,
klasyfikuje każdy produkt wg makroskładnika o największym udziale
kalorycznym (deterministyczna reguła, nie AI), dzieli cel danego makro
równo między produkty tej kategorii i zwraca gramaturę + kcal/makro per
produkt jako **sugestię do ręcznego wpisania** w `nutrition_plan_versions`
— zgodnie z zasadą Human OS, że AI/algorytm nigdy nie generuje ani nie
zmienia diety autonomicznie.

## Konsultacje

| Tabela | Uwagi |
|---|---|
| `consult_slots` | slot konsultacji trenera: starts_at (czas lokalny DZIK_TZ, „YYYY-MM-DDTHH:MM"), duration_min, status OPEN/BOOKED/CANCELLED, client_id + booked_at po rezerwacji. Klient rezerwuje wyłącznie sloty trenerów, którzy go aktywnie prowadzą; odwołanie klienta do 12 h przed terminem, trenera w każdej chwili (push do drugiej strony). Bez kar/metryk za odwołania. |

## Wyzwania (moduł prywatny — pełny opis: WYZWANIA.md)

| Tabela | Uwagi |
|---|---|
| `challenges` | wyzwanie tylko-dla-zaproszonych (visibility zawsze INVITE_ONLY): kind INDIVIDUAL/GROUP, organizer_id, NEUTRALNA jednostka (treningi/minuty/aktywnosci — nigdy masa ciała), goal_value, okno starts_on/ends_on, **strefa czasowa wyzwania**, status DRAFT/ACTIVE/FINISHED/CANCELLED, max_entries_per_day, aggregates_adjusted (po trwałym wycofaniu udziału). |
| `challenge_participants` | udział dobrowolny: status INVITED/ACTIVE/DECLINED/LEFT/REMOVED/WITHDRAWN, alias (pseudonim per wyzwanie), share_result i ranking_opt_in **domyślnie false** (konstytucja: zakaz rankingu domyślnego), auto_count_workouts (świadoma decyzja przy dołączaniu). Unikalne (challenge, user). |
| `challenge_entries` | wpis wyniku: entry_date wg strefy WYZWANIA, value, note (jedyny wolny tekst, moderowalny), source MANUAL/WORKOUT, workout_session_id (unikalny per wyzwanie — jeden trening raz), client_entry_id (idempotencja ponowień), status ACTIVE/CORRECTED + corrects_entry_id (korekty łańcuchem, historia nie jest nadpisywana). |
| `challenge_blocks` | blokada między uczestnikami (obustronna niewidoczność wyników/aliasów; agregat grupy bez zmian). |
| `challenge_reports` | zgłoszenie do organizatora: reason (widzi tylko organizator), status OPEN/RESOLVED, resolution REMOVED/ALIAS_RESET/NOTES_CLEARED/DISMISSED. |

## Powiadomienia push

| Tabela | Uwagi |
|---|---|
| `push_subscriptions` | subskrypcja Web Push (endpoint unique, klucze p256dh/auth, user_id). **Opt-in**: powstaje wyłącznie po jawnej zgodzie w UI (zdarzenie PUSH_SUBSCRIBED), usuwana jednym przyciskiem (PUSH_UNSUBSCRIBED) lub automatycznie po 404/410 od dostawcy. Treść powiadomień nigdy nie zawiera danych zdrowotnych ani treści wiadomości — wyłącznie neutralne wezwanie (push_service.py). Klucz VAPID generowany automatycznie, trwały na wolumenie danych (poza repo). Przypomnienia harmonogramu wysyła pętla w procesie (reminder_loop.py, strefa DZIK_TZ). |

## Komunikacja i płatności

| Tabela | Uwagi |
|---|---|
| `message_threads` | unique(coach, client) |
| `messages` | body, file_id, statusy: delivered_at/read_at (migracja 13), client_msg_id (deduplikacja ponowień, unikalny per wątek+autor); porządek (created_at, id) — patrz `WIADOMOSCI.md` |
| `payment_schedules` | pakiet, kwota (grosze), okres, external_link |
| `payment_records` | NALEŻNOŚĆ: due_date, status wg maszyny stanów (PLANNED/PENDING/IN_PROGRESS/PAID/OVERDUE/FAILED/CANCELLED/PARTIALLY_REFUNDED/REFUNDED — `payment_state.py`), paid_at, marked_by/marked_at (kto i kiedy oznaczył); pełny model: `PLATNOSCI.md` |
| `payment_transactions` | append-only przepływy/korekty (migracja 15): MANUAL_PAYMENT/PROVIDER_PAYMENT/REFUND/ADJUSTMENT/REVERSAL, kwota w groszach + waluta, document_ref (referencja faktury/przelewu), reverses_transaction_id |
| `payment_status_changes` | append-only historia przejść statusu per rekord (kto, kiedy, skąd→dokąd, powód, transakcja) |
| `payment_attempts` | próby płatności u przyszłego operatora online (system ręczny ich nie tworzy) |
| `payment_provider_events` | rejestr przetworzonych webhooków operatora — idempotencja (unique provider+event_id) i ochrona przed złą kolejnością |

## Audyt (Human OS Core)

| Magazyn | Uwagi |
|---|---|
| `audit.db` (SQLite, hash chain) | `hos_engine.sqlite_store.SQLiteEventStore` — zdarzenia niemutowalne, previous_hash/event_hash, `verify_chain()` |
| `receipts` (tabela główna) | pokwitowanie operacji: event_id, event_hash, action, actor, subject, summary |

Wspólne atrybuty encji istotnych: stabilny identyfikator, created_at,
created_by/author, wersja lub rewizja, status, źródło/proweniencja,
właściciel danych oraz powiązanie z łańcuchem zdarzeń przez `receipts`.

## Konwencje dat

Jedno źródło prawdy: `backend/dzik_os/dates.py` i `frontend/src/dates.ts`.

| Typ daty | Przykładowe pola | Format | Strefa |
|---|---|---|---|
| Data kalendarzowa użytkownika | `performed_on`, `logged_on`, `occurred_on`, `completed_on`, `week_start`, `measured_at` (pomiary), `taken_at`, `start_date`/`end_date`, `target_date` | `YYYY-MM-DD` | lokalna strefa użytkownika (frontend: przeglądarka; backend: `tz_for_user()` → `DZIK_TZ`, domyślnie Europe/Warsaw) |
| Dokładny moment zdarzenia | `created_at`, `updated_at`, `paid_at`, `read_at`, `booked_at`, `granted_at`, audyt | pełny timestamp ISO z offsetem | UTC (`now_iso()`); do strefy lokalnej przeliczany dopiero przy prezentacji (`plDateTime`) |
| Termin lokalny | `consult_slots.starts_at` | naiwny `YYYY-MM-DDTHH:MM` | lokalna (`DZIK_TZ`); porównywany wyłącznie z `local_now_minute()` / `localNowMinute()` |
| Data rozliczeniowa | `payment_records.due_date` | `YYYY-MM-DD` | jak data kalendarzowa; zaległość względem `local_today()` |

Zakazane wzorce: `new Date().toISOString().slice(0, 10)` i
`datetime.now(UTC).date()` dla dat kalendarzowych (o 00:00–02:00 czasu
polskiego wskazują wczorajszy dzień) oraz porównywanie `starts_at`
z czasem UTC. Strefa per użytkownik: punkt rozszerzenia
`tz_for_user(user)` honoruje przyszłe pole `User.timezone`.

## Plan wycofania migracji 12 (jakość raportów i zdjęć)

Migracja 12 jest **czysto addytywna**: trzy kolumny NULLable
(`weekly_checkins.photos_expected`, `progress_photos.pose`,
`progress_photos.position`) i jedna nowa tabela (`idempotency_keys`).
Nie zmienia żadnych istniejących wierszy (stare raporty z wartościami
1–5 pozostają nietknięte; `scale_states` żyje w `payload_json`, więc
wycofanie kodu nie wymaga migracji danych).

Kroki wycofania (w tej kolejności):

1. **Wycofanie kodu** do wersji sprzed 0.15.0. Stary kod ignoruje nowe
   kolumny (ORM czyta tylko znane pola przez nazwane atrybuty — SELECT-y
   nie używają `*` w sposób łamiący zgodność) i nie zna `scale_states`
   w payloadzie — raporty pozostają czytelne, bez utraty danych.
   Frontend sprzed 0.15.0 wysyła wartości bez `scale_states` (ścieżka
   legacy pozostaje wspierana w obie strony).
2. **Opcjonalne czyszczenie schematu** (tylko jeśli wymagane — kolumny
   NULLable nie przeszkadzają staremu kodowi):
   * `DROP TABLE idempotency_keys` (dane operacyjne — identyfikatory
     i liczniki, brak treści zdrowotnych; utrata = powrót do braku
     ochrony przed podwójnym wysłaniem, nic więcej),
   * SQLite ≥ 3.35 / PostgreSQL: `ALTER TABLE weekly_checkins DROP COLUMN
     photos_expected`, `ALTER TABLE progress_photos DROP COLUMN pose`,
     `ALTER TABLE progress_photos DROP COLUMN position` — **utrata
     informacji** o deklaracji kompletności oraz typie ujęcia/kolejności
     zdjęć; jeśli te dane mają przetrwać ewentualny powrót, pominąć DROP.
   * `DELETE FROM schema_migrations WHERE version = 12` po zdjęciu
     schematu (tylko razem z punktem powyżej — nigdy sam).
3. **Dane, których wycofanie nie dotyka**: `payload_json.scale_states`
   pozostaje w raportach wysłanych w 0.15.0 — stary kod go nie czyta
   i pokazuje wartości skal jak dotychczas (pominięte pytania będą
   widoczne jako puste, co jest poprawne semantycznie).

Ryzyko wycofania: niskie. Jedyny stan tracony bezpowrotnie przy pełnym
DROP to deklaracje `photos_expected`/`pose`/`position` i klucze
idempotencji.
