# Spotify Data Catalog

Questo documento descrive i dati scaricati dalla pipeline Spotify del progetto e chiarisce quali analisi sono realistiche usando soluzioni gratuite.

Data ultimo aggiornamento locale: 2026-05-19.

## Obiettivo Del Dataset

L'obiettivo non e piu analizzare tracce cercate per genere, ma costruire un dataset sui **brani piu ascoltati in Italia**.

La pipeline scarica:

1. La classifica giornaliera Spotify Italia, con posizione e stream.
2. I metadati dei brani tramite Spotify Web API, usando la Search API come arricchimento.
3. Tabelle normalizzate in PostgreSQL tramite dlt.

Flusso attuale:

```text
Kworb Spotify Daily Italy chart
  -> parser Python
  -> dlt
  -> PostgreSQL
  -> schema spotify_raw

Spotify Web API Search
  -> arricchimento metadati traccia, album, artisti
  -> dlt
  -> PostgreSQL
  -> schema spotify_raw
```

Il DAG Airflow `spotify_extract` esegue:

```text
/opt/airflow/dlt/spotify_pipeline.py
```

e carica i dati nel database:

```text
database: spotify_db
schema: spotify_raw
```

## Perche Non Filtriamo Per Genere

La vecchia impostazione usava query come:

```text
genre:pop
genre:rock
genre:hip hop
```

Questo approccio e utile per creare un dataset dimostrativo, ma non risponde bene alla domanda:

> Quali sono i brani piu ascoltati in Italia?

Per una classifica nazionale bisogna partire da una fonte di ranking, non da una ricerca per genere. Per questo il dataset principale ora e la classifica giornaliera Italia.

## Fonte Della Classifica

La classifica viene letta da:

```text
https://kworb.net/spotify/country/it_daily.html
```

Kworb e usato come mirror pubblico consultabile della classifica Spotify giornaliera. La fonte ufficiale Spotify Charts e preferibile dal punto di vista concettuale, ma nei test locali il download diretto automatico non era disponibile senza passare da endpoint protetti o pagine HTML non direttamente consumabili.

Per il portfolio questo va documentato con trasparenza:

- **ranking e stream**: fonte chart pubblica Kworb;
- **metadati musicali**: Spotify Web API;
- **orchestrazione e storage**: Airflow, dlt, PostgreSQL;
- **trasformazioni analytics**: dbt;
- **dashboard**: Evidence.

## Tabelle Create

dlt normalizza automaticamente gli oggetti JSON annidati. Le tabelle principali sono:

| Tabella | Descrizione | Righe attese |
|---|---|---:|
| `spotify_raw.italy_daily_chart` | Classifica giornaliera Spotify Italia | 200 |
| `spotify_raw.italy_daily_chart__artist_ids` | Lista normalizzata degli ID artista presenti nella chart | variabile |
| `spotify_raw.italy_daily_chart__artist_names` | Lista normalizzata dei nomi artista presenti nella chart | variabile |
| `spotify_raw.italy_daily_track_details` | Metadati traccia ottenuti dalla Spotify Search API | circa 200 |
| `spotify_raw.italy_daily_track_details__artists` | Artisti collegati alle tracce arricchite | variabile |
| `spotify_raw.italy_daily_track_details__album__artists` | Artisti associati all'album | variabile |
| `spotify_raw.italy_daily_track_details__album__images` | Immagini degli album in diverse dimensioni | variabile |
| `spotify_raw._dlt_loads` | Metadata dei caricamenti dlt | tecnica |
| `spotify_raw._dlt_pipeline_state` | Stato interno della pipeline dlt | tecnica |
| `spotify_raw._dlt_version` | Versione schema dlt | tecnica |

Nel test locale piu recente la pipeline ha caricato:

| Tabella | Righe |
|---|---:|
| `italy_daily_chart` | 200 |
| `italy_daily_track_details` | 199 |

Una differenza di poche righe e normale: l'arricchimento usa ricerca testuale `track + artist`, quindi puo non trovare un match esatto per ogni elemento della chart.

