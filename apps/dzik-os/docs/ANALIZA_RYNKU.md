# Analiza rynku aplikacji trenerskich — sierpień 2026

Pełny raport z researchu webowego (metoda: strony produktowe, porównania
PTPioneer/Coachway/PromealPlan, agregatory recenzji Capterra/G2, polskie
źródła branżowe). Wersja skrócona z rekomendacjami dla Dzik OS: artefakt
„Przegląd rozwiązań trenerskich" + sekcja „Filtr Human OS" poniżej.

## A. Aplikacja → wyróżniki

- **ABC Trainerize** — automatyzacje per klient (onboarding, re-engagement),
  habit coaching z gamifikacją, najszersze wearables (Garmin/WHOOP/Oura),
  Smart Meal Planner (~45 USD/mies.), Trainerize Pay (Stripe, auto-retry),
  AI Workout Builder na danych klienta.
- **TrueCoach** — najszybszy builder programów, wideo-feedback techniki
  przypięty do ćwiczenia (slow-motion), 850+ wideo, wearables; braki:
  nutrition, habit tracking, automatyczne dostarczanie bloków.
- **Everfit** — Autoflow (~29 USD/mies., sekwencje automatyczne), AI parser
  rozpisek tekst/PDF → klikalny plan, pełny moduł żywieniowy z foto-logiem,
  fora/challenge z leaderboardami, white-label z własnym listingiem w App
  Store, komentarze przy ćwiczeniu z historią.
- **PT Distinction** — własne testy/assessmenty (najmocniejsza diagnostyka),
  głębokie automatyzacje e-mail/SMS/in-app, brandowana aplikacja w cenie,
  coaching grupowy, brak tierów funkcji.
- **CoachRx (OPEX)** — RxBot: AI programujący z danych klienta (assessmenty,
  historia, sprzęt) i uzasadniający decyzje; Lifestyle Rx (sen/stres/nawyki);
  RPE jako biofeedback progresji; foto check-iny żywieniowe ze streakami.
- **Hevy Coach** — klient zna interfejs z konsumenckiego Hevy; logowanie
  sesji stacjonarnej przez trenera; dziennik siłowy (e1RM, objętość, PR-y);
  wąska specjalizacja siłowa, mało automatyzacji.

## B. Najciekawsze mechanizmy (15)

1. Asynchroniczny wideo-feedback techniki przypięty do ćwiczenia (TrueCoach).
2. Ustrukturyzowany check-in z auto-trendami (przegląd klienta 15 → 2–3 min).
3. AI-podsumowania check-inów z draftem odpowiedzi do zatwierdzenia
   (deklarowane ~80% mniej administracji przy 30–50 klientach).
4. Automatyczne sekwencje onboardingu i re-engagement nudges.
5. Habit coaching ze streakami i odznakami (codzienny punkt styku =
   najsilniejszy korelat retencji).
6. Import rozpiski tekst/PDF → trackowalny plan (Everfit).
7. AI-programowanie na danych klienta, nie pustym promptcie (RxBot) —
   zawsze „coach in the loop".
