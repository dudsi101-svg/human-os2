"""Testowa wysyłka e-maila przez skonfigurowanego dostawcę (0.52.3).

Użycie (lokalnie albo na maszynie Fly przez `flyctl ssh console`):

    python -m dzik_os.test_poczty adres@example.com

Sens istnienia: po ustawieniu sekretów SMTP konfiguracja ma być
UDOWODNIONA jedną wysyłką, a nie przyjęta na wiarę — workflow
„Sekrety produkcji (Fly.io)" wywołuje ten moduł po restarcie maszyny.
Kod wyjścia 0 wyłącznie przy potwierdzonej wysyłce.

Adres odbiorcy przychodzi argumentem CLI świadomie: to nie sekret,
a moduł nie loguje niczego ponad fakt i wynik (zasady dostawcy —
zero PII w logach — obowiązują bez zmian).
"""

from __future__ import annotations

import sys

from .config import settings
from .notifications_provider import provider


def wyslij_test(adres: str) -> bool:
    """Wysyła jeden testowy e-mail. Zwraca wynik dostawcy."""
    return provider.send_email(
        to=adres,
        subject="Dzik OS — test poczty",
        body=(
            "To jest testowa wiadomość z aplikacji Dzik OS.\n\n"
            "Jeśli ją czytasz, konfiguracja SMTP działa: zaproszenia "
            "klientów, resety haseł i poniedziałkowy digest będą "
            "docierać.\n\n"
            f"Aplikacja: {settings.public_base_url or 'adres nieustawiony'}"
        ),
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or "@" not in args[0]:
        print("Użycie: python -m dzik_os.test_poczty adres@example.com",
              file=sys.stderr)
        return 2
    if provider.name == "null":
        print(
            "BŁĄD: dostawca poczty to 'null' — brak DZIK_SMTP_HOST "
            "w środowisku. Ustaw sekrety SMTP i spróbuj ponownie.",
            file=sys.stderr,
        )
        return 1
    if wyslij_test(args[0]):
        print(f"Wysłano testowy e-mail (dostawca: {provider.name}).")
        return 0
    print(
        "BŁĄD: dostawca odmówił wysyłki — szczegóły (klasa wyjątku) "
        "w logu aplikacji.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
