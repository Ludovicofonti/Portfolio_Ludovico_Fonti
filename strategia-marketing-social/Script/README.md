# Documentazione Tecnica — Strategia Marketing e Analisi Social

## Linguaggio e Librerie

| Componente | Strumento |
|---|---|
| Linguaggio | Python 3 |
| Manipolazione dati | `pandas`, `numpy` |
| Visualizzazione | `matplotlib`, `wordcloud` |
| NLP / Sentiment | `nltk` (VADER, stopwords) |
| Text processing | `re`, `collections.Counter`, `urllib.parse` |

## Struttura dello Script

Lo script `analisi_strategia_marketing.py` esegue un'analisi multi-canale delle performance digitali dell'azienda Nuova Comes, articolata in 7 moduli indipendenti orchestrati dal `main()`.

### 1. EDA Contatti HubSpot (`eda_contatti`)

- Input: file Excel del database contatti HubSpot (periodo: ottobre 2023 – ottobre 2024).
- Quattro grafici a barre (subplot 2×2) per le distribuzioni di:
  - Città di provenienza
  - Tipologia contatto
  - Fase del ciclo di vita
  - Fonte record

### 2. Analisi Sorgenti di Traffico Web (`analisi_traffico`)

- Estrazione del dominio dalle colonne URL del dataset HubSpot:
  - Prima pagina visitata
  - Primo sito di riferimento
  - Ultima pagina visualizzata
  - Ultimo sito di riferimento
- **Grafici a barre** (2×2) con il conteggio per dominio.
- **Grafici a torta** (2×2) con raggruppamento delle sorgenti sotto soglia (< 10 occorrenze → "Altro").
- Esportazione della tabella riepilogativa in Excel (`riepilogo_sorgenti.xlsx`).

### 3. Tipologie di Intervento (`analisi_interventi`)

- Parsing del campo multi-valore `Tipologia intervento` (separatore `;`).
- Conteggio delle occorrenze per ciascuna tipologia tramite `Counter`.

### 4. Sentiment Analysis (`sentiment_analysis`)

- Algoritmo: **VADER** (Valence Aware Dictionary and sEntiment Reasoner) di NLTK.
- Classificazione in base al compound score:
  - Compound > 0.05 → Positivo
  - Compound < −0.05 → Negativo
  - Altrimenti → Neutro
- Applicata a due set di recensioni:
  - **Facebook** (15 commenti, hardcoded nello script)
  - **Google Maps** (31 recensioni, hardcoded nello script)
- Per ciascuna fonte: bar chart della distribuzione sentiment + istogramma del compound score.

### 5. Text Mining (`text_mining`)

- Aggregazione di tutte le recensioni (Facebook + Google Maps).
- **Word Cloud**: generata con rimozione delle stop-words italiane + lista custom di parole non informative.
- **Frequenza parole**: bar chart delle parole con più di 3 occorrenze, dopo pulizia di punteggiatura e stop-words.

### 6. Analisi Voti Google Maps (`analisi_voti`)

- Dataset di 81 voti (scala 1–5), hardcoded nello script.
- Statistiche descrittive: media, mediana, moda.
- Distribuzione dei voti (bar chart).

### 7. Analisi Campagne Meta (`analisi_meta`)

- Input: file Excel con i dati delle campagne pubblicitarie Meta (Facebook e Instagram).
- Estrazione della piattaforma (`FB` / `IG`) dal nome della campagna tramite regex.
- Calcolo della **durata** di ogni campagna in giorni.
- **CTR medio ponderato** per piattaforma (ponderato per la durata della campagna).
- **Metriche aggregate** per piattaforma: Impressions, Reach, Frequency, Link clicks.
- Grafici: CTR ponderato (barre) + Impressions vs Reach (barre raggruppate).

## Dati di Input

I dati sono organizzati nella sottocartella `Corretto/`:

| Sottocartella | File | Descrizione |
|---|---|---|
| `HUBSPOT/` | Database contatti HubSpot (.xlsx) | Contatti, sorgenti traffico, tipologie intervento |
| `META/` | Campagne Meta (.xlsx) | Campagne FB/IG con metriche di performance |

Le recensioni Facebook e Google Maps sono embedded direttamente nello script come liste Python.

## Output

Tutti gli output grafici vengono salvati nella cartella `output/` (creata automaticamente):

| File | Contenuto |
|---|---|
| `01_eda_contatti_hubspot.png` | EDA contatti HubSpot |
| `02_sorgenti_traffico_barre.png` | Sorgenti traffico (barre) |
| `03_sorgenti_traffico_torta.png` | Sorgenti traffico (torta) |
| `04_sentiment_facebook.png` | Sentiment analysis Facebook |
| `04_sentiment_google_maps.png` | Sentiment analysis Google Maps |
| `05_wordcloud.png` | Word cloud recensioni aggregate |
| `06_frequenza_parole.png` | Frequenza parole chiave |
| `07_distribuzione_voti.png` | Distribuzione voti Google Maps |
| `08_campagne_meta.png` | Performance campagne Meta |
| `riepilogo_sorgenti.xlsx` | Tabella sorgenti traffico |

## File

| File | Descrizione |
|---|---|
| `analisi_strategia_marketing.py` | Script completo dell'analisi |
| `Corretto/HUBSPOT/` | Dati contatti HubSpot |
| `Corretto/META/` | Dati campagne Meta |
