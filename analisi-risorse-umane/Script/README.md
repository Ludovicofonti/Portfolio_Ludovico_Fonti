# 📖 Guida Tecnica — `HR_analysis.R`

## Panoramica

Script R che implementa un'analisi end-to-end sull'attrition dei dipendenti.  
Il workflow copre: pulizia dati, EDA, regressione lineare e logistica, analisi discriminante, PCA e clustering.

---

## Requisiti

### Ambiente
- **R** ≥ 4.0

### Pacchetti R

| Pacchetto | Utilizzo |
|-----------|----------|
| `readr`, `dplyr` | Importazione e manipolazione dati |
| `ggplot2`, `gridExtra`, `grid` | Visualizzazioni |
| `corrplot` | Matrice di correlazione |
| `car`, `olsrr`, `lmtest` | Diagnostica regressione (VIF, NCV, normalità residui) |
| `caret` | Train/test split, cross-validation |
| `pscl`, `aod` | McFadden R², test di Wald |
| `MASS` | LDA, QDA |
| `pROC` | Curve ROC e AUC |
| `ROSE` | Bilanciamento dataset (under-sampling) |
| `klaR` | Partition plot per analisi discriminante |
| `factoextra`, `cluster` | Clustering e PCA |
| `NbClust` | Selezione automatica del numero ottimale di cluster |

Per installare tutti i pacchetti in una volta:

```r
install.packages(c(
  "readr", "dplyr", "ggplot2", "gridExtra", "corrplot",
  "car", "olsrr", "lmtest", "caret", "grid", "pscl", "aod",
  "MASS", "pROC", "ROSE", "klaR", "factoextra", "cluster", "NbClust"
))
```

### Dataset
Il file `HR_Analytics.csv` deve trovarsi nella stessa cartella dello script (o nella working directory di R).

---

## Struttura dello Script

Lo script è organizzato in **7 sezioni** sequenziali.

### 1. Data Loading & Cleaning
- Caricamento CSV e rimozione colonne non informative (`EmpID`, `EmployeeCount`, `EmployeeNumber`, `SalarySlab`, `Over18`, `StandardHours`)
- Gestione valori mancanti con `na.omit()`
- Fix etichette inconsistenti (`TravelRarely` → `Travel_Rarely`)
- Creazione variabili dummy: `Attrition_bin`, `Travel`, `Male`, `Relationship`, `OverTime_yes`
- Costruzione del dataset di regressione (solo variabili numeriche)
- Log-trasformazione di `MonthlyIncome` e rimozione variabili con basso information rate

### 2. Analisi Esplorativa (EDA)
- Boxplot di tutte le variabili numeriche
- Scatterplot vs `MonthlyIncome` (Age, JobLevel, YearsInCurrentRole, NumCompaniesWorked)
- Distribuzione del reddito: istogramma, densità, overlay
- Breakdown dell'attrition per: genere, fascia d'età, overtime, business travel (con percentuali)
- Matrice di correlazione (`corrplot`)

### 3. Regressione Lineare — `MonthlyIncome`
- Modello: `log(MonthlyIncome) ~ sqrt(Age) + JobLevel + YearsInCurrentRole + NumCompaniesWorked`
- Diagnostica completa:
  - Media residui ≈ 0
  - Q-Q plot e test di normalità (`ols_test_normality`)
  - Istogramma residui
  - Test NCV per eteroschedasticità
  - Test autocorrelazione

### 4. Regressione Logistica — `Attrition`
- Train/test split 80/20 con `createDataPartition` (seed = 6)
- Modello logit su tutte le variabili del dataset di regressione
- Funzione `evaluate_logit()` per valutazione a soglia variabile (accuracy, sensitivity, specificity)
- Soglia ottimale via indice di **Youden** dalla curva ROC
- Valutazione su train e test set
- **McFadden R²** e **test di Wald**
- Curva ROC con soglia ottimale annotata + AUC
- ROC costruita manualmente (threshold-by-threshold) per visualizzazione dettagliata
- **Likelihood-ratio test**

