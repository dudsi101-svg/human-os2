"""Głęboki wywiad — drugi scenariusz mechanizmu rozmowy (flow='deep').

Rozmowa startowa (`onboarding_flow.STEPS`) odpowiada na pytanie „CO mamy
zbudować"; głęboki wywiad — „dlaczego wcześniej się nie udawało i co tym
razem musi być inaczej". Mechanizm jest WSPÓLNY (te same tabele, walidacja,
wersjonowanie, zgody, wznowienie — patrz `routers/onboarding.build_router`);
ten moduł dostarcza wyłącznie scenariusz: kroki, reguły warunkowe i flagi.

Zasady identyczne jak w rozmowie startowej, plus dwie własne:

* **flagi wyboru** (`Step.flag_options`) — przesiew bezpieczeństwa przed
  wysiłkiem (moduł C, logika kwestionariuszy typu PAR-Q) oraz pytanie
  o relację z ciałem (moduł E) podnoszą flagę sesji przy odpowiedzi
  z listy; komunikat jest spokojny i NICZEGO nie ocenia — kieruje do
  lekarza/specjalisty i oznacza temat trenerowi do wstrzymania;
* **zero AI** — podsumowanie wywiadu jest zawsze deterministyczne
  (prompt AI rozmowy startowej nie zna tych pól; osobna decyzja, osobna
  runda, jeśli kiedyś w ogóle).

Granica INTENDED_PURPOSE §2: wywiad zbiera wyłącznie DEKLARACJE do planu
układanego przez człowieka. Moduł zdrowia to przesiew-do-skierowania,
nie diagnostyka; moduł „stres i głowa" zatrzymuje się na „czy prowadzić
ostrożniej" — diagnoza i terapia są poza aplikacją i poza trenerem.
"""

from __future__ import annotations

from .authz import DOMAIN_HEALTH, DOMAIN_NUTRITION
from .onboarding_flow import (
    KIND_BOOL,
    KIND_CHOICE,
    KIND_INFO,
    KIND_LONGTEXT,
    KIND_MULTI,
    KIND_SCALE,
    KIND_TEXT,
    Step,
)

# Komunikaty flag — spokojne, bez oceny, bez hipotez (wzorzec:
# onboarding_flow.SAFETY_MESSAGE, tylko dopasowane do kontekstu pytania).
FLAG_MESSAGE_PRESCREEN = (
    "Dziękujemy za szczerość. Taka odpowiedź oznacza jedno: zanim trener "
    "zaplanuje obciążenia, warto skonsultować się z lekarzem — to normalna "
    "praktyka, nie powód do niepokoju. Wywiad możesz spokojnie kontynuować; "
    "zaznaczyliśmy tę odpowiedź trenerowi, żeby wstrzymał się z tą częścią "
    "planu do czasu Twojej konsultacji."
)
FLAG_MESSAGE_BODY_RELATION = (
    "Dziękujemy, że o tym napisałeś(-aś) — to wymaga zaufania. Trener "
    "poprowadzi współpracę ostrożniej (np. bez nacisku na częste ważenie) "
    "i niczego nie będzie oceniał. Jeśli wsparcie specjalisty byłoby "
    "pomocne, warto je rozważyć — a ta aplikacja go nie zastępuje."
)

_PRZESIEW_OBJAWY = (
    "Ból lub ucisk w klatce piersiowej",
    "Omdlenie lub utrata przytomności",
    "Silne zawroty głowy",
    "Nagła duszność nieadekwatna do wysiłku",
    "Kołatanie serca",
    "Żadne z powyższych",
)

