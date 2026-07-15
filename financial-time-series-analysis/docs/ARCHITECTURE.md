# Architettura

## Flusso dati

1. Le pipeline in pipelines acquisiscono dati da fonti pubbliche abilitate.
2. dlt persiste i record grezzi in un database DuckDB locale.
3. dbt costruisce staging, tabelle intermedie, feature mart e dataset per i modelli.
4. features genera variabili point-in-time e applica controlli anti-leakage.
5. baselines e models producono previsioni comparabili.
6. evaluation esegue walk-forward, metriche, calibrazione e test sul rischio.
7. strategy applica segnali, costi, position sizing e metriche di portafoglio.
8. experiments registra metadati e artefatti locali.
9. reporting genera output tecnici e business.

## Principi

### Riproducibilità

Configurazioni e codice sono versionati; database, cache e report generati sono ricostruibili e restano locali.

### Point-in-time correctness

Feature, target e join temporali devono rispettare il momento in cui l'informazione era realmente disponibile. I test temporali impediscono l'uso involontario di dati futuri.

### Baseline first

Ogni modello viene confrontato con una baseline coerente con il task. Un risultato non viene promosso solo perché positivo in assoluto.

### Costi e rischio

Il gate decisionale considera costi di transazione, stabilità per regime, drawdown e rischio di coda.

### Separazione degli output

I risultati delle run sono scritti in data, reports e cartelle di artefatti ignorate da Git. Solo esempi sintetici curati sono conservati sotto examples.

## Componenti

| Cartella | Responsabilità |
|---|---|
| pipelines | ingestion, validazione e orchestrazione |
| dbt | modellazione SQL e data quality |
| features | feature e target point-in-time |
| baselines | benchmark minimi |
| models | modelli statistici e predittivi |
| evaluation | walk-forward, metriche e risk testing |
| strategy | segnali, costi e metriche economiche |
| experiments | registry e metadata delle run |
| reporting | report Markdown e grafici |

## Confini di sicurezza

- Le API key entrano soltanto da variabili d'ambiente.
- Il database locale non viene versionato.
- Il progetto non invia ordini e non si collega ad account di trading.
- I report dimostrativi non contengono risultati reali.
