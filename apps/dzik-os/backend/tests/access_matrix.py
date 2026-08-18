"""Macierz uprawnień: deklaracja dostępu dla KAŻDEJ operacji API.

Po co to istnieje
-----------------
Zewnętrzny audyt (18.08.2026) wskazał, że publiczne 401 nie dowodzi izolacji
między prawidłowo zalogowanymi kontami — brakowało systematycznego dowodu,
że klient A nie sięgnie po dane klienta B, a trener bez relacji po cudzego
podopiecznego. Aplikacja ma 182 operacje API; ręczna lista przypadków
zardzewiałaby przy pierwszym nowym endpoincie.

Dlatego macierz jest **wyliczana z aplikacji**, a nie pisana z pamięci:
`test_access_matrix.py` porównuje ten rejestr ze schematem OpenAPI i
przerywa build, gdy pojawi się operacja bez zadeklarowanej klasy dostępu
albo gdy w rejestrze zostanie wpis po usuniętej trasie. Dodanie endpointu
wymaga więc świadomej decyzji „kto ma tu dostęp", a nie milczącej zgody.

Deklaracja to jednak dopiero połowa: klasy są **weryfikowane wykonaniem**
(prawdziwe żądania prawdziwymi kontami), bo deklaracja może kłamać —
przy budowie tej macierzy heurystyka uznała `/api/metrics` za publiczne,
a w kodzie endpoint ma `require_role("ADMIN")`.
"""

from __future__ import annotations

import re
from enum import Enum


class Access(str, Enum):
    """Klasa dostępu operacji API."""

    #: Bez logowania (logowanie, aktywacja konta, reset hasła, health).
    PUBLIC = "PUBLIC"
    #: Dowolny zalogowany użytkownik — operuje wyłącznie na SWOICH danych
    #: (identyfikator brany z sesji, nie ze ścieżki).
    AUTHENTICATED = "AUTHENTICATED"
    #: Ścieżka zawiera {client_id}: dostęp ma sam klient albo jego trener
    #: przy aktywnej relacji i nieodwołanej zgodzie (resolve_client_access).
    CLIENT_SCOPED = "CLIENT_SCOPED"
    #: Wymaga roli COACH.
    COACH_ONLY = "COACH_ONLY"
    #: Wymaga roli ADMIN (rola techniczna, bez danych zdrowotnych).
    ADMIN_ONLY = "ADMIN_ONLY"
    #: Ścieżka wskazuje zasób po jego własnym id (plan, raport, plik,
    #: wątek…); autoryzacja wynika z właściciela zasobu, więc obcy
    #: użytkownik musi dostać odmowę mimo poprawnego formatu identyfikatora.
    RESOURCE_SCOPED = "RESOURCE_SCOPED"


#: Kody, które uznajemy za prawidłową ODMOWĘ.
#: 404 jest równoprawne z 403 — aplikacja świadomie nie ujawnia istnienia
#: cudzych zasobów (patrz authz.resolve_client_access).
DENIED_STATUSES = frozenset({401, 403, 404})

#: Kody odmowy dla żądania BEZ tokenu.
UNAUTHENTICATED_STATUSES = frozenset({401, 403})

