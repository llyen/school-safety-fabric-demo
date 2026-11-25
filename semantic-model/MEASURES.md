# Miary DAX

Nazwy miar nie zawierają polskich znaków, żeby były bezpieczne w narzędziach. Definicje generuje
`deploy\06_semantic_model.py`.

| Miara | Definicja (skrót) |
|---|---|
| Zgloszenia | liczba wierszy FactReport |
| Szkoly ze zgloszeniem | liczba różnych `school_id` w FactReport |
| Zgloszenia AI krytyczne | zgłoszenia z sugestią AI KRYTYCZNY |
| Zgloszenia decyzja krytyczna | zgłoszenia z decyzją dyżurnego KRYTYCZNY |
| Zgloszenia otwarte | status różny od ZAMKNIETE |
| Mediana czasu do decyzji (min) | mediana `decision_delay_min` |
| Decyzje po 10 min % | udział decyzji z opóźnieniem powyżej 10 min |
| Przekazania, Przekazania do Policji | liczba przekazań, w tym do POL |
| Polaczenia 112 szkolne | suma połączeń 112 związanych ze szkołami |
| Obciazenie 112 maks. | maksimum `load_ratio` |
| Godziny przeciazenia 112 | liczba wierszy z `load_ratio` powyżej 1,5 |
| Zasieg tresci | suma szacowanego zasięgu w mediach społecznościowych |
| Zdarzenia Z18, Uczestnicy zdarzen Z18 | liczba zdarzeń i suma szacowanych uczestników |
| Zgloszenia w kampanii | zgłoszenia z flagą kampanii |
| Zgloszenia dla czlowieka, Udzial zgloszen dla czlowieka % | zgłoszenia z `keep_for_human` i ich udział |
| Klastry skoordynowane, Najwiekszy klaster | liczba klastrów skoordynowanych i maksymalny rozmiar |
| KIZS wojewodztwa, KIZS powiatu | maksimum wskaźnika KIZS w kontekście filtra |
| KIZS krajowy - szczyt | maksimum średniej krajowej KIZS |
| Wojewodztwa powyzej progu | liczba województw powyżej progu KIZS |
| Zgloszenia kampanii 24h | zgłoszenia kampanii w oknie 24 h |
| Rekomendacja eskalacji | tekst: RZZK, Minister wiodacy, Wojewoda i kurator albo Brak eskalacji, wg flag w FactKizsNational |
| Opoznienie realnych krytycznych maks. (min) | maksymalne opóźnienie realnych krytycznych w wariancie what-if |
| Opoznienie BS-4826 (min) | opóźnienie BS-4826 w wariancie what-if |
| Zdarzenia Z18 po komunikacie | zdarzenia Z18 po komunikacie SPO-3 w wybranym czasie |
| Pokrycie patroli status quo - najgorszy dzien | minimum dziennego pokrycia w stanie obecnym |
| Pokrycie patroli po realokacji - najgorszy dzien | minimum dziennego pokrycia po realokacji |
| Powiaty w deficycie | liczba powiatów z niedoborem patroli |
| Naglowek sytuacji | tekst z liczbą zgłoszeń i oznaczonych jako kampania |

Zmienne w miarze "Rekomendacja eskalacji" nazywają się `vRzzk`, `vMin` i `vWoj`. Wcześniejsza nazwa
`Min` kolidowała z funkcją DAX i miara zwracała pusty wynik.

Wartości zweryfikowane na modelu (12 miar zgodnych z liczeniem lokalnym): zgłoszeń 4560, szkół ze zgłoszeniem
2317, AI krytyczne 958, decyzja krytyczna 876, klastry skoordynowane 7, największy klaster 1263, połączenia 112
szkolne 18397, zdarzenia Z18 263, przekazania 5386 (do Policji 1700), mediana do decyzji 3,4 min, KIZS szczyt
42,0, rekomendacja RZZK.

