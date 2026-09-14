"""Wbudowane bloki rozgrzewki (3 poziomy × 3 warianty) i rozciągania
(3 warianty, jeden poziom, po treningu) — szkic treści z pakietu zlecenia 5
(§5 promptu), złożony z pozycji katalogu ćwiczeń (`exercise_catalog.py`).

DO PRZEGLĄDU TRENERA: każdy blok ma `source="wbudowany — do przeglądu
trenera"`; trener przegląda dawki i pozycje przed użyciem u prawdziwych
klientów (zakładka Szablony → Bloki). Odniesienia do katalogu są po nazwie
i rozwiązywane do `exercise_id` przy ładowaniu (`load-builtin`) — miękko:
brak wpisu w bazie trenera nie blokuje bloku, znika tylko link do karty.

Warianty: G = góra ciała, D = dół ciała, C = całe ciało (spójne z nazwami dni
„Trening A — góra / B — dół / C — całe ciało”). Każda rozgrzewka: 1 pozycja
„podniesienie tętna” (3–6 min, RPE 3–4) + 3–5 pozycji mobilności/aktywacji
+ 1 pozycja „seria wprowadzająca” (opis, nie ćwiczenie).
"""

from __future__ import annotations

ZRODLO_WBUDOWANE = "wbudowany — do przeglądu trenera"

WARIANTY: tuple[str, ...] = ("G", "D", "C")
ETYKIETY_WARIANTOW: dict[str, str] = {"G": "góra ciała", "D": "dół ciała", "C": "całe ciało"}
RODZAJE: tuple[str, ...] = ("WARMUP", "STRETCH")
ETYKIETY_RODZAJOW: dict[str, str] = {"WARMUP": "rozgrzewka", "STRETCH": "rozciąganie"}

SERIA_WPROWADZAJACA = ("Seria wprowadzająca", "1×8–10 z 40–50 % ciężaru roboczego",
                       "Pierwsze ćwiczenie planu lekkim ciężarem — to opis, nie osobne ćwiczenie.")
SERIA_WPROWADZAJACA_2 = ("Seria wprowadzająca (2 stopnie)", "1×8 z 40 % + 1×5 z 60–70 %",
                         "Dwa stopnie przed serią roboczą pierwszego ćwiczenia planu.")


def _p(name: str, dose: str, note: str | None = None, *, catalog: bool = True) -> dict:
    """Pozycja bloku: `exercise_name` (nazwa w katalogu, gdy `catalog`),
    `dose` (czas / powtórzenia / sekundy na stronę), `note`."""
    return {"name": name, "dose": dose, "note": note, "catalog": catalog}


