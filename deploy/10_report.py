"""Raport Power BI "Zagrozenia szkolne" (4 strony) w formacie PBIR.

Buduje definicje raportu wprost z JSON-a (bez Power BI Desktop) i wdraza ja
przez Fabric REST API na model semantyczny sm_school_safety.

Zrodlo merytoryczne: report/REPORT_SPEC.md
Format PBIR: patrz deploy/README.md, sekcja "Format definicji raportu (PBIR)".

Uzycie:
    python deploy/10_report.py            # walidacja + wdrozenie
    python deploy/10_report.py --dry-run  # sama walidacja, bez wysylki
    python deploy/10_report.py --no-theme # bez ciemnego motywu (awaryjnie)
"""

from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import pathlib
import subprocess
import sys
import time

import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = ROOT / ".fabric" / "deployment.json"
REPORT_NAME = "rpt_zagrozenia_szkolne"
REPORT_DESC = "Krajowa warstwa zgloszen szkolnych: obraz, decyzje dyzurnych, kampanie, eskalacja."
FABRIC_API = "https://api.fabric.microsoft.com/v1"

W, H = 1280, 720
SCHEMA_VIS = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json"
SCHEMA_PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json"
SCHEMA_PAGES = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json"
SCHEMA_REPORT = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json"
SCHEMA_PBIR = "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/1.0.0/schema.json"
SCHEMA_VERSION = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json"

FOOTER = "Dane syntetyczne. Model wskazuje priorytety - decyzje podejmuje czlowiek."

# Funkcje agregujace wg schematu semanticQuery
SUM, AVG, DCOUNT, MIN, MAX, COUNT, MEDIAN = 0, 1, 2, 3, 4, 5, 6

# ---------------------------------------------------------------- metadane


def load_model_metadata() -> tuple[dict[str, str], dict[str, set[str]], dict[str, str]]:
    """Zwraca (tabela->tabela delta, tabela->kolumny, miara->tabela)."""
    spec = importlib.util.spec_from_file_location("sm06", ROOT / "deploy" / "06_semantic_model.py")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    tables = dict(mod.TABLES)
    schemas = json.loads((ROOT / ".fabric" / "schemas.json").read_text(encoding="utf-8"))
    columns: dict[str, set[str]] = {}
    for tbl, delta in tables.items():
        fields = schemas.get(delta, [])
        columns[tbl] = {f["name"] if isinstance(f, dict) else f for f in fields}
    measures = {name: tbl for tbl, name, *_ in mod.MEASURES}
    return tables, columns, measures


# ---------------------------------------------------------------- pola


def col(entity: str, prop: str) -> dict:
    return {
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": prop,
    }


def mea(entity: str, prop: str) -> dict:
    return {
        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": prop,
    }


AGG_NAME = {SUM: "Sum", AVG: "Avg", DCOUNT: "CountNonNull", MIN: "Min", MAX: "Max",
            COUNT: "CountNonNull", MEDIAN: "Median"}


def agg(entity: str, prop: str, fn: int = SUM, label: str | None = None) -> dict:
    name = AGG_NAME.get(fn, "Sum")
    return {
        "field": {
            "Aggregation": {
                "Expression": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
                "Function": fn,
            }
        },
        "queryRef": f"{name}({entity}.{prop})",
        "nativeQueryRef": label or f"{name} {prop}",
    }


def lit(value: str) -> dict:
    return {"expr": {"Literal": {"Value": f"'{value}'"}}}


def boolean(value: bool) -> dict:
    return {"expr": {"Literal": {"Value": "true" if value else "false"}}}


def title_obj(text: str) -> dict:
    return {
        "title": [{"properties": {"show": boolean(True), "text": lit(text),
                                  "fontSize": {"expr": {"Literal": {"Value": "11D"}}}}}]
    }


# ---------------------------------------------------------------- wizualizacje


