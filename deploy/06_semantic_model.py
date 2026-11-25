"""Model semantyczny DirectLake nad lh_school_safety (tabele logiczne FactReport, DimSchool itd.)."""
from __future__ import annotations

import base64
import json
import subprocess
import time
import uuid
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".fabric" / "deployment.json"
STATE = json.loads(STATE_PATH.read_text(encoding="utf-8"))
WS, LH = STATE["workspaceId"], STATE["lakehouseId"]
API = "https://api.fabric.microsoft.com/v1"
MODEL_NAME = "sm_school_safety"

SCHEMAS = json.loads((ROOT / ".fabric" / "schemas.json").read_text(encoding="utf-8"))

TYPE_MAP = {
    "string": "string", "boolean": "boolean", "date": "dateTime", "timestamp": "dateTime",
    "int": "int64", "bigint": "int64", "smallint": "int64", "tinyint": "int64",
    "double": "double", "float": "double",
}

# nazwa w modelu -> tabela Delta
TABLES = {
    "DimVoivodeship": "dim_voivodeship",
    "DimCounty": "dim_county",
    "DimSchool": "dim_school",
    "DimCategory": "dim_report_category",
    "DimPriority": "dim_priority",
    "DimStatus": "dim_status",
    "DimRecipient": "dim_recipient",
    "DimHazard": "dim_hazard",
    "FactReport": "fact_report",
    "FactReportStatus": "fact_report_status",
    "FactHandoff": "fact_report_handoff",
    "FactHotline": "fact_hotline_load",
    "FactSocial": "fact_social_signal",
    "FactDisorder": "fact_disorder_event",
    "FactPatrol": "fact_police_patrol",
    "FactSupport": "fact_support_capacity",
    "FactTask": "fact_task_activation",
    "FactReadiness": "fact_readiness_declaration",
    "FactEscalation": "fact_escalation_event",
    "FactCampaignFlag": "campaign_report_flags",
    "FactCampaignCluster": "campaign_clusters",
    "FactKizsVoivodeship": "kizs_voivodeship_hourly",
    "FactKizsNational": "kizs_national_hourly",
    "FactKizsCounty": "kizs_county_daily",
    "FactWhatIf": "whatif_queue_variants",
    "FactSpo3Timing": "whatif_spo3_message_timing",
    "FactPatrolDaily": "resources_patrol_daily",
}

RELATIONSHIPS = [
    # (fromTable, fromColumn, toTable, toColumn, isActive, bothDirections)
    ("FactReport", "school_id", "DimSchool", "school_id", True, False),
    ("FactReport", "category_code", "DimCategory", "category_code", True, False),
    ("FactReport", "ai_priority_code", "DimPriority", "priority_code", True, False),
    ("FactReportStatus", "report_id", "FactReport", "report_id", True, False),
    ("FactReportStatus", "duty_priority_code", "DimPriority", "priority_code", False, False),
    ("FactReportStatus", "status_code", "DimStatus", "status_code", True, False),
    ("FactCampaignFlag", "report_id", "FactReport", "report_id", True, False),
    ("FactHandoff", "report_id", "FactReport", "report_id", True, False),
    ("FactHandoff", "recipient_code", "DimRecipient", "recipient_code", True, False),
    ("FactHotline", "voivodeship_code", "DimVoivodeship", "voivodeship_code", True, False),
    ("FactDisorder", "voivodeship_code", "DimVoivodeship", "voivodeship_code", True, False),
    ("FactPatrol", "county_code", "DimCounty", "county_code", True, False),
    ("FactSupport", "county_code", "DimCounty", "county_code", True, False),
    ("FactKizsVoivodeship", "voivodeship_code", "DimVoivodeship", "voivodeship_code", True, False),
    ("FactKizsCounty", "county_code", "DimCounty", "county_code", True, False),
    ("FactTask", "hazard_code", "DimHazard", "hazard_code", True, False),
    ("DimSchool", "county_code", "DimCounty", "county_code", True, False),
    ("DimCounty", "voivodeship_code", "DimVoivodeship", "voivodeship_code", True, False),
]

FMT_INT = "#,0"
FMT_1DP = "#,0.0"
FMT_PCT = "#,0.0"

