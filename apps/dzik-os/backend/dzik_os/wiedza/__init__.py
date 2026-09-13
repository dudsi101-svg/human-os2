"""Wiedza (0.56.0, P0) — biblioteka edukacyjna powiązana z planem.

Podział odpowiedzialności (pakiet właściciela, plik 03): silnik
treningu i moduł diety pozostają właścicielami zaleceń; ten pakiet
odpowiada za treść ogólną, odczyt zapisanych uzasadnień (ślad
decyzji), powiązania, wyszukiwanie i prezentację. Nic tu nie oblicza
nowej diety ani nie zmienia liczby serii. Bez modelu językowego —
renderer jest deterministyczny.

Moduły:
* `dane`     — treści startowe (szkice), schematy Draft 2020-12, źródła;
* `tresci`   — repozytorium kart, powiązania, import, publikacja;
* `slad`     — niezmienny ślad decyzji (DecisionTrace) i jego zapis
               przez właścicieli decyzji;
* `reguly`   — rejestr reguł: wymagane fakty, kontrole spójności,
               szablony tekstu po polsku;
* `resolver` — 10 kroków wyjaśnienia i statusy odpowiedzi;
* `kanal`    — ranking „Dla Ciebie” bez uczenia maszynowego;
* `szukaj`   — wyszukiwanie po opublikowanych tekstach.
"""
