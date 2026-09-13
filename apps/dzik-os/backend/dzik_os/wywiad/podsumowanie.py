"""Deterministyczne podsumowanie wywiadu i podpowiedzi do konfiguratorów.

Bez modelu językowego: każdy punkt podsumowania wskazuje odpowiedź, z
której wynika (pytanie, wersja, autor, czas). Podpowiedzi do konfiguratora
treningu i kreatora dań to jawne mapowanie faktów → pola wejścia, a nie
decyzja: trener widzi źródło i może każdą podpowiedź odrzucić. Alergie
wchodzą jako OGRANICZENIA (brak informacji ≠ brak alergii); preferencje
i nietolerancje — jako preferencje.
"""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from ..models import InterviewSubmission
from . import definicje as D
from . import serwis

_POZIOM = {
    "Zaczynam od zera": "beginner",
    "Trenowałem(-am) kiedyś, wracam po przerwie": "beginner",
    "Trenuję regularnie od ponad roku": "intermediate",
    "Trenuję od lat, znam swoje ciało": "advanced",
}

_SPRZET_DOM = {
    "Dom — mam sprzęt (hantle, gumy, drążek)": ["dumbbells", "bands", "pullup_bar", "bodyweight"],
    "Dom — bez sprzętu, tylko masa ciała": ["bodyweight"],
    "Na zewnątrz (park, plac zabaw, bieganie)": ["bodyweight", "pullup_bar"],
}

_DNI = {"Pn": 1, "Wt": 2, "Śr": 3, "Cz": 4, "Pt": 5, "So": 6, "Nd": 7}

#: Alergeny kreatora dań (kulinaria.dane.ALERGENY) rozpoznawane w tekście
#: odpowiedzi — dopasowanie słów kluczowych, wyłącznie jako wstępne
#: zaznaczenie do potwierdzenia przez trenera.
_ALERGENY_SLOWA: dict[str, tuple[str, ...]] = {
    "gluten": ("gluten", "pszenic", "celiak"),
    "milk": ("mleko", "laktoz", "nabiał", "nabial"),
    "eggs": ("jaj",),
    "fish": ("ryb",),
    "shellfish": ("skorupiak", "krewet", "owoce morza"),
    "peanuts": ("orzeszk", "orzech ziemn", "fistasz"),
    "tree_nuts": ("orzech",),
    "soy": ("soj",),
    "sesame": ("sezam",),
}


def _wartosc(answers: dict[str, dict], qid: str) -> str | None:
    a = answers.get(qid)
    if not isinstance(a, dict) or a.get("skipped"):
        return None
    v = a.get("value")
    return v.strip() if isinstance(v, str) and v.strip() else None


def _zrodlo(sub: InterviewSubmission, answers: dict[str, dict], qid: str, label: str) -> dict[str, Any]:
    a = answers.get(qid) or {}
    return {"question_id": qid, "label": label, "version_no": sub.version_no, "typ": sub.typ,
            "entered_by": a.get("entered_by"), "at": a.get("at")}