MEASURES: list[tuple[str, str, str, str | None]] = [
    # --- 1. Obraz biezacy
    ("FactReport", "Zgloszenia", "COUNTROWS(FactReport)", FMT_INT),
    ("FactReport", "Szkoly ze zgloszeniem", "DISTINCTCOUNT(FactReport[school_id])", FMT_INT),
    ("FactReport", "Zgloszenia AI krytyczne",
     'CALCULATE(COUNTROWS(FactReport), FactReport[ai_priority_code] = "KRYTYCZNY")', FMT_INT),
    ("FactReportStatus", "Zgloszenia decyzja krytyczna",
     'CALCULATE(COUNTROWS(FactReportStatus), FactReportStatus[duty_priority_code] = "KRYTYCZNY")', FMT_INT),
    ("FactReportStatus", "Zgloszenia otwarte",
     'CALCULATE(COUNTROWS(FactReportStatus), FactReportStatus[status_code] <> "ZAMKNIETE")', FMT_INT),
    ("FactReportStatus", "Mediana czasu do decyzji (min)",
     "MEDIAN(FactReportStatus[decision_delay_min])", FMT_1DP),
    ("FactReportStatus", "Decyzje po 10 min %",
     "DIVIDE(CALCULATE(COUNTROWS(FactReportStatus), FactReportStatus[decision_delay_min] > 10), "
     "COUNTROWS(FactReportStatus)) * 100", FMT_PCT),

    # --- 2. Kampania
    ("FactCampaignFlag", "Zgloszenia w kampanii",
     "CALCULATE(COUNTROWS(FactCampaignFlag), FactCampaignFlag[campaign_flag] = 1)", FMT_INT),
    ("FactCampaignFlag", "Zgloszenia dla czlowieka",
     "CALCULATE(COUNTROWS(FactCampaignFlag), FactCampaignFlag[keep_for_human] = 1)", FMT_INT),
    ("FactCampaignFlag", "Udzial zgloszen dla czlowieka %",
     "DIVIDE([Zgloszenia dla czlowieka], COUNTROWS(FactCampaignFlag)) * 100", FMT_PCT),
    ("FactCampaignCluster", "Klastry skoordynowane",
     "CALCULATE(COUNTROWS(FactCampaignCluster), FactCampaignCluster[coordinated] = TRUE())", FMT_INT),
    ("FactCampaignCluster", "Najwiekszy klaster",
     "MAX(FactCampaignCluster[size])", FMT_INT),

    # --- 3. Indeks i eskalacja
    ("FactKizsVoivodeship", "KIZS wojewodztwa",
     "MAX(FactKizsVoivodeship[kizs])", FMT_1DP),
    ("FactKizsNational", "KIZS krajowy - szczyt",
     "MAX(FactKizsNational[kizs_national_mean])", FMT_1DP),
    ("FactKizsNational", "Wojewodztwa powyzej progu",
     "MAX(FactKizsNational[voivodeships_kizs_ge_threshold])", "0"),
    ("FactKizsNational", "Zgloszenia kampanii 24h",
     "MAX(FactKizsNational[campaign_24h])", FMT_INT),
    ("FactKizsNational", "Rekomendacja eskalacji",
     "VAR vRzzk = MAXX(FactKizsNational, IF(FactKizsNational[rec_rzzk] = TRUE(), 1, 0)) "
     "VAR vMin = MAXX(FactKizsNational, IF(FactKizsNational[rec_minister] = TRUE(), 1, 0)) "
     "VAR vWoj = MAXX(FactKizsNational, IF(FactKizsNational[rec_voivode_any] = TRUE(), 1, 0)) "
     'RETURN SWITCH(TRUE(), vRzzk = 1, "RZZK", vMin = 1, "Minister wiodacy", vWoj = 1, "Wojewoda i kurator", "Brak eskalacji")', None),
    ("FactKizsCounty", "KIZS powiatu", "MAX(FactKizsCounty[county_kizs])", FMT_1DP),

    # --- 4. Obciazenie 112 i zaklocenia
    ("FactHotline", "Polaczenia 112 szkolne",
     "SUM(FactHotline[calls_112_school_related])", FMT_INT),
    ("FactHotline", "Obciazenie 112 maks.", "MAX(FactHotline[load_ratio])", "#,0.00"),
    ("FactHotline", "Godziny przeciazenia 112",
     "CALCULATE(COUNTROWS(FactHotline), FactHotline[load_ratio] > 1.5)", FMT_INT),
    ("FactDisorder", "Zdarzenia Z18", "COUNTROWS(FactDisorder)", FMT_INT),
    ("FactDisorder", "Uczestnicy zdarzen Z18", "SUM(FactDisorder[est_participants])", FMT_INT),
    ("FactSocial", "Zasieg tresci", "SUM(FactSocial[est_reach])", FMT_INT),

    # --- 5. Zasoby
    ("FactPatrolDaily", "Pokrycie patroli status quo - najgorszy dzien",
     "MIN(FactPatrolDaily[coverage_status_quo])", "0.000"),
    ("FactPatrolDaily", "Pokrycie patroli po realokacji - najgorszy dzien",
     "MIN(FactPatrolDaily[coverage_after_reallocation])", "0.000"),
    ("FactPatrolDaily", "Powiaty w deficycie",
     "MAX(FactPatrolDaily[deficit_counties_status_quo])", "0"),

    # --- 6. Przekazania
    ("FactHandoff", "Przekazania", "COUNTROWS(FactHandoff)", FMT_INT),
    ("FactHandoff", "Przekazania do Policji",
     'CALCULATE(COUNTROWS(FactHandoff), FactHandoff[recipient_code] = "POL")', FMT_INT),

    # --- 7. What-if
    ("FactWhatIf", "Opoznienie realnych krytycznych maks. (min)",
     "MAX(FactWhatIf[real_critical_wave_max_delay_min])", FMT_1DP),
    ("FactWhatIf", "Opoznienie BS-4826 (min)", "MAX(FactWhatIf[bs4826_delay_min])", FMT_1DP),
    ("FactSpo3Timing", "Zdarzenia Z18 po komunikacie",
     "MAX(FactSpo3Timing[disorder_events_after])", FMT_INT),

    # --- 8. Narracja
    ("FactReport", "Naglowek sytuacji",
     'VAR N = FORMAT([Zgloszenia], "#,0") '
     'VAR K = FORMAT([Zgloszenia w kampanii], "#,0") '
     'RETURN "Zgloszen: " & N & " | oznaczonych jako kampania: " & K', None),
]


