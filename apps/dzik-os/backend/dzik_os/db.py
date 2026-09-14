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
    (26, "rozmowy: kolumna flow (rozmowa startowa vs gleboki wywiad)", [
        # Addytywna: sesje głębokiego wywiadu żyją w TEJ SAMEJ tabeli co
        # rozmowa startowa (ten sam mechanizm, drugi scenariusz), a kolumna
        # `flow` je rozróżnia. Istniejące wiersze dostają DEFAULT 'start',
        # więc baza sprzed migracji działa bez backfillu; wycofanie =
        # ignorowanie kolumny (żaden stary kod jej nie czyta).
        (
            "ALTER TABLE onboarding_sessions "
            "ADD COLUMN flow VARCHAR(20) NOT NULL DEFAULT 'start'"
        ),
    ]),
]

MIGRATIONS.append(
    (27, "szablony diety trenera (nutrition_templates)", [
        # Addytywna: nowa tabela, żadna istniejąca ścieżka jej nie czyta.
        (
            "CREATE TABLE IF NOT EXISTS nutrition_templates ("
            " id VARCHAR(40) PRIMARY KEY,"
            " coach_id VARCHAR(40) NOT NULL REFERENCES users(id),"
            " title VARCHAR(300) NOT NULL,"
            " content_json TEXT NOT NULL,"
            " created_at VARCHAR(40) NOT NULL,"
            " updated_at VARCHAR(40) NOT NULL)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_nutrition_templates_coach"
            " ON nutrition_templates (coach_id)"
        ),
    ])
)

