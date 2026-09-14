# Rozpoznanie (etap 0) — panel rozwojowy „Dzisiaj”

* `routers/today.py`: `today_view` → `client_id = require_client_self`, `today = local_today(user)`,
  `weekday = isoweekday()`; harmonogram filtruje `days_of_week` (string „1,2,…”), `start_date/end_date`;
  `done_today_ids` z `ScheduleCompletion`; zwraca słownik z `date, weekday, workout, nutrition,
  schedule, reminders, checkin_due, next_payment, last_coach_message`.
* `models.ScheduleCompletion`: `UniqueConstraint(schedule_item_id, completed_on)`, `status` DONE/SKIPPED,
  `created_by`; `routers/monitoring.complete_schedule_item`: `resolve_client_access(db, user, client_id,
  action="write", domain=DOMAIN_TRAINING)`, IDOR → `deny`, istniejący wpis nadpisywany (idempotencja).
* `routers/schedule.py` POST `/schedule`: `author_id=user.id`, `author_note`; `ScheduleItem` ma
  `days_of_week` default „1,2,3,4,5,6,7”, `status` ACTIVE/PAUSED/ENDED.
* `seed.py`: `ScheduleItem(... client_id=client_a.id, author_id=coach.id)`, `ScheduleCompletion(...)`
  w pętli po `offset` dni wstecz (ok. l. 410–470).
* `tests/access_matrix.py`: harmonogram `CLIENT_SCOPED` dla tras `/clients/{client_id}/…`,
  `RESOURCE_SCOPED` dla `/schedule/{item_id}`. Fixtury: `seeded`, `login`, `CLIENT_A/B`, `COACH`,
  `create_activated_client(client, coach_headers, email)`.
* Frontend: `Today.tsx` (286 linii) — karty u góry (`card card--accent`), harmonogram z
  `markScheduleDone` i `badge badge--ok`; `TodayData` w `types.ts` l. 396; `Icon` ma `check`,
  `target`, `star`, `sparkle`, `trophy`, `clipboard`; CSS `.stat`, `.card--accent`, `.badge--ok`.
* Trener: `ClientDetail.tsx` zakładka `harmonogram` → `ScheduleTab` (formularz „Dodaj element”).
* Dokumenty: `ANALIZA_RYNKU` §E (l. 81–100), `INTENDED_PURPOSE` §2/§3, `RISK_REGISTER` tabela R-xx,
  `PERMISSIONS.md` macierz (l. 70+, wiersze harmonogramu l. 108–109), `INSTRUKCJA_KLIENTA` §„Ekran
  Dzisiaj” (l. 24), `INSTRUKCJA_TRENERA` §„Prowadzenie klienta” (Harmonogram l. 103).
* a11y: `e2e/test_a11y.mjs` sprawdza ekran „Dzisiaj” (jeden h1, `HEADINGS_JS`), E2E logowania
  klienta oczekuje ekranu „Dzisiaj”.
