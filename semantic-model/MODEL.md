# Model semantyczny `sm_school_safety`

Model DirectLake nad Lakehouse `lh_school_safety`. Tworzy go `deploy\06_semantic_model.py`, a po każdej
zmianie danych lub definicji trzeba wykonać refresh (framing), inaczej tabele nie są rozpoznane. Ma 27 tabel,
18 relacji i 33 miary (`MEASURES.md`).

## Tabele

Wymiary: DimVoivodeship, DimCounty, DimSchool, DimCategory, DimPriority, DimStatus, DimRecipient, DimHazard.

Fakty: FactReport, FactReportStatus, FactHandoff, FactHotline, FactSocial, FactDisorder, FactPatrol,
FactSupport, FactTask, FactReadiness, FactEscalation.

Wyniki notebooków: FactCampaignFlag, FactCampaignCluster, FactKizsVoivodeship, FactKizsNational,
FactKizsCounty, FactWhatIf, FactSpo3Timing, FactPatrolDaily.

## Relacje

DimSchool do DimCounty do DimVoivodeship. FactReport do DimSchool, DimCategory i DimPriority (sugestia AI).
FactReportStatus do FactReport, DimPriority (decyzja) i DimStatus. FactCampaignFlag i FactHandoff do FactReport,
FactHandoff także do DimRecipient. FactHotline, FactDisorder i FactKizsVoivodeship do DimVoivodeship.
FactPatrol, FactSupport i FactKizsCounty do DimCounty. FactTask do DimHazard.

Relacji FactReport do DimVoivodeship nie ma, bo tworzyłaby drugą ścieżkę (przez szkołę i powiat) i model
zgłaszał niejednoznaczność. Województwo filtruje zgłoszenia przez szkołę i powiat.

## Weryfikacja

`deploy\07_verify_model.py` porównuje 12 miar DAX z liczeniem lokalnym na pandas, a dla miar kampanii z plikami
OneLake z Fabric. Wszystkie 12 zgodne. Model zawiera wyniki z Fabric (Spark), więc liczby kampanii są nieco
inne niż w dokumentach lokalnych (patrz `DEPLOYMENT_STATUS.md`). RLS nie jest skonfigurowany.
