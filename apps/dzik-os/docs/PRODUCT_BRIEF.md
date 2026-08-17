# Product Brief — Dzik OS (Panel Podopiecznego)

Data: 2026-08-17 · Wersja: 1.0 · Status: zrealizowane w MVP

## Problem

Internetowy trener personalny („Lubelski Dzik") prowadzi podopiecznych
przez rozproszone narzędzia: WhatsApp, arkusze, PDF-y, e-maile. Klient nie
ma jednego miejsca, w którym widzi swój plan, dietę, raporty i płatności;
trener nie ma jednego miejsca, w którym widzi stan wszystkich podopiecznych.

## Rozwiązanie

Prosty **agregat wymiany informacji trener ↔ podopieczny** jako
instalowalna PWA (telefon + komputer), zbudowany na fundamentach Human OS:
własność danych, zgody, wersjonowanie, proweniencja, audyt, kontrola
człowieka.

**Nie budujemy**: platformy fitness, sieci społecznościowej ani
AI-coacha. Klient przekazuje dane i wykonuje plan; decyzje podejmuje trener.

## Role

* **COACH** — tworzy i wersjonuje plany (trening/dieta), harmonogram,
  odpowiada na raporty i wiadomości, zarządza terminami płatności.
* **CLIENT** — widzi wyłącznie własne dane; wykonuje plan, raportuje,
  mierzy się, wysyła zdjęcia i wiadomości; kontroluje zgody, eksport
  i usunięcie danych.
* **ADMIN** — rola techniczna bez dostępu do danych zdrowotnych;
  działania audytowane.

## Najważniejsze przepływy

1. Trener zakłada klienta → przypisuje plan v1 + dietę + harmonogram + pakiet płatności.
2. Klient loguje się → ekran „Dzisiaj" → wykonuje trening („Wykonane ✓" / wyniki).
3. Klient wysyła raport tygodniowy (masa, skale 1–5, zdjęcia, pytania).
4. Trener odpowiada na raport i tworzy **nową wersję** planu z powodem zmiany;
   poprzednia wersja zostaje w historii.
5. Płatności: trener ustawia termin, klient widzi status, trener oznacza wpłatę.
6. Wszystkie istotne operacje trafiają do łańcucha audytu z pokwitowaniami.

## Wyróżniki (z Konstytucji Human OS)

* historia bez cichego nadpisywania — każda wersja planu i każda poprawka
  raportu zostaje;
* każde pole profilu ma źródło, autora, datę, wersję i cel;
* zgoda jest cofalna w aplikacji i działa natychmiast (decyzja w Core);
* brak oceny „wartości" klienta — wyłącznie obiektywne flagi operacyjne;
* aplikacja przechowuje harmonogram suplementacji wyłącznie jako plan
  wprowadzony przez człowieka, z zapisanym autorem — nigdy nie dobiera dawek.

## Poza zakresem MVP

Patrz [DEFERRED_FEATURES.md](DEFERRED_FEATURES.md).
