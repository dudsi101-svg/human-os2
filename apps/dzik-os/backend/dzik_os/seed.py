"""Syntetyczne dane demonstracyjne Dzik OS.

Uruchomienie: python -m dzik_os.seed
Konta (WYŁĄCZNIE środowisko lokalne/staging — nigdy produkcja z prawdziwymi
danymi):

  trener:  dzik@example.com      / DzikTrener#2026
  klient A: klient.a@example.com / KlientA#2026!x
  klient B: klient.b@example.com / KlientB#2026!x
  klient C: marek.dziczek@example.com / KlientC#2026!x  (raport do oceny)
  klient D: anna.wilk@example.com     / KlientD#2026!x  (praca trenera wykonana)
  klient E: piotr.zajac@example.com   / KlientE#2026!x  (zaległości + obserwacja)
  admin:   admin@example.com     / DzikAdmin#2026

Żadna z osób nie jest prawdziwa; wszystkie wartości są zmyślone.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from .config import settings
from .consent_catalog import ONBOARDING_CATEGORIES
from .dates import local_today
from .db import db_session, run_migrations
from .exercise_catalog import CATALOG as EXERCISE_CATALOG
from .food_catalog_data import FOOD_ROWS, FOOD_SOURCE
from .hos_bridge import ConsentService, record_event
from .models import (
    CoachClientRelationship,
    Document,
    Exercise,
    FoodProduct,
    Goal,
    Measurement,
    Message,
    MessageThread,
    NutritionPlan,
    NutritionPlanVersion,
    PaymentRecord,
    PaymentSchedule,
    ProfileField,
    RoleGrant,
    ScheduleItem,
    StoredFile,
    TrainingPlan,
    TrainingPlanVersion,
    User,
    WeeklyCheckin,
    new_id,
)
from .muscles import join_muscles
from .security import hash_password

DEMO_ACCOUNTS = {
    "coach": ("dzik@example.com", "DzikTrener#2026", "Lubelski Dzik"),
    "client_a": ("klient.a@example.com", "KlientA#2026!x", "Klient Testowy A"),
    "client_b": ("klient.b@example.com", "KlientB#2026!x", "Klient Testowy B"),
    # Symulowani podopieczni o zróżnicowanych stanach — panel trenera od
    # razu pokazuje realną pracę (raport do oceny, oceniony raport,
    # zaległości, niepokojąca obserwacja).
    "client_c": ("marek.dziczek@example.com", "KlientC#2026!x", "Marek Dziczek"),
    "client_d": ("anna.wilk@example.com", "KlientD#2026!x", "Anna Wilk"),
    "client_e": ("piotr.zajac@example.com", "KlientE#2026!x", "Piotr Zając"),
    "admin": ("admin@example.com", "DzikAdmin#2026", "Administrator Techniczny"),
}

# Dwa syntetyczne zdjęcia progresu (male PNG, sylwetka "przed/po") --
# wylacznie do demo porownywarki; zadnych prawdziwych osob.
DEMO_PHOTO_BEFORE_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAPAAAAFACAIAAAANimYEAAADUklEQVR42u3dQYqrQBiF0Rhc"
    "heBAQdz/ckIga8kwEwM/iSbl5Zxpw6MpP27b1CPdDeN0gRRXR4CgQdAgaBA0ggZBg6BB0CBo"
    "BA2CBkGDoEHQCBoEDYIGQYOgETQIGgQNggZBI2gQNAgaBA0vvSM4zrys7770uN+czxE6H6f7"
    "y46VLejMjpXtHTq55l3+BSx0EymbagsdW7OpFnRUzZoWdFrNmhZ0Ws2aFnRazZoWNAi6+ck0"
    "0oJOa0vTgkbQIGjvG946BA2CBkEn/cT31iFoBA2CBkGDoEHQCBoEDYI+hRY+WsDHGwgaQYOg"
    "vXV43xA0CBoEffaf+943BJ3TlpoFjaBpcjLNs6BzOlOzoHOaVrOgc5pWs6BzmlbzN/zRoH3s"
    "8hkDUrbQOVOtZgudsNY6FnRC2ToWNHiHRtAgaBA0CBoEjaBB0PBffcvfnL8q0qxmbzotNF45"
    "QNAgaAgK2v+x9FwsNBYaBA2CBkGDoBE0CBoEXeduxROx0FhoEDQIGgQNgkbQIGgQdJ27Fc/C"
    "QmOhQdAgaBA0CBpBg6BB0HXuVjwFC42FBkGDoEHQIGgEDYIGQde5W3H+FhoLDYIGQYOgQdAI"
    "GgQNgq5zt+LkLTQWGgQNggZBg6ARNAgaBF3nbsWZW2gsNAgaBA2CBkEjaBA0CLrO3YrTttBY"
    "aBA0CBoEDYJG0CBoEHSduxXnbKGx0CBoEDQIGgSNoEHQIOg6dytO2EJjoUHQIGgQNAgaQYOg"
    "QdB17lacrYXGQoOgQdAgaBA0ggZBg6Dr3K04VQuNhQZBg6BB0CBoBA2CBkHXuVtxnhYaCw2C"
    "BkGDoEHQCBoEDYKuc7fiJC00FhoEDYKGD/WO4Ly/Hs3L6klZaAQNggZBg6BB0AgaBA2CBkGD"
    "oBE0CBoEDYJG0CBoEDQIGgSNoEHQIGgQNAgaQYOgQdAgaBA0ggZBg6BB0CBoBA2CBkGDoEHQ"
    "CBoEDYIGQYOgETQIGgQNgkbQIGgQNAgaBI2gQdAgaBA0CBpBg6BB0CBoEDSCBkGDoEHQIGgE"
    "DYIGQYOgQdAIGgQNggZBg6ARNAgaBA2CBkEjaBA0CBoEjaAhRTeMk1PAQoOgQdAgaAQNggZB"
    "g6BB0AgaBA2CBkGDoBE0CBoEDYKGTU/cdKSOB1LNcgAAAABJRU5ErkJggg=="
)
DEMO_PHOTO_AFTER_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAPAAAAFACAIAAAANimYEAAADTklEQVR42u3dQYrqQBiFUSPZ"
    "QyBkmgyz/3U41M04dKIDMTGp+58zffBoio/b1V1gd8M0XiDF1REgaBA0CBoEjaBB0CBoEDQI"
    "GkGDoEHQIGgQNIIGQYOgQdAgaAQNggZBg6BB0AgaBA2CBkHDS+8I9jMv66d/etxvzmcPnY/T"
    "/WfHyhZ0ZsfKdodOrnmT/wELfYqUTbWFjq3ZVAs6qmZNCzqtZk0LOq1mTQs6rWZNCxoEffrJ"
    "NNKCTmtL04JG0CBo9w23DkGDoEHQSd/x3ToEjaBB0CBoEDQIGkGDoEHQTTjDRwv4eANBI2gQ"
    "tFuH+4agQdAg6Na/77tvCDqnLTULGkFzysk0z4LO6UzNgs5pWs2CzmlazYLOaVrNv/BHg7ax"
    "yWcMSNlC50y1mi10wlrrWNAJZetY0OAOjaBB0CBoEDQIGkGDoOFYfbtfur85sqtG3zItNK4c"
    "IGgQNAgaQfsxnIyztdBYaBA0CBoEjaBB0CBoEDSUCNpjoVO10FhoEDQIGgQNgkbQIGgQNAga"
    "2g/a67fztNBYaBA0CBoEDYJG0CBoEDQUDdpjoZO00FhoEDQIGgQNgkbQIGgQNAgaQbfP67cz"
    "tNBYaBA0CBoEjaAdAYIGQYOgoWjQHgudnoXGQoOgQdAgaAQNggZBg6BB0Ai6fV6/nZuFxkKD"
    "oEHQIGgEDYIGQYOgoWjQHguLn5iFxkKDoEHQIGgEDYIGQYOgQdAIOoLX78pnZaERNAgaBA2C"
    "RtAgaBA0CBpKB+2xsOwpWWgEDYIGQYOgETQIGgQNggZBI+ggXr9rno+FRtAgaBA0CBpBg6BB"
    "0CBoELTHwoonY6ERNAgaBA2CprDeEXzlkN8PzMvq5C00ggZBg6BB0CBoBA2CBkGDoEHQCBoE"
    "DYIGQYOgETQIGgQNggZBI2gQNAgaBA2CRtAgaBA0CBpBg6BB0CBoEDSCBkGDoEHQIGgEDYIG"
    "QYOgQdAIGgQNggZBg6ARNAgaBA2CBkEjaBA0CBoEDYJG0CBoEDQIGgSNoEHQIGgQNIIGQYOg"
    "QdAgaAQNggZBg6BB0AgaBA2CBkGDoBE0CBoEDYIGQZOuG6bRKWChQdAgaBA0ggZBg6BB0CBo"
    "BA2CBkGDoEHQCBoEDYIGQcNbT0O2mNs54tspAAAAAElFTkSuQmCC"
)


def seed() -> dict[str, str]:
    settings.ensure_dirs()
    run_migrations()
    with db_session() as db:
        if db.query(User).count() > 0:
            print("Baza nie jest pusta — pomijam seed.")
            return {}
        users: dict[str, User] = {}
        for key, (email, password, name) in DEMO_ACCOUNTS.items():
            user = User(
                id=new_id("USR"),
                email=email,
                password_hash=hash_password(password),
                display_name=name,
                identity_id=new_id("ID"),
            )
            db.add(user)
            users[key] = user
        coach, client_a, client_b, admin = (
            users["coach"], users["client_a"], users["client_b"], users["admin"],
        )
        client_c, client_d, client_e = (
            users["client_c"], users["client_d"], users["client_e"],
        )
        role_map = {
            coach.id: "COACH", client_a.id: "CLIENT",
            client_b.id: "CLIENT", client_c.id: "CLIENT",
            client_d.id: "CLIENT", client_e.id: "CLIENT",
            admin.id: "ADMIN",
        }
        for user_id, role in role_map.items():
            db.add(RoleGrant(id=new_id("ROL"), user_id=user_id, role=role,
                             scope="self" if role == "CLIENT" else "*",
                             issued_by="seed"))
        for user in users.values():
            record_event(
                db, action="IDENTITY_REGISTERED", actor_id="seed",
                subject_ids=[user.id],
                payload={"identity_id": user.identity_id, "identity_type": "HUMAN",
                         "display_name": user.display_name, "demo": True},
                summary=f"Seed: rejestracja tożsamości {user.display_name}",
            )

        # Daty kalendarzowe demo liczone w strefie lokalnej (DZIK_TZ),
        # żeby seed odpalony po północy czasu polskiego nie tworzył
        # danych "z wczoraj".
        today = local_today()
        monday = today - timedelta(days=today.isoweekday() - 1)

        for client in (client_a, client_b, client_c, client_d, client_e):
            rel = CoachClientRelationship(
                id=new_id("REL"), coach_id=coach.id, client_id=client.id,
                created_by=coach.id,
            )
            db.add(rel)
            db.add(MessageThread(id=new_id("THR"), coach_id=coach.id,
                                 client_id=client.id))
            # Konta demo: komplet zgód per kategoria, już potwierdzonych
            # (odrębne wiersze — RODO: jedna kategoria = jedna zgoda).
            for category_key in ONBOARDING_CATEGORIES:
                ConsentService.grant_category(
                    db, subject_id=client.id, category_key=category_key,
                    grantee_id=coach.id, actions="read,write",
                    source="SEED", confirmed=True,
                )
        # Klient A ma też opcjonalną zgodę na funkcje AI (demo ścieżki
        # podsumowań raportu w panelu trenera).
        ConsentService.grant_category(
            db, subject_id=client_a.id, category_key="funkcje_ai",
            source="SEED", confirmed=True,
        )

        # --- Profil i cele klienta A ---
        profile_a = {
            "cel_glowny": ("Redukcja 8 kg do wakacji", False),
            "doswiadczenie": ("2 lata treningu siłowego", False),
            "sprzet": ("Siłownia komercyjna, pełne wyposażenie", False),
            "dni_treningowe": ("pon, śr, pt", False),
            "preferencje_zywieniowe": ("Bez ryb; dużo kurczaka i ryżu", True),
            "alergie": ("Orzechy laskowe", True),
            "urazy": ("Przebyty uraz barku (2024) — unikać wyciskania za głowę", True),
        }
        for key, (value, sensitive) in profile_a.items():
            db.add(ProfileField(
                id=new_id("PRF"), client_id=client_a.id, field_key=key, value=value,
                source="CLIENT_DECLARED", author_id=client_a.id, sensitive=sensitive,
            ))
        db.add(Goal(id=new_id("GOL"), client_id=client_a.id,
                    title="Redukcja masy ciała do 82 kg", kind="MAIN",
                    target_date=(today + timedelta(days=90)).isoformat(),
                    created_by=coach.id))
        db.add(Goal(id=new_id("GOL"), client_id=client_a.id,
                    title="Przysiad 120 kg x 5", kind="SECONDARY",
                    created_by=coach.id))
        db.add(Goal(id=new_id("GOL"), client_id=client_b.id,
                    title="Budowa masy mięśniowej (+4 kg)", kind="MAIN",
                    created_by=coach.id))

        # --- Baza ćwiczeń trenera (know-how: technika, błędy, warianty) ---
        # Seedowana PRZED planami, bo pozycje planów odwołują się do niej
        # przez `exercise_id` (demo pokazuje przepływ „plan układany z bazy”).
        exercise_ids: dict[str, str] = {}
        for row in EXERCISE_CATALOG:
            item = Exercise(
                id=new_id("EXC"), coach_id=coach.id, name=row["name"],
                muscle_group=row["group"], how_to=row["how_to"],
                benefit=row["benefit"], equipment=row["equipment"],
                muscles_primary=join_muscles(row["primary"]),
                muscles_secondary=join_muscles(row["secondary"]),
                level=row["level"], pattern=row["pattern"],
                steps_json=json.dumps(row["steps"], ensure_ascii=False),
                mistakes_json=json.dumps(row["mistakes"], ensure_ascii=False),
                cues_json=json.dumps(row["cues"], ensure_ascii=False),
                safety=row["safety"], easier=row["easier"], harder=row["harder"],
                tempo_hint=row["tempo"], breathing=row["breathing"],
                created_by=coach.id,
            )
            db.add(item)
            exercise_ids[row["name"]] = item.id

        def ex_ref(name: str, **fields: object) -> dict:
            """Pozycja planu podpięta do bazy ćwiczeń (miękkie odniesienie:
            nazwa zostaje w planie nawet po archiwizacji ćwiczenia)."""
            return {"name": name, "exercise_id": exercise_ids[name], **fields}

        # --- Plan treningowy klienta A: v1 i v2 (historia wersji) ---
        plan_a = TrainingPlan(id=new_id("PLN"), client_id=client_a.id,
                              coach_id=coach.id, title="Redukcja — siła 3x/tydz.",
                              current_version_no=2)
        db.add(plan_a)
        days_v1 = [
            {"name": "Trening A — góra", "weekday": 1, "exercises": [
                ex_ref("Wyciskanie sztangi leżąc", sets="4", reps="8",
                       weight="70 kg", tempo="2011", rest="120 s",
                       comment="Ostatnia seria do 1 w zapasie",
                       video_url="https://example.com/wyciskanie"),
                ex_ref("Wiosłowanie hantlem w podporze", sets="3", reps="10",
                       weight="30 kg", rest="90 s"),
            ]},
            {"name": "Trening B — dół", "weekday": 3, "exercises": [
                ex_ref("Przysiad ze sztangą", sets="4", reps="6",
                       weight="100 kg", rest="180 s"),
                ex_ref("Rumuński martwy ciąg", sets="3", reps="8",
                       weight="80 kg", rest="120 s"),
            ]},
            {"name": "Trening C — całe ciało", "weekday": 5, "exercises": [
                ex_ref("Martwy ciąg klasyczny", sets="3", reps="5",
                       weight="120 kg", rest="180 s"),
                ex_ref("Wyciskanie żołnierskie (OHP)", sets="3", reps="8",
                       weight="45 kg", rest="120 s"),
            ]},
        ]
        db.add(TrainingPlanVersion(
            id=new_id("PLV"), plan_id=plan_a.id, version_no=1,
            reason="Plan startowy współpracy", created_by=coach.id,
            content_json=json.dumps({"days": days_v1}, ensure_ascii=False),
        ))
        days_v2 = json.loads(json.dumps(days_v1))
        days_v2[1]["exercises"][0]["weight"] = "105 kg"
        days_v2[0]["exercises"][0]["comment"] = "Bark OK — pełny zakres"
        plan_a_v2 = TrainingPlanVersion(
            id=new_id("PLV"), plan_id=plan_a.id, version_no=2,
            reason="Progresja przysiadu po raporcie z tygodnia 2; bark bez bólu",
            created_by=coach.id,
            content_json=json.dumps({"days": days_v2}, ensure_ascii=False),
        )
        db.add(plan_a_v2)
        record_event(db, action="PLAN_VERSION_CREATED", actor_id=coach.id,
                     subject_ids=[client_a.id],
                     payload={"plan_id": plan_a.id, "version_no": 2,
                              "reason": "Progresja przysiadu po raporcie"},
                     summary="Plan 'Redukcja — siła 3x/tydz.': nowa wersja v2")

        plan_b = TrainingPlan(id=new_id("PLN"), client_id=client_b.id,
                              coach_id=coach.id, title="Masa — FBW 3x/tydz.",
                              current_version_no=1)
        db.add(plan_b)
        db.add(TrainingPlanVersion(
            id=new_id("PLV"), plan_id=plan_b.id, version_no=1,
            reason="Plan startowy", created_by=coach.id,
            content_json=json.dumps({"days": [
                {"name": "FBW 1", "weekday": 2, "exercises": [
                    ex_ref("Przysiad ze sztangą", sets="3", reps="8", weight="80 kg"),
                    ex_ref("Wyciskanie sztangi leżąc", sets="3", reps="8",
                           weight="60 kg"),
                ]},
                {"name": "FBW 2", "weekday": 4, "exercises": [
                    ex_ref("Martwy ciąg klasyczny", sets="3", reps="5",
                           weight="110 kg"),
                ]},
                {"name": "FBW 3", "weekday": 6, "exercises": [
                    ex_ref("Podciąganie na drążku nachwytem", sets="4", reps="max"),
                ]},
            ]}, ensure_ascii=False),
        ))

        # Szablon trenera.
        tpl = TrainingPlan(id=new_id("PLN"), client_id=None, coach_id=coach.id,
                           title="Szablon: Push/Pull/Legs", is_template=True,
                           current_version_no=1)
        db.add(tpl)
        db.add(TrainingPlanVersion(
            id=new_id("PLV"), plan_id=tpl.id, version_no=1,
            reason="Szablon bazowy", created_by=coach.id,
            content_json=json.dumps({"days": [
                {"name": "Push", "exercises": [
                    ex_ref("Wyciskanie sztangi leżąc", sets="4", reps="8"),
                    ex_ref("Wyciskanie hantli nad głowę siedząc", sets="3", reps="10"),
                ]},
                {"name": "Pull", "exercises": [
                    ex_ref("Wiosłowanie sztangą w opadzie", sets="4", reps="10"),
                    ex_ref("Ściąganie drążka wyciągu górnego", sets="3", reps="12"),
                ]},
                {"name": "Legs", "exercises": [
                    ex_ref("Przysiad ze sztangą", sets="4", reps="8"),
                    ex_ref("Rumuński martwy ciąg", sets="3", reps="10"),
                ]},
            ]}, ensure_ascii=False),
        ))

        # --- Dieta klienta A ---
        nplan = NutritionPlan(id=new_id("NUT"), client_id=client_a.id,
                              coach_id=coach.id, title="Redukcja 2300 kcal",
                              current_version_no=1)
        db.add(nplan)
        db.add(NutritionPlanVersion(
            id=new_id("NUV"), plan_id=nplan.id, version_no=1,
            reason="Start współpracy — deficyt ~500 kcal", created_by=coach.id,
            content_json=json.dumps({
                "kcal": 2300, "protein_g": 180, "fat_g": 70, "carbs_g": 240,
                "sections": [
                    {"title": "Zasady ogólne",
                     "body": "4 posiłki dziennie. Minimum 2,5 l wody. "
                             "Warzywa do każdego posiłku. Bez orzechów laskowych "
                             "(alergia)."},
                    {"title": "Nawodnienie i sól",
                     "body": "Przy treningach w upale dosalaj posiłki."},
                ],
                "meals": [
                    {"name": "Śniadanie", "description":
                        "Owsianka 80 g + odżywka 30 g + banan",
                     "swaps": "Zamiennik: omlet z 3 jaj + 2 kromki chleba"},
                    {"name": "Obiad", "description":
                        "Kurczak 200 g + ryż 100 g + brokuły",
                     "swaps": "Zamiennik: indyk + kasza jaglana"},
                    {"name": "Posiłek potreningowy", "description":
                        "Odżywka 30 g + ryż preparowany 50 g"},
                    {"name": "Kolacja", "description":
                        "Twaróg półtłusty 250 g + pomidor + pieczywo 2 kromki"},
                ],
                "supplements": [
                    {"name": "Witamina D3", "dose": "2000 IU", "form": "kapsułki",
                     "timing": "rano, do posiłku zawierającego tłuszcz",
                     "purpose": "Uzupełnienie niedoboru stwierdzonego w badaniach",
                     "source": "Zalecenie lekarza rodzinnego z 2026-07-12 "
                               "(wynik 25(OH)D poniżej normy)",
                     "duration": "do kontrolnych badań w listopadzie",
                     "notes": "Przy zmianie dawki najpierw kontakt z lekarzem.",
                     "specialist_consulted": True},
                    {"name": "Kreatyna monohydrat", "dose": "5 g",
                     "form": "proszek", "timing": "codziennie, pora dowolna",
                     "purpose": "Wsparcie treningu siłowego",
                     "source": "Zalecenie trenera — standardowa dawka podtrzymująca",
                     "duration": "stale w okresie siłowym",
                     "notes": "Pilnuj nawodnienia (min. 2,5 l wody dziennie).",
                     "specialist_consulted": False},
                ],
            }, ensure_ascii=False),
        ))

        # --- Harmonogram klienta A ---
        schedule_by_name: dict[str, ScheduleItem] = {}
        for name, category, tod, days, instruction, note in [
            ("Trening siłowy", "TRENING", "17:30", "1,3,5",
             "Wg aktualnego planu treningowego", None),
            ("Kreatyna 5 g", "SUPLEMENT", "08:00", "1,2,3,4,5,6,7",
             "5 g jabłczanu z wodą, po śniadaniu",
             "Dawka wpisana przez trenera na prośbę klienta; produkt OTC"),
            ("Witamina D3 2000 IU", "SUPLEMENT", "08:00", "1,2,3,4,5,6,7",
             "Z posiłkiem zawierającym tłuszcz",
             "Suplementacja zgłoszona przez klienta (zalecenie lekarza POZ)"),
            ("Pomiar masy ciała", "POMIAR", "07:00", "1,4",
             "Rano, na czczo, po toalecie", None),
            ("Raport tygodniowy", "RAPORT", "18:00", "7",
             "Wypełnij formularz raportu w aplikacji", None),
        ]:
            item = ScheduleItem(
                id=new_id("SCH"), client_id=client_a.id, name=name,
                category=category, time_of_day=tod, days_of_week=days,
                instruction=instruction, author_id=coach.id, author_note=note,
            )
            db.add(item)
            schedule_by_name[name] = item

        # --- Adherencja harmonogramu klienta A (ostatnie 2 tygodnie) ---
        db.flush()
        from .models import (
            DailyNutritionLog,
            Observation,
            ScheduleCompletion,
            WorkoutEntry,
            WorkoutSession,
        )

        # --- Wykonane treningi klienta A (progresja przysiadu → rekord;
        # serie strukturalnie: ciężar × powtórzenia → wykresy siły) ---
        for offset, squat_kg, bench_kg in [(16, 95, 65), (9, 100, 67.5), (2, 105, 70)]:
            session = WorkoutSession(
                id=new_id("WKS"), client_id=client_a.id,
                plan_version_id=plan_a_v2.id, day_index=1,
                performed_on=(today - timedelta(days=offset)).isoformat(),
                status="DONE", created_at=(today - timedelta(days=offset)).isoformat(),
            )
            db.add(session)
            db.add(WorkoutEntry(
                id=new_id("WKE"), session_id=session.id, exercise_index=0,
                exercise_name="Przysiad ze sztangą",
                result=f"4x6 @ {squat_kg} kg",
                sets_json=json.dumps([{"weight_kg": squat_kg, "reps": 6}] * 4),
            ))
            db.add(WorkoutEntry(
                id=new_id("WKE"), session_id=session.id, exercise_index=1,
                exercise_name="Wyciskanie sztangi leżąc",
                result=f"4x8 @ {bench_kg} kg",
                sets_json=json.dumps([{"weight_kg": bench_kg, "reps": 8}] * 4),
            ))

        kreatyna = schedule_by_name["Kreatyna 5 g"]
        trening = schedule_by_name["Trening siłowy"]
        for offset in range(14):
            date = (today - timedelta(days=offset)).isoformat()
            # Suplement: pominięty co czwarty dzień (realistyczna adherencja).
            db.add(ScheduleCompletion(
                id=new_id("SCP"), schedule_item_id=kreatyna.id, client_id=client_a.id,
                completed_on=date, status="SKIPPED" if offset % 4 == 0 else "DONE",
                created_by=client_a.id,
            ))
        for offset in (2, 5, 9):
            date = (today - timedelta(days=offset)).isoformat()
            db.add(ScheduleCompletion(
                id=new_id("SCP"), schedule_item_id=trening.id, client_id=client_a.id,
                completed_on=date, status="DONE", created_by=client_a.id,
            ))

        # --- Dziennik obserwacji klienta A ---
        db.add(Observation(
            id=new_id("OBS"), client_id=client_a.id,
            occurred_on=(today - timedelta(days=1)).isoformat(),
            category="SAMOPOCZUCIE", severity="INFO",
            text="Dobra energia w ciągu dnia, sen bez zarzutu.",
            created_by=client_a.id,
        ))
        db.add(Observation(
            id=new_id("OBS"), client_id=client_a.id,
            occurred_on=(today - timedelta(days=3)).isoformat(),
            schedule_item_id=kreatyna.id, category="REAKCJA", severity="NIEPOKOJACE",
            text="Po kreatynie lekki dyskomfort żołądka — nie wiem, czy to od "
                 "niej, czy od kawy na czczo. Obserwuję.",
            created_by=client_a.id,
        ))

        # --- Dziennik kaloryczny klienta A (ostatnie 10 dni, na tle celu 2300 kcal) ---
        for offset in range(10):
            date = (today - timedelta(days=offset)).isoformat()
            db.add(DailyNutritionLog(
                id=new_id("NLG"), client_id=client_a.id, logged_on=date,
                kcal=2250 + (offset % 3) * 60, protein_g=175, water_l=2.4,
                created_by=client_a.id,
            ))

        # --- Pomiary klienta A (8 tygodni historii) ---
        for week in range(8):
            date = (today - timedelta(days=7 * (7 - week))).isoformat()
            db.add(Measurement(id=new_id("MSR"), client_id=client_a.id,
                               kind="weight", value=round(90.0 - week * 0.6, 1),
                               unit="kg", measured_at=date,
                               created_by=client_a.id))
            db.add(Measurement(id=new_id("MSR"), client_id=client_a.id,
                               kind="waist", value=round(96.0 - week * 0.5, 1),
                               unit="cm", measured_at=date,
                               created_by=client_a.id))
        db.add(Measurement(id=new_id("MSR"), client_id=client_b.id,
                           kind="weight", value=71.2, unit="kg",
                           measured_at=today.isoformat(), created_by=client_b.id))

        # --- Raport tygodniowy klienta A (zeszły tydzień, oceniony) ---
        checkin = WeeklyCheckin(
            id=new_id("CKN"), client_id=client_a.id,
            week_start=(monday - timedelta(days=7)).isoformat(),
            payload_json=json.dumps({
                "weight_kg": 86.4, "measurements": {"waist": 93.5},
                "trainings_done": 3, "diet_adherence": 4, "energy": 4,
                "sleep": 3, "hunger": 2, "stress": 3, "recovery": 4,
                "pain_note": None,
                "comment": "Dobry tydzień, przysiad czuję mocno.",
                "questions": "Czy mogę dodać interwały w sobotę?",
            }, ensure_ascii=False),
            status="REVIEWED",
            coach_response="Świetna robota. Interwały OK — 20 min, tętno do 160. "
                           "Od przyszłego tygodnia przysiad 105 kg (plan v2).",
            reviewed_by=coach.id,
            rating=5,
        )
        db.add(checkin)
        record_event(db, action="CHECKIN_SUBMITTED", actor_id=client_a.id,
                     subject_ids=[client_a.id],
                     payload={"checkin_id": checkin.id,
                              "week_start": checkin.week_start, "revision": 1},
                     summary=f"Raport tygodniowy {checkin.week_start} (demo)")

        # --- Wiadomości ---
        db.flush()
        thread_a = db.query(MessageThread).filter_by(client_id=client_a.id).one()
        db.add(Message(id=new_id("MSG"), thread_id=thread_a.id,
                       author_id=client_a.id,
                       body="Cześć! Po dzisiejszym treningu lekkie pieczenie w barku "
                            "przy ostatniej serii wyciskania. Nic mocnego, ale wolę "
                            "zgłosić."))
        db.add(Message(id=new_id("MSG"), thread_id=thread_a.id,
                       author_id=coach.id,
                       body="Dzięki za info! Na następnym treningu zejdź do 60 kg "
                            "i pełna kontrola tempa. Jak coś się powtórzy — dajemy "
                            "zamiennik. Trzymaj się planu v2 przy przysiadzie."))

        # --- Dokument (regulamin współpracy jako PDF demo) ---
        settings.ensure_dirs()
        pdf_bytes = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                     b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
                     b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj\n"
                     b"trailer<</Root 1 0 R>>\n%%EOF\n")
        import hashlib
        import uuid as _uuid
        from pathlib import Path

        rel_path = f"{_uuid.uuid4().hex}.pdf"
        (Path(settings.upload_dir) / rel_path).write_bytes(pdf_bytes)
        stored = StoredFile(
            id=new_id("FIL"), owner_user_id=client_a.id,
            filename="zasady-wspolpracy.pdf", content_type="application/pdf",
            size_bytes=len(pdf_bytes), sha256=hashlib.sha256(pdf_bytes).hexdigest(),
            storage_path=rel_path, uploaded_by=coach.id,
        )
        db.add(stored)
        db.add(Document(id=new_id("DOC"), client_id=client_a.id, file_id=stored.id,
                        title="Zasady współpracy", category="INNE",
                        uploaded_by=coach.id))

        # --- Zdjęcia progresu klienta A (syntetyczne, do porównywarki) ---
        import base64 as _b64

        photo_ids = []
        for b64, days_ago in [(DEMO_PHOTO_BEFORE_B64, 49), (DEMO_PHOTO_AFTER_B64, 0)]:
            png = _b64.b64decode(b64)
            rel = f"{_uuid.uuid4().hex}.png"
            (Path(settings.upload_dir) / rel).write_bytes(png)
            f = StoredFile(
                id=new_id("FIL"), owner_user_id=client_a.id,
                filename="sylwetka.png", content_type="image/png",
                size_bytes=len(png), sha256=hashlib.sha256(png).hexdigest(),
                storage_path=rel, uploaded_by=client_a.id,
            )
            db.add(f)
            photo_ids.append((f.id, days_ago))
        from .models import ProgressPhoto

        for file_id, days_ago in photo_ids:
            db.add(ProgressPhoto(
                id=new_id("PHT"), client_id=client_a.id, file_id=file_id,
                taken_at=(today - timedelta(days=days_ago)).isoformat(),
            ))


        # --- Płatności: opłacona i oczekująca ---
        pay = PaymentSchedule(
            id=new_id("PSC"), client_id=client_a.id, coach_id=coach.id,
            package_name="Prowadzenie miesięczne PRO", amount_cents=45000,
            period="MONTHLY", created_by=coach.id,
        )
        db.add(pay)
        db.add(PaymentRecord(id=new_id("PAY"), schedule_id=pay.id,
                             due_date=(today - timedelta(days=30)).isoformat(),
                             amount_cents=45000, status="PAID",
                             paid_at=(today - timedelta(days=29)).isoformat(),
                             marked_by=coach.id))
        db.add(PaymentRecord(id=new_id("PAY"), schedule_id=pay.id,
                             due_date=(today + timedelta(days=3)).isoformat(),
                             amount_cents=45000, status="PENDING"))
        pay_b = PaymentSchedule(
            id=new_id("PSC"), client_id=client_b.id, coach_id=coach.id,
            package_name="Prowadzenie miesięczne START", amount_cents=30000,
            period="MONTHLY", created_by=coach.id,
        )
        db.add(pay_b)
        db.add(PaymentRecord(id=new_id("PAY"), schedule_id=pay_b.id,
                             due_date=(today - timedelta(days=5)).isoformat(),
                             amount_cents=30000, status="PENDING"))

        # --- Symulowani klienci C–E: różne stany pracy trenerskiej ---

        # Klient C (Marek): raport CZEKA na ocenę + nieprzeczytana
        # wiadomość — widoczna praca "do zrobienia" na dashboardzie.
        db.add(Goal(id=new_id("GOL"), client_id=client_c.id,
                    title="Budowa masy mięśniowej (+5 kg)", kind="MAIN",
                    target_date=(today + timedelta(days=120)).isoformat(),
                    created_by=coach.id))
        plan_c = TrainingPlan(id=new_id("PLN"), client_id=client_c.id,
                              coach_id=coach.id, title="Masa — góra/dół 4x/tydz.",
                              current_version_no=1)
        db.add(plan_c)
        db.add(TrainingPlanVersion(
            id=new_id("PLV"), plan_id=plan_c.id, version_no=1,
            reason="Plan startowy", created_by=coach.id,
            content_json=json.dumps({"days": [
                {"name": "Góra A", "weekday": 1, "exercises": [
                    ex_ref("Wyciskanie sztangi leżąc", sets="4", reps="8",
                           weight="80 kg", rest="150 s"),
                    ex_ref("Wiosłowanie sztangą w opadzie", sets="4",
                           reps="10", weight="70 kg"),
                ]},
                {"name": "Dół A", "weekday": 2, "exercises": [
                    ex_ref("Przysiad ze sztangą", sets="4", reps="8",
                           weight="110 kg", rest="180 s"),
                ]},
            ]}, ensure_ascii=False),
        ))
        db.add(WeeklyCheckin(
            id=new_id("CKN"), client_id=client_c.id, week_start=monday.isoformat(),
            payload_json=json.dumps({
                "weight_kg": 78.9, "trainings_done": 4, "diet_adherence": 5,
                "energy": 4, "sleep": 4, "hunger": 4, "stress": 2, "recovery": 4,
                "comment": "Najlepszy tydzień od startu, apetyt dopisuje.",
                "questions": "Czy dokładamy piąty trening?",
            }, ensure_ascii=False),
        ))
        db.add(Measurement(id=new_id("MSR"), client_id=client_c.id, kind="weight",
                           value=78.9, unit="kg", measured_at=today.isoformat(),
                           created_by=client_c.id))
        pay_c = PaymentSchedule(
            id=new_id("PSC"), client_id=client_c.id, coach_id=coach.id,
            package_name="Prowadzenie miesięczne PRO", amount_cents=45000,
            period="MONTHLY", created_by=coach.id,
        )
        db.add(pay_c)
        db.add(PaymentRecord(id=new_id("PAY"), schedule_id=pay_c.id,
                             due_date=(today + timedelta(days=12)).isoformat(),
                             amount_cents=45000, status="PENDING"))

        # Klient D (Anna): praca trenera już WYKONANA — raport oceniony
        # (rating), odpowiedź w wątku, płatność opłacona, trend pomiarów.
        db.add(Goal(id=new_id("GOL"), client_id=client_d.id,
                    title="Redukcja 6 kg i poprawa kondycji", kind="MAIN",
                    target_date=(today + timedelta(days=60)).isoformat(),
                    created_by=coach.id))
        for week in range(6):
            db.add(Measurement(id=new_id("MSR"), client_id=client_d.id,
                               kind="weight", value=round(68.5 - week * 0.4, 1),
                               unit="kg",
                               measured_at=(today - timedelta(days=7 * (5 - week))).isoformat(),
                               created_by=client_d.id))
        db.add(WeeklyCheckin(
            id=new_id("CKN"), client_id=client_d.id,
            week_start=(monday - timedelta(days=7)).isoformat(),
            payload_json=json.dumps({
                "weight_kg": 66.5, "trainings_done": 3, "diet_adherence": 4,
                "energy": 3, "sleep": 4, "hunger": 3, "stress": 3, "recovery": 3,
                "comment": "Trzymam deficyt, weekend był trudny.",
            }, ensure_ascii=False),
            status="REVIEWED",
            coach_response="Bardzo dobra konsekwencja. Weekendy planujemy z "
                           "wyprzedzeniem — dorzucam przepis na wysokobiałkowy "
                           "deser do bazy wiedzy. Trening bez zmian.",
            reviewed_by=coach.id,
            rating=4,
        ))
        pay_d = PaymentSchedule(
            id=new_id("PSC"), client_id=client_d.id, coach_id=coach.id,
            package_name="Prowadzenie miesięczne START", amount_cents=30000,
            period="MONTHLY", created_by=coach.id,
        )
        db.add(pay_d)
        db.add(PaymentRecord(id=new_id("PAY"), schedule_id=pay_d.id,
                             due_date=(today - timedelta(days=14)).isoformat(),
                             amount_cents=30000, status="PAID",
                             paid_at=(today - timedelta(days=13)).isoformat(),
                             marked_by=coach.id))

        # Klient E (Piotr): zaległości — brak jakiegokolwiek raportu,
        # przeterminowana płatność, niepokojąca obserwacja (kolano).
        db.add(Goal(id=new_id("GOL"), client_id=client_e.id,
                    title="Powrót do formy i mobilność (start od zera)",
                    kind="MAIN", created_by=coach.id))
        pay_e = PaymentSchedule(
            id=new_id("PSC"), client_id=client_e.id, coach_id=coach.id,
            package_name="Prowadzenie miesięczne START", amount_cents=30000,
            period="MONTHLY", created_by=coach.id,
        )
        db.add(pay_e)
        db.add(PaymentRecord(id=new_id("PAY"), schedule_id=pay_e.id,
                             due_date=(today - timedelta(days=10)).isoformat(),
                             amount_cents=30000, status="PENDING"))
        db.add(Observation(
            id=new_id("OBS"), client_id=client_e.id,
            occurred_on=(today - timedelta(days=2)).isoformat(),
            category="OBJAW", severity="NIEPOKOJACE",
            text="Kłucie w prawym kolanie przy schodzeniu ze schodów, "
                 "od dwóch dni. Bez urazu, ale wolę zgłosić.",
            created_by=client_e.id,
        ))

        # Wiadomości symulowanych klientów (C: nieprzeczytana; D: wątek
        # domknięty odpowiedzią trenera).
        db.flush()
        thread_c = db.query(MessageThread).filter_by(client_id=client_c.id).one()
        db.add(Message(id=new_id("MSG"), thread_id=thread_c.id,
                       author_id=client_c.id,
                       body="Trenerze, wysłałem raport — i pytanie: mogę w "
                            "sobotę zrobić dodatkowy trening z kolegą?"))
        thread_d = db.query(MessageThread).filter_by(client_id=client_d.id).one()
        db.add(Message(id=new_id("MSG"), thread_id=thread_d.id,
                       author_id=client_d.id,
                       body="Dziękuję za ocenę raportu! Przepis na deser "
                            "bardzo się przyda.",
                       read_at=datetime.now(UTC).isoformat()))
        db.add(Message(id=new_id("MSG"), thread_id=thread_d.id,
                       author_id=coach.id,
                       body="Śmiało, jest już w bazie wiedzy w kategorii "
                            "Dieta. Daj znać jak smakował!"))


        # --- Baza produktów spożywczych (makro na 100 g) ---
        # Katalog (400+ pozycji w 16 kategoriach) mieszka w osobnym module
        # `food_catalog_data`, żeby seed pozostał czytelny. Pochodzenie i
        # status danych: docs/BAZA_PRODUKTOW.md.
        for food in FOOD_ROWS:
            db.add(FoodProduct(
                id=new_id("FOD"), coach_id=coach.id, name=food.name, category=food.category,
                kcal_100g=food.kcal, protein_100g=food.protein, fat_100g=food.fat,
                carbs_100g=food.carbs, fiber_100g=food.fiber,
                default_portion_g=food.portion_g,
                unit_name=food.unit_name, unit_grams=food.unit_grams,
                source=FOOD_SOURCE, note=food.note, created_by=coach.id,
            ))

        # --- Baza wiedzy trenera ---
        from .models import KnowledgeItem

        db.add(KnowledgeItem(
            id=new_id("KNW"), coach_id=coach.id,
            title="Jak czytać swój plan treningowy",
            category="Trening", pinned=True, created_by=coach.id,
            body="Każde ćwiczenie ma serie × powtórzenia, ciężar, tempo i "
                 "przerwę. Tempo (np. 2011) czytamy jako: 2 s opuszczanie, "
                 "0 s przerwy na dole, 1 s podnoszenie, 1 s przerwy na "
                 "górze. Jeśli czujesz, że zapas powtórzeń jest większy niż "
                 "2-3, to znak, żeby dać znać w raporcie — być może czas na "
                 "progresję.",
        ))
        db.add(KnowledgeItem(
            id=new_id("KNW"), coach_id=coach.id,
            title="Białko — ile i po co",
            category="Dieta", pinned=True, created_by=coach.id,
            body="Białko to budulec mięśni i jeden z filarów sytości. "
                 "Rozłóż dzienną porcję na 3-4 posiłki po ok. 30-40 g "
                 "(mięso, ryby, nabiał, rośliny strączkowe, odżywka "
                 "białkowa). Nie musisz jeść co 2-3 h — liczy się suma "
                 "w ciągu dnia.",
        ))
        db.add(KnowledgeItem(
            id=new_id("KNW"), coach_id=coach.id,
            title="Sen a regeneracja",
            category="Regeneracja", created_by=coach.id,
            body="7-9 h snu to nie luksus, tylko część treningu — w tym "
                 "czasie zachodzi większość regeneracji i adaptacji "
                 "mięśniowej. Stały rytm (podobna pora zasypiania) działa "
                 "lepiej niż nadrabianie w weekend.",
        ))
        db.add(KnowledgeItem(
            id=new_id("KNW"), coach_id=coach.id,
            title="Co zrobić, gdy motywacja siada",
            category="Motywacja", created_by=coach.id,
            body="To normalne, że intensywność chęci się zmienia. Zamiast "
                 "czekać na motywację, oprzyj się na harmonogramie — jedno "
                 "małe działanie (rozgrzewka, pierwsza seria) często "
                 "wystarcza, żeby ruszyć dalej. Jeśli to się powtarza, "
                 "napisz do mnie — razem dopasujemy plan.",
        ))
        db.add(KnowledgeItem(
            id=new_id("KNW"), coach_id=coach.id,
            title="Kiedy zgłosić ból, a kiedy to normalne zmęczenie",
            category="Zdrowie", created_by=coach.id,
            body="Delikatna zakwaszona bolesność mięśni 1-2 dni po treningu "
                 "to norma. Ostry, kłujący ból podczas ruchu, ból stawu "
                 "(nie mięśnia) albo obrzęk — zawsze zgłoś od razu przez "
                 "raport lub wiadomość. W razie wątpliwości zawsze "
                 "skonsultuj się z lekarzem — nie czekaj na odpowiedź "
                 "trenera.",
        ))

        db.commit()
        print("Seed OK. Konta demo:")
        for email, password, name in DEMO_ACCOUNTS.values():
            print(f"  {name}: {email} / {password}")
        return {k: u.id for k, u in users.items()}


if __name__ == "__main__":
    seed()
