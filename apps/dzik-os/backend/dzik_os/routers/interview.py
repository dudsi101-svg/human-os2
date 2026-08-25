"""Głęboki wywiad — drugi przepływ mechanizmu rozmowy (flow='deep').

Cały mechanizm (stan, wersjonowanie odpowiedzi, zgody per domena,
wznowienie, podsumowanie i dwie akceptacje) pochodzi z
`routers/onboarding.build_router`; ten moduł podaje wyłącznie
konfigurację scenariusza z `interview_flow`.

Różnice względem rozmowy startowej — świadome, nie przypadkowe:

* **zero AI** — podsumowanie zawsze deterministyczne, z jawnym powodem
  (prompt rozmowy startowej nie zna pól wywiadu; ewentualna zmiana to
  osobna decyzja właściciela i osobna runda);
* **bez celu** — wywiad nie tworzy `Goal` (cel główny powstaje
  w rozmowie startowej; wywiad go pogłębia, nie dubluje);
* **flagi wyboru** — przesiew bezpieczeństwa (moduł C) i pytanie
  o relację z ciałem (moduł E) podnoszą flagę sesji spokojnym
  komunikatem z `interview_flow.flag_message_for`.
"""

from __future__ import annotations

from ..interview_flow import DEEP_STEP_BY_ID, DEEP_STEPS, deep_triggered, flag_message_for
from ..onboarding_flow import plan_steps
from .onboarding import FlowConfig, build_router

AI_DISABLED_REASON = (
    "W głębokim wywiadzie nic nie jest wysyłane do dostawcy modelu — "
    "podsumowanie powstaje zawsze krok po kroku z Twoich własnych słów."
)

DEEP_CFG = FlowConfig(
    flow="deep",
    path_prefix="interview",
    label_acc="głęboki wywiad",
    label_nom="Głęboki wywiad",
    label_gen="głębokiego wywiadu",
    steps_by_id=DEEP_STEP_BY_ID,
    plan=lambda answers, domains: plan_steps(
        answers, allowed_domains=domains, steps=DEEP_STEPS, triggered=deep_triggered
    ),
    event_prefix="INTERVIEW",
    goal_on_approve=False,
    ai_enabled=False,
    ai_disabled_reason=AI_DISABLED_REASON,
    flag_message_for=flag_message_for,
)

router = build_router(DEEP_CFG)