def visual(name: str, vtype: str, x: int, y: int, w: int, h: int,
           roles: dict[str, list[dict]] | None = None,
           title: str | None = None,
           objects: dict | None = None,
           z: int | None = None) -> dict:
    v: dict = {"visualType": vtype}
    if roles:
        v["query"] = {"queryState": {role: {"projections": projs} for role, projs in roles.items()}}
    if objects:
        v["objects"] = objects
    if title:
        v["visualContainerObjects"] = title_obj(title)
    return {
        "$schema": SCHEMA_VIS,
        "name": name,
        "position": {"x": x, "y": y, "z": z if z is not None else 0,
                     "width": w, "height": h, "tabOrder": 0},
        "visual": v,
    }


def textbox(name: str, x: int, y: int, w: int, h: int, text: str,
            size: str = "14pt", color: str = "#F2F2F2", align: str = "left",
            bold: bool = False) -> dict:
    style = {"fontFamily": "Segoe UI", "fontSize": size, "color": color}
    if bold:
        style["fontWeight"] = "bold"
    return visual(
        name, "textbox", x, y, w, h,
        objects={"general": [{"properties": {"paragraphs": [
            {"textRuns": [{"value": text, "textStyle": style}], "horizontalTextAlignment": align}
        ]}}]},
    )


def header(page_no: int, title: str, question: str) -> list[dict]:
    return [
        textbox(f"p{page_no}_hdr", 16, 8, 900, 40, f"{page_no}. {title}", size="20pt", bold=True),
        textbox(f"p{page_no}_sub", 16, 46, 900, 26, question, size="11pt", color="#A6A6A6"),
        textbox(f"p{page_no}_ftr", 16, H - 26, 900, 22, FOOTER, size="9pt", color="#8C8C8C"),
    ]


def card(name: str, x: int, y: int, w: int, h: int, entity: str, measure: str, title: str) -> dict:
    return visual(name, "card", x, y, w, h, {"Values": [mea(entity, measure)]}, title=title)


def card_agg(name: str, x: int, y: int, w: int, h: int, entity: str, prop: str, fn: int, title: str) -> dict:
    return visual(name, "card", x, y, w, h, {"Values": [agg(entity, prop, fn)]}, title=title)


# ---------------------------------------------------------------- strony

CARD_H = 88


def cards_row(vis: list[dict], prefix: str, cards: list[tuple[str, str, str]]) -> None:
    for i, (e, m, t) in enumerate(cards):
        vis.append(card(f"{prefix}_c{i + 1}", 16 + i * 216, 80, 200, CARD_H, e, m, t))


def page1() -> tuple[str, str, list[dict]]:
    vis = header(1, "Obraz krajowy", "Ile zgloszen, gdzie i jak bardzo obciazone sa 112 i szkoly.")
    cards_row(vis, "p1", [
        ("FactReport", "Zgloszenia", "Zgloszenia"),
        ("FactReport", "Zgloszenia AI krytyczne", "Krytyczne wg AI"),
        ("FactDisorder", "Zdarzenia Z18", "Zdarzenia Z18"),
        ("FactHotline", "Polaczenia 112 szkolne", "Polaczenia 112 o szkolach"),
    ])
    vis.append(visual("p1_voiv", "barChart", 16, 180, 620, 380, {
        "Category": [col("DimVoivodeship", "voivodeship_name")],
        "Y": [mea("FactReport", "Zgloszenia")],
    }, title="Zgloszenia wg wojewodztwa"))
    vis.append(visual("p1_cat", "barChart", 648, 180, 400, 380, {
        "Category": [col("DimCategory", "category_name")],
        "Y": [mea("FactReport", "Zgloszenia")],
    }, title="Zgloszenia wg kategorii z aplikacji"))
    vis.append(visual("p1_sl1", "slicer", 1060, 180, 204, 90, {"Values": [col("DimVoivodeship", "voivodeship_name")]},
                      title="Wojewodztwo"))
    vis.append(visual("p1_sl2", "slicer", 1060, 280, 204, 90, {"Values": [col("DimPriority", "priority_name")]},
                      title="Priorytet wg AI"))
    vis.append(textbox("p1_note", 16, 568, 1248, 60,
                       "Zgloszenia pochodza z symulacji. Widok dyzurnego z aplikacji obejmuje dzis tylko mazowieckie, "
                       "pozostale wojewodztwa to ekstrapolacja demonstracyjna.", size="11pt", color="#D9D9D9"))
    return "p1ObrazKrajowy", "1. Obraz krajowy", vis


