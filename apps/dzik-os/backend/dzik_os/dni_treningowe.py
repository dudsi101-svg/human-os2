"""Dni treningowe (0.71.0): nakładka klienta na dni tygodnia planu trenera.

Czyste funkcje bez bazy i bez FastAPI — używane przez `routers/plan_weekdays.py`
i `routers/today.py`, testowane na przykładach ręcznych.

Zasady (decyzje właściciela 14.09, `docs/plan-sesji/dni-treningowe.md`):

* wersje planu są niemutowalne — nakładka nigdy nie dotyka `content_json`;
  `weekday` wpisany przez trenera jest **propozycją**;
* bez mieszania źródeł: jeśli klient zapisał układ dla planu, obowiązuje
  **wyłącznie** jego układ (dzień bez wpisu = nieprzypisany); bez układu —
  propozycja trenera jak dotąd;
* klucz dnia: `day.id` (stabilne `id` z publikacji 0.58.0) albo `idx:<n>`
  dla wersji bez `id` (seed, starsze wersje); klucz spoza bieżącej wersji
  jest ignorowany przy odczycie i odrzucany (422) przy zapisie;
* jeden dzień tygodnia = co najwyżej jedna jednostka;
* zero rekomendacji — jedyny automatyzm to prefill z propozycji trenera.
"""

from __future__ import annotations

from typing import Any

#: Klucz dnia → dzień tygodnia ISO (1 = poniedziałek … 7 = niedziela) albo None.
Uklad = dict[str, int | None]

ZRODLO_KLIENT = "client"
ZRODLO_TRENER = "coach"
ZRODLO_BRAK = "none"

PODPOWIEDZ_BRAK_DNI = "no_weekdays"
PODPOWIEDZ_NIEAKTUALNE = "stale"

#: Maksymalna długość klucza dnia przyjmowana w API (`id` ma ≤ 40 znaków,
#: `idx:<n>` jest krótsze).
KLUCZ_MAX = 80

NAZWY_DNI = ("poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela")


class BladWyboru(ValueError):
    """Niepoprawny wybór dni (422). `day_key` wskazuje pole, którego dotyczy
    błąd — front pokazuje komunikat przy właściwym polu."""

    def __init__(self, komunikat: str, day_key: str | None = None) -> None:
        super().__init__(komunikat)
        self.komunikat = komunikat
        self.day_key = day_key


