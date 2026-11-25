"""Banki szablonow tresci zgloszen (syntetyczne, krotkie, bez szczegolow operacyjnych).

Szablony opisuja sygnaly (co uczen zauwazyl), nie metody. Zadna tresc nie zawiera
instrukcji, a sprawy samookaleczenia ograniczono do sformulowania, ze ktos
potrzebuje pomocy.
"""
from __future__ import annotations

CLASSES = ["1a", "1b", "2a", "2b", "2c", "3a", "3b", "3c", "4a", "4b", "5a", "5b", "6a", "6c", "7a", "7b", "8a", "8b"]
PLACES = ["w szatni", "w toalecie", "w autobusie szkolnym", "na boisku", "na korytarzu", "przy sklepiku", "za salą gimnastyczną"]
# W tekstach uzywamy polskich znakow, wiec slowniki ponizej maja pelna pisownie.
DAYS_PL = ["w poniedziałek", "we wtorek", "w środę", "w czwartek", "w piątek"]
SUBJECTS = ["matematyki", "polskiego", "historii", "wf-u", "chemii"]

# (kategoria, waga_istotnosci 1..4, tekst, sygnaly)
# sev: 1 niski, 2 sredni, 3 wysoki, 4 krytyczny (prawda oceniana po zdarzeniu)
BG = [
    # BRON - narzedzie lub bron
    ("BRON", 4, "Chłopak z {cls} pokazywał {place} nóż motylkowy... {when_next}", ("weapon_mention", "specific_time")),
    ("BRON", 4, "Uczeń z {cls} chwalił się, że ma w plecaku nóż i {when_next}.", ("weapon_mention", "specific_time", "threat_intent")),
    ("BRON", 4, "Ktoś z {cls} powiedział, że {day} o {hhmm} przyniesie ostre narzędzie i 'pokaże wszystkim'.", ("weapon_mention", "specific_time", "threat_intent", "named_location")),
    ("BRON", 3, "Widziałem {place} nóż u chłopaka z {cls}, schował go szybko do plecaka.", ("weapon_mention",)),
    ("BRON", 3, "Dziewczyna z {cls} miała w torbie gaz pieprzowy i straszyła nim kolegów {place}.", ("weapon_mention", "harassment")),
    ("BRON", 2, "Koledzy z {cls} przynieśli scyzoryk i pokazują go na przerwie {place}.", ("weapon_mention",)),
    ("BRON", 2, "Ktoś z {cls} rzucał {place} petardami, nikomu nic się nie stało.", ("dangerous_object",)),
    ("BRON", 1, "{place_cap} leży porzucony składany nożyk, chyba ktoś go zgubił.", ("dangerous_object",)),
    ("BRON", 1, "Uczeń z {cls} przyniósł do szkoły plastikowy pistolet na kulki i bawi się nim na przerwie.", ("dangerous_object", "joke_context")),
    # GROZBY - grozby lub zapowiedz ataku
    ("GROZBY", 4, "Uczeń z {cls} napisał na prywatnym czacie, że {day} o {hhmm} 'zrobi tu coś, czego nikt nie zapomni'. Mam zrzut ekranu.", ("threat_intent", "specific_time", "named_location", "evidence_attached")),
    ("GROZBY", 4, "Kolega z {cls} powtarza, że zemści się na nauczycielu {subject} i że {when_next}. Mówi to poważnie.", ("threat_intent", "named_target", "specific_time")),
    ("GROZBY", 3, "Na ścianie {place} ktoś napisał, że {day} będzie 'ostatni dzień' w tej szkole.", ("threat_vague", "specific_time", "named_location")),
    ("GROZBY", 3, "Uczeń z {cls} grozi koledze, że 'załatwi go po lekcjach'. Powtarza to od kilku dni.", ("threat_intent", "named_target", "harassment")),
    ("GROZBY", 2, "Ktoś z {cls} wołał na korytarzu, że 'wszystkich załatwi', ale chyba się wygłupiał.", ("threat_vague", "joke_context")),
    ("GROZBY", 2, "Chłopak z {cls} pisał w grupie, że wysadzi szkołę, jeśli dostanie jedynkę. Wszyscy się śmiali.", ("bomb_mention", "joke_context")),
    ("GROZBY", 1, "Koleżanka z {cls} powiedziała w złości, że kogoś 'zabije', jak jej ktoś zabierze telefon.", ("threat_vague", "joke_context")),
    # TRESCI_SIEC - niepokojace tresci w sieci
    ("TRESCI_SIEC", 4, "W grupie klasowej ktoś wrzucił zdjęcie broni z podpisem, że {day} 'będzie głośno o naszej szkole'. Link: {link}", ("weapon_mention", "threat_intent", "specific_time", "media_link")),
    ("TRESCI_SIEC", 3, "Anonimowe konto publikuje posty, że 'niektórzy z {cls} nie dożyją wakacji'. Link: {link}", ("threat_vague", "media_link", "named_target")),
    ("TRESCI_SIEC", 2, "Uczniowie udostępniają filmik z bójki z naszej szkoły i wyśmiewają poszkodowanego. Link: {link}", ("harassment", "media_link")),
    ("TRESCI_SIEC", 2, "Na komunikatorze krąży wulgarny mem o uczennicach z {cls}. Link: {link}", ("harassment", "media_link")),
    ("TRESCI_SIEC", 1, "Ktoś założył śmieszne konto o naszej szkole, ale nic tam groźnego nie ma. Link: {link}", ("media_link",)),
    ("TRESCI_SIEC", 1, "W sieci jest nagranie z przerwy, na którym nauczyciel się potknął. Wszyscy się śmieją. Link: {link}", ("media_link", "joke_context")),
    # PRZEMOC - przemoc lub nekanie
    ("PRZEMOC", 4, "Na boisku podczas bójki jeden z uczniów upadł i nie wstawał, reszta uciekła.", ("physical_violence", "injury_indicator", "specific_time")),
    ("PRZEMOC", 3, "Grupa chłopaków z {cls} regularnie zaczepia młodszego kolegę {place}, wczoraj go popchnęli i zabrali plecak.", ("harassment", "physical_violence")),
    ("PRZEMOC", 3, "Po lekcjach {place} dochodzi do bójek, wczoraj ktoś miał rozciętą wargę.", ("physical_violence", "injury_indicator")),
    ("PRZEMOC", 2, "Koleżanka z {cls} jest wyśmiewana przez całą klasę, wczoraj płakała {place}.", ("harassment", "distress")),
    ("PRZEMOC", 2, "W autobusie szkolnym starsi uczniowie odbierają młodszym pieniądze na bułki.", ("harassment",)),
    ("PRZEMOC", 1, "{place_cap} ktoś kogoś popchnął, ale potem się pogodzili.", ("physical_violence", "joke_context")),
    ("PRZEMOC", 1, "Koledzy z {cls} wymyślają przezwiska jednemu chłopakowi, nie wiem czy mu to przeszkadza.", ("harassment",)),
    # SAMOUSZKODZENIE - ktos moze zrobic sobie krzywde (tylko kategoria, bez szczegolow)
    ("SAMOUSZKODZENIE", 4, "Koleżanka z {cls} napisała wiadomość pożegnalną i nie odbiera telefonu. Jestem bardzo przerażony.", ("self_harm_indicator", "farewell_message", "specific_time")),
    ("SAMOUSZKODZENIE", 3, "Koleżanka z {cls} napisała, że nie ma już siły i że wszystkim byłoby lepiej bez niej. Martwię się o nią.", ("self_harm_indicator", "distress")),
    ("SAMOUSZKODZENIE", 3, "Kolega z {cls} od kilku dni mówi, że 'nie ma po co żyć', unika wszystkich.", ("self_harm_indicator", "distress")),
    ("SAMOUSZKODZENIE", 2, "Kolega z {cls} jest od tygodni smutny, nic nie je w stołówce i ucieka z lekcji.", ("distress",)),
    ("SAMOUSZKODZENIE", 2, "Koleżanka z {cls} płacze prawie codziennie {place}, chciałbym jej pomóc.", ("distress",)),
    ("SAMOUSZKODZENIE", 1, "Kolega z {cls} powiedział, że ma 'gorszy dzień', ale poprosił, żeby nikomu nie mówić. Wolę dać znać.", ("distress",)),
    # INNE
    ("INNE", 4, "Przy wejściu do szkoły stoi obcy mężczyzna i zaczepia uczniów, próbował namawiać kogoś do wyjścia z nim {when_next}.", ("stranger", "specific_time", "named_location")),
    ("INNE", 3, "Przed szkołą kręci się obcy człowiek i obserwuje młodsze klasy od kilku dni.", ("stranger", "named_location")),
    ("INNE", 2, "Na boisku są potłuczone szyby i szkło, ktoś już się skaleczył.", ("hazard_physical", "injury_indicator")),
    ("INNE", 2, "{place_cap} jest rozlana woda i można się poślizgnąć. Nikt tego nie sprząta.", ("hazard_physical",)),
    ("INNE", 1, "Zepsuta furtka przy boisku, można wyjść poza teren szkoły.", ("hazard_physical",)),
    ("INNE", 1, "W sklepiku obok szkoły sprzedają energetyki młodszym dzieciom.", ("other",)),
]