MIGRATIONS.append(
    (28, "wiedza: karty, powiazania, slad decyzji, zakladki, odczyty, opinie, ustawienia", [
        # Addytywna: siedem nowych tabel, żadna istniejąca ścieżka ich nie
        # czyta. Wycofanie = flaga DZIK_WIEDZA_V2=false (tabele zostają —
        # ślady decyzji i zakładki nie giną, plik 09 pakietu Wiedza).
        (
            "CREATE TABLE IF NOT EXISTS wiedza_artykuly ("
            " id VARCHAR(40) PRIMARY KEY,"
            " article_id VARCHAR(80) NOT NULL,"
            " revision INTEGER NOT NULL,"
            " status VARCHAR(20) NOT NULL DEFAULT 'draft',"
            " category VARCHAR(20) NOT NULL,"
            " title VARCHAR(300) NOT NULL,"
            " summary TEXT NOT NULL,"
            " exercise_id VARCHAR(80),"
            " tresc_json TEXT NOT NULL,"
            " review_approved BOOLEAN NOT NULL DEFAULT false,"
            " reviewer_id VARCHAR(40),"
            " reviewed_at VARCHAR(40),"
            " next_review_at VARCHAR(40),"
            " zamiennik_id VARCHAR(80),"
            " created_by VARCHAR(40) NOT NULL,"
            " created_at VARCHAR(40) NOT NULL,"
            " updated_at VARCHAR(40) NOT NULL,"
            " UNIQUE (article_id, revision))"
        ),
        "CREATE INDEX IF NOT EXISTS ix_wiedza_artykuly_article_id ON wiedza_artykuly (article_id)",
        "CREATE INDEX IF NOT EXISTS ix_wiedza_artykuly_status ON wiedza_artykuly (status)",
        "CREATE INDEX IF NOT EXISTS ix_wiedza_artykuly_category ON wiedza_artykuly (category)",
        "CREATE INDEX IF NOT EXISTS ix_wiedza_artykuly_exercise_id ON wiedza_artykuly (exercise_id)",
        (
            "CREATE TABLE IF NOT EXISTS wiedza_powiazania ("
            " id VARCHAR(40) PRIMARY KEY,"
            " target_type VARCHAR(60) NOT NULL,"
            " target_key VARCHAR(120) NOT NULL,"
            " article_id VARCHAR(80) NOT NULL,"
            " role VARCHAR(40) NOT NULL,"
            " UNIQUE (target_type, target_key, article_id))"
        ),
        "CREATE INDEX IF NOT EXISTS ix_wiedza_powiazania_target_type ON wiedza_powiazania (target_type)",
        "CREATE INDEX IF NOT EXISTS ix_wiedza_powiazania_target_key ON wiedza_powiazania (target_key)",
        "CREATE INDEX IF NOT EXISTS ix_wiedza_powiazania_article_id ON wiedza_powiazania (article_id)",
        (
            "CREATE TABLE IF NOT EXISTS wiedza_slady ("
            " id VARCHAR(40) PRIMARY KEY,"
            " owner_id VARCHAR(40) NOT NULL REFERENCES users(id),"
            " plan_kind VARCHAR(20) NOT NULL,"
            " plan_id VARCHAR(40) NOT NULL,"
            " plan_revision INTEGER NOT NULL,"
            " target_type VARCHAR(60) NOT NULL,"
            " target_id VARCHAR(200) NOT NULL,"
            " decision_origin VARCHAR(20) NOT NULL,"
            " rule_id VARCHAR(60),"
            " rule_version VARCHAR(20),"
            " data_quality VARCHAR(20) NOT NULL,"
            " facts_json TEXT NOT NULL,"
            " outcome_code VARCHAR(60) NOT NULL,"
            " outcome_value_json TEXT NOT NULL,"
            " reason_note TEXT,"
            " article_ids_json TEXT NOT NULL DEFAULT '[]',"
            " created_at VARCHAR(40) NOT NULL)"
        ),
        "CREATE INDEX IF NOT EXISTS ix_wiedza_slady_owner_id ON wiedza_slady (owner_id)",
        "CREATE INDEX IF NOT EXISTS ix_wiedza_slady_plan_id ON wiedza_slady (plan_id)",
        (
            "CREATE INDEX IF NOT EXISTS ix_wiedza_slady_cel ON wiedza_slady"
            " (owner_id, plan_id, plan_revision, target_type, target_id)"
        ),
        (
            "CREATE TABLE IF NOT EXISTS wiedza_zakladki ("
            " id VARCHAR(40) PRIMARY KEY,"
            " owner_id VARCHAR(40) NOT NULL REFERENCES users(id),"
            " article_id VARCHAR(80) NOT NULL,"
            " created_at VARCHAR(40) NOT NULL,"
            " UNIQUE (owner_id, article_id))"
        ),
        "CREATE INDEX IF NOT EXISTS ix_wiedza_zakladki_owner_id ON wiedza_zakladki (owner_id)",
        (
            "CREATE TABLE IF NOT EXISTS wiedza_odczyty ("
            " id VARCHAR(40) PRIMARY KEY,"
            " owner_id VARCHAR(40) NOT NULL REFERENCES users(id),"
            " article_id VARCHAR(80) NOT NULL,"
            " last_opened_at VARCHAR(40) NOT NULL,"
            " explicitly_completed_at VARCHAR(40),"
            " UNIQUE (owner_id, article_id))"
        ),
        "CREATE INDEX IF NOT EXISTS ix_wiedza_odczyty_owner_id ON wiedza_odczyty (owner_id)",
        (
            "CREATE TABLE IF NOT EXISTS wiedza_opinie ("
            " id VARCHAR(40) PRIMARY KEY,"
            " owner_id VARCHAR(40) NOT NULL REFERENCES users(id),"
            " article_id VARCHAR(80) NOT NULL,"
            " revision INTEGER NOT NULL,"
            " useful BOOLEAN NOT NULL,"
            " note TEXT,"
            " created_at VARCHAR(40) NOT NULL)"
        ),
        "CREATE INDEX IF NOT EXISTS ix_wiedza_opinie_owner_id ON wiedza_opinie (owner_id)",
        (
            "CREATE TABLE IF NOT EXISTS wiedza_ustawienia ("
            " owner_id VARCHAR(40) PRIMARY KEY REFERENCES users(id),"
            " personalizacja BOOLEAN NOT NULL DEFAULT true,"
            " updated_at VARCHAR(40) NOT NULL)"
        ),
    ])
)

MIGRATIONS.append(
    (29, "kulinaria: stan publikacji receptur (kulinaria_receptury)", [
        # Addytywna: jedna tabela; biblioteka receptur pozostaje w pliku
        # pakietu, tu tylko decyzje publikacji trenera.
        (
            "CREATE TABLE IF NOT EXISTS kulinaria_receptury ("
            " id VARCHAR(40) PRIMARY KEY,"
            " recipe_id VARCHAR(80) NOT NULL,"
            " revision INTEGER NOT NULL,"
            " status VARCHAR(20) NOT NULL DEFAULT 'draft',"
            " review_json TEXT NOT NULL DEFAULT '{}',"
            " validated_variants_json TEXT NOT NULL DEFAULT '[]',"
            " updated_by VARCHAR(40) NOT NULL,"
            " updated_at VARCHAR(40) NOT NULL,"
            " UNIQUE (recipe_id, revision))"
        ),
        "CREATE INDEX IF NOT EXISTS ix_kulinaria_receptury_recipe_id ON kulinaria_receptury (recipe_id)",
    ])
)


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

