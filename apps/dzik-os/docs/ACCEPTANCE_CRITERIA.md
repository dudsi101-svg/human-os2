# Kryteria ukończenia (sekcja 16 briefu) — status weryfikacji

Data weryfikacji: 2026-08-17. Metody: `T` = test automatyczny (plik),
`E2E` = test przeglądarkowy Playwright, `M` = weryfikacja manualna/przegląd.

| Kryterium | Status | Dowód |
|---|---|---|
| Trener może założyć i prowadzić klienta | ✅ | T test_e2e_paths (create_client → plan → dieta → harmonogram) |
| Klient może się zalogować | ✅ | T test_auth; E2E |
| Klient widzi swój plan | ✅ | T test_client_sees_current_version; E2E |
| Klient może wykonać trening i uzupełnić wynik | ✅ | T test_workout_logging_against_plan |
| Klient widzi dietę i dokumenty | ✅ | T test_e2e_paths; T test_export (documents) |
| Klient widzi harmonogram | ✅ | T test_e2e_paths (schedule) |
| Klient może wysłać raport | ✅ | T test_checkins |
| Klient może przesłać zdjęcie | ✅ | T test_checkin_with_photo, test_uploads |
| Trener może odpowiedzieć | ✅ | T test_submit_correct_and_review_flow |
| Trener może utworzyć nową wersję planu | ✅ | T test_new_version_preserves_previous |
| Poprzednia wersja pozostaje dostępna | ✅ | T test_new_version_preserves_previous (v1 treść niezmieniona) |
| Klient widzi termin płatności | ✅ | T test_client_sees_payment_status_and_due_date |
| Trener może zmienić status płatności | ✅ | T test_coach_marks_payment_paid… |
| Klient i trener wymieniają wiadomości | ✅ | T test_e2e_paths (kroki 6–7) |
| Klient nie może odczytać danych innego klienta | ✅ | T test_isolation (10 ścieżek → 404) |
| Operacje wysokiego znaczenia audytowane | ✅ | T test_high_significance_operations_produce_events |
| Eksport danych działa | ✅ | T test_export_contains_all_sections |
| Aplikacja działa na telefonie i komputerze | ✅ | E2E viewport 390×844 i 1280×900 |
| Instalacja PWA działa | ✅* | E2E test_pwa_manifest_served (manifest+sw+ikony serwowane); M: instalacja na fizycznym urządzeniu wymaga HTTPS — do potwierdzenia na stagingu |
| Testy przechodzą | ✅ | 50 (backend) + 275 (Core) + 3 (E2E) — wszystkie zielone lokalnie |
| CI jest zielone | ⏳ | workflow dzik-os-ci.yml dodany; pierwszy przebieg nastąpi po pushu na GitHub (kroki identyczne z lokalnie zweryfikowanymi) |
| Dokumentacja pozwala uruchomić projekt | ✅ | README (Szybki start) + DEPLOYMENT.md; polecenia zweryfikowane w tej sesji |

\* Kryterium instalowalności PWA na urządzeniu fizycznym wymaga
wdrożenia z HTTPS (sekcja DEPLOYMENT). Wszystkie techniczne warunki
instalowalności (manifest, ikony 192/512 + maskable, service worker,
display standalone) są spełnione i serwowane.
