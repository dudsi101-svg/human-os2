"""Poprawki po przeglądzie krzyżowym wywiadu z 2026-08-26 (audyt B5).

Trzy ustalenia WYSOKIE dotyczyły jednego: treść odpowiedzi zdrowotnej
wyciekała obok bramki zgód — w `safety_signals` widoku trenera, w payloadzie
niemutowalnego zdarzenia audytowego i przez niewrażliwe pytanie otwarte.
Czwarte: obietnica „zaznaczyliśmy to trenerowi" bez kanału doręczenia.
Te testy przybijają każdą poprawkę do zachowania, nie do implementacji.
"""

from __future__ import annotations

import json

from conftest import CLIENT_A, COACH, get_user_id, login
from test_wywiad import BASE, answer_ok, run_to

from dzik_os import hos_bridge
from dzik_os.db import db_session
from dzik_os.interview_flow import DEEP_STEP_BY_ID
from dzik_os.models import Notification

OBJAW_KARDIOLOGICZNY = "Ból lub ucisk w klatce piersiowej"


def _revoke(client, headers, category: str) -> None:
    consents = client.get("/api/me/consents", headers=headers).json()["consents"]
    active = next(
        c for c in consents
        if c["revoked_at"] is None and c["category"] == category
    )
    r = client.post(f"/api/me/consents/{active['id']}/revoke", headers=headers)
    assert r.status_code == 200, r.text


def _odpowiedz_z_flaga(client, ha, id_a) -> None:
    run_to(client, ha, id_a, "gw_c1")
    answer_ok(client, ha, id_a, "gw_c1", OBJAW_KARDIOLOGICZNY)


def test_sygnaly_bezpieczenstwa_podlegaja_tej_samej_zgodzie_co_tresc(seeded):
    """Ustalenie 1: trener z cofniętą zgodą zdrowotną nie widział treści
    odpowiedzi, ale widział ją w `safety_signals` obok. Sygnał niesie
    dosłowną odpowiedź (flag_options), więc rządzi nim ta sama bramka."""
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    _odpowiedz_z_flaga(seeded, ha, id_a)
    _revoke(seeded, ha, "dane_zdrowotne")

    hc = login(seeded, COACH)
    body = seeded.get(BASE.format(id_a), headers=hc).json()
    wiersz = next(a for a in body["answers"] if a["step_id"] == "gw_c1")
    assert wiersz["hidden"] is True and wiersz["value"] == ""
    assert wiersz["safety_signals"] == []
    assert wiersz["safety_flagged"] is False

    # Klient swoją odpowiedź (i sygnały) widzi zawsze.
    moje = seeded.get(BASE.format(id_a), headers=ha).json()
    mojw = next(a for a in moje["answers"] if a["step_id"] == "gw_c1")
    assert OBJAW_KARDIOLOGICZNY in mojw["safety_signals"]


def test_zdarzenie_audytowe_bez_tresci_odpowiedzi(seeded):
    """Ustalenie 3: łańcuch audytu jest niemutowalny i nie podlega
    usunięciu konta — payload flagi nie może nieść treści zdrowotnej."""
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    _odpowiedz_z_flaga(seeded, ha, id_a)

    zdarzenia = [
        e for e in hos_bridge.event_store().all()
        if e.get("event_type", "").endswith("SAFETY_FLAGGED")
    ]
    assert zdarzenia, "brak zdarzenia flagi w łańcuchu"
    for e in zdarzenia:
        payload = e.get("payload", {})
        assert "signals" not in payload
        assert payload.get("signal_count", 0) >= 1
        assert payload.get("source") in ("wybor", "przesiew")
        assert OBJAW_KARDIOLOGICZNY not in json.dumps(payload, ensure_ascii=False)


def test_pytanie_otwarte_jest_wrazliwe_z_domena_zdrowia(seeded):
    """Ustalenie 2: `gw_i5` zaprasza do wyznania czegokolwiek — bez
    `sensitive` omijało zgody w kartach podpowiedzi trenera."""
    step = DEEP_STEP_BY_ID["gw_i5"]
    assert step.sensitive is True
    from dzik_os.authz import DOMAIN_HEALTH
    assert step.consent_domain == DOMAIN_HEALTH

    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    run_to(seeded, ha, id_a, "gw_i5")
    answer_ok(seeded, ha, id_a, "gw_i5", "Leczę się na tarczycę.")
    _revoke(seeded, ha, "dane_zdrowotne")

    hc = login(seeded, COACH)
    body = seeded.get(BASE.format(id_a), headers=hc).json()
    wiersz = next(a for a in body["answers"] if a["step_id"] == "gw_i5")
    assert wiersz["hidden"] is True and wiersz["value"] == ""


def test_flaga_powiadamia_trenera_raz_i_bez_danych_zdrowotnych(seeded):
    """Ustalenie 4: komunikat obiecuje klientowi „zaznaczyliśmy to
    trenerowi" — musi istnieć kanał. Raz na sesję, bez treści odpowiedzi."""
    ha = login(seeded, CLIENT_A)
    id_a = get_user_id(seeded, ha)
    hc = login(seeded, COACH)
    id_coach = get_user_id(seeded, hc)

    _odpowiedz_z_flaga(seeded, ha, id_a)
    # Druga oflagowana odpowiedź w tej samej sesji — bez drugiego powiadomienia.
    answer_ok(seeded, ha, id_a, "gw_c2", "Tak")

    with db_session() as db:
        rows = (
            db.query(Notification)
            .filter(Notification.user_id == id_coach,
                    Notification.category == "PRZESIEW",
                    Notification.source == "onboarding")
            .all()
        )
        assert len(rows) == 1, [r.title for r in rows]
        n = rows[0]
        assert OBJAW_KARDIOLOGICZNY not in (n.title + " " + (n.body or ""))
        assert "uwagi" in n.title or "uwaga" in n.title.lower()
