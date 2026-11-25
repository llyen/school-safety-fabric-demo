# CELL
"""05 - analizy what-if.

A. Kolejka dyzurnych: ponowna symulacja obslugi zgloszen (priorytet AI, FIFO w klasie, dyzurni jak w generatorze)
   dla wariantow: stan obecny, dodatkowy dyzurny, szybsza kwalifikacja (-30% czasu), kolejka swiadoma kampanii
   (zgloszenia z klastra kampanii obslugiwane zbiorczo, zgloszenia z zabezpieczenia na szczycie kolejki).
B. Komunikat SPO-3 do rodzicow: ekspozycja (zdarzenia Z18 i polaczenia 112 zwiazane ze szkolami po godzinie komunikatu)
   dla trzech terminow. Wplyw komunikatu na te wielkosci to ZALOZENIE (elastycznosc), a nie wynik pomiaru.
Wyjscie: derived/whatif_*.csv, metrics_05.json.
"""
from pathlib import Path
import heapq
import json
import math

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "datasets"
OUT = DATA / "derived"
OUT.mkdir(exist_ok=True)
TZ = "Europe/Warsaw"
SEED = 42

SERVICE_MIN = {4: 6.0, 3: 4.5, 2: 3.0, 1: 2.0}   # srednie minuty obslugi wg priorytetu AI (jak w generatorze)
DUTY_DAY = {"14": 3}                              # domyslnie 2 w dzien, mazowieckie 3
DUTY_NIGHT = {}                                   # domyslnie 1 w nocy
BATCH_SERVICE_MIN = 10.0                          # obsluga zbiorcza jednego klastra w oknie
BATCH_WINDOW_H = 6

# CELL
rep = pd.read_json(DATA / "fact_report.jsonl", lines=True, dtype={"county_code": str, "voivodeship_code": str})
sta = pd.read_csv(DATA / "fact_report_status.csv", dtype={"voivodeship_code": str})
tru = pd.read_csv(DATA / "fact_report_truth.csv")
flg = pd.read_csv(OUT / "campaign_report_flags.csv")
d = rep.merge(sta[["report_id", "decision_delay_min"]], on="report_id").merge(tru, on="report_id").merge(flg, on="report_id")
d["ts"] = pd.to_datetime(d.timestamp, utc=True).dt.tz_convert(TZ)
d["voivodeship_code"] = d.voivodeship_code.astype(str).str.zfill(2)
d["ai_rank"] = d.ai_priority_code.map({"NISKI": 1, "SREDNI": 2, "WYSOKI": 3, "KRYTYCZNY": 4})
d["minute"] = (d.ts - pd.Timestamp("2026-10-06 00:00", tz=TZ)).dt.total_seconds() / 60
d["hour_of_day"] = d.ts.dt.hour

