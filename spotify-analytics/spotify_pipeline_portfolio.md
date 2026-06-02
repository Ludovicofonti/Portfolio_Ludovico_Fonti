# Spotify Italy Chart Pipeline - Portfolio Project

### Stack: Apache Airflow, dlt, PostgreSQL, dbt, Evidence, GitHub Actions

---

## Panoramica Del Progetto

Questo progetto realizza una pipeline dati end-to-end per analizzare i **brani piu ascoltati in Italia su Spotify**.

La pipeline:

1. Estrae la classifica giornaliera Spotify Italia.
2. Arricchisce i brani con metadati dalla Spotify Web API.
3. Carica i dati raw in PostgreSQL con dlt.
4. Orchestra l'esecuzione locale con Apache Airflow.
5. Trasforma i dati con dbt.
6. Pubblica una dashboard/report con Evidence.
7. Usa GitHub Actions e GitHub Pages per aggiornare e pubblicare gratuitamente il progetto senza lasciare acceso il PC.

Il focus analitico non e piu "tracce per genere", ma:

> Quali sono i brani, gli artisti e gli album che dominano la classifica Spotify Italia?

---

## Architettura

### Modalita Locale - Sviluppo E Portfolio Tecnico

```text
Kworb Spotify Daily Italy chart
      |
      v
 Python parser + dlt
      |
      v
 PostgreSQL - schema spotify_raw
      |
      v
 dbt
      |
      v
 PostgreSQL - schema spotify_marts
      |
      v
 Evidence

Orchestrazione locale: Apache Airflow
```

Il ranking e gli stream arrivano dalla chart giornaliera Italia. I metadati musicali vengono arricchiti tramite Spotify Web API Search.

### Modalita GitHub - Aggiornamento Automatico Gratuito

```text
GitHub Actions cron giornaliero
      |
      v
 Python extraction script
      |
      v
 data/raw e data/processed
      |
      v
 Evidence build
      |
      v
 GitHub Pages
```

Questa modalita serve a mantenere vivo il portfolio senza lasciare il PC acceso. GitHub Actions esegue la pipeline su runner GitHub, usa i secret del repository e pubblica il sito statico Evidence.

> Nota: GitHub Actions non puo connettersi al PostgreSQL locale del tuo PC. Per questo PostgreSQL resta il warehouse locale, mentre su GitHub si salvano dataset pubblicabili in `data/`.

---

## Stack Tecnologico

| Tool | Ruolo | Perche |
|---|---|---|
| dlt | Extract & Load | Carica dati in PostgreSQL e normalizza JSON annidati |
| Apache Airflow | Orchestrazione locale | Standard industry, ottimo per portfolio |
| PostgreSQL | Warehouse locale | Database relazionale realistico e compatibile con Airflow |
| dbt Core | Trasformazione | Modelli SQL, test e documentazione |
| Evidence | Dashboard/report | Markdown + SQL, pubblicabile su GitHub Pages |
| Docker Compose | Ambiente locale | Airflow + PostgreSQL riproducibili |
| GitHub Actions | Automazione gratuita | Refresh schedulato senza PC acceso |
| GitHub Pages | Hosting | Pubblicazione gratuita del report |

### Perche PostgreSQL

PostgreSQL e la scelta migliore per questo portfolio perche:

- e uno standard molto richiesto nei ruoli data;
- e gia incluso nello stack Docker Compose di Airflow;
- permette di mostrare competenze reali su database, schema, SQL e connessioni;
- funziona bene con dlt, dbt ed Evidence.

DuckDB resta ottimo per analisi locali e notebook, ma qui PostgreSQL racconta meglio una pipeline data engineering completa.

### Perche Non Metabase

Metabase e un buon BI tool, ma per questo progetto Evidence e piu adatto:

- il report vive nel repository come codice;
- query, testo e grafici sono versionabili;
- il risultato e pubblicabile gratis su GitHub Pages;
- e piu coerente con un portfolio pubblico.

---

## Dataset

### Fonte Ranking

La classifica giornaliera Italia viene letta da:

```text
https://kworb.net/spotify/country/it_daily.html
```

Kworb viene usato come mirror pubblico della chart Spotify. Il progetto documenta chiaramente questa scelta:

- Kworb: posizione, stream, variazione, giorni in classifica, peak rank.
- Spotify Web API: metadati brano, album, artisti, durata, explicit, immagini e link.

### Fonte Metadati

La Spotify Web API viene usata con **Client Credentials Flow**, quindi senza login utente.

Endpoint principale:

```text
GET /v1/search
```

Per ogni brano in classifica, la pipeline cerca:

```text
track:<track_name> artist:<main_artist>
```

con `market=IT`.

### Tabelle Raw Principali

| Tabella | Descrizione |
|---|---|
| `spotify_raw.italy_daily_chart` | Top 200 giornaliera Italia con ranking e stream |
| `spotify_raw.italy_daily_chart__artist_names` | Nomi artisti normalizzati dalla chart |
| `spotify_raw.italy_daily_chart__artist_ids` | ID artisti normalizzati dalla chart |
| `spotify_raw.italy_daily_track_details` | Metadati Spotify dei brani arricchiti |
| `spotify_raw.italy_daily_track_details__artists` | Artisti dei brani arricchiti |
| `spotify_raw.italy_daily_track_details__album__images` | Copertine album |

Nel test locale piu recente:

| Tabella | Righe |
|---|---:|
| `italy_daily_chart` | 200 |
| `italy_daily_track_details` | 199 |

---

## Struttura Del Progetto

```text
spotify-analytics/
├── docker-compose.yaml
├── Dockerfile
├── requirements.txt
├── init-db.sql
├── .env                         # locale, non committare
├── .gitignore
│
├── airflow/
│   ├── dags/
│   │   ├── hello_spotify_dag.py
│   │   └── spotify_extract_dag.py
│   ├── config/                  # generata, ignorata
│   ├── logs/                    # generata, ignorata
│   └── plugins/
│
├── dlt/
│   ├── spotify_pipeline.py
│   ├── spotify_source.py
│   └── .dlt/
│       └── secrets.toml         # locale, non committare
│
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── staging/
│       ├── intermediate/
│       └── marts/
├── evidence/
│   ├── pages/
│   │   └── index.md
│   ├── sources/
│   │   └── spotify_public/
│   │       └── connection.yaml
│   ├── evidence.config.yaml
│   └── package.json
├── data/
│   └── raw/                     # snapshot versionati per GitHub Actions
├── scripts/
│   ├── refresh_public_data.py
│   └── requirements-public.txt
├── docs/
│   └── spotify_data_catalog.md
│
Repository root:
└── .github/
    └── workflows/
        ├── spotify-update-data.yml
        └── spotify-deploy-evidence.yml
```

---

## Configurazione Locale

### 1. Avviare Docker Compose

Da `spotify-analytics/`:

```powershell
docker compose up -d
```

Airflow sara disponibile su:

```text
http://localhost:8080
```

Credenziali locali:

```text
username: airflow
password: airflow
```

### 2. Database PostgreSQL

Il container PostgreSQL contiene:

```text
database Airflow metadata: airflow
database analytics: spotify_db
```

`init-db.sql` crea il database analytics:

```sql
CREATE DATABASE spotify_db;
GRANT ALL PRIVILEGES ON DATABASE spotify_db TO airflow;
```

### 3. Variabili E Secret Locali

Nel file `.env` locale:

```env
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_SPOTIFY_DB=spotify_db
```

Nel file `dlt/.dlt/secrets.toml` locale:

```toml
[spotify]
client_id = "your_client_id_here"
client_secret = "your_client_secret_here"

[destination.postgres.credentials]
database = "spotify_db"
username = "airflow"
password = "airflow"
host = "postgres"
port = 5432
```

Questi file non devono essere pubblicati su GitHub.

---

## Pipeline dlt

File principale:

```text
dlt/spotify_pipeline.py
```

Responsabilita:

