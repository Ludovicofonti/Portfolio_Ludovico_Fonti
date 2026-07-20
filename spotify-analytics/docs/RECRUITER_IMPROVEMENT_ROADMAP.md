# Spotify Analytics — Roadmap per GitHub e LinkedIn

> **Decisione implementativa aggiornata — 17 luglio 2026:** BigQuery è ora il warehouse
> di pubblicazione, mentre GitHub Actions rimane lo scheduler. I riferimenti a DuckDB nel
> piano originale descrivono la baseline iniziale e sono superati per il percorso pubblico.
> Configurazione, IAM e controlli di costo sono documentati in
> [BIGQUERY_DEPLOYMENT.md](BIGQUERY_DEPLOYMENT.md).

## Obiettivo

Rendere **Spotify Italy Analytics** più interessante per recruiter e hiring manager in ambito Data Engineering, Analytics Engineering e Business Intelligence, mantenendo i costi a zero o entro le quote gratuite disponibili.

Il progetto Google Cloud è condiviso con `job-market-agent`, che utilizza già BigQuery, Cloud Storage, Cloud Run e Cloud Scheduler. Per questo motivo, l'architettura raccomandata privilegia GitHub Actions, DuckDB e GitHub Pages, lasciando Google Cloud come estensione opzionale e controllata.

## Valutazione attuale

### Punti di forza

- Pipeline end-to-end con Airflow, dlt, PostgreSQL, dbt ed Evidence.
- Dashboard pubblica con filtri e indicatori orientati a decisioni commerciali.
- Aggiornamento giornaliero e deploy automatico tramite GitHub Actions.
- Documentazione trasparente sulle fonti e sulle limitazioni della Spotify Web API.
- Ambiente locale riproducibile tramite Docker Compose.
- Pubblicazione gratuita tramite GitHub Pages.

### Principali lacune

- Sono presenti solamente due snapshot raw: manca uno storico sufficiente per analisi temporali credibili.
- Non sono presenti test Python, configurazioni `pytest`, `ruff` o `pre-commit`.
- La pipeline pubblica genera i mart direttamente in Python e non esegue i modelli dbt dichiarati nell'architettura.
- L'arricchimento Spotify usa una ricerca testuale `track + artist`, nonostante la fonte Kworb fornisca già lo Spotify Track ID.
- I commit automatici dei dati finiscono sul branch principale e possono rendere poco leggibile la cronologia del portfolio.
- Il README non presenta screenshot, GIF, badge di qualità o risultati quantitativi immediatamente visibili.
- La dashboard mostra soprattutto uno snapshot corrente, mentre il vero elemento distintivo dovrebbe essere l'evoluzione della classifica nel tempo.

## Priorità

| Priorità | Miglioramento | Risultato atteso |
| --- | --- | --- |
| P0 | Conservare almeno 90 giorni di storico | Analisi temporali e pipeline incrementale reali |
| P0 | Eseguire `dbt build` nella pipeline pubblica | Coerenza tra architettura dichiarata e sistema live |
| P0 | Aggiungere test, controlli qualità e CI | Credibilità da progetto production-ready |
| P0 | Recuperare i metadati tramite Spotify Track ID | Matching deterministico e meno errori |
| P1 | Aggiungere trend, anomalie e metriche di qualità | Dashboard più utile e distintiva |
| P1 | Migliorare README e presentazione visuale | Maggiore impatto nei primi secondi di visita |
| P1 | Separare i commit automatici dei dati | Cronologia Git più pulita |
| P2 | Aggiungere un mirror BigQuery opzionale | Dimostrazione cloud con rischio economico limitato |

## 1. Costruire uno storico reale

La tabella principale dovrebbe avere la seguente grana:

```text
chart_date + country + track_id
```

È consigliabile conservare almeno 90 giorni di dati. Il volume rimarrebbe molto contenuto: 200 righe al giorno corrispondono a circa 73.000 righe all'anno.

### Analisi da aggiungere

- Nuove entrate e uscite dalla Top 200.
- Velocità di salita e discesa.
- Giorni necessari per raggiungere il picco.
- Persistenza e probabilità di permanenza in classifica.
- Concentrazione degli stream nella Top 10 e Top 50.
- Concentrazione per artista e collaborazione.
- Coorti per mese o trimestre di pubblicazione.
- Volatilità giornaliera della classifica.
- Brani breakout, resilienti e in declino.
- Quote di stream conquistate o perse dagli artisti.

### Nuovi mart suggeriti

```text
fct_track_chart_daily
mart_chart_entries_exits
mart_track_lifecycle
mart_artist_market_share
mart_release_cohorts
mart_chart_concentration
mart_data_quality_daily
```