## Tabella `italy_daily_chart`

Ogni riga rappresenta una traccia nella classifica giornaliera Spotify Italia.

| Colonna | Tipo atteso | Descrizione | Esempio |
|---|---|---|---|
| `chart_date` | date/text | Data della classifica | `2026-05-17` |
| `country` | text | Codice paese | `IT` |
| `country_name` | text | Nome paese | `Italy` |
| `chart_source` | text | Fonte tecnica della chart | `kworb_spotify_daily` |
| `rank` | integer | Posizione in classifica | `1` |
| `rank_change` | text | Variazione posizione rispetto al giorno precedente | `+2`, `-1`, `=` |
| `track_id` | text | ID traccia letto dalla chart | `...` |
| `track_name` | text | Titolo del brano | `OSSESSIONE` |
| `artist_ids` | array/list | ID artisti nella chart | lista |
| `artist_names` | array/list | Nomi artisti nella chart | lista |
| `artist_names_text` | text | Artisti concatenati | `Shiva, Geolier` |
| `days_on_chart` | integer | Giorni in classifica | `14` |
| `peak_rank` | integer | Miglior posizione raggiunta | `1` |
| `peak_count_text` | text | Informazione testuale sul picco | `x3` |
| `streams` | integer | Stream del giorno | `309719` |
| `streams_change` | integer | Variazione stream giornaliera | `-12031` |
| `streams_7day` | integer | Stream ultimi 7 giorni | `1800000` |
| `streams_7day_change` | integer | Variazione stream ultimi 7 giorni | `250000` |
| `streams_total` | integer | Stream totali tracciati dalla chart | `12000000` |
| `kworb_track_url` | text | URL pagina traccia su Kworb | `https://kworb.net/spotify/track/...` |

### Esempi Reali Dal Test Locale

| Rank | Track | Artisti | Stream giornalieri |
|---:|---|---|---:|
| 1 | `OSSESSIONE` | `Samurai Jay` | 309719 |
| 2 | `Bad Bad Bad` | `Shiva, Geolier` | 249191 |
| 3 | `Obsessed` | `Shiva, ANNA` | 232076 |
| 4 | `LA TESTA GIRA` | `Fred De Palma, Anitta, Emis Killa` | 195601 |
| 5 | `CANZONE D'AMORE` | `Geolier` | 191917 |

## Tabella `italy_daily_track_details`

Questa tabella contiene il risultato dell'arricchimento con Spotify Web API Search. Ogni riga rappresenta il miglior match trovato per una traccia della chart.

| Colonna | Tipo atteso | Descrizione | Esempio |
|---|---|---|---|
| `id` | text | ID Spotify della traccia trovata tramite Search API | `...` |
| `name` | text | Titolo restituito da Spotify | `OSSESSIONE` |
| `type` | text | Tipo oggetto Spotify | `track` |
| `uri` | text | URI Spotify interno | `spotify:track:...` |
| `href` | text | URL API Spotify | `https://api.spotify.com/v1/tracks/...` |
| `external_urls__spotify` | text | Link pubblico Spotify | `https://open.spotify.com/track/...` |
| `external_ids__isrc` | text | Codice ISRC | `...` |
| `duration_ms` | integer | Durata in millisecondi | `188184` |
| `explicit` | boolean | Indica se il brano e esplicito | `true` / `false` |
| `disc_number` | integer | Numero disco | `1` |
| `track_number` | integer | Numero traccia nell'album | `1` |
| `is_local` | boolean | Indica se e una traccia locale | `false` |
| `is_playable` | boolean | Riproducibile nel mercato richiesto | `true` |
| `album__id` | text | ID album | `...` |
| `album__name` | text | Nome album/singolo | `Vangelo` |
| `album__album_type` | text | Tipo release | `single`, `album`, `compilation` |
| `album__release_date` | text | Data di uscita | `2026-04-10` |
| `album__release_date_precision` | text | Precisione data | `day`, `month`, `year` |
| `album__total_tracks` | integer | Numero tracce nella release | `1` |
| `album__external_urls__spotify` | text | Link pubblico album | `https://open.spotify.com/album/...` |
| `chart_track_id` | text | ID traccia letto dalla chart | `...` |
| `chart_date` | date/text | Data della chart | `2026-05-17` |
| `chart_country` | text | Paese della chart | `IT` |
| `chart_rank` | integer | Posizione nella chart | `1` |
| `chart_track_name` | text | Titolo nella chart | `OSSESSIONE` |
| `chart_artist_names_text` | text | Artisti nella chart | `Samurai Jay` |
| `chart_streams` | integer | Stream giornalieri nella chart | `309719` |
| `chart_streams_total` | integer | Stream totali nella chart | `12000000` |