- inizializza la pipeline dlt;
- usa destinazione PostgreSQL;
- salva i dati nello schema `spotify_raw`;
- richiama la source definita in `spotify_source.py`.

Source:

```text
dlt/spotify_source.py
```

Risorse dlt:

| Resource | Descrizione |
|---|---|
| `italy_daily_chart` | Estrae la Top 200 giornaliera Italia |
| `italy_daily_track_details` | Arricchisce la chart con metadati Spotify |

Esecuzione manuale nel container:

```powershell
docker compose run --rm airflow-cli bash -c "cd /opt/airflow/dlt && python spotify_pipeline.py"
```

---

## Airflow

DAG principale:

```text
airflow/dags/spotify_extract_dag.py
```

Il DAG:

- si chiama `spotify_extract`;
- ha schedule giornaliera `@daily`;
- esegue `spotify_pipeline.py`;
- carica i dati raw in PostgreSQL.

Comando di test:

```powershell
docker compose run --rm airflow-cli airflow dags test spotify_extract 2026-05-19
```

---

## Piano dbt

Il progetto dbt e inizializzato in:

```text
dbt/
```

Il profilo usa le variabili ambiente del compose:

```text
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_SPOTIFY_DB=spotify_db
```

Gli output sono separati in schemi PostgreSQL dedicati:

```text
spotify_staging
spotify_intermediate
spotify_marts
```

Modelli creati:

```text
dbt/models/staging/
├── stg_italy_daily_chart.sql
├── stg_italy_daily_track_details.sql
├── stg_italy_daily_track_artists.sql
└── stg_italy_daily_album_images.sql

dbt/models/intermediate/
└── int_italy_chart_enriched.sql

dbt/models/marts/
├── mart_top_songs_italy.sql
├── mart_top_artists_italy.sql
├── mart_album_release_analysis.sql
└── mart_chart_momentum.sql
```

Esecuzione manuale nel container:

```powershell
docker compose run --rm airflow-cli bash -c "cd /opt/airflow/dbt && DBT_PROFILES_DIR=/opt/airflow/dbt dbt build"
```

Airflow include anche il DAG manuale:

```text
spotify_transform
```

Metriche principali:

| Metrica | Logica |
|---|---|
| `streams` | stream giornalieri |
| `streams_share` | stream del brano / stream totali Top 200 |
| `rank_bucket` | Top 10, Top 50, Top 100, Top 200 |
| `is_collaboration` | piu di un artista associato |
| `duration_minutes` | `duration_ms / 60000.0` |
| `release_year` | anno da `album__release_date` |
| `days_on_chart` | persistenza in classifica |

---

## Dashboard Evidence

La dashboard Evidence e inizializzata in:

```text
evidence/
```

In locale puo essere avviata via Docker:

```powershell
docker compose --profile evidence up evidence
```

URL:

```text
http://localhost:3000/Portfolio
```

La sorgente Evidence `spotify_public` legge i CSV pubblicabili generati da:

```text
scripts/refresh_public_data.py
```

Il report locale e il report GitHub Pages usano gli stessi artefatti CSV. PostgreSQL resta il warehouse locale per dimostrare dlt e dbt, ma non e necessario per servire il sito statico.

Domande da mostrare nel portfolio:

1. Quali sono i brani piu ascoltati oggi in Italia?
2. Quali artisti generano piu stream nella Top 200?
3. Quanto e concentrata la classifica sui primi 10 brani?
4. Quali brani sono in crescita o in calo?
5. Quali album o singoli dominano la chart?
6. Quanto pesano le collaborazioni?
7. Che quota della Top 200 contiene brani explicit?
8. Quanto sono recenti le release presenti in classifica?

Visualizzazioni consigliate:

| Vista | Grafico |
|---|---|
| Top songs | tabella con rank, stream, artisti, album, copertina |
| Stream distribution | bar chart o line chart per rank |
| Top artists | bar chart per stream aggregati |
| Chart momentum | tabella/grafico con rank change e streams change |
| Release analysis | istogramma per anno di uscita |
| Explicit share | KPI + donut/bar |