WHEN_NEXT = ["jutro przyniesie go znowu", "jutro też go przyniesie", "pojutrze zrobi to jeszcze raz", "dziś po lekcjach go znowu pokaże"]

# ---- Kampania K1: falszywe alarmy bombowe (boty) ----
K1_TEMPLATES = [
    "PILNE: w szkole jest ładunek wybuchowy, eksplozja o {hhmm}. Zgłoszenie przekazano również do mediów.",
    "Alarm! Ktoś podłożył bombę w budynku szkoły. Wybuchnie o {hhmm}. Natychmiast ewakuujcie uczniów.",
    "Uwaga, bomba w szkole, detonacja o {hhmm}. To nie jest żart. Przekażcie dalej.",
    "ALARM BOMBOWY: ładunek w szkole, wybuch o {hhmm}. Proszę o natychmiastową reakcję służb.",
    "Zgłaszam pilnie: w szkole znajduje się bomba, ma wybuchnąć o {hhmm}. Wszyscy to udostępniają.",
    "PILNE!!! bomba w szkole, o {hhmm} wybuch, ewakuacja teraz.",
]
K1_SIGNALS = ("bomb_mention", "specific_time", "imminence", "urgency_words", "mass_forward")

# ---- Kampania K2: falszywe nagrania zapowiedzi ataku ----
K2_BOT_TEMPLATES = [
    "Na filmie {link} chłopak w kapturze zapowiada atak w piątek w naszej szkole. Film ma już tysiące wyświetleń.",
    "Zobaczcie nagranie {link}: zapowiedź ataku na szkołę w piątek. Udostępniajcie, zanim zniknie.",
    "UWAGA nagranie {link} pokazuje uczniów, którzy planują atak w piątek. Służby milczą.",
    "Film {link}: człowiek w masce mówi, że w piątek szkoła 'przestanie istnieć'. Zgłaszam pilnie.",
    "Ktoś opublikował nagranie {link} z zapowiedzią ataku w piątek w szkołach w całym kraju.",
]
K2_BOT_SIGNALS = ("threat_intent", "media_link", "specific_time", "mass_forward", "urgency_words")

