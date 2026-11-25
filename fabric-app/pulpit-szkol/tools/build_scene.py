"""Buduje statyczna scene pulpitu z zasobow repo (datasets\\ i datasets\\derived\\).

Uruchomienie (z katalogu aplikacji):
    $env:PYTHONUTF8=1; python tools\\build_scene.py

Wynik: public\\data\\scene.json, reports.json, schools.json.
Zbiory zrodlowe sa tylko czytane. Plik fact_report_truth.csv sluzy wylacznie do
nadania klastrom nazwy kampanii z katalogu scenariusza (dim_campaign); etykiet
prawdy nie ma w zadnym pliku wynikowym.
"""
from __future__ import annotations

import json
import math
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DS = ROOT / "datasets"
DER = DS / "derived"
OUT = Path(__file__).resolve().parents[1] / "public" / "data"
RINGS_FILE = Path(__file__).resolve().parent / "poland_rings.json"
INWARD = 0.06


def csv(path: Path, **kw) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"county_code": str, "voivodeship_code": str}, **kw)


def jsonl(path: Path) -> pd.DataFrame:
    return pd.read_json(path, lines=True, dtype={"county_code": str, "voivodeship_code": str})


def c4(x) -> str:
    return str(int(x)).zfill(4)


def v2(x) -> str:
    return str(int(x)).zfill(2)


# ---------- geografia: przyciaganie punktow do wlasnych wojewodztw ----------

def _fold(text: str) -> str:
    text = text.replace("\u0142", "l").replace("\u0141", "L")
    s = unicodedata.normalize("NFD", text)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def load_regions() -> dict:
    with open(RINGS_FILE, encoding="utf-8") as f:
        return {_fold(k): v for k, v in json.load(f).items()}


def in_region(lon, lat, rings) -> bool:
    inside = False
    for ring in rings:
        n = len(ring)
        for i in range(n):
            x1, y1 = ring[i]
            x2, y2 = ring[(i + 1) % n]
            if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
    return inside


def snap_into(lon, lat, rings):
    best, cen, bd = None, (lon, lat), float("inf")
    for ring in rings:
        cx = sum(p[0] for p in ring) / len(ring)
        cy = sum(p[1] for p in ring) / len(ring)
        for x, y in ring:
            d = math.hypot((lon - x) * 68.5, (lat - y) * 111.2)
            if d < bd:
                bd, best, cen = d, (x, y), (cx, cy)
    if best is None:
        return lon, lat
    vx, vy = best
    cx, cy = cen
    for k in (INWARD, 0.12, 0.25, 0.5):
        nx, ny = round(vx + (cx - vx) * k, 3), round(vy + (cy - vy) * k, 3)
        if in_region(nx, ny, rings):
            return nx, ny
    return round(cx, 3), round(cy, 3)


