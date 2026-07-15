# 🔧 Analisi Statistica nel Settore Automotive

> **Progetto Universitario** · Università Politecnica delle Marche

## 📌 Contesto

Il mercato automotive presenta un'elevata eterogeneità nei prezzi di vendita consigliati (MSRP), influenzati da decine di variabili tecniche e di mercato — potenza, cilindrata, consumi, categoria, dimensione del veicolo. L'obiettivo è comprendere quali fattori determinano il prezzo e segmentare il mercato in modo data-driven, confrontando molteplici tecniche di modellazione per individuare l'approccio più efficace.

## 🎯 Obiettivo

- **Prevedere il prezzo consigliato (MSRP)** dei veicoli a partire da caratteristiche tecniche e di mercato
- **Classificare i veicoli in fasce di prezzo** per supportare strategie di posizionamento
- **Segmentare il mercato** tramite clustering per identificare gruppi omogenei di veicoli

## 🏗️ Approccio

1. **Data Cleaning** — Rimozione outlier, normalizzazione delle categorie (carburante, trasmissione, trazione), gestione dei missing values
2. **Analisi Esplorativa (EDA)** — Correlazioni, distribuzioni, boxplot per variabili chiave, analisi per dimensione veicolo
3. **PCA** — Riduzione dimensionale e visualizzazione 2D/3D dei cluster per fascia di prezzo
4. **Clustering** — K-Means (con metodo del gomito) e clustering gerarchico con analisi silhouette
5. **Regressione su MSRP** — Confronto tra OLS, Decision Tree, Random Forest, Neural Network, SVM (lineare e radiale)
6. **Classificazione per fasce di prezzo** — Multinomiale, LDA, Decision Tree, Random Forest, SVM, KNN con cross-validation

## 📊 Principali Risultati

| Area | Risultato |
|------|-----------|
| Regressione | **Random Forest** miglior modello per la previsione del prezzo (RMSE più basso) |
| Classificazione | **Random Forest** e **KNN** con le accuratezze più elevate sulla classificazione in 4 fasce |
| Feature più rilevanti | Potenza (HP), cilindri, categoria Luxury/Performance |
| Clustering | 2 cluster ottimali — segmentazione in veicoli standard vs. premium |
| PCA | Le prime 3 componenti spiegano la maggior parte della varianza, con separazione visibile per fascia di prezzo |

## 🧰 Tech Stack

`R` · `tidyverse` · `caret` · `randomForest` · `neuralnet` · `rpart` · `ggplot2` · `factoextra` · `corrplot`

## 📁 Struttura

```
Script/
├── analisi_automotive.R   # Script unico con l'intera pipeline
└── README.md              # Guida tecnica allo script
```

## 🏷️ Tags

`Statistica` · `Automotive` · `Machine Learning` · `Clustering` · `PCA` · `Regressione` · `Classificazione` · `EDA`

> Progetto didattico. Il dataset e il report originari non sono pubblicati perché fonte e diritti di redistribuzione non sono documentati nel repository; il codice va utilizzato soltanto con dati pubblici, sintetici o correttamente autorizzati.