def page2() -> tuple[str, str, list[dict]]:
    vis = header(2, "AI sugeruje, czlowiek decyduje", "Gdzie decyzja dyzurnego rozni sie od sugestii i jak szybko zapada.")
    cards_row(vis, "p2", [
        ("FactReportStatus", "Zgloszenia decyzja krytyczna", "Krytyczne wg dyzurnego"),
        ("FactReportStatus", "Mediana czasu do decyzji (min)", "Mediana do decyzji (min)"),
        ("FactReportStatus", "Decyzje po 10 min %", "Decyzje po 10 min %"),
        ("FactWhatIf", "Opoznienie BS-4826 (min)", "Opoznienie BS-4826 (min)"),
    ])
    vis.append(visual("p2_tbl", "tableEx", 16, 180, 760, 380, {
        "Values": [col("FactReport", "report_id"), col("DimSchool", "school_name"),
                   col("FactReport", "ai_priority_code"),
                   col("FactReportStatus", "duty_priority_code"),
                   col("FactReportStatus", "status_code"),
                   col("FactReportStatus", "decision_delay_min")],
    }, title="Zgloszenia: sugestia AI i decyzja dyzurnego"))
    vis.append(visual("p2_pri", "columnChart", 788, 180, 476, 190, {
        "Category": [col("FactReport", "ai_priority_code")],
        "Y": [mea("FactReport", "Zgloszenia")],
    }, title="Priorytet wg AI"))
    vis.append(visual("p2_rec", "barChart", 788, 378, 476, 182, {
        "Category": [col("DimRecipient", "recipient_name")],
        "Y": [mea("FactHandoff", "Przekazania")],
    }, title="Przekazania wg adresata"))
    vis.append(textbox("p2_note", 16, 568, 1248, 60,
                       "Sugestia AI klasyfikuje zgloszenie, nie osobe. Ostateczny priorytet nadaje dyzurny, a decyzje trafiaja do audytu.",
                       size="11pt", color="#D9D9D9"))
    return "p2DecyzjaDyzurnego", "2. AI sugeruje, czlowiek decyduje", vis


def page3() -> tuple[str, str, list[dict]]:
    vis = header(3, "Kampania czy realne zagrozenie", "Ktore zgloszenia tworza skoordynowana fale i czy realne krytyczne zostaja przy czlowieku.")
    cards_row(vis, "p3", [
        ("FactCampaignCluster", "Klastry skoordynowane", "Klastry skoordynowane"),
        ("FactCampaignFlag", "Zgloszenia w kampanii", "Zgloszenia w kampanii"),
        ("FactCampaignFlag", "Zgloszenia dla czlowieka", "Zgloszenia dla czlowieka"),
        ("FactSocial", "Zasieg tresci", "Zasieg tresci w sieci"),
    ])
    vis.append(visual("p3_cl", "tableEx", 16, 180, 760, 250, {
        "Values": [col("FactCampaignCluster", "cluster"), col("FactCampaignCluster", "size"),
                   col("FactCampaignCluster", "counties"), col("FactCampaignCluster", "voivodeships"),
                   col("FactCampaignCluster", "automated_client_share"),
                   col("FactCampaignCluster", "first_ts")],
    }, title="Wykryte klastry (czas, tresc, geografia)"))
    vis.append(visual("p3_soc", "barChart", 788, 180, 476, 250, {
        "Category": [col("FactSocial", "narrative_name")],
        "Y": [mea("FactSocial", "Zasieg tresci")],
    }, title="Zasieg narracji w mediach spolecznosciowych"))
    vis.append(visual("p3_dis", "columnChart", 16, 438, 620, 220, {
        "Category": [col("FactDisorder", "event_type")],
        "Y": [mea("FactDisorder", "Zdarzenia Z18")],
    }, title="Zdarzenia Z18 wg typu"))
    vis.append(visual("p3_hot", "columnChart", 648, 438, 616, 220, {
        "Category": [col("DimVoivodeship", "voivodeship_name")],
        "Y": [mea("FactHotline", "Obciazenie 112 maks.")],
    }, title="Najwyzsze obciazenie 112 wg wojewodztwa"))
    return "p3Kampania", "3. Kampania czy realne zagrozenie", vis


