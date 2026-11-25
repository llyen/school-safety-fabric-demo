# CELL
"""01 - klasyfikacja i scoring priorytetu zgloszenia.

Cel: sprawdzic, jak sugestia AI (klasyfikuje zgloszenie, nie osobe) ma sie do decyzji
dyzurnego i do wartosci referencyjnej, oraz jak szybko dyzurni decyduja w czasie fali.
Wejscie: fact_report, fact_report_status, fact_report_truth (ground truth tylko do ewaluacji).
Wyjscie: derived/priority_*.csv oraz derived/metrics_01.json.
"""
from pathlib import Path
import json
import re

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "datasets"
OUT = DATA / "derived"
OUT.mkdir(exist_ok=True)

PRI = ["NISKI", "SREDNI", "WYSOKI", "KRYTYCZNY"]
RANK = {p: i + 1 for i, p in enumerate(PRI)}
TZ = "Europe/Warsaw"

# CELL
rep = pd.read_json(DATA / "fact_report.jsonl", lines=True, dtype={"county_code": str, "voivodeship_code": str})
sta = pd.read_csv(DATA / "fact_report_status.csv", dtype={"voivodeship_code": str})
tru = pd.read_csv(DATA / "fact_report_truth.csv")
d = rep.merge(sta, on="report_id").merge(tru, on="report_id")
for c in ("report_ts", "decision_ts", "first_handoff_ts"):
    d[c] = pd.to_datetime(d[c], utc=True, errors="coerce").dt.tz_convert(TZ)
d["day"] = d.report_ts.dt.date
d["ai_rank"] = d.ai_priority_code.map(RANK)
d["duty_rank"] = d.duty_priority_code.map(RANK)
d["true_rank"] = d.true_severity.astype(int)
d["handoff_delay_min"] = (d.first_handoff_ts - d.report_ts).dt.total_seconds() / 60
print(f"zgloszen: {len(d)}, zakres {d.report_ts.min()} .. {d.report_ts.max()}")

# CELL - scoring tekstowy (jawne reguly, niezalezne od metadanych szablonu)
LEXICON = [
    (r"\bn[oó]ż|nożyk|scyzoryk|broń|broni|ostre narzędzie", 0.30, "weapon_mention"),
    (r"bomb|wybuch|ładunek|detonac", 0.30, "bomb_mention"),
    (r"zemści|zrobi coś|nikt nie wyjdzie|nie zapomni|będzie głośno|załatwi|zapowiada|zapowiedź|zapowiedział|grozi", 0.25, "threat_intent"),
    (r"\bo \d{1,2}:\d{2}\b|jutro|pojutrze|dziś|w (poniedziałek|piątek|środę|czwartek)|we wtorek", 0.12, "specific_time"),
    (r"zrzut ekranu|mam jego wiadomość|zdjęcie", 0.10, "evidence_attached"),
    (r"pożegnaln|nie odbiera telefonu|nie wstawał|uciekła", 0.35, "life_risk"),
    (r"nauczyciel", 0.08, "named_target"),
    (r"obcy mężczyzna", 0.25, "stranger"),
    (r"żart|chyba|może to|nic tam groźnego", -0.15, "joke_context"),
]
BASE_BY_CAT = {"BRON": 0.20, "GROZBY": 0.20, "SAMOUSZKODZENIE": 0.20, "PRZEMOC": 0.08, "TRESCI_SIEC": 0.05, "INNE": 0.03}


def lex_score(row) -> float:
    t = row.report_text.lower()
    s = BASE_BY_CAT.get(row.category_code, 0.05)
    for pat, w, _ in LEXICON:
        if re.search(pat, t):
            s += w
    return float(min(1.0, max(0.0, s)))


def to_priority(s: float) -> str:
    return "KRYTYCZNY" if s >= 0.70 else "WYSOKI" if s >= 0.50 else "SREDNI" if s >= 0.30 else "NISKI"


d["lex_score"] = d.apply(lex_score, axis=1)
d["lex_priority_code"] = d.lex_score.map(to_priority)
d["lex_rank"] = d.lex_priority_code.map(RANK)

# CELL - jakosc klasyfikacji: AI, leksykon i decyzja dyzurnego wobec wartosci referencyjnej
def quality(col: str) -> dict:
    p, y = d[col], d.true_rank
    crit_true = d.true_rank == 4
    crit_pred = p == 4
    tp = int((crit_true & crit_pred).sum())
    return {
        "exact_match": round(float((p == y).mean()), 4),
        "within_one": round(float(((p - y).abs() <= 1).mean()), 4),
        "critical_precision": round(tp / max(1, int(crit_pred.sum())), 4),
        "critical_recall": round(tp / max(1, int(crit_true.sum())), 4),
        "critical_predicted": int(crit_pred.sum()),
        "critical_true": int(crit_true.sum()),
    }