8. Wearables jako wejście do decyzji (alerty na anomalie snu/HRV).
9. Custom assessmenty okresowe z wykresami (PT Distinction).
10. Foto-log posiłków zamiast liczenia makro (niższa bariera = adherence).
11. Społeczności: prywatne grupy, challenge, leaderboardy.
12. White-label z własnym listingiem w sklepach.
13. Płatności wbudowane z auto-retry (przeciw „cichemu churnowi").
14. Logowanie sesji stacjonarnej przez trenera (model hybrydowy, Hevy Coach).
15. Komentarze/cue przypięte do ćwiczenia z pełną historią.

## C. Trendy 2025/2026

- AI jako warstwa robocza: podsumowania, drafty, generatory — „coach in the
  loop", nie autonomia.
- Coaching hybrydowy (sala + aplikacja) jako model domyślny.
- Wearables głębiej: alerty i korekty treningu; kierunek „longevity".
- Automatyzacja pełnego cyklu: onboarding → płatności → retencja.

## D. Polski rynek

- **BLIK jest standardem**: WodGuru→Autopay (~1,2%), Fitssey→Przelewy24
  (~1,9%), eFitness→Przelewy24. Stripe nie obsługuje BLIK w tym kontekście —
  przewaga lokalnych narzędzi.
- Segment zarządzania klubem (WodGuru 3000+ klubów, Fitssey, eFitness,
  Klubownik) vs. prowadzenie podopiecznych (CoachGuru — 1200+ wideo, Fitebo,
  Fitsy, CoachPRO, TreningLab, trainer-app — PWA, hosting UE).
- Ceny współprac online: typowo 250–350 zł/mies.; budżet ~100–150 zł,
  premium 800–1000 zł. Typowy pakiet: nowy plan co 4 tyg. + cotygodniowy
  raport (ankieta + wideo bojów głównych).
- Duża część trenerów pracuje na Excel/Google Forms/Messenger.
- „Harder" w PL = aplikacja członkowska sieci klubów (Perfect Gym), nie
  narzędzie coachingowe.

Chwalone: szybkość programowania (TrueCoach), prostota dla klienta (Hevy),
appka kliencka (Everfit), kompletność bez dopłat (PT Distinction ~4,9).
Krytykowane: Trainerize — ociężały interfejs trenera; TrueCoach — brak
nutrition/habitów, koszt rośnie z liczbą klientów; Everfit — niespójna baza
ćwiczeń; ogólnie — drożejące dodatki.

## E. Filtr Human OS dla Dzik OS

Konstytucja Human OS: zakaz optymalizacji pod zaangażowanie; anty-metryki
(czas w aplikacji, liczba powiadomień, **długość streaka**) nie mogą
definiować sukcesu; zakaz rankingowania „wartości" ludzi.

- **TAK**: wideo-feedback przy ćwiczeniu; cue przy ćwiczeniu; trendy przy
  raporcie; własne assessmenty; foto-log posiłków; import rozpisek;
  logowanie sesji przez trenera; BLIK.
- **ADAPTACJA**: nawyki bez streaków-presji/odznak (licznik tygodniowy,
  brak kary za przerwę); przypomnienia jako konfigurowalna usługa, nie
  re-engagement; AI-podsumowania tylko jako oznaczona propozycja za osobną
  zgodą.
- **NIE**: leaderboardy porównujące klientów; gamifikacja odznakami;
  automaty „dawno Cię nie było"; scoring klienta jednym wynikiem.

Proponowana kolejność: (1) cue przy ćwiczeniu, mini-trendy przy raporcie,
foto-log posiłków; (2) przegląd wideo w panelu trenera, nawyki w wersji
Human OS, logowanie sesji stacjonarnej; (3) BLIK, assessmenty, import
rozpisek; (później) AI-podsumowania, wearables, white-label.

## F. Źródła

Globalni: trainerize.com/features, trainerize.com/blog (roadmap 2026, AI),
truecoach.co/features (video-exercise-library, wearables), everfit.io
(automation, task-habit, nutrition, help.everfit.io — Autoflow, AI Workout
Builder, leaderboards), ptdistinction.com/features, coachrx.app (overview,
lifestylerx, rxbot), hevycoach.com; porównania: ptpioneer.com, coachway.io,
coachbox.app, promealplan.com, quickcoach.fit; recenzje: capterra.com,
softwareadvice.com. Trendy: mypthub.net, coach360news.com, blog.trainero.com,
anhco.org. Check-iny: hubfit.com/blog. Polska: wod.guru/pl, fitssey.com,
efitness.pl, klubownik.pl, coachguru.app, fitebo.com, trainerapp.pl,
systemtreningowy.pl, treninglab.pl, trenerhub.pl; ceny: lukaszpilat.pl,
oferteo.pl, arf.edu.pl, healthandfitness.pl.