def page4() -> tuple[str, str, list[dict]]:
    vis = header(4, "Eskalacja i zasoby", "Na ktorym poziomie powinna zapasc decyzja i gdzie rozstawic patrole.")
    cards_row(vis, "p4", [
        ("FactKizsNational", "Rekomendacja eskalacji", "Rekomendacja"),
        ("FactKizsNational", "KIZS krajowy - szczyt", "KIZS krajowy (szczyt)"),
        ("FactKizsNational", "Wojewodztwa powyzej progu", "Wojewodztwa powyzej progu"),
        ("FactPatrolDaily", "Powiaty w deficycie", "Powiaty z deficytem patroli"),
    ])
    vis.append(visual("p4_kizs", "barChart", 16, 180, 620, 380, {
        "Category": [col("DimVoivodeship", "voivodeship_name")],
        "Y": [mea("FactKizsVoivodeship", "KIZS wojewodztwa")],
    }, title="Krajowy Indeks Zagrozenia Szkolnego wg wojewodztwa (maks.)"))
    vis.append(visual("p4_cty", "tableEx", 648, 180, 616, 250, {
        "Values": [col("DimCounty", "county_name"), mea("FactKizsCounty", "KIZS powiatu")],
    }, title="Powiaty wg KIZS"))
    vis.append(visual("p4_pat", "tableEx", 648, 438, 616, 122, {
        "Values": [mea("FactPatrolDaily", "Pokrycie patroli status quo - najgorszy dzien"),
                   mea("FactPatrolDaily", "Pokrycie patroli po realokacji - najgorszy dzien"),
                   mea("FactSpo3Timing", "Zdarzenia Z18 po komunikacie")],
    }, title="Pokrycie patroli i efekt komunikatu SPO-3"))
    vis.append(textbox("p4_note", 16, 568, 1248, 60,
                       "Progi eskalacji i parametry zasobow sa parametrami demonstracyjnymi. Rekomendacja jest propozycja dla czlowieka, nie decyzja.",
                       size="11pt", color="#D9D9D9"))
    return "p4Eskalacja", "4. Eskalacja i zasoby", vis


PAGE_BUILDERS = [page1, page2, page3, page4]

# ---------------------------------------------------------------- motyw

DARK_THEME = {
    "name": "OL-ZK-Dark",
    "dataColors": ["#4FC3F7", "#FFB74D", "#E57373", "#81C784", "#BA68C8", "#4DD0E1",
                   "#F06292", "#AED581", "#FFD54F", "#9575CD", "#4DB6AC", "#FF8A65"],
    "background": "#1B1B1F",
    "foreground": "#F2F2F2",
    "tableAccent": "#4FC3F7",
    "good": "#81C784",
    "neutral": "#FFB74D",
    "bad": "#E57373",
    "maximum": "#E57373",
    "center": "#FFB74D",
    "minimum": "#81C784",
    "visualStyles": {
        "*": {
            "*": {
                "background": [{"color": {"solid": {"color": "#26262B"}}, "transparency": 0}],
                "border": [{"show": True, "color": {"solid": {"color": "#3A3A42"}}, "radius": 6}],
                "title": [{"show": True, "fontColor": {"solid": {"color": "#F2F2F2"}},
                           "background": {"solid": {"color": "#26262B"}}, "fontSize": 11}],
                "labels": [{"color": {"solid": {"color": "#F2F2F2"}}}],
                "categoryAxis": [{"labelColor": {"solid": {"color": "#C7C7CF"}},
                                  "gridlineColor": {"solid": {"color": "#3A3A42"}}}],
                "valueAxis": [{"labelColor": {"solid": {"color": "#C7C7CF"}},
                               "gridlineColor": {"solid": {"color": "#3A3A42"}}}],
                "legend": [{"labelColor": {"solid": {"color": "#C7C7CF"}}}],
            }
        },
        "card": {"*": {"labels": [{"color": {"solid": {"color": "#4FC3F7"}}, "fontSize": 26}],
                       "categoryLabels": [{"color": {"solid": {"color": "#A6A6A6"}}, "fontSize": 9}]}},
        "textbox": {"*": {"background": [{"show": False}], "border": [{"show": False}]}},
    },
}

