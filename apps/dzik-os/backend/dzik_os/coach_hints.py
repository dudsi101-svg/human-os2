"""Podpowiedzi z rozmów dla trenera — mapowanie pól profilu na obszary pracy.

Odpowiedzi z rozmowy startowej i głębokiego wywiadu trafiają (po
zatwierdzeniu przez klienta) do pól profilu. Ten moduł mówi wyłącznie,
KTÓRE pole jest istotne przy układaniu KTÓREGO elementu (plan, dieta,
harmonogram, współpraca) — żeby trener widział deklaracje podopiecznego
tam, gdzie podejmuje decyzję, a nie w osobnej zakładce.

Granice (Human OS / INTENDED_PURPOSE):

* podpowiedź to DOSŁOWNA deklaracja klienta z proweniencją (pytanie,
  moduł, przepływ) — nigdy interpretacja, wyliczenie ani rekomendacja;
* aplikacja niczego nie stosuje sama: trener czyta i decyduje;
* pola wrażliwe podlegają dokładnie tym samym zgodom co w profilu
  (mapowanie domen bierze się WPROST ze scenariuszy rozmów — jedno
  źródło prawdy, patrz `field_consent_domains`).
"""

from __future__ import annotations

from .interview_flow import DEEP_STEPS
from .onboarding_flow import STEPS, Step

AREA_PLAN = "PLAN"
AREA_DIETA = "DIETA"
AREA_HARMONOGRAM = "HARMONOGRAM"
AREA_WSPOLPRACA = "WSPOLPRACA"
AREAS = (AREA_PLAN, AREA_DIETA, AREA_HARMONOGRAM, AREA_WSPOLPRACA)

DISCLAIMER = (
    "To dosłowne deklaracje podopiecznego z rozmowy startowej i głębokiego "
    "wywiadu — punkt wyjścia do Twojej decyzji, nie zalecenie aplikacji."
)

#: Pole profilu -> obszary, przy których warto je pokazać. Pole może
#: zasilać kilka obszarów (np. charakter pracy: i plan, i dietę).
#: Test pilnuje, że KAŻDE pole obu scenariuszy jest tu ujęte świadomie —
#: nowe pytanie bez wpisu tutaj czerwieni build, zamiast po cichu zniknąć.
HINT_AREAS: dict[str, tuple[str, ...]] = {
    # --- rozmowa startowa -------------------------------------------------
    "cel_glowny": (AREA_PLAN, AREA_DIETA),
    "cel_termin": (AREA_PLAN, AREA_DIETA),
    "doswiadczenie": (AREA_PLAN,),
    "wsparcie_techniki": (AREA_PLAN,),
    "dostepnosc_tygodniowa": (AREA_PLAN, AREA_HARMONOGRAM),
    "dni_treningowe": (AREA_PLAN, AREA_HARMONOGRAM),
    "pora_treningu": (AREA_PLAN, AREA_HARMONOGRAM),
    "sprzet": (AREA_PLAN,),
    "sprzet_domowy": (AREA_PLAN,),
    "ograniczenia_organizacyjne": (AREA_PLAN, AREA_HARMONOGRAM),
    "urazy_deklaracja": (AREA_PLAN,),
    "urazy": (AREA_PLAN,),
    "ograniczenia_ruchu": (AREA_PLAN,),
    "bol_biezacy": (AREA_PLAN,),
    "bol_opis": (AREA_PLAN,),
    "sen_godziny": (AREA_PLAN,),
    "poziom_stresu": (AREA_PLAN, AREA_WSPOLPRACA),
    "preferencje_zywieniowe": (AREA_DIETA,),
    "alergie": (AREA_DIETA,),
    "suplementacja_deklaracja": (AREA_DIETA,),
    "preferencje_komunikacji": (AREA_WSPOLPRACA,),
    # --- głęboki wywiad ---------------------------------------------------
    "gw_cel_scena": (AREA_PLAN, AREA_WSPOLPRACA),
    "gw_cel_waznosc": (AREA_WSPOLPRACA,),
    "gw_cel_waznosc_powod": (AREA_WSPOLPRACA,),
    "gw_cel_wlasnosc": (AREA_WSPOLPRACA,),
    "gw_proby_historia": (AREA_PLAN, AREA_WSPOLPRACA),
    "gw_sygnaly_4tyg": (AREA_PLAN, AREA_WSPOLPRACA),
    "gw_najlepszy_okres": (AREA_PLAN,),
    "gw_ruch_preferencje": (AREA_PLAN,),
    "gw_trener_historia": (AREA_WSPOLPRACA,),
    "gw_reakcja_potkniecie": (AREA_PLAN, AREA_WSPOLPRACA),
    "gw_najdluzszy_okres": (AREA_PLAN,),
    "gw_przesiew_objawy": (AREA_PLAN,),
    "gw_lekarz_ograniczenie": (AREA_PLAN,),
    "gw_lekarz_ograniczenie_opis": (AREA_PLAN,),
    "gw_leki_deklaracja": (AREA_PLAN, AREA_DIETA),
    "gw_operacje_urazy": (AREA_PLAN,),
    "gw_bole_nawracajace": (AREA_PLAN,),
    "gw_cykl_uwagi": (AREA_PLAN, AREA_DIETA),
    "gw_sen_rytm": (AREA_PLAN, AREA_HARMONOGRAM),
    "gw_sen_jakosc": (AREA_PLAN,),
    "gw_sen_zaklocenia": (AREA_PLAN,),
    "gw_zmianowosc": (AREA_HARMONOGRAM,),
    "gw_zmianowosc_wzor": (AREA_HARMONOGRAM, AREA_PLAN),
    "gw_regeneracja_nawyki": (AREA_PLAN,),
    "gw_stres_poziom": (AREA_PLAN, AREA_WSPOLPRACA),
    "gw_stres_zrodlo": (AREA_WSPOLPRACA,),
    "gw_jedzenie_emocje": (AREA_DIETA,),
    "gw_jedzenie_emocje_kiedy": (AREA_DIETA,),
    "gw_relacja_cialo": (AREA_WSPOLPRACA,),
    "gw_otoczenie": (AREA_DIETA, AREA_WSPOLPRACA),
    "gw_dzien_jedzeniowy": (AREA_DIETA,),
    "gw_gotowanie": (AREA_DIETA,),
    "gw_poza_domem": (AREA_DIETA,),
    "gw_produkty_preferencje": (AREA_DIETA,),
    "gw_alkohol_slodycze": (AREA_DIETA,),
    "gw_diety_historia": (AREA_DIETA,),
    "gw_nawodnienie": (AREA_DIETA,),
    "gw_tydzien_mapa": (AREA_PLAN, AREA_HARMONOGRAM),
    "gw_praca_charakter": (AREA_PLAN, AREA_DIETA),
    "gw_wyjazdy": (AREA_DIETA, AREA_HARMONOGRAM),
    "gw_dzien_nieprzewidywalny": (AREA_PLAN, AREA_HARMONOGRAM),
    "gw_pomiary_start": (AREA_PLAN,),
    "gw_mierniki": (AREA_WSPOLPRACA,),
    "gw_zdjecia_chce": (AREA_WSPOLPRACA,),
    "gw_wspolpraca_podzial": (AREA_WSPOLPRACA,),
    "gw_feedback_forma": (AREA_WSPOLPRACA,),
    "gw_ryzyko_rezygnacji": (AREA_WSPOLPRACA,),
    "gw_raport_slot": (AREA_HARMONOGRAM, AREA_WSPOLPRACA),
    "gw_otwarte": (AREA_PLAN, AREA_DIETA, AREA_WSPOLPRACA),
}


