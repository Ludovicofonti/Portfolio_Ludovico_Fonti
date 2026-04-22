# Documentazione Tecnica — Campagna Marketing Bancario

## Linguaggio e Librerie

| Componente | Strumento |
|---|---|
| Linguaggio | R |
| Manipolazione dati | `dplyr`, `janitor` |
| Visualizzazione | `ggplot2`, `corrplot` |
| Outlier detection | `isotree` (Isolation Forest) |
| Bilanciamento classi | `smotefamily` (SMOTE) |
| Modellazione | `glm` (regressione logistica), `caTools`, `caret` |
| Diagnostica | `car` (VIF), `pROC` (curva ROC) |

## Struttura dello Script

Lo script `analisi_campagna_marketing.R` segue una pipeline sequenziale in 22 step.

### 1. Caricamento e Unione dei Dati

- Due fogli Excel (`Features` e `Targets`) vengono uniti tramite `left_join` sulla chiave `Record ID`.
- I nomi delle colonne vengono normalizzati con `make_clean_names`.

### 2. Analisi Esplorativa

- Controllo dei valori mancanti per colonna.
- Distribuzione della variabile target (adesione al deposito a termine): conteggi assoluti e proporzioni.

### 3. Standardizzazione Min-Max

- Tutte le variabili numeriche vengono scalate nell'intervallo [0, 1] con la formula:  
  `(x - min) / (max - min)`
- I valori originali vengono salvati per la successiva back-transformation dei coefficienti.

### 4. Rilevamento Outlier — Isolation Forest

- Viene addestrato un Isolation Forest (`ntrees = 100`) sulle variabili numeriche standardizzate.
- Soglia al 90° percentile dell'anomaly score: le osservazioni sopra la soglia (~10%) vengono rimosse.

### 5. Feature Engineering

- Aggiunta del termine quadratico `age²` per catturare una relazione non lineare tra età e probabilità di adesione.

### 6. Pulizia Valori `unknown`

- Rimozione dei record con valore `"unknown"` nei campi: `job`, `marital_status`, `education`, `house_ownershi`, `existing_loans`.

### 7. Encoding Variabili Categoriche

| Variabile | Tipo di encoding |
|---|---|
| `education` | Ordinale (1–7: da illiterate a university.degree) |
| `marital_status` | Binario (married = 1) |
| `house_ownershi` | Binario (yes = 1) |
| `existing_loans` | Binario (yes = 1) |
| `contact_channel` | Binario (cellular = 1) |

### 8. Analisi delle Correlazioni

- Matrice di correlazione pre-selezione variabili per identificare multicollinearità e ridondanze.

### 9. Selezione Variabili

Variabili escluse dal modello:
- `call_duration` → disponibile solo post-chiamata (data leakage)
- `cons_price_idx`, `emp_var_rate`, `cons_conf_idx` → alta multicollinearità
- `record_id` → identificativo non predittivo
- `day_of_week`, `pdays`, `campaign`, `previous_default` → bassa rilevanza

### 10. Dummy Encoding e Raggruppamento

- **Professioni**: raggruppate in 4 macro-categorie (non occupati, manuali, amministrativi, autonomi), con dummy encoding e baseline = non occupati.
- **Mesi**: aggregati in **stagioni** (primavera, estate, autunno), con baseline = inverno.
- `poutcome` e variabili residue: one-hot encoding tramite `model.matrix`.

### 11. Bilanciamento Classi — SMOTE

- Applicazione di SMOTE (`K = 5`, `dup_size = 10`) per bilanciare la classe minoritaria (target = 1).

### 12. Split Train / Test

- Suddivisione 80/20 stratificata con `sample.split`.

### 13. Regressione Logistica

- Modello `glm` con famiglia `binomial` sull'intero set di variabili.
- Calcolo del VIF (Variance Inflation Factor) per verificare la multicollinearità residua.

### 14. Odds Ratio

- Calcolo degli odds ratio (`exp(β)`) e della variazione percentuale per ogni predittore.
- Ordinamento per importanza (valore assoluto del coefficiente β).

### 15. Bontà del Modello

- **McFadden R²**: confronto della log-likelihood del modello completo vs modello nullo.
- **AIC**: criterio di informazione di Akaike.

### 16. Soglia Ottimale — Youden Index

- Dalla curva ROC sul training set, viene individuata la soglia che massimizza `Sensitivity + Specificity - 1`.

### 17–18. Valutazione Train e Test

- Confusion Matrix, AUC, F1-score calcolati sia sul training che sul test set.
- Curva ROC visualizzata per entrambi.

### 19. Back-transformation dei Coefficienti

- I coefficienti stimati sulla scala Min-Max vengono riportati alla scala originale dividendo per `(max - min)` della variabile corrispondente.

### 20. Diagnostica — ANOVA (Likelihood Ratio Test)

- Test del rapporto di verosimiglianza (`anova` con `test = "Chisq"`) per verificare se l'aggiunta di `age²` migliora significativamente il modello.

### 21. Diagnostica — Test di Chow

- Identificazione dell'età ottimale come vertice della parabola: `age* = -β_age / (2 · β_age²)`.
- Split del dataset in due sottogruppi (giovani / anziani rispetto ad `age*`).
- Test di Chow (F-test sui residui) per verificare la presenza di un break strutturale nei coefficienti tra i due gruppi.

### 22. Riepilogo Finale

- Tabella comparativa delle metriche Train vs Test (Accuracy, AUC, Sensitivity, Specificity, F1-Score).
- Riepilogo soglia ottimale, McFadden R², AIC e risultati del test di Chow.

## File

| File | Descrizione |
|---|---|
| `analisi_campagna_marketing.R` | Script completo dell'analisi |
| `Marketing_Campaign.xlsx` | Dataset di input (fogli: Features, Targets) |
