"""Panel trenera (0.58.0): szkice planów, różnice i publikacja zmian.

Moduły:
* `elementy` — stabilne identyfikatory elementów treści planu, normalizacja
  i operacje na szkicu (set/add/delete/move/duplicate/replace);
* `roznice` — porównanie migawki bazowej z treścią szkicu po `id`
  i deterministyczne podsumowanie po polsku (bez LLM);
* `serwis` — cykl życia szkicu, transakcja publikacji (wersja + ChangeSet
  + outbox + ślad Wiedzy + audyt + idempotencja) i procesor outboxu.
"""
