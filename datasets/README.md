# Zbiory danych

> Wszystkie dane są w 100% syntetyczne. Szkoły, powiaty, gminy, kody TERYT, numery zgłoszeń, treści i liczby
> połączeń zostały wygenerowane przez `generate_datasets.py` (seed=42). Prawdziwe są tylko nazwy województw,
> które służą jako poziom agregacji. Powiaty, miasta i gminy mają nazwy kodowe (np. „powiat P-0201”,
> „Miasto M-1402”, „Gmina G-0201002”), a szkoły nazywają się według typu, numeru i takiej kodowej
> miejscowości, więc żadne zgłoszenie nie jest przypisane do istniejącej szkoły ani miejscowości. Treści zgłoszeń opisują sygnały, nie zawierają instrukcji ani szczegółów
> operacyjnych. Nie odzwierciedlają żadnego rzeczywistego zdarzenia ani osoby.

Odtworzenie: `python generate_datasets.py` z katalogu głównego. Wynik jest powtarzalny.

## Liczności (z `derived\dataset_counts.json`)

| Zbiór | Wierszy |
|---|---|
| dim_school | 4215 |
| fact_report | 4560 (BS-2770 do BS-7329) |
| fact_report_update | 13565 |
| fact_report_handoff | 5386 |
| fact_hotline_load | 16896 |
| fact_social_signal | 1547 |
| fact_disorder_event | 263 |
| fact_police_patrol | 4180 |
| fact_support_capacity | 1140 |
| fact_task_activation | 45 |
| fact_readiness_declaration | 7 |

Wymiary: 16 województw, 380 powiatów, 2477 gmin, 6 kategorii zgłoszeń, 4 priorytety, 4 statusy, 8 adresatów,
20 zagrożeń KPZK, 16 SPO, 25 działów administracji.

## Ground truth

`fact_report_truth.csv` zawiera etykietę kampanii (tło 1771, K1 953, K2 z botami 650, K2 organiczne 850, K3
naśladowczy 320, realne krytyczne w fali 16) i służy wyłącznie do ewaluacji detekcji. Nie jest dostępne
dyżurnemu w żadnym widoku.

## Wyniki notebooków

`derived\` zawiera wyniki z lokalnego uruchomienia notebooków 01 do 05 (CSV i `metrics_*.json`). Uruchomienie
tych samych notebooków w Fabric daje drobne różnice w klastrach, opisane w `DEPLOYMENT_STATUS.md`. Pliki
`dry_run_*.jsonl` są lokalnymi wynikami symulatora i nie trafiają do repozytorium.

Czasy w danych są w UTC, D0 to 2026-10-09.
