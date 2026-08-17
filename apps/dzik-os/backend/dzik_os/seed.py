"""Syntetyczne dane demonstracyjne Dzik OS.

Uruchomienie: python -m dzik_os.seed
Konta (WYŁĄCZNIE środowisko lokalne/staging — nigdy produkcja z prawdziwymi
danymi):

  trener:  dzik@example.com      / DzikTrener#2026
  klient A: klient.a@example.com / KlientA#2026!x
  klient B: klient.b@example.com / KlientB#2026!x
  admin:   admin@example.com     / DzikAdmin#2026

Żadna z osób nie jest prawdziwa; wszystkie wartości są zmyślone.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from .authz import CONSENT_DOMAIN, CONSENT_PURPOSE
from .config import settings
from .db import db_session, run_migrations
from .hos_bridge import ConsentService, record_event
from .models import (
    CoachClientRelationship,
    Document,
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
from .security import hash_password

DEMO_ACCOUNTS = {
    "coach": ("dzik@example.com", "DzikTrener#2026", "Lubelski Dzik"),
    "client_a": ("klient.a@example.com", "KlientA#2026!x", "Klient Testowy A"),
    "client_b": ("klient.b@example.com", "KlientB#2026!x", "Klient Testowy B"),
    "admin": ("admin@example.com", "DzikAdmin#2026", "Administrator Techniczny"),
}


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
        role_map = {
            coach.id: "COACH", client_a.id: "CLIENT",
            client_b.id: "CLIENT", admin.id: "ADMIN",
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

        today = datetime.now(UTC).date()
        monday = today - timedelta(days=today.isoweekday() - 1)

        for client in (client_a, client_b):
            rel = CoachClientRelationship(
                id=new_id("REL"), coach_id=coach.id, client_id=client.id,
                created_by=coach.id,
            )
            db.add(rel)
            db.add(MessageThread(id=new_id("THR"), coach_id=coach.id,
                                 client_id=client.id))
            ConsentService.grant(
                db, subject_id=client.id, grantee_id=coach.id,
                purpose=CONSENT_PURPOSE, domain=CONSENT_DOMAIN,
                actions="read,write", allow_sensitive=True,
                confirmed=True,  # konta demo mają zgody już potwierdzone
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

        # --- Plan treningowy klienta A: v1 i v2 (historia wersji) ---
        plan_a = TrainingPlan(id=new_id("PLN"), client_id=client_a.id,
                              coach_id=coach.id, title="Redukcja — siła 3x/tydz.",
                              current_version_no=2)
        db.add(plan_a)
        days_v1 = [
            {"name": "Trening A — góra", "weekday": 1, "exercises": [
                {"name": "Wyciskanie sztangi leżąc", "sets": "4", "reps": "8",
                 "weight": "70 kg", "tempo": "2011", "rest": "120 s",
                 "comment": "Ostatnia seria do 1 w zapasie",
                 "video_url": "https://example.com/wyciskanie"},
                {"name": "Wiosłowanie hantlem", "sets": "3", "reps": "10",
                 "weight": "30 kg", "rest": "90 s"},
            ]},
            {"name": "Trening B — dół", "weekday": 3, "exercises": [
                {"name": "Przysiad ze sztangą", "sets": "4", "reps": "6",
                 "weight": "100 kg", "rest": "180 s"},
                {"name": "Rumuński martwy ciąg", "sets": "3", "reps": "8",
                 "weight": "80 kg", "rest": "120 s"},
            ]},
            {"name": "Trening C — całe ciało", "weekday": 5, "exercises": [
                {"name": "Martwy ciąg", "sets": "3", "reps": "5",
                 "weight": "120 kg", "rest": "180 s"},
                {"name": "OHP", "sets": "3", "reps": "8", "weight": "45 kg",
                 "rest": "120 s"},
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
        db.add(TrainingPlanVersion(
            id=new_id("PLV"), plan_id=plan_a.id, version_no=2,
            reason="Progresja przysiadu po raporcie z tygodnia 2; bark bez bólu",
            created_by=coach.id,
            content_json=json.dumps({"days": days_v2}, ensure_ascii=False),
        ))
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
                    {"name": "Przysiad", "sets": "3", "reps": "8", "weight": "80 kg"},
                    {"name": "Wyciskanie leżąc", "sets": "3", "reps": "8",
                     "weight": "60 kg"},
                ]},
                {"name": "FBW 2", "weekday": 4, "exercises": [
                    {"name": "Martwy ciąg", "sets": "3", "reps": "5", "weight": "110 kg"},
                ]},
                {"name": "FBW 3", "weekday": 6, "exercises": [
                    {"name": "Podciąganie", "sets": "4", "reps": "max"},
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
                {"name": "Push", "exercises": [{"name": "Wyciskanie leżąc",
                                               "sets": "4", "reps": "8"}]},
                {"name": "Pull", "exercises": [{"name": "Wiosłowanie", "sets": "4",
                                               "reps": "10"}]},
                {"name": "Legs", "exercises": [{"name": "Przysiad", "sets": "4",
                                               "reps": "8"}]},
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
            }, ensure_ascii=False),
        ))

        # --- Harmonogram klienta A ---
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
            db.add(ScheduleItem(
                id=new_id("SCH"), client_id=client_a.id, name=name,
                category=category, time_of_day=tod, days_of_week=days,
                instruction=instruction, author_id=coach.id, author_note=note,
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

        db.commit()
        print("Seed OK. Konta demo:")
        for email, password, name in DEMO_ACCOUNTS.values():
            print(f"  {name}: {email} / {password}")
        return {k: u.id for k, u in users.items()}


if __name__ == "__main__":
    seed()
