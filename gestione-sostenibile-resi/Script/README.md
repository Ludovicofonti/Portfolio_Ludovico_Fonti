# Documentazione Tecnica — Gestione Sostenibile dei Resi

## Linguaggio e Librerie

| Componente | Strumento |
|---|---|
| Linguaggio | Python 3 |
| Manipolazione dati | `pandas`, `numpy` |
| Visualizzazione | `matplotlib`, `seaborn` |
| Modellazione | `scikit-learn` (LinearRegression) |
| Mappe interattive | `folium`, `geopy` |

## Struttura dello Script

Lo script `analisi_gestione_resi.py` è organizzato in 5 sezioni principali, ciascuna implementata come funzione indipendente richiamata dal `main()`.

### 1. Caricamento e Pulizia Dati (`load_data`)

- Lettura del file `dati_resi_distanze.csv` (separatore `;`, formato numerico europeo con virgola).
- Conversione delle colonne numeriche (`weight`, `emission`, `price`, `distance`) dal formato europeo (virgola → punto).
- Parsing delle date (`creation_date`) e rimozione di colonne non necessarie.
- Eliminazione delle righe con valori mancanti nelle variabili critiche (`emission`, `distance`, `weight`).
- Calcolo del rimborso in EUR: `refund_eur = total_refund × exchange_rate`.
- Estrazione di anno e mese dalla data di creazione.

### 2. Analisi Esplorativa (EDA)

Cinque visualizzazioni per comprendere la struttura dei dati:

| Funzione | Output |
|---|---|
| `plot_items_per_return` | Distribuzione del numero di item per reso (bar chart + media) |
| `plot_emissions_by_country` | Top 15 paesi per emissioni totali e medie (barh charts) |
| `plot_emission_distribution` | Istogrammi di emissioni CO₂ e distanze dal centro logistico |
| `plot_correlation_matrix` | Heatmap di correlazione tra `emission`, `distance`, `weight`, `quantity`, `refund_eur` |
| `plot_temporal_trend` | Andamento mensile con doppio asse: n. resi (barre) ed emissioni totali (linea) |

### 3. Modello di Regressione Lineare Multipla (`build_regression_model`)

- **Target**: `emission` (kg CO₂ per reso)
- **Features**: `distance` (km), `weight` (kg)
- **Split**: 80% train / 20% test (`random_state=42`)
- **Algoritmo**: `LinearRegression` di scikit-learn
- **Metriche calcolate sul test set**:
  - R² (coefficiente di determinazione)
  - MAE (Mean Absolute Error)
  - RMSE (Root Mean Squared Error)
- **Visualizzazioni diagnostiche**:
  - Scatter plot predizioni vs valori reali con linea di predizione perfetta
  - Istogramma dei residui

### 4. Mappa Interattiva delle Emissioni (`create_emission_map`)

- Geocodifica delle città tramite `geopy.Nominatim` con caching locale (`city_coords.pkl`) per evitare chiamate ripetute.
- Aggregazione delle emissioni per città (totale, conteggio, media).
- Generazione di una mappa `folium` con `CircleMarker` proporzionali alle emissioni totali.
- Output: file HTML interattivo (`mappa_emissioni.html`).

### 5. Scenari di Riduzione Emissioni (`analyze_reduction_scenarios`)

Tre scenari simulati per stimare il potenziale di riduzione:

| Scenario | Logica |
|---|---|
| Riduzione 10% resi (più distanti) | Eliminazione del 10% dei resi con maggiore distanza |
| Centro resi locale EU | Emissioni dimezzate per i paesi europei (simulazione hub locale) |
| Consolidamento spedizioni | Riduzione del 30% delle emissioni per resi multipli dalla stessa città |

Ogni scenario è confrontato graficamente con la situazione attuale tramite bar chart.

## File

| File | Descrizione |
|---|---|
| `analisi_gestione_resi.py` | Script completo dell'analisi |
| `dati_resi_distanze.csv` | Dataset con 7.990 resi e relative emissioni calcolate via EcoTransit |
| `output/` | Directory generata automaticamente con grafici (PNG) e mappa interattiva (HTML) |
