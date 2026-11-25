# Wdrożenie w Microsoft Fabric

Kroki są zautomatyzowane skryptami z `deploy\` (opis w `deploy\README.md`). Wymagana jest pojemność Fabric
(F SKU lub trial) i konto z prawem tworzenia workspace.

Referencyjne wdrożenie:

| Element | Nazwa |
|---|---|
| Workspace | `OL-ZK-Demo-Szkoly` |
| Lakehouse | `lh_school_safety` |
| Eventhouse i baza KQL | `eh_school_realtime`, `SchoolSafety` |
| Eventstream | `es_school_reports` |
| Notebooki | `00_ingest_to_delta`, `01_priority_scoring` do `05_whatif` |
| Model semantyczny | `sm_school_safety` (DirectLake) |
| Raport | `rpt_zagrozenia_szkolne` |
| Real-Time Dashboard | `Krajowy obraz zagrozen szkolnych` |
| Activator | `act_fala_zagrozen_szkolnych` |
| Data Agent | `agent_zagrozenia_szkolne` |
| Fabric App | `pulpit-szkol` (wdrożona osobno, nie wdrażać ponownie) |

Identyfikatory trafiają do `.fabric\deployment.json`, który nie jest w repozytorium.

## 0. Dane lokalnie

```powershell
pip install -r requirements.txt
python generate_datasets.py
```

Generator jest deterministyczny (seed=42). Liczności zapisuje do `datasets\derived\dataset_counts.json`.

## 1. Logowanie

```powershell
az login --tenant <tenant>
```

Skrypty pobierają tokeny przez `az account get-access-token` dla zasobów Fabric, OneLake (storage),
Kusto i Power BI. Poświadczeń nie zapisujemy w plikach.

## 2. Workspace i pojemność

`deploy\ensure_capacity.ps1` sprawdza, czy pojemność działa, a `deploy\01_create_workspace.ps1`
tworzy workspace i przypina go do pojemności.

## 3. Lakehouse i dane

`deploy\02_upload_data.ps1` wysyła pliki do OneLake. `deploy\03_deploy_notebooks.py` wgrywa notebooki, a
`deploy\run_notebooks.py` uruchamia je (najpierw ingest do Delta, potem 01 do 05, potem ingest ponownie,
żeby wyniki analityczne trafiły do tabel).

## 4. Eventhouse

`deploy\04_deploy_kql.py` stosuje `kql\01_create_tables.kql` i `kql\02_functions.kql`, `deploy\05_load_eventhouse.py`
ładuje dane wsadowo. Weryfikacja: `deploy\08_verify_kql.py` (22 z 22 zapytań).

## 5. Eventstream

`deploy\12_eventstream.py` wdraża topologię (jedno źródło, pięć filtrów, pięć tabel). Klucz do symulatora:
`python deploy\12_eventstream.py --keys`, a test: `python deploy\13_verify_eventstream.py`. Test wysyła po
5 zdarzeń na strumień z datą 2030-01-01 i po sprawdzeniu usuwa je. Wymaga pakietu `azure-eventhub`.

Eventstream dopisuje zdarzenia do tabel, więc wysyłanie strumieniem danych już załadowanych wsadowo
tworzy duplikaty. Do demo na żywo użyj zakresu `--from` i `--to` spoza załadowanych danych albo
wyczyść tabele i załaduj ponownie.

## 6. Model semantyczny, raport, dashboard

`deploy\06_semantic_model.py` tworzy model DirectLake i wykonuje refresh (framing), bez którego tabele
nie są rozpoznane. `deploy\07_verify_model.py` porównuje miary DAX z liczeniem lokalnym. `deploy\10_report.py`
tworzy raport (4 strony), `deploy\11_verify_report.py` sprawdza odwołania. `deploy\09_realtime_dashboard.py`
tworzy dashboard (14 kafli, 2 strony).

## 7. Activator

`deploy\14_activator.py` tworzy 5 reguł. Odbiorcą alertów jest konto, na którym wykonano wdrożenie.
`deploy\15_verify_activator.py` sprawdza spójność.

## 8. Data Agent

`deploy\16_data_agent.py` składa instrukcję systemową z `ai\DATA_AGENT.md` i podpina trzy źródła.
Agent jest zapisany jako wersja robocza. Publikacja wymaga kliknięcia w portalu Fabric.

## 9. Fabric App

Aplikacja jest już wdrożona z katalogu `fabric-app\pulpit-szkol` (patrz `fabric-app\APP_SPEC.md`).
Czyta migawkę `datasets\`, a nie Lakehouse.

## Znane pułapki

Po aktualizacji modelu i ingeście trzeba zrobić refresh DirectLake. Nazwa zmiennej DAX nie może
być nazwą funkcji (`Min`). Nazwy węzłów Eventstream mogą zawierać tylko litery, cyfry i podkreślenie.
Przy pierwszym wdrożeniu Eventstream wszystkie destynacje przeszły w stan `Failed` z błędem usługi
Event Hub, a ponowne uruchomienie `deploy\12_eventstream.py` je naprawiło.