MATRIX: dict[tuple[str, str], Access] = {
    ("GET", "/api/admin/audit/verify"): Access.ADMIN_ONLY,
    ("GET", "/api/admin/receipts"): Access.ADMIN_ONLY,
    ("GET", "/api/admin/users"): Access.ADMIN_ONLY,
    ("POST", "/api/auth/activate"): Access.PUBLIC,
    # Ekran aktywacji działa PRZED zalogowaniem; jednolite 404 dla każdego
    # nieważnego tokenu (auth.py: bez rozróżniania wygasły/użyty/nieistniejący).
    ("POST", "/api/auth/activation/inspect"): Access.PUBLIC,
    ("GET", "/api/auth/brand"): Access.PUBLIC,
    ("POST", "/api/auth/change-password"): Access.AUTHENTICATED,
    ("POST", "/api/auth/login"): Access.PUBLIC,
    # Celowo bez current_user — wylogowanie ma działać także dla sesji
    # wygasłej (auth.py). Nie zwraca danych, więc brak tokenu jest bezpieczny.
    ("POST", "/api/auth/logout"): Access.PUBLIC,
    ("GET", "/api/auth/me"): Access.AUTHENTICATED,
    ("POST", "/api/auth/mfa/disable"): Access.AUTHENTICATED,
    ("POST", "/api/auth/mfa/enable"): Access.AUTHENTICATED,
    ("POST", "/api/auth/mfa/recovery-codes/regenerate"): Access.AUTHENTICATED,
    ("POST", "/api/auth/mfa/setup"): Access.AUTHENTICATED,
    ("GET", "/api/auth/mfa/status"): Access.AUTHENTICATED,
    ("POST", "/api/auth/mfa/verify"): Access.PUBLIC,
    ("POST", "/api/auth/password-reset/confirm"): Access.PUBLIC,
    ("POST", "/api/auth/password-reset/request"): Access.PUBLIC,
    ("GET", "/api/auth/security-events"): Access.AUTHENTICATED,
    ("GET", "/api/auth/sessions"): Access.AUTHENTICATED,
    ("POST", "/api/auth/sessions/revoke-others"): Access.AUTHENTICATED,
    ("POST", "/api/auth/sessions/{session_id}/revoke"): Access.AUTHENTICATED,
    # Statyczny katalog neutralnych jednostek wyniku — bez danych osób.
    ("GET", "/api/challenge-units"): Access.PUBLIC,
    ("GET", "/api/challenges/{challenge_id}"): Access.RESOURCE_SCOPED,
    ("POST", "/api/challenges/{challenge_id}/activate"): Access.RESOURCE_SCOPED,
    ("POST", "/api/challenges/{challenge_id}/block"): Access.RESOURCE_SCOPED,
    ("POST", "/api/challenges/{challenge_id}/cancel"): Access.RESOURCE_SCOPED,
    ("POST", "/api/challenges/{challenge_id}/decline"): Access.RESOURCE_SCOPED,
    ("GET", "/api/challenges/{challenge_id}/entries"): Access.RESOURCE_SCOPED,
    ("POST", "/api/challenges/{challenge_id}/entries"): Access.RESOURCE_SCOPED,
    ("POST", "/api/challenges/{challenge_id}/entries/{entry_id}/correct"): Access.RESOURCE_SCOPED,
    ("POST", "/api/challenges/{challenge_id}/finish"): Access.RESOURCE_SCOPED,
    ("POST", "/api/challenges/{challenge_id}/invite"): Access.RESOURCE_SCOPED,
    ("POST", "/api/challenges/{challenge_id}/join"): Access.RESOURCE_SCOPED,
    ("POST", "/api/challenges/{challenge_id}/leave"): Access.RESOURCE_SCOPED,
    ("PATCH", "/api/challenges/{challenge_id}/me"): Access.RESOURCE_SCOPED,
    ("POST", "/api/challenges/{challenge_id}/participants/{participant_id}/remove"): Access.RESOURCE_SCOPED,
    ("POST", "/api/challenges/{challenge_id}/participants/{participant_id}/reset-alias"): Access.RESOURCE_SCOPED,
    ("POST", "/api/challenges/{challenge_id}/report"): Access.RESOURCE_SCOPED,
    ("GET", "/api/challenges/{challenge_id}/reports"): Access.RESOURCE_SCOPED,
    ("POST", "/api/challenges/{challenge_id}/reports/{report_id}/resolve"): Access.RESOURCE_SCOPED,
    ("POST", "/api/challenges/{challenge_id}/unblock"): Access.RESOURCE_SCOPED,
    ("POST", "/api/challenges/{challenge_id}/withdraw"): Access.RESOURCE_SCOPED,
    ("POST", "/api/checkins"): Access.RESOURCE_SCOPED,
    ("POST", "/api/checkins/{checkin_id}/ai-summary"): Access.RESOURCE_SCOPED,
    ("POST", "/api/checkins/{checkin_id}/photos"): Access.RESOURCE_SCOPED,
    ("POST", "/api/checkins/{checkin_id}/review"): Access.RESOURCE_SCOPED,
    ("GET", "/api/checkins/{checkin_id}/revisions"): Access.RESOURCE_SCOPED,
    ("GET", "/api/clients/{client_id}/checkins"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/documents"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/goals"): Access.CLIENT_SCOPED,
    ("POST", "/api/clients/{client_id}/goals"): Access.CLIENT_SCOPED,
    ("POST", "/api/clients/{client_id}/goals/{goal_id}/status"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/measurements"): Access.CLIENT_SCOPED,
    ("POST", "/api/clients/{client_id}/measurements"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/metric-definitions"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/monitoring"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/nutrition"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/nutrition-log"): Access.CLIENT_SCOPED,
    ("POST", "/api/clients/{client_id}/nutrition-log"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/observations"): Access.CLIENT_SCOPED,
    ("POST", "/api/clients/{client_id}/observations"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/onboarding"): Access.CLIENT_SCOPED,
    ("POST", "/api/clients/{client_id}/onboarding/answer"): Access.CLIENT_SCOPED,
    ("POST", "/api/clients/{client_id}/onboarding/approve"): Access.CLIENT_SCOPED,
    ("POST", "/api/clients/{client_id}/onboarding/back"): Access.CLIENT_SCOPED,
    ("POST", "/api/clients/{client_id}/onboarding/coach-approve"): Access.CLIENT_SCOPED,
    ("POST", "/api/clients/{client_id}/onboarding/pause"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/onboarding/review"): Access.CLIENT_SCOPED,
    ("POST", "/api/clients/{client_id}/onboarding/start"): Access.CLIENT_SCOPED,
    ("POST", "/api/clients/{client_id}/onboarding/summary"): Access.CLIENT_SCOPED,
    ("PUT", "/api/clients/{client_id}/onboarding/summary"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/payments"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/personal-records"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/photos"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/plans"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/profile"): Access.CLIENT_SCOPED,
    ("PUT", "/api/clients/{client_id}/profile"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/profile/history"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/reminders"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/schedule"): Access.CLIENT_SCOPED,
    ("POST", "/api/clients/{client_id}/schedule/{item_id}/complete"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/strength-series"): Access.CLIENT_SCOPED,
    ("GET", "/api/clients/{client_id}/workouts"): Access.CLIENT_SCOPED,
    ("POST", "/api/clients/{client_id}/workouts"): Access.CLIENT_SCOPED,
    # Asystent trenera: rola COACH plus własność zadania — cudze zadanie
    # kończy się 404 (assistant.py::_owned_task), więc trasy z {task_id}
    # są RESOURCE_SCOPED, a nie samym COACH_ONLY.
    ("GET", "/api/coach/assistant/status"): Access.COACH_ONLY,
    ("POST", "/api/coach/assistant/tasks"): Access.COACH_ONLY,
    ("DELETE", "/api/coach/assistant/tasks/{task_id}"): Access.RESOURCE_SCOPED,
    ("GET", "/api/coach/assistant/tasks/{task_id}"): Access.RESOURCE_SCOPED,
    ("POST", "/api/coach/assistant/tasks/{task_id}/applied"): Access.RESOURCE_SCOPED,
    ("POST", "/api/coach/assistant/tasks/{task_id}/cancel"): Access.RESOURCE_SCOPED,
    ("GET", "/api/coach/challenges"): Access.COACH_ONLY,
    ("POST", "/api/coach/challenges"): Access.COACH_ONLY,
    ("GET", "/api/coach/clients"): Access.COACH_ONLY,
    ("POST", "/api/coach/clients"): Access.COACH_ONLY,
    ("GET", "/api/coach/clients/{client_id}/history"): Access.CLIENT_SCOPED,
    ("POST", "/api/coach/clients/{client_id}/invitations"): Access.CLIENT_SCOPED,
    ("POST", "/api/coach/clients/{client_id}/invitations/cancel"): Access.CLIENT_SCOPED,
    ("GET", "/api/coach/clients/{client_id}/overview"): Access.CLIENT_SCOPED,
    ("POST", "/api/coach/clients/{client_id}/relationship-status"): Access.CLIENT_SCOPED,
    ("GET", "/api/coach/consult-slots"): Access.COACH_ONLY,
    ("POST", "/api/coach/consult-slots"): Access.COACH_ONLY,
    ("POST", "/api/coach/consult-slots/{slot_id}/cancel"): Access.COACH_ONLY,
    ("GET", "/api/coach/dashboard"): Access.COACH_ONLY,
    ("POST", "/api/coach/diet-suggestion"): Access.COACH_ONLY,
    ("GET", "/api/coach/exercises"): Access.COACH_ONLY,
    ("POST", "/api/coach/exercises"): Access.COACH_ONLY,
    # Wymaga roli COACH (require_role) i niczego nie zapisuje — zwraca
    # wyłącznie propozycję pól edytora z wklejonego opisu.
    ("POST", "/api/coach/exercises/parse-description"): Access.COACH_ONLY,
    # Ostatnio używane ćwiczenia TEGO trenera (identyfikator z sesji).
    ("GET", "/api/coach/exercises/recent"): Access.COACH_ONLY,
    ("GET", "/api/coach/exercises/{item_id}"): Access.COACH_ONLY,
    ("PUT", "/api/coach/exercises/{item_id}"): Access.COACH_ONLY,
    ("POST", "/api/coach/exercises/{item_id}/status"): Access.COACH_ONLY,
    ("GET", "/api/coach/food-products"): Access.COACH_ONLY,
    ("POST", "/api/coach/food-products"): Access.COACH_ONLY,
    ("GET", "/api/coach/food-products/export"): Access.COACH_ONLY,
    ("POST", "/api/coach/food-products/import"): Access.COACH_ONLY,
    ("PUT", "/api/coach/food-products/{item_id}"): Access.COACH_ONLY,
    ("POST", "/api/coach/food-products/{item_id}/status"): Access.COACH_ONLY,
    ("GET", "/api/coach/knowledge"): Access.COACH_ONLY,
    ("POST", "/api/coach/knowledge"): Access.COACH_ONLY,
    ("PUT", "/api/coach/knowledge/{item_id}"): Access.COACH_ONLY,
    ("POST", "/api/coach/knowledge/{item_id}/status"): Access.COACH_ONLY,
    ("GET", "/api/coach/weekly-digest"): Access.COACH_ONLY,
    ("POST", "/api/consult-slots/{slot_id}/book"): Access.RESOURCE_SCOPED,
    ("POST", "/api/consult-slots/{slot_id}/unbook"): Access.RESOURCE_SCOPED,
    ("POST", "/api/documents"): Access.RESOURCE_SCOPED,
    ("GET", "/api/exercise-dictionaries"): Access.RESOURCE_SCOPED,
    ("POST", "/api/files"): Access.RESOURCE_SCOPED,
    ("GET", "/api/files/{file_id}"): Access.RESOURCE_SCOPED,
    ("POST", "/api/food-products/portion"): Access.RESOURCE_SCOPED,
    ("GET", "/api/health"): Access.PUBLIC,
    ("GET", "/api/me/challenges"): Access.AUTHENTICATED,
    ("POST", "/api/me/challenges"): Access.AUTHENTICATED,
    ("GET", "/api/me/consents"): Access.AUTHENTICATED,
    ("POST", "/api/me/consents"): Access.AUTHENTICATED,
    ("POST", "/api/me/consents/decline"): Access.AUTHENTICATED,
    ("POST", "/api/me/consents/{consent_id}/confirm"): Access.AUTHENTICATED,
    ("POST", "/api/me/consents/{consent_id}/revoke"): Access.AUTHENTICATED,
    ("GET", "/api/me/consult-slots"): Access.AUTHENTICATED,
    ("POST", "/api/me/deletion-request"): Access.AUTHENTICATED,
    ("GET", "/api/me/exercises"): Access.AUTHENTICATED,
    ("GET", "/api/me/exercises/{item_id}"): Access.AUTHENTICATED,
    ("GET", "/api/me/export"): Access.AUTHENTICATED,
    ("GET", "/api/me/export.xlsx"): Access.AUTHENTICATED,
    ("GET", "/api/me/food-products"): Access.AUTHENTICATED,
    ("GET", "/api/me/knowledge"): Access.AUTHENTICATED,
    ("GET", "/api/me/today"): Access.AUTHENTICATED,
    ("POST", "/api/metric-definitions"): Access.AUTHENTICATED,
    ("GET", "/api/metrics"): Access.ADMIN_ONLY,
    ("GET", "/api/notifications"): Access.RESOURCE_SCOPED,
    ("POST", "/api/notifications/read-all"): Access.RESOURCE_SCOPED,
    ("GET", "/api/notifications/settings"): Access.RESOURCE_SCOPED,
    ("PUT", "/api/notifications/settings"): Access.RESOURCE_SCOPED,
    ("POST", "/api/notifications/{notification_id}/read"): Access.RESOURCE_SCOPED,
    ("POST", "/api/nutrition"): Access.RESOURCE_SCOPED,
    ("POST", "/api/nutrition/{plan_id}/supplements/reminders"): Access.RESOURCE_SCOPED,
    ("GET", "/api/nutrition/{plan_id}/versions"): Access.RESOURCE_SCOPED,
    ("POST", "/api/nutrition/{plan_id}/versions"): Access.RESOURCE_SCOPED,
    # Gotowość silnika dla WŁASNEGO konta (owner z sesji). Opcjonalne
    # `client_id` przechodzi przez resolve_client_access, ale nie jest
    # wymagane, więc klasą bazową operacji jest AUTHENTICATED.
    ("GET", "/api/ocr/status"): Access.AUTHENTICATED,
    # Zlecenie idzie na konto zlecającego; cudzy plik/dokument w ciele
    # żądania kończy się odmową (ocr.py: _require_ocr_file, deny na
    # document.client_id) — ale ścieżka nie niesie cudzego id, więc to nie
    # jest RESOURCE_SCOPED w rozumieniu tej macierzy.
    ("POST", "/api/ocr/tasks"): Access.AUTHENTICATED,
    ("DELETE", "/api/ocr/tasks/{task_id}"): Access.RESOURCE_SCOPED,
    ("GET", "/api/ocr/tasks/{task_id}"): Access.RESOURCE_SCOPED,
    ("POST", "/api/ocr/tasks/{task_id}/approve"): Access.RESOURCE_SCOPED,
    ("GET", "/api/payments/reconciliation"): Access.RESOURCE_SCOPED,
    ("POST", "/api/payments/records/{record_id}/adjust"): Access.RESOURCE_SCOPED,
    ("GET", "/api/payments/records/{record_id}/history"): Access.RESOURCE_SCOPED,
    ("POST", "/api/payments/records/{record_id}/mark-paid"): Access.RESOURCE_SCOPED,
    ("POST", "/api/payments/records/{record_id}/refund"): Access.RESOURCE_SCOPED,
    ("POST", "/api/payments/records/{record_id}/status"): Access.RESOURCE_SCOPED,
    ("POST", "/api/payments/schedules"): Access.RESOURCE_SCOPED,
    ("POST", "/api/payments/schedules/{schedule_id}/records"): Access.RESOURCE_SCOPED,
    ("POST", "/api/payments/transactions/{transaction_id}/reverse"): Access.RESOURCE_SCOPED,
    ("POST", "/api/plans"): Access.RESOURCE_SCOPED,
    ("GET", "/api/plans/templates"): Access.RESOURCE_SCOPED,
    ("GET", "/api/plans/{plan_id}/versions"): Access.RESOURCE_SCOPED,
    ("POST", "/api/plans/{plan_id}/versions"): Access.RESOURCE_SCOPED,
    ("POST", "/api/plans/{template_id}/copy-to/{client_id}"): Access.CLIENT_SCOPED,
    ("GET", "/api/push/public-key"): Access.PUBLIC,
    ("POST", "/api/push/subscribe"): Access.RESOURCE_SCOPED,
    ("POST", "/api/push/unsubscribe"): Access.RESOURCE_SCOPED,
    ("GET", "/api/ready"): Access.PUBLIC,
    ("POST", "/api/reminders"): Access.RESOURCE_SCOPED,
    ("POST", "/api/schedule"): Access.RESOURCE_SCOPED,
    ("POST", "/api/schedule/{item_id}/status"): Access.RESOURCE_SCOPED,
    ("POST", "/api/telemetry/frontend-errors"): Access.PUBLIC,
    ("GET", "/api/threads"): Access.RESOURCE_SCOPED,
    ("GET", "/api/threads/events"): Access.RESOURCE_SCOPED,
    ("GET", "/api/threads/{thread_id}/messages"): Access.RESOURCE_SCOPED,
    ("POST", "/api/threads/{thread_id}/messages"): Access.RESOURCE_SCOPED,
    ("POST", "/api/threads/{thread_id}/read"): Access.RESOURCE_SCOPED,}


# --- Generowanie minimalnych ciał żądań ------------------------------------
# Bez poprawnego ciała FastAPI odrzuca żądanie z kodem 422 (walidacja)
# ZANIM wykona się autoryzacja — a 422 nie dowodzi izolacji. Dlatego dla
# operacji z ciałem budujemy najmniejszy ładunek spełniający schemat, żeby
# żądanie faktycznie doszło do warstwy uprawnień.

_PRIMITIVE_SAMPLES = {
    "string": "x",
    "integer": 1,
    "number": 1.0,
    "boolean": True,
}


def sample_for_pattern(pattern: str | None) -> str | None:
    """Wartość pasująca do typowych wzorców używanych w schematach aplikacji:
    data kalendarzowa, czas, słownik dozwolonych wartości. Zwraca None, gdy
    wzorzec jest nierozpoznany (wtedy wracamy do wartości domyślnej)."""
    if not pattern:
        return None
    if "\\d{4}-\\d{2}-\\d{2}" in pattern:
        return "2026-01-05T10:00" if "T" in pattern else "2026-01-05"
    if "\\d{2}:\\d{2}" in pattern:
        return "10:00"
    alternatives = re.fullmatch(r"\^\(([^)]+)\)\$", pattern)
    if alternatives:
        return alternatives.group(1).split("|")[0]
    return None


def _resolve_ref(spec: dict, ref: str) -> dict:
    node: dict = spec
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def sample_for_schema(spec: dict, schema: dict, depth: int = 0) -> object:
    """Najmniejsza wartość spełniająca schemat (rekurencyjnie, z limitem)."""
    if depth > 6 or not isinstance(schema, dict):
        return "x"
    if "$ref" in schema:
        return sample_for_schema(spec, _resolve_ref(spec, schema["$ref"]), depth + 1)
    for combinator in ("anyOf", "oneOf", "allOf"):
        if combinator in schema:
            options = [o for o in schema[combinator] if o.get("type") != "null"]
            if options:
                return sample_for_schema(spec, options[0], depth + 1)
            return None
    if schema.get("enum"):
        return schema["enum"][0]
    if "default" in schema:
        return schema["default"]
    kind = schema.get("type")
    if kind == "object" or "properties" in schema:
        props = schema.get("properties", {})
        required = schema.get("required", list(props)[:1])
        return {
            name: sample_for_schema(spec, props[name], depth + 1)
            for name in required
            if name in props
        }
    if kind == "array":
        items = schema.get("items")
        # Jeden element zamiast pustej listy: część endpointów przyjmuje
        # WYŁĄCZNIE niepustą tablicę, a pusta kończyłaby się na walidacji.
        return [sample_for_schema(spec, items, depth + 1)] if items else []
    if kind == "string":
        fmt = schema.get("format")
        if fmt == "date":
            return "2026-01-05"
        if fmt == "date-time":
            return "2026-01-05T10:00:00"
        if fmt == "email":
            return "probe@example.com"
        # Walidacja pól z `pattern` (daty kalendarzowe, słowniki kategorii)
        # następuje PRZED autoryzacją, więc bez pasującej wartości żądanie
        # kończy się na 422 i nie dowodzi izolacji.
        sample = sample_for_pattern(schema.get("pattern"))
        if sample is not None:
            return sample
        return "x" * max(1, schema.get("minLength", 1))
    return _PRIMITIVE_SAMPLES.get(kind, "x")


def body_for_operation(spec: dict, method: str, path: str) -> dict | list | None:
    """Minimalne ciało JSON dla operacji albo None, gdy operacja go nie ma."""
    operation = spec["paths"].get(path, {}).get(method.lower())
    if not operation:
        return None
    content = (operation.get("requestBody") or {}).get("content", {})
    schema = content.get("application/json", {}).get("schema")
    if not schema:
        return None
    value = sample_for_schema(spec, schema)
    return value if isinstance(value, (dict, list)) else {}


#: Prefiks tras rejestrowanych wyłącznie przez testy (np. sztuczny endpoint
#: rzucający wyjątkiem w test_observability) — nie istnieją w produkcji,
#: więc nie podlegają deklaracji dostępu.
TEST_ONLY_PREFIX = "/api/_test/"


def operations(spec: dict) -> list[tuple[str, str]]:
    """Wszystkie operacje API ze schematu OpenAPI (metoda, ścieżka)."""
    found: list[tuple[str, str]] = []
    for path, methods in spec["paths"].items():
        if path.startswith(TEST_ONLY_PREFIX):
            continue
        for method in methods:
            upper = method.upper()
            if upper in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                found.append((upper, path))
    return sorted(found, key=lambda item: (item[1], item[0]))


def query_for_operation(spec: dict, method: str, path: str) -> dict:
    """Wymagane parametry query — bez nich FastAPI odrzuca żądanie kodem 422
    (walidacja) i nigdy nie dochodzi do sprawdzenia uprawnień, więc test
    izolacji nie miałby czego dowieść."""
    operation = spec["paths"].get(path, {}).get(method.lower())
    if not operation:
        return {}
    values: dict[str, object] = {}
    for parameter in operation.get("parameters", []):
        if parameter.get("in") != "query" or not parameter.get("required"):
            continue
        values[parameter["name"]] = sample_for_schema(spec, parameter.get("schema", {}))
    return values
