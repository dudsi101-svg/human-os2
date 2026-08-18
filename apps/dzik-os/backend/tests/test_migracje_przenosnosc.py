"""Bramka przenośności migracji: surowy SQL musi działać na SQLite I PostgreSQL.

Dlaczego to jest osobna, statyczna bramka
-----------------------------------------
`run_migrations()` na ŚWIEŻEJ bazie nie wykonuje surowego SQL-a w ogóle:
buduje schemat z metadanych ORM (`Base.metadata.create_all`, dialektowo
poprawnie) i tylko stempluje wersje. Surowe instrukcje z `MIGRATIONS`
uruchamiają się wyłącznie na bazie ISTNIEJĄCEJ.

Skutek: nawet przebieg całego zestawu testów na PostgreSQL nie dotknie tego
SQL-a — pierwsza baza jest zawsze świeża. Błąd dialektu ujawniłby się dopiero
przy pierwszej migracji nakładanej na działającą produkcję, czyli w najgorszym
możliwym momencie.

Audyt 18.08.2026 znalazł tam 16 instrukcji `BOOLEAN … DEFAULT 0`, których
PostgreSQL nie przyjmuje (wymaga `false`, nie liczby). Zostały poprawione;
ten test pilnuje, żeby wzorzec nie wrócił wraz z migracją 21.

Instrukcje są sprawdzane tekstowo, bo tekstowo trafiają do `conn.execute(
text(...))` — bez żadnego tłumaczenia dialektu po drodze.
"""

from __future__ import annotations

import re
import unittest

from dzik_os.db import MIGRATIONS

#: Konstrukcje akceptowane przez SQLite, a odrzucane (albo nieistniejące)
#: w PostgreSQL. Klucz = czytelna nazwa do komunikatu błędu.
NIEPRZENOSNE: dict[str, str] = {
    "literał liczbowy jako wartość domyślna kolumny BOOLEAN "
    "(PostgreSQL wymaga false/true)": r"BOOLEAN[^,\n]*\bDEFAULT\s+[01]\b",
    "AUTOINCREMENT (PostgreSQL: GENERATED … AS IDENTITY)": r"\bAUTOINCREMENT\b",
    "funkcja datetime() z SQLite (PostgreSQL: now()/timestamp)": r"\bdatetime\s*\(",
    "funkcja strftime() z SQLite (PostgreSQL: to_char())": r"\bstrftime\s*\(",
    "INSERT OR IGNORE/REPLACE (PostgreSQL: ON CONFLICT)": r"\bINSERT\s+OR\s+(IGNORE|REPLACE)\b",
    "PRAGMA (nie istnieje w PostgreSQL)": r"\bPRAGMA\b",
    "WITHOUT ROWID (nie istnieje w PostgreSQL)": r"\bWITHOUT\s+ROWID\b",
    "cytowanie backtickami (MySQL/SQLite)": r"`",
}


class TestPrzenosnoscMigracji(unittest.TestCase):
    def test_zadna_migracja_nie_uzywa_skladni_tylko_dla_sqlite(self) -> None:
        naruszenia: list[str] = []
        for wersja, opis, instrukcje in MIGRATIONS:
            for nr, instrukcja in enumerate(instrukcje, start=1):
                for nazwa, wzorzec in NIEPRZENOSNE.items():
                    if re.search(wzorzec, instrukcja, re.IGNORECASE):
                        fragment = " ".join(instrukcja.split())[:120]
                        naruszenia.append(
                            f"  migracja {wersja} ({opis}), instrukcja {nr}: {nazwa}\n"
                            f"    {fragment}"
                        )

        self.assertEqual(
            naruszenia,
            [],
            "Migracje zawierają składnię, której PostgreSQL nie przyjmie. "
            "Ten SQL wykona się na KAŻDEJ istniejącej bazie przy najbliższym "
            "wdrożeniu — a świeża baza go pominie, więc testy tego nie złapią "
            "inaczej niż tutaj:\n" + "\n".join(naruszenia),
        )

    def test_numery_migracji_sa_unikalne_i_rosnace(self) -> None:
        """Kolejność decyduje o wyniku — luka albo duplikat to cicha katastrofa."""
        numery = [wersja for wersja, _, _ in MIGRATIONS]
        self.assertEqual(numery, sorted(numery), "Migracje muszą być posortowane rosnąco")
        self.assertEqual(len(numery), len(set(numery)), "Numery migracji muszą być unikalne")
        self.assertEqual(
            numery,
            list(range(1, len(numery) + 1)),
            "Numery migracji muszą tworzyć ciąg bez luk, zaczynając od 1",
        )


if __name__ == "__main__":
    unittest.main()
