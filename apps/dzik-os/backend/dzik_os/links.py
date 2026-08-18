"""Budowanie publicznych linków aplikacji (aktywacja konta, reset hasła).

Token jest umieszczany we FRAGMENCIE adresu (#token), nie w query stringu:
fragment nigdy nie jest wysyłany do serwera, więc token nie trafia do
logów dostępowych (uvicorn/proxy logują pełny URL z query). Frontend
odczytuje go z location.hash.
"""

from __future__ import annotations

from fastapi import Request

from .config import settings


def public_base_url(request: Request) -> str:
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


def activation_link(request: Request, token: str) -> str:
    return f"{public_base_url(request)}/aktywacja#{token}"


def password_reset_link(request: Request, token: str) -> str:
    return f"{public_base_url(request)}/reset-hasla#{token}"
