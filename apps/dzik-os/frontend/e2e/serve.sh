#!/usr/bin/env bash
# Backend dla testów E2E: świeża baza, dane demo, zbudowany frontend.
#
# Testy chodzą po tej samej ścieżce co produkcja — backend serwuje `dist/`,
# więc sprawdzamy realny sposób podania aplikacji, a nie dev-server z proxy.
#
# Baza ląduje w katalogu tymczasowym i jest kasowana przy każdym starcie:
# testy E2E muszą zaczynać od znanego stanu, inaczej pierwsze uruchomienie
# różni się od dziesiątego.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND="$(dirname "$HERE")"
BACKEND="$(dirname "$FRONTEND")/backend"
WORKDIR="${DZIK_E2E_DIR:-/tmp/dzik-e2e}"
PORT="${DZIK_E2E_PORT:-8099}"

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR/pliki"

export DZIK_DATABASE_URL="sqlite:///$WORKDIR/dzik.db"
export DZIK_EVENT_STORE="$WORKDIR/audit.db"
export DZIK_FILES_DIR="$WORKDIR/pliki"
export DZIK_FRONTEND_DIST="$FRONTEND/dist"
export DZIK_SECRET_KEY="e2e-tylko-do-testow-nie-uzywac-nigdzie-indziej"

# MFA jest wyłączone WYŁĄCZNIE w E2E i wyłącznie świadomie: bramka MFA ma
# własne pokrycie w testach backendu (routers/auth.py), a tutaj chodzi
# o ścieżki interfejsu, do których trener bez TOTP w ogóle by nie dotarł.
# Nie jest to konfiguracja produkcyjna — produkcja trzyma domyślne
# "COACH,ADMIN" (config.py).
export DZIK_MFA_REQUIRED_ROLES=""

cd "$BACKEND"
# Import `models` przed migracją jest konieczny: świeża baza dostaje schemat
# z `Base.metadata.create_all`, a metadane są puste, dopóki moduł z modelami
# nie zostanie zaimportowany (db.py sam go nie ciągnie).
python -c "
import dzik_os.models  # noqa: F401  — rejestruje tabele w Base.metadata
from dzik_os.db import run_migrations
run_migrations()
"
python -m dzik_os.seed

exec python -m uvicorn dzik_os.main:app --host 127.0.0.1 --port "$PORT" --log-level warning