THEME_FILE = "OL-ZK-Dark.json"

# ---------------------------------------------------------------- definicja


def build_parts(semantic_model_id: str, use_theme: bool) -> list[tuple[str, str]]:
    """Zwraca liste (sciezka, tekst JSON)."""
    parts: list[tuple[str, str]] = []

    parts.append(("definition.pbir", json.dumps({
        "$schema": SCHEMA_PBIR,
        "version": "4.0",
        "datasetReference": {"byConnection": {
            "connectionString": None,
            "pbiServiceModelId": None,
            "pbiModelVirtualServerName": "sobe_wowvirtualserver",
            "pbiModelDatabaseName": semantic_model_id,
            "connectionType": "pbiServiceXmlaStyleLive",
            "name": "EntityDataSource",
        }},
    }, indent=2, ensure_ascii=False)))

    parts.append(("definition/version.json", json.dumps({
        "$schema": SCHEMA_VERSION, "version": "2.0.0",
    }, indent=2)))

    report: dict = {
        "$schema": SCHEMA_REPORT,
        "themeCollection": {"baseTheme": {"name": "CY24SU02", "reportVersionAtImport": "5.55",
                                          "type": "SharedResources"}},
        "layoutOptimization": "None",
        "settings": {"useStylableVisualContainerHeader": True, "defaultDrillFilterOtherVisuals": True},
    }
    if use_theme:
        report["themeCollection"]["customTheme"] = {"name": "OL-ZK-Dark", "reportVersionAtImport": "5.55",
                                                   "type": "RegisteredResources"}
        report["resourcePackages"] = [{
            "name": "RegisteredResources", "type": "RegisteredResources",
            "items": [{"name": THEME_FILE, "path": THEME_FILE, "type": "CustomTheme"}],
        }]
        parts.append((f"StaticResources/RegisteredResources/{THEME_FILE}",
                      json.dumps(DARK_THEME, indent=2, ensure_ascii=False)))
    parts.append(("definition/report.json", json.dumps(report, indent=2, ensure_ascii=False)))

    order: list[str] = []
    for build in PAGE_BUILDERS:
        name, display, visuals = build()
        order.append(name)
        parts.append((f"definition/pages/{name}/page.json", json.dumps({
            "$schema": SCHEMA_PAGE, "name": name, "displayName": display,
            "displayOption": "FitToPage", "height": H, "width": W,
        }, indent=2, ensure_ascii=False)))
        for v in visuals:
            parts.append((f"definition/pages/{name}/visuals/{v['name']}/visual.json",
                          json.dumps(v, indent=2, ensure_ascii=False)))

    parts.append(("definition/pages/pages.json", json.dumps({
        "$schema": SCHEMA_PAGES, "pageOrder": order, "activePageName": order[0],
    }, indent=2)))

    parts.append((".platform", json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": REPORT_NAME, "description": REPORT_DESC},
        "config": {"version": "2.0", "logicalId": "00000000-0000-0000-0000-000000000000"},
    }, indent=2, ensure_ascii=False)))

    return parts


# ---------------------------------------------------------------- walidacja


