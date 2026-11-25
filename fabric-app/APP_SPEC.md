# Pulpit krajowy szkół: specyfikacja

Kod i opis aplikacji są w `fabric-app\pulpit-szkol\` (szczegóły w jej `README.md`). Identyfikatory poniżej
zastąpiono placeholderami.

| Element | Wartość |
|---|---|
| Adres | `<APP_URL>` |
| Workspace | `OL-ZK-Demo-Szkoly` (`<WORKSPACE_ID>`) |
| Element Rayfin | `pulpit-szkol` (`<APP_BACKEND_ID>`) |

## Odbiorcy i ekrany

Dyżurny krajowy, analityk RCB, minister wiodący i RZZK. Ekrany: obraz krajowy z kartogramem KIZS i
drill-downem do powiatu i szkoły, kolejka krajowa (zakładki Otwarte, Krytyczne, Nowe, Zamknięte, szczegół
BS-xxxx z sugestią AI i decyzją), kampanie (klastry K1, K2, K3 i lista realnych zgłoszeń ukrytych w fali),
eskalacja z zadaniami działów i szkicem komunikatu SPO-3 do zatwierdzenia, zasoby wsparcia.

## Skąd aplikacja bierze dane

Dziś czyta statyczną migawkę plików z `datasets\` i `datasets\derived\` (budowaną przez
`tools\build_scene.py` do `public\data\*.json`). Nie czyta Lakehouse ani Eventhouse na żywo, więc zmiana
danych w Fabric nie zmienia aplikacji bez ponownego zbudowania i wdrożenia. Zapisy decyzji idą do bazy
Rayfin aplikacji, a nie do Dataverse aplikacji Power Apps.

## Czego nie sprawdzono

Logowania brokerem Fabric i zapisu od końca do końca (wymagają sesji w portalu) oraz oceny wizualnej. Sprawdzono
odpowiedzi HTTP, 30 testów vitest, build, eslint i audyt kontrastu.

## Docelowo

Odczyt z Eventhouse (kolejka, klastry w czasie rzeczywistym) i z modelu semantycznego (KIZS), zapis
zwrotny decyzji do Dataverse (patrz `INTEGRATION_POWERAPPS.md`). To rozszerzenia, nie część obecnej wersji.

Monit do ponownego wygenerowania aplikacji: `RAYFIN_PROMPT.md`.
