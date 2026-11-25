# Wdrożenie na Microsoft Fabric: skrypty

Skrypty używają publicznego REST API Fabric, OneLake, API Kusto i Power BI. Tokeny pobierają przez
`az account get-access-token` (zasoby: `https://api.fabric.microsoft.com`, `https://storage.azure.com`,
`https://kusto.kusto.windows.net`, `https://analysis.windows.net/powerbi/api`). Wymagany jest `az login`
na koncie z prawem tworzenia workspace i pojemność Fabric (F SKU lub trial).

Identyfikatory elementów zapisują się w `..\.fabric\deployment.json`, który czytają kolejne skrypty,
więc kolejność ma znaczenie. Plik jest poza repozytorium.

## Kolejność

```powershell
cd ol-szkoly-bezpieczenstwo
$env:PYTHONIOENCODING = 'utf-8'
pwsh   deploy\ensure_capacity.ps1 -CapacityName <capacity-name> -ResourceGroup <resource-group>
pwsh   deploy\01_create_workspace.ps1 -CapacityId <CAPACITY_ID>
pwsh   deploy\02_upload_data.ps1
python deploy\03_deploy_notebooks.py --run-all
python deploy\04_deploy_kql.py
python deploy\05_load_eventhouse.py
python deploy\06_semantic_model.py
python deploy\07_verify_model.py
python deploy\08_verify_kql.py
python deploy\09_realtime_dashboard.py
python deploy\10_report.py
python deploy\11_verify_report.py
python deploy\12_eventstream.py
python deploy\13_verify_eventstream.py
python deploy\14_activator.py
python deploy\15_verify_activator.py
python deploy\16_data_agent.py
```

`run_notebooks.py` uruchamia wskazane notebooki osobno, np. `python deploy\run_notebooks.py 02_campaign_detection`.
Po `--run-all` warto jeszcze raz uruchomić `00_ingest_to_delta`, żeby wyniki z `derived` trafiły do tabel Delta.

## Weryfikacja

| Skrypt | Co sprawdza |
|---|---|
| `07_verify_model.py` | 12 miar DAX względem liczenia lokalnego i pliku z OneLake |
| `08_verify_kql.py` | 14 kafli dashboardu i 8 funkcji, razem 22 zapytania |
| `11_verify_report.py` | odwołania wizualizacji raportu do modelu |
| `13_verify_eventstream.py` | wysyła po 5 zdarzeń na strumień i sprawdza tabele, potem sprząta |
| `15_verify_activator.py` | spójność 5 reguł Activatora z zapytaniami KQL |

## Uwagi

Skrypt 13 wymaga pakietu `azure-eventhub`. Klucz do symulatora: `python deploy\12_eventstream.py --keys`,
a potem `EVENTHUB_CONNECTION_STRING` i `EVENTHUB_NAME` w `.env` albo plik `config.json` według `config.example.json`.

Data Agent zapisuje się jako wersja robocza, publikacja wymaga kliknięcia w portalu.
Aplikacja Fabric (`fabric-app\pulpit-szkol`) jest wdrażana osobno i nie należy do tej sekwencji.