qual = {"ai": quality("ai_rank"), "duty": quality("duty_rank"), "lexicon": quality("lex_rank")}
real = d[d.truth_label == "real_critical_wave"]  # R: realne krytyczne ukryte w fali
qual["real_critical_in_wave"] = {
    "n": int(len(real)),
    "ai_critical_or_high": int((real.ai_rank >= 3).sum()),
    "ai_critical": int((real.ai_rank == 4).sum()),
    "duty_critical_or_high": int((real.duty_rank >= 3).sum()),
}
print(json.dumps(qual, indent=2, ensure_ascii=False))

# CELL - zgodnosc AI i dyzurnego, macierz pomylek
conf = pd.crosstab(d.ai_priority_code, d.duty_priority_code).reindex(index=PRI, columns=PRI, fill_value=0)
conf.to_csv(OUT / "priority_confusion_ai_vs_duty.csv")
d["agree"] = (d.ai_rank == d.duty_rank).astype(int)
d["override"] = np.sign(d.duty_rank - d.ai_rank)
agree = {
    "agreement_all": round(float(d.agree.mean()), 4),
    "duty_raised": int((d.override > 0).sum()),
    "duty_lowered": int((d.override < 0).sum()),
    "agreement_by_ai_priority": {p: round(float(d[d.ai_priority_code == p].agree.mean()), 4) for p in PRI},
}
by_label = d.groupby("truth_label").agg(
    n=("report_id", "size"), agreement=("agree", "mean"),
    ai_critical=("ai_rank", lambda s: int((s == 4).sum())),
    duty_critical=("duty_rank", lambda s: int((s == 4).sum())),
    median_delay_min=("decision_delay_min", "median"),
).round(3)
by_label.to_csv(OUT / "priority_by_truth_label.csv")
print(conf)
print(by_label)

# CELL - tempo reakcji: opoznienie decyzji dyzurnego wzgledem zgloszenia
def delay_stats(g):
    return pd.Series({
        "n": len(g),
        "median_min": g.decision_delay_min.median(),
        "p90_min": g.decision_delay_min.quantile(.9),
        "share_over_10min": (g.decision_delay_min > 10).mean(),
        "critical_n": int((g.duty_rank == 4).sum()),
        "critical_median_min": g[g.duty_rank == 4].decision_delay_min.median(),
        "critical_share_over_10min": (g[g.duty_rank == 4].decision_delay_min > 10).mean(),
    })


by_day = d.groupby("day").apply(delay_stats, include_groups=False).round(3)
by_day.to_csv(OUT / "priority_reaction_by_day.csv")
maz = d[(d.voivodeship_code == "14")]
by_day_maz = maz.groupby("day").apply(delay_stats, include_groups=False).round(3)
by_day_maz.to_csv(OUT / "priority_reaction_mazowieckie_by_day.csv")
by_vc = d.groupby("voivodeship_code").apply(delay_stats, include_groups=False).round(3)
by_vc.to_csv(OUT / "priority_reaction_by_voivodeship.csv")
print(by_day_maz)

real_rows = real.sort_values("report_ts")[["report_id", "report_ts", "voivodeship_code", "ai_priority_code",
                                           "duty_priority_code", "decision_delay_min", "queue_len_at_decision_start"]]
real_rows.to_csv(OUT / "priority_real_critical_reaction.csv", index=False)

# CELL - korelacja dlugosci kolejki z opoznieniem (mechanizm "ukrycia w fali")
d["queue_bin"] = pd.cut(d.queue_len_at_decision_start, [-1, 3, 10, 30, 100, 10_000], labels=["0-3", "4-10", "11-30", "31-100", ">100"])
qb = d.groupby("queue_bin", observed=True).agg(n=("report_id", "size"), median_delay=("decision_delay_min", "median"),
                                               p90_delay=("decision_delay_min", lambda s: s.quantile(.9))).round(2)
qb.to_csv(OUT / "priority_delay_by_queue_length.csv")
print(qb)

# CELL
d0 = d[d.day == pd.Timestamp("2026-10-09").date()]
d0_crit = d0[d0.duty_rank == 4]
metrics = {
    "reports": int(len(d)),
    "quality": qual,
    "agreement": agree,
    "delay_all_median_min": round(float(d.decision_delay_min.median()), 2),
    "delay_all_p90_min": round(float(d.decision_delay_min.quantile(.9)), 2),
    "d0_reports": int(len(d0)),
    "d0_critical_by_duty": int(len(d0_crit)),
    "d0_critical_median_delay_min": round(float(d0_crit.decision_delay_min.median()), 1),
    "d0_critical_share_over_10min": round(float((d0_crit.decision_delay_min > 10).mean()), 4),
    "mazowieckie_d0_median_delay_min": round(float(maz[maz.day == pd.Timestamp("2026-10-09").date()].decision_delay_min.median()), 1),
    "bs4826": d[d.report_id == "BS-4826"][["report_ts", "decision_delay_min", "ai_priority_code", "duty_priority_code",
                                          "queue_len_at_decision_start"]].astype(str).to_dict("records")[0],
    "real_critical_decision_delay_min": {
        "median": round(float(real.decision_delay_min.median()), 1),
        "max": round(float(real.decision_delay_min.max()), 1),
        "over_60min": int((real.decision_delay_min > 60).sum()),
    },
}
(OUT / "metrics_01.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(metrics, indent=2, ensure_ascii=False))
