# Monit dla Rayfin: Pulpit krajowy szkół

Aplikacja z tego monitu jest już wdrożona (`fabric-app\pulpit-szkol`, adres w `APP_SPEC.md`). Monit
zostawiamy jako zapis wymagań na wypadek ponownego wygenerowania. Nie uruchamiaj go na istniejącym elemencie.

> Zbuduj aplikację Fabric "Pulpit krajowy szkół", krajową nakładkę na demo Power Apps do zgłoszeń szkolnych.
> Odbiorcy: dyżurny krajowy, analityk RCB, minister wiodący (MEN lub MSWiA) i RZZK. Dane w całości syntetyczne,
> w stopce widoczna informacja o tym.
>
> Ekrany: (1) obraz krajowy z kartogramem Krajowego Indeksu Zagrożenia Szkolnego dla 16 województw i
> drill-downem do powiatu i szkoły, kafle KPI i oś czasu D-3 do D+7; (2) kolejka z zakładkami Otwarte,
> Krytyczne, Nowe, Zamknięte, numery BS-xxxx, statusy Nowe, Przekazane, W analizie, Zamknięte, mapa w kolorach
> priorytetu, szczegół z sugestią AI i osobną decyzją dyżurnego ("AI: KRYTYCZNY" obok "DECYZJA: KRYTYCZNY"),
> przekazanie do Policji, Dyrekcji szkoły, Pedagoga lub psychologa, Dyżurnet.pl (NASK); (3) kampanie: klastry,
> województwa, zasięg social, oznaczenie "prawdopodobnie fałszywy alarm" lub "wymaga reakcji", lista realnych
> zgłoszeń ukrytych w fali; (4) eskalacja powiat, wojewoda, minister, RZZK z progami i zadaniami działów XV, XIX,
> X, XIII oraz SPO-1, SPO-3, SPO-12, SPO-16, szkic komunikatu SPO-3 wymagający zatwierdzenia człowieka;
> (5) zasoby wsparcia: pedagodzy, psycholodzy, patrole.
>
> Zasady: AI sugeruje, człowiek decyduje, każda decyzja trafia do audytu. Sugestie klasyfikują zgłoszenie, nie
> osoby. Bez danych osobowych uczniów. Treści zgłoszeń krótkie, bez instrukcji ani szczegółów operacyjnych.
> Jasna paleta rządowa i kontrast WCAG co najmniej 4,5:1. Dane z migawki plików `datasets\`.
