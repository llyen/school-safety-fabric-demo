# CELL
"""02 - detekcja kampanii (klastry czas / tresc / nadawca / geografia).

Cel: odroznic skoordynowana fale od pojedynczych realnych zgloszen i nie przeoczyc realnego krytycznego.
Metoda: TF-IDF na tekscie po normalizacji, krawedz miedzy podobnymi zgloszeniami bliskimi w czasie
albo ze wspolnym linkiem, skladowe spojne jako kandydaci na klastry, potem ocena klastra
(rozmiar, liczba powiatow, tempo, powtarzalnosc linku i tokenu nadawcy, wzorzec klienta).
Ground truth (fact_report_truth) sluzy tylko do liczenia precision / recall.
Wyjscie: derived/campaign_*.csv oraz derived/metrics_02.json.
"""
from pathlib import Path
import json
import re

import numpy as np
import pandas as pd
from scipy.sparse.csgraph import connected_components
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "datasets"
OUT = DATA / "derived"
OUT.mkdir(exist_ok=True)
TZ = "Europe/Warsaw"
D0_RZZK = pd.Timestamp("2026-10-09 14:00", tz=TZ)

# CELL
rep = pd.read_json(DATA / "fact_report.jsonl", lines=True, dtype={"county_code": str, "voivodeship_code": str})
tru = pd.read_csv(DATA / "fact_report_truth.csv")
d = rep.merge(tru, on="report_id").sort_values("timestamp").reset_index(drop=True)
d["ts"] = pd.to_datetime(d.timestamp, utc=True).dt.tz_convert(TZ)
d["link_key"] = d.link_url.fillna("").str.replace(r"^https?://", "", regex=True)
d["link_domain"] = d.link_key.str.split("/").str[0]
print(len(d), "zgloszen;", d.truth_label.value_counts().to_dict())

# CELL - normalizacja tekstu: usuwamy nazwe szkoly, klase, liczby i adresy, zostaje wzorzec jezykowy
def normalize(row) -> str:
    t = row.report_text.lower()
    t = re.sub(r"https?://\S+", " URL ", t)
    t = t.replace(str(row.school_name).lower(), " ")
    t = re.sub(r"szkoła [a-ząćęłńóśźż ]+ nr \d+[^.]*\.?$", " ", t)
    t = re.sub(r"\b\d+[a-z]\b", " KLASA ", t)
    t = re.sub(r"\d{1,2}:\d{2}", " GODZ ", t)
    t = re.sub(r"\d+", " # ", t)
    return re.sub(r"\s+", " ", t).strip()


d["norm"] = d.apply(normalize, axis=1)
vec = TfidfVectorizer(ngram_range=(1, 2), min_df=3, sublinear_tf=True)
X = vec.fit_transform(d.norm)
S = (X @ X.T).toarray().astype(np.float32)
print("macierz tekstu", X.shape)

# CELL - graf: podobienstwo tekstu i bliskosc w czasie albo wspolny link
SIM_MIN, WINDOW_H = 0.50, 36
t_h = d.ts.astype("int64").to_numpy() / 3.6e12
dt = np.abs(t_h[:, None] - t_h[None, :])
A = (S >= SIM_MIN) & (dt <= WINDOW_H)
link_id = d.link_key.where(d.link_key != "", None)
same_link = (link_id.to_numpy()[:, None] == link_id.to_numpy()[None, :]) & link_id.notna().to_numpy()[:, None]
A |= same_link & (dt <= 72)
np.fill_diagonal(A, False)
n_comp, labels = connected_components(csr_matrix(A), directed=False)
d["cluster"] = labels
print("skladowe:", n_comp)

# CELL - ocena klastra
def span_h(g):
    return (g.ts.max() - g.ts.min()).total_seconds() / 3600


rows = []
for cid, g in d.groupby("cluster"):
    if len(g) < 5:
        continue
    tokens = g.sender_token_day.value_counts()
    rows.append({
        "cluster": cid, "size": len(g), "counties": g.county_code.nunique(), "voivodeships": g.voivodeship_code.nunique(),
        "schools": g.school_id.nunique(), "span_h": round(span_h(g), 2),
        "reports_per_hour": round(len(g) / max(span_h(g), 1.0), 2),
        "repeated_link_share": round(float((g.link_key != "").mean() and g.link_key.duplicated(keep=False)[g.link_key != ""].mean()), 3),
        "repeated_token_share": round(float(g.sender_token_day.duplicated(keep=False).mean()), 3),
        "automated_client_share": round(float((g.client_class != "mobile_app").mean()), 3),
        "median_latency_s": round(float(g.submit_latency_s.median()), 1),
        "first_ts": g.ts.min(), "last_ts": g.ts.max(),
        "top_truth": g.truth_label.value_counts().idxmax(),
        "truth_purity": round(float(g.truth_label.value_counts(normalize=True).iloc[0]), 3),
    })
cl = pd.DataFrame(rows).sort_values("size", ascending=False)