def podsumowanie(db: Session, client_id: str, *, widoczne: set[str]) -> dict[str, Any]:
    """Cele, ograniczenia, preferencje, do wyjaśnienia, do aktualizacji —
    z ostatnich przesłanych wersji obu formularzy. Odpowiedzi spoza
    widocznych domen są pomijane (nie „ukryte z gwiazdką”)."""
    cele: list[dict] = []
    ograniczenia: list[dict] = []
    preferencje: list[dict] = []
    do_wyjasnienia: list[dict] = []
    do_aktualizacji: list[dict] = []
    for typ in D.TYPY:
        sub = serwis.ostatnie_przeslanie(db, client_id, typ)
        if sub is None:
            continue
        defn = D.definicja(typ)
        answers = json.loads(sub.answers_json or "{}")
        for q in defn.questions:
            if q.consent_domain and q.consent_domain not in widoczne:
                continue
            v = _wartosc(answers, q.question_id)
            if v is None:
                continue
            punkt = {"text": v, "source": _zrodlo(sub, answers, q.question_id, q.label)}
            if v in D.ODP_DO_OMOWIENIA:
                do_wyjasnienia.append(punkt)
                continue
            if q.section in ("cel",) or q.question_id in ("gw_a1", "gw_a3"):
                cele.append(punkt)
            elif q.section in ("zdrowie", "ograniczenia") or q.fact_key in serwis.FAKTY_PLANU:
                if q.fact_key in ("alergie", "alergie_status", "nietolerancje") or q.section == "zdrowie" \
                        or q.section == "ograniczenia":
                    if v == D.ODP_NIE_ZGLASZAM or v == "Nie":
                        continue
                    ograniczenia.append(punkt)
                else:
                    preferencje.append(punkt)
            elif q.section in ("odzywianie", "historia_odzywiania", "preferencje", "wspolpraca",
                               "codziennosc", "organizacja"):
                preferencje.append(punkt)
        for c in serwis.otwarte_doprecyzowania(db, client_id, typ):
            do_aktualizacji.append({"text": c.message or "Trener prosi o uzupełnienie wskazanych odpowiedzi.",
                                    "question_ids": json.loads(c.question_ids_json or "[]"),
                                    "typ": typ, "created_at": c.created_at, "clarification_id": c.id})
    return {"cele": cele, "ograniczenia": ograniczenia, "preferencje": preferencje,
            "do_wyjasnienia": do_wyjasnienia, "do_aktualizacji": do_aktualizacji}