## 2. Rendere coerente la pipeline pubblica

### Architettura pubblica raccomandata

```text
GitHub Actions
  -> estrazione Python/dlt
  -> DuckDB
  -> dbt Core con dbt-duckdb
  -> test dbt
  -> export dei mart in CSV
  -> Evidence
  -> GitHub Pages
```

### Architettura locale

```text
Airflow
  -> dlt
  -> PostgreSQL
  -> dbt-postgres
  -> controlli qualità
  -> Evidence
```

Gli stessi modelli dbt dovrebbero essere eseguibili su due target:

- `duckdb`, usato da GitHub Actions;
- `postgres`, usato dall'ambiente locale con Airflow.

Questo approccio permette al dashboard pubblico di dimostrare concretamente l'uso di dbt, mantenendo al tempo stesso PostgreSQL e Airflow come laboratorio tecnico locale.

### Miglioramento del DAG Airflow

Il flusso locale dovrebbe mostrare una dipendenza completa:

```text
extract
  >> validate_raw
  >> dbt_build
  >> validate_marts
  >> publish_metadata
```

È preferibile un singolo DAG coerente, oppure due DAG collegati esplicitamente tramite dataset scheduling, invece di un DAG di trasformazione esclusivamente manuale.

## 3. Migliorare il matching Spotify

Kworb espone già lo Spotify Track ID all'interno del link della traccia. L'arricchimento dovrebbe quindi usare:

```text
GET /v1/tracks/{id}
```

anziché affidarsi alla prima corrispondenza restituita dalla Search API.

### Vantaggi

- Corrispondenza deterministica.
- Eliminazione dei falsi match dovuti a remix, versioni live o titoli simili.
- Migliore spiegabilità della pipeline.
- Cache più semplice, indicizzata direttamente per `track_id`.

### Resilienza da aggiungere

- Cache permanente dei metadati per `track_id`.
- Retry con backoff e jitter.
- Rispetto dell'header Spotify `Retry-After`.
- Conteggio delle richieste, retry e risposte 429.
- Conservazione dell'ultimo snapshot valido.
- Blocco della pubblicazione se la chart contiene meno di 190 righe.
- Blocco della pubblicazione se data, rank o track ID sono assenti.
- Metrica giornaliera `metadata_match_rate`.
- Tabella degli ID non arricchiti e delle cause di errore.

## 4. Test e qualità

### Test Python

Aggiungere `pytest` con fixture locali per evitare dipendenze dalla rete durante la CI.

Test minimi:

- parsing di una pagina Kworb salvata come fixture HTML;
- estrazione della data della chart;
- parsing di rank, stream e variazioni;
- gestione di `NEW`, `RE`, `=` e valori mancanti;
- recupero diretto tramite Track ID;
- comportamento della cache;
- retry su 429, 500, 502 e 503;
- costruzione dei dataset pubblici;
- mancata pubblicazione di dataset vuoti o incompleti.

### Test dbt

- Unicità di `chart_date + country + track_id`.
- Unicità di `chart_date + country + chart_rank`.
- `chart_rank` compreso tra 1 e 200.
- Stream maggiori o uguali a zero.
- Relazioni tra tracce, artisti e album.
- `chart_date` non futura.
- `peak_rank` coerente con il rank corrente.
- Completezza minima dei metadati.
- Freshness della sorgente.

### Tooling gratuito

```text
pytest
pytest-cov
ruff
pre-commit
dbt-core
dbt-duckdb
```

### Workflow CI suggerito

```text
Pull request / push
  -> ruff check
  -> pytest
  -> dbt deps
  -> dbt seed
  -> dbt build
  -> build Evidence
```

## 5. Osservabilità della pipeline

Il dashboard dovrebbe mostrare un piccolo pannello tecnico con:

- data dell'ultimo aggiornamento;
- data della chart più recente;
- righe acquisite;
- percentuale di tracce arricchite;
- numero di test superati e falliti;
- durata della pipeline;
- retry Spotify e risposte 429;
- stato `fresh`, `stale` o `degraded`;
- link al workflow GitHub Actions più recente.

Una tabella `mart_data_quality_daily` può contenere:

```text
run_id
run_started_at
chart_date
chart_rows
matched_tracks
match_rate
duplicate_tracks
missing_streams
spotify_requests
spotify_retries
pipeline_duration_seconds
pipeline_status
```

## 6. GitHub Actions e cronologia dei dati

Il workflow giornaliero attuale aggiorna e committa i dataset sul branch principale. In un monorepo questo può nascondere i commit di sviluppo dietro molti commit automatici.

### Soluzione consigliata

