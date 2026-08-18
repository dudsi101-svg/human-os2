"""Wykonawcza weryfikacja macierzy uprawnień (access_matrix.py).

Każdy test wysyła PRAWDZIWE żądania PRAWDZIWYMI kontami przez API — nie
sprawdza deklaracji, tylko zachowanie. Testowane są wyłącznie ścieżki
ODMOWY, więc żadna operacja nie powinna niczego zmienić; gdyby jednak
jakaś przeszła, to właśnie jest szukana luka i test ją zgłosi.

Aktorzy: klient A, klient B (obaj u tego samego trenera), trener z relacją,
trener BEZ relacji (tworzony tutaj — audyt wymagał pary trener A/B),
administrator oraz użytkownik niezalogowany.
"""

from __future__ import annotations

import pytest
from access_matrix import (
    DENIED_STATUSES,
    MATRIX,
    UNAUTHENTICATED_STATUSES,
    Access,
    body_for_operation,
    operations,
    query_for_operation,
)
from conftest import ADMIN, CLIENT_A, CLIENT_B, COACH, login

from dzik_os.db import db_session
from dzik_os.main import app
from dzik_os.models import RoleGrant, User, new_id
from dzik_os.security import hash_password

OTHER_COACH = {"email": "obcy.trener@example.com", "password": "ObcyTrener#2026!x"}

#: Kody dopuszczalne przy odmowie operacji Z CIAŁEM: 422 oznacza, że
#: walidacja ładunku wyprzedziła autoryzację — dane nie wyciekły, choć taki
#: wynik nie jest dowodem izolacji (liczone osobno w teście pokrycia dowodu).
BODY_DENIED_STATUSES = DENIED_STATUSES | {422}


@pytest.fixture(scope="module")
def spec() -> dict:
    return app.openapi()


@pytest.fixture
def unrelated_coach(seeded):
    """Trener BEZ relacji z klientami z seeda — sprawdza, czy sama rola
    COACH nie wystarcza do sięgnięcia po cudzego podopiecznego."""
    with db_session() as db:
        existing = db.query(User).filter(User.email == OTHER_COACH["email"]).one_or_none()
        if existing is None:
            user = User(
                id=new_id("USR"), email=OTHER_COACH["email"],
                password_hash=hash_password(OTHER_COACH["password"]),
                display_name="Obcy Trener", identity_id=new_id("ID"),
            )
            db.add(user)
            db.add(RoleGrant(id=new_id("ROL"), user_id=user.id, role="COACH",
                             scope="*", issued_by="test"))
            db.commit()
    return login(seeded, OTHER_COACH)


def _user_id(client, headers) -> str:
    return client.get("/api/auth/me", headers=headers).json()["id"]


def _fill_path(path: str, client_id: str) -> str:
    """Podstawia parametry ścieżki: {client_id} realnym klientem, pozostałe
    identyfikatory wartością o poprawnym formacie, ale nieistniejącą."""
    filled = path.replace("{client_id}", client_id)
    while "{" in filled:
        start = filled.index("{")
        end = filled.index("}", start)
        filled = filled[:start] + "HOS-XXX-000000000000" + filled[end + 1:]
    return filled


def _call(client, method: str, path: str, headers, spec, real_path: str):
    """Wywołuje operację z minimalnym poprawnym ładunkiem i wymaganymi
    parametrami query, żeby żądanie doszło do warstwy uprawnień, a nie
    zatrzymało się na walidacji. Zwraca też informację, czy walidacja mogła
    wyprzedzić autoryzację (wtedy 422 jest dopuszczalnym wynikiem)."""
    body = body_for_operation(spec, method, path)
    query = query_for_operation(spec, method, path)
    kwargs = {"headers": headers}
    if body is not None:
        kwargs["json"] = body
    if query:
        kwargs["params"] = query
    return client.request(method, real_path, **kwargs), bool(body is not None or query)


# --- Bramka pokrycia -------------------------------------------------------


