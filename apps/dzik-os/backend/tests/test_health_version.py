"""Health identyfikuje uruchomioną wersję (audyt P1-5, 0.53.3)."""

from dzik_os import __version__


def test_health_zwraca_wersje_build_i_migracje(client):
    d = client.get("/api/health").json()
    assert d["ok"] is True
    assert d["version"]  # "dev" lokalnie, wersja z CHANGELOG na produkcji
    assert d["build"]
    assert isinstance(d["migration"], int) and d["migration"] > 0


def test_wersja_pakietu_nie_jest_zerowa():
    """Audyt P1-2: pakiet nie może wiecznie twierdzić, że jest 0.1.0."""
    assert __version__ != "0.1.0"
