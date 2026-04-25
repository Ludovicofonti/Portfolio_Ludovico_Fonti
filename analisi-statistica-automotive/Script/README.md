# 📖 Guida Tecnica — `analisi_automotive.R`

## Panoramica

Script R che implementa un'analisi statistica end-to-end su un dataset di ~11.000 veicoli.  
L'analisi copre l'intero workflow di un progetto di data science: dalla pulizia dei dati alla valutazione comparativa di modelli predittivi.

---

## Requisiti

### Ambiente
- **R** ≥ 4.0
- I pacchetti necessari vengono caricati all'inizio dello script

### Pacchetti R

| Pacchetto | Utilizzo |
|-----------|----------|
| `tidyverse`, `readr` | Manipolazione e importazione dati |
| `ggplot2`, `corrplot`, `gridExtra` | Visualizzazioni |
| `factoextra`, `cluster` | Clustering e PCA |
| `rgl` | Plot 3D interattivi |
| `caret` | Framework ML (train/test split, cross-validation) |
| `car`, `olsrr`, `lmtest` | Diagnostica regressione (VIF, NCV, autocorrelazione) |
| `rpart`, `rpart.plot` | Decision Tree |
| `randomForest` | Random Forest |
| `neuralnet` | Rete neurale |
| `nnet` | Regressione multinomiale |
| `MASS`, `klaR` | LDA |
| `pROC` | Curve ROC |

Per installare tutti i pacchetti in una volta:

```r
install.packages(c(
  "tidyverse", "readr", "corrplot", "ggplot2", "gridExtra",
  "factoextra", "cluster", "rgl", "caret", "car", "olsrr",
  "lmtest", "rpart", "rpart.plot", "randomForest", "neuralnet",
  "nnet", "MASS", "klaR", "pROC"
))
```

### Dataset
Il file `data.csv` deve trovarsi nella stessa cartella dello script (o nella working directory di R).

---

## Struttura dello Script

Lo script è organizzato in **6 sezioni** sequenziali, ciascuna identificata da un header con separatore visivo.

### 1. Data Cleaning
- Caricamento del dataset e standardizzazione dei nomi colonna
- Filtraggio outlier (`MSRP > 2000`, `MSRP ≤ 300000`, `highway.MPG ≤ 300`)
- Rimozione righe con valori mancanti e duplicati
- Raggruppamento categorie sparse:
  - **Carburante**: tutte le varianti unleaded → `"unleaded"`
  - **Trasmissione**: `DIRECT_DRIVE` e `UNKNOWN` → `"AUTOMATED_MANUAL"`
  - **Trazione**: `four wheel drive` → `"all wheel drive"`
- Parsing della colonna `Market.Category` (multi-valore separata da virgola)

### 2. Analisi Esplorativa (EDA)
- Matrice di correlazione (`corrplot`)
- Statistiche descrittive raggruppate per `Vehicle.Size`
- Boxplot: anno, HP, MSRP, consumi, cilindri
- Relazioni incrociate: cilindri vs consumi, HP vs city MPG, dimensione vs variabili chiave
- Distribuzioni: anno, potenza, cilindri, carrozzeria, trasmissione, trazione, carburante
- Creazione della variabile `Fascia.Prezzo` (4 fasce: 0-15k, 15k-30k, 30k-50k, 50k+)

### 3. PCA (Analisi Componenti Principali)
- Variabili: Year, Engine.HP, Cylinders, Transmission, Doors, MPG, Popularity, Vehicle.Size
- Scree plot e contributo variabili (`fviz_pca_var`)
- Visualizzazione 2D e 3D interattiva (`rgl`) colorata per fascia di prezzo
- Calcolo centroidi PCA per fascia

### 4. Clustering
- **K-Means**: Elbow method (k = 1-10), fit con k = 2, visualizzazione cluster
- **Gerarchico**: distanza euclidea, dendrogramma, taglio a h = 200000
- **Validazione**: silhouette plot via PAM
- Top 10 marchi per MSRP medio

### 5. Predizione MSRP (Regressione)
Feature engineering con dummy encoding delle variabili categoriche (stile, categoria di mercato, trasmissione, trazione, dimensione).

| Modello | Dettagli |
|---------|----------|
| **OLS** | Con diagnostica completa: VIF, Q-Q plot, test NCV, autocorrelazione |
| **OLS Scalata** | Stesse feature, dati standardizzati |
| **OLS + PCA** | Regressione sulle prime 3 componenti principali |
| **Decision Tree** | `rpart` con pruning via `cp` ottimale |
| **Random Forest** | 500 alberi, variable importance |
| **Neural Network** | `neuralnet`, architettura 2-1-3 |
| **SVM Lineare** | `caret` con 10-fold CV |
| **SVM Radiale** | Kernel RBF con 10-fold CV |

Output: tabella riepilogativa RMSE per tutti i modelli.

### 6. Classificazione per Fasce di Prezzo
Target: `Fascia.Prezzo` (4 classi). MSRP rimosso dai predittori.

| Modello | Dettagli |
|---------|----------|
| **Multinomiale** | `nnet::multinom` |
| **LDA** | `MASS::lda` con plot discriminante |
| **Decision Tree** | `rpart` con pruning |
| **Random Forest** | 500 alberi, variable importance |
| **SVM Lineare** | 10-fold CV |
| **KNN** | k = 1-10 con selezione automatica |

Output: tabella riepilogativa accuratezza per tutti i modelli.

---

## Esecuzione

1. Aprire R o RStudio
2. Impostare la working directory sulla cartella `Script/`:
   ```r
   setwd("percorso/alla/cartella/Script")
   ```
3. Eseguire lo script:
   ```r
   source("analisi_automotive.R")
   ```

> **Nota**: la sezione PCA 3D apre una finestra interattiva `rgl`. Chiuderla prima di proseguire se si esegue tutto lo script in blocco.

---

## Dataset — `data.csv`

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| Make | chr | Marca del veicolo |
| Model | chr | Modello |
| Year | int | Anno di produzione |
| Engine Fuel Type | chr | Tipo di carburante |
| Engine HP | dbl | Potenza in cavalli |
| Engine Cylinders | int | Numero di cilindri |
| Transmission Type | chr | Tipo di trasmissione |
| Driven Wheels | chr | Tipo di trazione |
| Number of Doors | int | Numero di porte |
| Market Category | chr | Categorie di mercato (multi-valore) |
| Vehicle Size | chr | Dimensione (Compact / Midsize / Large) |
| Vehicle Style | chr | Stile carrozzeria |
| highway MPG | int | Consumo autostradale |
| city mpg | int | Consumo in città |
| Popularity | int | Indice di popolarità |
| MSRP | int | Prezzo consigliato (variabile target) |
