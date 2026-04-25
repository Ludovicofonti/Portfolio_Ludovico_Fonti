# 👔 Analisi Risorse Umane — Employee Attrition

> **Progetto Universitario** · Università Politecnica delle Marche

## 📌 Contesto

Il turnover dei dipendenti rappresenta un costo significativo per le aziende: recruiting, onboarding e perdita di know-how impattano direttamente sulla produttività. L'analisi si concentra su un dataset HR di ~1.500 dipendenti con l'obiettivo di comprendere i fattori che determinano l'abbandono volontario e costruire modelli predittivi per identificare i dipendenti a rischio.

## 🎯 Obiettivo

- **Identificare i driver principali dell'attrition** (soddisfazione, overtime, retribuzione, anzianità)
- **Prevedere il rischio di abbandono** di ciascun dipendente tramite modelli di classificazione
- **Segmentare i dipendenti usciti** in profili omogenei per interventi HR mirati
- **Analizzare i fattori retributivi** tramite regressione sul reddito mensile

## 🏗️ Approccio

1. **Data Cleaning** — Rimozione colonne non informative, gestione missing values, creazione variabili dummy
2. **Analisi Esplorativa (EDA)** — Distribuzioni, correlazioni, breakdown dell'attrition per genere, età, overtime, business travel
3. **Regressione Lineare** — Modello su `log(MonthlyIncome)` con diagnostica completa dei residui
4. **Regressione Logistica** — Predizione dell'attrition con ottimizzazione della soglia via ROC/Youden, curva ROC, test di Wald e likelihood-ratio
5. **Analisi Discriminante** — LDA e QDA su dataset bilanciato (under-sampling), confronto ROC con logistica
6. **PCA** — Riduzione dimensionale e score plot colorato per attrition
7. **Clustering** — Gerarchico (Canberra + Ward), PAM e K-Means con silhouette, NbClust e elbow analysis

## 📊 Principali Risultati

| Area | Risultato |
|------|-----------|
| Driver attrition | **Overtime, soddisfazione lavorativa, job level e numero di aziende precedenti** tra i predittori più significativi |
| Regressione logistica | Soglia ottimale (Youden) migliora sensibilmente la **sensitivity** rispetto al default 0.5 |
| Confronto modelli | **Regressione logistica con AUC più alta** rispetto a LDA e QDA |
| PCA | PC2 discrimina parzialmente tra dipendenti usciti e rimasti |
| Clustering | **2 cluster ottimali** tra i dipendenti usciti — profili con diversa anzianità e livello retributivo |
| Retribuzione | **Job Level e Years in Current Role** principali predittori del reddito mensile |

## 🧰 Tech Stack

`R` · `caret` · `MASS` · `pROC` · `ROSE` · `factoextra` · `corrplot` · `ggplot2` · `NbClust`

## 📁 Struttura

```
Script/
├── HR_analysis.R      # Script unico con l'intera pipeline
├── HR_Analytics.csv   # Dataset (~1.500 dipendenti)
└── README.md          # Guida tecnica allo script
```

## 🏷️ Tags

`People Analytics` · `Classificazione` · `HR` · `Regressione Logistica` · `Clustering` · `PCA` · `LDA` · `EDA`
