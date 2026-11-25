"""Kontrola modelu semantycznego: miary DAX porownane z wartosciami liczonymi lokalnie z datasets\\."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"
STATE = json.loads((ROOT / ".fabric" / "deployment.json").read_text(encoding="utf-8"))
WS, MODEL = STATE["workspaceId"], STATE["semanticModelId"]
PBI = "https://api.powerbi.com/v1.0/myorg"


def token() -> str:
    out = subprocess.run(
        ["az", "account", "get-access-token", "--resource",
         "https://analysis.windows.net/powerbi/api", "--query", "accessToken", "-o", "tsv"],
        capture_output=True, text=True, shell=True)
    if out.returncode != 0:
        raise SystemExit(out.stderr)
    return out.stdout.strip()


def dax(query: str) -> list[dict]:
    r = requests.post(
        f"{PBI}/groups/{WS}/datasets/{MODEL}/executeQueries",
        headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json"},
        json={"queries": [{"query": query}], "serializerSettings": {"includeNulls": True}},
        timeout=300)
    if r.status_code != 200:
        raise SystemExit(f"DAX HTTP {r.status_code}: {r.text[:2000]}")
    return r.json()["results"][0]["tables"][0]["rows"]


def onelake_file(path: str):
    import io
    tk = subprocess.run(["az", "account", "get-access-token", "--resource", "https://storage.azure.com",
                         "--query", "accessToken", "-o", "tsv"], capture_output=True, text=True, shell=True).stdout.strip()
    r = requests.get(f"https://onelake.dfs.fabric.microsoft.com/{WS}/{STATE['lakehouseId']}/{path}",
                     headers={"Authorization": f"Bearer {tk}"}, timeout=120)
    r.raise_for_status()
    return io.BytesIO(r.content)


def expected() -> list[tuple[str, float]]:
    rep = pd.read_json(DATA / "fact_report.jsonl", lines=True)
    st = pd.read_csv(DATA / "fact_report_status.csv")
    # Delta zawiera wynik notebooka 02 z Fabric (Spark), nie z lokalnego uruchomienia: klastry roznia sie nieznacznie.
    flags = pd.read_csv(onelake_file("Files/raw/derived/campaign_report_flags.csv"))
    clusters = pd.read_csv(DATA / "derived" / "campaign_clusters.csv")
    hot = pd.read_json(DATA / "fact_hotline_load.jsonl", lines=True)
    dis = pd.read_json(DATA / "fact_disorder_event.jsonl", lines=True)
    ho = pd.read_csv(DATA / "fact_report_handoff.csv")
    return [
        ("Zgloszenia", len(rep)),
        ("Szkoly ze zgloszeniem", rep["school_id"].nunique()),
        ("Zgloszenia AI krytyczne", int((rep["ai_priority_code"] == "KRYTYCZNY").sum())),
        ("Zgloszenia decyzja krytyczna", int((st["duty_priority_code"] == "KRYTYCZNY").sum())),
        ("Zgloszenia w kampanii", int((flags["campaign_flag"] == 1).sum())),
        ("Zgloszenia dla czlowieka", int((flags["keep_for_human"] == 1).sum())),
        ("Klastry skoordynowane", int(clusters["coordinated"].astype(str).str.lower().eq("true").sum())),
        ("Najwiekszy klaster", int(clusters["size"].max())),
        ("Polaczenia 112 szkolne", int(hot["calls_112_school_related"].sum())),
        ("Zdarzenia Z18", len(dis)),
        ("Przekazania", len(ho)),
        ("Przekazania do Policji", int((ho["recipient_code"] == "POL").sum())),
    ]


def main() -> None:
    checks = expected()
    print("== Miary vs wartosci liczone lokalnie")
    expr = ", ".join(f'"{n}", [{n}]' for n, _ in checks)
    row = dax(f"EVALUATE ROW({expr})")[0]
    bad = 0
    for name, exp in checks:
        got = row.get(f"[{name}]")
        ok = got is not None and round(got) == exp
        bad += 0 if ok else 1
        print(f"   {'OK ' if ok else 'BLAD'} {name:<34} {got!s:>10}  (lokalnie {exp})")

    print("\n== Naglowek i eskalacja (kontekst: cala tabela)")
    r = dax('EVALUATE ROW("n", [Naglowek sytuacji], "e", [Rekomendacja eskalacji], '
            '"med", [Mediana czasu do decyzji (min)])')[0]
    print(f"   {r['[n]']}\n   eskalacja: {r['[e]']}   mediana do decyzji: {r['[med]']}")

    r = dax('EVALUATE ROW("a", [KIZS krajowy - szczyt], "b", [Pokrycie patroli status quo - najgorszy dzien], '
            '"c", [Pokrycie patroli po realokacji - najgorszy dzien], "d", [Powiaty w deficycie], "e", [Opoznienie BS-4826 (min)])')[0]
    print(f"   KIZS szczyt {r['[a]']}  pokrycie patroli {r['[b]']} -> {r['[c]']}  powiaty w deficycie {r['[d]']}  BS-4826 {r['[e]']} min")

    print("\n== Zgloszenia wg kategorii (relacja DimCategory)")
    for x in dax('EVALUATE SUMMARIZECOLUMNS(DimCategory[category_name], "n", [Zgloszenia])'):
        print(f"   {x['DimCategory[category_name]']:<40} {x['[n]']}")

    print("\n== Zgloszenia wg wojewodztwa (top 3)")
    for x in dax('EVALUATE TOPN(3, SUMMARIZECOLUMNS(DimVoivodeship[voivodeship_name], "n", [Zgloszenia]), [n], DESC)'):
        print(f"   {x['DimVoivodeship[voivodeship_name]']:<24} {x['[n]']}")

    if bad:
        raise SystemExit(f"\n{bad} miar niezgodnych z danymi lokalnymi.")
    print("\nModel semantyczny zweryfikowany.")


if __name__ == "__main__":
    main()
