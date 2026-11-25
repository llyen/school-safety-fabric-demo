# Pulpit krajowy szkół (Fabric App, Rayfin)

Krajowa nakładka na demo Power Apps do zgłoszeń szkolnych. Widok dla dyżurnego krajowego, analityka RCB, ministra wiodącego i RZZK: mapa 16 województw, kolejka zgłoszeń, kampanie fałszywych alarmów, eskalacja z zadaniami i zasoby wsparcia. Wszystkie dane są syntetyczne.

Adres aplikacji, identyfikator workspace i elementu Rayfin zależą od własnego wdrożenia (`npx rayfin up status`).

## Ekrany

| Ścieżka | Ekran | Zawartość |
|---|---|---|
| `/` | Obraz krajowy | Kartogram wskaźnika zagrożenia szkolnego (KIZS) dla 16 województw, drill-down do powiatu i szkoły, kafle KPI (otwarte zgłoszenia, krytyczne bez decyzji, odsetek przypisanych do kampanii, obciążenie 112, czas do przekazania), oś czasu D-3 do D+7 |
| `/kolejka` | Kolejka krajowa | Zakładki Otwarte, Krytyczne, Nowe, Zamknięte, filtr województwa, wyszukiwarka (`?q=`, `?id=`), mapa punktów w kolorach priorytetu, szczegół BS-xxxx z sugestią AI i sygnałami, formularz decyzji o priorytecie, statusie i przekazaniu |
| `/kampanie` | Kampanie | Klastry K1, K2, K3: liczba zgłoszeń, województwa, wzorzec czasu, wspólny motyw tekstu, zasięg social, oznaczenie „prawdopodobnie fałszywy alarm” albo „wymaga reakcji”, lista realnych zgłoszeń ukrytych w fali |
| `/eskalacja` | Eskalacja i zadania | Rekomendacja poziomu z progami i bieżącymi wartościami, formularz uruchomienia, checklista zadań działów XV, XIX, X, XIII oraz SPO-1, SPO-3, SPO-12, SPO-16, szkic komunikatu SPO-3 do zatwierdzenia przez człowieka, deklaracje gotowości |
| `/zasoby` | Zasoby wsparcia | Pokrycie pedagogami i psychologami na 10 tys. uczniów, obciążenie patroli, rekomendacja rozstawienia z analizy D0, podsumowanie dnia |

Pasek czasu (suwak, odtwarzanie, wybór dnia) działa na wszystkich ekranach. Przykład z demo Power Apps, BS-4826 (Zespół Szkół nr 3 w Mieście M-1402), jest w danych i wyszukiwalny po numerze oraz po kodzie „M-1402”.

Akcentem jest ciemny morski `#0F6B5C` na jasnym, szarozielonym tle. W nagłówku jest tarcza, nagłówki sekcji są pisane kapitalikami, a priorytet pokazują plakietki w kolorach czerwonym, pomarańczowym, niebieskim i szarym. Sugestia AI i decyzja dyżurnego mają osobne oznaczenia („AI: KRYTYCZNY”, „DECYZJA: KRYTYCZNY”). Kontrast akcentu na białym tle wynosi około 6,4:1.

## Architektura danych

```
datasets\ + derived\  ──►  tools\build_scene.py  ──►  public\data\{scene,reports,schools}.json
                                                              │ fetch
                                                              ▼
                                              React + Vite (src\)  ──►  zapisy do bazy Rayfin
```

