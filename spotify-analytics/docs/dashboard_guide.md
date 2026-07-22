# Guida alla dashboard Looker Studio

[**Apri il report Spotify Italy Analytics →**](https://datastudio.google.com/reporting/33349080-c859-45c9-859f-23671c6b0cc8)

Questa guida descrive tutte le visualizzazioni uniche presenti nel report. Per ogni
elemento sono indicate la domanda di business, la vista BigQuery, la configurazione in
Looker Studio e il significato analitico.

## Controlli globali

- Paese predefinito: `IT`.
- Intervallo date predefinito: tutta la storia osservata disponibile.
- Percentuali formattate con due decimali.
- Tooltip con nome dell'entità, valore, data e segmentazione rilevante.
- Ordinamento cronologico crescente per tutti i grafici temporali.
- Le osservazioni mancanti devono rimanere vuote: non devono diventare giornate con
  zero stream.
- I grafici definiti “ultimo snapshot” devono filtrare `chart_date` alla data massima
  disponibile.

## Pagina 1 — Panoramica del mercato

La pagina risponde alla domanda generale:

> Quanto vale il mercato osservato della Top 200 Spotify Italia, quanto è concentrato e
> quale quota della domanda proviene dalle nuove uscite rispetto al catalogo?

### Ultimo Aggiornamento

- **Tipo:** scorecard.
- **Vista:** `rpt_market_overview_daily`.
- **Campo:** `MAX(chart_date)`.

**Domanda di business:** quanto sono aggiornati i dati?

**Significato:** mostra la data più recente caricata e validata. È il primo controllo da
effettuare prima di interpretare qualsiasi altro indicatore.

### Stream Giornalieri Medi

- **Tipo:** scorecard.
- **Vista:** `rpt_market_overview_daily`.
- **Campo:** `AVG(streams)`.

**Domanda di business:** qual è il livello normale di domanda giornaliera della Top 200?

**Significato:** rappresenta la media degli stream complessivi giornalieri nel periodo
selezionato e costituisce il valore di riferimento per valutare picchi o rallentamenti.

### Variazione Giornaliera Stream

- **Tipo:** scorecard.
- **Vista:** `rpt_market_overview_daily`.
- **Campo:** `AVG(streams_change)`.

**Domanda di business:** il consumo complessivo sta crescendo o diminuendo?

**Significato:** misura la variazione media giornaliera degli stream della Top 200. Un
valore positivo indica espansione; un valore negativo indica contrazione. Nel layout
attuale la scorecard compare due volte: deve rimanerne una sola.

### Quota Stream Top 10

- **Tipo:** scorecard.
- **Vista:** `rpt_market_overview_daily`.
- **Campo:** `AVG(top_10_stream_share)`.

**Domanda di business:** quanta domanda è controllata dai dieci brani principali?

**Significato:** una quota in crescita segnala maggiore concentrazione dell'attenzione
sui vertici della classifica.

### Quota Stream Top 50

- **Tipo:** scorecard.
- **Vista:** `rpt_market_overview_daily`.
- **Campo:** `AVG(top_50_stream_share)`.

**Domanda di business:** quanto è profonda la domanda oltre i successi principali?

**Significato:** confrontata con la quota Top 10, permette di distinguere un mercato
dominato da pochi brani da uno con una fascia più ampia di hit rilevanti.

### Quota Collaborazioni

- **Tipo:** scorecard.
- **Vista:** `rpt_market_overview_daily`.
- **Campo:** `AVG(collaboration_share)`.

**Domanda di business:** quanto sono diffuse le release con più artisti?

**Significato:** è la percentuale dei brani in classifica attribuiti a più di un artista.
Descrive il formato del catalogo, non la quota di stream generata dalle collaborazioni.

### Quota Explicit

- **Tipo:** scorecard.
- **Vista:** `rpt_market_overview_daily`.
- **Campo:** `AVG(explicit_share)`.

**Domanda di business:** quanto è presente il contenuto explicit nella classifica?

**Significato:** indica la percentuale di brani contrassegnati come explicit nei
metadati Spotify e supporta valutazioni editoriali e di posizionamento del pubblico.

### Stream Top 200 nel Tempo

- **Tipo:** serie temporale con area.
- **Vista:** `rpt_market_overview_daily`.
- **Dimensione:** `chart_date`.
- **Metrica:** `SUM(streams)`.
- **Ordinamento:** `chart_date` crescente.
- **Filtro di validità consigliato:** `track_count >= 190` e `streams > 0`.

**Domanda di business:** la domanda complessiva della Top 200 cresce, rimane stabile o
si contrae nel tempo?

**Significato:** ogni punto rappresenta gli stream combinati dei brani osservati in una
giornata. Variazioni prolungate indicano un cambiamento di mercato; picchi isolati
possono dipendere da grandi release o stagionalità. Un valore zero segnala un problema
di acquisizione o copertura e non un reale azzeramento degli ascolti.

### Nuove Uscite vs Catalogo Consolidato

- **Tipo:** colonne impilate al 100%.
- **Vista:** `rpt_market_overview_daily`.
- **Dimensione:** `chart_date`.
- **Metriche:** `SUM(fresh_streams)`, `SUM(developing_streams)`,
  `SUM(catalog_streams)`.
- **Etichette:** “Release fino a 60 giorni”, “Release da 61 a 180 giorni”,
  “Release oltre 180 giorni”.
- **Ordinamento:** `chart_date` crescente.

**Domanda di business:** la domanda corrente è trainata dalle nuove uscite o dal
catalogo consolidato?

**Significato:** ogni colonna divide gli stream giornalieri in tre fasce di anzianità.
Una crescita della quota fresh indica un mercato guidato dalle release; una crescita
del catalogo segnala consumo evergreen. Il grafico deve usare direttamente le tre
metriche, senza categoria “Altri”, così ogni data totalizza il 100%.

## Pagina 2 — Dinamiche di artisti e brani

La pagina risponde alla domanda generale:

> Quali artisti concentrano l'attenzione, se il vantaggio dipende da una singola hit o
> dall'ampiezza del catalogo, e quali brani combinano longevità e intensità?

### Top 15 Artisti per Stream

- **Tipo:** barre orizzontali.
- **Vista:** `rpt_artist_performance_daily`.
- **Dimensione:** `artist_name`.
- **Metrica:** `SUM(streams)`.
- **Limite:** 15 righe.
- **Ordinamento:** `SUM(streams)` decrescente.
- **Intervallo:** aggregazione sul periodo selezionato.

**Domanda di business:** quali artisti hanno generato più stream nel periodo?

**Significato:** misura la domanda cumulata e non soltanto il miglior piazzamento. Nello
snapshot condiviso Geolier guida con circa 83,4 milioni di stream, seguito da Shiva e
Sfera Ebbasta. Un catalogo persistente può quindi superare una hit breve ma intensa.

### Ampiezza Catalogo vs Quota di Mercato

- **Tipo:** grafico a bolle.
- **Vista:** `rpt_artist_performance_daily`.
- **Dimensione:** `artist_name`.
- **Asse X:** `MAX(track_count)`.
- **Asse Y:** `MAX(market_share)`.
- **Dimensione bolla:** `MAX(streams)`.
- **Colore:** `artist_segment` (`Top 5`, `Top 15`, `Long tail`).
- **Intervallo:** ultimo snapshot.

**Domanda di business:** la quota di mercato di un artista dipende dall'ampiezza del
catalogo o da pochi brani dominanti?

**Significato:** l'area in alto a destra identifica artisti con molti brani e quota
elevata, quindi forza di catalogo. In alto a sinistra si trovano artisti molto
concentrati su poche hit. In basso a destra sono presenti cataloghi ampi ma con minore
efficienza per brano. La dimensione della bolla mostra il contributo assoluto di stream.

### Quota di Mercato degli Artisti nel Tempo

- **Tipo:** serie temporale multilinea.
- **Vista:** `rpt_artist_performance_daily`.
- **Dimensione:** `chart_date`.
- **Suddivisione:** `artist_name`.
- **Metrica:** `MAX(market_share)`.
- **Limite serie:** cinque artisti, selezionati per stream complessivi nel periodo.
- **Ordinamento:** `chart_date` crescente.

**Domanda di business:** quali artisti guadagnano o perdono attenzione e quanto durano
i cambi di leadership?

**Significato:** ogni linea rappresenta la quota giornaliera dell'artista sugli stream
totali della Top 200. Movimenti paralleli possono dipendere dal mercato complessivo;
un'impennata isolata è più probabilmente legata a una release. Lo screenshot mostra un
picco temporaneo di ANNA a metà luglio: i giorni successivi permettono di distinguere
un lancio da una crescita strutturale.

### Longevità vs Intensità

- **Tipo:** dispersione a bolle.
- **Vista:** `rpt_track_opportunities_daily`.
- **Dimensione:** `chart_track_id`.
- **Tooltip:** `track_name`, `artist_names_text`.
- **Asse X:** `days_on_chart`.
- **Asse Y:** `streams`.
- **Dimensione bolla:** `movement_size`.
- **Colore facoltativo:** `release_stage`.
- **Intervallo:** ultimo snapshot.

**Domanda di business:** quali brani combinano permanenza in classifica e consumo
corrente, e quali nuove uscite mostrano intensità da breakout?

**Significato:** in alto a sinistra si trovano brani nuovi e intensi, candidati ad
accelerazione. In alto a destra si trovano asset evergreen con domanda ancora elevata.
In basso a destra emerge il catalogo longevo a intensità inferiore, adatto a un
mantenimento efficiente. La dimensione della bolla evidenzia i movimenti più rilevanti.

## Lettura dello snapshot condiviso

Gli screenshot forniti mostrano dati aggiornati al **20 luglio 2026**. I valori sono una
fotografia del periodo; il report cambia dopo ogni aggiornamento schedulato riuscito.

- Stream giornalieri medi: circa **16,8 milioni**.
- Variazione giornaliera media: circa **−126 mila stream**.
- Quota Top 10: **14,05%**.
- Quota Top 50: **43,88%**.
- Quota collaborazioni: **43,08%**.
- Quota explicit: **34,41%**.
- Il grafico degli artisti suggerisce una relazione positiva tra ampiezza catalogo e
  quota di mercato, con una long tail concentrata sotto circa l'1%.
- La maggior parte dei picchi di intensità appartiene a brani recenti; un gruppo più
  ristretto mantiene stream significativi per periodi molto lunghi.

Queste evidenze sono descrittive e non causali. Calendario delle release,
collaborazioni e snapshot mancanti devono essere verificati prima di prendere decisioni
di allocazione del budget.
