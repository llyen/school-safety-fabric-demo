# Architektura

Diagram w pliku `architecture.mmd` (Mermaid). Linie przerywane oznaczają ścieżki opisane, ale
niezbudowane lub niewykonane w demo.

## Warstwy

Aplikacja Power Apps do zgłoszeń szkolnych jest źródłem zgłoszeń i miejscem decyzji dyżurnego.
Fabric dokłada widok krajowy. Zgłoszenia trafiają do Eventhouse strumieniem i do Lakehouse wsadowo.
Notebooki liczą priorytet, klastry kampanii, KIZS, rozstawienie zasobów i warianty what-if,
a wyniki wracają do tabel Delta. Model semantyczny (DirectLake) i raport pokazują to analitykowi,
Real-Time Dashboard dyżurnemu, Activator uruchamia powiadomienia, a Data Agent odpowiada na pytania po polsku.

| Funkcja Fabric | Rola |
|---|---|
| Lakehouse (Delta) | wymiary, fakty i wyniki notebooków |
| Notebooki (PySpark, Python) | scoring, klastry, KIZS, zasoby, what-if |
| Eventstream | wejście strumienia, pięć filtrów, pięć tabel KQL |
| Eventhouse i KQL | tabele, funkcje, anomalie napływu, kolejka, klastry |
| Real-Time Dashboard | 14 kafli na 2 stronach |
| Model semantyczny i raport | 33 miary DAX, 4 strony, 45 wizualizacji |
| Activator | 5 reguł (R1 do R5) |
| Data Agent | pytania po polsku do trzech źródeł |
| Fabric App | Pulpit krajowy szkół, dziś na migawce plików |

## Co jest zasymulowane

Zasymulowane jest wszystko, co dotyczy wejścia z aplikacji. Nie mamy połączenia z Dataverse
aplikacji ani jej schematu, więc zgłoszenia generuje `generate_datasets.py`, a strumień na żywo
odtwarza `simulate_realtime.py` (z opcją `--dry-run`, która działa offline). Zasymulowane są także:

- piętnaście centrów dyżurnych poza mazowieckim (w aplikacji dyżurny działa dziś tylko dla mazowieckiego),
- liczba dyżurnych i czasy obsługi zgłoszenia (założenia kolejki),
- sugestie AI (reguły i sygnały w notebooku 01, a nie model z aplikacji),
- pola techniczne `client_class`, `submit_latency_s`, `sender_token_day`, które aplikacja musiałaby rejestrować,
- obciążenie 112, zasięg w mediach społecznościowych, patrole, pedagodzy i psycholodzy,
- czasy eskalacji RZZK i progi KIZS (parametry demonstracyjne),
- opóźnienie w kolejce mazowieckiego w D0, które jest wynikiem symulacji, a nie pomiarem.

Nie zbudowano zapisu zwrotnego decyzji z Fabric do Dataverse. Aplikacja Fabric (Pulpit krajowy szkół)
czyta statyczną migawkę `datasets\`, nie Lakehouse ani Eventhouse na żywo.

## Detekcja kampanii

Notebook 02 buduje wektory TF-IDF (unigramy i bigramy) i łączy zgłoszenia, których podobieństwo cosinusowe wynosi co najmniej 0,50 w oknie 36 godzin. Komponenty połączone grafu stają się klastrami, a skoordynowany klaster wyznacza dodatkowo kryterium w kodzie notebooka. Zgłoszenie z klastra wraca jednak do człowieka, gdy ma cechy konkretnego zagrożenia (`guard_text`) albo jest mało podobne do centroidu klastra (poniżej 0,30). Ground truth w tabeli `fact_report_truth` (kampania, nadawca bot, realne krytyczne) służy wyłącznie do ewaluacji precision i recall i nie jest cechą detekcji.

Spark i scikit-learn dały różną liczbę komponentów (70 w Spark, 115 lokalnie), co przekłada się na
drobne różnice metryk. Wnioski są takie same, patrz `DEPLOYMENT_STATUS.md`.

## Eskalacja

Powiat, wojewoda lub kurator, minister wiodący (MEN lub MSWiA), RZZK. Rekomendacja wynika z progów KIZS i wolumenu kampanii
(`notebooks\03_kizs_escalation.py`, miara DAX "Rekomendacja eskalacji", funkcja KQL `EscalationState`).
Decyzję podejmuje człowiek, a system zapisuje podstawy rekomendacji.

## Rozróżnienie ZK i OL

Zarządzanie kryzysowe (ZK) to administracja: eskalacja, przypisanie zadań działom (XV Oświata i
wychowanie, XIX Sprawy wewnętrzne, X Informatyzacja, XIII Łączność), komunikacja z ludnością (SPO-3),
obieg informacji (SPO-12), Zespół ds. Incydentów Krytycznych (SPO-16). Ochrona ludności (OL) to człowiek:
uczeń, rodzic, pedagog, ewakuacja, wsparcie psychologiczne. Model danych przechowuje oba wymiary osobno.