def test_matrix_covers_every_operation(spec):
    """Każda operacja API ma zadeklarowaną klasę dostępu — i odwrotnie.

    Ten test jest bramką: nowy endpoint bez wpisu w macierzy przerywa build,
    więc „kto ma tu dostęp" musi być decyzją, a nie przeoczeniem.
    """
    live = set(operations(spec))
    declared = set(MATRIX)

    missing = sorted(live - declared)
    assert not missing, (
        "Operacje bez zadeklarowanej klasy dostępu — dopisz je do MATRIX "
        "w access_matrix.py:\n" + "\n".join(f"  {m} {p}" for m, p in missing)
    )

    stale = sorted(declared - live)
    assert not stale, (
        "Wpisy w MATRIX bez odpowiadającej trasy (macierz zardzewiała):\n"
        + "\n".join(f"  {m} {p}" for m, p in stale)
    )


# --- Odmowy dla niezalogowanego -------------------------------------------


def test_protected_operations_reject_anonymous(seeded, spec):
    """Bez tokenu żadna operacja poza PUBLIC nie może wykonać się skutecznie."""
    leaks = []
    for (method, path), access in sorted(MATRIX.items(), key=lambda i: i[0][1]):
        if access is Access.PUBLIC:
            continue
        real = _fill_path(path, "HOS-USR-000000000000")
        response, had_body = _call(seeded, method, path, {}, spec, real)
        allowed = UNAUTHENTICATED_STATUSES | ({422} if had_body else set())
        if response.status_code not in allowed:
            leaks.append(f"{method} {path} -> {response.status_code}")
    assert not leaks, "Operacje osiągalne bez logowania:\n" + "\n".join(leaks)


# --- Izolacja między klientami (IDOR) --------------------------------------


def test_client_scoped_denied_to_foreign_client(seeded, spec):
    """Klient B nie może dotknąć NICZEGO, co należy do klienta A."""
    headers_a = login(seeded, CLIENT_A)
    client_a_id = _user_id(seeded, headers_a)
    headers_b = login(seeded, CLIENT_B)

    leaks, proven = [], 0
    for (method, path), access in sorted(MATRIX.items(), key=lambda i: i[0][1]):
        if access is not Access.CLIENT_SCOPED:
            continue
        real = _fill_path(path, client_a_id)
        response, had_body = _call(seeded, method, path, headers_b, spec, real)
        allowed = BODY_DENIED_STATUSES if had_body else DENIED_STATUSES
        if response.status_code not in allowed:
            leaks.append(f"{method} {path} -> {response.status_code}")
        elif response.status_code in DENIED_STATUSES:
            proven += 1

    assert not leaks, "Klient B sięgnął po dane klienta A:\n" + "\n".join(leaks)
    # Dowód izolacji, a nie samej walidacji ładunku: zdecydowana większość
    # operacji musi kończyć się twardą odmową (401/403/404), nie 422.
    total = sum(1 for a in MATRIX.values() if a is Access.CLIENT_SCOPED)
    # Wszystkie operacje muszą dojść DO warstwy uprawnień i zostać tam
    # odrzucone. Zatrzymanie się na walidacji ładunku (422) nie dowodzi
    # izolacji, więc próg jest ustawiony na komplet — dziś osiągalny.
    assert proven == total, (
        f"Tylko {proven}/{total} operacji CLIENT_SCOPED dało twardą odmowę; "
        "reszta zatrzymała się na walidacji ładunku (422), co nie dowodzi izolacji. "
        "Uzupełnij generator ciał/parametrów w access_matrix.py."
    )


def test_client_scoped_denied_to_unrelated_coach(seeded, spec, unrelated_coach):
    """Sama rola COACH nie wystarcza — bez relacji z klientem dostęp jest zamknięty."""
    headers_a = login(seeded, CLIENT_A)
    client_a_id = _user_id(seeded, headers_a)

    leaks = []
    for (method, path), access in sorted(MATRIX.items(), key=lambda i: i[0][1]):
        if access is not Access.CLIENT_SCOPED:
            continue
        real = _fill_path(path, client_a_id)
        response, had_body = _call(seeded, method, path, unrelated_coach, spec, real)
        allowed = BODY_DENIED_STATUSES if had_body else DENIED_STATUSES
        if response.status_code not in allowed:
            leaks.append(f"{method} {path} -> {response.status_code}")
    assert not leaks, "Trener bez relacji sięgnął po dane klienta:\n" + "\n".join(leaks)


