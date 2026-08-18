from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def _make_engine(url: str):
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
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
        "ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0",
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
            pinned BOOLEAN NOT NULL DEFAULT 0,
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