- **Odczyt:** statyczny snapshot JSON zbudowany z plików repozytorium (`datasets\`, `derived\`). Aplikacja Rayfin nie czyta na żywo ani z Lakehouse, ani z Eventhouse, ani z SQL endpointu. Nie sprawdzano, czy tabele w Lakehouse mają te same wartości co pliki. Odświeżenie danych: `$env:PYTHONUTF8=1; python tools\build_scene.py`, potem `npm run build` i `npx rayfin up -y --workspace-id <id>`.
- **Zapis:** cztery encje append-only w bazie Rayfin: `ReportDecision`, `EscalationDecision`, `TaskStatus`, `CommsDraft`. Każdy zapis ma autora, rolę, czas, uzasadnienie i skrót kontrolny (`auditHash`, 64 znaki hex). Wersja z nowszym `version` zastępuje starszą w widoku, historia zostaje. Na `localhost` zapisy trafiają do pamięci przeglądarki.
- **AI tylko sugeruje:** sugestia AI (`ai.pri`, sygnały, rekomendacja) jest oddzielona od decyzji dyżurnego (`dec`). Priorytet „DECYZJA” pojawia się dopiero po decyzji sceny albo po zapisie użytkownika. Rekomendacja eskalacji i szkic komunikatu SPO-3 wymagają potwierdzenia przez człowieka.
- **Progi eskalacji** pochodzą z `notebooks\03_kizs_escalation.py` repozytorium i są zakodowane w `THRESHOLDS` (`src\data\model.ts`). Test porównuje wynik aplikacji z kolumnami `rec_minister` i `rec_rzzk` z danych dla każdej z 264 godzin.

## Uwagi o danych

- Współrzędne szkół w danych źródłowych mają szum. Skrypt przypisuje punkt do własnego województwa (przesunięcie do najbliższego punktu obrysu), co dotknęło 1183 z 4215 szkół. Bez tego punkty lądowałyby poza właściwym województwem na kartogramie.
- Nazwy kampanii K1, K2, K3 pochodzą z katalogu scenariusza (`dim_campaign`). Etykiety prawdy ze scenariusza (`fact_report_truth.csv`) służą wyłącznie do przypisania nazwy klastrowi i nie trafiają do wyników. W praktyce nazwę nadałby analityk.
- Ocena „prawdopodobnie fałszywy alarm” to prosta reguła: klaster skoordynowany, w którym co najmniej połowa zgłoszeń pochodzi z klientów automatycznych albo z powtórzonego linku. To sugestia, nie werdykt.
- Dane nie zawierają treści szkicu komunikatu SPO-3. Szkic jest generowany w aplikacji z bieżących wskaźników i oznaczony jako szkic do zatwierdzenia.

## Etyka

Brak danych osobowych, zgłaszający pozostaje anonimowy, nie ma profilowania uczniów (tylko zgłoszenia i szkoły), na każdym ekranie widoczny baner „dane syntetyczne”, treści zgłoszeń bez instrukcji operacyjnych. Test sprawdza, że rekordy zgłoszeń nie mają pól z danymi osobowymi.

## Uruchomienie lokalne

```powershell
npm install
npm run dev        # rayfin up bez hostingu i vite, http://localhost:5173
npm test           # vitest, 30 testów
npm run lint
npm run build
$env:PYTHONUTF8=1; python tools\audit_local.py   # audyt kontrastu WCAG 4,5:1, wymaga AUDIT_CONTRAST_DIR
```

Pakiety instalują się z publicznego rejestru npm.

## Wdrożenie

```powershell
npx rayfin login -t <TENANT_ID>
npx rayfin up -y --workspace-id <WORKSPACE_ID>
npx rayfin up status
```

Pułapki napotkane przy wdrożeniu:

1. `rayfin up switch --workspace-id` zwraca „No deployment found”, gdy w workspace nie ma jeszcze wdrożenia. Pierwsze `rayfin up -y` bez `--workspace-id` utworzyło wtedy osobny, tymczasowy workspace. Został usunięty przez API Fabric, a wdrożenie powtórzono z `--workspace-id`. Zawsze podawaj `--workspace-id` przy pierwszym wdrożeniu.
2. Nowa wersja CLI ustawia `assetAccess: protected`, co daje HTTP 401 dla anonimowego żądania. Ponieważ dane są syntetyczne, a aplikacja ma własną bramkę logowania, ustawiono `assetAccess: public`. Backend i dane nie są dzięki temu anonimowe.
3. Adres hostingu jest znany dopiero po pierwszym wdrożeniu i trafia do `allowedRedirectUris` (robi to CLI).
4. Pojemność Fabric bywa w stanie Paused, co objawia się błędem 404 „workspace not found”. Przed wdrożeniem była aktywna.

## Co sprawdzono automatycznie

- `tsc -b` i `vite build`: bez błędów. `eslint`: 0 błędów, 4 ostrzeżenia react-refresh.
- `vitest`: 30 testów (priorytet AI a decyzja, status w czasie, nakładka decyzji użytkownika, KPI, progi eskalacji wraz z regresją względem danych dla 264 godzin, klasyfikacja kampanii, `topTerms`, skrót audytu, walidacje formularzy, BS-4826, brak pól z danymi osobowymi).
- `tools\audit_local.py`: 15 plików `.tsx`, 0 par poniżej 4,5:1 (używa zewnętrznego skanera `audit_contrast.py`, którego nie ma w tym repozytorium; katalog ze skanerem wskazuje zmienna `AUDIT_CONTRAST_DIR`).
- Wdrożenie: `rayfin up` zakończony sukcesem, baza SQL utworzona, `GET /` zwraca 200 i dokument z tytułem aplikacji, `GET /data/scene.json` 200 (438 KB), `GET /data/reports.json` 200 (3,4 MB).

## Czego nie sprawdzono

- **Logowanie brokerem Fabric** działa tylko z poziomu portalu Fabric (SSO) i nie dało się go przejść automatycznie.
- **Zapis od końca do końca** (formularz, baza Rayfin, odczyt po odświeżeniu) nie został wykonany na wdrożonej aplikacji, bo wymaga zalogowanej sesji. Zapisy przetestowano tylko na poziomie walidacji i pamięci w testach jednostkowych. Wywołania `client.data.<Entity>.create/select` powielają wzorzec z wcześniejszych aplikacji Rayfin.
- **Wygląd w przeglądarce** (układ, mapa, responsywność) nie był oceniany wizualnie. Kontrast sprawdza skaner klas Tailwind, który nie widzi tła odziedziczonego z elementu nadrzędnego.
- **Role** (dyżurny krajowy, analityk RCB, minister wiodący, RZZK) są egzekwowane w interfejsie, nie w bazie. Każdy zalogowany użytkownik może zapisać rekord przez API. Do produkcji potrzebne byłyby role po stronie serwera.
- **Odczyt na żywo** z Lakehouse i Eventhouse nie jest zaimplementowany (patrz Architektura danych).
- `npm audit` zgłasza 6 podatności w zależnościach (4 umiarkowane, 2 krytyczne), nie analizowano ich.
