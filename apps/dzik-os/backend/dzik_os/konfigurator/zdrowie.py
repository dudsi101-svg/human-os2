"""Bramka zdrowotna (§5). Uruchamiana PRZED wyborem układu.

Kolejność ważności: objawy alarmowe → sytuacje do oceny specjalisty →
brak odpowiedzi → zakres wieku. Pola zdrowotne nigdy nie domyślają się
do „nie": `null` = brak odpowiedzi = `needs_input`. Sama nazwa choroby
nie zakazuje ruchu — bez ustalonego poziomu wysiłku daje `needs_review`.
Aktualne objawy alarmowe wygrywają z każdą wcześniejszą zgodą.
"""

from __future__ import annotations

POLA_TAK_NIE = (
    "current_red_flag", "unexplained_exertional_symptoms", "known_condition",
    "acute_injury_or_surgery", "pregnancy_postpartum", "active_rehabilitation",
)

PYTANIA = {
    "current_red_flag": "Czy obecnie występuje ból lub ucisk w klatce, omdlenie, nietypowa silna duszność albo nowe objawy neurologiczne?",
    "unexplained_exertional_symptoms": "Czy podczas wysiłku pojawiają się niewyjaśnione objawy (np. ból w klatce, zawroty głowy, nietypowa duszność)?",
    "known_condition": "Czy istnieje rozpoznana choroba przewlekła lub schorzenie istotne dla treningu?",
    "acute_injury_or_surgery": "Czy w ostatnim czasie wystąpił uraz lub zabieg operacyjny?",
    "pregnancy_postpartum": "Czy występuje ciąża lub okres połogu?",
    "active_rehabilitation": "Czy trwa aktywna rehabilitacja?",
    "restrictions_understood": "Czy zalecenia specjalisty (zakazane ćwiczenia, wzorce, limity) są znane i zrozumiałe?",
}


def ocen_zdrowie(wejscie: dict) -> tuple[str | None, list[dict], list[str]]:
    """Zwraca (status blokujący albo None, issues, questions)."""
    h = wejscie.get("health") or {}
    issues: list[dict] = []
    questions: list[str] = []

    # 1. Objawy alarmowe — pierwszeństwo przed wszystkim (także przed zgodą).
    if h.get("current_red_flag") is True:
        issues.append({
            "code": "URGENT_STOP", "severity": "critical", "rule_id": "H_HEALTH_GATE",
            "message": "Aktualne objawy alarmowe: przerwij trening i skorzystaj z pilnej pomocy "
                       "(w Polsce 112 przy podejrzeniu nagłego zagrożenia). Plan nie zostanie wygenerowany.",
        })
        return "urgent_stop", issues, questions

    # 2. Brak odpowiedzi = pytanie, nigdy zielone światło.
    brak = [p for p in POLA_TAK_NIE if h.get(p) is None]
    if h.get("restrictions_understood") is None and h.get("known_condition"):
        brak.append("restrictions_understood")
    if brak:
        for p in brak:
            questions.append(PYTANIA[p])
        issues.append({
            "code": "HEALTH_ANSWERS_MISSING", "severity": "error", "rule_id": "H_HEALTH_GATE",
            "message": "Brak odpowiedzi na pytania kwalifikacji zdrowotnej: " + ", ".join(brak) + ".",
        })
        return "needs_input", issues, questions

    # 3. Sytuacje do oceny specjalisty — bez automatycznej ścieżki specjalistycznej.
    powody = []
    if h.get("unexplained_exertional_symptoms"):
        powody.append("niewyjaśnione objawy wysiłkowe")
    if h.get("acute_injury_or_surgery"):
        powody.append("świeży uraz lub zabieg")
    if h.get("pregnancy_postpartum"):
        powody.append("ciąża lub połóg")
    if h.get("active_rehabilitation"):
        powody.append("aktywna rehabilitacja")
    if h.get("assessment") == "pending":
        powody.append("ocena specjalisty w toku")
    if h.get("known_condition") and h.get("assessment") != "completed":
        powody.append("znana choroba bez ustalonego dopuszczalnego poziomu wysiłku")
    if h.get("known_condition") and h.get("restrictions_understood") is False:
        powody.append("niejasne ograniczenia zalecone przez specjalistę")
    if powody:
        issues.append({
            "code": "NEEDS_PROFESSIONAL_REVIEW", "severity": "error", "rule_id": "H_HEALTH_GATE",
            "message": "Przed automatyczną generacją potrzebna ocena odpowiedniego specjalisty: "
                       + "; ".join(powody) + ". Choroba nie oznacza trwałego zakazu ruchu.",
        })
        return "needs_review", issues, questions

    # 4. Zakres produktu: dorośli. 65+ nie jest przeciwwskazaniem.
    wiek = wejscie.get("age")
    if wiek is not None and wiek < 18:
        issues.append({
            "code": "OUT_OF_SCOPE_AGE", "severity": "error", "rule_id": "H_SCOPE",
            "message": "Pierwsza wersja obejmuje osoby dorosłe (18+); dla osoby niepełnoletniej "
                       "potrzebna jest ścieżka z przeglądem trenera i opiekuna.",
        })
        return "needs_review", issues, questions

    return None, issues, questions
