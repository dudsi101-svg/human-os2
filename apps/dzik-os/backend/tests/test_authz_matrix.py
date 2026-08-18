"""Automatyczna macierz uprawnień: każdy endpoint danych klienta odpytany
tokenami wszystkich ról (anonim, klient-właściciel, obcy klient, trener
prowadzący, obcy trener, admin). Oczekiwania odpowiadają tabeli w
docs/PERMISSIONS.md; odmowa zasobowa to zawsze 404 (nie ujawniamy
istnienia), odmowa roli to 403, brak logowania to 401."""

from __future__ import annotations

import conftest
import pytest
from conftest import (
    ADMIN,
    CLIENT_A,
    CLIENT_B,
    COACH,
    create_user_with_role,
    get_user_id,
    login,
)
from fastapi.testclient import TestClient

from dzik_os import seed as seed_module
from dzik_os.main import app

FOREIGN_COACH = {"email": "obcy.trener@example.com", "password": "ObcyTrener#26x"}


@pytest.fixture(scope="module")
def mx():
    """Jedno wspólne środowisko dla całej macierzy (wyłącznie odczyty GET,
    żaden test nie mutuje danych) — sześć person, dane z seedu."""
    conftest._reset_state()
    with TestClient(app) as c:
        seed_module.seed()
        create_user_with_role(
            FOREIGN_COACH["email"], FOREIGN_COACH["password"], "Obcy Trener", "COACH"
        )
        personas = {
            "anon": {},
            "client_self": login(c, CLIENT_A),
            "other_client": login(c, CLIENT_B),
            "coach": login(c, COACH),
            "foreign_coach": login(c, FOREIGN_COACH),
            "admin": login(c, ADMIN),
        }
        client_id = get_user_id(c, personas["client_self"])
        # Logowanie ustawia też ciasteczko sesji — czyścimy je, żeby persona
        # „anon" była naprawdę anonimowa (personom wystarczy nagłówek Bearer).
        c.cookies.clear()
        yield c, personas, client_id


# Endpointy zakresu „dane jednego klienta" — wspólny kontrakt:
# właściciel i trener prowadzący (aktywna relacja + zgoda) widzą, cała
# reszta dostaje 404 (obcy) lub 401 (anonim). Payments celowo w tej samej
# grupie: sensitive=False nie zmienia odpowiedzi dla obcych.
CLIENT_SCOPED_GETS = [
    "/api/clients/{id}/profile",
    "/api/clients/{id}/profile/history",
    "/api/clients/{id}/goals",
    "/api/clients/{id}/plans",
    "/api/clients/{id}/workouts",
    "/api/clients/{id}/checkins",
    "/api/clients/{id}/measurements",
    "/api/clients/{id}/metric-definitions",
    "/api/clients/{id}/documents",
    "/api/clients/{id}/photos",
    "/api/clients/{id}/schedule",
    "/api/clients/{id}/reminders",
    "/api/clients/{id}/nutrition",
    "/api/clients/{id}/observations",
    "/api/clients/{id}/nutrition-log",
    "/api/clients/{id}/monitoring",
    "/api/clients/{id}/personal-records",
    "/api/clients/{id}/strength-series",
    "/api/clients/{id}/payments",
]

CLIENT_SCOPED_EXPECTED = {
    "anon": 401,
    "client_self": 200,
    "other_client": 404,
    "coach": 200,
    "foreign_coach": 404,
    "admin": 404,
}


@pytest.mark.parametrize("path", CLIENT_SCOPED_GETS)
def test_client_scoped_endpoint_matrix(mx, path):
    c, personas, client_id = mx
    url = path.format(id=client_id)
    for persona, expected in CLIENT_SCOPED_EXPECTED.items():
        r = c.get(url, headers=personas[persona])
        assert r.status_code == expected, (
            f"{persona} GET {url} -> {r.status_code}, oczekiwano {expected}"
        )


