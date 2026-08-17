# Mapa wymagań — Dzik OS

Wymaganie (brief) → implementacja → weryfikacja. Skróty:
`BE` = backend/dzik_os, `FE` = frontend/src, `T` = backend/tests.

| Wymaganie | Implementacja | Weryfikacja |
|---|---|---|
| Role COACH/CLIENT/ADMIN | BE models.RoleGrant, security.require_role | T test_isolation |
| Ekran „Dzisiaj" | BE routers/today.py, FE pages/client/Today | E2E test_client_login_and_today_screen |
| Profil z proweniencją pól | BE models.ProfileField (append-only), routers/profile | T test_audit… test_profile_versioning |
| Cele | BE routers/profile (goals), FE Profile/ClientDetail | T test_e2e_paths |
| Plany + wersje + powód zmiany | BE models.TrainingPlanVersion, routers/plans | T test_plan_versioning (5 testów) |
| Wyniki, ból, film z wykonania | BE WorkoutSession/WorkoutEntry, FE Plan | T test_workout_logging_against_plan |
| Dieta wersjonowana (kcal/makro/posiłki/zamienniki/PDF) | BE routers/nutrition, FE Nutrition + NutritionTab | T test_e2e_paths |
| Harmonogram (kategorie, autor, statusy) | BE models.ScheduleItem, routers/schedule | T test_high_significance…; E2E |
| Zakaz autonomicznego dawkowania | brak jakiegokolwiek kodu dobierającego dawki; author_id+author_note obowiązkowe w UI dla SUPLEMENT | przegląd kodu; ADR-DZIK-003 §4 |
| Raport tygodniowy + poprawki + odpowiedź trenera | BE routers/checkins (rewizje), FE Checkin/CheckinsTab | T test_checkins (3 testy) |
| Pomiary + wykresy + własne mierniki | BE routers/measurements, FE Sparkline | T test_e2e_paths |
| Wiadomości + załączniki + przeczytane | BE routers/messages, FE Messages/Thread | T test_e2e_paths |
| Dokumenty i zdjęcia (walidacja uploadu) | BE storage.py (whitelist, limit), routers/files | T test_uploads (7 testów) |
| Płatności (statusy, przypomnienie, adapter operatora) | BE routers/payments, payments_provider.py | T test_payments (5 testów) |
| Panel trenera (filtry, flagi operacyjne) | BE routers/clients.list_clients, FE Clients | T test_coach_dashboard_flags; E2E |
| Szablony treningów | BE plans (is_template), FE Templates | T (templates listing w seedzie) |
| Historia zmian (pokwitowania) | BE receipts + /coach/clients/{id}/history | T test_plan_change_is_audited |
| Zgody: nadanie/cofnięcie/wersje | BE hos_bridge.ConsentService → hos_engine.ConsentRegistry | T test_consents (4 testy) |
| Eksport danych | BE routers/privacy.export | T test_export_contains_all_sections |
| Usunięcie/anonimizacja | BE routers/privacy.request_deletion | T test_deletion_* (3 testy) |
| Izolacja klientów / IDOR | BE authz.resolve_client_access | T test_isolation (7 testów) |
| Rate limiting logowania | BE security.LoginRateLimiter | T test_login_rate_limit |
| Audyt operacji wysokiej wagi | BE hos_bridge.record_event → SQLiteEventStore (hash chain) | T test_audit_and_hos_bridge (6 testów) |
| Granica UI→Core (ADR-ARCH-003) | wszystkie decyzje w BE; FE bez logiki uprawnień | przegląd kodu FE (api.ts) |
| PWA + mobile-first + polski | FE manifest.webmanifest, sw.js, styles.css | E2E test_pwa_manifest_served; zrzuty ekranu |
| Konfigurowalna marka | BE config (DZIK_BRAND_*), endpoint /api/auth/brand | przegląd |
| Docker Compose + .env.example + CI | Dockerfile, docker-compose.yml, .github/workflows/dzik-os-ci.yml | build lokalny frontendu + testy w CI |
| Dane demo | BE seed.py | uruchomienie + testy `seeded` |