# Regula klastra skoordynowanego: duzy, rozproszony geograficznie i z sygnalem automatyzacji
# (powtarzany link albo token nadawcy albo wyrazny wzorzec klienta albo bardzo szybkie wypelnienie formularza).
cl["coordinated"] = (
    (cl["size"] >= 20) & (cl["counties"] >= 8)
    & ((cl.repeated_link_share >= 0.2) | (cl.repeated_token_share >= 0.1) | (cl.automated_client_share >= 0.3) | (cl.median_latency_s < 20))
)
cl.to_csv(OUT / "campaign_clusters.csv", index=False)
print(cl.head(15).to_string())
coord_ids = set(cl[cl.coordinated].cluster)
d["in_coordinated_cluster"] = d.cluster.isin(coord_ids).astype(int)

# CELL - zabezpieczenie: zgloszenie z cechami pojedynczego, konkretnego zagrozenia trafia do czlowieka,
# nawet jesli jest w klastrze kampanii. Klasyfikujemy tresc zgloszenia, nie osoby.
GUARD = re.compile(
    r"zrzut ekranu|mam jego wiadomość|pożegnaln|nie odbiera telefonu|nie wstawał|nauczyciel|\bnóż|nożyk|ostre narzędzie|"
    r"przygotowany plan|zemści|nikt nie wyjdzie|będzie głośno|zdjęcie broni|obcy mężczyzna|nosi przy sobie|mówi to poważnie"
)
d["guard_text"] = d.report_text.str.lower().str.contains(GUARD)
cent = {}
for cid in coord_ids:
    idx = np.where(d.cluster.to_numpy() == cid)[0]
    c = np.asarray(X[idx].mean(axis=0)).ravel()
    cent[cid] = (c / (np.linalg.norm(c) + 1e-9))
sim_to_centroid = np.ones(len(d))
for i, cid in enumerate(d.cluster):
    if cid in cent:
        row = X[i].toarray().ravel()
        sim_to_centroid[i] = float(row @ cent[cid] / (np.linalg.norm(row) + 1e-9))
d["sim_to_centroid"] = sim_to_centroid.round(3)
d["outlier_in_cluster"] = ((d.in_coordinated_cluster == 1) & (d.sim_to_centroid < 0.30)).astype(int)
d["keep_for_human"] = ((d.in_coordinated_cluster == 0) | d.guard_text | (d.outlier_in_cluster == 1)).astype(int)
d["campaign_flag"] = d.in_coordinated_cluster
d["suppressed_from_queue"] = ((d.in_coordinated_cluster == 1) & (d.keep_for_human == 0)).astype(int)

# CELL - metryki: precision / recall detekcji
def pr(pred: pd.Series, truth: pd.Series) -> dict:
    tp = int(((pred == 1) & (truth == 1)).sum())
    fp = int(((pred == 1) & (truth == 0)).sum())
    fn = int(((pred == 0) & (truth == 1)).sum())
    p, r = tp / max(1, tp + fp), tp / max(1, tp + fn)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(p, 4), "recall": round(r, 4),
            "f1": round(2 * p * r / max(1e-9, p + r), 4)}


m_campaign = pr(d.campaign_flag, d.is_campaign_related)
m_bot = pr(d.campaign_flag, d.is_bot_sender)

# Punkty odniesienia: (a) sam skok wolumenu w wojewodztwie i godzinie, (b) slowa kluczowe
d["vh"] = d.ts.dt.floor("h")
vh = d.groupby(["voivodeship_code", "vh"]).size().rename("n_vh").reset_index()
base = vh.groupby("voivodeship_code").n_vh.agg(["median", lambda s: (s - s.median()).abs().median()])
base.columns = ["med", "mad"]
vh = vh.merge(base, on="voivodeship_code")
vh["spike"] = vh.n_vh > (vh.med + 6 * vh.mad.clip(lower=1)) + 3
d = d.merge(vh[["voivodeship_code", "vh", "spike"]], on=["voivodeship_code", "vh"], how="left")
d["baseline_volume_flag"] = d.spike.fillna(False).astype(int)
d["baseline_keyword_flag"] = d.report_text.str.lower().str.contains(r"bomb|zapowiedź ataku|zapowiada atak|atak w piątek").astype(int)
baselines = {
    "volume_spike_voivodeship_hour": pr(d.baseline_volume_flag, d.is_campaign_related),
    "keywords_bomb_attack": pr(d.baseline_keyword_flag, d.is_campaign_related),
    "content_cluster_system": m_campaign,
}
by_label = d.groupby("truth_label").agg(
    n=("report_id", "size"), flagged=("campaign_flag", "sum"),
    suppressed=("suppressed_from_queue", "sum"), kept_for_human=("keep_for_human", "sum")).reset_index()
by_label["flag_rate"] = (by_label.flagged / by_label.n).round(4)
by_label.to_csv(OUT / "campaign_flags_by_truth_label.csv", index=False)
print(by_label)
print(json.dumps(baselines, indent=2))

