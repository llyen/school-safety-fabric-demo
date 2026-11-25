# Scenariusz demo: Fala zagrożeń szkolnych

Czas demo około 20 minut. Wszystkie liczby pochodzą z uruchomień na danych syntetycznych (seed=42).
Wersja z Fabric ma w klastrach drobne różnice, opisane na końcu.

## Oś czasu scenariusza

D0 to piątek 2026-10-09, dzień zwołania RZZK. Scenariusz obejmuje D-3 do D+7.

| Moment | Co się dzieje |
|---|---|
| D-3 (2026-10-06) | pierwsze fałszywe alarmy bombowe, kampania K1 zaczyna się wcześniej, 2026-10-05 22:25 UTC |
| 2026-10-07 14:43 | system wykrywa pierwszy klaster K1 (219 min od pierwszego zgłoszenia) |
| 2026-10-08 | fałszywe nagrania "zapowiedzi ataku" (K2), 61 min do wykrycia, rośnie rekomendacja dla ministra |
| D0 08:00 | pierwsza rekomendacja wojewódzka (mazowieckie, śląskie) |
| D0 08:41 | BS-4826 w Mieście M-1402, nóż motylkowy, realne zgłoszenie |
| D0 | szczyt: tłumne odbieranie dzieci (Z18), przeciążenie 112 |
| D+1 do D+7 | efekt naśladowczy K3 (320 zgłoszeń), wygaszanie |

## Role

Dyżurny powiatowy i wojewódzki widzi kolejkę, mapę i sugestię AI. Analityk RCB widzi klastry i KIZS.
Minister wiodący i RZZK dostają rekomendację eskalacji.

## Przebieg

### 1. Dyżurny powiatowy (Power Apps, 4 min)

Zaczynamy w aplikacji zgłoszeń szkolnych: kolejka mazowieckiego, kolory priorytetu, numer BS-4826,
Zespół Szkół nr 3 w Mieście M-1402, 9 paź 08:41. Sugestia AI to KRYTYCZNY, decyzja dyżurnego jest
osobna. W zbiorze zgodność AI z decyzją dyżurnego wynosi 0,8737 (dyżurny podniósł 246 priorytetów,
obniżył 330). To pokazuje wzorzec "AI sugeruje, człowiek decyduje".

W tej symulacji BS-4826 doczekał się decyzji po 144,7 min, a w D0 w mazowieckim mediana opóźnienia to
271,8 min. Zgłoszeń o decyzji krytycznej w D0 jest 493, z nich 69,4 proc. czekało ponad 10 minut.

### 2. Analityk RCB: kampania czy realne zagrożenie (6 min)

Raport `rpt_zagrozenia_szkolne` i Real-Time Dashboard. Mapa krajowa, strona klastrów.

Pokazujemy, że z 4560 zgłoszeń system oznacza 2216 jako należące do kampanii skoordynowanej,
a do człowieka kieruje 2344. W kampanii nie ma ani jednego z 16 realnych zgłoszeń krytycznych.

Wow moment pierwszy: rozpoznanie 16 realnych zagrożeń wśród 2453 zgłoszeń związanych z kampanią.
Filtr po skoku wolumenu ukryłby 8 z 16, system nie ukrywa żadnego. Precyzja wykrywania kampanii 1,0,
recall 0,9034, tło i efekt naśladowczy bez fałszywych flag (0 z 1771 i 0 z 320).

### 3. Wskazanie, gdzie być pierwszym (4 min)

KIZS krajowy ma szczyt 42,0, w mazowieckim 77,4. Na poziomie powiatów w D0 najwyższe wartości mają
Miasto M-1405 (80,9), Miasto M-1406 (74,6) i Miasto M-1402 (64,8). Rozstawienie zasobów: pokrycie patroli w
najgorszym dniu 0,949 w stanie obecnym, 13 powiatów w deficycie (niedobór 1237 min), po realokacji 1,0.
Pedagodzy i psycholodzy w danych nie są wąskim gardłem (pokrycie 1,0), co jest wynikiem założeń
popytu, a nie wnioskiem operacyjnym.

### 4. Minister i RZZK (3 min)

Miara "Rekomendacja eskalacji" pokazuje RZZK. Progi: wojewoda KIZS co najmniej 45 przez 2 h, minister
kampania co najmniej 150 zgłoszeń w 24 h w co najmniej 8 województwach, RZZK 400 w 24 h w co
najmniej 12 województwach. W symulacji rekomendacja dla ministra pojawia się 2026-10-08 o 09:00,
dla RZZK o 20:00, a detekcja wyprzedza zwołanie RZZK o 2836 min. Wrażliwość: próg kampanii 200,
300, 400, 600, 800 daje wyprzedzenie 1680, 1200, 1080, 540, 420 min.

Wow moment drugi: czas od zgłoszenia ucznia do decyzji krajowej. W zasymulowanym zbiorze mediana do
decyzji dyżurnego wynosi 3,4 min (p90 181 min), a pierwsza rekomendacja wojewódzka pojawia się w D0
o 08:00. Wartość "od zgłoszenia do RZZK" zależy od progów i jest parametrem, nie pomiarem.

### 5. What-if (3 min)

| Wariant | Realne krytyczne powyżej 10 min | Maks. opóźnienie realnego (min) | BS-4826 (min) |
|---|---|---|---|
| A0 stan obecny | 7 | 607,5 | 152,6 |
| A1 jeden dyżurny więcej w dzień | 7 | 442 | 93,0 |
| A2 dwóch dyżurnych więcej | 7 | 344 | 58,4 |
| A3 kwalifikacja o 30 proc. szybsza | 6 | 406 | 83,4 |
| A4 kolejka świadoma kampanii | 0 | 7,3 | 3,7 |
| A5 jak A4 plus jeden dyżurny | 0 | 7,3 | 3,7 |

Komunikat SPO-3 w T+30 min, 2 h, 4 h i 8 h: zdarzeń Z18 jest 263, 220, 126, 18, a połączeń 112
szkolnych 14669, 12111, 7288, 3426. Wpływ komunikatu to założenie elastyczności 10, 20 i 30 proc.,
nie zmierzona skuteczność.

W wariancie A4 zgłoszenia z klastrów kampanii są zwijane do jednej pozycji zbiorczej na klaster i okno, a zgłoszenia z cechami konkretnego zagrożenia mają pierwszeństwo. Mediana opóźnienia wszystkich zgłoszeń rośnie wtedy z 3,4 do 6,6 min, bo koszt płacą zgłoszenia kampanii, natomiast mediana dla zgłoszeń kierowanych do człowieka to 2,2 min. Definicje wariantów: `notebooks\05_whatif.py`.

## Plan B

Jeśli Fabric nie odpowiada, uruchom lokalnie `python simulate_realtime.py --dry-run` i notebooki
w wersji lokalnej, a liczby pokaż z `datasets\derived\metrics_*.json`. Pulpit krajowy szkół działa
niezależnie od Lakehouse, bo czyta migawkę `datasets\`. Raport można pokazać ze zrzutów, a aplikację
Power Apps z jej własnych danych.

## Różnice Fabric i lokalnie

Spark policzył 70 komponentów klastrów zamiast 115. Przy tych samych wnioskach (16 z 16 realnych
zachowanych, 0 w klastrach, ta sama pierwsza detekcja) w modelu Fabric kampania obejmuje 2128 zgłoszeń,
do człowieka 2432, recall 0,8675, F1 0,9291. BS-4826 w wariancie A4 ma 4,5 min zamiast 3,7.
W trakcie prezentacji na Fabric korzystaj z liczb modelu, a w materiałach pisanych z lokalnych.