# Endpointy panelu trenera o zakresie jednego klienta: wymagana rola COACH
# (403 dla klientów i admina) ORAZ relacja+zgoda (404 dla obcego trenera).
COACH_CLIENT_SCOPED_GETS = [
    "/api/coach/clients/{id}/history",
    "/api/coach/clients/{id}/overview",
]

COACH_CLIENT_SCOPED_EXPECTED = {
    "anon": 401,
    "client_self": 403,
    "other_client": 403,
    "coach": 200,
    "foreign_coach": 404,
    "admin": 403,
}


@pytest.mark.parametrize("path", COACH_CLIENT_SCOPED_GETS)
def test_coach_client_scoped_matrix(mx, path):
    c, personas, client_id = mx
    url = path.format(id=client_id)
    for persona, expected in COACH_CLIENT_SCOPED_EXPECTED.items():
        r = c.get(url, headers=personas[persona])
        assert r.status_code == expected, (
            f"{persona} GET {url} -> {r.status_code}, oczekiwano {expected}"
        )


# Endpointy wyłącznie-rolowe (bez identyfikatora zasobu w ścieżce).
ROLE_GATED_GETS = [
    ("/api/coach/clients", {"anon": 401, "client_self": 403, "other_client": 403,
                            "coach": 200, "foreign_coach": 200, "admin": 403}),
    ("/api/coach/dashboard", {"anon": 401, "client_self": 403, "other_client": 403,
                              "coach": 200, "foreign_coach": 200, "admin": 403}),
    ("/api/plans/templates", {"anon": 401, "client_self": 403, "other_client": 403,
                              "coach": 200, "foreign_coach": 200, "admin": 403}),
    ("/api/coach/exercises", {"anon": 401, "client_self": 403, "other_client": 403,
                              "coach": 200, "foreign_coach": 200, "admin": 403}),
    ("/api/coach/knowledge", {"anon": 401, "client_self": 403, "other_client": 403,
                              "coach": 200, "foreign_coach": 200, "admin": 403}),
    ("/api/coach/food-products", {"anon": 401, "client_self": 403, "other_client": 403,
                                  "coach": 200, "foreign_coach": 200, "admin": 403}),
    ("/api/coach/consult-slots", {"anon": 401, "client_self": 403, "other_client": 403,
                                  "coach": 200, "foreign_coach": 200, "admin": 403}),
    ("/api/admin/users", {"anon": 401, "client_self": 403, "other_client": 403,
                          "coach": 403, "foreign_coach": 403, "admin": 200}),
    ("/api/admin/receipts", {"anon": 401, "client_self": 403, "other_client": 403,
                             "coach": 403, "foreign_coach": 403, "admin": 200}),
    ("/api/admin/audit/verify", {"anon": 401, "client_self": 403, "other_client": 403,
                                 "coach": 403, "foreign_coach": 403, "admin": 200}),
    ("/api/me/today", {"anon": 401, "client_self": 200, "other_client": 200,
                       "coach": 403, "foreign_coach": 403, "admin": 403}),
]


@pytest.mark.parametrize("path,expected_map", ROLE_GATED_GETS)
def test_role_gated_matrix(mx, path, expected_map):
    c, personas, _ = mx
    for persona, expected in expected_map.items():
        r = c.get(path, headers=personas[persona])
        assert r.status_code == expected, (
            f"{persona} GET {path} -> {r.status_code}, oczekiwano {expected}"
        )


def test_isolation_between_coaches_in_catalogs(mx):
    """Katalogi (ćwiczenia/wiedza/produkty) są per trener: obcy trener widzi
    puste listy, nie zasoby trenera prowadzącego."""
    c, personas, _ = mx
    for path in ("/api/coach/exercises", "/api/coach/knowledge", "/api/coach/food-products"):
        own = c.get(path, headers=personas["coach"]).json()["items"]
        foreign = c.get(path, headers=personas["foreign_coach"]).json()["items"]
        assert foreign == [], f"{path}: obcy trener widzi cudze wpisy"
        assert own, f"{path}: seed powinien dawać wpisy trenera prowadzącego"