## Tabelle Figlie

### `italy_daily_track_details__artists`

Contiene gli artisti collegati alla traccia arricchita da Spotify.

Relazione:

```text
italy_daily_track_details._dlt_id = italy_daily_track_details__artists._dlt_parent_id
```

Campi principali:

| Colonna | Descrizione |
|---|---|
| `id` | ID Spotify artista |
| `name` | Nome artista |
| `type` | Tipo oggetto, di solito `artist` |
| `uri` | URI Spotify artista |
| `href` | URL API artista |
| `external_urls__spotify` | Link pubblico Spotify artista |
| `_dlt_parent_id` | ID tecnico della traccia padre |
| `_dlt_list_idx` | Posizione dell'artista nella lista |
| `_dlt_id` | ID tecnico dlt |

### `italy_daily_track_details__album__images`

Contiene le immagini dell'album in piu risoluzioni.

| Colonna | Descrizione |
|---|---|
| `url` | URL immagine album |
| `height` | Altezza in pixel |
| `width` | Larghezza in pixel |
| `_dlt_parent_id` | ID tecnico della traccia padre |
| `_dlt_list_idx` | Posizione immagine nella lista |
| `_dlt_id` | ID tecnico dlt |

Questa tabella e utile per Evidence, perche permette di mostrare copertine album nella dashboard.

## Campi Non Disponibili o Limitati

Alcuni campi molto usati nei vecchi tutorial Spotify non sono affidabili o disponibili per nuove app.

| Campo / Endpoint | Stato osservato | Impatto |
|---|---|---|
| `audio_features` | `403 Forbidden` | Non possiamo usare danceability, energy, valence, tempo, acousticness |
| `audio_analysis` | limitato/deprecato per nuove app | Non usarlo nel progetto |
| `recommendations` | limitato/deprecato per nuove app | Non usarlo nel progetto |
| `track.popularity` | non affidabile nei test attuali | Evitare analisi basate su popularity |
| `artist.popularity` | non affidabile nei test attuali | Evitare ranking artisti per popularity |
| `artist.genres` | non affidabile nei test attuali | Non usare come dimensione principale |
| `artist.followers` | non affidabile nei test attuali | Non usare analisi su follower |

Spotify ha annunciato restrizioni a diversi endpoint e campi dal 27 novembre 2024. Questo spiega perche molti esempi online basati su audio features o popularity non sono piu replicabili con nuove app.

Fonte: [Spotify Developer Blog - Changes to the Web API](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)

## Dati Gratuiti Che Possiamo Ancora Scaricare

### 1. Classifiche Pubbliche

La classifica Italia e il cuore del progetto.

| Dato | Uso nel portfolio |
|---|---|
| rank giornaliero | top brani Italia |
| stream giornalieri | metriche quantitative reali |
| variazione rank | trend e momentum |
| giorni in classifica | persistenza del successo |
| peak rank | miglior risultato raggiunto |
| stream ultimi 7 giorni | confronto breve periodo |
| stream totali | successo cumulativo |

### 2. Spotify Search API

Endpoint:

```text
GET /v1/search
```

Dati ottenibili:

| Tipo ricerca | Dati utili | Uso nel portfolio |
|---|---|---|
| `track` | tracce, album, artisti, durata, explicit, release date, ISRC, immagini album | arricchimento chart |
| `artist` | artisti trovati da query testuale | estensione anagrafica |
| `album` | album trovati da query testuale | analisi release/catalogo |
| `playlist` | playlist pubbliche cercabili, con limitazioni da verificare | possibile estensione |

