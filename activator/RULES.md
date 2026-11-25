# Reguły Activatora

Element `act_fala_zagrozen_szkolnych` ma 5 reguł. Każda wykonuje zapytanie KQL co 300 sekund na bazie
`SchoolSafety` (funkcje `ActivatorR1Inflow` do `ActivatorR5Escalation` z `activator\queries.kql`) i odpala
się, gdy zapytanie zwróci wiersz (kolumna techniczna `alert` większa od zera). Odbiorcą alertu jest konto,
na którym wykonano wdrożenie. Zapytania przyjmują parametr `at`, a bez niego liczą względem bieżącego
czasu scenariusza.

| Reguła | Warunek | Funkcje pomocnicze |
|---|---|---|
| R1 skok napływu zgłoszeń | anomalia napływu w województwie w oknie 12 h, krok 30 min, próg 2,0, ostatnie 90 min, co najmniej 15 zgłoszeń | `InflowAnomalies` |
| R2 wykryto klaster kampanii | klaster z co najmniej 20 zgłoszeniami i 8 powiatami, udział automatów co najmniej 0,3 albo 5 powtórzonych tokenów | `ClusterCandidates` |
| R3 krytyczne bez decyzji | zgłoszenie z sugestią KRYTYCZNY bez decyzji dyżurnego dłużej niż 10 min | `CriticalWithoutDecision` |
| R4 przeciążenie 112 | obciążenie 112 powyżej 1,5 w oknie 30 min | `HotlineOverload` |
| R5 kryterium eskalacji do RZZK | `EscalationState` zwraca rekomendację RZZK | `EscalationState` |

## Wyniki sprawdzone na czasie szczytu (2026-10-09 06:00 UTC)

Liczba wierszy zwracanych przez reguły: R1 1, R2 13, R3 1, R4 7, R5 1. Spójność reguł z zapytaniami potwierdza
`deploy\15_verify_activator.py`.

## Czego nie sprawdzono

Nie zweryfikowano w portalu, że alerty faktycznie docierają do skrzynki lub Teams, ani że reguły zostały
uruchomione (stan "Running") po utworzeniu elementu. Zapis `15_verify_activator.py` dotyczy definicji, a nie dostarczenia powiadomienia.

Reguły R1 do R5 to propozycje do zatwierdzenia przez człowieka, nie automatyczna eskalacja.