def podpowiedzi(db: Session, client_id: str, *, widoczne: set[str]) -> dict[str, Any]:
    """Wejścia konfiguratorów wyprowadzone z faktów (ostatnia wersja
    wstępnego + głębokiego). Każda podpowiedź ma źródło; brak faktu =
    brak podpowiedzi (nie wartość domyślna)."""
    wst = serwis.ostatnie_przeslanie(db, client_id, D.WSTEPNY)
    gle = serwis.ostatnie_przeslanie(db, client_id, D.GLEBOKI)
    if wst is None and gle is None:
        return {"available": False, "reason": "Brak przesłanego wywiadu.", "training": {}, "nutrition": {},
                "sources": [], "interview_submission_ids": {}}
    a_w = json.loads(wst.answers_json) if wst else {}
    a_g = json.loads(gle.answers_json) if gle else {}
    zrodla: list[dict] = []
    training: dict[str, Any] = {}
    nutrition: dict[str, Any] = {"allergens": [], "allergen_status": None, "preferences": [],
                                 "intolerances": None, "exclusions": None, "cooking": None}
    ostrzezenia: list[str] = []

    def src(sub, answers, qid, label):
        zrodla.append(_zrodlo(sub, answers, qid, label))

    if wst is not None:
        d = D.definicja(D.WSTEPNY).by_id
        if (v := _wartosc(a_w, "cel_glowny")):
            training["goal_text"] = v
            nutrition["goal_text"] = v
            src(wst, a_w, "cel_glowny", d["cel_glowny"].label)
        if (v := _wartosc(a_w, "doswiadczenie")) and v in _POZIOM:
            training["level"] = _POZIOM[v]
            src(wst, a_w, "doswiadczenie", d["doswiadczenie"].label)
        if (v := _wartosc(a_w, "dostepnosc")):
            m = re.search(r"\d+", v)
            if m:
                training["days_per_week"] = max(1, min(7, int(m.group())))
                src(wst, a_w, "dostepnosc", d["dostepnosc"].label)
        if (v := _wartosc(a_w, "preferowane_dni")):
            dni = sorted({_DNI[p.strip()] for p in v.split(",") if p.strip() in _DNI})
            if dni:
                training["available_weekdays"] = dni
                src(wst, a_w, "preferowane_dni", d["preferowane_dni"].label)
        if (v := _wartosc(a_w, "sprzet")):
            training["equipment_ids"] = _SPRZET_DOM.get(v, ["full_gym"])
            training["equipment_text"] = v
            src(wst, a_w, "sprzet", d["sprzet"].label)
        if "health_data" in widoczne:
            urazy = _wartosc(a_w, "urazy_czy")
            bol = _wartosc(a_w, "bol_obecny")
            ogr = [x for x in (_wartosc(a_w, "urazy_opis"), _wartosc(a_w, "urazy_ograniczenia"),
                               _wartosc(a_w, "bol_opis")) if x]
            training["health"] = {"injuries_declared": urazy == D.ODP_TAK, "pain_now": bol == D.ODP_TAK,
                                  "notes": ogr,
                                  "to_discuss": [x for x in (urazy, bol) if x in D.ODP_DO_OMOWIENIA]}
            if urazy is None or bol is None:
                ostrzezenia.append("Brak odpowiedzi o urazach/bólu — to NIE oznacza braku ograniczeń.")
            for qid in ("urazy_czy", "bol_obecny", "urazy_opis", "urazy_ograniczenia", "bol_opis"):
                if _wartosc(a_w, qid):
                    src(wst, a_w, qid, d[qid].label)
        if "nutrition_data" in widoczne:
            status = _wartosc(a_w, "alergie_status")
            tekst = _wartosc(a_w, "alergie")
            nutrition["allergen_status"] = status
            if status is None and tekst is None:
                ostrzezenia.append("Brak informacji o alergiach — nie zakładaj, że ich nie ma; potwierdź z klientem.")
            if tekst and tekst.strip().casefold() not in ("nie mam", "nie", "brak", D.ODP_NIE_ZGLASZAM.casefold()):
                t = tekst.casefold()
                nutrition["allergens"] = sorted({k for k, slowa in _ALERGENY_SLOWA.items()
                                                 if any(s in t for s in slowa)})
                nutrition["allergens_text"] = tekst
                if not nutrition["allergens"]:
                    ostrzezenia.append("Alergie opisane słownie nie pasują do listy alergenów kreatora — ustaw ręcznie.")
                src(wst, a_w, "alergie", d["alergie"].label)
            if status:
                src(wst, a_w, "alergie_status", d["alergie_status"].label)
            if (v := _wartosc(a_w, "nietolerancje")):
                nutrition["intolerances"] = v
                src(wst, a_w, "nietolerancje", d["nietolerancje"].label)
            if (v := _wartosc(a_w, "wykluczenia_preferencje")):
                nutrition["exclusions"] = v
                src(wst, a_w, "wykluczenia_preferencje", d["wykluczenia_preferencje"].label)
            if (v := _wartosc(a_w, "zywienie_styl")):
                nutrition["preferences"].append(v)
                src(wst, a_w, "zywienie_styl", d["zywienie_styl"].label)
    if gle is not None:
        d = D.definicja(D.GLEBOKI).by_id
        if "health_data" in widoczne:
            lek = _wartosc(a_g, "gw_c2")
            if lek:
                training.setdefault("health", {})["doctor_restriction"] = lek
                src(gle, a_g, "gw_c2", d["gw_c2"].label)
            if (v := _wartosc(a_g, "gw_c1")) and v != "Żadne z powyższych":
                training.setdefault("health", {})["prescreen"] = v
                src(gle, a_g, "gw_c1", d["gw_c1"].label)
        if "nutrition_data" in widoczne and (v := _wartosc(a_g, "gw_f2")):
            nutrition["cooking"] = v
            src(gle, a_g, "gw_f2", d["gw_f2"].label)
        if (v := _wartosc(a_g, "gw_g1")):
            training["week_map"] = v
            src(gle, a_g, "gw_g1", d["gw_g1"].label)
    return {
        "available": True, "training": training, "nutrition": nutrition, "sources": zrodla,
        "warnings": ostrzezenia,
        "interview_submission_ids": {**({D.WSTEPNY: wst.id} if wst else {}), **({D.GLEBOKI: gle.id} if gle else {})},
    }
