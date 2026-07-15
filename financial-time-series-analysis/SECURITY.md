# Sicurezza e pubblicazione

## Credenziali

Le credenziali devono essere fornite esclusivamente tramite variabili d'ambiente o secret store. Non inserire valori reali in file YAML, TOML, Markdown, notebook, test o fixture.

Sono esclusi dal repository:

- file .env e .dlt/secrets.toml;
- chiavi, certificati e cartelle credentials/secrets;
- profili dbt locali;
- database, dataset, backup e artefatti delle run.

## Dati e report

Usare esclusivamente dati pubblici, sintetici o correttamente autorizzati. I report sotto examples sono dimostrativi e non devono essere sostituiti con output reali senza una revisione di licenza, privacy e contenuto.

## Controlli prima della pubblicazione

1. Verificare che git status non includa database, log o output.
2. Cercare token, chiavi e percorsi locali nei file tracciati.
3. Controllare termini e licenze delle fonti dati.
4. Confermare che metriche e risultati pubblicati siano sintetici o riproducibili.
5. Eseguire test Python e parsing dbt.

## Ambito

Il progetto è didattico e non gestisce ordini reali, account di trading o denaro. Non costituisce consulenza finanziaria.