MIGRATIONS.append(
    (30, "panel trenera: szkice planów, zestawy zmian, outbox, pochodzenie kopii", [
        # Addytywna. Wersje planów dostają pochodzenie kopii (NULL dla
        # istniejących); istniejące wersje pozostają wersją początkową —
        # migracja NIE tworzy szkiców ani zdarzeń (bez masowych powiadomień).
        "ALTER TABLE training_plan_versions ADD COLUMN source_template_id VARCHAR(40)",
        "ALTER TABLE training_plan_versions ADD COLUMN source_template_version_no INTEGER",
        "ALTER TABLE nutrition_plan_versions ADD COLUMN source_template_id VARCHAR(40)",
        "ALTER TABLE nutrition_plan_versions ADD COLUMN source_template_version_no INTEGER",
        (
            "CREATE TABLE IF NOT EXISTS plan_drafts ("
            " id VARCHAR(40) PRIMARY KEY,"
            " plan_kind VARCHAR(20) NOT NULL,"
            " plan_id VARCHAR(40) NOT NULL,"
            " client_id VARCHAR(40),"
            " coach_id VARCHAR(40) NOT NULL,"
            " base_version_no INTEGER NOT NULL,"
            " base_content_json TEXT NOT NULL,"
            " content_json TEXT NOT NULL,"
            " revision INTEGER NOT NULL DEFAULT 1,"
            " status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',"
            " created_by VARCHAR(40) NOT NULL,"
            " updated_by VARCHAR(40) NOT NULL,"
            " created_at VARCHAR(40) NOT NULL,"
            " updated_at VARCHAR(40) NOT NULL)"
        ),
        "CREATE INDEX IF NOT EXISTS ix_plan_drafts_plan_id ON plan_drafts (plan_id)",
        "CREATE INDEX IF NOT EXISTS ix_plan_drafts_coach_id ON plan_drafts (coach_id)",
        "CREATE INDEX IF NOT EXISTS ix_plan_drafts_plan_status ON plan_drafts (plan_kind, plan_id, status)",
        (
            "CREATE TABLE IF NOT EXISTS change_sets ("
            " id VARCHAR(40) PRIMARY KEY,"
            " plan_kind VARCHAR(20) NOT NULL,"
            " plan_id VARCHAR(40) NOT NULL,"
            " client_id VARCHAR(40),"
            " old_version_no INTEGER NOT NULL,"
            " new_version_no INTEGER NOT NULL,"
            " diff_json TEXT NOT NULL,"
            " summary TEXT NOT NULL,"
            " note TEXT,"
            " author_id VARCHAR(40) NOT NULL,"
            " published_at VARCHAR(40) NOT NULL,"
            " notification_id VARCHAR(40))"
        ),
        "CREATE INDEX IF NOT EXISTS ix_change_sets_plan_id ON change_sets (plan_id)",
        "CREATE INDEX IF NOT EXISTS ix_change_sets_client_id ON change_sets (client_id)",
        "CREATE INDEX IF NOT EXISTS ix_change_sets_plan ON change_sets (plan_kind, plan_id)",
        (
            "CREATE TABLE IF NOT EXISTS outbox_events ("
            " id VARCHAR(40) PRIMARY KEY,"
            " event_type VARCHAR(40) NOT NULL,"
            " aggregate_id VARCHAR(40) NOT NULL,"
            " recipient_id VARCHAR(40) NOT NULL,"
            " payload_json TEXT NOT NULL,"
            " status VARCHAR(20) NOT NULL DEFAULT 'PENDING',"
            " attempts INTEGER NOT NULL DEFAULT 0,"
            " next_attempt_at VARCHAR(40) NOT NULL,"
            " last_error TEXT,"
            " created_at VARCHAR(40) NOT NULL,"
            " delivered_at VARCHAR(40),"
            " UNIQUE (event_type, aggregate_id, recipient_id))"
        ),
        "CREATE INDEX IF NOT EXISTS ix_outbox_events_recipient_id ON outbox_events (recipient_id)",
        "CREATE INDEX IF NOT EXISTS ix_outbox_events_status_next ON outbox_events (status, next_attempt_at)",
    ])
)

