"""Generator danych syntetycznych: scenariusz FALA ZAGROZEN SZKOLNYCH (D-3 ... D+7).

Wszystkie dane sa w 100% syntetyczne i powtarzalne (seed=42). Nie stanowia danych
operacyjnych zadnej instytucji. Szkoly, tresci zgloszen i osoby nie istnieja.

Uzycie:
    python generate_datasets.py
"""
from __future__ import annotations

import csv
import heapq
import json
import math
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

import text_bank as tb

SEED = 42
random.seed(SEED)
rng = np.random.default_rng(SEED)

ROOT = Path(__file__).resolve().parent
REF = ROOT / "reference"
OUT = ROOT / "datasets"
(OUT / "derived").mkdir(parents=True, exist_ok=True)

TZ = timezone(timedelta(hours=2))
T0 = datetime(2026, 10, 6, 0, 0, tzinfo=TZ)          # D-3 00:00
D0 = datetime(2026, 10, 9, 0, 0, tzinfo=TZ)          # D0 = piatek
END = datetime(2026, 10, 16, 23, 59, tzinfo=TZ)      # D+7
N_HOURS = 11 * 24
N_BINS = N_HOURS * 4
EVENT_ID = "FALA_ZAGROZEN_SZKOLNYCH_2026"
N_SCHOOLS = 4200
ANCHOR_BS = 4826
RZZK_TS = datetime(2026, 10, 9, 14, 0, tzinfo=TZ)

# Parametry modelu dyzurow (zalozenia scenariusza, opisane w LUKI_I_PYTANIA.md)
DUTY_DAY = {"14": 3}          # liczba dyzurnych w dzien (06-22), domyslnie 2
DUTY_NIGHT = {}               # w nocy domyslnie 1
SERVICE_MIN = {"KRYTYCZNY": 6.0, "WYSOKI": 4.5, "SREDNI": 3.0, "NISKI": 2.0}

