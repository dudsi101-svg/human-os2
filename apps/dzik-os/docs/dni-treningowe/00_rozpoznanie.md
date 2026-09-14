# Rozpoznanie (etap 0) — dni treningowe na „Dzisiaj” (0.71.0)

Weryfikacja linii z promptu `docs/zlecenia` (zlecenie 1) na `main` = `04d1d58`:

* `routers/today.py` l. 46–84: `todays_workout` = **pierwszy** dzień bieżącej wersji
  najnowszego ACTIVE planu, którego `day.get("weekday") == local_today(user).isoweekday()`;
  `done_today` po `WorkoutSession(client_id, plan_version_id, day_index, performed_on)`.
  Brak trafienia → `workout: null` → `Today.tsx` l. 192–197 karta „Dziś bez treningu”.
  Potwierdzona diagnoza: klient z planem bez `weekday` widzi tę kartę codziennie.
* `models.py` l. 224–262: `TrainingPlan` / `TrainingPlanVersion` (niemutowalne, `reason`),
  `content_json = {"days": [{"id"?, "name", "weekday": int|null, "exercises": [...]}]}`.
* `schemas.py` l. 97–101: `PlanDayIn.id: str|None`, `weekday: int|None (1–7)` — `POST /api/plans`
  i `POST /api/plans/{id}/versions` zapisują `model_dump()`, więc dni mają `id` tylko wtedy,
  gdy nadano je w szkicu (publikacja 0.58.0, `publikacja/elementy.py::znormalizuj` l. 73–96);
  seed i plany z API bez `id` → klucz zastępczy `idx:<n>`.
* `routers/habits.py` (cały) — wzorzec zasobu klienta z dostępem trenera:
  `resolve_client_access(db, user, client_id, action="read"|"write", domain=DOMAIN_TRAINING)`,
  IDOR → `deny(user.id, "habit:<id>")` = 404 z audytem, `record_event` przed `db.commit()`,
  payload bez treści. Skopiowany 1:1 do `routers/plan_weekdays.py`.
* `tests/access_matrix.py` l. 162/171–174: `/api/clients/{client_id}/plans` i `/habits` =
  `CLIENT_SCOPED`; `test_access_matrix._fill_path` podstawia obce `{plan_id}` nieistniejącym
  id — każda operacja `CLIENT_SCOPED` musi dać twardą odmowę (401/403/404), także z ciałem,
  więc `PUT …/dni` ma ciało satysfakcjonowalne domyślnymi (`choices: []`).
* `routers/privacy.py` l. 361–362 / 415–416 / 626–627 — wzorzec `Habit` w eksporcie
  (`_rows(db, Model, client_id=…)`, XLSX iteruje po kluczach) i usuwaniu konta;
  `export_version` = **„1.9”** (prompt mówił 1.8 — nieaktualne), sprawdzana w czterech testach.
* `db.py`: ostatni wpis **36**; 37 = `users.welcome_seen_at` z PR #70 (nie w `main`
  w chwili startu); `tests/test_migracje_przenosnosc.py` wymaga ciągu **bez luk** — wpis 38
  jest czerwony na tej gałęzi do scalenia `main` z 37 (`test_db_migracje` luki dopuszcza,
  `spojnosc.py` daje uwagę).
* `seed.py` l. 250–318: klient A pon./śr./pt. (v2), klient B FBW wt./czw./sob. (v1, bez `id`);
  klient C ma plan (l. 684), D (Anna Wilk) i E (Piotr Zając) — bez planu → stan „plan bez
  dni” w teście i przeklikaniu tworzony przez `POST /api/plans` trenera.
* Frontend: `Plan.tsx` l. 250–258 odznaka `WEEKDAYS[day.weekday-1]`; `Today.tsx` l. 156–197;
  `PlanEditor.tsx` l. 408–417 `select` z `<option value="">— dowolny —</option>` + `WEEKDAYS`
  (`dates.ts` l. 63); `ClientDetail.tsx::PlanTab` l. 517–640 (odznaka l. 621);
  `types.ts` `PlanDay` l. 51, `TodayData` l. 423; `api.ts` — `api.del`, nie `api.delete`;
  model błędów: `detail` zawsze tekst (`observability.http_exception_handler`), lista
  `errors: [{field,type,msg}]` tylko przy 422 → błąd „przy polu” idzie przez `error_response`.
* E2E: `playwright.config.ts` — `DZIK_E2E_PORT`, drugi serwer `PORT+1` (zmienna
  `DZIK_E2E_PORT_POSTEPY` przychodzi dopiero z PR #70); strefa `Europe/Warsaw`;
  `nawyki.spec.ts` na kliencie B (`zaloguj`, `data-testid`, `page.reload()`).