MIGRATIONS.append(
    (31, "zakładka Wywiad: szkice, wersje, przeglądy, doprecyzowania, fakty, zadania sprawdzenia planu", [
        # Addytywna. Tabele rozmowy startowej/głębokiego wywiadu ZOSTAJĄ;
        # przeniesienie sesji do wersji robi `wywiad.migracja` (ponawialnie,
        # bez powiadomień) po starcie aplikacji, nie ten skrypt.
        (
            "CREATE TABLE IF NOT EXISTS interview_drafts ("
            " id VARCHAR(40) PRIMARY KEY,"
            " client_id VARCHAR(40) NOT NULL,"
            " typ VARCHAR(20) NOT NULL,"
            " definition_version INTEGER NOT NULL DEFAULT 1,"
            " answers_json TEXT NOT NULL DEFAULT '{}',"
            " revision INTEGER NOT NULL DEFAULT 1,"
            " dirty BOOLEAN NOT NULL DEFAULT true,"
            " collection_mode VARCHAR(20) NOT NULL DEFAULT 'SELF',"
            " created_by VARCHAR(40) NOT NULL,"
            " updated_by VARCHAR(40) NOT NULL,"
            " created_at VARCHAR(40) NOT NULL,"
            " updated_at VARCHAR(40) NOT NULL,"
            " last_submission_id VARCHAR(40),"
            " source_session_id VARCHAR(40),"
            " UNIQUE (client_id, typ))"
        ),
        "CREATE INDEX IF NOT EXISTS ix_interview_drafts_client_id ON interview_drafts (client_id)",
        (
            "CREATE TABLE IF NOT EXISTS interview_submissions ("
            " id VARCHAR(40) PRIMARY KEY,"
            " client_id VARCHAR(40) NOT NULL,"
            " coach_id VARCHAR(40),"
            " typ VARCHAR(20) NOT NULL,"
            " version_no INTEGER NOT NULL,"
            " definition_version INTEGER NOT NULL DEFAULT 1,"
            " answers_json TEXT NOT NULL,"
            " progress_json TEXT NOT NULL DEFAULT '{}',"
            " submitted_by VARCHAR(40) NOT NULL,"
            " submitted_at VARCHAR(40) NOT NULL,"
            " collection_mode VARCHAR(20) NOT NULL DEFAULT 'SELF',"
            " migrated BOOLEAN NOT NULL DEFAULT false,"
            " source_session_id VARCHAR(40),"
            " safety_flag BOOLEAN NOT NULL DEFAULT false,"
            " UNIQUE (client_id, typ, version_no))"
        ),
        "CREATE INDEX IF NOT EXISTS ix_interview_submissions_client_id ON interview_submissions (client_id)",
        "CREATE INDEX IF NOT EXISTS ix_interview_submissions_coach_id ON interview_submissions (coach_id)",
        "CREATE INDEX IF NOT EXISTS ix_interview_submissions_client_typ ON interview_submissions (client_id, typ)",
        (
            "CREATE TABLE IF NOT EXISTS interview_reviews ("
            " id VARCHAR(40) PRIMARY KEY,"
            " submission_id VARCHAR(40) NOT NULL,"
            " coach_id VARCHAR(40) NOT NULL,"
            " outcome VARCHAR(30) NOT NULL,"
            " internal_note TEXT,"
            " migrated BOOLEAN NOT NULL DEFAULT false,"
            " created_at VARCHAR(40) NOT NULL)"
        ),
        "CREATE INDEX IF NOT EXISTS ix_interview_reviews_submission_id ON interview_reviews (submission_id)",
        "CREATE INDEX IF NOT EXISTS ix_interview_reviews_coach_id ON interview_reviews (coach_id)",
        (
            "CREATE TABLE IF NOT EXISTS clarification_requests ("
            " id VARCHAR(40) PRIMARY KEY,"
            " client_id VARCHAR(40) NOT NULL,"
            " typ VARCHAR(20) NOT NULL,"
            " submission_id VARCHAR(40),"
            " coach_id VARCHAR(40) NOT NULL,"
            " question_ids_json TEXT NOT NULL DEFAULT '[]',"
            " message TEXT NOT NULL DEFAULT '',"
            " status VARCHAR(20) NOT NULL DEFAULT 'OPEN',"
            " created_at VARCHAR(40) NOT NULL,"
            " resolved_at VARCHAR(40),"
            " resolved_by_submission_id VARCHAR(40))"
        ),
        "CREATE INDEX IF NOT EXISTS ix_clarification_requests_client_id ON clarification_requests (client_id)",
        "CREATE INDEX IF NOT EXISTS ix_clarification_requests_submission_id ON clarification_requests (submission_id)",
        (
            "CREATE TABLE IF NOT EXISTS client_fact_revisions ("
            " id VARCHAR(40) PRIMARY KEY,"
            " client_id VARCHAR(40) NOT NULL,"
            " fact_key VARCHAR(80) NOT NULL,"
            " value TEXT NOT NULL DEFAULT '',"
            " source_type VARCHAR(40) NOT NULL,"
            " source_id VARCHAR(40),"
            " question_id VARCHAR(40),"
            " author_id VARCHAR(40) NOT NULL,"
            " version INTEGER NOT NULL DEFAULT 1,"
            " is_current BOOLEAN NOT NULL DEFAULT true,"
            " sensitive BOOLEAN NOT NULL DEFAULT false,"
            " created_at VARCHAR(40) NOT NULL)"
        ),
        "CREATE INDEX IF NOT EXISTS ix_client_fact_revisions_client_id ON client_fact_revisions (client_id)",
        "CREATE INDEX IF NOT EXISTS ix_client_fact_revisions_current ON client_fact_revisions (client_id, fact_key, is_current)",
        (
            "CREATE TABLE IF NOT EXISTS plan_review_tasks ("
            " id VARCHAR(40) PRIMARY KEY,"
            " client_id VARCHAR(40) NOT NULL,"
            " coach_id VARCHAR(40) NOT NULL,"
            " plan_kind VARCHAR(20) NOT NULL,"
            " plan_id VARCHAR(40) NOT NULL,"
            " submission_id VARCHAR(40) NOT NULL,"
            " changed_facts_json TEXT NOT NULL DEFAULT '[]',"
            " status VARCHAR(20) NOT NULL DEFAULT 'OPEN',"
            " created_at VARCHAR(40) NOT NULL,"
            " resolved_at VARCHAR(40),"
            " resolved_by VARCHAR(40),"
            " resolution_note TEXT)"
        ),
        "CREATE INDEX IF NOT EXISTS ix_plan_review_tasks_client_id ON plan_review_tasks (client_id)",
        "CREATE INDEX IF NOT EXISTS ix_plan_review_tasks_coach_id ON plan_review_tasks (coach_id)",
        "CREATE INDEX IF NOT EXISTS ix_plan_review_tasks_plan ON plan_review_tasks (plan_kind, plan_id, status)",
    ])
)