# CELL - realne krytyczne ukryte w fali (R): czy detekcja je zachowala
R = d[d.truth_label == "real_critical_wave"].copy()
R["in_cluster"] = R.in_coordinated_cluster
R_out = R[["report_id", "ts", "voivodeship_code", "county_code", "in_coordinated_cluster", "guard_text",
           "sim_to_centroid", "keep_for_human", "report_text"]].copy()
R_out.to_csv(OUT / "campaign_real_critical_check.csv", index=False)
# wariant bez zabezpieczenia: co by sie stalo przy samym filtrowaniu klastrow
hard = R[R.report_text.str.lower().str.contains("wybuch|bomb|ładunek")]
real_check = {
    "real_critical_in_wave": int(len(R)),
    "inside_coordinated_cluster": int(R.in_coordinated_cluster.sum()),
    "hidden_by_keyword_filter": int(R.baseline_keyword_flag.sum()),
    "hidden_by_volume_spike_filter": int(R.baseline_volume_flag.sum()),
    "preserved_for_human_with_guard": int(R.keep_for_human.sum()),
    "lost_with_guard": int((R.keep_for_human == 0).sum()),
    "hard_cases_with_bomb_vocabulary": int(len(hard)),
    "hard_cases_preserved": int(hard.keep_for_human.sum()),
}
fp_cost = {
    "background_flagged": int(((d.truth_label == "background") & (d.campaign_flag == 1)).sum()),
    "copycat_flagged": int(((d.truth_label == "k3_copycat") & (d.campaign_flag == 1)).sum()),
    "copycat_total": int((d.truth_label == "k3_copycat").sum()),
}
print(json.dumps(real_check, indent=2), fp_cost)

# CELL - skrocenie kolejki: ile zgloszen czlowiek musi przejrzec po odfiltrowaniu kampanii
queue = {
    "reports_total": int(len(d)),
    "campaign_related_total": int(d.is_campaign_related.sum()),
    "suppressed_to_cluster_view": int(d.suppressed_from_queue.sum()),
    "left_for_human_review": int(d.keep_for_human.sum()),
    "left_for_human_share": round(float(d.keep_for_human.mean()), 4),
}
# jedno zgloszenie realne wsrod N skoordynowanych: stosunek w dniu D0 (rano, przed RZZK)
d0 = d[(d.ts >= pd.Timestamp("2026-10-09 00:00", tz=TZ)) & (d.ts < D0_RZZK)]
queue["d0_before_rzzk_reports"] = int(len(d0))
queue["d0_before_rzzk_campaign_related"] = int(d0.is_campaign_related.sum())
queue["d0_before_rzzk_real_in_wave"] = int((d0.truth_label == "real_critical_wave").sum())

# CELL - czas wykrycia kampanii: kiedy klaster osiaga rozmiar >=20 w >=8 powiatach
det = []
for cid in sorted(coord_ids):
    g = d[d.cluster == cid].sort_values("ts")
    seen, hit = set(), None
    for k, (ts, cc) in enumerate(zip(g.ts, g.county_code), start=1):
        seen.add(cc)
        if k >= 20 and len(seen) >= 8:
            hit = ts
            break
    top = g.truth_label.value_counts().idxmax()
    camp = "K1" if top.startswith("k1") else "K2" if top.startswith("k2") else top
    det.append({"cluster": cid, "campaign_majority": camp, "size": len(g), "first_report_ts": g.ts.min(),
                "detection_ts": hit, "minutes_from_first": None if hit is None else round((hit - g.ts.min()).total_seconds() / 60, 1)})
det = pd.DataFrame(det)
if len(det):
    det.to_csv(OUT / "campaign_detection_time.csv", index=False)
    print(det.to_string())

# CELL - zapis wynikow na poziomie zgloszen i metryk
d[["report_id", "cluster", "in_coordinated_cluster", "guard_text", "sim_to_centroid", "keep_for_human",
   "campaign_flag", "suppressed_from_queue"]].rename(columns={"cluster": "cluster_id"}).to_csv(OUT / "campaign_report_flags.csv", index=False)

first_detect = det[det.detection_ts.notna()].detection_ts.min() if len(det) else None
metrics = {
    "similarity_threshold": SIM_MIN, "window_h": WINDOW_H,
    "components": int(n_comp), "coordinated_clusters": int(len(coord_ids)),
    "campaign_vs_truth": m_campaign, "bots_vs_truth": m_bot,
    "baselines": baselines,
    "real_critical_check": real_check, "false_positive_cost": fp_cost, "queue": queue,
    "first_detection_ts": None if first_detect is None else str(first_detect),
    "detection_before_rzzk_minutes": None if first_detect is None else round((D0_RZZK - first_detect).total_seconds() / 60, 0),
    "detection_by_campaign": det.assign(first_report_ts=det.first_report_ts.astype(str), detection_ts=det.detection_ts.astype(str)).to_dict("records") if len(det) else [],
}
(OUT / "metrics_02.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps({k: v for k, v in metrics.items() if k != "detection_by_campaign"}, indent=2, ensure_ascii=False, default=str))
