#!/usr/bin/env python3
"""Diagnostyka SMTP do uruchomienia z maszyny Fly:

    fly ssh console -a NAZWA_APKI -C "python smtp_check.py"

Cztery kroki: zmienne środowiskowe → DNS → TCP → uwierzytelnienie.
Skrypt NIE wysyła wiadomości i NIGDY nie wypisuje hasła.
Kod wyjścia 0 = wszystko OK, 1 = pierwszy nieudany krok.
"""

import os
import socket
import smtplib
import ssl
import sys
from email.utils import parseaddr

REQUIRED = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM"]


def ok(step, msg):
    print(f"[OK]   {step}: {msg}")


def fail(step, msg, hint=""):
    print(f"[BŁĄD] {step}: {msg}")
    if hint:
        print(f"       → {hint}")
    sys.exit(1)


def step1_env():
    missing = [k for k in REQUIRED if not (os.environ.get(k) or "").strip()]
    if missing:
        fail("1/4 zmienne", f"brakuje: {', '.join(missing)}",
             "fly secrets set -a NAZWA_APKI KLUCZ=wartość, potem Deploy Secrets")

    host = os.environ["SMTP_HOST"].strip()
    port = os.environ["SMTP_PORT"].strip()
    user = os.environ["SMTP_USER"].strip()
    pwd = os.environ["SMTP_PASSWORD"]
    sender = parseaddr(os.environ["MAIL_FROM"])[1]

    if not port.isdigit():
        fail("1/4 zmienne", f"SMTP_PORT nie jest liczbą: {port!r}")
    if "@" not in sender:
        fail("1/4 zmienne", f"MAIL_FROM bez poprawnego adresu: {os.environ['MAIL_FROM']!r}",
             'format: "Nazwa <adres@domena.pl>"')

    ok("1/4 zmienne", f"host={host} port={port} user={user} from={sender} "
                      f"hasło={len(pwd)} znaków")

    domain = sender.rsplit("@", 1)[1]
    if domain not in host and not host.endswith(("brevo.com", "sendinblue.com")):
        print(f"       uwaga: domena nadawcy ({domain}) musi być uwierzytelniona u dostawcy,")
        print( "       inaczej serwer odrzuci wysyłkę kodem 550.")
    return host, int(port), user, pwd


def step2_dns(host):
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        fail("2/4 DNS", f"nie mogę rozwiązać {host}: {exc}",
             "literówka w SMTP_HOST albo brak DNS na maszynie")
    addrs = sorted({i[4][0] for i in infos})
    ok("2/4 DNS", f"{host} → {', '.join(addrs)}")
    if not any(":" not in a for a in addrs):
        print("       uwaga: host ma tylko IPv6 — na Fly bywa źródłem timeoutów na 587.")


def step3_tcp(host, port):
    try:
        with socket.create_connection((host, port), timeout=10) as sock:
            banner = sock.recv(256).decode("utf-8", "replace").strip()
    except OSError as exc:
        fail("3/4 TCP", f"brak połączenia z {host}:{port} — {exc}",
             "port zablokowany lub host nieosiągalny; sprawdź, czy u dostawcy "
             "nie włączono filtrowania po adresach IP")
    ok("3/4 TCP", f"połączono, baner: {banner[:80] or '(brak)'}")


def step4_auth(host, port, user, pwd):
    context = ssl.create_default_context()
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=15, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            server.ehlo()
            if not server.has_extn("starttls"):
                fail("4/4 auth", "serwer nie oferuje STARTTLS na tym porcie",
                     "spróbuj SMTP_PORT=465")
            server.starttls(context=context)
            server.ehlo()
        server.login(user, pwd)
        server.quit()
    except smtplib.SMTPAuthenticationError as exc:
        fail("4/4 auth", f"odrzucone dane logowania ({exc.smtp_code})",
             "w SMTP_PASSWORD musi być klucz SMTP, nie klucz API i nie hasło do konta")
    except (smtplib.SMTPException, OSError) as exc:
        fail("4/4 auth", f"{type(exc).__name__}: {exc}")
    ok("4/4 auth", "uwierzytelnienie przyjęte, TLS działa")


if __name__ == "__main__":
    host, port, user, pwd = step1_env()
    step2_dns(host)
    step3_tcp(host, port)
    step4_auth(host, port, user, pwd)
    print("\nWszystkie 4 kroki OK. Kanał SMTP jest sprawny — "
          "jeśli maile nadal nie docierają, przyczyna jest po stronie "
          "uwierzytelnienia domeny (SPF/DKIM) albo filtrów odbiorcy.")
