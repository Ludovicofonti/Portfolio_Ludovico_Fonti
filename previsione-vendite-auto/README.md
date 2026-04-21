# 🚗 Previsione Vendite Auto USA con Variabili Macroeconomiche

> **Progetto Universitario** · Università Politecnica delle Marche

## 📌 Contesto

Previsione delle **vendite mensili del settore automobilistico negli USA** (espresse in milioni di USD) per il primo trimestre 2025, su una serie storica che copre **gennaio 1992 – dicembre 2024**. Il progetto si articola in due fasi: un'analisi **univariata** (solo la serie storica) e un'analisi **multivariata** (con variabili esogene), confrontando i risultati dei due approcci.

## 🏗️ Pipeline di Analisi

### 1. Analisi Esplorativa
- La serie mostra **crescita costante 1992–2007**, crollo durante la crisi finanziaria 2008–2010, ripresa stabile 2010–2019, crollo COVID-19 nel 2020 e forte recupero dal 2021
- Componente **stagionale regolare** presente, trend di lungo periodo crescente, residui contenuti salvo shock eccezionali
- La serie non è stazionaria: resa tale tramite **differenziazione** nei modelli ARIMA

### 2. Preprocessing
- Trasformazione in **logaritmi naturali** per stabilizzare la varianza e ridurre l'effetto di valori anomali
- Training set: dati fino a **novembre 2024**

### 3. Modello Univariato — ARIMA
- Modello selezionato: **ARIMA(0,1,2)(0,1,2)[12] con drift**
- RMSE sul training: **0.039** · AIC negativo · assenza di autocorrelazione nei residui
- Wald test: tutte le componenti MA, SMA e drift risultano significative

### 4. Selezione Variabili Esogene (Test di Granger)
| Variabile | p-value Granger | Inclusione |
|-----------|:--------------:|------------|
| Prezzo del petrolio | **< 0.001** | ✅ inclusa |
| Tasso di disoccupazione | **< 0.001** | ✅ inclusa |
| Tasso d'interesse | ≈ 0.054 | ✅ inclusa (impatto contenuto ma rilevante) |

### 5. Modello Multivariato — ARIMAX
- Selezione del modello tramite **grid search** su parametri (p,d,q) e stagionali (P,D,Q) per minimizzare RMSE
- Modello ottimale: **ARIMAX(3,1,3)(1,1,1)[12]**
- AR1 = 0.88 (forte impatto del mese precedente), SMA1 = −1 (stagionalità gestita in modo deciso)

## 📊 Metriche del Modello ARIMAX (Training Set)

| Metrica | Valore |
|---------|--------|
| ME (Mean Error) | −0.002 (assenza di bias sistematico) |
| RMSE | **0.035** |
| MAE | 0.022 |
| MAPE | **< 0.2%** |
| ACF1 residui | −0.024 (no autocorrelazione) |

## 🔍 Influenza delle Variabili Esogene

| Variabile | Direzione | Interpretazione |
|-----------|:---------:|-----------------|
| Prezzo del petrolio | **+** | Riflette fasi di espansione economica → più acquisti |
| Tasso di disoccupazione | **−** | Riduce reddito disponibile e fiducia dei consumatori |
| Tasso d'interesse | − (contenuto) | Incide sulle decisioni di acquisto in fase di stretta monetaria |

## 📈 Previsione Q1 2025

| Mese | Stima centrale | IC 99% |
|------|:--------------:|--------|
| Gennaio 2025 | **130.316 M$** | 122 – 145 M$ |
| Febbraio 2025 | **128.253 M$** | 122 – 145 M$ |
| Marzo 2025 | lieve calo | 122 – 145 M$ |

Errore di previsione (range IC 99% sul valore centrale): **7.7% – 9.3%**

## 🏛️ Analisi degli Shock Storici

Identificati 4 periodi di shock sulla serie con impatto quantificato:

| Periodo | Evento | Impatto stimato |
|---------|--------|:--------------:|
| Giu 2001 – Dic 2002 | Crisi dot-com + 11 settembre | +0.0197 (leggero rebound) |
| Giu 2008 – Dic 2009 | Crisi finanziaria globale | −0.0491 |
| Feb 2020 – Lug 2020 | Pandemia COVID-19 | **−0.1073** (impatto più marcato) |
| Gen 2022 – Gen 2023 | Inflazione, geopolitica, rialzo tassi | +0.0186 |

> Questi risultati forniscono una baseline per valutare l'impatto di shock futuri — es. i dazi USA di aprile 2025.

## 🧰 Tech Stack

`R` · `ARIMA` · `ARIMAX` · `Test di Granger` · `Grid Search` · `Trasformazione Logaritmica` · `Ljung-Box` · `Shapiro-Wilk`

## 🏷️ Tags

`Time Series` · `Forecasting` · `Automotive` · `ARIMAX` · `Variabili Esogene` · `Analisi degli Shock`
