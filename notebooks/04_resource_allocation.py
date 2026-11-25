# CELL
"""04 - rozstawienie zasobow wsparcia: patrole, pedagodzy, psycholodzy (pokrycie przed i po).

Popyt dzienny z przekazan (fact_report_handoff). Pojemnosc dedykowana szkolom to czesc zasobu powiatu.
Trzy warianty: stan obecny, przesuniecie zasobow w obrebie wojewodztwa i z rezerwy krajowej,
oraz przesuniecie po odfiltrowaniu skoordynowanej kampanii (notebook 02).
Wszystkie parametry sa jawne i demonstracyjne. Wyjscie: derived/resources_*.csv, metrics_04.json.
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "datasets"
OUT = DATA / "derived"
OUT.mkdir(exist_ok=True)

P = {
    "patrol_dedicated_share": 0.15,      # czesc minut patroli, ktora mozna przeznaczyc na zgloszenia szkolne bez uszczerbku dla reszty sluzby
    "peak_window_start_h": 7, "peak_window_end_h": 12, "daytime_h": 12,   # poranne okno szczytu zgloszen; patrole liczone w oknie
    "ped_case_minutes": 60,              # czas obslugi jednego przekazania do pedagoga/psychologa
    "support_productive_min_per_fte": 300,  # produktywne minuty na etat dziennie
    "support_dedicated_share": 0.25,     # czesc czasu pedagogow i psychologow dostepna dla zgloszen z aplikacji
    "transfer_efficiency": 0.7,          # sprawnosc przesuniecia (dojazd, odprawa)
    "donor_max_share": 0.5,              # donor oddaje nie wiecej niz tyle swojej nadwyzki
    "reserve_team_minutes": 360,         # minuty dziennie jednego zespolu mobilnego z rezerwy krajowej
    "reserve_teams_used": 100,           # ile zespolow mobilnych (z 395 etatow) uruchamiamy jako rezerwe krajowa
}

# CELL
TZ = "Europe/Warsaw"
pat = pd.read_csv(DATA / "fact_police_patrol.csv", dtype={"county_code": str, "voivodeship_code": str})
sup = pd.read_csv(DATA / "fact_support_capacity.csv", dtype={"county_code": str, "voivodeship_code": str})
ho = pd.read_csv(DATA / "fact_report_handoff.csv", dtype={"county_code": str, "voivodeship_code": str})
flg = pd.read_csv(OUT / "campaign_report_flags.csv")
tru = pd.read_csv(DATA / "fact_report_truth.csv")
cty = pd.read_csv(DATA / "dim_county.csv", dtype={"county_code": str, "voivodeship_code": str})
voi = pd.read_csv(DATA / "dim_voivodeship.csv", dtype={"voivodeship_code": str})
ho = ho.merge(flg[["report_id", "campaign_flag", "suppressed_from_queue"]], on="report_id").merge(
    tru[["report_id", "truth_label", "is_campaign_related"]], on="report_id")
_h = pd.to_datetime(ho.handoff_ts, utc=True).dt.tz_convert(TZ)
ho["day"] = _h.dt.strftime("%Y-%m-%d")
ho["in_peak_window"] = ((_h.dt.hour >= P["peak_window_start_h"]) & (_h.dt.hour < P["peak_window_end_h"])).astype(int)
ho["voivodeship_code"] = ho.voivodeship_code.astype(str).str.zfill(2)

# CELL - rozstawienie: funkcja przesuwajaca pojemnosc w obrebie wojewodztwa, potem z rezerwy krajowej
def reallocate(df: pd.DataFrame, cap_col: str, dem_col: str, reserve_total: float = 0.0) -> pd.DataFrame:
    df = df.copy()
    df["cap_after"] = df[cap_col].astype(float)
    df["moved_in"] = 0.0
    for v, g in df.groupby("voivodeship_code"):
        surplus = (g[cap_col] - g[dem_col]).clip(lower=0) * P["donor_max_share"]
        deficit = (g[dem_col] - g[cap_col]).clip(lower=0)
        pool = surplus.sum() * P["transfer_efficiency"]
        if pool <= 0 or deficit.sum() <= 0:
            continue
        give = min(pool, deficit.sum())
        share = deficit / deficit.sum()
        gain = share * give
        df.loc[g.index, "moved_in"] += gain
        df.loc[g.index, "cap_after"] += gain - surplus * (give / pool) / P["transfer_efficiency"]
    if reserve_total > 0:
        deficit = (df[dem_col] - df["cap_after"]).clip(lower=0)
        if deficit.sum() > 0:
            gain = np.minimum(deficit, deficit / deficit.sum() * reserve_total * P["transfer_efficiency"])
            df["moved_in"] += gain
            df["cap_after"] += gain
    return df


def coverage(df, cap, dem):
    covered = np.minimum(df[dem], df[cap]).sum()
    return {"demand": float(df[dem].sum()), "covered": float(covered),
            "coverage": round(float(covered / max(1.0, df[dem].sum())), 4),
            "counties_in_deficit": int((df[dem] > df[cap]).sum()),
            "unmet": float((df[dem] - np.minimum(df[dem], df[cap])).sum())}


# CELL - patrole: dzien po dniu
base = pat.merge(cty[["county_code", "county_name"]], on="county_code")
window_share = (P["peak_window_end_h"] - P["peak_window_start_h"]) / P["daytime_h"]
base["cap_patrol"] = base.response_minutes_available * P["patrol_dedicated_share"] * window_share
res = []
detail_d0 = None
for day, g in base.groupby("date"):
    hp = ho[(ho.day == day) & (ho.recipient_code == "POL") & (ho.in_peak_window == 1)]
    dem_all = hp.groupby("county_code").patrol_minutes.sum()
    dem_filtered = hp[hp.suppressed_from_queue == 0].groupby("county_code").patrol_minutes.sum()
    g = g.set_index("county_code")
    g["dem_status_quo"] = dem_all.reindex(g.index).fillna(0)
    g["dem_filtered"] = dem_filtered.reindex(g.index).fillna(0)
    g = g.reset_index()
    reserve = P["reserve_teams_used"] * P["reserve_team_minutes"]
    r0 = coverage(g, "cap_patrol", "dem_status_quo")
    a = reallocate(g, "cap_patrol", "dem_status_quo", reserve)
    r1 = coverage(a, "cap_after", "dem_status_quo")
    f = reallocate(g, "cap_patrol", "dem_filtered", reserve)
    r2 = coverage(f, "cap_after", "dem_filtered")
    res.append({"date": day, "demand_status_quo_min": r0["demand"], "coverage_status_quo": r0["coverage"],
                "deficit_counties_status_quo": r0["counties_in_deficit"], "unmet_status_quo_min": r0["unmet"],
                "coverage_after_reallocation": r1["coverage"], "deficit_counties_after_reallocation": r1["counties_in_deficit"],
                "unmet_after_reallocation_min": r1["unmet"],
                "demand_after_filter_min": r2["demand"], "coverage_after_filter_and_reallocation": r2["coverage"],
                "deficit_counties_after_filter": r2["counties_in_deficit"], "unmet_after_filter_min": r2["unmet"]})
    if day == "2026-10-09":
        detail_d0 = a.merge(f[["county_code", "cap_after", "moved_in"]].rename(columns={"cap_after": "cap_after_filtered", "moved_in": "moved_in_filtered"}), on="county_code")
patrol = pd.DataFrame(res)
patrol.to_csv(OUT / "resources_patrol_daily.csv", index=False)
detail_d0["deficit_before_min"] = (detail_d0.dem_status_quo - detail_d0.cap_patrol).clip(lower=0).round(0)
detail_d0["deficit_after_min"] = (detail_d0.dem_status_quo - detail_d0.cap_after).clip(lower=0).round(0)
top = detail_d0.sort_values("deficit_before_min", ascending=False).head(25)[
    ["county_code", "county_name", "voivodeship_code", "dem_status_quo", "cap_patrol", "moved_in", "cap_after", "deficit_before_min", "deficit_after_min"]].round(0)
top.to_csv(OUT / "resources_patrol_top_deficit_d0.csv", index=False)
print(patrol.round(3).to_string())
print(top.head(12).to_string())

# CELL - wrazliwosc wyniku D0 na udzial pojemnosci dedykowanej szkolom i na wielkosc rezerwy krajowej
sens = []
g0 = base[base.date == "2026-10-09"].set_index("county_code")
hp0 = ho[(ho.day == "2026-10-09") & (ho.recipient_code == "POL") & (ho.in_peak_window == 1)]
g0["dem_status_quo"] = hp0.groupby("county_code").patrol_minutes.sum().reindex(g0.index).fillna(0)
g0["dem_filtered"] = hp0[hp0.suppressed_from_queue == 0].groupby("county_code").patrol_minutes.sum().reindex(g0.index).fillna(0)
g0 = g0.reset_index()
for share in (0.03, 0.05, 0.10, 0.15):
    for teams in (0, 50, 100):
        gg = g0.copy()
        gg["cap_patrol"] = gg.response_minutes_available * share * window_share
        reserve = teams * P["reserve_team_minutes"]
        b = coverage(gg, "cap_patrol", "dem_status_quo")
        a = reallocate(gg, "cap_patrol", "dem_status_quo", reserve)
        f = reallocate(gg, "cap_patrol", "dem_filtered", reserve)
        sens.append({"dedicated_share": share, "reserve_teams": teams,
                     "coverage_status_quo": b["coverage"], "deficit_counties_status_quo": b["counties_in_deficit"],
                     "coverage_reallocation": coverage(a, "cap_after", "dem_status_quo")["coverage"],
                     "deficit_counties_reallocation": coverage(a, "cap_after", "dem_status_quo")["counties_in_deficit"],
                     "coverage_filter_reallocation": coverage(f, "cap_after", "dem_filtered")["coverage"]})
sens = pd.DataFrame(sens)
sens.to_csv(OUT / "resources_patrol_sensitivity_d0.csv", index=False)
print(sens.to_string())

# CELL - pedagodzy i psycholodzy
fte = sup.pivot_table(index="county_code", columns="role", values="fte_available", aggfunc="sum").fillna(0)
fte["support_fte"] = fte.get("pedagog", 0) + fte.get("psycholog", 0)
fte = fte.reset_index().merge(cty[["county_code", "county_name", "voivodeship_code"]], on="county_code")
fte["cap_support"] = fte.support_fte * P["support_productive_min_per_fte"] * P["support_dedicated_share"]
sres = []
sdet = None
for day in sorted(ho.day.unique()):
    hp = ho[(ho.day == day) & (ho.recipient_code == "PED")]
    dem = hp.groupby("county_code").size() * P["ped_case_minutes"]
    dem_f = hp[hp.suppressed_from_queue == 0].groupby("county_code").size() * P["ped_case_minutes"]
    g = fte.set_index("county_code")
    g["dem_status_quo"] = dem.reindex(g.index).fillna(0)
    g["dem_filtered"] = dem_f.reindex(g.index).fillna(0)
    g = g.reset_index()
    r0 = coverage(g, "cap_support", "dem_status_quo")
    a = reallocate(g, "cap_support", "dem_status_quo")
    r1 = coverage(a, "cap_after", "dem_status_quo")
    sres.append({"date": day, "cases": int(len(hp)), "demand_min": r0["demand"], "coverage_status_quo": r0["coverage"],
                 "deficit_counties_status_quo": r0["counties_in_deficit"], "coverage_after_reallocation": r1["coverage"],
                 "deficit_counties_after": r1["counties_in_deficit"]})
    if day == "2026-10-09":
        sdet = a
support = pd.DataFrame(sres)
support.to_csv(OUT / "resources_support_daily.csv", index=False)
sdet["deficit_before_min"] = (sdet.dem_status_quo - sdet.cap_support).clip(lower=0).round(0)
sdet["deficit_after_min"] = (sdet.dem_status_quo - sdet.cap_after).clip(lower=0).round(0)
sdet.sort_values("deficit_before_min", ascending=False).head(25)[
    ["county_code", "county_name", "voivodeship_code", "pedagog", "psycholog", "dem_status_quo", "cap_support", "moved_in", "cap_after",
     "deficit_before_min", "deficit_after_min"]].round(0).to_csv(OUT / "resources_support_top_deficit_d0.csv", index=False)
print(support.round(3).to_string())

# CELL - marnotrawstwo: minuty patroli zuzyte na zgloszenia zwiazane z kampania
pol = ho[ho.recipient_code == "POL"]
waste = pol.groupby("truth_label").patrol_minutes.agg(["count", "sum"]).reset_index()
waste.to_csv(OUT / "resources_patrol_minutes_by_truth_label.csv", index=False)
camp_min = float(pol[pol.is_campaign_related == 1].patrol_minutes.sum())
print(waste)

# CELL
d0 = patrol[patrol.date == "2026-10-09"].iloc[0]
s0 = support[support.date == "2026-10-09"].iloc[0]
metrics = {
    "params": P,
    "patrol_d0": {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in d0.items()},
    "support_d0": {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in s0.items()},
    "patrol_sensitivity_d0": sens.to_dict("records"),
    "patrol_minutes_total": float(pol.patrol_minutes.sum()),
    "patrol_minutes_on_campaign_related": camp_min,
    "patrol_minutes_campaign_share": round(camp_min / float(pol.patrol_minutes.sum()), 4),
    "top_patrol_deficit_d0": top.head(5)[["county_name", "voivodeship_code", "dem_status_quo", "cap_patrol", "deficit_before_min", "deficit_after_min"]].to_dict("records"),
}
(OUT / "metrics_04.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(metrics, indent=2, ensure_ascii=False, default=str))
