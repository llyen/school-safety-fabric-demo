# Etyka i prywatność

System pokazuje zgłoszenia, nie osoby. Sugestie AI klasyfikują zgłoszenie (kategoria, sygnały
w treści, priorytet), a nie ucznia, rodzica ani nauczyciela. Dane w repozytorium są syntetyczne, ale
zasady poniżej obowiązują w każdym rzeczywistym wdrożeniu.

## Anonimowość zgłaszającego

Aplikacja przyjmuje zgłoszenia anonimowo. Model danych nie ma pól na imię, nazwisko, numer telefonu,
adres e-mail ani identyfikator ucznia. Pola techniczne w danych demonstracyjnych (`client_class`,
`submit_latency_s`, `sender_token_day`) służą wyłącznie do odróżnienia kampanii od pojedynczych zgłoszeń.
Token nadawcy w danych demonstracyjnych jest dzienny i nie zawiera danych osobowych. Czy aplikacja je dziś rejestruje, jest otwartym pytaniem
(`LUKI_I_PYTANIA.md`), a każde takie pole wymaga oceny skutków dla ochrony danych.

## Minimalizacja i agregacja

Na poziomie krajowym publikuje się wartości zagregowane do powiatu. Szkoła pojawia się w widoku
dyżurnego i analityka tylko z uprawnieniem. Drill-down do szkoły nie pokazuje treści zgłoszeń
osobom bez roli dyżurnego. Małe liczby (kilka zgłoszeń w małym powiecie) w publikacjach zbiorczych
należy łączyć lub zasłaniać, żeby nie dało się wskazać źródła.

## Dostęp i RLS

Dyżurny powiatowy i wojewódzki widzą swój zakres (RLS na województwo lub powiat). Analityk RCB i
minister widzą dane krajowe w agregacji. Model semantyczny w demo nie ma wdrożonego RLS. To
ustalenie do realizacji przed pracą na danych rzeczywistych.

## Etykiety wrażliwości

Opis docelowy (bez konfiguracji w demo): zgłoszenia i treści jako "Poufne", agregaty krajowe jako
"Wewnętrzne", dane publikowane jako "Publiczne" po agregacji. Etykiety Purview w demo nie zostały
nałożone.

## Retencja

Treści zgłoszeń przechowuje się tak krótko, jak pozwala cel (obsługa zdarzenia, ocena po
zdarzeniu). Po okresie retencji zostają agregaty bez treści. Okres ustala administrator danych,
w demo nie jest zdefiniowany.

## Ryzyko stygmatyzacji i fałszywych oskarżeń

Fałszywy alarm bombowy i fałszywe nagranie "zapowiedzi ataku" mogą wskazać niewinną osobę lub
szkołę. Dlatego wynik detekcji kampanii nie ma wskazywać sprawców, tylko odróżniać wzorzec
kampanii od zgłoszeń pojedynczych. Zgłoszenie z cechami konkretnego zagrożenia wraca do człowieka
nawet wtedy, gdy wygląda na część fali. System nie buduje profili uczniów, tylko zgłoszeń.

## Nadzór człowieka i audyt

AI sugeruje, człowiek decyduje. W kolejce widać osobno sugestię AI i decyzję dyżurnego. Rekomendacja
eskalacji i szkic komunikatu SPO-3 dla rodziców i mediów są propozycjami do zatwierdzenia przez
człowieka. Każdą decyzję zapisuje się z rolą, czasem i podstawą. Zgodność AI z decyzją dyżurnego
(w zbiorze demo 0,8737) jest miarą do monitorowania, a nie celem do maksymalizacji.

## Treść zgłoszeń

Syntetyczne zgłoszenia są krótkie, opisują sygnały (wzmianka o broni, konkretny czas), nie opisują
metod ani instrukcji. Zgłoszenia dotyczące samookaleczenia mają tylko kategorię i ścieżkę do
pedagoga lub psychologa, numeru 112 i telefonu zaufania, bez szczegółów.

## Pytania otwarte

Podstawa prawna przetwarzania, rola administratora, zgodność z ustawą o ochronie danych osobowych
małoletnich, ocena skutków (DPIA) oraz zgoda na przekazywanie danych między ministerstwami nie zostały
ocenione w demo i wymagają decyzji prawnej.