- Mantenere codice e documentazione su `main`.
- Salvare gli snapshot su un branch dedicato, ad esempio `spotify-data`.
- Fare leggere al workflow Evidence i dati dal branch dedicato.
- Usare una sola concurrency group per refresh e deploy.
- Impostare `cancel-in-progress: false` sul refresh dei dati.
- Impostare `cancel-in-progress: true` solamente sul deploy del sito.

Alternativamente, con BigQuery abilitato, gli snapshot storici possono essere conservati nel warehouse e su GitHub può essere pubblicato solamente un estratto recente.

## 7. Dashboard orientata ai recruiter

### Prima sezione

La parte iniziale dovrebbe comunicare immediatamente:

```text
Ultimo aggiornamento: oggi
200 tracce monitorate ogni giorno
90+ giorni di storico
Copertura metadati: 99%
Costo operativo: EUR 0/mese
```

### Sezioni consigliate

1. Executive summary.
2. Market pulse e concentrazione degli stream.
3. Nuove entrate e uscite.
4. Track lifecycle e momentum.
5. Artist market share.
6. Release cohort analysis.
7. Opportunità e segnali da monitorare.
8. Data quality e pipeline health.
9. Metodologia, fonti e limitazioni.

### Insight da evidenziare

Il dashboard dovrebbe presentare tre o quattro insight scritti, generati da regole deterministiche. Per esempio:

- aumento della concentrazione degli stream nella Top 10;
- artista con la maggiore crescita di quota settimanale;
- nuova entrata con crescita più rapida;
- brano di catalogo con resilienza inattesa;
- divergenza tra variazione del rank e variazione degli stream.

Non è necessario utilizzare machine learning. Analisi descrittive ben modellate e spiegabili sono più adatte al progetto e riducono anche i rischi legati alle policy Spotify.

## 8. Presentazione GitHub

Il README dovrebbe essere riorganizzato per comunicare valore nei primi secondi.

### Above the fold

- Titolo e descrizione di una riga.
- Screenshot hero del dashboard.
- Pulsante Markdown cliccabile `View live dashboard`.
- Badge CI, dbt build, ultimo refresh, licenza e costo.
- Tre risultati quantitativi.

### Sezioni successive

- Problema di business.
- Architettura visuale Mermaid.
- Insight principali.
- Data quality e affidabilità.
- Scelte architetturali e trade-off.
- Quick start riproducibile.
- Struttura del repository.
- Costi operativi.
- Limitazioni e roadmap.

### Asset da creare

- Screenshot desktop.
- Screenshot mobile.
- GIF di 20-30 secondi con l'uso dei filtri.
- Diagramma della pipeline.
- Diagramma della data lineage.

### Visibilità GitHub

- Creare un repository standalone o un mirror chiamato `spotify-italy-analytics`.
- Fissare il repository nel profilo GitHub.
- Aggiungere topic come `data-engineering`, `analytics-engineering`, `dbt`, `airflow`, `duckdb`, `spotify` ed `evidence`.
- Creare una release `v1.0`.
- Gestire la roadmap tramite GitHub Issues.

## 9. Presentazione LinkedIn

Il contenuto LinkedIn dovrebbe partire dal problema e dall'insight, non dall'elenco degli strumenti.

### Struttura del post

1. Domanda: cosa rende un brano resiliente nella Top 200 italiana?
2. Dataset: 200 tracce al giorno e almeno 90 giorni di storico.
3. Problema tecnico: API limitate, matching e rate limiting.
4. Architettura della pipeline.
5. Insight principale visualizzato nel dashboard.
6. Data quality e costo operativo.
7. Link al dashboard e al repository.

### Carosello suggerito

1. Copertina con la domanda di business.
2. Architettura end-to-end.
3. Evoluzione della Top 200.
4. Insight su artista, release o concentrazione.
5. Controlli di qualità.
6. Stack e costo `EUR 0/mese`.
7. Call to action verso dashboard e GitHub.

## 10. Strategia Google Cloud condivisa

`job-market-agent` utilizza già:

- Cloud Storage;
- BigQuery;
- Cloud Run Jobs;
- Cloud Scheduler.

Le quote gratuite di diversi servizi Google Cloud sono aggregate a livello di account di fatturazione, non garantite separatamente per ogni progetto o applicazione. Spotify Analytics non dovrebbe quindi duplicare inutilmente servizi già usati.

### Architettura raccomandata a costo zero

| Componente | Soluzione |
| --- | --- |
| Scheduling | GitHub Actions |
| Storage pubblico | Branch Git dedicato o file versionati |
| Warehouse CI | DuckDB |
| Trasformazioni | dbt Core + dbt-duckdb |
| Dashboard | Evidence |
| Hosting | GitHub Pages |
| Orchestrazione dimostrativa | Airflow locale |
| Warehouse dimostrativo | PostgreSQL locale |
| Consumo GCP aggiuntivo | Zero |