def validate(parts: list[tuple[str, str]], columns: dict[str, set[str]], measures: dict[str, str]) -> list[str]:
    errors: list[str] = []
    names: dict[str, set[str]] = {}
    checked = 0

    for path, text in parts:
        try:
            doc = json.loads(text)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}: niepoprawny JSON - {exc}")
            continue
        if not path.endswith("visual.json"):
            continue
        page = path.split("/")[2]
        vname = doc["name"]
        if vname in names.setdefault(page, set()):
            errors.append(f"{page}: zdublowana nazwa wizualizacji '{vname}'")
        names[page].add(vname)
        if len(vname) > 50 or not all(c.isalnum() or c in "-_" for c in vname):
            errors.append(f"{page}/{vname}: nazwa niezgodna z [A-Za-z0-9_-]{{1,50}}")
        pos = doc["position"]
        if pos["x"] < 0 or pos["y"] < 0 or pos["x"] + pos["width"] > W or pos["y"] + pos["height"] > H:
            errors.append(f"{page}/{vname}: wizualizacja poza kanwa {W}x{H} ({pos})")
        qs = doc["visual"].get("query", {}).get("queryState", {})
        for role, block in qs.items():
            for proj in block["projections"]:
                field = proj["field"]
                checked += 1
                if "Measure" in field:
                    entity = field["Measure"]["Expression"]["SourceRef"]["Entity"]
                    prop = field["Measure"]["Property"]
                    if prop not in measures:
                        errors.append(f"{page}/{vname}[{role}]: brak miary '{prop}' w modelu")
                    elif measures[prop] != entity:
                        errors.append(f"{page}/{vname}[{role}]: miara '{prop}' nalezy do "
                                      f"'{measures[prop]}', a nie '{entity}'")
                else:
                    if "Aggregation" in field:
                        c = field["Aggregation"]["Expression"]["Column"]
                    else:
                        c = field["Column"]
                    entity = c["Expression"]["SourceRef"]["Entity"]
                    prop = c["Property"]
                    if entity not in columns:
                        errors.append(f"{page}/{vname}[{role}]: brak tabeli '{entity}' w modelu")
                    elif prop not in columns[entity]:
                        errors.append(f"{page}/{vname}[{role}]: brak kolumny '{entity}'[{prop}]")
    print(f"  sprawdzono {checked} odwolan do modelu w {sum(len(v) for v in names.values())} wizualizacjach")
    return errors


# ---------------------------------------------------------------- Fabric API


def token(resource: str = "https://api.fabric.microsoft.com") -> str:
    out = subprocess.run(
        ["az", "account", "get-access-token", "--resource", resource, "--query", "accessToken", "-o", "tsv"],
        capture_output=True, text=True, shell=True)
    if out.returncode != 0:
        sys.exit(f"Blad az account get-access-token: {out.stderr[:400]}")
    return out.stdout.strip()


def wait_operation(resp: requests.Response, tk: str) -> requests.Response:
    if resp.status_code != 202:
        return resp
    op = resp.headers.get("x-ms-operation-id")
    for _ in range(120):
        time.sleep(3)
        r = requests.get(f"{FABRIC_API}/operations/{op}", headers={"Authorization": f"Bearer {tk}"}, timeout=60)
        status = r.json().get("status")
        if status not in ("NotStarted", "Running"):
            if status != "Succeeded":
                sys.exit(f"Operacja zakonczona statusem {status}: {r.text[:600]}")
            return r
    sys.exit("Przekroczono czas oczekiwania na operacje Fabric.")


