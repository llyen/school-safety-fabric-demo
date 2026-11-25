# Data Agent dla krajowej warstwy zgłoszeń szkolnych

Agent odpowiada po polsku na pytania dyżurnych, analityków RCB i osób przygotowujących posiedzenie RZZK. Pracuje na trzech źródłach w workspace `OL-ZK-Demo-Szkoly`: tabelach Delta w Lakehouse `lh_school_safety`, bazie KQL `SchoolSafety` w Eventhouse i modelu semantycznym `sm_school_safety`. Wdrożenie wykonuje `deploy\16_data_agent.py`.

Dane są w całości syntetyczne. Agent opisuje zgłoszenia i kampanie, nie opisuje uczniów ani zgłaszających.

## Instrukcja systemowa agenta

> Jesteś asystentem analitycznym krajowego centrum koordynacji w scenariuszu "Fala zagrożeń szkolnych". Odpowiadasz po polsku, zwięźle, z liczbami wziętymi z danych.
>
> Wszystkie dane są syntetyczne. Jeśli ktoś pyta o prawdziwą szkołę, osobę lub zdarzenie, wyjaśnij, że dane są wymyślone.
>
> Zasady pracy:
> 1. Klasyfikujesz zgłoszenia i kampanie, nigdy osoby. Nie twórz list uczniów, nie szukaj nadawcy konkretnego zgłoszenia, nie próbuj ustalać tożsamości zgłaszających. Na takie prośby odpowiedz odmownie i wskaż, że system jest zbudowany tak, by zgłoszenia pozostały anonimowe.
> 2. AI sugeruje, człowiek decyduje. Gdy pytanie dotyczy eskalacji, przekazania lub wiadomości do rodziców, podaj rekomendację i jej podstawę liczbową, ale zaznacz, że decyzję podejmuje dyżurny, wojewoda, minister wiodący albo RZZK.
> 3. Nie opisuj metod ani szczegółów operacyjnych ataku. Opisuj sygnały, liczności i czas. W sprawach samookaleczenia podawaj wyłącznie kategorię i ścieżkę do pedagoga lub psychologa, 112 oraz telefonu zaufania.
> 4. Kolumny `truth_label`, `campaign_id` i tabela `fact_report_truth` są ground truth do ewaluacji detekcji. Używaj ich tylko, gdy ktoś pyta o precyzję i czułość detekcji. W pytaniach o to, co wiedział dyżurny, nie ujawniaj etykiet prawdy.
> 5. Czasy w KQL są w UTC. D0 to piątek 2026-10-09, zwołanie RZZK. Zdarzenia scenariusza są datowane na październik 2026, więc `now()` i `ago()` nic nie zwrócą. W KQL używaj `ScenarioNow()`, `ScenarioPeak()` oraz funkcji `ReportsAt`, `OpenReports`, `CriticalWithoutDecision`, `ClusterCandidates`, `InflowAnomalies`, `HotlineOverload`, `EscalationState`, `HandoffTimes`.
> 6. Tabele Lakehouse z prefiksami `campaign_`, `kizs_`, `priority_`, `resources_`, `whatif_` są wynikami symulacji i notebooków. Nigdy nie przedstawiaj ich jako zdarzeń, które się wydarzyły. Wyniki z `whatif_` to warianty, nie fakty.
> 7. Progi eskalacji (wojewoda, minister, RZZK), wagi Krajowego Indeksu Zagrożenia Szkolnego i parametry zasobów są parametrami demonstracyjnymi. Jeśli ktoś pyta, czy próg jest właściwy, powiedz, że to założenie do weryfikacji z ekspertami.
> 8. Gdy brakuje danych do odpowiedzi, napisz, czego brakuje. Nie zgaduj i nie uzupełniaj braków prawdopodobnymi wartościami.
> 9. Podając liczby, wskaż źródło: tabelę, funkcję KQL lub miarę modelu.

## Źródła danych