Fonte: [Spotify Web API - Search](https://developer.spotify.com/documentation/web-api/reference/search)

### 3. Track, Album E Artist Metadata

I metadati piu utili sono:

| Dato | Uso |
|---|---|
| durata | distribuzione durata brani in classifica |
| explicit | quota di brani espliciti nella top 200 |
| album | analisi album/singolo/compilation |
| release date | eta dei brani in classifica |
| artisti | ranking artisti per presenze e stream |
| ISRC | deduplica registrazioni |
| immagini album | dashboard Evidence |
| link Spotify | report navigabile |

## Domande Analitiche Realistiche

Con il nuovo dataset, le domande migliori sono:

1. Quali sono i brani piu ascoltati oggi in Italia?
2. Quali artisti generano piu stream nella Top 200?
3. Quanti stream separano la posizione 1 dalla posizione 10, 50, 100 e 200?
4. Quali brani hanno piu giorni in classifica?
5. Quali brani sono in crescita o in calo rispetto al giorno precedente?
6. Quali album o singoli dominano la classifica?
7. Quanto pesano le collaborazioni tra piu artisti nella Top 200?
8. Che percentuale dei brani in classifica e explicit?
9. Qual e la distribuzione della durata dei brani piu ascoltati?
10. Quanto sono recenti le release presenti nella chart?

## Implicazioni Per dbt

I primi modelli dbt consigliati sono:

```text
stg_italy_daily_chart
stg_italy_daily_track_details
stg_italy_daily_track_artists
int_italy_chart_enriched
mart_top_songs_italy
mart_top_artists_italy
mart_album_release_analysis
mart_chart_momentum
```

Metriche chiave:

| Metrica | Formula / logica |
|---|---|
| `streams` | stream giornalieri dalla chart |
| `streams_share` | stream brano / stream totali Top 200 |
| `rank_bucket` | Top 10, Top 50, Top 100, Top 200 |
| `is_collaboration` | numero artisti > 1 |
| `duration_minutes` | `duration_ms / 60000.0` |
| `release_year` | anno da `album__release_date` |
| `days_since_release` | data chart - release date |

## Nota Su GitHub Actions

Su GitHub Actions non conviene usare il PostgreSQL locale del PC. Il runner GitHub gira su server esterni e non puo raggiungere il database locale.

Strategia gratuita implementata:

```text
Locale:
Airflow + dlt + PostgreSQL + dbt

GitHub:
workflow schedulato
  -> scripts/refresh_public_data.py
  -> snapshot raw in data/raw/
  -> CSV in evidence/sources/spotify_public/
  -> Evidence
  -> GitHub Pages
```

Evidence legge la source CSV `spotify_public`, quindi il sito statico non dipende dal PostgreSQL locale. Il workflow `spotify-update-data.yml` aggiorna giornalmente i dati, esegue build Evidence e pubblica il report tramite GitHub Pages nello stesso run.

Il workflow separato `spotify-deploy-evidence.yml` resta utile quando cambiano solo pagine, configurazione o dipendenze Evidence. Questa separazione evita di dipendere da un secondo workflow avviato dal commit del bot, perche GitHub Actions non rilancia automaticamente altri workflow quando il push e fatto con `GITHUB_TOKEN`.

## Fonti

- [Kworb Spotify Daily Italy](https://kworb.net/spotify/country/it_daily.html)
- [Spotify Web API - Search](https://developer.spotify.com/documentation/web-api/reference/search)
- [Spotify Web API - Get Track](https://developer.spotify.com/documentation/web-api/reference/get-track)
- [Spotify Web API - Get Album](https://developer.spotify.com/documentation/web-api/reference/get-an-album)
- [Spotify Web API - Get Artist](https://developer.spotify.com/documentation/web-api/reference/get-an-artist)
- [Spotify Developer Blog - Changes to the Web API, 2024-11-27](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)