MIGRATIONS.append(
    (32, "szablony diet ze skalowaniem: produkty, profile, odsłony, dni, posiłki, składniki, przypisania, wymiany", [
        # Addytywna; moduł za flagą DZIK_DIET_TEMPLATES_ENABLED. Seed danych
        # (142 produkty + odsłona Standard v1) robi dieta.seed idempotentnie.
        (
            "CREATE TABLE IF NOT EXISTS diet_products ("
            " id VARCHAR(40) PRIMARY KEY,"
            " name_pl VARCHAR(200) NOT NULL UNIQUE,"
            " category VARCHAR(60) NOT NULL,"
            " substitution_group VARCHAR(80) NOT NULL DEFAULT '',"
            " kcal_100 FLOAT NOT NULL,"
            " kcal_usda FLOAT,"
            " protein_100 FLOAT NOT NULL,"
            " fat_100 FLOAT NOT NULL,"
            " carbs_100 FLOAT NOT NULL,"
            " fiber_100 FLOAT NOT NULL DEFAULT 0,"
            " cooking_tags VARCHAR(200) NOT NULL DEFAULT '',"
            " allergens VARCHAR(200) NOT NULL DEFAULT '',"
            " diet_exclusions VARCHAR(200) NOT NULL DEFAULT '',"
            " default_scaling VARCHAR(20) NOT NULL DEFAULT 'LINIOWY',"
            " source VARCHAR(120) NOT NULL DEFAULT '',"
            " source_id VARCHAR(80),"
            " source_desc TEXT,"
            " created_at VARCHAR(40) NOT NULL)"
        ),
        (
            "CREATE TABLE IF NOT EXISTS diet_profiles ("
            " id VARCHAR(40) PRIMARY KEY,"
            " name VARCHAR(120) NOT NULL UNIQUE,"
            " description TEXT NOT NULL DEFAULT '',"
            " base_p_pct FLOAT NOT NULL,"
            " base_f_pct FLOAT NOT NULL,"
            " base_c_pct FLOAT NOT NULL,"
            " diet_tags VARCHAR(200) NOT NULL DEFAULT '',"
            " created_at VARCHAR(40) NOT NULL)"
        ),
        (
            "CREATE TABLE IF NOT EXISTS diet_template_weeks ("
            " id VARCHAR(40) PRIMARY KEY,"
            " profile_id VARCHAR(40) NOT NULL,"
            " variant_no INTEGER NOT NULL DEFAULT 1,"
            " name VARCHAR(200) NOT NULL DEFAULT '',"
            " base_kcal INTEGER NOT NULL DEFAULT 2000,"
            " kcal_min INTEGER NOT NULL DEFAULT 1400,"
            " kcal_max INTEGER NOT NULL DEFAULT 3200,"
            " status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',"
            " created_by VARCHAR(40),"
            " created_at VARCHAR(40) NOT NULL,"
            " updated_at VARCHAR(40) NOT NULL,"
            " UNIQUE (profile_id, variant_no))"
        ),
        "CREATE INDEX IF NOT EXISTS ix_diet_template_weeks_profile_id ON diet_template_weeks (profile_id)",
        (
            "CREATE TABLE IF NOT EXISTS diet_template_days ("
            " id VARCHAR(40) PRIMARY KEY,"
            " week_id VARCHAR(40) NOT NULL,"
            " day_no INTEGER NOT NULL,"
            " UNIQUE (week_id, day_no))"
        ),
        "CREATE INDEX IF NOT EXISTS ix_diet_template_days_week_id ON diet_template_days (week_id)",
        (
            "CREATE TABLE IF NOT EXISTS diet_template_meals ("
            " id VARCHAR(40) PRIMARY KEY,"
            " day_id VARCHAR(40) NOT NULL,"
            " position INTEGER NOT NULL DEFAULT 0,"
            " slot VARCHAR(40) NOT NULL,"
            " name VARCHAR(200) NOT NULL,"
            " kcal_share FLOAT NOT NULL,"
            " flexible BOOLEAN NOT NULL DEFAULT false,"
            " recipe_steps TEXT NOT NULL DEFAULT '',"
            " prep_minutes INTEGER,"
            " tags VARCHAR(200) NOT NULL DEFAULT '')"
        ),
        "CREATE INDEX IF NOT EXISTS ix_diet_template_meals_day_id ON diet_template_meals (day_id)",
        (
            "CREATE TABLE IF NOT EXISTS diet_template_ingredients ("
            " id VARCHAR(40) PRIMARY KEY,"
            " meal_id VARCHAR(40) NOT NULL,"
            " position INTEGER NOT NULL DEFAULT 0,"
            " product_id VARCHAR(40) NOT NULL,"
            " base_grams FLOAT NOT NULL,"
            " scaling_class VARCHAR(20),"
            " macro_role VARCHAR(8) NOT NULL DEFAULT 'NONE',"
            " min_factor FLOAT,"
            " max_factor FLOAT,"
            " round_step FLOAT,"
            " unit_g FLOAT,"
            " unit_step FLOAT,"
            " group_name VARCHAR(60),"
            " swappable BOOLEAN NOT NULL DEFAULT true)"
        ),
        "CREATE INDEX IF NOT EXISTS ix_diet_template_ingredients_meal_id ON diet_template_ingredients (meal_id)",
        "CREATE INDEX IF NOT EXISTS ix_diet_template_ingredients_product_id ON diet_template_ingredients (product_id)",
        (
            "CREATE TABLE IF NOT EXISTS diet_assigned ("
            " id VARCHAR(40) PRIMARY KEY,"
            " client_id VARCHAR(40) NOT NULL,"
            " coach_id VARCHAR(40) NOT NULL,"
            " week_id VARCHAR(40) NOT NULL,"
            " target_kcal INTEGER NOT NULL,"
            " target_p FLOAT NOT NULL,"
            " target_f FLOAT NOT NULL,"
            " target_c FLOAT NOT NULL,"
            " body_weight FLOAT,"
            " macro_mode VARCHAR(20) NOT NULL DEFAULT 'profile',"
            " exclusions_json TEXT NOT NULL DEFAULT '[]',"
            " computed_plan_json TEXT NOT NULL,"
            " overrides_json TEXT NOT NULL DEFAULT '{}',"
            " status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',"
            " version INTEGER NOT NULL DEFAULT 1,"
            " swaps_enabled BOOLEAN NOT NULL DEFAULT true,"
            " created_at VARCHAR(40) NOT NULL,"
            " updated_at VARCHAR(40) NOT NULL)"
        ),
        "CREATE INDEX IF NOT EXISTS ix_diet_assigned_client_id ON diet_assigned (client_id)",
        "CREATE INDEX IF NOT EXISTS ix_diet_assigned_coach_id ON diet_assigned (coach_id)",
        "CREATE INDEX IF NOT EXISTS ix_diet_assigned_week_id ON diet_assigned (week_id)",
        "CREATE INDEX IF NOT EXISTS ix_diet_assigned_client_status ON diet_assigned (client_id, status)",
        (
            "CREATE TABLE IF NOT EXISTS diet_swap_events ("
            " id VARCHAR(40) PRIMARY KEY,"
            " assigned_diet_id VARCHAR(40) NOT NULL,"
            " day_no INTEGER NOT NULL,"
            " meal_id VARCHAR(40) NOT NULL,"
            " ingredient_id VARCHAR(40) NOT NULL,"
            " from_product_id VARCHAR(40) NOT NULL,"
            " to_product_id VARCHAR(40) NOT NULL,"
            " from_grams FLOAT NOT NULL,"
            " to_grams FLOAT NOT NULL,"
            " actor_id VARCHAR(40) NOT NULL,"
            " created_at VARCHAR(40) NOT NULL)"
        ),
        "CREATE INDEX IF NOT EXISTS ix_diet_swap_events_assigned_diet_id ON diet_swap_events (assigned_diet_id)",
    ])
)