def _weekday_ok(value: Any) -> int | None:
    """Liczba całkowita 1–7 albo None; wszystko inne traktowane jak brak."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if 1 <= value <= 7 else None


def klucz_dnia(day: Any, idx: int) -> str:
    """Stabilny klucz jednostki: `day.id`, jeśli wersja go ma, inaczej `idx:<n>`."""
    if isinstance(day, dict):
        did = day.get("id")
        if isinstance(did, str) and did.strip():
            return did.strip()
    return f"idx:{idx}"


def dni(content: Any) -> list[tuple[str, int, dict]]:
    """Wszystkie jednostki wersji jako (klucz, indeks, dzień) — kolejność
    z `content_json`; elementy niebędące słownikiem są pomijane."""
    out: list[tuple[str, int, dict]] = []
    if not isinstance(content, dict):
        return out
    lista = content.get("days")
    if not isinstance(lista, list):
        return out
    for idx, day in enumerate(lista):
        if isinstance(day, dict):
            out.append((klucz_dnia(day, idx), idx, day))
    return out


def uklad_trenera(content: Any) -> Uklad:
    """Propozycja trenera: `weekday` z wersji planu (prefill formularza klienta)."""
    return {key: _weekday_ok(day.get("weekday")) for key, _, day in dni(content)}


def uklad_efektywny(content: Any, wybor: Uklad | None) -> Uklad:
    """Układ, który obowiązuje: w całości układ klienta (jeśli zapisał),
    inaczej propozycja trenera. Klucze spoza wersji są pomijane."""
    if wybor is None:
        return uklad_trenera(content)
    return {key: _weekday_ok(wybor.get(key)) for key, _, _ in dni(content)}


def zrodlo(content: Any, wybor: Uklad | None) -> str:
    """`client` — obowiązuje układ klienta; `coach` — propozycja trenera;
    `none` — plan bez jednostek."""
    if not dni(content):
        return ZRODLO_BRAK
    return ZRODLO_KLIENT if wybor is not None else ZRODLO_TRENER


def ma_przypisania(uklad: Uklad) -> bool:
    return any(v is not None for v in uklad.values())


def dzien_na_dzis(content: Any, wybor: Uklad | None, weekday: int) -> tuple[int, dict] | None:
    """Pierwsza jednostka przypisana do `weekday` w układzie efektywnym
    (indeks w wersji + dzień) albo None."""
    uklad = uklad_efektywny(content, wybor)
    for key, idx, day in dni(content):
        if uklad.get(key) == weekday:
            return idx, day
    return None


def klucze_nieaktualne(content: Any, wybor: Uklad | None) -> list[str]:
    """Klucze z wyboru klienta, których nie ma już w bieżącej wersji
    (trener opublikował nową wersję bez tych jednostek)."""
    if not wybor:
        return []
    aktualne = {key for key, _, _ in dni(content)}
    return [key for key in wybor if key not in aktualne]


def podpowiedz(content: Any, wybor: Uklad | None) -> str | None:
    """Co front ma pokazać na „Dzisiaj”, gdy plan istnieje:
    `stale` — wybór klienta ma klucze spoza wersji (łagodna notka),
    `no_weekdays` — układ efektywny nie przypisuje żadnej jednostki
    (karta „ustaw dni” zamiast „Dziś bez treningu”), None — nic."""
    if not dni(content):
        return None
    if klucze_nieaktualne(content, wybor):
        return PODPOWIEDZ_NIEAKTUALNE
    if not ma_przypisania(uklad_efektywny(content, wybor)):
        return PODPOWIEDZ_BRAK_DNI
    return None


def waliduj_wybor(content: Any, choices: list[dict]) -> Uklad:
    """Lista `{day_key, weekday}` z API → układ klienta. Błędy (422):
    klucz spoza bieżącej wersji, powtórzony klucz, `weekday` spoza 1–7,
    dwie jednostki tego samego dnia tygodnia. Jednostki nieobecne w liście
    dostają None (nieprzypisane) — zapisany układ zawsze pokrywa całą wersję."""
    aktualne = [key for key, _, _ in dni(content)]
    nazwy = {key: day.get("name") for key, _, day in dni(content)}
    if not aktualne:
        raise BladWyboru("Ten plan nie ma jeszcze jednostek treningowych.")
    uklad: Uklad = {key: None for key in aktualne}
    zajete: dict[int, str] = {}
    widziane: set[str] = set()
    for wpis in choices:
        key = wpis.get("day_key") if isinstance(wpis, dict) else None
        if not isinstance(key, str) or key not in uklad:
            raise BladWyboru(
                "Ta jednostka nie należy do bieżącej wersji planu — odśwież widok.",
                key if isinstance(key, str) else None,
            )
        if key in widziane:
            raise BladWyboru("Jednostka podana dwa razy.", key)
        widziane.add(key)
        weekday = wpis.get("weekday")
        if weekday is None:
            continue
        if isinstance(weekday, bool) or not isinstance(weekday, int) or not 1 <= weekday <= 7:
            raise BladWyboru("Dzień tygodnia musi być liczbą od 1 (poniedziałek) do 7 (niedziela).", key)
        if weekday in zajete:
            inna = nazwy.get(zajete[weekday]) or zajete[weekday]
            raise BladWyboru(
                f"W {NAZWY_DNI[weekday - 1]} jest już „{inna}” — jeden dzień tygodnia to jedna jednostka.",
                key,
            )
        zajete[weekday] = key
        uklad[key] = weekday
    return uklad


def do_json(uklad: Uklad) -> list[dict[str, Any]]:
    """Układ → lista `{day_key, weekday}` zapisywana w `choices_json`."""
    return [{"day_key": key, "weekday": weekday} for key, weekday in uklad.items()]


def z_json(lista: Any) -> Uklad:
    """`choices_json` → układ; wpisy nieczytelne są pomijane (dane z bazy,
    nie z API — nie rzucamy)."""
    out: Uklad = {}
    if not isinstance(lista, list):
        return out
    for wpis in lista:
        if isinstance(wpis, dict) and isinstance(wpis.get("day_key"), str):
            out[wpis["day_key"]] = _weekday_ok(wpis.get("weekday"))
    return out
