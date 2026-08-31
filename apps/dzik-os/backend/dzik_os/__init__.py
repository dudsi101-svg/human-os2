"""Dzik OS — Panel Podopiecznego.

Aplikacja domenowa dla trenera personalnego "Lubelski Dzik", zbudowana na
fundamentach Human OS (hos_engine): hash-chained Event Store, rejestr zgód
(ConsentRegistry), konwencje identyfikatorów i pokwitowania (receipts).

Granica architektoniczna: UI -> Request -> Core/Policy -> Result/Receipt -> UI.
Frontend nigdy nie podejmuje decyzji bezpieczeństwa — wszystkie reguły
uprawnień i zgód egzekwuje ten backend.
"""

__version__ = "0.54.2"
