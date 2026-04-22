# Documentazione Tecnica — Segmentazione Clienti

## Linguaggio e Librerie

| Componente | Strumento |
|---|---|
| Linguaggio | R |
| Manipolazione dati | `dplyr`, `openxlsx` |
| Visualizzazione | `ggplot2`, `ggcorrplot`, `factoextra` |
| Clustering | `cluster` (PAM, silhouette) |

## Struttura dello Script

Lo script `analisi_segmentazione_clienti.R` implementa una segmentazione non supervisionata tramite l'algoritmo PAM (Partitioning Around Medoids).

### 1. Caricamento Dati

- Dataset `dati_segmentazione_clienti.xlsx` con 2.999 transazioni nel periodo 01/01/2018 – 28/04/2019.

### 2. Data Quality e Preprocessing

- **Conversione valori negativi**: le colonne monetarie e di quantità (`Gross.Sales`, `Discounts`, `Returns`, ecc.) vengono convertite in valore assoluto.
- **Controllo duplicati** e valori mancanti.
- **Filtro di consistenza**: vengono mantenuti solo i record dove `Gross.Sales - Discounts == Net.Sales`.
- **Ricalcolo**: `Total.Sales.Correct = Net.Sales + Taxes`.
- **Rimozione righe a zero**: record con `Net.Sales = 0` e nessun reso.
- **Drop colonne ridondanti**: `Total.Sales` (ricalcolata), `Returns` (incorporata in `Returned.Item.Quantity`).

### 3. Analisi Esplorativa (EDA)

- **Matrice di correlazione** (`ggcorrplot`) sulle variabili numeriche.
- **Boxplot** delle variabili monetarie principali (`Gross.Sales`, `Net.Sales`, `Discounts`).

### 4. Clustering — PAM

#### Variabili di clustering

| Variabile | Descrizione |
|---|---|
| `Net.Sales` | Vendite nette |
| `Discounts` | Sconti applicati |
| `Returned.Item.Quantity` | Quantità di item resi |
| `Ordered.Item.Quantity` | Quantità di item ordinati |

#### Procedura

1. **Standardizzazione Z-score** delle 4 variabili.
2. **Distanza di Manhattan** calcolata sulla matrice standardizzata.
3. **Selezione del numero ottimale di cluster (k)**:
   - Metodo del gomito (Elbow Method) → minimizzazione WSS
   - Metodo della silhouette → massimizzazione della silhouette media
   - **k ottimale selezionato: 3**
4. **Fitting PAM** (`pam(dist_manhattan, k = 3, diss = TRUE)`).
5. **Silhouette analysis**: calcolo della silhouette media e visualizzazione per cluster.

### 5. Profilazione dei Cluster

- **Medoidi**: osservazioni rappresentative di ciascun cluster (valori standardizzati).
- **Centroidi**: medie per cluster nella scala originale.
- **Statistiche descrittive**: per ogni cluster e variabile → media, mediana, deviazione standard, min, max.

### 6. Visualizzazione dei Cluster

- **Cluster plot PCA**: proiezione 2D tramite PCA con ellissi convesse colorate per cluster.
- **Boxplot per cluster**: distribuzione di `Net.Sales` e `Discounts` per ciascun segmento.

### 7. Analisi Prodotti per Cluster

- Distribuzione della frequenza di `Product.Type` e `Product.Title` per cluster (bar chart raggruppati).
- Scatter plot di `Net.Sales` per `Product.Type`, colorato per cluster.

## File

| File | Descrizione |
|---|---|
| `analisi_segmentazione_clienti.R` | Script completo dell'analisi |
| `dati_segmentazione_clienti.xlsx` | Dataset transazionale di input |
