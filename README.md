# Szkoły i bezpieczeństwo: krajowa warstwa nad aplikacją zgłoszeń szkolnych

Wersja angielska: [README.en.md](README.en.md).

Scenariusz demonstracyjny z obszaru ochrony ludności i zarządzania kryzysowego na Microsoft Fabric.
Przykładowa aplikacja Power Apps do zgłoszeń szkolnych obsługuje zgłoszenie ucznia i dyżurnego (dziś w
województwie mazowieckim). To repozytorium dokłada poziom krajowy: wszystkie 16 województw,
drill-down do powiatu i szkoły, wykrywanie fal i korelacji między zgłoszeniami oraz decyzję
o eskalacji od powiatu przez wojewodę i ministra wiodącego aż do RZZK.

Pytanie decydenta: czy to fala fałszywych alarmów, czy realne zagrożenie, i gdzie muszę być pierwszy?

> Wszystkie dane są w 100% syntetyczne. Szkoły, powiaty, gminy, kody TERYT, numery zgłoszeń,
> treści i liczby połączeń zostały wygenerowane (seed=42). Prawdziwe są tylko nazwy województw,
> które służą jako poziom agregacji. Powiaty, miasta i gminy mają nazwy kodowe (np. „powiat P-0201”,
> „Miasto M-1402”, „Gmina G-0201002”), a szkoły nazywają się według typu, numeru i takiej kodowej
> miejscowości, więc żadne zgłoszenie nie jest przypisane do istniejącej szkoły ani miejscowości. Żadne zgłoszenie nie opisuje prawdziwego zdarzenia.
> Treści nie zawierają instrukcji ani operacyjnych szczegółów ataku, opisują wyłącznie sygnały.

## Trzy najważniejsze ustalenia (zmierzone, seed=42)

Zbiór ma 4560 zgłoszeń z 4215 szkół. Do kampanii skoordynowanej należy 2453 zgłoszeń, a wśród
nich i obok nich jest 16 realnych, krytycznych zgłoszeń, które fala miała ukryć.

1. Wszystkie 16 realnych krytycznych zgłoszeń zostało zachowanych dla człowieka, żadne nie wpadło
   do klastra kampanii. Filtr oparty na skoku wolumenu ukryłby 8 z nich, filtr po słowach
   kluczowych jedno. Wykrycie kampanii: precyzja 1,0, recall 0,9034, F1 0,9492 (7 klastrów
   skoordynowanych, największy ma 1263 zgłoszeń). Do człowieka trafia 2344 zgłoszeń z 4560 (51,4 proc.).
2. Pierwszą kampanię (K1, alarmy bombowe) system wykrywa 2026-10-07 o 14:43, czyli 2836 minut
   przed zwołaniem RZZK. Rekomendacja wojewódzka pojawia się w D0 o 08:00 dla mazowieckiego i śląskiego.
   Krajowy Indeks Zagrożenia Szkolnego (KIZS) osiąga szczyt 42,0, w mazowieckim 77,4.
3. Dyżurni w zasymulowanej kolejce nie nadążają: BS-4826 (nóż motylkowy w Mieście M-1402) czeka 152,6 min,
   a realne krytyczne zgłoszenie w najgorszym przypadku 607,5 min. Kolejka świadoma kampanii
   (wariant A4, zgłoszenia klastrów zwijane do jednej pozycji) sprowadza BS-4826 do 3,7 min, a maksymalne opóźnienie realnych do 7,3 min.
   Pokrycie patroli w najgorszym dniu rośnie z 0,949 do 1,0 po realokacji między powiatami (13 powiatów w deficycie).

Liczby pochodzą z notebooków `notebooks\01..05` uruchomionych lokalnie (`datasets\derived\metrics_*.json`).
Uruchomienie tych samych notebooków w Spark na Fabric daje te same wnioski, ale liczby klastrów
różnią się nieznacznie (inna liczba komponentów grafu): recall kampanii 0,8675, F1 0,9291.
Szczegóły w `DEPLOYMENT_STATUS.md`.

## Co zasymulowano

Integracja z aplikacją Power Apps jest opisana jako ścieżka (Dataverse z Fabric Link lub Synapse Link,
albo Eventstream), a w demo zasymulowana strumieniem z `simulate_realtime.py`. Schemat Dataverse
aplikacji nie był dostępny. Opis w `INTEGRATION_POWERAPPS.md`, luki w `LUKI_I_PYTANIA.md`.

## Fabric App: Pulpit krajowy szkół

Aplikacja jest w katalogu `fabric-app\pulpit-szkol` i wdraża się ją przez `npx rayfin up`. Dziś czyta statyczną migawkę plików z `datasets\`, a nie Lakehouse
ani Eventhouse na żywo. Specyfikacja: `fabric-app\APP_SPEC.md`.

## Struktura

| Ścieżka | Zawartość |
|---|---|
| `DEMO_SCRIPT.md` | scenariusz demo na role, oś czasu, plan B |
| `SETUP_FABRIC.md` | wdrożenie krok po kroku |
| `ARCHITECTURE.md`, `architecture.mmd` | architektura i granica symulacji |
| `DATA_MODEL.md` | wymiary, fakty, model semantyczny |
| `ETHICS_AND_PRIVACY.md` | anonimowość, minimalizacja, nadzór człowieka |
| `INTEGRATION_POWERAPPS.md` | jak podłączyć istniejące demo |
| `LUKI_I_PYTANIA.md` | czego nie wiemy |
| `DEPLOYMENT_STATUS.md` | rzeczywisty stan wdrożenia |
| `generate_datasets.py`, `simulate_realtime.py` | generator danych i symulator strumienia |
| `datasets\` | dane CSV i JSONL, `datasets\derived\` wyniki notebooków |
| `notebooks\` | analityka 01 do 05 |
| `kql\`, `dashboard\`, `activator\` | Eventhouse, Real-Time Dashboard, reguły |
| `semantic-model\`, `report\` | model DAX i raport |
| `ai\DATA_AGENT.md` | specyfikacja Data Agenta |
| `deploy\` | skrypty wdrożeniowe 01 do 16 |

## Szybki start

```powershell
cd ol-szkoly-bezpieczenstwo
pip install -r requirements.txt
python generate_datasets.py
python simulate_realtime.py --dry-run --speed 3600
```

Notebooki lokalne uruchamia się jako zwykłe skrypty Pythona (`python notebooks\01_priority_scoring.py`).
Wdrożenie na Fabric: `SETUP_FABRIC.md` i `deploy\README.md`.

## Data Agent

Agent `agent_zagrozenia_szkolne` odpowiada po polsku na pytania o dane (Lakehouse, Eventhouse, model
semantyczny). Jest w wersji roboczej, publikacja wymaga kliknięcia w portalu. Aplikacja Pulpit krajowy
szkół nie korzysta z agenta ani z Lakehouse, tylko z migawki `datasets\`.

## Licencja

MIT, patrz `LICENSE`.