def deploy(parts: list[tuple[str, str]], workspace_id: str) -> str:
    tk = token()
    hdr = {"Authorization": f"Bearer {tk}", "Content-Type": "application/json"}
    payload_parts = [{"path": p, "payload": base64.b64encode(t.encode("utf-8")).decode("ascii"),
                      "payloadType": "InlineBase64"} for p, t in parts]

    r = requests.get(f"{FABRIC_API}/workspaces/{workspace_id}/reports", headers=hdr, timeout=120)
    r.raise_for_status()
    existing = next((i for i in r.json().get("value", []) if i["displayName"] == REPORT_NAME), None)

    if existing:
        rid = existing["id"]
        print(f"  aktualizuje istniejacy raport {rid}")
        resp = requests.post(f"{FABRIC_API}/workspaces/{workspace_id}/reports/{rid}/updateDefinition",
                             headers=hdr, json={"definition": {"parts": payload_parts}}, timeout=300)
        if resp.status_code not in (200, 202):
            sys.exit(f"updateDefinition {resp.status_code}: {resp.text[:1200]}")
        wait_operation(resp, tk)
    else:
        print("  tworze nowy raport")
        resp = requests.post(f"{FABRIC_API}/workspaces/{workspace_id}/reports", headers=hdr, json={
            "displayName": REPORT_NAME, "description": REPORT_DESC,
            "definition": {"parts": payload_parts},
        }, timeout=300)
        if resp.status_code not in (200, 201, 202):
            sys.exit(f"create report {resp.status_code}: {resp.text[:1200]}")
        done = wait_operation(resp, tk)
        rid = (resp.json() if resp.status_code in (200, 201) else done.json().get("result", {})).get("id")
        if not rid:
            r = requests.get(f"{FABRIC_API}/workspaces/{workspace_id}/reports", headers=hdr, timeout=120)
            rid = next(i["id"] for i in r.json()["value"] if i["displayName"] == REPORT_NAME)
    return rid


def readback(workspace_id: str, report_id: str) -> None:
    tk = token()
    hdr = {"Authorization": f"Bearer {tk}"}
    r = requests.post(f"{FABRIC_API}/workspaces/{workspace_id}/reports/{report_id}/getDefinition",
                      headers=hdr, timeout=300)
    if r.status_code == 202:
        op = r.headers.get("x-ms-operation-id")
        wait_operation(r, tk)
        r = requests.get(f"{FABRIC_API}/operations/{op}/result", headers=hdr, timeout=300)
    parts = r.json().get("definition", {}).get("parts", [])
    print(f"  odczyt zwrotny: {len(parts)} czesci definicji")
    pages = sorted({p["path"].split("/")[2] for p in parts
                    if p["path"].startswith("definition/pages/") and p["path"].count("/") >= 3})
    vis = len([p for p in parts if p["path"].endswith("visual.json")])
    print(f"  strony: {len(pages)} -> {', '.join(pages)}")
    print(f"  wizualizacje: {vis}")
    if len(pages) != len(PAGE_BUILDERS):
        print(f"  UWAGA: oczekiwano {len(PAGE_BUILDERS)} stron")


# ---------------------------------------------------------------- main


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-theme", action="store_true", help="pomin ciemny motyw (diagnostyka)")
    ap.add_argument("--save", metavar="DIR", help="zapisz definicje na dysk (podglad)")
    args = ap.parse_args()

    state = json.loads(STATE.read_text(encoding="utf-8"))
    ws, sm = state["workspaceId"], state["semanticModelId"]

    print("Metadane modelu semantycznego...")
    _, columns, measures = load_model_metadata()
    print(f"  {len(columns)} tabel, {len(measures)} miar")

    print("Budowanie definicji PBIR...")
    parts = build_parts(sm, use_theme=not args.no_theme)
    print(f"  {len(parts)} czesci, {sum(len(t) for _, t in parts) // 1024} KB")

    print("Walidacja...")
    errors = validate(parts, columns, measures)
    if errors:
        print(f"\nBLEDY ({len(errors)}):")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print("  OK")

    if args.save:
        out = pathlib.Path(args.save)
        for p, t in parts:
            f = out / p
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(t, encoding="utf-8")
        print(f"  zapisano do {out}")

    if args.dry_run:
        print("\n--dry-run: pomijam wdrozenie.")
        return

    print("Wdrozenie do Fabric...")
    rid = deploy(parts, ws)
    print(f"  reportId = {rid}")
    readback(ws, rid)

    state["reportId"] = rid
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nGotowe. https://app.powerbi.com/groups/{ws}/reports/{rid}")


if __name__ == "__main__":
    main()
