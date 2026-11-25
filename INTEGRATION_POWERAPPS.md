# Integracja z aplikacją Power Apps do zgłoszeń szkolnych

Ten dokument opisuje, jak podłączyć istniejące demo do warstwy krajowej. W repozytorium nic z tego
nie jest podłączone do prawdziwej aplikacji. Schemat Dataverse aplikacji nie był dostępny, więc poniższe
ścieżki są projektem, a nie opisem wykonanego wdrożenia.

## Co zasymulowano

Zgłoszenia, decyzje dyżurnego i przekazania pochodzą z `generate_datasets.py`. Strumień na żywo
odtwarza `simulate_realtime.py` (`--speed`, `--from`, `--to`, `--dry-run`) do Eventstream (custom endpoint).
Eventstream przyjmuje pięć strumieni (zgłoszenie, aktualizacja, obciążenie 112, sygnał social, zdarzenie Z18),
każdy z polem `stream`, po którym filtry kierują ruch do tabel KQL. Test tego przepływu
(`deploy\13_verify_eventstream.py`) przeszedł po ponownym wdrożeniu Eventstream: po 5 zdarzeń na strumień
dotarło do właściwych tabel i zostało usunięte.

## Ścieżka A: Dataverse i Fabric Link lub Synapse Link

Tabele zgłoszeń aplikacji w Dataverse są udostępniane do Fabric (Link to Microsoft Fabric) jako skróty w
Lakehouse. Daje to pełną historię, dobrą do notebooków i modelu DirectLake, ale z opóźnieniem właściwym dla tej
usługi, więc nie nadaje się samodzielnie do alertów w minutach.

## Ścieżka B: Eventstream

Przepływ w Power Automate lub wtyczka w Dataverse wysyła nowe i zmienione zgłoszenia do custom endpoint
Eventstream. Dane trafiają do Eventhouse i uruchamiają Activator. To ścieżka dla widoku dyżurnego krajowego.
W praktyce zwykle łączy się obie: B dla czasu rzeczywistego, A dla historii.

## Mapowanie pól

| Pole w danych demo | Znaczenie | Co trzeba potwierdzić w aplikacji |
|---|---|---|
| report_id | numer BS-nnnn | czy format i unikalność odpowiadają aplikacji |
| category_code | jeden z sześciu kafli | nazwy i kody wartości |
| school_id | szkoła z listy | źródło listy, powiązanie z kodem TERYT |
| ts | czas zgłoszenia | strefa czasowa |
| ai_priority, ai_signals | sugestia AI | czy aplikacja zapisuje sugestię i sygnały |
| duty_priority, status_code | decyzja i status | wartości statusów (Nowe, Przekazane, W analizie, Zamknięte) |
| recipient_code | adresat przekazania | lista adresatów |
| client_class, submit_latency_s, sender_token_day | cechy techniczne nadawcy | czy aplikacja je rejestruje, to założenie demo |

## Zapis zwrotny decyzji

Decyzja o eskalacji (powiat, wojewoda lub kurator, minister, RZZK) i status "przekazane do poziomu krajowego"
powinny wracać do aplikacji, żeby dyżurny widział kontekst krajowy. Jeden z wariantów: Activator wywołuje przepływ
Power Automate, który aktualizuje rekord w Dataverse. Zapis zwrotny nie został zbudowany. Aplikacja Fabric
`pulpit-szkol` ma w kodzie zapis do własnej bazy, ale logowanie brokerem i zapis od końca do końca nie
zostały sprawdzone (wymagają sesji w portalu).

## Zakres dyżurnego

Aplikacja ogranicza dziś dyżurnego do mazowieckiego. W danych demo pozostałe piętnaście województw ma
centra dyżurne jako ekstrapolację. Rozszerzenie wymaga ustalenia, kto obsługuje zgłoszenia poza mazowieckim.

## Uprawnienia i prywatność

Połączenie musi zachować anonimowość zgłaszającego (patrz `ETHICS_AND_PRIVACY.md`): do Fabric nie
przekazuje się danych identyfikujących ucznia, a RLS na województwo i powiat odtwarza zakres dyżurnych.
