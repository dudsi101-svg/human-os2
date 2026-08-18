"""Katalog kategorii zgód i podstaw przetwarzania Dzik OS (RODO).

Jedno źródło prawdy dla:
* podziału zgód na odrębne, jednoznaczne kategorie (bez łączenia zgód
  wymaganych z opcjonalnymi),
* pełnego opisu każdej kategorii: cel, zakres danych, odbiorcy, okres
  przechowywania, dobrowolność, sposób wycofania, podstawa prawna,
* mapowania kategoria -> (purpose, domain) używanego przez
  hos_engine.ConsentRegistry (authz.resolve_client_access).

Wersja dokumentu zgód (CONSENT_DOC_VERSION) rośnie przy każdej istotnej
zmianie treści opisów — nowe zgody są rejestrowane z bieżącą wersją,
historyczne wiersze zachowują wersję, na którą faktycznie wyrażono zgodę.

UWAGA: opisy przygotowano technicznie na podstawie rzeczywistego
działania aplikacji; nie są poradą prawną. Miejsca wymagające decyzji
administratora danych: docs/ZGODY_MODEL.md ("DECYZJA ADMINISTRATORA
DANYCH").
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

# Identyfikator "odbiorcy" dla zgód systemowych (funkcje aplikacji, nie
# osoba). Trzymany w ConsentRecord.grantee_id.
SYSTEM_GRANTEE = "SYSTEM"

# Bieżąca wersja treści dokumentu zgód (patrz docstring modułu).
CONSENT_DOC_VERSION = "2.1"

# Ile czasu po zakończeniu współpracy dane są przechowywane, zanim klient
# powinien je usunąć/wyeksportować — wartość opisowa używana w treściach
# zgód. DECYZJA ADMINISTRATORA DANYCH: docelowy okres retencji.
RETENTION_DEFAULT = (
    "przez czas trwania współpracy trenerskiej; po jej zakończeniu do "
    "usunięcia konta albo upływu okresu retencji ustalonego przez "
    "administratora danych (patrz polityka prywatności)"
)
WITHDRAWAL_DEFAULT = (
    "w aplikacji: Profil → Prywatność i zgody → „Cofnij” — działa "
    "natychmiast i nieodwracalnie ogranicza dalsze przetwarzanie; "
    "wycofanie nie wpływa na zgodność z prawem przetwarzania sprzed "
    "wycofania"
)


@dataclass(frozen=True)
class ConsentCategory:
    key: str
    label: str
    purpose: str
    domain: str
    # "COACH" — odbiorcą jest konkretny trener (grantee_id = id trenera);
    # "SYSTEM" — funkcja aplikacji (grantee_id = SYSTEM_GRANTEE).
    grantee_kind: str
    # Wymagana do prowadzenia współpracy w aplikacji (podstawa umowna) —
    # NIE jest zgodą opt-in w rozumieniu art. 6 ust. 1 lit. a; klient
    # potwierdza, że został poinformowany. Kategorie z required=False to
    # właściwe, dobrowolne zgody (odmowa nie blokuje pozostałych funkcji).
    required: bool
    # Dane szczególnej kategorii (art. 9 RODO) — wymaga allow_sensitive.
    sensitive: bool
    legal_basis: str
    cel: str
    zakres: str
    odbiorcy: str
    okres: str
    dobrowolnosc: str
    wycofanie: str = WITHDRAWAL_DEFAULT


CONSENT_CATEGORIES: dict[str, ConsentCategory] = {
    c.key: c
    for c in [
        ConsentCategory(
            key="prowadzenie_konta",
            label="Prowadzenie konta",
            purpose="account",
            domain="account_data",
            grantee_kind="SYSTEM",
            required=True,
            sensitive=False,
            legal_basis="art. 6 ust. 1 lit. b RODO (umowa)",
            cel="założenie i utrzymanie Twojego konta, logowanie, "
            "bezpieczeństwo sesji i dziennik zdarzeń (audyt)",
            zakres="e-mail, imię i nazwisko, skrót hasła (bcrypt), "
            "identyfikatory sesji, zdarzenia audytowe (identyfikatory "
            "operacji — nigdy treść danych zdrowotnych)",
            odbiorcy="administrator danych (trener) i podmiot "
            "przetwarzający — dostawca hostingu (Fly.io, region UE)",
            okres="do usunięcia konta; zdarzenia audytowe (bez danych "
            "zdrowotnych) — trwale, dla rozliczalności",
            dobrowolnosc="podanie danych jest warunkiem korzystania z "
            "aplikacji (bez konta usługa nie działa); to informacja o "
            "warunkach umowy, nie zgoda opt-in",
            wycofanie="zakończenie przetwarzania = usunięcie konta "
            "(Profil → „Usuń konto i dane”)",
        ),
        ConsentCategory(
            key="udostepnianie_trenerowi",
            label="Udostępnianie danych współpracy trenerowi",
            purpose="coaching",
            domain="collaboration",
            grantee_kind="COACH",
            required=True,
            sensitive=False,
            legal_basis="art. 6 ust. 1 lit. b RODO (umowa)",
            cel="prowadzenie współpracy trenerskiej: wgląd trenera w profil "
            "współpracy, dokumenty i ewidencję płatności",
            zakres="pola profilu współpracy (bez pól wrażliwych), "
            "dokumenty, ewidencja płatności (pakiet, kwota, status), "
            "historia zmian (pokwitowania audytu)",
            odbiorcy="wyłącznie Twój trener; hosting jak wyżej",
            okres=RETENTION_DEFAULT,
            dobrowolnosc="niezbędne do prowadzenia współpracy w aplikacji; "
            "cofnięcie odbiera trenerowi dostęp i w praktyce wstrzymuje "
            "współpracę w aplikacji",
        ),
        ConsentCategory(
            key="dane_treningowe",
            label="Dane treningowe",
            purpose="coaching",
            domain="training_data",
            grantee_kind="COACH",
            required=True,
            sensitive=False,
            legal_basis="art. 6 ust. 1 lit. b RODO (umowa)",
            cel="układanie i korygowanie planu treningowego, harmonogram, "
            "cele, analiza wyników treningów (rekordy, siła w czasie)",
            zakres="plany treningowe i ich wersje, wyniki treningów "
            "(serie, ciężary), harmonogram i jego realizacja, cele",
            odbiorcy="wyłącznie Twój trener; hosting jak wyżej",
            okres=RETENTION_DEFAULT,
            dobrowolnosc="niezbędne do prowadzenia treningu w aplikacji; "
            "cofnięcie odbiera trenerowi dostęp do danych treningowych",
        ),
        ConsentCategory(
            key="komunikacja",
            label="Komunikacja z trenerem",
            purpose="communication",
            domain="messages",
            grantee_kind="COACH",
            required=True,
            sensitive=False,
            legal_basis="art. 6 ust. 1 lit. b RODO (umowa)",
            cel="wymiana wiadomości i załączników z trenerem, terminarz "
            "konsultacji",
            zakres="treść wiadomości, załączniki wysłane w wątku, "
            "rezerwacje konsultacji",
            odbiorcy="wyłącznie Twój trener; hosting jak wyżej",
            okres=RETENTION_DEFAULT,
            dobrowolnosc="niezbędne do komunikacji w aplikacji; cofnięcie "
            "odbiera trenerowi dostęp do wątku",
        ),
        ConsentCategory(
            key="dane_zdrowotne",
            label="Dane zdrowotne",
            purpose="coaching",
            domain="health_data",
            grantee_kind="COACH",
            required=False,
            sensitive=True,
            legal_basis="art. 9 ust. 2 lit. a RODO (wyraźna zgoda — dane "
            "szczególnej kategorii)",
            cel="bezpieczne prowadzenie treningu: uwzględnianie urazów i "
            "ograniczeń, monitorowanie masy ciała, samopoczucia, snu, "
            "stresu i bólu oraz Twoich obserwacji",
            zakres="pomiary (masa, obwody), raporty tygodniowe (sen, "
            "energia, stres, głód, regeneracja, ból), dziennik obserwacji, "
            "urazy i ograniczenia z profilu",
            odbiorcy="wyłącznie Twój trener; hosting jak wyżej",
            okres=RETENTION_DEFAULT,
            dobrowolnosc="dobrowolna — bez niej trener nie widzi Twoich "
            "danych zdrowotnych; możesz nadal korzystać z pozostałych "
            "funkcji aplikacji",
        ),
        ConsentCategory(
            key="zywienie_alergie",
            label="Żywienie i alergie",
            purpose="coaching",
            domain="nutrition_data",
            grantee_kind="COACH",
            required=False,
            sensitive=True,
            legal_basis="art. 9 ust. 2 lit. a RODO (wyraźna zgoda — dane "
            "szczególnej kategorii)",
            cel="układanie planu żywieniowego z uwzględnieniem alergii, "
            "nietolerancji i preferencji; monitorowanie realizacji diety",
            zakres="alergie i nietolerancje, preferencje żywieniowe, plany "
            "żywieniowe i ich wersje, dziennik kaloryczny (kcal/makro/woda)",
            odbiorcy="wyłącznie Twój trener; hosting jak wyżej",
            okres=RETENTION_DEFAULT,
            dobrowolnosc="dobrowolna — bez niej trener nie prowadzi diety "
            "w aplikacji; pozostałe funkcje działają",
        ),
        ConsentCategory(
            key="zdjecia_progresu",
            label="Zdjęcia progresu (wizerunek)",
            purpose="coaching",
            domain="progress_photos",
            grantee_kind="COACH",
            required=False,
            sensitive=True,
            legal_basis="art. 9 ust. 2 lit. a RODO (wyraźna zgoda — dane "
            "szczególnej kategorii / wizerunek)",
            cel="ocena postępów sylwetki i techniki przez trenera",
            zakres="zdjęcia sylwetki dodane do raportów i porównywarki "
            "„przed/po” (metadane EXIF, w tym GPS, są usuwane przy "
            "zapisie nowych zdjęć)",
            odbiorcy="wyłącznie Twój trener; hosting jak wyżej",
            okres=RETENTION_DEFAULT + "; przy usunięciu konta pliki są "
            "fizycznie usuwane z dysku",
            dobrowolnosc="dobrowolna — możesz prowadzić współpracę bez "
            "zdjęć",
        ),
        ConsentCategory(
            key="przypomnienia",
            label="Przypomnienia i powiadomienia push",
            purpose="reminders",
            domain="push_notifications",
            grantee_kind="SYSTEM",
            required=False,
            sensitive=False,
            legal_basis="art. 6 ust. 1 lit. a RODO (zgoda)",
            cel="wysyłanie powiadomień push (nowa wiadomość, odpowiedź "
            "trenera, przypomnienia z harmonogramu)",
            zakres="techniczny adres subskrypcji push Twojej przeglądarki; "
            "treść powiadomień nigdy nie zawiera danych zdrowotnych — "
            "wyłącznie neutralne wezwanie do wejścia do aplikacji",
            odbiorcy="dostawca push Twojej przeglądarki (np. Mozilla/Apple/"
            "Google — zależnie od przeglądarki); treść jest szyfrowana "
            "do Twojego urządzenia",
            okres="do wycofania zgody lub wyłączenia powiadomień",
            dobrowolnosc="w pełni dobrowolna; wyłączenie nie wpływa na "
            "żadną inną funkcję",
            wycofanie="Profil → Prywatność i zgody → „Cofnij” (usuwa też "
            "wszystkie subskrypcje push) albo wyłączenie powiadomień "
            "przyciskiem w Profilu",
        ),
        ConsentCategory(
            key="funkcje_ai",
            label="Funkcje AI (podsumowania raportów i rozmowy startowej)",
            purpose="ai_features",
            domain="checkin_summaries",
            grantee_kind="SYSTEM",
            required=False,
            sensitive=True,
            legal_basis="art. 9 ust. 2 lit. a RODO (wyraźna zgoda — "
            "raport zawiera dane zdrowotne)",
            cel="generowanie propozycji: (1) dla trenera — streszczenia "
            "Twojego raportu tygodniowego i szkicu odpowiedzi; (2) dla "
            "Ciebie — wersji roboczej podsumowania rozmowy startowej "
            "(onboardingu). Tryb propose-only: podsumowanie zatwierdzasz "
            "Ty, plan zatwierdza trener — model nie decyduje o niczym "
            "i nie tworzy planu ani diety",
            zakres="treść raportu tygodniowego oraz Twoje odpowiedzi "
            "z rozmowy startowej (bez imienia, nazwiska, e-maila i "
            "identyfikatorów; bez odpowiedzi oznaczonych sygnałem "
            "alarmowym) przekazywane do dostawcy AI skonfigurowanego "
            "przez operatora (obecnie ŻADEN dostawca nie jest "
            "skonfigurowany — funkcja nieaktywna)",
            odbiorcy="dostawca AI wskazany w polityce prywatności, o ile "
            "operator go skonfiguruje; do tego czasu dane nie opuszczają "
            "aplikacji",
            okres="do wycofania zgody",
            dobrowolnosc="w pełni dobrowolna; odmowa nie blokuje niczego — "
            "rozmowa startowa i podsumowanie działają wtedy krok po kroku, "
            "a trener po prostu nie użyje podsumowań AI",
        ),
        ConsentCategory(
            key="marketing",
            label="Marketing (opcjonalny)",
            purpose="marketing",
            domain="contact_data",
            grantee_kind="COACH",
            required=False,
            sensitive=False,
            legal_basis="art. 6 ust. 1 lit. a RODO (zgoda)",
            cel="informowanie Cię przez trenera o jego nowych usługach, "
            "pakietach lub materiałach",
            zakres="adres e-mail i imię; nigdy dane zdrowotne",
            odbiorcy="wyłącznie Twój trener",
            okres="do wycofania zgody",
            dobrowolnosc="w pełni dobrowolna i domyślnie NIEudzielona; "
            "nigdy nie jest rejestrowana przy zakładaniu konta",
        ),
    ]
}

# Kategorie rejestrowane jako deklaracja z onboardingu przy zakładaniu
# NOWEGO konta przez trenera (klient potwierdza/odmawia każdej z osobna
# przy pierwszym logowaniu). Zgody czysto opcjonalne (przypomnienia,
# funkcje AI, marketing) NIGDY nie są rejestrowane przez trenera.
ONBOARDING_CATEGORIES = [
    "prowadzenie_konta",
    "udostepnianie_trenerowi",
    "dane_treningowe",
    "komunikacja",
    "dane_zdrowotne",
    "zywienie_alergie",
    "zdjecia_progresu",
]

# Domeny nadawane trenerowi (grantee_kind == COACH) — używane do
# interpretacji HISTORYCZNYCH zgód parasolowych (sprzed migracji nr 10):
# stary wiersz coaching/health_data z allow_sensitive=True oznaczał pełny
# dostęp trenerski, więc hydratacja rozszerza go na wszystkie domeny
# trenerskie (patrz hos_bridge.ConsentService._hydrate).
LEGACY_UMBRELLA_DOMAINS = {
    c.domain for c in CONSENT_CATEGORIES.values() if c.grantee_kind == "COACH"
}
LEGACY_UMBRELLA_PURPOSES = {
    c.purpose for c in CONSENT_CATEGORIES.values() if c.grantee_kind == "COACH"
}


def category_by_key(key: str) -> ConsentCategory | None:
    return CONSENT_CATEGORIES.get(key)


def category_for_domain(domain: str) -> ConsentCategory | None:
    for c in CONSENT_CATEGORIES.values():
        if c.domain == domain:
            return c
    return None


def catalog_payload() -> list[dict]:
    """Pełny katalog do prezentacji w UI (ekran zgód / Profil)."""
    return [
        {**asdict(c), "document_version": CONSENT_DOC_VERSION}
        for c in CONSENT_CATEGORIES.values()
    ]
