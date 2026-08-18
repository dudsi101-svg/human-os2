"""Głęboka symulacja obciążeniowa Dzik OS — 10 podopiecznych z pełną historią.

Cel: sprawdzić zachowanie aplikacji, gdy WSZYSTKIE moduły pracują naraz na
realistycznym wolumenie danych (nie na szkielecie demo). Generuje dziesięć
zróżnicowanych person z kilkumiesięczną historią w każdej sekcji: profil
z proweniencją, cele, plany z wersjami, sesje treningowe z seriami, dieta,
dziennik kaloryczny, harmonogram z adherencją, raporty tygodniowe z rewizjami
i ocenami, pomiary, obserwacje, wiadomości, dokumenty, zdjęcia progresu,
płatności, zgody, konsultacje, powiadomienia push i wspólne wyzwania.

Uruchomienie (WYŁĄCZNIE lokalnie/staging — dane syntetyczne):

    python -m dzik_os.simulate                  # 10 klientów, 12 tygodni
    python -m dzik_os.simulate --clients 4 --weeks 6
    python -m dzik_os.simulate --reset          # czyści bazę przed symulacją

Moduł jest ODRĘBNY od seed.py: seed to minimalny zestaw demonstracyjny, na
którym opierają się testy; symulacja to narzędzie diagnostyczne o dużej
objętości. Żadna osoba nie jest prawdziwa — wszystkie wartości są zmyślone,
generowane deterministycznie (stałe ziarno), więc kolejne przebiegi dają
identyczne dane.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import timedelta

from .config import settings
from .consent_catalog import ONBOARDING_CATEGORIES
from .dates import local_today
from .db import db_session, run_migrations
from .hos_bridge import ConsentService, record_event
from .models import (
    Challenge,
    ChallengeEntry,
    ChallengeParticipant,
    CoachClientRelationship,
    ConsultSlot,
    DailyNutritionLog,
    Document,
    Exercise,
    FoodProduct,
    Goal,
    KnowledgeItem,
    Measurement,
    Message,
    MessageThread,
    NutritionPlan,
    NutritionPlanVersion,
    Observation,
    PaymentRecord,
    PaymentSchedule,
    ProfileField,
    ProgressPhoto,
    PushSubscription,
    RoleGrant,
    ScheduleCompletion,
    ScheduleItem,
    StoredFile,
    TrainingPlan,
    TrainingPlanVersion,
    User,
    WeeklyCheckin,
    WorkoutEntry,
    WorkoutSession,
    new_id,
)
from .security import hash_password

SIM_PASSWORD = "SymKlient#2026!x"
COACH_EMAIL = "dzik@example.com"

# Dziesięć person: różny staż, cel, sprzęt, dostępność i problemy zdrowotne —
# tak, żeby panel trenera pokazywał realnie różne stany, a nie dziesięć kopii.
PERSONAS = [
    {"email": "kamil.borowik@example.com", "name": "Kamil Borowik",
     "goal": "Redukcja 10 kg", "level": "2 lata siłowni", "sex": "M",
     "weight": 94.0, "trend": -0.45, "gear": "Siłownia komercyjna",
     "days": "pon, śr, pt", "diet": "Bez laktozy", "injury": "Kolano — dawna kontuzja ACL",
     "kcal": 2300, "adherence": 0.92, "payment": "PAID"},
    {"email": "olga.jastrzebska@example.com", "name": "Olga Jastrzębska",
     "goal": "Pierwsze podciągnięcie", "level": "Początkująca", "sex": "K",
     "weight": 61.5, "trend": -0.1, "gear": "Dom: gumy, drążek",
     "days": "wt, czw, sob", "diet": "Wegetarianka", "injury": "Brak",
     "kcal": 1900, "adherence": 0.75, "payment": "PENDING"},
    {"email": "tomasz.rys@example.com", "name": "Tomasz Ryś",
     "goal": "Masa +5 kg", "level": "5 lat treningu", "sex": "M",
     "weight": 78.2, "trend": 0.25, "gear": "Siłownia komercyjna",
     "days": "pon, wt, czw, pt", "diet": "Bez ograniczeń", "injury": "Bark — łopatka",
     "kcal": 3100, "adherence": 0.97, "payment": "PAID"},
    {"email": "natalia.sokol@example.com", "name": "Natalia Sokół",
     "goal": "Powrót po ciąży", "level": "Wraca po przerwie", "sex": "K",
     "weight": 68.9, "trend": -0.3, "gear": "Dom + spacery",
     "days": "pon, śr", "diet": "Karmi piersią — bez restrykcji", "injury": "Rozstęp mięśnia prostego",
     "kcal": 2200, "adherence": 0.62, "payment": "OVERDUE"},
    {"email": "marcin.zubr@example.com", "name": "Marcin Żubr",
     "goal": "Sylwetka na wesele", "level": "1 rok", "sex": "M",
     "weight": 102.4, "trend": -0.6, "gear": "Siłownia osiedlowa",
     "days": "pon, śr, pt, nd", "diet": "Nie je ryb", "injury": "Nadciśnienie — kontrola",
     "kcal": 2500, "adherence": 0.88, "payment": "PAID"},
    {"email": "ewa.lisowska@example.com", "name": "Ewa Lisowska",
     "goal": "Maraton w maju", "level": "Biegaczka 3 lata", "sex": "K",
     "weight": 56.8, "trend": -0.05, "gear": "Bieżnia + park",
     "days": "wt, czw, sob, nd", "diet": "Bez glutenu", "injury": "Ścięgno Achillesa",
     "kcal": 2400, "adherence": 0.94, "payment": "PAID"},
    {"email": "pawel.dzik@example.com", "name": "Paweł Dzik",
     "goal": "Siła: przysiad 150 kg", "level": "Zaawansowany", "sex": "M",
     "weight": 88.6, "trend": 0.1, "gear": "Klub siłowy",
     "days": "pon, śr, pt", "diet": "Bez ograniczeń", "injury": "Odcinek lędźwiowy",
     "kcal": 3300, "adherence": 0.99, "payment": "PAID"},
    {"email": "iwona.gadek@example.com", "name": "Iwona Gądek",
     "goal": "Zdrowy kręgosłup", "level": "Praca siedząca", "sex": "K",
     "weight": 73.1, "trend": -0.2, "gear": "Mata w domu",
     "days": "wt, czw", "diet": "Bez cukru", "injury": "Dyskopatia L4-L5",
     "kcal": 1800, "adherence": 0.55, "payment": "PENDING"},
    {"email": "robert.wilk@example.com", "name": "Robert Wilk",
     "goal": "Redukcja + cholesterol", "level": "Po przerwie 5 lat", "sex": "M",
     "weight": 110.7, "trend": -0.7, "gear": "Siłownia + basen",
     "days": "pon, śr, pt", "diet": "Dieta śródziemnomorska", "injury": "Podwyższony cholesterol",
     "kcal": 2600, "adherence": 0.81, "payment": "OVERDUE"},
    {"email": "zofia.bak@example.com", "name": "Zofia Bąk",
     "goal": "Powrót do formy 60+", "level": "Seniorka aktywna", "sex": "K",
     "weight": 64.3, "trend": -0.15, "gear": "Dom: hantle 2 kg",
     "days": "pon, śr, pt", "diet": "Niska podaż białka — do poprawy", "injury": "Osteopenia",
     "kcal": 1750, "adherence": 0.9, "payment": "PAID"},
]

EXERCISES_BY_GOAL = {
    "default": [
        ("Przysiad ze sztangą", "nogi", 4, 8, 80.0, 2.5),
        ("Wyciskanie leżąc", "klatka", 4, 8, 60.0, 2.0),
        ("Wiosłowanie sztangą", "plecy", 4, 10, 55.0, 2.0),
        ("Wyciskanie żołnierskie", "barki", 3, 10, 35.0, 1.0),
        ("Plank", "brzuch", 3, 60, 0.0, 0.0),
    ],
    "dom": [
        ("Przysiad z gumą", "nogi", 4, 15, 0.0, 0.0),
        ("Pompki na kolanach", "klatka", 4, 10, 0.0, 0.0),
        ("Wiosłowanie gumą", "plecy", 4, 12, 0.0, 0.0),
        ("Martwy ciąg hantlami", "nogi", 3, 12, 16.0, 1.0),
        ("Mostek biodrowy", "posladki", 3, 15, 0.0, 0.0),
    ],
}


def _sets_json(rng, sets, reps, weight, done_ratio):
    """Serie w formacie dziennika (migracja nr 7): lista {reps, weight, rpe}."""
    out = []
    for i in range(sets):
        actual = max(1, int(reps * rng.uniform(done_ratio, 1.0)))
        out.append({
            "reps": actual,
            "weight": round(weight, 1) if weight else None,
            "rpe": round(rng.uniform(6.5, 9.5), 1),
            "set_no": i + 1,
        })
    return json.dumps(out, ensure_ascii=False)


def simulate(n_clients: int = 10, weeks: int = 12, reset: bool = False) -> dict:
    """Generuje pełną, deterministyczną symulację. Zwraca statystyki."""
    settings.ensure_dirs()
    run_migrations()
    rng = random.Random(20260818)
    stats: dict[str, int] = {}

    def bump(key: str, n: int = 1) -> None:
        stats[key] = stats.get(key, 0) + n

    with db_session() as db:
        if reset:
            from .db import Base, engine
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            db.expire_all()

        coach = db.query(User).filter(User.email == COACH_EMAIL).one_or_none()
        if coach is None:
            coach = User(id=new_id("USR"), email=COACH_EMAIL,
                         password_hash=hash_password("DzikTrener#2026"),
                         display_name="Lubelski Dzik", identity_id=new_id("ID"))
            db.add(coach)
            db.add(RoleGrant(id=new_id("ROL"), user_id=coach.id, role="COACH",
                             scope="*", issued_by="simulate"))
            bump("uzytkownicy")

        today = local_today()
        monday = today - timedelta(days=today.isoweekday() - 1)
        start = monday - timedelta(weeks=weeks - 1)

        # --- Zasoby trenera (baza wiedzy, ćwiczenia, produkty) ---
        for i, (title, cat) in enumerate([
            ("Jak liczyć makroskładniki bez wagi", "Żywienie"),
            ("Technika przysiadu — 5 najczęstszych błędów", "Technika"),
            ("Sen a regeneracja: co realnie działa", "Regeneracja"),
            ("Rozgrzewka 8 minut przed treningiem siłowym", "Technika"),
            ("Co robić, gdy tydzień wypadnie z planu", "Motywacja"),
        ]):
            db.add(KnowledgeItem(
                id=new_id("KNW"), coach_id=coach.id, title=title, category=cat,
                body=f"Materiał trenera: {title}. Treść przygotowana przez trenera, "
                     "bez automatycznych rekomendacji systemu.",
                pinned=(i == 0), created_by=coach.id))
            bump("baza_wiedzy")

        for name, group, how, benefit in [
            ("Przysiad ze sztangą", "nogi", "Stopy na szerokość barków, kolana za palcami.",
             "Siła nóg i tułowia"),
            ("Wyciskanie leżąc", "klatka", "Łopatki ściągnięte, sztanga do mostka.",
             "Siła klatki i tricepsa"),
            ("Martwy ciąg", "plecy", "Plecy proste, sztanga blisko goleni.",
             "Siła całego łańcucha tylnego"),
            ("Podciąganie", "plecy", "Pełen zwis, broda nad drążkiem.", "Siła pleców"),
            ("Wyciskanie żołnierskie", "barki", "Napięty brzuch, sztanga nad głowę.",
             "Stabilność barków"),
            ("Plank", "brzuch", "Ciało w linii, biodra nie opadają.", "Stabilizacja"),
        ]:
            db.add(Exercise(id=new_id("EXE"), coach_id=coach.id, name=name,
                            muscle_group=group, how_to=how, benefit=benefit,
                            created_by=coach.id))
            bump("cwiczenia")

        for name, cat, kcal, p, f, c in [
            ("Pierś z kurczaka", "Mięso", 165, 31.0, 3.6, 0.0),
            ("Ryż biały", "Zboża", 130, 2.7, 0.3, 28.0),
            ("Jajko", "Nabiał", 155, 13.0, 11.0, 1.1),
            ("Twaróg półtłusty", "Nabiał", 133, 18.0, 5.0, 3.5),
            ("Banan", "Owoce", 89, 1.1, 0.3, 23.0),
            ("Owsianka", "Zboża", 372, 13.0, 7.0, 62.0),
            ("Łosoś", "Ryby", 208, 20.0, 13.0, 0.0),
            ("Brokuł", "Warzywa", 34, 2.8, 0.4, 7.0),
        ]:
            db.add(FoodProduct(id=new_id("FDP"), coach_id=coach.id, name=name,
                               category=cat, kcal_100g=kcal, protein_100g=p,
                               fat_100g=f, carbs_100g=c, default_portion_g=100,
                               created_by=coach.id))
            bump("produkty")

        clients = []
        existing_emails = {row[0] for row in db.query(User.email).all()}
        for persona in PERSONAS[:n_clients]:
            # Idempotencja: powtórny przebieg na tej samej bazie pomija konta,
            # które już istnieją, zamiast wywracać się na unikalności e-maila
            # (narzędzie diagnostyczne bywa uruchamiane wielokrotnie).
            if persona["email"] in existing_emails:
                bump("pominieto_istniejacych")
                continue
            client = User(id=new_id("USR"), email=persona["email"],
                          password_hash=hash_password(SIM_PASSWORD),
                          display_name=persona["name"], identity_id=new_id("ID"))
            db.add(client)
            db.add(RoleGrant(id=new_id("ROL"), user_id=client.id, role="CLIENT",
                             scope="self", issued_by="simulate"))
            db.add(CoachClientRelationship(id=new_id("REL"), coach_id=coach.id,
                                           client_id=client.id, created_by=coach.id))
            thread = MessageThread(id=new_id("THR"), coach_id=coach.id,
                                   client_id=client.id)
            db.add(thread)
            record_event(db, action="IDENTITY_REGISTERED", actor_id="simulate",
                         subject_ids=[client.id],
                         payload={"identity_id": client.identity_id,
                                  "identity_type": "HUMAN", "simulation": True},
                         summary=f"Symulacja: rejestracja {client.display_name}")
            for category_key in ONBOARDING_CATEGORIES:
                ConsentService.grant_category(
                    db, subject_id=client.id, category_key=category_key,
                    grantee_id=coach.id, actions="read,write",
                    source="SIMULATION", confirmed=True)
                bump("zgody")
            clients.append((client, persona, thread))
            bump("uzytkownicy")
        db.flush()

        for client, p, thread in clients:
            home = "Dom" in p["gear"] or "Mata" in p["gear"]
            plan_exercises = EXERCISES_BY_GOAL["dom" if home else "default"]

            # --- Profil z proweniencją (część pól w dwóch wersjach) ---
            fields = {
                "cel_glowny": (p["goal"], False),
                "doswiadczenie": (p["level"], False),
                "sprzet": (p["gear"], False),
                "dni_treningowe": (p["days"], False),
                "preferencje_zywieniowe": (p["diet"], True),
                "urazy": (p["injury"], True),
                "tryb_pracy": ("Praca biurowa, 8h siedząco", False),
                "sen_srednio": ("6,5 h", True),
                "poziom_stresu": ("Umiarkowany", True),
                "motywacja": ("Chcę wrócić do formy sprzed lat", False),
            }
            for key, (value, sens) in fields.items():
                db.add(ProfileField(id=new_id("PRF"), client_id=client.id,
                                    field_key=key, value=value,
                                    source="CLIENT_DECLARED", author_id=client.id,
                                    sensitive=sens))
                bump("pola_profilu")
            # Druga wersja jednego pola — historia nie jest nadpisywana.
            db.add(ProfileField(id=new_id("PRF"), client_id=client.id,
                                field_key="sen_srednio", value="7,5 h",
                                source="CLIENT_DECLARED", author_id=client.id,
                                sensitive=True, version=2))
            bump("pola_profilu")

            for kind, title in [("MAIN", p["goal"]),
                                ("SECONDARY", "Regularność: 3 treningi w tygodniu"),
                                ("SECONDARY", "8000 kroków dziennie")]:
                db.add(Goal(id=new_id("GOL"), client_id=client.id, title=title,
                            kind=kind, created_by=coach.id,
                            target_date=(today + timedelta(days=90)).isoformat()))
                bump("cele")

            # --- Plan treningowy: trzy wersje (progresja) ---
            plan = TrainingPlan(id=new_id("PLN"), client_id=client.id,
                                coach_id=coach.id,
                                title=f"Plan: {p['goal']}", current_version_no=3)
            db.add(plan)
            db.flush()
            versions = []
            for v in (1, 2, 3):
                days = []
                for d_i, day in enumerate(["Dzień A", "Dzień B", "Dzień C"]):
                    ex = []
                    for name, _grp, sets, reps, weight, step in plan_exercises:
                        ex.append({"name": name, "sets": str(sets), "reps": str(reps),
                                   "weight": f"{weight + step * (v - 1):.1f} kg" if weight else "—"})
                    days.append({"name": day, "weekday": 1 + d_i * 2, "exercises": ex})
                pv = TrainingPlanVersion(
                    id=new_id("PLV"), plan_id=plan.id, version_no=v,
                    reason=("Plan startowy po wywiadzie" if v == 1 else
                            f"Progresja obciążeń po raporcie z tygodnia {v * 3}"),
                    created_by=coach.id,
                    content_json=json.dumps({"days": days}, ensure_ascii=False))
                db.add(pv)
                versions.append(pv)
                record_event(db, action="PLAN_VERSION_CREATED", actor_id=coach.id,
                             subject_ids=[client.id],
                             payload={"plan_id": plan.id, "version_no": v},
                             summary=f"Plan {plan.title}: wersja v{v}")
                bump("wersje_planu")
            db.flush()

            # --- Sesje treningowe z seriami (3/tydzień) ---
            for w in range(weeks):
                pv = versions[min(2, w // max(1, weeks // 3))]
                for d_i in range(3):
                    if rng.random() > p["adherence"]:
                        continue
                    day = start + timedelta(weeks=w, days=d_i * 2)
                    if day > today:
                        continue
                    pain = rng.random() < 0.08
                    session = WorkoutSession(
                        id=new_id("WSE"), client_id=client.id, plan_version_id=pv.id,
                        day_index=d_i, performed_on=day.isoformat(), status="DONE",
                        pain_flag=pain,
                        pain_note="Ciągnięcie w kolanie przy 3. serii" if pain else None,
                        comment=rng.choice([None, "Dobra energia", "Ciężko szło",
                                            "Ostatnia seria na maksa"]))
                    db.add(session)
                    db.flush()
                    for e_i, (name, _grp, sets, reps, weight, step) in enumerate(plan_exercises):
                        w_now = (weight + step * (w / max(1, weeks)) * 3) if weight else 0
                        db.add(WorkoutEntry(
                            id=new_id("WEN"), session_id=session.id, exercise_index=e_i,
                            exercise_name=name,
                            result=f"{sets}x{reps}",
                            sets_json=_sets_json(rng, sets, reps, w_now, 0.85),
                            comment="Technika OK" if e_i == 0 else None))
                        bump("wpisy_treningowe")
                    bump("sesje_treningowe")

            # --- Dieta: dwie wersje ---
            nplan = NutritionPlan(id=new_id("NPL"), client_id=client.id,
                                  coach_id=coach.id, title=f"Dieta {p['kcal']} kcal",
                                  current_version_no=2)
            db.add(nplan)
            db.flush()
            for v, kcal in ((1, p["kcal"]), (2, p["kcal"] - 100)):
                db.add(NutritionPlanVersion(
                    id=new_id("NPV"), plan_id=nplan.id, version_no=v,
                    reason="Plan startowy" if v == 1 else "Korekta po 6 tygodniach",
                    created_by=coach.id,
                    content_json=json.dumps({
                        "kcal": kcal,
                        "macros": {"protein_g": int(p["weight"] * 1.8),
                                   "fat_g": int(p["weight"] * 0.8),
                                   "carbs_g": int(kcal / 8)},
                        "meals": [
                            {"name": "Śniadanie", "items": ["Owsianka 80 g", "Jajka 2 szt."]},
                            {"name": "Obiad", "items": ["Kurczak 180 g", "Ryż 80 g", "Brokuł"]},
                            {"name": "Kolacja", "items": ["Twaróg 200 g", "Pieczywo żytnie"]},
                        ],
                        "notes": p["diet"],
                    }, ensure_ascii=False)))
                bump("wersje_diety")

            # --- Dziennik kaloryczny (6 dni w tygodniu) ---
            for w in range(weeks):
                for d in range(6):
                    day = start + timedelta(weeks=w, days=d)
                    if day > today:
                        continue
                    db.add(DailyNutritionLog(
                        id=new_id("DNL"), client_id=client.id,
                        logged_on=day.isoformat(),
                        kcal=int(p["kcal"] * rng.uniform(0.85, 1.12)),
                        protein_g=int(p["weight"] * rng.uniform(1.4, 2.0)),
                        fat_g=int(p["weight"] * rng.uniform(0.6, 1.0)),
                        carbs_g=int(p["kcal"] / 8 * rng.uniform(0.8, 1.2)),
                        water_l=round(rng.uniform(1.5, 3.5), 1),
                        note=rng.choice([None, None, "Wyjście na mieście"]),
                        created_by=client.id))
                    bump("dziennik_kaloryczny")

            # --- Harmonogram + adherencja ---
            items = []
            for name, cat, tod, dows, note in [
                ("Trening siłowy", "TRENING", "18:00", "1,3,5", None),
                ("Witamina D 2000 IU", "SUPLEMENT", "08:00", "1,2,3,4,5,6,7",
                 "Dawkę ustalił trener na podstawie deklaracji klienta"),
                ("Magnez", "SUPLEMENT", "21:00", "1,2,3,4,5,6,7",
                 "Wpis wprowadzony ręcznie przez trenera"),
                ("Spacer 30 min", "AKTYWNOSC", "12:00", "2,4,6", None),
                ("Nawodnienie 2,5 l", "NAWYK", None, "1,2,3,4,5,6,7", None),
            ]:
                item = ScheduleItem(
                    id=new_id("SCH"), client_id=client.id, name=name, category=cat,
                    time_of_day=tod, days_of_week=dows, author_id=coach.id,
                    author_note=note, start_date=start.isoformat())
                db.add(item)
                items.append(item)
                bump("harmonogram")
            db.flush()
            for item in items:
                for w in range(weeks):
                    for d in range(7):
                        day = start + timedelta(weeks=w, days=d)
                        if day > today or str(d + 1) not in item.days_of_week.split(","):
                            continue
                        if rng.random() > p["adherence"]:
                            continue
                        db.add(ScheduleCompletion(
                            id=new_id("SCC"), schedule_item_id=item.id,
                            client_id=client.id, completed_on=day.isoformat(),
                            status="DONE", created_by=client.id))
                        bump("adherencja")

            # --- Pomiary ---
            for w in range(weeks):
                day = start + timedelta(weeks=w)
                if day > today:
                    continue
                db.add(Measurement(id=new_id("MSR"), client_id=client.id, kind="weight",
                                   value=round(p["weight"] + p["trend"] * w
                                               + rng.uniform(-0.4, 0.4), 1),
                                   unit="kg", measured_at=day.isoformat(),
                                   created_by=client.id))
                bump("pomiary")
                if w % 2 == 0:
                    for kind, base in (("waist", 88.0), ("chest", 102.0), ("arm", 36.0)):
                        db.add(Measurement(
                            id=new_id("MSR"), client_id=client.id, kind=kind,
                            value=round(base + p["trend"] * w * 0.6 + rng.uniform(-0.5, 0.5), 1),
                            unit="cm", measured_at=day.isoformat(), created_by=client.id))
                        bump("pomiary")

            # --- Raporty tygodniowe (część z rewizją i oceną) ---
            for w in range(weeks):
                week_start = start + timedelta(weeks=w)
                if week_start > monday:
                    continue
                reviewed = week_start < monday - timedelta(days=7)
                payload = {
                    "weight_kg": round(p["weight"] + p["trend"] * w, 1),
                    "measurements": {"waist": round(88 + p["trend"] * w * 0.6, 1)},
                    "trainings_done": rng.randint(1, 4),
                    "diet_adherence": rng.randint(2, 5), "energy": rng.randint(2, 5),
                    "sleep": rng.randint(2, 5), "hunger": rng.randint(1, 5),
                    "stress": rng.randint(1, 5), "recovery": rng.randint(2, 5),
                    "pain_note": "Bark pobolewa po wyciskaniu" if rng.random() < 0.15 else None,
                    "comment": rng.choice([
                        "Tydzień zgodnie z planem.",
                        "Ciężki tydzień w pracy, dwa treningi.",
                        "Waga stoi, ale ubrania luźniejsze.",
                        "Czuję progres w przysiadzie."]),
                    "questions": rng.choice([None, "Czy mogę zamienić ryż na kaszę?",
                                             "Kiedy zwiększamy ciężar?"]),
                }
                checkin = WeeklyCheckin(
                    id=new_id("CKN"), client_id=client.id,
                    week_start=week_start.isoformat(),
                    payload_json=json.dumps(payload, ensure_ascii=False),
                    status="REVIEWED" if reviewed else "SUBMITTED",
                    revision=1,
                    coach_response=("Dobra robota. Trzymamy kurs, w przyszłym tygodniu "
                                    "dokładamy serię." if reviewed else None),
                    reviewed_by=coach.id if reviewed else None,
                    rating=rng.randint(3, 5) if reviewed else None)
                db.add(checkin)
                record_event(db, action="CHECKIN_SUBMITTED", actor_id=client.id,
                             subject_ids=[client.id],
                             payload={"checkin_id": checkin.id,
                                      "week_start": checkin.week_start, "revision": 1},
                             summary=f"Raport tygodniowy {checkin.week_start}")
                bump("raporty")

            # --- Obserwacje (w tym niepokojące) ---
            for i in range(3):
                sev = "NIEPOKOJACE" if i == 0 and rng.random() < 0.4 else "INFO"
                db.add(Observation(
                    id=new_id("OBS"), client_id=client.id,
                    occurred_on=(today - timedelta(days=7 * i + 2)).isoformat(),
                    category=rng.choice(["SAMOPOCZUCIE", "REAKCJA", "SEN"]),
                    severity=sev,
                    text=("Zawroty głowy po porannym treningu na czczo"
                          if sev == "NIEPOKOJACE" else
                          "Lepszy sen po przesunięciu treningu na wcześniej"),
                    created_by=client.id))
                bump("obserwacje")

            # --- Wiadomości (wątek dwustronny) ---
            for i in range(16):
                author = client.id if i % 2 == 0 else coach.id
                db.add(Message(
                    id=new_id("MSG"), thread_id=thread.id, author_id=author,
                    body=rng.choice([
                        "Cześć, mam pytanie o technikę martwego ciągu.",
                        "Wrzuciłem film z ostatniej serii — zerkniesz?",
                        "Pamiętaj o rozgrzewce barków przed wyciskaniem.",
                        "Dzięki! W tym tygodniu było łatwiej.",
                        "Zmieniam Ci plan od poniedziałku — zobacz nową wersję.",
                        "Czy mogę przełożyć trening na sobotę?"]),
                    created_at=(today - timedelta(days=16 - i)).isoformat() + "T10:00:00Z",
                    read_at=(today - timedelta(days=15 - i)).isoformat() + "T11:00:00Z"
                    if i < 14 else None))
                bump("wiadomosci")

            # --- Dokumenty i zdjęcia progresu ---
            for title, cat in [("Plan treningowy PDF", "PLAN"),
                               ("Wyniki badań krwi", "BADANIA")]:
                sf = StoredFile(id=new_id("FIL"), owner_user_id=client.id,
                                filename=f"{title.lower().replace(' ', '_')}.pdf",
                                content_type="application/pdf", size_bytes=12345,
                                sha256="0" * 64, storage_path=f"{new_id('P')}.pdf",
                                uploaded_by=coach.id)
                db.add(sf)
                db.flush()
                db.add(Document(id=new_id("DOC"), client_id=client.id, file_id=sf.id,
                                title=title, category=cat, uploaded_by=coach.id))
                bump("dokumenty")
            for i in range(4):
                sf = StoredFile(id=new_id("FIL"), owner_user_id=client.id,
                                filename=f"progres_{i}.png", content_type="image/png",
                                size_bytes=4096, sha256="1" * 64,
                                storage_path=f"{new_id('P')}.png", uploaded_by=client.id)
                db.add(sf)
                db.flush()
                db.add(ProgressPhoto(
                    id=new_id("PHO"), client_id=client.id, file_id=sf.id,
                    taken_at=(today - timedelta(days=30 * (3 - i))).isoformat(),
                    pose=rng.choice(["FRONT", "SIDE", "BACK"]),
                    note="Zdjęcie kontrolne"))
                bump("zdjecia_progresu")

            # --- Płatności ---
            sched = PaymentSchedule(
                id=new_id("PSC"), client_id=client.id, coach_id=coach.id,
                package_name="Współpraca miesięczna", amount_cents=30000,
                currency="PLN", period="MONTHLY", created_by=coach.id)
            db.add(sched)
            db.flush()
            for m in range(3):
                due = today - timedelta(days=30 * (2 - m))
                status = "PAID" if m < 2 else p["payment"]
                db.add(PaymentRecord(
                    id=new_id("PRC"), schedule_id=sched.id, due_date=due.isoformat(),
                    amount_cents=30000, currency="PLN", status=status,
                    paid_at=due.isoformat() if status == "PAID" else None,
                    marked_by=coach.id if status == "PAID" else None))
                bump("platnosci")

            # --- Konsultacje i push ---
            for i in range(2):
                slot_day = today + timedelta(days=3 + i * 7)
                db.add(ConsultSlot(
                    id=new_id("CSL"), coach_id=coach.id,
                    starts_at=f"{slot_day.isoformat()}T17:{'00' if i == 0 else '30'}:00",
                    duration_min=30, status="BOOKED" if i == 0 else "OPEN",
                    client_id=client.id if i == 0 else None))
                bump("konsultacje")
            db.add(PushSubscription(
                id=new_id("PSH"), user_id=client.id,
                endpoint=f"https://push.example.com/{client.id}",
                p256dh="sym-p256dh-" + client.id[-8:], auth="sym-auth-" + client.id[-6:]))
            bump("push")

        # --- Wspólne wyzwanie (prywatne, opt-in) ---
        ch_start = monday - timedelta(weeks=2)
        challenge = Challenge(
            id=new_id("CHL"), kind="GROUP", organizer_id=coach.id,
            title="Wyzwanie: 8000 kroków dziennie", unit="STEPS", goal_value=8000,
            starts_on=ch_start.isoformat(),
            ends_on=(ch_start + timedelta(days=27)).isoformat(),
            timezone=settings.timezone, visibility="INVITE_ONLY", status="ACTIVE",
            description="Wspólne wyzwanie bez rankingu wartości osób — liczy się udział.")
        db.add(challenge)
        db.flush()
        bump("wyzwania")
        for client, p, _thread in clients[:6]:
            part = ChallengeParticipant(
                id=new_id("CHP"), challenge_id=challenge.id, user_id=client.id,
                status="ACTIVE", alias=p["name"].split()[0], share_result=True,
                ranking_opt_in=False, invited_by=coach.id)
            db.add(part)
            db.flush()
            bump("uczestnicy_wyzwania")
            for d in range(14):
                day = ch_start + timedelta(days=d)
                if day > today or rng.random() > p["adherence"]:
                    continue
                db.add(ChallengeEntry(
                    id=new_id("CHE"), challenge_id=challenge.id, participant_id=part.id,
                    entry_date=day.isoformat(),
                    value=float(rng.randint(4000, 14000)), source="MANUAL",
                    status="ACTIVE"))
                bump("wpisy_wyzwania")

        db.flush()
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description="Głęboka symulacja danych Dzik OS")
    ap.add_argument("--clients", type=int, default=10, help="liczba podopiecznych (max 10)")
    ap.add_argument("--weeks", type=int, default=12, help="tygodni historii")
    ap.add_argument("--reset", action="store_true", help="wyczyść bazę przed symulacją")
    args = ap.parse_args()
    stats = simulate(n_clients=args.clients, weeks=args.weeks, reset=args.reset)
    total = sum(stats.values())
    print(f"[symulacja] {args.clients} podopiecznych, {args.weeks} tygodni historii")
    for key in sorted(stats):
        print(f"  {key:24} {stats[key]:>6}")
    print(f"  {'RAZEM rekordów':24} {total:>6}")
    print(f"\nHasło wszystkich kont symulacji: {SIM_PASSWORD}")


if __name__ == "__main__":
    main()
