"""Dowód, że łańcuch audytu WYKRYWA manipulację — nie tylko że jest spójny.

Dlaczego osobny plik
--------------------
W kilku miejscach testy sprawdzały `verify_audit_chain() is True`. To dowodzi,
że łańcuch nie psuje się sam — ale nie dowodzi, że cokolwiek chroni. Detektor,
którego nigdy nie zmuszono do zapalenia się na czerwono, może być zwykłym
`return True` i żaden z tamtych testów by tego nie zauważył.

Tutaj baza zdarzeń jest modyfikowana Z POMINIĘCIEM aplikacji (bezpośredni
SQL), w dwóch wariantach odpowiadających realnemu zagrożeniu:

1. ktoś podmienia treść zdarzenia w bazie (np. przez dostęp do wolumenu),
2. ktoś zna schemat i przelicza `event_hash` podmienionego zdarzenia.

Wariant 2. jest istotniejszy: chroni przed nim dopiero DOWIĄZANIE do przodu
(`previous_hash` następnego zdarzenia), a nie sam hash pojedynczego wpisu.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3

from hos_engine.protocol_security import canonical_json


def _events_db(store) -> str:
    return str(store.path)


def test_podmiana_tresci_zdarzenia_jest_wykrywana(seeded):
    """Zmiana payloadu bez ruszania hashy — łańcuch musi pęknąć."""
    from dzik_os.hos_bridge import event_store, verify_audit_chain

    assert verify_audit_chain() is True, "przed manipulacją łańcuch ma być spójny"

    conn = sqlite3.connect(_events_db(event_store()))
    total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert total > 2, "potrzeba kilku zdarzeń, żeby test cokolwiek znaczył"
    seq = conn.execute(
        "SELECT sequence FROM events ORDER BY sequence LIMIT 1 OFFSET ?",
        (total // 2,),
    ).fetchone()[0]
    conn.execute(
        "UPDATE events SET payload = ? WHERE sequence = ?",
        ('{"zmanipulowane": true}', seq),
    )
    conn.commit()
    conn.close()

    assert verify_audit_chain() is False, (
        "manipulacja niewykryta — łańcuch audytu nie chroni niczego"
    )


def test_podmiana_z_przeliczonym_hashem_tez_jest_wykrywana(seeded):
    """Atakujący zna schemat i poprawia `event_hash` zmienionego zdarzenia.

    Łapie to dopiero `previous_hash` NASTĘPNEGO zdarzenia, które nadal wskazuje
    starą wartość. Bez tego dowiązania hash pojedynczego wpisu byłby ozdobą.
    """
    from dzik_os.hos_bridge import event_store, verify_audit_chain

    assert verify_audit_chain() is True

    conn = sqlite3.connect(_events_db(event_store()))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM events ORDER BY sequence").fetchall()
    assert len(rows) > 2
    target = rows[len(rows) // 2]
    payload = {"zmanipulowane": True}

    # Odtwarzamy DOKŁADNIE materiał, który liczy verify_chain (klucz "id",
    # odkodowane subject_ids/payload, immutable=True), czyli działamy jak
    # atakujący znający implementację — nie jak ktoś zgadujący format.
    material = {
        "id": target["event_id"],
        "event_type": target["event_type"],
        "occurred_at": target["occurred_at"],
        "actor_id": target["actor_id"],
        "subject_ids": json.loads(target["subject_ids"])["values"],
        "payload": payload,
        "correlation_id": target["correlation_id"],
        "immutable": True,
        "previous_hash": target["previous_hash"],
    }
    if target["causation_id"] is not None:
        material["causation_id"] = target["causation_id"]
    forged = hashlib.sha256(canonical_json(material)).hexdigest()
    conn.execute(
        "UPDATE events SET payload = ?, event_hash = ? WHERE sequence = ?",
        (json.dumps(payload), forged, target["sequence"]),
    )
    conn.commit()
    conn.close()

    assert verify_audit_chain() is False, (
        "podmiana z przeliczonym hashem niewykryta — brak dowiązania do przodu"
    )
