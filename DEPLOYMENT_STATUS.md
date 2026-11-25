# Stan wdrożenia

Identyfikatory elementów i adres aplikacji z wdrożenia demonstracyjnego zastąpiono placeholderami.

Opis rzeczywistego stanu na pojemności Fabric `<capacity-name>`. Wszystko, co niżej oznaczono jako sprawdzone,
zostało uruchomione i dało podany wynik. Czego nie wykonano albo nie sprawdzono, jest wprost wymienione.

## Elementy Fabric

| Element | Nazwa | Identyfikator | Weryfikacja |
|---|---|---|---|
| Workspace | `OL-ZK-Demo-Szkoly` | <WORKSPACE_ID> | utworzony, przypięty do `<capacity-name>` |
| Lakehouse | `lh_school_safety` | <LAKEHOUSE_ID> | 52 tabele Delta po ingeście i po notebookach |
| Eventhouse | `eh_school_realtime` | <EVENTHOUSE_ID> | tabele i funkcje utworzone |
| Baza KQL | `SchoolSafety` | <KQL_DATABASE_ID> | `08_verify_kql.py`: 22 z 22 zapytań (14 kafli, 8 funkcji) |
| Eventstream | `es_school_reports` | <EVENTSTREAM_ID> | `13_verify_eventstream.py`: po 5 zdarzeń na strumień dotarło do 5 tabel, testowe usunięte |
| Notebooki | `00_ingest_to_delta`, `01_priority_scoring`, `02_campaign_detection`, `03_kizs_escalation`, `04_resource_allocation`, `05_whatif` | w workspace | wszystkie uruchomione do końca |
| Model semantyczny | `sm_school_safety` | <SEMANTIC_MODEL_ID> | 27 tabel, 18 relacji, 33 miary; `07_verify_model.py`: 12 z 12 miar zgodnych |
| Raport | `rpt_zagrozenia_szkolne` | <REPORT_ID> | 4 strony, 45 wizualizacji; `11_verify_report.py`: 42 z 42 odwołań |
| Real-Time Dashboard | `Krajowy obraz zagrozen szkolnych` | <DASHBOARD_ID> | 14 kafli, 2 strony, 2 parametry |
| Activator | `act_fala_zagrozen_szkolnych` | <ACTIVATOR_ID> | 5 reguł; `15_verify_activator.py` spójny |
| Data Agent | `agent_zagrozenia_szkolne` | <DATA_AGENT_ID> | wersja robocza, odczyt zwrotny: 3 źródła |

## Przebieg i napotkane problemy

Pierwsze uruchomienie notebooka 01 zakończyło się błędem sesji (`System_Cancelled_Session_Statements_Failed`),
ponowne przeszło. Model DirectLake wymagał refresh po zmianie definicji, relacja zgłoszeń do województwa
została usunięta jako niejednoznaczna, a zmienna DAX `Min` kolidowała z funkcją i dawała pusty wynik.
Przy pierwszym wdrożeniu Eventstream wszystkie pięć destynacji przeszło w stan `Failed` (błąd usługi
Event Hub po stronie Fabric). Ponowne uruchomienie `12_eventstream.py` je naprawiło, test przeszedł.

## Liczby z Fabric (Spark) a lokalne

Notebooki 01, 03, 04 dały w Fabric te same metryki co lokalnie. Notebook 02 dał inną liczbę komponentów
(70 zamiast 115), stąd różnice, które widać w modelu. Wnioski są takie same.

| Wartość | Lokalnie (seed=42) | Fabric |
|---|---|---|
| zgłoszenia w kampanii | 2216 | 2128 |
| zgłoszenia dla człowieka | 2344 | 2432 |
| recall kampanii | 0,9034 | 0,8675 |
| F1 kampanii | 0,9492 | 0,9291 |
| realne krytyczne zachowane (z 16) | 16 | 16 |
| BS-4826 w wariancie A4 (min) | 3,7 | 4,5 |
| maks. opóźnienie realnych w wariancie A4 (min) | 7,3 | 8,2 |

Dokumenty merytoryczne podają wartości lokalne, bo są powtarzalne bez Fabric.

## Zapytania w Eventhouse (czas 2026-10-09 07:00 UTC)

`ReportsAt`: zamknięte 1125, przekazane 768, w analizie 7. `OpenReports` (12 h) 840. `CriticalWithoutDecision` 1.
`HotlineOverload` 7 województw. `EscalationState`: kampania 1390 zgłoszeń w 16 województwach, 16 realnych krytycznych,
10 województw z przeciążonym 112, 86 zdarzeń Z18, rekomendacja RZZK. Liczby w Eventhouse różnią się od tabel Delta,
bo to inne okno czasu i logika zapytania (liczy się napływ do 07:00 UTC).

## Czego nie wykonano lub wymaga człowieka

Data Agent nie jest opublikowany, publikacja wymaga kliknięcia w portalu. Nie oceniono wizualnie raportu ani
Real-Time Dashboard w przeglądarce. Nie sprawdzono, że alerty Activatora docierają do odbiorcy. Nie skonfigurowano
RLS ani etykiet Purview. Nie zbudowano zapisu zwrotnego do Dataverse. Eventstream dopisuje zdarzenia do tabel,
więc strumieniowe odtwarzanie danych już załadowanych wsadowo tworzy duplikaty. Test Eventstream używał zdarzeń z datą
2030-01-01 i je usunął.
## Fabric App

| Element | Wartość |
|---|---|
| Aplikacja | Pulpit krajowy szkół (Rayfin, `fabric-app\pulpit-szkol\`) |
| Adres | `<APP_URL>` |
| Workspace | `OL-ZK-Demo-Szkoly` (`<WORKSPACE_ID>`) |
| Element Rayfin | `pulpit-szkol` (`<APP_BACKEND_ID>`) |
| Sprawdzono | `GET /` 200, `GET /data/scene.json` 200, `GET /data/reports.json` 200, 30 testów vitest, build, eslint bez błędów, audyt kontrastu 0 par poniżej 4,5:1 |
| Nie sprawdzono | Logowanie brokerem Fabric i zapis od końca do końca (wymagają sesji w portalu), ocena wizualna |
| Ograniczenie | Dane z migawki plików `datasets\`, bez odczytu na żywo z Lakehouse i Eventhouse. Szczegóły w `fabric-app\pulpit-szkol\README.md` |