BLOKI: list[dict] = [
    # --- Rozgrzewki: POCZĄTKUJĄCY (≈8 min) ---
    {"kind": "WARMUP", "level": "POCZATKUJACY", "variant": "G", "duration_min": 8,
     "name": "Rozgrzewka — góra ciała (początkujący)", "items": [
         _p("Marsz w miejscu z wysokim kolanem", "3 min", "RPE 3–4"),
         _p("Krążenia ramion", "2×10"),
         _p("Koci grzbiet (cat-cow)", "8"),
         _p("Rozciąganie klatki w narożniku", "2×20 s"),
         _p("Rotacja piersiowa leżąc na boku (open book)", "6/str."),
         _p(*SERIA_WPROWADZAJACA, catalog=False),
     ]},
    {"kind": "WARMUP", "level": "POCZATKUJACY", "variant": "D", "duration_min": 8,
     "name": "Rozgrzewka — dół ciała (początkujący)", "items": [
         _p("Rower stacjonarny — jazda ciągła", "4 min", "RPE 3–4"),
         _p("Krążenia bioder w podporze", "8/str."),
         _p("Rozciąganie zginaczy bioder w wykroku", "20 s/str."),
         _p("Mobilizacja stawu skokowego w zakroku", "8/str."),
         _p("Rotacja bioder 90/90", "6/str."),
         _p(*SERIA_WPROWADZAJACA, catalog=False),
     ]},
    {"kind": "WARMUP", "level": "POCZATKUJACY", "variant": "C", "duration_min": 8,
     "name": "Rozgrzewka — całe ciało (początkujący)", "items": [
         _p("Marsz pod górę na bieżni", "4 min", "RPE 3–4"),
         _p("Koci grzbiet (cat-cow)", "8"),
         _p("World's greatest stretch", "4/str."),
         _p("Krążenia ramion", "2×10"),
         _p("Rozciąganie łydek o ścianę", "20 s/str."),
         _p(*SERIA_WPROWADZAJACA, catalog=False),
     ]},
    # --- Rozgrzewki: ŚREDNIOZAAWANSOWANY (≈10 min) ---
    {"kind": "WARMUP", "level": "SREDNIOZAAWANSOWANY", "variant": "G", "duration_min": 10,
     "name": "Rozgrzewka — góra ciała (średniozaawansowany)", "items": [
         _p("Wioślarz — wiosłowanie ciągłe", "4 min", "lekko, RPE 3–4"),
         _p("Halo z kettlebell", "2×8/str."),
         _p("Rotacja piersiowa leżąc na boku (open book)", "8/str."),
         _p("Rozciąganie klatki w narożniku", "2×20 s"),
         _p("Zwis na drążku", "2×20 s"),
         _p(*SERIA_WPROWADZAJACA, catalog=False),
     ]},
    {"kind": "WARMUP", "level": "SREDNIOZAAWANSOWANY", "variant": "D", "duration_min": 10,
     "name": "Rozgrzewka — dół ciała (średniozaawansowany)", "items": [
         _p("Stepper", "4 min", "RPE 3–4"),
         _p("Wykrok z rotacją (dynamiczny)", "6/str."),
         _p("Rotacja bioder 90/90", "8/str."),
         _p("Rozciąganie dwugłowych z taśmą", "20 s/str."),
         _p("Krążenia bioder w podporze", "8/str."),
         _p(*SERIA_WPROWADZAJACA, catalog=False),
     ]},
    {"kind": "WARMUP", "level": "SREDNIOZAAWANSOWANY", "variant": "C", "duration_min": 10,
     "name": "Rozgrzewka — całe ciało (średniozaawansowany)", "items": [
         _p("Orbitrek (trenażer eliptyczny)", "4 min", "RPE 3–4"),
         _p("World's greatest stretch", "5/str."),
         _p("Halo z kettlebell", "8/str."),
         _p("Wykrok z rotacją (dynamiczny)", "6/str."),
         _p("Mobilizacja stawu skokowego w zakroku", "8/str."),
         _p(*SERIA_WPROWADZAJACA, catalog=False),
     ]},
    # --- Rozgrzewki: ZAAWANSOWANY (≈12 min) ---
    {"kind": "WARMUP", "level": "ZAAWANSOWANY", "variant": "G", "duration_min": 12,
     "name": "Rozgrzewka — góra ciała (zaawansowany)", "items": [
         _p("Assault bike — interwały", "5 min", "z 2 przyspieszeniami (albo wioślarz)"),
         _p("Halo z kettlebell", "2×10/str."),
         _p("Zwis na drążku", "2×30 s"),
         _p("Rotacja piersiowa leżąc na boku (open book)", "8/str."),
         _p("Krążenia ramion", "2×12", "z taśmą"),
         _p(*SERIA_WPROWADZAJACA_2, catalog=False),
     ]},
    {"kind": "WARMUP", "level": "ZAAWANSOWANY", "variant": "D", "duration_min": 12,
     "name": "Rozgrzewka — dół ciała (zaawansowany)", "items": [
         _p("Skakanka", "4 min", "RPE 4"),
         _p("Wykrok z rotacją (dynamiczny)", "8/str."),
         _p("Rotacja bioder 90/90", "10/str."),
         _p("Rozciąganie zginaczy bioder w wykroku", "30 s/str."),
         _p("Podbiegi", "3×20 m", "lekkie; zamiennik: marsz pod górę"),
         _p(*SERIA_WPROWADZAJACA_2, catalog=False),
     ]},
    {"kind": "WARMUP", "level": "ZAAWANSOWANY", "variant": "C", "duration_min": 12,
     "name": "Rozgrzewka — całe ciało (zaawansowany)", "items": [
         _p("Interwały biegowe 30/30", "5 min", "lekkie, RPE 5"),
         _p("World's greatest stretch", "6/str."),
         _p("Halo z kettlebell", "10/str."),
         _p("Krążenia bioder w podporze", "10/str."),
         _p("Rozciąganie łydek o ścianę", "20 s/str."),
         _p(*SERIA_WPROWADZAJACA_2, catalog=False),
     ]},
    # --- Rozciąganie po treningu (bez poziomów; statyczne 20–30 s/str.) ---
    {"kind": "STRETCH", "level": None, "variant": "G", "duration_min": 6,
     "name": "Rozciąganie po treningu — góra ciała", "items": [
         _p("Rozciąganie klatki w narożniku", "2×25 s"),
         _p("Rozciąganie najszerszych przy drążku", "25 s/str."),
         _p("Rozciąganie karku", "20 s/str."),
         _p("Rozciąganie przedramion", "20 s/str."),
         _p("Rotacja piersiowa leżąc na boku (open book)", "6/str.", "spokojnie"),
     ]},
    {"kind": "STRETCH", "level": None, "variant": "D", "duration_min": 8,
     "name": "Rozciąganie po treningu — dół ciała", "items": [
         _p("Rozciąganie czworogłowych stojąc", "25 s/str."),
         _p("Rozciąganie dwugłowych siedząc", "25 s/str."),
         _p("Rozciąganie pośladkowych („figura 4”)", "25 s/str."),
         _p("Rozciąganie przywodzicieli", "25 s/str."),
         _p("Rozciąganie zginaczy bioder w wykroku", "25 s/str."),
         _p("Rozciąganie łydek o ścianę", "20 s/str."),
     ]},
    {"kind": "STRETCH", "level": None, "variant": "C", "duration_min": 7,
     "name": "Rozciąganie po treningu — całe ciało", "items": [
         _p("Rozciąganie czworogłowych stojąc", "20 s/str."),
         _p("Rozciąganie dwugłowych siedząc", "20 s/str."),
         _p("Rozciąganie pośladkowych („figura 4”)", "20 s/str."),
         _p("Rozciąganie klatki w narożniku", "2×20 s"),
         _p("Rozciąganie najszerszych przy drążku", "20 s/str."),
         _p("Rozciąganie karku", "20 s/str."),
     ]},
]


def klucz(blok: dict) -> tuple[str, str | None, str]:
    """Tożsamość bloku wbudowanego (rodzaj, poziom, wariant) — do idempotentnego ładowania."""
    return (blok["kind"], blok.get("level"), blok["variant"])


def nazwy_katalogu() -> set[str]:
    return {p["name"] for b in BLOKI for p in b["items"] if p["catalog"]}