def place(lon, lat, rings):
    lon, lat = round(float(lon), 3), round(float(lat), 3)
    if rings is None or in_region(lon, lat, rings):
        return lon, lat, 0
    nl, nt = snap_into(lon, lat, rings)
    return nl, nt, 1


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    regions = load_regions()

    voiv = csv(DS / "dim_voivodeship.csv")
    voiv["voivodeship_code"] = voiv["voivodeship_code"].map(v2)
    vname = dict(zip(voiv.voivodeship_code, voiv.voivodeship_name))
    vrings = {c: regions.get(_fold(n)) for c, n in vname.items()}

    county = csv(DS / "dim_county.csv")
    county["county_code"] = county["county_code"].map(c4)
    county["voivodeship_code"] = county["voivodeship_code"].map(v2)

    schools = csv(DS / "dim_school.csv")
    schools["county_code"] = schools["county_code"].map(c4)
    schools["voivodeship_code"] = schools["voivodeship_code"].map(v2)

    moved = 0
    sch_out, sch_xy = [], {}
    for r in schools.itertuples():
        lon, lat, m = place(r.lon, r.lat, vrings.get(r.voivodeship_code))
        moved += m
        sch_xy[r.school_id] = (lon, lat)
        sch_out.append({
            "id": r.school_id, "name": r.school_name, "type": r.school_type,
            "v": r.voivodeship_code, "c": r.county_code, "loc": r.locality_name,
            "students": int(r.students), "lat": lat, "lon": lon,
        })
    print(f"szkoly: {len(sch_out)}, przesuniete do wlasnego wojewodztwa: {moved}")

    students_by_county = schools.groupby("county_code").students.sum().to_dict()
    cty_out = []
    for r in county.itertuples():
        lon, lat, _ = place(r.lon, r.lat, vrings.get(r.voivodeship_code))
        cty_out.append({
            "code": r.county_code, "name": r.county_name, "v": r.voivodeship_code,
            "pop": int(r.population), "students": int(students_by_county.get(r.county_code, 0)),
            "lat": lat, "lon": lon,
        })

    # ---------- czas ----------
    kh = csv(DER / "kizs_voivodeship_hourly.csv")
    kh["voivodeship_code"] = kh["voivodeship_code"].map(v2)
    kh["t"] = pd.to_datetime(kh["hour"], utc=True).dt.tz_convert("Europe/Warsaw")
    start = kh["t"].min()
    kh["h"] = ((kh["t"] - start).dt.total_seconds() // 3600).astype(int)
    n_hours = int(kh["h"].max()) + 1
    start_iso = start.isoformat()

    def minutes(series) -> pd.Series:
        t = pd.to_datetime(series, utc=True).dt.tz_convert("Europe/Warsaw")
        return ((t - start).dt.total_seconds() / 60).round(1)

    def mn(value):
        if value is None or (isinstance(value, float) and math.isnan(value)) or value == "":
            return None
        t = pd.to_datetime(value, utc=True).tz_convert("Europe/Warsaw")
        return round((t - start).total_seconds() / 60, 1)

    def series(df, col, code_col="voivodeship_code", digits=3):
        out = {}
        for code, g in df.groupby(code_col):
            arr = [0.0] * n_hours
            for h, v in zip(g["h"], g[col]):
                if 0 <= h < n_hours:
                    arr[int(h)] = round(float(v), digits)
            out[code] = arr
        return out

    kizs = {c: series(kh, c, digits=3)
            for c in ["kizs", "c_signals", "c_campaign", "c_hotline", "c_backlog", "c_disorder"]}
    kizs = {k: v for k, v in kizs.items()}

    nat = csv(DER / "kizs_national_hourly.csv")
    nat["t"] = pd.to_datetime(nat["hour"], utc=True).dt.tz_convert("Europe/Warsaw")
    nat["h"] = ((nat["t"] - start).dt.total_seconds() // 3600).astype(int)
    nat = nat.sort_values("h")
    national = {col: [float(x) if not isinstance(x, (bool,)) else bool(x) for x in nat[col]]
                for col in ["campaign_24h", "campaign_voivodeships_24h", "genuine_critical_24h",
                            "voivodeships_112_over_1_5", "disorder_24h", "kizs_national_mean"]}
    national["rec"] = {col: [bool(x) for x in nat[col]]
                       for col in ["rec_minister", "rec_rzzk", "rec_voivode_any"]}

    # ---------- 112 ----------
    hot = jsonl(DS / "fact_hotline_load.jsonl")
    hot["voivodeship_code"] = hot["voivodeship_code"].map(v2)
    hot["t"] = pd.to_datetime(hot["timestamp"], utc=True).dt.tz_convert("Europe/Warsaw")
    hot["h"] = ((hot["t"] - start).dt.total_seconds() // 3600).astype(int)
    hg = hot.groupby(["voivodeship_code", "h"]).agg(
        load=("load_ratio", "max"), calls=("calls_112_total", "sum"),
        school=("calls_112_school_related", "sum"), wait=("wait_p90_s", "max"),
        abandoned=("abandoned_pct", "max")).reset_index()
    hotline = {"load": series(hg, "load"), "calls": series(hg, "calls", digits=0),
               "school": series(hg, "school", digits=0), "wait": series(hg, "wait", digits=1),
               "abandoned": series(hg, "abandoned", digits=1)}

    # ---------- social ----------
    soc = jsonl(DS / "fact_social_signal.jsonl")
    soc["t"] = pd.to_datetime(soc["timestamp"], utc=True).dt.tz_convert("Europe/Warsaw")
    soc["h"] = ((soc["t"] - start).dt.total_seconds() // 3600).astype(int)
    social = {}
    for nid, g in soc.groupby("narrative_id"):
        agg = g.groupby("h").agg(posts=("posts", "sum"), reach=("est_reach", "sum"),
                                 bot=("bot_score_mean", "mean"), newacc=("new_account_share", "mean"),
                                 accounts=("unique_accounts", "sum")).reset_index()
        def arr(col, d):
            a = [0.0] * n_hours
            for h, v in zip(agg["h"], agg[col]):
                if 0 <= h < n_hours:
                    a[int(h)] = round(float(v), d)
            return a
        plat = g.groupby("platform").posts.sum().sort_values(ascending=False)
        social[nid] = {"name": g["narrative_name"].iloc[0], "posts": arr("posts", 0),
                       "reach": arr("reach", 0), "bot": arr("bot", 3), "newAcc": arr("newacc", 3),
                       "accounts": arr("accounts", 0),
                       "platforms": {p: int(v) for p, v in plat.items()}}

    # ---------- powiaty dziennie ----------
    cd = csv(DER / "kizs_county_daily.csv")
    cd["county_code"] = cd["county_code"].map(c4)
    days = sorted(cd["day"].unique())
    day_of = {d: i for i, d in enumerate(days)}
    kizs_county = {}
    for code, g in cd.groupby("county_code"):
        arr = [0.0] * len(days)
        rep = [0] * len(days)
        for d, k, n in zip(g["day"], g["county_kizs"], g["reports"]):
            arr[day_of[d]] = round(float(k), 2)
            rep[day_of[d]] = int(n)
        kizs_county[code] = {"kizs": arr, "reports": rep}

    # ---------- zgloszenia ----------
    rep = pd.read_json(DS / "fact_report.jsonl", lines=True, dtype={"county_code": str, "voivodeship_code": str})
    rep["county_code"] = rep["county_code"].map(c4)
    rep["voivodeship_code"] = rep["voivodeship_code"].map(v2)
    st = csv(DS / "fact_report_status.csv").set_index("report_id")
    flags = pd.read_csv(DER / "campaign_report_flags.csv").set_index("report_id")
    truth = pd.read_csv(DS / "fact_report_truth.csv").set_index("report_id")
    ho = csv(DS / "fact_report_handoff.csv")
    ho_by = {k: g for k, g in ho.groupby("report_id")}

    clusters = pd.read_csv(DER / "campaign_clusters.csv")
    cl_camp = {}
    for cid, g in flags.assign(camp=truth["campaign_id"]).groupby("cluster_id"):
        vc = g["camp"].dropna()
        cl_camp[int(cid)] = vc.value_counts().index[0] if len(vc) else None

    rep_out = []
    for r in rep.itertuples():
        s = st.loc[r.report_id]
        f = flags.loc[r.report_id]
        hs = []
        if r.report_id in ho_by:
            for h in ho_by[r.report_id].itertuples():
                hs.append([mn(h.handoff_ts), h.recipient_code, int(h.is_primary), h.reason,
                           mn(h.acknowledged_ts), h.outcome if isinstance(h.outcome, str) else None,
                           mn(h.outcome_ts)])
        lon, lat = sch_xy.get(r.school_id, (round(float(r.lon), 3), round(float(r.lat), 3)))
        coord = int(f["cluster_id"])
        rep_out.append({
            "id": r.report_id, "n": int(r.report_id.split("-")[1]), "t": mn(r.timestamp),
            "sch": r.school_id, "sn": r.school_name, "v": r.voivodeship_code, "c": r.county_code,
            "lat": lat, "lon": lon, "cat": r.category_code, "text": r.report_text,
            "link": int(bool(r.has_link)), "client": r.client_class,
            "ai": {"cat": r.ai_category_code, "pri": r.ai_priority_code, "score": float(r.ai_score),
                   "sig": [x for x in str(r.ai_signals).split(";") if x and x != "nan"],
                   "conf": float(r.ai_confidence), "rec": r.ai_recipient_code},
            "dec": {"t": mn(s.decision_ts), "pri": s.duty_priority_code, "status": s.status_code,
                    "officer": s.duty_officer, "rec": s.recipient_code,
                    "queue": int(s.queue_len_at_decision_start), "delay": float(s.decision_delay_min)},
            "ho": hs, "t1": mn(s.first_handoff_ts), "tc": mn(s.closed_ts),
            "cl": coord if int(f["in_coordinated_cluster"]) else None,
            "flag": int(f["campaign_flag"]), "keep": int(f["keep_for_human"]),
            "guard": int(bool(f["guard_text"])),
        })
    rep_out.sort(key=lambda x: x["t"])

    # ---------- kampanie ----------
    camp_cat = pd.read_csv(DS / "dim_campaign.csv")
    camp_defs = {r.campaign_id: {"id": r.campaign_id, "name": r.campaign_name,
                                 "coordinated": int(r.coordinated)} for r in camp_cat.itertuples()}
    cl_out = []
    for r in clusters.itertuples():
        if r.size < 20 and not r.coordinated:
            continue
        cl_out.append({
            "id": int(r.cluster), "size": int(r.size), "counties": int(r.counties),
            "voivodeships": int(r.voivodeships), "schools": int(r.schools),
            "spanH": float(r.span_h), "perHour": float(r.reports_per_hour),
            "linkShare": float(r.repeated_link_share), "tokenShare": float(r.repeated_token_share),
            "autoShare": float(r.automated_client_share), "latency": float(r.median_latency_s),
            "first": mn(r.first_ts), "last": mn(r.last_ts), "coordinated": int(bool(r.coordinated)),
            "camp": cl_camp.get(int(r.cluster)),
        })

    real = pd.read_csv(DER / "campaign_real_critical_check.csv")
    hidden = [{"id": r.report_id, "t": mn(r.ts), "v": v2(r.voivodeship_code),
               "c": c4(r.county_code), "keep": int(r.keep_for_human),
               "inCluster": int(r.in_coordinated_cluster)} for r in real.itertuples()]

    # ---------- eskalacja, zadania ----------
    esc = pd.read_csv(DS / "fact_escalation_event.csv")
    esc_out = [{"id": r.escalation_id, "t": mn(r.timestamp), "level": r.level, "scope": r.scope,
                "type": r.decision_type, "actor": r.actor_role, "desc": r.description}
               for r in esc.itertuples()]
    tasks = jsonl(DS / "fact_task_activation.jsonl")
    task_out = []
    for r in tasks.to_dict("records"):
        row = {"t": mn(r["timestamp"]), "status": r["activation_status"], "id": r["task_id"],
               "spo": r["spo_code"], "div": r["leading_admin_division"], "level": r["level"],
               "title": r["task_title"], "due": mn(r.get("due_ts"))}
        for k in r:
            if k not in {"timestamp", "activation_status", "stream", "event_id", "task_id", "hazard_code",
                         "spo_code", "leading_admin_division", "level", "task_title", "due_ts"}:
                v = r[k]
                if isinstance(v, str):
                    row[k] = v
        task_out.append(row)
    ready = jsonl(DS / "fact_readiness_declaration.jsonl")
    ready_out = [{"t": mn(r.timestamp), "div": r.admin_division, "status": r.status,
                  "comment": r.comment, "forces": r.forces_and_assets} for r in ready.itertuples()]
    adm = pd.read_csv(DS / "dim_admin_division.csv")
    adm_out = [{"code": r.admin_division, "name": r.admin_name, "ministry": r.ministry,
                "inScenario": int(r.in_scenario)} for r in adm.itertuples()]
    spo = pd.read_csv(DS / "dim_spo.csv")
    spo_out = [{"code": r.spo_code, "name": r.spo_name, "inScenario": int(r.in_scenario)}
               for r in spo.itertuples()]
    rec = pd.read_csv(DS / "dim_recipient.csv")
    rec_out = [{"code": r.recipient_code, "name": r.recipient_name, "level": r.level,
                "div": r.ministry_division} for r in rec.itertuples()]

    # ---------- zasoby ----------
    cap = csv(DS / "fact_support_capacity.csv")
    cap["county_code"] = cap["county_code"].map(c4)
    support = {}
    for code, g in cap.groupby("county_code"):
        support[code] = {r.role: round(float(r.fte_available), 1) for r in g.itertuples()}
    pat = csv(DS / "fact_police_patrol.csv")
    pat["county_code"] = pat["county_code"].map(c4)
    pdays = sorted(pat["date"].unique())
    patrol = {}
    for code, g in pat.groupby("county_code"):
        g = g.set_index("date")
        patrol[code] = {
            "perShift": [int(g.loc[d, "patrols_per_shift_avg"]) if d in g.index else 0 for d in pdays],
            "util": [round(float(g.loc[d, "utilization_pct"]), 1) if d in g.index else 0 for d in pdays],
        }
    sup_def = csv(DER / "resources_support_top_deficit_d0.csv")
    pat_def = csv(DER / "resources_patrol_top_deficit_d0.csv")
    for d in (sup_def, pat_def):
        d["county_code"] = d["county_code"].map(c4)
        d["voivodeship_code"] = d["voivodeship_code"].map(v2)
    resources = {
        "supportDeficitD0": sup_def.round(1).to_dict("records"),
        "patrolDeficitD0": pat_def.round(1).to_dict("records"),
        "supportDaily": csv(DER / "resources_support_daily.csv").round(3).to_dict("records"),
        "patrolDaily": csv(DER / "resources_patrol_daily.csv").round(3).to_dict("records"),
        "supportDays": pdays and days,
    }

    scene = {
        "meta": {"start": start_iso, "hours": n_hours, "d0Hour": 72,
                 "days": [str(d) for d in days], "patrolDays": [str(d) for d in pdays],
                 "synthetic": True, "source": "datasets\\ i datasets\\derived\\ repozytorium ol-szkoly-bezpieczenstwo"},
        "voivodeships": [{"code": r.voivodeship_code, "name": r.voivodeship_name, "lat": float(r.lat),
                          "lon": float(r.lon), "pop": int(r.population)} for r in voiv.itertuples()],
        "counties": cty_out, "kizs": kizs, "national": national, "hotline": hotline, "social": social,
        "kizsCounty": kizs_county, "clusters": cl_out, "campaigns": list(camp_defs.values()),
        "hiddenReal": hidden, "escalations": esc_out, "tasks": task_out, "readiness": ready_out,
        "admin": adm_out, "spo": spo_out, "recipients": rec_out, "support": support, "patrol": patrol,
        "resources": resources,
    }
    for name, obj in (("scene.json", scene), ("reports.json", rep_out), ("schools.json", sch_out)):
        p = OUT / name
        p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str), encoding="utf-8")
        print(name, round(p.stat().st_size / 1e6, 2), "MB")
    print("godziny:", n_hours, "zgloszenia:", len(rep_out), "klastry:", len(cl_out))


if __name__ == "__main__":
    main()