def test_coach_scoped_denied_to_unrelated_coach(seeded, spec, unrelated_coach):
    """To samo dla tras trenerskich z {client_id} (np. przegląd, historia)."""
    headers_a = login(seeded, CLIENT_A)
    client_a_id = _user_id(seeded, headers_a)

    leaks = []
    for (method, path), access in MATRIX.items():
        if access is not Access.COACH_ONLY or "{client_id}" not in path:
            continue
        real = _fill_path(path, client_a_id)
        response, had_body = _call(seeded, method, path, unrelated_coach, spec, real)
        allowed = BODY_DENIED_STATUSES if had_body else DENIED_STATUSES
        if response.status_code not in allowed:
            leaks.append(f"{method} {path} -> {response.status_code}")
    assert not leaks, "Obcy trener użył trasy trenerskiej cudzego klienta:\n" + "\n".join(leaks)


# --- Rozdział ról ----------------------------------------------------------


def test_coach_only_denied_to_client(seeded, spec):
    """Klient nie może użyć operacji trenerskich."""
    headers_a = login(seeded, CLIENT_A)
    client_a_id = _user_id(seeded, headers_a)

    leaks = []
    for (method, path), access in sorted(MATRIX.items(), key=lambda i: i[0][1]):
        if access is not Access.COACH_ONLY:
            continue
        real = _fill_path(path, client_a_id)
        response, had_body = _call(seeded, method, path, headers_a, spec, real)
        allowed = BODY_DENIED_STATUSES if had_body else DENIED_STATUSES
        if response.status_code not in allowed:
            leaks.append(f"{method} {path} -> {response.status_code}")
    assert not leaks, "Klient wykonał operację trenerską:\n" + "\n".join(leaks)


def test_admin_only_denied_to_client_and_coach(seeded, spec):
    """Operacje administracyjne są zamknięte dla klienta i dla trenera."""
    leaks = []
    for role_name, creds in (("klient", CLIENT_A), ("trener", COACH)):
        headers = login(seeded, creds)
        for (method, path), access in MATRIX.items():
            if access is not Access.ADMIN_ONLY:
                continue
            real = _fill_path(path, "HOS-USR-000000000000")
            response, had_body = _call(seeded, method, path, headers, spec, real)
            allowed = BODY_DENIED_STATUSES if had_body else DENIED_STATUSES
            if response.status_code not in allowed:
                leaks.append(f"{role_name}: {method} {path} -> {response.status_code}")
    assert not leaks, "Operacja administracyjna dostępna nie-adminowi:\n" + "\n".join(leaks)


def test_admin_cannot_reach_client_health_data(seeded, spec):
    """Administrator to rola techniczna — dane zdrowotne podopiecznych
    pozostają poza jego zasięgiem mimo najwyższych uprawnień technicznych."""
    headers_a = login(seeded, CLIENT_A)
    client_a_id = _user_id(seeded, headers_a)
    headers_admin = login(seeded, ADMIN)

    leaks = []
    for (method, path), access in sorted(MATRIX.items(), key=lambda i: i[0][1]):
        if access is not Access.CLIENT_SCOPED:
            continue
        real = _fill_path(path, client_a_id)
        response, had_body = _call(seeded, method, path, headers_admin, spec, real)
        allowed = BODY_DENIED_STATUSES if had_body else DENIED_STATUSES
        if response.status_code not in allowed:
            leaks.append(f"{method} {path} -> {response.status_code}")
    assert not leaks, "Administrator sięgnął po dane klienta:\n" + "\n".join(leaks)
