"""Zapis pól profilu z proweniencją — jedno źródło prawdy.

Profil jest append-only: nowa wartość pola to NOWY wiersz z wyższą
wersją, a poprzedni traci `is_current`. Wartość identyczna z bieżącą nie
tworzy wersji (brak pustych rewizji w historii).

Ten sam kod obsługuje wszystkie ścieżki zapisu — formularz ankiety
(`routers/profile.py`) i zatwierdzone podsumowanie konwersacyjnego
onboardingu (`routers/onboarding.py`) — żeby dane z rozmowy trafiały do
profilu NORMALNĄ, wersjonowaną ścieżką, a nie obok niej.

Autoryzacja (kto może pisać, czy zgoda kategorii jest aktywna) należy do
wywołującego — ta funkcja wyłącznie zapisuje.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from .models import ProfileField, new_id


@dataclass(frozen=True)
class FieldWrite:
    field_key: str
    value: str
    purpose: str = "coaching"
    sensitive: bool = False


def apply_profile_fields(
    db: Session,
    *,
    client_id: str,
    author_id: str,
    source: str,
    items: list[FieldWrite],
) -> list[str]:
    """Zapisuje pola profilu i zwraca listę faktycznie zmienionych kluczy.
    Commit należy do wywołującego (jedna transakcja z resztą operacji)."""
    changed: list[str] = []
    for item in items:
        current = (
            db.query(ProfileField)
            .filter(
                ProfileField.client_id == client_id,
                ProfileField.field_key == item.field_key,
                ProfileField.is_current.is_(True),
            )
            .one_or_none()
        )
        if current is not None and current.value == item.value:
            continue
        version = 1
        if current is not None:
            current.is_current = False
            version = current.version + 1
        db.add(
            ProfileField(
                id=new_id("PRF"),
                client_id=client_id,
                field_key=item.field_key,
                value=item.value,
                source=source,
                author_id=author_id,
                purpose=item.purpose,
                version=version,
                sensitive=item.sensitive,
            )
        )
        changed.append(item.field_key)
    return changed
