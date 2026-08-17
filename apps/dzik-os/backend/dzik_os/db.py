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
