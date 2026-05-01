# 🔧 Advanced Time-Series Forecasting: Custom TSMixer Implementation

## 📌 Project Overview
Questo progetto documenta lo sviluppo di una pipeline avanzata per la previsione di serie storiche multivariate. L'obiettivo principale è l'integrazione di metriche di business core con covariate esogene (ambientali e macroeconomiche) per migliorare la precisione del forecast su orizzonti a medio termine.

Il cuore tecnologico risiede nell'implementazione personalizzata dell'architettura **TSMixer**, ottimizzata per catturare pattern non lineari e gestire la stagionalità complessa attraverso un approccio probabilistico.

---

## 🏗️ Architettura Tecnica e Metodologia

### 1. Custom TSMixer con Attivazione Mish
La pipeline utilizza un'estensione del modello **TSMixer** (Time-Series Mixer). La modifica principale riguarda la sostituzione della funzione di attivazione standard (ReLU) con la **Mish Activation Function**:

f(x) = x * tanh(ln(1 + e^x))

**Vantaggi tecnici:**
*   **Gradient Flow:** A differenza di ReLU, Mish è una funzione continua e liscia, il che facilita l'ottimizzazione durante la backpropagation.
*   **Avoidance of Dying ReLU:** Previene la scomparsa del gradiente per valori negativi, permettendo una migliore capacità espressiva dei blocchi mixer.

### 2. Integrazione Multi-Sorgente
Il sistema è progettato per consolidare flussi di dati con diverse granularità e chiavi di aggregazione:
*   **Dati Target:** Serie storiche ad alta frequenza (giornaliere) aggregate per categorie e cluster geografici.
*   **Covariate Ambientali:** Integrazione di dati meteorologici (temperatura, precipitazioni) come variabili dinamiche passate per catturare l'influenza del contesto esterno.
*   **Indicatori Macro:** Inserimento di indici economici a bassa frequenza (mensili), riproiettati sulla scala giornaliera per fungere da proxy dei trend di mercato.

### 3. Feature Engineering & Preprocessing
*   **Temporal Encoding:** Implementazione di feature cicliche (Seno/Coseno) per modellare la stagionalità settimanale e annuale, unite a positional encoding per mantenere il contesto sequenziale.
*   **Static Covariates:** Gestione di metadati non temporali (es. tipologia di asset, coordinate geografiche) tramite embedding dedicati.
*   **Robust Scaling:** Applicazione di trasformazioni differenziate per target e covariate, garantendo l'assenza di data leakage tra i set di training e validation.

### 4. Strategia di Forecasting Probabilistico
A differenza dei modelli deterministici, questa pipeline implementa la **Quantile Regression**. 
Il modello non restituisce un singolo valore, ma una distribuzione di probabilità (quantili), permettendo di:
*   Valutare l'incertezza della previsione.
*   Supportare decisioni di business basate su scenari (ottimista, pessimista, neutro).
*   Configurare l'output su orizzonti mobili (es. 32 giorni di look-ahead su 64 giorni di osservazione).

---

## 🛠️ Stack Tecnologico

*   **Core Framework:** Darts (Time Series Manipulation & Modeling)
*   **Deep Learning:** PyTorch & PyTorch Lightning
*   **Optimization:** Optuna (Hyperparameter Tuning via NSGA-III)
*   **Data Science:** Pandas, NumPy, Scikit-Learn

---

## 📈 Ottimizzazione degli Iperparametri
Il tuning del modello è affidato a un framework di ottimizzazione bayesiana multi-obiettivo. Lo spazio di ricerca comprende:
*   **Architettura:** Numero di blocchi mixer e dimensione dei layer nascosti.
*   **Regolarizzazione:** Dropout dinamico per prevenire l'overfitting su dataset rumorosi.
*   **Training:** Ottimizzazione del batch size e della patience per l'Early Stopping.

L'algoritmo **NSGA-III** è stato selezionato per bilanciare simultaneamente la minimizzazione del RMSE (accuratezza globale) e del MAE (robustezza agli outlier).

---

> **Nota Professionale**: Questa documentazione descrive l'architettura logica e tecnica del sistema. Per motivi di riservatezza, il codice sorgente originale e i dataset proprietari non sono inclusi in questa esposizione.