# CELL - symulator kolejki
def servers(vc: str, minute: float, extra_day: int) -> int:
    hod = int((minute // 60) % 24)
    if 6 <= hod < 22:
        return DUTY_DAY.get(vc, 2) + extra_day
    return DUTY_NIGHT.get(vc, 1)


def next_active(vc, j, t, extra_day):
    for _ in range(30):
        if j < servers(vc, t, extra_day):
            return t
        t = (t // 60 + 1) * 60
    return t


def simulate(items: pd.DataFrame, vc: str, rng, extra_day=0, speed=1.0, prio_col="prio", svc_col="svc_min") -> dict:
    items = items.sort_values("minute")
    mins = items.minute.to_numpy()
    prio = items[prio_col].to_numpy()
    svc_mean = items[svc_col].to_numpy()
    ids = items.index.to_numpy()
    k = max(DUTY_DAY.get(vc, 2) + extra_day, DUTY_NIGHT.get(vc, 1))
    free = [0.0] * k
    waiting, i, n = [], 0, len(items)
    done = {}
    while i < n or waiting:
        starts = [next_active(vc, j, free[j], extra_day) for j in range(k)]
        jb = min(range(k), key=lambda j: starts[j])
        best = starts[jb]
        if not waiting:
            best = max(best, mins[i])
        while i < n and mins[i] <= best:
            heapq.heappush(waiting, (-prio[i], mins[i], i))
            i += 1
        _, _, idx = heapq.heappop(waiting)
        svc = float(rng.lognormal(math.log(max(svc_mean[idx], 0.1) * speed) - .08, .4))
        free[jb] = best + svc
        done[ids[idx]] = best + svc - mins[idx]
    return done


def run_variant(name: str, extra_day=0, speed=1.0, aware=False) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    x = d.copy()
    x["svc_min"] = x.ai_rank.map(SERVICE_MIN)
    x["prio"] = x.ai_rank
    x["delay"] = np.nan
    if aware:
        keep = x.keep_for_human == 1
        # zabezpieczenie: zgloszenie z cechami konkretnego zagrozenia ma pierwszenstwo
        x.loc[keep & x.guard_text, "prio"] = 5
        for vc, g in x[keep].groupby("voivodeship_code"):
            res = simulate(g, vc, rng, extra_day, speed)
            x.loc[list(res.keys()), "delay"] = list(res.values())
        # klaster kampanii: jedna pozycja zbiorcza na klaster i okno, opoznienie liczone do konca obslugi pozycji zbiorczej
        sup = x[x.suppressed_from_queue == 1].copy()
        sup["win"] = (sup.minute // (BATCH_WINDOW_H * 60)).astype(int)
        for (vc, cid, w), g in sup.groupby(["voivodeship_code", "cluster_id", "win"]):
            x.loc[g.index, "delay"] = (g.minute.max() - g.minute) + BATCH_SERVICE_MIN
    else:
        for vc, g in x.groupby("voivodeship_code"):
            res = simulate(g, vc, rng, extra_day, speed)
            x.loc[list(res.keys()), "delay"] = list(res.values())
    x["variant"] = name
    return x


variants = {
    "A0_status_quo": dict(),
    "A1_plus_1_duty_officer_day": dict(extra_day=1),
    "A2_plus_2_duty_officers_day": dict(extra_day=2),
    "A3_qualification_30pct_faster": dict(speed=0.7),
    "A4_campaign_aware_queue": dict(aware=True),
    "A5_campaign_aware_plus_1_officer": dict(aware=True, extra_day=1),
}
runs = {k: run_variant(k, **v) for k, v in variants.items()}

# CELL - metryki wariantow
D0 = pd.Timestamp("2026-10-09").date()


def summarize(x: pd.DataFrame) -> dict:
    kept = x[x.keep_for_human == 1]
    real = x[x.truth_label == "real_critical_wave"]
    realall = x[x.is_real_critical == 1]
    gc = kept[(kept.ai_rank == 4)]
    d0 = x[x.ts.dt.date == D0]
    maz0 = d0[d0.voivodeship_code == "14"]
    anchor = x[x.report_id == "BS-4826"].delay.iloc[0]
    return {
        "median_delay_all_min": round(float(x.delay.median()), 1),
        "median_delay_kept_for_human_min": round(float(kept.delay.median()), 1),
        "real_critical_wave_n": int(len(real)),
        "real_critical_wave_median_delay_min": round(float(real.delay.median()), 1),
        "real_critical_wave_max_delay_min": round(float(real.delay.max()), 1),
        "real_critical_wave_over_10min": int((real.delay > 10).sum()),
        "real_critical_wave_over_60min": int((real.delay > 60).sum()),
        "real_critical_all_n": int(len(realall)),
        "real_critical_all_over_60min": int((realall.delay > 60).sum()),
        "ai_critical_kept_over_10min_share": round(float((gc.delay > 10).mean()), 4),
        "mazowieckie_d0_median_delay_min": round(float(maz0.delay.median()), 1),
        "mazowieckie_d0_kept_median_delay_min": round(float(maz0[maz0.keep_for_human == 1].delay.median()), 1),
        "bs4826_delay_min": round(float(anchor), 1),
    }


tab = pd.DataFrame({k: summarize(v) for k, v in runs.items()}).T
tab.to_csv(OUT / "whatif_queue_variants.csv")
print(tab.T.to_string())
pd.concat(runs.values())[["variant", "report_id", "delay"]].to_csv(OUT / "whatif_queue_delays.csv", index=False)

# CELL - B. komunikat SPO-3: ekspozycja po godzinie komunikatu
hot = pd.read_json(DATA / "fact_hotline_load.jsonl", lines=True)
hot["ts"] = pd.to_datetime(hot.timestamp, utc=True).dt.tz_convert(TZ)
dis = pd.read_json(DATA / "fact_disorder_event.jsonl", lines=True)
dis["ts"] = pd.to_datetime(dis.timestamp, utc=True).dt.tz_convert(TZ)
# punkt odniesienia T: pierwsze zgloszenie z klastra kampanii po godz. 06:00 w dniu D0 (zaczyna sie szczyt Z18 i obciazenia 112)
k2 = d[(d.campaign_flag == 1) & (d.ts >= pd.Timestamp("2026-10-09 06:00", tz=TZ))].ts.min()
ELAST = (0.10, 0.20, 0.30)  # zalozone zmniejszenie liczby zdarzen po komunikacie
rows = []
for label, delay_min in (("T+30 min", 30), ("T+2 h", 120), ("T+4 h", 240), ("T+8 h", 480)):
    t_msg = k2 + pd.Timedelta(minutes=delay_min)
    ev = int((dis.ts >= t_msg).sum())
    calls = int(hot[hot.ts >= t_msg].calls_112_school_related.sum())
    sch_calls = int(hot[hot.ts >= t_msg].school_phone_calls.sum())
    pol_ev = int(((dis.ts >= t_msg) & (dis.police_required == 1)).sum())
    rows.append({"message_at": label, "message_ts": str(t_msg), "disorder_events_after": ev, "police_required_events_after": pol_ev,
                 "school_related_112_calls_after": calls, "school_phone_calls_after": sch_calls,
                 **{f"events_avoided_elasticity_{int(e*100)}pct": round(ev * e, 1) for e in ELAST},
                 **{f"calls_112_avoided_elasticity_{int(e*100)}pct": round(calls * e, 1) for e in ELAST}})
spo3 = pd.DataFrame(rows)
spo3.to_csv(OUT / "whatif_spo3_message_timing.csv", index=False)
print(spo3.T.to_string())

# CELL
metrics = {
    "queue_variants": {k: v for k, v in tab.to_dict("index").items()},
    "spo3_message": {"reference_T_first_campaign_report_d0": str(k2), "elasticity_is_assumption": True, "rows": rows},
    "notes": "Wariant A0 to ponowna symulacja z innym ziarnem losowan czasu obslugi niz w generatorze, wiec liczby moga sie nieco roznic od notebooka 01.",
}
(OUT / "metrics_05.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
