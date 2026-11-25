# Luki i pytania

Lista tego, czego nie wiemy o aplikacji i danych. Nie uzupełniamy tych braków przypuszczeniami.

## Aplikacja zgłoszeń szkolnych

1. Jaki jest schemat Dataverse (tabele, kolumny, wartości statusów i priorytetów)? Dane demo odwzorowują
   tylko to, co widać na ekranach opisanych w zadaniu.
2. Czy aplikacja zapisuje sugestię AI i sygnały (broń, konkretny czas) i według jakiej logiki je liczy?
   Notebook 01 to nasza reguła, a nie ta z aplikacji.
3. Czy aplikacja rejestruje cechy techniczne nadawcy (klasa klienta, opóźnienie wysłania, token dzienny)?
   Bez nich detekcja kampanii opiera się wyłącznie na treści, czasie i geografii.
4. Kto jest dyżurnym poza mazowieckim i ilu dyżurnych jest na zmianie? Liczba dyżurnych i czasy obsługi
   w kolejce to założenia, więc opóźnienia (np. BS-4826 152,6 min) są wynikiem symulacji, nie pomiarem.
5. Skąd lista szkół w polu "szkoła" i czy zawiera identyfikatory, które można powiązać z TERYT?
6. Czy decyzja dyżurnego może zostać zapisana zwrotnie z poziomu krajowego?

## Dane

7. Wszystkie liczby (zgłoszenia, połączenia 112, patrole, pedagodzy, psycholodzy) są syntetyczne. Nie znamy
   rzeczywistych wolumenów zgłoszeń, obciążenia 112 ani zasobów wsparcia w powiatach.
8. Nazwy powiatów i gmin oraz kody TERYT są syntetyczne według konwencji przyjętej w demo.
9. Rozstawienie zasobów: model popytu na patrole i wsparcie jest założeniem. Pedagodzy i psycholodzy mają
   pokrycie 1,0, ale brak źródła popytu nie pozwala uznać tego za wniosek.
10. Wpływ komunikatu SPO-3 na liczbę zdarzeń Z18 i połączeń zakłada elastyczność 10, 20 i 30 proc. Nie
    mamy pomiaru skuteczności komunikatów.

## Parametry decyzyjne

11. Progi KIZS i eskalacji (wojewoda 45 przez 2 h, minister 150 w 24 h i 8 województw, RZZK 400 w 24 h i
    12 województw) są parametrami demonstracyjnymi. Kto i na jakiej podstawie ustala progi w praktyce?
12. Czasy eskalacji w scenariuszu (wojewoda 03:50, minister 09:10, RZZK 14:00) są parametrami scenariusza.

## Fabric i wdrożenie

13. Aplikacja Pulpit krajowy szkół czyta migawkę plików `datasets\`, a nie Lakehouse na żywo. Logowanie
    brokerem Fabric i zapis od końca do końca nie zostały sprawdzone.
14. Data Agent jest zapisany w wersji roboczej. Publikacja wymaga kliknięcia w portalu.
15. RLS i etykiety Purview nie są skonfigurowane w demo.
16. Uruchomienie notebooków w Spark daje inną liczbę komponentów klastrów niż lokalnie. Która wersja ma być
    wersją referencyjną dla rzeczywistych danych?
17. Nie oceniono wizualnie raportu i Real-Time Dashboard w przeglądarce. Sprawdzono odwołania do danych i
    wykonalność zapytań.

## Prawo

18. Podstawa prawna przetwarzania zgłoszeń małoletnich, rola administratora, DPIA i zasady udostępniania
    danych między MEN, MSWiA i RCB wymagają decyzji prawnej, której demo nie zastępuje.
