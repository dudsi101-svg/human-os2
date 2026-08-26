"""Wspólny system powiadomień i przypomnień (jeden model, wiele kanałów).

Jedno źródło prawdy dla wszystkich powiadomień aplikacji (trening,
suplement, raport, wiadomość, płatność, dokument, zmiana planu,
konsultacja): wiersz `Notification` w bazie. Kanały doręczenia:

* CENTER — centrum powiadomień w aplikacji (sam wiersz; pełna treść,
  widoczna wyłącznie po zalogowaniu),
* PUSH   — Web Push z treścią NEUTRALNĄ (tytuł kategorii + wezwanie do
  aplikacji; nigdy dane zdrowotne, kwoty, nazwy suplementów, treści
  wiadomości — Konstytucja Human OS / RODO),
* EMAIL  — opcjonalny kanał awaryjny (notifications_provider; domyślnie
  NullNotificationProvider), ta sama neutralna treść co push.

Idempotencja: `dedup_key` z UNIQUE(user_id, dedup_key) w bazie — restart
procesu nie duplikuje ani nie gubi powiadomień (zastępuje dawny dedup
`_sent` w pamięci pętli przypomnień). Terminy (`scheduled_at`) są liczone
w lokalnej strefie odbiorcy (users.timezone przez dates.tz_for_user —
DST rozstrzyga zoneinfo) i zapisywane w UTC.

Bramki sprawdzane PRZY WYSYŁCE (nie przy planowaniu): zadanie wykonane
(trening odhaczony / raport wysłany / płatność opłacona / źródło
wstrzymane), preferencje per kategoria × kanał, ciche godziny (wyciszają
push i e-mail; centrum zawsze dostaje wpis). Szczegóły i uzasadnienia:
docs/POWIADOMIENIA.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from . import notifications_provider, push_service
from .dates import local_now, tz_for_user
from .models import (
    Notification,
    NotificationPreference,
    NotificationSetting,
    PaymentRecord,
    Reminder,
    RoleGrant,
    ScheduleCompletion,
    ScheduleItem,
    User,
    WeeklyCheckin,
    new_id,
    now_iso,
)
from .observability import log_json, metrics
from .payment_state import DUE_STATUSES
from .realtime import bus

CHANNELS = ("PUSH", "CENTER", "EMAIL")

# Domyślne stany kanałów (brak wiersza preferencji): push i centrum
# włączone, e-mail wyłączony (kanał awaryjny — świadomy opt-in).
CHANNEL_DEFAULTS = {"PUSH": True, "CENTER": True, "EMAIL": False}
# Wyjątki od domyślnych kanałów per kategoria. E-mail jest domyślnie
# wyłączony wszędzie (kanał awaryjny), ale digest trenera bez e-maila nie
# miałby racji bytu — przy NullNotificationProvider i tak nic nie wychodzi,
# a trener może kanał wyłączyć w ustawieniach jak każdy inny.
CATEGORY_CHANNEL_DEFAULTS: dict[tuple[str, str], bool] = {
    ("PODSUMOWANIE", "EMAIL"): True,
    ("PODSUMOWANIE", "PUSH"): False,
}

# Maksymalne spóźnienie doręczenia zaplanowanego przypomnienia (nadganianie
# po restarcie/awarii). Starsze wiersze są tłumione jako "expired" —
# przypomnienie o treningu sprzed pół dnia byłoby szumem, nie pomocą.
LATE_SEND_MAX = timedelta(minutes=30)
# Zaległa należność przypomina o sobie co 7 dni od terminu (w sam dzień
# terminu zawsze) — patrz docs/PLATNOSCI.md i docs/POWIADOMIENIA.md.
PAYMENT_OVERDUE_EVERY_DAYS = 7


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    # Neutralny tytuł push/e-mail — bez szczegółów (ekran blokady).
    # SUPLEMENT celowo dostaje ogólne "Przypomnienie z harmonogramu":
    # sama nazwa kategorii zdradzałaby informację zdrowotną.
    push_title: str
    # Domyślny ekran docelowy w aplikacji po kliknięciu.
    default_url: str


CATEGORIES: dict[str, Category] = {
    c.key: c
    for c in [
        Category("TRENING", "Planowany trening", "Przypomnienie o treningu", "/"),
        Category("SUPLEMENT", "Suplement", "Przypomnienie z harmonogramu", "/"),
        Category("HARMONOGRAM", "Harmonogram", "Przypomnienie z harmonogramu", "/"),
        Category("RAPORT", "Raport tygodniowy", "Raport tygodniowy", "/raport"),
        Category("WIADOMOSC", "Nowa wiadomość", "Nowa wiadomość", "/wiadomosci"),
        Category("PLATNOSC", "Płatność", "Przypomnienie o płatności", "/platnosci"),
        Category("DOKUMENT", "Dokument lub zgoda", "Nowy dokument w aplikacji", "/dokumenty"),
        Category("ZMIANA_PLANU", "Ważna zmiana planu", "Zmiana Twojego planu", "/plan"),
        Category("KONSULTACJA", "Konsultacja", "Konsultacja", "/konsultacje"),
        # Digest trenera: metadane operacyjne własnej pracy (nie dane
        # zdrowotne podopiecznych) — jedyna kategoria z e-mailem włączonym
        # domyślnie, bo poniedziałkowa wiadomość jest całym jej sensem.
        Category(
            "PODSUMOWANIE", "Podsumowanie tygodnia",
            "Podsumowanie tygodnia", "/trener/podsumowanie",
        ),
        # Zapytanie z publicznej strony marketingowej (0.49.0): dane
        # kontaktowe nadawcy są w title/body, czyli wyłącznie w centrum
        # za logowaniem — kanały zewnętrzne dostają neutralne wezwanie.
        Category("ZAPYTANIE", "Zapytanie ze strony", "Nowe zapytanie", "/powiadomienia"),
        # Przesiew bezpieczeństwa rozmów (0.53.10, przegląd krzyżowy
        # ustalenie 4): trener dostaje FAKT podniesienia flagi — treść
        # odpowiedzi zdrowotnej nigdy nie opuszcza centrum za logowaniem,
        # a i tam podlega zgodom (kanały zewnętrzne: neutralne wezwanie).
        Category("PRZESIEW", "Przesiew bezpieczeństwa", "Odpowiedź wymaga uwagi", "/klienci"),
    ]
}

# Neutralna treść kanałów zewnętrznych — identyczna dla wszystkich
# kategorii; szczegóły dopiero po zalogowaniu (klik prowadzi do ekranu).
PUSH_BODY = "Masz nowe powiadomienie w Dzik OS. Szczegóły znajdziesz w aplikacji."

# Mapowanie kategorii elementu harmonogramu -> kategoria powiadomienia.
SCHEDULE_CATEGORY_MAP = {
    "TRENING": "TRENING",
    "SUPLEMENT": "SUPLEMENT",
    "RAPORT": "RAPORT",
    "PLATNOSC": "PLATNOSC",
}


# ---------------------------------------------------------------------------
# Preferencje i ustawienia
# ---------------------------------------------------------------------------


def get_settings(db: Session, user_id: str) -> NotificationSetting:
    """Wiersz ustawień użytkownika; nietrwały obiekt domyślny, gdy brak."""
    row = db.query(NotificationSetting).filter_by(user_id=user_id).one_or_none()
    if row is not None:
        return row
    return NotificationSetting(
        id="", user_id=user_id, quiet_hours_start=None, quiet_hours_end=None,
        active_days="1,2,3,4,5,6,7", raport_frequency="DAILY",
    )


def channel_enabled(db: Session, user_id: str, category: str, channel: str) -> bool:
    row = (
        db.query(NotificationPreference)
        .filter_by(user_id=user_id, category=category, channel=channel)
        .one_or_none()
    )
    if row is not None:
        return bool(row.enabled)
    override = CATEGORY_CHANNEL_DEFAULTS.get((category, channel))
    if override is not None:
        return override
    return CHANNEL_DEFAULTS.get(channel, False)


def in_quiet_hours(setting: NotificationSetting, local_dt: datetime) -> bool:
    """Czy lokalny moment przypada w cichych godzinach (zakres może
    przechodzić przez północ, np. 22:00–07:00)."""
    start, end = setting.quiet_hours_start, setting.quiet_hours_end
    if not start or not end or start == end:
        return False
    hhmm = local_dt.strftime("%H:%M")
    if start < end:
        return start <= hhmm < end
    return hhmm >= start or hhmm < end


def active_day(setting: NotificationSetting, local_dt: datetime) -> bool:
    days = {d.strip() for d in (setting.active_days or "").split(",") if d.strip()}
    return str(local_dt.isoweekday()) in days if days else True


# ---------------------------------------------------------------------------
# Tworzenie powiadomień
# ---------------------------------------------------------------------------


def _dedup_taken(db: Session, user_id: str, dedup_key: str) -> bool:
    return (
        db.query(Notification.id)
        .filter_by(user_id=user_id, dedup_key=dedup_key)
        .first()
        is not None
    )


def schedule(
    db: Session,
    *,
    user_id: str,
    category: str,
    title: str,
    body: str = "",
    url: str | None = None,
    source: str | None = None,
    dedup_key: str,
    scheduled_at_utc: datetime,
    timezone: str | None = None,
) -> Notification | None:
    """Planuje powiadomienie na termin (UTC). Idempotentne po dedup_key —
    ponowne planowanie tego samego wystąpienia jest bez efektu (None)."""
    if _dedup_taken(db, user_id, dedup_key):
        return None
    n = Notification(
        id=new_id("NTF"),
        user_id=user_id,
        category=category,
        title=title,
        body=body,
        url=url or CATEGORIES[category].default_url,
        status="SCHEDULED",
        dedup_key=dedup_key,
        source=source,
        timezone=timezone,
        scheduled_at=scheduled_at_utc.astimezone(UTC).isoformat(),
    )
    db.add(n)
    # Sesja ma autoflush=False — jawny flush, żeby kolejne zapytania w tej
    # samej transakcji (dedup, dispatch_due) widziały świeży wiersz.
    db.flush()
    return n


def notify_now(
    db: Session,
    *,
    user_id: str,
    category: str,
    title: str,
    body: str = "",
    url: str | None = None,
    source: str | None = None,
    dedup_key: str | None = None,
) -> Notification | None:
    """Powiadomienie zdarzeniowe (natychmiastowe): tworzy wiersz i od razu
    doręcza kanałami wg preferencji. Zwraca wiersz (do publish_realtime PO
    commicie) albo None (duplikat po dedup_key). Nigdy nie podnosi wyjątku
    z kanałów zewnętrznych (best-effort)."""
    key = dedup_key or f"event:{new_id('DDP')}"
    if _dedup_taken(db, user_id, key):
        return None
    n = Notification(
        id=new_id("NTF"),
        user_id=user_id,
        category=category,
        title=title,
        body=body,
        url=url or CATEGORIES[category].default_url,
        status="SCHEDULED",
        dedup_key=key,
        source=source,
    )
    db.add(n)
    db.flush()  # autoflush=False — wiersz musi być widoczny dla zapytań
    _dispatch(db, n)
    return n


def cancel_source(db: Session, source: str, *, user_id: str | None = None) -> int:
    """Anuluje ZAPLANOWANE powiadomienia danego źródła (np. przesunięty/
    odwołany termin, wstrzymany element harmonogramu). Wiersze wysłane
    zostają — historia doręczeń jest niemutowalna."""
    q = db.query(Notification).filter_by(source=source, status="SCHEDULED")
    if user_id is not None:
        q = q.filter_by(user_id=user_id)
    cancelled = 0
    for n in q.all():
        n.status = "CANCELLED"
        cancelled += 1
    return cancelled


# ---------------------------------------------------------------------------
# Doręczanie
# ---------------------------------------------------------------------------


def _task_done(
    db: Session, n: Notification, user: User, now_utc: datetime
) -> str | None:
    """Sprawdzenie PRZY WYSYŁCE, czy zadanie źródłowe nie zostało już
    wykonane/odwołane. Zwraca powód tłumienia albo None (wysyłamy)."""
    source = n.source or ""
    kind, _, obj_id = source.partition(":")
    today = local_now(user, now=now_utc).date()
    if kind == "schedule_item":
        item = db.get(ScheduleItem, obj_id)
        if item is None or item.status != "ACTIVE":
            return "source_gone"
        done = (
            db.query(ScheduleCompletion.id)
            .filter_by(schedule_item_id=obj_id, completed_on=today.isoformat())
            .first()
        )
        if done is not None:
            return "task_done"
        if n.category == "RAPORT":
            # Raport bieżącego tygodnia już wysłany → przypomnienie zbędne.
            week_start = (today - timedelta(days=today.weekday())).isoformat()
            sent = (
                db.query(WeeklyCheckin.id)
                .filter_by(client_id=n.user_id, week_start=week_start)
                .first()
            )
            if sent is not None:
                return "task_done"
    elif kind == "reminder":
        r = db.get(Reminder, obj_id)
        if r is None or r.status != "ACTIVE":
            return "source_gone"
    elif kind == "payment_record":
        rec = db.get(PaymentRecord, obj_id)
        if rec is None or rec.status not in DUE_STATUSES:
            return "task_done"
    elif kind == "consult_slot":
        from .models import ConsultSlot

        slot = db.get(ConsultSlot, obj_id)
        if slot is None or slot.status != "BOOKED" or slot.client_id != n.user_id:
            return "source_gone"
    return None


def _send_email(user: User, category: str) -> bool:
    """Neutralny e-mail (bez danych zdrowotnych i kwot — jak push)."""
    cat = CATEGORIES[category]
    try:
        ok = notifications_provider.provider.send_email(
            to=user.email,
            subject=f"Dzik OS — {cat.push_title}",
            body=PUSH_BODY + " Zaloguj się, aby zobaczyć szczegóły.",
        )
    # Best-effort: awaria dostawcy e-mail nie może wywrócić doręczenia
    # pozostałych kanałów ani pętli — policzona i zalogowana bez treści.
    except Exception:  # noqa: BLE001 - kanał pomocniczy
        metrics.inc("notif_email_failures")
        log_json("notif_email_failed", level="warning")
        return False
    return bool(ok)


def _dispatch(db: Session, n: Notification, now_utc: datetime | None = None) -> None:
    """Doręcza jedno powiadomienie: bramki (zadanie wykonane, preferencje,
    ciche godziny) → kanały → status. Wywoływane w otwartej transakcji;
    commit należy do wołającego."""
    user = db.get(User, n.user_id)
    if user is None or user.status != "ACTIVE":
        n.status = "SUPPRESSED"
        n.suppressed_reason = "source_gone"
        return
    if n.source:
        reason = _task_done(db, n, user, now_utc)
        if reason is not None:
            n.status = "SUPPRESSED"
            n.suppressed_reason = reason
            metrics.inc("notif_suppressed")
            return
    setting = get_settings(db, n.user_id)
    quiet = in_quiet_hours(setting, local_now(user, now=now_utc))
    channels: list[str] = []
    if channel_enabled(db, n.user_id, n.category, "CENTER"):
        channels.append("center")
        metrics.inc("notif_sent_center")
    if channel_enabled(db, n.user_id, n.category, "PUSH") and not quiet:
        cat = CATEGORIES[n.category]
        delivered = push_service.send_to_user(
            db, n.user_id, cat.push_title, PUSH_BODY, n.url
        )
        if delivered:
            channels.append("push")
            metrics.inc("notif_sent_push", delivered)
    email_wanted = channel_enabled(db, n.user_id, n.category, "EMAIL") and not quiet
    if email_wanted and _send_email(user, n.category):
        channels.append("email")
        metrics.inc("notif_sent_email")
    if not channels:
        n.status = "SUPPRESSED"
        n.suppressed_reason = "preferences"
        metrics.inc("notif_suppressed")
        return
    n.status = "SENT"
    n.sent_at = now_iso()
    n.channels = ",".join(channels)


def dispatch_due(db: Session, now_utc: datetime) -> list[Notification]:
    """Doręcza zaplanowane powiadomienia, których termin nadszedł.
    Spóźnione powyżej LATE_SEND_MAX są tłumione jako 'expired' (nadganianie
    po restarcie ma granicę zdrowego rozsądku). Zwraca wiersze SENT —
    wołający publikuje je do SSE PO commicie."""
    now_iso_utc = now_utc.astimezone(UTC).isoformat()
    due = (
        db.query(Notification)
        .filter(
            Notification.status == "SCHEDULED",
            Notification.scheduled_at.is_not(None),
            Notification.scheduled_at <= now_iso_utc,
        )
        .order_by(Notification.scheduled_at)
        .all()
    )
    sent: list[Notification] = []
    for n in due:
        scheduled = datetime.fromisoformat(n.scheduled_at)  # type: ignore[arg-type]
        if now_utc - scheduled > LATE_SEND_MAX:
            n.status = "SUPPRESSED"
            n.suppressed_reason = "expired"
            metrics.inc("notif_suppressed")
            continue
        _dispatch(db, n, now_utc)
        if n.status == "SENT":
            sent.append(n)
    return sent


def realtime_payload(n: Notification) -> dict[str, Any]:
    return {
        "type": "notification.new",
        "id": n.id,
        "category": n.category,
        "title": n.title,
        "body": n.body,
        "url": n.url,
        "created_at": n.created_at,
    }


def publish_realtime(n: Notification | None) -> None:
    """Zdarzenie SSE do otwartej aplikacji odbiorcy (centrum na żywo).
    Wołać PO db.commit() — zdarzenie nie może wyprzedzić trwałego zapisu."""
    if n is None or n.status != "SENT" or "center" not in (n.channels or ""):
        return
    bus.publish(n.user_id, realtime_payload(n))


# ---------------------------------------------------------------------------
# Planowanie dnia (pętla przypomnień)
# ---------------------------------------------------------------------------


def _week_key(day: datetime) -> str:
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def plan_day(db: Session, now_utc: datetime) -> int:
    """Materializuje dzisiejsze wystąpienia przypomnień jako wiersze
    SCHEDULED (idempotentnie po dedup_key): elementy harmonogramu z porą,
    jednorazowe przypomnienia trenera i płatności z dzisiejszym terminem.
    Pory liczone w strefie KAŻDEGO odbiorcy z osobna."""
    planned = 0
    users_cache: dict[str, User | None] = {}

    def _user(user_id: str) -> User | None:
        if user_id not in users_cache:
            users_cache[user_id] = db.get(User, user_id)
        return users_cache[user_id]

    items = (
        db.query(ScheduleItem)
        .filter(ScheduleItem.status == "ACTIVE", ScheduleItem.time_of_day.is_not(None))
        .all()
    )
    for item in items:
        user = _user(item.client_id)
        if user is None or user.status != "ACTIVE":
            continue
        tz = tz_for_user(user)
        local = now_utc.astimezone(tz)
        today = local.date()
        if str(local.isoweekday()) not in item.days_of_week.split(","):
            continue
        if item.start_date and item.start_date > today.isoformat():
            continue
        if item.end_date and item.end_date < today.isoformat():
            continue
        setting = get_settings(db, item.client_id)
        if not active_day(setting, local):
            continue
        try:
            hour, minute = (int(p) for p in (item.time_of_day or "").split(":"))
        except ValueError:
            continue
        occurs_local = datetime(today.year, today.month, today.day, hour, minute, tzinfo=tz)
        occurs_utc = occurs_local.astimezone(UTC)
        if now_utc - occurs_utc > LATE_SEND_MAX:
            continue  # wystąpienie minęło — nie tworzymy martwych wierszy
        category = SCHEDULE_CATEGORY_MAP.get(item.category, "HARMONOGRAM")
        if category == "RAPORT" and setting.raport_frequency == "WEEKLY":
            dedup = f"schedule:{item.id}:{_week_key(occurs_local)}"
        else:
            dedup = f"schedule:{item.id}:{today.isoformat()}"
        created = schedule(
            db,
            user_id=item.client_id,
            category=category,
            title=item.name + (f" — {item.time_of_day}" if item.time_of_day else ""),
            body="Zaplanowany punkt Twojego harmonogramu.",
            url=CATEGORIES[category].default_url,
            source=f"schedule_item:{item.id}",
            dedup_key=dedup,
            scheduled_at_utc=occurs_utc,
            timezone=str(tz),
        )
        planned += created is not None

    reminders = db.query(Reminder).filter(Reminder.status == "ACTIVE").all()
    for r in reminders:
        user = _user(r.client_id)
        if user is None or user.status != "ACTIVE":
            continue
        tz = tz_for_user(user)
        local = now_utc.astimezone(tz)
        if r.due_date != local.date().isoformat():
            continue
        occurs_local = local.replace(hour=8, minute=0, second=0, microsecond=0)
        occurs_utc = occurs_local.astimezone(UTC)
        if now_utc - occurs_utc > LATE_SEND_MAX:
            continue
        created = schedule(
            db,
            user_id=r.client_id,
            category="HARMONOGRAM",
            title="Przypomnienie od trenera",
            body=r.text,
            url="/",
            source=f"reminder:{r.id}",
            dedup_key=f"reminder:{r.id}:{r.due_date}",
            scheduled_at_utc=occurs_utc,
            timezone=str(tz),
        )
        planned += created is not None

    from .models import PaymentSchedule

    # Należności realnie wymagalne (maszyna stanów płatności: PENDING oraz
    # OVERDUE — patrz payment_state.DUE_STATUSES). Opłacona, anulowana czy
    # dopiero planowana rata nie generuje przypomnienia ani tutaj, ani przy
    # wysyłce (druga bramka w _suppression_reason).
    due = (
        db.query(PaymentRecord, PaymentSchedule)
        .join(PaymentSchedule, PaymentRecord.schedule_id == PaymentSchedule.id)
        .filter(PaymentRecord.status.in_(DUE_STATUSES))
        .all()
    )
    for rec, sched in due:
        user = _user(sched.client_id)
        if user is None or user.status != "ACTIVE":
            continue
        tz = tz_for_user(user)
        local = now_utc.astimezone(tz)
        today_local = local.date().isoformat()
        if rec.due_date > today_local:
            continue
        try:
            days_over = (
                date.fromisoformat(today_local) - date.fromisoformat(rec.due_date)
            ).days
        except ValueError:
            continue
        # W dniu terminu, a przy zaległości co 7 dni — przypomnienie ma
        # przypominać, a nie nękać codziennie.
        if days_over != 0 and days_over % PAYMENT_OVERDUE_EVERY_DAYS != 0:
            continue
        occurs_local = local.replace(hour=8, minute=0, second=0, microsecond=0)
        occurs_utc = occurs_local.astimezone(UTC)
        if now_utc - occurs_utc > LATE_SEND_MAX:
            continue
        created = schedule(
            db,
            user_id=sched.client_id,
            category="PLATNOSC",
            # Bez kwoty (także w centrum — jednolita zasada; kwoty są na
            # ekranie Płatności, do którego prowadzi klik).
            title=(
                "Termin płatności przypada dziś" if days_over == 0
                else "Masz zaległą płatność"
            ),
            body="Szczegóły znajdziesz na ekranie Płatności.",
            url="/platnosci",
            source=f"payment_record:{rec.id}",
            # Data WYSTĄPIENIA (nie terminu): kolejne przypomnienie
            # o zaległości ma własny klucz, a powtórka tego samego dnia
            # nadal jest odrzucana przez UNIQUE(user_id, dedup_key).
            dedup_key=f"payment-due:{rec.id}:{today_local}",
            scheduled_at_utc=occurs_utc,
            timezone=str(tz),
        )
        planned += created is not None
    return planned


# Digest trenera: poniedziałek rano czasu trenera.
DIGEST_WEEKDAY = 1  # poniedziałek (isoweekday)
DIGEST_HOUR = 7


def plan_weekly_digest(db: Session, now_utc: datetime) -> int:
    """Planuje poniedziałkowe „Podsumowanie tygodnia" dla każdego trenera.

    Powiadomienie jest neutralnym wezwaniem do panelu — liczby i nazwiska
    zostają na ekranie za logowaniem (ta sama zasada, co dla push:
    wiadomość może wyświetlić się na ekranie blokady). Idempotentne po
    kluczu tygodnia ISO, więc restart maszyny ani wielokrotny tick nie
    tworzą duplikatu. Bez skonfigurowanego dostawcy e-mail wpis po prostu
    trafia do centrum powiadomień w aplikacji — nic nie wychodzi na zewnątrz.
    """
    planned = 0
    coach_ids = [
        row[0]
        for row in db.query(RoleGrant.user_id)
        .filter(RoleGrant.role == "COACH", RoleGrant.revoked_at.is_(None))
        .distinct()
        .all()
    ]
    for coach_id in coach_ids:
        coach = db.get(User, coach_id)
        if coach is None or coach.status != "ACTIVE":
            continue
        tz = tz_for_user(coach)
        local = now_utc.astimezone(tz)
        if local.isoweekday() != DIGEST_WEEKDAY:
            continue
        occurs_local = local.replace(
            hour=DIGEST_HOUR, minute=0, second=0, microsecond=0
        )
        occurs_utc = occurs_local.astimezone(UTC)
        if now_utc - occurs_utc > LATE_SEND_MAX:
            continue
        created = schedule(
            db,
            user_id=coach_id,
            category="PODSUMOWANIE",
            title="Podsumowanie tygodnia",
            body="Zestawienie pracy z minionego tygodnia czeka w panelu.",
            url="/trener/podsumowanie",
            dedup_key=f"digest:{coach_id}:{_week_key(local)}",
            scheduled_at_utc=occurs_utc,
            timezone=str(tz),
        )
        planned += created is not None
    return planned
