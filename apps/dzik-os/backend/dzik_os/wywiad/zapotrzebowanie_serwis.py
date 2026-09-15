"""Bilans kaloryczny — warstwa bazy (specyfikacja właściciela 1.0).

Liczy wynik przy przesłaniu wywiadu „zapotrzebowanie” (wywołanie z
`serwis.przeslij`), trzyma jedną wersję na przesłanie, obsługuje nadpisanie
i odblokowanie przez trenera oraz WIDOK zależny od roli i od zgód:

* **klient** — pełny bilans, chyba że z wywiadu wynika flaga zaburzeń
  odżywiania (`hidden_for_client`, odwracalne przez trenera po rozmowie)
  albo flaga `MALOLETNI` (nieodwracalne tą drogą — wymaga zgody opiekuna,
  nie rozmowy). Wtedy z tej trasy nie wychodzi ŻADNA liczba wyniku ani
  wejścia wzoru (masa ciała też jest liczbą) — filtr po stronie serwera,
  nie interfejsu. Własne odpowiedzi klient nadal widzi w zakładce Wywiad,
  a eksport danych (RODO) zawiera pełne wiersze `calorie_estimates`.
* **trener** — pełny bilans; flagi wynikające z odpowiedzi zdrowotnych
  (ciąża, choroby, leki, zaburzenia, brak miesiączki) wyłącznie przy
  aktywnej zgodzie `DOMAIN_HEALTH`. Bez zgody trener dostaje informację,
  że wywiad zawiera odpowiedzi zdrowotne, których nie widzi — zgód nie
  obchodzimy zmianą w bazie ani obejściem w interfejsie.

Wiersze sprzed wyrównania (`formulas_version = "0.62.0-pal"`) zostają jako
historia i nie są przeliczane — nowy wynik powstaje dopiero przy nowym
przesłaniu wywiadu.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from sqlalchemy.orm import Session

from ..hos_bridge import record_event
from ..models import CalorieEstimate, InterviewSubmission, User, new_id, now_iso
from . import definicje as D
from . import zapotrzebowanie as Z

#: Zakres nadpisania trenera (kcal/dzień).
NADPISANIE_MIN, NADPISANIE_MAX = 800, 8000

KOMUNIKAT_UKRYTY = ("Wynik jest gotowy, ale najpierw omówi go z Tobą trener — tak wynika z Twojej "
                    "odpowiedzi w części „Zdrowie i kontekst”. Liczby pojawią się tutaj po rozmowie.")
KOMUNIKAT_UKRYTY_BEZ_TRENERA = ("Wynik jest gotowy, ale pokażemy go dopiero po rozmowie z trenerem — tak "
                                "wynika z Twojej odpowiedzi w części „Zdrowie i kontekst”. Gdy nawiążesz "
                                "współpracę z trenerem, omówicie go razem.")
KOMUNIKAT_MALOLETNI = ("Wynik jest policzony, ale wzory kaloryczne są przygotowane dla osób dorosłych. "
                       "Zobaczy go trener i omówi go z Tobą oraz z Twoim opiekunem.")
KOMUNIKAT_STARY_WYNIK = ("Ten wynik policzył starszy wzór (sprzed rozbicia na aktywność, trening "
                         "i termiczny efekt pożywienia). Zostaje w historii — jeśli chcesz dokładniejszy "
                         "bilans z makro, wypełnij wywiad jeszcze raz. Nic nie musisz robić od razu.")
KOMUNIKAT_FLAGI_BEZ_ZGODY = ("Wywiad zawiera odpowiedzi zdrowotne, których nie widzisz — klient nie ma "
                             "aktywnej zgody na udostępnianie Ci danych zdrowotnych. Wynik i jego "
                             "rozbicie widzisz normalnie.")


def _zapisz_wynik(est: CalorieEstimate, w: Z.Wejscie, y: Z.Wynik) -> None:
    """Zamrożenie wyniku w wierszu. `ppm`/`cpm`/`kcal`/`pal` wypełnione też
    po staremu — czytają je moduł diety i historia."""
    est.inputs_json = json.dumps(_wejscie_bez_zdrowia(w), ensure_ascii=False)
    est.formulas_version = y.formulas_version
    est.ppm, est.cpm, est.kcal = y.ppm_used, y.cpm, y.target_kcal
    est.pal, est.korekta_pct = y.pal_efektywny, y.korekta_pct
    est.ppm_mifflin, est.ppm_katch = y.ppm_mifflin, y.ppm_katch
    est.ppm_used, est.ppm_source = y.ppm_used, y.ppm_source
    est.neat_multiplier, est.training_kcal_day, est.tef = y.neat_multiplier, y.training_kcal_day, y.tef
    est.cpm_min, est.cpm_max, est.target_kcal = y.cpm_min, y.cpm_max, y.target_kcal
    est.macro_json = json.dumps(asdict(y.makro), ensure_ascii=False)
    est.tempo_json = json.dumps(asdict(y.tempo), ensure_ascii=False)
    est.flags_json = json.dumps(list(y.flags), ensure_ascii=False)
    est.expected_weekly_change_kg, est.bmi = y.tempo.kg_tydzien, y.bmi
    est.podstawienie_json = json.dumps(list(y.podstawienie), ensure_ascii=False)
    est.ostrzezenia_json = json.dumps(list(y.ostrzezenia), ensure_ascii=False)


def _wejscie_bez_zdrowia(w: Z.Wejscie) -> dict[str, Any]:
    """Wejścia wzoru BEZ odpowiedzi zdrowotnych — te zostają w wywiadzie,
    gdzie pilnuje ich zgoda domeny (minimalizacja: nie kopiujemy danych
    szczególnej kategorii do drugiej tabeli po to, żeby je tam znowu ukrywać).
    Skutki zdrowotnych odpowiedzi widać w `flags_json`."""
    d = asdict(w)
    for pole in ("ciaza", "choroba_metaboliczna", "leki", "zaburzenia_odzywiania", "brak_miesiaczki"):
        d.pop(pole, None)
    return d


#: Pytanie, z którego bierze się ukrycie wyniku (odwracalne przez trenera).
PYTANIE_ZABURZENIA = "zk_zaburzenia"


def _ukrycie_odziedziczone(db: Session, submission: InterviewSubmission,
                           answers: dict[str, dict]) -> bool:
    """Czy przenieść ukrycie z poprzedniej wersji wyniku.

    Pytania zdrowotne padają tylko przy zgodzie na dane zdrowotne. Gdy klient
    tę zgodę cofnie albo skończy współpracę, pytanie o zaburzenia odżywiania
    nie pada — a wtedy nowy wynik powstawał bez ukrycia i kalorie same wracały
    klientowi na ekran, choć nikt o tym nie zdecydował (przegląd PR #80, P1).
    Ochrona nie obniża się milcząco: zdejmuje ją wyłącznie trener, świadomie,
    trasą „odsłoń wynik”."""
    if PYTANIE_ZABURZENIA in (answers or {}):
        return False  # pytanie padło — decyduje bieżąca odpowiedź
    poprzedni = (
        db.query(CalorieEstimate)
        .filter_by(client_id=submission.client_id)
        .order_by(CalorieEstimate.version_no.desc(), CalorieEstimate.created_at.desc())
        .first()
    )
    return bool(poprzedni and poprzedni.hidden_for_client)


def przelicz_po_przeslaniu(db: Session, *, submission: InterviewSubmission,
                           answers: dict[str, dict]) -> CalorieEstimate | None:
    """Nowa wersja bilansu dla przesłania typu `zapotrzebowanie`. Brak danych
    (np. pytanie zdrowotne ukryte zgodą nie przeszkadza; brak masy — tak)
    = brak wyniku, bez wyjątku: przesłanie i tak jest ważne."""
    if submission.typ != D.ZAPOTRZEBOWANIE:
        return None
    wejscie = Z.z_odpowiedzi(D.wartosci(answers))
    try:
        wynik = Z.oblicz(wejscie)
    except Z.BrakDanych:
        return None
    est = CalorieEstimate(
        id=new_id("CAL"), client_id=submission.client_id, submission_id=submission.id,
        version_no=submission.version_no,
        # `safety_flag` przesłania = odpowiedź „Tak / Nie wiem / Wolę omówić”
        # na pytanie o zaburzenia odżywiania (szersza reguła niż specyfikacja —
        # decyzja właściciela nr 2, patrz `docs/WYWIAD.md`).
        hidden_for_client=(
            bool(submission.safety_flag)
            or _ukrycie_odziedziczone(db, submission, answers)
        ),
    )
    _zapisz_wynik(est, wejscie, wynik)
    db.add(est)
    db.flush()
    return est


#: Kolejność „od najnowszego”. Data rozstrzyga przy równym numerze wersji —
#: numeracja biegnie po przesłaniach wywiadu, a wiersze mogą pochodzić
#: z dwóch pokoleń silnika.
_OD_NAJNOWSZYCH = (CalorieEstimate.version_no.desc(), CalorieEstimate.created_at.desc())


def ostatni(db: Session, client_id: str) -> CalorieEstimate | None:
    return (db.query(CalorieEstimate).filter_by(client_id=client_id)
            .order_by(*_OD_NAJNOWSZYCH).first())


def historia(db: Session, client_id: str) -> list[CalorieEstimate]:
    return (db.query(CalorieEstimate).filter_by(client_id=client_id)
            .order_by(*_OD_NAJNOWSZYCH).all())


def kcal_obowiazujace(est: CalorieEstimate) -> int:
    return est.override_kcal if est.override_kcal is not None else est.kcal


def _json(tekst: str | None, domyslne: Any) -> Any:
    try:
        return json.loads(tekst) if tekst else domyslne
    except ValueError:
        return domyslne


def wejscia(est: CalorieEstimate) -> dict[str, Any]:
    """Zamrożone wejścia wzoru (bez odpowiedzi zdrowotnych — te zostają
    w wywiadzie, za zgodą domeny)."""
    w = _json(est.inputs_json, {})
    return w if isinstance(w, dict) else {}


def flagi(est: CalorieEstimate) -> list[str]:
    wart = _json(est.flags_json, [])
    return [f for f in wart if isinstance(f, str)] if isinstance(wart, list) else []


def stary_wzor(est: CalorieEstimate) -> bool:
    """Wiersz policzony silnikiem sprzed wyrównania do specyfikacji 1.0."""
    return (est.formulas_version or Z.FORMULAS_VERSION_PAL) == Z.FORMULAS_VERSION_PAL


def cel_redukcja(est: CalorieEstimate | None) -> bool:
    """Czy z wywiadu wynika cel „redukcja”. Rozumie kod silnika 1.0 („cut”)
    i etykietę zapisywaną przez silnik 0.62.0 („Redukcja masy ciała”) —
    porównanie wyłącznie z kodem przestałoby działać dla historii."""
    if est is None:
        return False
    return wejscia(est).get("cel") in ("cut", "redukcja", "Redukcja masy ciała", Z.CEL_REDUKCJA)


def ukryty_dla_klienta(est: CalorieEstimate) -> tuple[bool, str]:
    """(czy ukryty, powód). Zaburzenia odżywiania → odwracalne przez trenera;
    osoba niepełnoletnia → nieodwracalne (wymaga zgody opiekuna)."""
    if Z.FLAGA_MALOLETNI in flagi(est):
        return True, "maloletni"
    if est.hidden_for_client:
        return True, "zaburzenia"
    return False, ""


def _flagi_out(est: CalorieEstimate, *, zdrowie: bool, dla: str) -> list[dict[str, Any]]:
    """Flagi z opisem. `zdrowie=False` (trener bez zgody) wycina flagi
    wynikające z odpowiedzi zdrowotnych."""
    out = []
    for kod in flagi(est):
        if kod in Z.FLAGI_ZDROWOTNE and not zdrowie:
            continue
        opis = Z.FLAGI_OPIS.get(kod)
        if opis is None:
            continue
        tekst = opis.trener if dla == "coach" else opis.klient
        if tekst is None:
            continue
        out.append({"code": kod, "etykieta": opis.etykieta, "opis": tekst, "poziom": opis.poziom})
    return out


#: Zamiast wiersza o celu, gdy korekta jest zasłonięta (patrz `_pelny`).
WIERSZ_KOREKTA_ZASLONIETA = (
    "korekta celu: zmieniona ze względu na odpowiedzi, których nie widzisz "
    "(brak zgody na dane zdrowotne)"
)


def _podstawienie_out(est: CalorieEstimate, *, zaslon_korekte: bool) -> list[str]:
    wiersze = _json(est.podstawienie_json, [])
    if not zaslon_korekte:
        return wiersze
    return [
        WIERSZ_KOREKTA_ZASLONIETA if isinstance(w, str) and w.startswith("cel:") else w
        for w in wiersze
    ]


def _pelny(est: CalorieEstimate, *, dla: str, zdrowie: bool) -> dict[str, Any]:
    dane = wejscia(est)
    legacy = stary_wzor(est)
    ukryty, powod = ukryty_dla_klienta(est)
    # Wyłączony deficyt zdarza się WYŁĄCZNIE przy ciąży, karmieniu albo braku
    # miesiączki, więc „cel: redukcja → bez korekty” zawężałoby ukryte flagi do
    # dwóch konkretnych odpowiedzi (przegląd PR #80, P1). Bez zgody zdrowotnej
    # zastępujemy wiersz i sam procent neutralnym komunikatem.
    deficyt_wylaczony = Z.FLAGA_DEFICYT_WYLACZONY in flagi(est)
    zaslon_korekte = deficyt_wylaczony and not zdrowie and dla != "client"
    out: dict[str, Any] = {
        "id": est.id, "submission_id": est.submission_id, "version_no": est.version_no,
        "created_at": est.created_at, "formulas_version": est.formulas_version or Z.FORMULAS_VERSION_PAL,
        "legacy": legacy, "inputs": dane,
        "ppm": est.ppm, "pal": est.pal, "cpm": est.cpm,
        "korekta_pct": None if zaslon_korekte else est.korekta_pct,
        "kcal": est.kcal, "kcal_effective": kcal_obowiazujace(est),
        "podstawienie": _podstawienie_out(est, zaslon_korekte=zaslon_korekte),
        "ostrzezenia": _json(est.ostrzezenia_json, []),
        # Trener bez zgody zdrowotnej widzi SAM FAKT ukrycia (musi wiedzieć, że
        # klient nie zna liczb, i móc je odsłonić po rozmowie), ale nigdy POWODU:
        # powód wynika wprost z odpowiedzi na pytanie o zaburzenia odżywiania
        # (przegląd PR #80, P0). Klient zawsze zna powód ukrycia własnego wyniku.
        "hidden_for_client": ukryty,
        "hidden_reason": powod if (zdrowie or dla == "client") else None,
        "unhidden_by": est.unhidden_by, "unhidden_at": est.unhidden_at,
        "override": {"kcal": est.override_kcal, "by": est.override_by, "at": est.override_at,
                     "reason": est.override_reason} if est.override_kcal is not None else None,
        "flags": _flagi_out(est, zdrowie=zdrowie, dla=dla),
        "flags_hidden": bool(not zdrowie and (set(flagi(est)) & Z.FLAGI_ZDROWOTNE)),
    }
    if legacy:
        out["legacy_message"] = KOMUNIKAT_STARY_WYNIK
        return out
    out.update({
        "bmi": est.bmi, "ppm_mifflin": est.ppm_mifflin, "ppm_katch": est.ppm_katch,
        "ppm_used": est.ppm_used, "ppm_source": est.ppm_source,
        "neat_multiplier": est.neat_multiplier, "training_kcal_day": est.training_kcal_day,
        "tef": est.tef, "cpm_min": est.cpm_min, "cpm_max": est.cpm_max,
        "target_kcal": est.target_kcal, "macro": _json(est.macro_json, None),
        "tempo": _json(est.tempo_json, None),
        "expected_weekly_change_kg": est.expected_weekly_change_kg,
    })
    return out


def widok(est: CalorieEstimate | None, *, viewer: str, has_coach: bool = True,
          zdrowie: bool = True) -> dict[str, Any]:
    """Odpowiedź API. Trener: pełny bilans (flagi zdrowotne tylko przy
    `zdrowie=True`). Klient: pełny, chyba że wynik jest przed nim ukryty —
    wtedy wyłącznie status i komunikat, żadnej liczby wyniku ani wejścia
    wzoru (masa ciała też jest liczbą)."""
    if est is None:
        return {"status": "none", "estimate": None}
    if viewer == "client":
        ukryty, powod = ukryty_dla_klienta(est)
        if ukryty:
            if powod == "maloletni":
                komunikat = KOMUNIKAT_MALOLETNI
            else:
                komunikat = KOMUNIKAT_UKRYTY if has_coach else KOMUNIKAT_UKRYTY_BEZ_TRENERA
            return {"status": "hidden", "estimate": None, "message": komunikat,
                    "hidden_reason": powod, "version_no": est.version_no}
    return {"status": "ok",
            "estimate": _pelny(est, dla=("coach" if viewer == "coach" else "client"), zdrowie=zdrowie),
            "message": KOMUNIKAT_STARY_WYNIK if stary_wzor(est) else None,
            "coach_note": KOMUNIKAT_FLAGI_BEZ_ZGODY if (viewer == "coach" and not zdrowie
                                                        and set(flagi(est)) & Z.FLAGI_ZDROWOTNE) else None}


def nadpisz(db: Session, est: CalorieEstimate, *, actor: User, kcal: int | None, reason: str) -> CalorieEstimate:
    """Trener nadpisuje wynik (kcal=None cofa nadpisanie). Powód obowiązkowy."""
    if kcal is not None and not (NADPISANIE_MIN <= kcal <= NADPISANIE_MAX):
        raise ValueError(f"Nadpisanie poza zakresem {NADPISANIE_MIN}–{NADPISANIE_MAX} kcal.")
    if not reason.strip():
        raise ValueError("Podaj powód nadpisania (klient go zobaczy).")
    poprzednie = est.override_kcal
    if kcal is None and poprzednie is None:
        return est  # nie ma czego cofać — bez zdarzenia
    est.override_kcal = kcal
    est.override_by = actor.id if kcal is not None else None
    est.override_at = now_iso() if kcal is not None else None
    est.override_reason = reason.strip() if kcal is not None else None
    record_event(
        db, action="CALORIE_ESTIMATE_OVERRIDDEN", actor_id=actor.id, subject_ids=[est.client_id],
        payload={"estimate_id": est.id, "from": poprzednie, "to": kcal, "formula_kcal": est.kcal},
        summary=("Trener nadpisał zapotrzebowanie" if kcal is not None else "Trener cofnął nadpisanie zapotrzebowania"),
    )
    db.flush()
    return est


def odblokuj(db: Session, est: CalorieEstimate, *, actor: User) -> CalorieEstimate:
    """Trener po rozmowie z klientem odsłania liczby (flaga zaburzeń
    odżywiania). Ukrycia z powodu niepełnoletności ta trasa nie zdejmuje —
    to nie jest kwestia rozmowy, tylko zgody opiekuna."""
    if est.hidden_for_client:
        est.hidden_for_client = False
        est.unhidden_by = actor.id
        est.unhidden_at = now_iso()
        record_event(
            db, action="CALORIE_ESTIMATE_UNHIDDEN", actor_id=actor.id, subject_ids=[est.client_id],
            payload={"estimate_id": est.id}, summary="Zmieniono widoczność wyniku zapotrzebowania dla klienta",
        )
        db.flush()
    return est
