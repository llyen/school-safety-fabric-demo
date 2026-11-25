# CELL
"""03 - Krajowy Indeks Zagrozenia Szkolnego (KIZS) i rekomendacja eskalacji.

KIZS 0-100 liczony co godzine dla kazdego wojewodztwa (okno 6 h) z pieciu skladnikow:
rzeczywiste sygnaly (zgloszenia zachowane dla czlowieka, priorytet WYSOKI i wyzej),
presja kampanii, obciazenie 112, zalegle krytyczne bez decyzji dyzurnego >10 min, zdarzenia porzadkowe Z18.
Progi i wagi to parametry demonstracyjne, wymagaja kalibracji na danych RCB.
Wejscie: wyniki notebooka 02 (campaign_report_flags.csv). Wyjscie: derived/kizs_*.csv, metrics_03.json.
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "datasets"
OUT = DATA / "derived"
OUT.mkdir(exist_ok=True)
TZ = "Europe/Warsaw"
WINDOW_H = 6

# Parametry (jawne): wagi skladnikow i "pelna skala" skladnika (wartosc dajaca 100%)
WEIGHTS = {"signals": 0.30, "campaign": 0.20, "hotline": 0.20, "backlog": 0.20, "disorder": 0.10}
CAPS = {"signals": 12.0, "campaign": 60.0, "hotline": 2.0, "backlog": 25.0, "disorder": 5.0}
# Progi eskalacji
TH = {
    "county_signal": 1,                  # powiat: zachowane krytyczne zgloszenie bez decyzji >10 min
    "voiv_kizs": 45, "voiv_hours": 2,     # wojewoda / kurator: KIZS >= 45 przez 2 kolejne godziny
    "minister_campaign_24h": 150, "minister_voiv_24h": 8,
    "rzzk_campaign_24h": 400, "rzzk_voiv_24h": 12, "rzzk_extra": 1,
}

# CELL
rep = pd.read_json(DATA / "fact_report.jsonl", lines=True, dtype={"county_code": str, "voivodeship_code": str})
sta = pd.read_csv(DATA / "fact_report_status.csv", dtype={"voivodeship_code": str})
flg = pd.read_csv(OUT / "campaign_report_flags.csv")
tru = pd.read_csv(DATA / "fact_report_truth.csv")
d = rep.merge(sta[["report_id", "decision_ts"]], on="report_id").merge(flg, on="report_id").merge(tru[["report_id", "truth_label"]], on="report_id")
d["ts"] = pd.to_datetime(d.timestamp, utc=True).dt.tz_convert(TZ)
d["decision_ts"] = pd.to_datetime(d.decision_ts, utc=True).dt.tz_convert(TZ)
d["ai_rank"] = d.ai_priority_code.map({"NISKI": 1, "SREDNI": 2, "WYSOKI": 3, "KRYTYCZNY": 4})
d["genuine_signal"] = ((d.keep_for_human == 1) & (d.ai_rank >= 3)).astype(int)
d["genuine_critical"] = ((d.keep_for_human == 1) & (d.ai_rank == 4)).astype(int)

hot = pd.read_json(DATA / "fact_hotline_load.jsonl", lines=True, dtype={"voivodeship_code": str})
hot["voivodeship_code"] = hot.voivodeship_code.str.zfill(2)
hot["ts"] = pd.to_datetime(hot.timestamp, utc=True).dt.tz_convert(TZ)
dis = pd.read_json(DATA / "fact_disorder_event.jsonl", lines=True, dtype={"voivodeship_code": str, "county_code": str})
dis["voivodeship_code"] = dis.voivodeship_code.str.zfill(2)
dis["ts"] = pd.to_datetime(dis.timestamp, utc=True).dt.tz_convert(TZ)
sch = pd.read_csv(DATA / "dim_school.csv", dtype={"voivodeship_code": str, "county_code": str})
voiv = pd.read_csv(DATA / "dim_voivodeship.csv", dtype={"voivodeship_code": str})
students = sch.groupby("voivodeship_code").students.sum()
d["voivodeship_code"] = d.voivodeship_code.astype(str).str.zfill(2)

hours = pd.date_range("2026-10-06 00:00", "2026-10-16 23:00", freq="h", tz=TZ)
vcodes = sorted(d.voivodeship_code.unique())

# CELL - KIZS godzinowy per wojewodztwo
rows = []
for h in hours:
    lo = h - pd.Timedelta(hours=WINDOW_H - 1)
    hi = h + pd.Timedelta(hours=1)
    win = d[(d.ts >= lo) & (d.ts < hi)]
    hw = hot[(hot.ts >= lo) & (hot.ts < hi)]
    dw = dis[(dis.ts >= lo) & (dis.ts < hi)]
    # zalegle krytyczne: zachowane dla czlowieka, ai KRYTYCZNY, decyzja pozniej niz 10 min od zgloszenia i jeszcze nie zapadla w chwili h
    pend = d[(d.genuine_critical == 1) & (d.ts + pd.Timedelta(minutes=10) <= hi) & (d.decision_ts > hi)]
    for v in vcodes:
        w = win[win.voivodeship_code == v]
        sc = {
            "signals": float(w.genuine_signal.sum()),
            "campaign": float(w.campaign_flag.sum()),
            "hotline": float(hw[hw.voivodeship_code == v].load_ratio.max()) if (hw.voivodeship_code == v).any() else 0.0,
            "backlog": float((pend.voivodeship_code == v).sum()),
            "disorder": float((dw.voivodeship_code == v).sum()),
        }
        kizs = 100 * sum(WEIGHTS[k] * min(1.0, np.nan_to_num(sc[k]) / CAPS[k]) for k in WEIGHTS)
        rows.append({"hour": h, "voivodeship_code": v, **{f"c_{k}": round(x, 3) for k, x in sc.items()}, "kizs": round(kizs, 1)})
k = pd.DataFrame(rows).merge(voiv[["voivodeship_code", "voivodeship_name"]], on="voivodeship_code")
k.to_csv(OUT / "kizs_voivodeship_hourly.csv", index=False)
print(k.groupby("voivodeship_name").kizs.agg(["mean", "max"]).round(1).sort_values("max", ascending=False))

# CELL - KIZS dzienny (maksimum dnia) i na poziomie powiatu (max dobowy, uproszczony: bez zalegloci i 112)
k["day"] = k.hour.dt.date
daily = k.groupby(["day", "voivodeship_code", "voivodeship_name"]).kizs.agg(["max", "mean"]).round(1).reset_index()
daily.columns = ["day", "voivodeship_code", "voivodeship_name", "kizs_max", "kizs_mean"]
daily.to_csv(OUT / "kizs_voivodeship_daily.csv", index=False)

d["day"] = d.ts.dt.date
cd = d.groupby(["day", "county_code", "voivodeship_code"]).agg(
    reports=("report_id", "size"), genuine_signals=("genuine_signal", "sum"),
    campaign_reports=("campaign_flag", "sum")).reset_index()
cs = sch.groupby("county_code").students.sum()
cd["students"] = cd.county_code.map(cs)
cd["signals_per_10k_students"] = (10000 * cd.genuine_signals / cd.students).round(2)
cd["campaign_per_10k_students"] = (10000 * cd.campaign_reports / cd.students).round(2)
cd["county_kizs"] = (100 * (0.6 * np.minimum(1, cd.signals_per_10k_students / 6) + 0.4 * np.minimum(1, cd.campaign_per_10k_students / 40))).round(1)
cd.to_csv(OUT / "kizs_county_daily.csv", index=False)

# CELL - eskalacja: wartosci krajowe w kroku godzinowym
nat_rows = []
for h in hours:
    hi = h + pd.Timedelta(hours=1)
    w24 = d[(d.ts >= hi - pd.Timedelta(hours=24)) & (d.ts < hi)]
    camp = w24[w24.campaign_flag == 1]
    real_crit = int(w24.genuine_critical.sum())
    hw = hot[(hot.ts >= hi - pd.Timedelta(hours=6)) & (hot.ts < hi)]
    overload_v = int((hw.groupby("voivodeship_code").load_ratio.max() > 1.5).sum())
    dz = int(((dis.ts >= hi - pd.Timedelta(hours=24)) & (dis.ts < hi)).sum())
    kk = k[k.hour == h]
    nat_rows.append({
        "hour": h, "campaign_24h": len(camp), "campaign_voivodeships_24h": camp.voivodeship_code.nunique(),
        "genuine_critical_24h": real_crit, "voivodeships_112_over_1_5": overload_v, "disorder_24h": dz,
        "kizs_national_mean": round(kk.kizs.mean(), 1), "kizs_max_voiv": kk.kizs.max(),
        "voivodeships_kizs_ge_threshold": int((kk.kizs >= TH["voiv_kizs"]).sum()),
    })
nat = pd.DataFrame(nat_rows)
nat["rec_minister"] = (nat.campaign_24h >= TH["minister_campaign_24h"]) & (nat.campaign_voivodeships_24h >= TH["minister_voiv_24h"])
nat["rec_rzzk"] = (nat.campaign_24h >= TH["rzzk_campaign_24h"]) & (nat.campaign_voivodeships_24h >= TH["rzzk_voiv_24h"]) & (
    (nat.genuine_critical_24h >= TH["rzzk_extra"]) | (nat.voivodeships_112_over_1_5 >= 1) | (nat.disorder_24h >= 10))
nat["rec_voivode_any"] = nat.voivodeships_kizs_ge_threshold >= 1
nat.to_csv(OUT / "kizs_national_hourly.csv", index=False)

# CELL - pierwsze przekroczenia progow w kazdym wojewodztwie (wojewoda/kurator) i krajowo
k = k.sort_values(["voivodeship_code", "hour"])
k["hit"] = (k.kizs >= TH["voiv_kizs"]).astype(int)
k["run"] = k.groupby("voivodeship_code").hit.transform(lambda s: s.groupby((s != s.shift()).cumsum()).cumsum()) * k.hit
first_voiv = (k[k.run >= TH["voiv_hours"]].groupby(["voivodeship_code", "voivodeship_name"]).hour.min().reset_index()
              .rename(columns={"hour": "recommend_ts"}).sort_values("recommend_ts"))
first_voiv.to_csv(OUT / "kizs_voivodeship_first_recommendation.csv", index=False)
print(first_voiv)

def first(col):
    s = nat[nat[col]]
    return None if s.empty else s.hour.min()


t_min, t_rzzk = first("rec_minister"), first("rec_rzzk")
t_voiv = None if first_voiv.empty else first_voiv.recommend_ts.min()
# pierwsze zgloszenie, ktore weszlo do klastra kampanii
camp_first = d[d.campaign_flag == 1].ts.min()
RZZK_SCEN = pd.Timestamp("2026-10-09 14:00", tz=TZ)
MIN_SCEN = pd.Timestamp("2026-10-09 09:10", tz=TZ)
VOIV_SCEN = pd.Timestamp("2026-10-09 03:50", tz=TZ)

def minutes(a, b):
    return None if a is None or b is None else round((b - a).total_seconds() / 60, 0)


anchor = d[d.report_id == "BS-4826"].iloc[0]
# CELL - wrazliwosc czasu rekomendacji RZZK na prog liczby zgloszen kampanii w 24 h
sens = []
for thr in (200, 300, 400, 600, 800):
    m = (nat.campaign_24h >= thr) & (nat.campaign_voivodeships_24h >= TH["rzzk_voiv_24h"]) & (
        (nat.genuine_critical_24h >= TH["rzzk_extra"]) | (nat.voivodeships_112_over_1_5 >= 1) | (nat.disorder_24h >= 10))
    t = nat[m].hour.min() if m.any() else None
    sens.append({"rzzk_campaign_24h_threshold": thr, "recommend_ts": None if t is None else str(t),
                 "lead_before_rzzk_convened_min": minutes(t, RZZK_SCEN)})
pd.DataFrame(sens).to_csv(OUT / "kizs_rzzk_threshold_sensitivity.csv", index=False)
print(pd.DataFrame(sens))

# CELL - zapis
metrics = {
    "params": {"window_h": WINDOW_H, "weights": WEIGHTS, "caps": CAPS, "thresholds": TH},
    "first_campaign_flagged_report_ts": str(camp_first),
    "first_voivodeship_recommendation_ts": str(t_voiv),
    "first_minister_recommendation_ts": str(t_min),
    "first_rzzk_recommendation_ts": str(t_rzzk),
    "scenario_rzzk_convened_ts": str(RZZK_SCEN),
    "rzzk_recommendation_lead_min": minutes(t_rzzk, RZZK_SCEN),
    "minister_recommendation_lead_min": minutes(t_min, MIN_SCEN),
    "voivodeship_recommendation_lead_min": minutes(t_voiv, VOIV_SCEN),
    "minutes_first_campaign_report_to_rzzk_recommendation": minutes(camp_first, t_rzzk),
    "bs4826_to_rzzk_recommendation_min": minutes(anchor.ts, t_rzzk),
    "rzzk_threshold_sensitivity": sens,
    "voivodeships_with_recommendation": int(len(first_voiv)),
    "kizs_national_max_mean": float(nat.kizs_national_mean.max()),
    "kizs_peak_hour": str(nat.loc[nat.kizs_national_mean.idxmax(), "hour"]),
    "kizs_top_voivodeship_peak": k.loc[k.kizs.idxmax(), ["voivodeship_name", "hour", "kizs"]].astype(str).to_dict(),
    "county_kizs_top_d0": cd[cd.day == pd.Timestamp("2026-10-09").date()].sort_values("county_kizs", ascending=False).head(5)[
        ["county_code", "genuine_signals", "campaign_reports", "county_kizs"]].to_dict("records"),
}
(OUT / "metrics_03.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(metrics, indent=2, ensure_ascii=False, default=str))
