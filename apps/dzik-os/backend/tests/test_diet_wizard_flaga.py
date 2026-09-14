"""Kreator diety za flagą DZIK_DIET_WIZARD_ENABLED (0.67.0, zlecenie 0 właściciela).

Bez flagi obie trasy kreatora nie istnieją (404), a `features.diet_wizard` w
`/api/health` mówi interfejsowi, żeby nie pokazywał zakładki „Dieta”. Katalog
produktów, plany żywieniowe i szablony diet działają jak dotąd."""

from __future__ import annotations

from conftest import COACH, login

from dzik_os.config import settings

KREATOR = {"kcal": 2000, "meals": 4, "days": 1}
SUGESTIA = {"kcal": 2000, "product_ids": []}


def test_bez_flagi_kreator_znika_a_katalog_i_plany_zostaja(seeded, monkeypatch):
    hc = login(seeded, COACH)
    monkeypatch.setattr(settings, "diet_wizard_enabled", False)
    assert seeded.get("/api/health").json()["features"]["diet_wizard"] is False
    assert seeded.post("/api/coach/diet-wizard", headers=hc, json=KREATOR).status_code == 404
    assert seeded.post("/api/coach/diet-suggestion", headers=hc, json=SUGESTIA).status_code == 404
    # Katalog produktów (źródło dla zlecenia 2) i plany żywieniowe nietknięte.
    assert seeded.get("/api/coach/food-products", headers=hc).status_code == 200
    assert seeded.get("/api/templates", headers=hc).status_code == 200
    assert seeded.get("/api/diet/profiles", headers=hc).status_code == 200


def test_z_flaga_trasy_dzialaja_jak_dotad(seeded, monkeypatch):
    hc = login(seeded, COACH)
    monkeypatch.setattr(settings, "diet_wizard_enabled", True)
    assert seeded.get("/api/health").json()["features"]["diet_wizard"] is True
    # Walidacja wejścia (422) dowodzi, że trasa istnieje; pełną logikę sprawdza test_diet_wizard.py.
    assert seeded.post("/api/coach/diet-wizard", headers=hc, json={}).status_code == 422
    assert seeded.post("/api/coach/diet-suggestion", headers=hc, json={}).status_code == 422