def _scenario_steps() -> list[tuple[str, Step]]:
    return [("start", s) for s in STEPS] + [("deep", s) for s in DEEP_STEPS]


#: Pole profilu -> (pytanie, moduł, przepływ) — proweniencja podpowiedzi
#: brana WPROST ze scenariuszy (etykiety nie są nigdzie duplikowane).
FIELD_META: dict[str, dict] = {
    step.profile_field: {
        "question": step.question,
        "topic": step.topic,
        "flow": flow,
        "sensitive": step.sensitive,
    }
    for flow, step in _scenario_steps()
    if step.profile_field is not None
}

#: Kolejność pól = kolejność pytań w scenariuszach (stabilny porządek).
FIELD_ORDER: dict[str, int] = {
    field: i for i, field in enumerate(FIELD_META)
}


def field_consent_domains() -> dict[str, str]:
    """Domena zgody per pole wrażliwe — jedno źródło prawdy: scenariusze.

    Uzupełnia (nie zastępuje) ręczną mapę w `routers/profile.py`; pole
    wrażliwe spoza scenariuszy nadal domyślnie podlega domenie zdrowia."""
    return {
        step.profile_field: step.consent_domain
        for _, step in _scenario_steps()
        if step.profile_field is not None
        and step.sensitive
        and step.consent_domain is not None
    }


def hints_for_area(area: str, values: dict[str, str]) -> list[dict]:
    """Podpowiedzi obszaru z bieżących wartości pól profilu.

    `values` to pola już przefiltrowane przez zgody (ta sama ścieżka co
    widok profilu) — tu tylko wybieramy istotne dla obszaru i dokładamy
    proweniencję. Kolejność = kolejność pytań w scenariuszach."""
    picked = [
        field
        for field, areas in HINT_AREAS.items()
        if area in areas and values.get(field)
    ]
    picked.sort(key=lambda f: FIELD_ORDER.get(f, 10_000))
    return [
        {
            "field_key": field,
            "value": values[field],
            **FIELD_META.get(
                field,
                {"question": field, "topic": "", "flow": "start", "sensitive": False},
            ),
        }
        for field in picked
    ]