def tag() -> str:
    return str(uuid.uuid4())


def build_columns(delta_table: str) -> list[dict]:
    cols = []
    for f in SCHEMAS[delta_table]:
        base = f["type"].split("(")[0]
        dt = TYPE_MAP.get(base)
        if dt is None:
            dt = "decimal" if base.startswith("decimal") else "string"
        col = {
            "name": f["name"],
            "dataType": dt,
            "sourceColumn": f["name"],
            "lineageTag": tag(),
            "summarizeBy": "none",
        }
        if dt == "dateTime":
            col["formatString"] = "yyyy-mm-dd hh:nn:ss"
        cols.append(col)
    return cols


def build_model() -> dict:
    tables = []
    measures_by_table: dict[str, list[dict]] = {}
    for tbl, name, expr, fmt in MEASURES:
        m = {"name": name, "expression": expr, "lineageTag": tag()}
        if fmt:
            m["formatString"] = fmt
        measures_by_table.setdefault(tbl, []).append(m)

    for model_name, delta in TABLES.items():
        if delta not in SCHEMAS:
            raise SystemExit(f"Brak tabeli Delta '{delta}' w schemas.json")
        t = {
            "name": model_name,
            "lineageTag": tag(),
            "columns": build_columns(delta),
            "partitions": [{
                "name": model_name,
                "mode": "directLake",
                "source": {"type": "entity", "entityName": delta,
                           "expressionSource": "DatabaseQuery"},
            }],
        }
        if model_name in measures_by_table:
            t["measures"] = measures_by_table[model_name]
        tables.append(t)

    rels = []
    for i, (ft, fc, tt, tc, active, both) in enumerate(RELATIONSHIPS, start=1):
        for tname, cname in ((ft, fc), (tt, tc)):
            if not any(c["name"] == cname for c in
                       next(x for x in tables if x["name"] == tname)["columns"]):
                raise SystemExit(f"Relacja {i}: brak kolumny {tname}[{cname}]")
        r = {
            "name": f"rel_{i:02d}_{ft}_{fc}_{tt}",
            "fromTable": ft, "fromColumn": fc,
            "toTable": tt, "toColumn": tc,
            "isActive": active,
        }
        if both:
            r["crossFilteringBehavior"] = "bothDirections"
        rels.append(r)

    return {
        "name": MODEL_NAME,
        "compatibilityLevel": 1604,
        "model": {
            "culture": "pl-PL",
            "collation": "Latin1_General_100_BIN2_UTF8",
            "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "sourceQueryCulture": "pl-PL",
            "expressions": [{
                "name": "DatabaseQuery",
                "kind": "m",
                "lineageTag": tag(),
                "expression": (
                    "let\n"
                    f'    Source = AzureStorage.DataLake("https://onelake.dfs.fabric.microsoft.com/{WS}/{LH}")\n'
                    "in\n    Source"
                ),
                "annotations": [{"name": "PBI_IncludeFutureArtifacts", "value": "False"}],
            }],
            "tables": tables,
            "relationships": rels,
            "annotations": [{"name": "PBI_QueryOrder", "value": '["DatabaseQuery"]'}],
        },
    }


