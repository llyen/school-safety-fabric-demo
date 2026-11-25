# Real-Time Dashboard

Element `Krajowy obraz zagrozen szkolnych` tworzy `deploy\09_realtime_dashboard.py` na bazie KQL `SchoolSafety`.
Ma 2 strony, 14 kafli i 2 parametry. Zapytania kafli są w `kql\03_dashboard_queries.kql`, a każda linia
`// --- KAFEL n: tytuł` otwiera kafel.

| Kafel | Treść |
|---|---|
| 1 | wskaźniki krajowe |
| 2 | mapa otwartych zgłoszeń, kolor to priorytet |
| 3 | kolejka dyżurnego |
| 4 | tempo napływu zgłoszeń (30 min) |
| 5 | anomalie napływu według województwa (`series_decompose_anomalies`) |
| 6 | kandydaci na kampanie (klastry) |
| 7 | obciążenie 112 według województwa |
| 8 | obciążenie 112 w czasie |
| 9 | kampanie w mediach społecznościowych |
| 10 | czas do decyzji i przekazania |
| 11 | rekomendacja eskalacji |
| 12 | Krajowy Indeks Zagrożenia Szkolnego (godzinowy) |
| 13 | zdarzenia Z18 (odbieranie dzieci, blokady) |
| 14 | krytyczne bez decyzji powyżej 10 min |

Parametry: zakres czasu (`_startTime`, `_endTime`) i województwo (wielokrotny wybór).

Weryfikacja: `deploy\08_verify_kql.py` wykonał 22 z 22 zapytań (14 kafli i 8 funkcji). Wyglądu dashboardu
w przeglądarce nie oceniano.