---

## GitHub Automation Gratuita

Airflow resta locale per dimostrare orchestrazione. GitHub Actions gestisce il refresh automatico pubblico.

Workflow:

```text
.github/workflows/spotify-update-data.yml
```

Responsabilita:

- parte ogni giorno con cron;
- legge `SPOTIFY_CLIENT_ID` e `SPOTIFY_CLIENT_SECRET` dai GitHub Secrets;
- esegue uno script Python leggero;
- salva snapshot raw in `data/raw/`;
- aggiorna i CSV Evidence in `evidence/sources/spotify_public/`;
- committa i dataset aggiornati;
- builda Evidence;
- pubblica il sito su GitHub Pages nello stesso run.

Workflow deploy:

```text
.github/workflows/spotify-deploy-evidence.yml
```

Responsabilita:

- builda Evidence;
- pubblica il sito su GitHub Pages quando cambiano codice, pagine o configurazione Evidence.

Secret da configurare su GitHub:

```text
SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET
```

---

## Limitazioni Note

| Limite | Impatto |
|---|---|
| Audio features non disponibili per nuove app | niente danceability, energy, valence, tempo |
| Popularity non affidabile nei test attuali | usare stream e ranking come metriche principali |
| Generi artista non affidabili | non costruire analisi centrali sui generi |
| GitHub Actions non raggiunge PostgreSQL locale | usare file CSV/Parquet per il report pubblico |
| Arricchimento via Search API | possibile mismatch o mancato match per qualche brano |

Queste limitazioni non indeboliscono il progetto: lo rendono piu realistico. Un buon portfolio mostra anche la capacita di adattare l'architettura ai vincoli reali delle API.

---

## Roadmap

### Completato

- [x] Scelta PostgreSQL come warehouse locale
- [x] Setup Docker Compose con Airflow e PostgreSQL
- [x] Creazione database `spotify_db`
- [x] Struttura pulita `airflow/dags` e `dlt/`
- [x] DAG Airflow visibile in UI
- [x] Pipeline dlt funzionante verso PostgreSQL
- [x] Estrazione Top 200 Italia
- [x] Arricchimento metadati tramite Spotify Web API Search
- [x] Data catalog aggiornato
- [x] Inizializzazione progetto dbt
- [x] Configurazione profilo dbt per PostgreSQL
- [x] Creazione modelli staging
- [x] Creazione modello intermediate con join chart + metadati
- [x] Creazione mart analytics
- [x] Aggiunta test dbt
- [x] Creazione dashboard Evidence
- [x] Creazione script GitHub Actions per refresh gratuito
- [x] Configurazione deploy Evidence su GitHub Pages
- [x] Configurazione secret GitHub `SPOTIFY_CLIENT_ID` e `SPOTIFY_CLIENT_SECRET`
- [x] Abilitazione GitHub Pages con sorgente GitHub Actions
- [x] Esecuzione workflow completo refresh + deploy
- [x] Pubblicazione dashboard su `https://ludovicofonti.github.io/Portfolio_Ludovico_Fonti/`

### Prossimi Step

- [ ] Conservare piu snapshot giornalieri per analisi storiche
- [ ] Aggiungere trend temporali reali nel report Evidence
- [ ] Integrare alert o summary automatici sui cambiamenti piu rilevanti

---

## Fonti

- [Kworb Spotify Daily Italy](https://kworb.net/spotify/country/it_daily.html)
- [Spotify Web API - Search](https://developer.spotify.com/documentation/web-api/reference/search)
- [Spotify Web API - Get Track](https://developer.spotify.com/documentation/web-api/reference/get-track)
- [Spotify Developer Blog - Changes to the Web API, 2024-11-27](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)
- [Airflow Docker Compose Quickstart](https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html)
- [dlt Documentation](https://dlthub.com/docs)
- [dbt PostgreSQL Setup](https://docs.getdbt.com/docs/core/connect-data-platform/postgres-setup)
- [Evidence Documentation](https://docs.evidence.dev/)