MIGRATIONS.append(
    (33, "wywiad zapotrzebowania kalorycznego: szacunki (calorie_estimates)", [
        # Addytywna; typ wywiadu za flagą DZIK_CALORIE_INTERVIEW_ENABLED.
        (
            "CREATE TABLE IF NOT EXISTS calorie_estimates ("
            " id VARCHAR(40) PRIMARY KEY,"
            " client_id VARCHAR(40) NOT NULL REFERENCES users(id),"
            " submission_id VARCHAR(40) NOT NULL UNIQUE,"
            " version_no INTEGER NOT NULL,"
            " inputs_json TEXT NOT NULL,"
            " ppm INTEGER NOT NULL,"
            " pal FLOAT NOT NULL,"
            " cpm INTEGER NOT NULL,"
            " korekta_pct INTEGER NOT NULL,"
            " kcal INTEGER NOT NULL,"
            " podstawienie_json TEXT NOT NULL DEFAULT '[]',"
            " ostrzezenia_json TEXT NOT NULL DEFAULT '[]',"
            " hidden_for_client BOOLEAN NOT NULL DEFAULT false,"
            " unhidden_by VARCHAR(40),"
            " unhidden_at VARCHAR(40),"
            " override_kcal INTEGER,"
            " override_by VARCHAR(40),"
            " override_at VARCHAR(40),"
            " override_reason TEXT,"
            " created_at VARCHAR(40) NOT NULL)"
        ),
        "CREATE INDEX IF NOT EXISTS ix_calorie_estimates_client_id ON calorie_estimates (client_id)",
    ])
)

