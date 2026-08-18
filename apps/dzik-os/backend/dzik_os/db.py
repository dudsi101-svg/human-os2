from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def _make_engine(url: str):
    if url.startswith("sqlite"):
        eng = create_engine(url, connect_args={"check_same_thread": False})

        # SQLite domyślnie NIE egzekwuje kluczy obcych — trzeba go o to
        # poprosić na każdym połączeniu z osobna. Bez tego baza przyjmuje
        # wiersze wskazujące na nieistniejące rekordy, a błąd ujawnia się
        # dopiero na PostgreSQL, czyli przy wdrożeniu produkcyjnym
        # (audyt 18.08.2026: zakładanie konta klienta przez trenera
        # wywracało się na PG, przechodząc na SQLite — patrz R-18).
        @event.listens_for(eng, "connect")
        def _wymus_klucze_obce(dbapi_connection, _record):
            cur = dbapi_connection.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        return eng
    return create_engine(url, pool_pre_ping=True)


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# Migracje: rejestr wersji schematu. Świeża baza dostaje pełny schemat z
# metadanych ORM i stempel wszystkich wersji; istniejąca baza wykonuje
# wyłącznie brakujące wpisy MIGRATIONS w kolejności numerów
# (ADR-DZIK-001 §Migracje).
MIGRATIONS: list[tuple[int, str, list[str]]] = [
    (1, "initial schema (created from ORM metadata)", []),
    (2, "forced password change + consent confirmation", [
        "ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE consents ADD COLUMN confirmed_at VARCHAR(40)",
    ]),
    (3, "monitoring: schedule adherence, observations, daily nutrition log", [
        """
        CREATE TABLE IF NOT EXISTS schedule_completions (
            id VARCHAR(40) PRIMARY KEY,
            schedule_item_id VARCHAR(40) NOT NULL REFERENCES schedule_items(id),
            client_id VARCHAR(40) NOT NULL REFERENCES users(id),
            completed_on VARCHAR(40) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'DONE',
            note TEXT,
            created_by VARCHAR(40) NOT NULL,
            created_at VARCHAR(40) NOT NULL,
            UNIQUE(schedule_item_id, completed_on)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_schedule_completions_item "
            "ON schedule_completions(schedule_item_id)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_schedule_completions_client "
            "ON schedule_completions(client_id)"
        ),
        """
        CREATE TABLE IF NOT EXISTS observations (
            id VARCHAR(40) PRIMARY KEY,
            client_id VARCHAR(40) NOT NULL REFERENCES users(id),
            occurred_on VARCHAR(40) NOT NULL,
            schedule_item_id VARCHAR(40) REFERENCES schedule_items(id),
            category VARCHAR(30) NOT NULL,
            severity VARCHAR(20) NOT NULL DEFAULT 'INFO',
            text TEXT NOT NULL,
            created_by VARCHAR(40) NOT NULL,
            created_at VARCHAR(40) NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_observations_client ON observations(client_id)",
        """
        CREATE TABLE IF NOT EXISTS daily_nutrition_logs (
            id VARCHAR(40) PRIMARY KEY,
            client_id VARCHAR(40) NOT NULL REFERENCES users(id),
            logged_on VARCHAR(40) NOT NULL,
            kcal INTEGER,
            protein_g INTEGER,
            fat_g INTEGER,
            carbs_g INTEGER,
            water_l FLOAT,
            note TEXT,
            created_by VARCHAR(40) NOT NULL,
            created_at VARCHAR(40) NOT NULL,
            UNIQUE(client_id, logged_on)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_daily_nutrition_logs_client "
            "ON daily_nutrition_logs(client_id)"
        ),
    ]),
    (4, "knowledge base", [
        """
        CREATE TABLE IF NOT EXISTS knowledge_items (
            id VARCHAR(40) PRIMARY KEY,
            coach_id VARCHAR(40) NOT NULL REFERENCES users(id),
            title VARCHAR(300) NOT NULL,
            category VARCHAR(80) NOT NULL DEFAULT 'Inne',
            body TEXT,
            external_url VARCHAR(500),
            file_id VARCHAR(40) REFERENCES files(id),
            pinned BOOLEAN NOT NULL DEFAULT false,
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
            created_by VARCHAR(40) NOT NULL,
            created_at VARCHAR(40) NOT NULL,
            updated_at VARCHAR(40) NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_knowledge_items_coach ON knowledge_items(coach_id)",
    ]),
    (5, "exercise + food product catalog, checkin rating", [
        "ALTER TABLE weekly_checkins ADD COLUMN rating INTEGER",
        """
        CREATE TABLE IF NOT EXISTS exercises (
            id VARCHAR(40) PRIMARY KEY,
            coach_id VARCHAR(40) NOT NULL REFERENCES users(id),
            name VARCHAR(300) NOT NULL,
            muscle_group VARCHAR(30) NOT NULL,
            how_to TEXT NOT NULL,
            benefit TEXT,
            equipment VARCHAR(200),
            video_url VARCHAR(500),
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
            created_by VARCHAR(40) NOT NULL,
            created_at VARCHAR(40) NOT NULL,
            updated_at VARCHAR(40) NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_exercises_coach ON exercises(coach_id)",
        """
        CREATE TABLE IF NOT EXISTS food_products (
            id VARCHAR(40) PRIMARY KEY,
            coach_id VARCHAR(40) NOT NULL REFERENCES users(id),
            name VARCHAR(300) NOT NULL,
            category VARCHAR(80) NOT NULL DEFAULT 'Inne',
            kcal_100g FLOAT NOT NULL,
            protein_100g FLOAT NOT NULL,
            fat_100g FLOAT NOT NULL,
            carbs_100g FLOAT NOT NULL,
            default_portion_g FLOAT,
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
            created_by VARCHAR(40) NOT NULL,
            created_at VARCHAR(40) NOT NULL,
            updated_at VARCHAR(40) NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_food_products_coach ON food_products(coach_id)",
    ]),
    (6, "web push subscriptions", [
        """
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id VARCHAR(40) PRIMARY KEY,
            user_id VARCHAR(40) NOT NULL REFERENCES users(id),
            endpoint VARCHAR(1000) NOT NULL UNIQUE,
            p256dh VARCHAR(200) NOT NULL,
            auth VARCHAR(100) NOT NULL,
            created_at VARCHAR(40) NOT NULL
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_push_subscriptions_user "
            "ON push_subscriptions(user_id)"
        ),
    ]),
    (7, "structured workout sets", [
        "ALTER TABLE workout_entries ADD COLUMN sets_json TEXT",
    ]),
    (8, "consultation slots", [
        """
        CREATE TABLE IF NOT EXISTS consult_slots (
            id VARCHAR(40) PRIMARY KEY,
            coach_id VARCHAR(40) NOT NULL REFERENCES users(id),
            starts_at VARCHAR(20) NOT NULL,
            duration_min INTEGER NOT NULL DEFAULT 30,
            status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
            client_id VARCHAR(40) REFERENCES users(id),
            booked_at VARCHAR(40),
            created_at VARCHAR(40) NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_consult_slots_coach ON consult_slots(coach_id)",
    ]),
    (9, "session security: last used timestamp", [
        "ALTER TABLE auth_sessions ADD COLUMN last_used_at VARCHAR(40)",
    ]),
    (10, "granular consent categories (RODO)", [
        # Kategoria z consent_catalog; NULL = historyczna zgoda parasolowa
        # coaching/health_data (interpretacja: ConsentService._hydrate).
        "ALTER TABLE consents ADD COLUMN category VARCHAR(40)",
        "ALTER TABLE consents ADD COLUMN legal_basis VARCHAR(120)",
        "ALTER TABLE consents ADD COLUMN source VARCHAR(40)",
        "ALTER TABLE consents ADD COLUMN denied_at VARCHAR(40)",
    ]),
    (11, "invitations, password reset, TOTP MFA", [
        # MFA (TOTP) na koncie użytkownika; sekret nigdy nie opuszcza
        # backendu poza jednorazowym zwrotem przy konfiguracji.
        "ALTER TABLE users ADD COLUMN totp_secret VARCHAR(64)",
        "ALTER TABLE users ADD COLUMN totp_confirmed_at VARCHAR(40)",
        "ALTER TABLE users ADD COLUMN totp_last_counter INTEGER",
        """
        CREATE TABLE IF NOT EXISTS client_invitations (
            id VARCHAR(40) PRIMARY KEY,
            coach_id VARCHAR(40) NOT NULL REFERENCES users(id),
            client_id VARCHAR(40) NOT NULL REFERENCES users(id),
            email VARCHAR(255) NOT NULL,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            created_at VARCHAR(40) NOT NULL,
            expires_at VARCHAR(40) NOT NULL,
            used_at VARCHAR(40),
            cancelled_at VARCHAR(40)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_client_invitations_coach "
            "ON client_invitations(coach_id)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_client_invitations_client "
            "ON client_invitations(client_id)"
        ),
        """
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id VARCHAR(40) PRIMARY KEY,
            user_id VARCHAR(40) NOT NULL REFERENCES users(id),
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            created_at VARCHAR(40) NOT NULL,
            expires_at VARCHAR(40) NOT NULL,
            used_at VARCHAR(40)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_user "
            "ON password_reset_tokens(user_id)"
        ),
        """
        CREATE TABLE IF NOT EXISTS mfa_recovery_codes (
            id VARCHAR(40) PRIMARY KEY,
            user_id VARCHAR(40) NOT NULL REFERENCES users(id),
            code_hash VARCHAR(64) NOT NULL,
            created_at VARCHAR(40) NOT NULL,
            used_at VARCHAR(40)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_mfa_recovery_codes_user "
            "ON mfa_recovery_codes(user_id)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_mfa_recovery_codes_hash "
            "ON mfa_recovery_codes(code_hash)"
        ),
        """
        CREATE TABLE IF NOT EXISTS mfa_challenges (
            id VARCHAR(40) PRIMARY KEY,
            user_id VARCHAR(40) NOT NULL REFERENCES users(id),
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            created_at VARCHAR(40) NOT NULL,
            expires_at VARCHAR(40) NOT NULL,
            used_at VARCHAR(40)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_mfa_challenges_user "
            "ON mfa_challenges(user_id)"
        ),
    ]),
    (12, "checkin data quality: partial photos, pose/order, idempotency keys", [
        # Zadeklarowana liczba zdjęć raportu — raport z mniejszą liczbą
        # zapisanych zdjęć jest jawnie CZĘŚCIOWY (do dokończenia), a nie
        # cicho „wysłany". NULL = raport sprzed migracji / bez deklaracji.
        "ALTER TABLE weekly_checkins ADD COLUMN photos_expected INTEGER",
        # Typ ujęcia (PRZOD/BOK/TYL/INNE) i kolejność zdjęć wybrana przez
        # klienta przed wysyłką. NULL = zdjęcia historyczne.
        "ALTER TABLE progress_photos ADD COLUMN pose VARCHAR(20)",
        "ALTER TABLE progress_photos ADD COLUMN position INTEGER",
        # Klucze idempotencji operacji zapisu: powtórka tego samego żądania
        # (double-click, retry po utracie odpowiedzi) zwraca zapisany wynik
        # zamiast tworzyć duplikat/rewizję.
        """
        CREATE TABLE IF NOT EXISTS idempotency_keys (
            id VARCHAR(40) PRIMARY KEY,
            user_id VARCHAR(40) NOT NULL REFERENCES users(id),
            operation VARCHAR(80) NOT NULL,
            idem_key VARCHAR(80) NOT NULL,
            request_hash VARCHAR(64) NOT NULL,
            response_json TEXT NOT NULL,
            created_at VARCHAR(40) NOT NULL,
            UNIQUE(user_id, operation, idem_key)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_idempotency_keys_user "
            "ON idempotency_keys(user_id)"
        ),
    ]),
    (13, "messages realtime: delivery/read status, client dedup id", [
        # Status doręczenia: dostarczona (urządzenie odbiorcy odebrało) /
        # przeczytana (read_at istniał od v1). Model statusów i plan
        # wycofania: docs/WIADOMOSCI.md.
        "ALTER TABLE messages ADD COLUMN delivered_at VARCHAR(40)",
        # Deduplikacja ponowień z urządzenia nadawcy (utrata sieci):
        # identyfikator kliencki, unikalny per wątek+autor.
        "ALTER TABLE messages ADD COLUMN client_msg_id VARCHAR(64)",
        (
            "CREATE INDEX IF NOT EXISTS ix_messages_thread_created "
            "ON messages(thread_id, created_at, id)"
        ),
        (
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_messages_thread_author_client_msg "
            "ON messages(thread_id, author_id, client_msg_id) "
            "WHERE client_msg_id IS NOT NULL"
        ),
    ]),
    # Nr 14 zarezerwowany dla równoległej rundy.
    (14, "unified notifications: model, preferences, settings, user timezone", [
        # Strefa czasowa per użytkownik (IANA); NULL = strefa aplikacji
        # (DZIK_TZ) — czytana przez dates.tz_for_user().
        "ALTER TABLE users ADD COLUMN timezone VARCHAR(64)",
        # Wspólny model powiadomienia (wszystkie kanały). Klucz idempotencji
        # dedup_key w bazie zastępuje dedup `_sent` w pamięci procesu —
        # restart maszyny nie duplikuje ani nie gubi przypomnień.
        # Model i plan wycofania: docs/POWIADOMIENIA.md.
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id VARCHAR(40) PRIMARY KEY,
            user_id VARCHAR(40) NOT NULL REFERENCES users(id),
            category VARCHAR(20) NOT NULL,
            title VARCHAR(200) NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            url VARCHAR(300) NOT NULL DEFAULT '/',
            status VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED',
            suppressed_reason VARCHAR(40),
            channels VARCHAR(60),
            dedup_key VARCHAR(120) NOT NULL,
            source VARCHAR(120),
            timezone VARCHAR(64),
            scheduled_at VARCHAR(40),
            created_at VARCHAR(40) NOT NULL,
            sent_at VARCHAR(40),
            read_at VARCHAR(40),
            UNIQUE(user_id, dedup_key)
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id)",
        (
            "CREATE INDEX IF NOT EXISTS ix_notifications_user_status "
            "ON notifications(user_id, status)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_notifications_status_scheduled "
            "ON notifications(status, scheduled_at)"
        ),
        "CREATE INDEX IF NOT EXISTS ix_notifications_source ON notifications(source)",
        # Preferencje per kategoria × kanał; brak wiersza = domyślne
        # (PUSH/CENTER włączone, EMAIL wyłączony).
        """
        CREATE TABLE IF NOT EXISTS notification_preferences (
            id VARCHAR(40) PRIMARY KEY,
            user_id VARCHAR(40) NOT NULL REFERENCES users(id),
            category VARCHAR(20) NOT NULL,
            channel VARCHAR(10) NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT true,
            updated_at VARCHAR(40) NOT NULL,
            UNIQUE(user_id, category, channel)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_notification_preferences_user_id "
            "ON notification_preferences(user_id)"
        ),
        # Ciche godziny, dni aktywne, częstotliwość raportu.
        """
        CREATE TABLE IF NOT EXISTS notification_settings (
            id VARCHAR(40) PRIMARY KEY,
            user_id VARCHAR(40) NOT NULL UNIQUE REFERENCES users(id),
            quiet_hours_start VARCHAR(5),
            quiet_hours_end VARCHAR(5),
            active_days VARCHAR(30) NOT NULL DEFAULT '1,2,3,4,5,6,7',
            raport_frequency VARCHAR(10) NOT NULL DEFAULT 'DAILY',
            updated_at VARCHAR(40) NOT NULL
        )
        """,
    ]),
    (15, "płatności: transakcje, korekty, historia statusów, zdarzenia operatora", [
        # Kto oznaczył było (marked_by), od teraz też KIEDY (marked_at).
        # Istniejące wiersze: moment oznaczenia = paid_at (jedyny znany).
        # Statusy starych rekordów (PENDING/PAID/OVERDUE/CANCELLED) są
        # podzbiorem nowej maszyny stanów — NIC nie jest przepisywane
        # (mapowanie tożsamościowe, zero utraty danych); docs/PLATNOSCI.md.
        "ALTER TABLE payment_records ADD COLUMN marked_at VARCHAR(40)",
        "UPDATE payment_records SET marked_at = paid_at WHERE paid_at IS NOT NULL",
        """
        CREATE TABLE IF NOT EXISTS payment_transactions (
            id VARCHAR(40) PRIMARY KEY,
            record_id VARCHAR(40) NOT NULL REFERENCES payment_records(id),
            kind VARCHAR(30) NOT NULL,
            amount_cents INTEGER NOT NULL,
            currency VARCHAR(10) NOT NULL DEFAULT 'PLN',
            document_ref VARCHAR(120),
            note TEXT,
            reverses_transaction_id VARCHAR(40) REFERENCES payment_transactions(id),
            provider VARCHAR(40),
            provider_event_id VARCHAR(120),
            created_by VARCHAR(40) NOT NULL,
            created_at VARCHAR(40) NOT NULL
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_payment_transactions_record "
            "ON payment_transactions(record_id)"
        ),
        """
        CREATE TABLE IF NOT EXISTS payment_status_changes (
            id VARCHAR(40) PRIMARY KEY,
            record_id VARCHAR(40) NOT NULL REFERENCES payment_records(id),
            from_status VARCHAR(30) NOT NULL,
            to_status VARCHAR(30) NOT NULL,
            reason TEXT,
            transaction_id VARCHAR(40),
            changed_by VARCHAR(40) NOT NULL,
            changed_at VARCHAR(40) NOT NULL
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_payment_status_changes_record "
            "ON payment_status_changes(record_id)"
        ),
        """
        CREATE TABLE IF NOT EXISTS payment_attempts (
            id VARCHAR(40) PRIMARY KEY,
            record_id VARCHAR(40) NOT NULL REFERENCES payment_records(id),
            provider VARCHAR(40) NOT NULL,
            provider_session_id VARCHAR(120),
            status VARCHAR(20) NOT NULL DEFAULT 'STARTED',
            created_at VARCHAR(40) NOT NULL,
            updated_at VARCHAR(40) NOT NULL
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_payment_attempts_record "
            "ON payment_attempts(record_id)"
        ),
        """
        CREATE TABLE IF NOT EXISTS payment_provider_events (
            id VARCHAR(40) PRIMARY KEY,
            provider VARCHAR(40) NOT NULL,
            event_id VARCHAR(120) NOT NULL,
            event_type VARCHAR(60) NOT NULL,
            record_id VARCHAR(40),
            payload_hash VARCHAR(64) NOT NULL,
            occurred_at VARCHAR(40),
            received_at VARCHAR(40) NOT NULL,
            outcome VARCHAR(30) NOT NULL,
            note TEXT,
            UNIQUE(provider, event_id)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_payment_provider_events_record "
            "ON payment_provider_events(record_id)"
        ),
    ]),
    (16, "challenges: wspólne wyzwania (prywatne, tylko-zaproszeni)", [
        # Model i zasady prywatności: docs/WYZWANIA.md (w tym plan
        # wycofania tej migracji). Wyłącznie NOWE tabele — zero ALTER-ów
        # istniejących (czysto addytywna).
        """
        CREATE TABLE IF NOT EXISTS challenges (
            id VARCHAR(40) PRIMARY KEY,
            kind VARCHAR(20) NOT NULL DEFAULT 'GROUP',
            organizer_id VARCHAR(40) NOT NULL REFERENCES users(id),
            title VARCHAR(300) NOT NULL,
            description TEXT,
            unit VARCHAR(20) NOT NULL,
            goal_value FLOAT,
            starts_on VARCHAR(10) NOT NULL,
            ends_on VARCHAR(10) NOT NULL,
            timezone VARCHAR(50) NOT NULL,
            visibility VARCHAR(20) NOT NULL DEFAULT 'INVITE_ONLY',
            status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
            max_entries_per_day INTEGER NOT NULL DEFAULT 5,
            aggregates_adjusted BOOLEAN NOT NULL DEFAULT false,
            created_at VARCHAR(40) NOT NULL,
            updated_at VARCHAR(40) NOT NULL,
            finished_at VARCHAR(40),
            cancelled_at VARCHAR(40)
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_challenges_organizer ON challenges(organizer_id)",
        """
        CREATE TABLE IF NOT EXISTS challenge_participants (
            id VARCHAR(40) PRIMARY KEY,
            challenge_id VARCHAR(40) NOT NULL REFERENCES challenges(id),
            user_id VARCHAR(40) NOT NULL REFERENCES users(id),
            status VARCHAR(20) NOT NULL DEFAULT 'INVITED',
            alias VARCHAR(80),
            share_result BOOLEAN NOT NULL DEFAULT false,
            ranking_opt_in BOOLEAN NOT NULL DEFAULT false,
            auto_count_workouts BOOLEAN NOT NULL DEFAULT false,
            invited_by VARCHAR(40),
            invited_at VARCHAR(40),
            joined_at VARCHAR(40),
            declined_at VARCHAR(40),
            left_at VARCHAR(40),
            removed_at VARCHAR(40),
            withdrawn_at VARCHAR(40),
            created_at VARCHAR(40) NOT NULL,
            UNIQUE(challenge_id, user_id)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_challenge_participants_challenge "
            "ON challenge_participants(challenge_id)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_challenge_participants_user "
            "ON challenge_participants(user_id)"
        ),
        """
        CREATE TABLE IF NOT EXISTS challenge_entries (
            id VARCHAR(40) PRIMARY KEY,
            challenge_id VARCHAR(40) NOT NULL REFERENCES challenges(id),
            participant_id VARCHAR(40) NOT NULL REFERENCES challenge_participants(id),
            entry_date VARCHAR(10) NOT NULL,
            value FLOAT NOT NULL,
            note VARCHAR(200),
            source VARCHAR(20) NOT NULL DEFAULT 'MANUAL',
            workout_session_id VARCHAR(40),
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
            corrects_entry_id VARCHAR(40),
            client_entry_id VARCHAR(64),
            created_at VARCHAR(40) NOT NULL
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_challenge_entries_participant "
            "ON challenge_entries(participant_id, entry_date)"
        ),
        (
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_challenge_entries_workout "
            "ON challenge_entries(challenge_id, workout_session_id) "
            "WHERE workout_session_id IS NOT NULL"
        ),
        (
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_challenge_entries_client_id "
            "ON challenge_entries(participant_id, client_entry_id) "
            "WHERE client_entry_id IS NOT NULL"
        ),
        """
        CREATE TABLE IF NOT EXISTS challenge_blocks (
            id VARCHAR(40) PRIMARY KEY,
            challenge_id VARCHAR(40) NOT NULL REFERENCES challenges(id),
            blocker_id VARCHAR(40) NOT NULL REFERENCES users(id),
            blocked_id VARCHAR(40) NOT NULL REFERENCES users(id),
            created_at VARCHAR(40) NOT NULL,
            UNIQUE(challenge_id, blocker_id, blocked_id)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_challenge_blocks_challenge "
            "ON challenge_blocks(challenge_id)"
        ),
        """
        CREATE TABLE IF NOT EXISTS challenge_reports (
            id VARCHAR(40) PRIMARY KEY,
            challenge_id VARCHAR(40) NOT NULL REFERENCES challenges(id),
            reporter_id VARCHAR(40) NOT NULL REFERENCES users(id),
            reported_user_id VARCHAR(40) NOT NULL REFERENCES users(id),
            reason TEXT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
            resolution VARCHAR(20),
            resolution_note TEXT,
            resolved_by VARCHAR(40),
            resolved_at VARCHAR(40),
            created_at VARCHAR(40) NOT NULL
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_challenge_reports_challenge "
            "ON challenge_reports(challenge_id)"
        ),
    ]),
    (17, "konwersacyjny onboarding: rozmowa, odpowiedzi, podsumowanie, koszty AI", [
        # Model, prompty, zabezpieczenia i plan wycofania tej migracji:
        # docs/ONBOARDING_AI.md. Wyłącznie NOWE tabele — zero ALTER-ów
        # istniejących (czysto addytywna, stara ankieta `Intake` działa
        # dalej bez zmian jako tryb formularza).
        """
        CREATE TABLE IF NOT EXISTS onboarding_sessions (
            id VARCHAR(40) PRIMARY KEY,
            client_id VARCHAR(40) NOT NULL REFERENCES users(id),
            status VARCHAR(20) NOT NULL DEFAULT 'IN_PROGRESS',
            summary_mode VARCHAR(20) NOT NULL DEFAULT 'FORM',
            summary_mode_reason TEXT,
            current_step_id VARCHAR(40),
            safety_flag BOOLEAN NOT NULL DEFAULT false,
            safety_flag_at VARCHAR(40),
            ai_rejections INTEGER NOT NULL DEFAULT 0,
            started_at VARCHAR(40) NOT NULL,
            updated_at VARCHAR(40) NOT NULL,
            summary_at VARCHAR(40),
            client_approved_at VARCHAR(40),
            applied_at VARCHAR(40),
            coach_approved_at VARCHAR(40),
            coach_approved_by VARCHAR(40),
            abandoned_at VARCHAR(40)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_onboarding_sessions_client "
            "ON onboarding_sessions(client_id)"
        ),
        # Odpowiedzi append-only: poprawka klienta to NOWA wersja, stara
        # zostaje jako historia (sprzeczności są widoczne, nie nadpisane).
        """
        CREATE TABLE IF NOT EXISTS onboarding_answers (
            id VARCHAR(40) PRIMARY KEY,
            session_id VARCHAR(40) NOT NULL REFERENCES onboarding_sessions(id),
            step_id VARCHAR(40) NOT NULL,
            topic VARCHAR(80) NOT NULL,
            value TEXT NOT NULL DEFAULT '',
            skipped BOOLEAN NOT NULL DEFAULT false,
            sensitive BOOLEAN NOT NULL DEFAULT false,
            safety_flagged BOOLEAN NOT NULL DEFAULT false,
            safety_signals TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            is_current BOOLEAN NOT NULL DEFAULT true,
            created_at VARCHAR(40) NOT NULL,
            UNIQUE(session_id, step_id, version)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_onboarding_answers_session "
            "ON onboarding_answers(session_id)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_onboarding_answers_current "
            "ON onboarding_answers(session_id, step_id, is_current)"
        ),
        """
        CREATE TABLE IF NOT EXISTS onboarding_summary_items (
            id VARCHAR(40) PRIMARY KEY,
            session_id VARCHAR(40) NOT NULL REFERENCES onboarding_sessions(id),
            field_key VARCHAR(80) NOT NULL,
            value TEXT NOT NULL DEFAULT '',
            step_id VARCHAR(40),
            origin VARCHAR(20) NOT NULL DEFAULT 'DETERMINISTIC',
            confidence VARCHAR(10) NOT NULL DEFAULT 'HIGH',
            needs_confirmation BOOLEAN NOT NULL DEFAULT false,
            sensitive BOOLEAN NOT NULL DEFAULT false,
            coach_confirmed BOOLEAN NOT NULL DEFAULT false,
            version INTEGER NOT NULL DEFAULT 1,
            is_current BOOLEAN NOT NULL DEFAULT true,
            created_at VARCHAR(40) NOT NULL,
            UNIQUE(session_id, field_key, version)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_onboarding_summary_session "
            "ON onboarding_summary_items(session_id)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_onboarding_summary_current "
            "ON onboarding_summary_items(session_id, field_key, is_current)"
        ),
        # Kontrola kosztów: same liczby (wywołania, tokeny), zero treści.
        """
        CREATE TABLE IF NOT EXISTS ai_usage_counters (
            id VARCHAR(40) PRIMARY KEY,
            user_id VARCHAR(40) NOT NULL REFERENCES users(id),
            usage_date VARCHAR(10) NOT NULL,
            feature VARCHAR(40) NOT NULL,
            calls INTEGER NOT NULL DEFAULT 0,
            tokens_in INTEGER NOT NULL DEFAULT 0,
            tokens_out INTEGER NOT NULL DEFAULT 0,
            updated_at VARCHAR(40) NOT NULL,
            UNIQUE(user_id, usage_date, feature)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_ai_usage_counters_user "
            "ON ai_usage_counters(user_id)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_ai_usage_counters_date "
            "ON ai_usage_counters(usage_date)"
        ),
    ]),
    (18, "baza produktów: błonnik, jednostka sztukowa, źródło i uwagi", [
        # Czysto addytywna: same nowe kolumny NULLable na istniejącej tabeli.
        # Produkty sprzed migracji działają bez zmian (NULL = brak danych,
        # nigdy 0). Plan wycofania: docs/BAZA_PRODUKTOW.md.
        "ALTER TABLE food_products ADD COLUMN fiber_100g FLOAT",
        "ALTER TABLE food_products ADD COLUMN unit_name VARCHAR(60)",
        "ALTER TABLE food_products ADD COLUMN unit_grams FLOAT",
        "ALTER TABLE food_products ADD COLUMN source VARCHAR(200)",
        "ALTER TABLE food_products ADD COLUMN note VARCHAR(300)",
    ]),
    (19, "baza ćwiczeń: rozszerzony opis techniki i mapa mięśni", [
        # Wyłącznie ALTER-y addytywne, wszystkie kolumny NULLable —
        # ćwiczenia sprzed rozbudowy działają bez żadnego backfillu
        # (how_to/benefit pozostają polami zgodności wstecznej).
        "ALTER TABLE exercises ADD COLUMN muscles_primary TEXT",
        "ALTER TABLE exercises ADD COLUMN muscles_secondary TEXT",
        "ALTER TABLE exercises ADD COLUMN level VARCHAR(30)",
        "ALTER TABLE exercises ADD COLUMN pattern VARCHAR(30)",
        "ALTER TABLE exercises ADD COLUMN steps_json TEXT",
        "ALTER TABLE exercises ADD COLUMN mistakes_json TEXT",
        "ALTER TABLE exercises ADD COLUMN cues_json TEXT",
        "ALTER TABLE exercises ADD COLUMN safety TEXT",
        "ALTER TABLE exercises ADD COLUMN easier TEXT",
        "ALTER TABLE exercises ADD COLUMN harder TEXT",
        "ALTER TABLE exercises ADD COLUMN tempo_hint VARCHAR(200)",
        "ALTER TABLE exercises ADD COLUMN breathing VARCHAR(400)",
    ]),
    (20, "przepisywanie tekstu ze zdjęcia (OCR): zadania, tekst przy dokumencie, proweniencja produktu", [
        # Wyłącznie addytywne: jedna nowa tabela + kolumny NULLable na
        # istniejących. Dane sprzed migracji działają bez backfillu, a
        # wycofanie sprowadza się do usunięcia tabeli i kolumn
        # (plan wycofania: docs/OCR.md §migracja nr 20).
        """
        CREATE TABLE IF NOT EXISTS ocr_tasks (
            id VARCHAR(40) PRIMARY KEY,
            owner_user_id VARCHAR(40) NOT NULL REFERENCES users(id),
            created_by VARCHAR(40) NOT NULL,
            file_id VARCHAR(40) NOT NULL REFERENCES files(id),
            purpose VARCHAR(20) NOT NULL,
            document_id VARCHAR(40),
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            engine VARCHAR(20),
            mode_reason TEXT,
            text TEXT,
            proposal_json TEXT,
            error_code VARCHAR(40),
            error TEXT,
            chars INTEGER,
            duration_ms INTEGER,
            approved_at VARCHAR(40),
            result_ref VARCHAR(40),
            created_at VARCHAR(40) NOT NULL,
            started_at VARCHAR(40),
            finished_at VARCHAR(40)
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_ocr_tasks_owner ON ocr_tasks(owner_user_id)",
        "CREATE INDEX IF NOT EXISTS ix_ocr_tasks_created_by ON ocr_tasks(created_by)",
        "CREATE INDEX IF NOT EXISTS ix_ocr_tasks_status ON ocr_tasks(status)",
        "ALTER TABLE documents ADD COLUMN ocr_text TEXT",
        "ALTER TABLE documents ADD COLUMN ocr_engine VARCHAR(20)",
        "ALTER TABLE documents ADD COLUMN ocr_at VARCHAR(40)",
        "ALTER TABLE food_products ADD COLUMN origin_kind VARCHAR(20)",
        "ALTER TABLE food_products ADD COLUMN origin_file_id VARCHAR(40)",
        "ALTER TABLE food_products ADD COLUMN origin_engine VARCHAR(20)",
    ]),
    # Numer 21 nigdy nie istniał — kolejna migracja dostała od razu 22.
    # Luki w numeracji nie wolno zostawić otwartej: baza stosuje wyłącznie
    # BRAKUJĄCE numery, więc gdyby ktoś później dopisał migrację 21, na
    # bazach mających już 22 wykonałaby się PO niej, łamiąc kolejność.
    # Zamknięcie luki pustym wpisem jest bezpieczne dla obu przypadków:
    # istniejąca baza tylko stempluje wersję (zero instrukcji), a nowa
    # dostaje schemat z metadanych ORM jak zawsze.
    #
    # Stąd zasada na przyszłość: NOWĄ migrację bierz zawsze od największego
    # istniejącego numeru, nigdy z luki w środku numeracji.
    (21, "numer niewykorzystany (luka domknięta, brak zmian schematu)", []),
    (22, "baza ćwiczeń: proweniencja wpisu (skąd wzięły się dane)", [
        # Czysto addytywna: dwie nowe kolumny NULLable na istniejącej
        # tabeli. NULL znaczy „ćwiczenie sprzed tej migracji, nie wiemy” —
        # świadomie NIE robimy backfillu na MANUAL, bo to byłoby wpisanie
        # do bazy faktu, którego nikt nie stwierdził.
        # Plan wycofania: docs/BAZA_CWICZEN.md §migracja nr 22.
        "ALTER TABLE exercises ADD COLUMN source_kind VARCHAR(20)",
        "ALTER TABLE exercises ADD COLUMN source_engine VARCHAR(20)",
    ]),
    (23, "asystent trenera: wspólna tabela zadań (rejestr zadań, propozycje)", [
        # Wyłącznie addytywna: JEDNA nowa tabela, zero ALTER-ów na
        # istniejących. Wszystkie kolumny poza kluczami są NULLable, więc
        # baza sprzed migracji działa bez backfillu, a wycofanie sprowadza
        # się do `DROP TABLE assistant_tasks` (plan wycofania:
        # docs/ASYSTENT_TRENERA.md §migracja nr 23).
        """
        CREATE TABLE IF NOT EXISTS assistant_tasks (
            id VARCHAR(40) PRIMARY KEY,
            task_key VARCHAR(40) NOT NULL,
            owner_user_id VARCHAR(40) NOT NULL REFERENCES users(id),
            client_id VARCHAR(40),
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            input_json TEXT,
            result_json TEXT,
            engine VARCHAR(20),
            mode_reason TEXT,
            error_code VARCHAR(40),
            error TEXT,
            idem_key VARCHAR(80),
            duration_ms INTEGER,
            approved_at VARCHAR(40),
            provenance_json TEXT,
            result_ref VARCHAR(40),
            created_at VARCHAR(40) NOT NULL,
            started_at VARCHAR(40),
            finished_at VARCHAR(40)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_assistant_tasks_owner "
            "ON assistant_tasks(owner_user_id)"
        ),
        "CREATE INDEX IF NOT EXISTS ix_assistant_tasks_key ON assistant_tasks(task_key)",
        "CREATE INDEX IF NOT EXISTS ix_assistant_tasks_status ON assistant_tasks(status)",
    ]),
    (24, ("baza ćwiczeń: import biblioteki trenera — nazwa angielska, tagi, "
          "źródło pozycji i notatka o szablonowym opisie"), [
        # Czysto addytywna: cztery kolumny NULLable na istniejącej tabeli,
        # żadnego backfillu. NULL wszędzie znaczy „nie wiemy / nie dotyczy”,
        # więc ćwiczenia sprzed tej migracji działają bez zmian.
        # Plan wycofania: docs/BAZA_CWICZEN.md §migracja nr 24.
        "ALTER TABLE exercises ADD COLUMN name_en VARCHAR(300)",
        "ALTER TABLE exercises ADD COLUMN tags_json TEXT",
        "ALTER TABLE exercises ADD COLUMN source_ref VARCHAR(200)",
        "ALTER TABLE exercises ADD COLUMN review_reason VARCHAR(300)",
    ]),
    (25, "punkty przywracania importu z pliku (cofnij import)", [
        # Wyłącznie addytywna: JEDNA nowa tabela, zero ALTER-ów na
        # istniejących. Baza sprzed migracji działa bez backfillu (brak
        # migawek = po prostu nie ma czego cofać), a wycofanie sprowadza
        # się do `DROP TABLE import_snapshots`.
        # Plan wycofania: docs/IMPORT_BAZ.md §8.
        """
        CREATE TABLE IF NOT EXISTS import_snapshots (
            id VARCHAR(40) PRIMARY KEY,
            coach_id VARCHAR(40) NOT NULL REFERENCES users(id),
            kind VARCHAR(20) NOT NULL,
            source_ref VARCHAR(200) NOT NULL,
            mode VARCHAR(20) NOT NULL,
            rows INTEGER NOT NULL DEFAULT 0,
            payload_json TEXT NOT NULL,
            created_at VARCHAR(40) NOT NULL,
            restored_at VARCHAR(40)
        )
        """,
        (
            "CREATE INDEX IF NOT EXISTS ix_import_snapshots_coach "
            "ON import_snapshots(coach_id)"
        ),
    ]),
]


def run_migrations(target_engine=None) -> list[int]:
    eng = target_engine or engine
    applied: list[int] = []
    with eng.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version INTEGER PRIMARY KEY, "
                "description TEXT NOT NULL, "
                "applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
        )
        done = {row[0] for row in conn.execute(text("SELECT version FROM schema_migrations"))}

    def stamp(version: int, description: str) -> None:
        with eng.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO schema_migrations(version, description) "
                    "VALUES (:v, :d)"
                ),
                {"v": version, "d": description},
            )
        applied.append(version)

    if 1 not in done:
        # Świeża baza: ORM tworzy już docelowy schemat (ze wszystkimi
        # kolumnami), więc DDL późniejszych migracji nie jest wykonywany —
        # tylko stemplowany.
        #
        # Import modeli MUSI być tutaj, a nie po stronie wywołującego.
        # `Base.metadata` jest puste, dopóki moduł `models` nie zostanie
        # zaimportowany; bez tego `create_all` nie tworzy ANI JEDNEJ tabeli,
        # a mimo to wszystkie migracje zostają ostemplowane jako wykonane.
        # Efektem jest baza pusta, lecz „zmigrowana", która nigdy się już
        # nie naprawi — cichy błąd katastrofalny. Dziś każdy realny punkt
        # wejścia importuje modele przypadkiem; ta linia zamienia przypadek
        # w gwarancję. Patrz tests/test_db_migracje.py.
        from . import models  # noqa: F401 - rejestracja tabel w Base.metadata

        Base.metadata.create_all(eng)
        for version, description, _ in MIGRATIONS:
            stamp(version, description)
        return applied

    for version, description, statements in MIGRATIONS:
        if version in done:
            continue
        with eng.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))
        stamp(version, description)
    return applied


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
