# 🔧 Guida Tecnica — Script

## Struttura

```
Script/
├── main.py              # Pipeline completa (unico entry point)
├── syeewdataset.csv     # Dati di vendita (anonimizzati)
├── weather.csv          # Dati meteo giornalieri (anonimizzati)
└── economia.csv         # Indicatori macroeconomici mensili
```

## Dataset

| File | Granularità | Contenuto |
|------|-------------|-----------|
| `syeewdataset.csv` | Giornaliera × punto vendita × categoria | Fatturato netto, quantità, dimensione, giorni lavorativi |
| `weather.csv` | Giornaliera × località | Temperatura, umidità, precipitazioni |
| `economia.csv` | Mensile | Indice di fiducia consumatori, indice dei prezzi |

> ⚠️ I dati sono **anonimizzati**: ID clienti, CAP, coordinate e valori economici sono stati sostituiti o perturbati. La struttura e le relazioni tra i dati sono preservate.

## Architettura della Pipeline

La pipeline è organizzata in 6 sezioni all'interno di `main.py`:

### 1. Custom TSMixer

Estensione del modello `TSMixerModel` di Darts con **attivazione Mish** (al posto di ReLU). Mish fornisce un gradient flow più regolare e non presenta il problema del "dying neuron" tipico di ReLU.

```
TSMixerModel (Darts)
  └── CustomTSMixerModel
        └── _CustomTSMixerModule  ← sostituzione attivazione in tutti i blocchi
```

### 2. Data Integration

Merge di tre fonti dati su chiavi temporali e geografiche:
- **Vendite ↔ Meteo**: join su `(Date, Cap)` ↔ `(date, zip)`
- **Risultato ↔ Economia**: join su `(year, month)` per aggiungere indicatori mensili

### 3. TimeSeries & Preprocessing

- **Serie target**: `[Netto, Qta, Dim, Lav]` — raggruppate per `(idMatrice, idCat)` con covariate statiche `(TipoAttivita, Cap, TipoCalc)`
- **Covariate passate**: `[temp, precipitation, fiducia]` + festività italiane (auto-generate)
- **Scaling**: `Scaler` su target e covariate dinamiche, `StaticCovariatesTransformer` sulle statiche

### 4. Configurazione Modello

Parametri principali configurati in `DEFAULT_CONFIG`:

| Parametro | Valore | Descrizione |
|-----------|--------|-------------|
| `input_chunk_length` | 64 | Finestra di osservazione (giorni) |
| `output_chunk_length` | 32 | Orizzonte di previsione (giorni) |
| `hidden_size` | 32 | Dimensione layer nascosti |
| `num_blocks` | 4 | Blocchi mixer |
| `dropout` | 0.075 | Regolarizzazione |
| `likelihood` | Quantile Regression | Output probabilistico |

Encoding temporale: ciclico + datetime attributes + posizionale per catturare stagionalità a diverse scale.

### 5. Training & Prediction

- **Training**: split 60/40, EarlyStopping su `train_loss` (patience=20), accelerazione CUDA
- **Prediction**: previsioni per gruppo con MC Dropout (150 campioni) → output quantilico aggregato per mese

### 6. Hyperparameter Optimization

Tuning multi-obiettivo con **Optuna** (sampler NSGA-III):
- Obiettivi: minimizzare RMSE e MAE simultaneamente
- Spazio di ricerca: `hidden_size`, `batch_size`, `num_blocks`, `dropout`, `ff_size`

## Requisiti

```
darts
torch
pytorch-lightning
scikit-learn
pandas
numpy
optuna          # opzionale, solo per hyperparameter tuning
```

> Richiede una GPU CUDA per il training. Per eseguire su CPU, modificare `accelerator` in `_get_trainer_kwargs()`.

## Esecuzione

```bash
cd Script/
python main.py
```

Il main esegue: caricamento dati → creazione TimeSeries → training. Le sezioni di previsione e ottimizzazione sono commentate nel blocco `__main__` e attivabili al bisogno.
