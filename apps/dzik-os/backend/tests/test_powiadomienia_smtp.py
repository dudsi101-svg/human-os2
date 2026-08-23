"""Poczta wychodząca — bloker nr 4 bramki GO/NO-GO.

„E-mail nie wychodzi: przypomnienia o płatnościach i digest poniedziałkowy
nigdzie nie docierają" — funkcja miała ścieżkę kodu, której nigdy nie
wykonano. Te testy uruchamiają ją naprawdę, przeciw prawdziwemu serwerowi
SMTP postawionemu na czas testu, i sprawdzają, że list DOCHODZI.

Pilnują też trzech zasad, bez których ta funkcja byłaby groźniejsza niż
jej brak: nie rzuca wyjątkiem, ma limit czasu, nie loguje PII.
"""

from __future__ import annotations

import socket
import threading
import unittest

from dzik_os.notifications_provider import (
    NullNotificationProvider,
    SMTPNotificationProvider,
)


class _SerwerSMTP:
    """Minimalny, prawdziwy serwer SMTP na jedno połączenie.

    Świadomie bez zależności zewnętrznej: `aiosmtpd` nie jest w zależnościach
    projektu, a dokładanie paczki tylko po to, żeby przetestować 60 linii,
    byłoby gorszym interesem niż te 40 linii gniazd.
    """

    def __init__(self) -> None:
        self.odebrane: list[str] = []
        self._gniazdo = socket.socket()
        self._gniazdo.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._gniazdo.bind(("127.0.0.1", 0))
        self._gniazdo.listen(1)
        self.port = self._gniazdo.getsockname()[1]
        self._watek = threading.Thread(target=self._obsluz, daemon=True)
        self._watek.start()

    def _obsluz(self) -> None:
        try:
            polaczenie, _ = self._gniazdo.accept()
        except OSError:
            return
        strumien = polaczenie.makefile("rwb")
        polaczenie.sendall(b"220 test ESMTP\r\n")
        dane: list[bytes] = []
        w_danych = False
        while True:
            linia = strumien.readline()
            if not linia:
                break
            if w_danych:
                if linia == b".\r\n":
                    self.odebrane.append(b"".join(dane).decode())
                    polaczenie.sendall(b"250 OK\r\n")
                    w_danych = False
                    continue
                dane.append(linia)
                continue
            polecenie = linia.upper()
            if polecenie.startswith(b"EHLO"):
                polaczenie.sendall(b"250-test\r\n250 SIZE 10240000\r\n")
            elif polecenie.startswith(b"DATA"):
                polaczenie.sendall(b"354 dawaj\r\n")
                w_danych = True
            elif polecenie.startswith(b"QUIT"):
                polaczenie.sendall(b"221 pa\r\n")
                break
            else:
                polaczenie.sendall(b"250 OK\r\n")
        polaczenie.close()

    def zamknij(self) -> None:
        self._gniazdo.close()


def _provider(port: int, **nadpisz) -> SMTPNotificationProvider:
    parametry = {"host": "127.0.0.1", "port": port, "user": "", "password": "",
                 "sender": "dzik@example.com", "security": "none", "timeout": 5}
    parametry.update(nadpisz)
    return SMTPNotificationProvider(**parametry)


class TestWysylka(unittest.TestCase):
    def test_list_naprawde_dochodzi(self):
        """Sedno blokera nr 4: ta ścieżka kodu nigdy się nie wykonała."""
        serwer = _SerwerSMTP()
        try:
            wynik = _provider(serwer.port).send_email(
                to="trener@example.com",
                subject="Zaległa płatność",
                body="Masz nieopłaconą ratę. Szczegóły w aplikacji.",
            )
        finally:
            serwer.zamknij()
        self.assertTrue(wynik)
        self.assertEqual(len(serwer.odebrane), 1)
        list_ = serwer.odebrane[0]
        self.assertIn("To: trener@example.com", list_)
        self.assertIn("Masz nieopłaconą ratę", list_)

    def test_polskie_znaki_w_temacie_przezywaja(self):
        """Temat jedzie przez RFC 2047; bez tego trener dostawałby krzaki."""
        serwer = _SerwerSMTP()
        try:
            _provider(serwer.port).send_email(
                to="a@example.com", subject="Zaległość — świadczenie", body="treść")
        finally:
            serwer.zamknij()
        import email
        wiadomosc = email.message_from_string(serwer.odebrane[0])
        temat = str(email.header.make_header(email.header.decode_header(wiadomosc["Subject"])))
        self.assertEqual(temat, "Zaległość — świadczenie")


class TestAwariaNieWywracaAplikacji(unittest.TestCase):
    def test_brak_serwera_zwraca_false_zamiast_wyjatku(self):
        """Powiadomienie jest kanałem POBOCZNYM. Awaria poczty nie ma prawa
        wywrócić zapisu raportu ani założenia klienta."""
        wolny = socket.socket()
        wolny.bind(("127.0.0.1", 0))
        port = wolny.getsockname()[1]
        wolny.close()  # nikt nie słucha
        self.assertFalse(_provider(port, timeout=2).send_email(
            to="a@example.com", subject="t", body="b"))

    def test_log_awarii_nie_zawiera_adresu_ani_tresci(self):
        """Komunikat serwera SMTP potrafi zawierać adres odbiorcy, dlatego
        logujemy wyłącznie NAZWĘ KLASY wyjątku."""
        from dzik_os import observability
        zapisane: list[str] = []
        pierwotny = observability.log_json
        observability.log_json = lambda zdarzenie, **reszta: zapisane.append(
            f"{zdarzenie} {reszta}")
        try:
            wolny = socket.socket()
            wolny.bind(("127.0.0.1", 0))
            port = wolny.getsockname()[1]
            wolny.close()
            _provider(port, timeout=2).send_email(
                to="tajny.adres@example.com", subject="Wyniki badań", body="poufne")
        finally:
            observability.log_json = pierwotny
        polaczone = " ".join(zapisane)
        self.assertIn("email_send_failed", polaczone)
        for pii in ("tajny.adres", "Wyniki badań", "poufne"):
            self.assertNotIn(pii, polaczone, f"PII w logu: {pii}")


class TestWyborDostawcy(unittest.TestCase):
    def test_bez_konfiguracji_nic_nie_wychodzi(self):
        """Aplikacja bez `DZIK_SMTP_HOST` zachowuje się DOKŁADNIE jak przed
        0.40.0. Włączenie poczty jest decyzją operatora, nie domyślną."""
        from dzik_os import notifications_provider
        from dzik_os.config import settings
        pierwotny = settings.smtp_host
        settings.smtp_host = ""
        try:
            wybrany = notifications_provider._zbuduj_provider()
        finally:
            settings.smtp_host = pierwotny
        self.assertIsInstance(wybrany, NullNotificationProvider)
        self.assertFalse(wybrany.send_email(to="a@example.com", subject="t", body="b"))

    def test_z_konfiguracja_wybiera_smtp(self):
        from dzik_os import notifications_provider
        from dzik_os.config import settings
        pierwotny = settings.smtp_host
        settings.smtp_host = "poczta.example.com"
        try:
            wybrany = notifications_provider._zbuduj_provider()
        finally:
            settings.smtp_host = pierwotny
        self.assertIsInstance(wybrany, SMTPNotificationProvider)
        self.assertEqual(wybrany.name, "smtp")


if __name__ == "__main__":
    unittest.main()
