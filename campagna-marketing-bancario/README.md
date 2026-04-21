# 🏦 Campagna Marketing per Istituto Bancario

> **Progetto Universitario** · Università Politecnica delle Marche

## 📌 Contesto

Un istituto bancario vuole ottimizzare una campagna di marketing diretto finalizzata alla sottoscrizione di **depositi a termine**. Il dataset contiene variabili demografiche, finanziarie, macroeconomiche e informazioni sulle interazioni pregresse con i clienti.

## 🎯 Obiettivo

Costruire un modello predittivo in grado di stimare la probabilità di adesione di ciascun cliente, per indirizzare in modo più efficiente le risorse della campagna e massimizzare il tasso di conversione.

## 🏗️ Pipeline di Analisi

### 1. Preprocessing & Feature Engineering
- Analisi esplorativa e pulizia del dataset: gestione dei valori `unknown`, rimozione delle variabili ridondanti o non informative (es. `Record ID`, `Day of Week`)
- Rimozione delle variabili altamente correlate per evitare multicollinearità (`Cons Conf Idx`, `Cons Price Index`, `Emp Var Rate`)
- Esclusione della variabile `Call Duration`: disponibile solo a fine chiamata, inutilizzabile per la previsione e fonte potenziale di overfitting
- Creazione della variabile `Age²` per catturare la **relazione non lineare** tra età e propensione all'acquisto
- Encoding delle variabili categoriche (ordinali e nominali) e standardizzazione Min-Max
- Bilanciamento delle classi con **SMOTE** (ratio 60-40 per preservare la distribuzione realistica): la variabile target presentava uno sbilanciamento di circa 90/10
- Split train/test: 80% / 20%

### 2. Modellazione — Regressione Logistica
- Stima degli **odds ratio** per ogni feature, con intervalli di confidenza al 95%
- Threshold ottimale fissato a **0.4** per bilanciare sensibilità e specificità

### 3. Insight sull'età
- Analisi approfondita della relazione non lineare tra età e probabilità di conversione tramite **ANOVA** e **test di Chow**
- Identificato un **punto ottimale intorno ai 27 anni**, oltre il quale la probabilità decresce
- Costruzione di **modelli separati per giovani (Under 27) e adulti (Over 27)** per analizzare leve decisionali differenti

## 📊 Risultati del Modello

| Metrica | Valore |
|---------|--------|
| Accuratezza | **70.53%** |
| AUC | **0.7634** |
| Sensibilità | 66.06% |
| Specificità | 73.57% |
| F1-Score | 0.6449 |
| Kappa | 0.3932 |
| McFadden R² | 0.1804 |

## 🔍 Principali Driver di Conversione

| Variabile | Odds Ratio | Interpretazione |
|-----------|-----------|-----------------|
| `POutcome Success` | ~8x | Contatto positivo pregresso: il fattore più predittivo |
| `Previous` (negativo) | 0.015 | Contatti passati senza successo: probabilità crolla |
| `Cellular` | 2.56 | Il canale telefonico raddoppia la probabilità di successo |
| `Euribor3m` | 0.118 | Tassi alti riducono drasticamente la propensione |
| `Age` + `Age²` | non lineare | Picco di conversione ~27 anni |
| `Autumn` | 0.399 | L'autunno è il periodo meno favorevole alla campagna |
| `Existing Loans` | 0.778 | Prestiti attivi riducono la propensione |

## 💡 Raccomandazioni Strategiche

- **Priorità ai clienti con POutcome Success**: massima probabilità di conversione
- **Evitare clienti con Previous elevato**: rischio di percezione negativa; preferire approcci soft (es. report informativi)
- **Privilegiare il canale cellulare** come leva principale di contatto
- **Monitorare l'Euribor**: sospendere o rimodulare la campagna in periodi di tassi elevati
- **Segmentare per età**: strategie differenziate per Under 27 (meno influenzati da esperienze pregresse) e Over 27 (più sensibili alla relazione con la banca e alla stagionalità)
- **Evitare lanci autunnali**: periodo statisticamente meno favorevole all'adesione

## 🧰 Tech Stack

`R` · `Regressione Logistica` · `SMOTE` · `ANOVA` · `Test di Chow` · `Analisi della Correlazione`

## 🏷️ Tags

`Classificazione` · `Marketing` · `Banking` · `Regressione Logistica` · `Feature Engineering` · `Analisi Statistica`
