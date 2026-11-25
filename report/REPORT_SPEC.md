# Raport Power BI `rpt_zagrozenia_szkolne`

Raport w formacie PBIR tworzy `deploy\10_report.py`, połączony z modelem `sm_school_safety`. Ma 4 strony
i 45 wizualizacji. Motyw `OL-ZK-Dark`.

| Strona | Pytanie |
|---|---|
| 1. Obraz krajowy | ile zgłoszeń, gdzie i jak obciążone są 112 i szkoły |
| 2. AI sugeruje, człowiek decyduje | gdzie decyzja dyżurnego różni się od sugestii i jak szybko zapada |
| 3. Kampania czy realne zagrożenie | które zgłoszenia tworzą skoordynowaną falę i czy realne krytyczne zostają przy człowieku |
| 4. Eskalacja i zasoby | na jakim poziomie powinna zapaść decyzja i gdzie rozstawić patrole |

Strona 4 zawiera zastrzeżenie, że progi eskalacji i parametry zasobów są demonstracyjne, a rekomendacja jest
propozycją dla człowieka.

Weryfikacja: `deploy\11_verify_report.py` rozwiązał 42 z 42 odwołań wizualizacji do pól modelu. Wyglądu
raportu w przeglądarce nie oceniano.

Adres: https://app.powerbi.com/groups/<WORKSPACE_ID>/reports/<REPORT_ID>