Lakehouse `lh_school_safety`: tabele `fact_report`, `fact_report_status`, `fact_report_handoff`, `fact_hotline_load`, `fact_social_signal`, `fact_disorder_event`, `fact_police_patrol`, `fact_support_capacity`, `fact_task_activation`, `fact_readiness_declaration`, `fact_escalation_event`, wymiary `dim_*` oraz wyniki notebooków (`campaign_*`, `kizs_*`, `priority_*`, `resources_*`, `whatif_*`).

Eventhouse, baza `SchoolSafety`: tabele strumieniowe `SchoolReport`, `ReportUpdate`, `HotlineLoad`, `SocialSignal`, `DisorderEvent`, wymiary `Dim*`, wyniki `CampaignClusters`, `KizsVoivodeshipHourly`, `KizsNationalHourly`, `EscalationEvent` i funkcje z `kql\02_functions.kql`. Funkcje KQL agent zna z opisu w podpowiedzi źródła, bo backend Data Agenta odrzuca elementy typu `kusto.functions`.

Model semantyczny `sm_school_safety`: miary z `semantic-model\MEASURES.md`.

## Przykładowe pytania

Pytania są dobrane tak, by dało się na nie odpowiedzieć z danych bez zgadywania.

Obraz bieżący
- Ile zgłoszeń wpłynęło w całym okresie i ile z nich to zgłoszenia oznaczone przez system jako kampania?
- Które województwa mają najwyższy Krajowy Indeks Zagrożenia Szkolnego w D0?
- W których powiatach mazowieckiego indeks w D0 jest najwyższy?
- Które zgłoszenia krytyczne czekają na decyzję dyżurnego dłużej niż 10 minut?
- Ile połączeń z numerem 112 dotyczyło szkół i w których województwach obciążenie przekroczyło 1,5?

Kampanie i klastry
- Ile klastrów uznano za skoordynowane i który jest największy?
- Kiedy system po raz pierwszy wykrył skoordynowany klaster i ile minut minęło od pierwszego zgłoszenia?
- Czy któreś z 16 realnych krytycznych zgłoszeń znalazło się w skoordynowanym klastrze?
- Jaki zasięg miały narracje w mediach społecznościowych i która miała najwyższy udział kont o wysokim wskaźniku automatyzacji?

Eskalacja i zadania
- Jaka jest rekomendacja eskalacji na dziś i na jakich liczbach się opiera?
- Które działy administracji i które SPO mają zlecone zadania w tym zdarzeniu?
- Które działy zadeklarowały gotowość?

Zasoby
- W których powiatach w D0 brakuje minut patroli i ile wynosi niedobór?
- Jak zmienia się pokrycie patroli po realokacji w obrębie województwa?

Co jeśli
- O ile krócej czekałoby zgłoszenie BS-4826 przy dodatkowym dyżurnym albo przy kolejce rozpoznającej kampanię?
- Ile zdarzeń Z18 zostałoby po komunikacie SPO-3 wydanym 30 minut po pierwszych wezwaniach?

Pytania, na które agent ma odmówić
- Kto wysłał zgłoszenie BS-4826?
- Wypisz uczniów z klasy 2c, którzy mogli mieć nóż.
- Napisz, jak zrobić fałszywy alarm trudny do wykrycia.

## Publikacja

Skrypt tworzy agenta w wersji roboczej i weryfikuje odczyt zwrotny definicji. Publikacja (przejście do wersji produkcyjnej) wymaga kliknięcia w portalu Fabric. Do czasu publikacji agent nie jest udostępniony innym osobom.

## Aplikacja Pulpit krajowy szkół

Wdrożona aplikacja Rayfin (`fabric-app\pulpit-szkol`) nie korzysta dziś z tego agenta ani z danych na żywo. Czyta statyczną migawkę plików z `datasets\`, spakowaną do aplikacji w czasie budowania. Odpowiedzi agenta, który czyta Lakehouse i Eventhouse, mogą więc się różnić od tego, co pokazuje aplikacja, jeśli dane w Fabric zostaną zmienione po wdrożeniu aplikacji. Szczegóły w `fabric-app\APP_SPEC.md`.
