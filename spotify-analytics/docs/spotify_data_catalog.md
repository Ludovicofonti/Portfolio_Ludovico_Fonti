# Catalogo dati Spotify Analytics

Il catalogo descrive il percorso di produzione che alimenta il report Looker Studio di
Spotify Italy Analytics: ownership delle sorgenti, livelli BigQuery, granularità dei
modelli e controlli che impediscono ai dati incompleti di raggiungere le
visualizzazioni.

## Lineage di produzione

```text
Kworb Top 200 Italia + Spotify Web API
  -> validazione Python e arricchimento deterministico tramite Track ID
  -> caricamento diretto nelle partizioni raw BigQuery
  -> viste dbt di staging e intermediate
  -> fact e mart dbt
  -> viste di reporting rpt_* in BigQuery
  -> Looker Studio
```

GitHub Actions è l'unico scheduler. BigQuery è sia il data warehouse sia la sorgente di
pubblicazione; il progetto non mantiene un database o un orchestratore locale
alternativo e non versiona copie CSV o JSON dei dati.

## Sorgenti

| Sorgente | Dati utilizzati | Regola di acquisizione |
| --- | --- | --- |
| [Kworb Spotify Italy Daily](https://kworb.net/spotify/country/it_daily.html) | Rank giornaliero, stream, movimento e Spotify Track ID | Uno snapshot Top 200 osservato per ogni esecuzione riuscita |
| [Spotify Web API: Get Track](https://developer.spotify.com/documentation/web-api/reference/get-track) | Brano, artista, album, release, durata, explicit, artwork e link Spotify | Arricchimento esatto tramite `GET /tracks/{id}` usando il Track ID della classifica |

Kworb è indicato in modo trasparente come mirror pubblico della classifica. I metadati
Spotify sono memorizzati in cache e acquisiti con retry limitati. Il progetto non usa
contenuti Spotify per addestrare modelli di intelligenza artificiale o machine learning.

## Dataset BigQuery

I nomi possono essere personalizzati tramite variabili d'ambiente; i valori predefiniti
sono:

| Dataset | Materializzazione | Responsabile |
| --- | --- | --- |
| `spotify_analytics_raw` | Tabelle sorgente partizionate | Loader Python |
| `spotify_analytics_staging` | Viste tipizzate | dbt |
| `spotify_analytics_intermediate` | Viste di arricchimento riutilizzabili | dbt |
| `spotify_analytics_marts` | Fact, mart e viste `rpt_*` | dbt |

Le risorse usano l'etichetta `application=spotify-analytics`. Le partizioni raw
scadono dopo 365 giorni; i mart con granularità giornaliera richiedono il filtro di
partizione per limitare scansioni complete accidentali.

## Tabelle raw

| Tabella | Granularità | Chiave stabile |
| --- | --- | --- |
| `italy_daily_chart` | Una posizione per data, paese e brano | `chart_date`, `country`, `track_id` |
| `italy_daily_track_details` | Un arricchimento Spotify per riga osservata | `chart_date`, `chart_track_id` |
| `italy_daily_track_details__artists` | Un artista per brano arricchito | ID riga padre, artist ID e posizione nella lista |
| `italy_daily_track_details__album__images` | Un'immagine per brano arricchito | ID riga padre e posizione nella lista |
| `spotify_track_metadata_cache` | Una versione cache per brano e data | Track ID, mercato e data cache |
| `pipeline_runs` | Una riga per esecuzione riuscita | `run_id` |

Il loader riceve i record in memoria, genera identificativi tecnici deterministici,
sostituisce atomicamente soltanto la partizione giornaliera e rifiuta dataset vuoti.
La cache e le metriche operative sono anch'esse gestite in BigQuery.

## Modelli analitici

| Modello | Granularità e scopo |
| --- | --- |
| `fct_track_chart_daily` | Fact incrementale per data, paese e Spotify Track ID |
| `mart_top_songs_italy` | Rank, stream e metadati giornalieri del brano |
| `mart_top_artists_italy` | Stream e rank giornalieri dell'artista |
| `mart_album_release_analysis` | Prestazioni giornaliere di album e release |
| `mart_chart_momentum` | Movimento di rank e stream |
| `mart_chart_entries_exits` | Eventi di ingresso e uscita |
| `mart_track_lifecycle` | Picco osservato, persistenza e stato del ciclo di vita |
| `mart_artist_market_share` | Quota giornaliera dell'artista sugli stream Top 200 |
| `mart_release_cohorts` | Prestazioni raggruppate per mese di release |
| `mart_chart_concentration` | Concentrazione Top 10 e Top 50 |
| `mart_data_quality_daily` | Completezza, duplicati e copertura metadati |

## Viste per Looker Studio

La dashboard si collega alle viste seguenti. Le definizioni di business rimangono in
dbt e non vengono replicate nei singoli grafici.

| Vista | Granularità | Campi principali |
| --- | --- | --- |
| `rpt_market_overview_daily` | Data e paese | `streams`, `streams_change`, `top_10_stream_share`, `top_50_stream_share`, `collaboration_share`, `explicit_share`, `fresh_streams`, `developing_streams`, `catalog_streams` |
| `rpt_artist_performance_daily` | Data, paese e artista | `artist_name`, `track_count`, `streams`, `market_share`, `artist_stream_rank`, `artist_segment` |
| `rpt_track_opportunities_daily` | Data, paese e brano | `days_on_chart`, `streams`, `movement_size`, `release_stage`, `action_label` |
| `rpt_release_performance_daily` | Data, paese e brano | Data release, coorte, fase, collaborazione e stream |
| `rpt_chart_flow_daily` | Data di osservazione ed evento del brano | Ingresso/uscita e descrittori del brano |
| `rpt_track_lifecycle` | Paese e brano | Date osservate, picco, stream e ciclo di vita |
| `rpt_pipeline_health_daily` | Data e paese | Righe, match rate, freschezza e copertura storica |

La mappatura completa tra campi e visualizzazioni è disponibile nella
[guida alla dashboard](dashboard_guide.md).

## Contratto di qualità

L'esecuzione schedulata fallisce prima di ricostruire il livello di reporting quando si
verifica una delle condizioni seguenti:

- meno di 190 righe di classifica;
- date, rank, Track ID o stream obbligatori mancanti;
- duplicati della granularità o delle posizioni giornaliere;
- copertura dei metadati Spotify inferiore al 95%;
- modelli o test dbt non riusciti.

Il progetto controlla inoltre intervalli di rank e stream, date future, coerenza del
ciclo di vita e freschezza della sorgente. In caso di errore, Looker Studio continua a
leggere l'ultima versione valida delle viste BigQuery.

## Limitazioni note

- La storia inizia dal primo snapshot acquisito; nessun backfill sintetico viene
  presentato come dato osservato.
- Le audio feature non disponibili alle nuove applicazioni Spotify sono escluse.
- La continuità dipende dalla disponibilità del mirror pubblico e della Spotify API.
- Le date mancanti o non valide devono apparire come interruzioni, non come eventi con
  zero stream.
- Looker Studio è il livello di presentazione; la logica riutilizzabile rimane
  versionata in dbt e BigQuery.