MIGRATIONS.append(
    (34, "nawyki na ekranie Dzisiaj: habits, habit_completions", [
        # Addytywna; wycofanie = ignorowanie tabel.
        (
            "CREATE TABLE IF NOT EXISTS habits ("
            " id VARCHAR(40) PRIMARY KEY,"
            " client_id VARCHAR(40) NOT NULL REFERENCES users(id),"
            " name VARCHAR(200) NOT NULL,"
            " days_of_week VARCHAR(30) NOT NULL DEFAULT '1,2,3,4,5,6,7',"
            " target_days INTEGER NOT NULL DEFAULT 66,"
            " author_id VARCHAR(40) NOT NULL,"
            " author_note TEXT,"
            " started_on VARCHAR(40) NOT NULL,"
            " status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',"
            " graduated_on VARCHAR(40),"
            " ack_on VARCHAR(40),"
            " created_at VARCHAR(40) NOT NULL,"
            " updated_at VARCHAR(40) NOT NULL)"
        ),
        "CREATE INDEX IF NOT EXISTS ix_habits_client_id ON habits (client_id)",
        (
            "CREATE TABLE IF NOT EXISTS habit_completions ("
            " id VARCHAR(40) PRIMARY KEY,"
            " habit_id VARCHAR(40) NOT NULL REFERENCES habits(id),"
            " client_id VARCHAR(40) NOT NULL REFERENCES users(id),"
            " completed_on VARCHAR(40) NOT NULL,"
            " status VARCHAR(20) NOT NULL DEFAULT 'DONE',"
            " created_by VARCHAR(40) NOT NULL,"
            " created_at VARCHAR(40) NOT NULL,"
            " UNIQUE (habit_id, completed_on))"
        ),
        "CREATE INDEX IF NOT EXISTS ix_habit_completions_habit_id ON habit_completions (habit_id)",
        "CREATE INDEX IF NOT EXISTS ix_habit_completions_client_id ON habit_completions (client_id)",
    ])
)