DEEP_STEPS: tuple[Step, ...] = (
    Step(
        id="gw_intro",
        topic="O tym wywiadzie",
        question="To głęboki wywiad — rozmowa o tym, co ma sprawić, że tym "
        "razem się uda.",
        why="Kilkadziesiąt pytań o motywację, historię, sen, stres, jedzenie "
        "i logistykę tygodnia. Każde możesz pominąć, każde mówi, po co jest, "
        "a przerwać i wrócić możesz w dowolnym momencie — także z innego "
        "urządzenia. Odpowiedzi zobaczy tylko trener, w zakresie Twoich zgód.",
        kind=KIND_INFO,
        options=("Zaczynamy",),
        max_len=40,
    ),
    # ------------------------------------------------ A · Cel głębiej
    Step(
        id="gw_a1",
        topic="Cel głębiej",
        question="Co się zmieni w Twoim codziennym życiu, kiedy osiągniesz "
        "cel? Opisz jedną konkretną scenę.",
        why="Cel „schudnąć 8 kg” to liczba; scena „wchodzę po schodach bez "
        "zadyszki” to paliwo. Do niej wracamy w trudnych tygodniach.",
        kind=KIND_LONGTEXT,
        placeholder="np. wbiegam za synem na trzecie piętro i nie muszę udawać, że nic się nie stało",
        profile_field="gw_cel_scena",
        max_len=1000,
    ),
    Step(
        id="gw_a2",
        topic="Cel głębiej",
        question="Jak ważna jest dla Ciebie ta zmiana? (1 = mało, 10 = bardzo)",
        why="Sama liczba to początek — następne pytanie wydobędzie z niej "
        "prawdziwe powody.",
        kind=KIND_SCALE,
        options=("1", "2", "3", "4", "5", "6", "7", "8", "9", "10"),
        profile_field="gw_cel_waznosc",
        max_len=10,
    ),
    Step(
        id="gw_a2_powod",
        topic="Cel głębiej",
        question="Dlaczego nie wybrałeś(-aś) liczby o dwa niższej?",
        why="To pytanie z wywiadu motywującego: odpowiedź na nie to lista "
        "Twoich prawdziwych powodów — lepsza niż jakakolwiek skala.",
        kind=KIND_LONGTEXT,
        placeholder="np. bo mam dość zadyszki i nie chcę skończyć jak…",
        profile_field="gw_cel_waznosc_powod",
        max_len=800,
    ),
    Step(
        id="gw_a3",
        topic="Cel głębiej",
        question="Czy ten cel jest Twój, czy trochę czyjś?",
        why="Cel z zewnętrznej presji (partner, lekarz, wydarzenie) wymaga "
        "innego prowadzenia niż cel własny — i szybciej gaśnie, jeśli o tym "
        "nie wiemy.",
        kind=KIND_CHOICE,
        options=(
            "W pełni mój",
            "Częściowo czyjś (ktoś mnie namawia)",
            "Głównie czyjś — sam(a) bym nie zaczął(-ęła)",
        ),
        profile_field="gw_cel_wlasnosc",
        max_len=80,
    ),
    Step(
        id="gw_a4",
        topic="Cel głębiej",
        question="Ile razy wcześniej próbowałeś(-aś) osiągnąć podobny cel "
        "i co przerywało próbę?",
        why="Poprzednie próby to najcenniejsza mapa min. Plan, który nie "
        "omija znanych min, wybuchnie na tych samych.",
        kind=KIND_LONGTEXT,
        placeholder="np. 3 razy; za każdym razem kończyło się przy nadgodzinach w pracy",
        profile_field="gw_proby_historia",
        max_len=1200,
    ),
    Step(
        id="gw_a5",
        topic="Cel głębiej",
        question="Po czym poznasz po 4 tygodniach, że współpraca działa — "
        "zanim zmieni się sylwetka?",
        why="Waga potrafi stać tygodniami, a motywacja potrzebuje "
        "wcześniejszych sygnałów: sen, energia, siła, spodnie. Ustalamy je "
        "z góry.",
        kind=KIND_LONGTEXT,
        placeholder="np. zasypiam przed północą; nie ma zadyszki na schodach",
        profile_field="gw_sygnaly_4tyg",
        max_len=800,
    ),
    # ------------------------------------------------ B · Historia treningowa
    Step(
        id="gw_b1",
        topic="Historia treningowa",
        question="Opowiedz o najlepszym okresie treningowym w życiu: co "
        "wtedy robiłeś(-aś), z kim i dlaczego się skończył?",
        why="Najlepszy okres pokazuje warunki, w których działasz. "
        "Odtworzenie ich jest łatwiejsze niż wymyślanie nowych.",
        kind=KIND_LONGTEXT,
        placeholder="np. 2019, siłownia z kolegą 3x w tygodniu; skończyło się po przeprowadzce",
        profile_field="gw_najlepszy_okres",
        max_len=1200,
    ),
    Step(
        id="gw_b2",
        topic="Historia treningowa",
        question="Jakie formy ruchu sprawiają Ci frajdę, a jakich szczerze "
        "nie znosisz?",
        why="Plan z ćwiczeń, których nienawidzisz, to plan na trzy tygodnie. "
        "Lepiej wiedzieć od razu.",
        kind=KIND_LONGTEXT,
        placeholder="np. lubię: ciężary, rower; nie znoszę: biegania, burpees",
        profile_field="gw_ruch_preferencje",
        max_len=800,
    ),
    Step(
        id="gw_b3",
        topic="Historia treningowa",
        question="Czy pracowałeś(-aś) już z trenerem? Co działało, a co nie?",
        why="Nie chcę powtarzać cudzych błędów ani rezygnować z tego, co "
        "u Ciebie działało.",
        kind=KIND_LONGTEXT,
        placeholder="np. tak, rok temu — działały krótkie plany, nie działał brak kontaktu",
        profile_field="gw_trener_historia",
        max_len=1000,
    ),
    Step(
        id="gw_b4",
        topic="Historia treningowa",
        question="Jak reagujesz, gdy opuścisz zaplanowany trening?",
        why="Reakcja na pierwsze potknięcie przesądza o całości. Znając ją, "
        "ustawiamy z góry zasadę powrotu — nie karę.",
        kind=KIND_CHOICE,
        options=(
            "Odpuszczam resztę tygodnia",
            "Nadrabiam następnego dnia",
            "Mam poczucie winy, ale wracam do planu",
            "Nic się nie dzieje — po prostu trenuję dalej",
        ),
        profile_field="gw_reakcja_potkniecie",
        max_len=80,
    ),
    Step(
        id="gw_b5",
        topic="Historia treningowa",
        question="Jaki był Twój najdłuższy nieprzerwany okres regularnego "
        "ruchu i co go umożliwiło?",
        why="Realna, sprawdzona częstotliwość jest lepszym punktem startu "
        "niż ambitna deklaracja.",
        kind=KIND_TEXT,
        placeholder="np. 8 miesięcy — stały termin z kolegą",
        profile_field="gw_najdluzszy_okres",
        max_len=300,
    ),
    # ------------------------------------------------ C · Zdrowie (przesiew)
    Step(
        id="gw_c1",
        topic="Zdrowie — przesiew",
        question="Czy podczas wysiłku (lub tuż po) zdarzyło Ci się "
        "kiedykolwiek któreś z poniższych?",
        why="To pytania przesiewowe, które każdy odpowiedzialny trener "
        "zadaje przed obciążeniem. „Tak” nie oznacza niczego złego — "
        "oznacza, że najpierw lekarz, potem plan.",
        kind=KIND_MULTI,
        options=_PRZESIEW_OBJAWY,
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_przesiew_objawy",
        flag_options=tuple(o for o in _PRZESIEW_OBJAWY if o != "Żadne z powyższych"),
        max_len=300,
    ),
    Step(
        id="gw_c2",
        topic="Zdrowie — przesiew",
        question="Czy lekarz kiedykolwiek zalecił Ci ograniczenie wysiłku "
        "fizycznego?",
        why="Zalecenie lekarza jest dla trenera granicą, nie sugestią.",
        kind=KIND_BOOL,
        options=("Tak", "Nie"),
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_lekarz_ograniczenie",
        flag_options=("Tak",),
        max_len=20,
    ),
    Step(
        id="gw_c2_opis",
        topic="Zdrowie — przesiew",
        question="Kiedy to było i jakiego zakresu dotyczyło?",
        why="Trener zapisze to jako granicę planu. Oceny medycznej nie robi "
        "ani trener, ani aplikacja.",
        kind=KIND_LONGTEXT,
        placeholder="np. 2024, po zabiegu — pół roku bez dźwigania",
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_lekarz_ograniczenie_opis",
        scan_safety=True,
        conditional=True,
        max_len=1000,
    ),
    Step(
        id="gw_c3",
        topic="Zdrowie — przesiew",
        question="Czy przyjmujesz na stałe leki, o których trener powinien "
        "wiedzieć planując wysiłek (np. wpływające na tętno, ciśnienie, "
        "poziom cukru)?",
        why="Nie pytamy, na co się leczysz — pytamy, czy coś zmienia reakcję "
        "organizmu na trening. Zapisujemy wyłącznie Twoją deklarację.",
        kind=KIND_LONGTEXT,
        placeholder="np. lek na ciśnienie rano; wolę nie podawać nazw",
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_leki_deklaracja",
        max_len=800,
    ),
    Step(
        id="gw_c4",
        topic="Zdrowie — przesiew",
        question="Operacje i poważne urazy w życiu — co, kiedy, czy w pełni "
        "wyleczone?",
        why="Stary uraz „wyleczony na 90%” wraca przy złym doborze ćwiczeń. "
        "Historia pozwala go ominąć, zanim się przypomni.",
        kind=KIND_LONGTEXT,
        placeholder="np. artroskopia kolana 2021 — OK; złamany nadgarstek 2015 — czasem strzyka",
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_operacje_urazy",
        scan_safety=True,
        max_len=1500,
    ),
    Step(
        id="gw_c5",
        topic="Zdrowie — przesiew",
        question="Czy miewasz bóle nawracające (kręgosłup, kolana, barki, "
        "głowa)? Jak często i co je nasila?",
        why="„Co nasila” mówi więcej niż „co boli” — wokół tego układa się "
        "plan.",
        kind=KIND_LONGTEXT,
        placeholder="np. dół pleców raz w tygodniu, po długim siedzeniu",
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_bole_nawracajace",
        scan_safety=True,
        max_len=1200,
    ),
    Step(
        id="gw_c6",
        topic="Zdrowie — przesiew",
        question="Dobrowolnie: czy jest coś w cyklu, ciąży albo okresie "
        "poporodowym, co trener powinien uwzględnić?",
        why="Plan może i powinien to uwzględniać — ale wyłącznie jeśli "
        "chcesz o tym powiedzieć. To pytanie jest w pełni pomijalne.",
        kind=KIND_LONGTEXT,
        placeholder="np. drugi tydzień cyklu — dużo słabsze treningi",
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_cykl_uwagi",
        max_len=800,
    ),
    # ------------------------------------------------ D · Sen i regeneracja
    Step(
        id="gw_d1",
        topic="Sen i regeneracja",
        question="O której zwykle zasypiasz i wstajesz w dni robocze, "
        "a o której w weekendy?",
        why="Różnica ponad 2 h („społeczny jetlag”) obniża regenerację jak "
        "krótki sen — i zmienia, gdzie w tygodniu ma sens ciężki trening.",
        kind=KIND_TEXT,
        placeholder="np. rob.: 23:30–6:30; weekend: 1:00–9:30",
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_sen_rytm",
        max_len=200,
    ),
    Step(
        id="gw_d2",
        topic="Sen i regeneracja",
        question="Czy budzisz się wypoczęty(-a)? (1 = nigdy, 5 = zwykle tak)",
        why="8 godzin złego snu regeneruje gorzej niż 7 dobrego — liczy się "
        "jakość, nie tylko liczba.",
        kind=KIND_SCALE,
        options=("1", "2", "3", "4", "5"),
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_sen_jakosc",
        max_len=10,
    ),
    Step(
        id="gw_d2_opis",
        topic="Sen i regeneracja",
        question="Co najczęściej psuje Ci sen?",
        why="„Co psuje” (dziecko, ekrany, stres, zmiany) podpowiada, co "
        "realnie da się poprawić — a czego plan ma po prostu nie pogarszać.",
        kind=KIND_LONGTEXT,
        placeholder="np. telefon do 1 w nocy; dziecko budzi się ok. 5",
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_sen_zaklocenia",
        max_len=600,
    ),
    Step(
        id="gw_d3",
        topic="Sen i regeneracja",
        question="Czy pracujesz w nocy albo na zmiany?",
        why="Praca zmianowa przestawia całe planowanie: pory treningu, "
        "posiłków i przypomnień.",
        kind=KIND_BOOL,
        options=("Tak", "Nie"),
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_zmianowosc",
        max_len=20,
    ),
    Step(
        id="gw_d3_wzor",
        topic="Sen i regeneracja",
        question="Opisz wzór zmian — jak wygląda Twój typowy cykl?",
        why="Konkretny rytm zmian pozwala wpisać trening tam, gdzie "
        "naprawdę jest miejsce.",
        kind=KIND_LONGTEXT,
        placeholder="np. tydzień rano / tydzień w nocy; nocki pt–nd",
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_zmianowosc_wzor",
        conditional=True,
        max_len=600,
    ),
    Step(
        id="gw_d4",
        topic="Sen i regeneracja",
        question="Co robisz, żeby odpocząć — i ile razy w tygodniu naprawdę "
        "Ci się to udaje?",
        why="Regeneracja to nie tylko sen. Różnica między „co robię” a „ile "
        "razy się udaje” pokazuje realną przestrzeń na trening.",
        kind=KIND_TEXT,
        placeholder="np. spacer z psem — realnie 2 razy w tygodniu",
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_regeneracja_nawyki",
        max_len=400,
    ),
    # ------------------------------------------------ E · Stres i głowa
    Step(
        id="gw_e1",
        topic="Stres i głowa",
        question="Jak oceniasz swój przeciętny poziom stresu? (1 = spokojnie, "
        "5 = bardzo dużo)",
        why="W tygodniach wysokiego stresu forsowny plan pogarsza, nie "
        "poprawia. Trener, który to wie, planuje falami.",
        kind=KIND_SCALE,
        options=("1", "2", "3", "4", "5"),
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_stres_poziom",
        max_len=10,
    ),
    Step(
        id="gw_e1_zrodlo",
        topic="Stres i głowa",
        question="Co jest głównym źródłem tego stresu?",
        why="Źródło podpowiada rytm: stres z pracy ma szczyty w tygodniu, "
        "stres domowy — wieczorami i w weekendy.",
        kind=KIND_CHOICE,
        options=("Praca", "Dom i rodzina", "Finanse", "Zdrowie", "Coś innego"),
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_stres_zrodlo",
        max_len=40,
    ),
    Step(
        id="gw_e2",
        topic="Stres i głowa",
        question="Czy jedzenie bywa dla Ciebie sposobem na emocje (stres, "
        "nudę, nagrodę)?",
        why="To jeden z najczęstszych i najbardziej ludzkich wzorców. "
        "Nazwany — daje się obejść planem; przemilczany — rozbija każdą "
        "dietę.",
        kind=KIND_CHOICE,
        options=("Tak", "Czasem", "Nie"),
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_jedzenie_emocje",
        max_len=20,
    ),
    Step(
        id="gw_e2_kiedy",
        topic="Stres i głowa",
        question="Kiedy zdarza się to najczęściej?",
        why="Konkretny moment (wieczór po pracy, weekend, kłótnia) pozwala "
        "zaplanować alternatywę dokładnie tam, gdzie jest potrzebna.",
        kind=KIND_LONGTEXT,
        placeholder="np. wieczorem przy serialu, po trudnym dniu",
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_jedzenie_emocje_kiedy",
        conditional=True,
        max_len=600,
    ),
    Step(
        id="gw_e3",
        topic="Stres i głowa",
        question="Czy Twoja relacja z jedzeniem lub własnym ciałem była "
        "kiedyś na tyle trudna, że szukałeś(-aś) albo rozważałeś(-aś) pomoc "
        "specjalisty?",
        why="Pytamy, żeby wiedzieć, czy prowadzenie ma być szczególnie "
        "ostrożne — np. bez nacisku na częste ważenie. Trener nie jest "
        "terapeutą i nie będzie oceniał odpowiedzi.",
        kind=KIND_CHOICE,
        options=("Tak", "Nie", "Wolę pominąć"),
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_relacja_cialo",
        flag_options=("Tak",),
        max_len=20,
    ),
    Step(
        id="gw_e4",
        topic="Stres i głowa",
        question="Kto w Twoim otoczeniu będzie Ci kibicował, a kto może — "
        "nawet nieświadomie — przeszkadzać?",
        why="Domownik przynoszący słodycze potrafi zrobić więcej niż "
        "najlepszy plan. Wiedząc o tym, układamy strategię, nie pretensje.",
        kind=KIND_LONGTEXT,
        placeholder="np. żona kibicuje; teściowa karmi na siłę w każdą niedzielę",
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_otoczenie",
        max_len=800,
    ),
    # ------------------------------------------------ F · Żywienie pod lupą
    Step(
        id="gw_f1",
        topic="Żywienie pod lupą",
        question="Przeprowadź mnie przez wczorajszy dzień jedzeniowy — od "
        "pierwszej kawy do ostatniej przekąski, z godzinami.",
        why="Jeden prawdziwy dzień mówi więcej niż deklaracja „jem zdrowo”. "
        "Bez oceniania — to punkt startu, nie egzamin.",
        kind=KIND_LONGTEXT,
        placeholder="np. 7:00 kawa z mlekiem; 11:00 kanapka…; 22:30 chipsy przy serialu",
        sensitive=True,
        consent_domain=DOMAIN_NUTRITION,
        profile_field="gw_dzien_jedzeniowy",
        max_len=2000,
    ),
    Step(
        id="gw_f2",
        topic="Żywienie pod lupą",
        question="Kto planuje i gotuje posiłki u Ciebie w domu? Ile minut "
        "dziennie realnie masz na gotowanie?",
        why="Dieta dla osoby, która nie gotuje, musi wyglądać inaczej niż "
        "dla tej, która lubi spędzić godzinę w kuchni.",
        kind=KIND_TEXT,
        placeholder="np. gotuje partnerka; ja mam max 20 minut",
        sensitive=True,
        consent_domain=DOMAIN_NUTRITION,
        profile_field="gw_gotowanie",
        max_len=300,
    ),
    Step(
        id="gw_f3",
        topic="Żywienie pod lupą",
        question="Ile posiłków w tygodniu jesz poza domem (stołówka, miasto, "
        "„coś w biegu”)?",
        why="Plan musi obsłużyć realne jedzenie na mieście — inaczej "
        "rozjeżdża się w pierwszym tygodniu pracy.",
        kind=KIND_CHOICE,
        options=("0–2", "3–5", "6–10", "Ponad 10"),
        sensitive=True,
        consent_domain=DOMAIN_NUTRITION,
        profile_field="gw_poza_domem",
        max_len=20,
    ),
    Step(
        id="gw_f4",
        topic="Żywienie pod lupą",
        question="Produkty, których nie tkniesz — i produkty, bez których "
        "nie wyobrażasz sobie tygodnia?",
        why="Dieta z produktów, których nie lubisz, kończy się w sobotę. "
        "Ulubione produkty to klocki, z których warto budować.",
        kind=KIND_LONGTEXT,
        placeholder="np. nie tknę: ryb, wątróbki; must-have: pieczywo, kawa z mlekiem",
        sensitive=True,
        consent_domain=DOMAIN_NUTRITION,
        profile_field="gw_produkty_preferencje",
        max_len=800,
    ),
    Step(
        id="gw_f5",
        topic="Żywienie pod lupą",
        question="Jak wygląda Twój typowy tydzień z alkoholem i słodyczami? "
        "Bez oceniania — potrzebna jest prawda, nie wersja odświętna.",
        why="Ukryte 2000 kcal tygodniowo z piątkowych spotkań tłumaczy "
        "niejedną „niewyjaśnioną” stagnację. Plan uwzględnia życie, nie "
        "udaje, że go nie ma.",
        kind=KIND_LONGTEXT,
        placeholder="np. 4–6 piw w weekend; czekolada prawie codziennie wieczorem",
        sensitive=True,
        consent_domain=DOMAIN_NUTRITION,
        profile_field="gw_alkohol_slodycze",
        max_len=800,
    ),
    Step(
        id="gw_f6",
        topic="Żywienie pod lupą",
        question="Czy stosowałeś(-aś) wcześniej diety — z internetu albo od "
        "dietetyka? Która dowiozła efekt i co działo się po jej zakończeniu?",
        why="Historia efektu jo-jo pokazuje, jakiego tempa i jakiej "
        "struktury unikać tym razem.",
        kind=KIND_LONGTEXT,
        placeholder="np. keto — 8 kg w dół, po pół roku 10 w górę",
        sensitive=True,
        consent_domain=DOMAIN_NUTRITION,
        profile_field="gw_diety_historia",
        max_len=1000,
    ),
    Step(
        id="gw_f7",
        topic="Żywienie pod lupą",
        question="Ile płynów pijesz dziennie i co to głównie jest?",
        why="Słodzone napoje to najczęstsze „niewidzialne” kalorie, "
        "a nawodnienie wpływa na trening i głód.",
        kind=KIND_TEXT,
        placeholder="np. ~1,5 l — głównie kawa i cola zero",
        sensitive=True,
        consent_domain=DOMAIN_NUTRITION,
        profile_field="gw_nawodnienie",
        max_len=300,
    ),
    # ------------------------------------------------ G · Logistyka tygodnia
    Step(
        id="gw_g1",
        topic="Logistyka tygodnia",
        question="Opisz swój typowy tydzień godzinowo: praca, dojazdy, "
        "obowiązki domowe, opieka nad kimś.",
        why="Plan wpisany w prawdziwy tydzień wykonuje się sam; plan wpisany "
        "w idealny tydzień wymaga heroizmu co środę.",
        kind=KIND_LONGTEXT,
        placeholder="np. pn–pt 7–17 praca z dojazdem; wt/czw odbieram dzieci; nd obiad u rodziców",
        profile_field="gw_tydzien_mapa",
        max_len=1500,
    ),
    Step(
        id="gw_g2",
        topic="Logistyka tygodnia",
        question="Jaki charakter ma Twoja praca?",
        why="Magazynier i programista przy tym samym planie treningowym "
        "potrzebują zupełnie innej diety i regeneracji.",
        kind=KIND_CHOICE,
        options=("Siedząca", "Mieszana", "Fizyczna"),
        profile_field="gw_praca_charakter",
        max_len=20,
    ),
    Step(
        id="gw_g3",
        topic="Logistyka tygodnia",
        question="Jak często wyjeżdżasz (delegacje, weekendy poza domem) "
        "i co wtedy dzieje się z jedzeniem i treningiem?",
        why="Wyjazdy to najczęstszy moment zerwania rytmu — plan awaryjny "
        "„na wyjazd” ustawiamy z góry, nie po fakcie.",
        kind=KIND_TEXT,
        placeholder="np. delegacja co 2 tygodnie; wtedy jem na mieście i nie trenuję",
        profile_field="gw_wyjazdy",
        max_len=400,
    ),
    Step(
        id="gw_g4",
        topic="Logistyka tygodnia",
        question="Który dzień tygodnia jest u Ciebie najbardziej "
        "nieprzewidywalny?",
        why="Tam nie stawiamy najważniejszego treningu tygodnia.",
        kind=KIND_CHOICE,
        options=("Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd", "Żaden — tydzień jest stabilny"),
        profile_field="gw_dzien_nieprzewidywalny",
        max_len=40,
    ),
    # ------------------------------------------------ H · Punkt startu
    Step(
        id="gw_h1",
        topic="Punkt startu",
        question="Pomiary startowe, które chcesz podać: waga, wzrost, "
        "obwody (talia, biodra, klatka, udo, ramię).",
        why="Punkt odniesienia dla trendów. Każdy pomiar jest osobno "
        "dobrowolny — zwłaszcza waga, jeśli wolisz jej nie śledzić. "
        "Regularne pomiary prowadzi się potem na ekranie Postępy.",
        kind=KIND_LONGTEXT,
        placeholder="np. 92 kg, 181 cm, talia 98 cm — reszty nie podaję",
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_pomiary_start",
        max_len=500,
    ),
    Step(
        id="gw_h2",
        topic="Punkt startu",
        question="Po czym POZA wagą chcesz mierzyć postęp?",
        why="Waga to najgorszy pojedynczy miernik — kłamie tygodniami. "
        "Wybieramy 2–3 mierniki, które u Ciebie mają sens.",
        kind=KIND_MULTI,
        options=(
            "Jak leżą ubrania",
            "Siła (ciężary na sztandze)",
            "Kondycja (schody, bieg, tętno)",
            "Samopoczucie i energia",
            "Zdjęcia sylwetki",
            "Obwody",
        ),
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_mierniki",
        max_len=200,
    ),
    Step(
        id="gw_h3",
        topic="Punkt startu",
        question="Czy chcesz robić zdjęcia sylwetki co kilka tygodni?",
        why="Dla wielu osób zdjęcia to najlepszy dowód zmiany — ale tylko "
        "jeśli są komfortowe. Wymagają osobnej zgody (Profil → Prywatność); "
        "EXIF i lokalizacja są usuwane przy zapisie.",
        kind=KIND_BOOL,
        options=("Tak", "Nie"),
        sensitive=True,
        consent_domain=DOMAIN_HEALTH,
        profile_field="gw_zdjecia_chce",
        max_len=20,
    ),
    # ------------------------------------------------ I · Zasady współpracy
    Step(
        id="gw_i1",
        topic="Zasady współpracy",
        question="Czego oczekujesz od trenera — a co bierzesz na siebie?",
        why="Jawny podział odpowiedzialności zapobiega cichym rozczarowaniom "
        "po obu stronach.",
        kind=KIND_LONGTEXT,
        placeholder="np. od trenera: konkretny plan i reakcja na raport; ode mnie: szczerość i 3 treningi",
        profile_field="gw_wspolpraca_podzial",
        max_len=800,
    ),
    Step(
        id="gw_i2",
        topic="Zasady współpracy",
        question="Jak wolisz dostawać uwagi?",
        why="Ta sama uwaga zmotywuje jedną osobę, a zniechęci drugą. "
        "Dopasowujemy formę, nie treść.",
        kind=KIND_CHOICE,
        options=(
            "Krótko i konkretnie",
            "Z pełnym wyjaśnieniem „dlaczego”",
        ),
        profile_field="gw_feedback_forma",
        max_len=60,
    ),
    Step(
        id="gw_i3",
        topic="Zasady współpracy",
        question="Co musiałoby się wydarzyć, żebyś za miesiąc chciał(a) "
        "zrezygnować? Szczerze — to nasza wspólna lista ostrzegawcza.",
        why="Klienci prawie nigdy nie odchodzą bez sygnałów. Nazwane z góry "
        "sygnały widać na czas.",
        kind=KIND_LONGTEXT,
        placeholder="np. brak efektów na wadze przez 3 tygodnie; poczucie, że plan jest z szablonu",
        profile_field="gw_ryzyko_rezygnacji",
        max_len=800,
    ),
    Step(
        id="gw_i4",
        topic="Zasady współpracy",
        question="Kiedy w tygodniu masz najlepszy moment na 10 minut "
        "raportu i odpowiedź na uwagi trenera?",
        why="Raport tygodniowy działa, gdy ma stały, realny slot — nie "
        "„kiedyś w niedzielę”.",
        kind=KIND_TEXT,
        placeholder="np. niedziela po 20:00",
        profile_field="gw_raport_slot",
        max_len=200,
    ),
    Step(
        id="gw_i5",
        topic="Zasady współpracy",
        question="Czy jest coś, o co nie zapytaliśmy, a co Twoim zdaniem "
        "trener powinien wiedzieć?",
        why="Najważniejsze pytanie wywiadu. Zaskakująco często pada tu "
        "rzecz, która zmienia cały plan.",
        kind=KIND_LONGTEXT,
        placeholder="cokolwiek uznasz za ważne",
        profile_field="gw_otwarte",
        scan_safety=True,
        max_len=2000,
    ),
)

DEEP_STEP_BY_ID: dict[str, Step] = {s.id: s for s in DEEP_STEPS}


def _yes(value: str | None) -> bool:
    return (value or "").strip().casefold() == "tak"


def deep_triggered(step_id: str, answers: dict[str, str | None]) -> bool:
    """Reguły odsłaniania kroków warunkowych wywiadu — jawne i serwerowe,
    jak `onboarding_flow._triggered` (pominięcie = None = nie odsłania)."""
    if step_id == "gw_c2_opis":
        return _yes(answers.get("gw_c2"))
    if step_id == "gw_d3_wzor":
        return _yes(answers.get("gw_d3"))
    if step_id == "gw_e2_kiedy":
        return answers.get("gw_e2") in ("Tak", "Czasem")
    return False


def flag_message_for(step_id: str) -> str:
    """Komunikat flagi wyboru dla danego kroku (spokojny, bez oceny)."""
    if step_id == "gw_e3":
        return FLAG_MESSAGE_BODY_RELATION
    return FLAG_MESSAGE_PRESCREEN
