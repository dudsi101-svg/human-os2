# Model danych — Dzik OS

Definicje: `backend/dzik_os/models.py` (SQLAlchemy). Identyfikatory w
konwencji Human OS: `HOS-<PREFIX>-<hex12>` (wzorzec
`schemas/common.schema.json` po DD-010). Daty jako ISO-8601 (UTC).
Migracje: `db.py` — rejestr `schema_migrations`, wersja 1 = schemat MVP.

## Konta i dostęp

| Tabela | Rola | Kluczowe pola |
|---|---|---|
| `users` | konto | email, password_hash (bcrypt), display_name, identity_id, status, anonymized_at |
| `role_grants` | rola uprawnień (oś B) | user_id, role, scope, issued_by, valid_from/to, revoked_at |
| `auth_sessions` | sesje | token_hash (SHA-256), expires_at, revoked_at |
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
| `weekly_checkins` | payload_json (formularz), status SUBMITTED/REVIEWED, revision, coach_response, rating (1-5, opcjonalna ocena **raportu** przez trenera — nie ocena osoby) |
| `checkin_revisions` | poprzednie wersje poprawianych raportów (append-only) |

## Pomiary i pliki

| Tabela | Uwagi |
|---|---|
| `metric_definitions` | własne mierniki trenera (nazwa, jednostka) |
| `measurements` | kind, value, unit, measured_at, source, created_by |
| `files` | filename, content_type (whitelist), size, sha256, storage_path (losowa nazwa), uploaded_by, deleted_at |
| `documents` | metadane dokumentu klienta (tytuł, kategoria) → files |
| `progress_photos` | zdjęcia sylwetki, opcjonalnie związane z raportem |

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

## Powiadomienia push

| Tabela | Uwagi |
|---|---|
| `push_subscriptions` | subskrypcja Web Push (endpoint unique, klucze p256dh/auth, user_id). **Opt-in**: powstaje wyłącznie po jawnej zgodzie w UI (zdarzenie PUSH_SUBSCRIBED), usuwana jednym przyciskiem (PUSH_UNSUBSCRIBED) lub automatycznie po 404/410 od dostawcy. Treść powiadomień nigdy nie zawiera danych zdrowotnych ani treści wiadomości — wyłącznie neutralne wezwanie (push_service.py). Klucz VAPID generowany automatycznie, trwały na wolumenie danych (poza repo). Przypomnienia harmonogramu wysyła pętla w procesie (reminder_loop.py, strefa DZIK_TZ). |

## Komunikacja i płatności

| Tabela | Uwagi |
|---|---|
| `message_threads` | unique(coach, client) |
| `messages` | body, file_id, read_at |
| `payment_schedules` | pakiet, kwota (grosze), okres, external_link |
| `payment_records` | due_date, status PENDING/PAID/OVERDUE/CANCELLED, paid_at, marked_by |

## Audyt (Human OS Core)

| Magazyn | Uwagi |
|---|---|
| `audit.db` (SQLite, hash chain) | `hos_engine.sqlite_store.SQLiteEventStore` — zdarzenia niemutowalne, previous_hash/event_hash, `verify_chain()` |
| `receipts` (tabela główna) | pokwitowanie operacji: event_id, event_hash, action, actor, subject, summary |

Wspólne atrybuty encji istotnych: stabilny identyfikator, created_at,
created_by/author, wersja lub rewizja, status, źródło/proweniencja,
właściciel danych oraz powiązanie z łańcuchem zdarzeń przez `receipts`.