### 5. Analisi Discriminante (LDA / QDA)
- Bilanciamento dataset con under-sampling (`ROSE::ovun.sample`, N = 500)
- **LDA**: fit, plot discriminante, accuratezza, partition plot
- **QDA**: fit, accuratezza, partition plot
- **Confronto ROC**: Logistica vs LDA vs QDA con AUC nella legenda

### 6. PCA (Analisi Componenti Principali)
- PCA su tutte le variabili del dataset di regressione (correlazione)
- Scree plot (`fviz_eig`)
- Score plot 2D (PC1 vs PC2) colorato per attrition
- Analisi della soglia su PC2 per discriminare attrition

### 7. Clustering — Solo dipendenti usciti
Il clustering opera esclusivamente sul sottoinsieme di dipendenti con `Attrition = Yes`, rimuovendo le variabili dummy binarie.

| Metodo | Dettagli |
|--------|----------|
| **Gerarchico (Canberra + Complete)** | Dendrogramma, distanza aggregazione, NbClust per k ottimale, silhouette |
| **Gerarchico (Euclidea + Ward)** | Dendrogramma, ANOVA sulle variabili chiave per k = 4 |
| **Profiling k = 2** | Summary statistico per ciascun gruppo |
| **PAM** | Silhouette per k = 2..7 |
| **K-Means** | k = 2 su tutte le variabili + versione raffinata su variabili chiave |
| **Elbow analysis** | Delta R² e Delta F-statistic per k = 2..10 |

---

## Esecuzione

1. Aprire R o RStudio
2. Impostare la working directory sulla cartella `Script/`:
   ```r
   setwd("percorso/alla/cartella/Script")
   ```
3. Eseguire lo script:
   ```r
   source("HR_analysis.R")
   ```

---

## Dataset — `HR_Analytics.csv`

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| EmpID | chr | ID dipendente (rimosso) |
| Age | int | Età |
| AgeGroup | chr | Fascia d'età |
| Attrition | chr | Uscita volontaria (Yes/No) — **target classificazione** |
| BusinessTravel | chr | Frequenza viaggi di lavoro |
| DailyRate | int | Tariffa giornaliera |
| Department | chr | Dipartimento |
| DistanceFromHome | int | Distanza casa-lavoro |
| Education | int | Livello di istruzione (1-5) |
| EducationField | chr | Campo di studi |
| EnvironmentSatisfaction | int | Soddisfazione ambiente (1-4) |
| Gender | chr | Genere |
| HourlyRate | int | Tariffa oraria |
| JobInvolvement | int | Coinvolgimento nel lavoro (1-4) |
| JobLevel | int | Livello professionale |
| JobRole | chr | Ruolo |
| JobSatisfaction | int | Soddisfazione lavorativa (1-4) |
| MaritalStatus | chr | Stato civile |
| MonthlyIncome | int | Reddito mensile — **target regressione** |
| MonthlyRate | int | Tariffa mensile |
| NumCompaniesWorked | int | Numero aziende precedenti |
| OverTime | chr | Lavoro straordinario (Yes/No) |
| PercentSalaryHike | int | Percentuale ultimo aumento |
| PerformanceRating | int | Valutazione performance (1-4) |
| RelationshipSatisfaction | int | Soddisfazione relazionale (1-4) |
| StockOptionLevel | int | Livello stock option (0-3) |
| TotalWorkingYears | int | Anni di esperienza totale |
| TrainingTimesLastYear | int | Sessioni formazione ultimo anno |
| WorkLifeBalance | int | Equilibrio vita-lavoro (1-4) |
| YearsAtCompany | int | Anni in azienda |
| YearsInCurrentRole | int | Anni nel ruolo attuale |
| YearsSinceLastPromotion | int | Anni dall'ultima promozione |
| YearsWithCurrManager | int | Anni con il manager attuale |
