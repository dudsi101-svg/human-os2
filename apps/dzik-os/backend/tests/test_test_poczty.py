"""Testowa wysyłka poczty (0.52.3): fake dostawcy + odmowa bez konfiguracji."""

from dzik_os import test_poczty


class FakeProvider:
    name = "smtp"

    def __init__(self, wynik: bool):
        self.wynik = wynik
        self.wyslane: list[dict] = []

    def send_email(self, *, to: str, subject: str, body: str) -> bool:
        self.wyslane.append({"to": to, "subject": subject, "body": body})
        return self.wynik


def test_wysyla_i_zwraca_zero_przy_sukcesie(monkeypatch):
    fake = FakeProvider(True)
    monkeypatch.setattr(test_poczty, "provider", fake)
    assert test_poczty.main(["ktos@example.com"]) == 0
    assert fake.wyslane[0]["to"] == "ktos@example.com"
    assert "test poczty" in fake.wyslane[0]["subject"]


def test_kod_bledu_gdy_dostawca_odmawia(monkeypatch):
    monkeypatch.setattr(test_poczty, "provider", FakeProvider(False))
    assert test_poczty.main(["ktos@example.com"]) == 1


def test_odmawia_bez_konfiguracji_smtp(monkeypatch):
    class NullProvider:
        name = "null"

        def send_email(self, **kw) -> bool:  # pragma: no cover
            raise AssertionError("null nie może wysyłać")

    monkeypatch.setattr(test_poczty, "provider", NullProvider())
    assert test_poczty.main(["ktos@example.com"]) == 1


def test_walidacja_argumentow():
    assert test_poczty.main([]) == 2
    assert test_poczty.main(["nie-adres"]) == 2