K2_ORGANIC_TEMPLATES = [
    "Widziałem film, który wszyscy udostępniają: ktoś zapowiada atak w piątek. Nie wiem, czy to nasza szkoła, ale się boję. {link}",
    "Koleżanka przesłała mi nagranie z zapowiedzią ataku w piątek. Nie wiem, czy to prawda. {link}",
    "Wszyscy w klasie oglądają film o ataku w piątek, rodzice pytają, czy mamy iść do szkoły.",
    "Na komunikatorze krąży nagranie z groźbą na piątek. Wolę to zgłosić, żeby ktoś sprawdził. {link}",
    "Ten film z zapowiedzią ataku jest wszędzie. Czy ktoś sprawdza, czy to prawda? Boję się iść w piątek do szkoły.",
    "Mama kazała mi to zgłosić: w sieci jest nagranie, że w piątek coś się stanie w szkołach. {link}",
    "Mój brat pokazał mi film o zapowiedzi ataku. Wygląda dziwnie, może to fałszywka. {link}",
]
K2_ORGANIC_SIGNALS = ("threat_vague", "media_link", "hearsay", "mass_forward", "distress")
K2_LINKS = ["https://klip-wideo.example/w/9fA3xQ", "https://klip-wideo.example/w/9fA3xQ", "https://klip-wideo.example/w/Lm72Bd", "https://krotki-film.example/v/ZZ41kc"]