PRIORITIES = ["NISKI", "SREDNI", "WYSOKI", "KRYTYCZNY"]
PRANK = {p: i + 1 for i, p in enumerate(PRIORITIES)}


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(name: str, rows: list[dict], cols: list[str] | None = None) -> None:
    cols = cols or list(rows[0].keys())
    with (OUT / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def write_jsonl(name: str, rows: list[dict]) -> None:
    with (OUT / name).open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def hour_idx(day_off: int, hour: int) -> int:
    return (day_off + 3) * 24 + hour


# ----------------------------------------------------------------------------
# 1. Geografia
# ----------------------------------------------------------------------------
voivs = read_csv(REF / "dim_voivodeship.csv")
counties = read_csv(REF / "dim_powiat.csv")
munis = read_csv(REF / "dim_gmina.csv")

# Powiaty grodzkie (miasta) w danych demo. Nazwy sa kodowe i fikcyjne, wspolrzedne pochodza
# z syntetycznego pliku reference. Zostaje tylko liczba ludnosci jako waga losowania.
# kod powiatu -> ludnosc
SEAT_POP = {
    "0203": 641000,
    "0401": 345000,
    "0601": 335000,
    "0801": 140000,
    "1001": 655000,
    "1201": 800000,
    "1401": 1860000,
    "1402": 205000,
    "1403": 77000,
    "1404": 115000,
    "1405": 44000,
    "1406": 51000,
    "1601": 127000,
    "1801": 197000,
    "2001": 295000,
    "2201": 486000,
    "2401": 290000,
    "2601": 190000,
    "2801": 170000,
    "3001": 540000,
    "3201": 395000,
}


def seat_name(code: str) -> str:
    return f"Miasto M-{code}"


def seat_locative(code: str) -> str:
    return f"Mieście M-{code}"


county_rows = []
for c in counties:
    code = c["powiat_code"]
    row = {
        "county_code": code, "county_name": f"powiat P-{code}", "voivodeship_code": c["voivodeship_code"],
        "population": int(c["population"]), "area_km2": float(c["area_km2"]),
        "lat": float(c["lat"]), "lon": float(c["lon"]), "is_seat_city": 0, "locative": "",
    }
    if code in SEAT_POP:
        row.update(county_name=seat_name(code), population=SEAT_POP[code], is_seat_city=1, locative=seat_locative(code))
    county_rows.append(row)
county_by_code = {c["county_code"]: c for c in county_rows}

muni_rows = []
first_in_county: set[str] = set()
for m in munis:
    cc = m["powiat_code"]
    row = {
        "municipality_code": m["gmina_code"], "municipality_name": f"Gmina G-{m['gmina_code']}", "county_code": cc,
        "municipality_type": m["gmina_type"], "population": int(m["population"]),
        "lat": float(m["lat"]), "lon": float(m["lon"]),
    }
    if cc in SEAT_POP and cc not in first_in_county:
        first_in_county.add(cc)
        row.update(municipality_name=seat_name(cc), municipality_type="miejska", population=SEAT_POP[cc])
    muni_rows.append(row)
munis_by_county: dict[str, list[dict]] = {}
for m in muni_rows:
    munis_by_county.setdefault(m["county_code"], []).append(m)

voiv_rows = []
for v in voivs:
    voiv_rows.append({
        "voivodeship_code": v["voivodeship_code"], "voivodeship_name": v["voivodeship_name"],
        "population": int(v["population"]), "seat": v["wczk_seat"], "lat": float(v["lat"]), "lon": float(v["lon"]),
        "duty_center_in_app_today": 1 if v["voivodeship_code"] == "14" else 0,
    })
voiv_codes = [v["voivodeship_code"] for v in voiv_rows]
voiv_name = {v["voivodeship_code"]: v["voivodeship_name"] for v in voiv_rows}
voiv_pop = {v["voivodeship_code"]: v["population"] for v in voiv_rows}
voiv_idx = {c: i for i, c in enumerate(voiv_codes)}

# ----------------------------------------------------------------------------
# 2. Szkoly
# ----------------------------------------------------------------------------
SCHOOL_TYPES = [("SP", 0.55), ("LO", 0.15), ("TECH", 0.10), ("ZS", 0.12), ("BRAN", 0.05), ("SPEC", 0.03)]
STUDENT_RANGE = {"SP": (120, 650), "LO": (250, 800), "TECH": (300, 900), "ZS": (300, 1000), "BRAN": (150, 450), "SPEC": (40, 160)}
ANCHOR_SCHOOL = "Zespół Szkół nr 3 w Mieście M-1402"
ZS_NAMES = ["Zespół Szkół Technicznych", "Zespół Szkół Ogólnokształcących", "Zespół Szkół Elektronicznych",
            "Zespół Szkół Ekonomicznych", "Zespół Szkół Mechanicznych", "Zespół Szkół Budowlanych"]

total_pop = sum(c["population"] for c in county_rows)
n_per_county: dict[str, int] = {}
for c in county_rows:
    n_per_county[c["county_code"]] = max(3, round(N_SCHOOLS * c["population"] / total_pop))

schools: list[dict] = []
for c in county_rows:
    cc = c["county_code"]
    ms = munis_by_county[cc]
    mw = np.array([m["population"] for m in ms], float)
    mw /= mw.sum()
    counters: dict[tuple, int] = {}
    zs_used: dict[str, set] = {}
    for k in range(n_per_county[cc]):
        if cc == "1402" and k == 0:
            m = ms[0]
            stype, sname = "ZS", ANCHOR_SCHOOL
            zs_used.setdefault(m["municipality_code"], set()).add("Zespół Szkół Technicznych")
        else:
            m = ms[int(rng.choice(len(ms), p=mw))]
            stype = random.choices([t for t, _ in SCHOOL_TYPES], weights=[w for _, w in SCHOOL_TYPES])[0]
            is_seat = (cc in SEAT_POP and m is ms[0])
            where = f"w {seat_locative(cc)}" if is_seat else f", {m['municipality_name']}"
            mc = m["municipality_code"]
            if stype == "ZS":
                free = [n for n in ZS_NAMES if n not in zs_used.setdefault(mc, set())]
                if free:
                    base = free[0]
                    zs_used[mc].add(base)
                    sname = f"{base} {where}" if is_seat else f"{base}{where}"
                else:
                    counters[(mc, "ZS")] = counters.get((mc, "ZS"), 0) + 1
                    sname = f"Zespół Szkół Ogólnokształcących nr {counters[(mc, 'ZS')]} {where}" if is_seat else f"Zespół Szkół nr {counters[(mc, 'ZS')]}{where}"
            else:
                label = {"SP": "Szkoła Podstawowa", "LO": "Liceum Ogólnokształcące", "TECH": "Technikum", "BRAN": "Branżowa Szkoła I Stopnia", "SPEC": "Szkoła Specjalna"}[stype]
                counters[(mc, stype)] = counters.get((mc, stype), 0) + 1
                n = counters[(mc, stype)]
                sname = f"{label} nr {n} {where}" if is_seat else f"{label} nr {n}{where}"
        lo, hi = STUDENT_RANGE[stype]
        students = int(rng.integers(lo, hi + 1))
        schools.append({
            "school_id": f"SCH-{cc}-{k + 1:03d}", "school_name": sname, "school_type": stype,
            "municipality_code": m["municipality_code"], "county_code": cc, "voivodeship_code": c["voivodeship_code"],
            "locality_name": m["municipality_name"], "students": students,
            "lat": round(m["lat"] + float(rng.normal(0, 0.012)), 5), "lon": round(m["lon"] + float(rng.normal(0, 0.018)), 5),
        })
school_by_id = {s["school_id"]: s for s in schools}
anchor_school = next(s for s in schools if s["school_name"] == ANCHOR_SCHOOL)
S_COUNTY = np.array([s["county_code"] for s in schools])
S_VOIV = np.array([s["voivodeship_code"] for s in schools])
S_STUD = np.array([s["students"] for s in schools], float)
schools_in_county: dict[str, np.ndarray] = {}
for i, s in enumerate(schools):
    schools_in_county.setdefault(s["county_code"], []).append(i)
schools_in_county = {k: np.array(v) for k, v in schools_in_county.items()}

HOT = {"14": 3.0, "10": 2.0, "24": 1.8, "12": 1.6, "02": 1.5, "30": 1.1}
county_hot = {c["county_code"]: (c["population"] ** 0.5) * HOT.get(c["voivodeship_code"], 0.7) for c in county_rows}
MAZ_CITIES = ["1401", "1402", "1403", "1404", "1405", "1406"]


def pick_school(county_code: str) -> int:
    idx = schools_in_county[county_code]
    w = S_STUD[idx]
    return int(idx[int(rng.choice(len(idx), p=w / w.sum()))])


def pick_school_weighted(weights: np.ndarray) -> int:
    return int(rng.choice(len(schools), p=weights / weights.sum()))


# ----------------------------------------------------------------------------
# 3. Zgloszenia
# ----------------------------------------------------------------------------
AI_W = {
    "weapon_mention": .35, "threat_intent": .25, "bomb_mention": .30, "specific_time": .15, "imminence": .15,
    "named_target": .10, "named_location": .05, "evidence_attached": .05, "self_harm_indicator": .30,
    "farewell_message": .20, "injury_indicator": .20, "physical_violence": .15, "harassment": .10,
    "distress": .08, "stranger": .20, "media_link": .03, "mass_forward": .05, "urgency_words": .05,
    "dangerous_object": .12, "hazard_physical": .05, "threat_vague": .15, "hearsay": -.08,
    "joke_context": -.15, "other": 0.0,
}
AI_BASE = {"BRON": .15, "GROZBY": .20, "TRESCI_SIEC": .10, "PRZEMOC": .10, "SAMOUSZKODZENIE": .15, "INNE": .05}


def ai_priority_from_score(sc: float) -> str:
    return "KRYTYCZNY" if sc >= .70 else "WYSOKI" if sc >= .50 else "SREDNI" if sc >= .30 else "NISKI"


def hhmm() -> str:
    h, m = int(rng.integers(8, 15)), int(rng.choice([0, 10, 15, 20, 30, 40, 45]))
    return f"{h}:{m:02d}"


def fill(template: str, **kw) -> str:
    base = dict(cls=random.choice(tb.CLASSES), place=(pl := random.choice(tb.PLACES)), place_cap=pl[0].upper()+pl[1:], day=random.choice(tb.DAYS_PL),
                hhmm=hhmm(), subject=random.choice(tb.SUBJECTS), when_next=random.choice(tb.WHEN_NEXT),
                link=f"https://komunikator.example/p/{int(rng.integers(10**5, 10**6)):06d}")
    base.update(kw)
    return template.format(**base)


reports: list[dict] = []


def add_report(ts, school_idx, cat, text, signals, sev, label, campaign, bot=False, link="", latency=None, human_lat=75):
    if label.startswith("k1") or label == "k2_clip_bot":
        pass
    r = {
        "ts": ts, "school_idx": school_idx, "category": cat, "text": text, "signals": tuple(signals),
        "true_sev": sev, "label": label, "campaign": campaign, "bot": bot, "link": link,
    }
    if bot:
        r["latency"] = round(float(rng.uniform(0.8, 6.0)), 1) if rng.random() < .85 else round(float(rng.lognormal(math.log(40), .5)), 1)
        r["client"] = "headless_client" if rng.random() < .7 else "mobile_web"
    else:
        r["latency"] = round(float(rng.lognormal(math.log(human_lat), .6)), 1)
        r["client"] = "mobile_app" if rng.random() < .82 else "mobile_web"
    reports.append(r)


def sample_times(weights: dict, total: int) -> list[datetime]:
    keys = list(weights)
    w = np.array([weights[k] for k in keys], float)
    counts = rng.multinomial(total, w / w.sum())
    out = []
    for k, c in zip(keys, counts):
        base = T0 + timedelta(days=k[0] + 3, hours=k[1])
        for _ in range(int(c)):
            out.append(base + timedelta(seconds=int(rng.integers(0, 3600))))
    return sorted(out)


def hours(day: int, start: int, ws: list[float]) -> dict:
    return {(day, start + i): w for i, w in enumerate(ws)}


# --- 3a. Tlo -----------------------------------------------------------------
DIURN_BG = np.array([.2, .1, .1, .1, .1, .2, .8, 3, 5, 6, 6, 5, 5, 5, 5, 4, 3, 2.5, 2, 2.5, 2.5, 2, 1.2, .6])
WAVE_MULT = {-3: 1.0, -2: 1.15, -1: 1.4, 0: 1.5, 1: 1.3, 2: 1.3, 3: 1.4, 4: 1.2, 5: 1.1, 6: 1.0, 7: 1.0}
CAT_P = {"BRON": .06, "GROZBY": .09, "TRESCI_SIEC": .18, "PRZEMOC": .35, "SAMOUSZKODZENIE": .20, "INNE": .12}
SEV_P = {"BRON": (.10, .25, .40, .25), "GROZBY": (.15, .35, .35, .15), "TRESCI_SIEC": (.35, .45, .17, .03),
         "PRZEMOC": (.40, .47, .12, .01), "SAMOUSZKODZENIE": (.15, .40, .35, .10), "INNE": (.60, .33, .06, .01)}
bg_by_cat_sev: dict[tuple, list] = {}
for t in tb.BG:
    bg_by_cat_sev.setdefault((t[0], t[1]), []).append(t)

bg_w = S_STUD.copy()
for d in range(-3, 8):
    wk = (D0 + timedelta(days=d)).weekday()
    daily = 150 * (0.25 if wk >= 5 else 1.0) * WAVE_MULT[d]
    prof = DIURN_BG / DIURN_BG.sum()
    for h in range(24):
        n = int(rng.poisson(daily * prof[h]))
        base = D0 + timedelta(days=d, hours=h)
        for _ in range(n):
            ts = base + timedelta(seconds=int(rng.integers(0, 3600)))
            cat = random.choices(list(CAT_P), weights=list(CAT_P.values()))[0]
            sev = random.choices([1, 2, 3, 4], weights=SEV_P[cat])[0]
            t = random.choice(bg_by_cat_sev[(cat, sev)])
            text = fill(t[2])
            sg = list(t[3]) + (["imminence"] if "{when_next}" in t[2] else [])
            link = ""
            if "{link}" in t[2]:
                link = text.split("Link: ")[-1].strip()
            add_report(ts, pick_school_weighted(bg_w), cat, text, sg, sev, "background", "")
            reports[-1]["link"] = link

# --- 3b. K1: falszywe alarmy bombowe (boty) ----------------------------------
K1_BURSTS = [
    (hours(-2, 11, [1, 3, 2, 1]), 105, 25),
    (hours(-1, 8, [2, 4, 4, 3, 1]), 205, 40),
    (hours(0, 5, [1, 3, 7, 10, 8, 5, 3, 1]), 555, 60),
    (hours(3, 7, [1, 2, 2, 1]), 88, 20),
]
bot_tokens_pool = {d: [f"B{d + 3:02d}-{int(rng.integers(16**6)):06x}" for _ in range(60)] for d in range(-3, 8)}


def burst_targets(n_targets: int, n_counties: int, forced: list[str]) -> list[int]:
    codes = list(county_hot)
    w = np.array([county_hot[c] for c in codes])
    chosen = list(rng.choice(len(codes), size=n_counties, replace=False, p=w / w.sum()))
    sel = list(dict.fromkeys(forced + [codes[i] for i in chosen]))
    ws = np.array([county_hot[c] for c in sel])
    shares = ws / ws.sum()
    out = []
    for c, sh in zip(sel, shares):
        k = max(1, round(n_targets * sh))
        idx = schools_in_county[c]
        k = min(k, len(idx))
        w2 = S_STUD[idx]
        out.extend(int(i) for i in rng.choice(idx, size=k, replace=False, p=w2 / w2.sum()))
    return out


for bi, (wts, total, ncounty) in enumerate(K1_BURSTS):
    forced = MAZ_CITIES if bi >= 1 else ["1402"]
    targets = burst_targets(max(20, int(total / 2.2)), ncounty, forced)
    zipf = 1.0 / np.arange(1, len(targets) + 1) ** 0.5
    for ts in sample_times(wts, total):
        si = targets[int(rng.choice(len(targets), p=zipf / zipf.sum()))]
        tpl = random.choice(tb.K1_TEMPLATES)
        text = fill(tpl)
        if rng.random() < .5:
            text += f" {schools[si]['school_name']}."
        add_report(ts, si, "GROZBY", text, tb.K1_SIGNALS, 1, "k1_bomb_bot", "K1", bot=True)

# --- 3c. K2: falszywe nagrania zapowiedzi ataku ------------------------------
K2_BOT_W = {**hours(-1, 15, [1, 3, 4, 4, 3, 2, 2, 1, 1]), **hours(0, 0, [1, .5, .5, .5, 1, 2, 4, 6, 7, 6, 4, 3, 2]),
            **hours(1, 8, [1, 1, 1, 1, .5, .5, .5, .5, .3, .3])}
K2_ORG_W = {**hours(-1, 17, [.5, 1, 2, 3, 3, 2, 1]), **hours(0, 5, [3, 6, 9, 10, 8, 5, 3, 2, 1]),
            **hours(1, 8, [1.5, 1.5, 1.2, 1, 1, 1, .8, .8, .5, .5, .3, .3, .2]), **hours(3, 7, [1, 2, 2, 1.5, 1, .5, .3])}
codes_all = list(county_hot)
cw = np.array([county_hot[c] for c in codes_all])
k2_counties = [codes_all[i] for i in rng.choice(len(codes_all), size=70, replace=False, p=cw / cw.sum())]
k2_counties = list(dict.fromkeys(MAZ_CITIES + k2_counties))
k2w = np.array([county_hot[c] for c in k2_counties])
for ts in sample_times(K2_BOT_W, 650):
    c = k2_counties[int(rng.choice(len(k2_counties), p=k2w / k2w.sum()))]
    link = random.choice(tb.K2_LINKS)
    add_report(ts, pick_school(c), "TRESCI_SIEC", fill(random.choice(tb.K2_BOT_TEMPLATES), link=link),
               tb.K2_BOT_SIGNALS, 1, "k2_clip_bot", "K2", bot=True, link=link)
for ts in sample_times(K2_ORG_W, 850):
    link = random.choice(tb.K2_LINKS)
    tpl = random.choice(tb.K2_ORGANIC_TEMPLATES)
    text = fill(tpl, link=link)
    has_link = "{link}" in tpl
    wsch = S_STUD * np.where(np.isin(S_VOIV, ["14", "10", "24", "12", "02"]), 1.3, 1.0)
    add_report(ts, pick_school_weighted(wsch), "TRESCI_SIEC", text.strip(), tb.K2_ORGANIC_SIGNALS, 1, "k2_clip_organic", "K2",
               link=link if has_link else "", human_lat=45)

# --- 3d. K3: copycat po incydencie ------------------------------------------
K3_W = {**hours(-1, 16, [1, 2, 3, 3, 3, 2, 1, 1]), **hours(0, 7, [1, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1]),
        **hours(1, 9, [1] * 6), **hours(2, 9, [1] * 5), **hours(3, 7, [3, 4, 4, 3, 3, 2, 2, 1, 1, 1]), **hours(4, 7, [2, 2, 2, 2, 1, 1, 1, 1]),
        **hours(5, 7, [1, 1, 1, 1, 1])}
k3_school_w = S_STUD * np.where(S_VOIV == "10", 3.0, np.where(np.isin(S_VOIV, ["14", "30", "24"]), 1.5, 1.0))
for ts in sample_times(K3_W, 320):
    t = random.choice(tb.K3_TEMPLATES)
    cat = "GROZBY" if "threat_intent" in t[1] else "PRZEMOC" if "harassment" in t[1] else "TRESCI_SIEC" if "media_link" in t[1] else "GROZBY"
    add_report(ts, pick_school_weighted(k3_school_w), cat, fill(t[0]), t[1], t[2], "k3_copycat", "K3")

# --- 3e. R: realne krytyczne ukryte w fali -----------------------------------
R_FIXED = [
    # (dzien, godzina, minuta, powiat, indeks szablonu)  indeks 0 = BS-4826 (ekran aplikacji)
    (0, 8, 41, "1402", 0),
    (0, 10, 5, "1404", 1),
    (-1, 10, 30, "1403", 2),
    (0, 11, 20, "1406", 10),
    (0, 9, 15, "1401", 5),
    (0, 7, 50, "1405", 6),
]
for day, h, mi, cc, ti in R_FIXED:
    t = tb.REAL_CRITICAL[ti]
    if ti == 0:
        si = schools.index(anchor_school)
        text = "Chłopak z 2c pokazywał w szatni nóż motylkowy... jutro przyniesie go znowu"
        sg = ("weapon_mention", "specific_time", "imminence")
        cat = "BRON"
    else:
        si = pick_school(cc)
        text = fill(t[0])
        sg, cat = t[1], t[2]
    ts = D0 + timedelta(days=day, hours=h, minutes=mi, seconds=int(rng.integers(0, 60)))
    add_report(ts, si, cat, text, sg, 4, "real_critical_wave", "R", human_lat=110)
extra_ts = sample_times({**hours(-2, 11, [1] * 5), **hours(-1, 8, [2] * 6), **hours(0, 6, [3] * 7), **hours(1, 9, [1] * 4), **hours(3, 7, [2] * 5)}, 10)
for k, ts in enumerate(extra_ts):
    ti = [3, 4, 7, 8, 9, 1, 2, 6, 7, 3][k]
    t = tb.REAL_CRITICAL[ti]
    c = codes_all[int(rng.choice(len(codes_all), p=cw / cw.sum()))]
    add_report(ts, pick_school(c), t[2], fill(t[0]), t[1], 4, "real_critical_wave", "R", human_lat=110)

# ----------------------------------------------------------------------------
# 4. Sygnaly AI, kolejnosc, numery BS
# ----------------------------------------------------------------------------
reports.sort(key=lambda r: (r["ts"], r["text"]))
anchor_i = next(i for i, r in enumerate(reports) if r["text"].startswith("Chłopak z 2c pokazywał w szatni"))
for i, r in enumerate(reports):
    r["bs_no"] = ANCHOR_BS - anchor_i + i
    r["report_id"] = f"BS-{r['bs_no']}"
    sg = list(r["signals"])
    ai_sg = [s for s in sg if rng.random() > .08]
    if rng.random() < .05 and "urgency_words" not in ai_sg:
        ai_sg.append("urgency_words")
    if r["report_id"] == f"BS-{ANCHOR_BS}":
        ai_sg = ["weapon_mention", "specific_time", "imminence"]
    score = AI_BASE[r["category"]] + sum(AI_W.get(s, 0) for s in ai_sg)
    score = float(min(1.0, max(0.0, score + float(rng.normal(0, .04)))))
    if r["report_id"] == f"BS-{ANCHOR_BS}":
        score = 0.86
    r["ai_signals"] = ai_sg
    r["ai_score"] = round(score, 3)
    r["ai_priority"] = ai_priority_from_score(score)
    r["ai_confidence"] = round(float(min(.98, max(.45, .55 + abs(score - .5) * .8 + rng.normal(0, .04)))), 2)
    cats = list(CAT_P)
    r["ai_category"] = r["category"] if rng.random() < .9 else random.choice(cats)
    if r["report_id"] == f"BS-{ANCHOR_BS}":
        r["ai_category"] = "BRON"
    cat, p = r["ai_category"], r["ai_priority"]
    if cat == "SAMOUSZKODZENIE":
        rec = "PED"
    elif cat in ("BRON", "GROZBY") and PRANK[p] >= 3:
        rec = "POL"
    elif cat == "TRESCI_SIEC" and r["link"]:
        rec = "DYZ"
    elif cat in ("PRZEMOC",):
        rec = "PED" if PRANK[p] <= 2 else "DIR"
    else:
        rec = "DIR"
    if "bomb_mention" in ai_sg or ("threat_intent" in ai_sg and PRANK[p] >= 3):
        rec = "POL"
    r["ai_recipient"] = rec
    r["voivodeship_code"] = schools[r["school_idx"]]["voivodeship_code"]
    r["county_code"] = schools[r["school_idx"]]["county_code"]
    day = (r["ts"] - T0).days
    pool = bot_tokens_pool[day - 3]
    if r["bot"] and rng.random() < .4:
        r["sender_token_day"] = random.choice(pool)
    else:
        r["sender_token_day"] = f"T{day:02d}-{int(rng.integers(16**8)):08x}"

# ----------------------------------------------------------------------------
# 5. Kolejka dyzurnych (status quo): priorytet wg sugestii AI, FIFO w klasie
# ----------------------------------------------------------------------------
OFFICER_ID: dict[int, str] = {}


def active_servers(vc: str, t: datetime) -> int:
    day = 6 <= t.hour < 22
    return DUTY_DAY.get(vc, 2) if day else DUTY_NIGHT.get(vc, 1)


def next_active(vc: str, j: int, t: datetime) -> datetime:
    for _ in range(30):
        if j < active_servers(vc, t):
            return t
        t = (t.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    return t


def simulate_queue(items: list[dict], vc: str) -> None:
    k = max(DUTY_DAY.get(vc, 2), DUTY_NIGHT.get(vc, 1))
    free = [T0] * k
    waiting: list = []
    i, n = 0, len(items)
    while i < n or waiting:
        starts = [next_active(vc, j, free[j]) for j in range(k)]
        j_best = min(range(k), key=lambda j: starts[j])
        best = starts[j_best]
        if not waiting:
            best = max(best, items[i]["ts"])
        while i < n and items[i]["ts"] <= best:
            heapq.heappush(waiting, (-PRANK[items[i]["ai_priority"]], items[i]["ts"], i))
            i += 1
        qlen = len(waiting)
        _, _, idx = heapq.heappop(waiting)
        it = items[idx]
        mean = SERVICE_MIN[it["ai_priority"]]
        svc = float(rng.lognormal(math.log(mean) - .08, .4))
        done = best + timedelta(minutes=svc)
        free[j_best] = done
        it["decision_ts"] = done
        it["queue_len_at_start"] = qlen
        it["officer"] = f"DZ-{vc}-{j_best + 1}"


for vc in voiv_codes:
    items = [r for r in reports if r["voivodeship_code"] == vc]
    simulate_queue(items, vc)


def shift_toward(cur: int, target: int) -> int:
    if cur == target:
        return cur
    return cur + (1 if target > cur else -1)


for r in reports:
    ai = PRANK[r["ai_priority"]]
    agree = .93 if r["queue_len_at_start"] >= 15 else .80
    if rng.random() < agree:
        dp = ai
    elif rng.random() < .65:
        dp = shift_toward(ai, r["true_sev"])
    else:
        dp = min(4, max(1, ai + random.choice([-1, 1])))
    r["duty_priority"] = PRIORITIES[dp - 1]
    rec = r["ai_recipient"] if rng.random() < .9 else random.choice(["DIR", "PED", "POL", "DYZ"])
    if dp <= 1 and rec == "POL":
        rec = "DIR"
    if dp >= 3 and r["category"] in ("BRON", "GROZBY") and rec in ("DIR", "PED"):
        rec = "POL"
    r["recipient"] = rec

# ----------------------------------------------------------------------------
# 6. Przekazania, wyniki, status
# ----------------------------------------------------------------------------
handoffs: list[dict] = []
updates: list[dict] = []
PATROL_MIN = {"KRYTYCZNY": 60, "WYSOKI": 40, "SREDNI": 20, "NISKI": 10}
REASON = {"POL": "zgłoszenie broni lub groźby wymagające weryfikacji", "DIR": "informacja dla dyrekcji szkoły",
          "PED": "potrzeba wsparcia pedagoga lub psychologa", "DYZ": "treść online do oceny przez Dyżurnet.pl (NASK)"}
campaign_labels = {"k1_bomb_bot", "k2_clip_bot", "k2_clip_organic"}
hid = 0
for r in reports:
    dec = r["decision_ts"]
    r["decision_delay_min"] = round((dec - r["ts"]).total_seconds() / 60, 1)
    recs = [r["recipient"]]
    if r["duty_priority"] in ("KRYTYCZNY",) and r["recipient"] == "POL":
        recs.append("DIR")
    r["handoffs"] = []
    first_ho = None
    for k, rc in enumerate(recs):
        hid += 1
        hts = dec + timedelta(minutes=float(rng.uniform(1, 4)))
        ack = hts + timedelta(minutes=float(rng.lognormal(math.log(12 if rc == "POL" else 90), .6)))
        fake = r["label"] in ("k1_bomb_bot", "k2_clip_bot", "k2_clip_organic") or r["true_sev"] <= 1
        if rc == "POL":
            outcome = "niepotwierdzone" if (fake or rng.random() < .35) else "potwierdzone"
            out_ts = ack + timedelta(minutes=float(rng.uniform(20, 90)))
            pm = int(PATROL_MIN[r["duty_priority"]] * float(rng.uniform(.8, 1.3)))
        elif rc == "PED":
            outcome = "rozmowa_wsparcie" if rng.random() < .8 else "brak_kontaktu"
            out_ts = ack + timedelta(hours=float(rng.uniform(2, 30)))
            pm = 0
        elif rc == "DYZ":
            outcome = "tresc_usunieta" if (r["label"] == "k2_clip_bot" or rng.random() < .5) else "bez_zasadnosci"
            out_ts = ack + timedelta(hours=float(rng.uniform(1, 20)))
            pm = 0
        else:
            outcome = "podjeto_dzialania" if r["true_sev"] >= 2 else "zamkniete_bez_dzialan"
            out_ts = ack + timedelta(hours=float(rng.uniform(1, 28)))
            pm = 0
        row = {
            "handoff_id": f"HO-{hid:06d}", "report_id": r["report_id"], "handoff_ts": iso(hts), "recipient_code": rc,
            "is_primary": 1 if k == 0 else 0, "reason": REASON[rc], "acknowledged_ts": iso(ack),
            "outcome": outcome, "outcome_ts": iso(out_ts) if out_ts <= END else "", "patrol_minutes": pm,
            "county_code": r["county_code"], "voivodeship_code": r["voivodeship_code"],
        }
        handoffs.append(row)
        r["handoffs"].append((rc, hts, out_ts, pm))
        if first_ho is None:
            first_ho = hts
    r["first_handoff_ts"] = first_ho
    close = max(h[2] for h in r["handoffs"]) if r["handoffs"] else dec
    r["closed_ts"] = close if close <= END else None

STATUS_LABEL = {"NOWE": "Nowe", "PRZEKAZANE": "Przekazane", "W_ANALIZIE": "W analizie", "ZAMKNIETE": "Zamknięte"}
for r in reports:
    final = "ZAMKNIETE" if r["closed_ts"] else "PRZEKAZANE"
    r["status"] = final
    updates.append({"timestamp": iso(r["decision_ts"]), "stream": "report_update", "report_id": r["report_id"],
                    "new_status": "W_ANALIZIE", "duty_priority": r["duty_priority"], "recipient_code": r["recipient"],
                    "actor": r["officer"], "voivodeship_code": r["voivodeship_code"], "county_code": r["county_code"]})
    updates.append({"timestamp": iso(r["first_handoff_ts"]), "stream": "report_update", "report_id": r["report_id"],
                    "new_status": "PRZEKAZANE", "duty_priority": r["duty_priority"], "recipient_code": r["recipient"],
                    "actor": r["officer"], "voivodeship_code": r["voivodeship_code"], "county_code": r["county_code"]})
    if r["closed_ts"]:
        updates.append({"timestamp": iso(r["closed_ts"]), "stream": "report_update", "report_id": r["report_id"],
                        "new_status": "ZAMKNIETE", "duty_priority": r["duty_priority"], "recipient_code": r["recipient"],
                        "actor": r["officer"], "voivodeship_code": r["voivodeship_code"], "county_code": r["county_code"]})
updates.sort(key=lambda u: (u["timestamp"], u["report_id"]))

# ----------------------------------------------------------------------------
# 7. Zdarzenia porzadkowe Z18
# ----------------------------------------------------------------------------
disorder: list[dict] = []
trigger_counts: dict[tuple, int] = {}
for r in reports:
    if r["label"] in campaign_labels and r["ts"].hour < 12 and (r["ts"] - T0).days in (3, 6):
        trigger_counts[(r["school_idx"], (r["ts"] - T0).days)] = trigger_counts.get((r["school_idx"], (r["ts"] - T0).days), 0) + 1
did = 0
for (si, d), c in sorted(trigger_counts.items()):
    p = min(.7, .10 + .12 * c) * (1.0 if d == 3 else .45)
    if rng.random() < p:
        s = schools[si]
        ts = T0 + timedelta(days=d, hours=7, minutes=int(rng.integers(0, 330)))
        et = random.choices(["mass_pickup", "parents_gathering", "road_blockade", "protest_unplanned"], weights=[70, 15, 8, 7])[0]
        share = {"mass_pickup": .35, "parents_gathering": .15, "road_blockade": .08, "protest_unplanned": .10}[et]
        did += 1
        disorder.append({"timestamp": iso(ts), "stream": "disorder", "event_id": f"ZP-{did:05d}", "school_id": s["school_id"],
                         "county_code": s["county_code"], "voivodeship_code": s["voivodeship_code"], "lat": s["lat"], "lon": s["lon"],
                         "event_type": et, "est_participants": int(s["students"] * share * float(rng.uniform(.6, 1.4)) + rng.integers(5, 40)),
                         "police_required": 1 if (et != "mass_pickup" or rng.random() < .3) else 0,
                         "source": random.choice(["dyrekcja", "112", "monitoring_mediow"])})
disorder.sort(key=lambda d: d["timestamp"])

# ----------------------------------------------------------------------------
# 8. Obciazenie 112 i telefonow szkol
# ----------------------------------------------------------------------------
camp_w = np.zeros((16, N_BINS))
dis_w = np.zeros((16, N_BINS))
for r in reports:
    b = int((r["ts"] - T0).total_seconds() // 900)
    w = 1.0 if r["label"] in ("k1_bomb_bot", "k2_clip_bot") else .4 if r["label"] in ("k2_clip_organic", "k3_copycat") else 0.0
    camp_w[voiv_idx[r["voivodeship_code"]], b] += w
for d in disorder:
    b = int((datetime.fromisoformat(d["timestamp"]) - T0).total_seconds() // 900)
    dis_w[voiv_idx[d["voivodeship_code"]], b] += 1
DIURN = np.array([.45, .35, .3, .28, .3, .4, .6, .85, 1.1, 1.25, 1.3, 1.3, 1.3, 1.3, 1.35, 1.4, 1.45, 1.5, 1.4, 1.3, 1.15, 1, .8, .6])
DIURN = DIURN / DIURN.mean()
tot_voiv_pop = sum(voiv_pop.values())
n_school_v = {v: sum(1 for s in schools if s["voivodeship_code"] == v) for v in voiv_codes}
hotline: list[dict] = []
for vc in voiv_codes:
    vi = voiv_idx[vc]
    share = voiv_pop[vc] / tot_voiv_pop
    for b in range(N_BINS):
        ts = T0 + timedelta(minutes=15 * b)
        d = DIURN[ts.hour]
        base = 38000 / 96 * share * d * (0.9 if ts.weekday() >= 5 else 1.0)
        ops = max(2, math.ceil(38000 / 96 * share * DIURN[ts.hour] / (11 * .65)))
        extra = int(rng.poisson(4.0 * camp_w[vi, b] + 30 * dis_w[vi, b]))
        total = int(rng.poisson(base)) + extra
        school_rel = int(rng.poisson(base * .006)) + extra
        load = total / (ops * 11)
        wait = 8 + 12 * min(load, .85) + (140 * max(0, load - .85) ** 1.5)
        aband = min(45.0, max(0.0, (load - .9) * 55))
        sw = int(rng.poisson(n_school_v[vc] * .02 * d * (.3 if ts.weekday() >= 5 else 1)) + rng.poisson(6 * camp_w[vi, b] + 25 * dis_w[vi, b]))
        hotline.append({"timestamp": iso(ts), "stream": "hotline", "voivodeship_code": vc, "calls_112_total": total,
                        "calls_112_school_related": school_rel, "operators_on_duty": ops, "load_ratio": round(load, 3),
                        "wait_p90_s": round(float(wait + rng.normal(0, 1.5)), 1), "abandoned_pct": round(aband, 1), "school_phone_calls": sw})
hotline.sort(key=lambda h: (h["timestamp"], h["voivodeship_code"]))

# ----------------------------------------------------------------------------
# 9. Sygnaly social
# ----------------------------------------------------------------------------
k1_h = np.zeros(N_HOURS); k2b_h = np.zeros(N_HOURS); k2o_h = np.zeros(N_HOURS); k3_h = np.zeros(N_HOURS)
for r in reports:
    h = int((r["ts"] - T0).total_seconds() // 3600)
    if r["label"] == "k1_bomb_bot":
        k1_h[h] += 1
    elif r["label"] == "k2_clip_bot":
        k2b_h[h] += 1
    elif r["label"] == "k2_clip_organic":
        k2o_h[h] += 1
    elif r["label"] == "k3_copycat":
        k3_h[h] += 1


def lead(arr: np.ndarray, hrs: int) -> np.ndarray:
    out = np.zeros_like(arr)
    out[:len(arr) - hrs] = arr[hrs:]
    return out


NARR = {
    "N0": ("tło: rozmowy o szkole", None, .10, .12),
    "N1": ("plotka o alarmach bombowych", lead(k1_h, 2) * 9, .78, .55),
    "N2": ("fałszywe nagranie zapowiedzi ataku", lead(k2b_h + k2o_h, 3) * 55 + lead(k2o_h, 1) * 20, .66, .40),
    "N3": ("naśladownictwo po incydencie", lead(k3_h, 1) * 15, .12, .12),
}
PLATFORMS = [("platform_video", .35), ("platform_microblog", .30), ("platform_messenger", .25), ("platform_forum", .10)]
social: list[dict] = []
for nid, (nm, curve, bot, newacc) in NARR.items():
    for h in range(N_HOURS):
        ts = T0 + timedelta(hours=h)
        if curve is None:
            posts_h = 120 * DIURN[ts.hour]
            bs = bot
        else:
            posts_h = float(curve[h])
            if nid == "N2":
                tot = k2b_h[h] + k2o_h[h]
                bs = .72 * (k2b_h[h] + 1) / (tot + 2) + .18 * (1 - (k2b_h[h] + 1) / (tot + 2))
            else:
                bs = bot
        for pl, share in PLATFORMS:
            posts = int(rng.poisson(posts_h * share)) if posts_h > 0 else 0
            if nid != "N0" and posts == 0:
                continue
            uniq = int(posts * (0.45 if bs > .5 else .8) + rng.integers(0, 3))
            social.append({"timestamp": iso(ts), "stream": "social", "narrative_id": nid, "narrative_name": nm, "platform": pl,
                           "posts": posts, "unique_accounts": uniq, "bot_score_mean": round(float(min(.99, max(.02, bs + rng.normal(0, .03)))), 3),
                           "new_account_share": round(float(min(.95, max(.02, newacc * (bs / max(bot, .01)) ** .5 + rng.normal(0, .03)))), 3),
                           "est_reach": int(posts * float(rng.uniform(120, 900)) * (3 if pl == "platform_video" else 1))})
social.sort(key=lambda s: (s["timestamp"], s["narrative_id"], s["platform"]))

# ----------------------------------------------------------------------------
# 10. Patrole i wsparcie
# ----------------------------------------------------------------------------
used_min: dict[tuple, float] = {}
for r in reports:
    for rc, hts, _, pm in r["handoffs"]:
        if rc == "POL":
            k = (r["county_code"], (hts - T0).days)
            used_min[k] = used_min.get(k, 0) + pm
for d in disorder:
    if d["police_required"]:
        k = (d["county_code"], (datetime.fromisoformat(d["timestamp"]) - T0).days)
        used_min[k] = used_min.get(k, 0) + 90
patrol_rows = []
for c in county_rows:
    patrols = max(2, round(c["population"] / 9000))
    avail = patrols * 1440 * .35
    for dd in range(11):
        used = used_min.get((c["county_code"], dd), 0)
        patrol_rows.append({
            "date": (T0 + timedelta(days=dd)).date().isoformat(), "county_code": c["county_code"], "voivodeship_code": c["voivodeship_code"],
            "patrols_per_shift_avg": patrols, "response_minutes_available": int(avail), "response_minutes_used_school": int(used),
            "utilization_pct": round(100 * used / avail, 2),
            "median_response_min": round(7 + 30 * max(0, used / avail - .02) + float(rng.normal(0, .6)), 1),
        })
school_cnt = {c["county_code"]: len(schools_in_county[c["county_code"]]) for c in county_rows}
support_rows = []
for c in county_rows:
    n = school_cnt[c["county_code"]]
    for role, fte in (("pedagog", n * .8), ("psycholog", n * .45), ("zespol_mobilny", max(1, round(n / 25)))):
        support_rows.append({"snapshot_date": D0.date().isoformat(), "county_code": c["county_code"],
                             "voivodeship_code": c["voivodeship_code"], "role": role, "fte_available": round(fte, 1),
                             "n_schools": n, "students": int(S_STUD[schools_in_county[c["county_code"]]].sum())})

# ----------------------------------------------------------------------------
# 11. Eskalacja, zadania, gotowosc (osia scenariusza)
# ----------------------------------------------------------------------------
escalation = [
    ("ESC-01", datetime(2026, 10, 7, 15, 40, tzinfo=TZ), "powiat", "Miasto M-1402", "decyzja", "starosta", "Powiatowy zespół zarządzania kryzysowego: pierwsze posiedzenie, nadzwyczajna weryfikacja alarmów", "scenariusz"),
    ("ESC-02", datetime(2026, 10, 8, 19, 30, tzinfo=TZ), "wojewoda", "łódzkie", "decyzja", "wojewoda łódzki", "Wojewódzki zespół zarządzania kryzysowego po incydencie w szkole w Mieście M-1001", "scenariusz"),
    ("ESC-03", datetime(2026, 10, 9, 3, 50, tzinfo=TZ), "wojewoda", "mazowieckie", "decyzja", "wojewoda mazowiecki", "Zwołanie WZZK: skoordynowane alarmy w kilkunastu powiatach", "scenariusz"),
    ("ESC-04", datetime(2026, 10, 9, 9, 10, tzinfo=TZ), "minister", "MEN/MSWiA", "decyzja", "minister wiodący", "Minister Edukacji Narodowej i MSWiA: wspólne stanowisko robocze", "scenariusz"),
    ("ESC-05", RZZK_TS, "RZZK", "kraj", "decyzja", "Premier / Dyrektor RCB", "Zwołanie Rządowego Zespołu Zarządzania Kryzysowego (SPO-1) i Zespołu ds. Incydentów Krytycznych (SPO-16)", "scenariusz"),
    ("ESC-06", datetime(2026, 10, 13, 12, 0, tzinfo=TZ), "RZZK", "kraj", "decyzja", "Dyrektor RCB", "Zakończenie eskalacji: obniżenie poziomu reagowania, monitoring", "scenariusz"),
]
esc_rows = [{"escalation_id": e[0], "timestamp": iso(e[1]), "level": e[2], "scope": e[3], "decision_type": e[4], "actor_role": e[5],
             "description": e[6], "source": e[7], "event_id": EVENT_ID} for e in escalation]

TASKS = [
    ("TSK-01", 0, "Z16", "SPO-1", "I", "RZZK", "Organizacja posiedzenia RZZK z obrazem sytuacji i rekomendacją z systemu krajowego", 2, "wykonane"),
    ("TSK-02", 15, "Z16", "SPO-12", "I", "RZZK", "Uruchomienie wymiany informacji między dyżurnymi powiatowymi, wojewódzkimi i RCB", 1, "wykonane"),
    ("TSK-03", 30, "Z04", "SPO-16", "X", "minister", "Zwołanie Zespołu ds. Incydentów Krytycznych: analiza skoordynowanej kampanii fałszywych alarmów", 4, "wykonane"),
    ("TSK-04", 30, "Z16", "SPO-16", "XIX", "minister", "Priorytetyzacja wyjazdów patroli: zgłoszenia o wysokiej wiarygodności przed klastrami kampanii", 2, "wykonane"),
    ("TSK-05", 30, "Z20", "SPO-12", "X", "minister", "CSIRT NASK i Dyżurnet.pl: zgłoszenia do platform, zdjęcie fałszywych nagrań", 3, "opoznione"),
    ("TSK-06", 20, "Z12", "SPO-10", "XIII", "minister", "Ochrona łączności alarmowej: priorytet dla linii 112 przy przeciążeniu, współpraca z operatorami", 2, "wykonane"),
    ("TSK-07", 45, "Z18", "SPO-3", "XV", "minister", "Komunikat do rodziców i mediów o sposobie weryfikacji alarmów (szkic do zatwierdzenia przez człowieka)", 2, "wykonane"),
    ("TSK-08", 45, "Z16", "SPO-12", "XIX", "minister", "Przekazanie do Policji listy zgłoszeń wydzielonych z kampanii jako wiarygodne", 1, "wykonane"),
    ("TSK-09", 60, "Z18", "SPO-3", "I", "RZZK", "Uzgodnienie jednego kanału komunikacji z ludnością (gov.pl, RCB, kuratoria)", 3, "wykonane"),
    ("TSK-10", 60, "Z18", "SPO-12", "XV", "minister", "Instrukcja dla kuratoriów i dyrekcji: tryb weryfikacji alarmów i zgłaszania do Policji", 3, "wykonane"),
    ("TSK-11", 60, "Z04", "SPO-12", "X", "minister", "Analiza wzorców kont rozsiewających treści (nowe konta, aktywność botów)", 12, "w_toku"),
    ("TSK-12", 60, "Z12", "SPO-12", "XIII", "minister", "Filtrowanie masowych, automatycznych połączeń do szkół i 112 we współpracy z operatorami", 6, "opoznione"),
    ("TSK-13", 90, "Z18", "SPO-1", "XV", "wojewoda", "Wsparcie psychologiczno-pedagogiczne: zespoły mobilne poradni w powiatach o najwyższym obciążeniu", 12, "w_toku"),
    ("TSK-14", 120, "Z20", "SPO-3", "X", "minister", "Komunikat prebunkingowy o fałszywych nagraniach w mediach społecznościowych", 6, "wykonane"),
    ("TSK-15", 180, "Z04", "SPO-12", "XX", "RZZK", "Zapytanie do partnerów zagranicznych o możliwego zewnętrznego inspiratora (wg potrzeby)", 48, "warunkowe"),
    ("TSK-16", 180, "Z04", "SPO-16", "XIV", "RZZK", "Wsparcie cyberobrony przy analizie dezinformacji (wg potrzeby)", 48, "warunkowe"),
    ("TSK-17", 1440 * 3 + 600, "Z18", "SPO-12", "XV", "minister", "Monitoring naśladownictwa w poniedziałek po weekendzie (D+3)", 24, "wykonane"),
]
task_rows = []
for tid, off, hz, spo, div, lvl, title, due_h, final in TASKS:
    t_start = RZZK_TS + timedelta(minutes=off)
    due = t_start + timedelta(hours=due_h)
    base = {"stream": "task_activation", "event_id": EVENT_ID, "task_id": tid, "hazard_code": hz, "spo_code": spo,
            "leading_admin_division": div, "level": lvl, "task_title": title, "due_ts": iso(due)}
    task_rows.append({"timestamp": iso(t_start), "activation_status": "zlecone", **base})
    if final == "warunkowe":
        task_rows[-1]["activation_status"] = "warunkowe"
        continue
    task_rows.append({"timestamp": iso(t_start + timedelta(minutes=float(rng.uniform(8, 25)))), "activation_status": "w_toku", **base})
    if final == "wykonane":
        task_rows.append({"timestamp": iso(t_start + timedelta(hours=due_h * float(rng.uniform(.5, .95)))), "activation_status": "wykonane", **base})
    elif final == "opoznione":
        task_rows.append({"timestamp": iso(due + timedelta(minutes=5)), "activation_status": "opoznione", **base})
task_rows.sort(key=lambda t: (t["timestamp"], t["task_id"]))

readiness = []
for div, nm, status, assets in [("I", "RCB", "gotowe", "zespoły=1; analitycy=6; dyżur=24/7"), ("X", "CSIRT NASK", "gotowe", "zespoły=2; analitycy=9; dyżur=24/7"),
                                ("XIII", "UKE i operatorzy", "w_toku", "zespoły=1; łącznicy=4"), ("XV", "MEN i kuratoria", "gotowe", "zespoły=1; koordynatorzy=16"),
                                ("XIX", "Policja", "gotowe", "zespoły=3; patrole rezerwowe=40"), ("XIV", "MON (cyberobrona)", "w_toku", "zespoły=1"),
                                ("XX", "MSZ", "brak", "zespoły=0")]:
    readiness.append({"timestamp": iso(RZZK_TS + timedelta(minutes=int(rng.integers(20, 150)))), "stream": "readiness", "event_id": EVENT_ID,
                      "admin_division": div, "status": status, "comment": f"deklaracja syntetyczna: {nm}", "forces_and_assets": assets})
readiness.sort(key=lambda x: x["timestamp"])

# ----------------------------------------------------------------------------
# 12. Zapis
# ----------------------------------------------------------------------------
write_csv("dim_voivodeship.csv", voiv_rows)
write_csv("dim_county.csv", county_rows, ["county_code", "county_name", "voivodeship_code", "population", "area_km2", "lat", "lon", "is_seat_city"])
write_csv("dim_municipality.csv", muni_rows)
write_csv("dim_school.csv", schools)
write_csv("dim_report_category.csv", [
    {"category_code": "BRON", "category_name": "Niebezpieczne narzędzie lub broń", "tile_order": 1},
    {"category_code": "GROZBY", "category_name": "Groźby lub zapowiedź ataku", "tile_order": 2},
    {"category_code": "TRESCI_SIEC", "category_name": "Niepokojące treści w sieci", "tile_order": 3},
    {"category_code": "PRZEMOC", "category_name": "Przemoc lub nękanie", "tile_order": 4},
    {"category_code": "SAMOUSZKODZENIE", "category_name": "Ktoś może zrobić sobie krzywdę", "tile_order": 5},
    {"category_code": "INNE", "category_name": "Inne zagrożenie", "tile_order": 6}])
write_csv("dim_priority.csv", [
    {"priority_code": "NISKI", "priority_name": "Niski", "rank": 1, "color": "#15803d"},
    {"priority_code": "SREDNI", "priority_name": "Średni", "rank": 2, "color": "#a16207"},
    {"priority_code": "WYSOKI", "priority_name": "Wysoki", "rank": 3, "color": "#c2410c"},
    {"priority_code": "KRYTYCZNY", "priority_name": "Krytyczny", "rank": 4, "color": "#d5233f"}])
write_csv("dim_status.csv", [
    {"status_code": "NOWE", "status_name": "Nowe", "rank": 1}, {"status_code": "W_ANALIZIE", "status_name": "W analizie", "rank": 2},
    {"status_code": "PRZEKAZANE", "status_name": "Przekazane", "rank": 3}, {"status_code": "ZAMKNIETE", "status_name": "Zamknięte", "rank": 4}])
write_csv("dim_recipient.csv", [
    {"recipient_code": "POL", "recipient_name": "Policja", "level": "aplikacja", "ministry_division": "XIX"},
    {"recipient_code": "DIR", "recipient_name": "Dyrekcja szkoły", "level": "aplikacja", "ministry_division": "XV"},
    {"recipient_code": "PED", "recipient_name": "Pedagog/psycholog", "level": "aplikacja", "ministry_division": "XV"},
    {"recipient_code": "DYZ", "recipient_name": "Dyżurnet.pl (NASK)", "level": "aplikacja", "ministry_division": "X"},
    {"recipient_code": "KUR", "recipient_name": "Kuratorium Oświaty", "level": "krajowy", "ministry_division": "XV"},
    {"recipient_code": "MEN", "recipient_name": "Ministerstwo Edukacji Narodowej", "level": "krajowy", "ministry_division": "XV"},
    {"recipient_code": "RCB", "recipient_name": "Rządowe Centrum Bezpieczeństwa", "level": "krajowy", "ministry_division": "I"},
    {"recipient_code": "CSIRT", "recipient_name": "CSIRT NASK", "level": "krajowy", "ministry_division": "X"}])

SCEN_HAZ = {"Z04": "kampania skoordynowanych fałszywych alarmów (działania hybrydowe)", "Z16": "alarmy bombowe i realne groźby ataku",
            "Z18": "panika, tłumne odbieranie dzieci, blokady dojazdów", "Z20": "fałszywe nagrania zapowiedzi ataku w mediach społecznościowych",
            "Z12": "przeciążenie 112 i telefonów szkół (opcjonalnie)"}
haz = read_csv(REF / "dim_hazard.csv")
for h in haz:
    h["in_scenario"] = 1 if h["hazard_code"] in SCEN_HAZ else 0
    h["scenario_role"] = SCEN_HAZ.get(h["hazard_code"], "")
write_csv("dim_hazard.csv", haz)
SCEN_SPO = {"SPO-1": "posiedzenie RZZK", "SPO-3": "komunikacja z ludnością (rodzice, media)", "SPO-10": "współpraca z operatorami łączności alarmowej",
            "SPO-12": "obieg informacji między dyżurnymi, kuratoriami, Policją i RCB", "SPO-16": "Zespół ds. Incydentów Krytycznych"}
spo = read_csv(REF / "dim_spo.csv")
for s in spo:
    s["in_scenario"] = 1 if s["spo_code"] in SCEN_SPO else 0
    s["scenario_role"] = SCEN_SPO.get(s["spo_code"], "")
write_csv("dim_spo.csv", spo)
SCEN_DIV = {"I": "RCB i obieg informacji", "X": "CSIRT NASK, Dyżurnet.pl, dezinformacja", "XIII": "operatorzy łączności i 112", "XV": "kuratoria i szkoły, komunikacja do rodziców",
            "XIX": "Policja", "XIV": "cyberobrona (wg potrzeby)", "XX": "współpraca międzynarodowa (wg potrzeby)"}
div = read_csv(REF / "dim_admin_division.csv")
for d in div:
    d["in_scenario"] = 1 if d["admin_division"] in SCEN_DIV else 0
    d["scenario_role"] = SCEN_DIV.get(d["admin_division"], "")
write_csv("dim_admin_division.csv", div)

report_rows = []
truth_rows = []
for r in reports:
    s = schools[r["school_idx"]]
    report_rows.append({
        "timestamp": iso(r["ts"]), "stream": "report", "report_id": r["report_id"], "bs_no": r["bs_no"], "school_id": s["school_id"],
        "school_name": s["school_name"], "county_code": r["county_code"], "voivodeship_code": r["voivodeship_code"], "lat": s["lat"], "lon": s["lon"],
        "category_code": r["category"], "report_text": r["text"], "link_url": r["link"], "has_link": 1 if r["link"] else 0,
        "sender_token_day": r["sender_token_day"], "client_class": r["client"], "submit_latency_s": r["latency"],
        "ai_category_code": r["ai_category"], "ai_priority_code": r["ai_priority"], "ai_score": r["ai_score"],
        "ai_signals": ";".join(r["ai_signals"]), "ai_confidence": r["ai_confidence"], "ai_recipient_code": r["ai_recipient"],
    })
    truth_rows.append({"report_id": r["report_id"], "truth_label": r["label"], "campaign_id": r["campaign"], "true_severity": r["true_sev"],
                       "is_campaign_related": 1 if r["label"] in campaign_labels else 0,
                       "is_bot_sender": 1 if r["bot"] else 0,
                       "is_real_critical": 1 if (r["true_sev"] == 4 and r["label"] in ("background", "real_critical_wave")) else 0})
write_jsonl("fact_report.jsonl", report_rows)
write_jsonl("fact_report_update.jsonl", updates)
write_csv("fact_report_status.csv", [{
    "report_id": r["report_id"], "report_ts": iso(r["ts"]), "decision_ts": iso(r["decision_ts"]), "first_handoff_ts": iso(r["first_handoff_ts"]),
    "closed_ts": iso(r["closed_ts"]) if r["closed_ts"] else "", "duty_priority_code": r["duty_priority"], "status_code": r["status"],
    "duty_officer": r["officer"], "recipient_code": r["recipient"], "queue_len_at_decision_start": r["queue_len_at_start"],
    "decision_delay_min": r["decision_delay_min"]} for r in reports])
write_csv("fact_report_handoff.csv", handoffs)
write_csv("fact_report_truth.csv", truth_rows)
write_csv("dim_campaign.csv", [
    {"campaign_id": "K1", "campaign_name": "Fałszywe alarmy bombowe (boty)", "hazard_codes": "Z16;Z04", "coordinated": 1, "first_ts": iso(min(r["ts"] for r in reports if r["campaign"] == "K1"))},
    {"campaign_id": "K2", "campaign_name": "Fałszywe nagrania zapowiedzi ataku (boty i dobrowolne zgłoszenia uczniów)", "hazard_codes": "Z20;Z04", "coordinated": 1, "first_ts": iso(min(r["ts"] for r in reports if r["campaign"] == "K2"))},
    {"campaign_id": "K3", "campaign_name": "Naśladownictwo po głośnym incydencie (nieskoordynowane)", "hazard_codes": "Z18;Z16", "coordinated": 0, "first_ts": iso(min(r["ts"] for r in reports if r["campaign"] == "K3"))},
    {"campaign_id": "R", "campaign_name": "Realne krytyczne zgłoszenia ukryte w fali", "hazard_codes": "Z16", "coordinated": 0, "first_ts": iso(min(r["ts"] for r in reports if r["campaign"] == "R"))}])
write_jsonl("fact_hotline_load.jsonl", hotline)
write_jsonl("fact_social_signal.jsonl", social)
write_jsonl("fact_disorder_event.jsonl", disorder)
write_csv("fact_police_patrol.csv", patrol_rows)
write_csv("fact_support_capacity.csv", support_rows)
write_csv("fact_escalation_event.csv", esc_rows)
write_jsonl("fact_task_activation.jsonl", task_rows)
write_jsonl("fact_readiness_declaration.jsonl", readiness)

counts = {
    "schools": len(schools), "reports": len(reports), "report_updates": len(updates), "handoffs": len(handoffs),
    "hotline_rows": len(hotline), "social_rows": len(social), "disorder_events": len(disorder), "patrol_rows": len(patrol_rows),
    "support_rows": len(support_rows), "task_rows": len(task_rows), "readiness_rows": len(readiness),
    "by_label": {k: sum(1 for r in reports if r["label"] == k) for k in sorted({r["label"] for r in reports})},
    "first_bs": reports[0]["report_id"], "last_bs": reports[-1]["report_id"],
}
(OUT / "derived" / "dataset_counts.json").write_text(json.dumps(counts, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(counts, indent=2, ensure_ascii=False))