### Estensione BigQuery opzionale

Se si desidera dimostrare anche competenze Google Cloud, aggiungere soltanto un dataset BigQuery dedicato:

```text
spotify_analytics_raw
spotify_analytics_staging
spotify_analytics_marts
```

Controlli obbligatori:

- tabelle partizionate per `chart_date`;
- clustering per `track_id` o `artist_id`;
- `require_partition_filter = true`;
- scadenza dei dati raw dopo 365 giorni;
- service account separato;
- permessi limitati ai dataset Spotify;
- autenticazione GitHub tramite Workload Identity Federation;
- label `application=spotify-analytics`;
- limite massimo di byte processati per query;
- dashboard di billing separata per label o dataset.

Non sono necessari un nuovo Cloud Run Job, un nuovo bucket GCS o un nuovo Cloud Scheduler. GitHub Actions può caricare direttamente piccoli batch in BigQuery.

### Quote da considerare

- BigQuery: primi 10 GiB di storage e 1 TiB mensile di query gratuiti.
- Cloud Scheduler: tre job gratuiti per account di fatturazione.
- Cloud Run: quote gratuite aggregate tra i progetti dello stesso billing account.
- Cloud Storage: 5 GB gratuiti solamente in specifiche regioni statunitensi.

Un budget Google Cloud genera notifiche ma non costituisce un limite rigido alla spesa. È necessario affiancarlo a quote, permessi minimi, scadenze e limiti applicativi.

## 11. Governance e attribuzione

Il progetto dovrebbe mostrare chiaramente:

- Kworb come fonte della classifica e degli stream;
- Spotify Web API come fonte dei metadati;
- data e ora dell'ultimo aggiornamento;
- metodologia di matching;
- limitazioni dei dati;
- attribuzione e link a Spotify quando vengono mostrate copertine o metadati;
- disclaimer che il progetto non è affiliato a Spotify;
- nessun utilizzo dei contenuti Spotify per addestrare modelli AI o ML.

## Piano di esecuzione

### Sprint 1 — Affidabilità

- Passare da Search API a Track ID.
- Aggiungere cache e health gate.
- Creare test Python e fixture.
- Configurare Ruff e GitHub Actions CI.
- Impedire la pubblicazione di snapshot incompleti.

### Sprint 2 — Analytics engineering

- Conservare lo storico giornaliero.
- Rendere incrementali i modelli dbt.
- Aggiungere test dbt e freshness.
- Eseguire dbt-duckdb nella pipeline pubblica.
- Eliminare la duplicazione della business logic Python/dbt.

### Sprint 3 — Dashboard e portfolio

- Aggiungere analisi temporali e data quality.
- Creare screenshot, GIF e diagrammi.
- Riscrivere la parte iniziale del README.
- Pubblicare una release `v1.0`.
- Preparare carosello e post LinkedIn.

### Sprint 4 — Cloud opzionale

- Creare dataset BigQuery separati.
- Configurare service account e Workload Identity Federation.
- Aggiungere partizionamento, clustering e limiti di query.
- Verificare il consumo congiunto con `job-market-agent`.

## Criteri di completamento

Il progetto può essere considerato pronto per recruiter quando:

- contiene almeno 90 giorni di storico;
- il dashboard pubblico è aggiornato automaticamente;
- la pipeline pubblica esegue realmente dbt;
- test Python e dbt sono verdi in CI;
- la copertura dei metadati è visibile;
- esistono controlli contro snapshot incompleti;
- il README mostra subito dashboard, architettura e risultati;
- è disponibile una demo visuale breve;
- il costo operativo è documentato;
- l'eventuale consumo GCP è isolato e misurabile.

## Riferimenti

- [GitHub Actions — billing and usage](https://docs.github.com/en/actions/concepts/billing-and-usage)
- [Spotify Web API — Get Track](https://developer.spotify.com/documentation/web-api/reference/get-track)
- [Spotify Web API — Rate Limits](https://developer.spotify.com/documentation/web-api/concepts/rate-limits)
- [Spotify Web API changes](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)
- [Google BigQuery pricing](https://cloud.google.com/bigquery/pricing)
- [Google Cloud Scheduler pricing](https://cloud.google.com/scheduler/pricing)
- [Google Cloud Run pricing](https://cloud.google.com/run/pricing)
- [Google Cloud Storage pricing](https://cloud.google.com/storage/pricing)
- [Google Cloud budget notifications](https://docs.cloud.google.com/billing/docs/how-to/budgets-programmatic-notifications)
