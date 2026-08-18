"""Reguły dostępu Dzik OS (egzekwowane wyłącznie w backendzie).

Zasady (docs/PERMISSIONS.md):
* Klient widzi wyłącznie własne dane (ochrona przed IDOR — każda ścieżka
  z client_id przechodzi przez resolve_client_access).
* Trener widzi dane tylko AKTYWNIE przypisanych klientów i tylko w
  zakresie AKTYWNYCH zgód danej KATEGORII danych (consent_catalog;
  decyzję podejmuje hos_engine.ConsentRegistry przez
  ConsentService.authorize). Cofnięcie zgody jednej kategorii odbiera
  dostęp do tej kategorii, nie ruszając pozostałych.
* ADMIN nie ma automatycznego dostępu do danych zdrowotnych — rola
  techniczna. Dostęp administracyjny jest ograniczony i audytowany.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .consent_catalog import category_for_domain
from .hos_bridge import ConsentService
from .models import CoachClientRelationship, MessageThread, StoredFile, User
from .security import active_roles

# Domeny danych (jedna domena = jedna kategoria zgody z consent_catalog).
DOMAIN_COLLABORATION = "collaboration"    # profil współpracy, dokumenty, płatności
DOMAIN_TRAINING = "training_data"         # plany, wyniki, harmonogram, cele
DOMAIN_HEALTH = "health_data"             # pomiary, raporty, obserwacje, urazy
DOMAIN_NUTRITION = "nutrition_data"       # dieta, dziennik kaloryczny, alergie
DOMAIN_PHOTOS = "progress_photos"         # zdjęcia sylwetki
DOMAIN_MESSAGES = "messages"              # wiadomości i konsultacje


class ResourceAccessDenied(HTTPException):
    """Odmowa dostępu do KONKRETNEGO zasobu po pozytywnej autoryzacji roli
    (IDOR: zasób istnieje, ale należy do kogoś innego / poza zakresem zgód).

    Odpowiedź to zawsze 404 — nie ujawniamy istnienia zasobu. Wyjątek jest
    przechwytywany centralnie w main.py, gdzie odmowa jest logowana w
    łańcuchu audytu jako ACCESS_DENIED (endpoint + id aktora, nigdy dane
    zdrowotne ani sekrety). Zwykłe 404 dla nieistniejących zasobów NIE
    przechodzi tą ścieżką i nie jest logowane."""

    def __init__(self, actor_id: str, resource: str = "") -> None:
        super().__init__(status_code=404, detail="Nie znaleziono")
        self.actor_id = actor_id
        self.resource = resource


def deny(actor_id: str, resource: str = "") -> None:
    """Skrót: rzuca logowaną odmowę zasobową (404)."""
    raise ResourceAccessDenied(actor_id, resource)


def active_relationship(db: Session, coach_id: str, client_id: str) -> CoachClientRelationship | None:
    return (
        db.query(CoachClientRelationship)
        .filter(
            CoachClientRelationship.coach_id == coach_id,
            CoachClientRelationship.client_id == client_id,
            CoachClientRelationship.status == "ACTIVE",
        )
        .one_or_none()
    )


def coach_can_access_client(
    db: Session,
    coach_id: str,
    client_id: str,
    *,
    action: str = "read",
    domain: str = DOMAIN_HEALTH,
) -> bool:
    """Dostęp trenera do danych klienta w JEDNEJ domenie danych.
    Cel (purpose) i wrażliwość wynikają z katalogu kategorii — wywołujący
    wskazuje tylko domenę, o którą pyta."""
    if active_relationship(db, coach_id, client_id) is None:
        return False
    cat = category_for_domain(domain)
    purpose = cat.purpose if cat else "coaching"
    sensitive = cat.sensitive if cat else True
    return ConsentService.authorize(
        db,
        subject_id=client_id,
        grantee_id=coach_id,
        purpose=purpose,
        domain=domain,
        action=action,
        sensitive=sensitive,
    )


def resolve_client_access(
    db: Session,
    actor: User,
    client_id: str,
    *,
    action: str = "read",
    domain: str = DOMAIN_HEALTH,
) -> str:
    """Zwraca client_id, jeśli aktor ma prawo do danych tego klienta w
    danej domenie; w przeciwnym razie 404 (nie 403 — nie ujawniamy
    istnienia zasobu)."""
    roles = active_roles(db, actor.id)
    if "CLIENT" in roles and actor.id == client_id:
        return client_id
    if "COACH" in roles and coach_can_access_client(
        db, actor.id, client_id, action=action, domain=domain
    ):
        return client_id
    raise ResourceAccessDenied(actor.id, f"client:{client_id}")


def require_owned_resource(entity, *, actor: User, resource: str, owner_attr: str = "coach_id"):
    """Wspólny wzorzec „zasób musi istnieć I należeć do aktora".

    * zasób nie istnieje → zwykłe 404 (nieudane trafienie identyfikatora,
      nie jest logowane jako odmowa),
    * zasób istnieje, ale właścicielem (pole `owner_attr`) jest ktoś inny →
      ResourceAccessDenied (404 + wpis ACCESS_DENIED w audycie — próba IDOR).
    Zwraca zasób, jeśli kontrola przeszła."""
    if entity is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if getattr(entity, owner_attr) != actor.id:
        raise ResourceAccessDenied(actor.id, resource)
    return entity


def require_thread_party(db: Session, actor: User, thread_id: str) -> MessageThread:
    """Dostęp do wątku wiadomości: wyłącznie strona wątku. Klient zawsze;
    trener w ramach aktywnej relacji i zgody kategorii „komunikacja"
    (domena messages). Obcy → logowana odmowa 404."""
    thread = db.get(MessageThread, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono")
    if actor.id == thread.client_id:
        return thread
    if actor.id == thread.coach_id:
        resolve_client_access(db, actor, thread.client_id, domain=DOMAIN_MESSAGES)
        return thread
    raise ResourceAccessDenied(actor.id, f"thread:{thread_id}")


def require_attachable_file(
    db: Session,
    actor: User,
    file_id: str,
    *,
    owner_id: str,
    allow_uploader: bool = False,
    require_image: bool = False,
) -> StoredFile:
    """Walidacja pliku PRZY PODPINANIU go do zasobu (wiadomość, raport,
    dokument, baza wiedzy, trening). Plik musi istnieć, nie być usunięty i
    należeć do wskazanego właściciela danych (opcjonalnie wystarczy, że
    aktor sam go wgrał — załączniki wiadomości). Bez tej bramki podpięcie
    cudzego file_id nadawałoby innym osobom dostęp do nie swojego pliku.
    422, bo to walidacja wejścia tworzonego zasobu (nie odczyt pliku)."""
    stored = db.get(StoredFile, file_id)
    if stored is None or stored.deleted_at is not None:
        raise HTTPException(status_code=422, detail="Nie znaleziono pliku")
    if stored.owner_user_id != owner_id and not (
        allow_uploader and stored.uploaded_by == actor.id
    ):
        raise HTTPException(status_code=422, detail="Plik nie należy do tego konta")
    if require_image and not stored.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Załącznik musi być zdjęciem")
    return stored


def require_client_self(db: Session, actor: User) -> str:
    if "CLIENT" not in active_roles(db, actor.id):
        raise HTTPException(status_code=403, detail="Tylko dla klienta")
    return actor.id
