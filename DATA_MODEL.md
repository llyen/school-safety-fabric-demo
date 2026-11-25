# Model danych

Wszystkie dane są syntetyczne (seed=42). Generator: `generate_datasets.py`, wyniki w `datasets\`
(CSV dla wymiarów i faktów tabelarycznych, JSONL dla zdarzeń). Liczności z `datasets\derived\dataset_counts.json`.

## Wymiary

| Tabela | Wierszy | Uwagi |
|---|---|---|
| dim_voivodeship | 16 | flaga `duty_center_in_app_today` (tylko mazowieckie) |
| dim_county | 380 | powiaty, kody TERYT syntetyczne wg konwencji przyjętej w demo |
| dim_municipality | 2477 | gminy |
| dim_school | 4215 | szkoły syntetyczne, typ, liczba uczniów, współrzędne |
| dim_report_category | 6 | kafle aplikacji |
| dim_priority | 4 | NISKI, SREDNI, WYSOKI, KRYTYCZNY |
| dim_status | 4 | NOWE, W_ANALIZIE, PRZEKAZANE, ZAMKNIETE |
| dim_recipient | 8 | POL, DIR, PED, DYZ, KUR, MEN, RCB, CSIRT |
| dim_hazard | 20 | zagrożenia KPZK, w scenariuszu Z04, Z16, Z18, Z20 |
| dim_spo | 16 | Standardowe Procedury Operacyjne |
| dim_admin_division | 25 | działy administracji rządowej |
| dim_campaign | 4 | kampanie K1, K2, K3 i tło |

Kategorie zgłoszeń: BRON, GROZBY, TRESCI_SIEC, PRZEMOC, SAMOUSZKODZENIE, INNE.

## Fakty

| Tabela | Wierszy | Treść |
|---|---|---|
| fact_report | 4560 | zgłoszenie: numer BS, czas, szkoła, kategoria, tekst, sugestia AI (priorytet, sygnały) |
| fact_report_truth | 4560 | ground truth do ewaluacji: etykieta, kampania, bot, realne krytyczne |
| fact_report_status | 4560 | decyzja dyżurnego, czasy, opóźnienie, długość kolejki |
| fact_report_update | 13565 | zmiany statusu |
| fact_report_handoff | 5386 | przekazania z czasem |
| fact_hotline_load | 16896 | obciążenie 112 i telefonów szkół |
| fact_social_signal | 1547 | zasięg treści w mediach społecznościowych |
| fact_disorder_event | 263 | zdarzenia Z18: tłumne odbieranie dzieci, blokady, protesty |
| fact_police_patrol | 4180 | patrole per powiat |
| fact_support_capacity | 1140 | pedagodzy i psycholodzy per powiat |
| fact_task_activation | 45 | zadania działów administracji i SPO |
| fact_readiness_declaration | 7 | deklaracje gotowości |
| fact_escalation_event | 6 | zdarzenia eskalacji |

Numery zgłoszeń: BS-2770 do BS-7329. Etykiety ground truth: tło 1771, K1 alarmy bombowe (boty) 953,
K2 fałszywe nagrania z botami 650, K2 rozsiewane organicznie 850, K3 naśladowczy 320, realne krytyczne w fali 16.
W całym zbiorze `is_real_critical` ma 112 rekordów, z czego 16 w fali.

## Wyniki notebooków (`datasets\derived\`)

Priorytet i reakcja (`priority_*`), klastry (`campaign_*`), KIZS (`kizs_*`), zasoby (`resources_*`)
i what-if (`whatif_*`), plus `metrics_01..05.json`. Pliki z Fabric (Spark) trafiają do tych samych
tabel Delta i mogą się różnić drobnie w klastrach.

## Model semantyczny `sm_school_safety`

27 tabel, 18 relacji (schemat gwiazdy wokół szkoły, powiatu i województwa), 33 miary DAX. Opis w
`semantic-model\MODEL.md` i `semantic-model\MEASURES.md`. Relacji z faktu zgłoszeń do województwa nie
ma celowo: byłaby drugą ścieżką obok szkoły i powiatu (niejednoznaczność). Województwo filtruje zgłoszenia
przez szkołę i powiat.

## Eventhouse

Tabele: DimVoivodeship 16, DimCounty 380, DimSchool 4215, SchoolReport 4560, ReportUpdate 13565,
HotlineLoad 16896, SocialSignal 1547, DisorderEvent 263, CampaignClusters 58 i inne (`kql\01_create_tables.kql`).
Czas w KQL jest w UTC, a lokalny D0 08:41 to 06:41Z.