# ---- Kampania K3: copycat po glosnym incydencie ----
K3_TEMPLATES = [
    ("Po tym, co stało się w Mieście M-1001, kolega z {cls} napisał, że też przyniesie nóż. Chyba żartował, ale się boję.", ("weapon_mention", "threat_vague", "hearsay", "joke_context"), 2),
    ("Chłopak z {cls} mówi na przerwie, że 'zrobi jak tamten w Mieście M-1001'. Nikt nie wie, czy serio.", ("threat_vague", "hearsay"), 2),
    ("Uczniowie z {cls} naśladują wiadomości o incydencie w Mieście M-1001 i straszą młodszych.", ("harassment", "hearsay"), 1),
    ("Ktoś z {cls} napisał w grupie 'u nas też może być jak w Mieście M-1001'. Nauczyciele nie wiedzą.", ("threat_vague", "hearsay", "media_link"), 2),
    ("Kolega z {cls} powiedział, że jak w Mieście M-1001 przyniesie coś i wszyscy go zauważą. Mówił to {place}.", ("threat_intent", "threat_vague", "named_location"), 3),
    ("Dzieci z {cls} bawią się w 'napad jak w wiadomościach', jeden płakał.", ("harassment", "joke_context"), 1),
    ("Uczeń z {cls} wrzucił na komunikator wpis 'kto następny po tamtej szkole?'. Został usunięty, ale mam zrzut.", ("threat_vague", "evidence_attached", "media_link"), 2),
    ("W naszej szkole też ktoś zapowiada, że będzie jak w Mieście M-1001. To pewnie żarty, ale wolę zgłosić.", ("threat_vague", "hearsay", "joke_context"), 1),
    ("Kolega z {cls} pokazał kolegom {place} zdjęcie noża z internetu i powiedział, że chce taki sam, jak ten z wiadomości.", ("weapon_mention", "threat_vague"), 3),
    ("Uczennica z {cls} pisze w sieci, że boi się, że ktoś powtórzy to, co było w Mieście M-1001.", ("distress", "hearsay"), 1),
]

# ---- Realne krytyczne zgloszenia ukryte w fali (R) ----
# Ostatnie trzy to przypadki trudne: slownictwo zbliżone do kampanii K1, ale ze szczegolami lokalnymi.
REAL_CRITICAL = [
    ("Uczeń z {cls} pokazał {place} nóż i powiedział, że {when_next}.", ("weapon_mention", "specific_time", "threat_intent"), "BRON"),
    ("Chłopak z {cls} napisał w prywatnej wiadomości, że {day} o {hhmm} 'zrobi coś' w szkole. Mam zrzut ekranu.", ("threat_intent", "specific_time", "named_location", "evidence_attached"), "GROZBY"),
    ("Kolega z {cls} ma w plecaku ostre narzędzie, schował je {place} i wspomniał, że 'dziś się przyda'.", ("weapon_mention", "imminence", "threat_intent"), "BRON"),
    ("Uczeń z {cls} grozi nauczycielowi {subject}, że {day} 'załatwi sprawę po lekcjach'. Pokazywał też nóż {place}.", ("weapon_mention", "threat_intent", "named_target", "specific_time"), "GROZBY"),
    ("Po wydarzeniach w Mieście M-1001 uczeń z {cls} powiedział, że {day} zrobi to samo u nas. Nosi przy sobie nóż.", ("weapon_mention", "threat_intent", "specific_time", "hearsay"), "GROZBY"),
    ("Koleżanka z {cls} napisała wiadomość pożegnalną i nie odbiera telefonu od rana. Boję się o nią.", ("self_harm_indicator", "farewell_message", "imminence"), "SAMOUSZKODZENIE"),
    ("Chłopak z {cls} przyniósł do szkoły coś, co wygląda jak broń. Pokazał to {place} dwóm kolegom.", ("weapon_mention", "named_location"), "BRON"),
    ("{place_cap} ktoś z {cls} zapowiedział, że {day} 'nikt nie wyjdzie ze szkoły o czasie'. Ma na to przygotowany plan.", ("threat_intent", "specific_time", "named_location"), "GROZBY"),
    # przypadki trudne
    ("ALARM: bomba w szkole, wybuch o {hhmm}. Napisał to uczeń z {cls} w naszej klasowej grupie, mam jego wiadomość, wcześniej mówił, że ma dość tej szkoły.", ("bomb_mention", "specific_time", "urgency_words", "threat_intent", "evidence_attached"), "GROZBY"),
    ("PILNE: uczeń z {cls} powiedział mi na przerwie {place}, że o {hhmm} w szkole będzie wybuch. Nie wiem, czy to część tego, co jest w internecie, ale mówił o tym bardzo poważnie.", ("bomb_mention", "specific_time", "urgency_words", "threat_intent"), "GROZBY"),
    ("Uwaga, ładunek w szkole, detonacja o {hhmm}. Widziałem kolegę z {cls}, jak chował {place} torbę i mówił, że nikt nie ma jej ruszać.", ("bomb_mention", "specific_time", "imminence", "named_location", "threat_intent"), "GROZBY"),
]