def token() -> str:
    out = subprocess.run(
        ["az", "account", "get-access-token", "--resource", "https://api.fabric.microsoft.com",
         "--query", "accessToken", "-o", "tsv"], capture_output=True, text=True, shell=True)
    if out.returncode != 0:
        raise SystemExit(out.stderr)
    return out.stdout.strip()


def headers() -> dict:
    return {"Authorization": f"Bearer {token()}", "Content-Type": "application/json"}


def b64(obj) -> str:
    text = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, indent=2)
    return base64.b64encode(text.encode("utf-8")).decode()


def wait(resp: requests.Response):
    if resp.status_code in (200, 201):
        return resp.json() if resp.content else None
    if resp.status_code == 202:
        op = resp.headers.get("x-ms-operation-id")
        while True:
            time.sleep(5)
            st = requests.get(f"{API}/operations/{op}", headers=headers(), timeout=120).json()
            if st["status"] not in ("NotStarted", "Running"):
                break
        if st["status"] != "Succeeded":
            raise SystemExit(f"Operacja {op}: {st['status']} {json.dumps(st.get('error'), ensure_ascii=False)}")
        return None
    raise SystemExit(f"HTTP {resp.status_code}: {resp.text[:2000]}")


def main() -> None:
    model = build_model()
    (ROOT / ".fabric" / "model.bim").write_text(
        json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    n_meas = sum(len(t.get("measures", [])) for t in model["model"]["tables"])
    print(f"== TMSL: {len(model['model']['tables'])} tabel, "
          f"{len(model['model']['relationships'])} relacji, {n_meas} miar")

    definition = {"parts": [
        {"path": "model.bim", "payload": b64(model), "payloadType": "InlineBase64"},
        {"path": "definition.pbism",
         "payload": b64({"version": "1.0", "settings": {}}), "payloadType": "InlineBase64"},
    ]}

    items = requests.get(f"{API}/workspaces/{WS}/items", headers=headers(), timeout=120).json()
    ex = next((i for i in items["value"]
               if i["displayName"] == MODEL_NAME and i["type"] == "SemanticModel"), None)

    if ex:
        r = requests.post(f"{API}/workspaces/{WS}/semanticModels/{ex['id']}/updateDefinition",
                          headers=headers(), json={"definition": definition}, timeout=600)
        wait(r)
        model_id = ex["id"]
        print(f"   zaktualizowano: {model_id}")
    else:
        body = {"displayName": MODEL_NAME,
                "description": "Krajowy obraz zagrozen szkolnych, DirectLake nad lh_school_safety.",
                "definition": definition}
        r = requests.post(f"{API}/workspaces/{WS}/semanticModels", headers=headers(), json=body, timeout=600)
        item = wait(r)
        if item is None:
            items = requests.get(f"{API}/workspaces/{WS}/items", headers=headers(), timeout=120).json()
            item = next(i for i in items["value"]
                        if i["displayName"] == MODEL_NAME and i["type"] == "SemanticModel")
        model_id = item["id"]
        print(f"   utworzono: {model_id}")

    STATE["semanticModelId"] = model_id
    STATE_PATH.write_text(json.dumps(STATE, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nGotowe.")


if __name__ == "__main__":
    main()