MIGRATIONS.append(
    (35, "biblioteka szablonów diet po audycie: notatki, alergeny posiłku, skrót źródła", [
        # Addytywna (ALTER ADD COLUMN z DEFAULT — jak migracja 2).
        "ALTER TABLE diet_template_weeks ADD COLUMN derived_from VARCHAR(120)",
        "ALTER TABLE diet_template_weeks ADD COLUMN supplements_note TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE diet_template_weeks ADD COLUMN sodium_note TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE diet_template_weeks ADD COLUMN audit_json TEXT NOT NULL DEFAULT '{}'",
        "ALTER TABLE diet_template_weeks ADD COLUMN source_hash VARCHAR(64)",
        "ALTER TABLE diet_template_meals ADD COLUMN allergens VARCHAR(300) NOT NULL DEFAULT ''",
    ])
)

MIGRATIONS.append(
    (36, "postępy: rekordy osobiste (historia) i agregaty tygodnia treningowego", [
        # Addytywna; wycofanie = ignorowanie tabel. Numer 35 = biblioteka diet.
        (
            "CREATE TABLE IF NOT EXISTS exercise_records ("
            " id VARCHAR(40) PRIMARY KEY,"
            " client_id VARCHAR(40) NOT NULL REFERENCES users(id),"
            " exercise_key VARCHAR(300) NOT NULL,"
            " exercise_name VARCHAR(300) NOT NULL,"
            " record_type VARCHAR(20) NOT NULL,"
            " value FLOAT NOT NULL,"
            " secondary_value FLOAT,"
            " set_ref VARCHAR(80),"
            " session_id VARCHAR(40),"
            " achieved_on VARCHAR(40) NOT NULL,"
            " previous_value FLOAT,"
            " equaled_on VARCHAR(40),"
            " superseded_at VARCHAR(40),"
            " created_at VARCHAR(40) NOT NULL)"
        ),
        "CREATE INDEX IF NOT EXISTS ix_exercise_records_client_id ON exercise_records (client_id)",
        "CREATE INDEX IF NOT EXISTS ix_exercise_records_exercise_key ON exercise_records (exercise_key)",
        (
            "CREATE TABLE IF NOT EXISTS training_week_aggregates ("
            " id VARCHAR(40) PRIMARY KEY,"
            " client_id VARCHAR(40) NOT NULL REFERENCES users(id),"
            " week_start VARCHAR(40) NOT NULL,"
            " sessions_count INTEGER NOT NULL DEFAULT 0,"
            " planned_count INTEGER NOT NULL DEFAULT 0,"
            " tonnage_kg FLOAT NOT NULL DEFAULT 0,"
            " sets_by_group_json TEXT NOT NULL DEFAULT '{}',"
            " session_days_json TEXT NOT NULL DEFAULT '[]',"
            " updated_at VARCHAR(40) NOT NULL,"
            " UNIQUE (client_id, week_start))"
        ),
        "CREATE INDEX IF NOT EXISTS ix_training_week_aggregates_client_id ON training_week_aggregates (client_id)",
    ])
)
MIGRATIONS.append(
    (37, "powitanie po pierwszym logowaniu: users.welcome_seen_at", [
        # Addytywna (ALTER ADD COLUMN bez DEFAULT — jak migracja 14);
        # NULL = okno powitalne jeszcze nie pokazane. Wycofanie = ignorowanie
        # kolumny. Numer 37 = ta runda; dni treningowe przesunięte na 38.
        "ALTER TABLE users ADD COLUMN welcome_seen_at VARCHAR(40)",
    ])
)
